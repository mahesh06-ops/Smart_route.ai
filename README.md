# 🚗 Smart Route AI — Intelligent Route Optimization Platform

> Multi-Factor Route Optimization & Recommendation Engine driven by Live/Simulated Traffic, Weather Risk, Analytical Road Safety, Vehicle Fuel Economy, and Machine Learning.

---

## 🌟 Key Capabilities

1. **Multi-Factor Decision Matrix**:
   - **Travel Time** (live road congestion & delay factor)
   - **Traffic Flow** (analytical congestion index: Low, Moderate, High, Heavy)
   - **Weather Hazards** (Open-Meteo precipitation, storm, fog, visibility)
   - **Safety Index** (curvature, corridor flow, night-time & wet-surface hazards)
   - **Fuel & Carbon Footprint** (dynamic mileage & fuel cost for Cars, Bikes, SUVs)
   - **Distance Minimization**

2. **Personalized Preference Profiles**:
   - `Balanced` (Default harmonized weights)
   - `Fastest` (High time & traffic priority)
   - `Safest` (High safety & weather avoidance priority)
   - `Shortest` (Distance-first optimization)
   - `Fuel Efficient` (Mileage & cost preservation)
   - 🚨 **Emergency Mode**: Instant override prioritizing absolute travel time and traffic bypass.

3. **Machine Learning Layer (`src/ml/`)**:
   - `RouteFeatureExtractor`: Converts multi-modal environmental route data into 12-dimensional numerical vectors.
   - `MLRouteRanker`: Random Forest model predicting route desirability and ranking routes alongside composite mathematical scores.

4. **Dynamic AI Explanation Engine**:
   - Humanized rationale explaining *why* the recommended route was selected, highlighting strengths and cautioning on potential trade-offs.

5. **Interactive Frontend SaaS Experience**:
   - Dark-mode-first glassmorphism design.
   - Interactive Leaflet map with **CARTO basemaps** (Dark Matter, Positron, Voyager).
   - Radar & bar comparison charts powered by Chart.js.
   - SQLite search history with reload & management capabilities.

---

## 🏗️ Project Architecture

```
s route/
├── backend/
│   ├── api/                    # REST API endpoints (routes, history, settings, health)
│   ├── schemas/                # Pydantic data validation & request/response schemas
│   └── main.py                 # FastAPI application, CORS, static mounts
├── frontend/
│   ├── css/                    # Glassmorphic themes, responsive styles
│   ├── js/                     # Map (CARTO/Leaflet), charts, route handler, history
│   └── index.html              # Modern web client
├── src/
│   ├── config/                 # Pydantic settings & environment configuration
│   ├── database/               # SQLite database & route history repository
│   ├── intelligence/           # Scoring, traffic, weather, safety, fuel, and AI explanations
│   ├── ml/                     # ML feature extraction & Random Forest route ranker
│   ├── services/               # Geocoding, OSRM routing, weather & traffic providers
│   └── utils/                  # Normalization, validation, secure logging
├── tests/                      # 28 comprehensive unit & integration tests
├── requirements.txt            # Python dependencies
├── run.py                      # Production/dev startup script
└── app.py                      # ASGI entrypoint
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+ installed

### 2. Environment Setup
```bash
# Clone or navigate to the project directory
cd "s route"

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
# Copy .env.example to .env if not already present
cp .env.example .env
```

### 3. Running the Application
```bash
python run.py
```
- **Web UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive API Docs (Swagger)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Alternative Docs (ReDoc)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 🧪 Running Automated Tests

Run the full pytest suite:
```bash
pytest tests/
```
Output:
```
tests/test_api.py ....
tests/test_fuel.py ....
tests/test_geocoding.py ...
tests/test_ml.py ...
tests/test_preferences.py .....
tests/test_safety.py ...
tests/test_scoring.py ...
tests/test_weather.py ...
======================== 28 passed in 3.99s ========================
```

---

## 📡 API Reference

### Health & Status
- `GET /api/health` — Subsystem operational status and CARTO readiness.
- `GET /api/settings/api-status` — Connectivity status of external data providers.

### Route Optimization
- `POST /api/routes/geocode` — Resolve place name to coordinates.
- `POST /api/routes/calculate` — Execute full multi-factor optimization, return route geometry, smart scores, radar data, and AI explanation.

### History Management
- `GET /api/history` — Fetch recent route searches.
- `GET /api/history/{id}` — Fetch details of a specific saved search.
- `DELETE /api/history/{id}` — Delete a saved route record.
- `DELETE /api/history` — Clear search history.
