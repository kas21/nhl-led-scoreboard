"""
Game Stats board module - Displays game comparison statistics.

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


class GameStatsBoard(BoardBase):
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
        """Render the game stats display."""
        # Get current game ID from data
        game_id = getattr(self.data, 'current_game_id', None)
        if not game_id:
            debug.warning("GameStatsBoard: No current game ID available")
            return

        debug.info(f"GameStatsBoard: Looking for cached stats for game {game_id}")

        # Get cached stats from worker
        stats = GameStoryWorker.get_game_stats(game_id)
        if not stats:
            debug.warning(f"GameStatsBoard: No cached stats for game {game_id}")
            self._render_no_data()
            return

        # Debug: Log all the stat values we received
        debug.info(
            f"GameStatsBoard: Retrieved stats - "
            f"HOME: shots={stats.home_stats.shots}, hits={stats.home_stats.hits}, "
            f"faceoff={stats.home_stats.faceoff_pct}%, pp={stats.home_stats.power_play_goals}/{stats.home_stats.power_play_opportunities}"
        )
        debug.info(
            f"GameStatsBoard: Retrieved stats - "
            f"AWAY: shots={stats.away_stats.shots}, hits={stats.away_stats.hits}, "
            f"faceoff={stats.away_stats.faceoff_pct}%, pp={stats.away_stats.power_play_goals}/{stats.away_stats.power_play_opportunities}"
        )

        # Get team colors
        home_color = self._get_team_color(stats.home_team_id)
        away_color = self._get_team_color(stats.away_team_id)

        debug.info(
            f"GameStatsBoard: Rendering stats for "
            f"{stats.away_team_abbrev} @ {stats.home_team_abbrev}"
        )

        # Combined stats screen (shots, hits, faceoff)
        combined_cats = {'shots', 'hits', 'faceoff'}
        has_combined = any(cat in combined_cats for cat in self.categories)

        if has_combined and not self.sleepEvent.is_set():
            self.matrix.clear()
            self._render_combined_stats(stats, home_color, away_color)
            self.matrix.render()
            self.sleepEvent.wait(self.display_duration)

        # Render remaining categories individually (powerplay, blocked, etc.)
        for category in self.categories:
            if self.sleepEvent.is_set():
                break
            if category in combined_cats or category not in self.STAT_LABELS:
                continue

            self.matrix.clear()
            self._render_stat_category(stats, category, home_color, away_color)
            self.matrix.render()
            self.sleepEvent.wait(self.display_duration)

    def _render_stat_category(
        self,
        stats: GameStoryStats,
        category: str,
        home_color: Tuple[int, int, int],
        away_color: Tuple[int, int, int]
    ):
        """Render a single stat category comparison with team header."""
        label = self.STAT_LABELS.get(category, category.upper())

        if category == 'faceoff':
            self._render_faceoff_stat(stats, home_color, away_color)
        elif category == 'powerplay':
            self._render_powerplay_stat(stats, home_color, away_color)
        else:
            # Standard comparison bars (shots, hits, blocked)
            home_val, away_val = self._get_stat_values(stats, category)
            self._render_comparison_stat(
                stats, label, home_val, away_val, home_color, away_color
            )

    def _render_comparison_stat(
        self,
        stats: GameStoryStats,
        label: str,
        home_val: int,
        away_val: int,
        home_color: Tuple[int, int, int],
        away_color: Tuple[int, int, int]
    ):
        """Render a comparison stat as a labeled split bar with team header."""
        # Calculate percentage split
        total = home_val + away_val
        left_pct = (home_val / total * 100) if total > 0 else 50

        # Adjust layout based on display size
        if self.display_width >= 128:
            bar_width = 100
            bar_height = 8
            font = self.font
        else:
            bar_width = 50
            bar_height = 6
            font = self.font

        # Calculate bar position (centered)
        bar_x = (self.display_width - bar_width) // 2

        # Draw header and position content below it
        header_height = self._render_header(
            stats, home_color, away_color, bar_x, bar_width
        )
        # Center the stat vertically in remaining space
        stat_bbox = font.getbbox("X")
        stat_label_h = stat_bbox[3] - stat_bbox[1]
        stat_total_h = stat_label_h + 2 + bar_height  # label + spacing + bar
        available = self.display_height - header_height
        y_pos = header_height + max(0, (available - stat_total_h) // 2)

        # pre_draw redraws the header on each animation frame
        def draw_header():
            self._render_header(
                stats, home_color, away_color, bar_x, bar_width
            )

        if self.animate_bars:
            self.chart.animate_split_bar(
                position=(bar_x, y_pos),
                left_pct=left_pct,
                render_callback=self.matrix.render,
                clear_callback=self.matrix.clear,
                sleep_func=self._animation_sleep,
                width=bar_width,
                height=bar_height,
                left_color=home_color,
                right_color=away_color,
                duration=0.5,
                frames=15,
                title=label,
                left_label=str(home_val),
                right_label=str(away_val),
                font=font,
                left_label_color=home_color,
                right_label_color=away_color,
                animation="fill",
                pre_draw=draw_header
            )
        else:
            self.chart.draw_split_bar(
                position=(bar_x, y_pos),
                left_pct=left_pct,
                width=bar_width,
                height=bar_height,
                left_color=home_color,
                right_color=away_color,
                title=label,
                left_label=str(home_val),
                right_label=str(away_val),
                font=font,
                left_label_color=home_color,
                right_label_color=away_color
            )

    def _render_faceoff_stat(
        self,
        stats: GameStoryStats,
        home_color: Tuple[int, int, int],
        away_color: Tuple[int, int, int]
    ):
        """Render faceoff percentage split bar with team header."""
        home_pct = stats.home_stats.faceoff_pct
        away_pct = 100 - home_pct

        # Adjust layout based on display size
        if self.display_width >= 128:
            bar_width = 100
            bar_height = 8
            font = self.font
        else:
            bar_width = 50
            bar_height = 6
            font = self.font

        # Calculate bar position (centered)
        bar_x = (self.display_width - bar_width) // 2

        # Draw header and position content below it
        header_height = self._render_header(
            stats, home_color, away_color, bar_x, bar_width
        )
        stat_bbox = font.getbbox("X")
        stat_label_h = stat_bbox[3] - stat_bbox[1]
        stat_total_h = stat_label_h + 2 + bar_height
        available = self.display_height - header_height
        y_pos = header_height + max(0, (available - stat_total_h) // 2)

        home_label = f"{home_pct:.0f}%"
        away_label = f"{away_pct:.0f}%"

        def draw_header():
            self._render_header(
                stats, home_color, away_color, bar_x, bar_width
            )

        if self.animate_bars:
            self.chart.animate_split_bar(
                position=(bar_x, y_pos),
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
                title="FACEOFF %",
                left_label=home_label,
                right_label=away_label,
                font=font,
                left_label_color=home_color,
                right_label_color=away_color,
                animation="fill",
                pre_draw=draw_header
            )
        else:
            self.chart.draw_split_bar(
                position=(bar_x, y_pos),
                left_pct=home_pct,
                width=bar_width,
                height=bar_height,
                left_color=home_color,
                right_color=away_color,
                title="FACEOFF %",
                left_label=home_label,
                right_label=away_label,
                font=font,
                left_label_color=home_color,
                right_label_color=away_color
            )

    def _render_combined_stats(
        self,
        stats: GameStoryStats,
        home_color: Tuple[int, int, int],
        away_color: Tuple[int, int, int]
    ):
        """Render shots, hits, and faceoffs on one screen with sequential animation."""
        font = self.font

        # Build stat definitions: (title, left_label, right_label, left_pct)
        stat_defs = []

        home_shots, away_shots = stats.home_stats.shots, stats.away_stats.shots
        total_shots = home_shots + away_shots
        stat_defs.append((
            'SHOTS', str(home_shots), str(away_shots),
            (home_shots / total_shots * 100) if total_shots > 0 else 50
        ))

        home_hits, away_hits = stats.home_stats.hits, stats.away_stats.hits
        total_hits = home_hits + away_hits
        stat_defs.append((
            'HITS', str(home_hits), str(away_hits),
            (home_hits / total_hits * 100) if total_hits > 0 else 50
        ))

        home_fo = stats.home_stats.faceoff_pct
        stat_defs.append((
            'FACEOFF %', f"{home_fo:.0f}%", f"{100 - home_fo:.0f}%",
            home_fo
        ))

        # Layout based on display size
        if self.display_width >= 128:
            bar_width = 100
            bar_height = 6
            stat_gap = 4
        else:
            bar_width = 50
            bar_height = 3
            stat_gap = 2

        bar_x = (self.display_width - bar_width) // 2
        label_spacing = 2

        # Draw header and get vertical offset
        header_height = self._render_header(
            stats, home_color, away_color, bar_x, bar_width
        )

        # Measure label height from font
        sample_bbox = font.getbbox("X")
        label_height = sample_bbox[3] - sample_bbox[1]
        stat_height = label_height + label_spacing + bar_height

        # Center the block of stats in remaining space below header
        total_block = stat_height * len(stat_defs) + stat_gap * (len(stat_defs) - 1)
        available_height = self.display_height - header_height
        y_start = header_height + max(0, (available_height - total_block) // 2)

        y_positions = [y_start + i * (stat_height + stat_gap) for i in range(len(stat_defs))]

        # Helper to draw header (needed for animation pre_draw since clear wipes it)
        def draw_header():
            self._render_header(stats, home_color, away_color, bar_x, bar_width)

        # Helper to draw a single stat statically
        def draw_stat(idx):
            title, left_label, right_label, left_pct = stat_defs[idx]
            self.chart.draw_split_bar(
                position=(bar_x, y_positions[idx]),
                left_pct=left_pct,
                width=bar_width,
                height=bar_height,
                left_color=home_color,
                right_color=away_color,
                title=title,
                left_label=left_label,
                right_label=right_label,
                font=font,
                left_label_color=home_color,
                right_label_color=away_color,
                label_spacing=label_spacing
            )

        if self.animate_bars:
            # Animate each stat sequentially; pre_draw redraws header + completed stats
            for stat_idx in range(len(stat_defs)):
                if self.sleepEvent.is_set():
                    break

                # Closure to redraw header and all previously completed stats
                def make_pre_draw(completed):
                    def pre_draw():
                        draw_header()
                        for j in range(completed):
                            draw_stat(j)
                    return pre_draw

                title, left_label, right_label, left_pct = stat_defs[stat_idx]
                self.chart.animate_split_bar(
                    position=(bar_x, y_positions[stat_idx]),
                    left_pct=left_pct,
                    render_callback=self.matrix.render,
                    clear_callback=self.matrix.clear,
                    sleep_func=self._animation_sleep,
                    width=bar_width,
                    height=bar_height,
                    left_color=home_color,
                    right_color=away_color,
                    duration=0.5,
                    frames=15,
                    title=title,
                    left_label=left_label,
                    right_label=right_label,
                    font=font,
                    left_label_color=home_color,
                    right_label_color=away_color,
                    label_spacing=label_spacing,
                    animation="fill",
                    pre_draw=make_pre_draw(stat_idx)
                )
        else:
            for idx in range(len(stat_defs)):
                draw_stat(idx)

    def _render_powerplay_stat(
        self,
        stats: GameStoryStats,
        home_color: Tuple[int, int, int],
        away_color: Tuple[int, int, int]
    ):
        """Render power play statistics with ratio blocks and team header."""
        home_pp = stats.home_stats
        away_pp = stats.away_stats

        # Adjust layout based on display size
        if self.display_width >= 128:
            bar_width = 100
            label_width = 30
            block_width = 6
            block_height = 6
            font = self.font
        else:
            bar_width = 50
            label_width = 24
            block_width = 4
            block_height = 5
            font = self.font

        bar_x = (self.display_width - bar_width) // 2

        # Draw header
        header_height = self._render_header(
            stats, home_color, away_color, bar_x, bar_width
        )

        # Position content below header
        content_x = 2
        y_title = header_height + (2 if self.display_width >= 128 else 1)
        y_home = y_title + (14 if self.display_width >= 128 else 8)
        y_away = y_home + (14 if self.display_width >= 128 else 10)

        # Draw title
        self.matrix.draw_text(
            (content_x, y_title), "POWER PLAY", font, fill=(255, 255, 255)
        )

        # Draw home PP (use team abbreviation as label)
        self.chart.draw_power_play_stat(
            position=(content_x, y_home),
            label=stats.home_team_abbrev,
            goals=home_pp.power_play_goals,
            attempts=home_pp.power_play_opportunities,
            font=font,
            label_width=label_width,
            block_width=block_width,
            block_height=block_height,
            filled_color=home_color,
            text_color=home_color
        )

        # Draw away PP (use team abbreviation as label)
        self.chart.draw_power_play_stat(
            position=(content_x, y_away),
            label=stats.away_team_abbrev,
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
            return (255, 255, 255)

    def _get_team_text_color(self, team_id: int) -> Tuple[int, int, int]:
        """Get RGB tuple for a team's text/contrast color."""
        try:
            color = self.team_colors.color(f"{team_id}.text")
            return (color['r'], color['g'], color['b'])
        except Exception:
            return (255, 255, 255)

    def _get_game_status_text(self, stats: GameStoryStats) -> str:
        """Get display text for current game state."""
        state = stats.game_state.upper() if stats.game_state else ""
        if state in ("FINAL", "OFF"):
            return "FINAL"
        if stats.period > 3:
            return "OT"
        if stats.period > 0:
            return f"P{stats.period} {stats.clock}"
        return ""

    def _render_header(
        self,
        stats: GameStoryStats,
        home_color: Tuple[int, int, int],
        away_color: Tuple[int, int, int],
        bar_x: int,
        bar_width: int
    ) -> int:
        """
        Draw team name pills and game status at the top of the display.

        Layout: [HOME]  STATUS  [AWAY]
        Each team name is drawn as text on a colored pill (rectangle background).

        Returns:
            Total header height in pixels (pill + bottom gap).
        """
        font = self.font
        home_text_color = self._get_team_text_color(stats.home_team_id)
        away_text_color = self._get_team_text_color(stats.away_team_id)
        status_text = self._get_game_status_text(stats)

        # Measure text dimensions
        home_bbox = font.getbbox(stats.home_team_abbrev)
        home_text_w = home_bbox[2] - home_bbox[0]
        text_h = home_bbox[3] - home_bbox[1]

        away_bbox = font.getbbox(stats.away_team_abbrev)
        away_text_w = away_bbox[2] - away_bbox[0]

        # Pill padding
        pad_x = 2
        pad_y = 1
        pill_h = text_h + pad_y * 2
        y = 0

        # Home team pill (left-aligned with bar area)
        home_pill_w = home_text_w + pad_x * 2
        self.matrix.draw_rectangle(
            (bar_x, y), (home_pill_w, pill_h), fill=home_color
        )
        self.matrix.draw_text(
            (bar_x + pad_x, y + pad_y),
            stats.home_team_abbrev, font, fill=home_text_color
        )

        # Away team pill (right-aligned with bar area)
        away_pill_w = away_text_w + pad_x * 2
        away_pill_x = bar_x + bar_width - away_pill_w
        self.matrix.draw_rectangle(
            (away_pill_x, y), (away_pill_w, pill_h), fill=away_color
        )
        self.matrix.draw_text(
            (away_pill_x + pad_x, y + pad_y),
            stats.away_team_abbrev, font, fill=away_text_color
        )

        # Game status text (centered in bar area)
        if status_text:
            status_bbox = font.getbbox(status_text)
            status_w = status_bbox[2] - status_bbox[0]
            status_x = bar_x + (bar_width - status_w) // 2
            self.matrix.draw_text(
                (status_x, y + pad_y),
                status_text, font, fill=(255, 255, 255)
            )

        # Return total header height including gap below
        header_gap = 2 if self.display_width >= 128 else 1
        return pill_h + header_gap

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
