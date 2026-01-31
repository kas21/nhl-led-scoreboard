"""
Live Scoreboard Board - Modern implementation using Game model.

Displays real-time game scoreboard during live games with period, clock, and score.
Periodically shows an animated stats banner with shots, hits, and faceoff stats.
Handles all rendering logic directly using modern Game model.

This is the modern board implementation used in the 'live' state, while
the legacy ScoreboardRenderer remains intact for fallback rendering.
"""
import logging
from typing import Optional

from PIL import Image

from boards.base_board import BoardBase
from nhl_api.models import Game
from nhl_api.workers import LiveGameWorker, GameStoryWorker
from renderer.logos import LogoRenderer
from renderer.stats_banner import StatsBanner
from utils import get_file

debug = logging.getLogger("scoreboard")


class LiveScoreboardBoard(BoardBase):
    """
    Modern live scoreboard board using Game model.

    Shows current game state including score, period, and time. Periodically
    displays an animated stats banner. Handles all rendering logic directly.
    """

    def __init__(self, data, matrix, sleepEvent):
        super().__init__(data, matrix, sleepEvent)

        # Get the scoreboard-specific layout (same as ScoreboardRenderer)
        self.layout = data.config.config.layout.get_board_layout('scoreboard')
        self.team_colors = data.config.team_colors

        # Load config with automatic priority: central config -> board config -> defaults
        self.display_duration = self.get_config_value('display_duration', None)
        if self.display_duration is None:
            # Fall back to live_game_refresh_rate from main config
            self.display_duration = data.config.live_game_refresh_rate

        # Extended display configuration for predominant board behavior
        self.total_display_duration = self.get_config_value('total_display_duration', 180)
        self.refresh_interval = self.get_config_value('refresh_interval', 9)

        self.show_power_play_details = self.get_config_value('show_power_play_details', True)

        # Logo renderers - will be initialized when we know team abbrevs
        self.home_logo_renderer = None
        self.away_logo_renderer = None

        # Stats banner configuration
        self.stats_banner_enabled = self.get_config_value('stats_banner_enabled', True)
        self.stats_banner_frequency = self.get_config_value('stats_banner_frequency', 5)
        self.stats_banner_stat_duration = self.get_config_value('stats_banner_stat_duration', 2.0)
        self.stats_banner_animation_duration = self.get_config_value('stats_banner_animation_duration', 0.3)
        self.stats_banner_categories = self.get_config_value('stats_banner_categories', ['shots', 'hits', 'faceoff'])
        # Persist banner counter across board re-instantiations
        self._banner_counter = getattr(data, '_stats_banner_counter', 0)
        self._stats_banner = None  # Lazy initialized

    def _init_logo_renderers(self, game: Game):
        """Initialize logo renderers for home and away teams."""
        self.home_logo_renderer = LogoRenderer(
            self.matrix,
            self.data.config,
            self.layout.home_logo,
            game.home_team.abbrev,
            'scoreboard',
            'home'
        )
        self.away_logo_renderer = LogoRenderer(
            self.matrix,
            self.data.config,
            self.layout.away_logo,
            game.away_team.abbrev,
            'scoreboard',
            'away'
        )

    def render(self):
        """Render the live scoreboard display with periodic refresh.

        Displays the scoreboard for total_display_duration seconds, refreshing
        every refresh_interval seconds with fresh cached data from the worker.
        """
        debug.debug("LiveScoreboardBoard: Starting render cycle")

        elapsed_time = 0

        while elapsed_time < self.total_display_duration and not self.sleepEvent.is_set():
            try:
                game_id = getattr(self.data, 'current_game_id', None)
                if not game_id:
                    debug.warning("LiveScoreboardBoard: No current game ID available")
                    return

                # Get fresh cached data from worker (updated every 5s)
                cached_overview = LiveGameWorker.get_cached_overview(game_id)
                if not cached_overview:
                    debug.warning(f"LiveScoreboardBoard: No cached overview for game {game_id}")
                    return

                # Create Game object from cached data
                game = Game.from_dict(cached_overview)

                # Initialize logo renderers if needed
                if not self.home_logo_renderer or not self.away_logo_renderer:
                    self._init_logo_renderers(game)

                # Parse situation data
                situation = self._parse_situation(cached_overview)

                # Clear and render
                self.matrix.clear()
                self._draw_live(game, situation)

                # Show indicators
                if self.data.network_issues:
                    self.matrix.network_issue_indicator()
                if self.data.newUpdate and not self.data.config.clock_hide_indicators:
                    self.matrix.update_indicator()

                # Check stats banner
                self._banner_counter += 1
                self.data._stats_banner_counter = self._banner_counter

                refresh_num = int(elapsed_time / self.refresh_interval) + 1
                debug.debug(f"LiveScoreboardBoard: Refresh {refresh_num}, "
                           f"Banner {self._banner_counter}/{self.stats_banner_frequency}")

                if (self.stats_banner_enabled and
                    self._banner_counter >= self.stats_banner_frequency):
                    debug.debug("LiveScoreboardBoard: Triggering stats banner")
                    self._banner_counter = 0
                    self.data._stats_banner_counter = 0
                    self._show_stats_banner(game, situation)

                # Wait for next refresh
                self.sleepEvent.wait(self.refresh_interval)
                elapsed_time += self.refresh_interval

            except Exception as e:
                debug.error(f"LiveScoreboardBoard: Error during render: {e}")
                import traceback
                traceback.print_exc()
                self.sleepEvent.wait(self.refresh_interval)
                elapsed_time += self.refresh_interval

        debug.debug(f"LiveScoreboardBoard: Completed after {elapsed_time}s")

    def _parse_situation(self, overview: dict) -> dict:
        """Parse game situation (power plays, skater counts) from raw overview."""
        situation = {
            'home_powerplay': False,
            'away_powerplay': False,
            'home_skaters': 5,
            'away_skaters': 5,
            'pp_time_remaining': None
        }

        try:
            if overview.get("situation"):
                situation['home_skaters'] = overview["situation"]["homeTeam"]["strength"]
                situation['away_skaters'] = overview["situation"]["awayTeam"]["strength"]

                if overview["situation"]["homeTeam"].get("situationDescriptions"):
                    if "PP" in overview["situation"]["homeTeam"]["situationDescriptions"]:
                        situation['home_powerplay'] = True
                        situation['pp_time_remaining'] = overview["situation"].get("timeRemaining")

                if overview["situation"]["awayTeam"].get("situationDescriptions"):
                    if "PP" in overview["situation"]["awayTeam"]["situationDescriptions"]:
                        situation['away_powerplay'] = True
                        situation['pp_time_remaining'] = overview["situation"].get("timeRemaining")
        except Exception as e:
            debug.warning(f"Error parsing situation data: {e}")

        return situation

    def _draw_live(self, game: Game, situation: dict):
        """Draw the live game scoreboard."""
        # Draw background and logos (same as ScoreboardRenderer)
        display_width = self.matrix.width
        display_height = self.matrix.height

        # Draw background rectangles for team areas
        self.matrix.draw_rectangle((0, 0), ((display_width/2), display_height), (0, 0, 0))
        self.away_logo_renderer.render()

        self.matrix.draw_rectangle(((display_width/2), 0), ((display_width), display_height), (0, 0, 0))
        self.home_logo_renderer.render()

        # Draw center gradient
        gradient = Image.open(get_file('assets/images/64x32_scoreboard_center_gradient.png'))
        if display_height == 64:
            gradient = Image.open(get_file('assets/images/128x64_scoreboard_center_gradient.png'))
        self.matrix.draw_image((display_width/2, 0), gradient, align="center")

        # Get the info
        period = game.period.ordinal if game.period else "1st"
        clock = game.time_remaining or "20:00"
        score = f"{game.score.away}-{game.score.home}"

        # Draw the period and clock
        self.matrix.draw_text_layout(
            self.layout.period,
            period,
        )
        self.matrix.draw_text_layout(
            self.layout.clock,
            clock
        )

        # Draw the score
        self.matrix.draw_text_layout(
            self.layout.score,
            score
        )

        self.matrix.render()

        # Draw power play indicators/details if applicable
        if situation['away_powerplay'] or situation['home_powerplay']:
            if self.show_power_play_details:
                debug.debug("Drawing power play details")
                self._draw_power_play_details(game, situation)
            else:
                debug.debug("Drawing power play indicators")
                self._draw_power_play_indicators(situation)

    def _draw_power_play_details(self, game: Game, situation: dict):
        """Draw detailed power play information."""
        # Get the power play info
        pp_time = situation['pp_time_remaining'] or "1:23"
        max_skaters = max(situation['home_skaters'], situation['away_skaters'])
        min_skaters = min(situation['home_skaters'], situation['away_skaters'])

        # Determine which team is on power play
        if situation['home_powerplay']:
            pp_team_id = game.home_team.id
            pp_team_abbrev = game.home_team.abbrev
            is_home_pp = True
        else:
            pp_team_id = game.away_team.id
            pp_team_abbrev = game.away_team.abbrev
            is_home_pp = False

        # Get team colors
        pp_team_color = self.team_colors.color(f"{pp_team_id}.primary")
        text_color = self.team_colors.color(f"{pp_team_id}.text")

        # Build power play text - varies on matrix size
        if self.matrix.width < 128:
            pp_text = "PP"
        else:
            pp_text = f"{pp_team_abbrev} PP {max_skaters}-{min_skaters}"

        debug.debug(f"Power Play Info: {pp_team_abbrev} {max_skaters}-{min_skaters}")

        # Draw based on which team has power play
        if is_home_pp:
            self.matrix.draw_text_layout(
                self.layout.pp_badge_home_time,
                pp_time
            )
            self.matrix.draw_text_layout(
                self.layout.pp_badge_home,
                pp_text,
                backgroundColor=(pp_team_color['r'], pp_team_color['g'], pp_team_color['b']),
                fillColor=(text_color['r'], text_color['g'], text_color['b'])
            )
        else:
            self.matrix.draw_text_layout(
                self.layout.pp_badge_away_time,
                pp_time
            )
            self.matrix.draw_text_layout(
                self.layout.pp_badge_away,
                pp_text,
                backgroundColor=(pp_team_color['r'], pp_team_color['g'], pp_team_color['b']),
                fillColor=(text_color['r'], text_color['g'], text_color['b'])
            )

        self.matrix.render()

    def _show_stats_banner(self, game: Game, situation: dict):
        """Display the animated stats banner overlay."""
        # Skip if power play is active (conflicts with bottom indicators)
        if situation['away_powerplay'] or situation['home_powerplay']:
            debug.debug("StatsBanner: Skipping due to active power play")
            return

        # Get stats from GameStoryWorker
        stats = GameStoryWorker.get_game_stats(game.id)
        if not stats:
            debug.debug("StatsBanner: No stats available yet")
            return

        # Initialize banner if needed
        if not self._stats_banner:
            self._stats_banner = StatsBanner(
                self.matrix,
                self.team_colors,
                self.data.config.layout.font
            )

        # Capture current scoreboard state
        base_image = self.matrix.image.copy()

        # Run banner animation sequence
        self._stats_banner.show_stats_banner(
            stats=stats,
            home_team_id=game.home_team.id,
            away_team_id=game.away_team.id,
            base_image=base_image,
            sleep_func=self.sleepEvent.wait,
            is_interrupted=self.sleepEvent.is_set,
            stat_duration=self.stats_banner_stat_duration,
            animation_duration=self.stats_banner_animation_duration,
            categories=self.stats_banner_categories
        )

    def _draw_power_play_indicators(self, situation: dict):
        """Draw simple power play indicators (colored lines)."""
        away_num_skaters = situation['away_skaters']
        home_num_skaters = situation['home_skaters']

        # Color mapping based on number of skaters
        yellow = (255, 255, 0)
        red = (255, 0, 0)
        green = (0, 255, 0)
        colors = {6: green, 5: green, 4: yellow, 3: red}

        # Draw away team indicator (left side, bottom)
        away_color = colors.get(away_num_skaters, green)
        self.matrix.draw.line(
            (0, self.matrix.height - 1, 3, self.matrix.height - 1),
            fill=away_color,
        )
        self.matrix.draw.line(
            (0, self.matrix.height - 2, 1, self.matrix.height - 2),
            fill=away_color,
        )
        self.matrix.draw.line(
            (0, self.matrix.height - 3, 0, self.matrix.height - 3),
            fill=away_color,
        )

        # Draw home team indicator (right side, bottom)
        home_color = colors.get(home_num_skaters, green)
        self.matrix.draw.line(
            (self.matrix.width - 1, self.matrix.height - 1, self.matrix.width - 4, self.matrix.height - 1),
            fill=home_color,
        )
        self.matrix.draw.line(
            (self.matrix.width - 1, self.matrix.height - 2, self.matrix.width - 2, self.matrix.height - 2),
            fill=home_color,
        )
        self.matrix.draw.line(
            (self.matrix.width - 1, self.matrix.height - 3, self.matrix.width - 1, self.matrix.height - 3),
            fill=home_color,
        )

        self.matrix.render()
