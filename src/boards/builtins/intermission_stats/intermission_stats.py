"""
Intermission Stats board module - Displays game comparison statistics.

Shows animated chart comparisons of team stats during intermission and post-game:
- Shots on Goal
- Hits
- Faceoff Percentage
- Power Play
"""

import logging
from typing import Optional, Tuple

from boards.base_board import BoardBase
from nhl_api.models import GameStoryStats
from nhl_api.workers import GameStoryWorker
from renderer.charts import ChartRenderer

debug = logging.getLogger("scoreboard")


class IntermissionStatsBoard(BoardBase):
    """
    Displays game comparison statistics during intermission and post-game.

    Uses ChartRenderer to display animated bar charts comparing team stats.
    """

    # Mapping of category IDs to display labels
    STAT_LABELS = {
        'shots': 'SHOTS',
        'hits': 'HITS',
        'faceoff': 'FACEOFF %',
        'powerplay': 'POWER PLAY',
        'blocked': 'BLOCKED',
    }

    def __init__(self, data, matrix, sleepEvent):
        super().__init__(data, matrix, sleepEvent)

        self.chart = ChartRenderer(matrix)
        self.team_colors = data.config.team_colors

        # Load fonts from layout
        self.font = data.config.layout.font
        self.font_large = data.config.layout.font_large

        # Load config with automatic priority: central config -> board config -> defaults
        self.display_duration = self.get_config_value('display_duration', 5)
        self.animate_bars = self.get_config_value('animate_bars', True)
        self.categories = self.get_config_value(
            'categories',
            ['shots', 'hits', 'faceoff', 'powerplay']
        )

    def render(self):
        """Render the intermission stats display."""
        # Get current game ID from data
        game_id = getattr(self.data, 'current_game_id', None)
        if not game_id:
            debug.warning("IntermissionStatsBoard: No current game ID available")
            return

        debug.info(f"IntermissionStatsBoard: Looking for cached stats for game {game_id}")

        # Get cached stats from worker
        stats = GameStoryWorker.get_game_stats(game_id)
        if not stats:
            debug.warning(f"IntermissionStatsBoard: No cached stats for game {game_id}")
            self._render_no_data()
            return

        # Debug: Log all the stat values we received
        debug.info(
            f"IntermissionStatsBoard: Retrieved stats - "
            f"HOME: shots={stats.home_stats.shots}, hits={stats.home_stats.hits}, "
            f"faceoff={stats.home_stats.faceoff_pct}%, pp={stats.home_stats.power_play_goals}/{stats.home_stats.power_play_opportunities}"
        )
        debug.info(
            f"IntermissionStatsBoard: Retrieved stats - "
            f"AWAY: shots={stats.away_stats.shots}, hits={stats.away_stats.hits}, "
            f"faceoff={stats.away_stats.faceoff_pct}%, pp={stats.away_stats.power_play_goals}/{stats.away_stats.power_play_opportunities}"
        )

        # Get team colors
        home_color = self._get_team_color(stats.home_team_id)
        away_color = self._get_team_color(stats.away_team_id)

        debug.info(
            f"IntermissionStatsBoard: Rendering stats for "
            f"{stats.away_team_abbrev} @ {stats.home_team_abbrev}"
        )

        # Render each configured stat category
        for category in self.categories:
            if self.sleepEvent.is_set():
                break

            if category not in self.STAT_LABELS:
                continue

            self.matrix.clear()
            self._render_stat_category(stats, category, home_color, away_color)
            self.matrix.render()

            # Wait for display duration (or until interrupted)
            self.sleepEvent.wait(self.display_duration)

    def _render_stat_category(
        self,
        stats: GameStoryStats,
        category: str,
        home_color: Tuple[int, int, int],
        away_color: Tuple[int, int, int]
    ):
        """Render a single stat category comparison."""
        label = self.STAT_LABELS.get(category, category.upper())

        if category == 'faceoff':
            self._render_faceoff_stat(stats, home_color, away_color)
        elif category == 'powerplay':
            self._render_powerplay_stat(stats, home_color, away_color)
        else:
            # Standard comparison bars (shots, hits, blocked)
            home_val, away_val = self._get_stat_values(stats, category)
            self._render_comparison_stat(label, home_val, away_val, home_color, away_color)

    def _render_comparison_stat(
        self,
        label: str,
        home_val: int,
        away_val: int,
        home_color: Tuple[int, int, int],
        away_color: Tuple[int, int, int]
    ):
        """Render a simple comparison bar chart."""
        # Adjust layout based on display size
        if self.display_width >= 128:
            y_pos = 8
            bar_width = 70
            bar_height = 6
            label_width = 30
            font = self.font
        else:
            y_pos = 4
            bar_width = 35
            bar_height = 4
            label_width = 24
            font = self.font

        if self.animate_bars:
            self.chart.animate_comparison_bars(
                position=(2, y_pos),
                label=label,
                home_value=home_val,
                away_value=away_val,
                font=font,
                render_callback=self.matrix.render,
                clear_callback=self.matrix.clear,
                sleep_func=self._animation_sleep,
                max_bar_width=bar_width,
                bar_height=bar_height,
                label_width=label_width,
                home_color=home_color,
                away_color=away_color,
                duration=0.5,
                frames=15
            )
        else:
            self.chart.draw_comparison_bars(
                position=(2, y_pos),
                label=label,
                home_value=home_val,
                away_value=away_val,
                font=font,
                max_bar_width=bar_width,
                bar_height=bar_height,
                label_width=label_width,
                home_color=home_color,
                away_color=away_color
            )

    def _render_faceoff_stat(
        self,
        stats: GameStoryStats,
        home_color: Tuple[int, int, int],
        away_color: Tuple[int, int, int]
    ):
        """Render faceoff percentage split bar."""
        home_pct = stats.home_stats.faceoff_pct

        # Adjust layout based on display size
        if self.display_width >= 128:
            bar_width = 100
            bar_height = 8
            y_title = 4
            y_bar = 22
            font = self.font
        else:
            bar_width = 50
            bar_height = 6
            y_title = 2
            y_bar = 12
            font = self.font

        # Draw title
        self.matrix.draw_text((2, y_title), "FACEOFF %", font, fill=(255, 255, 255))

        # Calculate bar position (centered)
        bar_x = (self.display_width - bar_width) // 2

        if self.animate_bars:
            # Define pre_draw to redraw title during animation
            def pre_draw():
                self.matrix.draw_text((2, y_title), "FACEOFF %", font, fill=(255, 255, 255))

            self.chart.animate_split_bar(
                position=(bar_x, y_bar),
                left_pct=home_pct,
                render_callback=self.matrix.render,
                clear_callback=self.matrix.clear,
                sleep_func=self._animation_sleep,
                width=bar_width,
                height=bar_height,
                left_color=home_color,
                right_color=away_color,
                duration=0.5,
                frames=15,
                pre_draw=pre_draw
            )
        else:
            self.chart.draw_faceoff_stat(
                position=(bar_x, y_bar),
                home_pct=home_pct,
                font=font,
                bar_width=bar_width,
                bar_height=bar_height,
                home_color=home_color,
                away_color=away_color
            )

    def _render_powerplay_stat(
        self,
        stats: GameStoryStats,
        home_color: Tuple[int, int, int],
        away_color: Tuple[int, int, int]
    ):
        """Render power play statistics with ratio blocks."""
        home_pp = stats.home_stats
        away_pp = stats.away_stats

        # Adjust layout based on display size
        if self.display_width >= 128:
            y_title = 4
            y_home = 18
            y_away = 32
            label_width = 30
            block_width = 6
            block_height = 6
            font = self.font
        else:
            y_title = 2
            y_home = 10
            y_away = 20
            label_width = 24
            block_width = 4
            block_height = 5
            font = self.font

        # Draw title
        self.matrix.draw_text((2, y_title), "POWER PLAY", font, fill=(255, 255, 255))

        # Draw home PP
        self.chart.draw_power_play_stat(
            position=(2, y_home),
            label="HOME",
            goals=home_pp.power_play_goals,
            attempts=home_pp.power_play_opportunities,
            font=font,
            label_width=label_width,
            block_width=block_width,
            block_height=block_height,
            filled_color=home_color,
            text_color=home_color
        )

        # Draw away PP
        self.chart.draw_power_play_stat(
            position=(2, y_away),
            label="AWAY",
            goals=away_pp.power_play_goals,
            attempts=away_pp.power_play_opportunities,
            font=font,
            label_width=label_width,
            block_width=block_width,
            block_height=block_height,
            filled_color=away_color,
            text_color=away_color
        )

    def _get_stat_values(self, stats: GameStoryStats, category: str) -> Tuple[int, int]:
        """Extract home and away values for a stat category."""
        if category == 'shots':
            return stats.home_stats.shots, stats.away_stats.shots
        elif category == 'hits':
            return stats.home_stats.hits, stats.away_stats.hits
        elif category == 'blocked':
            return stats.home_stats.blocked_shots, stats.away_stats.blocked_shots
        return 0, 0

    def _get_team_color(self, team_id: int) -> Tuple[int, int, int]:
        """Get RGB tuple for a team's primary color."""
        try:
            color = self.team_colors.color(f"{team_id}.primary")
            return (color['r'], color['g'], color['b'])
        except Exception:
            # Default to white if color lookup fails
            return (255, 255, 255)

    def _animation_sleep(self, duration: float):
        """Sleep function for animations that respects sleep event."""
        self.sleepEvent.wait(duration)

    def _render_no_data(self):
        """Render a message when no stats are available."""
        self.matrix.clear()

        # Center the message
        text = "STATS LOADING..."
        x = 2
        y = self.display_height // 2 - 4

        self.matrix.draw_text((x, y), text, self.font, fill=(128, 128, 128))
        self.matrix.render()

        # Brief wait before returning
        self.sleepEvent.wait(2)
