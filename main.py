# main.py - moving square on a 1.3" OLED screen with ESP32
# Files needed on the board: main.py + sh1106.py + microtween.py

import time                          # for small pauses
from machine import I2C, Pin         # tools to talk to the screen
from Sh1106 import SH1106            # screen driver (file sh1106.py)
from oled_I2C import Animator      # animation tool (file microtween.py)

# 1) Start the screen (SDA wire = pin 21, SCL wire = pin 22)
i2c = I2C(0, sda=Pin(21), scl=Pin(22))
oled = SH1106(i2c)

# 2) Define the animations: name, from, to, seconds, style
a = Animator()
a.go("x", 0, 110, 1.5, "bounce")     # moves left and right like a ball
a.go("y", 12, 46, 0.9, "smooth")     # moves up and down smoothly
a.go("size", 6, 16, 0.7, "elastic")  # grows and shrinks like a spring

# 3) Main loop (runs forever)
while True:
    a.update()                       # update all animations
    oled.fill(0)                     # clear the screen (0 = black)
    oled.text("Hello", 0, 0, 1)      # write text at the top-left corner
    oled.fill_rect(a.get("x"), a.get("y"), a.get("size"), a.get("size"), 1)  # draw the square
    oled.show()                      # display the drawing on the screen
    time.sleep_ms(15)                # wait 15 ms (about 60 frames per second)