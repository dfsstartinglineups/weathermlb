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

            // Create Card HTML
            const gameCard = document.createElement('div');
            gameCard.className = 'col-md-6 col-lg-4';
            
            // Basic Game Info
            const awayTeam = game.teams.away.team.name;
            const homeTeam = game.teams.home.team.name;
            const gameTime = new Date(game.gameDate).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            let weatherHtml = `<div class="text-muted p-3">Weather data unavailable for this stadium.</div>`;

            // If we have stadium data, fetch weather
            if (stadium) {
                const weather = await fetchGameWeather(stadium.lat, stadium.lon, game.gameDate);
                let windInfo = calculateWind(weather.windDir, stadium.bearing);
                
                // ROOF LOGIC:
                // If the stadium has a roof, check if we should assume it's closed.
                // Logic: If Precip > 0.1 inch OR Temp < 50F OR Temp > 95F -> Assume Closed
                let isRoofClosed = false;
                
                if (stadium.dome) {
                    isRoofClosed = true; // Tropicana Field is always a dome
                } else if (stadium.roof) {
                    if (weather.precip > 0.05 || weather.temp < 50 || weather.temp > 95) {
                        isRoofClosed = true;
                    }
                }
                
                // Override display if roof is closed
                if (isRoofClosed) {
                    windInfo = { text: "Roof Closed 🏟️", cssClass: "bg-secondary text-white", arrow: "" };
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
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <span class="badge bg-secondary">${gameTime}</span>
                            <span class="stadium-name">${game.venue.name}</span>
                        </div>
                        <h5 class="card-title text-center mb-3">
                            ${awayTeam} <span class="text-muted">at</span> ${homeTeam}
                        </h5>
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
        const index = gameHour; // Open-Meteo returns 0-23 hours index mapped perfectly

        return {
            temp: Math.round(data.hourly.temperature_2m[index]),
            precip: data.hourly.precipitation[index], // In inches (archive data)
            windSpeed: Math.round(data.hourly.wind_speed_10m[index]),
            windDir: data.hourly.wind_direction_10m[index]
        };
    } catch (e) {
        console.error("Weather fetch failed", e);
        return { temp: '--', precip: 0, windSpeed: '--', windDir: 0 };
    }
}

// 3. CALCULATE WIND DIRECTION (Corrected Logic)
function calculateWind(windDirection, stadiumBearing) {
    // windDirection: Where wind is coming FROM (0=N, 90=E)
    // stadiumBearing: Angle from Home Plate to Center Field
    
    // Calculate difference
    let diff = (windDirection - stadiumBearing + 360) % 360;

    // Determine Logic
    // 0 deg diff = Wind coming from Center Field direction (Blowing IN)
    // 180 deg diff = Wind coming from Home Plate direction (Blowing OUT)
    
    // Positive Diff (0-180) means wind is to the RIGHT of Center Field
    // Negative Diff (180-360) means wind is to the LEFT of Center Field
    
    if (diff >= 337.5 || diff < 22.5) {
        return { text: "Blowing IN ⬇️", cssClass: "bg-in", arrow: "⬇" };
    } else if (diff >= 22.5 && diff < 67.5) {
        return { text: "In from Right ↙️", cssClass: "bg-in", arrow: "↙" }; // FIXED
    } else if (diff >= 67.5 && diff < 112.5) {
        return { text: "Cross (R to L) ⬅️", cssClass: "bg-cross", arrow: "⬅" };
    } else if (diff >= 112.5 && diff < 157.5) {
        return { text: "Out to Left ↖️", cssClass: "bg-out", arrow: "↖" };
    } else if (diff >= 157.5 && diff < 202.5) {
        return { text: "Blowing OUT ⬆️", cssClass: "bg-out", arrow: "⬆" };
    } else if (diff >= 202.5 && diff < 247.5) {
        return { text: "Out to Right ↗️", cssClass: "bg-out", arrow: "↗" };
    } else if (diff >= 247.5 && diff < 292.5) {
        return { text: "Cross (L to R) ➡️", cssClass: "bg-cross", arrow: "➡" };
    } else { // 292.5 to 337.5
        return { text: "In from Left ↘️", cssClass: "bg-in", arrow: "↘" }; // FIXED
    }
}
// Run the script
init();
