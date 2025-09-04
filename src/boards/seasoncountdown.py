import driver
from renderer.matrix import Matrix

if driver.is_hardware():
    from rgbmatrix import graphics
else:
    from RGBMatrixEmulator import graphics

from PIL import ImageFont, Image
from utils import center_text
from datetime import datetime, date
import debug
from time import sleep
from utils import get_file

PATH = 'assets/logos'
LOGO_LINK = "https://www-league.nhlstatic.com/images/logos/league-dark/133-flat.svg"

class SeasonCountdown:
    def __init__(self, data, matrix: Matrix, sleepEvent):
        
        self.data = data
        self.teams_info = data.teams_info
        self.matrix = matrix
        self.sleepEvent = sleepEvent
        self.layout = self.get_layout()

        self.team_colors = data.config.team_colors
        self.font_large_2 = data.config.layout.font_large_2
        self.font_large = data.config.layout.font_large
        self.font = data.config.layout.font

        self.season_start = datetime.strptime(self.data.status.next_season_start(), '%Y-%m-%d').date()
        self.days_until_season = (self.season_start - date.today()).days
        self.scroll_pos = self.matrix.width
        
        # Set up season text
        self.current_year = date.today().year
        self.next_year = self.current_year + 1
    
        self.nextseason="{0}-{1}".format(self.current_year,self.next_year)
        self.nextseason_short="NHL {0}-{1}".format(str(self.current_year)[-2:],str(self.next_year)[-2:])

        # Holidays
        self.holidays = [
            {"name": "Halloween", "month": 10, "day": 31, "image": "pumpkin"},
            {"name": "Christmas", "month": 12, "day": 25, "image": "christmas_tree"}
        ]



    def get_layout(self):
        """Get the layout for SeasonCountdown"""
        layout = self.data.config.config.layout.get_board_layout('season_countdown')
        return layout
    
    def draw(self):
        
        for h in self.holidays:
            hdate = date(self.current_year, h["month"], h["day"])
            print(f"Holiday: {h["name"]} - {str(hdate)}")

            days_until = (hdate - date.today()).days
            
            # season starts today
            if days_until == 0:
                self.season_start_today()

            #still counting down to season
            elif days_until > 0:
                self.season_countdown(days_until, h["name"], h["image"])

        debug.info("NHL Countdown Launched")

        # for testing purposes
        #self.days_until_season = 0
        #self.days_until_season = 2
        #self.days_until_season = -1

        debug.info(str(self.days_until_season) + " days to NHL Season")

        # season starts today
        if self.days_until_season == 0:
            self.season_start_today()

        #still counting down to season
        elif self.days_until_season > 0:
            self.season_countdown(self.days_until_season, self.nextseason_short, "nhl_logo")

        # dont show anything if season has started
        # could show someething in the future if wanted
        # like season day count, count down to playoffs, etc.

  
    
    def season_start_today(self) :
        #  it's just like Christmas!
        self.matrix.clear()

        rows = self.matrix.height
        cols = self.matrix.width

        nhl_logo = Image.open(get_file(f'assets/images/{cols}x{rows}_nhl_logo.png'))
        black_gradiant = Image.open(get_file(f'assets/images/{cols}x{rows}_scoreboard_center_gradient.png'))

        self.matrix.draw_image_layout(self.layout.logo, nhl_logo)
        self.matrix.draw_image_layout(self.layout.gradient, black_gradiant)
        
        debug.info("Counting down to {0}".format(self.nextseason_short))

        self.matrix.render()
        self.sleepEvent.wait(0.5)

        #draw season
        self.matrix.draw_text_layout(
            self.layout.season_today_text, 
            self.nextseason_short, 
            fillColor=(0,0,0),
            backgroundColor=(155,155,155)
        )
        
        self.matrix.render()
        self.sleepEvent.wait(1)

        #draw bottom text
        self.matrix.draw_text_layout(
            self.layout.starts_text, 
            "STARTS TODAY",
            fillColor=(255,165,0)
        )
            
        self.matrix.render()
        self.sleepEvent.wait(1)

        #draw bottom text  
        self.matrix.draw_text_layout(
            self.layout.lets_go_text, 
            "LETS GO",
            fillColor=(255,165,0)

        )

        self.matrix.render()
        self.sleepEvent.wait(15)

    def season_countdown(self, daysUntil, dateName, imageName) :
        
        self.matrix.clear()

        rows = self.matrix.height
        cols = self.matrix.width

        nhl_logo = Image.open(get_file(f'assets/images/{cols}x{rows}_{imageName}.png'))
        black_gradiant = Image.open(get_file(f'assets/images/{cols}x{rows}_scoreboard_center_gradient.png'))

        self.matrix.draw_image_layout(self.layout.logo, nhl_logo)
        self.matrix.draw_image_layout(self.layout.gradient, black_gradiant)
        
        debug.info("Counting down to {0}".format(self.nextseason_short))

        self.matrix.render()
        self.sleepEvent.wait(0.5)

        #draw days
        self.matrix.draw_text_layout(self.layout.count_text,str(daysUntil), fillColor=(255,165,0))
        
        self.matrix.render()
        self.sleepEvent.wait(1)

        #draw bottom text
        self.matrix.draw_text_layout(
            self.layout.until_text, 
            "DAYS TIL", 
            fillColor=(255,165,0)
        )

        self.matrix.render()
        self.sleepEvent.wait(1)

        #draw bottom text  
        self.matrix.draw_text_layout(
            self.layout.season_text, 
            dateName, 
            fillColor=(0,0,0),
            backgroundColor=(155,155,155)
        )

        self.matrix.render()
        self.sleepEvent.wait(15)
