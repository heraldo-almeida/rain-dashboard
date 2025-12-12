import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import pytz
import plotly.graph_objects as go

# -------------------------
# Config
# -------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")
st.set_page_config(page_title="Brazil Rain Dashboard", layout="wide")

# -------------------------
# Cities
# -------------------------
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

# -------------------------
# Helpers
# -------------------------
def safe_request_json(url: str, timeout: int = 25):
    try:
        r = requests.get(url, timeout=timeout)
    except Exception as e:
        return {"__error__": f"Request failed: {e}"}
    try:
        return r.json()
    except Exception as e:
        return {"__error__": f"Invalid JSON response: {e}", "text": r.text if hasattr(r, "text") else None}


def ensure_brt_timezone(series: pd.Series) -> pd.Series:
    s = pd.to_datetime(series, errors="coerce")
    # if series parsing failed, return it as-is
    if s.isna().all():
        return s
    # If dtype is timezone-aware, convert; otherwise localize to America/Sao_Paulo
    try:
        if s.dt.tz is None:
            s = s.dt.tz_localize("America/Sao_Paulo")
        else:
            s = s.dt.tz_convert("America/Sao_Paulo")
    except Exception:
        # fallback: coerce to naive then localize
        s = pd.to_datetime(series, errors="coerce").dt.tz_localize("America/Sao_Paulo")
    return s


def fetch_precip(lat: float, lon: float) -> pd.DataFrame:
    now = datetime.now(BR_TZ)
    start = now - timedelta(days=7)

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation"
        f"&start_date={start.strftime('%Y-%m-%d')}&end_date={(now + timedelta(days=2)).strftime('%Y-%m-%d')}"
        "&timezone=America%2FSao_Paulo"
    )

    data = safe_request_json(url)
    if "__error__" in data:
        st.error(f"Error fetching hourly data: {data['__error__']}")
        return pd.DataFrame(columns=["time", "precip"])

    if "hourly" not in data or "time" not in data["hourly"] or "precipitation" not in data["hourly"]:
        st.error("Open-Meteo response missing 'hourly' payload. Full response shown in debug.")
        st.json(data)
        return pd.DataFrame(columns=["time", "precip"])

    hours = data["hourly"]["time"]
    precip = data["hourly"]["precipitation"]

    df = pd.DataFrame({"time": hours, "precip": precip})
    df["time"] = ensure_brt_timezone(df["time"])
    df = df.sort_values("time").reset_index(drop=True)
    return df


def fetch_monthly_precip(lat: float, lon: float) -> pd.DataFrame:
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
    if "__error__" in data:
        st.error(f"Error fetching monthly data: {data['__error__']}")
        return pd.DataFrame(columns=["month", "precip"])

    if "daily" not in data or "time" not in data.get("daily", {}) or "precipitation_sum" not in data.get("daily", {}):
        st.warning("Archive API returned no daily data for monthly aggregation. Showing empty monthly table.")
        return pd.DataFrame(columns=["month", "precip"])

    dates = data["daily"]["time"]
    precip = data["daily"]["precipitation_sum"]
    df = pd.DataFrame({"date": pd.to_datetime(dates), "precip": precip})
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    monthly = df.groupby("month", as_index=False)["precip"].sum().sort_values("month").tail(12)
    return monthly


# -------------------------
# App UI
# -------------------------
st.title("🌧️ Brazil Precipitation Dashboard (7-day Rolling + Forecast)")

city = st.selectbox("Select a city:", list(CITIES.keys()))
lat, lon = CITIES[city]

with st.spinner("Fetching hourly data..."):
    df = fetch_precip(lat, lon)

with st.spinner("Fetching monthly data (last 12 months)..."):
    df_monthly = fetch_monthly_precip(lat, lon)

# If df is empty, show friendly message and skip plotting
if df.empty:
    st.warning("No hourly data available to plot. See debug output for details.")
    with st.expander("🔍 Debug: raw response / monthly data"):
        st.write("Hourly dataframe is empty. Monthly data (if any):")
        st.dataframe(df_monthly)
    st.stop()

# Ensure times are timezone-aware in BRT for comparison
now = datetime.now(BR_TZ)

# split historical vs forecast safely
try:
    df["is_forecast"] = df["time"] > now
except Exception:
    # If comparison fails for any reason, fall back to no-split (plot everything)
    st.warning("Could not split history vs forecast due to timestamp types. Plotting full series.")
    df["is_forecast"] = False

df_hist = df[df["is_forecast"] == False]
df_fore = df[df["is_forecast"] == True]

# Plot hourly
fig = go.Figure()
if not df_hist.empty:
    fig.add_trace(
        go.Scatter(
            x=df_hist["time"],
            y=df_hist["precip"],
            mode="lines",
            name="Historical Precipitation",
            line=dict(width=3),
        )
    )
if not df_fore.empty:
    fig.add_trace(
        go.Scatter(
            x=df_fore["time"],
            y=df_fore["precip"],
            mode="lines",
            name="Forecast Precipitation",
            line=dict(width=3, dash="dash"),
        )
    )
if df_hist.empty and df_fore.empty:
    st.info("No plot data available after processing.")
else:
    fig.update_layout(
        title=f"Hourly Precipitation — {city}",
        xaxis_title="Date / Time (UTC-3)",
        yaxis_title="Precipitation (mm)",
        hovermode="x unified",
        template="plotly_white",
    )
    st.plotly_chart(fig, use_container_width=True)

# Monthly bar chart
st.subheader("📊 Total Monthly Precipitation — Last 12 Months")
if df_monthly.empty:
    st.info("No monthly precipitation data available for this location.")
else:
    fig_month = go.Figure()
    fig_month.add_trace(go.Bar(x=df_monthly["month"], y=df_monthly["precip"], name="Monthly total"))
    fig_month.update_layout(xaxis_title="Month", yaxis_title="Precipitation (mm)", hovermode="x unified", template="plotly_white")
    st.plotly_chart(fig_month, use_container_width=True)

# Debug
with st.expander("🛠 Debug: Raw hourly data / API info"):
    st.write("Hourly DataFrame:")
    st.dataframe(df)
    st.write("Monthly aggregated (last 12 months):")
    st.dataframe(df_monthly)
