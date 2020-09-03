#! /usr/bin/python3

# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import sys
from inspect import getframeinfo, stack
from z80 import z80

io = [ 0 ] * 256

ram0 = [ 0 ] * 16384

slots = [ ] # slots
slots.append(( ram0, None, None, None ))
slots.append(( None, None, None, None ))
slots.append(( None, None, None, None ))
slots.append(( None, None, None, None ))

pages = [ 0, 0, 0, 0]

def reset_mem():
    global ram0
    ram0 = [ 0 ] * 16384

def read_mem(a):
    page = a >> 14

    if slots[page][pages[page]] == None:
        return 0xee

    return slots[page][pages[page]][a & 0x3fff]

def write_mem(a, v):
    global subpage

    my_assert(v >= 0 and v <= 255)

    page = a >> 14

    if slots[page][pages[page]] == None:
        my_assert(False)

    slots[page][pages[page]][a & 0x3fff] = v

def read_io(a):
    return io[a]
 
def write_io(a, v):
    io[a] = v

def debug(x):
#    print('%s <%02x/%02x>' % (x, io[0xa8], 0), file=sys.stderr)
    pass

def flag_str(f):
    flags = ''

    flags += 's1 ' if f & 128 else 's0 '
    flags += 'z1 ' if f & 64 else 'z0 '
    flags += '51 ' if f & 32 else '50 '
    flags += 'h1 ' if f & 16 else 'h0 '
    flags += '31 ' if f & 8 else '30 '
    flags += 'P1 ' if f & 4 else 'P0 '
    flags += 'n1 ' if f & 2 else 'n0 '
    flags += 'c1 ' if f & 1 else 'c0 '

    return flags

def my_assert(r):
    if not r:
        print(cpu.reg_str())
        caller = getframeinfo(stack()[1][0])
        print(flag_str(cpu.f))
        print('%s:%d' % (caller.filename, caller.lineno))
        sys.exit(1)

def test_ld():
    # LD C,L
    reset_mem()
    cpu.reset()
    cpu.c = 123
    cpu.l = 4
    cpu.a = 0
    cpu.f = 0
    ram0[0] = 0x4d
    cpu.step()
    my_assert(cpu.c == 4)
    my_assert(cpu.l == 4)
    my_assert(cpu.a == 0)
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 1)

    # LD A,*
    reset_mem()
    cpu.reset()
    cpu.a = 123
    cpu.f = 0
    ram0[0] = 0x3e
    ram0[1] = 0xff
    cpu.step()
    my_assert(cpu.a == 0xff)
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 2)

    # LD (HL),*
    reset_mem()
    cpu.reset()
    cpu.f = 0
    ram0[0] = 0x21 # LD HL,0101
    ram0[1] = 0x01
    ram0[2] = 0x01
    ram0[3] = 0x36 # LD (HL),*
    ram0[4] = 0xff
    cpu.step()
    cpu.step()
    my_assert(cpu.a == 0xff)
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 5)
    my_assert(cpu.read_mem(0x0101) == 0xff)

    # LD HL,**
    reset_mem()
    cpu.reset()
    cpu.f = 0
    ram0[0] = 0x21
    ram0[1] = 0xff
    ram0[2] = 0x12
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.h == 0x12)
    my_assert(cpu.l == 0xff)
    my_assert(cpu.pc == 3)

    # LD A,(BC)
    reset_mem()
    cpu.reset()
    cpu.a = 123
    cpu.b = 0x10
    cpu.c = 0x00
    cpu.write_mem(0x1000, 0x99)
    cpu.f = 0
    ram0[0] = 0x0a
    cpu.step()
    my_assert(cpu.a == 0x99)
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 1)

    # LD HL,(**)
    reset_mem()
    cpu.reset()
    cpu.h = 0x77
    cpu.l = 0x77
    cpu.write_mem_16(0x1000, 0x9988)
    cpu.f = 0
    ram0[0] = 0x2a
    ram0[1] = 0x00
    ram0[2] = 0x10
    cpu.step()
    my_assert(cpu.h == 0x99)
    my_assert(cpu.l == 0x88)
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 3)

    # LD SP,HL
    reset_mem()
    cpu.reset()
    cpu.h = 0x10
    cpu.l = 0x21
    cpu.sp = 0x1234
    cpu.f = 0
    ram0[0] = 0xf9
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.sp == 0x1021)

    # LD (BC),A
    reset_mem()
    cpu.reset()
    cpu.b = 0x10
    cpu.c = 0x21
    cpu.a = 0x34
    cpu.f = 0
    ram0[0] = 0x02
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.read_mem(0x1021) == 0x34)

    # LD (**),HL
    reset_mem()
    cpu.reset()
    cpu.h = 0x77
    cpu.l = 0x22
    cpu.write_mem_16(0x1000, 0x9988)
    cpu.f = 0
    ram0[0] = 0x22
    ram0[1] = 0x00
    ram0[2] = 0x10
    cpu.step()
    my_assert(cpu.h == 0x77)
    my_assert(cpu.l == 0x22)
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 3)
    my_assert(cpu.read_mem_16(0x1000) == 0x7722)

    # LD (**),SP
    reset_mem()
    cpu.reset()
    cpu.sp = 0x1234
    cpu.write_mem_16(0x1000, 0x9988)
    cpu.f = 0
    ram0[0] = 0xed
    ram0[1] = 0x73
    ram0[2] = 0x00
    ram0[3] = 0x10
    cpu.step()
    my_assert(cpu.sp == 0x1234)
    my_assert(cpu.pc == 4)
    my_assert(cpu.read_mem_16(0x1000) == 0x1234)

    # LD (**),A
    reset_mem()
    cpu.reset()
    cpu.h = 0x77
    cpu.l = 0x22
    cpu.a = 213
    cpu.write_mem_16(0x1000, 0x9988)
    cpu.f = 0
    ram0[0] = 0x32
    ram0[1] = 0x00
    ram0[2] = 0x10
    cpu.step()
    my_assert(cpu.h == 0x77)
    my_assert(cpu.l == 0x22)
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 3)
    my_assert(cpu.read_mem(0x1000) == 213)

    # LD DE,(**)
    reset_mem()
    cpu.reset()
    cpu.d = 0x77
    cpu.e = 0x22
    cpu.write_mem_16(0x1000, 0x9988)
    cpu.f = 0
    ram0[0] = 0xed
    ram0[1] = 0x5b
    ram0[2] = 0x00
    ram0[3] = 0x10
    cpu.step()
    my_assert(cpu.pc == 4)
    my_assert(cpu.f == 0)
    my_assert(cpu.d == 0x99)
    my_assert(cpu.e == 0x88)

    # LD H,(IX+*)
    reset_mem()
    cpu.reset()
    cpu.d = 0x77
    cpu.e = 0x22
    cpu.ix = 0x1000
    cpu.write_mem_16(0x1003, 0x9988)
    cpu.f = 0
    ram0[0] = 0xdd
    ram0[1] = 0x66
    ram0[2] = 3
    cpu.step()
    my_assert(cpu.pc == 3)
    my_assert(cpu.f == 0)
    my_assert(cpu.h == 0x88)

    # LD H,(IY+*)
    reset_mem()
    cpu.reset()
    cpu.d = 0x77
    cpu.e = 0x22
    cpu.iy = 0x1000
    cpu.write_mem_16(0x1003, 0x9988)
    cpu.f = 0
    ram0[0] = 0xfd
    ram0[1] = 0x66
    ram0[2] = 3
    cpu.step()
    my_assert(cpu.pc == 3)
    my_assert(cpu.f == 0)
    my_assert(cpu.h == 0x88)

    # LD IX,**
    reset_mem()
    cpu.reset()
    cpu.f = 0
    ram0[0] = 0xdd
    ram0[1] = 0x21
    ram0[2] = 0x21
    ram0[3] = 0x23
    cpu.step()
    my_assert(cpu.ix == 0x2321)
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 4)

    # LD IY,(**)
    reset_mem()
    cpu.reset()
    cpu.f = 0
    ram0[0] = 0xfd
    ram0[1] = 0x2a
    ram0[2] = 0x21
    ram0[3] = 0x23
    cpu.write_mem_16(0x2321, 0x1234)
    cpu.step()
    my_assert(cpu.iy == 0x1234)
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 4)

    # LD (IY + *), E
    reset_mem()
    cpu.reset()
    cpu.f = 0
    cpu.e = 0x79
    cpu.iy = 0x1000
    ram0[0] = 0xfd
    ram0[1] = 0x73
    ram0[2] = 0x21
    cpu.write_mem_16(0x1021, 0x12)
    cpu.step()
    my_assert(cpu.iy == 0x1000)
    my_assert(cpu.e == 0x79)
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 3)
    my_assert(cpu.read_mem(0x1021) == 0x79)

def test_jp():
    # JP **
    reset_mem()
    cpu.reset()
    cpu.f = 0
    ram0[0] = 0xc3
    ram0[1] = 0x10
    ram0[2] = 0x22
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 0x2210)
    my_assert(cpu.sp == 0xffff)

    # JP Z,** taken
    reset_mem()
    cpu.reset()
    cpu.f = 64
    ram0[0] = 0xca
    ram0[1] = 0x10
    ram0[2] = 0x22
    cpu.step()
    my_assert(cpu.f == 64)
    my_assert(cpu.pc == 0x2210)
    my_assert(cpu.sp == 0xffff)

    # JP Z,** not taken
    reset_mem()
    cpu.reset()
    cpu.f = 0
    ram0[0] = 0xca
    ram0[1] = 0x10
    ram0[2] = 0x22
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 3)
    my_assert(cpu.sp == 0xffff)

    # JP M,** taken
    reset_mem()
    cpu.reset()
    cpu.f = 128
    ram0[0] = 0xfa
    ram0[1] = 0x10
    ram0[2] = 0x22
    cpu.step()
    my_assert(cpu.f == 128)
    my_assert(cpu.pc == 0x2210)
    my_assert(cpu.sp == 0xffff)

    # JP (IX)
    reset_mem()
    cpu.reset()
    cpu.f = 0
    cpu.ix = 0x1000
    ram0[0] = 0xdd
    ram0[1] = 0xe9
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 0x1000)
    my_assert(cpu.sp == 0xffff)

    # JP (IY)
    reset_mem()
    cpu.reset()
    cpu.f = 0
    cpu.iy = 0x2000
    ram0[0] = 0xfd
    ram0[1] = 0xe9
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 0x2000)
    my_assert(cpu.sp == 0xffff)

def test_call_ret():
    # CALL **
    reset_mem()
    cpu.reset()
    cpu.f = 0
    cpu.sp = 0x3fff
    ram0[0] = 0xcd
    ram0[1] = 0x10
    ram0[2] = 0x22
    ram0[0x2210] = 0xc9
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 0x2210)
    my_assert(cpu.sp == 0x3ffd)
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 3)
    my_assert(cpu.sp == 0x3fff)

    # CALL Z,** taken
    reset_mem()
    cpu.reset()
    cpu.f = 64
    cpu.sp = 0x3fff
    ram0[0] = 0xcc
    ram0[1] = 0x10
    ram0[2] = 0x22
    ram0[0x2210] = 0xc9
    cpu.step()
    my_assert(cpu.f == 64)
    my_assert(cpu.pc == 0x2210)
    my_assert(cpu.sp == 0x3ffd)
    cpu.step()
    my_assert(cpu.f == 64)
    my_assert(cpu.pc == 3)
    my_assert(cpu.sp == 0x3fff)

    # CALL Z,** not taken
    reset_mem()
    cpu.reset()
    cpu.f = 0
    cpu.sp = 0x3fff
    ram0[0] = 0xcc
    ram0[1] = 0x10
    ram0[2] = 0x22
    ram0[0x2210] = 0xc9
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 3)
    my_assert(cpu.sp == 0x3fff)

    # CALL NC,** taken
    reset_mem()
    cpu.reset()
    cpu.f = 0
    cpu.sp = 0x3fff
    ram0[0] = 0xd4
    ram0[1] = 0x10
    ram0[2] = 0x22
    ram0[0x2210] = 0xc9
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 0x2210)
    my_assert(cpu.sp == 0x3ffd)
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 3)
    my_assert(cpu.sp == 0x3fff)

    # CALL NC,** not taken
    reset_mem()
    cpu.reset()
    cpu.f = 1
    cpu.sp = 0x3fff
    ram0[0] = 0xd4
    ram0[1] = 0x10
    ram0[2] = 0x22
    ram0[0x2210] = 0xc9
    cpu.step()
    my_assert(cpu.f == 1)
    my_assert(cpu.pc == 3)
    my_assert(cpu.sp == 0x3fff)
    
    # RET C taken
    reset_mem()
    cpu.reset()
    cpu.f = 1
    cpu.sp = 0x3fff
    ram0[0] = 0xcd
    ram0[1] = 0x10
    ram0[2] = 0x22
    ram0[0x2210] = 0xd8
    cpu.step()
    my_assert(cpu.f == 1)
    my_assert(cpu.pc == 0x2210)
    my_assert(cpu.sp == 0x3ffd)
    cpu.step()
    my_assert(cpu.f == 1)
    my_assert(cpu.pc == 3)
    my_assert(cpu.sp == 0x3fff)
    
    # RET P taken
    reset_mem()
    cpu.reset()
    cpu.f = 4
    cpu.sp = 0x3fff
    ram0[0] = 0xcd
    ram0[1] = 0x10
    ram0[2] = 0x22
    ram0[0x2210] = 0xf0
    cpu.step()
    my_assert(cpu.f == 4)
    my_assert(cpu.pc == 0x2210)
    my_assert(cpu.sp == 0x3ffd)
    cpu.step()
    my_assert(cpu.f == 4)
    my_assert(cpu.pc == 3)
    my_assert(cpu.sp == 0x3fff)
    
    # RET C not taken
    reset_mem()
    cpu.reset()
    cpu.f = 0
    cpu.sp = 0x3fff
    ram0[0] = 0xcd
    ram0[1] = 0x10
    ram0[2] = 0x22
    ram0[0x2210] = 0xd8
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 0x2210)
    my_assert(cpu.sp == 0x3ffd)
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 0x2211)
    my_assert(cpu.sp == 0x3ffd)

def test_cpl():
    # CPL
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.f = 0
    ram0[0] = 0x2f
    cpu.step()
    my_assert(cpu.a == 0x0f)
    my_assert(cpu.f == 0x12)
    my_assert(cpu.pc == 1)

    # CPL
    reset_mem()
    cpu.reset()
    cpu.a = 0x00
    cpu.f = 0
    ram0[0] = 0x2f
    cpu.step()
    my_assert(cpu.a == 0xff)
    my_assert(cpu.f == 0x12)
    my_assert(cpu.pc == 1)

def test__flags():
    # test flags
    reset_mem()
    cpu.reset()

    cpu.f = 0xff
    my_assert(cpu.get_flag_c())
    my_assert(cpu.get_flag_n())
    my_assert(cpu.get_flag_pv())
    my_assert(cpu.get_flag_h())
    my_assert(cpu.get_flag_z())
    my_assert(cpu.get_flag_s())

    cpu.f = 0
    cpu.a = 12
    cpu.set_flag_parity()
    my_assert(cpu.f == 4)
    cpu.a = 13
    cpu.set_flag_parity()
    my_assert(cpu.f == 0)

    cpu.f = 0x00
    my_assert(not cpu.get_flag_c())
    my_assert(not cpu.get_flag_n())
    my_assert(not cpu.get_flag_pv())
    my_assert(not cpu.get_flag_h())
    my_assert(not cpu.get_flag_z())
    my_assert(not cpu.get_flag_s())

    cpu.set_flag_c(True)
    my_assert(cpu.f == 1)
    my_assert(cpu.get_flag_c())
    cpu.set_flag_n(True)
    my_assert(cpu.f == 3)
    my_assert(cpu.get_flag_n())
    cpu.set_flag_pv(True)
    my_assert(cpu.f == 7)
    my_assert(cpu.get_flag_pv())
    cpu.set_flag_h(True)
    my_assert(cpu.f == 23)
    my_assert(cpu.get_flag_h())
    cpu.set_flag_z(True)
    my_assert(cpu.f == 87)
    my_assert(cpu.get_flag_z())
    cpu.set_flag_s(True)
    my_assert(cpu.f == 215)
    my_assert(cpu.get_flag_s())
    cpu.set_flag_s(True)

def _test_registers_initial(incl_pc):
    my_assert(cpu.a == 0xff)
    my_assert(cpu.b == 0xff)
    my_assert(cpu.c == 0xff)
    my_assert(cpu.d == 0xff)
    my_assert(cpu.e == 0xff)
    my_assert(cpu.f == 0xff)
    my_assert(cpu.h == 0xff)
    my_assert(cpu.l == 0xff)
    my_assert(cpu.a_ == 0xff)
    my_assert(cpu.b_ == 0xff)
    my_assert(cpu.c_ == 0xff)
    my_assert(cpu.d_ == 0xff)
    my_assert(cpu.e_ == 0xff)
    my_assert(cpu.f_ == 0xff)
    my_assert(cpu.h_ == 0xff)
    my_assert(cpu.l_ == 0xff)
    my_assert(cpu.ix == 0xffff)
    my_assert(cpu.iy == 0xffff)
    my_assert(cpu.interrupts)
    my_assert(cpu.pc == 0x0000 or not incl_pc)
    my_assert(cpu.sp == 0xffff)
    my_assert(cpu.im == 0)

def test__support():
    my_assert(cpu.parity(0) == True)
    my_assert(cpu.parity(127) == False)
    my_assert(cpu.parity(128) == False)
    my_assert(cpu.parity(129) == True)
    my_assert(cpu.parity(255) == True)

    cpu.a = cpu.b = cpu.c = cpu.d = cpu.e = cpu.f = cpu.h = cpu.l = 0x12
    cpu.a_ = cpu.b_ = cpu.c_ = cpu.d_ = cpu.e_ = cpu.f_ = cpu.h_ = cpu.l_ = 0x34
    cpu.ix = cpu.iy = 0x1234
    cpu.interrupts = False
    cpu.pc = 0x4321
    cpu.sp = 0xee55
    cpu.im = 2
    cpu.reset()
    _test_registers_initial(True)

    cpu.out(0xa8, 123)
    my_assert(io[0xa8] == 123)
    my_assert(cpu.in_(0xa8) == 123)
    my_assert(cpu.in_(0xa7) == 0x00)

    cpu.reset()
    ram0[0x0000] = 0x56
    my_assert(cpu.read_pc_inc() == 0x56)
    my_assert(cpu.pc == 0x0001)
    ram0[0x0001] = 0x12
    ram0[0x0002] = 0x34
    my_assert(cpu.read_pc_inc_16() == 0x3412)
    my_assert(cpu.pc == 0x0003)

    my_assert(cpu.m16(0x34, 0x12) == 0x3412)

    cpu.set_dst(0, 0x10)
    my_assert(cpu.b == 0x10)
    my_assert(cpu.get_src(0) == (0x10, 'B'))
    cpu.set_dst(1, 0x19)
    my_assert(cpu.c == 0x19)
    my_assert(cpu.get_src(1) == (0x19, 'C'))
    cpu.set_dst(2, 0x39)
    my_assert(cpu.d == 0x39)
    my_assert(cpu.get_src(2) == (0x39, 'D'))
    cpu.set_dst(3, 0x49)
    my_assert(cpu.e == 0x49)
    my_assert(cpu.get_src(3) == (0x49, 'E'))
    cpu.set_dst(4, 0x12)
    my_assert(cpu.h == 0x12)
    my_assert(cpu.get_src(4) == (0x12, 'H'))
    cpu.set_dst(5, 0x13)
    my_assert(cpu.l == 0x13)
    my_assert(cpu.get_src(5) == (0x13, 'L'))
    ram0[0x1213] = 0x34
    my_assert(cpu.get_src(6) == (0x34, '(HL)'))
    cpu.set_dst(7, 0x99)
    my_assert(cpu.a == 0x99)
    my_assert(cpu.get_src(7) == (0x99, 'A'))

    my_assert(cpu.get_pair(0) == (0x1019, 'BC'))
    my_assert(cpu.get_pair(1) == (0x3949, 'DE'))
    my_assert(cpu.get_pair(2) == (0x1213, 'HL'))
    my_assert(cpu.get_pair(3) == (0xffff, 'SP'))

    my_assert(cpu.set_pair(0, 0x7723) == 'BC')
    my_assert(cpu.b == 0x77)
    my_assert(cpu.c == 0x23)
    my_assert(cpu.set_pair(1, 0x4422) == 'DE')
    my_assert(cpu.d == 0x44)
    my_assert(cpu.e == 0x22)
    my_assert(cpu.set_pair(2, 0xBCDE) == 'HL')
    my_assert(cpu.h == 0xBC)
    my_assert(cpu.l == 0xDE)
    my_assert(cpu.set_pair(3, 0x1133) == 'SP')
    my_assert(cpu.sp == 0x1133)

    reset_mem()
    cpu.write_mem_16(0x0103, 0x1934)
    my_assert(ram0[0x0103] == 0x34)
    my_assert(ram0[0x0104] == 0x19)
    my_assert(cpu.read_mem_16(0x0103) == 0x1934)

    reset_mem()
    cpu.reset()
    cpu.f = 0x00
    cpu.set_dst(5, 0x12)
    my_assert(cpu.l == 0x12)
    my_assert(cpu.get_src(5) == (0x12, 'L'))
    cpu.set_dst(4, 0x34)
    my_assert(cpu.h == 0x34)
    my_assert(cpu.get_src(4) == (0x34, 'H'))
    cpu.set_dst(7, 0x55)
    my_assert(cpu.a == 0x55)
    my_assert(cpu.get_src(7) == (0x55, 'A'))
    my_assert(cpu.f == 0x00)
    cpu.set_dst(6, 0xa9)
    my_assert(ram0[0x3412] == 0xa9)
    my_assert(cpu.get_src(6) == (0xa9, '(HL)'))

    reset_mem()
    cpu.reset()
    cpu.sp = 0x3fff
    cpu.push(0x1020)
    cpu.ret_flag(False)
    my_assert(cpu.pc == 0x0000)

    cpu.reset()
    cpu.sp = 0x3fff
    cpu.push(0x1122)
    cpu.ret_flag(True)
    my_assert(cpu.pc == 0x1122)

    # SUB flags
    cpu.reset()
    cpu.f = 0
    cpu.a = 0xf0
    print(cpu.flags_add_sub_cp(True, False, 0x21))
    my_assert(cpu.flags_add_sub_cp(True, False, 0x21) == 0xf0 - 0x21)
    my_assert(cpu.f == 0xb2)

    cpu.f = 0
    cpu.a = 0xf0
    my_assert(cpu.flags_add_sub_cp(True, False, 0xf0) == 0xf0 - 0xf0)
    my_assert(cpu.f == 0x62)

    cpu.f = 0
    cpu.a = 0x01
    my_assert(cpu.flags_add_sub_cp(True, False, 0xa0) == (0x01 - 0xa0) & 0xff)
    my_assert(cpu.f == 0x23)

    # ADD flags
    cpu.reset()
    cpu.f = 0
    cpu.set_add_flags(0xf0, 0x21, 0xf0 + 0x21)
    my_assert(cpu.f == 0x01)

    cpu.f = 0
    cpu.set_add_flags(0xf0, 0xf0, 0xf0 + 0xf0)
    my_assert(cpu.f == 0x81)

    cpu.f = 0
    cpu.set_add_flags(0x01, 0xa0, 0x01 + 0xa0)
    my_assert(cpu.f == 0x80)

    cpu.f = 0
    cpu.set_add_flags(0xa0, 0xa0, 0xa0 + 0xa0)
    my_assert(cpu.f == 0x05)

def test_nop():
    cpu.reset()
    ram0[0] = 0x00
    cpu.step()
    _test_registers_initial(False)

def test_cp_cpir():
    # CP B
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.b = 0x21 # 
    cpu.f = 0
    ram0[0] = 0xb8
    cpu.step()
    my_assert(cpu.a == 0xf0)
    # 04
    my_assert(cpu.f == 0xb2)
    my_assert(cpu.pc == 1)

    cpu.reset()
    cpu.a = 0xf0
    cpu.b = 0xf0 # zero flag
    cpu.f = 0
    cpu.step()
    my_assert(cpu.a == 0xf0)
    my_assert(cpu.f == 0x62)

    cpu.reset()
    cpu.a = 0x01
    cpu.b = 0xa0 # overflow flag
    cpu.f = 0
    cpu.step()
    my_assert(cpu.a == 0x01)
    my_assert(cpu.f == 0x23)

    # CP *
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.f = 0
    ram0[0] = 0xfe
    ram0[1] = 0x21 # 
    cpu.step()
    my_assert(cpu.a == 0xf0)
    my_assert(cpu.f == 0xb2)
    my_assert(cpu.pc == 2)

    # CP (IX+*)
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.f = 0
    cpu.ix = 0x1000
    cpu.write_mem(0x1003, 0x21)
    ram0[0] = 0xdd
    ram0[1] = 0xbe
    ram0[2] = 0x03
    cpu.step()
    my_assert(cpu.a == 0xf0)
    my_assert(cpu.f == 0xb2)
    my_assert(cpu.pc == 3)

    # CPIR
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.f = 0
    cpu.h = 0x10
    cpu.l = 0x00
    cpu.b = 0x20
    cpu.c = 0x19
    ram0[0x1010] = 0xf0
    ram0[0] = 0xed
    ram0[1] = 0xb1
    cpu.step()
    my_assert(cpu.a == 0xf0)
    my_assert(cpu.h == 0x10)
    my_assert(cpu.l == 0x11)
    my_assert(cpu.b == 0x20)
    my_assert(cpu.c == 0x08)
    my_assert(cpu.f == 0x42)
    my_assert(cpu.pc == 2)

def test_add():
    # ADD B
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.b = 0x21 # 
    cpu.f = 0
    ram0[0] = 0x80
    cpu.step()
    my_assert(cpu.a == 0x11)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 1)

    # ADD B
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.c = 0x21 # 
    cpu.f = 0
    ram0[0] = 0x81
    cpu.step()
    my_assert(cpu.a == 0x11)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 1)

    # ADD L
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.l = 0x21 
    cpu.f = 0
    ram0[0] = 0x85
    cpu.step()
    my_assert(cpu.a == 0x11)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 1)

    # ADD *
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.f = 0
    ram0[0] = 0xc6
    ram0[1] = 0x21
    cpu.step()
    my_assert(cpu.a == 0x11)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 2)

    # ADC B
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.b = 0x21 # 
    cpu.f = 0
    ram0[0] = 0x37
    cpu.step()
    my_assert(cpu.get_flag_c())
    ram0[1] = 0x88
    cpu.step()
    my_assert(cpu.a == 0x12)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 2)

    # ADD HL,BC [1]
    reset_mem()
    cpu.reset()
    cpu.h = 0x21
    cpu.l = 0xf0
    cpu.b = 0x57
    cpu.c = 0x03
    cpu.f = 0
    ram0[0] = 0x09
    cpu.step()
    my_assert(cpu.h == 0x78)
    my_assert(cpu.l == 0xf3)
    my_assert(cpu.f == 0x00)
    my_assert(cpu.pc == 1)

    # ADC HL,BC [2]
    reset_mem()
    cpu.reset()
    cpu.h = 0x0f
    cpu.l = 0x0f
    cpu.b = 0x7f
    cpu.c = 0x7f
    cpu.f = 1
    ram0[0] = 0xed
    ram0[1] = 0x4a
    cpu.step()
    my_assert(cpu.h == 0x8e)
    my_assert(cpu.l == 0x8f)
    my_assert(cpu.f == 0x94)
    my_assert(cpu.pc == 2)

    # ADC HL,BC [3]
    reset_mem()
    cpu.reset()
    cpu.h = 0x0f
    cpu.l = 0x0f
    cpu.b = 0x7f
    cpu.c = 0x7f
    cpu.f = 0
    ram0[0] = 0xed
    ram0[1] = 0x4a
    cpu.step()
    my_assert(cpu.h == 0x8e)
    my_assert(cpu.l == 0x8e)
    my_assert(cpu.f == 0x94)
    my_assert(cpu.pc == 2)

    # ADD A,(IX+*)
    reset_mem()
    cpu.reset()
    cpu.a = 0x01
    cpu.ix = 0x1000
    cpu.write_mem_16(0x1003, 0x9988)
    cpu.f = 0
    ram0[0] = 0xdd
    ram0[1] = 0x86
    ram0[2] = 3
    cpu.step()
    my_assert(cpu.pc == 3)
    my_assert(cpu.f == 0x80)
    my_assert(cpu.a == 0x89)

    # ADD IX,BC [1]
    reset_mem()
    cpu.reset()
    cpu.ix = 0x0f0f
    cpu.b = 0x7f
    cpu.c = 0x7f
    cpu.f = 1
    ram0[0] = 0xdd
    ram0[1] = 0x09
    cpu.step()
    my_assert(cpu.ix == 0x8e8e)
    my_assert(cpu.f == 0x94)
    my_assert(cpu.pc == 2)

    # ADD IX,BC [2]
    reset_mem()
    cpu.reset()
    cpu.ix = 0x0f0f
    cpu.b = 0x7f
    cpu.c = 0x7f
    cpu.f = 0
    ram0[0] = 0xdd
    ram0[1] = 0x09
    cpu.step()
    my_assert(cpu.ix == 0x8e8e)
    my_assert(cpu.f == 0x94)
    my_assert(cpu.pc == 2)

def test_or():
    # OR B
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.b = 0x21 # 
    cpu.f = 0
    ram0[0] = 0xb0
    cpu.step()
    my_assert(cpu.a == 0xf1)
    my_assert(cpu.f == 0x80)
    my_assert(cpu.pc == 1)

    # OR *
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.f = 0
    ram0[0] = 0xf6
    ram0[1] = 0x21
    cpu.step()
    my_assert(cpu.a == 0xf1)
    my_assert(cpu.f == 0x80)
    my_assert(cpu.pc == 2)

    # OR *
    reset_mem()
    cpu.reset()
    cpu.a = 0x7f
    cpu.f = 0
    ram0[0] = 0xf6
    ram0[1] = 0xf1
    cpu.step()
    my_assert(cpu.a == 0xff)
    my_assert(cpu.f == 0x84)
    my_assert(cpu.pc == 2)

def test_and():
    # AND B
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.b = 0x21 # 
    cpu.f = 0
    ram0[0] = 0xa0
    cpu.step()
    my_assert(cpu.a == 0x20)
    my_assert(cpu.f == 0x10)
    my_assert(cpu.pc == 1)

    # AND *
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.f = 0
    ram0[0] = 0xe6
    ram0[1] = 0x21
    cpu.step()
    my_assert(cpu.a == 0x20)
    my_assert(cpu.f == 0x10)
    my_assert(cpu.pc == 2)

    # AND *
    reset_mem()
    cpu.reset()
    cpu.a = 0x7f
    cpu.f = 0
    ram0[0] = 0xe6
    ram0[1] = 0xf1
    cpu.step()
    my_assert(cpu.a == 0x71)
    my_assert(cpu.f == 0x14)
    my_assert(cpu.pc == 2)

    # AND A,(IX+*)
    reset_mem()
    cpu.reset()
    cpu.a = 0x01
    cpu.ix = 0x1000
    cpu.write_mem_16(0x1003, 0x9988)
    cpu.f = 0
    ram0[0] = 0xdd
    ram0[1] = 0xa6
    ram0[2] = 3
    cpu.step()
    my_assert(cpu.pc == 3)
    my_assert(cpu.f == 0x54)
    my_assert(cpu.a == 0x00)

def test_xor():
    # XOR B
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.b = 0x21
    cpu.f = 0
    ram0[0] = 0xa8
    cpu.step()
    my_assert(cpu.a == 0xd1)
    my_assert(cpu.f == 0x84)
    my_assert(cpu.pc == 1)

    # XOR *
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.b = 0x00
    cpu.f = 0
    ram0[0] = 0xee
    ram0[1] = 0x21
    cpu.step()
    my_assert(cpu.a == 0xd1)
    my_assert(cpu.f == 0x84)
    my_assert(cpu.pc == 2)

    # XOR *
    reset_mem()
    cpu.reset()
    cpu.a = 0x7f
    cpu.f = 0
    ram0[0] = 0xee
    ram0[1] = 0xf1
    cpu.step()
    my_assert(cpu.a == 0x8e)
    my_assert(cpu.f == 0x84)
    my_assert(cpu.pc == 2)

def test_out_in():
    # OUT (*),A
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.f = 0
    ram0[0] = 0xd3
    ram0[1] = 0x00
    cpu.step()
    my_assert(cpu.a == 0xf0)
    my_assert(cpu.f == 0x00)
    my_assert(cpu.pc == 2)
    my_assert(io[0x00] == 0xf0)

    # IN A,(*)
    cpu.pc = 0x0000
    cpu.a = 123
    ram0[0] = 0xdb
    ram0[1] = 0x00
    cpu.step()
    my_assert(cpu.a == 0xf0)
    my_assert(cpu.f == 0x00)
    my_assert(cpu.pc == 2)
    my_assert(io[0x00] == 0xf0)

#    # IN B,(C)
#    reset_mem()
#    cpu.reset()
#    cpu.c = 0x23
#    cpu.f = 0xff
#    io[0x23] = 0x45
#    ram0[0] = 0xed
#    ram0[1] = 0x40
#    cpu.step()
#    my_assert(cpu.b == 0x45)
#    my_assert(cpu.get_flag_c() == True)
#    my_assert(cpu.get_flag_n() == False)
#    my_assert(cpu.get_flag_pv() == False)
#    my_assert(cpu.get_flag_z() == False)
#    my_assert(cpu.get_flag_s() == False)
#    my_assert(cpu.pc == 2)

def test_sla():
    # SLA B
    reset_mem()
    cpu.reset()
    cpu.b = 0x21
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0x20
    cpu.step()
    my_assert(cpu.a == 0xff)
    my_assert(cpu.b == 0x42)
    my_assert(cpu.f == 0x04)
    my_assert(cpu.pc == 2)

    # SLA B
    reset_mem()
    cpu.reset()
    cpu.b = 0x21
    cpu.f = 1
    ram0[0] = 0xcb
    ram0[1] = 0x20
    cpu.step()
    my_assert(cpu.a == 0xff)
    my_assert(cpu.b == 0x42)
    my_assert(cpu.f == 0x04)
    my_assert(cpu.pc == 2)

def test_push_pop():
    reset_mem()
    cpu.reset()
    cpu.b = 0x12
    cpu.c = 0x34
    cpu.sp = 0x3fff
    cpu._push(0xc0) # PUSH BC
    my_assert(cpu.sp == 0x3ffd)
    my_assert(cpu.read_mem_16(0x3ffd) == 0x1234)
    cpu.a = 0xaa
    cpu.f = 0xbb
    cpu._push(0xf0) # PUSH AF
    cpu._push(0xd0) # PUSH DE => 0xffff

    cpu._pop(0xf0) # POP
    my_assert(cpu.a == 0xff)
    my_assert(cpu.f == 0xff)
    cpu._pop(0xc0)
    my_assert(cpu.b == 0xaa)
    my_assert(cpu.c == 0xbb)
    cpu.d = 0x50
    cpu.e = 0x50
    cpu._pop(0xd0)
    my_assert(cpu.d == 0x12)
    my_assert(cpu.e == 0x34)

    # PUSH IX
    reset_mem()
    cpu.reset()
    cpu.sp = 0x3fff
    cpu.f = 0
    cpu.ix = 0x4321
    ram0[0] = 0xdd
    ram0[1] = 0xe5
    ram0[2] = 0xfd
    ram0[3] = 0xe1
    cpu.step()
    my_assert(cpu.f == 0x00)
    my_assert(cpu.pc == 2)
    my_assert(cpu.sp == 0x3ffd)
    my_assert(cpu.read_mem_16(0x3ffd) == 0x4321)
    cpu.step()
    my_assert(cpu.f == 0x00)
    my_assert(cpu.pc == 4)
    my_assert(cpu.sp == 0x3fff)
    my_assert(cpu.iy == 0x4321)

    # PUSH IY
    reset_mem()
    cpu.reset()
    cpu.sp = 0x3fff
    cpu.f = 0
    cpu.iy = 0x4321
    ram0[0] = 0xfd
    ram0[1] = 0xe5
    ram0[2] = 0xdd
    ram0[3] = 0xe1
    cpu.step()
    my_assert(cpu.f == 0x00)
    my_assert(cpu.pc == 2)
    my_assert(cpu.sp == 0x3ffd)
    my_assert(cpu.read_mem_16(0x3ffd) == 0x4321)
    cpu.step()
    my_assert(cpu.f == 0x00)
    my_assert(cpu.pc == 4)
    my_assert(cpu.sp == 0x3fff)
    my_assert(cpu.ix == 0x4321)

def test_jr():
    # JR -2
    reset_mem()
    cpu.reset()
    cpu.f = 0
    ram0[0] = 0x18
    ram0[1] = 0xfe
    cpu.step()
    my_assert(cpu.f == 0x00)
    my_assert(cpu.pc == 0)

    # JR NZ,-2
    reset_mem()
    cpu.reset()
    cpu.f = 64
    ram0[0] = 0x20
    ram0[1] = 0xfe
    cpu.step()
    my_assert(cpu.f == 64)
    my_assert(cpu.pc == 2)

    # JR 9
    reset_mem()
    cpu.reset()
    cpu.f = 0
    ram0[0] = 0x18
    ram0[1] = 0x09
    cpu.step()
    my_assert(cpu.f == 0x00)
    my_assert(cpu.pc == 0x0b)

def test_djnz():
    # DJNZ -2 not taken
    reset_mem()
    cpu.reset()
    cpu.b = 1
    cpu.f = 0
    ram0[0] = 0x10
    ram0[1] = 0xfe
    cpu.step()
    my_assert(cpu.f == 0x00)
    my_assert(cpu.pc == 2)

    # DJNZ,-2 taken
    reset_mem()
    cpu.reset()
    cpu.b == 2
    cpu.f = 0
    ram0[0] = 0x10
    ram0[1] = 0xfe
    cpu.step()
    my_assert(cpu.f == 0x00)
    my_assert(cpu.pc == 0)

def test_sub():
    # SUB B
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.b = 0x21
    cpu.f = 0
    ram0[0] = 0x90
    cpu.step()
    my_assert(cpu.a == 0xf0 - 0x21)
    my_assert(cpu.f == 0xb2)
    my_assert(cpu.pc == 1)

    # SUB (HL)
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.h = 0x10
    cpu.l = 0x00
    ram0[0x1000] = 0x21
    cpu.f = 0
    ram0[0] = 0x96
    cpu.step()
    my_assert(cpu.a == 0xf0 - 0x21)
    my_assert(cpu.f == 0xb2)
    my_assert(cpu.pc == 1)

    # SBC B
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.b = 0x21
    cpu.f = 1
    ram0[0] = 0x98
    cpu.step()
    my_assert(cpu.a == 0xf0 - 0x21 - 1)
    my_assert(cpu.f == 0xb2)
    my_assert(cpu.pc == 1)

    # SUB *
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.f = 0
    ram0[0] = 0xd6
    ram0[1] = 0x21
    cpu.step()
    my_assert(cpu.a == 0xf0 - 0x21)
    my_assert(cpu.f == 0xb2)
    my_assert(cpu.pc == 2)

    # SBC *
    reset_mem()
    cpu.reset()
    cpu.a = 0xf0
    cpu.f = 1
    ram0[0] = 0xd6
    ram0[1] = 0x21
    cpu.step()
    my_assert(cpu.a == 0xcf)
    my_assert(cpu.f == 0x92)
    my_assert(cpu.pc == 2)

    # SBC HL,BC
    reset_mem()
    cpu.reset()
    cpu.b = 0xf0
    cpu.c = 0x21
    cpu.h = 0x29
    cpu.l = 0x29
    cpu.f = 1
    ram0[0] = 0xed
    ram0[1] = 0x42
    cpu.step()
    my_assert(cpu.pc == 2)
    my_assert(cpu.b == 0xf0)
    my_assert(cpu.c == 0x21)
    my_assert(cpu.h == 0x39)
    my_assert(cpu.l == 0x07)
    my_assert(cpu.f == 0x03)

    # SBC HL,BC [1]
    reset_mem()
    cpu.reset()
    cpu.b = 0x7f
    cpu.c = 0x7f
    cpu.h = 0x0f
    cpu.l = 0x0f
    cpu.f = 1
    ram0[0] = 0xed
    ram0[1] = 0x42
    cpu.step()
    my_assert(cpu.pc == 2)
    my_assert(cpu.h == 0x8f)
    my_assert(cpu.l == 0x8f)
    my_assert(cpu.f == 0x93)

    # SBC HL,BC [2]
    reset_mem()
    cpu.reset()
    cpu.b = 0x7f
    cpu.c = 0x7f
    cpu.h = 0x0f
    cpu.l = 0x0f
    cpu.f = 0
    ram0[0] = 0xed
    ram0[1] = 0x42
    cpu.step()
    my_assert(cpu.pc == 2)
    my_assert(cpu.h == 0x8f)
    my_assert(cpu.l == 0x90)
    my_assert(cpu.f == 0x93)

def test_inc():
    # INC b
    reset_mem()
    cpu.reset()
    cpu.b = 0xff
    cpu.f = 1
    ram0[0] = 0x04
    cpu.step()
    my_assert(cpu.b == 0x00)
    my_assert(cpu.f == 0x51)
    my_assert(cpu.pc == 1)

    # INC b
    reset_mem()
    cpu.reset()
    cpu.b = 0x7f
    cpu.f = 1
    ram0[0] = 0x04
    cpu.step()
    my_assert(cpu.b == 0x80)
    my_assert(cpu.f == 0x95)
    my_assert(cpu.pc == 1)

    # INC b
    reset_mem()
    cpu.reset()
    cpu.b = 0x0f
    cpu.f = 1
    ram0[0] = 0x04
    cpu.step()
    my_assert(cpu.b == 0x10)
    my_assert(cpu.f == 0x11)
    my_assert(cpu.pc == 1)

    # INC de
    reset_mem()
    cpu.reset()
    cpu.d = 0x22
    cpu.e = 0x33
    cpu.f = 123
    ram0[0] = 0x13
    cpu.step()
    my_assert(cpu.d == 0x22)
    my_assert(cpu.e == 0x34)
    my_assert(cpu.f == 123)
    my_assert(cpu.pc == 1)

    # INC hl
    reset_mem()
    cpu.reset()
    cpu.h = 0x22
    cpu.l = 0x33
    cpu.f = 0
    ram0[0] = 0x34
    ram0[0x2233] = 0xff
    cpu.step()
    my_assert(cpu.h == 0x22)
    my_assert(cpu.l == 0x33)
    my_assert(cpu.pc == 1)
    my_assert(cpu.read_mem(0x2233) == 0x00)
    my_assert(cpu.f == 0x50)

def test_dec():
    # DEC b
    reset_mem()
    cpu.reset()
    cpu.b = 0x80
    cpu.f = 1
    ram0[0] = 0x05
    cpu.step()
    my_assert(cpu.b == 0x7f)
    my_assert(cpu.f == 0x17)
    my_assert(cpu.pc == 1)

    # DEC b
    reset_mem()
    cpu.reset()
    cpu.b = 0x04
    cpu.f = 1
    ram0[0] = 0x05
    cpu.step()
    my_assert(cpu.b == 0x03)
    my_assert(cpu.f == 0x03)
    my_assert(cpu.pc == 1)

    # DEC de
    reset_mem()
    cpu.reset()
    cpu.d = 0x22
    cpu.e = 0x33
    cpu.f = 123
    ram0[0] = 0x1b
    cpu.step()
    my_assert(cpu.d == 0x22)
    my_assert(cpu.e == 0x32)
    my_assert(cpu.f == 123)
    my_assert(cpu.pc == 1)

    # DEC a
    reset_mem()
    cpu.reset()
    cpu.a = 0x80
    cpu.f = 1
    ram0[0] = 0x3d
    cpu.step()
    my_assert(cpu.a == 0x7f)
    my_assert(cpu.f == 0x17)
    my_assert(cpu.pc == 1)

def test_rlca_rlc_rl_rla():
    # RLCA
    reset_mem()
    cpu.reset()
    cpu.a = 0xe1
    cpu.f = 0
    ram0[0] = 0x07
    cpu.step()
    my_assert(cpu.a == 0xc3)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 1)

    # RLCA
    reset_mem()
    cpu.reset()
    cpu.a = 0xe1
    cpu.f = 1
    ram0[0] = 0x07
    cpu.step()
    my_assert(cpu.a == 0xc3)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 1)

    # RLC B
    reset_mem()
    cpu.reset()
    cpu.b = 0xe1
    cpu.f = 1
    ram0[0] = 0xcb
    ram0[1] = 0x00
    cpu.step()
    my_assert(cpu.b == 0xc3)
    my_assert(cpu.f == 0x85)
    my_assert(cpu.pc == 2)

    # RLC B
    reset_mem()
    cpu.reset()
    cpu.b = 0xe1
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0x00
    cpu.step()
    my_assert(cpu.b == 0xc3)
    my_assert(cpu.f == 0x85)
    my_assert(cpu.pc == 2)

    # RL B
    reset_mem()
    cpu.reset()
    cpu.b = 0x71
    cpu.f = 1
    ram0[0] = 0xcb
    ram0[1] = 0x10
    cpu.step()
    my_assert(cpu.b == 0xe3)
    my_assert(cpu.f == 0x80)
    my_assert(cpu.pc == 2)

    # RL B
    reset_mem()
    cpu.reset()
    cpu.b = 0x71
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0x10
    cpu.step()
    my_assert(cpu.b == 0xe2)
    my_assert(cpu.f == 0x84)
    my_assert(cpu.pc == 2)

    # RLA
    reset_mem()
    cpu.reset()
    cpu.a = 0xe1
    cpu.f = 1
    ram0[0] = 0x17
    cpu.step()
    my_assert(cpu.a == 0xc3)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 1)

    # RLA
    reset_mem()
    cpu.reset()
    cpu.a = 0xe1
    cpu.f = 0
    ram0[0] = 0x17
    cpu.step()
    my_assert(cpu.a == 0xc2)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 1)

def test_di_ei():
    # DI
    reset_mem()
    cpu.reset()
    cpu.f = 0
    ram0[0] = 0xf3
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 1)
    my_assert(cpu.interrupts == False)

    # EI
    reset_mem()
    cpu.reset()
    cpu.f = 0
    ram0[0] = 0xfb
    cpu.step()
    my_assert(cpu.f == 0)
    my_assert(cpu.pc == 1)
    my_assert(cpu.interrupts == True)

def test_ex():
    # EX DE,HL
    reset_mem()
    cpu.reset()
    cpu.d = 123
    cpu.e = 210
    cpu.h = 50
    cpu.l = 20
    cpu.f = 123
    ram0[0] = 0xeb
    cpu.step()
    my_assert(cpu.f == 123)
    my_assert(cpu.pc == 1)
    my_assert(cpu.d == 50)
    my_assert(cpu.e == 20)
    my_assert(cpu.h == 123)
    my_assert(cpu.l == 210)

    # EX (SP),HL
    reset_mem()
    cpu.reset()
    cpu.sp = 0x1000
    cpu.write_mem_16(0x1000, 0xffdd)
    cpu.h = 0x50
    cpu.l = 0x20
    cpu.f = 123
    ram0[0] = 0xe3
    cpu.step()
    my_assert(cpu.f == 123)
    my_assert(cpu.pc == 1)
    my_assert(cpu.h == 0xff)
    my_assert(cpu.l == 0xdd)
    my_assert(cpu.read_mem_16(0x1000) == 0x5020)

    # EXX
    reset_mem()
    cpu.reset()
    cpu.h = 0x50
    cpu.h_ = 0x10
    cpu.l = 0x20
    cpu.l_ = 0x29
    cpu.f = 123
    ram0[0] = 0xd9
    cpu.step()
    my_assert(cpu.f == 123)
    my_assert(cpu.pc == 1)
    my_assert(cpu.h == 0x10)
    my_assert(cpu.h_ == 0x50)
    my_assert(cpu.l == 0x29)
    my_assert(cpu.l_ == 0x20)

    # EX AF
    reset_mem()
    cpu.reset()
    cpu.a = 0x50
    cpu.a_ = 0x10
    cpu.f = 0x20
    cpu.f_ = 0x29
    ram0[0] = 0x08
    cpu.step()
    my_assert(cpu.pc == 1)
    my_assert(cpu.a == 0x10)
    my_assert(cpu.a_ == 0x50)
    my_assert(cpu.f == 0x29)
    my_assert(cpu.f_ == 0x20)

def test_rrca():
    # RRCA
    reset_mem()
    cpu.reset()
    cpu.a = 0xe1
    cpu.f = 0
    ram0[0] = 0x0f
    cpu.step()
    my_assert(cpu.a == 0xf0)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 1)

    # RRCA
    reset_mem()
    cpu.reset()
    cpu.a = 0xe1
    cpu.f = 1
    ram0[0] = 0x0f
    cpu.step()
    my_assert(cpu.a == 0xf0)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 1)

def test_rr():
    # RR B
    reset_mem()
    cpu.reset()
    cpu.b = 0xe1
    cpu.f = 1
    ram0[0] = 0xcb
    ram0[1] = 0x18
    cpu.step()
    my_assert(cpu.pc == 2)
    my_assert(cpu.f == 0x85)
    my_assert(cpu.b == 0xf0)

    # RR B
    reset_mem()
    cpu.reset()
    cpu.b = 0xe1
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0x18
    cpu.step()
    my_assert(cpu.pc == 2)
    my_assert(cpu.b == 0x70)
    my_assert(cpu.f == 0x01)

def test_rst():
    # RST
    reset_mem()
    cpu.reset()
    cpu.f = 123
    cpu.sp = 0x3fff
    ram0[0] = 0xd7
    cpu.step()
    my_assert(cpu.pc == 0x10)
    my_assert(cpu.f == 123)
    my_assert(cpu.sp == 0x3ffd)
    my_assert(cpu.read_mem_16(0x3ffd) == 0x001)

    # RST
    reset_mem()
    cpu.reset()
    cpu.f = 123
    cpu.sp = 0x3fff
    ram0[0] = 0xdf
    cpu.step()
    my_assert(cpu.pc == 0x18)
    my_assert(cpu.f == 123)
    my_assert(cpu.sp == 0x3ffd)
    my_assert(cpu.read_mem_16(0x3ffd) == 0x001)

def test_ccf():
    # CCF
    reset_mem()
    cpu.reset()
    cpu.f = 0xff
    ram0[0] = 0x3f
    cpu.step()
    my_assert(cpu.pc == 1)
    my_assert(cpu.f == 0xec)

    # CCF
    reset_mem()
    cpu.reset()
    cpu.f = 0x00
    ram0[0] = 0x3f
    cpu.step()
    my_assert(cpu.pc == 1)
    my_assert(cpu.f == 0x01)

def test_res():
    # RES 0,C
    reset_mem()
    cpu.reset()
    cpu.c = 0xff
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0x81
    cpu.step()
    my_assert(cpu.c == 0xfe)
    my_assert(cpu.pc == 2)
    my_assert(cpu.get_flag_c() == False)
    my_assert(cpu.get_flag_n() == False)
    my_assert(cpu.get_flag_h() == False)
    my_assert(cpu.get_flag_z() == False)

    # RES 0,C
    reset_mem()
    cpu.reset()
    cpu.c = 0x00
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0x81
    cpu.step()
    my_assert(cpu.c == 0x00)
    my_assert(cpu.pc == 2)
    my_assert(cpu.get_flag_c() == False)
    my_assert(cpu.get_flag_n() == False)
    my_assert(cpu.get_flag_h() == False)
    my_assert(cpu.get_flag_z() == False)

    # RES 7,C
    reset_mem()
    cpu.reset()
    cpu.c = 0xff
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0xb9
    cpu.step()
    my_assert(cpu.c == 0x7f)
    my_assert(cpu.pc == 2)
    my_assert(cpu.get_flag_c() == False)
    my_assert(cpu.get_flag_n() == False)
    my_assert(cpu.get_flag_h() == False)
    my_assert(cpu.get_flag_z() == False)

def test_set():
    # SET 0,C
    reset_mem()
    cpu.reset()
    cpu.c = 0xfe
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0xc1
    cpu.step()
    my_assert(cpu.c == 0xff)
    my_assert(cpu.pc == 2)
    my_assert(cpu.get_flag_c() == False)
    my_assert(cpu.get_flag_n() == False)
    my_assert(cpu.get_flag_h() == False)
    my_assert(cpu.get_flag_z() == False)

    # SET 7,C
    reset_mem()
    cpu.reset()
    cpu.c = 0x7f
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0xf9
    cpu.step()
    my_assert(cpu.c == 0xff)
    my_assert(cpu.pc == 2)
    my_assert(cpu.get_flag_c() == False)
    my_assert(cpu.get_flag_n() == False)
    my_assert(cpu.get_flag_h() == False)
    my_assert(cpu.get_flag_z() == False)

    # SET 7,C
    reset_mem()
    cpu.reset()
    cpu.c = 0xff
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0xf9
    cpu.step()
    my_assert(cpu.c == 0xff)
    my_assert(cpu.pc == 2)
    my_assert(cpu.get_flag_c() == False)
    my_assert(cpu.get_flag_n() == False)
    my_assert(cpu.get_flag_h() == False)
    my_assert(cpu.get_flag_z() == False)

def test_bit():
    # BIT 0,C
    reset_mem()
    cpu.reset()
    cpu.c = 0xff
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0x41
    cpu.step()
    my_assert(cpu.c == 0xff)
    my_assert(cpu.pc == 2)
    my_assert(cpu.f == (0x11 & 0xd6))

    # BIT 0,(HL)
    reset_mem()
    cpu.reset()
    cpu.h = 0x10
    cpu.l = 0x00
    cpu.write_mem(0x1000, 0xff)
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0x46
    cpu.step()
    my_assert(cpu.pc == 2)
    my_assert(cpu.get_flag_c() == False)
    my_assert(cpu.get_flag_n() == False)
    my_assert(cpu.get_flag_h() == True)
    my_assert(cpu.get_flag_z() == False)

    # BIT 4,C
    reset_mem()
    cpu.reset()
    cpu.c = 0x10
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0x61
    cpu.step()
    my_assert(cpu.c == 0x10)
    my_assert(cpu.pc == 2)
    my_assert(cpu.get_flag_c() == False)
    my_assert(cpu.get_flag_n() == False)
    my_assert(cpu.get_flag_h() == True)
    my_assert(cpu.get_flag_z() == False)

    # BIT 4,C
    reset_mem()
    cpu.reset()
    cpu.c = 0x00
    cpu.f = 1
    ram0[0] = 0xcb
    ram0[1] = 0x61
    cpu.step()
    my_assert(cpu.c == 0)
    my_assert(cpu.pc == 2)
    my_assert(cpu.get_flag_c() == True)
    my_assert(cpu.get_flag_n() == False)
    my_assert(cpu.get_flag_h() == True)
    my_assert(cpu.get_flag_z() == True)

def test_ldi_r():
    # LDIR
    reset_mem()
    cpu.reset()
    cpu.b = 0x00
    cpu.c = 0x08
    cpu.d = 0x10
    cpu.e = 0x00
    cpu.h = 0x20
    cpu.l = 0x00
    cpu.f = 0xff
    for i in range(0x2000, 0x2008):
        ram0[i] = i & 0xff
    ram0[0] = 0xed
    ram0[1] = 0xb0
    cpu.step()
    my_assert(cpu.b == 0)
    my_assert(cpu.c == 0)
    my_assert(cpu.d == 0x10)
    my_assert(cpu.e == 0x08)
    my_assert(cpu.h == 0x20)
    my_assert(cpu.l == 0x08)
    my_assert(cpu.pc == 2)
    my_assert(cpu.get_flag_c() == True)
    my_assert(cpu.get_flag_n() == False)
    my_assert(cpu.get_flag_pv() == False)
    my_assert(cpu.get_flag_h() == False)
    my_assert(cpu.get_flag_z() == True)
    my_assert(cpu.get_flag_s() == True)
    for i in range(0x1000, 0x1008):
        assert(ram0[i] == i & 0xff)

    # LDI
    reset_mem()
    cpu.reset()
    cpu.b = 0x00
    cpu.c = 0x08
    cpu.d = 0x10
    cpu.e = 0x00
    cpu.h = 0x20
    cpu.l = 0x00
    cpu.f = 0xff
    ram0[0x2000] = 123
    ram0[0] = 0xed
    ram0[1] = 0xa0
    cpu.step()
    my_assert(cpu.b == 0)
    my_assert(cpu.c == 7)
    my_assert(cpu.d == 0x10)
    my_assert(cpu.e == 0x01)
    my_assert(cpu.h == 0x20)
    my_assert(cpu.l == 0x01)
    my_assert(cpu.pc == 2)
    my_assert(cpu.get_flag_c() == True)
    my_assert(cpu.get_flag_n() == False)
    my_assert(cpu.get_flag_pv() == False)
    my_assert(cpu.get_flag_h() == False)
    my_assert(cpu.get_flag_z() == True)
    my_assert(cpu.get_flag_s() == True)
    assert(ram0[0x1000] == 123)

def test_srl():
    # SRL B
    reset_mem()
    cpu.reset()
    cpu.b = 0x21
    cpu.f = 0
    ram0[0] = 0xcb
    ram0[1] = 0x38
    cpu.step()
    my_assert(cpu.b == 0x10)
    my_assert(cpu.f == 0x01)
    my_assert(cpu.pc == 2)

cpu = z80(read_mem, write_mem, read_io, write_io, debug)

test__flags()
test__support()
test_add()
test_and()
test_bit()
test_call_ret()
test_ccf()
test_cp_cpir()
test_cpl()
test_dec()
test_di_ei()
test_djnz()
test_ex()
test_inc()
test_jp()
test_jr()
test_ld()
test_ldi_r()
test_nop()
test_or()
test_out_in()
test_push_pop()
test_res()
test_rlca_rlc_rl_rla()
test_rr()
test_rrca()
test_rst()
test_set()
test_sla()
test_srl()
test_sub()
test_xor()

print('All fine')
