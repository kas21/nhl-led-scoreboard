"""
Stats Leaders Worker - Background data fetching and caching for stats leaders.
"""
import logging
from typing import Dict, List, Optional

from nhl_api.data import get_skater_stats_leaders
from nhl_api.models import StatsLeadersData
from utils import sb_cache

debug = logging.getLogger("scoreboard")


class StatsLeadersWorker:
    """Background worker that fetches and caches stats leaders data."""

    JOB_ID = "statsLeadersWorker"
    CACHE_KEY = "nhl_stats_leaders"

    def __init__(self, data, scheduler, categories: List[str] = None, limit: int = 15, refresh_minutes: int = 30):
        self.data = data
        self.categories = categories or ['goals', 'assists', 'points']
        self.limit = limit
        self.refresh_minutes = refresh_minutes

        # Register with scheduler
        scheduler.add_job(
            self.fetch_and_cache,
            'interval',
            minutes=self.refresh_minutes,
            jitter=60,
            id=self.JOB_ID
        )

        debug.info(f"StatsLeadersWorker: Scheduled to refresh every {self.refresh_minutes} minutes")

        # Fetch immediately on startup
        self.fetch_and_cache()

    def fetch_and_cache(self):
        """Fetch stats leaders from API and cache the results."""
        try:
            all_leaders: Dict[str, StatsLeadersData] = {}

            for category in self.categories:
                raw_data = get_skater_stats_leaders(category=category, limit=self.limit)

                if raw_data and category in raw_data:
                    # Convert to structured data
                    leaders_data = StatsLeadersData.from_api_response(
                        category,
                        raw_data[category]
                    )
                    all_leaders[category] = leaders_data
                    debug.debug(f"StatsLeadersWorker: Fetched {len(leaders_data.leaders)} {category} leaders")

            if all_leaders:
                # Cache with TTL slightly longer than refresh interval
                expire_seconds = (self.refresh_minutes * 60) + 120
                sb_cache.set(self.CACHE_KEY, all_leaders, expire=expire_seconds)
                debug.info(f"StatsLeadersWorker: Cached {len(all_leaders)} categories")

        except Exception as e:
            debug.error(f"StatsLeadersWorker: Failed to fetch stats leaders: {e}")

    @staticmethod
    def get_cached_data() -> Optional[Dict[str, StatsLeadersData]]:
        """Retrieve cached stats leaders data."""
        return sb_cache.get(StatsLeadersWorker.CACHE_KEY)

    @staticmethod
    def get_category(category: str) -> Optional[StatsLeadersData]:
        """Get a specific category from cache."""
        data = StatsLeadersWorker.get_cached_data()
        if data:
            return data.get(category)
        return None
