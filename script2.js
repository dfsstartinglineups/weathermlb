// ==========================================
// CONFIGURATION
// ==========================================
const DEFAULT_DATE = new Date().toLocaleDateString('en-CA');

// Global State
let ALL_GAMES_DATA = []; 

// ==========================================
// 1. MAIN APP LOGIC (NOW LIGHTNING FAST)
// ==========================================

async function init(dateToFetch) {
    console.log(`🚀 Starting App. Fetching pre-built JSON for: ${dateToFetch}`);
    
    // --- DYNAMIC PAGE META UPDATE ---
    if (window.updatePageMeta) window.updatePageMeta(dateToFetch);
    
    const container = document.getElementById('games-container');
    const datePicker = document.getElementById('date-picker');
    const loader = document.getElementById('global-loader');
    const loadingText = document.getElementById('loading-text');
    
    // Reset State & Show Loader
    ALL_GAMES_DATA = [];
    if (datePicker) datePicker.value = dateToFetch;
    if (container) container.innerHTML = ''; 
    
    if (loader) loader.style.display = 'block';
    if (loadingText) loadingText.innerText = 'Loading Schedule...';

    try {
        // Fetch the pre-built JSON directly! No more MLB API or Weather API calls on the client.
        const response = await fetch(`data/daily_files/games_${dateToFetch}.json?v=` + new Date().getTime());
        
        if (!response.ok) {
            throw new Error(`No local file available for ${dateToFetch}`);
        }

        ALL_GAMES_DATA = await response.json();

        if (ALL_GAMES_DATA.length === 0) {
            if (loader) loader.style.display = 'none'; 
            container.innerHTML = `
                <div class="col-12 text-center mt-5">
                    <div class="alert alert-light shadow-sm py-4">
                        <h4 class="text-muted">No games scheduled for ${dateToFetch}</h4>
                    </div>
                </div>`;
            return;
        }

        renderGames();
        if (loader) loader.style.display = 'none';

    } catch (error) {
        console.log(`No local file for ${dateToFetch} or rendering failed. Falling back to live MLB API...`);
        console.error("The exact error was:", error); // <-- Added so we can see any future bugs!
        
        try {
            // Fallback: Hit the MLB API directly just to show the schedule
            const [year, month, day] = dateToFetch.split('-');
            const mlbApiDate = `${month}/${day}/${year}`;
            
            const mlbRes = await fetch(`https://statsapi.mlb.com/api/v1/schedule?sportId=1,51&date=${mlbApiDate}&hydrate=probablePitcher,lineups`);
            
            if (!mlbRes.ok) throw new Error("MLB API Failed");
            
            const mlbData = await mlbRes.json();
            
            if (mlbData.dates && mlbData.dates.length > 0) {
                // Map the raw MLB data with blank weather/odds so the renderer doesn't crash
                ALL_GAMES_DATA = mlbData.dates[0].games.map(game => {
                    return {
                        gameRaw: game,
                        stadium: null,
                        weather: null,
                        wind: null,
                        roof: false,
                        roofPending: false,
                        odds: null,
                        lineupHandedness: {},
                        lineupPositions: {}
                    };
                });
                
                renderGames();
                
                // Add an alert banner to inform the user about the forecast limits
                const weatherWarning = document.createElement('div');
                weatherWarning.className = 'col-12 mb-3';
                weatherWarning.innerHTML = `
                    <div class="alert alert-info text-center py-2 mb-0 shadow-sm border" style="font-size: 0.85rem;">
                        ℹ️ <strong>Schedule-Only Mode:</strong> Detailed weather forecasts and matchup analysis are currently generated up to 7 days in advance.
                    </div>
                `;
                container.prepend(weatherWarning);

                if (loader) loader.style.display = 'none';
            } else {
                throw new Error("No games scheduled");
            }
            
        } catch (fallbackError) {
            console.error("Fallback failed:", fallbackError);
            if (loader) loader.style.display = 'none';
            container.innerHTML = `
                <div class="col-12 text-center mt-5">
                    <div class="alert alert-light border shadow-sm py-4">
                        <h4 class="text-muted">Schedule pending for ${dateToFetch}</h4>
                        <p class="small text-muted mb-0">Check back later or select a different date.</p>
                    </div>
                </div>`;
        }
    }
}

// ==========================================
// 2. RENDERING ENGINE
// ==========================================

function renderGames() {
    const container = document.getElementById('games-container');
    const cardsContainer = document.createElement('div');
    cardsContainer.className = 'row w-100 m-0 p-0';

    const searchText = document.getElementById('team-search').value.toLowerCase();
    const sortMode = document.getElementById('sort-filter').value;
    const risksOnly = document.getElementById('risk-only').checked;

    let filteredGames = ALL_GAMES_DATA.filter(item => {
        const g = item.gameRaw;
        const teams = (g.teams.away.team.name + " " + g.teams.home.team.name).toLowerCase();
        
        if (!teams.includes(searchText)) return false;

        if (risksOnly) {
            if (!item.weather || item.weather.temp === '--') return false; 
            if (item.roof) return false;
            if (item.weather.maxPrecipChance < 30) return false;
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
        if (sortMode === 'humidity') return (b.weather?.humidity || 0) - (a.weather?.humidity || 0);
        
        return new Date(a.gameRaw.gameDate) - new Date(b.gameRaw.gameDate);
    });

    if (filteredGames.length === 0) {
        cardsContainer.innerHTML = `<div class="col-12 text-center py-5 text-muted">No games match your filters.</div>`;
    } else {
        filteredGames.forEach(item => {
            cardsContainer.appendChild(createGameCard(item));
        });
    }
    
    // Safely append the cards without destroying the alert banner
    const existingAlert = container.querySelector('.alert-info');
    container.innerHTML = '';
    if (existingAlert) container.appendChild(existingAlert.parentElement);
    container.appendChild(cardsContainer);

    setTimeout(() => {
        if (window.location.hash) {
            const targetCard = document.querySelector(window.location.hash);
            if (targetCard) {
                targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
                const innerCard = targetCard.querySelector('.game-card');
                innerCard.classList.add('border-primary', 'border-3');
                setTimeout(() => { innerCard.classList.remove('border-primary', 'border-3'); }, 2000);
            }
        }
    }, 300);
}

function createGameCard(data) {
    const game = data.gameRaw;
    const stadium = data.stadium;
    const weather = data.weather;
    const windInfo = data.wind;
    const isRoofClosed = data.roof;
    const isRoofPending = data.roofPending;

    let borderClass = ""; 
    if (weather && !isRoofClosed) {
        let sustainedRainHours = 0;
        if (weather.hourly && weather.hourly.length > 0) {
            sustainedRainHours = weather.hourly.filter(h => h.precipChance >= 60).length;
        }

        if (weather.isThunderstorm) {
            borderClass = "border-danger border-3"; 
        } else if (sustainedRainHours >= 3) {
            borderClass = "border-danger border-3"; 
        } else if (weather.maxPrecipChance >= 30) {
            borderClass = "border-warning border-3"; 
        } 
    }

    let bgClass = "bg-weather-sunny"; 
    if (isRoofClosed) {
        bgClass = "bg-weather-roof";
    } else if (weather) {
        if (weather.isThunderstorm) bgClass = "bg-weather-storm";
        else if (weather.isSnow) bgClass = "bg-weather-snow";
        else if (weather.maxPrecipChance >= 50) bgClass = "bg-weather-rain";
        else if (weather.maxPrecipChance >= 20) bgClass = "bg-weather-cloudy";
        else if (weather.temp >= 90) bgClass = "bg-weather-sunny"; 
    } else {
        bgClass = "bg-light"; 
    }

    const gameCard = document.createElement('div');
    gameCard.className = 'col-md-6 col-lg-4 col-xl-3 col-xxl-2 animate-card mb-2 px-1';
    gameCard.id = `game-${game.gamePk}`;

    const awayId = game.teams.away.team.id;
    const homeId = game.teams.home.team.id;
    const awayName = game.teams.away.team.name; 
    const homeName = game.teams.home.team.name; 
    const awayShortName = getShortTeamName(awayName); 
    const homeShortName = getShortTeamName(homeName);

    const awayLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${awayId}.svg`;
    const homeLogo = `https://www.mlbstatic.com/team-logos/team-cap-on-light/${homeId}.svg`;
    let gameTime = new Date(game.gameDate).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    let timeBadgeClass = "bg-light text-dark border";

    // --- GAME STATUS OVERRIDES ---
    const matchState = game.status?.detailedState || "";
    
    if (matchState.includes("Postponed")) {
        gameTime = "Postponed";
        timeBadgeClass = "bg-danger text-white";
    } else if (matchState.includes("Cancel")) {
        gameTime = "Canceled";
        timeBadgeClass = "bg-danger text-white";
    } else if (matchState.includes("Delay")) {
        gameTime = "Delayed";
        timeBadgeClass = "bg-warning text-dark";
    } else if (matchState === "In Progress" || matchState.includes("Live")) {
        gameTime = "Live";
        timeBadgeClass = "bg-success text-white";
    } else if (game.status?.abstractGameState === "Final") {
        gameTime = "Final";
        timeBadgeClass = "bg-secondary text-white";
    }

    let awayPitcher = "TBD";
    if (game.teams.away.probablePitcher) {
        const pInfo = game.teams.away.probablePitcher;
        const hand = pInfo.pitchHand?.code ? ` (${pInfo.pitchHand.code})` : "";
        awayPitcher = formatPlayerName(pInfo.fullName) + hand;
    }

    let homePitcher = "TBD";
    if (game.teams.home.probablePitcher) {
        const pInfo = game.teams.home.probablePitcher;
        const hand = pInfo.pitchHand?.code ? ` (${pInfo.pitchHand.code})` : "";
        homePitcher = formatPlayerName(pInfo.fullName) + hand;
    }

    const lineupAway = game.lineups?.awayPlayers || [];
    const lineupHome = game.lineups?.homePlayers || [];
    const handDict = data.lineupHandedness || {}; 

    const isLineupsExpanded = document.getElementById('show-lineups')?.checked;
    const collapseClass = isLineupsExpanded ? "collapse show" : "collapse";
    const ariaExpanded = isLineupsExpanded ? "true" : "false";

    const windText = windInfo?.text || "";
    const windSpeed = weather?.windSpeed || 0;
    const isWindImpactful = windSpeed >= 9; 

    const isWindOutToRight = isWindImpactful && windText.includes("Out to Right");
    const isWindOutToLeft = isWindImpactful && windText.includes("Out to Left");
    const isWindInFromRight = isWindImpactful && windText.includes("In from Right");
    const isWindInFromLeft = isWindImpactful && windText.includes("In from Left");

    const homePitcherHand = game.teams.home.probablePitcher?.pitchHand?.code || "";
    const awayPitcherHand = game.teams.away.probablePitcher?.pitchHand?.code || "";

    // --- AWAY LINEUP RENDERING ---
    let awayLineupHtml = '';
    if (lineupAway.length > 0) {
        const list = lineupAway.map((p, index) => {
            const batCode = handDict[p.id]; 
            const gamePos = data.lineupPositions[p.id] || "";
            const prefixText = gamePos ? gamePos : `${index + 1}.`;
            
            let itemStyle = "";
            let tooltip = "";
            
            const orderHtml = `<span class="fw-bold text-dark d-inline-block text-start" style="opacity: 0.85; font-size: 0.65rem; width: 20px;">${prefixText}</span>`;
            const shortName = formatPlayerName(p.fullName);
            
            if (batCode) {
                let effectiveBatSide = batCode;
                let switchNote = "";
                if (batCode === 'S' && homePitcherHand) {
                    effectiveBatSide = (homePitcherHand === 'R') ? 'L' : 'R';
                    switchNote = `Batting ${effectiveBatSide} vs ${homePitcherHand}HP - `;
                }

                if (isWindOutToRight && effectiveBatSide === 'L') {
                    itemStyle = "color: #198754;"; 
                    tooltip = `title='Favorable Matchup: ${switchNote}Wind blowing out to Right Field (${windSpeed}mph)'`;
                } else if (isWindOutToLeft && effectiveBatSide === 'R') {
                    itemStyle = "color: #198754;";
                    tooltip = `title='Favorable Matchup: ${switchNote}Wind blowing out to Left Field (${windSpeed}mph)'`;
                } else if (isWindInFromRight && effectiveBatSide === 'L') {
                    itemStyle = "color: #dc3545;"; 
                    tooltip = `title='Unfavorable Matchup: ${switchNote}Wind blowing in from Right Field (${windSpeed}mph)'`;
                } else if (isWindInFromLeft && effectiveBatSide === 'R') {
                    itemStyle = "color: #dc3545;";
                    tooltip = `title='Unfavorable Matchup: ${switchNote}Wind blowing in from Left Field (${windSpeed}mph)'`;
                }
            }

            const handHtml = batCode ? `<span style="font-weight:normal; opacity:0.8; color: inherit;">(${batCode})</span>` : "";
            
            return `<li ${tooltip} style="${itemStyle} cursor: default; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${orderHtml}<span class="d-md-none">${p.fullName}</span><span class="d-none d-md-inline">${shortName}</span>${handHtml}</li>`;
        }).join('');
        
        const collapseId = `lineup-away-${game.gamePk}`;
        awayLineupHtml = `
            <div class="mt-0 w-100"> 
                <a href="#${collapseId}" data-bs-toggle="collapse" aria-expanded="${ariaExpanded}" class="badge bg-primary text-white text-decoration-none" style="font-size: 0.65rem;">📋 View Lineup</a>
                <div class="${collapseClass} mt-1 text-start bg-light rounded px-1 py-1 border w-100" id="${collapseId}">
                    <ul class="list-unstyled text-muted mb-0 w-100" style="font-size: 0.65rem; line-height: 1.35; padding-left: 0.2rem;">${list}</ul>
                </div>
            </div>`;
    }

    // --- HOME LINEUP RENDERING ---
    let homeLineupHtml = '';
    if (lineupHome.length > 0) {
        const list = lineupHome.map((p, index) => {
            const batCode = handDict[p.id]; 
            const gamePos = data.lineupPositions[p.id] || "";
            const prefixText = gamePos ? gamePos : `${index + 1}.`;
            
            let itemStyle = "";
            let tooltip = "";
            
            const orderHtml = `<span class="fw-bold text-dark d-inline-block text-start" style="opacity: 0.85; font-size: 0.65rem; width: 20px;">${prefixText}</span>`;
            const shortName = formatPlayerName(p.fullName);
            
            if (batCode) {
                let effectiveBatSide = batCode;
                let switchNote = "";
                if (batCode === 'S' && awayPitcherHand) {
                    effectiveBatSide = (awayPitcherHand === 'R') ? 'L' : 'R';
                    switchNote = `Batting ${effectiveBatSide} vs ${awayPitcherHand}HP - `;
                }

                if (isWindOutToRight && effectiveBatSide === 'L') {
                    itemStyle = "color: #198754;"; 
                    tooltip = `title='Favorable Matchup: ${switchNote}Wind blowing out to Right Field (${windSpeed}mph)'`;
                } else if (isWindOutToLeft && effectiveBatSide === 'R') {
                    itemStyle = "color: #198754;";
                    tooltip = `title='Favorable Matchup: ${switchNote}Wind blowing out to Left Field (${windSpeed}mph)'`;
                } else if (isWindInFromRight && effectiveBatSide === 'L') {
                    itemStyle = "color: #dc3545;"; 
                    tooltip = `title='Unfavorable Matchup: ${switchNote}Wind blowing in from Right Field (${windSpeed}mph)'`;
                } else if (isWindInFromLeft && effectiveBatSide === 'R') {
                    itemStyle = "color: #dc3545;";
                    tooltip = `title='Unfavorable Matchup: ${switchNote}Wind blowing in from Left Field (${windSpeed}mph)'`;
                }
            }

            const handHtml = batCode ? `<span style="font-weight:normal; opacity:0.8; color: inherit;">(${batCode})</span>` : "";
            
            return `<li ${tooltip} style="${itemStyle} cursor: default; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${orderHtml}<span class="d-md-none">${p.fullName}</span><span class="d-none d-md-inline">${shortName}</span>${handHtml}</li>`;
        }).join('');
        
        const collapseId = `lineup-home-${game.gamePk}`;
        homeLineupHtml = `
            <div class="mt-0 w-100"> 
                <a href="#${collapseId}" data-bs-toggle="collapse" aria-expanded="${ariaExpanded}" class="badge bg-primary text-white text-decoration-none" style="font-size: 0.65rem;">📋 View Lineup</a>
                <div class="${collapseClass} mt-1 text-start bg-light rounded px-1 py-1 border w-100" id="${collapseId}">
                    <ul class="list-unstyled text-muted mb-0 w-100" style="font-size: 0.65rem; line-height: 1.35; padding-left: 0.2rem;">${list}</ul>
                </div>
            </div>`;
    }

    let crossPromoHtml = '';
    if (lineupAway.length > 0 || lineupHome.length > 0) {
        crossPromoHtml = `
            <div class="px-2 pt-2 pb-1 w-100">
                <a href="https://mlbstartingnine.com/#game-${game.gamePk}" target="_blank" class="btn btn-sm w-100 text-decoration-none shadow-sm" style="background-color: #f8f9fa; border: 1px solid #dee2e6; color: #0d6efd; font-weight: 700; font-size: 0.75rem;">
                    ⚾ View BvP Matchups & Splits
                </a>
            </div>
        `;
    }

    const oddsData = data.odds; 
    let mlAway = `<div class="fw-bold text-muted mt-1" style="font-size: 0.8rem;">TBD</div>`; 
    let mlHome = `<div class="fw-bold text-muted mt-1" style="font-size: 0.8rem;">TBD</div>`;
    let totalHtml = `
        <div class="d-flex flex-column justify-content-center align-items-center pt-2">
            <div class="text-muted small fw-bold mb-1">@</div>
            <div class="fw-bold text-muted" style="font-size: 0.8rem; letter-spacing: 0.5px;">O/U TBD</div>
        </div>`;

    // --- ODDS FIX: Now properly accesses bookmakers array ---
    if (oddsData && oddsData.bookmakers && oddsData.bookmakers.length > 0) {
        // Fallback to the first available bookie if FanDuel isn't found
        let selectedBook = oddsData.bookmakers.find(b => b.key === 'fanduel') || oddsData.bookmakers[0];
        
        if (selectedBook && selectedBook.markets) {
            const h2hMarket = selectedBook.markets.find(m => m.key === 'h2h');
            if (h2hMarket && h2hMarket.outcomes) {
                const awayOutcome = h2hMarket.outcomes.find(o => o.name === awayName);
                const homeOutcome = h2hMarket.outcomes.find(o => o.name === homeName);
                if (awayOutcome) {
                    const price = awayOutcome.price > 0 ? `+${awayOutcome.price}` : awayOutcome.price;
                    mlAway = `<div class="fw-bold text-dark mt-1" style="font-size: 0.8rem;">${price}</div>`;
                }
                if (homeOutcome) {
                    const price = homeOutcome.price > 0 ? `+${homeOutcome.price}` : homeOutcome.price;
                    mlHome = `<div class="fw-bold text-dark mt-1" style="font-size: 0.8rem;">${price}</div>`;
                }
            }

            const totalsMarket = selectedBook.markets.find(m => m.key === 'totals');
            if (totalsMarket && totalsMarket.outcomes && totalsMarket.outcomes.length > 0) {
                const gameTotal = totalsMarket.outcomes[0].point; 
                totalHtml = `
                    <div class="d-flex flex-column justify-content-center align-items-center pt-2">
                        <div class="text-muted small fw-bold mb-1">@</div>
                        <div class="fw-bold text-dark" style="font-size: 0.8rem; letter-spacing: 0.5px;">O/U ${gameTotal}</div>
                    </div>`;
            }
        }
    }

    let weatherHtml = `<div class="text-muted p-3 text-center small">Weather data unavailable.<br><span class="badge bg-light text-dark mt-1">Venue ID: ${game.venue.id || "N/A"}</span></div>`;

    if (stadium && weather) {
        if (weather.status === "too_early") {
            weatherHtml = `
                <div class="text-center p-3">
                    <h6 class="text-muted mb-1">🔭 Too Early to Forecast</h6>
                    <p class="small text-muted mb-0" style="font-size: 0.75rem;">Forecasts available ~14 days out.</p>
                </div>`;
        } else if (weather.temp !== '--') {
            const analysisText = generateMatchupAnalysis(weather, windInfo, isRoofClosed, isRoofPending); 
            
            let displayRain = isRoofClosed ? "0%" : `${weather.maxPrecipChance}%`;
            let precipLabel = "Rain"; 

            if (!isRoofClosed) {
                if (weather.isThunderstorm) displayRain += " ⚡";
                else if (weather.isSnow) { displayRain += " ❄️"; precipLabel = "Snow"; }
            }
            
            const radarUrl = `https://embed.windy.com/embed2.html?lat=${stadium.lat}&lon=${stadium.lon}&detailLat=${stadium.lat}&detailLon=${stadium.lon}&width=650&height=450&zoom=11&level=surface&overlay=rain&product=ecmwf&menu=&message=&marker=&calendar=now&pressure=&type=map&location=coordinates&detail=&metricWind=mph&metricTemp=%C2%B0F&radarRange=-1`;

            let hourlyHtml = '';
            if (isRoofClosed) {
                hourlyHtml = `<div class="text-center mt-2"><small class="text-muted">Indoor Conditions</small></div>`;
            } else if (weather.hourly && weather.hourly.length > 0) {
                const cardsHtml = weather.hourly.map((h, index) => {
                    const ampm = h.hour >= 12 ? 'PM' : 'AM';
                    const hour12 = h.hour % 12 || 12;
                    const timeLabel = `${hour12}${ampm}`;

                    let icon = '';
                    let popHtml = '&nbsp;'; 
                    const isNight = h.hour >= 20 || h.hour < 6;

                    if (h.precipChance >= 30) {
                        if (h.isThunderstorm) icon = '⛈️';
                        else if (h.isSnow) icon = '🌨️';
                        else icon = '🌧️';
                        popHtml = `${h.precipChance}%`;
                    } else if (h.precipChance > 0) {
                        icon = '⛅'; 
                        popHtml = `${h.precipChance}%`;
                    } else {
                        icon = isNight ? '🌙' : '☀️';
                    }
                    const tempDisplay = h.temp !== undefined ? `${h.temp}°` : '--';

                    return `
                        <div class="hour-card">
                            <div class="hour-time">${timeLabel}</div>
                            <div class="hour-icon">${icon}</div>
                            <div class="hour-pop">${popHtml}</div>
                            <div class="hour-temp">${tempDisplay}</div>
                        </div>`;
                }).join('');
                hourlyHtml = `<div class="hourly-scroll-container">${cardsHtml}</div>`;
            }
            
            let windArrow = windInfo ? windInfo.arrow : "💨";
            let windCss = windInfo ? windInfo.cssClass : "bg-secondary";
            
            weatherHtml = `
                <div class="weather-row row text-center align-items-center mt-2">
                    <div class="col-3 border-end px-1">
                        <div class="fw-bold">${weather.temp}°F</div>
                        <div class="small text-muted" style="font-size: 0.7rem;">Temp</div>
                    </div>
                    <div class="col-3 border-end px-1">
                        <div class="fw-bold text-dark">${weather.humidity}%</div>
                        <div class="small text-muted" style="font-size: 0.7rem;">Hum</div>
                    </div>
                    <div class="col-3 border-end px-1">
                        <div class="fw-bold text-primary" style="white-space: nowrap;">${displayRain}</div>
                        <div class="small text-muted" style="font-size: 0.7rem;">${precipLabel}</div>
                    </div>
                    <div class="col-3 px-1">
                        <div class="fw-bold">${weather.windSpeed} <span style="font-size:0.7em">mph</span></div>
                        <span class="wind-badge ${windCss}" style="font-size: 0.55rem; white-space: nowrap; display: inline-block; padding: 2px 4px;">
                            ${windArrow}
                        </span>
                    </div>
                </div>
                ${hourlyHtml}
                
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-primary w-100 py-1" onclick="showRadar('${radarUrl}', '${game.venue.name}')">
                        🗺️ View Live Radar
                    </button>
                </div>

                <div class="analysis-box">
                    <span class="analysis-title">✨ Weather Impact</span>
                    ${generateMatchupAnalysis(weather, windInfo, isRoofClosed, isRoofPending)}
                </div>`;
        }
    }

    gameCard.innerHTML = `
        <div class="card game-card h-100 ${borderClass} ${bgClass}">
            <div class="card-body px-2 pt-2 pb-2"> 
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="badge ${timeBadgeClass}">${gameTime}</span>
                    <span class="stadium-name text-truncate" style="max-width: 180px;">${game.venue?.name || 'TBD'}</span>
                </div>
                
                <div class="d-flex justify-content-between align-items-start px-1">
                    <div class="text-center" style="width: 45%; min-width: 0;"> 
                        <img src="${awayLogo}" alt="${awayName}" class="team-logo mb-1" onerror="this.style.display='none'">
                        <div class="d-flex flex-column justify-content-center align-items-center w-100">
                            <div class="fw-bold lh-sm text-dark text-truncate w-100" style="font-size: 0.9rem; letter-spacing: -0.3px;">${awayShortName}</div>
                            ${mlAway}
                        </div>
                        <div class="text-muted mt-1 mb-0 text-truncate w-100" style="font-size: 0.7rem;">${awayPitcher}</div>
                    </div>
                    
                    <div class="text-center" style="width: 10%; min-width: 0;">
                        ${totalHtml}
                    </div>
                    
                    <div class="text-center" style="width: 45%; min-width: 0;"> 
                        <img src="${homeLogo}" alt="${homeName}" class="team-logo mb-1" onerror="this.style.display='none'">
                        <div class="d-flex flex-column justify-content-center align-items-center w-100">
                            <div class="fw-bold lh-sm text-dark text-truncate w-100" style="font-size: 0.9rem; letter-spacing: -0.3px;">${homeShortName}</div>
                            ${mlHome}
                        </div>
                        <div class="text-muted mt-1 mb-0 text-truncate w-100" style="font-size: 0.7rem;">${homePitcher}</div>
                    </div>
                </div>
                
                <div class="row g-0 mt-1 mx-0 w-100">
                    <div class="col-6 pe-1 text-center w-50">
                        ${awayLineupHtml}
                    </div>
                    <div class="col-6 ps-1 text-center w-50">
                        ${homeLineupHtml}
                    </div>
                </div>
                
                ${crossPromoHtml}
                
                ${weatherHtml}
            </div>
        </div>`;
    
    return gameCard;
}

// ==========================================
// 3. LISTENERS
// ==========================================

document.addEventListener('DOMContentLoaded', () => {
    const lineupsToggle = document.getElementById('show-lineups');
    
    if (lineupsToggle) {
        const savedState = localStorage.getItem('weatherMlb_showLineups');
        if (savedState === 'true') {
            lineupsToggle.checked = true;
        }
    }
    
    init(DEFAULT_DATE);

    const searchInput = document.getElementById('team-search');
    const sortSelect = document.getElementById('sort-filter');
    const riskToggle = document.getElementById('risk-only');
    
    if(searchInput) searchInput.addEventListener('input', renderGames);
    if(sortSelect) sortSelect.addEventListener('change', renderGames);
    if(riskToggle) riskToggle.addEventListener('change', renderGames);

    if(lineupsToggle) {
        lineupsToggle.addEventListener('change', (e) => {
            localStorage.setItem('weatherMlb_showLineups', e.target.checked);
            renderGames();
        });
    }

    const datePicker = document.getElementById('date-picker');
    
    if (datePicker) {
        datePicker.value = DEFAULT_DATE;
        datePicker.addEventListener('change', (e) => {
            if (e.target.value) {
                e.target.blur(); 
                
                const riskToggle = document.getElementById('risk-only');
                if (riskToggle) riskToggle.checked = false;

                init(e.target.value);
            }
        });
    }
    
    const radarModal = document.getElementById('radarModal');
    if (radarModal) {
        radarModal.addEventListener('hidden.bs.modal', () => {
            const iframe = document.getElementById('radarFrame');
            if (iframe) iframe.src = ''; 
        });
    }
});

// ==========================================
// 4. HELPER FUNCTIONS
// ==========================================
function getWindArrowEmoji(direction) {
    if (direction === null || direction === undefined) return "💨";

    if (typeof direction === 'number') {
        const val = Math.floor((direction / 22.5) + 0.5);
        const arr = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
        direction = arr[(val % 16)];
    }

    const map = {
        "N": "⬇️",   "NNE": "⬇️", "NE": "↙️",  "ENE": "↙️", 
        "E": "⬅️",   "ESE": "⬅️", "SE": "↖️",  "SSE": "↖️", 
        "S": "⬆️",   "SSW": "⬆️", "SW": "↗️",  "WSW": "↗️", 
        "W": "➡️",   "WNW": "➡️", "NW": "↘️",  "NNW": "↘️"  
    };

    return map[direction.toUpperCase()] || "💨";
}

function getTeamAbbr(teamName) {
    const map = {
        // MLB Teams
        "Yankees": "NYY", "Mets": "NYM", "Cubs": "CHC", "White Sox": "CWS",
        "Dodgers": "LAD", "Angels": "LAA", "Diamondbacks": "ARI", "Braves": "ATL", 
        "Orioles": "BAL", "Red Sox": "BOS", "Reds": "CIN", "Guardians": "CLE", 
        "Rockies": "COL", "Tigers": "DET", "Astros": "HOU", "Royals": "KC",  
        "Marlins": "MIA", "Brewers": "MIL", "Twins": "MIN", "Athletics": "OAK", 
        "Phillies": "PHI", "Pirates": "PIT", "Padres": "SD",  "Giants": "SF",  
        "Mariners": "SEA", "Cardinals": "STL", "Rays": "TB",   "Rangers": "TEX", 
        "Blue Jays": "TOR", "Nationals": "WSH",
        // WBC Teams
        "United States": "USA", "Japan": "JPN", "Dominican Republic": "DOM",
        "Venezuela": "VEN", "Puerto Rico": "PUR", "Mexico": "MEX",
        "South Korea": "KOR", "Cuba": "CUB", "Canada": "CAN",
        "Netherlands": "NED", "Italy": "ITA", "Israel": "ISR",
        "Great Britain": "GBR", "Australia": "AUS", "Colombia": "COL",
        "Panama": "PAN", "Nicaragua": "NIC", "Chinese Taipei": "TPE", "Czech Republic": "CZE"
    };

    const key = Object.keys(map).find(k => teamName.includes(k));
    return key ? map[key] : "TBD"; 
}

function formatPlayerName(fullName) {
    if (!fullName) return "";
    const parts = fullName.split(" ");
    if (parts.length === 1) return fullName; 
    
    const firstInitial = parts[0].charAt(0);
    const lastName = parts.slice(1).join(" ");
    return `${firstInitial}. ${lastName}`;
}

function getShortTeamName(fullName) {
    if (!fullName) return "";
    
    // MLB Exceptions
    if (fullName.includes("Red Sox")) return "Red Sox";
    if (fullName.includes("White Sox")) return "White Sox";
    if (fullName.includes("Blue Jays")) return "Blue Jays";
    
    // WBC Exceptions
    if (fullName.includes("Dominican Republic")) return "Dom Rep";
    if (fullName.includes("United States")) return "USA";
    if (fullName.includes("Puerto Rico")) return "Puerto Rico";
    if (fullName.includes("South Korea")) return "South Korea";
    if (fullName.includes("Great Britain")) return "Britain";
    if (fullName.includes("Chinese Taipei")) return "Chinese Taipei";
    if (fullName.includes("Czech Republic")) return "Czechia";
    
    const parts = fullName.split(" ");
    return parts[parts.length - 1];
}

window.showRadar = function(url, venueName) {
    const modalElement = document.getElementById('radarModal');
    const modalTitle = document.querySelector('#radarModal .modal-title');
    const iframe = document.getElementById('radarFrame');
    
    if(modalTitle) modalTitle.innerText = `Radar: ${venueName}`;

    const myModal = bootstrap.Modal.getOrCreateInstance(modalElement);

    if(iframe) iframe.src = '';

    const loadMap = function () {
        if(iframe) iframe.src = url; 
        modalElement.removeEventListener('shown.bs.modal', loadMap); 
    };

    modalElement.addEventListener('shown.bs.modal', loadMap);
    myModal.show();
}

function generateMatchupAnalysis(weather, windInfo, isRoofClosed, isRoofPending) {
    if (isRoofClosed) return "✅ <b>Roof Closed:</b> Controlled environment with zero weather impact.";

    let notes = [];

    if (isRoofPending) {
        notes.push("🏟️ <b>Roof Status Pending:</b> Borderline weather. The team may elect to close the roof, neutralizing wind and temperature impacts.");
    }

    if (weather.isThunderstorm) {
        notes.push("⚡ <b>Lightning Risk:</b> Thunderstorms detected. Mandatory 30-minute safety delays are likely.");
    }
    if (weather.isSnow) {
        notes.push("❄️ <b>Snow Risk:</b> Low visibility and slippery field conditions could delay play.");
    }

    let sustainedRainHours = 0;
    if (weather.hourly && weather.hourly.length > 0) {
        sustainedRainHours = weather.hourly.filter(h => h.precipChance >= 60).length;
    }

    if (sustainedRainHours >= 3) {
        notes.push("🌧️ <b>Rainout Risk:</b> Sustained heavy rain. High probability of postponement.");
    } else if (weather.maxPrecipChance >= 70) {
        notes.push("☔ <b>Severe Delay Risk:</b> Heavy rain expected, but should pass. Delays likely.");
    } else if (weather.maxPrecipChance >= 30) {
        notes.push("☔ <b>Delay Risk:</b> Scattered showers could interrupt play.");
    }

    if (weather.humidity <= 30) {
        notes.push("🌵 <b>Dry Air (<30%):</b> Sharp breaking balls (Pitcher Adv), but the ball travels up to 4.5ft farther (Hitter Adv).");
    } else if (weather.humidity >= 70) {
        notes.push("💧 <b>High Humidity (>70%):</b> Breaking balls hang/flatten (Hitter Adv), but the ball travels shorter distances (Pitcher Adv).");
    }

    if (weather.temp >= 85) {
        notes.push("🔥 <b>Hitter Friendly:</b> High temps reduce air density, helping fly balls carry.");
    } else if (weather.temp <= 50) {
        notes.push("❄️ <b>Pitcher Friendly:</b> Cold, dense air suppresses ball flight and scoring.");
    }

    if (weather.windSpeed >= 8) {
        const dir = windInfo ? windInfo.text : "";
        if (dir.includes("Blowing OUT")) notes.push("🚀 <b>Home Runs:</b> Strong wind blowing out creates ideal hitting conditions.");
        else if (dir.includes("Blowing IN")) notes.push("🛑 <b>Suppressed:</b> Wind blowing in will knock down fly balls. Advantage pitchers.");
        else if (dir.includes("Out to Right")) notes.push("↗️ <b>Lefty Advantage:</b> Wind blowing out to Right Field favors <b>Left-Handed</b> power.");
        else if (dir.includes("Out to Left")) notes.push("↖️ <b>Righty Advantage:</b> Wind blowing out to Left Field favors <b>Right-Handed</b> power.");
        else if (dir.includes("In from Right")) notes.push("📉 <b>Lefty Nightmare:</b> Wind blowing in from Right knocks down Lefty power.");
        else if (dir.includes("In from Left")) notes.push("📉 <b>Righty Nightmare:</b> Wind blowing in from Left knocks down Righty power.");
        else if (dir.includes("Cross")) notes.push("↔️ <b>Tricky:</b> Crosswinds may affect outfield defense and breaking balls.");
    }

    if (notes.length === 0) return "✅ <b>Neutral:</b> Fair weather conditions. No significant advantage.";
    return notes.join("<br>");
}

function generateDailyReport() {
    if (ALL_GAMES_DATA.length === 0) {
        alert("No games data available to report!");
        return;
    }

    const sortedGames = [...ALL_GAMES_DATA].sort((a, b) => 
        new Date(a.gameRaw.gameDate) - new Date(b.gameRaw.gameDate)
    );

    const today = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    
    let reportText = `⚾ MLB Spring Training Weather Report for ${today} by https://weathermlb.com\n\n`; 

    sortedGames.forEach(game => {
        const teams = game.gameRaw.teams;
        const w = game.weather || {}; 
        
        const awayName = teams.away.team.name;
        const homeName = teams.home.team.name;
        
        const awayAbbr = getTeamAbbr(awayName);
        const homeAbbr = getTeamAbbr(homeName);
        
        const awayP = teams.away.probablePitcher ? teams.away.probablePitcher.fullName.split(' ').pop() : "TBD";
        const homeP = teams.home.probablePitcher ? teams.home.probablePitcher.fullName.split(' ').pop() : "TBD";
        
        const oddsData = game.odds;
        let awayOddsStr = "[TBD]";
        let homeOddsStr = "[TBD]";
        let totalStr = " • O/U TBD";

        // --- ODDS FIX: Now properly accesses bookmakers array ---
        if (oddsData && oddsData.bookmakers && oddsData.bookmakers.length > 0) {
            const bookie = oddsData.bookmakers.find(b => b.key === 'fanduel') || oddsData.bookmakers[0];
            
            if (bookie && bookie.markets) {
                const h2hMarket = bookie.markets.find(m => m.key === 'h2h');
                if (h2hMarket && h2hMarket.outcomes) {
                    const awayOutcome = h2hMarket.outcomes.find(o => o.name === awayName);
                    const homeOutcome = h2hMarket.outcomes.find(o => o.name === homeName);
                    
                    if (awayOutcome) {
                        awayOddsStr = awayOutcome.price > 0 ? `[+${awayOutcome.price}]` : `[${awayOutcome.price}]`;
                    }
                    if (homeOutcome) {
                        homeOddsStr = homeOutcome.price > 0 ? `[+${homeOutcome.price}]` : `[${homeOutcome.price}]`;
                    }
                }

                const totalsMarket = bookie.markets.find(m => m.key === 'totals');
                if (totalsMarket && totalsMarket.outcomes && totalsMarket.outcomes.length > 0) {
                    totalStr = ` • O/U ${totalsMarket.outcomes[0].point}`;
                }
            }
        }

        let arrow = "💨";
        if (game.wind && game.wind.arrow) {
             arrow = game.wind.arrow;
        } else if (game.weather && game.weather.windDir !== undefined) {
             arrow = getWindArrowEmoji(game.weather.windDir);
        }

        const isRoofClosed = game.roof;
        const rain = isRoofClosed ? 0 : Math.round(Number(w.maxPrecipChance) || 0);
        const temp = Math.round(Number(w.temp) || 0);
        const hum = Math.round(Number(w.humidity) || 0);
        const windSpd = isRoofClosed ? 0 : Math.round(Number(w.windSpeed) || 0);

        let weatherString = `🌧️${rain}% 🌡️${temp}° 💧${hum}% ${arrow}${windSpd}mph`;
        
        if (w.status === "too_early" || w.temp === '--') {
            weatherString = `Forecast Unavailable`;
        } else if (isRoofClosed) {
            weatherString = `Roof Closed 🌡️${temp}° 💧${hum}%`;
        }

        const line = `${awayAbbr} (${awayP}) ${awayOddsStr} @ ${homeAbbr} (${homeP}) ${homeOddsStr}${totalStr}:\n${weatherString}`;
        reportText += line + "\n\n";
    });

    reportText += `#MLB #FantasyBaseball #SpringTraining`;

    const textArea = document.getElementById('tweet-text');
    const twitterLink = document.getElementById('twitter-link');
    
    if (textArea) {
        textArea.value = reportText;

        if (twitterLink) {
            twitterLink.innerHTML = "📋 Copy Full Report & Open X";
            twitterLink.href = "javascript:void(0);"; 
            
            twitterLink.onclick = function() {
                navigator.clipboard.writeText(reportText).then(() => {
                    window.open('https://twitter.com/compose/tweet', '_blank');
                }).catch(err => {
                    textArea.select();
                    document.execCommand('copy');
                    window.open('https://twitter.com/compose/tweet', '_blank');
                });
            };
        }
        
        const modalElement = document.getElementById('tweetModal');
        if (modalElement && typeof bootstrap !== 'undefined') {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
        } else {
             alert("Report generated:\n\n" + reportText);
        }
    }
}
