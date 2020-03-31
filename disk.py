# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import struct
import sys
from enum import Enum, IntFlag, IntEnum
from typing import List

class disk:
    class T1(IntFlag):
        BUSY = 0x01
        INDEX = 0x02
        TRACK0 = 0x04
        CRCERR = 0x08
        SEEKERR = 0x10
        HEADLOAD = 0x20
        PROT = 0x40
        NOTREADY = 0x80

    class T2(IntFlag):
        BUSY = 0x01
        DRQ = 0x02
        NOTREADY = 0x80

    class BufMode(Enum):
        IDLE = 1
        READ = 2
        WRITE = 3

    class Register(IntEnum):
        STATUS_CMD = 0x08
        TRACK = 0x09
        SECTOR = 0x0a
        DATA_REGISTER = 0x0b
        FLAGS = 0x0c

    class Cmd(IntEnum):
        RESTORE = 0
        SEEK = 1
        STEP1 = 2
        STEP2 = 3
        STEP_IN1 = 4
        STEP_IN2 = 5
        STEP_OUT1 = 6
        STEP_OUT2 = 7
        READ1 = 8
        READ2 = 9
        WRITE1 = 10
        WRITE2 = 11
        READ_ADDR = 12
        FORCE_INT = 13
        READ_TRACK = 14
        WRITE_TRACK = 15

    def __init__(self, disk_rom_file: str, debug, disk_image_file: str):
        print('Loading disk rom %s...' % disk_rom_file, file=sys.stderr)

        fh = open(disk_rom_file, 'rb')
        self.rom = [ int(b) for b in fh.read() ]
        fh.close()

        self.fh = open(disk_image_file, 'ab+')

        self.regs: List[int] = [ 0 ] * 16

        self.buffer: List[int] = [ 0 ] * 512
        self.bufp: int = 0
        self.bmode: disk.BufMode = disk.BufMode.IDLE
        self.need_flush: bool = False

        self.tc: int = 1
        self.flags: int = 0

        self.step_dir: int = 1
        self.track: int = 0

        self.debug = debug

    def get_ios(self):
        return [ [ ], [ ] ]

    def get_name(self):
        return 'FDC'

    def get_pages(self):
        return [ p for p in range(1, 1 + (len(self.rom) + 16383) // 16384) ]

    def file_offset(self, side: int, track: int, sector: int) -> int:
        o = (sector - 1) * 512 + (track * 9 * 512) + (80 * 9 * 512) * side
        self.debug('file offset side %d track %d sector %d: %d' % (side, track, sector, o))
        return o

    def write_mem(self, a: int, v: int) -> None:
        offset = a - 0x4000

        if offset >= 0x3ff0: # HW registers
            reg = offset - 0x3ff0

            self.regs[reg] = v

            if reg == disk.Register.STATUS_CMD:
                command: disk.Cmd = disk.Cmd(v >> 4)
                T: bool = ((v >> 4) & 1) == 1
                h: bool = ((v >> 3) & 1) == 1

                self.debug('write command register %02x: %02x, cmd %d' % (reg, v, command))

                if command == disk.Cmd.RESTORE:
                    self.debug('i restore')
                    self.track = self.regs[disk.Register.TRACK] = 0

                    self.flags = disk.T1.INDEX | disk.T1.TRACK0
                    if h:
                        self.flags |= disk.T1.HEADLOAD

                    self.tc = 1

                elif command == disk.Cmd.SEEK:
                    assert self.bmode == disk.BufMode.IDLE
                    self.track = self.regs[disk.Register.TRACK] = self.regs[0x0b]
                    self.debug('i seek to %d' % self.track)

                    self.flags = disk.T1.INDEX | (disk.T1.TRACK0 if self.track == 0 else 0)
                    if h:
                        self.flags |= disk.T1.HEADLOAD

                    self.tc = 1

                elif command in (disk.Cmd.STEP1, disk.Cmd.STEP2):
                    self.debug('i step to %d + %d' % (self.track, self.step_dir))
                    self.track += self.step_dir

                    if self.track < 0:
                        self.track = 0
                    elif self.track > 79:
                        self.track = 79

                    self.flags = disk.T1.INDEX

                    if self.track == 0:
                        self.flags |= disk.T1.TRACK0

                    if T:
                        self.regs[disk.Register.TRACK] = self.track

                    self.tc = 1

                elif command in (disk.Cmd.STEP_IN1, disk.Cmd.STEP_IN2):
                    self.track += 1
                    self.debug('i step in to %d' % self.track)

                    if self.track > 79:
                        self.track = 79

                    self.step_dir = 1

                    self.tc = 1

                    self.flags = disk.T1.INDEX

                    if T:
                        self.regs[disk.Register.TRACK] = self.track

                elif command in (disk.Cmd.STEP_OUT1, disk.Cmd.STEP_OUT2):
                    self.track -= 1
                    self.debug('i step out to %d' % self.track)

                    if self.track < 0:
                        self.track = 0

                    self.step_dir = -1

                    self.tc = 1

                    self.flags = disk.T1.INDEX
                    if self.track == 0:
                        self.flags |= disk.T1.TRACK0

                    if T:
                        self.regs[disk.Register.TRACK] = self.track

                elif command in (disk.Cmd.READ1, disk.Cmd.READ2):
                    # self.debug('CMD read sector')
                    self.bufp = 0
                    self.need_flush = False

                    side = 1 if (self.regs[self.Register.FLAGS] & 0x08) == 0x08 else 0
                    o = self.file_offset(side, self.track, self.regs[disk.Register.SECTOR])
                    m = (v >> 4) & 1
                    self.debug('ii read sector at %d / %d:%d:%d multiple: %d:' % (self.track, side, self.regs[0x09], self.regs[0x0a], m))
                    out = 'sector'
                    self.fh.seek(o)
                    for i in range(0, 512):
                        b = self.fh.read(1)

                        if len(b) == 0:
                            self.buffer[i] = 0
                        else:
                            self.buffer[i] = struct.unpack('<B', b)[0]
                            # self.debug('%c' % self.buffer[i], end='')
                        if i < 16:
                            out += ' %02x' % self.buffer[i]
                    self.debug(out)

                    self.tc = 2

                    self.flags |= disk.T2.BUSY | disk.T2.DRQ

                    self.bmode = disk.BufMode.READ

                elif command in (disk.Cmd.WRITE1, disk.Cmd.WRITE2):
                    self.bufp = 0
                    self.need_flush = True

                    self.tc = 2

                    self.flags |= disk.T2.BUSY | disk.T2.DRQ

                    self.bmode = disk.BufMode.WRITE

                    m = (v >> 4) & 1
                    self.debug('ii write sector at %d(%d):%d multiple: %d:' % (self.track, self.regs[0x09], self.regs[0x0a], m))

                elif command == disk.Cmd.READ_ADDR:
                    self.debug('iii read address')
                    assert False
                    self.tc = 3

                    self.flags |= disk.T2.BUSY | disk.T2.DRQ
                    self.bmode = disk.BufMode.READ

                elif command == disk.Cmd.FORCE_INT:
                    self.debug('iv force interrupt %d' % (v & 15))
                    self.bufp = 0
                    self.bmode = disk.BufMode.IDLE
                    self.tc = 4

                elif command == disk.Cmd.READ_TRACK:
                    self.debug('iii read track')

                    self.tc = 3

                    self.flags |= disk.T2.BUSY | disk.T2.DRQ

                elif command == disk.Cmd.WRITE_TRACK:
                    self.debug('iii write track')

                    self.tc = 3

                    self.flags |= disk.T2.BUSY | disk.T2.DRQ

                    self.bmode = disk.BufMode.WRITE

                else:
                    self.debug('unknown disk-command %02x' % command)

            elif reg == disk.Register.DATA_REGISTER:
                # self.debug('Write data register %02x' % v)

                if self.bmode == disk.BufMode.WRITE and self.bufp < 512:
                    self.buffer[self.bufp] = v
                    self.bufp += 1

                    if self.bufp == 512:
                        if self.need_flush:
                            side = 1 if (self.regs[self.Register.FLAGS] & 0x08) == 0x08 else 0
                            o = self.file_offset(side, self.track, self.regs[disk.Register.SECTOR])
                            self.debug('Write sector %d:%d:%d (offset %o) / %d' % (side, self.track, self.regs[disk.Register.SECTOR], o, self.regs[disk.Register.TRACK]))

                            self.fh.seek(o)
                            self.fh.write(bytes(self.buffer))
                            self.fh.flush()

                        self.flags &= ~(disk.T2.DRQ | disk.T2.BUSY)

                        self.bmode = disk.BufMode.IDLE

                    else:
                        self.flags |= disk.T2.DRQ
                else:
                    self.debug('Setting up data register for seek to %d' % v)
                    assert self.bmode == disk.BufMode.IDLE

            elif reg == disk.Register.SECTOR:  # sector
                self.debug('set sector to %d (%d)' % (v, self.regs[reg]))

            elif reg == self.Register.FLAGS:  # side
                if (v & 0x04) == 0x04:  # reset
                    self.debug('resetting controller')
                    self.track = 0

                self.debug('side: %d, drive: %d' % (1 if v & 0x10 else 0, v & 0x03))

            elif reg == 0x0d:  # motor control
                self.debug('set motor to %s (%d / %d)' % ("off" if v & 1 else "on", v, v & 1))

            else:
                self.debug('write: unknown disk register %02x' % reg)

    def read_mem(self, a: int) -> int:
        offset = a - 0x4000

        if offset >= 0x3ff0: # HW registers
            reg = offset - 0x3ff0

            # self.debug('Read DISK register %02x' % reg)

            if reg == self.Register.STATUS_CMD:
                if self.tc == 1 or self.tc == 4:  # read
                    self.debug('read status register type i: %02x' % self.flags)
                    v = self.flags
                    self.flags &= (disk.T1.NOTREADY | disk.T1.BUSY)
                    return v

                elif self.tc == 2 or self.tc == 3:  # write
                    self.debug('read status register type ii: %02x' % self.flags)
                    return self.flags

                else:
                    self.debug('status reg: unknown state')

            elif reg == self.Register.TRACK:
                self.debug('read track nr %d' % self.regs[reg])
                return self.regs[reg]

            elif reg == disk.Register.SECTOR:
                self.debug('read sector nr %d' % self.regs[reg])
                return self.regs[reg]

            elif reg == disk.Register.DATA_REGISTER:
                if self.bmode == disk.BufMode.READ:
                    if self.bufp == 0:
                        self.debug('start read data %02x at index %d' % (self.buffer[self.bufp], self.bufp))

                    if self.bufp < 512:
                        v = self.buffer[self.bufp]
                        self.bufp += 1

                        if self.bufp == 512:
                            self.flags &= ~(disk.T2.DRQ | disk.T2.BUSY | 32)
                            self.debug('finished reading data at index %d' % self.bufp)
                            self.bmode = disk.BufMode.IDLE

                        else:
                            self.flags |= disk.T2.DRQ

                        self.debug('data register: %02x' % v)

                        return v

                else:
                    self.debug('read sector already finished reading (offset %d)' % self.bufp)

                # self.debug('Read data register: %02x' % self.regs[reg])
                self.debug('data register: %02x' % 0xff)

                return 0xff  # self.regs[reg]

            elif reg == self.Register.FLAGS:
                self.debug('read side nr %d' % self.regs[reg])
                return self.regs[reg]

            elif reg == 0x0f:
                v = 0

                if self.flags & disk.T2.DRQ:
                    v |= 128
                    self.flags &= ~disk.T2.DRQ

                if self.flags & disk.T2.BUSY:
                    v |= 64

                self.debug('read DRQ: %d' % v)
                return v

            elif reg == 0x0d:
                self.debug('read motor state %d' % self.regs[0x0d])

            else:
                self.debug('unhandled disk read: %04x' % a)

            return self.regs[reg]

        return self.rom[offset]
