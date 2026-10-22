
import streamlit as st
import asyncio
import httpx

st.set_page_config(
    page_title="Smart Route AI",
    page_icon="🌍",
    layout="wide",
)

@st.cache_resource
def load_backend():
    from backend.main import app
    return app

st.title("🌍 Smart Route AI")
st.caption("Intelligent Route Optimization Platform")

try:
    fastapi_app = load_backend()
    st.success("FastAPI backend imported successfully.")
except Exception as exc:
    fastapi_app = None
    st.error(f"Backend import failed: {exc}")

async def api_request(method, path, **kwargs):
    if fastapi_app is None:
        raise RuntimeError("FastAPI backend is unavailable.")

    transport = httpx.ASGITransport(app=fastapi_app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://smart-route.local",
        timeout=30.0,
    ) as client:
        response = await client.request(method, path, **kwargs)
        response.raise_for_status()

        if "application/json" in response.headers.get(
            "content-type", ""
        ):
            return response.json()

        return response.text

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choose a section",
    [
        "Dashboard",
        "Route Planning",
        "Weather",
        "Visa Information",
        "Backend Diagnostics",
    ],
)

if page == "Dashboard":
    st.subheader("Dashboard")
    st.write("Your Smart Route AI deployment is being configured.")

    if st.button("Check Backend Health"):
        try:
            result = asyncio.run(
                api_request("GET", "/api/health")
            )
            st.json(result)
        except Exception as exc:
            st.error(f"Health check failed: {exc}")

elif page == "Route Planning":
    st.subheader("🗺️ Route Planning")
    origin = st.text_input("Starting location")
    destination = st.text_input("Destination")
    st.info(
        "Your existing route API must be connected using "
        "its actual endpoint and request format."
    )

elif page == "Weather":
    st.subheader("🌦️ Weather")
    st.text_input("Enter a location")
    st.info("Your existing weather API needs to be connected.")

elif page == "Visa Information":
    st.subheader("🛂 Visa Information")
    st.text_input("Enter a destination country")
    st.info("Your existing visa API needs to be connected.")

elif page == "Backend Diagnostics":
    st.subheader("🔧 Backend Diagnostics")

    if fastapi_app is not None:
        routes = []
        for route in fastapi_app.routes:
            routes.append({
                "Path": getattr(route, "path", ""),
                "Methods": ", ".join(sorted(
                    getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
                )),
                "Name": getattr(route, "name", ""),
            })

        st.dataframe(routes, use_container_width=True)
    else:
        st.error("The backend could not be loaded.")

st.divider()
st.caption("Smart Route AI | Streamlit Community Cloud")
