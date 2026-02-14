// CONFIGURATION
const TEST_DATE = "2024-09-25"; 
const MLB_API_URL = `https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=${TEST_DATE}&hydrate=linescore,venue`;

// 1. MAIN FUNCTION: START THE APP
async function init() {
    document.getElementById('current-date').innerText = new Date(TEST_DATE).toDateString();
    const container = document.getElementById('games-container');
    
    try {
        // Step A: Load Stadium Data
        const stadiumResponse = await fetch('data/stadiums.json');
        const stadiums = await stadiumResponse.json();

        // Step B: Load MLB Schedule
        const scheduleResponse = await fetch(MLB_API_URL);
        const scheduleData = await scheduleResponse.json();

        // Clear Loading Spinner
        container.innerHTML = '';

        if (scheduleData.totalGames === 0) {
            container.innerHTML = '<div class="col-12 text-center"><h3>No games scheduled for this date.</h3></div>';
            return;
        }

        const games = scheduleData.dates[0].games;

        // Step C: Process Each Game
        for (const game of games) {
            const venueId = game.venue.id;
            const stadium = stadiums.find(s => s.id === venueId);

            // Create Card HTML Wrapper
            const gameCard = document.createElement('div');
            gameCard.className = 'col-md-6 col-lg-4';
            
            // --- Get Team IDs and Logos ---
            const awayId = game.teams.away.team.id;
            const homeId = game.teams.home.team.id;
            const awayName = game.teams.away.team.name;
            const homeName = game.teams.home.team.name;
            
            const awayLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${awayId}.svg`;
            const homeLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${homeId}.svg`;
            const gameTime = new Date(game.gameDate).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            // --- BUG FIX: Define default values HERE, before the 'if' block ---
            let weatherHtml = `<div class="text-muted p-3 text-center small">Weather data unavailable for this stadium.<br>(Venue ID: ${venueId})</div>`;
            
            // Define a default 'windInfo' so the code doesn't crash if stadium is missing
            let windInfo = { text: "N/A", cssClass: "bg-secondary text-white", arrow: "-" };

            // If we have stadium data, fetch weather
            if (stadium) {
                const weather = await fetchGameWeather(stadium.lat, stadium.lon, game.gameDate);
                
                // Update windInfo with real calculations
                windInfo = calculateWind(weather.windDir, stadium.bearing);

                // Roof Logic
                let isRoofClosed = false;
                if (stadium.dome) {
                    isRoofClosed = true; 
                } else if (stadium.roof) {
                    if (weather.precip > 0.05 || weather.temp < 50 || weather.temp > 95) {
                        isRoofClosed = true;
                    }
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
        console.error("Error fetching data:", error);
        container.innerHTML = `<div class="alert alert-danger">Error loading data. Check console for details.</div>`;
    }
}

// 2. FETCH WEATHER (Using Open-Meteo Historical Archive)
async function fetchGameWeather(lat, lon, gameDateIso) {
    // Open-Meteo requires YYYY-MM-DD
    const dateStr = gameDateIso.split('T')[0];
    
    // Construct URL for Historical Weather
    const url = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}&start_date=${dateStr}&end_date=${dateStr}&hourly=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto`;

    try {
        const response = await fetch(url);
        const data = await response.json();
        
        // Find the hour nearest to game time
        const gameHour = new Date(gameDateIso).getHours();
        
        // Open-Meteo returns 0-23 hours index mapped perfectly
        // Use simpler variable names for clarity
        const temps = data.hourly.temperature_2m;
        const precips = data.hourly.precipitation;
        const winds = data.hourly.wind_speed_10m;
        const dirs = data.hourly.wind_direction_10m;

        return {
            temp: Math.round(temps[gameHour]),
            precip: precips[gameHour], 
            windSpeed: Math.round(winds[gameHour]),
            windDir: dirs[gameHour]
        };
    } catch (e) {
        console.error("Weather fetch failed", e);
        return { temp: '--', precip: 0, windSpeed: '--', windDir: 0 };
    }
}
