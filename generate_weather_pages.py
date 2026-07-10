import os

# ==========================================
# 1. THE MASTER 30 MLB TEAMS DICTIONARY
# ==========================================
# Maps exact MLB API IDs to clean URL slugs, display names, and home stadiums
MLB_TEAMS = [
    # AL East
    {"id": 110, "slug": "baltimore-orioles", "name": "Baltimore Orioles", "stadium": "Oriole Park at Camden Yards"},
    {"id": 111, "slug": "boston-red-sox", "name": "Boston Red Sox", "stadium": "Fenway Park"},
    {"id": 147, "slug": "new-york-yankees", "name": "New York Yankees", "stadium": "Yankee Stadium"},
    {"id": 139, "slug": "tampa-bay-rays", "name": "Tampa Bay Rays", "stadium": "Tropicana Field"},
    {"id": 141, "slug": "toronto-blue-jays", "name": "Toronto Blue Jays", "stadium": "Rogers Centre"},
    
    # AL Central
    {"id": 145, "slug": "chicago-white-sox", "name": "Chicago White Sox", "stadium": "Guaranteed Rate Field"},
    {"id": 114, "slug": "cleveland-guardians", "name": "Cleveland Guardians", "stadium": "Progressive Field"},
    {"id": 116, "slug": "detroit-tigers", "name": "Detroit Tigers", "stadium": "Comerica Park"},
    {"id": 118, "slug": "kansas-city-royals", "name": "Kansas City Royals", "stadium": "Kauffman Stadium"},
    {"id": 142, "slug": "minnesota-twins", "name": "Minnesota Twins", "stadium": "Target Field"},
    
    # AL West
    {"id": 117, "slug": "houston-astros", "name": "Houston Astros", "stadium": "Minute Maid Park"},
    {"id": 108, "slug": "los-angeles-angels", "name": "Los Angeles Angels", "stadium": "Angel Stadium"},
    {"id": 133, "slug": "athletics", "name": "Athletics", "stadium": "Sutter Health Park"},
    {"id": 136, "slug": "seattle-mariners", "name": "Seattle Mariners", "stadium": "T-Mobile Park"},
    {"id": 140, "slug": "texas-rangers", "name": "Texas Rangers", "stadium": "Globe Life Field"},
    
    # NL East
    {"id": 144, "slug": "atlanta-braves", "name": "Atlanta Braves", "stadium": "Truist Park"},
    {"id": 146, "slug": "miami-marlins", "name": "Miami Marlins", "stadium": "loanDepot park"},
    {"id": 121, "slug": "new-york-mets", "name": "New York Mets", "stadium": "Citi Field"},
    {"id": 143, "slug": "philadelphia-phillies", "name": "Philadelphia Phillies", "stadium": "Citizens Bank Park"},
    {"id": 120, "slug": "washington-nationals", "name": "Washington Nationals", "stadium": "Nationals Park"},
    
    # NL Central
    {"id": 112, "slug": "chicago-cubs", "name": "Chicago Cubs", "stadium": "Wrigley Field"},
    {"id": 113, "slug": "cincinnati-reds", "name": "Cincinnati Reds", "stadium": "Great American Ball Park"},
    {"id": 158, "slug": "milwaukee-brewers", "name": "Milwaukee Brewers", "stadium": "American Family Field"},
    {"id": 134, "slug": "pittsburgh-pirates", "name": "Pittsburgh Pirates", "stadium": "PNC Park"},
    {"id": 138, "slug": "st-louis-cardinals", "name": "St. Louis Cardinals", "stadium": "Busch Stadium"},
    
    # NL West
    {"id": 109, "slug": "arizona-diamondbacks", "name": "Arizona Diamondbacks", "stadium": "Chase Field"},
    {"id": 115, "slug": "colorado-rockies", "name": "Colorado Rockies", "stadium": "Coors Field"},
    {"id": 119, "slug": "los-angeles-dodgers", "name": "Los Angeles Dodgers", "stadium": "Dodger Stadium"},
    {"id": 135, "slug": "san-diego-padres", "name": "San Diego Padres", "stadium": "Petco Park"},
    {"id": 137, "slug": "san-francisco-giants", "name": "San Francisco Giants", "stadium": "Oracle Park"}
]

# ==========================================
# 2. THE HARDCODED STATIC HTML TEMPLATE
# ==========================================
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Google Analytics -->
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-0TNW6W5ZVN"></script>
    <script>
      window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'G-0TNW6W5ZVN');
    </script>
    
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- DYNAMIC SEO META TAGS -->
    <title>{team_name} Game Weather Today at {stadium_name} | Rain & Wind Forecast</title>
    <meta name="description" content="View the live weather forecast for today's {team_name} game at {stadium_name}. Track real-time rain delay risks, stadium wind direction, hourly temperatures, and betting odds.">
    <meta name="keywords" content="{team_name} weather, {stadium_name} wind direction, {stadium_name} rain delay, {team_name} game weather today, fantasy baseball weather">
    <link rel="canonical" href="https://weathermlb.com/{team_slug}/" />
    
    <!-- OpenGraph Metadata -->
    <meta property="og:title" content="{team_name} Game Weather Today at {stadium_name} - Weather MLB">
    <meta property="og:description" content="Track stadium wind, hourly rain risks, and weather impact analytics for the {team_name} game at {stadium_name}.">
    <meta property="og:url" content="https://weathermlb.com/{team_slug}/">
    <meta property="og:type" content="website">
    <meta property="og:image" content="https://weathermlb.com/social-share.png">
    
    <meta name="twitter:card" content="summary">
    <meta name="twitter:site" content="@weathermlbdaily">
    
    <!-- Bootstrap CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <style>
        body { background-color: #f8f9fa; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; } 
        .main-container { max-width: 520px; margin: 30px auto; padding: 0 15px; }
        .game-card { border: 1px solid #dee2e6; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); background: white; overflow: hidden; }
        .weather-row { font-size: 0.9rem; border-top: 1px solid #f1f3f5; padding-top: 8px; margin-top: 8px; padding-bottom: 4px; }
        .stadium-name { color: #6c757d; font-size: 0.85rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px; }
        .wind-badge { font-size: 0.85rem; padding: 4px 10px; border-radius: 20px; font-weight: 600; display: inline-block; }
        .wind-badge .arrow-emoji { font-size: 1.1rem; line-height: 0.5; vertical-align: middle; }
        .bg-out { background-color: #d1e7dd; color: #0f5132; } 
        .bg-in { background-color: #f8d7da; color: #842029; }
        .bg-cross { background-color: #fff3cd; color: #664d03; }
        .bg-secondary.text-white { background-color: #adb5bd !important; color: #fff !important; }
        .analysis-box { background-color: rgba(255, 255, 255, 0.6); border-left: 4px solid #0d6efd; padding: 8px 12px; margin-top: 12px; font-size: 0.8rem; color: #495057; line-height: 1.4; border-radius: 0 4px 4px 0; }
        .analysis-title { font-weight: 800; text-transform: uppercase; font-size: 0.7rem; color: #0d6efd; display: block; margin-bottom: 4px; letter-spacing: 0.5px; }
        .hourly-scroll-container { display: flex; overflow-x: auto; gap: 8px; padding: 8px 4px; margin-top: 8px; border-top: 1px solid rgba(0,0,0,0.05); scrollbar-width: thin; }
        .hour-card { display: flex; flex: 1; flex-direction: column; align-items: center; min-width: 60px; text-align: center; }
        .hour-time { font-size: 0.75rem; font-weight: 600; color: #6c757d; margin-bottom: 2px; }
        .hour-icon { font-size: 1.3rem; line-height: 1; margin-bottom: 2px; }
        .hour-pop { font-size: 0.65rem; color: #5ac8fa; font-weight: 700; line-height: 1; height: 12px; margin-bottom: 2px; }
        .hour-temp { font-size: 0.85rem; font-weight: 600; color: #212529; line-height: 1; }
        @keyframes weather-flow { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
        .bg-weather-sunny { background: linear-gradient(-45deg, #e3f2fd, #e1f5fe, #f1f8e9); background-size: 300% 300%; animation: weather-flow 15s ease infinite; }
        .bg-weather-cloudy { background: linear-gradient(-45deg, #f5f5f5, #e0e0e0, #eeeeee); background-size: 300% 300%; animation: weather-flow 20s ease infinite; }
        .bg-weather-rain { background: linear-gradient(180deg, #e3f2fd, #cfd8dc, #eceff1); background-size: 200% 200%; animation: weather-flow 8s ease infinite; }
        .bg-weather-storm { background: linear-gradient(-45deg, #e1bee7, #cfd8dc, #e0e0e0); background-size: 300% 300%; animation: weather-flow 10s ease infinite; }
        .bg-weather-snow { background: linear-gradient(-45deg, #f3e5f5, #e3f2fd, #ffffff); background-size: 300% 300%; animation: weather-flow 15s ease infinite; }
        .bg-weather-roof { background-color: #ffffff; }
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
                    <option value="/arizona-diamondbacks/">Arizona Diamondbacks</option>
                    <option value="/athletics/">Athletics</option>
                    <option value="/atlanta-braves/">Atlanta Braves</option>
                    <option value="/baltimore-orioles/">Baltimore Orioles</option>
                    <option value="/boston-red-sox/">Boston Red Sox</option>
                    <option value="/chicago-cubs/">Chicago Cubs</option>
                    <option value="/chicago-white-sox/">Chicago White Sox</option>
                    <option value="/cincinnati-reds/">Cincinnati Reds</option>
                    <option value="/cleveland-guardians/">Cleveland Guardians</option>
                    <option value="/colorado-rockies/">Colorado Rockies</option>
                    <option value="/detroit-tigers/">Detroit Tigers</option>
                    <option value="/houston-astros/">Houston Astros</option>
                    <option value="/kansas-city-royals/">Kansas City Royals</option>
                    <option value="/los-angeles-angels/">Los Angeles Angels</option>
                    <option value="/los-angeles-dodgers/">Los Angeles Dodgers</option>
                    <option value="/miami-marlins/">Miami Marlins</option>
                    <option value="/milwaukee-brewers/">Milwaukee Brewers</option>
                    <option value="/minnesota-twins/">Minnesota Twins</option>
                    <option value="/new-york-mets/">New York Mets</option>
                    <option value="/new-york-yankees/">New York Yankees</option>
                    <option value="/philadelphia-phillies/">Philadelphia Phillies</option>
                    <option value="/pittsburgh-pirates/">Pittsburgh Pirates</option>
                    <option value="/san-diego-padres/">San Diego Padres</option>
                    <option value="/san-francisco-giants/">San Francisco Giants</option>
                    <option value="/seattle-mariners/">Seattle Mariners</option>
                    <option value="/st-louis-cardinals/">St. Louis Cardinals</option>
                    <option value="/tampa-bay-rays/">Tampa Bay Rays</option>
                    <option value="/texas-rangers/">Texas Rangers</option>
                    <option value="/toronto-blue-jays/">Toronto Blue Jays</option>
                    <option value="/washington-nationals/">Washington Nationals</option>
                </select>
                <a href="/" class="btn btn-sm btn-outline-light px-3 fw-bold" style="font-size: 0.75rem;">
                    Full Slate
                </a>
            </div>
        </div>
    </nav>

    <div class="main-container">
        <!-- Target container where JavaScript renders the report card -->
        <div id="team-weather-container">
            <div class="text-center p-5 text-muted">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                Loading today's forecast details...
            </div>
        </div>
    </div>

    <footer class="text-center py-4 text-muted mt-5" style="font-size: 0.75rem;">
        <div class="container">
            <p class="mb-1">© 2026 Weather MLB. All rights reserved.</p>
            <p class="mb-0">Data curated via official sources. Not affiliated with Major League Baseball.</p>
        </div>
    </footer>

    <!-- Pass this unique team's context directly down to your engine script -->
    <script>
        window.TARGET_TEAM_ID = {team_id};
        window.TARGET_TEAM_SLUG = "{team_slug}";
        
        // Auto-select this team in the dropdown menu on page load
        document.addEventListener("DOMContentLoaded", () => {
            const selectMenu = document.getElementById("team-nav-select");
            if (selectMenu) {
                selectMenu.value = `/${window.TARGET_TEAM_SLUG}/`;
            }
        });
    </script>
    <!-- Use ../ to look one directory up to the root where script.js lives -->
    <script src="../script.js"></script>
</body>
</html>
"""

# ==========================================
# 3. BUILD ENGINE
# ==========================================
def generate_all_weather_pages():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("🌤️ Starting Programmatic Weather Page Generator Engine...")
    
    for team in MLB_TEAMS:
        team_dir = os.path.join(base_dir, team["slug"])
        
        # Create team folder if it doesn't exist
        if not os.path.exists(team_dir):
            os.makedirs(team_dir)
            
        # Format the HTML template with this specific team's data
        file_content = (
            HTML_TEMPLATE.replace("{team_name}", team["name"])
                         .replace("{team_slug}", team["slug"])
                         .replace("{stadium_name}", team["stadium"])
                         .replace("{team_id}", str(team["id"]))
        )
        
        file_path = os.path.join(team_dir, "index.html")
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(file_content)
            
        print(f"✅ Generated: /{team['slug']}/index.html (Stadium: {team['stadium']})")
        
    print("\n🚀 Successfully compiled all 30 inner team media folders!")

if __name__ == "__main__":
    generate_all_weather_pages()
