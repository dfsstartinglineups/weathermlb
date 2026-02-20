import requests
import json
import os
from datetime import datetime

# --- CONFIGURATION ---

SPORT = "baseball_mlb_preseason" # IMPORTANT: Change to "baseball_mlb" when regular season starts!
REGIONS = "us"
MARKETS = "h2h,totals"
ODDS_FORMAT = "american"

# The file where the frontend expects to find the data
# Make sure this path aligns with your web server's public directory (e.g., /var/www/html/data/odds.json)
OUTPUT_FILE = "data/odds.json" 

def fetch_and_save_odds():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Fetching MLB odds...")
    
    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds/?apiKey={API_KEY}&regions={REGIONS}&markets={MARKETS}&oddsFormat={ODDS_FORMAT}"
    
    try:
        response = requests.get(url)
        
        # Check if the API request was successful
        if response.status_code == 200:
            odds_data = response.json()
            
            # Create a structured object so the frontend knows when it was last updated
            output_data = {
                "last_updated": datetime.now().isoformat(),
                "sport": SPORT,
                "game_count": len(odds_data),
                "odds": odds_data
            }
            
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
            
            # Save the file
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
