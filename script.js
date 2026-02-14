// ==========================================
// CONFIGURATION
// ==========================================

// The date to show when the page first loads.
// Once the 2026 season starts, you can change this to: new Date().toISOString().split('T')[0]
const DEFAULT_DATE = "2024-09-25"; 

// ==========================================
// 1. MAIN APP LOGIC
// ==========================================

async function init(dateToFetch) {
    console.log(`🚀 Starting App. Fetching games for: ${dateToFetch}`);
    
    // UI References
    const container = document.getElementById('games-container');
    const datePicker = document.getElementById('date-picker');
    const displayDate = document.getElementById('current-date');

    // 1. Update UI Elements
    if (datePicker) datePicker.value = dateToFetch;
    if (displayDate) displayDate.innerText = "Loading...";

    // 2. Show Loading Spinner
    container.innerHTML = `
        <div class="col-12 text-center mt-5 pt-5">
            <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;"></div>
            <p class="mt-3 text-muted">Scouting the skies...</p>
        </div>`;
    
    // 3. Construct API URL
    const MLB_API_URL = `https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=${dateToFetch}&hydrate=linescore,venue`;

    try {
        // --- STEP A: Load Stadium Data ---
        // Try looking in 'data/' folder first, fallback to root if needed
        let stadiumResponse = await fetch('data/stadiums.json');
        if (!stadiumResponse.ok) {
            console.warn("⚠️ data/stadiums.json not found. Trying root folder...");
            stadiumResponse = await fetch('stadiums.json');
        }
        
        if (!stadiumResponse.ok) throw new Error("Could not load stadium data.");
        const stadiums = await stadiumResponse.json();

        // --- STEP B: Load MLB Schedule ---
        const scheduleResponse = await fetch(MLB_API_URL);
        const scheduleData = await scheduleResponse.json();

        // Clear Spinner
        container.innerHTML = '';

        // Check if any games exist
        if (scheduleData.totalGames === 0) {
            container.innerHTML = `
                <div class="col-12 text-center mt-5">
                    <div class="alert alert-light shadow-sm" style="display:inline-block; padding: 20px 40px;">
                        <h4 class="text-muted mb-0">No games scheduled for ${dateToFetch}</h4>
                        <p class="small text-muted mt-2">Try selecting a different date from the picker above.</p>
                    </div>
                </div>`;
            return;
        }

        const games = scheduleData.dates[0].games;

        // --- STEP C: Loop Through Each Game ---
        for (const game of games) {
            const venueId = game.venue.id;
            const stadium = stadiums.find(s => s.id === venueId);

            // Create Card Wrapper
            const gameCard = document.createElement('div');
            gameCard.className = 'col-md-6 col-lg-4';
            
            // Team Data
            const awayId = game.teams.away.team.id;
            const homeId = game.teams.home.team.id;
            const awayName = game.teams.away.team.name;
            const homeName = game.teams.home.team.name;
            
            // Official Logos
            const awayLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${awayId}.svg`;
            const homeLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${homeId}.svg`;
            
            // Game Time
            const gameTime = new Date(game.gameDate).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            // Default Weather State (in case fetch fails or stadium missing)
            let weatherHtml = `<div class="text-muted p-3 text-center small">Weather data unavailable.<br><span class="badge bg-light text-dark">Venue ID: ${venueId}</span></div>`;
            
            // If we have stadium data, fetch weather
            if (stadium) {
                // Fetch Historical or Forecast Weather
                const weather = await fetchGameWeather(stadium.lat, stadium.lon, game.gameDate);
                
                // Only proceed if we got a valid temp
                if (weather.temp !== '--') {
                    // Calculate Wind Vector
                    let windInfo = calculateWind(weather.windDir, stadium.bearing);

                    // --- ROOF LOGIC ---
                    let isRoofClosed = false;
                    // 1. Permanent Dome?
                    if (stadium.dome) isRoofClosed = true;
                    // 2. Retractable Roof + Bad Weather?
                    else if (stadium.roof) {
                        if (weather.precip > 0.05 || weather.temp < 50 || weather.temp > 95) {
                            isRoofClosed = true;
                        }
                    }

                    // Override if Roof Closed
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
                                <div class="small text-muted">Rain</div>
                            </div>
                            <div class="col-4">
                                <div class="fw-bold">${weather.windSpeed} <span style="font-size:0.7em">mph</span></div>
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

            // Build HTML
            gameCard.innerHTML = `
                <div class="card game-card h-100">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <span class="badge bg-light text-dark border">${gameTime}</span>
                            <span class="stadium-name text-truncate" style="max-width: 180px;" title="${game.venue.name}">${game.venue.name}</span>
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
        console.error("❌ ERROR:", error);
        container.innerHTML = `
            <div class="col-12 text-center mt-5">
                <div class="alert alert-danger d-inline-block">
                    <h4>Unable to load data</h4>
                    <p class="mb-0">${error.message}</p>
                    <small>Check console for details.</small>
                </div>
            </div>`;
    }
}

// ==========================================
// 2. HELPER FUNCTIONS
// ==========================================

async function fetchGameWeather(lat, lon, gameDateIso) {
    // Open-Meteo works for both Historical (Archive) and Future (Forecast)
    // We need to check if the date is in the past or future to choose the right API endpoint?
    // Actually, for simplicity, the Archive API works for past dates. 
    // For future dates, we would need the Forecast API.
    // For this demo, we assume Historical. 
    
    // NOTE: If you want this to work for LIVE games in 2025, you need to switch logic here:
    // If date < today -> Use Archive API
    // If date >= today -> Use Forecast API
    
    const dateStr = gameDateIso.split('T')[0];
    const today = new Date().toISOString().split('T')[0];
    
    let url = "";
    
    // Simple logic: If the requested date is older than 5 days ago, use Archive.
    // Otherwise use Forecast.
    const isHistorical = dateStr < today; // Rough check

    if (isHistorical || dateStr === "2024-09-25") {
         url = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}&start_date=${dateStr}&end_date=${dateStr}&hourly=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto`;
    } else {
         // Forecast API for current/future games
         url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&hourly=temperature_2m,precipitation_probability,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto&start_date=${dateStr}&end_date=${dateStr}`;
    }

    try {
        const response = await fetch(url);
        const data = await response.json();
        
        // Find the hour nearest to game time
        const gameHour = new Date(gameDateIso).getHours();
        
        // Map API data (Forecast API uses 'precipitation_probability', Archive uses 'precipitation')
        const temps = data.hourly.temperature_2m;
        const winds = data.hourly.wind_speed_10m;
        const dirs = data.hourly.wind_direction_10m;
        
        // Handle Precip difference
        let precipVal = 0;
        if (data.hourly.precipitation) precipVal = data.hourly.precipitation[gameHour];
        else if (data.hourly.precipitation_probability) precipVal = data.hourly.precipitation_probability[gameHour] / 100;

        return {
            temp: Math.round(temps[gameHour]),
            precip: precipVal, 
            windSpeed: Math.round(winds[gameHour]),
            windDir: dirs[gameHour]
        };
    } catch (e) {
        console.error("⚠️ Weather fetch failed:", e);
        return { temp: '--', precip: 0, windSpeed: '--', windDir: 0 };
    }
}

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

// ==========================================
// 3. INITIALIZATION & EVENT LISTENERS
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    // A. Start with default date
    init(DEFAULT_DATE);

    // B. Add Event Listeners for Date Picker
    const datePicker = document.getElementById('date-picker');
    const refreshBtn = document.getElementById('refresh-btn');

    if (refreshBtn && datePicker) {
        // Load when button clicked
        refreshBtn.addEventListener('click', () => {
            if (datePicker.value) init(datePicker.value);
        });

        // Load when date changes (optional, but nice UX)
        datePicker.addEventListener('change', (e) => {
            if (e.target.value) init(e.target.value);
        });
    }
});
