// CONFIGURATION
const TEST_DATE = "2024-09-25"; 
const MLB_API_URL = `https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=${TEST_DATE}&hydrate=linescore,venue`;

// 1. MAIN FUNCTION: START THE APP
async function init() {
    console.log("🚀 App Starting...");
    document.getElementById('current-date').innerText = new Date(TEST_DATE).toDateString();
    const container = document.getElementById('games-container');
    
    try {
        // --- CHECKPOINT 1: Load Stadiums ---
        console.log("... Fetching stadiums.json");
        
        // Try looking in the data folder first
        let stadiumResponse = await fetch('data/stadiums.json');
        
        // If that fails (404), try looking in the root folder (common mistake)
        if (!stadiumResponse.ok) {
            console.warn("⚠️ data/stadiums.json not found. Trying root folder...");
            stadiumResponse = await fetch('stadiums.json');
        }

        if (!stadiumResponse.ok) {
            throw new Error(`CRITICAL: Could not find stadiums.json. Status: ${stadiumResponse.status}`);
        }

        const stadiums = await stadiumResponse.json();
        console.log(`✅ Loaded ${stadiums.length} stadiums.`);

        // --- CHECKPOINT 2: Load Schedule ---
        console.log("... Fetching MLB Schedule");
        const scheduleResponse = await fetch(MLB_API_URL);
        const scheduleData = await scheduleResponse.json();
        console.log("✅ MLB Schedule Loaded.");

        // Clear Loading Spinner
        container.innerHTML = '';

        if (scheduleData.totalGames === 0) {
            container.innerHTML = '<div class="col-12 text-center"><h3>No games scheduled for this date.</h3></div>';
            return;
        }

        const games = scheduleData.dates[0].games;

        // --- CHECKPOINT 3: Loop Through Games ---
        for (const game of games) {
            const venueId = game.venue.id;
            const stadium = stadiums.find(s => s.id === venueId);

            // Create Card Wrapper
            const gameCard = document.createElement('div');
            gameCard.className = 'col-md-6 col-lg-4';
            
            // Team Info
            const awayId = game.teams.away.team.id;
            const homeId = game.teams.home.team.id;
            const awayName = game.teams.away.team.name;
            const homeName = game.teams.home.team.name;
            
            // Logos
            const awayLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${awayId}.svg`;
            const homeLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${homeId}.svg`;
            const gameTime = new Date(game.gameDate).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            // Default Weather State (Prevents crashing if weather fails)
            let weatherHtml = `<div class="text-muted p-3 text-center small">Weather data unavailable for this stadium.<br>(Venue ID: ${venueId})</div>`;
            
            // If we have stadium data, fetch weather
            if (stadium) {
                // Fetch weather (safely)
                const weather = await fetchGameWeather(stadium.lat, stadium.lon, game.gameDate);
                
                // Only calculate wind if we actually got weather data
                if (weather.temp !== '--') {
                    let windInfo = calculateWind(weather.windDir, stadium.bearing);

                    // ROOF LOGIC
                    let isRoofClosed = false;
                    if (stadium.dome) isRoofClosed = true;
                    else if (stadium.roof) {
                        if (weather.precip > 0.05 || weather.temp < 50 || weather.temp > 95) isRoofClosed = true;
                    }

                    if (isRoofClosed) {
                        windInfo = { text: "Roof Closed 🏟️", cssClass: "bg-secondary text-white", arrow: "" };
                        weather.windSpeed = 0; 
                    }

                    weatherHtml = `
                        <div class="weather-row row text-center">
                            <div class="col-4 border-end">
                                <div class="fw-bold">${weather.temp}°F</div>
                                <div class="small text-muted">Temp</div>
                            </div>
                            <div class="col-4 border-end">
                                <div class="fw-bold">${weather.precip > 0 ? Math.round(weather.precip * 100) + '%' : '0%'}</div>
                                <div class="small text-muted">Rain Risk</div>
                            </div>
                            <div class="col-4">
                                <div class="fw-bold">${weather.windSpeed} mph</div>
                                <div class="small text-muted">Wind</div>
                            </div>
                        </div>
                        <div class="text-center mt-3">
                            <span class="wind-badge ${windInfo.cssClass}">
                                ${windInfo.arrow} ${windInfo.text}
                            </span>
                        </div>
                    `;
                }
            }

            // Build the Card HTML
            gameCard.innerHTML = `
                <div class="card game-card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <span class="badge bg-secondary">${gameTime}</span>
                            <span class="stadium-name text-truncate" style="max-width: 180px;">${game.venue.name}</span>
                        </div>
                        
                        <div class="d-flex justify-content-between align-items-center mb-3 px-2">
                            <div class="text-center" style="width: 45%;">
                                <img src="${awayLogo}" alt="${awayName}" class="team-logo mb-2" onerror="this.style.display='none'">
                                <div class="fw-bold small lh-1">${awayName}</div>
                            </div>
                            <div class="text-muted small fw-bold">@</div>
                            <div class="text-center" style="width: 45%;">
                                <img src="${homeLogo}" alt="${homeName}" class="team-logo mb-2" onerror="this.style.display='none'">
                                <div class="fw-bold small lh-1">${homeName}</div>
                            </div>
                        </div>

                        ${weatherHtml}
                    </div>
                </div>
            `;
            container.appendChild(gameCard);
        }

    } catch (error) {
        console.error("❌ ERROR IN INIT:", error);
        // Display error on screen so you don't need console
        container.innerHTML = `
            <div class="col-12 text-center mt-5">
                <div class="alert alert-danger">
                    <h4>Something went wrong</h4>
                    <p>${error.message}</p>
                    <small>Check the browser console (F12) for details.</small>
                </div>
            </div>`;
    }
}

// 2. FETCH WEATHER
async function fetchGameWeather(lat, lon, gameDateIso) {
    const dateStr = gameDateIso.split('T')[0];
    const url = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}&start_date=${dateStr}&end_date=${dateStr}&hourly=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto`;

    try {
        const response = await fetch(url);
        const data = await response.json();
        const gameHour = new Date(gameDateIso).getHours();
        
        return {
            temp: Math.round(data.hourly.temperature_2m[gameHour]),
            precip: data.hourly.precipitation[gameHour], 
            windSpeed: Math.round(data.hourly.wind_speed_10m[gameHour]),
            windDir: data.hourly.wind_direction_10m[gameHour]
        };
    } catch (e) {
        console.error("⚠️ Weather fetch failed:", e);
        return { temp: '--', precip: 0, windSpeed: '--', windDir: 0 };
    }
}

// 3. CALCULATE WIND
function calculateWind(windDirection, stadiumBearing) {
    let diff = (windDirection - stadiumBearing + 360) % 360;
    
    if (diff >= 337.5 || diff < 22.5) return { text: "Blowing IN ⬇️", cssClass: "bg-in", arrow: "⬇" };
    if (diff >= 22.5 && diff < 67.5) return { text: "In from Right ↙️", cssClass: "bg-in", arrow: "↙" };
    if (diff >= 67.5 && diff < 112.5) return { text: "Cross (R to L) ⬅️", cssClass: "bg-cross", arrow: "⬅" };
    if (diff >= 112.5 && diff < 157.5) return { text: "Out to Left ↖️", cssClass: "bg-out", arrow: "↖" };
    if (diff >= 157.5 && diff < 202.5) return { text: "Blowing OUT ⬆️", cssClass: "bg-out", arrow: "⬆" };
    if (diff >= 202.5 && diff < 247.5) return { text: "Out to Right ↗️", cssClass: "bg-out", arrow: "↗" };
    if (diff >= 247.5 && diff < 292.5) return { text: "Cross (L to R) ➡️", cssClass: "bg-cross", arrow: "➡" };
    return { text: "In from Left ↘️", cssClass: "bg-in", arrow: "↘" };
}

// Run
init();
