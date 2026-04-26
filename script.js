// ==========================================
// CONFIGURATION
// ==========================================
const DEFAULT_DATE = new Date().toLocaleDateString('en-CA');

// Global State
let ALL_GAMES_DATA = []; 
let ARE_ALL_EXPANDED = false;
window.HAS_SHOWN_TUTORIAL = false; // Tracks if they've seen the tooltips

// Global CSS injection for our bouncing tutorial tooltips
const mlbStyle = document.createElement('style');
mlbStyle.innerHTML = `
    @keyframes tutorialBounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-5px); }
    }
    .tutorial-tooltip {
        transition: opacity 0.4s ease-out;
        pointer-events: none; /* So they don't block clicks underneath them */
    }
`;
document.head.appendChild(mlbStyle);

// Helper to dismiss the tooltips once the user understands how the site works
window.dismissTutorials = function() {
    window.HAS_SHOWN_TUTORIAL = true;
    document.querySelectorAll('.tutorial-tooltip').forEach(el => {
        el.style.opacity = '0'; // Smooth fade out
        setTimeout(() => el.remove(), 400); // Remove from DOM after fade
    });
};

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
        console.error("The exact error was:", error); 
        
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
                        ℹ️ <strong>Forcast Unavailable this far out from game day:</strong> Detailed weather forecasts and matchup analysis are currently generated up to 7 days in advance.
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
    cardsContainer.className = 'row w-100 m-0 p-0 align-items-start';

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

    // --- NEW: Global Expand/Collapse Button (With Tutorial Tooltip) ---
    if (filteredGames.length > 0) {
        let expandTutorialHtml = '';
        if (!window.HAS_SHOWN_TUTORIAL) {
            expandTutorialHtml = `<div class="tutorial-tooltip text-primary fw-bold mb-1" style="font-size: 0.75rem; animation: tutorialBounce 1.5s infinite;">👇 Click to expand all cards</div>`;
        }

        const toggleRow = document.createElement('div');
        toggleRow.className = 'col-12 text-center mb-3 mt-1 position-relative';
        toggleRow.innerHTML = `
            ${expandTutorialHtml}
            <button class="btn btn-sm shadow-sm fw-bold px-4 py-1" style="background-color: #fff; border: 1px solid #dee2e6; color: #495057; border-radius: 20px;" onclick="window.toggleAllWeatherCards()">
                <span id="expand-toggle-icon">${ARE_ALL_EXPANDED ? '▲' : '▼'}</span> 
                <span id="expand-toggle-text">${ARE_ALL_EXPANDED ? 'Collapse All Cards' : 'Expand All Cards'}</span>
            </button>
        `;
        container.appendChild(toggleRow);
    }

    // --- NEW: First Ribbon Tutorial Pointer ---
    if (!window.HAS_SHOWN_TUTORIAL && cardsContainer.firstChild) {
        const firstWrapper = cardsContainer.firstChild; // The column wrapper, outside the card
        if (firstWrapper) {
            firstWrapper.classList.add('position-relative'); // Anchor the absolute tooltip here
            
            const pointer = document.createElement('div');
            pointer.className = 'tutorial-tooltip badge bg-primary position-absolute shadow-sm border border-light';
            // Attached to the wrapper, it completely bypasses the overflow:hidden on the card!
            pointer.style.cssText = 'top: -12px; right: 15px; font-size: 0.65rem; animation: tutorialBounce 1.5s infinite; z-index: 10; pointer-events: none;';
            pointer.innerHTML = '👇 Click to expand';
            firstWrapper.appendChild(pointer);
        }
        
        // Auto-dismiss the tooltips after 8 seconds if they haven't clicked anything
        setTimeout(window.dismissTutorials, 8000);
    }

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
            if (isRoofPending) {
                borderClass = "border-warning border-3"; // Downgrade to yellow for retractable roofs
            } else {
                borderClass = "border-danger border-3"; // Keep red for open-air stadiums
            }
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

    // --- 1. CROSS PROMO LINK ---
    const crossPromoHtml = `
        <div class="px-2 pt-2 pb-1 w-100 border-top mt-1 mb-1">
            <a href="https://mlbstartingnine.com/#game-${game.gamePk}" target="_blank" class="btn btn-sm w-100 text-decoration-none shadow-sm" style="background-color: #f8f9fa; border: 1px solid #dee2e6; color: #0d6efd; font-weight: 700; font-size: 0.75rem;">
                📋 View Projected/Starting Lineups
            </a>
        </div>
    `;

    // --- 2. ODDS ENGINE (COMPACT BADGES) ---
    const oddsData = data.odds; 
    let mlAwayBadge = `<span class="badge bg-light text-muted border" style="font-size: 0.65rem;">TBD</span>`; 
    let mlHomeBadge = `<span class="badge bg-light text-muted border" style="font-size: 0.65rem;">TBD</span>`;
    let totalBadgeHtml = ``;

    if (oddsData && oddsData.bookmakers && oddsData.bookmakers.length > 0) {
        let selectedBook = oddsData.bookmakers.find(b => b.key === 'fanduel') || oddsData.bookmakers[0];
        
        if (selectedBook && selectedBook.markets) {
            const h2hMarket = selectedBook.markets.find(m => m.key === 'h2h');
            if (h2hMarket && h2hMarket.outcomes) {
                const awayOutcome = h2hMarket.outcomes.find(o => o.name === awayName);
                const homeOutcome = h2hMarket.outcomes.find(o => o.name === homeName);
                if (awayOutcome) {
                    const price = awayOutcome.price > 0 ? `+${awayOutcome.price}` : awayOutcome.price;
                    mlAwayBadge = `<span class="badge bg-light text-dark border" style="font-size: 0.65rem;">${price}</span>`;
                }
                if (homeOutcome) {
                    const price = homeOutcome.price > 0 ? `+${homeOutcome.price}` : homeOutcome.price;
                    mlHomeBadge = `<span class="badge bg-light text-dark border" style="font-size: 0.65rem;">${price}</span>`;
                }
            }

            const totalsMarket = selectedBook.markets.find(m => m.key === 'totals');
            if (totalsMarket && totalsMarket.outcomes && totalsMarket.outcomes.length > 0) {
                const gameTotal = totalsMarket.outcomes[0].point; 
                totalBadgeHtml = `<span class="badge bg-secondary ms-1" style="font-size: 0.65rem;">O/U ${gameTotal}</span>`;
            }
        }
    }
    let weatherHtml = `<div class="text-muted p-3 text-center small">Weather forecast unavailable.<br></div>`;

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
                    let dateObj;
                    if (h.timestamp) {
                        dateObj = new Date(h.timestamp);
                    } else {
                        dateObj = new Date();
                        dateObj.setHours(h.hour, 0, 0, 0); 
                    }

                    const hour12 = dateObj.getHours() % 12 || 12;
                    const ampm = dateObj.getHours() >= 12 ? 'PM' : 'AM';
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
            
            let windArrow = windInfo ? `<span class="arrow-emoji">${windInfo.arrow}</span>` : "💨";
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

    const weatherEmojiLine = getWeatherEmojiString(data);
    const showRibbon = ARE_ALL_EXPANDED ? 'none' : 'block';
    const showFull = ARE_ALL_EXPANDED ? 'block' : 'none';

    gameCard.innerHTML = `
        <div class="card game-card shadow-sm ${borderClass} ${bgClass}" style="overflow: hidden;">
            
            <div class="ribbon-view p-2 position-relative" onclick="toggleSingleCard(event, '${game.gamePk}')" style="cursor: pointer; display: ${showRibbon};">
                
                <div class="d-flex align-items-center mb-1">
                    <span class="badge ${timeBadgeClass} flex-shrink-0 px-2 py-1" style="font-size: 0.65rem;">${gameTime}</span>
                    <div class="fw-bold text-dark text-center flex-grow-1 ms-2" style="font-size: 0.75rem; letter-spacing: 0.2px;">
                        ${weatherEmojiLine}
                    </div>
                </div>
                
                <div class="d-flex align-items-center mt-1" style="gap: 4px;">
                    <div class="d-flex align-items-center flex-shrink-0" style="gap: 3px;">
                        <img src="${awayLogo}" style="width: 16px; height: 16px; object-fit: contain;" onerror="this.style.display='none'">
                        <span class="fw-bold text-dark lh-1" style="font-size: 0.75rem; letter-spacing: -0.3px;">${awayShortName}</span>
                    </div>
                    
                    <span class="fw-bold text-muted flex-shrink-0 lh-1" style="font-size: 0.7rem;">@</span>
                    
                    <div class="d-flex align-items-center flex-shrink-0" style="gap: 3px;">
                        <img src="${homeLogo}" style="width: 16px; height: 16px; object-fit: contain;" onerror="this.style.display='none'">
                        <span class="fw-bold text-dark lh-1" style="font-size: 0.75rem; letter-spacing: -0.3px;">${homeShortName}</span>
                    </div>

                    <div class="text-truncate text-end fw-bold flex-grow-1 ms-1" style="font-size: 0.7rem; opacity: 0.75;">${game.venue?.name || 'TBD'}</div>
                </div>
                
            </div>

            <div class="full-card-view" onclick="toggleSingleCard(event, '${game.gamePk}')" style="cursor: pointer; display: ${showFull};">
                <div class="card-body px-2 pt-2 pb-2"> 
                    
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div class="d-flex align-items-center">
                            <span class="badge ${timeBadgeClass}">${gameTime}</span>
                            ${totalBadgeHtml}
                        </div>
                        <span class="stadium-name text-truncate text-end flex-grow-1 ms-2" style="font-size: 0.8rem; font-weight: 600;">${game.venue?.name || 'TBD'}</span>
                    </div>
                    
                    <div class="d-flex justify-content-between align-items-center px-1 mb-1">
                        <div class="d-flex align-items-center text-truncate" style="width: 45%; min-width: 0;"> 
                            <img src="${awayLogo}" alt="${awayName}" class="me-2" style="width: 20px; height: 20px; object-fit: contain; filter: drop-shadow(0px 1px 1px rgba(0,0,0,0.1));" onerror="this.style.display='none'">
                            <div class="fw-bold lh-sm text-dark text-truncate" style="font-size: 0.95rem; letter-spacing: -0.3px;">${awayShortName}</div>
                        </div>
                        
                        <div class="text-center text-muted fw-bold" style="width: 10%; font-size: 0.8rem;">@</div>
                        
                        <div class="d-flex align-items-center justify-content-end text-truncate" style="width: 45%; min-width: 0;"> 
                            <img src="${homeLogo}" alt="${homeName}" class="me-2" style="width: 20px; height: 20px; object-fit: contain; filter: drop-shadow(0px 1px 1px rgba(0,0,0,0.1));" onerror="this.style.display='none'">
                            <div class="fw-bold lh-sm text-dark text-truncate text-end" style="font-size: 0.95rem; letter-spacing: -0.3px;">${homeShortName}</div>
                        </div>
                    </div>

                    <div class="d-flex justify-content-between align-items-center px-1 mb-2">
                        <div class="d-flex align-items-center text-truncate" style="width: 48%;">
                            <span class="text-muted text-truncate me-2" style="font-size: 0.75rem;">${awayPitcher}</span>
                            ${mlAwayBadge}
                        </div>
                        <div class="d-flex align-items-center justify-content-end text-truncate" style="width: 48%;">
                            <span class="text-muted text-truncate me-2 text-end" style="font-size: 0.75rem;">${homePitcher}</span>
                            ${mlHomeBadge}
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
    
    init(DEFAULT_DATE);

    const searchInput = document.getElementById('team-search');
    const sortSelect = document.getElementById('sort-filter');
    const riskToggle = document.getElementById('risk-only');
    
    if(searchInput) searchInput.addEventListener('input', renderGames);
    if(sortSelect) sortSelect.addEventListener('change', renderGames);
    if(riskToggle) riskToggle.addEventListener('change', renderGames);

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
        "Yankees": "NYY", "Mets": "NYM", "Cubs": "CHC", "White Sox": "CWS",
        "Dodgers": "LAD", "Angels": "LAA", "Diamondbacks": "ARI", "Braves": "ATL", 
        "Orioles": "BAL", "Red Sox": "BOS", "Reds": "CIN", "Guardians": "CLE", 
        "Rockies": "COL", "Tigers": "DET", "Astros": "HOU", "Royals": "KC",  
        "Marlins": "MIA", "Brewers": "MIL", "Twins": "MIN", "Athletics": "OAK", 
        "Phillies": "PHI", "Pirates": "PIT", "Padres": "SD",  "Giants": "SF",  
        "Mariners": "SEA", "Cardinals": "STL", "Rays": "TB",   "Rangers": "TEX", 
        "Blue Jays": "TOR", "Nationals": "WSH",
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
    if (fullName.includes("Diamondbacks")) return "Dbacks"; // <-- Added Dbacks fix!
    
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

    if (!isRoofPending) {
        notes.push("🏟️ <b>Roof Status Pending:</b> Borderline weather. The team may elect to close the roof, neutralizing wind and temperature impacts.");
    }

    if (weather.isThunderstorm) {
        if (isRoofPending) {
            notes.push("⚡ <b>Lightning Risk:</b> Thunderstorms detected. Possible brief delay for roof closure, but no risk of postponement.");
        } else {
            notes.push("⚡ <b>Lightning Risk:</b> Thunderstorms detected. Mandatory 30-minute safety delays are likely.");
        }
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

function getWeatherEmojiString(data) {
    const w = data.weather || {};
    let arrow = "💨";
    if (data.wind && data.wind.arrow) {
         arrow = data.wind.arrow;
    } else if (w.windDir !== undefined) {
         arrow = getWindArrowEmoji(w.windDir);
    }

    const isRoofClosed = data.roof;
    const rain = isRoofClosed ? 0 : Math.round(Number(w.maxPrecipChance) || 0);
    const temp = Math.round(Number(w.temp) || 0);
    const hum = Math.round(Number(w.humidity) || 0);
    const windSpd = isRoofClosed ? 0 : Math.round(Number(w.windSpeed) || 0);

    if (w.status === "too_early" || w.temp === '--' || w.temp === undefined) {
        return `Forecast Unavailable`;
    } else if (isRoofClosed) {
        return `Roof Closed 🌡️${temp}° 💧${hum}%`;
    }
    return `🌧️${rain}% 🌡️${temp}° 💧${hum}% ${arrow}${windSpd}mph`;
}

// --- NEW STATE HANDLERS ---
window.toggleSingleCard = function(e, gamePk) {
    if (e && e.target.closest('a, button, input, label, [data-bs-toggle="collapse"]')) {
        return; 
    }
    if (window.dismissTutorials) window.dismissTutorials();

    const card = document.getElementById(`game-${gamePk}`);
    if (!card) return;
    
    const ribbon = card.querySelector('.ribbon-view');
    const full = card.querySelector('.full-card-view');
    
    if (ribbon.style.display === 'none') {
        ribbon.style.display = 'block';
        full.style.display = 'none';
    } else {
        ribbon.style.display = 'none';
        full.style.display = 'block';
    }
};

window.toggleAllWeatherCards = function() {
    if (window.dismissTutorials) window.dismissTutorials();
    ARE_ALL_EXPANDED = !ARE_ALL_EXPANDED;
    
    const btnText = document.getElementById('expand-toggle-text');
    const btnIcon = document.getElementById('expand-toggle-icon');
    if (btnText && btnIcon) {
        btnText.innerText = ARE_ALL_EXPANDED ? 'Collapse All Cards' : 'Expand All Cards';
        btnIcon.innerText = ARE_ALL_EXPANDED ? '▲' : '▼';
    }
    
    document.querySelectorAll('.game-card').forEach(card => {
        const ribbon = card.querySelector('.ribbon-view');
        const full = card.querySelector('.full-card-view');
        if (ribbon && full) {
            ribbon.style.display = ARE_ALL_EXPANDED ? 'none' : 'block';
            full.style.display = ARE_ALL_EXPANDED ? 'block' : 'none';
        }
    });
};

function generateDailyReport() {
    if (ALL_GAMES_DATA.length === 0) {
        alert("No games data available to report!");
        return;
    }

    const sortedGames = [...ALL_GAMES_DATA].sort((a, b) => 
        new Date(a.gameRaw.gameDate) - new Date(b.gameRaw.gameDate)
    );

    const today = new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    
    let reportText = `⚾ MLB Weather Report for ${today} by https://weathermlb.com\n\n`; 

    sortedGames.forEach(game => {
        const teams = game.gameRaw.teams;
        
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

        const weatherString = getWeatherEmojiString(game);
        const line = `${awayAbbr} (${awayP}) ${awayOddsStr} @ ${homeAbbr} (${homeP}) ${homeOddsStr}${totalStr}:\n${weatherString}`;
        reportText += line + "\n\n";
    });

    reportText += `#MLB #FantasyBaseball #MLBWeather`;

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
