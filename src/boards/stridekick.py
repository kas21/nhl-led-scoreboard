from PIL import Image, ImageFont, ImageDraw
from utils import get_file
from renderer.screen_config import screenConfig
from nhl_api.player import PlayerStats
from renderer.logos import LogoRenderer
import debug
import traceback
import json
import os
import time

class StrideKickRenderer:
    def __init__(self, data, matrix, sleepEvent):
        self.data = data
        self.teams_info = data.teams_info
        self.matrix = matrix
        self.sleepEvent = sleepEvent
        #self.layout = self.get_layout()

        # Set font size based on matrix width
        if self.matrix.width >= 128:
            self.font = data.config.layout.font_large
            self.font_height = 13
        else:
            self.font = data.config.layout.font
            self.font_height = 7

        # Scrolling state
        self.scroll_positions = {}
        self.scroll_delay = 0.1  # seconds between scroll updates
        self.scroll_pause = 2.0  # seconds to pause before starting scroll
        self.scroll_cycle_pause = 1.0  # seconds to pause at end of scroll cycle

    def get_layout(self):
        return screenConfig.get_layout("stridekick")

    def load_stridekick_data(self):
        try:
            data_path = os.path.join("assets", "stridekick_data.json")
            with open(data_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            debug.error(f"Failed to load stridekick data: {e}")
            return []

    def draw_leaderboard(self, records, width, img_height, scroll_offset=0):
        image = Image.new('RGB', (width, img_height))
        draw = ImageDraw.Draw(image)

        # Calculate max scroll offset based on longest name
        max_scroll_offset = max(draw.textlength(record["name"], font=self.font) for record in records) + 40

        # Create gradient background
        for y in range(img_height):
            # Calculate gradient from dark blue to lighter blue
            r = int(0 + (y / img_height) * 20)
            g = int(0 + (y / img_height) * 40)
            b = int(50 + (y / img_height) * 50)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        row_pos = 0
        row_height = self.font_height
        top = row_height - 1

        # Draw header with white text
        draw.text((1, 0), "WALK THIS WAY", font=self.font, fill=(255, 255, 255))
        row_pos += row_height

        # Draw each record
        for record in records:
            place = str(record["place"])
            name = record["name"]
            steps = str(record["steps"])

            # Draw place with gold color for top 3
            if int(place) <= 3:
                place_color = (255, 215, 0)  # Gold
            else:
                place_color = (200, 200, 200)  # Light gray
            
            # Draw name with white text
            name_color = (255, 255, 255)
            
            # Draw steps with green text
            steps_color = (0, 255, 0)

            # Draw place
            place_width = draw.textlength(f"{place}.", font=self.font)
            draw.text((1, row_pos), f"{place}.", font=self.font, fill=place_color)
            
            # Draw steps (right-aligned)
            steps_width = draw.textlength(steps, font=self.font)
            steps_x = width - steps_width - 2  # 2 pixels padding from right edge
            draw.text((steps_x, row_pos), steps, font=self.font, fill=steps_color)
            
            # Calculate available space for name
            name_start_x = 10 + place_width
            name_end_x = steps_x - 5  # 5 pixels padding before steps
            available_width = name_end_x - name_start_x
            
            # Draw name with scrolling
            name_width = draw.textlength(name, font=self.font)
            
            if name_width > available_width:
                # Calculate scroll position for this name
                scroll_pos = scroll_offset % (name_width + 40)
                
                # Calculate visible portion of name
                if scroll_pos < 40:  # Initial pause
                    # Show truncated name that fits
                    visible_name = name
                    while draw.textlength(visible_name, font=self.font) > available_width:
                        visible_name = visible_name[:-1]
                    name_x = name_start_x
                else:
                    # Scroll the name
                    scroll_pos -= 40  # Account for initial pause
                    name_x = name_start_x - scroll_pos
                    visible_name = name
                    
                    # If we're scrolling past the start, truncate the beginning
                    if name_x < name_start_x:
                        # Find how many characters to skip at the start
                        skip_chars = 0
                        while name_x < name_start_x and skip_chars < len(name):
                            name_x += draw.textlength(name[skip_chars], font=self.font)
                            skip_chars += 1
                        visible_name = name[skip_chars:]
                    
                    # Truncate the end if it would overlap steps
                    while draw.textlength(visible_name, font=self.font) > (name_end_x - name_x):
                        visible_name = visible_name[:-1]
            else:
                visible_name = name
                name_x = name_start_x
            
            draw.text((name_x, row_pos), visible_name, font=self.font, fill=name_color)
            
            row_pos += row_height

        return image, max_scroll_offset

    def render(self):
        try:
            records = self.load_stridekick_data()
            if not records:
                debug.error("No stridekick data available")
                return

            # Calculate image height based on number of records + header
            img_height = (len(records) + 1) * self.font_height
            
            # Initial position
            i = 0
            scroll_offset = 0
            scroll_start_time = time.time() + self.scroll_pause

            while not self.sleepEvent.is_set():
                current_time = time.time()
                
                # Create the leaderboard image with current scroll position
                image, max_scroll_offset = self.draw_leaderboard(records, self.matrix.width, img_height, scroll_offset)
                
                # Draw the image at current vertical position
                self.matrix.draw_image((0, i), image)
                self.matrix.render()
                if i == 0:
                    self.sleepEvent.wait(1)

                # Handle vertical scrolling
                if i > -(img_height - self.matrix.height):
                    i -= 1
                    self.sleepEvent.wait(0.2)
                else:
                    # Reset vertical position and scroll offset when we reach the bottom
                    i = 0
                    scroll_offset = 0
                    scroll_start_time = current_time + self.scroll_pause
                    self.sleepEvent.wait(5)
                    return  # Exit after one complete cycle

                # Update horizontal scroll position only after initial delay
                if current_time >= scroll_start_time:
                    # Check if we need to pause at end of scroll cycle
                    if scroll_offset >= max_scroll_offset:
                        scroll_offset = 0
                        scroll_start_time = current_time + self.scroll_pause
                        self.sleepEvent.wait(self.scroll_cycle_pause)
                    else:
                        scroll_offset += 1
                        self.sleepEvent.wait(self.scroll_delay)

        except Exception as e:
            debug.error(f"Error rendering stridekick board: {e}")
            traceback.print_exc()
        