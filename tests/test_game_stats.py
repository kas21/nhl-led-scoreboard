#!/usr/bin/env python3
"""
Test script for GameStatsBoard with mock or live NHL data.

Run with mock data:
    uv run tests/test_game_stats.py --emulated --led-rows=64 --led-cols=128

Run with live data (game ID):
    uv run tests/test_game_stats.py --emulated --led-rows=64 --led-cols=128 --game-id 2024020456

Run with live data (team + date):
    uv run tests/test_game_stats.py --emulated --led-rows=64 --led-cols=128 --team BOS --date 2025-01-15
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

    # Live data options
    parser.add_argument("--game-id", action="store", help="NHL game ID to fetch live stats for",
                        default=None, type=int)
    parser.add_argument("--team", action="store", help="Team abbreviation to find a game for (use with --date)",
                        default=None, type=str)
    parser.add_argument("--date", action="store",
                        help="Date to look up games (YYYY-MM-DD format, default: today). Use with --team.",
                        default=None, type=str)

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
from nhl_api.client import NHLAPIClient
from utils import led_matrix_options


def fetch_live_stats(game_id):
    """Fetch live GameStoryStats from the NHL API by game ID."""
    logger.info(f"Fetching live stats for game {game_id}...")
    client = NHLAPIClient()
    try:
        raw_data = client.get_game_story(game_id)
        stats = GameStoryStats.from_dict(raw_data)
        logger.info(
            f"Live stats: {stats.away_team_abbrev} @ {stats.home_team_abbrev} "
            f"(state={stats.game_state}, period={stats.period})"
        )
        return stats
    except Exception as e:
        logger.error(f"Failed to fetch live stats for game {game_id}: {e}")
        return None
    finally:
        client.close()


def find_game_id_for_team(team_abbrev, date_str=None):
    """
    Find a game ID for a team on a given date.

    Args:
        team_abbrev: Three-letter team code (e.g. 'BOS')
        date_str: Date string in YYYY-MM-DD format. Defaults to today.

    Returns:
        Game ID (int) or None if no game found.
    """
    from datetime import date as date_type

    if date_str is None:
        lookup_date = date_type.today().isoformat()
    else:
        lookup_date = date_str

    logger.info(f"Looking up games for {team_abbrev} on {lookup_date}...")
    client = NHLAPIClient()
    try:
        data = client.get_score_details(lookup_date)
        games = data.get('games', [])
        logger.info(f"Found {len(games)} game(s) on {lookup_date}")

        team_upper = team_abbrev.upper()
        for game in games:
            home_abbrev = game.get('homeTeam', {}).get('abbrev', '')
            away_abbrev = game.get('awayTeam', {}).get('abbrev', '')
            game_id = game.get('id')
            logger.debug(f"  Game {game_id}: {away_abbrev} @ {home_abbrev}")

            if home_abbrev == team_upper or away_abbrev == team_upper:
                logger.info(f"Found game: {away_abbrev} @ {home_abbrev} (ID: {game_id})")
                return game_id

        logger.warning(f"No game found for {team_upper} on {lookup_date}")
        # List available games to help the user
        if games:
            available = [
                f"{g.get('awayTeam', {}).get('abbrev', '?')} @ "
                f"{g.get('homeTeam', {}).get('abbrev', '?')}"
                for g in games
            ]
            logger.info(f"Available games on {lookup_date}: {', '.join(available)}")
        return None
    except Exception as e:
        logger.error(f"Failed to look up games: {e}")
        return None
    finally:
        client.close()


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
            hits=12,
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
            shots=21,
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

    # Team color mapping keyed by team ID (as string, since _get_team_color
    # looks up "{team_id}.primary")
    color_map = {
        "6":  {"primary": (252, 181, 20), "text": (0, 0, 0)},       # BOS - Gold/Black
        "10": {"primary": (0, 32, 91), "text": (255, 255, 255)},    # TOR - Blue/White
        "8":  {"primary": (175, 30, 45), "text": (255, 255, 255)},  # MTL - Red/White
        "3":  {"primary": (0, 51, 160), "text": (255, 255, 255)},   # NYR - Blue/White
        "4":  {"primary": (247, 73, 2), "text": (0, 0, 0)},         # PHI - Orange/Black
        "5":  {"primary": (252, 181, 20), "text": (0, 0, 0)},       # PIT - Gold/Black
        "21": {"primary": (111, 38, 61), "text": (255, 255, 255)},  # COL - Burgundy/White
        "22": {"primary": (4, 30, 66), "text": (252, 76, 2)},       # EDM - Navy/Orange
        "20": {"primary": (210, 0, 28), "text": (255, 255, 255)},   # CGY - Red/White
        "23": {"primary": (0, 32, 91), "text": (255, 255, 255)},    # VAN - Blue/White
        "55": {"primary": (0, 22, 40), "text": (153, 217, 217)},    # SEA - Navy/Ice
        "26": {"primary": (17, 17, 17), "text": (162, 170, 173)},   # LAK - Black/Silver
        "24": {"primary": (252, 76, 2), "text": (0, 0, 0)},         # ANA - Orange/Black
        "28": {"primary": (0, 109, 117), "text": (255, 255, 255)},  # SJS - Teal/White
        "54": {"primary": (185, 151, 91), "text": (51, 63, 72)},    # VGK - Gold/Grey
        "25": {"primary": (0, 104, 71), "text": (255, 255, 255)},   # DAL - Green/White
        "30": {"primary": (2, 73, 48), "text": (255, 255, 255)},    # MIN - Green/White
        "52": {"primary": (4, 30, 66), "text": (255, 255, 255)},    # WPG - Navy/White
        "18": {"primary": (255, 182, 18), "text": (0, 0, 0)},       # NSH - Gold/Black
        "19": {"primary": (0, 47, 135), "text": (255, 255, 255)},   # STL - Blue/White
        "16": {"primary": (207, 10, 44), "text": (255, 255, 255)},  # CHI - Red/White
        "17": {"primary": (206, 17, 38), "text": (255, 255, 255)},  # DET - Red/White
        "14": {"primary": (0, 40, 104), "text": (255, 255, 255)},   # TBL - Blue/White
        "13": {"primary": (185, 29, 71), "text": (255, 255, 255)},  # FLA - Red/White
        "12": {"primary": (206, 17, 38), "text": (255, 255, 255)},  # CAR - Red/White
        "2":  {"primary": (0, 51, 160), "text": (255, 255, 255)},   # NYI - Blue/White
        "1":  {"primary": (206, 17, 38), "text": (255, 255, 255)},  # NJD - Red/White
        "15": {"primary": (200, 16, 46), "text": (255, 255, 255)},  # WSH - Red/White
        "29": {"primary": (0, 38, 84), "text": (255, 255, 255)},    # CBJ - Navy/White
        "9":  {"primary": (200, 16, 46), "text": (255, 255, 255)},  # OTT - Red/White
        "7":  {"primary": (0, 38, 84), "text": (255, 255, 255)},    # BUF - Navy/White
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

    def __init__(self, matrix, delay=5, loop=False, home_team="BOS", away_team="TOR",
                 live_stats=None):
        self.matrix = matrix
        self.delay = delay
        self.loop = loop
        self.sleepEvent = Event()
        self.live_mode = live_stats is not None

        if live_stats:
            # Use live data from the NHL API
            self.home_team = live_stats.home_team_abbrev
            self.away_team = live_stats.away_team_abbrev
            self.stats = live_stats
            self.data = create_mock_data_object(self.home_team, self.away_team)
            self.data.current_game_id = live_stats.game_id
        else:
            # Use mock data
            self.home_team = home_team
            self.away_team = away_team
            self.stats = create_mock_game_stats(home_team, away_team)
            self.data = create_mock_data_object(home_team, away_team)

        source = "Live" if self.live_mode else "Mock"
        logger.info(f"Testing game stats ({source}): {self.away_team} @ {self.home_team}")
        logger.info(f"Stats: {self.away_team} {self.stats.away_stats.shots} SOG, "
                   f"{self.home_team} {self.stats.home_stats.shots} SOG")

    def run(self):
        """Run the test display."""
        # Give the emulator window time to initialize
        self.sleepEvent.wait(0.5)

        try:
            # Patch GameStoryWorker.get_game_stats to return our stats (live or mock)
            with patch.object(GameStoryWorker, 'get_game_stats', return_value=self.stats):
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

    # Resolve live stats if requested
    live_stats = None
    game_id = commandArgs.game_id

    if commandArgs.team and not game_id:
        # Look up game ID by team + date
        game_id = find_game_id_for_team(commandArgs.team, commandArgs.date)
        if not game_id:
            print(f"ERROR: No game found for {commandArgs.team}"
                  f"{' on ' + commandArgs.date if commandArgs.date else ' today'}. "
                  f"Falling back to mock data.")

    if game_id:
        live_stats = fetch_live_stats(game_id)
        if not live_stats:
            print(f"ERROR: Could not fetch stats for game {game_id}. Falling back to mock data.")

    if live_stats:
        print(f"Data: LIVE (game {live_stats.game_id})")
        print(f"Teams: {live_stats.away_team_abbrev} @ {live_stats.home_team_abbrev}")
        print(f"State: {live_stats.game_state}, Period: {live_stats.period}")
    else:
        print("Data: Mock")
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
        away_team=commandArgs.away_team,
        live_stats=live_stats
    )
    test.run()

    print("\nTest complete!")


if __name__ == "__main__":
    main()
