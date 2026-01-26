"""
Game Story Worker - Background data fetching for game stats during intermission.

Provides team comparison statistics (shots, hits, faceoffs, power play, etc.)
for display during intermission and post-game periods.
"""

import logging
from typing import Optional

from nhl_api.data import get_game_story
from nhl_api.models import GameStoryStats
from nhl_api.workers.base_worker import LifecycleWorker

debug = logging.getLogger("scoreboard")


class GameStoryWorker(LifecycleWorker[GameStoryStats]):
    """
    Background worker that fetches game story data for intermission stats display.

    This worker is tied to the same game lifecycle as LiveGameWorker and provides
    team comparison stats (shots, hits, faceoffs, power play, etc.) for display
    during intermission and post-game periods.

    Refresh intervals based on game state:
    - Live play: 30 seconds (stats update after each event)
    - Intermission: 60 seconds (stats frozen during break)
    - Post-game: 120 seconds (final stats, slow updates)

    Usage:
        worker = GameStoryWorker(data, scheduler)
        worker.start_monitoring(game_id)  # When game becomes active
        worker.stop_monitoring()           # When leaving game context
    """

    JOB_ID = "gameStoryWorker"
    CACHE_KEY_PREFIX = "game_story_stats"
    DEFAULT_TTL_BUFFER = 10

    def fetch_data(self, game_id: int) -> Optional[GameStoryStats]:
        """
        Fetch game story from NHL API and parse stats.

        Args:
            game_id: NHL game ID to fetch

        Returns:
            GameStoryStats dataclass, or None if fetch failed
        """
        try:
            debug.info(f"GameStoryWorker: Fetching game story for game {game_id}")
            raw_data = get_game_story(game_id)

            if not raw_data:
                debug.warning(f"GameStoryWorker: get_game_story returned None/empty for game {game_id}")
                return None

            debug.info(f"GameStoryWorker: Raw API response has {len(raw_data)} top-level keys: {list(raw_data.keys())}")

            # Check if teamGameStats exists in the response
            team_stats = raw_data.get('teamGameStats', [])
            debug.info(f"GameStoryWorker: teamGameStats has {len(team_stats)} entries")
            if team_stats:
                debug.info(f"GameStoryWorker: First stat entry: {team_stats[0] if team_stats else 'N/A'}")

            stats = GameStoryStats.from_dict(raw_data)
            debug.info(
                f"GameStoryWorker: Parsed stats for game {game_id} - "
                f"{stats.away_team_abbrev} @ {stats.home_team_abbrev}, "
                f"home_shots={stats.home_stats.shots}, away_shots={stats.away_stats.shots}"
            )
            return stats
        except Exception as e:
            debug.error(f"GameStoryWorker: Failed to parse game story: {e}", exc_info=True)
        return None

    def _on_fetch_success(self, stats: GameStoryStats):
        """Adjust refresh based on game state."""
        self._adjust_refresh_interval(stats)

    def _adjust_refresh_interval(self, stats: GameStoryStats):
        """
        Adjust refresh interval based on game state.

        Args:
            stats: Parsed game story stats
        """
        try:
            game_state = stats.game_state

            if game_state in ['FINAL', 'OFF']:
                # Game is over - use slow refresh (final stats rarely change)
                new_interval = 120
                debug.debug(f"GameStoryWorker: Game {game_state}, using 120s refresh")
            elif game_state in ['LIVE', 'CRIT']:
                # Live play - moderate refresh (stats update after plays)
                new_interval = 30
                debug.debug(f"GameStoryWorker: Live play ({game_state}), using 30s refresh")
            elif game_state in ['PRE', 'FUT']:
                # Pre-game - slower refresh
                new_interval = 60
                debug.debug(f"GameStoryWorker: Pre-game ({game_state}), using 60s refresh")
            else:
                # Unknown state - default
                new_interval = 60
                debug.debug(f"GameStoryWorker: Unknown state ({game_state}), using 60s refresh")

            if new_interval != self.current_refresh_seconds:
                self._update_refresh_interval(new_interval)
                debug.info(f"GameStoryWorker: Adjusted refresh to {new_interval}s (state: {game_state})")

        except Exception as e:
            debug.error(f"GameStoryWorker: Error adjusting interval: {e}")

    @classmethod
    def get_game_stats(cls, game_id: int) -> Optional[GameStoryStats]:
        """
        Convenience method to retrieve cached game stats.

        Args:
            game_id: NHL game ID

        Returns:
            GameStoryStats or None if not cached
        """
        cache_key = f"{cls.CACHE_KEY_PREFIX}_{game_id}"
        debug.info(f"GameStoryWorker.get_game_stats: Looking for cache key '{cache_key}'")

        stats = cls.get_cached_data(game_id)

        if stats:
            debug.info(
                f"GameStoryWorker.get_game_stats: Found cached stats - "
                f"home_shots={stats.home_stats.shots}, away_shots={stats.away_stats.shots}"
            )
        else:
            debug.warning(f"GameStoryWorker.get_game_stats: No cached stats found for game {game_id}")

        return stats
