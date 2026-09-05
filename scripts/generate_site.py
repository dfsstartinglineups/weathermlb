import os
import sys
import json
import time
import requests
import zoneinfo
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. PATH CONFIGURATION & MASTER DATA
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR)

DATA_DIR = os.path.join(ROOT_DIR, 'data')
DAILY_FILES_DIR = os.path.join(DATA_DIR, 'daily_files')
STADIUMS_FILE = os.path.join(DATA_DIR, 'stadiums.json')
ODDS_FILE = os.path.join(DATA_DIR, 'odds.json')
TEAM_PAGES_DIR = os.path.join(ROOT_DIR, 'team_pages')
MAIN_INDEX_FILE = os.path.join(ROOT_DIR, 'index.html')
SITEMAP_FILE = os.path.join(ROOT_DIR, 'sitemap.xml')

WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
INDEXNOW_KEY = "720a7241f9ed46778f358f5e4ab98695"


os.makedirs(DAILY_FILES_DIR, exist_ok=True)
os.makedirs(TEAM_PAGES_DIR, exist_ok=True)

MLB_TEAMS = [
    {"id": 110, "slug": "baltimore-orioles", "name": "Baltimore Orioles", "stadium": "Oriole Park at Camden Yards"},
    {"id": 111, "slug": "boston-red-sox", "name": "Boston Red Sox", "stadium": "Fenway Park"},
    {"id": 147, "slug": "new-york-yankees", "name": "New York Yankees", "stadium": "Yankee Stadium"},
    {"id": 139, "slug": "tampa-bay-rays", "name": "Tampa Bay Rays", "stadium": "Tropicana Field"},
    {"id": 141, "slug": "toronto-blue-jays", "name": "Toronto Blue Jays", "stadium": "Rogers Centre"},
    {"id": 145, "slug": "chicago-white-sox", "name": "Chicago White Sox", "stadium": "Guaranteed Rate Field"},
    {"id": 114, "slug": "cleveland-guardians", "name": "Cleveland Guardians", "stadium": "Progressive Field"},
    {"id": 116, "slug": "detroit-tigers", "name": "Detroit Tigers", "stadium": "Comerica Park"},
    {"id": 118, "slug": "kansas-city-royals", "name": "Kansas City Royals", "stadium": "Kauffman Stadium"},
    {"id": 142, "slug": "minnesota-twins", "name": "Minnesota Twins", "stadium": "Target Field"},
    {"id": 117, "slug": "houston-astros", "name": "Houston Astros", "stadium": "Minute Maid Park"},
    {"id": 108, "slug": "los-angeles-angels", "name": "Los Angeles Angels", "stadium": "Angel Stadium"},
    {"id": 133, "slug": "athletics", "name": "Athletics", "stadium": "Sutter Health Park"},
    {"id": 136, "slug": "seattle-mariners", "name": "Seattle Mariners", "stadium": "T-Mobile Park"},
    {"id": 140, "slug": "texas-rangers", "name": "Texas Rangers", "stadium": "Globe Life Field"},
    {"id": 144, "slug": "atlanta-braves", "name": "Atlanta Braves", "stadium": "Truist Park"},
    {"id": 146, "slug": "miami-marlins", "name": "Miami Marlins", "stadium": "loanDepot park"},
    {"id": 121, "slug": "new-york-mets", "name": "New York Mets", "stadium": "Citi Field"},
    {"id": 143, "slug": "philadelphia-phillies", "name": "Philadelphia Phillies", "stadium": "Citizens Bank Park"},
    {"id": 120, "slug": "washington-nationals", "name": "Washington Nationals", "stadium": "Nationals Park"},
    {"id": 112, "slug": "chicago-cubs", "name": "Chicago Cubs", "stadium": "Wrigley Field"},
    {"id": 113, "slug": "cincinnati-reds", "name": "Cincinnati Reds", "stadium": "Great American Ball Park"},
    {"id": 158, "slug": "milwaukee-brewers", "name": "Milwaukee Brewers", "stadium": "American Family Field"},
    {"id": 134, "slug": "pittsburgh-pirates", "name": "Pittsburgh Pirates", "stadium": "PNC Park"},
    {"id": 138, "slug": "st-louis-cardinals", "name": "St. Louis Cardinals", "stadium": "Busch Stadium"},
    {"id": 109, "slug": "arizona-diamondbacks", "name": "Arizona Diamondbacks", "stadium": "Chase Field"},
    {"id": 115, "slug": "colorado-rockies", "name": "Colorado Rockies", "stadium": "Coors Field"},
    {"id": 119, "slug": "los-angeles-dodgers", "name": "Los Angeles Dodgers", "stadium": "Dodger Stadium"},
    {"id": 135, "slug": "san-diego-padres", "name": "San Diego Padres", "stadium": "Petco Park"},
    {"id": 137, "slug": "san-francisco-giants", "name": "San Francisco Giants", "stadium": "Oracle Park"}
]

API_CALL_TRACKER = {"schedule": 0, "weather_api": 0}

# ==========================================
# 2. WEATHER FETCHING ENGINE
# ==========================================
def load_json(path, default_val):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: pass
    return default_val

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def get_active_sport_ids():
    current_date = datetime.now(timezone.utc).date()
    wbc_start = datetime(2026, 3, 4).date()
    wbc_end = datetime(2026, 3, 17).date()
    if wbc_start <= current_date <= wbc_end: return "1,51"
    return "1"

def calculate_wind(wind_direction, stadium_bearing):
    if wind_direction is None or stadium_bearing is None:
        return {"text": "Unknown", "cssClass": "bg-secondary", "arrow": "💨"}
    diff = (wind_direction - stadium_bearing + 360) % 360
    if diff >= 337.5 or diff < 22.5: return {"text": "Blowing IN", "cssClass": "bg-in", "arrow": "⬇"}
    if 22.5 <= diff < 67.5: return {"text": "In from Right", "cssClass": "bg-in", "arrow": "↙"}
    if 67.5 <= diff < 112.5: return {"text": "Cross (R to L)", "cssClass": "bg-cross", "arrow": "⬅"}
    if 112.5 <= diff < 157.5: return {"text": "Out to Left", "cssClass": "bg-out", "arrow": "↖"}
    if 157.5 <= diff < 202.5: return {"text": "Blowing OUT", "cssClass": "bg-out", "arrow": "⬆"}
    if 202.5 <= diff < 247.5: return {"text": "Out to Right", "cssClass": "bg-out", "arrow": "↗"}
    if 247.5 <= diff < 292.5: return {"text": "Cross (L to R)", "cssClass": "bg-cross", "arrow": "➡"}
    return {"text": "In from Left", "cssClass": "bg-in", "arrow": "↘"}

def fetch_game_weather(session, lat, lon, game_date_iso):
    global API_CALL_TRACKER
    if not WEATHER_API_KEY:
        print("⚠️ WEATHER_API_KEY environment variable is missing!")
        return {"temp": "--", "hourly": []}

    utc_time = datetime.fromisoformat(game_date_iso.replace('Z', '+00:00'))
    url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={lat},{lon}&days=2&aqi=no&alerts=no"

    max_retries = 2
    for attempt in range(max_retries):
        try:
            API_CALL_TRACKER["weather_api"] += 1
            res = session.get(url, timeout=12)
            if res.status_code != 200:
                print(f"⚠️ WeatherAPI status code {res.status_code}")
                return {"temp": "--", "hourly": []}

            data = res.json()
            all_hours = []
            for day in data.get('forecast', {}).get('forecastday', []):
                all_hours.extend(day.get('hour', []))

            target_epoch = int(utc_time.replace(minute=0, second=0, microsecond=0).timestamp())
            start_idx = next((i for i, h in enumerate(all_hours) if h['time_epoch'] == target_epoch), 0)

            actual_start = max(0, start_idx - 1)
            actual_end = min(len(all_hours), start_idx + 4)

            hourly_slice, max_chance_in_window = [], 0
            is_game_thunderstorm, is_game_snow = False, False

            for i in range(actual_start, actual_end):
                hour = all_hours[i]
                chance = int(hour.get('chance_of_rain', 0))
                cond_text = hour.get('condition', {}).get('text', '').lower()
                weather_code = hour.get('condition', {}).get('code', 1000)

                is_hour_thunderstorm = "thunder" in cond_text
                is_hour_snow = any(s in cond_text for s in ["snow", "ice", "sleet", "blizzard"])

                if is_hour_thunderstorm: is_game_thunderstorm = True
                if is_hour_snow: is_game_snow = True
                if chance > max_chance_in_window: max_chance_in_window = chance

                hour_iso = datetime.fromtimestamp(hour['time_epoch'], timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                hourly_slice.append({
                    "timestamp": hour_iso,
                    "temp": round(hour.get('temp_f', 72)),
                    "precipChance": chance,
                    "isThunderstorm": is_hour_thunderstorm,
                    "isSnow": is_hour_snow,
                    "weatherCode": weather_code
                })

            kickoff_hour = all_hours[start_idx] if len(all_hours) > start_idx else (all_hours[0] if all_hours else {})

            return {
                "status": "ok",
                "lastUpdated": datetime.now(timezone.utc).timestamp(),
                "temp": round(kickoff_hour.get('temp_f', 70)),
                "humidity": round(kickoff_hour.get('humidity', 50)),
                "maxPrecipChance": max_chance_in_window,
                "isThunderstorm": is_game_thunderstorm,
                "isSnow": is_game_snow,
                "windSpeed": round(kickoff_hour.get('wind_mph', 0)),
                "windDir": kickoff_hour.get('wind_degree', 0),
                "hourly": hourly_slice
            }
        except Exception as e:
            print(f"⚠️ WeatherAPI fetch failed with error: {e}")
            return {"temp": "--", "hourly": []}

    return {"temp": "--", "hourly": []}
def run_weather_update(est_now):
    global API_CALL_TRACKER

    date_str = est_now.strftime('%Y-%m-%d')
    print(f"🚀 Updating Weather Data for {date_str} (EST)")

    session = requests.Session()
    stadiums = load_json(STADIUMS_FILE, [])
    odds_data = load_json(ODDS_FILE, {}).get('odds', [])

    API_CALL_TRACKER["schedule"] += 1
    sport_ids = get_active_sport_ids()
    schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId={sport_ids}&startDate={date_str}&endDate={date_str}&hydrate=linescore,venue,probablePitcher,lineups,person"

    try:
        schedule_data = session.get(schedule_url, timeout=15).json()
    except Exception as e:
        print(f"❌ Failed to fetch schedule: {e}")
        return []

    daily_file_path = os.path.join(DAILY_FILES_DIR, f'games_{date_str}.json')
    daily_memory = {}
    if os.path.exists(daily_file_path):
        for g in load_json(daily_file_path, []):
            daily_memory[str(g['gameRaw']['gamePk'])] = g

    games_list = []
    calls_made_this_run = 0

    for date_item in schedule_data.get('dates', []):
        for game in date_item.get('games', []):
            game_pk = str(game['gamePk'])
            existing_game_state = daily_memory.get(game_pk, {})

            game_odds = None
            away_team_name = game.get('teams', {}).get('away', {}).get('team', {}).get('name', '')
            home_team_name = game.get('teams', {}).get('home', {}).get('team', {}).get('name', '')
            game_time_dt = datetime.strptime(game['gameDate'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            game_time_ms = game_time_dt.timestamp() * 1000

            def parse_odds_time(d_str):
                if d_str.endswith('Z'): d_str = d_str[:-1]
                if len(d_str.split(':')) == 2: d_str += ":00"
                return datetime.strptime(d_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000

            potential_odds = [o for o in odds_data if o['home_team'] == home_team_name and o['away_team'] == away_team_name]
            if potential_odds:
                game_odds = sorted(potential_odds, key=lambda o: abs(parse_odds_time(o['commence_time']) - game_time_ms))[0]

            venue_id = game.get('venue', {}).get('id')
            stadium = next((s for s in stadiums if s.get('id') == venue_id), None)
            weather_data = existing_game_state.get('weather')
            needs_weather_fetch = True

            if stadium and weather_data and weather_data.get('temp') != '--':
                last_updated = weather_data.get('lastUpdated', 0)
                last_updated_dt = datetime.fromtimestamp(last_updated, est_now.tzinfo)
                game_status = game.get('status', {}).get('abstractGameState', '')

                if game_status in ['Final', 'Game Over']:
                    needs_weather_fetch = False
                elif last_updated_dt.hour == est_now.hour and last_updated_dt.date() == est_now.date():
                    needs_weather_fetch = False
            if stadium and needs_weather_fetch:
                print(f"   ☁️ Fetching Weather for {away_team_name} @ {home_team_name}")
                new_weather = fetch_game_weather(session, stadium['lat'], stadium['lon'], game['gameDate'])
                calls_made_this_run += 1

                if new_weather.get('temp') == '--' and weather_data and weather_data.get('temp') != '--':
                    print("      🛡️ Fetch failed, keeping existing cached weather.")
                else:
                    weather_data = new_weather

                time.sleep(0.2)
            wind_data, is_roof_closed, is_roof_pending = None, False, False

            if stadium and stadium.get('roof'):
                try:
                    live_feed_url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
                    live_res = session.get(live_feed_url, timeout=5)
                    if live_res.status_code == 200:
                        mlb_weather = live_res.json().get('gameData', {}).get('weather', {})
                        if mlb_weather.get('condition') in ["Roof Closed", "Dome"]:
                            is_roof_closed = True
                except Exception: pass

            if stadium and weather_data and weather_data.get('status') != "too_early" and weather_data.get('temp') != '--':
                wind_data = calculate_wind(weather_data.get('windDir'), stadium.get('bearing'))
                if stadium.get('dome'):
                    is_roof_closed = True
                elif stadium.get('roof') and not is_roof_closed:
                    temp = weather_data.get('temp', 70)
                    precip = weather_data.get('maxPrecipChance', 0)
                    if precip >= 30 or temp <= 50 or temp >= 95: is_roof_closed = True
                    elif precip >= 15 or temp <= 55 or temp >= 90: is_roof_pending = True

                if is_roof_closed:
                    wind_data = {"text": "Roof Closed", "cssClass": "bg-secondary text-white", "arrow": ""}
                    weather_data['windSpeed'] = 0

            games_list.append({
                "gameRaw": game,
                "stadium": stadium,
                "odds": game_odds,
                "weather": weather_data,
                "wind": wind_data,
                "roof": is_roof_closed,
                "roofPending": is_roof_pending,
                "lineupHandedness": existing_game_state.get('lineupHandedness', {}),
                "lineupPositions": existing_game_state.get('lineupPositions', {})
            })

    save_json(daily_file_path, games_list)
    print(f"✅ Created/Updated {daily_file_path} with {len(games_list)} games.")
    return games_list

# ==========================================
# 3. HTML & CARD BUILDER HELPERS
# ==========================================
def write_if_changed(filepath, new_content):
    """Compares new HTML against existing HTML. Writes and returns True only if changed."""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            old_content = f.read()
        if old_content == new_content:
            return False
            
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True

def get_short_team_name(full_name):
    if not full_name: return ""
    if "Red Sox" in full_name: return "Red Sox"
    if "White Sox" in full_name: return "White Sox"
    if "Blue Jays" in full_name: return "Blue Jays"
    if "Diamondbacks" in full_name: return "Dbacks"
    parts = full_name.split()
    return parts[-1] if parts else ""

def format_player_name(full_name):
    if not full_name: return ""
    parts = full_name.split()
    if len(parts) == 1: return full_name
    return f"{parts[0][0]}. {' '.join(parts[1:])}"

def get_wind_arrow_emoji(direction):
    if direction is None: return "💨"
    if isinstance(direction, (int, float)):
        val = int((direction / 22.5) + 0.5)
        arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
        direction = arr[(val % 16)]
    mapping = {
        "N": "⬇️", "NNE": "⬇️", "NE": "↙️", "ENE": "↙️",
        "E": "⬅️", "ESE": "⬅️", "SE": "↖️", "SSE": "↖️",
        "S": "⬆️", "SSW": "⬆️", "SW": "↗️", "WSW": "↗️",
        "W": "➡️", "WNW": "➡️", "NW": "↘️", "NNW": "↘️"
    }
    return mapping.get(str(direction).upper(), "💨")

def get_weather_emoji_string(data):
    w = data.get('weather') or {}
    wind = data.get('wind') or {}
    arrow = wind.get('arrow') or get_wind_arrow_emoji(w.get('windDir'))
    is_roof_closed = data.get('roof', False)
    rain = 0 if is_roof_closed else round(float(w.get('maxPrecipChance') or 0))
    temp = round(float(w.get('temp') or 0))
    hum = round(float(w.get('humidity') or 0))
    wind_spd = 0 if is_roof_closed else round(float(w.get('windSpeed') or 0))

    if w.get('status') == "too_early" or w.get('temp') == '--' or 'temp' not in w:
        return "Forecast Unavailable"
    elif is_roof_closed:
        return f"Roof Closed 🌡️{temp}° 💧{hum}%"
    return f"🌧️{rain}% 🌡️{temp}° 💧{hum}% {arrow}{wind_spd}mph"

def get_weather_blurb(data):
    stadium = data.get('stadium') or {}
    is_roof_closed = data.get('roof', False)
    is_roof_pending = data.get('roofPending', False)
    weather = data.get('weather') or {}
    wind_info = data.get('wind') or {}
    
    if is_roof_closed or stadium.get('dome'):
        return "This game is played indoors or with the roof closed. Weather conditions will not directly impact the field."
    if weather.get('status') == "too_early" or weather.get('temp') == '--' or not weather:
        return "A detailed weather forecast is not yet available for this game. Check back closer to first pitch."
        
    temp = weather.get('temp', 70)
    wind_spd = weather.get('windSpeed', 0)
    wind_dir_text = wind_info.get('text', '')
    max_pop = weather.get('maxPrecipChance', 0)
    is_thunder = weather.get('isThunderstorm', False)
    is_snow = weather.get('isSnow', False)
    
    blurb = f"Expect temperatures around {temp}°F at first pitch with {wind_spd} mph winds"
    if wind_dir_text and wind_dir_text != "Unknown":
        blurb += f" ({wind_dir_text}). "
    else:
        blurb += ". "
    
    if is_thunder:
        blurb += f"There is a risk of thunderstorms and a {max_pop}% chance of rain, making delays possible."
    elif is_snow:
        blurb += f"Snow is possible with a {max_pop}% chance of precipitation."
    elif max_pop >= 30:
        blurb += f"There is a {max_pop}% chance of rain during the game."
    else:
        blurb += "Conditions look mostly clear with a minimal chance of rain."
        
    if wind_spd >= 10 and "Blowing OUT" in wind_dir_text:
        blurb += " Wind blowing out creates highly favorable hitting conditions for home runs."
    elif wind_spd >= 10 and "Blowing IN" in wind_dir_text:
        blurb += " Wind blowing in will knock down deep fly balls."
        
    if is_roof_pending:
        blurb += " Note: The stadium roof status is pending due to borderline weather."
        
    return blurb

def generate_matchup_analysis(weather, wind_info, is_roof_closed, is_roof_pending, stadium):
    if is_roof_closed:
        return "✅ <b>Roof Closed:</b> Controlled environment with zero weather impact."

    notes = []
    if is_roof_pending:
        notes.append("🏟️ <b>Roof Status Pending:</b> Borderline weather. The team may elect to close the roof.")

    if weather.get('isThunderstorm'):
        if stadium and stadium.get('roof'):
            notes.append("⚡ <b>Lightning Risk:</b> Thunderstorms detected. Possible delay to close roof.")
        else:
            notes.append("⚡ <b>Lightning Risk:</b> Thunderstorms detected. Mandatory 30-minute safety delays are likely.")

    if weather.get('isSnow'):
        notes.append("❄️ <b>Snow Risk:</b> Low visibility and slippery field conditions could delay play.")

    hourly = weather.get('hourly', [])
    sustained_rain = len([h for h in hourly if h.get('precipChance', 0) >= 60])
    max_precip = weather.get('maxPrecipChance', 0)

    if sustained_rain >= 3:
        notes.append("🌧️ <b>Rainout Risk:</b> Sustained heavy rain. Possibility of postponement.")
    elif max_precip >= 70:
        notes.append("☔ <b>Severe Delay Risk:</b> Heavy rain expected, but should pass. Delays likely.")
    elif max_precip >= 30:
        notes.append("☔ <b>Delay Risk:</b> Scattered showers could interrupt play.")

    hum = weather.get('humidity', 50)
    if hum <= 30:
        notes.append("🌵 <b>Dry Air (<30%):</b> Sharp breaking balls (Pitcher Adv), but the ball travels up to 4.5ft farther (Hitter Adv).")
    elif hum >= 70:
        notes.append("💧 <b>High Humidity (>70%):</b> Breaking balls hang/flatten (Hitter Adv), but the ball travels shorter distances (Pitcher Adv).")

    temp = weather.get('temp', 70)
    if temp >= 85:
        notes.append("🔥 <b>Hitter Friendly:</b> High temps reduce air density, helping fly balls carry.")
    elif temp <= 50:
        notes.append("❄️ <b>Pitcher Friendly:</b> Cold, dense air suppresses ball flight and scoring.")

    wind_speed = weather.get('windSpeed', 0)
    if wind_speed >= 8 and wind_info:
        dir_text = wind_info.get('text', '')
        if "Blowing OUT" in dir_text: notes.append("🚀 <b>Home Runs:</b> Strong wind blowing out creates ideal hitting conditions.")
        elif "Blowing IN" in dir_text: notes.append("🛑 <b>Suppressed:</b> Wind blowing in will knock down fly balls. Advantage pitchers.")
        elif "Out to Right" in dir_text: notes.append("↗️ <b>Lefty Advantage:</b> Wind blowing out to Right Field favors <b>Left-Handed</b> power.")
        elif "Out to Left" in dir_text: notes.append("↖️ <b>Righty Advantage:</b> Wind blowing out to Left Field favors <b>Right-Handed</b> power.")
        elif "In from Right" in dir_text: notes.append("📉 <b>Lefty Nightmare:</b> Wind blowing in from Right knocks down Lefty power.")
        elif "In from Left" in dir_text: notes.append("📉 <b>Righty Nightmare:</b> Wind blowing in from Left knocks down Righty power.")
        elif "Cross" in dir_text: notes.append("↔️ <b>Tricky:</b> Crosswinds may affect outfield defense and breaking balls.")

    if not notes:
        return "✅ <b>Neutral:</b> Fair weather conditions. No significant advantage."
    return "<br>".join(notes)

def get_hourly_icon(code, precip_chance, is_night, is_thunderstorm=False, is_snow=False):
    if is_thunderstorm or code == 8000:
        return '⛈️'
    if is_snow or (5000 <= code < 6000):
        return '🌨️'
    if (4000 <= code < 5000) or precip_chance >= 50:
        return '🌧️'
    
    # Cloud & Sky Condition Mapping
    if code == 1000:          # Clear
        return '🌙' if is_night else '☀️'
    elif code == 1100:        # Mostly Clear
        return '🌙' if is_night else '🌤️'
    elif code == 1101:        # Partly Cloudy
        return '🌙' if is_night else '⛅'
    elif code in [1102, 1001]:# Mostly Cloudy / Overcast
        return '☁️'
    elif 2000 <= code < 3000: # Fog / Haze
        return '🌫️'
    
    # Fallback based on rain chance
    if precip_chance >= 30:
        return '🌧️'
    elif precip_chance > 0:
        return '⛅'
    return '🌙' if is_night else '☀️'

def render_main_game_card(data):
    game = data['gameRaw']
    stadium = data.get('stadium') or {}
    weather = data.get('weather') or {}
    wind_info = data.get('wind') or {}
    is_roof_closed = data.get('roof', False)
    is_roof_pending = data.get('roofPending', False)

    border_class = ""
    if weather and not is_roof_closed and weather.get('temp') != '--':
        hourly = weather.get('hourly', [])
        sustained_rain = len([h for h in hourly if h.get('precipChance', 0) >= 60])
        if weather.get('isThunderstorm'):
            border_class = "border-warning border-3" if stadium.get('roof') else "border-danger border-3"
        elif sustained_rain >= 3:
            border_class = "border-danger border-3"
        elif weather.get('maxPrecipChance', 0) >= 30:
            border_class = "border-warning border-3"

    bg_class = "bg-weather-sunny"
    if is_roof_closed:
        bg_class = "bg-weather-roof"
    elif weather and weather.get('temp') != '--':
        if weather.get('isThunderstorm'): bg_class = "bg-weather-storm"
        elif weather.get('isSnow'): bg_class = "bg-weather-snow"
        elif weather.get('maxPrecipChance', 0) >= 50: bg_class = "bg-weather-rain"
        elif weather.get('maxPrecipChance', 0) >= 20: bg_class = "bg-weather-cloudy"
        elif weather.get('temp', 0) >= 90: bg_class = "bg-weather-sunny"
    else:
        bg_class = "bg-light"

    away_team, home_team = game['teams']['away'], game['teams']['home']
    away_id, home_id = away_team['team']['id'], home_team['team']['id']
    away_name, home_name = away_team['team']['name'], home_team['team']['name']
    away_short, home_short = get_short_team_name(away_name), get_short_team_name(home_name)
    away_logo = f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{away_id}.svg"
    home_logo = f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{home_id}.svg"

    utc_date = datetime.fromisoformat(game['gameDate'].replace('Z', '+00:00'))
    et_date = utc_date.astimezone(zoneinfo.ZoneInfo("America/New_York"))
    game_time = et_date.strftime("%I:%M %p").lstrip("0")
    time_badge_class = "bg-light text-dark border"

    match_state = game.get('status', {}).get('detailedState', '')
    if "Postponed" in match_state: game_time = "Postponed"; time_badge_class = "bg-danger text-white"
    elif "Cancel" in match_state: game_time = "Canceled"; time_badge_class = "bg-danger text-white"
    elif "Delay" in match_state: game_time = "Delayed"; time_badge_class = "bg-warning text-dark"
    elif match_state in ["In Progress", "Live"]: game_time = "Live"; time_badge_class = "bg-success text-white"
    elif game.get('status', {}).get('abstractGameState') == "Final": game_time = "Final"; time_badge_class = "bg-secondary text-white"

    away_p_info = away_team.get('probablePitcher')
    away_pitcher = format_player_name(away_p_info['fullName']) + (f" ({away_p_info['pitchHand']['code']})" if away_p_info and 'pitchHand' in away_p_info else "") if away_p_info else "TBD"

    home_p_info = home_team.get('probablePitcher')
    home_pitcher = format_player_name(home_p_info['fullName']) + (f" ({home_p_info['pitchHand']['code']})" if home_p_info and 'pitchHand' in home_p_info else "") if home_p_info else "TBD"

    odds_data = data.get('odds')
    ml_away = '<span class="badge bg-light text-muted border" style="font-size: 0.65rem;">TBD</span>'
    ml_home = '<span class="badge bg-light text-muted border" style="font-size: 0.65rem;">TBD</span>'
    total_badge = ""

    if odds_data and odds_data.get('bookmakers'):
        bookie = next((b for b in odds_data['bookmakers'] if b['key'] == 'fanduel'), odds_data['bookmakers'][0])
        if bookie and bookie.get('markets'):
            h2h = next((m for m in bookie['markets'] if m['key'] == 'h2h'), None)
            if h2h and h2h.get('outcomes'):
                ao = next((o for o in h2h['outcomes'] if o['name'] == away_name), None)
                ho = next((o for o in h2h['outcomes'] if o['name'] == home_name), None)
                if ao: ml_away = f'<span class="badge bg-light text-dark border" style="font-size: 0.65rem;">{("+" + str(ao["price"])) if ao["price"] > 0 else ao["price"]}</span>'
                if ho: ml_home = f'<span class="badge bg-light text-dark border" style="font-size: 0.65rem;">{("+" + str(ho["price"])) if ho["price"] > 0 else ho["price"]}</span>'

            totals = next((m for m in bookie['markets'] if m['key'] == 'totals'), None)
            if totals and totals.get('outcomes'):
                total_badge = f'<span class="badge bg-secondary ms-1" style="font-size: 0.65rem;">O/U {totals["outcomes"][0]["point"]}</span>'

    weather_html = '<div class="text-muted p-3 text-center small">Weather forecast unavailable.<br></div>'
    if stadium and weather:
        if weather.get('status') == "too_early":
            weather_html = '''<div class="text-center p-3"><h6 class="text-muted mb-1">🔭 Too Early to Forecast</h6><p class="small text-muted mb-0" style="font-size: 0.75rem;">Forecasts available ~14 days out.</p></div>'''
        elif weather.get('temp') != '--':
            display_rain = "0%" if is_roof_closed else f"{weather.get('maxPrecipChance', 0)}%"
            precip_label = "Rain"
            if not is_roof_closed:
                if weather.get('isThunderstorm'): display_rain += " ⚡"
                elif weather.get('isSnow'): display_rain += " ❄️"; precip_label = "Snow"

            radar_url = f"https://embed.windy.com/embed2.html?lat={stadium.get('lat')}&lon={stadium.get('lon')}&detailLat={stadium.get('lat')}&detailLon={stadium.get('lon')}&width=650&height=450&zoom=11&level=surface&overlay=rain&product=ecmwf&menu=&message=&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=mph&metricTemp=%C2%B0F&radarRange=-1"

            hourly_html = ''
            if is_roof_closed:
                hourly_html = '<div class="text-center mt-2"><small class="text-muted">Indoor Conditions</small></div>'
            elif weather.get('hourly'):
                cards = []
                for h in weather['hourly']:
                    ts = h.get('timestamp')
                    h_dt = datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(zoneinfo.ZoneInfo("America/New_York")) if ts else datetime.now(zoneinfo.ZoneInfo("America/New_York"))
                    time_label = h_dt.strftime("%I%p").lstrip("0")
                    is_night = h_dt.hour >= 20 or h_dt.hour < 6

                    code = h.get('weatherCode', 1000)
                    icon = get_hourly_icon(code, h.get('precipChance', 0), is_night, h.get('isThunderstorm'), h.get('isSnow'))

                    pop_html = '&nbsp;'
                    if h.get('precipChance', 0) > 0:
                        pop_html = f"{h['precipChance']}%"

                    cards.append(f'''<div class="hour-card"><div class="hour-time">{time_label}</div><div class="hour-icon">{icon}</div><div class="hour-pop">{pop_html}</div><div class="hour-temp">{h.get("temp", "--")}°</div></div>''')
                    hourly_html = f'''<div class="hourly-scroll-container">{"".join(cards)}</div>'''

            wind_arrow = f'<span class="arrow-emoji">{wind_info.get("arrow")}</span>' if wind_info else "💨"
            wind_css = wind_info.get("cssClass", "bg-secondary") if wind_info else "bg-secondary"

            weather_html = f'''
                <div class="weather-row row text-center align-items-center mt-2">
                    <div class="col-3 border-end px-1"><div class="fw-bold">{weather.get("temp")}°F</div><div class="small text-muted" style="font-size: 0.7rem;">Temp</div></div>
                    <div class="col-3 border-end px-1"><div class="fw-bold text-dark">{weather.get("humidity")}%</div><div class="small text-muted" style="font-size: 0.7rem;">Hum</div></div>
                    <div class="col-3 border-end px-1"><div class="fw-bold text-primary" style="white-space: nowrap;">{display_rain}</div><div class="small text-muted" style="font-size: 0.7rem;">{precip_label}</div></div>
                    <div class="col-3 px-1"><div class="fw-bold">{weather.get("windSpeed")} <span style="font-size:0.7em">mph</span></div><span class="wind-badge {wind_css}" style="font-size: 0.55rem; white-space: nowrap; display: inline-block; padding: 2px 4px;">{wind_arrow}</span></div>
                </div>
                {hourly_html}
                <div class="mt-2"><button class="btn btn-sm btn-outline-primary w-100 py-1" onclick="showRadar('{radar_url}', '{game.get("venue", {}).get("name", "Stadium")}')">🗺️ View Live Radar</button></div>
                <div class="analysis-box"><span class="analysis-title">✨ Weather Impact</span>{generate_matchup_analysis(weather, wind_info, is_roof_closed, is_roof_pending, stadium)}</div>
            '''

    emoji_line = get_weather_emoji_string(data)
    game_date_iso = game['gameDate']
    precip_chance = weather.get('maxPrecipChance', 0) if weather else 0
    temp_val = weather.get('temp', 0) if (weather and weather.get('temp') != '--') else -999
    wind_val = weather.get('windSpeed', 0) if (weather and weather.get('temp') != '--') else -999
    hum_val = weather.get('humidity', 0) if (weather and weather.get('temp') != '--') else -999
    is_risk = 1 if (weather and not is_roof_closed and precip_chance >= 30) else 0

    return f'''
    <div class="col-md-6 col-lg-4 col-xl-3 animate-card mb-2 px-1 game-card-wrapper" 
         id="game-{game['gamePk']}"
         data-game-date="{game_date_iso}"
         data-wind="{wind_val}"
         data-rain="{precip_chance}"
         data-temp="{temp_val}"
         data-humidity="{hum_val}"
         data-risk="{is_risk}"
         data-teams="{away_name.lower()} {home_name.lower()}">
        <div class="card game-card shadow-sm {border_class} {bg_class}" style="overflow: hidden;">
            <div class="ribbon-view p-2 position-relative" onclick="toggleSingleCard(event, '{game['gamePk']}')" style="cursor: pointer; display: block;">
                <div class="d-flex align-items-center mb-1">
                    <span class="badge {time_badge_class} flex-shrink-0 px-2 py-1" style="font-size: 0.65rem;">{game_time}</span>
                    <div class="fw-bold text-dark text-center flex-grow-1 ms-2" style="font-size: 0.75rem; letter-spacing: 0.2px;">{emoji_line}</div>
                </div>
                <div class="d-flex align-items-center mt-1" style="gap: 4px;">
                    <div class="d-flex align-items-center flex-shrink-0" style="gap: 3px;">
                        <img src="{away_logo}" style="width: 16px; height: 16px; object-fit: contain;" onerror="this.style.display='none'">
                        <span class="fw-bold text-dark lh-1" style="font-size: 0.75rem; letter-spacing: -0.3px;">{away_short}</span>
                    </div>
                    <span class="fw-bold text-muted flex-shrink-0 lh-1" style="font-size: 0.7rem;">@</span>
                    <div class="d-flex align-items-center flex-shrink-0" style="gap: 3px;">
                        <img src="{home_logo}" style="width: 16px; height: 16px; object-fit: contain;" onerror="this.style.display='none'">
                        <span class="fw-bold text-dark lh-1" style="font-size: 0.75rem; letter-spacing: -0.3px;">{home_short}</span>
                    </div>
                    <div class="text-truncate text-end fw-bold flex-grow-1 ms-1" style="font-size: 0.7rem; opacity: 0.75;">{game.get('venue', {}).get('name', 'TBD')}</div>
                </div>
            </div>
            <div class="full-card-view" onclick="toggleSingleCard(event, '{game['gamePk']}')" style="cursor: pointer; display: none;">
                <div class="card-body px-2 pt-2 pb-2"> 
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div class="d-flex align-items-center"><span class="badge {time_badge_class}">{game_time}</span>{total_badge}</div>
                        <span class="stadium-name text-truncate text-end flex-grow-1 ms-2" style="font-size: 0.8rem; font-weight: 600;">{game.get('venue', {}).get('name', 'TBD')}</span>
                    </div>
                    <div class="d-flex justify-content-between align-items-center px-1 mb-1">
                        <div class="d-flex align-items-center text-truncate" style="width: 45%; min-width: 0;"> 
                            <img src="{away_logo}" alt="{away_name}" class="me-2" style="width: 20px; height: 20px; object-fit: contain;" onerror="this.style.display='none'">
                            <div class="fw-bold lh-sm text-dark text-truncate" style="font-size: 0.95rem;">{away_short}</div>
                        </div>
                        <div class="text-center text-muted fw-bold" style="width: 10%; font-size: 0.8rem;">@</div>
                        <div class="d-flex align-items-center justify-content-end text-truncate" style="width: 45%; min-width: 0;"> 
                            <img src="{home_logo}" alt="{home_name}" class="me-2" style="width: 20px; height: 20px; object-fit: contain;" onerror="this.style.display='none'">
                            <div class="fw-bold lh-sm text-dark text-truncate text-end" style="font-size: 0.95rem;">{home_short}</div>
                        </div>
                    </div>
                    <div class="d-flex justify-content-between align-items-center px-1 mb-2">
                        <div class="d-flex align-items-center text-truncate" style="width: 48%;"><span class="text-muted text-truncate me-2" style="font-size: 0.75rem;">{away_pitcher}</span>{ml_away}</div>
                        <div class="d-flex align-items-center justify-content-end text-truncate" style="width: 48%;"><span class="text-muted text-truncate me-2 text-end" style="font-size: 0.75rem;">{home_pitcher}</span>{ml_home}</div>
                    </div>
                    <div class="px-2 pt-2 pb-1 w-100 border-top mt-1 mb-1">
                        <a href="https://mlbstartingnine.com/#game-{game['gamePk']}" target="_blank" class="btn btn-sm w-100 text-decoration-none shadow-sm" style="background-color: #f8f9fa; border: 1px solid #dee2e6; color: #0d6efd; font-weight: 700; font-size: 0.75rem;">📋 View Projected/Starting Lineups</a>
                    </div>
                    {weather_html}
                </div>
            </div>
        </div>
    </div>
    '''

def render_standalone_team_card(data):
    game = data['gameRaw']
    stadium = data.get('stadium') or {}
    weather = data.get('weather') or {}
    wind_info = data.get('wind') or {}
    is_roof_closed = data.get('roof', False)
    is_roof_pending = data.get('roofPending', False)

    border_class = ""
    if weather and not is_roof_closed and weather.get('temp') != '--':
        hourly = weather.get('hourly', [])
        sustained_rain = len([h for h in hourly if h.get('precipChance', 0) >= 60])
        if weather.get('isThunderstorm'):
            border_class = "border-warning border-3" if stadium.get('roof') else "border-danger border-3"
        elif sustained_rain >= 3:
            border_class = "border-danger border-3"
        elif weather.get('maxPrecipChance', 0) >= 30:
            border_class = "border-warning border-3"

    bg_class = "bg-weather-sunny"
    if is_roof_closed: bg_class = "bg-weather-roof"
    elif weather and weather.get('temp') != '--':
        if weather.get('isThunderstorm'): bg_class = "bg-weather-storm"
        elif weather.get('isSnow'): bg_class = "bg-weather-snow"
        elif weather.get('maxPrecipChance', 0) >= 50: bg_class = "bg-weather-rain"
        elif weather.get('maxPrecipChance', 0) >= 20: bg_class = "bg-weather-cloudy"

    away_team, home_team = game['teams']['away'], game['teams']['home']
    away_short, home_short = get_short_team_name(away_team['team']['name']), get_short_team_name(home_team['team']['name'])
    away_logo = f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{away_team['team']['id']}.svg"
    home_logo = f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{home_team['team']['id']}.svg"

    utc_date = datetime.fromisoformat(game['gameDate'].replace('Z', '+00:00'))
    et_date = utc_date.astimezone(zoneinfo.ZoneInfo("America/New_York"))
    game_time = et_date.strftime("%I:%M %p").lstrip("0")
    time_badge_class = "bg-light text-dark border"

    match_state = game.get('status', {}).get('detailedState', '')
    if "Postponed" in match_state: game_time = "Postponed"; time_badge_class = "bg-danger text-white"
    elif "Delay" in match_state: game_time = "Delayed"; time_badge_class = "bg-warning text-dark"
    elif match_state in ["In Progress", "Live"]: game_time = "Live"; time_badge_class = "bg-success text-white"
    elif game.get('status', {}).get('abstractGameState') == "Final": game_time = "Final"; time_badge_class = "bg-secondary text-white"

    away_p_info = away_team.get('probablePitcher')
    away_pitcher = format_player_name(away_p_info['fullName']) + (f" ({away_p_info['pitchHand']['code']})" if away_p_info and 'pitchHand' in away_p_info else "") if away_p_info else "TBD"

    home_p_info = home_team.get('probablePitcher')
    home_pitcher = format_player_name(home_p_info['fullName']) + (f" ({home_p_info['pitchHand']['code']})" if home_p_info and 'pitchHand' in home_p_info else "") if home_p_info else "TBD"

    ml_away = '<span class="badge bg-light text-muted border" style="font-size: 0.65rem;">TBD</span>'
    ml_home = '<span class="badge bg-light text-muted border" style="font-size: 0.65rem;">TBD</span>'
    total_badge = ""

    odds_data = data.get('odds')
    if odds_data and odds_data.get('bookmakers'):
        bookie = next((b for b in odds_data['bookmakers'] if b['key'] == 'draftkings'), odds_data['bookmakers'][0])
        if bookie and bookie.get('markets'):
            h2h = next((m for m in bookie['markets'] if m['key'] == 'h2h'), None)
            if h2h and h2h.get('outcomes'):
                ao = next((o for o in h2h['outcomes'] if o['name'] == away_team['team']['name']), None)
                ho = next((o for o in h2h['outcomes'] if o['name'] == home_team['team']['name']), None)
                if ao: ml_away = f'<span class="badge bg-light text-dark border" style="font-size: 0.65rem;">{("+" + str(ao["price"])) if ao["price"] > 0 else ao["price"]}</span>'
                if ho: ml_home = f'<span class="badge bg-light text-dark border" style="font-size: 0.65rem;">{("+" + str(ho["price"])) if ho["price"] > 0 else ho["price"]}</span>'

            totals = next((m for m in bookie['markets'] if m['key'] == 'totals'), None)
            if totals and totals.get('outcomes'):
                total_badge = f'<span class="badge bg-secondary ms-1" style="font-size: 0.65rem;">O/U {totals["outcomes"][0]["point"]}</span>'

    weather_html = '<div class="text-muted p-3 text-center small">Weather forecast unavailable.</div>'
    if stadium and weather and weather.get('temp') != '--':
        display_rain = "0%" if is_roof_closed else f"{weather.get('maxPrecipChance', 0)}%"
        hourly_html = ''
        if is_roof_closed:
            hourly_html = '<div class="text-center mt-2"><small class="text-muted">Indoor Conditions Controlled</small></div>'
        elif weather.get('hourly'):
            hours_markup = []
            for h in weather['hourly']:
                ts = h.get('timestamp')
                h_dt = datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(zoneinfo.ZoneInfo("America/New_York")) if ts else datetime.now(zoneinfo.ZoneInfo("America/New_York"))
                time_label = h_dt.strftime("%I%p").lstrip("0")
                is_night = h_dt.hour >= 20 or h_dt.hour < 6

                code = h.get('weatherCode', 1000)
                icon = get_hourly_icon(code, h.get('precipChance', 0), is_night, h.get('isThunderstorm'), h.get('isSnow'))

                pop_html = '&nbsp;'
                if h.get('precipChance', 0) > 0:
                    pop_html = f"{h['precipChance']}%"

                hours_markup.append(f'<div class="hour-card"><div class="hour-time">{time_label}</div><div class="hour-icon">{icon}</div><div class="hour-pop">{pop_html}</div><div class="hour-temp">{h.get("temp", "--")}°</div></div>')
                hourly_html = f'<div class="hourly-scroll-container">{"".join(hours_markup)}</div>'

        wind_arrow = f'<span class="arrow-emoji">{wind_info.get("arrow")}</span>' if wind_info else "💨"
        wind_css = wind_info.get("cssClass", "bg-secondary") if wind_info else "bg-secondary"
        radar_url = f"https://embed.windy.com/embed2.html?lat={stadium.get('lat')}&lon={stadium.get('lon')}&detailLat={stadium.get('lat')}&detailLon={stadium.get('lon')}&width=650&height=450&zoom=11&level=surface&overlay=rain&product=ecmwf&menu=&message=&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=mph&metricTemp=%C2%B0F&radarRange=-1"

        weather_html = f'''
            <div class="weather-row row text-center align-items-center mt-2">
                <div class="col-3 border-end px-1"><div class="fw-bold">{weather.get("temp")}°F</div><div class="small text-muted" style="font-size: 0.7rem;">Temp</div></div>
                <div class="col-3 border-end px-1"><div class="fw-bold text-dark">{weather.get("humidity")}%</div><div class="small text-muted" style="font-size: 0.7rem;">Hum</div></div>
                <div class="col-3 border-end px-1"><div class="fw-bold text-primary">{display_rain}</div><div class="small text-muted" style="font-size: 0.7rem;">Rain</div></div>
                <div class="col-3 px-1"><div class="fw-bold">{weather.get("windSpeed")} <span style="font-size:0.7em">mph</span></div><span class="wind-badge {wind_css}" style="font-size: 0.55rem; white-space: nowrap; display: inline-block; padding: 2px 4px;">{wind_arrow}</span></div>
            </div>
            {hourly_html}
            <div class="mt-2 mb-2">
                <a href="{radar_url}" target="_blank" class="btn btn-sm btn-outline-primary w-100 py-1" style="font-weight: 600; font-size: 0.8rem;">🗺️ View Live Radar Map</a>
            </div>
            <div class="analysis-box"><span class="analysis-title">✨ Weather Impact Analysis</span>{generate_matchup_analysis(weather, wind_info, is_roof_closed, is_roof_pending, stadium)}</div>
        '''

    target_slug = next((t['slug'] for t in MLB_TEAMS if t['id'] in [away_team['team']['id'], home_team['team']['id']]), "")

    return f'''
    <div class="card game-card shadow-sm {border_class} {bg_class}">
        <div class="card-body p-3"> 
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div><span class="badge {time_badge_class}">{game_time}</span>{total_badge}</div>
                <span class="stadium-name text-truncate text-end flex-grow-1 ms-2">{game.get('venue', {}).get('name', 'TBD')}</span>
            </div>
            <div class="d-flex justify-content-between align-items-center px-1 mb-2">
                <div class="d-flex align-items-center text-truncate" style="width: 45%; min-width: 0;"> 
                    <img src="{away_logo}" class="me-2" style="width: 28px; height: 28px; object-fit: contain;">
                    <div class="fw-bold lh-sm text-dark text-truncate" style="font-size: 1.15rem;">{away_short}</div>
                </div>
                <div class="text-center text-muted fw-bold" style="width: 10%; font-size: 0.9rem;">@</div>
                <div class="d-flex align-items-center justify-content-end text-truncate" style="width: 45%; min-width: 0;"> 
                    <img src="{home_logo}" class="me-2" style="width: 28px; height: 28px; object-fit: contain;">
                    <div class="fw-bold lh-sm text-dark text-truncate text-end" style="font-size: 1.15rem;">{home_short}</div>
                </div>
            </div>
            <div class="d-flex justify-content-between align-items-center px-1 mb-3">
                <div class="d-flex align-items-center text-truncate" style="width: 48%;"><span class="text-muted text-truncate me-2" style="font-size: 0.75rem;">{away_pitcher}</span>{ml_away}</div>
                <div class="d-flex align-items-center justify-content-end text-truncate" style="width: 48%;"><span class="text-muted text-truncate me-2 text-end" style="font-size: 0.75rem;">{home_pitcher}</span>{ml_home}</div>
            </div>
            <div class="px-0 pt-2 pb-1 w-100 border-top mt-1 mb-1">
                <a href="https://mlbstartingnine.com/lineups/{target_slug}/" target="_blank" class="btn btn-sm w-100 text-decoration-none shadow-sm" style="background-color: #f8f9fa; border: 1px solid #dee2e6; color: #0d6efd; font-weight: 700; font-size: 0.75rem;">📋 View Projected/Starting Lineups</a>
            </div>
            {weather_html}
        </div>
    </div>
    '''

# ==========================================
# 4. MASTER HTML TEMPLATES (EMBEDDED)
# ==========================================
MAIN_SITE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-0TNW6W5ZVN"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-0TNW6W5ZVN');
    </script>
    {schema_json}
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Weather MLB | MLB Weather Forecasts, DFS Lineups & Odds for {display_date}</title>
    <meta name="description" content="MLB weather forecasts, stadium wind direction, starting lineups, probable pitchers, and live betting odds for {display_date}.">
    <meta name="keywords" content="MLB weather, baseball weather, MLB starting lineups, probable pitchers, MLB betting odds, moneyline, stadium wind direction, fantasy baseball, DFS weather, rain delay risk, baseball odds">
    <meta name="author" content="WeatherMLB">
    
    <meta property="og:title" content="Weather MLB - MLB Weather, Lineups & Live Odds">
    <meta property="og:description" content="Track stadium wind, rain delay risks, starting lineups, pitchers, and live betting odds for every MLB game in one place.">
    <meta property="og:image" content="https://weathermlb.com/social-share.png">
    <meta property="og:site_name" content="Weather MLB">
    <meta property="og:url" content="https://weathermlb.com">
    <meta property="og:type" content="website">
    
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="Weather MLB - MLB Weather, Lineups & Live Odds">
    <meta name="twitter:description" content="Track stadium wind, rain delay risks, starting lineups, pitchers, and live betting odds for every MLB game in one place.">
    <meta name="twitter:image" content="https://weathermlb.com/social-share.png">
    <meta name="twitter:site" content="@weathermlbdaily">
    
    <link rel="canonical" href="https://weathermlb.com/">
    <link rel="icon" href="/favicon.ico" sizes="any">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
    <link rel="apple-touch-icon" href="/apple-touch-icon.png">

    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <style>
        body {{ background-color: #f8f9fa; }} 
        .game-card {{ 
            border: 1px solid #dee2e6; 
            border-radius: 12px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
            transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s; 
            background: white;
            overflow: hidden; 
        }}
        .game-card:hover {{ 
            transform: translateY(-5px); 
            box-shadow: 0 12px 24px rgba(0,0,0,0.1);
            border-color: #0d6efd; 
        }}
        .team-logo {{ width: 60px; height: 60px; object-fit: contain; filter: drop-shadow(0px 2px 2px rgba(0,0,0,0.1)); }}
        .weather-row {{ font-size: 0.9rem; border-top: 1px solid #f1f3f5; padding-top: 4px; margin-top: 4px; padding-bottom: 2px; }}
        .stadium-name {{ color: #6c757d; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
        .wind-badge {{ font-size: 0.85rem; padding: 6px 12px; border-radius: 20px; font-weight: 600; }}
        .wind-badge .arrow-emoji {{ font-size: 1.2rem; line-height: 0.5; vertical-align: middle; }}
        .bg-out {{ background-color: #d1e7dd; color: #0f5132; }} 
        .bg-in {{ background-color: #f8d7da; color: #842029; }}
        .bg-cross {{ background-color: #fff3cd; color: #664d03; }}
        .bg-secondary.text-white {{ background-color: #adb5bd !important; color: #fff !important; }}
        .analysis-box {{ background-color: #f8f9fa; border-left: 4px solid #0d6efd; padding: 6px 10px; margin-top: 10px; margin-bottom: 0px; font-size: 0.8rem; color: #495057; line-height: 1.3; border-radius: 0 4px 4px 0; }}
        .analysis-title {{ font-weight: 800; text-transform: uppercase; font-size: 0.7rem; color: #0d6efd; display: block; margin-bottom: 3px; letter-spacing: 0.5px; }}
        .hourly-scroll-container {{ display: flex; overflow-x: hidden; gap: 4px; padding: 4px 2px; margin-top: 2px; border-top: 1px solid #f1f3f5; scrollbar-width: none; -ms-overflow-style: none; }}
        .hourly-scroll-container::-webkit-scrollbar {{ display: none; }}
        .hour-card {{ display: flex; flex: 1; flex-direction: column; align-items: center; min-width: 0; text-align: center; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        .hour-time {{ font-size: 0.8rem; font-weight: 600; color: #6c757d; margin-bottom: 4px; }}
        .hour-icon {{ font-size: 1.5rem; line-height: 1; margin-bottom: 0px; }}
        .hour-pop {{ font-size: 0.7rem; color: #5ac8fa; font-weight: 700; line-height: 1; height: 12px; display: flex; align-items: center; margin-bottom: 2px; margin-top: 2px; }}
        .hour-temp {{ font-size: 0.95rem; font-weight: 600; margin-top: 0px; color: #212529; line-height: 1; }}

        @keyframes weather-flow {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
        .bg-weather-sunny {{ background: linear-gradient(-45deg, #e3f2fd, #e1f5fe, #f1f8e9); background-size: 300% 300%; animation: weather-flow 15s ease infinite; }}
        .bg-weather-cloudy {{ background: linear-gradient(-45deg, #f5f5f5, #e0e0e0, #eeeeee); background-size: 300% 300%; animation: weather-flow 20s ease infinite; }}
        .bg-weather-rain {{ background: linear-gradient(180deg, #e3f2fd, #cfd8dc, #eceff1); background-size: 200% 200%; animation: weather-flow 8s ease infinite; }}
        .bg-weather-storm {{ background: linear-gradient(-45deg, #e1bee7, #cfd8dc, #e0e0e0); background-size: 300% 300%; animation: weather-flow 10s ease infinite; }}
        .bg-weather-snow {{ background: linear-gradient(-45deg, #f3e5f5, #e3f2fd, #ffffff); background-size: 300% 300%; animation: weather-flow 15s ease infinite; }}
        .bg-weather-roof {{ background-color: #ffffff; }}
    </style>
</head>
<body>

<nav class="navbar shadow-sm py-2 mb-0 sticky-top border-bottom border-dark" style="background-color: #0f172a;">
    <div class="container d-flex justify-content-between align-items-center flex-row">
        <div class="d-flex align-items-center gap-2">
            <a href="https://weathermlb.com" class="navbar-brand text-white fw-bold m-0 text-decoration-none" style="font-style: italic; letter-spacing: 0.5px; font-size: 2.0rem;">
                Weather <span style="color: #5ac8fa;">MLB</span>
            </a>
            <div class="d-flex align-items-center gap-1 ms-1 ps-2" style="border-left: 1px solid rgba(255, 255, 255, 0.2);">
                <a href="https://weathernfl.com" class="p-1 text-decoration-none" title="Weather NFL" aria-label="Weather NFL">
                    <img src="https://weathernfl.com/apple-touch-icon.png" alt="Weather NFL" style="width: 26px; height: 26px; border-radius: 6px; display: block;">
                </a>
                <a href="https://weathercfb.com" class="p-1 text-decoration-none" title="Weather CFB" aria-label="Weather CFB">
                    <img src="https://weathercfb.com/apple-touch-icon.png" alt="Weather CFB" style="width: 26px; height: 26px; border-radius: 6px; display: block;">
                </a>
                <a href="https://weatherfootball.com" class="p-1 text-decoration-none" title="Weather Football" aria-label="Weather Football">
                    <img src="https://weatherfootball.com/apple-touch-icon.png" alt="Weather Football" style="width: 26px; height: 26px; border-radius: 6px; display: block;">
                </a>
            </div>
        </div>
    </div>
</nav>

<div class="container-fluid px-3 px-xl-5 mt-2">
    <div class="text-center mt-3 mb-3">
        <h1 class="h5 fw-bold text-dark mb-1">Weather MLB | Daily Forecasts, Lineups & Odds for {display_date}</h1>
        <p class="text-muted mb-0" style="font-size: 0.85rem;">Track stadium wind direction, rain delay risks, probable pitchers, and live betting lines.</p>
    </div>
    
    <div class="sticky-top bg-light border-bottom py-3 mb-4 shadow-sm" style="z-index: 100;">
        <div class="container">
            <div class="row g-2 align-items-center">
                <div class="col-12 col-md-4">
                    <select class="form-select fw-bold text-muted px-3" style="border: 1px solid #dee2e6; border-radius: 20px; height: 38px; cursor: pointer;" onchange="if(this.value) window.location.href=this.value;">
                        <option value="">🔍 Go to Team Report...</option>
                        {team_options}
                    </select>
                </div>
                <div class="col-12 col-md-4">
                    <select id="sort-filter" class="form-select">
                        <option value="time">Sort: Game Time ⏰</option>
                        <option value="wind">Sort: Highest Wind 💨</option>
                        <option value="rain">Sort: Rain Chance 🌧️</option>
                        <option value="temp">Sort: Temperature 🔥</option>
                        <option value="humidity">Sort: Humidity 💧</option>
                    </select>
                </div>
                <div class="col-12 col-md-4">
                    <div class="form-check form-switch d-flex align-items-center justify-content-center bg-white border rounded p-2" style="height: 38px;">
                        <input class="form-check-input me-2" type="checkbox" id="risk-only">
                        <label class="form-check-label small fw-bold" for="risk-only" style="white-space: nowrap;">Toggle ON for games at ⚠️Risk</label>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <input type="text" id="team-search" value="" class="d-none">
    
    <div id="games-container" class="row justify-content-start">
        {main_cards_content}
    </div>
</div>

<footer class="text-center py-5 text-muted mt-5">
    <small>Data provided by MLB Stats API & Open-Meteo Historical Weather. Not affiliated with Major League Baseball.</small>
</footer>

<div class="modal fade" id="radarModal" tabindex="-1" aria-hidden="true">
  <div class="modal-dialog modal-lg modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title">Live Radar & Forecast</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body p-0" style="height: 500px;">
        <iframe id="radarFrame" src="" width="100%" height="100%" frameborder="0" style="border:0;"></iframe>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>

<script>
let ARE_ALL_EXPANDED = false;

function toggleSingleCard(e, gamePk) {{
    if (e && e.target.closest('a, button, input, label, [data-bs-toggle="collapse"]')) return;
    const card = document.getElementById(`game-${{gamePk}}`);
    if (!card) return;
    const ribbon = card.querySelector('.ribbon-view');
    const full = card.querySelector('.full-card-view');
    if (ribbon.style.display === 'none') {{
        ribbon.style.display = 'block'; full.style.display = 'none';
    }} else {{
        ribbon.style.display = 'none'; full.style.display = 'block';
    }}
}}

function toggleAllWeatherCards() {{
    ARE_ALL_EXPANDED = !ARE_ALL_EXPANDED;
    const btnText = document.getElementById('expand-toggle-text');
    const btnIcon = document.getElementById('expand-toggle-icon');
    if (btnText && btnIcon) {{
        btnText.innerText = ARE_ALL_EXPANDED ? 'Collapse All Cards' : 'Expand All Cards';
        btnIcon.innerText = ARE_ALL_EXPANDED ? '▲' : '▼';
    }}
    document.querySelectorAll('.game-card-wrapper').forEach(card => {{
        const ribbon = card.querySelector('.ribbon-view');
        const full = card.querySelector('.full-card-view');
        if (ribbon && full) {{
            ribbon.style.display = ARE_ALL_EXPANDED ? 'none' : 'block';
            full.style.display = ARE_ALL_EXPANDED ? 'block' : 'none';
        }}
    }});
}}

function filterAndSortGames() {{
    const container = document.getElementById('games-container');
    const cards = Array.from(container.querySelectorAll('.game-card-wrapper'));
    const sortMode = document.getElementById('sort-filter').value;
    const riskOnly = document.getElementById('risk-only').checked;

    cards.forEach(card => {{
        const isRisk = card.getAttribute('data-risk') === '1';
        if (riskOnly && !isRisk) {{
            card.style.display = 'none';
        }} else {{
            card.style.display = 'block';
        }}
    }});

    cards.sort((a, b) => {{
        if (sortMode === 'wind') return parseFloat(b.getAttribute('data-wind')) - parseFloat(a.getAttribute('data-wind'));
        if (sortMode === 'rain') return parseFloat(b.getAttribute('data-rain')) - parseFloat(a.getAttribute('data-rain'));
        if (sortMode === 'temp') return parseFloat(b.getAttribute('data-temp')) - parseFloat(a.getAttribute('data-temp'));
        if (sortMode === 'humidity') return parseFloat(b.getAttribute('data-humidity')) - parseFloat(a.getAttribute('data-humidity'));
        return new Date(a.getAttribute('data-game-date')) - new Date(b.getAttribute('data-game-date'));
    }});

    cards.forEach(card => container.appendChild(card));
}}

document.addEventListener('DOMContentLoaded', () => {{
    const sortFilter = document.getElementById('sort-filter');
    const riskToggle = document.getElementById('risk-only');
    if (sortFilter) sortFilter.addEventListener('change', filterAndSortGames);
    if (riskToggle) riskToggle.addEventListener('change', filterAndSortGames);
}});

function showRadar(url, venueName) {{
    const modalElement = document.getElementById('radarModal');
    const modalTitle = document.querySelector('#radarModal .modal-title');
    const iframe = document.getElementById('radarFrame');
    if (modalTitle) modalTitle.innerText = `Radar: ${{venueName}}`;
    
    const myModal = bootstrap.Modal.getOrCreateInstance(modalElement);
    if (iframe) iframe.src = '';
    
    const loadMap = function () {{
        if (iframe) iframe.src = url; 
        modalElement.removeEventListener('shown.bs.modal', loadMap); 
    }};
    modalElement.addEventListener('shown.bs.modal', loadMap);
    myModal.show();
}}
</script>
</body>
</html>
"""

TEAM_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-0TNW6W5ZVN"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-0TNW6W5ZVN');
    </script>
    {schema_json}
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{team_name} Game Weather Today | {display_date} Forecast at {stadium_name}</title>
    <meta name="description" content="View the live weather forecast for today's {team_name} game at {stadium_name} for {display_date}. Track real-time rain delay risks, stadium wind direction, hourly temperatures, and betting odds.">
    <meta name="keywords" content="{team_name} weather, {stadium_name} wind direction, {stadium_name} rain delay, {team_name} game weather today, fantasy baseball weather">
    <link rel="canonical" href="https://weathermlb.com/team_pages/{team_slug}/" />
    <meta property="og:title" content="{team_name} Game Weather Today at {stadium_name} - Weather MLB">
    <meta property="og:description" content="Track stadium wind, hourly rain risks, and weather impact analytics for the {team_name} game at {stadium_name}.">
    <meta property="og:url" content="https://weathermlb.com/team_pages/{team_slug}/">
    <meta property="og:type" content="website">
    <meta property="og:image" content="https://weathermlb.com/social-share.png">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:site" content="@weathermlbdaily">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f8f9fa; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }} 
        .main-container {{ max-width: 520px; margin: 30px auto; padding: 0 15px; }}
        .game-card {{ border: 1px solid #dee2e6; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); background: white; overflow: hidden; }}
        .weather-row {{ font-size: 0.9rem; border-top: 1px solid #f1f3f5; padding-top: 8px; margin-top: 8px; padding-bottom: 4px; }}
        .stadium-name {{ color: #6c757d; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }}
        .wind-badge {{ font-size: 0.85rem; padding: 4px 10px; border-radius: 20px; font-weight: 600; display: inline-block; }}
        .wind-badge .arrow-emoji {{ font-size: 1.1rem; line-height: 0.5; vertical-align: middle; }}
        .bg-out {{ background-color: #d1e7dd; color: #0f5132; }} 
        .bg-in {{ background-color: #f8d7da; color: #842029; }}
        .bg-cross {{ background-color: #fff3cd; color: #664d03; }}
        .bg-secondary.text-white {{ background-color: #adb5bd !important; color: #fff !important; }}
        .analysis-box {{ background-color: rgba(255, 255, 255, 0.6); border-left: 4px solid #0d6efd; padding: 8px 12px; margin-top: 12px; font-size: 0.8rem; color: #495057; line-height: 1.4; border-radius: 0 4px 4px 0; }}
        .analysis-title {{ font-weight: 800; text-transform: uppercase; font-size: 0.7rem; color: #0d6efd; display: block; margin-bottom: 4px; letter-spacing: 0.5px; }}
        .hourly-scroll-container {{ display: flex; overflow-x: auto; gap: 8px; padding: 8px 4px; margin-top: 8px; border-top: 1px solid rgba(0,0,0,0.05); scrollbar-width: thin; }}
        .hour-card {{ display: flex; flex: 1; flex-direction: column; align-items: center; min-width: 60px; text-align: center; }}
        .hour-time {{ font-size: 0.75rem; font-weight: 600; color: #6c757d; margin-bottom: 2px; }}
        .hour-icon {{ font-size: 1.3rem; line-height: 1; margin-bottom: 2px; }}
        .hour-pop {{ font-size: 0.65rem; color: #5ac8fa; font-weight: 700; line-height: 1; height: 12px; margin-bottom: 2px; }}
        .hour-temp {{ font-size: 0.85rem; font-weight: 600; color: #212529; line-height: 1; }}
        @keyframes weather-flow {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
        .bg-weather-sunny {{ background: linear-gradient(-45deg, #e3f2fd, #e1f5fe, #f1f8e9); background-size: 300% 300%; animation: weather-flow 15s ease infinite; }}
        .bg-weather-cloudy {{ background: linear-gradient(-45deg, #f5f5f5, #e0e0e0, #eeeeee); background-size: 300% 300%; animation: weather-flow 20s ease infinite; }}
        .bg-weather-rain {{ background: linear-gradient(180deg, #e3f2fd, #cfd8dc, #eceff1); background-size: 200% 200%; animation: weather-flow 8s ease infinite; }}
        .bg-weather-storm {{ background: linear-gradient(-45deg, #e1bee7, #cfd8dc, #e0e0e0); background-size: 300% 300%; animation: weather-flow 10s ease infinite; }}
        .bg-weather-snow {{ background: linear-gradient(-45deg, #f3e5f5, #e3f2fd, #ffffff); background-size: 300% 300%; animation: weather-flow 15s ease infinite; }}
        .bg-weather-roof {{ background-color: #ffffff; }}
    </style>
</head>
<body>
    <nav class="navbar shadow-sm py-2 mb-0 sticky-top" style="background-color: #0f172a;">
        <div class="container d-flex justify-content-between align-items-center flex-wrap gap-2">
            <div class="d-flex align-items-center gap-2">
                <a href="/" class="navbar-brand text-white fw-bold m-0" style="font-style: italic; font-size: 1.6rem;">
                    Weather <span style="color: #5ac8fa;">MLB</span>
                </a>
                <div class="d-flex align-items-center gap-1 ms-1 ps-2" style="border-left: 1px solid rgba(255, 255, 255, 0.2);">
                    <a href="https://weathernfl.com" class="p-1 text-decoration-none" title="Weather NFL" aria-label="Weather NFL">
                        <img src="https://weathernfl.com/apple-touch-icon.png" alt="Weather NFL" style="width: 26px; height: 26px; border-radius: 6px; display: block;">
                    </a>
                    <a href="https://weathercfb.com" class="p-1 text-decoration-none" title="Weather CFB" aria-label="Weather CFB">
                        <img src="https://weathercfb.com/apple-touch-icon.png" alt="Weather CFB" style="width: 26px; height: 26px; border-radius: 6px; display: block;">
                    </a>
                    <a href="https://weatherfootball.com" class="p-1 text-decoration-none" title="Weather Football" aria-label="Weather Football">
                        <img src="https://weatherfootball.com/apple-touch-icon.png" alt="Weather Football" style="width: 26px; height: 26px; border-radius: 6px; display: block;">
                    </a>
                </div>
            </div>
            <div class="d-flex align-items-center gap-2">
                <select id="team-nav-select" class="form-select form-select-sm fw-bold" style="background-color: #1e293b; color: #adb5bd; border: 1px solid #334155; cursor: pointer; max-width: 180px;" onchange="if(this.value) window.location.href=this.value;">
                    <option value="">Switch Team</option>
                    {team_options}
                </select>
                <a href="/" class="btn btn-sm btn-outline-light px-3 fw-bold" style="font-size: 0.75rem;">Full Slate</a>
            </div>
        </div>
    </nav>
    <div class="main-container">
        <div class="text-center mt-3 mb-3">
            <h1 class="h5 fw-bold text-dark mb-1">{team_name} Weather Today</h1>
            <p class="text-muted mb-0" style="font-size: 0.85rem;">{display_date} at {stadium_name}</p>
        </div>
        <div id="team-weather-container">
            {team_card_content}
        </div>
    </div>
    <footer class="text-center py-4 text-muted mt-5" style="font-size: 0.75rem;">
        <div class="container">
            <p class="mb-1">© 2026 Weather MLB. All rights reserved.</p>
            <p class="mb-0">Data curated via official sources. Not affiliated with Major League Baseball.</p>
        </div>
    </footer>
    <script>
        document.addEventListener("DOMContentLoaded", () => {{
            const selectMenu = document.getElementById("team-nav-select");
            if (selectMenu) selectMenu.value = "/team_pages/{team_slug}/";
        }});

        function showRadar(url, venueName) {{
            const modalElement = document.getElementById('radarModal');
            const modalTitle = document.querySelector('#radarModal .modal-title');
            const iframe = document.getElementById('radarFrame');
            if (modalTitle) modalTitle.innerText = `Radar: ${{venueName}}`;
            
            const myModal = bootstrap.Modal.getOrCreateInstance(modalElement);
            if (iframe) iframe.src = '';
            
            const loadMap = function () {{
                if(iframe) iframe.src = url; 
                modalElement.removeEventListener('shown.bs.modal', loadMap); 
            }};
            modalElement.addEventListener('shown.bs.modal', loadMap);
            myModal.show();
        }}
    </script>
</body>
</html>
"""

# ==========================================
# 5. SITEMAP & INDEXNOW GENERATOR
# ==========================================
def generate_sitemap_and_ping(changed_urls):
    urls_with_paths = [
        ("https://weathermlb.com/", MAIN_INDEX_FILE)
    ]
    for team in sorted(MLB_TEAMS, key=lambda x: x["name"]):
        urls_with_paths.append((
            f"https://weathermlb.com/team_pages/{team['slug']}/",
            os.path.join(TEAM_PAGES_DIR, team['slug'], "index.html")
        ))

    sitemap_entries = []
    for i, (url, filepath) in enumerate(urls_with_paths):
        priority = "1.0" if i == 0 else "0.8"
        
        if os.path.exists(filepath):
            mtime = os.path.getmtime(filepath)
            dt = datetime.fromtimestamp(mtime, timezone.utc)
            lastmod = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        else:
            lastmod = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        sitemap_entries.append(
            f"  <url>\n"
            f"    <loc>{url}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>hourly</changefreq>\n"
            f"    <priority>{priority}</priority>\n"
            f"  </url>"
        )

    sitemap_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(sitemap_entries) +
        '\n</urlset>'
    )

    with open(SITEMAP_FILE, 'w', encoding='utf-8') as f:
        f.write(sitemap_xml)
    print("✅ Generated sitemap.xml using actual file modification dates!")

    if not changed_urls:
        print("ℹ️ No HTML changes detected. Skipping IndexNow ping.")
        return

    payload = {
        "host": "weathermlb.com",
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://weathermlb.com/{INDEXNOW_KEY}.txt",
        "urlList": changed_urls
    }

    try:
        res = requests.post("https://api.indexnow.org/indexnow", json=payload, timeout=10)
        if res.status_code in [200, 202]:
            print(f"🚀 Successfully pinged IndexNow with {len(changed_urls)} modified URLs!")
        else:
            print(f"⚠️ IndexNow ping failed: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"⚠️ IndexNow ping exception: {e}")

# ==========================================
# 6. MAIN CONTROLLER PIPELINE
# ==========================================
def main():
    est_tz = zoneinfo.ZoneInfo("America/New_York")
    est_now = datetime.now(est_tz)
    
    if 3 <= est_now.hour < 8:
        print(f"💤 SLEEP MODE ACTIVE: It is currently {est_now.strftime('%I:%M %p')} EST. Halting script to preserve yesterday's site data.")
        sys.exit(0)

    date_str = est_now.strftime('%Y-%m-%d')
    display_date = est_now.strftime('%B %d, %Y').replace(' 0', ' ')

    print(f"🎬 Starting All-In-One Static Site Pipeline for {date_str} (EST)...")

    # Step 1: Run weather updates first
    games_data = run_weather_update(est_now)
    
    # Track which URLs actually received new HTML
    changed_urls = []

    # Step 2: Render Dropdown Options
    sorted_teams = sorted(MLB_TEAMS, key=lambda x: x["name"])
    team_options = "\n".join([f'<option value="/team_pages/{t["slug"]}/">{t["name"]}</option>' for t in sorted_teams])

    # Step 3: Render Main Page Cards
    cards_html_list = []
    if games_data:
        for item in games_data:
            cards_html_list.append(render_main_game_card(item))
        main_cards_content = f'''
        <div class="col-12 text-center mb-3 mt-1 position-relative">
            <button class="btn btn-sm shadow-sm fw-bold px-4 py-1" style="background-color: #fff; border: 1px solid #dee2e6; color: #495057; border-radius: 20px;" onclick="toggleAllWeatherCards()">
                <span id="expand-toggle-icon">▼</span> 
                <span id="expand-toggle-text">Expand All Cards</span>
            </button>
        </div>
        {"".join(cards_html_list)}
        '''
    else:
        main_cards_content = f'''
        <div class="col-12 text-center mt-5">
            <div class="alert alert-light border shadow-sm py-4">
                <h4 class="text-muted">No games scheduled for {display_date}</h4>
            </div>
        </div>
        '''

    # Step 4: Write Main index.html
    schema_list = []
    if games_data:
        for data in games_data:
            game = data['gameRaw']
            home_team = game['teams']['home']['team']['name']
            away_team = game['teams']['away']['team']['name']
            game_date_iso = game['gameDate']
            actual_stadium = game.get('venue', {}).get('name', 'Unknown Stadium')
            
            event_schema = {
                "@context": "https://schema.org",
                "@type": "SportsEvent",
                "name": f"{away_team} at {home_team}",
                "description": get_weather_blurb(data),
                "startDate": game_date_iso,
                "location": {
                    "@type": "Place",
                    "name": actual_stadium
                },
                "homeTeam": {"@type": "SportsTeam", "name": home_team},
                "awayTeam": {"@type": "SportsTeam", "name": away_team}
            }
            schema_list.append(event_schema)
            
    if not schema_list:
        schema_list = {
            "@context": "https://schema.org",
            "@type": "WebSite",
            "name": "Weather MLB",
            "alternateName": ["WeatherMLB"],
            "url": "https://weathermlb.com/"
        }
        
    main_schema_json = f'<script type="application/ld+json">\n{json.dumps(schema_list, indent=4)}\n    </script>'

    main_html = MAIN_SITE_TEMPLATE.format(
        schema_json=main_schema_json,
        display_date=display_date,
        team_options=team_options,
        main_cards_content=main_cards_content
    )
    if write_if_changed(MAIN_INDEX_FILE, main_html):
        changed_urls.append("https://weathermlb.com/")
        print("✅ Main index.html updated.")
    else:
        print("⏭️ Main index.html unchanged. Skipped write.")

    # Step 5: Render and Write 30 Team Pages
    for team in MLB_TEAMS:
        t_dir = os.path.join(TEAM_PAGES_DIR, team["slug"])
        os.makedirs(t_dir, exist_ok=True)

        target_game = None
        if games_data:
            for g in games_data:
                home_id = g['gameRaw']['teams']['home']['team']['id']
                away_id = g['gameRaw']['teams']['away']['team']['id']
                if home_id == team["id"] or away_id == team["id"]:
                    target_game = g
                    break

        if target_game:
            card_markup = render_standalone_team_card(target_game)
            actual_stadium = target_game['gameRaw'].get('venue', {}).get('name', team['stadium'])
            
            game_date_iso = target_game['gameRaw']['gameDate']
            home_name = target_game['gameRaw']['teams']['home']['team']['name']
            away_name = target_game['gameRaw']['teams']['away']['team']['name']
            
            weather_description = get_weather_blurb(target_game)
            
            schema_dict = {
                "@context": "https://schema.org",
                "@type": "SportsEvent",
                "name": f"{away_name} at {home_name}",
                "startDate": game_date_iso,
                "location": {
                    "@type": "Place",
                    "name": actual_stadium
                },
                "homeTeam": {"@type": "SportsTeam", "name": home_name},
                "awayTeam": {"@type": "SportsTeam", "name": away_name},
                "description": weather_description
            }
        else:
            actual_stadium = team['stadium']
            card_markup = '''
            <div class="card p-5 text-center text-muted" style="border: 2px dashed #dee2e6; border-radius: 12px; background: #fff;">
                <h3 class="h5 fw-bold text-dark mb-2">No Game Scheduled Today</h3>
                <p class="small mb-0">This team has an off-day, travel day, or their matchup was postponed early.</p>
            </div>
            '''
            schema_dict = {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "name": f"{team['name']} Weather Forecasts",
                "description": f"Daily MLB weather forecasts, wind directions, and odds for the {team['name']}."
            }

        schema_json = f'<script type="application/ld+json">\n{json.dumps(schema_dict, indent=4)}\n    </script>'

        team_html = TEAM_PAGE_TEMPLATE.format(
            schema_json=schema_json,
            team_name=team["name"],
            team_slug=team["slug"],
            stadium_name=actual_stadium,
            display_date=display_date,
            team_options=team_options,
            team_card_content=card_markup
        )

        output_filepath = os.path.join(t_dir, "index.html")
        if write_if_changed(output_filepath, team_html):
            changed_urls.append(f"https://weathermlb.com/team_pages/{team['slug']}/")

    print(f"🚀 HTML parsing complete. {len(changed_urls)} pages required updates.")

    # Step 6: Generate Sitemap and Ping IndexNow
    generate_sitemap_and_ping(changed_urls)
    print("🎉 All-in-one site generation pipeline completed successfully!")

if __name__ == "__main__":
    main()
