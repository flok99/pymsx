# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

import time
from typing import List

class RP_5C01:
    def __init__(self, debug):
        self.ri: int = 0
        self.regs: List[int] = [ 0 ] * 16
        self.debug = debug

    def get_ios(self):
        return [ [ 0xb5 ] , [ 0xb4, 0xb5 ] ]

    def get_name(self):
        return 'RP-5C01 (RTC)'

    def get_pages(self):
        return []

    def read_io(self, a: int) -> int:
        now = time.localtime()

        if self.ri == 0:
            return now.tm_sec % 10
        elif self.ri == 1:
            return now.tm_sec // 10
        elif self.ri == 2:
            return now.tm_min % 10
        elif self.ri == 3:
            return now.tm_min // 10
        elif self.ri == 4:
            return now.tm_hour % 10
        elif self.ri == 5:
            return now.tm_hour // 10
        elif self.ri == 6:
            return now.tm_wday
        elif self.ri == 7:
            return now.tm_mday % 10
        elif self.ri == 8:
            return now.tm_mday // 10
        elif self.ri == 9:
            return now.tm_mon % 10
        elif self.ri == 0x0a:
            return now.tm_mon // 10
        elif self.ri == 0x0b:
            return now.tm_year % 10
        elif self.ri == 0x0c:
            return (now.tm_year // 10) % 10

        self.debug('RP_5C01: read %02x' % a)

        return self.regs[self.ri]

    def write_io(self, a: int, v: int) -> None:
        if a == 0xb4:
            self.ri = v

        elif a == 0xb5:
            self.regs[self.ri] = v

            if self.ri >= 0x0d:
                self.debug('RP_5C01: write %02x %02x' % (a, v))
