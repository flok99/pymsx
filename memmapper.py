# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import sys
from typing import List, Tuple

class memmap:
    def __init__(self, n_pages:int, debug):
        assert n_pages > 0 and n_pages <= 256

        self.n_pages: int = n_pages
        self.debug = debug

        self.mapper: List[int] = [ 3, 2, 1, 0 ]

        self.ram = [ [ 0 for k in range(16384)] for j in range(self.n_pages)]

    def get_ios(self):
        return [ [ 0xfc, 0xfd, 0xfe, 0xff ], [ 0xfc, 0xfd, 0xfe, 0xff ] ]

    def get_name(self):
        return 'memory mapper'

    def get_pages(self):
        return [ 0, 1, 2, 3 ]

    def split_addr(self, a: int) -> Tuple[int, int]:
        page = self.mapper[a >> 14]
        offset = a & 0x3fff

        return page, offset

    def write_mem(self, a:int, v:int) -> None:
        page, offset = self.split_addr(a)

        self.ram[page][offset] = v

    def read_mem(self, a: int) -> int:
        page, offset = self.split_addr(a)

        return self.ram[page][offset]

    def write_io(self, a: int, v: int) -> None:
        self.debug('memmap write %02x: %d' % (a, v))

        self.mapper[a - 0xfc] = v

    def read_io(self, a: int) -> int:
        self.debug('memmap read %02x' % a)

        return self.mapper[a - 0xfc]
