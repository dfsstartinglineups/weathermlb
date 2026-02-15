// ==========================================
// CONFIGURATION
// ==========================================
const DEFAULT_DATE = new Date().toLocaleDateString('en-CA');

// Global State
let ALL_GAMES_DATA = []; 

// ==========================================
// 1. MAIN APP LOGIC
// ==========================================

async function init(dateToFetch) {
    console.log(`🚀 Starting App. Fetching games for: ${dateToFetch}`);
    
    const container = document.getElementById('games-container');
    const datePicker = document.getElementById('date-picker');
    
    // Reset State
    ALL_GAMES_DATA = [];
    if (datePicker) datePicker.value = dateToFetch;

    if (container) {
        container.innerHTML = `
            <div class="col-12 text-center mt-5 pt-5">
                <div class="spinner-border text-primary" role="status"></div>
                <p class="mt-3 text-muted" id="loading-text">Loading Schedule...</p>
            </div>`;
    }
    
    const MLB_API_URL = `https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=${dateToFetch}&hydrate=linescore,venue`;

    try {
        let stadiumResponse = await fetch('data/stadiums.json');
        if (!stadiumResponse.ok) stadiumResponse = await fetch('stadiums.json');
        const stadiums = await stadiumResponse.json();

        const scheduleResponse = await fetch(MLB_API_URL);
        const scheduleData = await scheduleResponse.json();

        if (scheduleData.totalGames === 0) {
            container.innerHTML = `
                <div class="col-12 text-center mt-5">
                    <div class="alert alert-light shadow-sm py-4">
                        <h4 class="text-muted">No games scheduled for ${dateToFetch}</h4>
                        <p class="small text-muted mb-0">Spring Training starts Feb 20!</p>
                    </div>
                </div>`;
            return;
        }

        const rawGames = scheduleData.dates[0].games;
        const totalGames = rawGames.length;
        
        // Loop through games
        for (let i = 0; i < totalGames; i++) {
            const game = rawGames[i];
            document.getElementById('loading-text').innerText = `Analyzing game ${i+1} of ${totalGames}...`;

            const venueId = game.venue.id;
            const stadium = stadiums.find(s => s.id === venueId);
            
            let weatherData = null;
            let windData = null;
            let isRoofClosed = false;

            if (stadium) {
                weatherData = await fetchGameWeather(stadium.lat, stadium.lon, game.gameDate);
                
                if (weatherData.status !== "too_early" && weatherData.temp !== '--') {
                    windData = calculateWind(weatherData.windDir, stadium.bearing);
                    
                    if (stadium.dome) isRoofClosed = true;
                    else if (stadium.roof) {
                        if (weatherData.maxPrecipChance > 30 || weatherData.temp < 50 || weatherData.temp > 95) isRoofClosed = true;
                    }
                    if (isRoofClosed) {
                        windData = { text: "Roof Closed", cssClass: "bg-secondary text-white", arrow: "" };
                        weatherData.windSpeed = 0; 
                    }
                }
            }

            ALL_GAMES_DATA.push({
                gameRaw: game,
                stadium: stadium,
                weather: weatherData,
                wind: windData,
                roof: isRoofClosed
            });
        }

        renderGames();

    } catch (error) {
        console.error("❌ ERROR:", error);
        container.innerHTML = `<div class="col-12 text-center mt-5"><div class="alert alert-danger">${error.message}</div></div>`;
    }
}

// ==========================================
// 2. RENDERING ENGINE
// ==========================================

function renderGames() {
    const container = document.getElementById('games-container');
    container.innerHTML = '';

    const searchText = document.getElementById('team-search').value.toLowerCase();
    const sortMode = document.getElementById('sort-filter').value;
    const risksOnly = document.getElementById('risk-only').checked;

    let filteredGames = ALL_GAMES_DATA.filter(item => {
        const g = item.gameRaw;
        const teams = (g.teams.away.team.name + " " + g.teams.home.team.name).toLowerCase();
        if (!teams.includes(searchText)) return false;

        if (risksOnly) {
            if (!item.weather || item.weather.temp === '--') return false; 
            const isRainy = item.weather.maxPrecipChance >= 30;
            const isWindy = item.weather.windSpeed >= 12;
            const isExtremeTemp = item.weather.temp <= 45 || item.weather.temp >= 90;
            if (!isRainy && !isWindy && !isExtremeTemp) return false;
        }
        return true;
    });

    filteredGames.sort((a, b) => {
        const aValid = a.weather && a.weather.temp !== '--';
        const bValid = b.weather && b.weather.temp !== '--';
        if (!aValid && bValid) return 1;
        if (aValid && !bValid) return -1;

        if (sortMode === 'wind') return (b.weather?.windSpeed || 0) - (a.weather?.windSpeed || 0);
        if (sortMode === 'rain') return (b.weather?.maxPrecipChance || 0) - (a.weather?.maxPrecipChance || 0);
        if (sortMode === 'temp') return (b.weather?.temp || 0) - (a.weather?.temp || 0);
        if (sortMode === 'humidity') return (b.weather?.humidity || 0) - (a.weather?.humidity || 0); // NEW SORT
        
        return new Date(a.gameRaw.gameDate) - new Date(b.gameRaw.gameDate);
    });

    if (filteredGames.length === 0) {
        container.innerHTML = `<div class="col-12 text-center py-5 text-muted">No games match your filters.</div>`;
        return;
    }

    filteredGames.forEach(item => {
        container.appendChild(createGameCard(item));
    });
}

function createGameCard(data) {
    const game = data.gameRaw;
    const stadium = data.stadium;
    const weather = data.weather;
    const windInfo = data.wind;
    const isRoofClosed = data.roof;

    // --- UPDATED: Risk Border Logic (Now starts at 30%) ---
    let borderClass = ""; 
    
    if (weather && !isRoofClosed) {
        if (weather.maxPrecipChance >= 70) {
            borderClass = "border-danger border-3"; // Red Border (High Risk)
        } else if (weather.maxPrecipChance >= 30) {
            borderClass = "border-warning border-3"; // Yellow Border (Medium Risk)
        }
    }

    const gameCard = document.createElement('div');
    gameCard.className = 'col-md-6 col-lg-4 animate-card';

    // Basic Info
    const awayId = game.teams.away.team.id;
    const homeId = game.teams.home.team.id;
    const awayName = game.teams.away.team.name;
    const homeName = game.teams.home.team.name;
    const awayLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${awayId}.svg`;
    const homeLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${homeId}.svg`;
    const gameTime = new Date(game.gameDate).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

    let weatherHtml = `<div class="text-muted p-3 text-center small">Weather data unavailable.<br><span class="badge bg-light text-dark">Venue ID: ${game.venue.id}</span></div>`;

    if (stadium && weather) {
        if (weather.status === "too_early") {
            weatherHtml = `
                <div class="text-center p-4">
                    <h5 class="text-muted">🔭 Too Early to Forecast</h5>
                    <p class="small text-muted mb-0">Forecasts available ~14 days out.</p>
                </div>`;
        } else if (weather.temp !== '--') {
            const analysisText = generateMatchupAnalysis(weather, windInfo, isRoofClosed);
            const displayRain = isRoofClosed ? 0 : weather.maxPrecipChance;
            
            const radarUrl = `https://embed.windy.com/embed2.html?lat=${stadium.lat}&lon=${stadium.lon}&detailLat=${stadium.lat}&detailLon=${stadium.lon}&width=650&height=450&zoom=11&level=surface&overlay=rain&product=ecmwf&menu=&message=&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=mph&metricTemp=%C2%B0F&radarRange=-1`;

            let hourlyHtml = '';
            if (isRoofClosed) {
                hourlyHtml = `<div class="text-center mt-3"><small class="text-muted">Indoor Conditions</small></div>`;
            } else if (weather.hourly && weather.hourly.length > 0) {
                const segments = weather.hourly.map(h => {
                    let colorClass = 'risk-low'; 
                    if (h.precipChance >= 50) colorClass = 'risk-high'; 
                    else if (h.precipChance >= 30) colorClass = 'risk-med'; // Updated to 30%
                    const textLabel = h.precipChance > 0 ? `${h.precipChance}%` : '';
                    return `<div class="rain-segment ${colorClass}" title="${h.precipChance}% chance of rain">${textLabel}</div>`;
                }).join('');
                
                const labels = weather.hourly.map(h => {
                    const ampm = h.hour >= 12 ? 'p' : 'a';
                    const hour12 = h.hour % 12 || 12; 
                    return `<div class="rain-time-label">${hour12}${ampm}</div>`;
                }).join('');

                hourlyHtml = `
                    <div class="rain-container">
                        <div class="d-flex justify-content-between mb-1">
                            <span style="font-size: 0.65rem; color: #adb5bd; font-weight: bold;">HOURLY RAIN RISK</span>
                        </div>
                        <div class="rain-track">${segments}</div>
                        <div class="rain-labels">${labels}</div>
                    </div>`;
            }

            weatherHtml = `
                <div class="weather-row row text-center align-items-center">
                    <div class="col-3 border-end">
                        <div class="fw-bold">${weather.temp}°F</div>
                        <div class="small text-muted">Temp</div>
                    </div>
                    <div class="col-3 border-end">
                        <div class="fw-bold text-dark">${weather.humidity}%</div>
                        <div class="small text-muted">Hum</div>
                    </div>
                    <div class="col-3 border-end">
                        <div class="fw-bold text-primary">${displayRain}%</div>
                        <div class="small text-muted">Rain</div>
                    </div>
                    <div class="col-3">
                        <div class="fw-bold mb-1">${weather.windSpeed} <span style="font-size:0.7em">mph</span></div>
                        <span class="wind-badge ${windInfo.cssClass}" style="font-size: 0.6rem; white-space: nowrap; display: inline-block; padding: 2px 6px;">
                            ${windInfo.arrow}
                        </span>
                    </div>
                </div>
                ${hourlyHtml}
                <div class="text-center mt-3">
                    <button class="btn btn-sm btn-outline-primary w-100" onclick="showRadar('${radarUrl}', '${game.venue.name}')">
                        🗺️ View Radar Map
                    </button>
                </div>
                <div class="analysis-box">
                    <span class="analysis-title">✨ Weather Impact</span>
                    ${analysisText}
                </div>`;
        }
    }

    // Apply the border class here
    gameCard.innerHTML = `
        <div class="card game-card h-100 ${borderClass}">
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
        </div>`;
    
    return gameCard;
}

// ==========================================
// 3. LISTENERS
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    init(DEFAULT_DATE);

    document.getElementById('team-search').addEventListener('input', renderGames);
    document.getElementById('sort-filter').addEventListener('change', renderGames);
    document.getElementById('risk-only').addEventListener('change', renderGames);

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

// ==========================================
// 4. HELPER FUNCTIONS
// ==========================================

window.showRadar = function(url, venueName) {
    const modalTitle = document.querySelector('#radarModal .modal-title');
    const iframe = document.getElementById('radarFrame');
    if(modalTitle) modalTitle.innerText = `Radar: ${venueName}`;
    if(iframe) iframe.src = url;
    const myModal = new bootstrap.Modal(document.getElementById('radarModal'));
    myModal.show();
}

function generateMatchupAnalysis(weather, windInfo, isRoofClosed) {
    if (isRoofClosed) return "Roof closed. Controlled environment with zero weather impact.";

    let notes = [];

    // 1. Humidity Analysis (Based on your Chart)
    if (weather.humidity <= 30) {
        notes.push("🌵 <b>Dry Air (<30%):</b> Sharp breaking balls (Pitcher Adv), but the ball travels up to 4.5ft farther (Hitter Adv).");
    } else if (weather.humidity >= 70) {
        notes.push("💧 <b>High Humidity (>70%):</b> Breaking balls hang/flatten (Hitter Adv), but the ball travels shorter distances (Pitcher Adv).");
    }

    // 2. Temp Analysis
    if (weather.temp >= 85) {
        notes.push("🔥 <b>Hitter Friendly:</b> High temps reduce air density, helping fly balls carry.");
    } else if (weather.temp <= 50) {
        notes.push("❄️ <b>Pitcher Friendly:</b> Cold, dense air suppresses ball flight and scoring.");
    }

    // 3. Wind Analysis (Only if speed > 8mph)
    if (weather.windSpeed >= 8) {
        const dir = windInfo.text;
        
        // Power Boosts
        if (dir.includes("Blowing OUT")) {
            notes.push("🚀 <b>Home Runs:</b> Strong wind blowing out creates ideal hitting conditions.");
        } else if (dir.includes("Out to Right")) {
            notes.push("↗️ <b>Lefty Advantage:</b> Wind blowing out to Right favors <b>Left-Handed</b> power.");
        } else if (dir.includes("Out to Left")) {
            notes.push("↖️ <b>Righty Advantage:</b> Wind blowing out to Left favors <b>Right-Handed</b> power.");
        } 
        
        // Power Suppression
        else if (dir.includes("Blowing IN")) {
            notes.push("🛑 <b>Suppressed:</b> Wind blowing in will knock down fly balls. Advantage pitchers.");
        } else if (dir.includes("In from Right")) {
            notes.push("📉 <b>Lefty Nightmare:</b> Wind blowing in from Right knocks down Lefty power.");
        } else if (dir.includes("In from Left")) {
            notes.push("📉 <b>Righty Nightmare:</b> Wind blowing in from Left knocks down Righty power.");
        } 
        
        // Neutral/Tricky
        else if (dir.includes("Cross")) {
            notes.push("↔️ <b>Tricky:</b> Crosswinds may affect outfield defense and breaking balls.");
        }
    }

    // 4. Rain Analysis
    if (weather.maxPrecipChance >= 70) {
        notes.push("⚠️ <b>Delay Risk:</b> High probability of rain delay or postponement.");
    } else if (weather.maxPrecipChance >= 40) {
        notes.push("⚠️ <b>Delay Risk:</b> Scattered storms could interrupt play.");
    }

    if (notes.length === 0) {
        return "✅ <b>Neutral:</b> Fair weather conditions. No significant advantage.";
    }

    return notes.join("<br>");
}

async function fetchGameWeather(lat, lon, gameDateIso) {
    const dateStr = gameDateIso.split('T')[0];
    const today = new Date().toLocaleDateString('en-CA'); 
    const isHistorical = dateStr < today; 
    const daysDiff = (new Date(dateStr) - new Date(today)) / (1000 * 60 * 60 * 24);

    if (!isHistorical && daysDiff > 16) return { status: "too_early", temp: '--' };

    let url = "";
    // ADDED relative_humidity_2m TO ALL URLS
    if (isHistorical || dateStr === "2024-09-25") {
         url = `https://archive-api.open-meteo.com/v1/archive?latitude=${lat}&longitude=${lon}&start_date=${dateStr}&end_date=${dateStr}&hourly=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto`;
    } 
    else if (daysDiff <= 3) {
         url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m,wind_direction_10m&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto&start_date=${dateStr}&end_date=${dateStr}`;
    }
    else {
         url = `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&hourly=temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m,wind_direction_10m&models=gfs_seamless&temperature_unit=fahrenheit&wind_speed_unit=mph&precipitation_unit=inch&timezone=auto&start_date=${dateStr}&end_date=${dateStr}`;
    }

    try {
        const response = await fetch(url);
        if (!response.ok) {
            if (response.status === 400) return { status: "too_early", temp: '--' };
            return { temp: '--', hourly: [] };
        }
        const data = await response.json();
        const gameHour = new Date(gameDateIso).getHours();
        
        const normalizePrecip = (index) => {
            let chance = 0;
            if (data.hourly.precipitation_probability) chance = data.hourly.precipitation_probability[index];
            else if (data.hourly.precipitation) {
                const amount = data.hourly.precipitation[index];
                if (amount >= 0.10) chance = 80;      
                else if (amount >= 0.05) chance = 60; 
                else if (amount >= 0.01) chance = 30; 
            }
            return chance;
        };

        const hourlySlice = [];
        let maxChanceInWindow = 0;
        for (let i = gameHour - 1; i <= gameHour + 4; i++) {
            if (i >= 0 && i < 24) {
                let chance = normalizePrecip(i);
                if (i >= gameHour && i <= gameHour + 3 && chance > maxChanceInWindow) maxChanceInWindow = chance;
                hourlySlice.push({ hour: i, precipChance: chance });
            }
        }

        return {
            status: "ok",
            temp: Math.round(data.hourly.temperature_2m[gameHour]),
            humidity: Math.round(data.hourly.relative_humidity_2m[gameHour]), // NEW FIELD
            maxPrecipChance: maxChanceInWindow, 
            windSpeed: Math.round(data.hourly.wind_speed_10m[gameHour]),
            windDir: data.hourly.wind_direction_10m[gameHour],
            hourly: hourlySlice
        };
    } catch (e) {
        console.error("⚠️ Weather fetch failed:", e);
        return { temp: '--', hourly: [] };
    }
}

function calculateWind(windDirection, stadiumBearing) {
    let diff = (windDirection - stadiumBearing + 360) % 360;
    if (diff >= 337.5 || diff < 22.5) return { text: "Blowing IN", cssClass: "bg-in", arrow: "⬇" };
    if (diff >= 22.5 && diff < 67.5) return { text: "In from Right", cssClass: "bg-in", arrow: "↙" };
    if (diff >= 67.5 && diff < 112.5) return { text: "Cross (R to L)", cssClass: "bg-cross", arrow: "⬅" };
    if (diff >= 112.5 && diff < 157.5) return { text: "Out to Left", cssClass: "bg-out", arrow: "↖" };
    if (diff >= 157.5 && diff < 202.5) return { text: "Blowing OUT", cssClass: "bg-out", arrow: "⬆" };
    if (diff >= 202.5 && diff < 247.5) return { text: "Out to Right", cssClass: "bg-out", arrow: "↗" };
    if (diff >= 247.5 && diff < 292.5) return { text: "Cross (L to R)", cssClass: "bg-cross", arrow: "➡" };
    return { text: "In from Left", cssClass: "bg-in", arrow: "↘" };
}
