import requests
import json
import os
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
API_KEY = os.environ.get("ODDS_API_KEY") 
REGIONS = "us"
MARKETS = "h2h,totals"
ODDS_FORMAT = "american"
OUTPUT_FILE = "data/odds.json" 

def get_active_sports():
    """
    Dynamically determines which sports to fetch based on the current date.
    """
    # Grab the current date in UTC
    current_date = datetime.now(timezone.utc).date()
    
    # Define our transition dates (Year, Month, Day)
    wbc_start = datetime(2026, 3, 4).date()
    wbc_end = datetime(2026, 3, 17).date()
    opening_day = datetime(2026, 3, 25).date()
    
    # 1. Regular Season (March 25th onwards)
    if current_date >= opening_day:
        return ["baseball_mlb"]
        
    # 2. WBC Window (March 4th - March 17th)
    elif wbc_start <= current_date <= wbc_end:
        return ["baseball_mlb_preseason", "baseball_wbc"]
        
    # 3. Default/Current (Before March 4th, or March 18-24)
    else:
        return ["baseball_mlb"]

def fetch_and_save_odds():
    if not API_KEY:
        print("❌ ERROR: API key not found in environment variables.")
        return

    # Call our new smart calendar function
    active_sports = get_active_sports()
    
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Active Sports: {active_sports}")
    
    new_odds_data = []
    
    # --- DYNAMICALLY FETCH MULTIPLE SPORTS ---
    for sport in active_sports:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}&oddsFormat={ODDS_FORMAT}"
        
        try:
            response = requests.get(url)
            if response.status_code == 200:
                sport_odds = response.json()
                new_odds_data.extend(sport_odds)
                print(f"✅ Fetched {len(sport_odds)} games for {sport}")
            else:
                print(f"❌ API Error for {sport}: {response.status_code}")
        except Exception as e:
            print(f"❌ Request failed for {sport}: {e}")

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
        commence_time = datetime.strptime(game['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        
        if now_utc - commence_time < timedelta(hours=24):
            final_odds_list.append(game)

    # --- 4. SAVE FILE ---
    output_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "sport": "dynamic_baseball", 
        "game_count": len(final_odds_list),
        "odds": final_odds_list
    }
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output_data, f, indent=4)
        
    print(f"✅ Successfully merged and saved {len(final_odds_list)} total games to {OUTPUT_FILE}")

if __name__ == "__main__":
    fetch_and_save_odds()
