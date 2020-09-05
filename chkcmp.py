#! /usr/bin/python3

# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import sys
import time
from inspect import getframeinfo, stack
from z80 import z80
from screen_kb_dummy import screen_kb_dummy

fh = None # open('debug.log', 'a+')

def debug(x):
    if fh:
        fh.write('%s\n' % x)

class msx:
    def __init__(self):
        self.io = [ 0 ] * 256

        self.ram0 = [ 0 ] * 16384

        dk = screen_kb_dummy(self.io, None)
        dk.start()

        self.cpu = z80(self.read_mem, self.write_mem, self.read_io, self.write_io, debug, dk)

        self.reset()

    def reset(self):
        self.cpu.reset()
        self.cpu.sp = 0x3fff

        self.ram0 = [ 0 ] * 16384

    def read_mem(self, a):
        # print('z80 read %04x %02x' % (a, self.ram0[a & 0x3fff]))
        return self.ram0[a & 0x3fff]

    def write_mem(self, a, v):
        # print('z80 write %04x %02x' % (a, v))
        self.ram0[a & 0x3fff] = v

    def read_io(self, a):
        return self.io[a]
     
    def write_io(self, a, v):
        self.io[a] = v

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

def my_assert(m, before, after, v1, v2):
    global errs

    if v1 != v2:
        print(before)
        print(after)
        print('expected: %x, is: %x ' % (v2, v1))
        print(m.cpu.reg_str())
        caller = getframeinfo(stack()[1][0])
        print(flag_str(m.cpu.f))
        print('%s:%d' % (caller.filename, caller.lineno))
        print('')
#        sys.exit(1)
        errs += 1

def check_flag(m, before, line, is_, should_be):
    if is_ != should_be:
        print('is: %s, should be: %s' % (flag_str(is_), flag_str(should_be)))
        my_assert(m, before, line, is_, should_be)

m = msx()

errs = 0

startt = pt = time.time()
lines = ntests = 0
before = after = None
while True:
    line = sys.stdin.readline()
    if not line:
        break

    parts = line.split()
    i = 1

    lines += 1

    if parts[0] == 'reset':
        ntests += 1
        m.reset()

    elif parts[0] == 'before':
        # print('---')
        # print(line)
        before = line

        memp = 0
        while parts[i] != '|':
            m.write_mem(memp, int(parts[i], 16))
            i += 1
            memp += 1

        i += 1  # skip |
        i += 1  # skip endaddr
        i += 1  # skip cycles

        m.cpu.a, m.cpu.f = m.cpu.u16(int(parts[i], 16))
        i += 1
        m.cpu.b, m.cpu.c = m.cpu.u16(int(parts[i], 16))
        i += 1
        m.cpu.d, m.cpu.e = m.cpu.u16(int(parts[i], 16))
        i += 1
        m.cpu.h, m.cpu.l = m.cpu.u16(int(parts[i], 16))
        i += 1

        m.cpu.a_, m.cpu.f_ = m.cpu.u16(int(parts[i], 16))
        i += 1
        m.cpu.b_, m.cpu.c_ = m.cpu.u16(int(parts[i], 16))
        i += 1
        m.cpu.d_, m.cpu.e_ = m.cpu.u16(int(parts[i], 16))
        i += 1
        m.cpu.h_, m.cpu.l_ = m.cpu.u16(int(parts[i], 16))
        i += 1

        m.cpu.ix = int(parts[i], 16)
        i += 1

        m.cpu.iy = int(parts[i], 16)
        i += 1

        i += 1  # PC

        m.cpu.sp = int(parts[i], 16)
        i += 1

    elif parts[0] == 'memchk':
        my_assert(m, before, line, m.read_mem(int(parts[1], 16)), int(parts[2], 16))

    elif parts[0] == 'memset':
        m.write_mem(int(parts[1], 16), int(parts[2], 16))

    else:
        # print(line)
        after = line
        while parts[i] != '|':
            i += 1

        i += 1  # skip |

        endaddr = int(parts[i], 16)
        i += 1

        expcycles = int(parts[i])
        i += 1

        cycles = 0
        while True:
            cycles += m.cpu.step()

            if m.cpu.pc >= endaddr:
                break

        # my_assert(m, before, line, cycles, expcycles)

        v = int(parts[i], 16)
        my_assert(m, before, line, m.cpu.a, v >> 8)
        #check_flag(m, before, line, m.cpu.f & 0xd7, (v & 255) & 0xd7);
        check_flag(m, before, line, m.cpu.f, v & 255);
        i += 1

        my_assert(m, before, line, m.cpu.m16(m.cpu.b, m.cpu.c), int(parts[i], 16))
        i += 1

        my_assert(m, before, line, m.cpu.m16(m.cpu.d, m.cpu.e), int(parts[i], 16))
        i += 1

        my_assert(m, before, line, m.cpu.m16(m.cpu.h, m.cpu.l), int(parts[i], 16))
        i += 1

        my_assert(m, before, line, m.cpu.m16(m.cpu.a_, m.cpu.f_), int(parts[i], 16))
        i += 1
        my_assert(m, before, line, m.cpu.m16(m.cpu.b_, m.cpu.c_), int(parts[i], 16))
        i += 1
        my_assert(m, before, line, m.cpu.m16(m.cpu.d_, m.cpu.e_), int(parts[i], 16))
        i += 1
        my_assert(m, before, line, m.cpu.m16(m.cpu.h_, m.cpu.l_), int(parts[i], 16))
        i += 1

        my_assert(m, before, line, m.cpu.ix, int(parts[i], 16))
        i += 1

        my_assert(m, before, line, m.cpu.iy, int(parts[i], 16))
        i += 1

        my_assert(m, before, line, m.cpu.pc, int(parts[i], 16))
        i += 1

        my_assert(m, before, line, m.cpu.sp, int(parts[i], 16))
        i += 1

        i += 1  # i
        i += 1  # r
        i += 1  # r7

        my_assert(m, before, line, m.cpu.im, int(parts[i], 16))
        i += 1

        i += 1  # iff1
        i += 1  # iff2

        assert i == len(parts)

    now = time.time()
    if now - pt >= 1.0:
        took = now - startt
        print('%d lines, %.1f tests/s' % (lines, ntests / took))
        pt = now

#    if now - startt >= 10.0:
#        break

took = time.time() - startt

if errs:
    print('%d errors, took %.1f seconds, %d lines (%.1f lines/s)' % (errs, took, lines, lines / took))
else:
    print('All fine, took %.1f seconds, %d lines (%.1f lines/s)' % (took, lines, lines / took))

if fh:
    fh.close()
