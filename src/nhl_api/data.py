import json
import requests
import debug
from datetime import date
from nhl_api.nhl_client import client
import backoff
import httpx

"""
    TODO:
        Add functions to call single series overview (all the games of a single series) using the NHL record API. 
        https://records.nhl.com/site/api/playoff-series?cayenneExp=playoffSeriesLetter="A" and seasonId=20182019
"""

BASE_URL = "https://api-web.nhle.com/v1/"
SCHEDULE_URL = BASE_URL + 'score/{0}-{1}-{2}'
TEAM_SCHEDULE_URL = BASE_URL + 'club-schedule-season/{0}/{1}'
TEAM_URL = "https://api.nhle.com/stats/rest/en/team"
PLAYER_URL = '{0}player/{1}/landing'
OVERVIEW_URL = BASE_URL + 'gamecenter/{0}/play-by-play'
STATUS_URL = BASE_URL + 'gameStatus'
CURRENT_SEASON_URL = BASE_URL + 'season'
NEXT_SEASON_URL = BASE_URL + 'schedule/now'
STANDINGS_URL = BASE_URL + 'standings'
STANDINGS_WILD_CARD = STANDINGS_URL + '/wildCardWithLeaders'
PLAYOFF_URL = BASE_URL + "tournaments/playoffs?expand=round.series,schedule.game.seriesSummary&season={}"
SERIES_RECORD = "https://records.nhl.com/site/api/playoff-series?cayenneExp=playoffSeriesLetter='{}' and seasonId={}"
SKATER_STATS_LEADERS_URL = BASE_URL + 'skater-stats-leaders/current'
REQUEST_TIMEOUT = 5

TIMEOUT_TESTING = 0.001  # TO DELETE

#from nhlpy import NHLClient

@backoff.on_exception(backoff.expo,
                      httpx.HTTPError,
                      logger='scoreboard')

def get_score_details(date):
    #client = NHLClient(verbose=False)
    #with client as client:
    try:
        score_details = client.game_center.score_now(date)
        return score_details
    
    except httpx.HTTPError as exc:
        print(f"Error while requesting {exc}.")
        
def get_team_schedule(team_code, season_code):
    try:
        data = requests.get(TEAM_SCHEDULE_URL.format(team_code, season_code), timeout=REQUEST_TIMEOUT)
        return data
    except requests.exceptions.RequestException as e:
        raise ValueError(e)

def get_teams():
    try:
        data = requests.get(TEAM_URL, timeout=REQUEST_TIMEOUT)
        return data
    except requests.exceptions.RequestException as e:
        raise ValueError(e)

@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException,
                      logger='player_stats')
# def get_player_stats(player_id, season=None):
#     """
#     Get player statistics from NHL API
#     Args:
#         player_id: NHL player ID
#         season: Optional season (e.g., '20232024'). If None, gets current season
#     Returns:
#         Dictionary containing player stats
#     """
#     try:
#         # For current season stats
#         url = f"{BASE_URL}player/{player_id}/stats"
#         if season:
#             url += f"/season/{season}"
            
#         response = requests.get(url, timeout=REQUEST_TIMEOUT)
#         response.raise_for_status()  # Raises an HTTPError for bad responses
#         return response.json()
        
#     except requests.exceptions.RequestException as exc:
#         print(f"Error while requesting player stats: {exc}")
#         raise

@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException,
                      logger='player_info')
def get_player(player_id):
    """
    Get player information from NHL API
    Args:
        player_id: NHL player ID
    Returns:
        Dictionary containing player information
    """
    try:
        url = f"{BASE_URL}player/{player_id}/landing"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as exc:
        print(f"Error while requesting player info: {exc}")
        raise

def get_overview(game_id):
    try:
        data = requests.get(OVERVIEW_URL.format(game_id), timeout=REQUEST_TIMEOUT)
        # data = dummie_overview()
        return data
    except requests.exceptions.RequestException as e:
        raise ValueError(e)


def get_game_status():
    try:
        data = requests.get(STATUS_URL, timeout=REQUEST_TIMEOUT)
        return data
    except requests.exceptions.RequestException as e:
        raise ValueError(e)


def get_current_season():
    try:
        data = requests.get(CURRENT_SEASON_URL, timeout=REQUEST_TIMEOUT)
        return data
    except requests.exceptions.RequestException as e:
        raise ValueError(e)
    
def get_next_season():
     # Create the next seasonID from the current year and curent year +1 eg: 20232024 is seasonID for 2023-2024 season
     # This will return an empty set for seasons data if the seasonID has nothing, a 200 response will always occur
     #current_year = date.today().year
     #next_year = current_year + 1
    
#     nextseasonID="{0}{1}".format(current_year,next_year)
    
     try:
         data = requests.get(NEXT_SEASON_URL, timeout=REQUEST_TIMEOUT)
         return data
     except requests.exceptions.RequestException as e:
         raise ValueError(e)


def get_standings():
    try:
        data = requests.get(STANDINGS_URL, timeout=REQUEST_TIMEOUT)
        return data
    except requests.exceptions.RequestException as e:
        raise ValueError(e)

def get_standings_wildcard():
    try:
        data = requests.get(STANDINGS_WILD_CARD, timeout=REQUEST_TIMEOUT)
        return data
    except requests.exceptions.RequestException as e:
        raise ValueError(e)

def get_playoff_data(season):
    try:
        data = requests.get(PLAYOFF_URL.format(season), timeout=REQUEST_TIMEOUT)
        return data
    except requests.exceptions.RequestException as e:
        raise ValueError(e)

def get_series_record(seriesCode, season):
    try:
        data = requests.get(SERIES_RECORD.format(seriesCode, season), timeout=REQUEST_TIMEOUT)
        return data
    except requests.exceptions.RequestException as e:
        raise ValueError(e)

## DEBUGGING DATA (TO DELETE)
def dummie_overview():
    with open('dummie_nhl_data/overview_reg_final.json') as json_file:
        data = json.load(json_file)
        return data

def fetch_player_data(player_id):
    """Fetch player data from NHL API"""
    url = f'https://api-web.nhle.com/v1/player/{player_id}/landing'
    response = requests.get(url)
    
    if response.status_code != 200:
        raise Exception('API request failed')
        
    return response.json()

def get_player_stats(player_id):
    """Get player stats from the NHL API"""
    from nhl_api.player import PlayerStats  # Import here to avoid circular imports
    player_stats = PlayerStats.from_api(player_id)
    
    # Convert relevant attributes to dictionary
    return {
        attr: getattr(player_stats, attr)
        for attr in player_stats.__dict__
        if not attr.startswith('_') and attr != 'player_data'
    }

@backoff.on_exception(backoff.expo,
                      requests.exceptions.RequestException,
                      logger='skater_stats')
def get_skater_stats_leaders(category=None, limit=None):
    """
    Get current NHL skater statistics leaders from NHL API
    Args:
        category (str, optional): Specific stat category to query. Must be one of:
            - goals
            - points
            - assists
            - toi (time on ice)
            - plusMinus
            - penaltyMins
            - faceoffLeaders
            - goalsPp (powerplay)
            - goalsSh (shorthanded)
        limit (int, optional): Number of results to return
    Returns:
        Dictionary containing leader statistics
    Raises:
        ValueError: If category is invalid
    """
    valid_categories = {
        'goals', 'points', 'assists', 'toi', 'plusMinus',
        'penaltyMins', 'faceoffLeaders', 'goalsPp', 'goalsSh'
    }
    
    try:
        params = {}
        if category:
            if category not in valid_categories:
                raise ValueError(f"Invalid category. Must be one of: {', '.join(sorted(valid_categories))}")
            params['categories'] = category
        if limit:
            params['limit'] = limit

        response = requests.get(
            SKATER_STATS_LEADERS_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as exc:
        print(f"Error while requesting skater stats leaders: {exc}")
        raise
