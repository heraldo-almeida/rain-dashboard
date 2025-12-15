import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go
import os
import math

# ------------------------------------------------------------------
# Branding import (DO NOT MODIFY company_branding.py)
# ------------------------------------------------------------------
try:
    import company_branding as cb
except Exception:
    cb = None

PRIMARY_LOGO = getattr(cb, "PRIMARY_LOGO_PATH", None) if cb else None
SECONDARY_LOGO = getattr(cb, "SECONDARY_LOGO_PATH", None) if cb else None
COMPANY_NAME = getattr(cb, "COMPANY_NAME", "") if cb else ""
PRODUCT_NAME = getattr(cb, "PRODUCT_NAME", "Rainfall Insights") if cb else "Rainfall Insights"
TAGLINE = getattr(cb, "TAGLINE", "Brazilian Precipitation Analytics") if cb else "Brazilian Precipitation Analytics"

# ------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------
def is_valid_image(path: str) -> bool:
    if not path or not isinstance(path, str):
        return False
    path = path.strip()
    if path.startswith("http"):
        return True
    return os.path.exists(path)

def safe_request(url, params):
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": True, "reason": str(e)}

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")
st.set_page_config(page_title="Brazil Rain Dashboard", layout="wide")

GOOGLE_API_KEY = st.secrets.get("GOOGLE_WEATHER_API_KEY", "")

# ------------------------------------------------------------------
# Header (logos left / right)
# ------------------------------------------------------------------
l, c, r = st.columns([1, 2, 1])

with l:
    if is_valid_image(PRIMARY_LOGO):
        st.image(PRIMARY_LOGO, width=160)
    else:
        st.write("")

with c:
    st.markdown(
        f"""
        <div style="text-align:center;">
            <div style="font-size:18px;"><strong>{PRODUCT_NAME}</strong></div>
            <div style="font-size:13px;color:#555;">{COMPANY_NAME}</div>
            <div style="font-size:12px;color:#777;">{TAGLINE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with r:
    if is_valid_image(SECONDARY_LOGO):
        st.image(SECONDARY_LOGO, width=140)
    else:
        st.write("")

st.markdown("---")

# ------------------------------------------------------------------
# Cities
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
# Radius sampling (5 km)
# ------------------------------------------------------------------
def generate_radius_points(lat, lon, radius_km=5, step_km=2.5):
    points = []
    lat_km = 1 / 111
    lon_km = 1 / (111 * math.cos(math.radians(lat)))
    steps = int(radius_km / step_km)

    for i in range(-steps, steps + 1):
        for j in range(-steps, steps + 1):
            points.append((
                lat + i * step_km * lat_km,
                lon + j * step_km * lon_km
            ))
    return points

# ------------------------------------------------------------------
# Google Weather API – single point
# ------------------------------------------------------------------
def fetch_google_hourly_precip(lat, lon):
    url = "https://weather.googleapis.com/v1/forecast/hours"

    params = {
        "location.latitude": lat,
        "location.longitude": lon,
        "hours": 384,
        "unitsSystem": "METRIC",
        "key": GOOGLE_API_KEY,
    }

    data = safe_request(url, params)
    if data.get("error") or "forecastHours" not in data:
        return pd.DataFrame(columns=["time", "precip"]), data

    rows = []
    for h in data["forecastHours"]:
        rows.append({
            "time": pd.to_datetime(h["forecastTime"]),
            "precip": h.get("precipitation", {}).get("amount", {}).get("value", 0.0)
        })

    df = pd.DataFrame(rows)
    df["time"] = df["time"].dt.tz_convert("America/Sao_Paulo")
    return df, data

# ------------------------------------------------------------------
# Max precipitation within 5 km radius
# ------------------------------------------------------------------
def fetch_max_precip_radius(lat, lon):
    points = generate_radius_points(lat, lon, radius_km=5)
    dfs = []
    raw = []

    for p_lat, p_lon in points:
        df, raw_resp = fetch_google_hourly_precip(p_lat, p_lon)
        raw.append(raw_resp)
        if not df.empty:
            dfs.append(df)

    if not dfs:
        return pd.DataFrame(columns=["time", "max_precip"]), raw

    combined = pd.concat(dfs)
    df_max = (
        combined
        .groupby("time", as_index=False)["precip"]
        .max()
        .rename(columns={"precip": "max_precip"})
        .sort_values("time")
    )

    return df_max, raw

@st.cache_data(ttl=3600)
def fetch_max_precip_radius_cached(lat, lon):
    return fetch_max_precip_radius(lat, lon)

# ------------------------------------------------------------------
# STREAMLIT UI
# ------------------------------------------------------------------
st.title("🌧️ Brazil Precipitation Dashboard (Google Weather API)")

city = st.selectbox("Select a city:", list(CITIES.keys()))
lat, lon = CITIES[city]

with st.spinner("Fetching Google Weather data (cached hourly)..."):
    df_radius, raw_responses = fetch_max_precip_radius_cached(lat, lon)

# ------------------------------------------------------------------
# Plot
# ------------------------------------------------------------------
if df_radius.empty:
    st.warning("No precipitation data available.")
else:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_radius["time"],
        y=df_radius["max_precip"],
        mode="lines",
        name="Max precipitation (5 km radius)",
        line=dict(width=3)
    ))

    fig.update_layout(
        title=f"Hourly Max Precipitation (5 km radius) — {city}",
        xaxis_title="Date / Time (BRT)",
        yaxis_title="Precipitation (mm)",
        hovermode="x unified",
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------
# Current status card
# ------------------------------------------------------------------
if not df_radius.empty:
    last_row = df_radius.iloc[-1]
    val = float(last_row["max_precip"])
    time_str = last_row["time"].strftime("%d/%m/%Y %H:%M")

    if val <= 0:
        label = "Not raining"
        emoji = "☀️"
    elif val <= 2:
        label = "Mild rain"
        emoji = "🌦️"
    else:
        label = "Heavy rain"
        emoji = "⛈️"

    st.markdown(
        f"""
        <div style="padding:12px;border-radius:10px;border:1px solid #e6e6e6;background:#ffffffcc;">
            <strong>{emoji} Current Rain Status — {city}</strong><br/>
            {label} · Last hour: <strong>{val:.2f} mm</strong><br/>
            <small>{time_str} (BRT)</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ------------------------------------------------------------------
# Debug
# ------------------------------------------------------------------
with st.expander("🛠 Debug: Raw Google API responses"):
    st.json(raw_responses)

with st.expander("🛠 Debug: Aggregated DataFrame"):
    st.dataframe(df_radius)
