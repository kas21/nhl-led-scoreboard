"""
Stats Banner - Animated lower banner for displaying game stats on live scoreboard.

Slides up from the bottom, shows stats (shots, hits, faceoff %) with split bars,
then slides back down.
"""

import logging
from typing import Tuple, Optional, List, Callable
from PIL import Image

from renderer.charts import ChartRenderer, ease_out_quad, is_dark_color, lighten_color

debug = logging.getLogger("scoreboard")

# Type aliases
Color = Tuple[int, int, int]


class StatsBanner:
    """
    Animated stats banner that slides up from the bottom of the display.

    Shows game statistics (shots, hits, faceoff %) using split bar charts
    matching the game_stats board format.
    """

    def __init__(self, matrix, team_colors, font):
        """
        Initialize the stats banner.

        Args:
            matrix: Matrix instance for rendering
            team_colors: Team colors configuration
            font: Font to use for labels
        """
        self.matrix = matrix
        self.team_colors = team_colors
        self.font = font
        self.chart = ChartRenderer(matrix)

        # Banner dimensions based on display size
        self.display_width = matrix.width
        self.display_height = matrix.height

        # Banner height needs to fit: gradient fade + label row + bar
        # For 128x64: ~18px, for 64x32: ~12px
        if self.display_height >= 64:
            self.banner_height = 18
            self.bar_width = 90
            self.bar_height = 6
        else:
            self.banner_height = 12
            self.bar_width = 50
            self.bar_height = 4

    def show_stats_banner(
        self,
        stats,
        home_team_id: int,
        away_team_id: int,
        base_image: Image.Image,
        sleep_func: Callable[[float], None],
        is_interrupted: Callable[[], bool],
        stat_duration: float = 2.0,
        animation_duration: float = 0.3,
        animation_frames: int = 10,
        categories: Optional[List[str]] = None
    ):
        """
        Animate the full stats banner sequence.

        1. Slide up from bottom
        2. Show each stat with pause
        3. Slide down and disappear

        Args:
            stats: GameStoryStats object with game statistics
            home_team_id: NHL team ID for home team
            away_team_id: NHL team ID for away team
            base_image: Current scoreboard state to overlay on
            sleep_func: Function to call for sleeping (e.g., sleepEvent.wait)
            is_interrupted: Function that returns True if animation should stop
            stat_duration: Seconds to display each stat
            animation_duration: Seconds for slide animation
            animation_frames: Number of frames for slide animation
            categories: List of stat categories to show (default: shots, hits, faceoff)
        """
        if categories is None:
            categories = ['shots', 'hits', 'faceoff']

        # Get team colors
        home_color = self._get_team_color(home_team_id)
        away_color = self._get_team_color(away_team_id)

        # Get outline/text colors for dark teams
        home_outline = self._get_outline_for_color(home_color)
        away_outline = self._get_outline_for_color(away_color)
        home_text = self._get_readable_text_color(home_color)
        away_text = self._get_readable_text_color(away_color)

        # Build stat data for each category
        stat_data = []
        for cat in categories:
            data = self._get_stat_data(stats, cat)
            if data:
                stat_data.append(data)

        if not stat_data:
            debug.warning("StatsBanner: No stat data available")
            return

        # Calculate the Y position for the banner (starts off-screen)
        start_y = self.display_height  # Below screen
        end_y = self.display_height - self.banner_height  # Final position

        # Phase 1: Slide up
        debug.debug("StatsBanner: Sliding up")
        self._animate_slide(
            base_image, start_y, end_y,
            stat_data[0], home_color, away_color,
            home_outline, away_outline, home_text, away_text,
            animation_duration, animation_frames,
            sleep_func, is_interrupted
        )

        if is_interrupted():
            return

        # Phase 2: Show each stat with animated bar
        for i, data in enumerate(stat_data):
            debug.debug(f"StatsBanner: Showing {data['label']}")

            # Animate the stat bar (it handles its own render loop)
            self._animate_stat(
                base_image, end_y,
                data, home_color, away_color,
                home_outline, away_outline, home_text, away_text,
                sleep_func
            )

            # Wait for stat duration after animation completes
            sleep_func(stat_duration)

            if is_interrupted():
                return

        # Phase 3: Slide down
        debug.debug("StatsBanner: Sliding down")
        self._animate_slide(
            base_image, end_y, start_y,
            stat_data[-1], home_color, away_color,
            home_outline, away_outline, home_text, away_text,
            animation_duration, animation_frames,
            sleep_func, is_interrupted
        )

    def _animate_slide(
        self,
        base_image: Image.Image,
        start_y: int,
        end_y: int,
        stat_data: dict,
        home_color: Color,
        away_color: Color,
        home_outline: Optional[Color],
        away_outline: Optional[Color],
        home_text: Color,
        away_text: Color,
        duration: float,
        frames: int,
        sleep_func: Callable[[float], None],
        is_interrupted: Callable[[], bool]
    ):
        """Animate the banner sliding between two Y positions."""
        frame_delay = duration / frames

        for frame in range(frames + 1):
            if is_interrupted():
                return

            # Calculate current Y using easing
            progress = ease_out_quad(frame / frames)
            current_y = int(start_y + (end_y - start_y) * progress)

            self._draw_frame(
                base_image, current_y,
                stat_data, home_color, away_color,
                home_outline, away_outline, home_text, away_text
            )

            sleep_func(frame_delay)

    def _draw_frame(
        self,
        base_image: Image.Image,
        banner_y: int,
        stat_data: dict,
        home_color: Color,
        away_color: Color,
        home_outline: Optional[Color],
        away_outline: Optional[Color],
        home_text: Color,
        away_text: Color
    ):
        """Draw a single frame with the banner at the given Y position."""
        # Restore base scoreboard image
        self.matrix.image.paste(base_image)

        # Draw gradient background
        self._draw_banner_background(banner_y)

        # Draw the stat content
        self._draw_stat_content(
            banner_y, stat_data,
            home_color, away_color,
            home_outline, away_outline,
            home_text, away_text
        )

        self.matrix.render()

    def _draw_banner_background(self, y_pos: int):
        """Draw gradient black background for the banner."""
        # Gradient from transparent to solid black (top to bottom)
        gradient_rows = min(6, self.banner_height // 3)

        for row in range(self.banner_height):
            row_y = y_pos + row
            if row_y < 0 or row_y >= self.display_height:
                continue

            # Calculate alpha for gradient effect
            if row < gradient_rows:
                # Gradient zone - fade from transparent to black
                alpha = int(180 * (row / gradient_rows))
            else:
                # Solid black zone
                alpha = 180

            # Draw a semi-transparent black row
            # Since we can't do true alpha blending, use darker values
            gray_level = 255 - alpha  # Inverted for blending effect

            # Draw black rectangle (we paste base image first, so this overlays)
            for x in range(self.display_width):
                # Get current pixel and darken it
                try:
                    current = self.matrix.image.getpixel((x, row_y))
                    if isinstance(current, tuple) and len(current) >= 3:
                        # Blend toward black based on alpha
                        blend = alpha / 255
                        new_r = int(current[0] * (1 - blend))
                        new_g = int(current[1] * (1 - blend))
                        new_b = int(current[2] * (1 - blend))
                        self.matrix.image.putpixel((x, row_y), (new_r, new_g, new_b))
                except (IndexError, TypeError):
                    pass

    def _draw_stat_content(
        self,
        banner_y: int,
        stat_data: dict,
        home_color: Color,
        away_color: Color,
        home_outline: Optional[Color],
        away_outline: Optional[Color],
        home_text: Color,
        away_text: Color
    ):
        """Draw the stat content (label and split bar) statically - used during slide."""
        # Calculate bar position (centered horizontally)
        bar_x = (self.display_width - self.bar_width) // 2

        # Y position for the split bar (accounting for gradient fade at top)
        content_y = banner_y + 4  # Leave some space for gradient

        # Only draw if content is visible
        if content_y >= self.display_height:
            return

        # Draw the split bar with labels (static, no animation)
        self.chart.draw_split_bar(
            position=(bar_x, content_y),
            left_pct=stat_data['away_pct'],
            width=self.bar_width,
            height=self.bar_height,
            left_color=away_color,
            right_color=home_color,
            divider_color=(255, 255, 255),
            divider_width=1,
            title=stat_data['label'],
            left_label=stat_data['away_label'],
            right_label=stat_data['home_label'],
            font=self.font,
            title_color=(255, 255, 255),
            left_label_color=away_text,
            right_label_color=home_text,
            left_outline_color=away_outline,
            right_outline_color=home_outline
        )

    def _animate_stat(
        self,
        base_image: Image.Image,
        banner_y: int,
        stat_data: dict,
        home_color: Color,
        away_color: Color,
        home_outline: Optional[Color],
        away_outline: Optional[Color],
        home_text: Color,
        away_text: Color,
        sleep_func: Callable[[float], None]
    ):
        """Animate a stat's split bar with the fill animation."""
        # Calculate bar position (centered horizontally)
        bar_x = (self.display_width - self.bar_width) // 2

        # Y position for the split bar (accounting for gradient fade at top)
        content_y = banner_y + 4  # Leave some space for gradient

        # Only animate if content is visible
        if content_y >= self.display_height:
            return

        # Create pre_draw callback that restores background and gradient
        def pre_draw():
            self.matrix.image.paste(base_image)
            self._draw_banner_background(banner_y)

        # Animate the split bar (handles its own render loop)
        self.chart.animate_split_bar(
            position=(bar_x, content_y),
            left_pct=stat_data['away_pct'],
            render_callback=self.matrix.render,
            clear_callback=self.matrix.clear,
            sleep_func=sleep_func,
            width=self.bar_width,
            height=self.bar_height,
            left_color=away_color,
            right_color=home_color,
            divider_color=(255, 255, 255),
            divider_width=1,
            duration=0.5,
            frames=15,
            animation="fill",
            pre_draw=pre_draw,
            title=stat_data['label'],
            left_label=stat_data['away_label'],
            right_label=stat_data['home_label'],
            font=self.font,
            title_color=(255, 255, 255),
            left_label_color=away_text,
            right_label_color=home_text,
            left_outline_color=away_outline,
            right_outline_color=home_outline
        )

    def _get_stat_data(self, stats, category: str) -> Optional[dict]:
        """Get stat data for a given category."""
        if category == 'shots':
            home_val = stats.home_stats.shots
            away_val = stats.away_stats.shots
            total = home_val + away_val
            away_pct = (away_val / total * 100) if total > 0 else 50
            return {
                'label': 'SHOTS',
                'home_label': str(home_val),
                'away_label': str(away_val),
                'away_pct': away_pct
            }
        elif category == 'hits':
            home_val = stats.home_stats.hits
            away_val = stats.away_stats.hits
            total = home_val + away_val
            away_pct = (away_val / total * 100) if total > 0 else 50
            return {
                'label': 'HITS',
                'home_label': str(home_val),
                'away_label': str(away_val),
                'away_pct': away_pct
            }
        elif category == 'faceoff':
            home_pct = stats.home_stats.faceoff_pct
            away_pct = 100 - home_pct
            return {
                'label': 'FO%',
                'home_label': f"{home_pct:.0f}%",
                'away_label': f"{away_pct:.0f}%",
                'away_pct': away_pct
            }
        return None

    def _get_team_color(self, team_id: int) -> Color:
        """Get RGB tuple for a team's primary color."""
        try:
            color = self.team_colors.color(f"{team_id}.primary")
            return (color['r'], color['g'], color['b'])
        except Exception:
            return (255, 255, 255)

    def _get_outline_for_color(self, color: Color) -> Optional[Color]:
        """Get outline color for dark colors, or None if not needed."""
        if is_dark_color(color):
            return lighten_color(color, factor=0.6)
        return None

    def _get_readable_text_color(self, color: Color) -> Color:
        """Get readable text color - lightens dark colors for visibility."""
        if is_dark_color(color):
            return lighten_color(color, factor=0.6)
        return color
