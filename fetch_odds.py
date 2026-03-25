import requests
import json
import os
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
# No API Keys Needed! We are using ESPN's free scoreboard API.
OUTPUT_FILE = "data/odds.json" 

def get_active_sports():
    """
    Dynamically determines which ESPN sports to fetch based on the current date.
    """
    current_date = datetime.now(timezone.utc).date()
    wbc_start = datetime(2026, 3, 4).date()
    wbc_end = datetime(2026, 3, 17).date()
    
    if wbc_start <= current_date <= wbc_end:
        return ["world-baseball-classic", "mlb"]
        
    return ["mlb"]

def fetch_and_save_odds():
    active_sports = get_active_sports()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Active Sports: {active_sports}")
    
    new_odds_data = []
    
    # Fetch today and tomorrow to catch all upcoming slates
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
                        
                        # 1. Map ESPN Moneyline using the newly discovered paths
                        h2h_outcomes = []
                        moneyline_data = espn_odds.get('moneyline', {})
                        
                        home_ml = moneyline_data.get('home', {}).get('close', {}).get('odds')
                        away_ml = moneyline_data.get('away', {}).get('close', {}).get('odds')
                        
                        if home_ml is not None:
                            h2h_outcomes.append({"name": home_team, "price": home_ml})
                        if away_ml is not None:
                            h2h_outcomes.append({"name": away_team, "price": away_ml})
                            
                        if h2h_outcomes:
                            markets.append({"key": "h2h", "outcomes": h2h_outcomes})
                            
                        # 2. Map ESPN Over/Under using the newly discovered paths
                        totals_outcomes = []
                        over_under_point = espn_odds.get('overUnder')
                        totals_data = espn_odds.get('total', {})
                        
                        if over_under_point is not None:
                            over_juice = totals_data.get('over', {}).get('close', {}).get('odds', -110)
                            under_juice = totals_data.get('under', {}).get('close', {}).get('odds', -110)
                            
                            totals_outcomes.append({"name": "Over", "point": over_under_point, "price": over_juice})
                            totals_outcomes.append({"name": "Under", "point": over_under_point, "price": under_juice})
                            
                        if totals_outcomes:
                            markets.append({"key": "totals", "outcomes": totals_outcomes})
                            
                        if not markets:
                            continue
                            
                        # Package exactly like The Odds API so the frontend doesn't break
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

    # --- 2. SMART MERGE LOGIC ---
    merged_odds = {game['id']: game for game in existing_odds_data}
    
    for new_game in new_odds_data:
        game_id = new_game['id']
        
        if game_id not in merged_odds:
            # It's a brand new game we haven't seen before
            merged_odds[game_id] = new_game
        else:
            # We already have this game in memory. Let's merge the markets carefully.
            existing_game = merged_odds[game_id]
            new_book = new_game['bookmakers'][0] 
            
            # Grab the existing bookmaker (ESPN)
            existing_book = next((b for b in existing_game.get('bookmakers', []) if b['key'] == new_book['key']), None)
            
            if not existing_book:
                existing_game.setdefault('bookmakers', []).append(new_book)
            else:
                # Merge individual markets (h2h vs totals)
                existing_markets = {m['key']: m for m in existing_book.get('markets', [])}
                
                # Overwrite/Update ONLY the markets ESPN actually provided in this fresh pull
                for new_market in new_book.get('markets', []):
                    existing_markets[new_market['key']] = new_market
                
                # Put the protected markets back into the bookmaker
                existing_book['markets'] = list(existing_markets.values())

    # --- 3. CLEANUP STALE GAMES (Keep only last 24 hours) ---
    now_utc = datetime.now(timezone.utc)
    final_odds_list = []
    
    for game in merged_odds.values():
        try:
            date_str = game['commence_time']
            if date_str.endswith('Z'):
                date_str = date_str[:-1]
            if len(date_str.split(':')) == 2:
                date_str += ":00"
                
            commence_time = datetime.fromisoformat(date_str).replace(tzinfo=timezone.utc)
            
            if now_utc - commence_time < timedelta(hours=24):
                final_odds_list.append(game)
        except Exception as e:
            print(f"⚠️ Dropped game {game.get('id')} due to date parsing error: {e}")

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
