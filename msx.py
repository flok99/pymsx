#! /usr/bin/python3

# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import sys
import threading
import time
from disk import disk
from gen_rom import gen_rom
from scc import scc
from z80 import z80
from screen_kb import screen_kb
from sound import sound
from memmapper import memmap
from rom import rom
from optparse import OptionParser
from RP_5C01 import RP_5C01
from NMS_1205 import NMS_1205
from typing import Callable, List
from sunriseide import sunriseide
from cas import load_cas_file
from ascii16kb import ascii16kb
from msxdos2 import msxdos2

abort_time = None # 60

debug_log = None

io_values: List[int] = [ 0 ] * 256
io_read: List[Callable[[int], int]] = [ None ] * 256
io_write: List[Callable[[int, int], None]] = [ None ] * 256

subslot: List[int] = [ 0x00, 0x00, 0x00, 0x00 ]
has_subslots: List[bool] = [ False, False, False, False ]

def debug(x):
    #dk.debug('%s' % x)

    if debug_log:
        fh = open(debug_log, 'a+')
        fh.write('%s\t%02x %02x\n' % (x, read_page_layout(0), read_mem(0xffff) ^ 0xff))
        # fh.write('%s\n' % x)
        fh.close()

slots = [[[None for k in range(4)] for j in range(4)] for i in range(4)]

def put_page(slot: int, subslot: int, page: int, obj):
    has_subslots[slot] |= subslot > 0

    slots[slot][subslot][page] = obj

def get_page(slot: int, subslot: int, page: int):
    return slots[slot][subslot][page]

mm = memmap(256, debug)
for p in range(0, 4):
    put_page(3, 2, p, mm)

bb_file = None

parser = OptionParser()
parser.add_option('-b', '--biosbasic', dest='bb_file', help='select BIOS/BASIC ROM')
parser.add_option('-l', '--debug-log', dest='debug_log', help='logfile to write to (optional)')
parser.add_option('-R', '--rom', action='append', dest='rom', help='select a simple ROM to use, format: slot:subslot:rom-filename')
parser.add_option('-S', '--scc-rom', action='append', dest='scc_rom', help='select an SCC ROM to use, format: slot:subslot:rom-filename')
parser.add_option('-D', '--disk-rom', action='append', dest='disk_rom', help='select a disk ROM to use, format: slot:subslot:rom-filename:disk-image.dsk')
parser.add_option('-I', '--ide-rom', action='append', dest='ide_rom', help='select a Sunrise IDE ROM to use, format: slot:subslot:rom-filename:disk-image.dsk')
parser.add_option('-C', '--cas-file', dest='cas_file', help='select a .cas file to load')
parser.add_option('-A', '--ascii-16kb', action='append', dest='a16_rom', help='select an ASCII-16kB ROM to use, format: slot:subslot:rom-filename')
parser.add_option('-M', '--msx-dos2', action='append', dest='msxdos2_rom', help='select an MSX-DOS2 ROM to use, format: slot:subslot:rom-filename')
parser.add_option('-T', '--time', action='store_true', dest='time', help='enable RTC')
parser.add_option('-W', '--wrescale', dest='wrescale', help='Width rescale factor')
parser.add_option('-H', '--hrescale', dest='hrescale', help='Height rescale factor')
(options, args) = parser.parse_args()

debug_log = options.debug_log

if not options.bb_file:
    print('No BIOS/BASIC ROM selected (e.g. msxbiosbasic.rom)')
    sys.exit(1)

# bb == bios/basic
bb = rom(options.bb_file, debug, 0x0000)
put_page(0, 0, 0, bb)
put_page(0, 0, 1, bb)

snd = sound(debug)

if options.scc_rom:
    for o in options.scc_rom:
        parts = o.split(':')
        scc_obj = scc(parts[2], snd, debug)
        scc_slot = int(parts[0])
        scc_subslot = int(parts[1])
        put_page(scc_slot, scc_subslot, 1, scc_obj)
        put_page(scc_slot, scc_subslot, 2, scc_obj)

if options.disk_rom:
    for o in options.disk_rom:
        parts = o.split(':')
        disk_slot = int(parts[0])
        disk_subslot = int(parts[1])
        disk_obj = disk(parts[2], debug, parts[3])
        put_page(disk_slot, disk_subslot, 1, disk_obj)

if options.rom:
    for o in options.rom:
        parts = o.split(':')
        rom_slot = int(parts[0])
        rom_subslot = int(parts[1])
        offset = 0x4000
        if len(parts) == 4:
            offset = int(parts[3], 16)
        rom_obj = gen_rom(parts[2], debug, offset=offset)
        page_offset = offset // 0x4000
        for p in range(page_offset, page_offset + rom_obj.get_n_pages()):
            put_page(rom_slot, rom_subslot, p, rom_obj)

if options.ide_rom:
    for o in options.ide_rom:
        parts = o.split(':')
        ide_slot = int(parts[0])
        ide_subslot = int(parts[1])
        ide_obj = sunriseide(parts[2], debug, parts[3])
        put_page(ide_slot, ide_subslot, 1, ide_obj)

if options.a16_rom:
    for o in options.a16_rom:
        parts = o.split(':')
        a16_obj = ascii16kb(parts[2], debug)
        a16_slot = int(parts[0])
        a16_subslot = int(parts[1])
        put_page(a16_slot, a16_subslot, 1, a16_obj)
        put_page(a16_slot, a16_subslot, 2, a16_obj)

if options.msxdos2_rom:
    for o in options.msxdos2_rom:
        parts = o.split(':')
        md2_obj = msxdos2(parts[2], debug)
        md2_slot = int(parts[0])
        md2_subslot = int(parts[1])
        put_page(md2_slot, md2_subslot, 1, md2_obj)

slot_for_page: List[int] = [ 0, 0, 0, 0 ]

clockchip = None
if options.time:
    clockchip = RP_5C01(debug)

def get_subslot_for_page(slot: int, page: int):
    if has_subslots[slot]:
        return (subslot[slot] >> (page * 2)) & 3

    return 0

def read_mem(a: int) -> int:
    assert a >= 0
    assert a < 0x10000

    page = a >> 14

    slot = get_page(slot_for_page[page], get_subslot_for_page(slot_for_page[page], page), page)

    if a == 0xffff:
        if has_subslots[slot_for_page[3]]:
            return subslot[slot_for_page[3]] ^ 0xff

        if slot:
            return 0 ^ 0xff

    if slot == None:
        return 0xee

    return slot.read_mem(a)

def write_mem(a: int, v: int) -> None:
    assert a >= 0
    assert a < 0x10000

    if a == 0xffff:
        if has_subslots[slot_for_page[3]]:
            debug('Setting sub-page layout to %02x' % v)
            subslot[slot_for_page[3]] = v
            return

    page = a >> 14

    slot = get_page(slot_for_page[page], get_subslot_for_page(slot_for_page[page], page), page)
    if slot == None:
        debug('Writing %02x to %04x which is not backed by anything (slot: %02x, subslot: %02x)' % (v, a, read_page_layout(0), subslot[slot_for_page[3]]))
        return
    
    slot.write_mem(a, v)

def read_page_layout(a: int) -> int:
    return (slot_for_page[3] << 6) | (slot_for_page[2] << 4) | (slot_for_page[1] << 2) | slot_for_page[0]

def write_page_layout(a: int, v: int) -> None:
    for i in range(0, 4):
        slot_for_page[i] = (v >> (i * 2)) & 3

def printer_out(a: int, v: int) -> None:
    # FIXME handle strobe
    print('PRINTER: %c' % v)

def terminator(a: int, v: int) -> None:
    global stop_flag

    if a == 0:
        stop_flag = True

def lightpen(a: int) -> int:
    return 0

def lightpenw(a: int, v: int) -> None:
    pass

def invoke_load_cas(a: int) -> int:
    if options.cas_file:
        global cpu

        cpu.pc = load_cas_file(write_mem, options.cas_file)

    return 123

def add_dev(d) -> None:
    print('Registering %s' % d.get_name())

    dev_io_rw = d.get_ios()

    for r in dev_io_rw[0]:
        io_read[r] = d.read_io

    for r in dev_io_rw[1]:
        io_write[r] = d.write_io

def init_io():
    global dk
    global mm
    global musicmodule
    global snd
    global clockchip

    io_write[0x80] = terminator
    io_read[0x81] = invoke_load_cas

    io_read[0xb8] = lightpen
    io_read[0xb9] = lightpen
    io_read[0xba] = lightpen
    io_read[0xbb] = lightpen
    io_write[0xb8] = lightpenw
    io_write[0xb9] = lightpenw
    io_write[0xba] = lightpenw
    io_write[0xbb] = lightpenw

    if musicmodule:
        add_dev(musicmodule)

    if clockchip:
        add_dev(clockchip)

    if dk:
        add_dev(dk)

    if snd:
        add_dev(snd)

    add_dev(mm)

    print('set "mmu"')
    io_read[0xa8] = read_page_layout
    io_write[0xa8] = write_page_layout

    print('set printer')
    io_write[0x91] = printer_out

def read_io(a: int) -> int:
    global io_read

    if io_read[a]:
        return io_read[a](a)

    print('Unmapped I/O read %02x' % a)

    return io_values[a]
 
def write_io(a: int, v: int) -> None:
    global io_write

    io_values[a] = v

    if io_write[a]:
        io_write[a](a, v)
    else:
        print('Unmapped I/O write %02x: %02x' % (a, v))

stop_flag = False

def cpu_thread():
    #t = time.time()
    #while time.time() - t < 5:
    while not stop_flag:
        cpu.step()

dk = screen_kb(io_values, options)

cpu = z80(read_mem, write_mem, read_io, write_io, debug, dk)

musicmodule = NMS_1205(cpu, debug)
musicmodule.start()

init_io()

t = threading.Thread(target=cpu_thread)
t.start()

if abort_time:
    time.sleep(abort_time)
    stop_flag = True

try:
    t.join()

except KeyboardInterrupt:
    stop_flag = True
    t.join()

dk.stop()

#for i in range(0, 256):
#    if cpu.counts[i]:
#        print('instr %02x: %d' % (i, cpu.counts[i]), file=sys.stderr)
