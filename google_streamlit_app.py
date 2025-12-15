import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go
import os

# ------------------------------------------------------------
# Branding (DO NOT MODIFY company_branding.py)
# ------------------------------------------------------------
try:
    import company_branding as cb
except Exception:
    cb = None

PRIMARY_LOGO = getattr(cb, "PRIMARY_LOGO_PATH", None) if cb else None
SECONDARY_LOGO = getattr(cb, "SECONDARY_LOGO_PATH", None) if cb else None
COMPANY_NAME = getattr(cb, "COMPANY_NAME", "") if cb else ""
PRODUCT_NAME = getattr(cb, "PRODUCT_NAME", "Rainfall Insights") if cb else "Rainfall Insights"
TAGLINE = getattr(cb, "TAGLINE", "Brazilian Precipitation Analytics") if cb else "Brazilian Precipitation Analytics"

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def is_valid_image(path: str) -> bool:
    if not path or not isinstance(path, str):
        return False
    path = path.strip()
    if path.startswith("http"):
        return True
    return os.path.exists(path)

def safe_json(url: str):
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": True, "reason": str(e)}

# ------------------------------------------------------------
# Config
# ------------------------------------------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")
st.set_page_config(page_title="Brazil Rain Dashboard", layout="wide")

# ------------------------------------------------------------
# Header (logos left / right)
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Cities
# ------------------------------------------------------------
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

# ------------------------------------------------------------
# Open-Meteo: hourly precipitation (7d past + 2d forecast)
# ------------------------------------------------------------
def fetch_hourly_precip(lat, lon):
    now = datetime.now(BR_TZ)
    start = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    end = (now + timedelta(days=2)).strftime("%Y-%m-%d")

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation"
        f"&start_date={start}&end_date={end}"
        "&timezone=America%2FSao_Paulo"
    )

    data = safe_json(url)
    if data.get("error") or "hourly" not in data:
        return pd.DataFrame(columns=["time", "precip"]), data

    df = pd.DataFrame({
        "time": pd.to_datetime(data["hourly"]["time"], errors="coerce"),
        "precip": data["hourly"]["precipitation"],
    })

    df["time"] = df["time"].dt.tz_localize("America/Sao_Paulo", nonexistent="shift_forward", ambiguous="NaT")
    return df.sort_values("time").reset_index(drop=True), data

@st.cache_data(ttl=3600)
def fetch_hourly_cached(lat, lon):
    return fetch_hourly_precip(lat, lon)

# ------------------------------------------------------------
# Open-Meteo ERA5: monthly totals (last 12 months)
# ------------------------------------------------------------
def fetch_monthly_precip(lat, lon):
    end = datetime.utcnow().date()
    start = end - timedelta(days=365)

    url = (
        "https://archive-api.open-meteo.com/v1/era5"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start}&end_date={end}"
        "&daily=precipitation_sum"
        "&timezone=America%2FSao_Paulo"
    )

    data = safe_json(url)
    if data.get("error") or "daily" not in data:
        return pd.DataFrame(columns=["month", "precip"]), data

    df = pd.DataFrame({
        "date": pd.to_datetime(data["daily"]["time"], errors="coerce"),
        "precip": data["daily"]["precipitation_sum"],
    })

    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df = df.groupby("month", as_index=False)["precip"].sum().tail(12)
    return df, data

@st.cache_data(ttl=3600)
def fetch_monthly_cached(lat, lon):
    return fetch_monthly_precip(lat, lon)

# ------------------------------------------------------------
# UI
# ------------------------------------------------------------
st.title("🌧️ Brazil Precipitation Dashboard")

city = st.selectbox("Select a city:", list(CITIES.keys()))
lat, lon = CITIES[city]

with st.spinner("Loading hourly precipitation..."):
    df_hourly, raw_hourly = fetch_hourly_cached(lat, lon)

with st.spinner("Loading monthly precipitation..."):
    df_monthly, raw_monthly = fetch_monthly_cached(lat, lon)

# ------------------------------------------------------------
# Hourly chart
# ------------------------------------------------------------
if not df_hourly.empty:
    now = datetime.now(BR_TZ)
    df_hourly["forecast"] = df_hourly["time"] > now

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_hourly[~df_hourly["forecast"]]["time"],
        y=df_hourly[~df_hourly["forecast"]]["precip"],
        name="Observed",
        line=dict(width=3)
    ))
    fig.add_trace(go.Scatter(
        x=df_hourly[df_hourly["forecast"]]["time"],
        y=df_hourly[df_hourly["forecast"]]["precip"],
        name="Forecast",
        line=dict(width=3, dash="dash")
    ))

    fig.update_layout(
        title=f"Hourly Precipitation — {city}",
        yaxis_title="mm",
        hovermode="x unified",
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No hourly data available.")

# ------------------------------------------------------------
# Monthly chart
# ------------------------------------------------------------
st.subheader("📊 Monthly Total — Last 12 Months")

if not df_monthly.empty:
    fig = go.Figure(go.Bar(
        x=df_monthly["month"],
        y=df_monthly["precip"]
    ))
    fig.update_layout(
        yaxis_title="mm",
        hovermode="x unified",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No monthly data available.")

# ------------------------------------------------------------
# Debug
# ------------------------------------------------------------
with st.expander("Debug — Hourly API"):
    st.json(raw_hourly)

with st.expander("Debug — Monthly API"):
    st.json(raw_monthly)
