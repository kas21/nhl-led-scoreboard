# Test Scripts

This directory contains test scripts for manually testing specific components of the NHL LED Scoreboard.

## Available Tests

### test_goal_renderer.py

Tests the goal animation renderer that displays goal details on the LED matrix.

**Usage:**
```bash
# Basic test with emulated 64x32 display
uv run tests/test_goal_renderer.py --emulated

# Test with 128x64 display
uv run tests/test_goal_renderer.py --emulated --led-rows=64 --led-cols=128

# Test with custom team and player
uv run tests/test_goal_renderer.py --emulated --team=BOS --player-number=63 --player-first=Brad --player-last=Marchand

# Test unassisted goal
uv run tests/test_goal_renderer.py --emulated --no-assists

# Test with debug logging
uv run tests/test_goal_renderer.py --emulated --loglevel=DEBUG
```

**Options:**
- All standard LED matrix options (--led-rows, --led-cols, --led-brightness, etc.)
- `--team` - Team abbreviation (COL, BOS, TOR, etc.)
- `--player-number` - Jersey number
- `--player-first` - Player first name
- `--player-last` - Player last name
- `--period` - Period number
- `--period-time` - Time in period (e.g., "12:34")
- `--no-assists` - Test unassisted goal
- `--loglevel` - Log level (DEBUG, INFO, WARN, ERROR)

**Supported Teams:**
NJD, NYI, NYR, PHI, PIT, BOS, BUF, MTL, OTT, TOR, CAR, FLA, TBL, WSH, CHI, DET, NSH, STL, CGY, COL, EDM, VAN, ANA, DAL, LAK, SJS, CBJ, MIN, WPG, ARI, VGK, SEA, UTA

---

### test_penalty_renderer.py

Tests the penalty renderer that displays penalty details on the LED matrix.

**Usage:**
```bash
# Basic test with emulated 64x32 display
uv run tests/test_penalty_renderer.py --emulated

# Test with 128x64 display
uv run tests/test_penalty_renderer.py --emulated --led-rows=64 --led-cols=128

# Test with custom team and player
uv run tests/test_penalty_renderer.py --emulated --team=BOS --player-number=63 --player-last=Marchand

# Test major penalty
uv run tests/test_penalty_renderer.py --emulated --severity=MAJOR --penalty-minutes=5

# Test with different teams
uv run tests/test_penalty_renderer.py --emulated --team=TOR --player-number=34 --player-last=Matthews

# Test with debug logging
uv run tests/test_penalty_renderer.py --emulated --loglevel=DEBUG
```

**Options:**
- All standard LED matrix options (--led-rows, --led-cols, --led-brightness, etc.)
- `--team` - Team abbreviation (COL, BOS, TOR, etc.)
- `--player-number` - Jersey number (default: 29)
- `--player-last` - Player last name (default: MacKinnon)
- `--period-time` - Time in period (e.g., "12:34")
- `--penalty-minutes` - Penalty duration in minutes (default: 2)
- `--severity` - Penalty severity: MINOR, MAJOR, MISCONDUCT, MATCH (default: MINOR)
- `--loglevel` - Log level (DEBUG, INFO, WARN, ERROR)

**Supported Teams:**
NJD, NYI, NYR, PHI, PIT, BOS, BUF, MTL, OTT, TOR, CAR, FLA, TBL, WSH, CHI, DET, NSH, STL, CGY, COL, EDM, VAN, ANA, DAL, LAK, SJS, CBJ, MIN, WPG, ARI, VGK, SEA, UTA

---

### test_game_stats.py

Tests the GameStatsBoard with mock game story data - displays team comparison stats (shots, hits, faceoffs, power play, etc.)

**Usage:**
```bash
# Basic test with emulated 128x64 display (default)
uv run tests/test_game_stats.py --emulated

# Test with 64x32 display
uv run tests/test_game_stats.py --emulated --led-rows=32 --led-cols=64

# Test with specific teams
uv run tests/test_game_stats.py --emulated --home-team=BOS --away-team=TOR

# Show only specific stat
uv run tests/test_game_stats.py --emulated --stat=shots
uv run tests/test_game_stats.py --emulated --stat=faceoff

# Disable animations for faster testing
uv run tests/test_game_stats.py --emulated --no-animation

# Loop continuously
uv run tests/test_game_stats.py --emulated --loop

# Custom display duration
uv run tests/test_game_stats.py --emulated --delay=3

# Test with debug logging
uv run tests/test_game_stats.py --emulated --loglevel=DEBUG
```

**Options:**
- All standard LED matrix options (--led-rows, --led-cols, --led-brightness, etc.)
- `--home-team` - Home team abbreviation (default: BOS)
- `--away-team` - Away team abbreviation (default: TOR)
- `--stat` - Show only specific stat: shots, hits, faceoff, powerplay, blocked
- `--delay` - Seconds to display each stat (default: 5)
- `--loop` - Loop continuously through stats
- `--no-animation` - Disable bar animations
- `--loglevel` - Log level (DEBUG, INFO, WARN, ERROR)

**Supported Teams:**
BOS, TOR, MTL, NYR, PHI, PIT, COL, EDM, CGY, VAN, SEA, LAK, ANA, SJS, VGK, DAL, MIN, WPG, NSH, STL, CHI, DET, TBL, FLA, CAR, NYI, NJD, WSH, CBJ, OTT, BUF

**Mock Data:**
The test uses realistic mock stats:
- Home: 28 SOG, 22 hits, 52.4% faceoffs, 1/4 PP
- Away: 24 SOG, 19 hits, 47.6% faceoffs, 0/3 PP

---

## Adding New Tests

When creating new test scripts:
1. Place them in this `tests/` directory
2. Use the same command-line argument pattern as the main application
3. Document usage in this README
4. Follow the naming convention: `test_<component>_<description>.py`
