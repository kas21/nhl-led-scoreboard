"""
Chart and visualization rendering utilities for LED matrix displays.

This module provides reusable chart components for displaying stats,
comparisons, and data visualizations on the LED matrix.

Usage:
    from renderer.charts import ChartRenderer

    charts = ChartRenderer(matrix)  # or any MatrixDrawer-compatible object
    charts.draw_bar_chart((2, 5), "SHOTS", 24, 17, font=my_font)

    # Animated version
    charts.animate_comparison_bars(
        (2, 5), "SHOTS", 24, 17, font=my_font,
        render_callback=matrix.render,
        sleep_func=time.sleep
    )
"""

from typing import Tuple, Optional, Union, Callable, Generator
from PIL import ImageFont


# Type aliases for clarity
Color = Tuple[int, int, int]
Position = Tuple[Union[int, str], Union[int, str]]


def ease_out_quad(t: float) -> float:
    """Quadratic ease-out: decelerates towards the end."""
    return t * (2 - t)


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out: stronger deceleration."""
    return 1 - (1 - t) ** 3


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out: smooth start and end."""
    return 2 * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 2 / 2


def linear(t: float) -> float:
    """Linear interpolation (no easing)."""
    return t


class ChartRenderer:
    """
    Utility class for drawing charts and stat visualizations on LED matrices.

    Works with Matrix, MatrixDrawer, or OffscreenBuffer instances - any object
    that provides draw_rectangle(), draw_text(), and draw_pixel() methods.
    """

    def __init__(self, drawer):
        """
        Initialize the chart renderer.

        Args:
            drawer: A Matrix, MatrixDrawer, or OffscreenBuffer instance
        """
        self.drawer = drawer

    def draw_horizontal_bar(
        self,
        position: Position,
        value: int,
        max_value: int,
        max_width: int = 50,
        height: int = 4,
        fill_color: Color = (255, 255, 255),
        bg_color: Optional[Color] = None
    ) -> dict:
        """
        Draw a single horizontal bar representing a value.

        Args:
            position: (x, y) top-left corner
            value: Current value to display
            max_value: Maximum possible value (for scaling)
            max_width: Maximum bar width in pixels
            height: Bar height in pixels
            fill_color: RGB tuple for the filled portion
            bg_color: Optional RGB tuple for unfilled background

        Returns:
            Dict with position and size info
        """
        x, y = position

        # Calculate bar width proportionally
        if max_value > 0:
            bar_width = max(1, int((value / max_value) * max_width))
        else:
            bar_width = 0

        # Draw background if specified
        if bg_color:
            self.drawer.draw_rectangle((x, y), (max_width, height), fill=bg_color)

        # Draw filled bar
        if bar_width > 0:
            self.drawer.draw_rectangle((x, y), (bar_width, height), fill=fill_color)

        return {"position": (x, y), "size": (max_width, height), "bar_width": bar_width}

    def draw_comparison_bars(
        self,
        position: Position,
        label: str,
        home_value: int,
        away_value: int,
        font: ImageFont.FreeTypeFont,
        max_bar_width: int = 50,
        bar_height: int = 5,
        label_width: int = 28,
        value_spacing: int = 3,
        row_spacing: int = 2,
        home_color: Color = (255, 255, 255),
        away_color: Color = (200, 200, 200),
        label_color: Color = (255, 255, 255),
        show_team_labels: bool = True
    ) -> dict:
        """
        Draw a comparison bar chart for home vs away stats.

        Example output:
            SHOTS
            HOME ██████████ 24
            AWAY ████████   17

        Args:
            position: (x, y) top-left corner
            label: Chart title (e.g., "SHOTS", "HITS")
            home_value: Home team's value
            away_value: Away team's value
            font: PIL ImageFont for text
            max_bar_width: Maximum width of bars in pixels
            bar_height: Height of each bar
            label_width: Width reserved for "HOME"/"AWAY" labels
            value_spacing: Space between bar and value text
            row_spacing: Vertical space between rows
            home_color: RGB tuple for home team
            away_color: RGB tuple for away team
            label_color: RGB tuple for title and team labels
            show_team_labels: Whether to show HOME/AWAY labels

        Returns:
            Dict with total size of the rendered chart
        """
        x, y = position
        start_y = y

        # Draw title label
        self.drawer.draw_text((x, y), label, font, fill=label_color)

        # Get text height for spacing
        bbox = font.getbbox(label)
        text_height = bbox[3] - bbox[1]
        y += text_height + row_spacing

        # Calculate max value for proportional scaling
        max_val = max(home_value, away_value, 1)

        # Calculate bar start position
        bar_x = x + (label_width if show_team_labels else 0)

        # Draw HOME row
        if show_team_labels:
            self.drawer.draw_text((x, y), "HOME", font, fill=home_color)

        bar_info = self.draw_horizontal_bar(
            (bar_x, y + 1),
            home_value, max_val,
            max_width=max_bar_width,
            height=bar_height,
            fill_color=home_color
        )

        # Draw home value
        value_x = bar_x + max_bar_width + value_spacing
        self.drawer.draw_text((value_x, y), str(home_value), font, fill=home_color)

        y += bar_height + row_spacing + 2

        # Draw AWAY row
        if show_team_labels:
            self.drawer.draw_text((x, y), "AWAY", font, fill=away_color)

        self.draw_horizontal_bar(
            (bar_x, y + 1),
            away_value, max_val,
            max_width=max_bar_width,
            height=bar_height,
            fill_color=away_color
        )

        # Draw away value
        self.drawer.draw_text((value_x, y), str(away_value), font, fill=away_color)

        y += bar_height + 1

        total_height = y - start_y
        total_width = value_x + 20  # Approximate width including value

        return {"position": position, "size": (total_width, total_height)}

    def draw_ratio_blocks(
        self,
        position: Position,
        success: int,
        total: int,
        block_width: int = 4,
        block_height: int = 5,
        spacing: int = 1,
        filled_color: Color = (200, 200, 200),
        empty_color: Color = (60, 60, 60),
        outline_color: Optional[Color] = None
    ) -> dict:
        """
        Draw a series of blocks showing success/total ratio.

        Example: ▓▓▓░ for 3 successes out of 4 attempts

        Args:
            position: (x, y) top-left corner
            success: Number of successful attempts (filled blocks)
            total: Total number of attempts (total blocks)
            block_width: Width of each block
            block_height: Height of each block
            spacing: Horizontal space between blocks
            filled_color: RGB tuple for filled/success blocks
            empty_color: RGB tuple for empty/failed blocks
            outline_color: Optional outline color for blocks

        Returns:
            Dict with position and size info
        """
        x, y = position

        for i in range(total):
            color = filled_color if i < success else empty_color
            block_x = x + i * (block_width + spacing)

            self.drawer.draw_rectangle(
                (block_x, y),
                (block_width, block_height),
                fill=color,
                outline=outline_color
            )

        total_width = total * (block_width + spacing) - spacing if total > 0 else 0

        return {"position": position, "size": (total_width, block_height)}

    def draw_power_play_stat(
        self,
        position: Position,
        label: str,
        goals: int,
        attempts: int,
        font: ImageFont.FreeTypeFont,
        block_width: int = 4,
        block_height: int = 5,
        spacing: int = 1,
        label_width: int = 25,
        filled_color: Color = (200, 200, 200),
        empty_color: Color = (60, 60, 60),
        text_color: Color = (255, 255, 255)
    ) -> dict:
        """
        Draw a power play statistic with label, blocks, and ratio.

        Example: PP  ▓▓░░ 2/4

        Args:
            position: (x, y) top-left corner
            label: Stat label (e.g., "PP", "HOME")
            goals: Power play goals scored
            attempts: Total power play opportunities
            font: PIL ImageFont for text
            block_width: Width of each block
            block_height: Height of each block
            spacing: Horizontal space between blocks
            label_width: Width reserved for label
            filled_color: RGB for successful blocks
            empty_color: RGB for empty blocks
            text_color: RGB for label and ratio text

        Returns:
            Dict with position and size info
        """
        x, y = position

        # Draw label
        self.drawer.draw_text((x, y), label, font, fill=text_color)

        # Draw blocks
        blocks_x = x + label_width
        block_info = self.draw_ratio_blocks(
            (blocks_x, y),
            goals, attempts,
            block_width=block_width,
            block_height=block_height,
            spacing=spacing,
            filled_color=filled_color,
            empty_color=empty_color
        )

        # Draw ratio text
        ratio_x = blocks_x + block_info["size"][0] + 4
        ratio_text = f"{goals}/{attempts}"
        self.drawer.draw_text((ratio_x, y), ratio_text, font, fill=text_color)

        return {"position": position, "size": (ratio_x + 20, block_height)}

    def draw_split_bar(
        self,
        position: Position,
        left_pct: float,
        width: int = 60,
        height: int = 6,
        left_color: Color = (255, 255, 255),
        right_color: Color = (150, 150, 150),
        divider_color: Optional[Color] = (80, 80, 80),
        divider_width: int = 1
    ) -> dict:
        """
        Draw a horizontal bar split into two portions by percentage.

        Example: ███████│█████ (showing 60/40 split)

        Args:
            position: (x, y) top-left corner
            left_pct: Percentage for left portion (0-100)
            width: Total bar width in pixels
            height: Bar height in pixels
            left_color: RGB tuple for left portion
            right_color: RGB tuple for right portion
            divider_color: Optional RGB for center divider line
            divider_width: Width of center divider

        Returns:
            Dict with position and size info
        """
        x, y = position

        # Clamp percentage
        left_pct = max(0, min(100, left_pct))

        # Calculate split widths
        left_width = int((left_pct / 100) * width)
        right_width = width - left_width - divider_width

        # Draw left portion
        if left_width > 0:
            self.drawer.draw_rectangle((x, y), (left_width, height), fill=left_color)

        # Draw divider
        if divider_color and divider_width > 0:
            self.drawer.draw_rectangle(
                (x + left_width, y),
                (divider_width, height),
                fill=divider_color
            )

        # Draw right portion
        if right_width > 0:
            self.drawer.draw_rectangle(
                (x + left_width + divider_width, y),
                (right_width, height),
                fill=right_color
            )

        return {"position": position, "size": (width, height)}

    def draw_faceoff_stat(
        self,
        position: Position,
        home_pct: float,
        font: ImageFont.FreeTypeFont,
        bar_width: int = 80,
        bar_height: int = 6,
        home_color: Color = (255, 255, 255),
        away_color: Color = (150, 150, 150),
        text_color: Optional[Color] = None,
        show_percentages: bool = True,
        label_below: bool = True
    ) -> dict:
        """
        Draw a faceoff percentage visualization with split bar and labels.

        Example:
            ███████│█████▶
               54%     46%

        Args:
            position: (x, y) top-left corner
            home_pct: Home team's faceoff win percentage (0-100)
            font: PIL ImageFont for percentage labels
            bar_width: Total bar width in pixels
            bar_height: Bar height in pixels
            home_color: RGB for home team portion
            away_color: RGB for away team portion
            text_color: RGB for percentage text (defaults to bar colors)
            show_percentages: Whether to show percentage labels
            label_below: If True, labels go below bar; if False, beside bar

        Returns:
            Dict with position and size info
        """
        x, y = position
        start_y = y

        # Draw split bar
        bar_info = self.draw_split_bar(
            (x, y),
            home_pct,
            width=bar_width,
            height=bar_height,
            left_color=home_color,
            right_color=away_color
        )

        total_height = bar_height

        # Draw percentage labels
        if show_percentages:
            away_pct = 100 - home_pct
            home_text = f"{home_pct:.0f}%"
            away_text = f"{away_pct:.0f}%"

            home_text_color = text_color or home_color
            away_text_color = text_color or away_color

            if label_below:
                y += bar_height + 2

                # Calculate positions to center under each portion
                home_width = int((home_pct / 100) * bar_width)
                away_width = bar_width - home_width

                # Get text widths for centering
                home_bbox = font.getbbox(home_text)
                away_bbox = font.getbbox(away_text)
                home_text_width = home_bbox[2] - home_bbox[0]
                away_text_width = away_bbox[2] - away_bbox[0]

                # Center home percentage under home portion
                home_text_x = x + (home_width - home_text_width) // 2
                self.drawer.draw_text((home_text_x, y), home_text, font, fill=home_text_color)

                # Center away percentage under away portion
                away_text_x = x + home_width + (away_width - away_text_width) // 2
                self.drawer.draw_text((away_text_x, y), away_text, font, fill=away_text_color)

                text_height = home_bbox[3] - home_bbox[1]
                total_height += 2 + text_height
            else:
                # Labels beside the bar
                self.drawer.draw_text((x - 25, y), home_text, font, fill=home_text_color)
                self.drawer.draw_text((x + bar_width + 3, y), away_text, font, fill=away_text_color)

        return {"position": position, "size": (bar_width, total_height)}

    def draw_stat_row(
        self,
        position: Position,
        label: str,
        home_value: Union[int, str],
        away_value: Union[int, str],
        font: ImageFont.FreeTypeFont,
        total_width: int = 120,
        label_color: Color = (255, 255, 255),
        home_color: Color = (255, 255, 255),
        away_color: Color = (200, 200, 200),
        center_label: bool = True
    ) -> dict:
        """
        Draw a simple stat comparison row.

        Example: 24  SHOTS  17

        Args:
            position: (x, y) top-left corner
            label: Stat name in center
            home_value: Home team value (left side)
            away_value: Away team value (right side)
            font: PIL ImageFont for text
            total_width: Total width of the row
            label_color: RGB for center label
            home_color: RGB for home value
            away_color: RGB for away value
            center_label: Whether to center the label

        Returns:
            Dict with position and size info
        """
        x, y = position

        home_str = str(home_value)
        away_str = str(away_value)

        # Get text measurements
        label_bbox = font.getbbox(label)
        home_bbox = font.getbbox(home_str)
        away_bbox = font.getbbox(away_str)

        label_width = label_bbox[2] - label_bbox[0]
        home_width = home_bbox[2] - home_bbox[0]
        away_width = away_bbox[2] - away_bbox[0]
        text_height = label_bbox[3] - label_bbox[1]

        # Calculate positions
        if center_label:
            label_x = x + (total_width - label_width) // 2
        else:
            label_x = x + 30  # Fixed offset

        home_x = x + 2
        away_x = x + total_width - away_width - 2

        # Draw text elements
        self.drawer.draw_text((home_x, y), home_str, font, fill=home_color)
        self.drawer.draw_text((label_x, y), label, font, fill=label_color)
        self.drawer.draw_text((away_x, y), away_str, font, fill=away_color)

        return {"position": position, "size": (total_width, text_height)}

    def draw_vertical_bar(
        self,
        position: Position,
        value: int,
        max_value: int,
        width: int = 4,
        max_height: int = 30,
        fill_color: Color = (255, 255, 255),
        bg_color: Optional[Color] = None,
        grow_up: bool = True
    ) -> dict:
        """
        Draw a single vertical bar representing a value.

        Args:
            position: (x, y) position (bottom-left if grow_up, top-left otherwise)
            value: Current value to display
            max_value: Maximum possible value (for scaling)
            width: Bar width in pixels
            max_height: Maximum bar height in pixels
            fill_color: RGB tuple for the filled portion
            bg_color: Optional RGB tuple for unfilled background
            grow_up: If True, bar grows upward; if False, downward

        Returns:
            Dict with position and size info
        """
        x, y = position

        # Calculate bar height proportionally
        if max_value > 0:
            bar_height = max(1, int((value / max_value) * max_height))
        else:
            bar_height = 0

        # Adjust y position for upward growth
        if grow_up:
            bg_y = y - max_height
            bar_y = y - bar_height
        else:
            bg_y = y
            bar_y = y

        # Draw background if specified
        if bg_color:
            self.drawer.draw_rectangle((x, bg_y), (width, max_height), fill=bg_color)

        # Draw filled bar
        if bar_height > 0:
            self.drawer.draw_rectangle((x, bar_y), (width, bar_height), fill=fill_color)

        return {"position": (x, bg_y), "size": (width, max_height), "bar_height": bar_height}

    # =========================================================================
    # Animation Methods
    # =========================================================================

    def animate_horizontal_bar(
        self,
        position: Position,
        value: int,
        max_value: int,
        max_width: int = 50,
        height: int = 4,
        fill_color: Color = (255, 255, 255),
        bg_color: Optional[Color] = None,
        frames: int = 15,
        easing: Callable[[float], float] = ease_out_quad
    ) -> Generator[dict, None, None]:
        """
        Generator that yields animation frames for a growing horizontal bar.

        Args:
            position: (x, y) top-left corner
            value: Target value to animate to
            max_value: Maximum possible value (for scaling)
            max_width: Maximum bar width in pixels
            height: Bar height in pixels
            fill_color: RGB tuple for the filled portion
            bg_color: Optional RGB tuple for unfilled background
            frames: Number of animation frames
            easing: Easing function (default: ease_out_quad)

        Yields:
            Dict with current animation state (progress, bar_width)
        """
        x, y = position

        # Calculate target bar width
        if max_value > 0:
            target_width = max(1, int((value / max_value) * max_width))
        else:
            target_width = 0

        for frame in range(frames + 1):
            progress = easing(frame / frames)
            current_width = int(target_width * progress)

            # Draw background if specified
            if bg_color:
                self.drawer.draw_rectangle((x, y), (max_width, height), fill=bg_color)

            # Draw current bar
            if current_width > 0:
                self.drawer.draw_rectangle((x, y), (current_width, height), fill=fill_color)

            yield {
                "progress": progress,
                "frame": frame,
                "total_frames": frames,
                "bar_width": current_width,
                "target_width": target_width
            }

    def animate_comparison_bars(
        self,
        position: Position,
        label: str,
        home_value: int,
        away_value: int,
        font: ImageFont.FreeTypeFont,
        render_callback: Callable[[], None],
        clear_callback: Callable[[], None],
        sleep_func: Callable[[float], None],
        max_bar_width: int = 50,
        bar_height: int = 5,
        label_width: int = 28,
        value_spacing: int = 3,
        row_spacing: int = 2,
        home_color: Color = (255, 255, 255),
        away_color: Color = (200, 200, 200),
        label_color: Color = (255, 255, 255),
        show_team_labels: bool = True,
        duration: float = 0.5,
        frames: int = 15,
        easing: Callable[[float], float] = ease_out_quad,
        stagger: float = 0.1,
        pre_draw: Optional[Callable[[], None]] = None
    ) -> dict:
        """
        Animate comparison bars growing from 0 to their final values.

        Args:
            position: (x, y) top-left corner
            label: Chart title (e.g., "SHOTS", "HITS")
            home_value: Home team's value
            away_value: Away team's value
            font: PIL ImageFont for text
            render_callback: Function to call to render the frame (e.g., matrix.render)
            clear_callback: Function to call to clear the display (e.g., matrix.clear)
            sleep_func: Function to sleep between frames (e.g., time.sleep or event.wait)
            max_bar_width: Maximum width of bars in pixels
            bar_height: Height of each bar
            label_width: Width reserved for "HOME"/"AWAY" labels
            value_spacing: Space between bar and value text
            row_spacing: Vertical space between rows
            home_color: RGB tuple for home team
            away_color: RGB tuple for away team
            label_color: RGB tuple for title and team labels
            show_team_labels: Whether to show HOME/AWAY labels
            duration: Total animation duration in seconds
            frames: Number of animation frames
            easing: Easing function
            stagger: Delay between home and away bar animations (seconds)
            pre_draw: Optional callback to draw other elements before each frame

        Returns:
            Dict with final chart size
        """
        x, y = position
        start_y = y
        frame_delay = duration / frames

        # Get text height for spacing
        bbox = font.getbbox(label)
        text_height = bbox[3] - bbox[1]

        # Calculate positions
        bar_y_home = y + text_height + row_spacing + 1
        bar_y_away = bar_y_home + bar_height + row_spacing + 2 + 1
        bar_x = x + (label_width if show_team_labels else 0)
        value_x = bar_x + max_bar_width + value_spacing

        # Calculate max value for proportional scaling
        max_val = max(home_value, away_value, 1)

        # Calculate target widths
        home_target = max(1, int((home_value / max_val) * max_bar_width)) if max_val > 0 else 0
        away_target = max(1, int((away_value / max_val) * max_bar_width)) if max_val > 0 else 0

        # Stagger frames
        stagger_frames = int(stagger / frame_delay) if frame_delay > 0 else 0

        for frame in range(frames + stagger_frames + 1):
            clear_callback()

            if pre_draw:
                pre_draw()

            # Draw static elements
            self.drawer.draw_text((x, y), label, font, fill=label_color)

            if show_team_labels:
                self.drawer.draw_text((x, bar_y_home - 1), "HOME", font, fill=home_color)
                self.drawer.draw_text((x, bar_y_away - 1), "AWAY", font, fill=away_color)

            # Calculate home bar progress
            home_progress = min(1.0, easing(min(frame, frames) / frames))
            home_width = int(home_target * home_progress)

            # Calculate away bar progress (staggered)
            away_frame = max(0, frame - stagger_frames)
            away_progress = min(1.0, easing(min(away_frame, frames) / frames))
            away_width = int(away_target * away_progress)

            # Draw home bar
            if home_width > 0:
                self.drawer.draw_rectangle((bar_x, bar_y_home), (home_width, bar_height), fill=home_color)

            # Draw away bar
            if away_width > 0:
                self.drawer.draw_rectangle((bar_x, bar_y_away), (away_width, bar_height), fill=away_color)

            # Draw values (animate numbers too)
            home_display = int(home_value * home_progress)
            away_display = int(away_value * away_progress)
            self.drawer.draw_text((value_x, bar_y_home - 1), str(home_display), font, fill=home_color)
            self.drawer.draw_text((value_x, bar_y_away - 1), str(away_display), font, fill=away_color)

            render_callback()
            sleep_func(frame_delay)

        # Final frame with exact values
        clear_callback()
        if pre_draw:
            pre_draw()

        return self.draw_comparison_bars(
            position, label, home_value, away_value, font,
            max_bar_width=max_bar_width, bar_height=bar_height,
            label_width=label_width, value_spacing=value_spacing,
            row_spacing=row_spacing, home_color=home_color,
            away_color=away_color, label_color=label_color,
            show_team_labels=show_team_labels
        )

    def animate_split_bar(
        self,
        position: Position,
        left_pct: float,
        render_callback: Callable[[], None],
        clear_callback: Callable[[], None],
        sleep_func: Callable[[float], None],
        width: int = 60,
        height: int = 6,
        left_color: Color = (255, 255, 255),
        right_color: Color = (150, 150, 150),
        divider_color: Optional[Color] = (80, 80, 80),
        divider_width: int = 1,
        duration: float = 0.5,
        frames: int = 15,
        easing: Callable[[float], float] = ease_out_quad,
        pre_draw: Optional[Callable[[], None]] = None
    ) -> dict:
        """
        Animate a split bar from 50/50 to the target percentage.

        Args:
            position: (x, y) top-left corner
            left_pct: Target percentage for left portion (0-100)
            render_callback: Function to render the frame
            clear_callback: Function to clear the display
            sleep_func: Function to sleep between frames
            width: Total bar width in pixels
            height: Bar height in pixels
            left_color: RGB for left portion
            right_color: RGB for right portion
            divider_color: Optional RGB for center divider
            divider_width: Width of center divider
            duration: Total animation duration in seconds
            frames: Number of animation frames
            easing: Easing function
            pre_draw: Optional callback to draw other elements

        Returns:
            Dict with final bar info
        """
        x, y = position
        frame_delay = duration / frames

        # Clamp target percentage
        target_pct = max(0, min(100, left_pct))

        # Animate from 50% to target
        for frame in range(frames + 1):
            progress = easing(frame / frames)
            current_pct = 50 + (target_pct - 50) * progress

            clear_callback()
            if pre_draw:
                pre_draw()

            self.draw_split_bar(
                (x, y), current_pct,
                width=width, height=height,
                left_color=left_color, right_color=right_color,
                divider_color=divider_color, divider_width=divider_width
            )

            render_callback()
            sleep_func(frame_delay)

        return self.draw_split_bar(
            (x, y), target_pct,
            width=width, height=height,
            left_color=left_color, right_color=right_color,
            divider_color=divider_color, divider_width=divider_width
        )

    def animate_ratio_blocks(
        self,
        position: Position,
        success: int,
        total: int,
        render_callback: Callable[[], None],
        clear_callback: Callable[[], None],
        sleep_func: Callable[[float], None],
        block_width: int = 4,
        block_height: int = 5,
        spacing: int = 1,
        filled_color: Color = (200, 200, 200),
        empty_color: Color = (60, 60, 60),
        outline_color: Optional[Color] = None,
        delay_per_block: float = 0.15,
        pre_draw: Optional[Callable[[], None]] = None
    ) -> dict:
        """
        Animate ratio blocks appearing one at a time.

        Args:
            position: (x, y) top-left corner
            success: Number of successful attempts (filled blocks)
            total: Total number of attempts
            render_callback: Function to render the frame
            clear_callback: Function to clear the display
            sleep_func: Function to sleep between frames
            block_width: Width of each block
            block_height: Height of each block
            spacing: Horizontal space between blocks
            filled_color: RGB for filled/success blocks
            empty_color: RGB for empty/failed blocks
            outline_color: Optional outline color
            delay_per_block: Delay between each block appearing
            pre_draw: Optional callback to draw other elements

        Returns:
            Dict with final block info
        """
        x, y = position

        for shown in range(total + 1):
            clear_callback()
            if pre_draw:
                pre_draw()

            # Draw blocks up to current count
            for i in range(shown):
                color = filled_color if i < success else empty_color
                block_x = x + i * (block_width + spacing)
                self.drawer.draw_rectangle(
                    (block_x, y),
                    (block_width, block_height),
                    fill=color,
                    outline=outline_color
                )

            render_callback()
            if shown < total:
                sleep_func(delay_per_block)

        total_width = total * (block_width + spacing) - spacing if total > 0 else 0
        return {"position": position, "size": (total_width, block_height)}
