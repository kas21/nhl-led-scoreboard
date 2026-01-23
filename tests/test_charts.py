#!/usr/bin/env python3
"""
Test script for ChartRenderer visualizations.

Run with:
    uv run tests/test_charts.py --emulated --led-rows=64 --led-cols=128

This displays mock intermission stats to test the chart rendering system.
"""

import sys
import logging
import argparse
from pathlib import Path
from threading import Event

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import driver


def parse_args():
    parser = argparse.ArgumentParser(description="Test the chart renderer with mock intermission stats")

    # LED Matrix options
    parser.add_argument("--led-rows", action="store", help="Display rows. (Default: 64)",
                        default=64, type=int)
    parser.add_argument("--led-cols", action="store", help="Panel columns. (Default: 128)",
                        default=128, type=int)
    parser.add_argument("--led-chain", action="store", help="Daisy-chained boards. (Default: 1)", default=1, type=int)
    parser.add_argument("--led-parallel", action="store",
                        help="For Plus-models or RPi2: parallel chains. 1..3. (Default: 1)", default=1, type=int)
    parser.add_argument("--led-pwm-bits", action="store", help="Bits used for PWM. Range 1..11. (Default: 11)",
                        default=11, type=int)
    parser.add_argument("--led-brightness", action="store", help="Sets brightness level. Range: 1..100. (Default: 100)",
                        default=100, type=int)
    parser.add_argument("--led-gpio-mapping", help="Hardware Mapping: regular, adafruit-hat, adafruit-hat-pwm",
                        choices=['regular', 'adafruit-hat', 'adafruit-hat-pwm'], type=str)
    parser.add_argument("--led-scan-mode", action="store",
                        help="Progressive or interlaced scan. 0 = Progressive, 1 = Interlaced. (Default: 1)", default=1,
                        choices=range(2), type=int)
    parser.add_argument("--led-pwm-lsb-nanoseconds", action="store",
                        help="Base time-unit for the on-time in the lowest significant bit in nanoseconds. (Default: 130)",
                        default=130, type=int)
    parser.add_argument("--led-pwm-dither-bits", action="store",
                        help="Time dithering of lower bits (Default: 0)",
                        default=0, type=int)
    parser.add_argument("--led-show-refresh", action="store_true",
                        help="Shows the current refresh rate of the LED panel.")
    parser.add_argument("--led-slowdown-gpio", action="store",
                        help="Slow down writing to GPIO. Range: 0..4. (Default: 1)", choices=range(5), type=int)
    parser.add_argument("--led-no-hardware-pulse", action="store", help="Don't use hardware pin-pulse generation.")
    parser.add_argument("--led-rgb-sequence", action="store",
                        help="Switch if your matrix has led colors swapped. (Default: RGB)", default="RGB", type=str)
    parser.add_argument("--led-pixel-mapper", action="store", help="Apply pixel mappers. e.g \"Rotate:90\"", default="",
                        type=str)
    parser.add_argument("--led-row-addr-type", action="store",
                        help="0 = default; 1 = AB-addressed panels; 2 = direct row select; 3 = ABC-addressed panels",
                        default=0, type=int, choices=[0, 1, 2, 3, 4, 5])
    parser.add_argument("--led-multiplexing", action="store",
                        help="Multiplexing type: 0 = direct; 1 = strip; 2 = checker; 3 = spiral",
                        default=0, type=int)
    parser.add_argument("--led-panel-type", action="store", help="Needed to initialize special panels. Supported: 'FM6126A'",
                        default="", type=str)
    parser.add_argument("--led-limit-refresh", action="store",
                        help="Limit refresh rate to this frequency in Hz. 0=no limit. Default: 0", default=0, type=int)
    parser.add_argument("--emulated", action="store_true", help="Run in software emulation mode.")

    # Test options
    parser.add_argument("--page", action="store", help="Show only a specific page (1-7). Default: cycle all",
                        default=None, type=int)
    parser.add_argument("--delay", action="store", help="Seconds per page. (Default: 5)",
                        default=5, type=float)
    parser.add_argument("--loop", action="store_true", help="Loop continuously", default=False)
    parser.add_argument("--easing", action="store",
                        help="Easing function: linear, ease_out_quad, ease_out_cubic, ease_in_out_quad (Default: ease_out_quad)",
                        default="ease_out_quad", type=str,
                        choices=["linear", "ease_out_quad", "ease_out_cubic", "ease_in_out_quad"])
    parser.add_argument("--loglevel", action="store", help="Log level (DEBUG, INFO, WARN, ERROR, CRITICAL)",
                        default="INFO", type=str)

    return parser.parse_args()


# Parse args before imports that depend on driver mode
commandArgs = parse_args()

# Set up logging
log_level = getattr(logging, commandArgs.loglevel.upper(), logging.INFO)
logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Set driver mode based on --emulated flag
if commandArgs.emulated:
    from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
    driver.mode = driver.DriverMode.SOFTWARE_EMULATION
else:
    try:
        from rgbmatrix import RGBMatrix, RGBMatrixOptions  # type: ignore
        driver.mode = driver.DriverMode.HARDWARE
    except ImportError:
        from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions
        driver.mode = driver.DriverMode.SOFTWARE_EMULATION
        print("Warning: Hardware library not found, falling back to emulation mode")

# Now import modules that depend on driver mode
from PIL import ImageFont
from renderer.matrix import Matrix
from renderer.charts import ChartRenderer, ease_in_out_quad, linear, ease_out_cubic
from utils import led_matrix_options


# Mock intermission stats data
MOCK_STATS = {
    "home_team": "BOS",
    "away_team": "TOR",
    "home_color": (252, 181, 20),   # Bruins gold
    "away_color": (0, 32, 91),      # Leafs blue
    "period": 2,
    "stats": {
        "shots": {"home": 24, "away": 17},
        "hits": {"home": 18, "away": 22},
        "blocks": {"home": 8, "away": 12},
        "faceoff_pct": {"home": 54.2, "away": 45.8},
        "power_plays": {"home": {"goals": 1, "attempts": 3}, "away": {"goals": 0, "attempts": 2}},
        "pim": {"home": 6, "away": 4},
        "giveaways": {"home": 5, "away": 8},
        "takeaways": {"home": 7, "away": 4},
    }
}


class ChartTestRenderer:
    """Test renderer for chart visualizations."""

    def __init__(self, matrix, delay=5):
        self.matrix = matrix
        self.charts = ChartRenderer(matrix)
        self.delay = delay
        self.sleepEvent = Event()

        # Load the same font as Team Summary board (04B_24__.TTF at size 8)
        try:
            self.font = ImageFont.truetype("assets/fonts/04B_24__.TTF", 8)
        except:
            try:
                # Fallback if running from different directory
                font_path = Path(__file__).parent.parent / "assets/fonts/04B_24__.TTF"
                self.font = ImageFont.truetype(str(font_path), 8)
            except:
                self.font = ImageFont.load_default()

        self.pages = [
            ("Animated Bars", self.render_animated_bars),
            ("Animated Faceoffs", self.render_animated_faceoffs),
            ("Shots & Hits", self.render_shots_hits),
            ("Power Plays", self.render_power_plays),
            ("Faceoffs", self.render_faceoffs),
            ("Stat Rows", self.render_stat_rows),
            ("Mirror Bars", self.render_all_bars),
        ]

    def run(self, page=None, loop=False):
        """Run the test display."""
        # Give the emulator window time to initialize before animating
        self.sleepEvent.wait(0.5)

        try:
            while True:
                if page is not None:
                    # Show only specific page
                    if 1 <= page <= len(self.pages):
                        name, func = self.pages[page - 1]
                        self._render_page(name, func)
                        self.sleepEvent.wait(self.delay)
                    else:
                        print(f"Invalid page {page}. Valid pages: 1-{len(self.pages)}")
                        return
                else:
                    # Cycle through all pages
                    for name, func in self.pages:
                        if self.sleepEvent.is_set():
                            break
                        self._render_page(name, func)
                        self.sleepEvent.wait(self.delay)

                if not loop:
                    break

        except KeyboardInterrupt:
            print("\nInterrupted")

    def _render_page(self, name, func):
        """Render a single page."""
        print(f"  Rendering: {name}")
        self.matrix.clear()
        func()
        self.matrix.render()

    def render_animated_bars(self):
        """Page 1: Animated comparison bars growing from zero."""
        stats = MOCK_STATS["stats"]
        home_color = MOCK_STATS["home_color"]
        away_color = MOCK_STATS["away_color"]

        def draw_title():
            self.matrix.draw_text_centered(1, "ANIMATED STATS", self.font, fill=(255, 255, 255))

        # Animate shots
        self.charts.animate_comparison_bars(
            (2, 12), "SHOTS",
            home_value=stats["shots"]["home"],
            away_value=stats["shots"]["away"],
            font=self.font,
            render_callback=self.matrix.render,
            clear_callback=self.matrix.clear,
            sleep_func=self.sleepEvent.wait,
            max_bar_width=45,
            bar_height=4,
            home_color=home_color,
            away_color=away_color,
            duration=0.6,
            frames=20,
            stagger=0.15,
            pre_draw=draw_title
        )

        # Small pause between animations
        self.sleepEvent.wait(0.3)

        def draw_title_and_shots():
            draw_title()
            self.charts.draw_comparison_bars(
                (2, 12), "SHOTS",
                home_value=stats["shots"]["home"],
                away_value=stats["shots"]["away"],
                font=self.font,
                max_bar_width=45,
                bar_height=4,
                home_color=home_color,
                away_color=away_color
            )

        # Animate hits
        self.charts.animate_comparison_bars(
            (2, 38), "HITS",
            home_value=stats["hits"]["home"],
            away_value=stats["hits"]["away"],
            font=self.font,
            render_callback=self.matrix.render,
            clear_callback=self.matrix.clear,
            sleep_func=self.sleepEvent.wait,
            max_bar_width=45,
            bar_height=4,
            home_color=home_color,
            away_color=away_color,
            duration=0.6,
            frames=20,
            stagger=0.15,
            pre_draw=draw_title_and_shots
        )

        self.matrix.render()

    def render_animated_faceoffs(self):
        """Page 2: Animated faceoff split bar."""
        stats = MOCK_STATS["stats"]
        home_color = MOCK_STATS["home_color"]
        away_color = MOCK_STATS["away_color"]

        def draw_static():
            self.matrix.draw_text_centered(1, "FACEOFFS", self.font, fill=(255, 255, 255))
            self.matrix.draw_text((5, 15), MOCK_STATS["home_team"], self.font, fill=home_color)
            self.matrix.draw_text((105, 15), MOCK_STATS["away_team"], self.font, fill=away_color)

        # Animate the split bar from 50/50 to actual percentage
        self.charts.animate_split_bar(
            (14, 28),
            left_pct=stats["faceoff_pct"]["home"],
            render_callback=self.matrix.render,
            clear_callback=self.matrix.clear,
            sleep_func=self.sleepEvent.wait,
            width=100,
            height=8,
            left_color=home_color,
            right_color=away_color,
            duration=0.8,
            frames=25,
            pre_draw=draw_static
        )

        # Draw final state with percentages
        self.matrix.clear()
        draw_static()
        self.charts.draw_faceoff_stat(
            (14, 28),
            home_pct=stats["faceoff_pct"]["home"],
            font=self.font,
            bar_width=100,
            bar_height=8,
            home_color=home_color,
            away_color=away_color,
            show_percentages=True,
            label_below=True
        )
        self.matrix.draw_text_centered(52, "END OF PERIOD 2", self.font, fill=(150, 150, 150))
        self.matrix.render()

    def render_shots_hits(self):
        """Page 1: Shots and Hits comparison bars."""
        stats = MOCK_STATS["stats"]
        home_color = MOCK_STATS["home_color"]
        away_color = MOCK_STATS["away_color"]

        # Title
        self.matrix.draw_text_centered(1, "INTERMISSION STATS", self.font, fill=(255, 255, 255))

        # Shots
        self.charts.draw_comparison_bars(
            (2, 12), "SHOTS",
            home_value=stats["shots"]["home"],
            away_value=stats["shots"]["away"],
            font=self.font,
            max_bar_width=45,
            bar_height=4,
            home_color=home_color,
            away_color=away_color
        )

        # Hits
        self.charts.draw_comparison_bars(
            (2, 38), "HITS",
            home_value=stats["hits"]["home"],
            away_value=stats["hits"]["away"],
            font=self.font,
            max_bar_width=45,
            bar_height=4,
            home_color=home_color,
            away_color=away_color
        )

    def render_power_plays(self):
        """Page 2: Power play stats with blocks."""
        stats = MOCK_STATS["stats"]
        home_color = MOCK_STATS["home_color"]
        away_color = MOCK_STATS["away_color"]

        # Title
        self.matrix.draw_text_centered(1, "POWER PLAYS", self.font, fill=(255, 255, 255))

        # Home PP
        self.matrix.draw_text((2, 15), "HOME", self.font, fill=home_color)
        self.charts.draw_power_play_stat(
            (35, 15), "",
            goals=stats["power_plays"]["home"]["goals"],
            attempts=stats["power_plays"]["home"]["attempts"],
            font=self.font,
            block_width=6,
            block_height=6,
            filled_color=home_color,
            empty_color=(60, 60, 60),
            label_width=0
        )

        # Away PP
        self.matrix.draw_text((2, 28), "AWAY", self.font, fill=away_color)
        self.charts.draw_power_play_stat(
            (35, 28), "",
            goals=stats["power_plays"]["away"]["goals"],
            attempts=stats["power_plays"]["away"]["attempts"],
            font=self.font,
            block_width=6,
            block_height=6,
            filled_color=away_color,
            empty_color=(60, 60, 60),
            label_width=0
        )

        # PIM comparison
        self.matrix.draw_text_centered(42, "PENALTY MINUTES", self.font, fill=(255, 255, 255))
        self.charts.draw_stat_row(
            (4, 52),
            "PIM",
            stats["pim"]["home"],
            stats["pim"]["away"],
            font=self.font,
            total_width=120,
            home_color=home_color,
            away_color=away_color
        )

    def render_faceoffs(self):
        """Page 3: Faceoff percentage visualization."""
        stats = MOCK_STATS["stats"]
        home_color = MOCK_STATS["home_color"]
        away_color = MOCK_STATS["away_color"]

        # Title
        self.matrix.draw_text_centered(1, "FACEOFFS", self.font, fill=(255, 255, 255))

        # Team labels
        self.matrix.draw_text((5, 15), MOCK_STATS["home_team"], self.font, fill=home_color)
        self.matrix.draw_text((105, 15), MOCK_STATS["away_team"], self.font, fill=away_color)

        # Faceoff split bar
        self.charts.draw_faceoff_stat(
            (14, 28),
            home_pct=stats["faceoff_pct"]["home"],
            font=self.font,
            bar_width=100,
            bar_height=8,
            home_color=home_color,
            away_color=away_color,
            show_percentages=True,
            label_below=True
        )

        # Additional context
        self.matrix.draw_text_centered(52, "END OF PERIOD 2", self.font, fill=(150, 150, 150))

    def render_stat_rows(self):
        """Page 4: Simple stat row display."""
        stats = MOCK_STATS["stats"]
        home_color = MOCK_STATS["home_color"]
        away_color = MOCK_STATS["away_color"]

        # Title with team abbreviations
        self.matrix.draw_text((5, 1), MOCK_STATS["home_team"], self.font, fill=home_color)
        self.matrix.draw_text_centered(1, "VS", self.font, fill=(150, 150, 150))
        self.matrix.draw_text((105, 1), MOCK_STATS["away_team"], self.font, fill=away_color)

        y = 14
        row_height = 10

        # Multiple stat rows
        stat_pairs = [
            ("SHOTS", stats["shots"]),
            ("HITS", stats["hits"]),
            ("BLOCKS", stats["blocks"]),
            ("GIVES", stats["giveaways"]),
            ("TAKES", stats["takeaways"]),
        ]

        for label, values in stat_pairs:
            self.charts.draw_stat_row(
                (4, y),
                label,
                values["home"],
                values["away"],
                font=self.font,
                total_width=120,
                home_color=home_color,
                away_color=away_color,
                label_color=(200, 200, 200)
            )
            y += row_height

    def render_all_bars(self):
        """Page 5: Side-by-side horizontal bars (mirrored from center)."""
        stats = MOCK_STATS["stats"]
        home_color = MOCK_STATS["home_color"]
        away_color = MOCK_STATS["away_color"]

        # Title
        self.matrix.draw_text_centered(1, "GAME STATS", self.font, fill=(255, 255, 255))

        y = 12
        bar_height = 3
        row_spacing = 9
        max_bar = 35
        center_x = self.matrix.width // 2

        stat_list = [
            ("SOG", stats["shots"]["home"], stats["shots"]["away"]),
            ("HIT", stats["hits"]["home"], stats["hits"]["away"]),
            ("BLK", stats["blocks"]["home"], stats["blocks"]["away"]),
            ("GVA", stats["giveaways"]["home"], stats["giveaways"]["away"]),
            ("TKA", stats["takeaways"]["home"], stats["takeaways"]["away"]),
        ]

        for label, home_val, away_val in stat_list:
            max_val = max(home_val, away_val, 1)

            # Label in center
            label_bbox = self.font.getbbox(label)
            label_width = label_bbox[2] - label_bbox[0]
            self.matrix.draw_text((center_x - label_width // 2, y), label, self.font, fill=(180, 180, 180))

            # Home bar (grows left from center)
            home_width = int((home_val / max_val) * max_bar)
            self.charts.draw_horizontal_bar(
                (center_x - 20 - home_width, y + 1),
                home_val, max_val,
                max_width=home_width,
                height=bar_height,
                fill_color=home_color
            )
            self.matrix.draw_text((2, y), str(home_val), self.font, fill=home_color)

            # Away bar (grows right from center)
            away_width = int((away_val / max_val) * max_bar)
            self.charts.draw_horizontal_bar(
                (center_x + 20, y + 1),
                away_val, max_val,
                max_width=away_width,
                height=bar_height,
                fill_color=away_color
            )
            self.matrix.draw_text((self.matrix.width - 15, y), str(away_val), self.font, fill=away_color)

            y += row_spacing


def main():
    cols = commandArgs.led_cols
    rows = commandArgs.led_rows

    print("=" * 60)
    print("Chart Renderer Test")
    print("=" * 60)
    print(f"Display size: {cols}x{rows}")
    print(f"Driver mode: {driver.mode.name}")
    print(f"Delay: {commandArgs.delay}s per page")
    if commandArgs.page:
        print(f"Showing page: {commandArgs.page}")
    if commandArgs.loop:
        print("Looping: enabled")
    print("=" * 60)

    # Create matrix
    try:
        matrixOptions = led_matrix_options(commandArgs)
        matrixOptions.drop_privileges = False

        if driver.is_emulated():
            matrixOptions.emulator_title = "Chart Renderer Test"
            matrixOptions.icon_path = (Path(__file__).parent.parent / "assets" / "images" / "favicon.ico").resolve()

        matrix = Matrix(RGBMatrix(options=matrixOptions))
        print(f"Created matrix ({matrix.width}x{matrix.height})")
    except Exception as e:
        print(f"Failed to create matrix: {e}")
        import traceback
        traceback.print_exc()
        return

    # Run test renderer
    print("\nStarting chart test...")
    print("Pages:")
    print("  1. Animated Bars - Bars grow from zero with easing")
    print("  2. Animated Faceoffs - Split bar animates from 50/50")
    print("  3. Shots & Hits - Static comparison bar charts")
    print("  4. Power Plays - Block indicators with ratios")
    print("  5. Faceoffs - Split percentage bar")
    print("  6. Stat Rows - Simple value comparisons")
    print("  7. Mirror Bars - Center-aligned mirrored bars")
    print()

    renderer = ChartTestRenderer(matrix, delay=commandArgs.delay)
    renderer.run(page=commandArgs.page, loop=commandArgs.loop)

    print("\nTest completed!")


if __name__ == "__main__":
    main()
