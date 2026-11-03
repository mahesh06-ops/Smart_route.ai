/**
 * Map Integration Engine for Smart Route AI
 * Uses MapLibre GL JS with MapTiler vector styles.
 */

let mapInstance = null;
let mapApiKey = "";
let currentMapStyle = "streets";
let mapStyleLoaded = false;
let currentRouteData = null;
let routeBounds = null;
let routeMarkers = [];
let routeLayersData = [];
let selectedRouteId = null;
let routePopup = null;
let mapErrorReported = false;
let routeClickHandlersRegistered = false;

const MAPTILER_STYLES = {
  hybrid: "hybrid",
  streets: "streets-v2",
  dark: "dataviz-dark",
  light: "basic-v2",
};

const ROUTES_SOURCE_ID = "smart-routes";
const ROUTE_GLOW_LAYER_ID = "smart-route-glow";
const ROUTE_ALTERNATIVE_LAYER_ID = "smart-route-alternatives";
const ROUTE_RECOMMENDED_LAYER_ID = "smart-route-recommended";

const MAP_STYLE_ERROR =
  "Map style failed to load. Check the MapTiler API key, its allowed origins, and your network connection.";

/**
 * Initializes the MapLibre map (MapTiler Streets v2 by default).
 */
function initMap(apiKey = mapApiKey, initialStyle = "streets") {
  if (mapInstance) return mapInstance;

  mapApiKey = typeof apiKey === "string" ? apiKey.trim() : "";

  if (!mapApiKey) {
    showMapStatus(
      "Configure MAPTILER_API_KEY in .env and restart the app to load the map."
    );
    return null;
  }

  if (typeof maplibregl === "undefined") {
    showMapStatus(
      "MapLibre GL JS could not be loaded. Check the network connection and refresh."
    );
    return null;
  }

  currentMapStyle = MAPTILER_STYLES[initialStyle] ? initialStyle : "streets";

  mapInstance = new maplibregl.Map({
    container: "map",
    // FIX: use the helper so the chosen style is respected
    style: getMapStyleUrl(currentMapStyle),
    center: [77.0, 14.5],
    zoom: 7,
    attributionControl: true,
  });

  mapInstance.addControl(new maplibregl.NavigationControl(), "top-right");

  mapInstance.on("style.load", () => {
    mapStyleLoaded = true;
    mapErrorReported = false;
    hideMapStatus();

    if (currentRouteData) {
      renderRouteOverlays();
    }
  });

  mapInstance.on("error", (event) => {
    if (!mapStyleLoaded && !mapErrorReported) {
      mapErrorReported = true;
      const err = event && event.error;
      const status = err && err.status;
      const msg = (err && err.message) || "";
      let userMsg = MAP_STYLE_ERROR;

      if (status === 403 || msg.includes("403") || msg.toLowerCase().includes("restricted")) {
        userMsg = "MapTiler returned HTTP 403 (Key usage restricted). Please add http://127.0.0.1:8000 and http://localhost:8000 to Allowed Origins in your MapTiler Cloud account.";
      } else if (status === 401 || msg.includes("401")) {
        userMsg = "MapTiler returned HTTP 401 (Unauthorized). Check MAPTILER_API_KEY in .env.";
      }

      showMapStatus(userMsg);

      console.error(
        "MapTiler map error:",
        userMsg,
        err
      );
    }
  });

  syncMapStyleSelect();

  return mapInstance;
}

/**
 * Creates the MapTiler style URL using the configured API key.
 */
function getMapStyleUrl(styleName) {
  const styleId = MAPTILER_STYLES[styleName] || MAPTILER_STYLES.streets;

  return `https://api.maptiler.com/maps/${styleId}/style.json?key=${encodeURIComponent(mapApiKey)}`;
}

function showMapStatus(message) {
  const container = document.getElementById("map");
  if (!container) return;

  let status = container.querySelector(".map-status-message");

  if (!status) {
    status = document.createElement("div");
    status.className = "map-status-message";
    status.setAttribute("role", "status");
    container.appendChild(status);
  }

  status.textContent = message;
}

function hideMapStatus() {
  const status = document.querySelector("#map .map-status-message");
  if (status) status.remove();
}

function syncMapStyleSelect() {
  const styleSelect = document.getElementById("mapStyleSelect");

  if (styleSelect && styleSelect.value !== currentMapStyle) {
    styleSelect.value = currentMapStyle;
  }
}

/**
 * Changes the active MapTiler vector style.
 */
function setMapBasemap(styleName) {
  const nextStyle = MAPTILER_STYLES[styleName] ? styleName : "streets";
  const styleChanged = nextStyle !== currentMapStyle;

  currentMapStyle = nextStyle;
  syncMapStyleSelect();

  if (!mapInstance || !styleChanged) {
    return;
  }

  mapStyleLoaded = false;
  mapErrorReported = false;

  mapInstance.setStyle(getMapStyleUrl(nextStyle));
}

/**
 * Updates the MapTiler style for the light/dark theme toggle.
 */
function updateMapBasemap(styleName) {
  setMapBasemap(
    styleName === "light" ? "light" : styleName === "dark" ? "dark" : "streets"
  );
}

function removeRenderedOverlays() {
  if (mapInstance && mapStyleLoaded) {
    [
      ROUTE_RECOMMENDED_LAYER_ID,
      ROUTE_ALTERNATIVE_LAYER_ID,
      ROUTE_GLOW_LAYER_ID,
    ].forEach((layerId) => {
      if (mapInstance.getLayer(layerId)) {
        mapInstance.removeLayer(layerId);
      }
    });

    if (mapInstance.getSource(ROUTES_SOURCE_ID)) {
      mapInstance.removeSource(ROUTES_SOURCE_ID);
    }
  }

  routeMarkers.forEach((marker) => marker.remove());
  routeMarkers = [];
  routeLayersData = [];
  routeBounds = null;

  if (routePopup) {
    routePopup.remove();
    routePopup = null;
  }
}

/**
 * Clears the current route geometry and location markers.
 */
function clearMapOverlays() {
  removeRenderedOverlays();
  currentRouteData = null;
  selectedRouteId = null;
}

function escapeMapHtml(value) {
  return String(value == null ? "" : value).replace(/[&<>"']/g, (character) => {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    };

    return replacements[character];
  });
}

function createCustomMarker(type) {
  const isStart = type === "start";
  const marker = document.createElement("div");

  marker.className = `custom-map-marker ${
    isStart ? "start-marker" : "destination-marker"
  }`;

  marker.setAttribute(
    "aria-label",
    isStart ? "Route start" : "Route destination"
  );

  marker.textContent = isStart ? "📍" : "🏁";

  return marker;
}

function validLatLon(latitude, longitude) {
  return (
    latitude !== null &&
    longitude !== null &&
    latitude !== "" &&
    longitude !== "" &&
    Number.isFinite(Number(latitude)) &&
    Number.isFinite(Number(longitude))
  );
}

function getRoutePopupHtml(route, color) {
  const traffic = route.traffic || {};
  const safety = route.safety || {};
  const fuel = route.fuel || {};
  const routeName = escapeMapHtml(route.route_name);
  const isSimulated = !route.is_live_route || route.is_estimated_route;

  return `
    <div class="route-map-popup">
      <div class="route-map-popup-title" style="color: ${color}">
        ${routeName}${route.is_recommended ? " 🏆 (Recommended)" : ""}
      </div>
      ${isSimulated ? '<div style="margin: 3px 0;"><span style="background: rgba(245, 158, 11, 0.2); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.4); font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: bold;">⚠️ Simulated route</span></div>' : ''}
      <div class="route-map-popup-summary">
        ${escapeMapHtml(route.via_summary || "")}
      </div>
      <div><b>Smart Score:</b> ${Math.round(Number(route.smart_score) || 0)}/100</div>
      <div><b>Distance:</b> ${escapeMapHtml(route.distance_km)} km</div>
      <div><b>Duration:</b> ${Math.round(Number(route.duration_minutes) || 0)} mins</div>
      <div><b>Traffic:</b> ${escapeMapHtml(traffic.level)} (${escapeMapHtml(traffic.score)}/100) ${traffic.is_live ? '<span style="color: #10B981; font-size: 10px; font-weight: 700;">(Live)</span>' : '<span style="color: #f59e0b; font-size: 10px; font-weight: 700;">(Simulated)</span>'}</div>
      <div><b>Safety:</b> ${escapeMapHtml(safety.score)}/100 (${escapeMapHtml(safety.category || "High")})</div>
      <div><b>Fuel:</b> ${escapeMapHtml(fuel.fuel_liters)} L (~₹${Math.round(Number(fuel.fuel_cost) || 0)})</div>
    </div>
  `;
}

function getRoutePaint(property, selectedValue, defaultValue) {
  const selectedRoute = ["==", ["get", "routeId"], selectedRouteId];
  const isSelected = selectedRouteId !== null;

  if (property === "line-color") {
    return [
      "case",
      selectedRoute,
      selectedValue,
      isSelected ? "#64748B" : defaultValue,
    ];
  }

  if (property === "line-width") {
    return [
      "case",
      selectedRoute,
      selectedValue,
      isSelected ? 3.5 : defaultValue,
    ];
  }

  return [
    "case",
    selectedRoute,
    selectedValue,
    isSelected ? 0.4 : defaultValue,
  ];
}

function applyRouteHighlightStyle() {
  if (!mapInstance || !mapStyleLoaded) return;

  [ROUTE_ALTERNATIVE_LAYER_ID, ROUTE_RECOMMENDED_LAYER_ID].forEach((layerId) => {
    if (!mapInstance.getLayer(layerId)) return;

    mapInstance.setPaintProperty(
      layerId,
      "line-color",
      getRoutePaint("line-color", "#10B981", ["get", "color"])
    );

    mapInstance.setPaintProperty(
      layerId,
      "line-width",
      getRoutePaint("line-width", 7, ["get", "weight"])
    );

    mapInstance.setPaintProperty(
      layerId,
      "line-opacity",
      getRoutePaint("line-opacity", 1, ["get", "opacity"])
    );
  });
}

function registerRouteClickHandlers() {
  if (routeClickHandlersRegistered) return;

  const layerIds = [ROUTE_ALTERNATIVE_LAYER_ID, ROUTE_RECOMMENDED_LAYER_ID];

  mapInstance.on("click", layerIds, (event) => {
    const feature = event.features && event.features[0];
    if (!feature) return;

    // FIX: close any previous popup before opening a new one
    if (routePopup) routePopup.remove();

    routePopup = new maplibregl.Popup({ closeButton: true, offset: 10 })
      .setLngLat(event.lngLat)
      .setHTML(feature.properties.popupHtml)
      .addTo(mapInstance);
  });

  mapInstance.on("mouseenter", layerIds, () => {
    mapInstance.getCanvas().style.cursor = "pointer";
  });

  mapInstance.on("mouseleave", layerIds, () => {
    mapInstance.getCanvas().style.cursor = "";
  });

  routeClickHandlersRegistered = true;
}

function addRouteMarkers(source, destination) {
  if (
    !validLatLon(source.lat, source.lon) ||
    !validLatLon(destination.lat, destination.lon)
  ) {
    return;
  }

  const markerConfigs = [
    { type: "start", place: source, label: "Source" },
    { type: "destination", place: destination, label: "Destination" },
  ];

  markerConfigs.forEach(({ type, place, label }) => {
    const popup = new maplibregl.Popup({ offset: 22 }).setHTML(
      `<b>${label}:</b><br>${escapeMapHtml(place.display_name)}`
    );

    const marker = new maplibregl.Marker({
      element: createCustomMarker(type),
      anchor: "center",
    })
      .setLngLat([Number(place.lon), Number(place.lat)])
      .setPopup(popup)
      .addTo(mapInstance);

    routeMarkers.push(marker);
  });
}

function getAlternativeColor(route, fallbackIndex) {
  const alternativeColors = ["#F59E0B", "#8B5CF6", "#06B6D4"];
  const rank = Number(route.rank);
  // FIX: avoid negative / NaN indexes when rank is missing or 1
  const base = Number.isFinite(rank) ? rank - 2 : fallbackIndex;
  const index =
    ((base % alternativeColors.length) + alternativeColors.length) %
    alternativeColors.length;
  return alternativeColors[index] || "#94A3B8";
}

function renderRouteOverlays() {
  if (!mapInstance || !mapStyleLoaded || !currentRouteData) {
    return;
  }

  removeRenderedOverlays();

  const { source, destination } = currentRouteData;

  if (
    !source ||
    !destination ||
    !validLatLon(source.lat, source.lon) ||
    !validLatLon(destination.lat, destination.lon)
  ) {
    console.error(
      "Route map data is missing valid source or destination coordinates."
    );
    return;
  }

  routeBounds = new maplibregl.LngLatBounds();
  routeBounds.extend([Number(source.lon), Number(source.lat)]);
  routeBounds.extend([Number(destination.lon), Number(destination.lat)]);

  addRouteMarkers(source, destination);

  // Reverse so the recommended route is drawn on top
  const routes = [...(currentRouteData.routes || [])].reverse();
  const features = [];

  routes.forEach((route, index) => {
    if (!Array.isArray(route.coordinates) || route.coordinates.length === 0) {
      return;
    }

    // Backend sends [lat, lon]; MapLibre needs [lon, lat]
    const coordinates = route.coordinates
      .filter((point) => Array.isArray(point) && validLatLon(point[0], point[1]))
      .map(([latitude, longitude]) => [Number(longitude), Number(latitude)]);

    if (coordinates.length === 0) return;

    coordinates.forEach((coordinate) => routeBounds.extend(coordinate));

    const isRecommended = Boolean(route.is_recommended);
    const color = isRecommended ? "#10B981" : getAlternativeColor(route, index);
    const popupHtml = getRoutePopupHtml(route, color);

    features.push({
      type: "Feature",
      properties: {
        routeId: String(route.route_id),
        isRecommended,
        color,
        weight: isRecommended ? 6 : 4,
        opacity: isRecommended ? 0.95 : 0.65,
        popupHtml,
      },
      geometry: {
        type: "LineString",
        coordinates,
      },
    });

    routeLayersData.push({
      routeId: String(route.route_id),
      coordinates,
      popupHtml,
    });
  });

  mapInstance.addSource(ROUTES_SOURCE_ID, {
    type: "geojson",
    data: {
      type: "FeatureCollection",
      features,
    },
  });

  mapInstance.addLayer({
    id: ROUTE_GLOW_LAYER_ID,
    type: "line",
    source: ROUTES_SOURCE_ID,
    filter: ["==", ["get", "isRecommended"], true],
    layout: {
      "line-cap": "round",
      "line-join": "round",
    },
    paint: {
      "line-color": "#10B981",
      "line-width": 12,
      "line-opacity": 0.25,
    },
  });

  mapInstance.addLayer({
    id: ROUTE_ALTERNATIVE_LAYER_ID,
    type: "line",
    source: ROUTES_SOURCE_ID,
    filter: ["==", ["get", "isRecommended"], false],
    // FIX: line-dasharray is a PAINT property, not a layout property
    layout: {
      "line-cap": "round",
      "line-join": "round",
    },
    paint: {
      "line-color": ["get", "color"],
      "line-width": ["get", "weight"],
      "line-opacity": ["get", "opacity"],
      "line-dasharray": [2, 2],
    },
  });

  mapInstance.addLayer({
    id: ROUTE_RECOMMENDED_LAYER_ID,
    type: "line",
    source: ROUTES_SOURCE_ID,
    filter: ["==", ["get", "isRecommended"], true],
    layout: {
      "line-cap": "round",
      "line-join": "round",
    },
    paint: {
      "line-color": ["get", "color"],
      "line-width": ["get", "weight"],
      "line-opacity": ["get", "opacity"],
    },
  });

  registerRouteClickHandlers();
  applyRouteHighlightStyle();

  if (!routeBounds.isEmpty()) {
    mapInstance.fitBounds(routeBounds, {
      padding: 50,
      maxZoom: 15,
    });
  }

  if (selectedRouteId) {
    openSelectedRoutePopup();
  }
}

/**
 * Renders calculated routes and start/destination markers on the map.
 * Route data is retained until the style is ready.
 */
function renderRoutesOnMap(routeData) {
  currentRouteData = routeData;
  selectedRouteId = null;

  if (!mapInstance) {
    initMap(mapApiKey);
  }

  if (mapInstance && mapStyleLoaded) {
    renderRouteOverlays();
  }
}

function openSelectedRoutePopup() {
  const route = routeLayersData.find((item) => item.routeId === selectedRouteId);

  if (!route || !route.coordinates.length) return;

  const midpoint = route.coordinates[Math.floor(route.coordinates.length / 2)];

  if (routePopup) routePopup.remove();

  routePopup = new maplibregl.Popup({ closeButton: true, offset: 10 })
    .setLngLat(midpoint)
    .setHTML(route.popupHtml)
    .addTo(mapInstance);
}

/**
 * Focuses and highlights a specific route on the map.
 */
function highlightRouteOnMap(routeId) {
  const targetRouteId = String(routeId);

  if (
    !currentRouteData ||
    !(currentRouteData.routes || []).some(
      (route) => String(route.route_id) === targetRouteId
    )
  ) {
    return;
  }

  selectedRouteId = targetRouteId;
  applyRouteHighlightStyle();

  if (mapStyleLoaded) {
    openSelectedRoutePopup();
  }
}

/**
 * Re-centers the map to the bounds of the current route and markers.
 */
function recenterMap() {
  if (!mapInstance || !mapStyleLoaded || !routeBounds || routeBounds.isEmpty()) {
    return;
  }

  mapInstance.fitBounds(routeBounds, {
    padding: 40,
    maxZoom: 15,
  });
}