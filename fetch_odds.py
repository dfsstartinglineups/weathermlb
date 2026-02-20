import requests
import json
import os
from datetime import datetime, timedelta, timezone

# --- CONFIGURATION ---
API_KEY = os.environ.get("ODDS_API_KEY") 
SPORT = "baseball_mlb_preseason" # Change to "baseball_mlb" when regular season starts
REGIONS = "us"
MARKETS = "h2h,totals"
ODDS_FORMAT = "american"
OUTPUT_FILE = "data/odds.json" 

def fetch_and_save_odds():
    if not API_KEY:
        print("❌ ERROR: API key not found in environment variables.")
        return

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching MLB odds...")
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}&oddsFormat={ODDS_FORMAT}"
    
    try:
        response = requests.get(url)
        if response.status_code == 200:
            new_odds_data = response.json()
            
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
            # Create a dictionary keyed by game ID for easy updating
            merged_odds = {game['id']: game for game in existing_odds_data}
            
            # Overwrite/Add the freshly fetched games
            for game in new_odds_data:
                merged_odds[game['id']] = game

            # --- 3. CLEANUP STALE GAMES (Keep only last 24 hours) ---
            now_utc = datetime.now(timezone.utc)
            final_odds_list = []
            
            for game in merged_odds.values():
                # Parse the game's start time
                commence_time = datetime.strptime(game['commence_time'], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                
                # If the game is in the future, OR started less than 24 hours ago, keep it!
                if now_utc - commence_time < timedelta(hours=24):
                    final_odds_list.append(game)

            # --- 4. SAVE FILE ---
            output_data = {
                "last_updated": datetime.now(timezone.utc).isoformat(),
                "sport": SPORT,
                "game_count": len(final_odds_list),
                "odds": final_odds_list
            }
            
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(output_data, f, indent=4)
                
            print(f"✅ Successfully merged and saved {len(final_odds_list)} games to {OUTPUT_FILE}")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Script failed: {e}")

if __name__ == "__main__":
    fetch_and_save_odds()
