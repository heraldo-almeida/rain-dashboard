# streamlit_app.py
import streamlit as st
import requests
import pandas as pd
from dateutil import parser, tz
from datetime import datetime, timedelta

st.set_page_config(page_title="Rainfall Dashboard", layout="wide")

# ---- USER CONFIG ----
# Example: Santana de Parnaíba coords
DEFAULT_LAT = -23.5200
DEFAULT_LON = -46.8697
TIMEZONE = "America/Sao_Paulo"

st.title("Real-time Rainfall Dashboard (Open-Meteo)")

with st.sidebar:
    st.markdown("### Settings")
    lat = st.number_input("Latitude", value=float(DEFAULT_LAT), format="%.6f")
    lon = st.number_input("Longitude", value=float(DEFAULT_LON), format="%.6f")
    hours_history = st.slider("Hours of history", min_value=6, max_value=72, value=24, step=1)
    cache_minutes = st.slider("Auto cache (minutes)", min_value=1, max_value=60, value=5, step=1)
    if st.button("Refresh now"):
        st.experimental_memo.clear()

# ---- CACHING: cache data for cache_minutes to avoid repeated API calls ----
@st.cache_data(ttl=60*60)  # top-level cache fallback (in case user doesn't set)
def _fetch_forecast(lat, lon, hours):
    # fetch hourly precipitation for last `hours` + next few hours using Open-Meteo
    # We'll call the archive endpoint for explicit historical range, and the forecast for next hours.
    now = datetime.utcnow()
    # compute start/end in ISO format in UTC
    start_utc = now - timedelta(hours=hours)
    end_utc = now + timedelta(hours=3)  # small window into near future
    start_iso = start_utc.strftime("%Y-%m-%dT%H:%M")
    end_iso = end_utc.strftime("%Y-%m-%dT%H:%M")
    # Archive endpoint for historical (Open-Meteo)
    base_archive = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start": start_iso,
        "end": end_iso,
        "hourly": "precipitation",
        "timezone": TIMEZONE
    }
    r = requests.get(base_archive, params=params, timeout=15)
    r.raise_for_status()
    j = r.json()
    # build dataframe
    times = j.get("hourly", {}).get("time", [])
    prec = j.get("hourly", {}).get("precipitation", [])
    df = pd.DataFrame({"time": pd.to_datetime(times), "precip_mm": prec})
    df = df.set_index("time")
    return df, j

# Use cache with TTL selected by user
@st.cache_data(ttl=lambda: 60*int(st.session_state.get("cache_minutes", 5)))
def fetch_cached(lat, lon, hours):
    return _fetch_forecast(lat, lon, hours)

# store user cache_minutes in session_state (used by cache_data wrapper)
st.session_state["cache_minutes"] = st.sidebar.session_state.get("cache_minutes", 5)

try:
    # call fetch (this will be cached for cache_minutes)
    df, raw = fetch_cached(lat, lon, hours_history)
except Exception as e:
    st.error(f"Error fetching data: {e}")
    st.stop()

# ---- DISPLAY CURRENT INFO ----
now_local = datetime.now(tz.gettz(TIMEZONE))
st.subheader(f"Location: {lat:.4f}, {lon:.4f} — {now_local.strftime('%Y-%m-%d %H:%M %Z')}")

# latest precipitation
if not df.empty:
    latest_time = df.index.max()
    latest_prec = df.loc[latest_time, "precip_mm"]
    col1, col2, col3 = st.columns([1, 2, 2])
    col1.metric("Latest precipitation (mm)", f"{latest_prec:.2f}", delta=None)
    col2.write("**Last measurement**")
    col2.write(f"{latest_time.strftime('%Y-%m-%d %H:%M')}")
    # 24h sum
    last_24h = df.last("24H")["precip_mm"].sum()
    col3.metric("Accumulated last 24h (mm)", f"{last_24h:.2f}")
else:
    st.write("No data returned for this location/time range.")

# ---- PLOT ----
st.markdown("### Precipitation (last hours)")
chart_df = df.reset_index()
chart_df = chart_df.rename(columns={"time": "index"}).set_index("index")
st.line_chart(chart_df["precip_mm"])

# ---- RAW DATA TABLE ----
with st.expander("Show raw data (table)"):
    st.dataframe(df.tail(48))

st.markdown("---")
st.write("Data source: Open-Meteo Archive / Forecast APIs. This dashboard caches API results for a few minutes to avoid rate limits.")
