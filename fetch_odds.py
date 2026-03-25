import requests
import json
import os
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
# No API Keys Needed for ESPN!
OUTPUT_FILE = "data/odds.json" 

def get_active_sports():
    """
    Dynamically determines which ESPN sports to fetch based on the current date.
    ESPN uses 'mlb' for both preseason and regular season.
    """
    current_date = datetime.now(timezone.utc).date()
    wbc_start = datetime(2026, 3, 4).date()
    wbc_end = datetime(2026, 3, 17).date()
    
    # During WBC, check both WBC and MLB (Spring Training)
    if wbc_start <= current_date <= wbc_end:
        return ["world-baseball-classic", "mlb"]
        
    return ["mlb"]

def fetch_and_save_odds():
    active_sports = get_active_sports()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Active Sports: {active_sports}")
    
    new_odds_data = []
    
    # ESPN fetches by specific date, so we grab Today and Tomorrow to catch all upcoming slates
    dates_to_fetch = [
        datetime.now(timezone.utc).strftime('%Y%m%d'),
        (datetime.now(timezone.utc) + timedelta(days=1)).strftime('%Y%m%d')
    ]
    
    # --- DYNAMICALLY FETCH FROM ESPN ---
    for sport in active_sports:
        for target_date in dates_to_fetch:
            url = f"https://site.api.espn.com/apis/site/v2/sports/baseball/{sport}/scoreboard?dates={target_date}"
            
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    events = data.get('events', [])
                    
                    valid_games_count = 0
                    for event in events:
                        game_id = event['id']
                        commence_time = event['date']
                        
                        comp = event['competitions'][0]
                        
                        # Grab full team names (e.g., "New York Yankees") to match the MLB API
                        try:
                            home_team = next(c['team']['displayName'] for c in comp['competitors'] if c['homeAway'] == 'home')
                            away_team = next(c['team']['displayName'] for c in comp['competitors'] if c['homeAway'] == 'away')
                        except StopIteration:
                            continue
                        
                        odds_list = comp.get('odds', [])
                        if not odds_list:
                            continue
                            
                        espn_odds = odds_list[0]
                        provider = espn_odds.get('provider', {}).get('name', 'ESPN BET')
                        
                        markets = []
                        
                        # 1. Map ESPN Moneyline to Odds API 'h2h' structure
                        h2h_outcomes = []
                        home_ml = espn_odds.get('homeTeamOdds', {}).get('moneyLine')
                        away_ml = espn_odds.get('awayTeamOdds', {}).get('moneyLine')
                        
                        if home_ml is not None:
                            h2h_outcomes.append({"name": home_team, "price": home_ml})
                        if away_ml is not None:
                            h2h_outcomes.append({"name": away_team, "price": away_ml})
                            
                        if h2h_outcomes:
                            markets.append({"key": "h2h", "outcomes": h2h_outcomes})
                            
                        # 2. Map ESPN Over/Under to Odds API 'totals' structure
                        totals_outcomes = []
                        over_under = espn_odds.get('overUnder')
                        if over_under is not None:
                            # ESPN doesn't always provide the juice on totals, so we default to standard -110
                            totals_outcomes.append({"name": "Over", "point": over_under, "price": -110})
                            totals_outcomes.append({"name": "Under", "point": over_under, "price": -110})
                            
                        if totals_outcomes:
                            markets.append({"key": "totals", "outcomes": totals_outcomes})
                            
                        if not markets:
                            continue
                            
                        # Package exactly like The Odds API
                        formatted_game = {
                            "id": game_id,
                            "sport_key": f"baseball_{sport}",
                            "sport_title": "MLB" if sport == "mlb" else "WBC",
                            "commence_time": commence_time,
                            "home_team": home_team,
                            "away_team": away_team,
                            "bookmakers": [
                                {
                                    "key": provider.lower().replace(" ", ""),
                                    "title": provider,
                                    "markets": markets
                                }
                            ]
                        }
                        new_odds_data.append(formatted_game)
                        valid_games_count += 1
                        
                    print(f"✅ Fetched {valid_games_count} games with odds for {sport} on {target_date}")
                else:
                    print(f"❌ ESPN API Error for {sport} on {target_date}: {response.status_code}")
            except Exception as e:
                print(f"❌ Request failed for {sport} on {target_date}: {e}")

    # --- 1. LOAD EXISTING DATA ---
    existing_odds_data = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                old_file = json.load(f)
                existing_odds_data = old_file.get("odds", [])
        except Exception as e:
            print(f"⚠️ Could not read existing file (starting fresh): {e}")

    # --- 2. MERGE LOGIC ---
    merged_odds = {game['id']: game for game in existing_odds_data}
    
    for game in new_odds_data:
        merged_odds[game['id']] = game

    # --- 3. CLEANUP STALE GAMES (Keep only last 24 hours) ---
    now_utc = datetime.now(timezone.utc)
    final_odds_list = []
    
    for game in merged_odds.values():
        try:
            commence_time = datetime.strptime(game['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if now_utc - commence_time < timedelta(hours=24):
                final_odds_list.append(game)
        except Exception as e:
            pass

    # --- 4. SAVE FILE ---
    output_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "sport": "dynamic_baseball_espn", 
        "game_count": len(final_odds_list),
        "odds": final_odds_list
    }
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=4)
        
    print(f"✅ Successfully merged and saved {len(final_odds_list)} total games to {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_and_save_odds()
