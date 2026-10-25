/**
 * Map Integration Engine for Smart Route AI
 * Uses Leaflet + CARTO Basemap layer (Dark Matter / Positron / Voyager)
 * Preserves required CARTO & OpenStreetMap attribution.
 */

let mapInstance = null;
let currentTileLayer = null;
let currentMapStyle = "voyager";
let routeLayers = [];
let markerLayers = [];

const MAP_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6ImRmNGE0MGIwNzI0YjRhYjViOTA3YmIzMWE5NmNmNjc1IiwiaCI6Im11cm11cjY0In0=";
const CARTO_ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions" target="_blank">CARTO</a>';

const BASEMAP_CONFIGS = {
  voyager: {
    name: "CARTO Voyager (Ultra Clear)",
    url: "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    attribution: CARTO_ATTRIBUTION,
    subdomains: "abcd",
    maxZoom: 20,
  },
  dark: {
    name: "CARTO Dark Matter",
    url: "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    attribution: CARTO_ATTRIBUTION,
    subdomains: "abcd",
    maxZoom: 20,
  },
  light: {
    name: "CARTO Positron Light",
    url: "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
    attribution: CARTO_ATTRIBUTION,
    subdomains: "abcd",
    maxZoom: 20,
  },
  osm: {
    name: "OpenStreetMap High-Res",
    url: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors',
    subdomains: "abc",
    maxZoom: 19,
  },
};

/**
 * Initializes the Leaflet map with CARTO Basemap (defaults to ultra-clear Voyager)
 */
function initMap(initialStyle = "voyager") {
  if (mapInstance) return;

  // Default centered near Karnataka / Deccan Hub (Ballari - Bengaluru corridor)
  mapInstance = L.map("map", {
    center: [14.5, 77.0],
    zoom: 7,
    zoomControl: false,
    preferCanvas: true,
  });

  // Add zoom control to top-right
  L.control.zoom({ position: "topright" }).addTo(mapInstance);

  // Set initial ultra-clear basemap
  setMapBasemap(initialStyle);
}

/**
 * Sets the active Basemap style with Retina @2x high-resolution support
 */
function setMapBasemap(styleName) {
  if (!mapInstance) return;

  const config = BASEMAP_CONFIGS[styleName] || BASEMAP_CONFIGS.voyager;
  currentMapStyle = styleName;

  if (currentTileLayer) {
    mapInstance.removeLayer(currentTileLayer);
  }

  currentTileLayer = L.tileLayer(config.url, {
    attribution: config.attribution,
    subdomains: config.subdomains,
    maxZoom: config.maxZoom,
    detectRetina: true,
    tileSize: 256,
  }).addTo(mapInstance);

  // Sync select element if present
  const styleSelect = document.getElementById("mapStyleSelect");
  if (styleSelect && styleSelect.value !== styleName) {
    styleSelect.value = styleName;
  }
}

/**
 * Updates the CARTO basemap style (backward compatible)
 */
function updateMapBasemap(styleName) {
  setMapBasemap(styleName);
}

let routeLayersData = [];

/**
 * Clears existing route polylines and location markers
 */
function clearMapOverlays() {
  if (!mapInstance) return;
  routeLayers.forEach((l) => mapInstance.removeLayer(l));
  markerLayers.forEach((m) => mapInstance.removeLayer(m));
  routeLayers = [];
  markerLayers = [];
  routeLayersData = [];
}

/**
 * Creates custom glowing SVG icons for Start and Destination
 */
function createCustomMarker(type) {
  const isStart = type === "start";
  const color = isStart ? "#10B981" : "#EF4444";
  const symbol = isStart ? "📍" : "🏁";

  return L.divIcon({
    className: "custom-map-marker",
    html: `
      <div style="
        background: ${color};
        width: 34px;
        height: 34px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
        box-shadow: 0 0 16px ${color};
        border: 2px solid #ffffff;
        cursor: pointer;
      ">
        ${symbol}
      </div>
    `,
    iconSize: [34, 34],
    iconAnchor: [17, 17],
    popupAnchor: [0, -20],
  });
}

/**
 * Renders calculated routes and start/destination markers on map
 */
function renderRoutesOnMap(routeData) {
  if (!mapInstance) initMap();
  clearMapOverlays();

  const source = routeData.source;
  const destination = routeData.destination;
  const routes = routeData.routes || [];

  // Add Source Marker
  const startMarker = L.marker([source.lat, source.lon], {
    icon: createCustomMarker("start"),
  })
    .addTo(mapInstance)
    .bindPopup(`<b>Source:</b><br>${source.display_name}`);
  markerLayers.push(startMarker);

  // Add Destination Marker
  const destMarker = L.marker([destination.lat, destination.lon], {
    icon: createCustomMarker("destination"),
  })
    .addTo(mapInstance)
    .bindPopup(`<b>Destination:</b><br>${destination.display_name}`);
  markerLayers.push(destMarker);

  const bounds = L.latLngBounds([
    [source.lat, source.lon],
    [destination.lat, destination.lon],
  ]);

  // Color scheme: Recommended = Glowing Emerald/Cyan, Alts = Amber, Purple, Cyan
  const altColors = ["#F59E0B", "#8B5CF6", "#06B6D4"];

  // Render Alternative routes first so Recommended sits visibly on top
  const sortedForRendering = [...routes].reverse();

  sortedForRendering.forEach((route) => {
    const isRec = route.is_recommended;
    const coords = route.coordinates;

    if (!coords || coords.length === 0) return;

    coords.forEach((pt) => bounds.extend(pt));

    const color = isRec ? "#10B981" : altColors[(route.rank - 2) % altColors.length] || "#94A3B8";
    const weight = isRec ? 6 : 4;
    const opacity = isRec ? 0.95 : 0.65;
    const dashArray = isRec ? null : "6, 8";

    // Glow background line for recommended route
    let glowLine = null;
    if (isRec) {
      glowLine = L.polyline(coords, {
        color: "#10B981",
        weight: 12,
        opacity: 0.25,
      }).addTo(mapInstance);
      routeLayers.push(glowLine);
    }

    const polyline = L.polyline(coords, {
      color: color,
      weight: weight,
      opacity: opacity,
      dashArray: dashArray,
    }).addTo(mapInstance);

    const popupHtml = `
      <div style="font-family: inherit; font-size: 13px; line-height: 1.5; color: #111;">
        <div style="font-weight: 800; font-size: 14px; margin-bottom: 4px; color: ${color}">
          ${route.route_name} ${isRec ? "🏆 (Recommended)" : ""}
        </div>
        <div style="font-size: 11px; color: #64748B; margin-bottom: 4px;">${route.via_summary || ""}</div>
        <div><b>Smart Score:</b> <span style="font-size: 15px; font-weight: 800; color: #059669">${Math.round(route.smart_score)}/100</span></div>
        <div><b>Distance:</b> ${route.distance_km} km</div>
        <div><b>Duration:</b> ${Math.round(route.duration_minutes)} mins</div>
        <div><b>Traffic:</b> ${route.traffic.level} (${route.traffic.score}/100)</div>
        <div><b>Safety:</b> ${route.safety.score}/100 (${route.safety.category || 'High'})</div>
        <div><b>Fuel:</b> ${route.fuel.fuel_liters} L (~₹${Math.round(route.fuel.fuel_cost)})</div>
      </div>
    `;

    polyline.bindPopup(popupHtml);
    routeLayers.push(polyline);

    routeLayersData.push({
      routeId: route.route_id,
      polyline: polyline,
      glowLine: glowLine,
      baseColor: color,
      coords: coords,
      isRec: isRec,
    });
  });

  // Fit map to contain entire route with padding
  mapInstance.fitBounds(bounds, { padding: [50, 50] });
}

/**
 * Focuses and highlights a specific route on the map
 */
function highlightRouteOnMap(routeId) {
  if (!mapInstance || routeLayersData.length === 0) return;

  routeLayersData.forEach((item) => {
    if (item.routeId === routeId) {
      item.polyline.setStyle({
        color: "#10B981",
        weight: 7,
        opacity: 1.0,
        dashArray: null,
      });
      item.polyline.bringToFront();
      item.polyline.openPopup();
    } else {
      item.polyline.setStyle({
        color: "#64748B",
        weight: 3.5,
        opacity: 0.4,
        dashArray: "6, 8",
      });
    }
  });
}

/**
 * Re-centers map to bounds of current route
 */
function recenterMap() {
  if (!mapInstance || routeLayers.length === 0) return;
  const group = new L.featureGroup([...routeLayers, ...markerLayers]);
  mapInstance.fitBounds(group.getBounds(), { padding: [40, 40] });
}

