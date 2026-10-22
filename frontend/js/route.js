/**
 * Route Optimization and UI Controller for Smart Route AI
 */

let currentRouteResponse = null;

// Format minutes into "Xh Ym" or "Y mins"
function formatDuration(minutes) {
  const m = Math.round(minutes);
  if (m < 60) return `${m} mins`;
  const hrs = Math.floor(m / 60);
  const remMins = m % 60;
  return `${hrs}h ${remMins}m`;
}

// Multi-stage loading progress simulator
async function runLoadingStages(onStage) {
  const stages = [
    { text: "Validating locations and geocoding coordinates...", pct: 20, delay: 250 },
    { text: "Querying OSRM driving corridors & alternative paths...", pct: 45, delay: 300 },
    { text: "Evaluating traffic congestion and corridor delay factors...", pct: 65, delay: 250 },
    { text: "Retrieving weather conditions and visibility metrics...", pct: 80, delay: 250 },
    { text: "Computing vehicle mileage, fuel, and journey costs...", pct: 90, delay: 200 },
    { text: "Calculating multi-factor Smart Scores & AI explanations...", pct: 98, delay: 200 },
  ];

  for (const s of stages) {
    onStage(s.text, s.pct);
    await new Promise((r) => setTimeout(r, s.delay));
  }
}

/**
 * Executes route calculation API call
 */
async function calculateSmartRoute(formData) {
  const loadingCard = document.getElementById("loadingCard");
  const loadingText = document.getElementById("loadingText");
  const loadingBar = document.getElementById("loadingBar");
  const submitBtn = document.getElementById("submitBtn");

  try {
    // Show loading state
    loadingCard.classList.add("active");
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>⏳ Optimizing...</span>`;

    // Start UI stages concurrently
    const loadingPromise = runLoadingStages((text, pct) => {
      loadingText.textContent = text;
      loadingBar.style.width = `${pct}%`;
    });

    // Make API request
    const response = await fetch("/api/routes/calculate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    });

    await loadingPromise;

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.detail || "Unable to calculate route.");
    }

    currentRouteResponse = data;

    // Render components
    renderRecommendationCard(data.recommended_route, data.explanation);
    renderComparisonCards(data.routes);
    renderComparisonTable(data.routes);
    updateCompareBanner(data);
    renderRoutesOnMap(data);
    renderAnalyticsCharts(data.routes);

    // Refresh history list if open
    if (typeof loadHistoryList === "function") {
      loadHistoryList();
    }

    showToast("Route successfully optimized!", "success");

    // Scroll slightly to view map and recommendation
    const recSection = document.getElementById("recommendationSection");
    if (recSection) {
      recSection.style.display = "block";
    }
  } catch (err) {
    console.error("Route calculation error:", err);
    showToast(err.message, "error");
  } finally {
    loadingCard.classList.remove("active");
    submitBtn.disabled = false;
    submitBtn.innerHTML = `<span>✨ FIND SMART ROUTE</span>`;
  }
}

/**
 * Updates Corridor Context Banner in Compare Tab
 */
function updateCompareBanner(data) {
  const banner = document.getElementById("compareCorridorBanner");
  const srcEl = document.getElementById("compareCorridorSource");
  const destEl = document.getElementById("compareCorridorDest");
  const countEl = document.getElementById("compareRouteCountBadge");
  const prefEl = document.getElementById("comparePreferenceBadge");

  if (!banner) return;
  banner.style.display = "flex";

  if (srcEl) srcEl.textContent = data.source ? data.source.display_name.split(",")[0] : "Origin";
  if (destEl) destEl.textContent = data.destination ? data.destination.display_name.split(",")[0] : "Destination";
  if (countEl) countEl.textContent = `${(data.routes || []).length} Corridors Evaluated`;
  if (prefEl) prefEl.textContent = `Vehicle: ${data.vehicle_type || 'Car'} | Preference: ${(data.applied_weights ? 'Custom' : 'Balanced')}`;
}

/**
 * Displays AI Recommended Route Card & Dynamic Breakdown
 */
function renderRecommendationCard(rec, explanation) {
  const section = document.getElementById("recommendationSection");
  if (section) section.style.display = "block";

  // Name & Score
  const nameEl = document.getElementById("recRouteName");
  if (nameEl) nameEl.textContent = rec.route_name;
  const scoreEl = document.getElementById("recSmartScore");
  if (scoreEl) scoreEl.textContent = Math.round(rec.smart_score);

  // Key Metrics
  const distEl = document.getElementById("recDistance");
  if (distEl) distEl.textContent = `${rec.distance_km} km`;
  const durEl = document.getElementById("recDuration");
  if (durEl) durEl.textContent = formatDuration(rec.duration_minutes);

  // Traffic badge
  const trafLevel = rec.traffic.level;
  const trafBadge = document.getElementById("recTraffic");
  if (trafBadge) {
    trafBadge.textContent = trafLevel;
    trafBadge.style.color = trafLevel === "LOW" ? "#10B981" : trafLevel === "MODERATE" ? "#F59E0B" : "#EF4444";
  }

  // Weather badge
  const weathEl = document.getElementById("recWeather");
  if (weathEl) weathEl.textContent = `${rec.weather.condition} (${rec.weather.temperature_c}°C)`;

  // Safety
  const safeEl = document.getElementById("recSafety");
  if (safeEl) {
    safeEl.textContent = `${rec.safety.score} / 100`;
    safeEl.style.color = rec.safety.color;
  }

  // Fuel & Cost
  const fuelEl = document.getElementById("recFuel");
  if (fuelEl) fuelEl.textContent = `${rec.fuel.fuel_liters} L`;
  const costEl = document.getElementById("recCost");
  if (costEl) costEl.textContent = `₹${Math.round(rec.fuel.fuel_cost)}`;

  // Why this route narrative
  const headEl = document.getElementById("whyHeadline");
  if (headEl) headEl.textContent = explanation.headline || "Why This Route is Recommended";
  const sumEl = document.getElementById("whySummary");
  if (sumEl) sumEl.textContent = explanation.summary || "";

  // Dynamic advantages list
  const prosList = document.getElementById("prosList");
  if (prosList) {
    prosList.innerHTML = "";
    (explanation.advantages || []).forEach((adv) => {
      const li = document.createElement("li");
      li.className = "pros-item";
      li.innerHTML = `<span>✓</span> <span>${adv}</span>`;
      prosList.appendChild(li);
    });
  }

  // Dynamic caveats list
  const caveatsList = document.getElementById("caveatsList");
  if (caveatsList) {
    caveatsList.innerHTML = "";
    (explanation.caveats || []).forEach((cav) => {
      const li = document.createElement("li");
      li.className = "caveat-item";
      li.innerHTML = `<span>⚠</span> <span>${cav}</span>`;
      caveatsList.appendChild(li);
    });
  }

  // Smart Score Breakdown meters
  const b = rec.score_breakdown || {};
  renderBreakdownMeter("meterTime", "scoreTime", b.travel_time);
  renderBreakdownMeter("meterTraffic", "scoreTraffic", b.traffic);
  renderBreakdownMeter("meterSafety", "scoreSafety", b.safety);
  renderBreakdownMeter("meterWeather", "scoreWeather", b.weather);
  renderBreakdownMeter("meterFuel", "scoreFuel", b.fuel);
  renderBreakdownMeter("meterDistance", "scoreDistance", b.distance);

  const totalEl = document.getElementById("scoreTotal");
  if (totalEl) totalEl.textContent = `${Math.round(b.total || rec.smart_score)} / 100`;
}

function renderBreakdownMeter(barId, labelId, item) {
  if (!item) return;
  const bar = document.getElementById(barId);
  const label = document.getElementById(labelId);
  if (bar) {
    const pct = item.max > 0 ? (item.score / item.max) * 100 : 0;
    bar.style.width = `${pct}%`;
  }
  if (label) {
    label.textContent = `${item.score} / ${item.max}`;
  }
}

/**
 * Renders Side-by-Side Specific Route Cards in Compare Tab
 */
function renderComparisonCards(routes) {
  const container = document.getElementById("comparisonCardsContainer");
  if (!container || !routes || routes.length === 0) return;

  container.innerHTML = "";

  routes.forEach((r, idx) => {
    const card = document.createElement("div");
    card.className = `compare-route-card ${r.is_recommended ? "is-recommended" : ""}`;
    card.id = `compareCard_${r.route_id}`;

    const trafColor = r.traffic.level === "LOW" ? "#10B981" : r.traffic.level === "MODERATE" ? "#F59E0B" : "#EF4444";
    const tagsHtml = (r.tags || [])
      .map((t) => `<span class="route-tag-pill ${t.type}">${t.label}</span>`)
      .join("");

    const highwaysText = r.major_highways ? r.major_highways.join(" • ") : (r.via_summary || "Highway Corridor");

    card.innerHTML = `
      <div class="compare-score-badge">
        ${Math.round(r.smart_score)} <span style="font-size: 0.75rem; font-weight: 600;">/ 100</span>
      </div>

      <div>
        <div class="compare-card-badge-row">
          ${tagsHtml}
        </div>

        <h4 class="compare-card-title">${r.route_name}</h4>
        
        <div class="compare-card-highways">
          <span>🛣️</span> <span>${highwaysText}</span>
        </div>

        <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; font-size: 0.78rem;">
          <span style="background: var(--bg-tertiary); padding: 2px 8px; border-radius: 4px; border: 1px solid var(--border-color); color: var(--text-secondary);">
            🏗️ ${r.road_type || "Divided Expressway"}
          </span>
          <span style="background: var(--bg-tertiary); padding: 2px 8px; border-radius: 4px; border: 1px solid var(--border-color); color: var(--text-secondary);">
            💳 ${r.toll_info || "Toll-Free"}
          </span>
        </div>

        <div class="compare-card-metrics">
          <div class="compare-metric-item">
            <span class="compare-metric-label">Distance</span>
            <span class="compare-metric-value">${r.distance_km} km</span>
          </div>
          <div class="compare-metric-item">
            <span class="compare-metric-label">Transit Time</span>
            <span class="compare-metric-value">${formatDuration(r.duration_minutes)}</span>
          </div>
          <div class="compare-metric-item">
            <span class="compare-metric-label">Traffic Flow</span>
            <span class="compare-metric-value" style="color: ${trafColor}">${r.traffic.level}</span>
          </div>
          <div class="compare-metric-item">
            <span class="compare-metric-label">Safety Index</span>
            <span class="compare-metric-value" style="color: ${r.safety.color}">${r.safety.score}/100</span>
          </div>
          <div class="compare-metric-item">
            <span class="compare-metric-label">Weather</span>
            <span class="compare-metric-value">${r.weather.condition} (${r.weather.temperature_c}°C)</span>
          </div>
          <div class="compare-metric-item">
            <span class="compare-metric-label">Fuel & Cost</span>
            <span class="compare-metric-value">${r.fuel.fuel_liters}L (₹${Math.round(r.fuel.fuel_cost)})</span>
          </div>
        </div>
      </div>

      <div class="compare-card-actions">
        <button class="btn-compare-action primary" onclick="activateRouteFromCompare('${r.route_id}')">
          <span>🗺️ View on Map</span>
        </button>
        <button class="btn-compare-action secondary" onclick="inspectRouteDetails('${r.route_id}')">
          <span>🔍 Deep Breakdown</span>
        </button>
      </div>
    `;

    container.appendChild(card);
  });
}

/**
 * Renders the Multi-Factor Route Comparison Table
 */
function renderComparisonTable(routes) {
  const tbody = document.getElementById("comparisonTableBody");
  if (!tbody || !routes || routes.length === 0) return;
  tbody.innerHTML = "";

  routes.forEach((r) => {
    const tr = document.createElement("tr");
    if (r.is_recommended) {
      tr.className = "highlight-recommended";
    }

    const trafColor = r.traffic.level === "LOW" ? "#10B981" : r.traffic.level === "MODERATE" ? "#F59E0B" : "#EF4444";

    tr.innerHTML = `
      <td>
        <strong style="color: ${r.is_recommended ? "#10B981" : "inherit"}; font-size: 0.95rem;">${r.route_name}</strong>
        ${r.is_recommended ? '<span style="font-size: 10px; background: #10B981; color: #fff; padding: 2px 6px; border-radius: 4px; margin-left: 6px; font-weight: 800;">RECOMMENDED</span>' : ""}
        <div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">
          🛣️ ${r.via_summary || "Highway Corridor"} | 🏗️ ${r.road_type || "Divided Highway"}
        </div>
      </td>
      <td><strong>${r.distance_km} km</strong></td>
      <td>
        <strong>${formatDuration(r.duration_minutes)}</strong>
        ${r.traffic.delay_minutes > 0 ? `<div style="font-size: 11px; color: #EF4444;">+${Math.round(r.traffic.delay_minutes)}m delay</div>` : '<div style="font-size: 11px; color: #10B981;">Smooth</div>'}
      </td>
      <td><span style="font-weight: 700; color: ${trafColor}">${r.traffic.level} (${r.traffic.score}/100)</span></td>
      <td>${r.weather.condition} (${r.weather.temperature_c}°C)</td>
      <td><span style="font-weight: 700; color: ${r.safety.color}">${r.safety.score}/100</span></td>
      <td>${r.fuel.fuel_liters} L <span style="font-size: 11px; color: var(--text-muted);">(~₹${Math.round(r.fuel.fuel_cost)})</span></td>
      <td>
        <span style="font-size: 1.15rem; font-weight: 800; color: ${r.is_recommended ? "#10B981" : "inherit"}">
          ${Math.round(r.smart_score)}
        </span> / 100
      </td>
      <td>
        <button class="btn-xs" onclick="activateRouteFromCompare('${r.route_id}')" style="display: flex; align-items: center; gap: 4px; padding: 6px 12px; font-weight: 700;">
          <span>🗺️ Map</span>
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

/**
 * Activates a specific route on the interactive Leaflet map and switches to the Dashboard
 */
function activateRouteFromCompare(routeId) {
  if (typeof highlightRouteOnMap === "function") {
    highlightRouteOnMap(routeId);
  }
  switchTab("dashboard");
  showToast(`Switched active corridor to ${routeId.replace('_', ' ').toUpperCase()} on map!`, "info");
}

/**
 * Deep-dive route inspector in the compare tab
 */
function inspectRouteDetails(routeId) {
  if (!currentRouteResponse || !currentRouteResponse.routes) return;
  const route = currentRouteResponse.routes.find((r) => r.route_id === routeId);
  if (!route) return;

  // Highlight card
  document.querySelectorAll(".compare-route-card").forEach((c) => c.classList.remove("is-active-inspect"));
  const activeCard = document.getElementById(`compareCard_${routeId}`);
  if (activeCard) activeCard.classList.add("is-active-inspect");

  const container = document.getElementById("comparisonInspectorContainer");
  if (!container) return;
  container.style.display = "block";

  const b = route.score_breakdown || {};
  const trafColor = route.traffic.level === "LOW" ? "#10B981" : route.traffic.level === "MODERATE" ? "#F59E0B" : "#EF4444";

  container.innerHTML = `
    <div style="background: var(--bg-tertiary); border: 1px solid var(--border-color); border-radius: var(--radius-lg); padding: 22px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 18px; border-bottom: 1px solid var(--border-color); padding-bottom: 14px;">
        <div>
          <span style="font-size: 0.8rem; font-weight: 800; color: var(--accent-primary); text-transform: uppercase;">Deep-Dive Corridor Analysis</span>
          <h3 style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); margin-top: 4px;">${route.route_name}</h3>
        </div>
        <div style="display: flex; gap: 10px; align-items: center;">
          <span style="font-size: 1.3rem; font-weight: 800; color: #10B981;">${Math.round(route.smart_score)} / 100</span>
          <button class="btn-primary" onclick="activateRouteFromCompare('${route.route_id}')" style="padding: 8px 16px; font-size: 0.85rem;">
            <span>🗺️ Activate & Focus on Map</span>
          </button>
        </div>
      </div>

      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px;">
        <!-- Column 1: Highway & Road Quality -->
        <div style="background: var(--bg-card); padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
          <h4 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 12px; color: var(--text-primary);">🛣️ Corridor & Infrastructure</h4>
          <p style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 8px;"><strong>Via:</strong> ${route.via_summary || "National Highway"}</p>
          <p style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 8px;"><strong>Road Profile:</strong> ${route.road_type || "Divided Multi-Lane Highway"}</p>
          <p style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 8px;"><strong>Tolls & Tariffs:</strong> ${route.toll_info || "Toll-Free Route"}</p>
          <p style="font-size: 0.88rem; color: var(--text-secondary);"><strong>Provider:</strong> ${route.source_provider}</p>
        </div>

        <!-- Column 2: Environmental & Real-Time Friction -->
        <div style="background: var(--bg-card); padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
          <h4 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 12px; color: var(--text-primary);">🚦 Traffic & Environmental Friction</h4>
          <p style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 8px;"><strong>Traffic Level:</strong> <span style="font-weight: 700; color: ${trafColor}">${route.traffic.level} (${route.traffic.score}/100)</span></p>
          <p style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 8px;"><strong>Congestion Delay:</strong> ${Math.round(route.traffic.delay_minutes || 0)} mins added</p>
          <p style="font-size: 0.88rem; color: var(--text-secondary); margin-bottom: 8px;"><strong>Weather Conditions:</strong> ${route.weather.condition} (${route.weather.temperature_c}°C, Wind ${route.weather.wind_speed_kmh} km/h)</p>
          <p style="font-size: 0.88rem; color: var(--text-secondary);"><strong>Safety Grade:</strong> ${route.safety.score}/100 (${route.safety.category || 'High Safety'})</p>
        </div>

        <!-- Column 3: Multi-Factor Score Allocation -->
        <div style="background: var(--bg-card); padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--border-color);">
          <h4 style="font-size: 0.95rem; font-weight: 700; margin-bottom: 12px; color: var(--text-primary);">⚖️ Multi-Factor Score Breakdown</h4>
          <div style="font-size: 0.82rem; display: flex; flex-direction: column; gap: 6px;">
            <div style="display: flex; justify-content: space-between;"><span>Time Efficiency:</span> <strong>${b.travel_time ? b.travel_time.score : '-'}/${b.travel_time ? b.travel_time.max : '-'}</strong></div>
            <div style="display: flex; justify-content: space-between;"><span>Traffic Flow:</span> <strong>${b.traffic ? b.traffic.score : '-'}/${b.traffic ? b.traffic.max : '-'}</strong></div>
            <div style="display: flex; justify-content: space-between;"><span>Corridor Safety:</span> <strong>${b.safety ? b.safety.score : '-'}/${b.safety ? b.safety.max : '-'}</strong></div>
            <div style="display: flex; justify-content: space-between;"><span>Weather Quality:</span> <strong>${b.weather ? b.weather.score : '-'}/${b.weather ? b.weather.max : '-'}</strong></div>
            <div style="display: flex; justify-content: space-between;"><span>Fuel Economy:</span> <strong>${b.fuel ? b.fuel.score : '-'}/${b.fuel ? b.fuel.max : '-'}</strong></div>
          </div>
        </div>
      </div>
    </div>
  `;

  container.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

/**
 * Toast Notification Utility
 */
function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const icon = type === "success" ? "✓" : type === "error" ? "⚠" : "ℹ";
  toast.innerHTML = `<span>${icon}</span> <span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.remove();
  }, 4000);
}
