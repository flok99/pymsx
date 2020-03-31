# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

class screen_kb_dummy:
    def __init__(self, io):
        pass

    def get_ios(self):
        return [ [ ] , [ ] ]

    def get_name(self):
        return 'screen/keyboard'
    
    def get_pages(self):
        return []

    def interrupt(self):
        pass

    def IE0(self) -> bool:
        return False

    def start(self):
        pass

    def write_io(self, a: int, v: int) -> None:
        pass

    def read_io(self, a: int) -> int:
        return 0x00

    def debug(self, str_):
        pass

    def stop(self):
        pass
