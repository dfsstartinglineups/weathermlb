import os
import json
import zoneinfo
from datetime import datetime, timezone

# ==========================================
# 1. MASTER MLB TEAMS LIST
# ==========================================
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

# ==========================================
# 2. HELPER FORMATTING FUNCTIONS
# ==========================================
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

def generate_matchup_analysis(weather, wind_info, is_roof_closed, is_roof_pending, stadium):
    if is_roof_closed:
        return "✅ <b>Roof Closed:</b> Controlled environment with zero weather impact."

    notes = []
    if is_roof_pending:
        notes.push("🏟️ <b>Roof Status Pending:</b> Borderline weather. The team may elect to close the roof.") if hasattr(notes, 'push') else notes.append("🏟️ <b>Roof Status Pending:</b> Borderline weather. The team may elect to close the roof.")

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
        notes.append("🌧️ <b>Rainout Risk:</b> Sustained heavy rain. High probability of postponement.")
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

# ==========================================
# 3. CARD GENERATION LOGIC
# ==========================================
def render_main_game_card(data, index):
    game = data['gameRaw']
    stadium = data.get('stadium') or {}
    weather = data.get('weather') or {}
    wind_info = data.get('wind') or {}
    is_roof_closed = data.get('roof', False)
    is_roof_pending = data.get('roofPending', False)

    # Border Class
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

    # Background Class
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

    away_team = game['teams']['away']
    home_team = game['teams']['home']
    away_id, home_id = away_team['team']['id'], home_team['team']['id']
    away_name, home_name = away_team['team']['name'], home_team['team']['name']
    away_short, home_short = get_short_team_name(away_name), get_short_team_name(home_name)
    away_logo = f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{away_id}.svg"
    home_logo = f"https://www.mlbstatic.com/team-logos/team-cap-on-light/{home_id}.svg"

    # Time formatting in Eastern Time
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

    # Probable Pitchers
    away_pitcher_info = away_team.get('probablePitcher')
    away_pitcher = format_player_name(away_pitcher_info['fullName']) + (f" ({away_pitcher_info['pitchHand']['code']})" if away_pitcher_info and 'pitchHand' in away_pitcher_info else "") if away_pitcher_info else "TBD"
    
    home_pitcher_info = home_team.get('probablePitcher')
    home_pitcher = format_player_name(home_pitcher_info['fullName']) + (f" ({home_pitcher_info['pitchHand']['code']})" if home_pitcher_info and 'pitchHand' in home_pitcher_info else "") if home_pitcher_info else "TBD"

    # Odds
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

    # Weather
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
                    et_hour = h_dt.hour
                    is_night = et_hour >= 20 or et_hour < 6

                    pop_html = '&nbsp;'
                    if h.get('precipChance', 0) >= 30:
                        icon = '⛈️' if h.get('isThunderstorm') else ('🌨️' if h.get('isSnow') else '🌧️')
                        pop_html = f"{h['precipChance']}%"
                    elif h.get('precipChance', 0) > 0:
                        icon = '⛅'
                        pop_html = f"{h['precipChance']}%"
                    else:
                        icon = '🌙' if is_night else '☀️'

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
    <div class="col-md-6 col-lg-4 col-xl-3 col-xxl-2 animate-card mb-2 px-1 game-card-wrapper" 
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

                pop_html = '&nbsp;'
                if h.get('precipChance', 0) >= 30:
                    icon = '⛈️' if h.get('isThunderstorm') else ('🌨️' if h.get('isSnow') else '🌧️')
                    pop_html = f"{h['precipChance']}%"
                elif h.get('precipChance', 0) > 0:
                    icon = '⛅'
                    pop_html = f"{h['precipChance']}%"
                else:
                    icon = '🌙' if is_night else '☀️'

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
# 4. LIGHTWEIGHT CLIENT-SIDE JS INJECTION
# ==========================================
MAIN_PAGE_INTERACTIVE_JS = """
<script>
let ARE_ALL_EXPANDED = false;

function toggleSingleCard(e, gamePk) {
    if (e && e.target.closest('a, button, input, label, [data-bs-toggle="collapse"]')) return;
    const card = document.getElementById(`game-${gamePk}`);
    if (!card) return;
    const ribbon = card.querySelector('.ribbon-view');
    const full = card.querySelector('.full-card-view');
    if (ribbon.style.display === 'none') {
        ribbon.style.display = 'block'; full.style.display = 'none';
    } else {
        ribbon.style.display = 'none'; full.style.display = 'block';
    }
}

function toggleAllWeatherCards() {
    ARE_ALL_EXPANDED = !ARE_ALL_EXPANDED;
    const btnText = document.getElementById('expand-toggle-text');
    const btnIcon = document.getElementById('expand-toggle-icon');
    if (btnText && btnIcon) {
        btnText.innerText = ARE_ALL_EXPANDED ? 'Collapse All Cards' : 'Expand All Cards';
        btnIcon.innerText = ARE_ALL_EXPANDED ? '▲' : '▼';
    }
    document.querySelectorAll('.game-card-wrapper').forEach(card => {
        const ribbon = card.querySelector('.ribbon-view');
        const full = card.querySelector('.full-card-view');
        if (ribbon && full) {
            ribbon.style.display = ARE_ALL_EXPANDED ? 'none' : 'block';
            full.style.display = ARE_ALL_EXPANDED ? 'block' : 'none';
        }
    });
}

function filterAndSortGames() {
    const container = document.getElementById('games-container');
    const cards = Array.from(container.querySelectorAll('.game-card-wrapper'));
    const sortMode = document.getElementById('sort-filter').value;
    const riskOnly = document.getElementById('risk-only').checked;

    cards.forEach(card => {
        const isRisk = card.getAttribute('data-risk') === '1';
        if (riskOnly && !isRisk) {
            card.style.display = 'none';
        } else {
            card.style.display = 'block';
        }
    });

    cards.sort((a, b) => {
        if (sortMode === 'wind') return parseFloat(b.getAttribute('data-wind')) - parseFloat(a.getAttribute('data-wind'));
        if (sortMode === 'rain') return parseFloat(b.getAttribute('data-rain')) - parseFloat(a.getAttribute('data-rain'));
        if (sortMode === 'temp') return parseFloat(b.getAttribute('data-temp')) - parseFloat(a.getAttribute('data-temp'));
        if (sortMode === 'humidity') return parseFloat(b.getAttribute('data-humidity')) - parseFloat(a.getAttribute('data-humidity'));
        return new Date(a.getAttribute('data-game-date')) - new Date(b.getAttribute('data-game-date'));
    });

    cards.forEach(card => container.appendChild(card));
}

document.addEventListener('DOMContentLoaded', () => {
    const sortFilter = document.getElementById('sort-filter');
    const riskToggle = document.getElementById('risk-only');
    const datePicker = document.getElementById('date-picker');

    if (sortFilter) sortFilter.addEventListener('change', filterAndSortGames);
    if (riskToggle) riskToggle.addEventListener('change', filterAndSortGames);

    if (datePicker) {
        datePicker.addEventListener('change', (e) => {
            if (e.target.value) {
                window.location.href = `/?date=${e.target.value}`;
            }
        });
    }
});

function showRadar(url, venueName) {
    const modalElement = document.getElementById('radarModal');
    const modalTitle = document.querySelector('#radarModal .modal-title');
    const iframe = document.getElementById('radarFrame');
    if (modalTitle) modalTitle.innerText = `Radar: ${venueName}`;
    const myModal = bootstrap.Modal.getOrCreateInstance(modalElement);
    if (iframe) iframe.src = url;
    myModal.show();
}
</script>
"""

# ==========================================
# 5. MAIN GENERATOR ENGINE
# ==========================================
def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(base_dir) # Steps up to the root folder
    data_dir = os.path.join(root_dir, "data", "daily_files")
    
    today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    daily_file = os.path.join(data_dir, f"games_{today_str}.json")

    games_data = []
    if os.path.exists(daily_file):
        with open(daily_file, 'r', encoding='utf-8') as f:
            games_data = json.load(f)
    else:
        print(f"⚠️ No game JSON file found for {today_str}. Creating fallback containers.")

    # ------------------------------------------
    # 5A. BUILD MAIN INDEX.HTML
    # ------------------------------------------
    cards_html_list = []
    if games_data:
        for idx, item in enumerate(games_data):
            cards_html_list.append(render_main_game_card(item, idx))
        cards_container_html = f'''
        <div class="col-12 text-center mb-3 mt-1 position-relative">
            <button class="btn btn-sm shadow-sm fw-bold px-4 py-1" style="background-color: #fff; border: 1px solid #dee2e6; color: #495057; border-radius: 20px;" onclick="toggleAllWeatherCards()">
                <span id="expand-toggle-icon">▼</span> 
                <span id="expand-toggle-text">Expand All Cards</span>
            </button>
        </div>
        {"".join(cards_html_list)}
        '''
    else:
        cards_container_html = f'''
        <div class="col-12 text-center mt-5">
            <div class="alert alert-light border shadow-sm py-4">
                <h4 class="text-muted">No games scheduled for {today_str}</h4>
            </div>
        </div>
        '''

    # Load main template structure
    main_template_path = os.path.join(root_dir, "index.html")
    with open(main_template_path, 'r', encoding='utf-8') as f:
        main_html = f.read()

    # Replace container content and inject lightweight client JS
    main_html = main_html.replace(
        '<div id="games-container" class="row justify-content-center">',
        f'<div id="games-container" class="row justify-content-center">\n{cards_container_html}'
    )
    main_html = main_html.replace('</body>', f'{MAIN_PAGE_INTERACTIVE_JS}\n</body>')

    # Remove dynamic client-side JS script include
    main_html = main_html.replace('<script src="script.js"></script>', '')

    with open(main_template_path, 'w', encoding='utf-8') as f:
        f.write(main_html)

    print("✅ Pre-rendered main index.html with static weather cards!")

    # ------------------------------------------
    # 5B. BUILD 30 INNER TEAM PAGES
    # ------------------------------------------
    team_pages_dir = os.path.join(root_dir, "team_pages")
    os.makedirs(team_pages_dir, exist_ok=True)

    sorted_teams = sorted(MLB_TEAMS, key=lambda x: x["name"])
    dropdown_options = "\n".join([f'<option value="/team_pages/{t["slug"]}/">{t["name"]}</option>' for t in sorted_teams])

    for team in MLB_TEAMS:
        t_dir = os.path.join(team_pages_dir, team["slug"])
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
        else:
            actual_stadium = team['stadium']
            card_markup = '''
            <div class="card p-5 text-center text-muted" style="border: 2px dashed #dee2e6; border-radius: 12px; background: #fff;">
                <h3 class="h5 fw-bold text-dark mb-2">No Game Scheduled Today</h3>
                <p class="small mb-0">This team has an off-day, travel day, or their matchup was postponed early.</p>
            </div>
            '''

        team_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-0TNW6W5ZVN"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){{dataLayer.push(arguments);}}
      gtag('js', new Date());
      gtag('config', 'G-0TNW6W5ZVN');
    </script>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{team["name"]} Game Weather Today at {actual_stadium} | Rain & Wind Forecast</title>
    <meta name="description" content="View the live weather forecast for today's {team["name"]} game at {actual_stadium}. Track real-time rain delay risks, stadium wind direction, hourly temperatures, and betting odds.">
    <meta name="keywords" content="{team["name"]} weather, {actual_stadium} wind direction, {actual_stadium} rain delay, {team["name"]} game weather today, fantasy baseball weather">
    <link rel="canonical" href="https://weathermlb.com/team_pages/{team["slug"]}/" />
    <meta property="og:title" content="{team["name"]} Game Weather Today at {actual_stadium} - Weather MLB">
    <meta property="og:description" content="Track stadium wind, hourly rain risks, and weather impact analytics for the {team["name"]} game at {actual_stadium}.">
    <meta property="og:url" content="https://weathermlb.com/team_pages/{team["slug"]}/">
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
            <a href="/" class="navbar-brand text-white fw-bold m-0" style="font-style: italic; font-size: 1.6rem;">
                Weather <span style="color: #5ac8fa;">MLB</span>
            </a>
            <div class="d-flex align-items-center gap-2">
                <select id="team-nav-select" class="form-select form-select-sm fw-bold" style="background-color: #1e293b; color: #adb5bd; border: 1px solid #334155; cursor: pointer; max-width: 180px;" onchange="if(this.value) window.location.href=this.value;">
                    <option value="">Switch Team</option>
                    {dropdown_options}
                </select>
                <a href="/" class="btn btn-sm btn-outline-light px-3 fw-bold" style="font-size: 0.75rem;">Full Slate</a>
            </div>
        </div>
    </nav>
    <div class="main-container">
        <div id="team-weather-container">
            {card_markup}
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
            if (selectMenu) selectMenu.value = "/team_pages/{team['slug']}/";
        }});
    </script>
</body>
</html>'''

        with open(os.path.join(t_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(team_html)

    print("🚀 Pre-rendered all 30 inner team pages with static weather cards!")

if __name__ == "__main__":
    main()
