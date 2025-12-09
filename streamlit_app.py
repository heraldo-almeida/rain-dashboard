import streamlit as st
import pandas as pd
import requests
import pytz
from datetime import datetime, timedelta
import plotly.graph_objects as go
from matplotlib.colors import LinearSegmentedColormap
import geopandas as gpd
import matplotlib.pyplot as plt
import io
import base64
import os
import zipfile


# ---------------------------------------------------------
# CITIES (alphabetical)
# ---------------------------------------------------------
CITIES = {
    "Botucatu": (-22.8858, -48.4450),
    "Campinas": (-22.9058, -47.0608),
    "Curitiba": (-25.4284, -49.2733),
    "Goiânia": (-16.6869, -49.2648),
    "Macapá": (0.0349, -51.0694),
    "Poços de Caldas": (-21.7878, -46.5608),
    "Porto Alegre": (-30.0277, -51.2287),
    "Recife": (-8.0476, -34.8770),
    "Rio de Janeiro": (-22.9068, -43.1729),
    "Salvador": (-12.9777, -38.5016),
    "São Paulo": (-23.5505, -46.6333),
    "Vassouras": (-22.4039, -43.6628),
}


# ---------------------------------------------------------
# Fetch 7-day history + 24-hour forecast
# ---------------------------------------------------------
def get_precip_data(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation&past_days=7&forecast_days=2"
        "&timezone=America%2FSao_Paulo"
    )
    r = requests.get(url).json()

    df = pd.DataFrame({
        "time": r["hourly"]["time"],
        "precipitation": r["hourly"]["precipitation"]
    })
    df["time"] = pd.to_datetime(df["time"])
    return df


# ---------------------------------------------------------
# Fetch last 12 months monthly precipitation
# ---------------------------------------------------------
def get_monthly_precip(lat, lon):
    today = datetime.now().date()
    one_year_ago = today - timedelta(days=365)

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&monthly=precipitation_sum&start_date={one_year_ago}&end_date={today}"
        "&timezone=America%2FSao_Paulo"
    )
    r = requests.get(url).json()

    df = pd.DataFrame({
        "month": r["monthly"]["time"],
        "precip_sum": r["monthly"]["precipitation_sum"]
    })
    df["month"] = pd.to_datetime(df["month"])
    return df


# ---------------------------------------------------------
# Rain Emoji Detector
# thresholds:
#   0 mm  → ☀️ Not raining
#   0–2mm → 🌧️ Mild rain
#   >2mm  → ⛈️ Strong rain  (your custom threshold)
# ---------------------------------------------------------
def rain_emoji(value):
    if value <= 0:
        return "☀️ Not raining"
    elif value <= 2:
        return "🌧️ Mild rain"
    else:
        return "⛈️ Strong rain"


# ---------------------------------------------------------
# Brazil Heatmap (download + cache shapefile)
# ---------------------------------------------------------
def ensure_brazil_map():
    if not os.path.exists("br_states.shp"):
        st.info("Downloading Brazil map (IBGE)…")

        shp_url = "https://www.dropbox.com/scl/fi/6j4l1l8tfbrz0p2k5hny5/br_shp.zip?rlkey=8jv04qd68yk4ikjc8hjp14q6p&dl=1"
        r = requests.get(shp_url)
        with open("br.zip", "wb") as f:
            f.write(r.content)

        with zipfile.ZipFile("br.zip", "r") as zip_ref:
            zip_ref.extractall(".")

    return gpd.read_file("br_states.shp")


def create_brazil_heatmap(days=7):
    gdf = ensure_brazil_map()

    values = []
    for state, row in gdf.iterrows():
        lat = row.geometry.centroid.y
        lon = row.geometry.centroid.x

        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            "&hourly=precipitation&past_days=7&forecast_days=0"
            "&timezone=America%2FSao_Paulo"
        )
        r = requests.get(url).json()
        vals = pd.Series(r["hourly"]["precipitation"]).tail(24 * days)
        values.append(vals.sum())  # total last X days

    gdf["precip"] = values

    cmap = LinearSegmentedColormap.from_list(
        "custom",
        [
            (0.0, (0, 0, 0, 0)),       # transparent
            (0.3, "green"),
            (0.6, "blue"),
            (1.0, "darkblue")
        ]
    )

    fig, ax = plt.subplots(1, 1, figsize=(6, 8))
    gdf.plot(column="precip", cmap=cmap, legend=True, linewidth=0.3, ax=ax, edgecolor="black")
    ax.set_title(f"Brazil — Precipitation Heatmap (Last {days} Days)")

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=140)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


# ---------------------------------------------------------
# STREAMLIT USER INTERFACE
# ---------------------------------------------------------
st.set_page_config(page_title="Brazil Precipitation Dashboard", layout="wide")

st.title("🌧️ Brazil Precipitation Dashboard")

city = st.selectbox("Select city", sorted(CITIES.keys()))

lat, lon = CITIES[city]

df = get_precip_data(lat, lon)
df_month = get_monthly_precip(lat, lon)

latest_precip = df.iloc[-1]["precipitation"]
emoji = rain_emoji(latest_precip)

st.subheader(f"{city} — Current Condition: {emoji}")


# ---------------------------------------------------------
# Line chart (last 7 days + dashed forecast)
# ---------------------------------------------------------
hist = df[df["time"] < datetime.now()]
forecast = df[df["time"] >= datetime.now()]

fig = go.Figure()
fig.add_trace(go.Scatter(x=hist["time"], y=hist["precipitation"],
                         mode="lines", name="History"))
fig.add_trace(go.Scatter(x=forecast["time"], y=forecast["precipitation"],
                         mode="lines", name="Forecast", line=dict(dash="dash")))
fig.update_layout(title="Hourly Precipitation — Last 7 Days",
                  xaxis_title="Time", yaxis_title="mm")
st.plotly_chart(fig, use_container_width=True)


# ---------------------------------------------------------
# Monthly 12-month bar chart
# ---------------------------------------------------------
fig2 = go.Figure()
fig2.add_bar(x=df_month["month"], y=df_month["precip_sum"])
fig2.update_layout(title="Total Monthly Precipitation (Last 12 Months)",
                   xaxis_title="Month", yaxis_title="mm")
st.plotly_chart(fig2, use_container_width=True)


# ---------------------------------------------------------
# Heatmap (Brazil)
# ---------------------------------------------------------
days = st.slider("Heatmap range (days)", 3, 14, 7)
st.subheader(f"Brazil Precipitation Heatmap — Last {days} Days")

heatmap_img = create_brazil_heatmap(days)
st.image("data:image/png;base64," + heatmap_img)

