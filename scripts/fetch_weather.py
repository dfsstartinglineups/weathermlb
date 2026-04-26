import requests
import json
import os
import time
import zoneinfo
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
DAILY_FILES_DIR = os.path.join(DATA_DIR, 'daily_files')
STADIUMS_FILE = os.path.join(DATA_DIR, 'stadiums.json')
ODDS_FILE = os.path.join(DATA_DIR, 'odds.json')

os.makedirs(DAILY_FILES_DIR, exist_ok=True)

# --- API TRACKING ---
API_CALL_TRACKER = {
    "schedule": 0, "open_meteo": 0
}

def load_json(path, default_val):
    if os.path.exists(path):
        try:
            with open(path, 'r') as f: return json.load(f)
        except Exception: pass
    return default_val

def save_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)

def get_active_sport_ids():
    current_date = datetime.now(timezone.utc).date()
    wbc_start = datetime(2026, 3, 4).date()
    wbc_end = datetime(2026, 3, 17).date()
    if wbc_start <= current_date <= wbc_end:
        return "1,51"
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
    
    utc_time = datetime.fromisoformat(game_date_iso.replace('Z', '+00:00'))
    date_str = utc_time.strftime('%Y-%m-%d')
    
    next_day_obj = utc_time + timedelta(days=1)
    next_date_str = next_day_obj.strftime('%Y-%m-%d')
    
    today_utc = datetime.now(timezone.utc).date()
    is_historical = utc_time.date() < today_utc
    days_diff = (utc_time.date() - today_utc).days

    if not is_historical and days_diff > 16:
        return {"status": "too_early", "temp": "--"}

    if is_historical or date_str == "2024-09-25":
        url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={date_str}&end_date={next_date_str}&hourly=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=GMT"
    elif days_diff <= 3:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=GMT&start_date={date_str}&end_date={next_date_str}"
    else:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_direction_10m&models=gfs_seamless&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=GMT&start_date={date_str}&end_date={next_date_str}"

    max_retries = 3
    for attempt in range(max_retries):
        try:
            API_CALL_TRACKER["open_meteo"] += 1
            res = session.get(url, timeout=15) 
            
            if res.status_code == 400: return {"status": "too_early", "temp": "--"}
            if res.status_code != 200: return {"temp": "--", "hourly": []}
            
            data = res.json()
            time_array = data['hourly']['time']
            target_time_str = utc_time.strftime('%Y-%m-%dT%H:00')
            
            try:
                start_idx = time_array.index(target_time_str)
            except ValueError:
                start_idx = 0

            def normalize_precip(idx):
                prob = data['hourly'].get('precipitation_probability', [0]*len(time_array))[idx] or 0
                amount = data['hourly'].get('precipitation', [0]*len(time_array))[idx] or 0
                code = data['hourly']['weather_code'][idx]
                
                if amount == 0 and code <= 3: return 0
                if amount > 0:
                    if amount >= 0.10: return max(80, prob)
                    if amount >= 0.05: return max(60, prob)
                    if amount >= 0.01: return max(30, prob)
                    return 15
                return prob

            hourly_slice = []
            max_chance_in_window = 0
            is_game_thunderstorm = False
            is_game_snow = False

            actual_start = max(0, start_idx - 1)
            actual_end = min(len(time_array), start_idx + 4)

            for i in range(actual_start, actual_end):
                chance = normalize_precip(i)
                code = data['hourly']['weather_code'][i]
                
                is_hour_thunderstorm = 95 <= code <= 99
                is_hour_snow = code in [71, 73, 75, 77, 85, 86]
                
                if is_hour_thunderstorm: is_game_thunderstorm = True
                if is_hour_snow: is_game_snow = True
                
                if chance > max_chance_in_window:
                    max_chance_in_window = chance
                    
                temp_val = data['hourly']['temperature_2m'][i]
                
                hourly_slice.append({
                    "timestamp": time_array[i] + "Z",
                    "temp": round(temp_val) if temp_val is not None else "--",
                    "precipChance": chance,
                    "isThunderstorm": is_hour_thunderstorm,
                    "isSnow": is_hour_snow
                })

            return {
                "status": "ok",
                "lastUpdated": datetime.now(timezone.utc).timestamp(),
                "temp": round(data['hourly']['temperature_2m'][start_idx]),
                "humidity": round(data['hourly']['relative_humidity_2m'][start_idx]),
                "maxPrecipChance": max_chance_in_window,
                "isThunderstorm": is_game_thunderstorm,
                "isSnow": is_game_snow,
                "windSpeed": round(data['hourly']['wind_speed_10m'][start_idx]),
                "windDir": data['hourly']['wind_direction_10m'][start_idx],
                "hourly": hourly_slice
            }
            
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                sleep_time = (attempt + 1) * 3
                print(f"      ⏳ Open-Meteo Timeout. Retrying in {sleep_time}s ({attempt+1}/{max_retries})...")
                time.sleep(sleep_time) 
            else:
                print(f"      ❌ Weather fetch completely failed after {max_retries} attempts.")
                return {"temp": "--", "hourly": []}
        except Exception as e:
            print(f"⚠️ Weather fetch failed with error: {e}")
            return {"temp": "--", "hourly": []}

def main():
    global API_CALL_TRACKER
    est_tz = zoneinfo.ZoneInfo("America/New_York")
    current_est_time = datetime.now(est_tz)
    
    if 3 <= current_est_time.hour < 8:
        print(f"💤 SLEEP MODE ACTIVE: It is currently {current_est_time.strftime('%I:%M %p')} EST.")
        return
        
    start_date = (current_est_time - timedelta(days=1)).strftime('%Y-%m-%d')
    end_date = (current_est_time + timedelta(days=7)).strftime('%Y-%m-%d') 
    
    print(f"🚀 Building WeatherMLB Master JSONs (7-Day Horizon)")
    
    session = requests.Session()
    stadiums = load_json(STADIUMS_FILE, [])
    odds_data = load_json(ODDS_FILE, {}).get('odds', [])
    
    API_CALL_TRACKER["schedule"] += 1
    sport_ids = get_active_sport_ids()
    schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId={sport_ids}&startDate={start_date}&endDate={end_date}&hydrate=linescore,venue,probablePitcher,lineups,person"
    
    try: schedule_data = session.get(schedule_url, timeout=15).json()
    except Exception as e:
        print(f"❌ Failed to fetch schedule: {e}")
        return

    master_dates = {}

    for date_item in schedule_data.get('dates', []):
        date_str = date_item['date']
        master_dates[date_str] = []
        
        daily_file_path = os.path.join(DAILY_FILES_DIR, f'games_{date_str}.json')
        daily_memory = {}
        if os.path.exists(daily_file_path):
            existing_games = load_json(daily_file_path, [])
            for g in existing_games:
                daily_memory[str(g['gameRaw']['gamePk'])] = g
                
        target_date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        days_away = (target_date_obj - current_est_time.date()).days
        
        for game in date_item.get('games', []):
            game_pk = str(game['gamePk'])
            existing_game_state = daily_memory.get(game_pk, {})
            
            game_odds = None
            away_team_name = game.get('teams', {}).get('away', {}).get('team', {}).get('name', '')
            home_team_name = game.get('teams', {}).get('home', {}).get('team', {}).get('name', '')
            game_time_ms = datetime.strptime(game['gameDate'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp() * 1000
            
            def parse_odds_time(date_str):
                if date_str.endswith('Z'): date_str = date_str[:-1]
                if len(date_str.split(':')) == 2: date_str += ":00"
                return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000

            potential_odds = [o for o in odds_data if o['home_team'] == home_team_name and o['away_team'] == away_team_name]
            if potential_odds:
                game_odds = sorted(potential_odds, key=lambda o: abs(parse_odds_time(o['commence_time']) - game_time_ms))[0]

            venue_id = game.get('venue', {}).get('id')
            stadium = next((s for s in stadiums if s.get('id') == venue_id), None)
            
            weather_data = existing_game_state.get('weather')
            needs_weather_fetch = True
            
            if stadium and weather_data and weather_data.get('temp') != '--':
                last_updated = weather_data.get('lastUpdated', 0)
                time_since_update = current_est_time.timestamp() - last_updated
                
                if days_away == 0 and time_since_update < 900: 
                    needs_weather_fetch = False
                elif 0 < days_away <= 2 and time_since_update < 10800: 
                    needs_weather_fetch = False
                elif days_away > 2 and time_since_update < 43200: 
                    needs_weather_fetch = False
                    
            if stadium and needs_weather_fetch:
                print(f"   ☁️ Fetching Weather for {away_team_name} @ {home_team_name} ({date_str})")
                
                new_weather = fetch_game_weather(session, stadium['lat'], stadium['lon'], game['gameDate'])
                
                if new_weather.get('temp') == '--' and weather_data and weather_data.get('temp') != '--':
                    print("      🛡️ Fetch failed, but keeping existing cached weather to prevent data loss.")
                else:
                    weather_data = new_weather
                
                time.sleep(1.0) 

            wind_data = None
            is_roof_closed = False
            is_roof_pending = False

            # --- NEW: MLB OFFICIAL ROOF STATUS CHECK ---
            if stadium and stadium.get('roof'):
                try:
                    live_feed_url = f"https://statsapi.mlb.com/api/v1.1/game/{game_pk}/feed/live"
                    live_res = session.get(live_feed_url, timeout=5)
                    if live_res.status_code == 200:
                        live_json = live_res.json()
                        game_data = live_json.get('gameData', {})
                        mlb_weather = game_data.get('weather', {})
                        
                        # Check the official condition string from the stadium
                        if mlb_weather.get('condition') == "Roof Closed" or mlb_weather.get('condition') == "Dome":
                            is_roof_closed = True
                            print(f"      🏟️ OVERRIDE: MLB official feed confirms roof is CLOSED.")
                except Exception as e:
                    print(f"      ⚠️ Failed to check MLB live feed for roof status: {e}")
            
            if stadium and weather_data and weather_data.get('status') != "too_early" and weather_data.get('temp') != '--':
                wind_data = calculate_wind(weather_data.get('windDir'), stadium.get('bearing'))
                
                if stadium.get('dome'):
                    is_roof_closed = True
                elif stadium.get('roof') and not is_roof_closed: # <-- Added the check here
                    temp = weather_data.get('temp', 70)
                    precip = weather_data.get('maxPrecipChance', 0)
                    
                    if precip >= 30 or temp <= 50 or temp >= 95:
                        is_roof_closed = True
                    elif precip >= 15 or temp <= 55 or temp >= 90:
                        is_roof_pending = True
                        
                if is_roof_closed:
                    wind_data = {"text": "Roof Closed", "cssClass": "bg-secondary text-white", "arrow": ""}
                    weather_data['windSpeed'] = 0

            lineup_handedness = existing_game_state.get('lineupHandedness', {})
            lineup_positions = existing_game_state.get('lineupPositions', {})
            
            master_dates[date_str].append({
                "gameRaw": game,
                "stadium": stadium,
                "odds": game_odds,
                "weather": weather_data,
                "wind": wind_data,
                "roof": is_roof_closed,
                "roofPending": is_roof_pending,
                "lineupHandedness": lineup_handedness,
                "lineupPositions": lineup_positions
            })

    for date_str, games_list in master_dates.items():
        daily_file = os.path.join(DAILY_FILES_DIR, f'games_{date_str}.json')
        save_json(daily_file, games_list)
        print(f"✅ Created/Updated {daily_file} with {len(games_list)} games.")

    total_calls = sum(API_CALL_TRACKER.values())
    print("\n" + "="*40)
    print(f"📊 API CALL SUMMARY: {total_calls} Total Requests")
    print("="*40)
    for k, v in API_CALL_TRACKER.items(): print(f"  - {k.replace('_', ' ').title()}: {v}")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
