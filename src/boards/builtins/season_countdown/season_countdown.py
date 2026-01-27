"""
Season Countdown board module implementation.
"""
import logging
from datetime import date, datetime

from PIL import Image

from boards.base_board import BoardBase

from . import __board_name__, __description__, __version__

debug = logging.getLogger("scoreboard")

class SeasonCountdownBoard(BoardBase):
    """
    Season Countdown Board.  Counts down the days until the NHL Season.
    """


    def __init__(self, data, matrix, sleepEvent):
        super().__init__(data, matrix, sleepEvent)

        # Board metadata from package
        self.board_name = __board_name__
        self.board_version = __version__
        self.board_description = __description__

        # Get configuration values with defaults
        self.text_color = tuple(self.board_config.get("text_color", [255, 165, 0]))
        self.season_bg_color = tuple(self.board_config.get("season_bg_color", [155, 155, 155]))
        self.until_text = self.board_config.get("until_text", "DAYS TIL")
        self.display_seconds = self.board_config.get("display_seconds", 5)

        # Access standard application config
        self.font = data.config.layout.font
        self.font_large = data.config.layout.font_large

        # Set up season text (static parts only)
        self.season_start = datetime.strptime(self.data.status.next_season_start(), '%Y-%m-%d').date()

        # Date-dependent values will be computed fresh in render()
        self.days_until_season = None
        self.nextseason = None
        self.nextseason_short = None

    def render(self):
        # Compute fresh date-dependent values
        today = date.today()
        self.days_until_season = (self.season_start - today).days

        # Todo: make this more robust.  If we want users to be able to change the text
        # If 1 day until season, change "DAYS" to "DAY"
        if self.days_until_season == 1:
            self.until_text = "DAY TIL"


        current_year = today.year
        next_year = current_year + 1
        self.nextseason = "{0}-{1}".format(current_year, next_year)
        self.nextseason_short = "NHL {0}-{1}".format(str(current_year)[-2:], str(next_year)[-2:])

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
            self.season_countdown()

        # dont show anything if season has started
        # could show someething in the future if wanted
        # like season day count, count down to playoffs, etc.



    def season_start_today(self) :
        #  it's just like Christmas!
        # Get the layout for this plugin
        layout = self.get_board_layout('season_countdown')

        self.matrix.clear()

        rows = self.matrix.height
        cols = self.matrix.width

        try:
            nhl_logo = Image.open(f'assets/images/{cols}x{rows}_nhl_logo.png').convert("RGBA")
            black_gradiant = Image.open(f'assets/images/{cols}x{rows}_scoreboard_center_gradient.png')
        except Exception:
            debug.error("Could not open image")

        self.matrix.draw_image_layout(layout.logo, nhl_logo)
        self.matrix.draw_image_layout(layout.gradient, black_gradiant)

        debug.info("Counting down to {0}".format(self.nextseason_short))

        self.matrix.render()
        self.sleepEvent.wait(0.5)

        #draw season
        self.matrix.draw_text_layout(
            layout.season_today_text,
            self.nextseason_short,
            fillColor=(0,0,0),
            backgroundColor=(155,155,155)
        )

        self.matrix.render()
        self.sleepEvent.wait(1)

        #draw bottom text
        self.matrix.draw_text_layout(
            layout.starts_text,
            "STARTS TODAY",
            fillColor=(255,165,0)
        )

        self.matrix.render()
        self.sleepEvent.wait(1)

        #draw bottom text
        self.matrix.draw_text_layout(
            layout.lets_go_text,
            "LETS GO",
            fillColor=(255,165,0)

        )

        self.matrix.render()
        self.sleepEvent.wait(self.display_seconds)

    def season_countdown(self) :

        # Get the layout for this plugin
        layout = self.get_board_layout('season_countdown')

        self.matrix.clear()

        rows = self.matrix.height
        cols = self.matrix.width

        try:
            nhl_logo = Image.open(f'assets/images/{cols}x{rows}_nhl_logo.png').convert("RGBA")
            black_gradiant = Image.open(f'assets/images/{cols}x{rows}_scoreboard_center_gradient.png')
        except Exception:
            debug.error("Could not open image")

        self.matrix.draw_image_layout(layout.logo, nhl_logo)
        self.matrix.draw_image_layout(layout.gradient, black_gradiant)

        debug.info("Counting down to {0}".format(self.nextseason_short))

        self.matrix.render()
        self.sleepEvent.wait(0.5)

        #draw days
        self.matrix.draw_text_layout(layout.count_text,str(self.days_until_season), fillColor=(255,165,0))

        self.matrix.render()
        self.sleepEvent.wait(1)

        #draw bottom text
        self.matrix.draw_text_layout(
            layout.until_text,
            self.until_text,
            fillColor=self.text_color
        )

        self.matrix.render()
        self.sleepEvent.wait(1)

        #draw bottom text
        self.matrix.draw_text_layout(
            layout.season_text,
            self.nextseason_short,
            fillColor=(0,0,0),
            backgroundColor=(self.season_bg_color)
        )

        self.matrix.render()
        self.sleepEvent.wait(self.display_seconds)
