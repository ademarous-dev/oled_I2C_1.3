# sh1106.py - driver for 1.3" I2C OLED screens (128x64)
# You don't need to read or edit this file. Just copy it to the board.

import framebuf


class SH1106(framebuf.FrameBuffer):
    def __init__(self, i2c, addr=0x3C, width=128, height=64):
        self.i2c = i2c
        self.addr = addr
        self.width = width
        self.height = height
        self.pages = height // 8
        self.buffer = bytearray(self.pages * width)
        self._view = memoryview(self.buffer)
        self._cmd = bytearray(2)
        self._pack = [b"\x40", None]
        super().__init__(self.buffer, width, height, framebuf.MONO_VLSB)
        for c in (0xAE, 0xD5, 0x80, 0xA8, height - 1, 0xD3, 0x00, 0x40,
                  0xAD, 0x8B, 0xA1, 0xC8, 0xDA, 0x12, 0x81, 0xFF,
                  0xD9, 0x1F, 0xDB, 0x40, 0xA4, 0xA6, 0xAF):
            self._send(c)
        self.fill(0)
        self.show()

    def _send(self, c):
        self._cmd[0] = 0x80
        self._cmd[1] = c
        self.i2c.writeto(self.addr, self._cmd)

    def show(self):
        w = self.width
        for p in range(self.pages):
            self._send(0xB0 | p)
            self._send(0x02)
            self._send(0x10)
            self._pack[1] = self._view[p * w:(p + 1) * w]
            self.i2c.writevto(self.addr, self._pack)