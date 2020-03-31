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

abort_time = None # 60

debug_log = None

stop_flag = False

def debug(x):
    #dk.debug('%s' % x)

    if debug_log:
        fh = open(debug_log, 'a+')
        #fh.write('%s\t%02x %02x\n' % (x, read_page_layout(0), read_mem(0xffff) ^ 0xff))
        fh.write('%s\n' % x)
        fh.close()

def cpu_thread(cpu):
    while not stop_flag:
        cpu.step()

class bus:
    def __init__(self, debug):
        self.io_values: List[int] = [ 0 ] * 256
        self.io_read: List[Callable[[int], int]] = [ None ] * 256
        self.io_write: List[Callable[[int, int], None]] = [ None ] * 256

        self.subslot: List[int] = [ 0x00, 0x00, 0x00, 0x00 ]
        self.has_subslots: List[bool] = [ False, False, False, False ]

        self.slots = [[[None for k in range(4)] for j in range(4)] for i in range(4)]
        self.slot_for_page: List[int] = [ 0, 0, 0, 0 ]

        self.mm = memmap(256, debug)
        for p in range(0, 4):
            self.put_page(3, 0, p, self.mm)

        self.io_read[0xa8] = self.read_page_layout
        self.io_write[0xa8] = self.write_page_layout

    def put_page(self, slot: int, subslot: int, page: int, obj):
        self.has_subslots[slot] |= subslot > 0

        self.slots[slot][subslot][page] = obj

    def get_page(self, slot: int, subslot: int, page: int):
        return self.slots[slot][subslot][page]

    def get_subslot_for_page(self, slot: int, page: int):
        if self.has_subslots[slot]:
            return (self.subslot[slot] >> (page * 2)) & 3

        return 0

    def read_mem(self, a: int) -> int:
        assert a >= 0
        assert a < 0x10000

        page = a >> 14

        slot = self.get_page(self.slot_for_page[page], self.get_subslot_for_page(self.slot_for_page[page], page), page)

        if a == 0xffff:
            if self.has_subslots[self.slot_for_page[3]]:
                return self.subslot[self.slot_for_page[3]] ^ 0xff

            if slot:
                return 0 ^ 0xff

        if slot == None:
            return 0xee

        return slot.read_mem(a)

    def write_mem(self, a: int, v: int) -> None:
        assert a >= 0
        assert a < 0x10000

        if a == 0xffff:
            if self.has_subslots[self.slot_for_page[3]]:
                debug('Setting sub-page layout to %02x' % v)
                self.subslot[self.slot_for_page[3]] = v
                return

        page = a >> 14

        slot = self.get_page(self.slot_for_page[page], self.get_subslot_for_page(self.slot_for_page[page], page), page)
        if slot == None:
            debug('Writing %02x to %04x which is not backed by anything (slot: %02x, subslot: %02x)' % (v, a, self.read_page_layout(0), self.subslot[self.slot_for_page[3]]))
            return
        
        slot.write_mem(a, v)

    def read_page_layout(self, a: int) -> int:
        return (self.slot_for_page[3] << 6) | (self.slot_for_page[2] << 4) | (self.slot_for_page[1] << 2) | self.slot_for_page[0]

    def write_page_layout(self, a: int, v: int) -> None:
        for i in range(0, 4):
            self.slot_for_page[i] = (v >> (i * 2)) & 3

    def add_dev(self, d, slot: int, subslot: int):
        print('Registering %s' % d.get_name())

        dev_io_rw = d.get_ios()

        for r in dev_io_rw[0]:
            print('\tread I/O %02x' % r)
            self.io_read[r] = d.read_io

        for w in dev_io_rw[1]:
            print('\twrite I/O %02x' % w)
            self.io_write[w] = d.write_io

        if not slot is None and not subslot is None:
            for p in d.get_pages():
                print('\tput in %d/%d/%d' % (slot, subslot, p))
                self.put_page(slot, subslot, p, d)

    def read_io(self, a: int) -> int:
        if self.io_read[a]:
            return self.io_read[a](a)

        print('Unmapped I/O read %02x' % a)

        return self.io_values[a]
     
    def write_io(self, a: int, v: int) -> None:
        self.io_values[a] = v

        if self.io_write[a]:
            self.io_write[a](a, v)
        else:
            print('Unmapped I/O write %02x: %02x' % (a, v))


def printer_out(a: int, v: int) -> None:
    # FIXME handle strobe
    print('%c' % v, END='')

def terminator(a: int, v: int):
    global stop_flag

    if a == 0:
        stop_flag = True

def invoke_load_cas(a: int):
    if options.cas_file:
        global cpu

        cpu.pc = load_cas_file(write_mem, options.cas_file)

    return 123

parser = OptionParser()
parser.add_option('-b', '--biosbasic', dest='bb_file', help='select BIOS/BASIC ROM')
parser.add_option('-l', '--debug-log', dest='debug_log', help='logfile to write to (optional)')
parser.add_option('-R', '--rom', dest='rom', help='select a simple ROM to use, format: slot:rom-filename')
parser.add_option('-S', '--scc-rom', dest='scc_rom', help='select an SCC ROM to use, format: slot:rom-filename')
parser.add_option('-D', '--disk-rom', dest='disk_rom', help='select a disk ROM to use, format: slot:rom-filename:disk-image.dsk')
parser.add_option('-I', '--ide-rom', dest='ide_rom', help='select a Sunrise IDE ROM to use, format: slot:rom-filename:disk-image.dsk')
parser.add_option('-C', '--cas-file', dest='cas_file', help='select a .cas file to load')
(options, args) = parser.parse_args()

debug_log = options.debug_log

if not options.bb_file:
    print('No BIOS/BASIC ROM selected (e.g. msxbiosbasic.rom)')
    sys.exit(1)

b = bus(debug)

b.add_dev(rom(options.bb_file, debug, 0x0000), 0, 0)

snd = sound(debug)
b.add_dev(snd, None, None)

if options.scc_rom:
    parts = options.scc_rom.split(':')
    scc_obj = scc(parts[1], snd, debug)
    scc_slot = int(parts[0])
    b.add_dev(scc_obj, scc_slot, 0)

if options.disk_rom:
    parts = options.disk_rom.split(':')
    disk_slot = int(parts[0])
    disk_obj = disk(parts[1], debug, parts[2])
    b.add_dev(disk_obj, disk_slot, 0)

if options.rom:
    parts = options.rom.split(':')
    rom_slot = int(parts[0])
    offset = 0x4000
    if len(parts) == 3:
        offset = int(parts[2], 16)
    rom_obj = gen_rom(parts[1], debug, offset=offset)
    b.add_dev(rom_obj, rom_slot, 0)

if options.ide_rom:
    parts = options.ide_rom.split(':')
    ide_slot = int(parts[0])
    ide_obj = sunriseide(parts[1], debug, parts[2])
    b.add_dev(ide_obj, ide_slot, 0)

b.add_dev(RP_5C01(debug), None, None)

b.io_write[0x80] = terminator
b.io_read[0x81] = invoke_load_cas
b.io_write[0x91] = printer_out

dk = screen_kb(b)
b.add_dev(dk, None, None)

cpu = z80(b, debug, dk)

musicmodule = NMS_1205(cpu, debug)
musicmodule.start()
b.add_dev(musicmodule, None, None)

t = threading.Thread(target=cpu_thread, args=(cpu,))
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
