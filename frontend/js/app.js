/**
 * Main Application Orchestrator for Smart Route AI
 *
 * Loads backend settings before initializing the map, then wires up
 * navigation, routing, quick actions, theme controls, and API status.
 */

"use strict";

let emergencyMode = false;
let demoMode = false;
let appSettings = null;

document.addEventListener("DOMContentLoaded", async () => {
  // Load settings first so the map receives its key before initialization.
  await loadSystemSettings();

  const mapKey = appSettings?.maptiler_api_key || "";

  if (typeof initMap === "function") {
    initMap(mapKey, "streets");
  } else {
    console.error(
      "initMap() is unavailable. Check that frontend/js/map.js loads before app.js."
    );
  }

  // Initialize application controls.
  setupNavigationTabs();
  setupFormListener();
  setupQuickChipsAndSwap();
  setupControls();

  await loadHistoryListSafely();

  // Start the default demonstration route only when both fields are present.
  const sourceInput = document.getElementById("sourceInput");
  const destinationInput = document.getElementById("destInput");

  if (
    sourceInput?.value.trim() &&
    destinationInput?.value.trim() &&
    typeof calculateSmartRoute === "function"
  ) {
    calculateSmartRoute({
      source: sourceInput.value.trim(),
      destination: destinationInput.value.trim(),
      vehicle_type: "car",
      preference: "balanced",
      emergency_mode: emergencyMode,
      demo_mode: demoMode,
    });
  }
});

/**
 * Tab Navigation Routing
 */
function setupNavigationTabs() {
  document.querySelectorAll(".nav-item").forEach((item) => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");

      if (tabId) {
        switchTab(tabId);
      }
    });
  });
}

function switchTab(tabId) {
  // Update navigation links.
  document.querySelectorAll(".nav-item").forEach((nav) => {
    nav.classList.toggle(
      "active",
      nav.getAttribute("data-tab") === tabId
    );
  });

  // Update tab panes.
  document.querySelectorAll(".tab-pane").forEach((pane) => {
    pane.classList.toggle("active", pane.id === `tab-${tabId}`);
  });

  // Resize the map after its tab becomes visible.
  if (
    tabId === "dashboard" &&
    typeof mapInstance !== "undefined" &&
    mapInstance
  ) {
    window.setTimeout(() => {
      if (typeof mapInstance !== "undefined" && mapInstance) {
        mapInstance.resize();

        if (typeof recenterMap === "function") {
          recenterMap();
        }
      }
    }, 100);
  }

  // Route comparison tab.
  if (
    tabId === "compare" &&
    typeof currentRouteResponse !== "undefined"
  ) {
    const routes = currentRouteResponse?.routes;

    if (routes) {
      if (typeof renderComparisonCards === "function") {
        renderComparisonCards(routes);
      }

      if (typeof renderComparisonTable === "function") {
        renderComparisonTable(routes);
      }

      if (typeof updateCompareBanner === "function") {
        updateCompareBanner(currentRouteResponse);
      }
    }
  }

  // Analytics tab.
  if (
    tabId === "analytics" &&
    typeof currentRouteResponse !== "undefined"
  ) {
    const routes = currentRouteResponse?.routes;

    if (routes && typeof renderAnalyticsCharts === "function") {
      renderAnalyticsCharts(routes);
    }
  }

  // History tab.
  if (tabId === "history") {
    loadHistoryListSafely();
  }

  // Settings tab.
  if (tabId === "settings") {
    loadApiStatus();
  }
}

/**
 * Form Submission Handling
 */
function setupFormListener() {
  const form = document.getElementById("routeForm");

  if (!form) {
    console.warn('Route form "#routeForm" was not found.');
    return;
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();

    const sourceInput = document.getElementById("sourceInput");
    const destinationInput = document.getElementById("destInput");

    const source = sourceInput?.value.trim() || "";
    const destination = destinationInput?.value.trim() || "";

    const vehicleType =
      document.getElementById("vehicleSelect")?.value || "car";

    const preference =
      document.getElementById("preferenceSelect")?.value || "balanced";

    const fuelInput = document.getElementById("fuelPriceInput");

    const parsedFuelPrice = fuelInput
      ? Number.parseFloat(fuelInput.value)
      : 102.5;

    const fuelPrice =
      Number.isFinite(parsedFuelPrice) && parsedFuelPrice > 0
        ? parsedFuelPrice
        : 102.5;

    if (!source || !destination) {
      if (typeof showToast === "function") {
        showToast(
          "Please enter both source and destination locations.",
          "error"
        );
      } else {
        console.warn(
          "Please enter both source and destination locations."
        );
      }

      return;
    }

    if (typeof calculateSmartRoute !== "function") {
      console.error(
        "calculateSmartRoute() is unavailable. Check the route script loading order."
      );
      return;
    }

    calculateSmartRoute({
      source,
      destination,
      vehicle_type: vehicleType,
      preference,
      emergency_mode: emergencyMode,
      fuel_price: fuelPrice,
      demo_mode: demoMode,
    });
  });
}

/**
 * Setup Quick City Chips and Swap Location Button
 */
function setupQuickChipsAndSwap() {
  // Swap source and destination.
  const swapButton = document.getElementById("btnSwap");

  if (swapButton) {
    swapButton.addEventListener("click", () => {
      const sourceInput = document.getElementById("sourceInput");
      const destinationInput = document.getElementById("destInput");

      if (!sourceInput || !destinationInput) {
        return;
      }

      const oldSource = sourceInput.value;

      sourceInput.value = destinationInput.value;
      destinationInput.value = oldSource;
    });
  }

  // Quick route chips.
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const source = chip.getAttribute("data-src");
      const destination = chip.getAttribute("data-dest");

      const sourceInput = document.getElementById("sourceInput");
      const destinationInput = document.getElementById("destInput");
      const form = document.getElementById("routeForm");

      if (
        !source ||
        !destination ||
        !sourceInput ||
        !destinationInput ||
        !form
      ) {
        return;
      }

      sourceInput.value = source;
      destinationInput.value = destination;

      if (typeof form.requestSubmit === "function") {
        form.requestSubmit();
      } else {
        form.dispatchEvent(
          new Event("submit", {
            bubbles: true,
            cancelable: true,
          })
        );
      }
    });
  });
}

/**
 * Emergency Mode, Demo Mode and Theme Toggles
 */
function setupControls() {
  // Emergency mode.
  const emergencyButton =
    document.getElementById("btnEmergencyToggle");

  const emergencyBanner =
    document.getElementById("emergencyBanner");

  if (emergencyButton) {
    emergencyButton.addEventListener("click", () => {
      emergencyMode = !emergencyMode;

      emergencyButton.classList.toggle(
        "active",
        emergencyMode
      );

      if (emergencyBanner) {
        emergencyBanner.classList.toggle(
          "active",
          emergencyMode
        );
      }

      emergencyButton.innerHTML = emergencyMode
        ? "<span>🚨 EMERGENCY MODE ON</span>"
        : "<span>🚨 EMERGENCY MODE</span>";

      if (typeof showToast === "function") {
        showToast(
          emergencyMode
            ? "Emergency Prioritization Mode Activated!"
            : "Normal Mode Restored",
          emergencyMode ? "error" : "info"
        );
      }

      // Recalculate only if both locations have been entered.
      const form = document.getElementById("routeForm");

      const source =
        document.getElementById("sourceInput")?.value.trim();

      const destination =
        document.getElementById("destInput")?.value.trim();

      if (form && source && destination) {
        if (typeof form.requestSubmit === "function") {
          form.requestSubmit();
        } else {
          form.dispatchEvent(
            new Event("submit", {
              bubbles: true,
              cancelable: true,
            })
          );
        }
      }
    });
  }

  // Demo mode.
  const demoBadge = document.getElementById("demoBadge");

  if (demoBadge) {
    demoBadge.addEventListener("click", () => {
      demoMode = !demoMode;

      demoBadge.textContent = demoMode
        ? "DEMO MODE (ACTIVE)"
        : "LIVE DATA MODE";

      demoBadge.className =
        `badge-mode ${demoMode ? "badge-demo" : "badge-live"}`;

      if (typeof showToast === "function") {
        showToast(
          demoMode
            ? "Switched to Simulated Demo Mode"
            : "Switched to Live API Mode",
          "info"
        );
      }
    });
  }

  // Dark/light theme.
  const themeButton = document.getElementById("themeToggleBtn");

  if (themeButton) {
    themeButton.addEventListener("click", () => {
      const isLight =
        document.body.classList.toggle("light-theme");

      themeButton.innerHTML = isLight ? "🌙" : "☀️";

      if (typeof updateMapBasemap === "function") {
        updateMapBasemap(isLight ? "light" : "dark");
      }

      if (
        typeof currentRouteResponse !== "undefined" &&
        currentRouteResponse?.routes &&
        typeof renderAnalyticsCharts === "function"
      ) {
        renderAnalyticsCharts(currentRouteResponse.routes);
      }
    });
  }
}

/**
 * Loads application settings and MapTiler configuration from the backend.
 *
 * A map-config failure will not discard settings that were already loaded.
 */
async function loadSystemSettings() {
  appSettings = {};

  // Load general settings.
  try {
    const response = await fetch("/api/settings", {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(
        `Settings request failed (${response.status}).`
      );
    }

    const settings = await response.json();

    if (settings && typeof settings === "object") {
      appSettings = settings;
    }
  } catch (error) {
    console.error(
      "Failed to load general settings:",
      error
    );
  }

  // Load MapTiler configuration separately.
  try {
    const response = await fetch("/api/settings/map-config", {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(
        `Map configuration request failed (${response.status}).`
      );
    }

    const mapConfig = await response.json();
    const key = mapConfig?.maptiler_api_key;

    appSettings.maptiler_api_key =
      typeof key === "string" ? key.trim() : "";

    if (!appSettings.maptiler_api_key) {
      console.error(
        "The backend returned an empty MapTiler key. Check MAPTILER_API_KEY in the server environment."
      );
    }
  } catch (error) {
    appSettings.maptiler_api_key = "";

    console.error(
      "Failed to load MapTiler configuration:",
      error
    );
  }

  // Apply the configured default fuel price if available.
  const fuelInput = document.getElementById("fuelPriceInput");

  if (
    fuelInput &&
    appSettings.default_fuel_price != null
  ) {
    fuelInput.value = appSettings.default_fuel_price;
  }
}

/**
 * Loads API status for the Settings tab.
 */
async function loadApiStatus() {
  try {
    const response = await fetch("/api/settings/api-status", {
      cache: "no-store",
    });

    if (!response.ok) {
      throw new Error(
        `API status request failed (${response.status}).`
      );
    }

    const data = await response.json();

    const mapTilerElement =
      document.getElementById("statusMapTiler");

    if (mapTilerElement) {
      mapTilerElement.textContent =
        data?.maptiler?.status || "Unknown";
    }

    const routingElement =
      document.getElementById("statusRouting");

    if (routingElement) {
      routingElement.textContent =
        data?.routing?.status || "Unknown";
    }

    const weatherElement =
      document.getElementById("statusWeather");

    if (weatherElement) {
      weatherElement.textContent =
        data?.weather?.status || "Unknown";
    }

    const trafficElement =
      document.getElementById("statusTraffic");

    if (trafficElement) {
      trafficElement.textContent =
        data?.traffic?.status || "Unknown";
    }
  } catch (error) {
    console.error(
      "Failed to fetch API status:",
      error
    );
  }
}

/**
 * Safely loads route history if its script is available.
 */
async function loadHistoryListSafely() {
  if (typeof loadHistoryList !== "function") {
    console.warn(
      "loadHistoryList() is unavailable; check that the history script is loaded."
    );
    return;
  }

  try {
    await loadHistoryList();
  } catch (error) {
    console.error(
      "Failed to load route history:",
      error
    );
  }
}