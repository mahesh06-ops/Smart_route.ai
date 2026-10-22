
import streamlit as st

st.set_page_config(
    page_title="Smart Route AI",
    page_icon="🌍",
    layout="wide",
)

backend_url = st.secrets.get("BACKEND_URL", "").rstrip("/")

if not backend_url:
    st.error("Backend URL is not configured.")
    st.info(
        "Add BACKEND_URL in Streamlit Cloud "
        "app settings after deploying your backend."
    )
else:
    st.components.v1.iframe(
        backend_url,
        height=900,
        scrolling=True,
    )
