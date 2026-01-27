#!/usr/bin/env python3
"""
Test script for GameStatsBoard with mock data.

Run with:
    uv run tests/test_game_stats.py --emulated --led-rows=64 --led-cols=128
    uv run tests/test_game_stats.py --emulated --led-rows=32 --led-cols=64
"""

import sys
import logging
import argparse
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch
from dataclasses import dataclass

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import driver


def parse_args():
    parser = argparse.ArgumentParser(description="Test GameStatsBoard with mock game story data")

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
    parser.add_argument("--stat", action="store",
                        help="Show only a specific stat (shots, hits, faceoff, powerplay, blocked). Default: cycle all",
                        default=None, type=str, choices=['shots', 'hits', 'faceoff', 'powerplay', 'blocked'])
    parser.add_argument("--delay", action="store", help="Seconds per stat. (Default: 5)",
                        default=5, type=float)
    parser.add_argument("--loop", action="store_true", help="Loop continuously", default=False)
    parser.add_argument("--no-animation", action="store_true", help="Disable animations", default=False)
    parser.add_argument("--home-team", action="store", help="Home team abbreviation (Default: BOS)",
                        default="BOS", type=str)
    parser.add_argument("--away-team", action="store", help="Away team abbreviation (Default: TOR)",
                        default="TOR", type=str)
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
from renderer.matrix import Matrix
# Import directly to bypass broken __init__.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "boards" / "builtins" / "game_stats"))
from game_stats import GameStatsBoard
from nhl_api.models import GameStoryStats, TeamGameStats
from nhl_api.workers.game_story_worker import GameStoryWorker
from utils import led_matrix_options


# Mock game story data - realistic NHL stats
def create_mock_game_stats(home_team="BOS", away_team="TOR"):
    """Create mock GameStoryStats with realistic data."""

    # Team ID mapping (simplified)
    team_ids = {
        "BOS": 6, "TOR": 10, "MTL": 8, "NYR": 3, "PHI": 4,
        "PIT": 5, "COL": 21, "EDM": 22, "CGY": 20, "VAN": 23,
        "SEA": 55, "LAK": 26, "ANA": 24, "SJS": 28, "VGK": 54,
        "DAL": 25, "MIN": 30, "WPG": 52, "NSH": 18, "STL": 19,
        "CHI": 16, "DET": 17, "TBL": 14, "FLA": 13, "CAR": 12,
        "NYI": 2, "NJD": 1, "WSH": 15, "CBJ": 29, "OTT": 9, "BUF": 7
    }

    return GameStoryStats(
        game_id=2024020123,
        home_team_abbrev=home_team,
        away_team_abbrev=away_team,
        home_team_id=team_ids.get(home_team, 6),
        away_team_id=team_ids.get(away_team, 10),
        home_stats=TeamGameStats(
            shots=28,
            hits=22,
            blocked_shots=14,
            giveaways=7,
            takeaways=9,
            pim=8,
            faceoff_pct=52.4,
            power_play_goals=1,
            power_play_opportunities=4,
            power_play_pct=25.0
        ),
        away_stats=TeamGameStats(
            shots=24,
            hits=19,
            blocked_shots=11,
            giveaways=5,
            takeaways=6,
            pim=10,
            faceoff_pct=47.6,
            power_play_goals=0,
            power_play_opportunities=3,
            power_play_pct=0.0
        ),
        game_state="LIVE",
        period=2
    )


def create_mock_data_object(home_team="BOS", away_team="TOR"):
    """Create a mock data object with necessary config."""
    from types import SimpleNamespace
    from PIL import ImageFont

    # Create mock config
    config = SimpleNamespace()

    # Mock team colors
    team_colors = SimpleNamespace()

    # Team color mapping (RGB tuples)
    color_map = {
        "BOS": {"primary": (252, 181, 20), "text": (0, 0, 0)},  # Gold/Black
        "TOR": {"primary": (0, 32, 91), "text": (255, 255, 255)},  # Blue/White
        "MTL": {"primary": (175, 30, 45), "text": (255, 255, 255)},  # Red/White
        "COL": {"primary": (111, 38, 61), "text": (255, 255, 255)},  # Burgundy/White
        "EDM": {"primary": (4, 30, 66), "text": (252, 76, 2)},  # Navy/Orange
        "NYR": {"primary": (0, 51, 160), "text": (255, 255, 255)},  # Blue/White
        "VGK": {"primary": (185, 151, 91), "text": (51, 63, 72)},  # Gold/Grey
    }

    def color_func(key):
        """Mock color function."""
        team_id, prop = key.split('.')
        colors = color_map.get(team_id, {"primary": (128, 128, 128), "text": (255, 255, 255)})
        rgb = colors.get(prop, (255, 255, 255))
        return {'r': rgb[0], 'g': rgb[1], 'b': rgb[2]}

    team_colors.color = color_func
    config.team_colors = team_colors

    # Mock layout
    layout = SimpleNamespace()
    try:
        layout.font = ImageFont.truetype("assets/fonts/04B_24__.TTF", 8)
        layout.font_large = ImageFont.truetype("assets/fonts/04B_24__.TTF", 12)
    except:
        font_path = Path(__file__).parent.parent / "assets/fonts/04B_24__.TTF"
        layout.font = ImageFont.truetype(str(font_path), 8)
        layout.font_large = ImageFont.truetype(str(font_path), 12)

    config.layout = layout

    # Mock central config (for board config loading)
    config.config = SimpleNamespace()

    # Create game_stats board config
    game_stats_config = {
        'display_duration': commandArgs.delay,
        'animate_bars': not commandArgs.no_animation,
        'categories': [commandArgs.stat] if commandArgs.stat else ['shots', 'hits', 'faceoff', 'powerplay', 'blocked']
    }
    config.config.game_stats = game_stats_config

    # Create main data object
    data = SimpleNamespace()
    data.config = config
    data.current_game_id = 2024020123

    return data


class GameStatsTest:
    """Test runner for GameStatsBoard."""

    def __init__(self, matrix, delay=5, loop=False, home_team="BOS", away_team="TOR"):
        self.matrix = matrix
        self.delay = delay
        self.loop = loop
        self.sleepEvent = Event()
        self.home_team = home_team
        self.away_team = away_team

        # Create mock data
        self.data = create_mock_data_object(home_team, away_team)
        self.mock_stats = create_mock_game_stats(home_team, away_team)

        logger.info(f"Testing game stats: {away_team} @ {home_team}")
        logger.info(f"Mock stats: {away_team} {self.mock_stats.away_stats.shots} SOG, "
                   f"{home_team} {self.mock_stats.home_stats.shots} SOG")

    def run(self):
        """Run the test display."""
        # Give the emulator window time to initialize
        self.sleepEvent.wait(0.5)

        try:
            # Patch GameStoryWorker.get_game_stats to return our mock data
            with patch.object(GameStoryWorker, 'get_game_stats', return_value=self.mock_stats):
                # Create and run the board
                board = GameStatsBoard(self.data, self.matrix, self.sleepEvent)

                print("\nRendering GameStatsBoard...")
                print(f"  Categories: {board.categories}")
                print(f"  Display duration: {board.display_duration}s")
                print(f"  Animations: {'enabled' if board.animate_bars else 'disabled'}")

                while True:
                    # Render the board (it will cycle through all configured stats)
                    board.render()

                    if not self.loop:
                        break

                    print("\nLooping...")
                    self.sleepEvent.wait(1)

        except KeyboardInterrupt:
            print("\nInterrupted")


def main():
    """Main entry point."""
    print("\n=== GameStatsBoard Test ===")
    print(f"Matrix size: {commandArgs.led_cols}x{commandArgs.led_rows}")
    print(f"Mode: {'Emulated' if commandArgs.emulated else 'Hardware'}")
    print(f"Teams: {commandArgs.away_team} @ {commandArgs.home_team}")
    print(f"Stat filter: {commandArgs.stat or 'All'}")
    print(f"Animation: {'Disabled' if commandArgs.no_animation else 'Enabled'}")
    print(f"Loop: {'Yes' if commandArgs.loop else 'No'}\n")

    # Set up the LED matrix
    options = led_matrix_options(commandArgs)
    matrix = Matrix(RGBMatrix(options=options))

    # Run the test
    test = GameStatsTest(
        matrix,
        delay=commandArgs.delay,
        loop=commandArgs.loop,
        home_team=commandArgs.home_team,
        away_team=commandArgs.away_team
    )
    test.run()

    print("\nTest complete!")


if __name__ == "__main__":
    main()
