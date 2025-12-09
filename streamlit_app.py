# streamlit_app.py
import streamlit as st
import requests
import pandas as pd
from dateutil import parser, tz
from datetime import datetime, timedelta

st.set_page_config(page_title="Brazil Rainfall Dashboard", layout="wide")

# ---- BRAZILIAN STATE CAPITALS (lat, lon) ----
CAPITALS = {
    "Aracaju (SE)": (-10.9472, -37.0731),
    "Belém (PA)": (-1.4558, -48.5039),
    "Belo Horizonte (MG)": (-19.9167, -43.9345),
    "Boa Vista (RR)": (2.8208, -60.6717),
    "Brasília (DF)": (-15.7939, -47.8828),
    "Campo Grande (MS)": (-20.4697, -54.6200),
    "Cuiabá (MT)": (-15.6010, -56.0974),
    "Curitiba (PR)": (-25.4284, -49.2733),
    "Florianópolis (SC)": (-27.5949, -48.5482),
    "Fortaleza (CE)": (-3.7275, -38.5270),
    "Goiânia (GO)": (-16.6869, -49.2648),
    "João Pessoa (PB)": (-7.1150, -34.8631),
    "Macapá (AP)": (0.0349, -51.0694),
    "Maceió (AL)": (-9.6658, -35.7351),
    "Manaus (AM)": (-3.1190, -60.0217),
    "Natal (RN)": (-5.7945, -35.2110),
    "Palmas (TO)": (-10.1840, -48.3336),
    "Porto Alegre (RS)": (-30.0346, -51.2177),
    "Porto Velho (RO)": (-8.7608, -63.9004),
    "Recife (PE)": (-8.0476, -34.8770),
    "Rio Branco (AC)": (-9.9747, -67.8105),
    "Rio de Janeiro (RJ)": (-22.9068, -43.1729),
    "Salvador (BA)": (-12.9777, -38.5016),
    "São Luís (MA)": (-2.5391, -44.2825),
    "São Paulo (SP)": (-23.5505, -46.6333),
    "Teresina (PI)": (-5.0919, -42.8034),
    "Vitória (ES)": (-20.3155, -40.3128),
}

TIMEZONE = "America/Sao_Paulo"

st.title("🌧️ Real-time Rainfall Dashboard — Brazil Capitals")

# ---- SIDEBAR ----
with st.sidebar:
    st.header("Settings")

    city = st.selectbox("Select a capital city", list(CAPITALS.keys()))

    lat, lon = CAPITALS[city]

    hours_history = st.slider("Hours of history", 6, 72, 24)
    cache_minutes = st.slider("Cache duration (minutes)", 1, 60, 5)

    if st.button("Refresh now"):
        st.cache_data.clear()

# ---- DATA FETCHING ----

@st.cache_data(ttl=lambda: 60*int(st.session_state.get("cache_minutes", 5)))
def fetch_data(lat, lon, hours):

    now = datetime.utcnow()
    start = (now - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M")
    end = (now + timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M")

    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": lat,
        "longitude": lon,
        "start": start,
        "end": end,
        "hourly": "precipitation",
        "timezone": TIMEZONE
    }

    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    times = data["hourly"]["time"]
    rain = data["hourly"]["precipitation"]

    df = pd.DataFrame({"time": pd.to_datetime(times), "precip_mm": rain})
    df = df.set_index("time")

    return df

st.session_state["cache_minutes"] = cache_minutes

# ---- MAIN LOGIC ----

try:
    df = fetch_data(lat, lon, hours_history)
except Exception as e:
    st.error(f"Could not fetch data: {e}")
    st.stop()

now_local = datetime.now(tz.gettz(TIMEZONE))

st.subheader(f"{city} — {now_local.strftime('%Y-%m-%d %H:%M')}")

# ---- METRICS ----
if not df.empty:
    latest_time = df.index.max()
    latest_prec = df.loc[latest_time, "precip_mm"]
    last_24h = df.last("24H")["precip_mm"].sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Rain (mm)", f"{latest_prec:.2f}")
    col2.metric("Last 24h Accumulated (mm)", f"{last_24h:.2f}")
    col3.write(f"Last measurement: {latest_time.strftime('%H:%M')}")

else:
    st.warning("No data available.")
    st.stop()

# ---- CHART ----
st.markdown("### Rainfall Over Time")
chart_df = df.rename_axis("Time")
st.line_chart(chart_df)

# ---- TABLE ----
with st.expander("Show raw data table"):
    st.dataframe(df.tail(48))

st.caption("Data source: Open-Meteo (free). Dashboard cached to reduce API load.")
