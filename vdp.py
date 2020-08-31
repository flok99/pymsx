# (C) 2020 by Folkert van Heusden <mail@vanheusden.com>
# released under AGPL v3.0

# implements VDP logic

import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = 'hide'
import sys
import threading
import time
from typing import List
import traceback
import renderer

class vdp(threading.Thread):
    def __init__(self, wrescale : int = 1, hrescale : int = 1):

        self.ram: List[int] = [ 0 ] * 131072

        self.vdp_rw_pointer: int = 0
        self.vdp_addr_state: bool = False
        self.vdp_addr_b1 = None
        self.vdp_read_ahead: int = 0

        self.registers: List[int] = [ 0 ] * 47
        self.status_register: List[int] = [ 0 ] * 10

        self.stop_flag: bool = False

        # TMS9918 palette 
        self.rgb = [ self.rgb_to_i(0, 0, 0), self.rgb_to_i(0, 0, 0), self.rgb_to_i(33, 200, 66), self.rgb_to_i(94, 220, 120), self.rgb_to_i(84, 85, 237), self.rgb_to_i(125, 118, 252), self.rgb_to_i(212, 82, 77), self.rgb_to_i(66, 235, 245), self.rgb_to_i(252, 85, 84), self.rgb_to_i(255, 121, 120), self.rgb_to_i(212, 193, 84), self.rgb_to_i(231, 206, 128), self.rgb_to_i(33, 176, 59), self.rgb_to_i(201, 91, 186), self.rgb_to_i(204, 204, 204), self.rgb_to_i(255, 255, 255) ]
        self.pal_sel = False
        self.pal_byte_0 = 0

        self.sc8_rgb_map: List[[int, int, int, int]] = [ [ 0, 0, 0 ] ] * 256
        for i in range(0, 256):
            r = int((i >> 5) * (255 / 7))
            g = int(((i >> 2) & 7) * (255 / 7))
            b = int((i & 3) * (255 / 3))

            self.sc8_rgb_map[i] = [ self.rgb_to_i(r, g, b), r, g, b ]

        self.sourcex: int = 0
        self.sourcey: int = 0
        self.destinationx: int = 0
        self.destinationy: int = 0
        self.numberx: int = 0
        self.numbery: int = 0
        self.vdp_cmd = None
        self.start_destinationx: int = 0
        start_destinationy: int = 0
        self.pixelsleft: int = 0
        self.pixeloffset: int = 0
        self.highspeed: bool = False

        self.prev_hsync_int = 0
        self.prev_vsync_int = 0

        self.cv = threading.Condition()

        self.renderer = renderer.Renderer(wrescale, hrescale)

        super(vdp, self).__init__()

    def resize_window(self, w: int, h: int):
        self.arr = self.renderer.win_resize(w, h)
        
    def rgb_to_i(self, r: int, g: int, b: int) -> int:
        return (r << 16) | (g << 8) | b

    def interrupt(self) -> None:
        self.status_register[0] |= 128

    def video_mode(self) -> int:
        m1 = (self.registers[1] >> 4) & 1
        m2 = (self.registers[1] >> 3) & 1
        m3 = (self.registers[0] >> 1) & 1
        m4 = (self.registers[0] >> 2) & 1
        m5 = (self.registers[0] >> 3) & 1

        return (m1 << 4) | (m2 << 3) | (m3 << 2) | (m4 << 1) | m5

    def set_register(self, a: int, v: int) -> None:
        self.registers[a] = v

        if a == 0x10:  # palette index
            self.pal_sel = False

        elif a == 0x20:
            self.sourcex &= ~255
            self.sourcex |= v

        elif a == 0x21:
            self.sourcex &= 255
            self.sourcex |= (v & 1) << 8

        elif a == 0x22:
            self.sourcey &= ~255
            self.sourcey |= v

        elif a == 0x23:
            self.sourcey &= 255
            self.sourcey |= (v & 3) << 8

        elif a == 0x24:
            self.destinationx &= ~255
            self.destinationx |= v

        elif a == 0x25:
            self.destinationx &= 255
            self.destinationx |= (v & 1) << 8

        elif a == 0x26:
            self.destinationy &= ~255
            self.destinationy |= v

        elif a == 0x27:
            self.destinationy &= 255
            self.destinationy |= (v & 3) << 8

        elif a == 0x28:
            self.numberx &= ~255
            self.numberx |= v

        elif a == 0x29:
            self.numberx &= 255
            self.numberx |= (v & 3) << 8

        elif a == 0x2a:
            self.numbery &= ~255
            self.numbery |= v

        elif a == 0x2b:
            self.numbery &= 255
            self.numbery |= (v & 3) << 8

        elif a == 0x2e:  # command register
            self.vdp_cmd = v >> 4
            self.pixelsleft = self.numberx * self.numbery
            self.pixeloffset = 0
            self.start_destinationx = self.destinationx
            self.start_destinationy = self.destinationy
            self.highspeed = False

            if self.vdp_cmd == 0x05:
                self.put_vdp_2c(self.registers[0x2c])

            elif self.vdp_cmd == 0x07:
                self.draw_line(self.video_mode(), self.destinationx, self.destinationy, self.numberx, self.numbery, self.registers[0x2d], self.registers[0x2c])

            elif self.vdp_cmd == 0x0b:
                self.put_vdp_2c(self.registers[0x2c])
                self.highspeed = False

            elif self.vdp_cmd == 0x0c:
                self.highspeed = True
                self.fill_rect(self.video_mode(), self.destinationx, self.destinationy, self.numberx, self.numbery, self.registers[0x2c]);

            else:
                print('Unsupported VDP command %02x' % self.vdp_cmd)

            self.status_register[2] |= 1
            
            # FIXME

        self.resize_trigger = True

    def put_vdp_2c(self, v):
        # print('Call to put_vdp_2c %02x' % v)
        if self.pixelsleft == 0:
            return

        vm = self.video_mode()

        if self.vdp_cmd == 0x05 or self.vdp_cmd == 0x0b:  # logical put pixels, cpu -> vram
            y = self.pixeloffset // self.numberx
            x = self.pixeloffset - (y * self.numberx)

            self.plot(vm, self.destinationx, self.destinationy, v, self.highspeed)
            self.pixeloffset += 1
            self.pixelsleft -= 1

            self.destinationx += 1
            if self.destinationx == self.start_destinationx + self.numberx:
                self.destinationx = self.start_destinationx
                self.destinationy += 1

        elif self.vdp_cmd == 0x0c:  # fill rect
            y = self.pixeloffset // self.numberx
            x = self.pixeloffset - (y * self.numberx)

            self.plot(vm, self.destinationx, self.destinationy, v, self.highspeed)
            self.pixeloffset += 1
            self.pixelsleft -= 1

            self.destinationx += 1
            if self.destinationx == self.start_destinationx + self.numberx:
                self.destinationx = self.start_destinationx
                self.destinationy += 1

        elif self.vdp_cmd == 0x0f:  # plot
            np = 0
            dy = self.pixeloffset // self.numberx
            y = self.destinationy + dy
            x = self.destinationx + (self.pixeloffset - (dy * self.numberx))
            offset = 0

            if vm == 6:
                offset = (y * (256 // 2)) + (x // 2)
            elif vm == 1:
                offset = (y * (512 // 4)) + (x // 4)
            elif vm == 5:
                offset = (y * (512 // 2)) + (x // 2)
            elif vm == 7:
                offset = (y * 256) + x

            self.ram[offset] = v

            if vm == 6:
                np = 2
            elif vm == 1:
                np = 4
            elif vm == 5:
                np = 2
            elif vm == 7:
                np = 1
            # FIXME

            self.pixeloffset += np
            self.pixelsleft -= np

        else:
            print('put_vdp_2c vdp_cmd unsupported %02x' % self.vdp_cmd)

    def write_io(self, a: int, v: int) -> None:
        vm = self.video_mode()

        if a == 0x98:
            if vm in (4, 16, 0):  # MSX 1 modi
                self.ram[self.vdp_rw_pointer] = v
                self.vdp_rw_pointer += 1
                self.vdp_rw_pointer &= 0x3fff

            else:
                vram_addr_high = (self.registers[0x0e] & 7) << 14
                vram_addr = vram_addr_high + self.vdp_rw_pointer
                self.ram[vram_addr] = v

                self.vdp_rw_pointer += 1

                if self.vdp_rw_pointer >= 16384:
                    self.registers[0x0e] += 1
                    self.registers[0x0e] &= 7

                    self.vdp_rw_pointer = 0

            self.vdp_addr_state = False
            self.vdp_read_ahead = v

        elif a == 0x99:
            if self.vdp_addr_state == False:
                self.vdp_addr_b1 = v

            else:
                if (v & 128) == 128:
                    v &= 63
                    # print('set vdp register %x to %02x' % (v, self.vdp_addr_b1))
                    self.set_register(v, self.vdp_addr_b1)

                else:
                    vram_addr = self.vdp_rw_pointer = ((v & 63) << 8) + self.vdp_addr_b1

                    if vm not in (4, 16, 0):  # not MSX 1 modi
                        vram_addr += (self.registers[0x0e] & 7) << 14

                    if (v & 64) == 0:
                        self.vdp_read_ahead = self.ram[vram_addr]

                        self.vdp_rw_pointer += 1

                        if self.vdp_rw_pointer >= 16384:
                            self.registers[0x0e] += 1
                            self.registers[0x0e] &= 7

                            self.vdp_rw_pointer = 0

            self.vdp_addr_state = not self.vdp_addr_state

        elif a == 0x9a:  # palette
            if self.pal_sel == False:
                self.pal_byte_0 = v

            else:
                entry = self.registers[0x10] & 15

                self.registers[0x10] += 1
                self.registers[0x10] &= 15

                r = int(((self.pal_byte_0 >> 4) & 7) * 255 / 7)
                g = int((v & 7) * 255 / 7)
                b = int((self.pal_byte_0 & 7) * 255 / 7)

                self.rgb[entry] = self.rgb_to_i(r, g, b)
                print('set RGB %d to %d,%d,%d' % (entry, r, g, b))

            self.pal_sel = not self.pal_sel

        elif a == 0x9b:  # indirect register access port
            register_index = self.registers[0x11] & 63

            if register_index != 0x11:
                self.set_register(register_index, v)

            if (self.registers[0x11] & 128) == 0:
                self.registers[0x11] += 1
                self.registers[0x11] &= 63

            if register_index == 0x2c:
                self.put_vdp_2c(v)

        elif a == 0xaa:  # PPI register C
            self.renderer.kb_set_row(v & 15)

        else:
            print('vdp::write_io: Unexpected port %02x' % a)

    def read_io(self, a: int) -> int:
        vm = self.video_mode()

        rc = 0

        if a == 0x98:
            rc = self.vdp_read_ahead

            if vm in (4, 16, 0):  # MSX 1 modi
                self.vdp_read_ahead = self.ram[self.vdp_rw_pointer]

                self.vdp_rw_pointer += 1
                self.vdp_rw_pointer &= 0x3fff

            else:
                vram_addr_high = (self.registers[0x0e] & 7) << 14
                self.vdp_read_ahead = self.ram[vram_addr_high + self.vdp_rw_pointer]

                self.vdp_rw_pointer += 1
                if self.vdp_rw_pointer >= 0x4000:
                    self.vdp_rw_pointer &= 0x3fff

                    self.registers[0x0e] += 1
                    self.registers[0x0e] &= 7

            self.vdp_addr_state = False

        elif a == 0x99:
            reg = self.registers[15]
            rc = self.status_register[reg]

            if reg == 0:
                self.status_register[reg] &= ~(128 | 32)

            elif reg == 2:
                self.status_register[reg] = (self.status_register[reg] & 0x7e) | ((~(self.status_register[reg] & 0x81)) & 0x81)
                self.status_register[reg] &= ~0x60

                now = time.time()

                if now - self.prev_vsync_int >= 1 / 50: # FIXME 50Hz configurable?
                    self.status_register[reg] |= 0x40
                    self.prev_vsync_int = now

                if now - self.prev_hsync_int >= 1 / (228 * 50): # hsync
                    self.status_register[reg] |= 0x20
                    self.prev_hsync_int = now

            self.vdp_addr_state = False

        elif a == 0xa9:
            rc = self.renderer.kb_read() 

        else:
            print('vdp::read_io: Unexpected port %02x' % a)

        return rc

    def draw_sprite_part(self, off_x: int, off_y: int, pattern_offset: int, color: int, nr: int) -> None:
        sc = (self.registers[5] << 7) + nr * 16

        for y in range(off_y, off_y + 8):
            cur_pattern = self.ram[pattern_offset]
            pattern_offset += 1

            col = self.ram[sc]
            i = 128 if col & 8 else 0

            if y >= 192:
                break

            for x in range(off_x, off_x + 8):
                if x >= 256:
                    break

                if cur_pattern & 128:
                    self.arr[x, y] = color

                cur_pattern <<= 1

            sc += 1

    def draw_sprites(self) -> None:
        attr = (self.registers[5] & 127) << 7
        patt = self.registers[6] << 11

        for i in range(0, 32):
            attribute_offset = attr + i * 4

            spx = self.ram[attribute_offset + 1]
            if spx == 0xd0:
                break

            colori = self.ram[attribute_offset + 3] & 15
            if colori == 0:
                continue

            rgb = self.rgb[colori]

            spy = self.ram[attribute_offset + 0]

            pattern_index = self.ram[attribute_offset + 2]

            if self.registers[1] & 2:
                offset = patt + 8 * pattern_index

                self.draw_sprite_part(spx + 0, spy + 0, offset + 0, rgb, i)
                self.draw_sprite_part(spx + 0, spy + 8, offset + 8, rgb, i)
                self.draw_sprite_part(spx + 8, spy + 0, offset + 16, rgb, i)
                self.draw_sprite_part(spx + 8, spy + 8, offset + 24, rgb, i)

            else:
                self.draw_sprite_part(spx, spy, pattern_index, rgb, i)

    def get_pixel(self, vm: int, x: int, y: int, highspeed: bool) -> int:
        if vm == 6:  # screen 5
            offset = (y * (256 // 2)) + (x // 2)
            hnibble = x & 1
            shift = (1 - hnibble) * 4
            mask = 15

            if highspeed:
                return self.ram[offset]

            return (self.ram[offset] >> shift) & mask

        elif vm == 1:  # screen 6
            offset = (y * (512 // 4)) + (x // 4)
            hnibble = x & 3
            shift = (3 - hnibble) * 2
            mask = 3

            if highspeed:
                return self.ram[offset]

            return (self.ram[offset] >> shift) & mask

        elif vm == 5:  # screen 7
            offset = (y * (512 // 2)) + (x // 2)
            hnibble = x & 1
            shift = (1 - hnibble) * 4
            mask = 15

            if highspeed:
                return self.ram[offset]

            return (self.ram[offset] >> shift) & mask

        elif vm == 7:  # screen 8
            offset = (y * 256) + x

            if highspeed:
                return self.ram[offset]

            return self.ram[offset]

        return 123

    def plot(self, vm: int, x: int, y: int, color: int, highspeed: bool) -> None:
        # print('plot', x, y)

        if x < 0 or y < 0:
            return

        if vm == 6:  # screen 5
            if x >= 256 or y >= 212:
                return

            offset = (y * (256 // 2)) + (x // 2)

            if highspeed:
                self.ram[offset] = color

            else:
                bit = x & 1
                shift = ( 4, 0 )
                mask = ( 0xf0, 0x0f )

                self.ram[offset] &= mask[bit]
                self.ram[offset] |= (color & 15) << shift[bit]

        elif vm == 1:  # screen 6
            if x >= 512 or y >= 212:
                return

            offset = (y * (512 // 4)) + (x // 4)
            hnibble = x & 3
            shift = (3 - hnibble) * 2
            mask = ~(3 << shift)

            self.ram[offset] &= mask
            self.ram[offset] |= (color & 3) << shift

        elif vm == 5:  # screen 7
            if x >= 512 or y >= 212:
                return

            offset = (y * (512 // 2)) + (x // 2)

            if highspeed:
                self.ram[offset] = color

            else:
                hnibble = x & 1
                shift = (1 - hnibble) * 4
                mask = ~(15 << shift)

                self.ram[offset] &= mask
                self.ram[offset] |= (color & 15) << shift

        elif vm == 7:  # screen 8
            if x >= 256 or y >= 212:
                return

            offset = (y * 256) + x

            self.ram[offset] = color

    def fill_rect(self, video_mode: int, destinationx: int, destinationy: int, numberx: int, numbery: int, color: int):
        for y in range(destinationy, destinationy + numbery):
            for x in range(destinationx, destinationx + numberx):
                self.plot(video_mode, x, y, color, self.highspeed)

    def draw_line(self, video_mode: int, destinationx: int, destinationy: int, numberx: int, numbery: int, flags: int, color: int):
        # print('draw_line', destinationx, destinationy, numberx, numbery)
        error = 0.0

        MAJ = flags & 1
        DIX = flags & 4
        DIY = flags & 8

        dx = -1 if DIX else 1
        dy = -1 if DIY else 1

        if MAJ:  # y is longer side
            deltaerr = numberx / numbery
            x = destinationx
            y = destinationy

            while numbery > 0:
                self.plot(video_mode, x, y, color, self.highspeed)

                error += deltaerr
                if error >= 0.5:
                    x += dx
                    error -= 1.0

                y += dy
                numbery -= 1

        else:
            deltaerr = numbery / numberx
            x = destinationx
            y = destinationy

            while numberx > 0:
                self.plot(video_mode, x, y, color, self.highspeed)

                error += deltaerr
                if error >= 0.5:
                    y += dy
                    error -= 1.0

                x += dx
                numberx -= 1

    def draw_screen_0(self, vm):
        cols = 40 if vm == 16 else 80

        bg_map = (self.registers[2] & 0x7c) << 10 if cols == 80 else (self.registers[2] & 15) << 10
        bg_tiles = (self.registers[4] & 7) << 11

        bg = self.rgb[self.registers[7] & 15]
        fg = self.rgb[self.registers[7] >> 4]

        cache = [ None ] * 256

        for map_index in range(0, cols * 24):
            cur_char_nr = self.ram[bg_map + map_index]

            scr_x = (map_index % cols) * 8
            scr_y = (map_index // cols) * 8

            if cache[cur_char_nr] == None:
                cache[cur_char_nr] = [ 0 ] * 64

                cur_tiles = bg_tiles + cur_char_nr * 8

                for y in range(0, 8):
                    current_tile = self.ram[cur_tiles]
                    cur_tiles += 1

                    for x in range(0, 8):
                        cache[cur_char_nr][y * 8 + x] = fg if (current_tile & 128) == 128 else bg
                        current_tile <<= 1

            for y in range(0, 8):
                for x in range(0, 8):
                    self.arr[scr_x + x, scr_y + y] = cache[cur_char_nr][y * 8 + x]

        self.renderer.win_draw(self.arr)

    def draw_screen_1(self):
        bg_map    = (self.registers[2] &  15) << 10
        bg_colors = (self.registers[3] & 128) <<  6
        bg_tiles  = (self.registers[4] &   4) << 11

        cols = 32

        cache = [ None ] * 256


        for map_index in range(0, 32 * 24):
            cur_char_nr = self.ram[bg_map + map_index]

            current_color = self.ram[bg_colors + cur_char_nr // 8]
            fg = self.rgb[current_color >> 4]
            bg = self.rgb[current_color & 15]

            scr_x = (map_index % cols) * 8
            scr_y = (map_index // cols) * 8

            if cache[cur_char_nr] == None:
                cache[cur_char_nr] = [ 0 ] * 64

                cur_tiles = bg_tiles + cur_char_nr * 8

                for y in range(0, 8):
                    current_tile = self.ram[cur_tiles]
                    cur_tiles += 1

                    for x in range(0, 8):
                        cache[cur_char_nr][y * 8 + x] = fg if (current_tile & 128) == 128 else bg
                        current_tile <<= 1

            for y in range(0, 8):
                for x in range(0, 8):
                    self.arr[scr_x + x, scr_y + y] = cache[cur_char_nr][y * 8 + x]

        self.renderer.win_draw(self.arr)

    def draw_screen_2(self):
        bg_map    = (self.registers[2] &  15) << 10
        bg_colors = (self.registers[3] & 128) <<  6
        bg_tiles  = (self.registers[4] &   4) << 11

        pb = None
        cache = None

        tiles_offset = colors_offset = 0

        for map_index in range(0, 32 * 24):
            block_nr = (map_index >> 8) & 3

            if block_nr != pb:
                cache = [ None ] * 256
                pb = block_nr

                tiles_offset = bg_tiles  + (block_nr * 256 * 8)
                colors_offset = bg_colors + (block_nr * 256 * 8)

            cur_char_nr = self.ram[bg_map + map_index]

            scr_x = (map_index & 31) * 8
            scr_y = ((map_index >> 5) & 31) * 8

            if cache[cur_char_nr] == None:
                cache[cur_char_nr] = [ 0 ] * 64

                cur_tiles   = tiles_offset + cur_char_nr * 8
                cur_colors  = colors_offset + cur_char_nr * 8

                for y in range(0, 8):
                    current_tile = self.ram[cur_tiles]
                    cur_tiles += 1

                    current_color = self.ram[cur_colors]
                    cur_colors += 1

                    fg = self.rgb[current_color >> 4]
                    bg = self.rgb[current_color & 15]

                    for x in range(0, 8):
                        cache[cur_char_nr][y * 8 + x] = fg if (current_tile & 128) == 128 else bg
                        current_tile <<= 1

            for y in range(0, 8):
                for x in range(0, 8):
                    self.arr[scr_x + x, scr_y + y] = cache[cur_char_nr][y * 8 + x]

        self.draw_sprites()
        self.renderer.win_draw(self.arr)

    def draw_screen_6(self):
        name_table = (self.registers[2] & 0x60) << 9
        ny = 212 if (self.registers[9] & 128) == 128 else 192
        yo = self.registers[0x17]

        for y in range(0, ny):
            yp = ((y + yo) % 212) * 128

            for xp in range(0, 128):
                x = xp * 4
                p = name_table + yp + xp
                byte = self.ram[p]

                self.arr[x + 0, y] = self.rgb[byte >> 6]
                self.arr[x + 1, y] = self.rgb[(byte >> 4) & 3]
                self.arr[x + 2, y] = self.rgb[(byte >> 2) & 3]
                self.arr[x + 3, y] = self.rgb[byte & 3]

        self.draw_sprites()
        self.renderer.win_draw(self.arr)

    def draw_screen_5(self):
        name_table = 0

        for y in range(0, 212):
            offset = name_table + y * 128

            for x in range(0, 256, 2):
                byte = self.ram[offset]
                offset += 1

                p1 = self.rgb[byte >> 4]
                p2 = self.rgb[byte & 15]

                self.arr[x, y] = p1
                self.arr[x + 1, y] = p2

        self.draw_sprites()
        self.renderer.win_draw(self.arr)

    def draw_screen_8(self):
        name_table = 0

        for y in range(0, 212):
            offset = name_table + y * 256

            for x in range(0, 256):
                byte = self.ram[offset]
                offset += 1

                self.arr[x, y] = self.sc8_rgb_map[byte][0]

        self.draw_sprites()
        self.renderer.win_draw(self.arr)

    def run(self):
        try:
            self.setName('msx-display')

            pvm = None

            while not self.stop_flag:
                self.renderer.kb_poll()
                time.sleep(0.02)

                #msg = self.debug_msg[0:79]

                # s = time.time()

                vm = self.video_mode()

                resize_trigger = pvm != vm
                if resize_trigger:
                    print('new video mode:', vm)
                pvm = vm

                if vm == 4:  # 'screen 2' (256 x 192)
                    if resize_trigger:
                        self.resize_window(256, 192)

                    self.draw_screen_2()

                elif vm == 16 or vm == 18:  # 40/80 x 24
                    if resize_trigger:
                        self.resize_window(320 if vm == 16 else 640, 192)

                    self.draw_screen_0(vm)

                elif vm == 0:  # 'screen 1' (32 x 24)
                    if resize_trigger:
                        self.resize_window(256, 192)

                    self.draw_screen_1()

                elif vm == 6:  # 'screen 5' (256 x 212 x 16)
                    if resize_trigger:
                        self.resize_window(256, 212)

                    self.draw_screen_5()

                elif vm == 1:  # 'screen 6' (512 x 212 x 4)
                    if resize_trigger:
                        self.resize_window(512, 212)

                    self.draw_screen_6()

                elif vm == 7:  # 'screen 8' (256 x 212 x 256)
                    if resize_trigger:
                        self.resize_window(256, 212)

                    self.draw_screen_8()

                else:
                    #msg = 'Unsupported resolution'
                    print('Unsupported resolution', vm)
                    pass

                # took = time.time() - s
                # sfmt = 'display [vm {:02d} rescale x{:1}, x{:1}] update took: {:.2f} ms'
                # print(sfmt.format(vm, self.renderer.wrescale, self.renderer.hrescale, 1000*took))

                #self.debug_msg_lock.acquire()
                #if self.debug_msg:
                    #self.win.addstr(25, 0, msg)
                #    pass  # FIXME
                #self.debug_msg_lock.release()

        except Exception as e:
            print('VDP exception', e)
            traceback.print_exc(file=sys.stdout)
