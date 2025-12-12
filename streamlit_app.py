import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go
import os

# ------------------------------------------------------------------
# Branding import (do not modify company_branding.py)
# ------------------------------------------------------------------
try:
    import company_branding as cb
except Exception:
    cb = None

# safe access to branding variables (do not modify company_branding.py)
PRIMARY_LOGO = None
SECONDARY_LOGO = None
COMPANY_NAME = ""
PRODUCT_NAME = "Rainfall Insights"
TAGLINE = "Brazilian Precipitation Analytics"

if cb is not None:
    PRIMARY_LOGO = getattr(cb, "PRIMARY_LOGO_PATH", None)
    SECONDARY_LOGO = getattr(cb, "SECONDARY_LOGO_PATH", None)
    COMPANY_NAME = getattr(cb, "COMPANY_NAME", COMPANY_NAME) or COMPANY_NAME
    PRODUCT_NAME = getattr(cb, "PRODUCT_NAME", PRODUCT_NAME) or PRODUCT_NAME
    TAGLINE = getattr(cb, "TAGLINE", TAGLINE) or TAGLINE

# ------------------------------------------------------------------
# Utility to decide if an image path is usable
# ------------------------------------------------------------------
def is_valid_image(path: str) -> bool:
    if not path or not isinstance(path, str):
        return False
    path = path.strip()
    if path == "":
        return False
    if path.startswith("http://") or path.startswith("https://"):
        return True
    return os.path.exists(path)

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")
st.set_page_config(page_title="Brazil Rain Dashboard", layout="wide")

# ------------------------------------------------------------------
# Header with logos (Option B: left and right)
# ------------------------------------------------------------------
col_l, col_c, col_r = st.columns([1, 2, 1])

with col_l:
    if is_valid_image(PRIMARY_LOGO):
        try:
            st.image(PRIMARY_LOGO, width=160)
        except Exception:
            st.write("")  # keep space, do not crash
    else:
        # keep space to maintain header balance (empty string)
        st.write("")

with col_c:
    st.markdown(
        f"""
        <div style="text-align:center;">
            <div style="font-size:18px;color:#222;margin-bottom:6px;"><strong>{PRODUCT_NAME}</strong></div>
            <div style="font-size:13px;color:#555;margin-bottom:2px;">{COMPANY_NAME}</div>
            <div style="font-size:12px;color:#777;">{TAGLINE}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_r:
    if is_valid_image(SECONDARY_LOGO):
        try:
            st.image(SECONDARY_LOGO, width=140)
        except Exception:
            st.write("")
    else:
        st.write("")

st.markdown("---")

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
# SAFE REQUEST WRAPPER
# ------------------------------------------------------------------
def safe_request_json(url: str):
    try:
        r = requests.get(url, timeout=15)
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

    # If API explicitly returned an error (e.g., rate limit), return empty df and raw json
    if isinstance(data, dict) and data.get("error") is True:
        return pd.DataFrame(columns=["time", "precip"]), data

    if "hourly" not in data:
        return pd.DataFrame(columns=["time", "precip"]), data

    hours = data["hourly"].get("time", [])
    precip = data["hourly"].get("precipitation", [])

    df = pd.DataFrame({"time": hours, "precip": precip})
    # parse times robustly
    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    try:
        if df["time"].dt.tz is None:
            df["time"] = df["time"].dt.tz_localize("America/Sao_Paulo")
        else:
            df["time"] = df["time"].dt.tz_convert("America/Sao_Paulo")
    except Exception:
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df["time"] = df["time"].dt.tz_localize("America/Sao_Paulo", ambiguous="NaT", nonexistent="shift_forward")
    df = df.sort_values("time").reset_index(drop=True)
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

    if isinstance(data, dict) and data.get("error") is True:
        return pd.DataFrame(columns=["month", "precip"]), data

    if "daily" not in data:
        return pd.DataFrame(columns=["month", "precip"]), data

    dates = data["daily"].get("time", [])
    precip = data["daily"].get("precipitation_sum", [])

    df = pd.DataFrame({"date": pd.to_datetime(dates, errors="coerce"), "precip": precip})
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df_month = df.groupby("month", as_index=False)["precip"].sum().sort_values("month").tail(12)
    return df_month, data

# ------------------------------------------------------------------
# MONTHLY CACHE WRAPPER (1 hour)
# ------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_monthly_precip_cached(lat, lon):
    return fetch_monthly_precip(lat, lon)

# ------------------------------------------------------------------
# STREAMLIT UI
# ------------------------------------------------------------------
st.title("🌧️ Brazil Precipitation Dashboard")

city = st.selectbox("Select a city:", list(CITIES.keys()))
lat, lon = CITIES[city]

# Fetch hourly and monthly data (cached hourly)
with st.spinner("Fetching hourly data (cached hourly)..."):
    df_hourly, raw_hourly = fetch_precip_cached(lat, lon, city)

with st.spinner("Fetching monthly data (cached hourly)..."):
    df_monthly, raw_monthly = fetch_monthly_precip_cached(lat, lon)

# If hourly data failed
if df_hourly.empty:
    st.warning("No hourly data available to plot. See debug section for raw response.")
else:
    now = datetime.now(BR_TZ)
    try:
        df_hourly["is_forecast"] = df_hourly["time"] > now
    except Exception:
        df_hourly["is_forecast"] = False

    df_hist = df_hourly[df_hourly["is_forecast"] == False]
    df_fore = df_hourly[df_hourly["is_forecast"] == True]

    fig = go.Figure()
    if not df_hist.empty:
        fig.add_trace(go.Scatter(
            x=df_hist["time"], y=df_hist["precip"],
            mode="lines",
            name="Historical Precipitation",
            line=dict(width=3)
        ))
    if not df_fore.empty:
        fig.add_trace(go.Scatter(
            x=df_fore["time"], y=df_fore["precip"],
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

# Monthly bar plot
st.subheader("📊 Total Monthly Precipitation — Last 12 Months")
if df_monthly.empty:
    st.info("No monthly precipitation data available for this location.")
else:
    fig_month = go.Figure()
    fig_month.add_trace(go.Bar(x=df_monthly["month"], y=df_monthly["precip"], name="Monthly total"))
    fig_month.update_layout(xaxis_title="Month", yaxis_title="Precipitation (mm)", hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig_month, use_container_width=True)

# Current status card (2 mm threshold)
if not df_hourly.empty:
    last_obs = df_hourly[df_hourly["is_forecast"] == False]
    if last_obs.empty:
        last_row = df_hourly.iloc[-1]
    else:
        last_row = last_obs.iloc[-1]
    latest_precip = float(last_row["precip"]) if pd.notna(last_row["precip"]) else 0.0
    latest_time = last_row["time"]
    if latest_time is not None and hasattr(latest_time, "tz_convert"):
        latest_time_str = latest_time.tz_convert("America/Sao_Paulo").strftime("%d/%m/%Y %H:%M")
    else:
        latest_time_str = str(latest_time)

    if latest_precip <= 0:
        emoji = "☀️"
        label = "Not raining"
    elif latest_precip <= 2:
        emoji = "🌦️"
        label = "Mild rain"
    else:
        emoji = "⛈️"
        label = "Heavy rain"

    st.markdown(
        f"""
        <div style="padding:12px 16px;border-radius:10px;border:1px solid #e6e6e6;background:#ffffffbb;">
           <strong>{emoji} Current Rain Status — {city}</strong><br/>
           <span style="font-size:14px;">{label} · Last hour: <strong>{latest_precip:.2f} mm</strong></span><br/>
           <small style="color:#666;">Time: {latest_time_str} (BRT)</small>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Debug panels
with st.expander("🛠 Debug: Raw hourly API response"):
    st.json(raw_hourly)

with st.expander("🛠 Debug: Raw monthly API response"):
    st.json(raw_monthly)

with st.expander("🛠 Debug: Hourly DataFrame"):
    st.dataframe(df_hourly)

with st.expander("🛠 Debug: Monthly DataFrame"):
    st.dataframe(df_monthly)
