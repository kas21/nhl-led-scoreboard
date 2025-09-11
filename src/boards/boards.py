"""
A Board is simply a display object with specific parameters made to be shown on screen.
    TODO: Make the board system customizable so that all the user needs to do is paste a board file and modify the
        config file to add the custom board.
"""
import debug
from boards.scoreticker import Scoreticker
from boards.seriesticker import Seriesticker
from boards.standings import Standings
from boards.team_summary import TeamSummary
from boards.clock import Clock
from boards.pbdisplay import pbDisplay
from boards.wxWeather import wxWeather
from boards.wxAlert import wxAlert
from boards.christmas import Christmas
from boards.seasoncountdown import SeasonCountdown
from boards.wxForecast import wxForecast
from boards.screensaver import screenSaver
from boards.stanley_cup_champions import StanleyCupChampions
from boards.player_stats import PlayerStatsRenderer
from time import sleep
from boards.ovi_tracker import OviTrackerRenderer
from boards.stats_leaders import StatsLeaders
from boards.stridekick import StrideKickRenderer
from boards.holidays import Holidays
import traceback

class Boards:
    def __init__(self):
        pass

    # Board handler for PushButton
    def _pb_board(self, data, matrix, sleepEvent):

        board = getattr(self, data.config.pushbutton_state_triggered1)
        board(data, matrix, sleepEvent)

    # Board handler for Weather Alert
    def _wx_alert(self, data, matrix, sleepEvent):

        board = getattr(self, "wxalert")
        board(data, matrix, sleepEvent)

    # Board handler for screensaver
    def _screensaver(self, data, matrix, sleepEvent):

        board = getattr(self, "screensaver")
        board(data, matrix, sleepEvent)

    # Board handler for Off day state
    def _off_day(self, data, matrix, sleepEvent):
        bord_index = 0
        while True:
            board = getattr(self, data.config.boards_off_day[bord_index])
            data.curr_board = data.config.boards_off_day[bord_index]

            if data.pb_trigger:
                debug.info('PushButton triggered....will display ' + data.config.pushbutton_state_triggered1 + ' board ' + "Overriding off_day -> " + data.config.boards_off_day[bord_index])
                if not data.screensaver:
                    data.pb_trigger = False
                board = getattr(self,data.config.pushbutton_state_triggered1)
                data.curr_board = data.config.pushbutton_state_triggered1
                bord_index -= 1

            if data.mqtt_trigger:
                debug.info('MQTT triggered....will display ' + data.mqtt_showboard + ' board ' + "Overriding off_day -> " + data.config.boards_off_day[bord_index])
                if not data.screensaver:
                    data.mqtt_trigger = False
                board = getattr(self,data.mqtt_showboard)
                data.curr_board = data.mqtt_showboard
                bord_index -= 1

            # Display the Weather Alert board
            if data.wx_alert_interrupt:
                debug.info('Weather Alert triggered in off day loop....will display weather alert board')
                data.wx_alert_interrupt = False
                #Display the board from the config
                board = getattr(self,"wxalert")
                data.curr_board = "wxalert"
                bord_index -= 1

            # Display the Screensaver Board
            if data.screensaver:
                if not data.pb_trigger:
                    debug.info('Screensaver triggered in off day loop....')
                    #Display the board from the config
                    board = getattr(self,"screensaver")
                    data.curr_board = "screensaver"
                    data.prev_board = data.config.boards_off_day[bord_index]
                    bord_index -= 1
                else:
                    data.pb_trigger = False

            board(data, matrix, sleepEvent)

            if bord_index >= (len(data.config.boards_off_day) - 1):
                return
            else:
                if not data.pb_trigger or not data.wx_alert_interrupt or not data.screensaver or not data.mqtt_trigger:
                    bord_index += 1

    def _scheduled(self, data, matrix, sleepEvent):
        bord_index = 0
        while True:
            board = getattr(self, data.config.boards_scheduled[bord_index])
            data.curr_board = data.config.boards_scheduled[bord_index]
            if data.pb_trigger:
                debug.info('PushButton triggered....will display ' + data.config.pushbutton_state_triggered1 + ' board ' + "Overriding scheduled -> " + data.config.boards_scheduled[bord_index])
                if not data.screensaver:
                    data.pb_trigger = False
                board = getattr(self,data.config.pushbutton_state_triggered1)
                data.curr_board = data.config.pushbutton_state_triggered1
                bord_index -= 1

            if data.mqtt_trigger:
                debug.info('MQTT triggered....will display ' + data.mqtt_showboard + ' board ' + "Overriding scheduled -> " + data.config.boards_off_day[bord_index])
                if not data.screensaver:
                    data.mqtt_trigger = False
                board = getattr(self,data.mqtt_showboard)
                data.curr_board = data.mqtt_showboard
                bord_index -= 1


            # Display the Weather Alert board
            if data.wx_alert_interrupt:
                debug.info('Weather Alert triggered in scheduled loop....will display weather alert board')
                data.wx_alert_interrupt = False
                #Display the board from the config
                board = getattr(self,"wxalert")
                data.curr_board = "wxalert"
                bord_index -= 1

            # Display the Screensaver Board
            if data.screensaver:
                if not data.pb_trigger:
                    debug.info('Screensaver triggered in scheduled loop....')
                    #Display the board from the config
                    board = getattr(self,"screensaver")
                    data.curr_board = "screensaver"
                    data.prev_board = data.config.boards_off_day[bord_index]
                    bord_index -= 1
                else:
                    data.pb_trigger = False

            board(data, matrix, sleepEvent)

            if bord_index >= (len(data.config.boards_scheduled) - 1):
                return
            else:
                if not data.pb_trigger or not data.wx_alert_interrupt or not data.screensaver or not data.mqtt_trigger:
                    bord_index += 1

    def _intermission(self, data, matrix, sleepEvent):
        bord_index = 0
        while True:
            board = getattr(self, data.config.boards_intermission[bord_index])
            data.curr_board = data.config.boards_intermission[bord_index]

            if data.pb_trigger:
                debug.info('PushButton triggered....will display ' + data.config.pushbutton_state_triggered1 + ' board ' + "Overriding intermission -> " + data.config.boards_intermission[bord_index])
                if not data.screensaver:
                    data.pb_trigger = False
                board = getattr(self,data.config.pushbutton_state_triggered1)
                data.curr_board = data.config.pushbutton_state_triggered1
                bord_index -= 1

            if data.mqtt_trigger:
                debug.info('MQTT triggered....will display ' + data.mqtt_showboard + ' board ' + "Overriding intermission -> " + data.config.boards_off_day[bord_index])
                if not data.screensaver:
                    data.mqtt_trigger = False
                board = getattr(self,data.mqtt_showboard)
                data.curr_board = data.mqtt_showboard
                bord_index -= 1

            # Display the Weather Alert board
            if data.wx_alert_interrupt:
                debug.info('Weather Alert triggered in intermission....will display weather alert board')
                data.wx_alert_interrupt = False
                #Display the board from the config
                board = getattr(self,"wxalert")
                data.curr_board = "wxalert"
                bord_index -= 1

            ## Don't Display the Screensaver Board in "live game mode"
            # if data.screensaver:
            #     if not data.pb_trigger:
            #         debug.info('Screensaver triggered in intermission loop....')
            #         #Display the board from the config
            #         board = getattr(self,"screensaver")
            #         data.curr_board = "screensaver"
            #         data.prev_board = data.config.boards_off_day[bord_index]
            #         bord_index -= 1
            #     else:
            #         data.pb_trigger = False
        
            board(data, matrix, sleepEvent)

            if bord_index >= (len(data.config.boards_intermission) - 1):
                return
            else:
                if not data.pb_trigger or not data.wx_alert_interrupt or not data.screensaver or not data.mqtt_trigger:
                    bord_index += 1

    def _post_game(self, data, matrix, sleepEvent):
        bord_index = 0
        while True:
            board = getattr(self, data.config.boards_post_game[bord_index])
            data.curr_board = data.config.boards_post_game[bord_index]

            if data.pb_trigger:
                debug.info('PushButton triggered....will display ' + data.config.pushbutton_state_triggered1 + ' board ' + "Overriding post_game -> " + data.config.boards_post_game[bord_index])
                if not data.screensaver:
                    data.pb_trigger = False
                board = getattr(self,data.config.pushbutton_state_triggered1)
                data.curr_board = data.config.pushbutton_state_triggered1
                bord_index -= 1

            if data.mqtt_trigger:
                debug.info('MQTT triggered....will display ' + data.mqtt_showboard + ' board ' + "Overriding post_game -> " + data.config.boards_off_day[bord_index])
                if not data.screensaver:
                    data.mqtt_trigger = False
                board = getattr(self,data.mqtt_showboard)
                data.curr_board = data.mqtt_showboard
                bord_index -= 1

            # Display the Weather Alert board
            if data.wx_alert_interrupt:
                debug.info('Weather Alert triggered in post game loop....will display weather alert board')
                data.wx_alert_interrupt = False
                #Display the board from the config
                board = getattr(self,"wxalert")
                data.curr_board = "wxalert"
                bord_index -= 1

            # Display the Screensaver Board
            if data.screensaver:
                if not data.pb_trigger:
                    debug.info('Screensaver triggered in post game loop....')
                    #Display the board from the config
                    board = getattr(self,"screensaver")
                    data.curr_board = "screensaver"
                    data.prev_board = data.config.boards_off_day[bord_index]
                    bord_index -= 1
                else:
                    data.pb_trigger = False


            board(data, matrix, sleepEvent)

            if bord_index >= (len(data.config.boards_post_game) - 1):
                return
            else:
                if not data.pb_trigger or not data.wx_alert_interrupt or not data.screensaver or not data.mqtt_trigger:
                    bord_index += 1

    def fallback(self, data, matrix, sleepEvent):
        Clock(data, matrix, sleepEvent)

    def scoreticker(self, data, matrix, sleepEvent):
        Scoreticker(data, matrix, sleepEvent).render()

    # Since 2024, the playoff features are removed as we have not colected the new API endpoint for them. 
    def seriesticker(self, data, matrix, sleepEvent):
        Seriesticker(data, matrix, sleepEvent).render()
    
    # Since 2024, the playoff features are removed as we have not colected the new API endpoint for them. 
    def stanley_cup_champions(self, data, matrix, sleepEvent):
        debug.info("stanley_cup_champions is disabled. This feature is not available right now")
        pass
        #StanleyCupChampions(data, matrix, sleepEvent).render()

    def standings(self, data, matrix, sleepEvent):
        #Try making standings a thread
        Standings(data, matrix, sleepEvent).render()

    def team_summary(self, data, matrix, sleepEvent):
        TeamSummary(data, matrix, sleepEvent).render()

    def clock(self, data, matrix, sleepEvent):
        Clock(data, matrix, sleepEvent)

    def pbdisplay(self, data, matrix, sleepEvent):
        pbDisplay(data, matrix, sleepEvent)

    def weather(self, data, matrix, sleepEvent):
        wxWeather(data, matrix, sleepEvent)

    def wxalert(self, data, matrix, sleepEvent):
        wxAlert(data, matrix, sleepEvent)

    def wxforecast(self, data, matrix, sleepEvent):
        wxForecast(data, matrix, sleepEvent)

    def screensaver(self, data, matrix, sleepEvent):
        screenSaver(data, matrix, sleepEvent)

    def christmas(self, data, matrix, sleepEvent):
        Christmas(data, matrix, sleepEvent).draw()

    def seasoncountdown(self, data, matrix, sleepEvent):
        SeasonCountdown(data, matrix, sleepEvent).draw()

    def player_stats(self, data, matrix, sleepEvent):
        PlayerStatsRenderer(data, matrix, sleepEvent).render()

    def ovi_tracker(self, data, matrix, sleepEvent):
        OviTrackerRenderer(data, matrix, sleepEvent).render()

    def stats_leaders(self, data, matrix, sleepEvent):
        StatsLeaders(data, matrix, sleepEvent).render()

    def stridekick(self, data, matrix, sleepEvent):
        StrideKickRenderer(data, matrix, sleepEvent).render()

    def holidays(self, data, matrix, sleepEvent):
        Holidays(data, matrix, sleepEvent).render()

    def _get_board_list(self):
        boards = []
        
        # Add stats leaders board check
        if self.data.config.boards_enabled["stats_leaders"]:
            boards.append(self.stats_leaders)
            
        return boards
