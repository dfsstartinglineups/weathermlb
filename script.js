// ==========================================
// CONFIGURATION
// ==========================================
const DEFAULT_DATE = "2024-09-25"; 

// ==========================================
// 1. MAIN APP LOGIC
// ==========================================

async function init(dateToFetch) {
    console.log(`🚀 Starting App. Fetching games for: ${dateToFetch}`);
    
    const container = document.getElementById('games-container');
    const datePicker = document.getElementById('date-picker');

    if (datePicker) datePicker.value = dateToFetch;

    if (container) {
        container.innerHTML = `
            <div class="col-12 text-center mt-5 pt-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-3 text-muted">Analyzing hourly forecasts...</p>
            </div>`;
    }
    
    const MLB_API_URL = `https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=${dateToFetch}&hydrate=linescore,venue`;

    try {
        // --- STEP A: Load Data ---
        let stadiumResponse = await fetch('data/stadiums.json');
        if (!stadiumResponse.ok) {
            stadiumResponse = await fetch('stadiums.json');
        }
        const stadiums = await stadiumResponse.json();

        const scheduleResponse = await fetch(MLB_API_URL);
        const scheduleData = await scheduleResponse.json();

        container.innerHTML = '';

        if (scheduleData.totalGames === 0) {
            container.innerHTML = `
                <div class="col-12 text-center mt-5">
                    <div class="alert alert-light shadow-sm py-4">
                        <h4 class="text-muted">No games scheduled for ${dateToFetch}</h4>
                    </div>
                </div>`;
            return;
        }

        const games = scheduleData.dates[0].games;

        // --- STEP B: Loop Through Games ---
        for (const game of games) {
            const venueId = game.venue.id;
            const stadium = stadiums.find(s => s.id === venueId);

            // Create Card Wrapper
            const gameCard = document.createElement('div');
            gameCard.className = 'col-md-6 col-lg-4';
            
            // Basic Info
            const awayId = game.teams.away.team.id;
            const homeId = game.teams.home.team.id;
            const awayName = game.teams.away.team.name;
            const homeName = game.teams.home.team.name;
            const awayLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${awayId}.svg`;
            const homeLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${homeId}.svg`;
            const gameTime = new Date(game.gameDate).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

            // Default State
            let weatherHtml = `<div class="text-muted p-3 text-center small">Weather data unavailable.<br><span class="badge bg-light text-dark">Venue ID: ${venueId}</span></div>`;
            
            if (stadium) {
                // Fetch Weather Data
                const weather = await fetchGameWeather(stadium.lat, stadium.lon, game.gameDate);
                
                if (weather.temp !== '--') {
                    // Wind Logic
                    let windInfo = calculateWind(weather.windDir, stadium.bearing);
                    
                    // Roof Logic
                    let isRoofClosed = false;
                    if (stadium.dome) isRoofClosed = true;
                    else if (stadium.roof) {
                        // Use maxPrecipChance to decide roof status, not just current
                        if (weather.maxPrecipChance > 30 || weather.temp < 50 || weather.temp > 95) isRoofClosed = true;
                    }

                    if (isRoofClosed) {
                        windInfo = { text: "Roof Closed 🏟️", cssClass: "bg-secondary text-white", arrow: "" };
                        weather.windSpeed = 0; 
                    }

                    // --- HORIZONTAL RAIN HEAT MAP ---
                    let hourlyHtml = '';
                    
                    if (isRoofClosed) {
                        hourlyHtml = `<div class="text-center mt-3"><small class="text-muted">Indoor Conditions</small></div>`;
                    } else if (weather.hourly && weather.hourly.length > 0) {
                        
                        // 1. Build segments
                        const segments = weather.hourly.map(h => {
                            let colorClass = 'risk-low'; 
                            if (h.precipChance >= 50) colorClass = 'risk-high'; // Red
                            else if (h.precipChance >= 15) colorClass = 'risk-med'; // Yellow
                            
                            return `<div class="rain-segment ${colorClass}" title="${h.precipChance}% chance of rain"></div>`;
                        }).join('');
                        
                        // 2. Build time labels
                        const labels = weather.hourly.map(h => {
                             let timeLabel = new Date(`2000-01-01T${h.hour}:00:00`)
                                .toLocaleTimeString([], {hour: 'numeric'})
                                .replace(':00 ', '').replace(' PM','p').replace(' AM','a');
                             return `<div class="rain-time-label">${timeLabel}</div>`;
                        }).join('');

                        hourlyHtml = `
                            <div class="rain-container">
                                <div class="d-flex justify-content-between mb-1">
                                    <span style="font-size: 0.65rem; color: #adb5bd; font-weight: bold;">HOURLY RAIN RISK</span>
                                </div>
                                <div class="rain-track">
                                    ${segments}
                                </div>
                                <div class="rain-labels">
                                    ${labels}
                                </div>
                            </div>
                        `;
                    }

                    // --- DISPLAY ---
                    // Important: Use 'maxPrecipChance' for the main number so it matches the red bars
                    // If roof is closed, force 0%
                    const displayRain = isRoofClosed ? 0 : weather.maxPrecipChance;

                    weatherHtml = `
                        <div class="weather-row row text-center">
                            <div class="col-4 border-end">
                                <div class="fw-bold">${weather.temp}°F</div>
                                <div class="small text-muted">Temp</div>
                            </div>
                            <div class="col-4 border-end">
                                <div class="fw-bold text-primary">${displayRain}%</div>
                                <div class="small text-muted">Max Rain</div>
                            </div>
                            <div class="col-4">
                                <div class="fw-bold">${weather.windSpeed} <span style="font-size:0.7em">mph</span></div>
                                <div class="small text-muted">Wind</div>
                            </div>
                        </div>
                        
                        <div class="text-center mt-3 mb-2">
                            <span class="wind-badge ${windInfo.cssClass}">
                                ${windInfo.arrow} ${windInfo.text}
                            </span>
                        </div>

                        ${hourlyHtml}
                    `;
                }
            }

            // Build Card HTML
            gameCard.innerHTML = `
                <div class="card game-card h-100">
                    <div class="card-body pb-2">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <span class="badge bg-light text-dark border">${gameTime}</span>
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
        console.error("❌ ERROR:", error);
        container.innerHTML = `<div class="col-12 text-center mt-5"><div class="alert alert-danger">${error.message}</div></div>`;
    }
}

// ==========================================
// 2. HELPER FUNCTIONS
// ==========================================

async function fetchGameWeather(lat, lon, gameDateIso) {
    const dateStr = gameDateIso.split('T')[0];
    const today = new Date().toISOString().split('T')[0];
    const isHistorical = dateStr < today; 

    // Determine API Endpoint
    let url = "";
    if (isHistorical || dateStr === "2024-09-25") {
         url = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}&start_date=${dateStr}&end_date=${dateStr}&hourly=temperature_2m,precipitation,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto`;
    } else {
         url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&hourly=temperature_2m,precipitation_probability,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto&start_date=${dateStr}&end_date=${dateStr}`;
    }

    try {
        const response = await fetch(url);
        const data = await response.json();
        const gameHour = new Date(gameDateIso).getHours();
        
        // --- Helper to normalize rain data ---
        // Converts either raw inches OR raw probability into a clean 0-100% integer
        const normalizePrecip = (index) => {
            let chance = 0;
            if (data.hourly.precipitation_probability) {
                // Forecast API: Direct percentage (0-100)
                chance = data.hourly.precipitation_probability[index];
            } else if (data.hourly.precipitation) {
                // Historical API: Inches (0.00, 0.05, etc.)
                const amount = data.hourly.precipitation[index];
                if (amount >= 0.10) chance = 80;      // Heavy
                else if (amount >= 0.05) chance = 60; // Moderate
                else if (amount >= 0.01) chance = 30; // Light
                else chance = 0;
            }
            return chance;
        };

        // --- Extract Hourly Slice (Hour-1 to Hour+4) ---
        const hourlySlice = [];
        let maxChanceInWindow = 0;

        for (let i = gameHour - 1; i <= gameHour + 4; i++) {
            if (i >= 0 && i < 24) {
                let chance = normalizePrecip(i);
                
                // Track the HIGHEST chance of rain during the game window
                // (Only count the actual game hours: Start to Start+3)
                if (i >= gameHour && i <= gameHour + 3) {
                    if (chance > maxChanceInWindow) maxChanceInWindow = chance;
                }

                hourlySlice.push({
                    hour: i,
                    precipChance: chance
                });
            }
        }

        const temps = data.hourly.temperature_2m;
        const winds = data.hourly.wind_speed_10m;
        const dirs = data.hourly.wind_direction_10m;

        return {
            temp: Math.round(temps[gameHour]),
            maxPrecipChance: maxChanceInWindow, // Used for main display
            windSpeed: Math.round(winds[gameHour]),
            windDir: dirs[gameHour],
            hourly: hourlySlice 
        };
    } catch (e) {
        console.error("⚠️ Weather fetch failed:", e);
        return { temp: '--', hourly: [] };
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
// 3. LISTENERS
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    init(DEFAULT_DATE);

    const datePicker = document.getElementById('date-picker');
    const refreshBtn = document.getElementById('refresh-btn');

    if (refreshBtn && datePicker) {
        refreshBtn.addEventListener('click', () => {
            if (datePicker.value) init(datePicker.value);
        });
        datePicker.addEventListener('change', (e) => {
            if (e.target.value) init(e.target.value);
        });
    }
});
