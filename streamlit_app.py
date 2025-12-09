import streamlit as st
import pandas as pd
import requests
import pytz
from datetime import datetime, timedelta
import plotly.graph_objects as go

# =========================================================
# BASIC CONFIG
# =========================================================
BR_TZ = pytz.timezone("America/Sao_Paulo")

st.set_page_config(page_title="Brazil Precipitation Dashboard", layout="wide")
st.title("🌧️ Brazil Precipitation Dashboard")

# =========================================================
# CITY LIST (12 CITIES, ALPHABETICAL)
# =========================================================
CITIES = {
    "Botucatu": (-22.8858, -48.4450),
    "Campinas": (-22.9058, -47.0608),
    "Curitiba": (-25.4284, -49.2733),
    "Goiânia": (-16.6869, -49.2648),
    "Macapá": (0.0349, -51.0694),
    "Poços de Caldas": (-21.7878, -46.5608),
    "Porto Alegre": (-30.0346, -51.2177),
    "Recife": (-8.0476, -34.8770),
    "Rio de Janeiro": (-22.9068, -43.1729),
    "Salvador": (-12.9777, -38.5016),
    "São Paulo": (-23.5505, -46.6333),
    "Vassouras": (-22.4039, -43.6628),
}
CITY_NAMES = sorted(CITIES.keys())

# =========================================================
# HELPERS
# =========================================================
def rain_emoji(value: float) -> str:
    if value <= 0:
        return "☀️ Not raining"
    elif value <= 2:
        return "🌧️ Mild rain"
    else:
        return "⛈️ Strong rain"


@st.cache_data(show_spinner=False)
def get_hourly_precip(lat: float, lon: float) -> pd.DataFrame:
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation&past_days=7&forecast_days=2"
        "&timezone=America%2FSao_Paulo"
    )
    data = requests.get(url, timeout=25).json()
    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


@st.cache_data(show_spinner=False)
def get_monthly_precip(lat: float, lon: float) -> pd.DataFrame:
    now = datetime.utcnow()
    end_date = now.date()
    start_date = (now - timedelta(days=730)).date()

    url = (
        "https://climate-api.open-meteo.com/v1/climate?"
        f"latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        "&monthly=precipitation_sum"
    )
    data = requests.get(url, timeout=25).json()

    if "monthly" not in data:
        return pd.DataFrame(columns=["month", "precip"])

    months = data["monthly"].get("time", [])
    precip = data["monthly"].get("precipitation_sum", [])
    if not months:
        return pd.DataFrame(columns=["month", "precip"])

    df = pd.DataFrame({"month": pd.to_datetime(months), "precip": precip})
    df = df.sort_values("month").tail(12)
    return df

# =========================================================
# UI – CITY SELECTION
# =========================================================
city = st.selectbox("Select city", CITY_NAMES)
lat, lon = CITIES[city]

# =========================================================
# LOAD DATA
# =========================================================
with st.spinner("Loading hourly data..."):
    df_hourly = get_hourly_precip(lat, lon)

with st.spinner("Loading monthly data..."):
    df_monthly = get_monthly_precip(lat, lon)

# =========================================================
# FIX TIMEZONE / TIMESTAMP COMPARISON
# =========================================================
df_hourly["time"] = pd.to_datetime(df_hourly["time"], utc=True)
df_hourly["time"] = df_hourly["time"].dt.tz_convert("America/Sao_Paulo").dt.tz_localize(None)

now_br_aware = datetime.now(BR_TZ)
now_br = now_br_aware.replace(tzinfo=None)

df_hourly["ts"] = df_hourly["time"].astype("int64")
now_ts = pd.Timestamp(now_br).value

hist_mask = df_hourly["ts"] <= now_ts
df_hist = df_hourly[hist_mask]
df_forecast = df_hourly[~hist_mask]

# =========================================================
# CURRENT PRECIP + EMOJI
# =========================================================
if not df_hist.empty:
    latest_precip = float(df_hist.iloc[-1]["precipitation"])
else:
    latest_precip = float(df_hourly.iloc[-1]["precipitation"])

status = rain_emoji(latest_precip)

st.subheader(f"{city} — Current rain status: {status}")
st.caption(
    f"Last observed hourly precipitation: {latest_precip:.2f} mm "
    f"(local time {now_br_aware.strftime('%d/%m/%Y %H:%M')} BRT)"
)

# =========================================================
# HOURLY LINE CHART (7 DAYS + FORECAST DASHED)
# =========================================================
fig_hourly = go.Figure()

if not df_hist.empty:
    fig_hourly.add_trace(
        go.Scatter(
            x=df_hist["time"],
            y=df_hist["precipitation"],
            mode="lines",
            name="History",
        )
    )

if not df_forecast.empty:
    fig_hourly.add_trace(
        go.Scatter(
            x=df_forecast["time"],
            y=df_forecast["precipitation"],
            mode="lines",
            name="Forecast",
            line=dict(dash="dash"),
        )
    )

fig_hourly.update_layout(
    title="Hourly Precipitation – Last 7 Days",
    xaxis_title="Time (America/Sao_Paulo)",
    yaxis_title="mm",
    hovermode="x unified",
)
st.plotly_chart(fig_hourly, use_container_width=True)

# =========================================================
# MONTHLY BAR CHART (12 MONTHS)
# =========================================================
st.subheader("Last 12 Months – Total Monthly Precipitation")

if df_monthly.empty:
    st.info("No monthly precipitation data available for this location.")
else:
    fig_month = go.Figure()
    fig_month.add_bar(x=df_monthly["month"], y=df_monthly["precip"])
    fig_month.update_layout(
        xaxis_title="Month",
        yaxis_title="mm",
        hovermode="x unified",
    )
    st.plotly_chart(fig_month, use_container_width=True)

# =========================================================
# OPTIONAL DEBUG TABLE
# =========================================================
with st.expander("Debug – raw hourly data"):
    st.dataframe(df_hourly)
