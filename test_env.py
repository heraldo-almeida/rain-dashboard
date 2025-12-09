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
# FETCH HOURLY DATA FROM OPEN-METEO (7 days + forecast)
# ------------------------------------------------------------------
def fetch_precip(lat, lon):
    now = datetime.now(BR_TZ)
    start = now - timedelta(days=7)

    start_str = start.strftime("%Y-%m-%dT%H:00")
    end_str = (now + timedelta(days=2)).strftime("%Y-%m-%dT%H:00")  # Forecast

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

# ------------------------------------------------------------------
# FETCH MONTHLY DATA (LAST 12 MONTHS) FROM ARCHIVE API (ERA5)
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

    r = requests.get(url)
    data = r.json()

    if "daily" not in data:
        return pd.DataFrame(columns=["month", "precip"])

    dates = data["daily"].get("time", [])
    precip = data["daily"].get("precipitation_sum", [])

    if not dates:
        return pd.DataFrame(columns=["month", "precip"])

    df = pd.DataFrame({"date": dates, "precip": precip})
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()

    monthly = (
        df.groupby("month", as_index=False)["precip"]
        .sum()
        .sort_values("month")
        .tail(12)
    )
    monthly.rename(columns={"month": "month", "precip": "precip"}, inplace=True)
    return monthly

# ------------------------------------------------------------------
# APP UI
# ------------------------------------------------------------------
st.set_page_config(page_title="Brazil Rain Dashboard", layout="wide")
st.title("🌧️ Brazil Precipitation Dashboard (7-day Rolling + Forecast)")

city = st.selectbox("Select a city:", list(CITIES.keys()))
lat, lon = CITIES[city]

with st.spinner("Fetching hourly data..."):
    df = fetch_precip(lat, lon)

with st.spinner("Fetching monthly data (last 12 months)..."):
    df_monthly = fetch_monthly_precip(lat, lon)

# ------------------------------------------------------------------
# SPLIT HISTORICAL vs FORECAST
# ------------------------------------------------------------------
now = datetime.now(BR_TZ)
df["is_forecast"] = df["time"] > now

df_hist = df[df["is_forecast"] == False]
df_fore = df[df["is_forecast"] == True]

# ------------------------------------------------------------------
# HOURLY PLOT
# ------------------------------------------------------------------
fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df_hist["time"],
        y=df_hist["precip"],
        mode="lines",
        name="Historical Precipitation",
        line=dict(width=3),
    )
)

fig.add_trace(
    go.Scatter(
        x=df_fore["time"],
        y=df_fore["precip"],
        mode="lines",
        name="Forecast Precipitation",
        line=dict(width=3, dash="dash"),
    )
)

fig.update_layout(
    title=f"Hourly Precipitation — {city}",
    xaxis_title="Date / Time (UTC-3)",
    yaxis_title="Precipitation (mm)",
    hovermode="x unified",
    template="plotly_white",
)

st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------
# MONTHLY BAR PLOT (LAST 12 MONTHS)
# ------------------------------------------------------------------
st.subheader("📊 Total Monthly Precipitation — Last 12 Months")

if df_monthly.empty:
    st.info("No monthly precipitation data available for this location.")
else:
    fig_month = go.Figure()
    fig_month.add_trace(
        go.Bar(
            x=df_monthly["month"],
            y=df_monthly["precip"],
            name="Monthly total",
        )
    )
    fig_month.update_layout(
        xaxis_title="Month",
        yaxis_title="Precipitation (mm)",
        hovermode="x unified",
        template="plotly_white",
    )
    st.plotly_chart(fig_month, use_container_width=True)

# ------------------------------------------------------------------
# DEBUG TABLE
# ------------------------------------------------------------------
with st.expander("🛠 Debug: Raw hourly data returned by Open-Meteo"):
    st.dataframe(df, use_container_width=True)
