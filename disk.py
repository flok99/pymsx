# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import struct
import sys
from pagetype import PageType

class disk:
    T1_BUSY = 0x01
    T1_INDEX = 0x02
    T1_TRACK0 = 0x04
    T1_CRCERR = 0x08
    T1_SEEKERR = 0x10
    T1_HEADLOAD = 0x20
    T1_PROT = 0x40
    T1_NOTREADY = 0x80

    T2_BUSY = 0x01
    T2_DRQ = 0x02
    T2_NOTREADY = 0x80

    BUF_MODE_IDLE = 1
    BUF_MODE_RW = 2

    FDC_STATUS_CMD = 0x08
    FDC_TRACK = 0x09
    FDC_SECTOR = 0x0a
    FDC_DATA_REGISTER = 0x0b
    FDC_FLAGS = 0x0c

    CMD_RESTORE = 0
    CMD_SEEK = 1
    CMD_STEP1 = 2
    CMD_STEP2 = 3
    CMD_STEP_IN1 = 4
    CMD_STEP_IN2 = 5
    CMD_STEP_OUT1 = 6
    CMD_STEP_OUT2 = 7
    CMD_READ1 = 8
    CMD_READ2 = 9
    CMD_WRITE1 = 10
    CMD_WRITE2 = 11
    CMD_READ_ADDR = 12
    CMD_FORCE_INT = 13
    CMD_READ_TRACK = 14
    CMD_WRITE_TRACK = 15

    def __init__(self, disk_rom_file, debug, disk_image_file):
        print('Loading disk rom %s...' % disk_rom_file, file=sys.stderr)

        fh = open(disk_rom_file, 'rb')
        self.disk_rom = [ int(b) for b in fh.read() ]
        fh.close()

        self.fh = open(disk_image_file, 'ab+')

        self.regs = [ 0 ] * 16

        self.buffer = [ 0 ] * 512
        self.bufp = 0
        self.bmode = disk.BUF_MODE_IDLE
        self.need_flush = False

        self.tc = None
        self.flags = 0

        self.step_dir = 1
        self.track = 0

        self.debug = debug

    def file_offset(self, side: int, track: int, sector: int) -> int:
        return (sector - 1) * 512 + (track * 9 * 512) + (80 * 9 * 512) * side;

    def get_signature(self):
        return (self.disk_rom, PageType.DISK, self)

    def write_mem(self, a: int, v: int) -> None:
        offset = a - 0x4000

        if offset >= 0x3ff0: # HW registers
            reg = offset - 0x3ff0

            self.regs[reg] = v

            if reg == disk.FDC_STATUS_CMD:
                command= v >> 4
                T      = (v >> 4) & 1;
                h      = (v >> 3) & 1;
                V      = (v >> 2) & 1;
                r1     = (v >> 1) & 1;
                r0     = (v     ) & 1;
                m      = (v >> 4) & 1;
                S      = (v >> 3) & 1;
                E      = (v >> 2) & 1;
                C      = (v >> 1) & 1;
                A0     = (v     ) & 1;
                i      = (v & 15);

                if command == disk.CMD_RESTORE:
                    self.debug('CMD: restore')
                    self.track = self.regs[disk.FDC_TRACK] = 0

                    self.flags = disk.T1_INDEX | disk.T1_TRACK0
                    if h:
                        self.flags |= disk.T1_HEADLOAD

                    self.tc = 1

                elif command == disk.CMD_SEEK:
                    self.track = self.regs[disk.FDC_TRACK] = self.regs[0x0b]
                    self.debug('CMD: seek to %d' % self.track)

                    self.flags = disk.T1_INDEX | (disk.T1_TRACK0 if self.track == 0 else 0)
                    if h:
                        self.flags |= disk.T1_HEADLOAD

                    self.tc = 1

                elif command == disk.CMD_STEP1 or command == disk.CMD_STEP2:
                    self.debug('CMD step %d' % self.step_dir)
                    self.track += self.step_dir

                    if self.track < 0:
                        self.track = 0
                    elif self.track > 79:
                        self.track = 79

                    self.flags = disk.T1_INDEX

                    if self.track == 0:
                        self.flags |= disk.T1_TRACK0

                    if T:
                        self.regs[disk.FDC_TRACK] = self.track

                    self.tc = 1

                elif command == disk.CMD_STEP_IN1 or command == disk.CMD_STEP_IN2:
                    self.debug('CMD step in')
                    self.track += 1

                    if self.track > 79:
                        self.track = 79

                    self.step_dir = 1

                    self.tc = 1

                    self.flags = disk.T1_INDEX

                    if T:
                        self.regs[disk.FDC_TRACK] = self.track

                elif command == disk.CMD_STEP_OUT1 or command == disk.CMD_STEP_OUT2:
                    self.debug('CMD step out')
                    self.track -= 1

                    if self.track < 0:
                        self.track = 0

                    self.step_dir = -1

                    self.tc = 1

                    self.flags = disk.T1_INDEX
                    if self.track == 0:
                        self.flags |= disk.T1_TRACK0;

                    if T:
                        self.regs[disk.FDC_TRACK] = self.track

                elif command == disk.CMD_READ1 or command == disk.CMD_READ2:
                    self.debug('CMD read sector')
                    self.bufp = 0
                    self.need_flush = False

                    side = 1 if (self.regs[self.FDC_FLAGS] & 0x08) == 0x08 else 0
                    o = self.file_offset(side, self.track, self.regs[disk.FDC_SECTOR])
                    self.debug('Read sector %d:%d:%d (offset %d) / %d' % (side, self.track, self.regs[disk.FDC_SECTOR], o, self.regs[disk.FDC_TRACK]))
                    self.fh.seek(o)
                    for i in range(0, 512):
                        b = self.fh.read(1)

                        if len(b) == 0:
                            self.buffer[i] = 0
                        else:
                            self.buffer[i] = struct.unpack('<B', b)[0]
                            print('%c' % self.buffer[i], end='')
                    print('')

                    self.tc = 2

                    self.flags |= disk.T2_BUSY | disk.T2_DRQ

                    self.bmode = disk.BUF_MODE_RW

                elif command == disk.CMD_WRITE1 or command == disk.CMD_WRITE2:
                    self.debug('CMD write sector')
                    self.bufp = 0
                    self.need_flush = True

                    self.tc = 2

                    self.flags |= disk.T2_BUSY | disk.T2_DRQ

                    self.bmode = disk.BUF_MODE_RW

                elif command == disk.CMD_READ_ADDR:
                    self.debug('CMD read address')
                    self.tc = 3

                    self.flags |= disk.T2_BUSY | disk.T2_DRQ
                    self.bmode = disk.BUF_MODE_RW

                elif command == disk.CMD_FORCE_INT:
                    self.debug('CMD force interrupt')
                    self.bufp = 0
                    self.bmode = disk.BUF_MODE_IDLE
                    self.tc = 4

                elif command == disk.CMD_READ_TRACK:
                    self.debug('CMD read track %d' % self.regs[disk.FDC_TRACK])

                    self.tc = 3

                    self.flags |= disk.T2_BUSY | disk.T2_DRQ

                elif command == disk.CMD_WRITE_TRACK:
                    self.debug('CMD write track %d' % self.regs[disk.FDC_TRACK])

                    self.tc = 3

                    self.flags |= disk.T2_BUSY | disk.T2_DRQ

                    self.bmode = disk.BUF_MODE_RW

                else:
                    self.debug('unknown disk-command %02x' % command)

            elif reg == disk.FDC_DATA_REGISTER:
                # self.debug('Write data register %02x' % v)

                if self.bmode != disk.BUF_MODE_IDLE and self.bufp < 512:
                    self.buffer[self.bufp] = v
                    self.bufp += 1

                    if self.bufp == 512:
                        if self.need_flush:
                            side = 1 if (self.regs[self.FDC_FLAGS] & 0x08) == 0x08 else 0
                            o = self.file_offset(side, self.track, self.regs[disk.FDC_SECTOR])
                            self.debug('Write sector %d:%d:%d (offset %o) / %d' % (side, self.track, self.regs[disk.FDC_SECTOR], o, self.regs[disk.FDC_TRACK]))

                            self.fh.seek(o)
                            self.fh.write(bytes(self.buffer))
                            self.fh.flush()

                        self.flags &= ~(disk.T2_DRQ | disk.T2_BUSY)

                        self.bmode = disk.BUF_MODE_IDLE

                    else:
                        self.flags |= disk.T2_DRQ
                else:
                    self.debug('Write data register: %02x' % self.regs[reg])

            elif reg == disk.FDC_SECTOR:  # sector
                self.debug('Select sector %d' % v)

            elif reg == self.FDC_FLAGS:  # side
                self.debug('Write side register %d' % 1 if v & 0x04 else 0)

                if (v & 0x04) == 0x04:  # reset
                    self.regs[disk.FDC_TRACK] = 0

            elif reg == 0x0d:  # motor control
                self.debug('Write motor control')

            else:
                self.debug('write: unknown disk register %02x' % reg)

    def read_mem(self, a: int) -> int:
        offset = a - 0x4000

        if offset >= 0x3ff0: # HW registers
            reg = offset - 0x3ff0

            self.debug('Read DISK register %02x' % reg)

            if reg == self.FDC_STATUS_CMD:
                self.debug('Read register %d' % reg)

                if self.tc == 1 or self.tc == 4:  # read
                    v = self.flags
                    self.flags &= (disk.T1_NOTREADY | disk.T1_BUSY)
                    return v

                elif self.tc == 2 or self.tc == 3:  # write
                    return self.flags

            elif reg == self.FDC_TRACK:
                self.debug('Read track nr (%d)' % self.regs[reg])
                return self.regs[reg]

            elif reg == disk.FDC_SECTOR:
                self.debug('Read sector nr (%d)' % self.regs[reg])
                return self.regs[reg]

            elif reg == disk.FDC_DATA_REGISTER:
                if self.bmode != disk.BUF_MODE_IDLE:
                    if self.bufp < 512:
                        v = self.buffer[self.bufp]
                        self.bufp += 1
                        self.flags |= disk.T2_DRQ
                        return v

                    else:
                        self.flags &= ~(disk.T2_DRQ | disk.T2_BUSY | 32)
                        self.debug('end of buffer READ')
                        self.bmode = disk.BUF_MODE_IDLE

                self.debug('Read data register: %02x' % self.regs[reg])

                return self.regs[reg]

            elif reg == self.FDC_FLAGS:
                self.debug('Read side (%d)' % self.regs[reg])
                return self.regs[reg]

            elif reg == 0x0f:
                v = 0

                if self.flags & disk.T2_DRQ:
                        v |= 128
                        self.flags &= ~disk.T2_DRQ

                if self.flags & disk.T2_BUSY:
                        v |= 64

                self.debug('Read status register (%02x) %02x' % (reg, v))
                return v

            else:
                self.debug('read (unknown) disk reg %d' % reg)

            return self.regs[reg]

        return self.disk_rom[offset]
