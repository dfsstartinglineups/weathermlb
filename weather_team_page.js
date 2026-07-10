/**
 * ============================================================================
 * WEATHER MLB - MASTER STANDALONE TEAM PAGE ENGINE (weather_team_page.js)
 * Parses current date packets and loads direct isolated target dashboards.
 * ============================================================================
 */

const DEFAULT_DATE = new Date().toLocaleDateString('en-CA');

document.addEventListener('DOMContentLoaded', () => {
    let targetDate = DEFAULT_DATE;
    
    // Check if a date can be parsed from a date picker on the parent page template
    const datePicker = document.getElementById('date-picker');
    if (datePicker && datePicker.value) {
        targetDate = datePicker.value;
    } else if (datePicker) {
        datePicker.value = DEFAULT_DATE;
    }

    initSingleTeamPage(targetDate);
    
    if (datePicker) {
        datePicker.addEventListener('change', (e) => {
            if (e.target.value) {
                e.target.blur(); 
                initSingleTeamPage(e.target.value);
            }
        });
    }
});

async function initSingleTeamPage(dateToFetch) {
    const container = document.getElementById('team-weather-container');
    if (!container) return;

    try {
        // Look up two levels out of /team_pages/[team-name]/ to pull daily json cache
        const response = await fetch(`../../data/daily_files/games_${dateToFetch}.json?v=` + new Date().getTime());
        if (!response.ok) throw new Error("Local JSON cache matrix not available.");

        const gamesData = await response.json();
        
        // Isolate the game where the active target team matches either Home or Away rosters
        const targetMatch = gamesData.find(item => {
            return item.gameRaw.teams.away.team.id === window.TARGET_TEAM_ID || 
                   item.gameRaw.teams.home.team.id === window.TARGET_TEAM_ID;
        });

        if (!targetMatch) {
            container.innerHTML = `
                <div class="card p-5 text-center text-muted" style="border: 2px dashed #dee2e6; border-radius: 12px; background: #fff;">
                    <h3 class="h5 fw-bold text-dark mb-2">No Game Scheduled Today</h3>
                    <p class="small mb-0">This team has an off-day, travel day, or their matchup was postponed early.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        container.appendChild(createStandaloneWeatherCard(targetMatch));

    } catch (error) {
        console.error("Single team weather rendering failure:", error);
        container.innerHTML = `<div class="alert alert-light border text-center text-muted py-4">Forecast data pending for ${dateToFetch}</div>`;
    }
}

function createStandaloneWeatherCard(data) {
    const game = data.gameRaw;
    const stadium = data.stadium;
    const weather = data.weather;
    const windInfo = data.wind;
    const isRoofClosed = data.roof;
    const isRoofPending = data.roofPending;

    let borderClass = ""; 
    if (weather && !isRoofClosed) {
        let sustainedRainHours = weather.hourly ? weather.hourly.filter(h => h.precipChance >= 60).length : 0;
        if (weather.isThunderstorm) {
            borderClass = stadium.roof ? "border-warning border-3" : "border-danger border-3";
        } else if (sustainedRainHours >= 3) {
            borderClass = "border-danger border-3"; 
        } else if (weather.maxPrecipChance >= 30) {
            borderClass = "border-warning border-3"; 
        } 
    }

    let bgClass = "bg-weather-sunny"; 
    if (isRoofClosed) bgClass = "bg-weather-roof";
    else if (weather) {
        if (weather.isThunderstorm) bgClass = "bg-weather-storm";
        else if (weather.isSnow) bgClass = "bg-weather-snow";
        else if (weather.maxPrecipChance >= 50) bgClass = "bg-weather-rain";
        else if (weather.maxPrecipChance >= 20) bgClass = "bg-weather-cloudy";
    }

    const cardNode = document.createElement('div');
    cardNode.className = `card game-card shadow-sm ${borderClass} ${bgClass}`;

    const awayShortName = getShortTeamName(game.teams.away.team.name); 
    const homeShortName = getShortTeamName(game.teams.home.team.name);
    const awayLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${game.teams.away.team.id}.svg`;
    const homeLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${game.teams.home.team.id}.svg`;
    
    let gameTime = new Date(game.gameDate).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    let timeBadgeClass = "bg-light text-dark border";
    if (game.status?.detailedState.includes("Postponed")) { gameTime = "Postponed"; timeBadgeClass = "bg-danger text-white"; }
    else if (game.status?.detailedState.includes("Delay")) { gameTime = "Delayed"; timeBadgeClass = "bg-warning text-dark"; }
    else if (game.status?.detailedState === "In Progress" || game.status?.detailedState.includes("Live")) { gameTime = "Live"; timeBadgeClass = "bg-success text-white"; }
    else if (game.status?.abstractGameState === "Final") { gameTime = "Final"; timeBadgeClass = "bg-secondary text-white"; }

    const awayPitcher = game.teams.away.probablePitcher ? formatPlayerName(game.teams.away.probablePitcher.fullName) + (game.teams.away.probablePitcher.pitchHand?.code ? ` (${game.teams.away.probablePitcher.pitchHand.code})` : "") : "TBD";
    const homePitcher = game.teams.home.probablePitcher ? formatPlayerName(game.teams.home.probablePitcher.fullName) + (game.teams.home.probablePitcher.pitchHand?.code ? ` (${game.teams.home.probablePitcher.pitchHand.code})` : "") : "TBD";

    let mlAwayBadge = `<span class="badge bg-light text-muted border" style="font-size: 0.65rem;">TBD</span>`; 
    let mlHomeBadge = `<span class="badge bg-light text-muted border" style="font-size: 0.65rem;">TBD</span>`;
    let totalBadgeHtml = ``;
    if (data.odds?.bookmakers?.length > 0) {
        let selectedBook = data.odds.bookmakers.find(b => b.key === 'draftkings') || data.odds.bookmakers[0];
        if (selectedBook?.markets) {
            const h2h = selectedBook.markets.find(m => m.key === 'h2h');
            const awayOutcome = h2h?.outcomes.find(o => o.name === game.teams.away.team.name);
            const homeOutcome = h2h?.outcomes.find(o => o.name === game.teams.home.team.name);
            if (awayOutcome) mlAwayBadge = `<span class="badge bg-light text-dark border" style="font-size: 0.65rem;">${awayOutcome.price > 0 ? '+'+awayOutcome.price : awayOutcome.price}</span>`;
            if (homeOutcome) mlHomeBadge = `<span class="badge bg-light text-dark border" style="font-size: 0.65rem;">${homeOutcome.price > 0 ? '+'+homeOutcome.price : homeOutcome.price}</span>`;
            const totals = selectedBook.markets.find(m => m.key === 'totals');
            if (totals?.outcomes?.length > 0) totalBadgeHtml = `<span class="badge bg-secondary ms-1" style="font-size: 0.65rem;">O/U ${totals.outcomes[0].point}</span>`;
        }
    }

    let weatherHtml = `<div class="text-muted p-3 text-center small">Weather forecast unavailable.</div>`;
    if (stadium && weather && weather.temp !== '--') {
        let displayRain = isRoofClosed ? "0%" : `${weather.maxPrecipChance}%`;
        let hourlyHtml = '';
        if (isRoofClosed) hourlyHtml = `<div class="text-center mt-2"><small class="text-muted">Indoor Conditions Controlled</small></div>`;
        else if (weather.hourly?.length > 0) {
            const hoursMarkup = weather.hourly.map(h => {
                const dateObj = h.timestamp ? new Date(h.timestamp) : new Date();
                const hr12 = dateObj.getHours() % 12 || 12;
                const ampm = dateObj.getHours() >= 12 ? 'PM' : 'AM';
                let icon = h.precipChance >= 30 ? (h.isThunderstorm ? '⛈️' : '🌧️') : (dateObj.getHours() >= 20 || dateObj.getHours() < 6 ? '🌙' : '☀️');
                return `<div class="hour-card"><div class="hour-time">${hr12}${ampm}</div><div class="hour-icon">${icon}</div><div class="hour-pop">${h.precipChance >= 20 ? h.precipChance+'%' : '&nbsp;'}</div><div class="hour-temp">${h.temp}°</div></div>`;
            }).join('');
            hourlyHtml = `<div class="hourly-scroll-container">${hoursMarkup}</div>`;
        }

        let windArrow = windInfo ? `<span class="arrow-emoji">${windInfo.arrow}</span>` : "💨";
        let windCss = windInfo ? windInfo.cssClass : "bg-secondary";

        weatherHtml = `
            <div class="weather-row row text-center align-items-center mt-2">
                <div class="col-3 border-end px-1"><div class="fw-bold">${weather.temp}°F</div><div class="small text-muted" style="font-size: 0.7rem;">Temp</div></div>
                <div class="col-3 border-end px-1"><div class="fw-bold text-dark">${weather.humidity}%</div><div class="small text-muted" style="font-size: 0.7rem;">Hum</div></div>
                <div class="col-3 border-end px-1"><div class="fw-bold text-primary">${displayRain}</div><div class="small text-muted" style="font-size: 0.7rem;">Rain</div></div>
                <div class="col-3 px-1"><div class="fw-bold">${weather.windSpeed} <span style="font-size:0.7em">mph</span></div><span class="wind-badge ${windCss}" style="font-size: 0.55rem; white-space: nowrap; display: inline-block; padding: 2px 4px;">${windArrow}</span></div>
            </div>
            ${hourlyHtml}
            <div class="analysis-box">
                <span class="analysis-title">✨ Weather Impact Analysis</span>
                ${generateMatchupAnalysis(weather, windInfo, isRoofClosed, isRoofPending, stadium)}
            </div>
        `;
    }

    cardNode.innerHTML = `
        <div class="card-body p-3"> 
            <div class="d-flex justify-content-between align-items-center mb-3">
                <div><span class="badge ${timeBadgeClass}">${gameTime}</span>${totalBadgeHtml}</div>
                <span class="stadium-name text-truncate text-end flex-grow-1 ms-2">${game.venue?.name || 'TBD'}</span>
            </div>
            <div class="d-flex justify-content-between align-items-center px-1 mb-2">
                <div class="d-flex align-items-center text-truncate" style="width: 45%; min-width: 0;"> 
                    <img src="${awayLogo}" class="me-2" style="width: 28px; height: 28px; object-fit: contain;">
                    <div class="fw-bold lh-sm text-dark text-truncate" style="font-size: 1.15rem; letter-spacing: -0.3px;">${awayShortName}</div>
                </div>
                <div class="text-center text-muted fw-bold" style="width: 10%; font-size: 0.9rem;">@</div>
                <div class="d-flex align-items-center justify-content-end text-truncate" style="width: 45%; min-width: 0;"> 
                    <img src="${homeLogo}" class="me-2" style="width: 28px; height: 28px; object-fit: contain;">
                    <div class="fw-bold lh-sm text-dark text-truncate text-end" style="font-size: 1.15rem; letter-spacing: -0.3px;">${homeShortName}</div>
                </div>
            </div>
            <div class="d-flex justify-content-between align-items-center px-1 mb-3">
                <div class="d-flex align-items-center text-truncate" style="width: 48%;">
                    <span class="text-muted text-truncate me-2" style="font-size: 0.75rem;">${awayPitcher}</span>${mlAwayBadge}
                </div>
                <div class="d-flex align-items-center justify-content-end text-truncate" style="width: 48%;">
                    <span class="text-muted text-truncate me-2 text-end" style="font-size: 0.75rem;">${homePitcher}</span>${mlHomeBadge}
                </div>
            </div>
            <div class="px-0 pt-2 pb-1 w-100 border-top mt-1 mb-1">
                <a href="https://mlbstartingnine.com/lineups/${window.TARGET_TEAM_SLUG}/" target="_blank" class="btn btn-sm w-100 text-decoration-none shadow-sm" style="background-color: #f8f9fa; border: 1px solid #dee2e6; color: #0d6efd; font-weight: 700; font-size: 0.75rem;">
                    📋 View Projected/Starting Lineups
                </a>
            </div>
            ${weatherHtml}
        </div>
    `;

    return cardNode;
}

function getShortTeamName(fullName) {
    if (!fullName) return "";
    if (fullName.includes("Red Sox")) return "Red Sox";
    if (fullName.includes("White Sox")) return "White Sox";
    if (fullName.includes("Blue Jays")) return "Blue Jays";
    if (fullName.includes("Diamondbacks")) return "Dbacks";
    const parts = fullName.split(" ");
    return parts[parts.length - 1];
}

function formatPlayerName(fullName) {
    if (!fullName) return "";
    const parts = fullName.split(" ");
    if (parts.length === 1) return fullName; 
    return `${parts[0].charAt(0)}. ${parts.slice(1).join(" ")}`;
}

function generateMatchupAnalysis(weather, windInfo, isRoofClosed, isRoofPending, stadium) {
    if (isRoofClosed) return "✅ <b>Roof Closed:</b> Controlled environment with zero weather impact.";
    let notes = [];
    if (isRoofPending) notes.push("🏟️ <b>Roof Status Pending:</b> Borderline weather. The team may elect to close the roof.");
    if (weather.isThunderstorm) notes.push(stadium.roof ? "⚡ <b>Lightning Risk:</b> Thunderstorms detected. Possible delay to close roof." : "⚡ <b>Lightning Risk:</b> Thunderstorms detected. Mandatory safety delays likely.");
    if (weather.isSnow) notes.push("❄️ <b>Snow Risk:</b> Low visibility and slippery field conditions could delay play.");
    let sustainedRainHours = weather.hourly ? weather.hourly.filter(h => h.precipChance >= 60).length : 0;
    if (sustainedRainHours >= 3) notes.push("🌧️ <b>Rainout Risk:</b> Sustained heavy rain. High probability of postponement.");
    else if (weather.maxPrecipChance >= 70) notes.push("☔ <b>Severe Delay Risk:</b> Heavy rain expected. Delays likely.");
    else if (weather.maxPrecipChance >= 30) notes.push("☔ <b>Delay Risk:</b> Scattered showers could interrupt play.");
    if (weather.humidity <= 30) notes.push("🌵 <b>Dry Air (<30%):</b> Sharp breaking balls, but the ball travels farther.");
    else if (weather.humidity >= 70) notes.push("💧 <b>High Humidity (>70%):</b> Breaking balls hang, but ball distance is suppressed.");
    if (weather.temp >= 85) notes.push("🔥 <b>Hitter Friendly:</b> High temps reduce air density, helping fly balls carry.");
    else if (weather.temp <= 50) notes.push("❄️ <b>Pitcher Friendly:</b> Cold, dense air suppresses ball flight and scoring.");
    if (weather.windSpeed >= 8 && windInfo) {
        const dir = windInfo.text;
        if (dir.includes("Blowing OUT")) notes.push("🚀 <b>Home Runs:</b> Strong wind blowing out creates ideal hitting conditions.");
        else if (dir.includes("Blowing IN")) notes.push("🛑 <b>Suppressed:</b> Wind blowing in will knock down fly balls.");
        else if (dir.includes("Out to Right")) notes.push("↗️ <b>Lefty Advantage:</b> Wind blowing out to Right Field favors Left-Handed power.");
        else if (dir.includes("Out to Left")) notes.push("↖️ <b>Righty Advantage:</b> Wind blowing out to Left Field favors Right-Handed power.");
    }
    if (notes.length === 0) return "✅ <b>Neutral:</b> Fair weather conditions. No significant advantage.";
    return notes.join("<br>");
}
