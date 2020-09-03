#! /usr/bin/python3

# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import sys
import time
from inspect import getframeinfo, stack
from z80 import z80
from screen_kb_dummy import screen_kb_dummy

io = [ 0 ] * 256

ram = [ 0 ] * 65536

def read_mem(a):
    return ram[a]

def write_mem(a, v):
    ram[a] = v

def read_io(a):
    return io[a]
 
def write_io(a, v):
    io[a] = v

def debug(x):
    pass

dk = screen_kb_dummy(io, None)
dk.start()

cpu = z80(read_mem, write_mem, read_io, write_io, debug, dk)

fh = open('zexall.com', 'rb')
zex = [ int(b) for b in fh.read() ]
fh.close()

p = 0x0100
for b in zex:
    write_mem(p, b)
    p += 1

cpu.sp = 0xf000
cpu.pc = 0x0100

while True:
    if cpu.pc == 0x0005:
        if cpu.c == 2:
            print('%c' % cpu.e, end='', flush=True)

        elif cpu.c == 9:
            a = cpu.m16(cpu.d, cpu.e)

            str_ = ''

            while True:
                c = cpu.read_mem(a)
                if c == ord('$'):
                    break

                print('%c' % c, end='', flush=True)

                str_ += chr(c)

                a += 1

            if 'Tests complete' in str_:
                break

        cpu._ret(True, 'bla')

        continue

    cpu.step()
