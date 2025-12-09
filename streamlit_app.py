import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import pytz

st.set_page_config(page_title="Brazil Weather Dashboard", layout="wide")

# -----------------------------
# Timezone (Brazil GMT-3)
# -----------------------------
BR_TZ = pytz.timezone("America/Sao_Paulo")

# -----------------------------
# Allowed Cities Only (with coordinates when provided)
# -----------------------------
cities = {
    "Botucatu - SP": {"city": "Botucatu", "state": "SP", "lat": -22.8858, "lon": -48.4450},
    "Campinas - SP": {"city": "Campinas", "state": "SP", "lat": -22.9056, "lon": -47.0608},
    "Curitiba - PR": {"city": "Curitiba", "state": "PR"},
    "Goiânia - GO": {"city": "Goiânia", "state": "GO"},
    "Macapá - AP": {"city": "Macapá", "state": "AP"},
    "Poços de Caldas - MG": {"city": "Poços de Caldas", "state": "MG", "lat": -21.7878, "lon": -46.5608},
    "Porto Alegre - RS": {"city": "Porto Alegre", "state": "RS"},
    "Recife - PE": {"city": "Recife", "state": "PE"},
    "Rio de Janeiro - RJ": {"city": "Rio de Janeiro", "state": "RJ"},
    "Salvador - BA": {"city": "Salvador", "state": "BA"},
    "São Paulo - SP": {"city": "São Paulo", "state": "SP"},
    "Vassouras - RJ": {"city": "Vassouras", "state": "RJ", "lat": -22.4039, "lon": -43.6628},
}

# -----------------------------
# Sort cities alphabetically for the dropdown
# -----------------------------
sorted_city_names = sorted(cities.keys(), key=lambda x: x.lower())

# -----------------------------
# Select City
# -----------------------------
st.title("🌤️ Brazil Weather Dashboard")
selected_city = st.selectbox("Select a city:", sorted_city_names)

city_data = cities[selected_city]
city_name = city_data["city"]

# -----------------------------
# Fetch Weather Data
# -----------------------------
API_URL = f"https://wttr.in/{city_name}?format=j1"

try:
    response = requests.get(API_URL)
    response.raise_for_status()
    weather_json = response.json()
except Exception as e:
    st.error(f"Could not fetch data: {e}")
    st.stop()

# -----------------------------
# Extract Current Conditions
# -----------------------------
current = weather_json["current_condition"][0]

temp = float(current["temp_C"])
feels_like = float(current["FeelsLikeC"])
humidity = float(current["humidity"])
wind = float(current["windspeedKmph"])
desc = current["weatherDesc"][0]["value"]

# Local time formatted 24h GMT-3
now_br = datetime.now(BR_TZ).strftime("%d/%m/%Y %H:%M")

# -----------------------------
# Extract Hourly Precipitation
# -----------------------------
today = weather_json["weather"][0]["hourly"]
times = []
precip = []

for entry in today:
    hour = str(entry["time"]).zfill(4)  # e.g., "300" -> "0300"
    hour_fmt = f"{hour[:2]}:{hour[2:]}"
    precip_mm = float(entry["precipMM"])  # rainfall
    times.append(hour_fmt)
    precip.append(precip_mm)

df = pd.DataFrame({"Time": times, "Precipitation (mm)": precip})

# -----------------------------
# Display Current Conditions (Card)
# -----------------------------
st.subheader(f"Weather in **{selected_city}**")

col1, col2, col3, col4 = st.columns(4)

col1.metric("🌡️ Temperature", f"{temp} °C")
col2.metric("🤔 Feels Like", f"{feels_like} °C")
col3.metric("💧 Humidity", f"{humidity}%")
col4.metric("💨 Wind", f"{wind} km/h")

st.write(f"**Condition:** {desc}")
st.write(f"⏰ **Local Time (GMT-3):** {now_br}")

# -----------------------------
# Plot Precipitation
# -----------------------------
st.subheader("🌧️ Precipitation Today (mm)")
st.line_chart(df.set_index("Time"))
