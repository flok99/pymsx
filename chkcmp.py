#! /usr/bin/python3

# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import multiprocessing
import sys
import threading
import time
from inspect import getframeinfo, stack
from z80 import z80
from screen_kb_dummy import screen_kb_dummy

nproc = 12
file_ = '/data/rlc.dat'

class msx:
    def __init__(self):
        self.io = [ 0 ] * 256

        ram0 = [ 0 ] * 16384
        ram1 = [ 0 ] * 16384
        ram2 = [ 0 ] * 16384
        ram3 = [ 0 ] * 16384

        self.slots = [ ] # slots
        self.slots.append(( ram0, None, None, None ))
        self.slots.append(( ram1, None, None, None ))
        self.slots.append(( ram2, None, None, None ))
        self.slots.append(( ram3, None, None, None ))

        self.pages = [ 0, 0, 0, 0 ]

        self.dk = screen_kb_dummy(self.io)
        self.dk.start()

        self.cpu = z80(self.read_mem, self.write_mem, self.read_io, self.write_io, self.debug, self.dk)

    def read_mem(self, a):
        page = a >> 14

        if self.slots[page][self.pages[page]] == None:
            assert False

        return self.slots[page][self.pages[page]][a & 0x3fff]

    def write_mem(self, a, v):
        assert v >= 0 and v <= 255

        page = a >> 14

        if self.slots[page][self.pages[page]] == None:
            assert False

        self.slots[page][self.pages[page]][a & 0x3fff] = v

    def read_io(self, a):
        return self.io[a]
     
    def write_io(self, a, v):
        self.io[a] = v

    def debug(self, x):
        #fh = open('debug.log', 'a+')
        #fh.write('%s\n' % x)
        #fh.close()
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

def my_assert(before, after, v1, v2):
    if v1 != v2:
        print(before)
        print(after)
        print('expected:', v2)
        print('is:', v1)
        print(cpu.reg_str())
        caller = getframeinfo(stack()[1][0])
        print(flag_str(cpu.f))
        print('%s:%d' % (caller.filename, caller.lineno))
        sys.exit(1)

def worker(q, show):
    print('Thread started')

    pt = startt = time.time()
    n_tests = 0

    first = True

    while True:
        item = q.get()
        if item == None:
            break

        if first:
            first = False
            print('Processing started')

        m = msx()

        before = after = None

        for line in item:
            line = line.rstrip()
            parts = line.split()
            i = 1

            if parts[0] == 'before':
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

                i += 1 # AF_
                i += 1 # BC_
                i += 1 # DE_
                i += 1 # HL_

                m.cpu.ix = int(parts[i], 16)
                i += 1

                m.cpu.iy = int(parts[i], 16)
                i += 1

            elif parts[0] == 'memchk':
                my_assert(before, line, m.read_mem(int(parts[1], 16)), int(parts[2], 16))

            else:
                after = line
                while parts[i] != '|':
                    i += 1

                i += 1  # skip |

                endaddr = int(parts[i], 16)
                i += 1

                expcycles = int(parts[i])
                i += 1

                cycles = 0
                while m.cpu.pc < endaddr:
                    cycles += m.cpu.step()

                # my_assert(before, line, cycles, expcycles)

                my_assert(before, line, m.cpu.m16(m.cpu.a, m.cpu.f), int(parts[i], 16))
                i += 1

                my_assert(before, line, m.cpu.m16(m.cpu.b, m.cpu.c), int(parts[i], 16))
                i += 1

                my_assert(before, line, m.cpu.m16(m.cpu.d, m.cpu.e), int(parts[i], 16))
                i += 1

                my_assert(before, line, m.cpu.m16(m.cpu.h, m.cpu.l), int(parts[i], 16))
                i += 1

                i += 1 # AF_
                i += 1 # BC_
                i += 1 # DE_
                i += 1 # HL_

                my_assert(before, line, m.cpu.ix, int(parts[i], 16))
                i += 1

                my_assert(before, line, m.cpu.iy, int(parts[i], 16))
                i += 1

                my_assert(before, line, m.cpu.pc, int(parts[i], 16))
                i += 1

                my_assert(before, line, m.cpu.sp, int(parts[i], 16))
                i += 1

                i += 1  # i
                i += 1  # r
                i += 1  # r7

                my_assert(before, line, m.cpu.im, int(parts[i], 16))
                i += 1

                i += 1  # iff1
                i += 1  # iff2

                # obsoloted by memchk: my_assert(before, line, read_mem(m.cpu.m16(m.cpu.h, m.cpu.l)), int(parts[i], 16))
                i += 1

                assert i == len(parts)

        n_tests += 1

        now = time.time()
        if now - pt >= 1.0 and show:
            print('%.1f' % ((n_tests / (now - startt)) * nproc))
            pt = now

q = multiprocessing.Queue(16384)

for i in range(nproc):
    reader_p = multiprocessing.Process(target=worker, args=(q, i == 0,))
    reader_p.daemon = True
    reader_p.start()

batch = []
for line in open(file_, 'r'):
    line = line.rstrip()
    parts = line.split()

    if parts[0] == 'before':
        if batch:
            q.put(batch)
            batch = []

    batch.append(line)

if batch:
    q.put(batch)

print('Data loaded')

q.join()

print('Data processed')

for i in range(len(threads)):
    q.put(None)

for t in threads:
    t.join()
