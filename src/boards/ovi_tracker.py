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
        self.font = data.config.layout.font
        
        # Gretzky's career goals record
        self.GRETZKY_GOALS = 894
        self.OVI_ID = "8471214"  # Ovechkin's NHL ID
        self.team_id = 15 # Capitals
        
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
                img='assets/images/GR8_CHASE.png'
            )

            # Clear the matrix
            self.matrix.clear()

            gradient = Image.open(get_file('assets/images/64x32_scoreboard_center_gradient.png'))

            #   For 128x64 use the bigger gradient image.
            if self.matrix.height == 64:
                gradient = Image.open(get_file('assets/images/128x64_scoreboard_center_gradient.png'))
            
            
            logo_renderer.render()
            self.matrix.draw_image((25,0), gradient, align="center")

            # Draw text over rectangles
            self.matrix.draw_text(
                (1, 1), 
                "GR8 CHASE", 
                self.font,
                fill=(txt_color['r'], txt_color['g'], txt_color['b']),
                backgroundColor=(bg_color['r'], bg_color['g'], bg_color['b'])
                )
            
            # Draw stats
            self.matrix.draw_text(
                (3, 8),
                f"Career:",
                font=self.font
            ) 
            self.matrix.draw_text(
                (3, 14),
                f"{stats.career_goals}",
                font=self.font
            )

            # Calculate and draw goals needed
            goals_needed = self.GRETZKY_GOALS - stats.career_goals + 1
            self.matrix.draw_text(
                (3, 22),
                f"{goals_needed} To Go!!!",
                font=self.font
            )

            # Render to matrix
            self.matrix.render()
            self.sleepEvent.wait(15)
        except Exception as e:
            debug.error(f"Error rendering Ovi tracker: {str(e)}\n{traceback.format_exc()}") 