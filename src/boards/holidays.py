import driver

if driver.is_hardware():
    from rgbmatrix import graphics
else:
    from RGBMatrixEmulator import graphics

from PIL import ImageFont, Image
from utils import center_text
import datetime
import debug
from time import sleep
from utils import get_file
from renderer.matrix import Matrix
from renderer.logos import LogoRenderer


class Holidays:
    def __init__(self, data, matrix: Matrix, sleepEvent):
        self.data = data
        self.matrix = matrix
        self.sleepEvent = sleepEvent
        self.sleepEvent.clear()
        self.font = data.config.layout.font
        self.font.large = data.config.layout.font_large_2
        self.font.scroll = data.config.layout.font_xmas
        self.days_to_xmas = 0
        self.scroll_pos = self.matrix.width
        self.img = get_file(f'assets/images/{self.matrix.width}x{self.matrix.height}_HappyMothersDay.png')
        self.img = Image.open(self.img)

    def render(self):
        self.matrix.clear()

        today = datetime.datetime.now()
        #if today is Mother's Day, draw a heart
        if today.month == 5 and today.day == 11:
            self.matrix.draw_image(
                (0, 0),
                self.img,
                align="left"
            )

        if today.month == 5 and (today.day == 31 or today.day==30):
            debug.info("Its a holiday")
            img = get_file(f'assets/images/{self.matrix.width}x{self.matrix.height}_CongratsGrad.png')
            img = Image.open(img)
            self.matrix.draw_image(
                (0, 0),
                img,
                align="left"
            )

            self.matrix.render()
            self.sleepEvent.wait(10)

            img = get_file(f'assets/images/{self.matrix.width}x{self.matrix.height}_CCUSoon.png')
            img = Image.open(img)
            self.matrix.draw_image(
                (0, 0),
                img,
                align="left"
            )

            self.matrix.render()
            self.sleepEvent.wait(10)
        
        
   