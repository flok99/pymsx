# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import mido  # type: ignore
import queue
import threading
import time

class NMS_1205(threading.Thread):
    def __init__(self, cpu, debug):
        self.cpu = cpu
        self.debug = debug

        self.mpo = mido.open_output()
        self.mpi = mido.open_input()

        self.outbuf = [ 0 ] * 3
        self.outbufin = 0

        self.qinbuf = queue.Queue()
        self.inbuf = [ ]

        self.stop_flag = False

        super(NMS_1205, self).__init__()

    def get_ios(self):
        return [ [ 0x00, 0x01, 0x04, 0x05, 0xc0 ] , [ 0x00, 0x01, 0x04, 0x05 ] ]

    def get_name(self):
        return 'NMS-1205'

    def get_pages(self):
        return []

    def stop(self):
        self.stop_flag = True
        self.mpo.close()

    def run(self):
        while not self.stop_flag:
            in_ = self.mpi.receive()

            self.qinbuf.put(in_)

            self.cpu.interrupt()

        self.mpi.close()

    def read_io(self, a: int) -> int:
        if a == 0x00:  # status register mpo
            return 0b00001110
        elif a == 0x01:
            return 0xff
        elif a == 0x04:  # status register mpo
            return 0b00001110 | (1 + 128 if self.inbuf or not self.qinbuf.empty() else 0)
        elif a == 0x05:
            if not self.inbuf and not self.qinbuf.empty():
                self.inbuf = self.qinbuf.get(block=False)

            if self.inbuf:
                c = self.inbuf[0]
                del self.inbuf[0]
                return c
        elif a == 0xc0:  # MSX-Music
            return 6

        return 0

    def push_byte(self, v: int) -> None:
        if v & 128:
            if self.outbufin > 0:
                self.mpo.write_short(self.outbuf)

            self.outbuf[0] = v
            self.outbufin = 1

        elif self.outbufin < 3:
            self.outbuf[self.outbufin] = v
            self.outbufin += 1

            cmd = self.outbuf[0] & 0xf0
            if cmd in (0x80, 0x90, 0xa0, 0xb0, 0xe0) and self.outbufin == 3:
                self.mpo.write_short(self.outbuf)
                self.outbufin = 0
            elif cmd in (0xc0, 0xd0) and self.outbufin == 2:
                self.mpo.write_short(self.outbuf)
                self.outbufin = 0
            else:
                self.mpo.write_short(self.outbuf)
                self.outbufin = 0

        else:
            self.debug('MIDI out buffer overrun')

    def write_io(self, a: int, v: int) -> None:
        if a == 0x00:
            pass
        elif a == 0x01:
            self.push_byte(v)
        elif a == 0x04:
            pass
        elif a == 0x05:
            pass
