#! /usr/bin/python3

# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import sys
import traceback
from inspect import getframeinfo, stack
from z80 import z80
from screen_kb_dummy import screen_kb_dummy

io = [ 0 ] * 256

ram0 = [ 0 ] * 16384
ram1 = [ 0 ] * 16384
ram2 = [ 0 ] * 16384
ram3 = [ 0 ] * 16384

slots = [ ] # slots
slots.append(( ram0, None, None, None ))
slots.append(( ram1, None, None, None ))
slots.append(( ram2, None, None, None ))
slots.append(( ram3, None, None, None ))

pages = [ 0, 0, 0, 0]

final = { }

def reset_mem():
    ram0 = [ 0 ] * 16384
    ram1 = [ 0 ] * 16384
    ram2 = [ 0 ] * 16384
    ram3 = [ 0 ] * 16384

def read_mem(a):
    page = a >> 14

    if slots[page][pages[page]] == None:
        return 0xee

    return slots[page][pages[page]][a & 0x3fff]

def write_mem(a, v):
    global subpage

    page = a >> 14

    if slots[page][pages[page]] == None:
        return

    slots[page][pages[page]][a & 0x3fff] = v

def read_io(a):
    return io[a]
 
def write_io(a, v):
    io[a] = v

debug_msgs = []

def debug(x):
    debug_msgs.append(x)

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

def my_assert(f, r, what):
    if not r:
        print(' *** FAIL FOR %s (%s) ***' % (f['id'], what))
        print('==========================')
        print('CURRENT')
        print('-------')
        print(cpu.reg_str())
        caller = getframeinfo(stack()[1][0])
        print('Flags: %s' % flag_str(cpu.f))
        print('%s:%d' % (caller.filename, caller.lineno))
        print('t-states: %d' % cpu.interrupt_cycles)
        print('')
        print('EXPECTED')
        print('--------')
        print('Flags: %s' % flag_str(f['r1'][0]))
        print('AF %04x' % f['r1'][0])
        print('BC %04x' % f['r1'][1])
        print('DE %04x' % f['r1'][2])
        print('HL %04x' % f['r1'][3])
        print('AF_ %04x' % f['r1'][4])
        print('BC_ %04x' % f['r1'][5])
        print('DE_ %04x' % f['r1'][6])
        print('HL_ %04x' % f['r1'][7])
        print('IX %04x' % f['r1'][8])
        print('IY %04x' % f['r1'][9])
        print('SP %04x' % f['r1'][10])
        print('PC %04x' % f['r1'][11])
        print('memptr %04x' % f['r1'][12])
        print('t-states %d' % f['r2'][6])
        for d in debug_msgs:
            print(d)
        print('')
        # sys.exit(1)

dk = screen_kb_dummy(io, None)
dk.start()

cpu = z80(read_mem, write_mem, read_io, write_io, debug, dk)

# tests.in
# --------

# Each test has the format:

# <arbitrary test description>
# AF BC DE HL AF' BC' DE' HL' IX IY SP PC MEMPTR
# I R IFF1 IFF2 IM <halted> <tstates>

# <halted> specifies whether the Z80 is halted.
# <tstates> specifies the number of tstates to run the test for, in
#   decimal; the number actually executed may be higher, as the final
#   instruction is allowed to complete.

# Then followed by lines specifying the initial memory setup. Each has
# the format:

# <start address> <byte1> <byte2> ... -1

# eg

# 1234 56 78 9a -1

# says to put 0x56 at 0x1234, 0x78 at 0x1235 and 0x9a at 0x1236.

# Finally, -1 to end the test. Blank lines may follow before the next test.

### load tests.expected and put it in a dictionary for later comparing ###

fh = open('tests.expected', 'r')
while True:
    while True:
        descr = fh.readline()
        if not descr:
            break

        descr = descr.rstrip('\n').rstrip(' ')
        if descr != '':
            break
    if not descr:
        break

    while True:
        event = fh.readline()
        if not event:
            break

        event = event.rstrip('\n').rstrip(' ')
        if event[0] != ' ' and event[0] != '\t':
            break

    next_line = event

    test_id = descr
    final[test_id] = { }
    final[test_id]['id'] = test_id  # hack

    registers1 = next_line
    parts = registers1.split()
    regs1 = [int(x, 16) for x in parts]
    final[test_id]['r1'] = regs1

    registers2 = fh.readline().rstrip('\n').rstrip(' ')
    parts = registers2.split()
    regs2 = [int(x, 16) for x in parts]
    regs2[6] = int(parts[6])
    final[test_id]['r2'] = regs2

    mem = []

    while True:
        setup = fh.readline()
        setup = setup.rstrip('\n')
        if setup == '-1':
            break

        parts = setup.split()
        if len(parts) == 0:
            break

        a = int(parts[0], 16)
        first = a

        for b in parts[1:]:
            if b == '':
                continue

            if b == '-1':
                break

            mem.append((a, int(b, 16)))
            a += 1
            a &= 0xffff

    final[test_id]['mem'] = mem

### process tests.in & execute tests in it ###

fh = open('tests.in', 'r')

while True:
    debug_msgs = []

    while True:
        descr = fh.readline()
        if not descr:
            break

        descr = descr.rstrip('\n').rstrip(' ')
        if descr != '':
            break
    if not descr:
        break

    # print(descr)

    cpu.reset()
    reset_mem()

    registers1 = fh.readline().rstrip('\n').rstrip(' ')
    parts = registers1.split()
    regs1 = [int(x, 16) for x in parts]
    (cpu.a, cpu.f) = cpu.u16(regs1[0])
    initial_f = cpu.f
    (cpu.b, cpu.c) = cpu.u16(regs1[1])
    (cpu.d, cpu.e) = cpu.u16(regs1[2])
    (cpu.h, cpu.l) = cpu.u16(regs1[3])
    (cpu.a_, cpu.f_) = cpu.u16(regs1[4])
    (cpu.b_, cpu.c_) = cpu.u16(regs1[5])
    (cpu.d_, cpu.e_) = cpu.u16(regs1[6])
    (cpu.h_, cpu.l_) = cpu.u16(regs1[7])
    cpu.ix = regs1[8]
    cpu.iy = regs1[9]
    cpu.sp = regs1[10]
    cpu.pc = regs1[11]
    cpu.memptr = regs1[12]

    f = final[descr]

    registers2 = fh.readline().rstrip('\n').rstrip(' ')
    parts = registers2.split()
    # print(parts)
    regs2 = [int(x, 16) for x in parts]
    regs2[6] = int(parts[6])

    while True:
        setup = fh.readline()
        setup = setup.rstrip('\n')
        if setup == '-1':
            break

        parts = setup.split()
        if len(parts) == 0:
            break

        a = int(parts[0], 16)
        first = a

        for b in parts[1:]:
            if b == '':
                continue

            if b == '-1':
                break

            cpu.write_mem(a, int(b, 16)) 
            a += 1
            a &= 0xffff

    ok = False

    try:
        ccnt = 0

        while ccnt < regs2[6]:
            ccnt += cpu.step()

        ok = True
    except:
        traceback.print_exc(file=sys.stdout)
        my_assert(f, False, 'exec')

    if ok:
        # verify registers
        (expa, expf) = cpu.u16(f['r1'][0])
        my_assert(f, cpu.a == expa, 'a')
        my_assert(f, (cpu.b, cpu.c) == cpu.u16(f['r1'][1]), 'bc')
        my_assert(f, (cpu.d, cpu.e) == cpu.u16(f['r1'][2]), 'de')
        my_assert(f, (cpu.h, cpu.l) == cpu.u16(f['r1'][3]), 'hl')
        my_assert(f, (cpu.a_, cpu.f_) == cpu.u16(f['r1'][4]), 'af_')
        my_assert(f, (cpu.b_, cpu.c_) == cpu.u16(f['r1'][5]), 'bc_')
        my_assert(f, (cpu.d_, cpu.e_) == cpu.u16(f['r1'][6]), 'de_')
        my_assert(f, (cpu.h_, cpu.l_) == cpu.u16(f['r1'][7]), 'hl_')
        my_assert(f, cpu.ix == f['r1'][8], 'ix')
        my_assert(f, cpu.iy == f['r1'][9], 'iy')
        my_assert(f, cpu.sp == f['r1'][10], 'sp')
        my_assert(f, cpu.pc == f['r1'][11], 'pc')
        my_assert(f, cpu.f == expf, 'f (%02x -> %02x and is %02x)' % (initial_f, expf, cpu.f))
        my_assert(f, cpu.memptr == f['r1'][12], 'memptr')

        # verify memory
        m = f['mem']

        for c in m:
            my_assert(f, cpu.read_mem(c[0]) == c[1], 'mem: %04x = %02x (is: %02x)' % (c[0], c[1], cpu.read_mem(c[0]))) 
