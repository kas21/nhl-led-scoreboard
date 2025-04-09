from PIL import Image, ImageFont, ImageDraw
from utils import get_file
from renderer.screen_config import screenConfig
from nhl_api.player import PlayerStats
from renderer.logos import LogoRenderer
import debug
import traceback

class OviTrackerRenderer:
    def __init__(self, data, matrix, sleepEvent):
        self.data = data
        self.teams_info = data.teams_info
        self.matrix = matrix
        self.sleepEvent = sleepEvent
        self.layout = self.get_layout()

        self.team_colors = data.config.team_colors
        
        # Gretzky's career goals record
        #self.GRETZKY_GOALS = 894
        self.OVI_ID = "8471214"  # Ovechkin's NHL ID
        self.team_id = 15 # Capitals

        rows = self.matrix.height
        cols = self.matrix.width
        self.img = get_file(f'assets/images/{cols}x{rows}_ovi_gsoat_bg.png')

        self.title_text = "NHL GOAL LEADER"
        self.name_text = "ALEX OVECHKIN"
        if cols > 64:
            self.title_text = "NHL ALL-TIME GOALS LEADER"

        
        
    def get_layout(self):
        """Get the layout for Ovechkin goal tracker display"""
        layout = self.data.config.config.layout.get_board_layout('ovi_tracker')
        return layout

    def render(self):
        """Render Ovechkin's goal tracking statistics"""
        try:
            # Get Ovi's stats using the PlayerStats class
            stats = PlayerStats.from_api(self.OVI_ID)
            if not stats:
                debug.error("Could not get stats for Ovechkin")
                return

            team_id = self.team_id
            team = self.teams_info[team_id]
            team_colors = self.data.config.team_colors
            bg_color = team_colors.color("{}.primary".format(team_id))
            txt_color = team_colors.color("{}.text".format(team_id))

            # Render logo
            logo_renderer = LogoRenderer(
                self.matrix,
                self.data.config,
                self.layout.logo,
                team.details.abbrev,
                'ovi_tracker',
                img=self.img
            )

            # Clear the matrix
            self.matrix.clear()
            
            logo_renderer.render()
            # Draw stats
            current_y = 2

            self.matrix.draw_text_layout(
                self.layout.title,
                self.title_text
            )
 
            self.matrix.draw_text_layout(
                self.layout.name,
                f"ALEX OVECHKIN",
                fillColor=(txt_color['r'], txt_color['g'], txt_color['b']),
                backgroundColor=(bg_color['r'], bg_color['g'], bg_color['b'])
            ) 
            self.matrix.draw_text_layout(
                self.layout.career_goals,
                f"{stats.career_goals}"
            )

            # Render to matrix
            self.matrix.render()
            self.sleepEvent.wait(8)
        except Exception as e:
            debug.error(f"Error rendering Ovi tracker: {str(e)}\n{traceback.format_exc()}") 