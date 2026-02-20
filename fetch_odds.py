import requests
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
# Pull the API key from GitHub Secrets securely
API_KEY = os.environ.get("ODDS_API_KEY") 
SPORT = "baseball_mlb_preseason" # Change to "baseball_mlb" when regular season starts
REGIONS = "us"
MARKETS = "h2h,totals"
ODDS_FORMAT = "american"

# Save path (Ensure this matches where your JS looks for it)
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
            odds_data = response.json()
            output_data = {
                "last_updated": datetime.now().isoformat(),
                "sport": SPORT,
                "game_count": len(odds_data),
                "odds": odds_data
            }
            
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(output_data, f, indent=4)
                
            print(f"✅ Successfully saved {len(odds_data)} games to {OUTPUT_FILE}")
        else:
            print(f"❌ API Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Script failed: {e}")

if __name__ == "__main__":
    fetch_and_save_odds()
