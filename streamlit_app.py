import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go

# ------------------------------------------------------------------
# CITY COORDINATES (12 cities, alphabetical order)
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
# TIMEZONE
# ------------------------------------------------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")

# ------------------------------------------------------------------
# SAFE REQUEST WRAPPER
# ------------------------------------------------------------------
def safe_request_json(url: str):
    """Perform a request but never crash if Open-Meteo returns error."""
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": True, "reason": str(e)}

# ------------------------------------------------------------------
# FETCH HOURLY PRECIPITATION (7 days history + forecast)
# ------------------------------------------------------------------
def fetch_precip(lat, lon, city_name):
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

    data = safe_request_json(url)

    # Handle missing data
    if "hourly" not in data:
        st.error(f"Open-Meteo response missing 'hourly' payload for {city_name}. Reason: {data.get('reason')}")
        return pd.DataFrame(columns=["time", "precip", "is_forecast", "raw_json"]), data

    hours = data["hourly"]["time"]
    precip = data["hourly"]["precipitation"]

    df = pd.DataFrame({"time": hours, "precip": precip})
    df["time"] = pd.to_datetime(df["time"]).dt.tz_localize("America/Sao_Paulo")
    df.sort_values("time", inplace=True)

    return df, data

# ------------------------------------------------------------------
# HOURLY CACHE WRAPPER (1 hour)
# ------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_precip_cached(lat, lon, city):
    return fetch_precip(lat, lon, city)

# ------------------------------------------------------------------
# FETCH MONTHLY PRECIP (last 12 months)
# ------------------------------------------------------------------
def fetch_monthly_precip(lat, lon):
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
        return pd.DataFrame(columns=["month", "precip"]), data

    dates = data["daily"]["time"]
    precip = data["daily"]["precipitation_sum"]

    df = pd.DataFrame({"date": pd.to_datetime(dates), "precip": precip})
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    df_month = df.groupby("month", as_index=False)["precip"].sum()

    return df_month.tail(12), data

# ------------------------------------------------------------------
# MONTHLY CACHE WRAPPER (1 hour)
# ------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_monthly_precip_cached(lat, lon):
    return fetch_monthly_precip(lat, lon)

# ------------------------------------------------------------------
# STREAMLIT UI
# ------------------------------------------------------------------
st.set_page_config(page_title="Brazil Rain Dashboard", layout="wide")
st.title("🌧️ Brazil Precipitation Dashboard")

city = st.selectbox("Select a city:", list(CITIES.keys()))
lat, lon = CITIES[city]

# Hourly
with st.spinner("Fetching hourly data..."):
    df_hourly, raw_hourly = fetch_precip_cached(lat, lon, city)

# Monthly
with st.spinner("Fetching monthly data..."):
    df_monthly, raw_monthly = fetch_monthly_precip_cached(lat, lon)

# If hourly data failed → stop gracefully
if df_hourly.empty:
    st.warning("No hourly data available — see debug section below.")
else:
    now = datetime.now(BR_TZ)
    df_hourly["is_forecast"] = df_hourly["time"] > now

    df_hist = df_hourly[df_hourly["is_forecast"] == False]
    df_fore = df_hourly[df_hourly["is_forecast"] == True]

    # ------------------------------------------------------------------
    # HOURLY LINE PLOT
    # ------------------------------------------------------------------
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_hist["time"], y=df_hist["precip"],
        mode="lines", name="Historical Precipitation",
        line=dict(width=3)
    ))

    fig.add_trace(go.Scatter(
        x=df_fore["time"], y=df_fore["precip"],
        mode="lines", name="Forecast Precipitation",
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

# ------------------------------------------------------------------
# MONTHLY BAR CHART
# ------------------------------------------------------------------
if not df_monthly.empty:
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(
        x=df_monthly["month"],
        y=df_monthly["precip"],
        name="Monthly Precipitation",
    ))

    fig2.update_layout(
        title="Total Monthly Precipitation (Last 12 Months)",
        xaxis_title="Month",
        yaxis_title="Precipitation (mm)",
        template="plotly_white",
    )

    st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------------------
# DEBUG SECTIONS
# ------------------------------------------------------------------
with st.expander("🛠 Debug: Raw hourly API response"):
    st.json(raw_hourly)

with st.expander("🛠 Debug: Raw monthly API response"):
    st.json(raw_monthly)

with st.expander("🛠 Raw hourly DataFrame"):
    st.dataframe(df_hourly, use_container_width=True)

with st.expander("🛠 Raw monthly DataFrame"):
    st.dataframe(df_monthly, use_container_width=True)
