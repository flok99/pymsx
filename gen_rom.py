# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import sys
from typing import List

class gen_rom:
    def __init__(self, gen_rom_file, debug, offset=0x4000):
        print('Loading gen rom %s at %04x...' % (gen_rom_file, offset), file=sys.stderr)

        self.offset: int = offset

        fh = open(gen_rom_file, 'rb')
        self.rom: List[int] = [ int(b) for b in fh.read() ]
        fh.close()

        self.debug = debug

    def get_ios(self):
        return [ [ ], [ ] ]

    def get_name(self):
        return 'generic ROM'

    def get_pages(self):
        return [ p for p in range(1, 1 + (len(self.rom) + 16383) // 16384) ]

    def write_mem(self, a: int, v: int) -> None:
        pass

    def read_mem(self, a: int) -> int:
        offset = a - self.offset
        return self.rom[offset]
