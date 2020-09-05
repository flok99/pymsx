import sys
import pygame  # type: ignore


class Renderer:

    def __init__(self, wrescale, hrescale, scanline):

        # video
        self.wrescale : int = wrescale
        self.hrescale : int = hrescale
        self.scanline : float = scanline
        pygame.init()
        pygame.fastevent.init()
        pygame.display.set_caption('pymsx')

        # keyboard
        self.keyboard_row: int = 0
        self.keys_pressed: dict = {}
        self.kb_init()

    def scrn_resize(self, w : int, h : int):
        wrescale, hrescale = int(self.wrescale), int(self.hrescale)
        self.screen = pygame.display.set_mode((w*wrescale, h*hrescale), pygame.RESIZABLE)
        self.arr_rescaled = pygame.surfarray.array2d(self.screen)
        arr_original = self.arr_rescaled[:w, :h]
        return arr_original

    def scrn_draw(self, arr) -> None:

        wrescale, hrescale = int(self.wrescale), int(self.hrescale)

        # create rescaled array
        if wrescale > 1 or hrescale > 1:
            arr = arr.copy()
            for xi in range(wrescale):
                for yi in range(hrescale):
                    self.arr_rescaled[xi::wrescale, yi::hrescale] = arr
            pygame.surfarray.blit_array(self.screen, self.arr_rescaled)
        else:
            pygame.surfarray.blit_array(self.screen, arr)
        
        # add scanline effect
        if self.scanline > 0:
            pixels = pygame.surfarray.array3d(self.screen)
            for idx in range(hrescale - 1):
                pixels[:,idx::(hrescale+1), :] = pixels[:,idx::(hrescale+1),:] * (1 - self.scanline)
            pygame.surfarray.blit_array(self.screen, pixels)

        pygame.display.flip()

    def kb_init(self):
        self.keys = [ None ] * 16
        self.keys[0] = ( pygame.K_0, pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5, pygame.K_6, pygame.K_7 )
        self.keys[1] = ( pygame.K_8, pygame.K_9, pygame.K_MINUS, pygame.K_PLUS, pygame.K_BACKSLASH, pygame.K_LEFTBRACKET, pygame.K_RIGHTBRACKET, pygame.K_SEMICOLON )
        self.keys[2] = ( pygame.K_QUOTE, pygame.K_BACKQUOTE, pygame.K_COMMA, pygame.K_PERIOD, pygame.K_SLASH, None, pygame.K_a, pygame.K_b )
        self.keys[3] = ( pygame.K_c, pygame.K_d, pygame.K_e, pygame.K_f, pygame.K_g, pygame.K_h, pygame.K_i, pygame.K_j )
        self.keys[4] = ( pygame.K_k, pygame.K_l, pygame.K_m, pygame.K_n, pygame.K_o, pygame.K_p, pygame.K_q, pygame.K_r )
        self.keys[5] = ( pygame.K_s, pygame.K_t, pygame.K_u, pygame.K_v, pygame.K_w, pygame.K_x, pygame.K_y, pygame.K_z )
        self.keys[6] = ( pygame.K_LSHIFT, pygame.K_LCTRL, None, pygame.K_CAPSLOCK, None, pygame.K_F1, pygame.K_F2, pygame.K_F3 )
        self.keys[7] = ( pygame.K_F4, pygame.K_F5, pygame.K_ESCAPE, pygame.K_TAB, None, pygame.K_BACKSPACE, None, pygame.K_RETURN )
        self.keys[8] = ( pygame.K_SPACE, None, None, None, pygame.K_LEFT, pygame.K_UP, pygame.K_DOWN, pygame.K_RIGHT )

    def kb_poll(self) -> None:
        events = pygame.fastevent.get()

        for event in events:
            if event.type == pygame.QUIT:
                self.stop_flag = True
                break

            if event.type == pygame.KEYDOWN: 
                if event.key == pygame.K_RETURN:
                    print('MARKER', file=sys.stderr, flush=True)

                self.keys_pressed[event.key] = True

            elif event.type == pygame.KEYUP:
                self.keys_pressed[event.key] = False

            else:
                print(event)

    def kb_read(self) -> int:
        cur_row = self.keys[self.keyboard_row]
        if not cur_row:
            # print('kb fail', self.keyboard_row)
            return 255

        bits = bit_nr = 0

        for key in cur_row:
            if key and key in self.keys_pressed and self.keys_pressed[key]:
                bits |= 1 << bit_nr
            bit_nr += 1

        return bits ^ 0xff

    def kb_set_row(self, v):
        self.keyboard_row = v