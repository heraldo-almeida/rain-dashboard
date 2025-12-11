import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go

# ---------------------------------------------------------
# BRANDING (background + logos)
# ---------------------------------------------------------
from company_branding import apply_background, BACKGROUND_IMAGE

# Apply the background immediately after setting the page config
st.set_page_config(page_title="Brazil Rain Dashboard", layout="wide")
apply_background(BACKGROUND_IMAGE, opacity=0.35)

# ---------------------------------------------------------
# CITY COORDINATES
# ---------------------------------------------------------
CITIES = {
    "Botucatu": (-22.8858, -48.4450),
    "Campinas": (-22.9058, -47.0608),
    "Curitiba": (-25.4284, -49.2733),
    "Goiânia": (-16.6864, -49.2643),
    "Macapá": (0.0349, -51.0694),
    "Poços de Caldas": (-21.7878, -46.5608),
    "Porto Alegre": (-30.0346, -51.2177),
    "Recife": (-8.0476, -34.8770),
    "Rio de Janeiro": (-22.9068, -43.1729),
    "Salvador": (-12.9777, -38.5016),
    "São Paulo": (-23.5505, -46.6333),
    "Vassouras": (-22.4039, -43.6628),
}

# ---------------------------------------------------------
# TIMEZONE
# ---------------------------------------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")

# ---------------------------------------------------------
# FETCH PRECIPITATION DATA
# ---------------------------------------------------------
def fetch_precip(lat, lon):
    now = datetime.now(BR_TZ)
    start = now - timedelta(days=7)

    start_str = start.strftime("%Y-%m-%dT%H:00")
    end_str = (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:00")

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation"
        f"&start_date={start_str[:10]}&end_date={end_str[:10]}"
        "&timezone=America%2FSao_Paulo"
    )

    r = requests.get(url)
    data = r.json()

    hours = data["hourly"]["time"]
    precip = data["hourly"]["precipitation"]

    df = pd.DataFrame({"time": hours, "precip": precip})
    df["time"] = pd.to_datetime(df["time"], utc=False).dt.tz_localize("America/Sao_Paulo")
    df.sort_values("time", inplace=True)

    return df

# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
st.title("🌧️ Brazil Precipitation Dashboard (7-Day Rolling + Forecast)")

city = st.selectbox("Select a city:", list(CITIES.keys()))
lat, lon = CITIES[city]

with st.spinner("Fetching data..."):
    df = fetch_precip(lat, lon)

# ---------------------------------------------------------
# HISTORICAL VS FORECAST SPLIT
# ---------------------------------------------------------
now = datetime.now(BR_TZ)
df["is_forecast"] = df["time"] > now

df_hist = df[df["is_forecast"] == False]
df_fore = df[df["is_forecast"] == True]

# ---------------------------------------------------------
# PLOT
# ---------------------------------------------------------
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df_hist["time"],
    y=df_hist["precip"],
    mode="lines",
    name="Historical Precipitation",
    line=dict(width=3)
))

fig.add_trace(go.Scatter(
    x=df_fore["time"],
    y=df_fore["precip"],
    mode="lines",
    name="Forecast Precipitation",
    line=dict(width=3, dash="dash")
))

fig.update_layout(
    title=f"Hourly Precipitation — {city}",
    xaxis_title="Date / Time (UTC-3)",
    yaxis_title="Precipitation (mm)",
    hovermode="x unified",
    template="plotly_white",
)

st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# DEBUG TABLE
# ---------------------------------------------------------
with st.expander("🛠 Debug: Raw hourly data returned by Open-Meteo"):
    st.dataframe(df, use_container_width=True)
