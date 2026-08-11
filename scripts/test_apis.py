import os
import sys
import json
import time
import requests
import zoneinfo
from datetime import datetime, timedelta, timezone

# ==========================================
# 1. PATHS & KEYS CONFIGURATION
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(SCRIPT_DIR) if os.path.basename(SCRIPT_DIR) == 'scripts' else SCRIPT_DIR

STADIUMS_FILE = os.path.join(ROOT_DIR, 'data', 'stadiums.json')
TEST_INDEX_FILE = os.path.join(ROOT_DIR, 'test_index.html')

TOMORROW_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_API_KEY = os.environ.get("THE_WEATHER_API_KEY", "")

EST_TZ = zoneinfo.ZoneInfo("America/New_York")

def load_json(path, default_val):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f: return json.load(f)
        except Exception: pass
    return default_val

def get_short_team_name(full_name):
    if not full_name: return ""
    if "Red Sox" in full_name: return "Red Sox"
    if "White Sox" in full_name: return "White Sox"
    if "Blue Jays" in full_name: return "Blue Jays"
    if "Diamondbacks" in full_name: return "Dbacks"
    parts = full_name.split()
    return parts[-1] if parts else ""

# ==========================================
# 2. ADAPTER 1: TOMORROW.IO
# ==========================================
def fetch_tomorrow_io(session, lat, lon, game_date_iso):
    if not TOMORROW_API_KEY:
        return {"status": "no_key", "temp": "--", "maxPrecipChance": 0, "windSpeed": 0, "humidity": 0, "hourly": []}

    utc_time = datetime.fromisoformat(game_date_iso.replace('Z', '+00:00'))
    start_time = (utc_time - timedelta(hours=1)).strftime('%Y-%m-%dT%H:00:00Z')
    end_time = (utc_time + timedelta(hours=4)).strftime('%Y-%m-%dT%H:00:00Z')

    url = (
        f"https://api.tomorrow.io/v4/timelines"
        f"?location={lat},{lon}"
        f"&fields=temperature,humidity,precipitationProbability,weatherCode,windSpeed"
        f"&timesteps=1h&units=imperial"
        f"&startTime={start_time}&endTime={end_time}"
        f"&apikey={TOMORROW_API_KEY}"
    )

    try:
        res = session.get(url, timeout=12)
        if res.status_code != 200:
            return {"status": "error", "temp": "--", "maxPrecipChance": 0, "windSpeed": 0, "humidity": 0, "hourly": []}

        data = res.json()
        timelines = data.get('data', {}).get('timelines', [])
        if not timelines: return {"status": "empty", "temp": "--", "maxPrecipChance": 0, "windSpeed": 0, "humidity": 0, "hourly": []}

        intervals = timelines[0].get('intervals', [])
        hourly_slice, max_chance = [], 0
        is_thunder, is_snow = False, False

        for hour in intervals:
            vals = hour.get('values', {})
            chance_raw = vals.get('precipitationProbability')
            chance = int(float(chance_raw)) if chance_raw is not None else 0
            code = vals.get('weatherCode') or 1000

            if code == 8000: is_thunder = True
            if 5000 <= code < 8000: is_snow = True
            if chance > max_chance: max_chance = chance

            temp_raw = vals.get('temperature')
            hourly_slice.append({
                "timestamp": hour.get('startTime'),
                "temp": round(float(temp_raw)) if temp_raw is not None else 0,
                "precipChance": chance,
                "isThunderstorm": code == 8000,
                "isSnow": 5000 <= code < 8000
            })

        start_vals = intervals[1].get('values', {}) if len(intervals) > 1 else (intervals[0].get('values', {}) if intervals else {})
        return {
            "status": "ok",
            "temp": round(float(start_vals.get('temperature', 70))),
            "humidity": round(float(start_vals.get('humidity', 50))),
            "maxPrecipChance": max_chance,
            "windSpeed": round(float(start_vals.get('windSpeed', 0))),
            "isThunderstorm": is_thunder,
            "isSnow": is_snow,
            "hourly": hourly_slice
        }
    except Exception as e:
        print(f"⚠️ Tomorrow.io Test Fetch Error: {e}")
        return {"status": "error", "temp": "--", "maxPrecipChance": 0, "windSpeed": 0, "humidity": 0, "hourly": []}

# ==========================================
# 3. ADAPTER 2: WEATHERAPI.COM
# ==========================================
def fetch_weather_api(session, lat, lon, game_date_iso):
    if not WEATHER_API_KEY:
        return {"status": "no_key", "temp": "--", "maxPrecipChance": 0, "windSpeed": 0, "humidity": 0, "hourly": []}

    utc_time = datetime.fromisoformat(game_date_iso.replace('Z', '+00:00'))
    url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHER_API_KEY}&q={lat},{lon}&days=2&aqi=no&alerts=no"

    try:
        res = session.get(url, timeout=12)
        if res.status_code != 200:
            return {"status": "error", "temp": "--", "maxPrecipChance": 0, "windSpeed": 0, "humidity": 0, "hourly": []}

        data = res.json()
        all_hours = []
        for day in data.get('forecast', {}).get('forecastday', []):
            all_hours.extend(day.get('hour', []))

        target_epoch = int(utc_time.replace(minute=0, second=0, microsecond=0).timestamp())
        start_idx = next((i for i, h in enumerate(all_hours) if h['time_epoch'] == target_epoch), 0)

        actual_start = max(0, start_idx - 1)
        actual_end = min(len(all_hours), start_idx + 4)

        hourly_slice, max_chance = [], 0
        is_thunder, is_snow = False, False

        for i in range(actual_start, actual_end):
            hour = all_hours[i]
            chance = hour.get('chance_of_rain', 0)
            cond = hour.get('condition', {}).get('text', '').lower()

            if "thunder" in cond: is_thunder = True
            if any(s in cond for s in ["snow", "ice", "sleet", "blizzard"]): is_snow = True
            if chance > max_chance: max_chance = chance

            hour_iso = datetime.fromtimestamp(hour['time_epoch'], timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            hourly_slice.append({
                "timestamp": hour_iso,
                "temp": round(hour.get('temp_f', 72)),
                "precipChance": chance,
                "isThunderstorm": "thunder" in cond,
                "isSnow": any(s in cond for s in ["snow", "ice", "sleet", "blizzard"])
            })

        kickoff_h = all_hours[start_idx] if len(all_hours) > start_idx else (all_hours[0] if all_hours else {})
        return {
            "status": "ok",
            "temp": round(kickoff_h.get('temp_f', 70)),
            "humidity": round(kickoff_h.get('humidity', 50)),
            "maxPrecipChance": max_chance,
            "windSpeed": round(kickoff_h.get('wind_mph', 0)),
            "isThunderstorm": is_thunder,
            "isSnow": is_snow,
            "hourly": hourly_slice
        }
    except Exception as e:
        print(f"⚠️ WeatherAPI Test Fetch Error: {e}")
        return {"status": "error", "temp": "--", "maxPrecipChance": 0, "windSpeed": 0, "humidity": 0, "hourly": []}

# ==========================================
# 4. ADAPTER 3: OPEN-METEO
# ==========================================
def fetch_open_meteo(session, lat, lon, game_date_iso):
    utc_time = datetime.fromisoformat(game_date_iso.replace('Z', '+00:00'))
    game_date_str = utc_time.strftime('%Y-%m-%d')
    next_day_str = (utc_time + timedelta(days=1)).strftime('%Y-%m-%d')

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
        "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,weather_code",
        "temperature_unit": "fahrenheit", "wind_speed_unit": "mph",
        "timezone": "GMT", "start_date": game_date_str, "end_date": next_day_str
    }

    try:
        res = session.get(url, params=params, timeout=12)
        if res.status_code != 200:
            return {"status": "error", "temp": "--", "maxPrecipChance": 0, "windSpeed": 0, "humidity": 0, "hourly": []}

        data = res.json()
        current = data.get('current', {})
        time_array = data.get('hourly', {}).get('time', [])
        target_time_str = utc_time.strftime('%Y-%m-%dT%H:00')

        try: start_idx = time_array.index(target_time_str)
        except ValueError: start_idx = 1

        actual_start = max(0, start_idx - 1)
        actual_end = min(len(time_array), start_idx + 4)

        hourly_slice, max_chance = [], 0
        is_thunder, is_snow = False, False

        for i in range(actual_start, actual_end):
            code = data['hourly'].get("weather_code", [0])[i]
            chance = data['hourly'].get("precipitation_probability", [0])[i] or 0
            temp_v = data['hourly'].get("temperature_2m", [72])[i] or 72

            if code in [95, 96, 99]: is_thunder = True
            if code in [71, 73, 75, 77, 85, 86]: is_snow = True
            if chance > max_chance: max_chance = chance

            hourly_slice.append({
                "timestamp": time_array[i] + "Z",
                "temp": int(temp_v),
                "precipChance": chance,
                "isThunderstorm": code in [95, 96, 99],
                "isSnow": code in [71, 73, 75, 77, 85, 86]
            })

        target_temp = data['hourly'].get("temperature_2m", [72])[start_idx] if len(data['hourly'].get("temperature_2m", [])) > start_idx else current.get('temperature_2m', 72)
        target_hum = data['hourly'].get("relative_humidity_2m", [50])[start_idx] if len(data['hourly'].get("relative_humidity_2m", [])) > start_idx else current.get('relative_humidity_2m', 50)

        return {
            "status": "ok",
            "temp": int(target_temp if target_temp is not None else 72),
            "humidity": int(target_hum if target_hum is not None else 50),
            "maxPrecipChance": max_chance,
            "windSpeed": int(current.get('wind_speed_10m', 0)),
            "isThunderstorm": is_thunder,
            "isSnow": is_snow,
            "hourly": hourly_slice
        }
    except Exception as e:
        print(f"⚠️ Open-Meteo Test Fetch Error: {e}")
        return {"status": "error", "temp": "--", "maxPrecipChance": 0, "windSpeed": 0, "humidity": 0, "hourly": []}

# ==========================================
# 5. SINGLE CARD HTML GENERATOR
# ==========================================
def render_test_card(game, weather, api_label, badge_color_class):
    stadium = game.get('stadium') or {}
    is_dome = stadium.get('dome', False) or stadium.get('roof') in ["Dome", "Retractable"]
    w = weather or {"status": "error", "temp": "--", "maxPrecipChance": 0, "windSpeed": 0, "humidity": 0}

    border_class = ""
    bg_class = "bg-weather-sunny"

    max_pop = w.get('maxPrecipChance', 0)
    wind_val = w.get('windSpeed', 0)
    temp_val = w.get('temp', '--')
    hum_val = w.get('humidity', 0)

    if w.get('status') != 'ok':
        bg_class = "bg-light"
    elif is_dome:
        bg_class = "bg-weather-roof"
    elif w.get('isThunderstorm') or w.get('isSnow') or max_pop >= 60 or wind_val >= 20:
        border_class = "border-danger border-3"
        bg_class = "bg-weather-storm"
    elif max_pop >= 30 or wind_val >= 15:
        border_class = "border-warning border-3"
        bg_class = "bg-weather-rain"
    elif wind_val >= 12 or max_pop >= 15:
        bg_class = "bg-weather-cloudy"

    away_team = game['teams']['away']['team']['name']
    home_team = game['teams']['home']['team']['name']
    away_short = get_short_team_name(away_team)
    home_short = get_short_team_name(home_team)

    away_logo = f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{game['teams']['away']['team']['id']}.svg"
    home_logo = f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{game['teams']['home']['team']['id']}.svg"

    utc_date = datetime.fromisoformat(game['gameDate'].replace('Z', '+00:00'))
    et_date = utc_date.astimezone(EST_TZ)
    game_time = et_date.strftime("%I:%M %p").lstrip("0")

    display_rain = "0%" if is_dome else f"{max_pop}%"
    stadium_name = stadium.get('name', 'Stadium')
    stadium_lat = stadium.get('lat', 39.0)
    stadium_lon = stadium.get('lon', -95.0)

    radar_url = f"https://embed.windy.com/embed2.html?lat={stadium_lat}&lon={stadium_lon}&detailLat={stadium_lat}&detailLon={stadium_lon}&width=650&height=450&zoom=11&level=surface&overlay=rain&product=ecmwf&menu=&message=&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=mph&metricTemp=%C2%B0F&radarRange=-1"

    hourly_html = ''
    if not is_dome and w.get('hourly'):
        hours_markup = []
        for h in w['hourly'][:5]:
            ts = h.get('timestamp')
            h_dt = datetime.fromisoformat(ts.replace('Z', '+00:00')).astimezone(EST_TZ) if ts else datetime.now(EST_TZ)
            hr12 = h_dt.strftime("%I%p").lstrip("0")
            is_night = h_dt.hour >= 20 or h_dt.hour < 6

            pop = h.get('precipChance', 0)
            icon = '☀️'
            if pop >= 30:
                icon = '⛈️' if h.get('isThunderstorm') else ('🌨️' if h.get('isSnow') else '🌧️')
            elif pop > 0:
                icon = '⛅'
            elif is_night:
                icon = '🌙'

            pop_str = f"{pop}%" if pop >= 20 else "&nbsp;"
            hours_markup.append(f'''
                <div class="hour-card">
                    <div class="hour-time">{hr12}</div>
                    <div class="hour-icon">{icon}</div>
                    <div class="hour-pop">{pop_str}</div>
                    <div class="hour-temp">{h.get("temp", "--")}°</div>
                </div>
            ''')
        hourly_html = f'<div class="hourly-scroll-container">{"".join(hours_markup)}</div>'

    card_id = f"{game['gamePk']}-{api_label.lower().replace('.', '')}"

    return f"""
    <div class="col-md-4 mb-3">
        <div class="card game-card shadow-sm {border_class} {bg_class}" id="card-{card_id}">
            <!-- RIBBON VIEW -->
            <div class="ribbon-view p-2 position-relative" onclick="toggleSingleCard(event, '{card_id}')" style="cursor: pointer; display: block;">
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="badge {badge_color_class} px-2 py-1" style="font-size: 0.65rem;">📡 {api_label}</span>
                    <span class="badge bg-light text-dark border px-2 py-1" style="font-size: 0.65rem;">{game_time}</span>
                </div>
                <div class="fw-bold text-dark text-center my-1" style="font-size: 0.75rem;">
                    🌧️{display_rain} &nbsp;🌡️{temp_val}° &nbsp;💨{wind_val}mph
                </div>
                <div class="d-flex align-items-center justify-content-between mt-1">
                    <div class="d-flex align-items-center gap-1">
                        <img src="{away_logo}" style="width: 16px; height: 16px; object-fit: contain;">
                        <span class="fw-bold text-dark" style="font-size: 0.75rem;">{away_short}</span>
                        <span class="text-muted small">@</span>
                        <img src="{home_logo}" style="width: 16px; height: 16px; object-fit: contain;">
                        <span class="fw-bold text-dark" style="font-size: 0.75rem;">{home_short}</span>
                    </div>
                    <span class="text-truncate text-muted small" style="max-width: 110px; font-size: 0.65rem;">{stadium_name}</span>
                </div>
            </div>

            <!-- FULL CARD VIEW -->
            <div class="full-card-view p-2" onclick="toggleSingleCard(event, '{card_id}')" style="cursor: pointer; display: none;">
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="badge {badge_color_class}">📡 {api_label}</span>
                    <span class="stadium-name text-truncate text-end flex-grow-1 ms-2" style="font-size: 0.8rem; font-weight: 600;">{stadium_name}</span>
                </div>
                <div class="d-flex justify-content-between align-items-center px-1 mb-2">
                    <div class="d-flex align-items-center text-truncate" style="width: 45%;">
                        <img src="{away_logo}" class="me-2" style="width: 20px; height: 20px; object-fit: contain;">
                        <span class="fw-bold text-dark" style="font-size: 0.9rem;">{away_short}</span>
                    </div>
                    <span class="text-muted fw-bold">@</span>
                    <div class="d-flex align-items-center justify-content-end text-truncate" style="width: 45%;">
                        <img src="{home_logo}" class="me-2" style="width: 20px; height: 20px; object-fit: contain;">
                        <span class="fw-bold text-dark" style="font-size: 0.9rem;">{home_short}</span>
                    </div>
                </div>
                <div class="weather-row row text-center align-items-center mt-2 mx-0">
                    <div class="col-3 border-end px-1"><div class="fw-bold">{temp_val}°F</div><div class="small text-muted" style="font-size: 0.65rem;">Temp</div></div>
                    <div class="col-3 border-end px-1"><div class="fw-bold text-dark">{hum_val}%</div><div class="small text-muted" style="font-size: 0.65rem;">Hum</div></div>
                    <div class="col-3 border-end px-1"><div class="fw-bold text-primary">{display_rain}</div><div class="small text-muted" style="font-size: 0.65rem;">Rain</div></div>
                    <div class="col-3 px-1"><div class="fw-bold">{wind_val} <span style="font-size:0.65em">mph</span></div><div class="small text-muted" style="font-size: 0.65rem;">Wind</div></div>
                </div>
                {hourly_html}
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-primary w-100 py-1 fw-bold" style="font-size: 0.75rem;" onclick="event.stopPropagation(); showRadar('{radar_url}', '{stadium_name}')">🗺️ Live Radar Map</button>
                </div>
            </div>
        </div>
    </div>
    """

# ==========================================
# 6. MASTER TEMPLATE FOR TEST PAGE
# ==========================================
TEST_SITE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧪 Weather API Triplicate Comparison Test Slate | Weather MLB</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f8f9fa; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        .main-container {{ max-width: 1400px; margin: 30px auto; padding: 0 15px; }}
        .game-card {{ border: 1px solid #dee2e6; border-radius: 12px; background: white; overflow: hidden; }}
        .weather-row {{ font-size: 0.85rem; border-top: 1px solid #f1f3f5; padding-top: 6px; margin-top: 6px; }}
        .stadium-name {{ color: #6c757d; font-size: 0.8rem; font-weight: 700; text-transform: uppercase; }}
        .hourly-scroll-container {{ display: flex; overflow-x: auto; gap: 6px; padding: 6px 2px; margin-top: 6px; border-top: 1px solid rgba(0,0,0,0.05); scrollbar-width: thin; }}
        .hour-card {{ display: flex; flex: 1; flex-direction: column; align-items: center; min-width: 50px; text-align: center; }}
        .hour-time {{ font-size: 0.7rem; font-weight: 600; color: #6c757d; }}
        .hour-icon {{ font-size: 1.1rem; line-height: 1; }}
        .hour-pop {{ font-size: 0.6rem; color: #5ac8fa; font-weight: 700; height: 10px; }}
        .hour-temp {{ font-size: 0.75rem; font-weight: 600; color: #212529; }}

        @keyframes weather-flow {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}
        .bg-weather-sunny {{ background: linear-gradient(-45deg, #e3f2fd, #e1f5fe, #f1f8e9); background-size: 300% 300%; animation: weather-flow 15s ease infinite; }}
        .bg-weather-cloudy {{ background: linear-gradient(-45deg, #f5f5f5, #e0e0e0, #eeeeee); background-size: 300% 300%; animation: weather-flow 20s ease infinite; }}
        .bg-weather-rain {{ background: linear-gradient(180deg, #e3f2fd, #cfd8dc, #eceff1); background-size: 200% 200%; animation: weather-flow 8s ease infinite; }}
        .bg-weather-storm {{ background: linear-gradient(-45deg, #e1bee7, #cfd8dc, #e0e0e0); background-size: 300% 300%; animation: weather-flow 10s ease infinite; }}
        .bg-weather-roof {{ background-color: #ffffff; }}
    </style>
</head>
<body>
    <nav class="navbar navbar-dark bg-dark py-2 sticky-top">
        <div class="container d-flex justify-content-between align-items-center">
            <a href="/test_index.html" class="navbar-brand text-white fw-bold m-0" style="font-style: italic;">
                🧪 Weather MLB <span class="badge bg-warning text-dark ms-2" style="font-style: normal; font-size: 0.7rem;">API Test Slate</span>
            </a>
            <a href="/" class="btn btn-sm btn-outline-light px-3 fw-bold">Live Production Site ➔</a>
        </div>
    </nav>

    <div class="main-container">
        <div class="text-center mb-4">
            <h1 class="fw-bold h2 mb-1">Weather API Triplicate Comparison</h1>
            <p class="text-muted mb-3" style="font-size: 0.9rem;">Comparing Today's Slate Across Tomorrow.io, WeatherAPI, and Open-Meteo ({display_date})</p>
            <button class="btn btn-sm btn-outline-secondary fw-bold px-4 py-1" style="border-radius: 20px;" onclick="toggleAllCards()">
                <span id="expand-icon">▼</span> Toggle All Cards
            </button>
        </div>

        <div id="test-games-container">
            {test_clusters_html}
        </div>
    </div>

    <!-- LIVE RADAR MODAL -->
    <div class="modal fade" id="radarModal" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-lg modal-dialog-centered">
            <div class="modal-content shadow">
                <div class="modal-header bg-dark text-white border-0 py-2">
                    <h5 class="modal-title fw-bold" style="font-size: 1rem;">Live Weather Radar</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body p-0 bg-light" style="height: 60vh;">
                    <iframe id="radarFrame" src="" class="w-100 h-100 border-0" allowfullscreen></iframe>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
    let globalCompact = true;

    function toggleSingleCard(e, cardId) {{
        if (e && e.target.closest('a, button, input, label, select')) return;
        const card = document.getElementById(`card-${{cardId}}`);
        if (!card) return;
        const ribbon = card.querySelector('.ribbon-view');
        const full = card.querySelector('.full-card-view');
        if (ribbon.style.display === 'none') {{
            ribbon.style.display = 'block'; full.style.display = 'none';
        }} else {{
            ribbon.style.display = 'none'; full.style.display = 'block';
        }}
    }}

    function toggleAllCards() {{
        globalCompact = !globalCompact;
        document.querySelectorAll('.game-card').forEach(card => {{
            const ribbon = card.querySelector('.ribbon-view');
            const full = card.querySelector('.full-card-view');
            if (ribbon && full) {{
                ribbon.style.display = globalCompact ? 'block' : 'none';
                full.style.display = globalCompact ? 'none' : 'block';
            }}
        }});
    }}

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

# ==========================================
# 7. MAIN CONTROLLER
# ==========================================
def main():
    est_now = datetime.now(EST_TZ)
    date_str = est_now.strftime('%Y-%m-%d')
    display_date = est_now.strftime('%B %d, %Y').replace(' 0', ' ')

    print(f"🎬 Starting Triplicate Weather API Comparison Generator ({date_str} EST)...")

    session = requests.Session()
    stadiums = load_json(STADIUMS_FILE, [])

    schedule_url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={date_str}&endDate={date_str}&hydrate=venue"
    
    try:
        schedule_data = session.get(schedule_url, timeout=15).json()
    except Exception as e:
        print(f"❌ Failed to fetch MLB schedule for test script: {e}")
        return

    clusters_markup = []

    for date_item in schedule_data.get('dates', []):
        for game in date_item.get('games', []):
            away_team = game['teams']['away']['team']['name']
            home_team = game['teams']['home']['team']['name']
            venue_id = game.get('venue', {}).get('id')
            stadium = next((s for s in stadiums if s.get('id') == venue_id), None)

            if not stadium:
                stadium = {
                    "name": game.get('venue', {}).get('name', 'Stadium'),
                    "lat": 39.0, "lon": -95.0, "dome": False
                }

            game['stadium'] = stadium
            print(f"   ☁️ Testing APIs for: {away_team} @ {home_team}")

            # Fetch weather from all 3 sources
            w_tomorrow = fetch_tomorrow_io(session, stadium['lat'], stadium['lon'], game['gameDate'])
            time.sleep(1)
            w_weatherapi = fetch_weather_api(session, stadium['lat'], stadium['lon'], game['gameDate'])
            time.sleep(1)
            w_meteo = fetch_open_meteo(session, stadium['lat'], stadium['lon'], game['gameDate'])
            time.sleep(1)

            card_tomorrow = render_test_card(game, w_tomorrow, "Tomorrow.io", "bg-primary text-white")
            card_weatherapi = render_test_card(game, w_weatherapi, "WeatherAPI", "bg-success text-white")
            card_meteo = render_test_card(game, w_meteo, "Open-Meteo", "bg-dark text-white")

            cluster_html = f"""
            <div class="matchup-cluster mb-4 p-3 bg-white border rounded shadow-sm">
                <h5 class="fw-bold text-dark border-bottom pb-2 mb-3">
                    ⚾ {away_team} @ {home_team} <span class="text-muted fs-6 font-normal">({stadium['name']})</span>
                </h5>
                <div class="row">
                    {card_tomorrow}
                    {card_weatherapi}
                    {card_meteo}
                </div>
            </div>
            """
            clusters_markup.append(cluster_html)

    if not clusters_markup:
        clusters_html = f"""
        <div class="alert alert-light border text-center py-5 shadow-sm">
            <h4 class="text-muted">No MLB games scheduled for today ({display_date})</h4>
        </div>
        """
    else:
        clusters_html = "\n".join(clusters_markup)

    page_html = TEST_SITE_TEMPLATE.format(
        display_date=display_date,
        test_clusters_html=clusters_html
    )

    with open(TEST_INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(page_html)

    print(f"🎉 Created test comparison page: {TEST_INDEX_FILE}")

if __name__ == "__main__":
    main()
