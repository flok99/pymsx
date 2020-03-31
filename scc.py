# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import sys
from typing import List, Tuple

class scc:
    def __init__(self, scc_rom_file, snd, debug):
        print('Loading SCC rom %s...' % scc_rom_file, file=sys.stderr)

        fh = open(scc_rom_file, 'rb')
        self.scc_rom = [ int(b) for b in fh.read() ]
        fh.close()

        self.n_pages: int = (len(self.scc_rom) + 0x1fff) // 0x2000

        self.scc_pages: List[int] = [ 0, 1, 2, 3 ]

        self.snd = snd

        self.debug = debug

    def get_ios(self):
        return [ [ ] , [ ] ]

    def get_name(self):
        return 'SCC'

    def get_pages(self):
        return [1, 2]

    def split_addr(self, a: int) -> Tuple[int, int]:
        bank = (a >> 13) - 2
        offset = a & 0x1fff

        return bank, offset

    def write_mem(self, a: int, v: int) -> None:
        bank, offset = self.split_addr(a)

        p = self.scc_pages[bank] * 0x2000 + offset

        if offset >= 0x1000 and offset < 0x1800: # 0x5000, 0x7000 and so on
            and_ = v & (self.n_pages - 1)
            self.debug('Set bank %d to %d/%d (%04x)' % (bank, v, and_, a))
            self.scc_pages[bank] = and_

        elif a >= 0x9800 and a <= 0xafff0:
            if self.snd:
                self.snd.set_scc(a & 0xff, v)

        else:
            self.debug('SCC write to %04x not understood' % a)

    def read_mem(self, a: int) -> int:
        bank, offset = self.split_addr(a)

        p = self.scc_pages[bank] * 0x2000 + offset

        return self.scc_rom[p]
