"""
Live Scoreboard Board - renders the current game scoreboard during live games.

This board is specifically designed to be used in the 'live' state to show
the actual game scoreboard with alternating SOG (shots on goal) display.
"""
import logging

from boards.base_board import BoardBase
from data.scoreboard import Scoreboard
from renderer.scoreboard import ScoreboardRenderer

debug = logging.getLogger("scoreboard")


class LiveScoreboardBoard(BoardBase):
    """
    Displays the live game scoreboard.

    This board shows the current game state including score, period, time,
    and alternates showing shots on goal based on the configured frequency.
    """

    def __init__(self, data, matrix, sleepEvent):
        super().__init__(data, matrix, sleepEvent)

        # Track alternation for SOG display
        self.alternate_counter = getattr(data, '_live_scoreboard_counter', 1)
        self.sog_display_frequency = data.config.sog_display_frequency

    def render(self):
        """Render the live scoreboard with SOG alternation."""
        debug.debug("LiveScoreboardBoard: Rendering live scoreboard")

        try:
            # Get latest game data from LiveGameWorker cache
            # (refresh_overview uses the background worker's cache, so this is efficient)
            self.data.refresh_overview()
            scoreboard = Scoreboard(self.data.overview, self.data)

            # Create scoreboard renderer
            sbrenderer = ScoreboardRenderer(self.data, self.matrix, scoreboard)

            # Determine if we should show SOG based on counter
            sbrenderer.show_SOG = False
            if self.alternate_counter % self.sog_display_frequency == 0:
                sbrenderer.show_SOG = True
                debug.debug(f"LiveScoreboardBoard: Showing SOG (counter: {self.alternate_counter})")

            # Clear and render
            self.matrix.clear()
            sbrenderer.render()

            # Increment and store counter for next time
            self.alternate_counter += 1
            self.data._live_scoreboard_counter = self.alternate_counter

            # Show network/update indicators if needed
            if self.data.network_issues:
                self.matrix.network_issue_indicator()

            if self.data.newUpdate and not self.data.config.clock_hide_indicators:
                self.matrix.update_indicator()

            # Wait before returning (using live game refresh rate)
            display_duration = self.data.config.live_game_refresh_rate
            debug.debug(f"LiveScoreboardBoard: Waiting {display_duration} seconds")
            self.sleepEvent.wait(display_duration)

        except Exception as e:
            debug.error(f"LiveScoreboardBoard: Error rendering scoreboard: {e}")
            # Render error message or fallback
            self.matrix.clear()
