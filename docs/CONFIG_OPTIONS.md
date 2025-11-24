# NHL LED Scoreboard Configuration Options

This document provides a reference for all configuration options available in the NHL LED Scoreboard.

## Top-Level Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `debug` | boolean | `false` | Enable debug mode showing console output |
| `loglevel` | string | `"INFO"` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `live_mode` | boolean | `true` | Enable live game data display for favorite team |

---

## Preferences (`preferences`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `time_format` | string | `"12h"` | Time display format: `"12h"` or `"24h"` |
| `end_of_day` | string | `"12:00"` | 24h time considered end of previous day (e.g., `"8:00"`) |
| `location` | string | `""` | Location for weather/dimmer. Format: `"City, State"` or `"lat,lon"` |
| `live_game_refresh_rate` | integer | `15` | API refresh rate in seconds during live games (min: 10) |
| `teams` | array | `[]` | List of preferred team names (first is favorite) |
| `sog_display_frequency` | integer | `4` | How often shots on goal are updated |
| `goal_animations.pref_team_only` | boolean | `false` | Show goal animations only for preferred teams |
| `disable_penalty_animation` | boolean | `false` | Disable penalty animations |
| `show_power_play_details` | boolean | `false` | Show power play details on live game scoreboard |

### Valid Team Names

`Avalanche`, `Blackhawks`, `Blue Jackets`, `Blues`, `Bruins`, `Canadiens`, `Canucks`, `Capitals`, `Devils`, `Ducks`, `Flames`, `Flyers`, `Golden Knights`, `Hurricanes`, `Islanders`, `Jets`, `Kings`, `Kraken`, `Lightning`, `Maple Leafs`, `Oilers`, `Panthers`, `Penguins`, `Predators`, `Rangers`, `Red Wings`, `Sabres`, `Senators`, `Sharks`, `Stars`, `Wild`, `Mammoth`

---

## States (`states`)

Define which boards display during each game state. Each is an array of board names.

| State | Description |
|-------|-------------|
| `off_day` | When preferred teams are not playing |
| `scheduled` | When a game is scheduled for today |
| `intermission` | During intermission between periods |
| `post_game` | After game completion |

### Available Board Names

- `wxalert` - Weather alerts
- `wxforecast` - Weather forecast
- `scoreticker` - Score ticker for all/preferred games
- `seriesticker` - Playoff series ticker
- `standings` - League standings
- `team_summary` - Team summary information
- `season_countdown` - NHL season countdown
- `clock` - Clock display
- `weather` - Weather information
- `player_stats` - Individual player statistics
- `ovi_tracker` - Ovechkin goal tracker
- `stats_leaders` - NHL stats leaders

---

## Boards (`boards`)

### Scoreticker (`boards.scoreticker`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `preferred_teams_only` | boolean | `false` | Show only preferred teams' games |
| `rotation_rate` | integer | `5` | Seconds to display each game |

### Seriesticker (`boards.seriesticker`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `preferred_teams_only` | boolean | `false` | Show only preferred teams' series |
| `rotation_rate` | integer | `5` | Seconds to display each series |
| `hide_completed_rounds` | boolean | `false` | Hide completed playoff rounds |

### Standings (`boards.standings`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `preferred_standings_only` | boolean | `false` | Show only preferred division/conference |
| `standing_type` | string | `"conference"` | Type: `"conference"`, `"division"`, `"wild_card"` |
| `divisions` | string | `""` | Preferred division: `"central"`, `"atlantic"`, `"metropolitan"`, `"pacific"` |
| `conference` | string | `""` | Preferred conference: `"eastern"`, `"western"` |
| `wildcard_limit` | integer | `4` | Number of wildcard teams to show |
| `large_font` | boolean | `false` | Use large font (128x64 displays only) |

### Clock (`boards.clock`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `duration` | integer | `60` | How long to display clock (seconds) |
| `hide_indicator` | boolean | `false` | Hide network/update indicator bar |
| `preferred_team_colors` | boolean | `false` | Use first preferred team's colors |
| `clock_rgb` | string | `""` | Custom RGB for clock numbers (e.g., `"230,230,23"`) |
| `date_rgb` | string | `""` | Custom RGB for date/weather text |
| `flash_seconds` | boolean | `false` | Flash the colon separator |

### Weather (`boards.weather`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable weather functionality |
| `view` | string | `"full"` | View mode: `"full"` (3 pages) or `"summary"` (1 page) |
| `units` | string | `"metric"` | Units: `"metric"` or `"imperial"` |
| `duration` | integer | `30` | Seconds to flip through pages (min: 30) |
| `data_feed` | string | `"EC"` | Data source: `"EC"` (Environment Canada), `"OWM"` (OpenWeatherMap) |
| `owm_apikey` | string | `""` | API key for OpenWeatherMap |
| `update_freq` | integer | `5` | Weather refresh frequency (minutes) |
| `show_on_clock` | boolean | `false` | Show temperature/humidity on clock board |
| `forecast_enabled` | boolean | `false` | Enable weather forecast |
| `forecast_show_today` | boolean | `false` | Include today in forecast |
| `forecast_days` | integer | `3` | Number of forecast days (max: 3) |
| `forecast_update` | integer | `3` | Forecast update frequency (hours) |

### Weather Alerts (`boards.wxalert`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `alert_feed` | string | `""` | Alert source: `"EC"` or `"NWS"` |
| `update_freq` | integer | `5` | Alert refresh frequency (minutes) |
| `show_alerts` | boolean | `false` | Display weather alerts |
| `nws_show_expire` | boolean | `false` | Show expiry time instead of effective time |
| `alert_title` | boolean | `false` | Display alert type (WARNING/WATCH/ADVISORY) |
| `scroll_alert` | boolean | `false` | Scroll alert text |
| `alert_duration` | integer | `5` | Alert display duration (seconds) |
| `show_on_clock` | boolean | `false` | Show alert indicator on clock |

### Player Stats (`boards.player_stats`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `rotation_rate` | integer | `7` | Seconds to display each player |
| `players` | array | `[]` | List of NHL player IDs to display |

### Stats Leaders (`boards.stats_leaders`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `rotation_rate` | integer | `5` | Seconds to display bottom of list |
| `categories` | array | `["goals", "assists", "points"]` | Stat categories to show |
| `use_large_font` | boolean | `true` | Use large font (128x64 displays) |
| `scroll_speed` | float | `0.2` | Scroll speed in seconds |
| `limit` | integer | `10` | Number of players to show per category |

#### Available Stats Categories

- `goals` - Goals scored
- `points` - Total points
- `assists` - Assists

---

## Scoreboard IO (`sbio`)

### MQTT (`sbio.mqtt`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable MQTT control |
| `broker` | string | `""` | MQTT broker hostname/IP |
| `port` | integer | `1883` | MQTT broker port |
| `auth.username` | string | `""` | MQTT username |
| `auth.password` | string | `""` | MQTT password |
| `main_topic` | string | `"scoreboard"` | Main MQTT topic |

### Screensaver (`sbio.screensaver`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable screensaver |
| `animations` | boolean | `false` | Show animation before black screen |
| `start` | string | `""` | Start time (24h format, e.g., `"22:00"`) |
| `stop` | string | `""` | Stop time (24h format, e.g., `"08:00"`) |
| `data_updates` | boolean | `false` | Continue data updates while screensaver active |
| `motionsensor` | boolean | `false` | Use motion sensor to wake |
| `pin` | integer | `0` | GPIO pin for motion sensor |
| `delay` | integer | `30` | Seconds of no motion before re-enabling screensaver |

### Dimmer (`sbio.dimmer`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable auto-dimming |
| `source` | string | `"software"` | Source: `"software"` (location-based) or `"hardware"` (TSL2591 sensor) |
| `daytime` | string | `""` | Daytime start (e.g., `"8:30 AM"` or `"08:30"`) |
| `nighttime` | string | `""` | Nighttime start (e.g., `"5:30 PM"` or `"17:30"`) |
| `offset` | integer | `0` | Sunrise/sunset offset in minutes |
| `frequency` | integer | `5` | Check frequency (minutes) |
| `light_level_lux` | integer | `10` | Light level threshold for hardware sensor |
| `mode` | string | `"always"` | Run mode: `"always"` or `"off_day"` |
| `sunset_brightness` | integer | `5` | Nighttime brightness level |
| `sunrise_brightness` | integer | `40` | Daytime brightness level |

### Pushbutton (`sbio.pushbutton`)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `false` | Enable pushbutton functionality |
| `bonnet` | boolean | `false` | Using Adafruit bonnet (true) vs HAT (false) |
| `pin` | integer | `25` | GPIO pin for button |
| `reboot_duration` | integer | `2` | Seconds held to trigger reboot (min: 2) |
| `reboot_override_process` | string | `""` | Custom reboot command path |
| `display_reboot` | boolean | `false` | Show "REBOOT" on screen when triggered |
| `poweroff_duration` | integer | `10` | Seconds held to trigger poweroff |
| `poweroff_override_process` | string | `""` | Custom poweroff command path |
| `display_halt` | boolean | `false` | Show "! HALT !" on screen when triggered |
| `state_triggered1` | string | `"clock"` | Board to display on button press |
| `state_triggered1_process` | string | `""` | Custom process on button press |
