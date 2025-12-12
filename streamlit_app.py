import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go
import os
import time

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")
st.set_page_config(page_title="Brazil Rain Dashboard", layout="wide")

# ------------------------------------------------------------------
# CITY COORDINATES (alphabetical order)
# ------------------------------------------------------------------
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

# ------------------------------------------------------------------
# SAFE REQUEST WRAPPER
# ------------------------------------------------------------------
def safe_request_json(url: str, timeout: int = 25):
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.json()
    except Exception as e:
        return {"__error__": str(e)}

# ------------------------------------------------------------------
# HOURLY PRECIP FETCH
# ------------------------------------------------------------------
def fetch_precip(lat: float, lon: float, city_name: str) -> pd.DataFrame:
    now = datetime.now(BR_TZ)
    start = now - timedelta(days=7)
    start_date = start.strftime("%Y-%m-%d")
    end_date = (now + timedelta(days=2)).strftime("%Y-%m-%d")

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation"
        f"&start_date={start_date}&end_date={end_date}"
        "&timezone=America%2FSao_Paulo"
    )

    data = safe_request_json(url)

    # Explicit API limit case
    if isinstance(data, dict) and data.get("error") is True:
        st.warning(f"Open-Meteo error: {data.get('reason')}")
        return pd.DataFrame(columns=["time", "precip"])

    # Missing hourly block
    if "hourly" not in data:
        st.error("Open-Meteo response missing 'hourly' payload. See debug below.")
        st.json(data)
        return pd.DataFrame(columns=["time", "precip"])

    hours = data["hourly"]["time"]
    precip = data["hourly"]["precipitation"]

    df = pd.DataFrame({"time": hours, "precip": precip})
    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    # Convert to timezone-aware BRT if naive
    try:
        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize("America/Sao_Paulo")
        else:
            df["time"] = df["time"].dt.tz_convert("America/Sao_Paulo")
    except Exception:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df["time"] = df["time"].dt.tz_localize("America/Sao_Paulo")

    df = df.sort_values("time").reset_index(drop=True)
    return df

# ------------------------------------------------------------------
# HOURLY CACHE: Only refreshes once per hour
# ------------------------------------------------------------------
@st.cache_data(ttl=3600)  # CACHE FOR 1 HOUR
def fetch_precip_cached(lat: float, lon: float, city_name: str):
    return fetch_precip(lat, lon, city_name)

# ------------------------------------------------------------------
# MONTHLY PRECIP (12-month bar chart)
# ------------------------------------------------------------------
def fetch_monthly_precip(lat: float, lon: float):
    today = datetime.utcnow().date()
    start = today - timedelta(days=365)

    url = (
        "https://archive-api.open-meteo.com/v1/era5"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start}&end_date={today}"
        "&daily=precipitation_sum"
        "&timezone=America%2FSao_Paulo"
    )

    data = safe_request_json(url)

    if "daily" not in data:
        return pd.DataFrame(columns=["month", "precip"])

    dates = data["daily"]["time"]
    precip = data["daily"]["precipitation_sum"]

    df = pd.DataFrame({"date": pd.to_datetime(dates), "precip": precip})
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    return df.groupby("month", as_index=False)["precip"].sum().tail(12)

# ------------------------------------------------------------------
# UI
# ------------------------------------------------------------------
st.title("🌧️ Brazil Precipitation Dashboard (7-day Rolling + Forecast)")

city = st.selectbox("Select a city:", list(CITIES.keys()))
lat, lon = CITIES[city]

# ------------------------------------------------------------------
# FETCH DATA (HOURLY + MONTHLY)
# ------------------------------------------------------------------
with st.spinner("Fetching hourly precipitation (cached for 1 hour)..."):
    df = fetch_precip_cached(lat, lon, city)

with st.spinner("Fetching monthly precipitation..."):
    df_monthly = fetch_monthly_precip(lat, lon)

# ------------------------------------------------------------------
# HANDLE EMPTY HOURLY DATA
# ------------------------------------------------------------------
if df.empty:
    st.error("No hourly precipitation data available.")
    st.stop()

# ------------------------------------------------------------------
# SPLIT HISTORICAL VS FORECAST
# ------------------------------------------------------------------
now = datetime.now(BR_TZ)
try:
    df["is_forecast"] = df["time"] > now
except Exception:
    df["is_forecast"] = False

df_hist = df[df["is_forecast"] == False]
df_fore = df[df["is_forecast"] == True]

# ------------------------------------------------------------------
# LINE PLOT
# ------------------------------------------------------------------
fig = go.Figure()

if not df_hist.empty:
    fig.add_trace(go.Scatter(
        x=df_hist["time"],
        y=df_hist["precip"],
        mode="lines",
        name="Historical",
        line=dict(width=3),
    ))

if not df_fore.empty:
    fig.add_trace(go.Scatter(
        x=df_fore["time"],
        y=df_fore["precip"],
        mode="lines",
        name="Forecast",
        line=dict(width=3, dash="dash"),
    ))

fig.update_layout(
    title=f"Hourly Precipitation — {city}",
    xaxis_title="Date / Time (UTC-3)",
    yaxis_title="Precipitation (mm)",
    hovermode="x unified",
    template="plotly_white",
)

st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------
# MONTHLY BAR PLOT
# ------------------------------------------------------------------
st.subheader("📊 Total Monthly Precipitation (Last 12 Months)")

if df_monthly.empty:
    st.info("No monthly data available.")
else:
    fig_m = go.Figure()
    fig_m.add_trace(go.Bar(
        x=df_monthly["month"],
        y=df_monthly["precip"],
        name="Monthly Total",
    ))
    fig_m.update_layout(
        xaxis_title="Month",
        yaxis_title="Precipitation (mm)",
        template="plotly_white"
    )
    st.plotly_chart(fig_m, use_container_width=True)

# ------------------------------------------------------------------
# DEBUG PANEL
# ------------------------------------------------------------------
with st.expander("🛠 Debug: Raw DataFrames"):
    st.write("Hourly Data:")
    st.dataframe(df)
    st.write("Monthly Data:")
    st.dataframe(df_monthly)
