/**
 * Main Application Orchestrator for Smart Route AI
 */

let emergencyMode = false;
let demoMode = false;
let appSettings = null;

document.addEventListener("DOMContentLoaded", async () => {
  // 1. Initialize Map with CARTO Basemap
  initMap();

  // 2. Load API & System Settings
  await loadSystemSettings();

  // 3. Register Navigation Tabs
  setupNavigationTabs();

  // 4. Form Submit Listener
  setupFormListener();

  // 5. Setup Quick Chips & Swap
  setupQuickChipsAndSwap();

  // 6. Setup Emergency & Theme Toggles
  setupControls();

  // 7. Initial History Fetch
  loadHistoryList();

  // 8. Auto-calculate default demonstration route (Ballari -> Bengaluru)
  const defaultSource = document.getElementById("sourceInput").value;
  const defaultDest = document.getElementById("destInput").value;
  if (defaultSource && defaultDest) {
    calculateSmartRoute({
      source: defaultSource,
      destination: defaultDest,
      vehicle_type: "car",
      preference: "balanced",
      emergency_mode: false,
      demo_mode: false,
    });
  }
});

/**
 * Tab Navigation Routing
 */
function setupNavigationTabs() {
  const navItems = document.querySelectorAll(".nav-item");
  navItems.forEach((item) => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");
      switchTab(tabId);
    });
  });
}

function switchTab(tabId) {
  // Update nav links
  document.querySelectorAll(".nav-item").forEach((nav) => {
    nav.classList.toggle("active", nav.getAttribute("data-tab") === tabId);
  });

  // Update tab panes
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.toggle("active", pane.id === `tab-${tabId}`);
  });

  // If map tab, trigger map invalidateSize to ensure tiles fill container
  if (tabId === "dashboard" && mapInstance) {
    setTimeout(() => {
      mapInstance.invalidateSize();
      recenterMap();
    }, 100);
  }

  if (tabId === "compare") {
    if (currentRouteResponse && currentRouteResponse.routes) {
      renderComparisonCards(currentRouteResponse.routes);
      renderComparisonTable(currentRouteResponse.routes);
      updateCompareBanner(currentRouteResponse);
    }
  }

  if (tabId === "analytics") {
    if (currentRouteResponse && currentRouteResponse.routes) {
      renderAnalyticsCharts(currentRouteResponse.routes);
    }
  }

  if (tabId === "history") {
    loadHistoryList();
  }

  if (tabId === "settings") {
    loadApiStatus();
  }
}

/**
 * Form Submission Handling
 */
function setupFormListener() {
  const form = document.getElementById("routeForm");
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const source = document.getElementById("sourceInput").value.trim();
    const destination = document.getElementById("destInput").value.trim();
    const vehicleTypeEl = document.getElementById("vehicleSelect");
    const preferenceEl = document.getElementById("preferenceSelect");
    const vehicleType = vehicleTypeEl ? vehicleTypeEl.value : "car";
    const preference = preferenceEl ? preferenceEl.value : "balanced";
    const fuelPriceEl = document.getElementById("fuelPriceInput");
    const fuelPriceVal = fuelPriceEl ? parseFloat(fuelPriceEl.value) : 102.5;

    if (!source || !destination) {
      showToast("Please enter both source and destination locations.", "error");
      return;
    }

    calculateSmartRoute({
      source,
      destination,
      vehicle_type: vehicleType,
      preference: preference,
      emergency_mode: emergencyMode,
      fuel_price: fuelPriceVal || 102.5,
      demo_mode: demoMode,
    });
  });
}

/**
 * Setup Quick City Chips and Swap Location Button
 */
function setupQuickChipsAndSwap() {
  // Swap button
  const swapBtn = document.getElementById("btnSwap");
  if (swapBtn) {
    swapBtn.addEventListener("click", () => {
      const s = document.getElementById("sourceInput");
      const d = document.getElementById("destInput");
      const tmp = s.value;
      s.value = d.value;
      d.value = tmp;
    });
  }

  // Quick Chips
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const src = chip.getAttribute("data-src");
      const dest = chip.getAttribute("data-dest");
      if (src && dest) {
        document.getElementById("sourceInput").value = src;
        document.getElementById("destInput").value = dest;
        const form = document.getElementById("routeForm");
        if (form) form.dispatchEvent(new Event("submit"));
      }
    });
  });
}

/**
 * Emergency Mode, Demo Mode & Theme Toggles
 */
function setupControls() {
  // Emergency Toggle
  const emBtn = document.getElementById("btnEmergencyToggle");
  const emBanner = document.getElementById("emergencyBanner");

  if (emBtn) {
    emBtn.addEventListener("click", () => {
      emergencyMode = !emergencyMode;
      emBtn.classList.toggle("active", emergencyMode);
      emBanner.classList.toggle("active", emergencyMode);
      emBtn.innerHTML = emergencyMode
        ? `<span>🚨 EMERGENCY MODE ON</span>`
        : `<span>🚨 EMERGENCY MODE</span>`;

      showToast(
        emergencyMode ? "Emergency Prioritization Mode Activated!" : "Normal Mode Restored",
        emergencyMode ? "error" : "info"
      );

      // Re-trigger calculation if routes are already loaded
      const form = document.getElementById("routeForm");
      if (form) form.dispatchEvent(new Event("submit"));
    });
  }

  // Demo Mode Badge Toggle
  const demoBadge = document.getElementById("demoBadge");
  if (demoBadge) {
    demoBadge.addEventListener("click", () => {
      demoMode = !demoMode;
      demoBadge.textContent = demoMode ? "DEMO MODE (ACTIVE)" : "LIVE DATA MODE";
      demoBadge.className = `badge-mode ${demoMode ? "badge-demo" : "badge-live"}`;
      showToast(demoMode ? "Switched to Simulated Demo Mode" : "Switched to Live API Mode", "info");
    });
  }

  // Theme Toggle (Dark / Light)
  const themeBtn = document.getElementById("themeToggleBtn");
  if (themeBtn) {
    themeBtn.addEventListener("click", () => {
      const isLight = document.body.classList.toggle("light-theme");
      themeBtn.innerHTML = isLight ? "🌙" : "☀️";
      updateMapBasemap(isLight ? "light" : "dark");
      if (currentRouteResponse && currentRouteResponse.routes) {
        renderAnalyticsCharts(currentRouteResponse.routes);
      }
    });
  }
}

/**
 * Loads system settings from backend
 */
async function loadSystemSettings() {
  try {
    const res = await fetch("/api/settings");
    appSettings = await res.json();
    if (appSettings.default_fuel_price) {
      const fuelInput = document.getElementById("fuelPriceInput");
      if (fuelInput) fuelInput.value = appSettings.default_fuel_price;
    }
  } catch (err) {
    console.error("Failed to load settings:", err);
  }
}

/**
 * Loads API status for Settings Tab
 */
async function loadApiStatus() {
  try {
    const res = await fetch("/api/settings/api-status");
    const data = await res.json();

    const cartoEl = document.getElementById("statusCarto");
    if (cartoEl) cartoEl.textContent = data.carto.status;

    const routingEl = document.getElementById("statusRouting");
    if (routingEl) routingEl.textContent = data.routing.status;

    const weatherEl = document.getElementById("statusWeather");
    if (weatherEl) weatherEl.textContent = data.weather.status;

    const trafficEl = document.getElementById("statusTraffic");
    if (trafficEl) trafficEl.textContent = data.traffic.status;
  } catch (err) {
    console.error("Failed to fetch API status:", err);
  }
}
