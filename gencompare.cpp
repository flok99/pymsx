#include <assert.h>
#include <initializer_list>
#include <stdio.h>
#include <string.h>
#include <z80ex/z80ex.h>
#include <z80ex/z80ex_dasm.h>

bool quick = false;

uint8_t ram[65536];

Z80EX_BYTE read_mem_cb(Z80EX_CONTEXT *z80, Z80EX_WORD addr, int m1_state, void *user_data)
{
	fprintf(stderr, "z80 read %04x: %02x\n", addr, ram[addr]);
	return ram[addr];
}

void write_mem_cb(Z80EX_CONTEXT *z80, Z80EX_WORD addr, Z80EX_BYTE value, void *user_data)
{
//	printf("z80 write %04x: %02x\n", addr, value);
	ram[addr] = value;
}

void write_port(Z80EX_CONTEXT *z80, Z80EX_WORD port, Z80EX_BYTE value, void *user_data)
{
}

Z80EX_BYTE read_port(Z80EX_CONTEXT *z80, Z80EX_WORD port, void *user_data)
{
	return 0;
}

Z80EX_BYTE read_interrupt_vector(Z80EX_CONTEXT *z80, void *user_data)
{
	return 0;
}

Z80EX_CONTEXT * init_test()
{
	printf("reset\n");
	memset(ram, 0x00, sizeof ram);

	Z80EX_CONTEXT *z80 = z80ex_create(read_mem_cb, NULL, write_mem_cb, NULL, read_port, NULL, write_port, NULL, read_interrupt_vector, NULL);

	z80ex_set_reg(z80, regAF, 0x0000);
	z80ex_set_reg(z80, regPC, 0x0000);
	z80ex_set_reg(z80, regSP, 0x3fff);

	return z80;
}

void uninit_test(Z80EX_CONTEXT *const z80)
{
	z80ex_destroy(z80);
}

void dump_state(const char *const name, Z80EX_CONTEXT *const z80, int endaddr, int cycles)
{
	printf("%s ", name);

	for(int i=0; i<endaddr; i++)
		printf("%02x ", ram[i]);

	printf("| %04x %d", endaddr, cycles);

	for(int i=regAF; i<=regIFF2; i++)
		printf(" %04x", z80ex_get_reg(z80, Z80_REG_T(i)));

	printf("\n");
}

void memcheck(int a, uint8_t v)
{
	if (ram[a] != v)
		fprintf(stderr, "mem %04x: %02x expecting %02x\n", a, ram[a], v);

	assert(ram[a] == v); // sanity check

	printf("memchk %04x %02x\n", a, v);
}

void do_memset(int a, uint8_t v)
{
	ram[a] = v;
	printf("memset %04x %02x\n", a, v);
}

void run(Z80EX_CONTEXT *const z80, int endaddr)
{
	int cycles = 0;

	do {
		cycles += z80ex_step(z80);
	}
	while(z80ex_get_reg(z80, regPC) < endaddr || (endaddr == 0 && z80ex_last_op_type(z80) != 0));

	dump_state("after", z80, endaddr, cycles);
}

uint8_t get(Z80EX_CONTEXT *const z80, const int reg_nr)
{
	if (reg_nr == 0)
		return z80ex_get_reg(z80, regBC) >> 8;
	else if (reg_nr == 1)
		return z80ex_get_reg(z80, regBC) & 255;
	else if (reg_nr == 2)
		return z80ex_get_reg(z80, regDE) >> 8;
	else if (reg_nr == 3)
		return z80ex_get_reg(z80, regDE) & 255;
	else if (reg_nr == 4)
		return z80ex_get_reg(z80, regHL) >> 8;
	else if (reg_nr == 5)
		return z80ex_get_reg(z80, regHL) & 255;
	else if (reg_nr == 6)
		return ram[z80ex_get_reg(z80, regHL)];
	else if (reg_nr == 7)
		return z80ex_get_reg(z80, regAF) >> 8;
	
	assert(0);
}

void set(Z80EX_CONTEXT *const z80, const int reg_nr, const uint8_t vin)
{
	if (reg_nr == 0)
		z80ex_set_reg(z80, regBC, (z80ex_get_reg(z80, regBC) & 0x00ff) | (vin << 8));
	else if (reg_nr == 1)
		z80ex_set_reg(z80, regBC, (z80ex_get_reg(z80, regBC) & 0xff00) | vin);
	else if (reg_nr == 2)
		z80ex_set_reg(z80, regDE, (z80ex_get_reg(z80, regDE) & 0x00ff) | (vin << 8));
	else if (reg_nr == 3)
		z80ex_set_reg(z80, regDE, (z80ex_get_reg(z80, regDE) & 0xff00) | vin);
	else if (reg_nr == 4)
		z80ex_set_reg(z80, regHL, (z80ex_get_reg(z80, regHL) & 0x00ff) | (vin << 8));
	else if (reg_nr == 5)
		z80ex_set_reg(z80, regHL, (z80ex_get_reg(z80, regHL) & 0xff00) | vin);
	else if (reg_nr == 6)
		ram[z80ex_get_reg(z80, regHL)] = vin;
	else if (reg_nr == 7)
		z80ex_set_reg(z80, regAF, (z80ex_get_reg(z80, regAF) & 0x00ff) | (vin << 8));
	else
		assert(0);
}

void emit_rlc()
{
	fprintf(stderr, "RLC\n");

	for(int f=0; f<256; f++) {
		for(int instr=0x00; instr<0x08; instr++) {
			for(int v=0; v<256; v += quick ? 13 : 1) {
				Z80EX_CONTEXT *z80 = init_test();

				z80ex_set_reg(z80, regAF, f);
				set(z80, instr & 0x07, v);
				ram[0] = 0xcb;
				ram[1] = instr;
				ram[2] = 99;
				z80ex_set_reg(z80, regHL, 2);

				dump_state("before", z80, 0x0003, 0);

				run(z80, 0x0002);

				uninit_test(z80);
			}
		}
	}

	fprintf(stderr, "RLC (IX+*)\n");
	for(int o=-128; o<128; o++) {
		for(int f=0; f<256; f++) {
			for(int v1=0; v1<256; v1 += quick ? 13 : 1) {
				Z80EX_CONTEXT *z80 = init_test();

				z80ex_set_reg(z80, regIX, 0x1000);
				z80ex_set_reg(z80, regAF, f);
				ram[0] = 0xdd;
				ram[1] = 0xcb;
				ram[2] = o;
				ram[3] = 0x06;
				do_memset(0x1000 + o, v1);

				dump_state("before", z80, 0x0004, 0);

				run(z80, 0x0004);

				uninit_test(z80);
			}
		}
	}
}

void emit_rrc()
{
	fprintf(stderr, "RRC\n");

	for(int f=0; f<256; f++) {
		for(int instr=0x08; instr<0x10; instr++) {
			for(int v=0; v<256; v += quick ? 13 : 1) {
				Z80EX_CONTEXT *z80 = init_test();

				z80ex_set_reg(z80, regAF, f);
				set(z80, instr & 0x07, v);
				ram[0] = 0xcb;
				ram[1] = instr;
				ram[2] = 99;
				z80ex_set_reg(z80, regHL, 2);

				dump_state("before", z80, 0x0003, 0);

				run(z80, 0x0002);

				uninit_test(z80);
			}
		}
	}
}

void emit_rl()
{
	fprintf(stderr, "RL\n");

	for(int f=0; f<256; f++) {
		for(int instr=0x10; instr<0x18; instr++) {
			for(int v=0; v<256; v += quick ? 13 : 1) {
				Z80EX_CONTEXT *z80 = init_test();

				z80ex_set_reg(z80, regAF, f);
				set(z80, instr & 0x07, v);
				ram[0] = 0xcb;
				ram[1] = instr;
				ram[2] = 99;
				z80ex_set_reg(z80, regHL, 2);

				dump_state("before", z80, 0x0003, 0);

				run(z80, 0x0002);

				uninit_test(z80);
			}
		}
	}
}

void emit_rr()
{
	fprintf(stderr, "RR\n");

	for(int f=0; f<256; f++) {
		for(int instr=0x18; instr<0x20; instr++) {
			for(int v=0; v<256; v += quick ? 13 : 1) {
				Z80EX_CONTEXT *z80 = init_test();

				z80ex_set_reg(z80, regAF, f);
				set(z80, instr & 0x07, v);
				ram[0] = 0xcb;
				ram[1] = instr;
				ram[2] = 99;
				z80ex_set_reg(z80, regHL, 2);

				dump_state("before", z80, 0x0003, 0);

				run(z80, 0x0002);

				uninit_test(z80);
			}
		}
	}
}

void emit_sla()
{
	fprintf(stderr, "SLA\n");

	for(int instr=0x20; instr<0x28; instr++) {
		for(int v=0; v<256; v += quick ? 13 : 1) {
			Z80EX_CONTEXT *z80 = init_test();

			set(z80, instr & 0x07, v);
			ram[0] = 0xcb;
			ram[1] = instr;
			ram[2] = 99;
			z80ex_set_reg(z80, regHL, 2);

			dump_state("before", z80, 0x0003, 0);

			run(z80, 0x0002);

			uninit_test(z80);
		}
	}
}

void emit_sra()
{
	fprintf(stderr, "SRA\n");

	for(int f=0; f<256; f++) {
		for(int instr=0x28; instr<0x30; instr++) {
			for(int v=0; v<256; v += quick ? 13 : 1) {
				Z80EX_CONTEXT *z80 = init_test();

				z80ex_set_reg(z80, regAF, f);
				set(z80, instr & 0x07, v);
				ram[0] = 0xcb;
				ram[1] = instr;
				ram[2] = 99;
				z80ex_set_reg(z80, regHL, 2);

				dump_state("before", z80, 0x0003, 0);

				run(z80, 0x0002);

				uninit_test(z80);
			}
		}
	}
}

void emit_sll()
{
	fprintf(stderr, "SLL\n");

	for(int instr=0x30; instr<0x38; instr++) {
		for(int v=0; v<256; v++) {
			Z80EX_CONTEXT *z80 = init_test();

			set(z80, instr & 0x07, v);
			ram[0] = 0xcb;
			ram[1] = instr;
			ram[2] = 99;
			z80ex_set_reg(z80, regHL, 2);

			dump_state("before", z80, 0x0003, 0);

			run(z80, 0x0002);

			uninit_test(z80);
		}
	}
}

void emit_srl()
{
	fprintf(stderr, "SRL\n");

	for(int instr=0x38; instr<0x40; instr++) {
		for(int v=0; v<256; v++) {
			Z80EX_CONTEXT *z80 = init_test();

			set(z80, instr & 0x07, v);
			ram[0] = 0xcb;
			ram[1] = instr;
			ram[2] = 99;
			z80ex_set_reg(z80, regHL, 2);

			dump_state("before", z80, 0x0003, 0);

			run(z80, 0x0002);

			uninit_test(z80);
		}
	}
}

void emit_bit()
{
	fprintf(stderr, "bit\n");

	// regular bit
	for(int instr=0x40; instr<0x80; instr++) {
		for(int f=0; f<256; f++) {
			for(int v=0; v<256; v++) {
				Z80EX_CONTEXT *z80 = init_test();

				ram[0] = 0xcb;
				ram[1] = instr;
				ram[2] = -1;

				z80ex_set_reg(z80, regAF, f);
				z80ex_set_reg(z80, regHL, 0x0002);
				set(z80, instr & 7, v);

				dump_state("before", z80, 0x0003, 0);

				run(z80, 0x0002);

				if ((instr & 7) == 6)
					memcheck(0x0002, v);

				uninit_test(z80);
			}
		}
	}

	// only testing ix
	fprintf(stderr, "bit ix/y\n");

	for(int instr=0x40; instr<0x80; instr++) {
		for(int o=-128; o<128; o++) {
			for(int f=0; f<256; f++) {
				for(int v=0; v<256; v++) {
					Z80EX_CONTEXT *z80 = init_test();

					ram[0] = 0xdd;
					ram[1] = 0xcb;
					ram[2] = o;
					ram[3] = instr;

					z80ex_set_reg(z80, regAF, f);
					z80ex_set_reg(z80, regIX, 0x2233 + o);
					do_memset(0x2233 + o, v);

					dump_state("before", z80, 0x0004, 0);

					run(z80, 0x0004);

					uninit_test(z80);
				}
			}
		}
	}
}

void emit_res_set()
{
	fprintf(stderr, "res & set\n");

	for(int instr=0x80; instr<0x100; instr++) {
		for(int f=0; f<256; f++) {
			for(int v=0; v<256; v++) {
				Z80EX_CONTEXT *z80 = init_test();

				z80ex_set_reg(z80, regAF, f);
				z80ex_set_reg(z80, regHL, 0x0002);
				set(z80, instr & 7, v);
				ram[0] = 0xcb;
				ram[1] = instr;
				ram[2] = v;

				dump_state("before", z80, 0x0003, 0);

				run(z80, 0x0002);

				uninit_test(z80);
			}
		}
	}
}

void emit_daa()
{
	fprintf(stderr, "DAA\n");

	for(int f=0; f<256; f++) {
		for(int v=0; v<256; v++) {
			Z80EX_CONTEXT *z80 = init_test();

			z80ex_set_reg(z80, regAF, f);
			set(z80, 0x07, v);
			ram[0] = 0x27;

			dump_state("before", z80, 0x0001, 0);

			run(z80, 0x0001);

			uninit_test(z80);
		}
	}
}

void emit_cpl()
{
	fprintf(stderr, "CPL\n");

	for(int v=0; v<256; v++) {
		Z80EX_CONTEXT *z80 = init_test();

		set(z80, 0x07, v);
		ram[0] = 0x2f;

		dump_state("before", z80, 0x0001, 0);

		run(z80, 0x0001);

		uninit_test(z80);
	}
}

void emit_scf()
{
	fprintf(stderr, "SCF\n");

	for(int v=0; v<256; v++) {
		Z80EX_CONTEXT *z80 = init_test();

		set(z80, 0x07, v);
		ram[0] = 0x37;

		dump_state("before", z80, 0x0001, 0);

		run(z80, 0x0001);

		uninit_test(z80);
	}
}

void emit_ccf()
{
	fprintf(stderr, "CCF\n");

	for(int f=0; f<256; f++) {
		for(int v=0; v<256; v++) {
			Z80EX_CONTEXT *z80 = init_test();

			z80ex_set_reg(z80, regAF, f);
			set(z80, 0x07, v);
			ram[0] = 0x3f;

			dump_state("before", z80, 0x0001, 0);

			run(z80, 0x0001);

			uninit_test(z80);
		}
	}
}

void emit_ld_ixy(uint8_t which)
{
	fprintf(stderr, "LD IX/Y\n");

	// mirror
	for(int instr=0x40; instr<0x60; instr++) {
		int t = instr & 7;
		if (t == 4 || t == 5 || t == 6)
			continue;

		int regfrom = t;
		int regto = (instr / 0x08) - 8;

		for(int v=0; v<256; v++) {
			Z80EX_CONTEXT *z80 = init_test();

			set(z80, regfrom, v);
			set(z80, regto, v ^ 0xff);

			ram[0] = which;
			ram[1] = instr;

			dump_state("before", z80, 0x0002, 0);

			run(z80, 0x0002);

			uninit_test(z80);
		}
	}

	// LD IXY[lh], r
	for(int instr=0x60; instr<0x70; instr++) {
		for(int v=0; v<256; v++) {
			Z80EX_CONTEXT *z80 = init_test();

			set(z80, instr & 7, v);
			ram[0] = which;
			ram[1] = instr;
			ram[2] = 1;
			ram[3] = 0x81;

			z80ex_set_reg(z80, which == 0xdd ? regIX : regIY, 0x1234);

			dump_state("before", z80, 0x0004, 0);

			run(z80, 0x0002);

			uninit_test(z80);
		}
	}

	// ld r,ixh	ld r,ixl	ld r,(ix+*)
	for(int instr=0x40; instr<0x80; instr++) {
		if ((instr & 0xf8) == 0x70)
			continue;
		int t = instr & 7;
		if (t != 4 && t != 5 && t != 6)
			continue;

		int reg = (instr / 0x08) - 8;

		for(int o=-128; o<128; o += quick ? 13 : 1) {
			for(int v=0; v<256; v += quick ? 13 : 1) {
				Z80EX_CONTEXT *z80 = init_test();

				set(z80, reg, v);
				ram[0] = which;
				ram[1] = instr;

				if (reg == 6) {
					ram[2] = o & 0xff;
					ram[0x2000 + o] = v;
					z80ex_set_reg(z80, which == 0xdd ? regIX : regIY, 0x2000);
				}
				else {
					z80ex_set_reg(z80, which == 0xdd ? regIX : regIY, (v ^ 0xff) | (v << 8));
				}

				dump_state("before", z80, reg == 6 ? 0x0003 : 0x0002, 0);

				run(z80, reg == 6 ? 0x0003 : 0x0002);

				uninit_test(z80);
			}
		}
	}

	// LD (IXY+*),r
	for(int instr=0x70; instr<0x78; instr++) {
		if (instr == 0x76)
			continue;

		for(int o=-128; o<128; o += quick ? 13 : 1) {
			for(int v=0; v<256; v += quick ? 13 : 1) {
				Z80EX_CONTEXT *z80 = init_test();

				set(z80, instr & 7, v);
				ram[0] = which;
				ram[1] = instr;
				ram[2] = o & 0xff;

				z80ex_set_reg(z80, which == 0xdd ? regIX : regIY, 0x2000);

				dump_state("before", z80, 0x0003, 0);

				run(z80, 0x0003);

				memcheck(0x2000 + o, v);

				uninit_test(z80);
			}
		}
	}
}

void emit_ld_ixy_misc(uint8_t which)
{
	fprintf(stderr, "LD IX/Y misc\n");

	// LD IX/Y,****
	{
		Z80EX_CONTEXT *z80 = init_test();

		ram[0] = which;
		ram[1] = 0x21;
		ram[2] = 1;
		ram[3] = 0x81;
		z80ex_set_reg(z80,  which == 0xdd ? regIX : regIY, 0x1234);

		dump_state("before", z80, 0x0004, 0);

		run(z80, 0x0004);

		uninit_test(z80);
	}
	 
	// ld (**),ix
	{
		Z80EX_CONTEXT *z80 = init_test();

		ram[0] = which;
		ram[1] = 0x22;
		ram[2] = 0x34;
		ram[3] = 0x12;
		z80ex_set_reg(z80,  which == 0xdd ? regIX : regIY, 0x2233);

		dump_state("before", z80, 0x0004, 0);

		run(z80, 0x0004);

		memcheck(0x1234, 0x33);
		memcheck(0x1235, 0x22);

		uninit_test(z80);
	}

	// ld ixh,*
	{
		Z80EX_CONTEXT *z80 = init_test();

		z80ex_set_reg(z80,  which == 0xdd ? regIX : regIY, 0xffee);

		ram[0] = which;
		ram[1] = 0x26;
		ram[2] = 0x04;

		dump_state("before", z80, 0x0003, 0);

		run(z80, 0x0003);

		uninit_test(z80);
	}

	// ld ixl,*
	{
		Z80EX_CONTEXT *z80 = init_test();

		z80ex_set_reg(z80,  which == 0xdd ? regIX : regIY, 0xeeff);

		ram[0] = which;
		ram[1] = 0x2e;
		ram[2] = 0x04;

		dump_state("before", z80, 0x0003, 0);

		run(z80, 0x0003);

		uninit_test(z80);
	}

	// ld ix,(**)
	{
		Z80EX_CONTEXT *z80 = init_test();

		ram[0] = which;
		ram[1] = 0x2a;
		ram[2] = 0x04;
		ram[3] = 0x00;
		ram[4] = 0x33;
		ram[5] = 0x22;

		dump_state("before", z80, 0x0006, 0);

		run(z80, 0x0004);

		uninit_test(z80);
	}

	// ld (ix+*),*
	for(int o=-128; o<128; o++) {
		Z80EX_CONTEXT *z80 = init_test();

		ram[0] = which;
		ram[1] = 0x36;
		ram[2] = o;
		ram[3] = 0x12;
		z80ex_set_reg(z80,  which == 0xdd ? regIX : regIY, 0x2233);

		dump_state("before", z80, 0x0006, 0);

		run(z80, 0x0004);

		memcheck(0x2233 + o, 0x12);

		uninit_test(z80);
	}

	// ld sp,ix
	{
		Z80EX_CONTEXT *z80 = init_test();

		ram[0] = which;
		ram[1] = 0xf9;
		z80ex_set_reg(z80,  which == 0xdd ? regIX : regIY, 0x1234);

		dump_state("before", z80, 0x0006, 0);

		run(z80, 0x0004);

		uninit_test(z80);
	}
}

void emit_aluop_a_nn()
{
	fprintf(stderr, "aluop a nn\n");

	for(int instr=0xc6; instr<0x106; instr += 0x08) {
		for(int f=0; f<256; f++) {
			for(int v1=0; v1<256; v1 += quick ? 13 : 1) {
				for(int v2=0; v2<256; v2 += quick ? 13 : 1) {
					Z80EX_CONTEXT *z80 = init_test();

					z80ex_set_reg(z80, regAF, f);
					set(z80, 0x07, v1);
					ram[0] = instr;
					ram[1] = v2;

					dump_state("before", z80, 0x0002, 0);

					run(z80, 0x0002);

					uninit_test(z80);
				}
			}
		}
	}
}

void emit_dec_inc()
{
	fprintf(stderr, "dec/inc\n");

	// DEC
	for(int instr=0x05; instr<0x40; instr += 8) {
		for(int f=0; f<256; f++) {
			for(int v=0; v<256; v += quick ? 13 : 1) {
				Z80EX_CONTEXT *z80 = init_test();

				z80ex_set_reg(z80, regHL, 0x0001);
				z80ex_set_reg(z80, regAF, f);
				set(z80, instr / 8, v);
				ram[0] = instr;
				ram[1] = v;

				dump_state("before", z80, 0x0002, 0);

				run(z80, 0x0001);

				if (instr / 8 == 6)
					memcheck(0x0001, (v - 1) & 0xff);

				uninit_test(z80);
			}
		}
	}

	// INC
	for(int instr=0x04; instr<0x40; instr += 8) {
		for(int f=0; f<256; f++) {
			for(int v=0; v<256; v += quick ? 13 : 1) {
				Z80EX_CONTEXT *z80 = init_test();

				z80ex_set_reg(z80, regHL, 0x0001);
				z80ex_set_reg(z80, regAF, f);
				set(z80, instr / 8, v);
				ram[0] = instr;
				ram[1] = v;

				dump_state("before", z80, 0x0002, 0);

				run(z80, 0x0001);

				if (instr / 8 == 6)
					memcheck(0x0001, (v + 1) & 0xff);

				uninit_test(z80);
			}
		}
	}
}

void emit_adc_pair()
{
	fprintf(stderr, "adc pair\n");

	for(int v1=0; v1<65536; v1 += quick ? 1313 : 1) {
		for(int v2=0; v2<65536; v2 += quick ? 1313 : 1) {
			for(int instr=0x4a; instr<0x80; instr += 16) {
				for(int f=0; f<256; f++) {
					Z80EX_CONTEXT *z80 = init_test();

					z80ex_set_reg(z80, regHL, v1);

					if (instr == 0x4a)
						z80ex_set_reg(z80, regBC, v2);
					else if (instr == 0x5a)
						z80ex_set_reg(z80, regDE, v2);
					else if (instr == 0x6a)
						z80ex_set_reg(z80, regHL, v2);
					else if (instr == 0x7a)
						z80ex_set_reg(z80, regSP, v2);
					else
						assert(false);

					ram[0] = 0xed;
					ram[1] = instr;

					dump_state("before", z80, 0x0002, 0);

					run(z80, 0x0002);

					uninit_test(z80);
				}
			}
		}
	}
}

void emit_sbc_pair()
{
	fprintf(stderr, "sbc pair\n");

	for(int v1=0; v1<65536; v1 += quick ? 1313 : 1) {
		for(int v2=0; v2<65536; v2 += quick ? 1313 : 1) {
			for(int instr=0x42; instr<0x80; instr += 16) {
				for(int f=0; f<256; f++) {
					Z80EX_CONTEXT *z80 = init_test();

					z80ex_set_reg(z80, regHL, v1);

					if (instr == 0x42)
						z80ex_set_reg(z80, regBC, v2);
					else if (instr == 0x52)
						z80ex_set_reg(z80, regDE, v2);
					else if (instr == 0x62)
						z80ex_set_reg(z80, regHL, v2);
					else if (instr == 0x72)
						z80ex_set_reg(z80, regSP, v2);
					else
						assert(false);

					ram[0] = 0xed;
					ram[1] = instr;

					dump_state("before", z80, 0x0002, 0);

					run(z80, 0x0002);

					uninit_test(z80);
				}
			}
		}
	}
}

void emit_hl_deref()
{
	fprintf(stderr, "hl deref\n");

	// DEC
	for(int instr=0x86; instr<0xc6; instr += 8) {
		for(int f=0; f<256; f++) {
			for(int v1=0; v1<256; v1 += quick ? 13 : 1) {
				for(int v2=0; v2<256; v2 += quick ? 13 : 1) {
					Z80EX_CONTEXT *z80 = init_test();

					z80ex_set_reg(z80, regHL, 0x0001);
					z80ex_set_reg(z80, regAF, f | (v1 << 8));
					ram[0] = instr;
					ram[1] = v2;

					dump_state("before", z80, 0x0002, 0);

					run(z80, 0x0001);

					uninit_test(z80);
				}
			}
		}
	}
}

void emit_ixy_misc_w_offset(uint8_t which)
{
	for(int instr=0x86; instr<=0xbe; instr += 8) {
		fprintf(stderr, "IX/Y misc %02x\n", instr);

		for(int v1=0; v1<256; v1 += quick ? 13 : 1) {
			for(int v2=0; v2<256; v2 += quick ? 13 : 1) {
				for(int o=-128; o<128; o++) {
					for(int f=0; f<256; f += quick ? 13 : 1) {
						Z80EX_CONTEXT *z80 = init_test();

						z80ex_set_reg(z80, regAF, f | (v1 << 8));
						z80ex_set_reg(z80, which == 0xdd ? regIX : regIY, 0x2233);

						ram[0] = which;
						ram[1] = instr;
						ram[2] = o;
						do_memset(0x2233 + o, v2);

						dump_state("before", z80, 0x0003, 0);

						run(z80, 0x0003);

						memcheck(0x2233 + o, v2);

						uninit_test(z80);
					}
				}
			}
		}
	}
}

void emit_jp_jr_call()
{
	fprintf(stderr, "jp x,**\n");
	for(int instr=0xc2; instr<=0xfa; instr += 8) {
		for(int f=0; f<256; f++) {
			Z80EX_CONTEXT *z80 = init_test();

			z80ex_set_reg(z80, regAF, f);
			ram[0] = instr;
			ram[1] = 0x33;
			ram[2] = 0x22;

			dump_state("before", z80, 0x0003, 0);

			run(z80, 0x0003);

			uninit_test(z80);
		}
	}

	fprintf(stderr, "jp **\n");
	{
		Z80EX_CONTEXT *z80 = init_test();

		ram[0] = 0xc3;
		ram[1] = 0x33;
		ram[2] = 0x22;

		dump_state("before", z80, 0x0003, 0);

		run(z80, 0x0003);

		uninit_test(z80);
	}

	fprintf(stderr, "jp (hl)\n");
	{
		Z80EX_CONTEXT *z80 = init_test();

		z80ex_set_reg(z80, regHL, 0x2233);
		ram[0] = 0xe9;

		dump_state("before", z80, 0x0001, 0);

		run(z80, 0x0001);

		uninit_test(z80);
	}

	fprintf(stderr, "jp (ix)\n");
	{
		Z80EX_CONTEXT *z80 = init_test();

		z80ex_set_reg(z80, regIX, 0x2233);
		ram[0] = 0xdd;
		ram[1] = 0xe9;

		dump_state("before", z80, 0x0002, 0);

		run(z80, 0x0002);

		uninit_test(z80);
	}

	fprintf(stderr, "jr x,**\n");
	for(int instr=0x10; instr<=0x38; instr += 8) {
		for(int f=0; f<256; f++) {
			for(int o=-128; o<128; o++) {
				Z80EX_CONTEXT *z80 = init_test();

				z80ex_set_reg(z80, regAF, f);
				ram[0] = instr;
				ram[1] = o & 0xff;

				dump_state("before", z80, 0x0002, 0);

				run(z80, 0x0000);

				uninit_test(z80);
			}
		}
	}

	fprintf(stderr, "call x,**\n");
	for(int instr=0xc4; instr<=0xfc; instr += 8) {
		for(int f=0; f<256; f++) {
			Z80EX_CONTEXT *z80 = init_test();

			z80ex_set_reg(z80, regAF, f);
			ram[0] = instr;
			ram[1] = 0x33;
			ram[2] = 0x22;

			dump_state("before", z80, 0x0003, 0);

			run(z80, 0x0003);

			uninit_test(z80);
		}
	}

	fprintf(stderr, "call **\n");
	{
		Z80EX_CONTEXT *z80 = init_test();

		ram[0] = 0xcd;
		ram[1] = 0x33;
		ram[2] = 0x22;

		dump_state("before", z80, 0x0003, 0);

		run(z80, 0x0003);

		uninit_test(z80);
	}
}

void emit_ret()
{
	fprintf(stderr, "ret x\n");
	for(int instr=0xc2; instr<=0xfa; instr += 8) {
		for(int f=0; f<256; f++) {
			Z80EX_CONTEXT *z80 = init_test();

			z80ex_set_reg(z80, regAF, f);
			ram[0] = 0x21; // LD HL, #3322
			ram[1] = 0x22;
			ram[2] = 0x33;
			ram[3] = 0xe5; // PUSH HL
			ram[4] = instr;

			dump_state("before", z80, 0x0005, 0);

			run(z80, 0x0005);

			uninit_test(z80);
		}
	}
}

void emit_ex()
{
	fprintf(stderr, "EX AF,AF'\n");
	{
		Z80EX_CONTEXT *z80 = init_test();

		z80ex_set_reg(z80, regAF, 0x1234);
		z80ex_set_reg(z80, regAF_, 0xee55);
		ram[0] = 0x08;

		dump_state("before", z80, 0x0001, 0);

		run(z80, 0x0001);

		uninit_test(z80);
	}

	fprintf(stderr, "EXX\n");
	{
		Z80EX_CONTEXT *z80 = init_test();

		z80ex_set_reg(z80, regBC, 0x1234);
		z80ex_set_reg(z80, regBC_, 0xee55);
		z80ex_set_reg(z80, regDE, 0x2233);
		z80ex_set_reg(z80, regDE_, 0x4455);
		z80ex_set_reg(z80, regHL, 0xbbaa);
		z80ex_set_reg(z80, regHL_, 0x9911);
		ram[0] = 0xd9;

		dump_state("before", z80, 0x0001, 0);

		run(z80, 0x0001);

		uninit_test(z80);
	}

	fprintf(stderr, "EX (SP),HL\n");
	{
		Z80EX_CONTEXT *z80 = init_test();

		ram[0] = 0x21; // LD HL, #3322
		ram[1] = 0x22;
		ram[2] = 0x33;
		ram[3] = 0xe5; // PUSH HL
		ram[4] = 0x21; // LD HL, #5544
		ram[5] = 0x44;
		ram[6] = 0x55;
		ram[7] = 0xe3;

		dump_state("before", z80, 0x0008, 0);

		run(z80, 0x0008);

		uninit_test(z80);
	}

	fprintf(stderr, "EX DE,HL\n");
	{
		Z80EX_CONTEXT *z80 = init_test();

		z80ex_set_reg(z80, regDE, 0x2233);
		z80ex_set_reg(z80, regHL, 0xbbaa);
		ram[0] = 0xeb;

		dump_state("before", z80, 0x0001, 0);

		run(z80, 0x0001);

		uninit_test(z80);
	}

	fprintf(stderr, "EX (SP),IX\n");
	{
		Z80EX_CONTEXT *z80 = init_test();

		ram[0] = 0x21; // LD HL, #3322
		ram[1] = 0x22;
		ram[2] = 0x33;
		ram[3] = 0xe5; // PUSH HL
		ram[4] = 0xdd; // LD IX, #5544
		ram[5] = 0x21;
		ram[6] = 0x44;
		ram[7] = 0x55;
		ram[8] = 0xdd;
		ram[9] = 0xe3;

		dump_state("before", z80, 0x000a, 0);

		run(z80, 0x000a);

		uninit_test(z80);
	}
}

void emit_djnz()
{
	fprintf(stderr, "djnz *\n");
	for(int b=0x00; b<=0xff; b++) {
		for(int o=-128; o<128; o++) {
			Z80EX_CONTEXT *z80 = init_test();

			z80ex_set_reg(z80, regBC, b << 8);
			ram[0] = 0x10;
			ram[1] = o;

			dump_state("before", z80, 0x0002, 0);

			run(z80, 0x0002);

			uninit_test(z80);
		}
	}
}

void emit_ld_id_r()
{
	// LDIR
	{
		Z80EX_CONTEXT *z80 = init_test();

		for(int i=0x2000; i<0x2100; i++)
			do_memset(i, i | 1);

		z80ex_set_reg(z80, regHL, 0x2000);
		z80ex_set_reg(z80, regDE, 0x3000);
		z80ex_set_reg(z80, regBC, 0x0100);
		ram[0] = 0xed;
		ram[1] = 0xb0;

		dump_state("before", z80, 0x0002, 0);

		run(z80, 0x0002);

		for(int i=0x2000; i<0x2100; i++)
			memcheck(i, i | 1);
		for(int i=0x2000; i<0x2100; i++)
			memcheck(i, i | 1);

		uninit_test(z80);
	}

	// LDI
	{
		Z80EX_CONTEXT *z80 = init_test();

		for(int i=0x2000; i<0x2100; i++)
			do_memset(i, i | 1);

		z80ex_set_reg(z80, regHL, 0x2000);
		z80ex_set_reg(z80, regDE, 0x3000);
		z80ex_set_reg(z80, regBC, 0x0100);
		ram[0] = 0xed;
		ram[1] = 0xa0;

		dump_state("before", z80, 0x0002, 0);

		run(z80, 0x0002);

		for(int i=0x2000; i<0x2100; i++)
			memcheck(i, i | 1);
		for(int i=0x2000; i<0x2100; i++)
			memcheck(i, i | 1);

		uninit_test(z80);
	}

	// LDDR
	{
		Z80EX_CONTEXT *z80 = init_test();

		for(int i=0x2000; i<0x2100; i++)
			do_memset(i, i | 1);

		z80ex_set_reg(z80, regHL, 0x2100);
		z80ex_set_reg(z80, regDE, 0x3100);
		z80ex_set_reg(z80, regBC, 0x0100);
		ram[0] = 0xed;
		ram[1] = 0xb8;

		dump_state("before", z80, 0x0002, 0);

		run(z80, 0x0002);

		for(int i=0x2000; i<0x2100; i++)
			memcheck(i, i | 1);
		for(int i=0x2000; i<0x2100; i++)
			memcheck(i, i | 1);

		uninit_test(z80);
	}

	// LDD
	{
		Z80EX_CONTEXT *z80 = init_test();

		for(int i=0x2000; i<0x2100; i++)
			do_memset(i, i | 1);

		z80ex_set_reg(z80, regHL, 0x2100);
		z80ex_set_reg(z80, regDE, 0x3100);
		z80ex_set_reg(z80, regBC, 0x0100);
		ram[0] = 0xed;
		ram[1] = 0xa8;

		dump_state("before", z80, 0x0002, 0);

		run(z80, 0x0002);

		for(int i=0x2000; i<0x2100; i++)
			memcheck(i, i | 1);
		for(int i=0x2000; i<0x2100; i++)
			memcheck(i, i | 1);

		uninit_test(z80);
	}
}

void emit_cpir()
{
	// CPIR
	for(int v=0; v<256; v++) {
		for(int f=0; f<256; f++) {
			for(int i : { 0x0100, 0x0333 }) {
				Z80EX_CONTEXT *z80 = init_test();

				for(int i=0x2000; i<0x2100; i++)
					do_memset(i, i + 1);

				z80ex_set_reg(z80, regAF, f | (v << 8));
				z80ex_set_reg(z80, regHL, 0x2000);
				z80ex_set_reg(z80, regBC, i);
				ram[0] = 0xed;
				ram[1] = 0xb1;

				dump_state("before", z80, 0x0002, 0);

				run(z80, 0x0002);

				uninit_test(z80);
			}
		}
	}
}

void emit_inc_dec_ix_l_h(int which)
{
	for(int instr : { 0x24, 0x25, 0x2c, 0x2d }) {
		for(int v=0; v<256; v++) {
			for(int f=0; f<256; f++) {
				Z80EX_CONTEXT *z80 = init_test();

				z80ex_set_reg(z80, regAF, f);
				z80ex_set_reg(z80, regIX, v | ((v ^ 255) << 8));
				z80ex_set_reg(z80, regIY, v | (((v ^ 255) << 8)) ^ 65535);
				ram[0] = which;
				ram[1] = instr;

				dump_state("before", z80, 0x0002, 0);

				run(z80, 0x0002);

				uninit_test(z80);
			}
		}
	}
}

void emit_rst()
{
	for(int instr=0xc7; instr<=0xff; instr += 8) {
		for(int pc=0; pc<0x10000; pc += 129) {
			Z80EX_CONTEXT *z80 = init_test();

			z80ex_set_reg(z80, regPC, pc);
			ram[pc] = instr;

			dump_state("before", z80, 1, 0);

			int which = (instr >> 4) - 0x0c;
			int end_pc = (instr & 8) ? 0x08 + (which << 4) : (which << 4);

			run(z80, end_pc);

			uninit_test(z80);
		}
	}
}

void emit_funnies()
{
#if 0
	fprintf(stderr, "SCF + CCF\n");

	for(int v=0; v<256; v++) {
		Z80EX_CONTEXT *z80 = init_test();

		set(z80, 0x07, v);
		ram[0] = 0x37;
		ram[1] = 0x3f;

		dump_state("before", z80, 0x0002, 0);

		run(z80, 0x0002);

		uninit_test(z80);
	}

	fprintf(stderr, "CCF + SCF\n");

	for(int v=0; v<256; v++) {
		Z80EX_CONTEXT *z80 = init_test();

		set(z80, 0x07, v);
		ram[0] = 0x3f;
		ram[1] = 0x37;

		dump_state("before", z80, 0x0002, 0);

		run(z80, 0x0002);

		uninit_test(z80);
	}

	fprintf(stderr, "DJNZ\n");

	{
		Z80EX_CONTEXT *z80 = init_test();

		ram[0] = 0x3e; // LD A,#AB
		ram[1] = 0xab;
		ram[2] = 0xc6; // ADD A,#55
		ram[3] = 0x55;
		ram[4] = 0x10; // DJNZ,0x000
		ram[5] = 252; // -4

		dump_state("before", z80, 0x0006, 0);

		run(z80, 0x0006);

		uninit_test(z80);
	}
#endif

	fprintf(stderr, "DJNZ 2\n");

	{
		Z80EX_CONTEXT *z80 = init_test();

		ram[0] = 0x3e; // LD A,#c0
		ram[1] = 0xc0;
		ram[2] = 0x07; // RLCA
		ram[3] = 0x07; // RLCA
		ram[4] = 0x07; // RLCA
		ram[5] = 0x07; // RLCA
		ram[6] = 0x2f; // CPL
		ram[7] = 0xe6; // AND #03
		ram[8] = 0x03;
		ram[9] = 0x47; // LD B,A
		ram[10] = 0x04; // INC B

		dump_state("before", z80, 11, 0);

		run(z80, 11);

		uninit_test(z80);
	}
}

int main(int argc, char *argv[])
{
	quick = argc == 2 && argv[1][0] == 'q';

	if (quick)
		fprintf(stderr, "Quick mode\n");

#if 0
	emit_rlc();
	emit_rrc();
	emit_rl();
	emit_rr();
	emit_sla();
	emit_sra();
	emit_sll();
	emit_srl();
	emit_daa();
	emit_cpl();
	emit_scf();
	emit_aluop_a_nn();
	emit_adc_pair();
	emit_sbc_pair();
	emit_dec_inc();
	emit_ccf();
	emit_res_set();
	emit_hl_deref();
	emit_ld_ixy(0xdd);
	emit_ld_ixy_misc(0xdd);
	emit_ld_ixy(0xfd);
	emit_ld_ixy_misc(0xfd);
	emit_ixy_misc_w_offset(0xdd);
	emit_ixy_misc_w_offset(0xfd);
	emit_bit();
	emit_ret();
	emit_jp_jr_call();
	emit_djnz();
	emit_ld_id_r();
	emit_cpir();
	emit_inc_dec_ix_l_h(0xdd);
	emit_inc_dec_ix_l_h(0xfd);
	emit_rst();
	emit_ex();
#endif
	emit_funnies();

	return 0;
}
