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
# Cities: Capitals + Your 4 cities
# -----------------------------
cities = {
    # --- Your cities ---
    "Poços de Caldas - MG": {"city": "Poços de Caldas", "state": "MG", "lat": -21.7878, "lon": -46.5608},
    "Vassouras - RJ": {"city": "Vassouras", "state": "RJ", "lat": -22.4039, "lon": -43.6628},
    "Botucatu - SP": {"city": "Botucatu", "state": "SP", "lat": -22.8858, "lon": -48.4450},
    "Campinas - SP": {"city": "Campinas", "state": "SP", "lat": -22.9056, "lon": -47.0608},

    # --- Brazil state capitals ---
    "Rio Branco - AC": {"city": "Rio Branco", "state": "AC"},
    "Maceió - AL": {"city": "Maceió", "state": "AL"},
    "Macapá - AP": {"city": "Macapá", "state": "AP"},
    "Manaus - AM": {"city": "Manaus", "state": "AM"},
    "Salvador - BA": {"city": "Salvador", "state": "BA"},
    "Fortaleza - CE": {"city": "Fortaleza", "state": "CE"},
    "Brasília - DF": {"city": "Brasília", "state": "DF"},
    "Vitória - ES": {"city": "Vitória", "state": "ES"},
    "Goiânia - GO": {"city": "Goiânia", "state": "GO"},
    "São Luís - MA": {"city": "São Luís", "state": "MA"},
    "Cuiabá - MT": {"city": "Cuiabá", "state": "MT"},
    "Campo Grande - MS": {"city": "Campo Grande", "state": "MS"},
    "Belo Horizonte - MG": {"city": "Belo Horizonte", "state": "MG"},
    "Belém - PA": {"city": "Belém", "state": "PA"},
    "João Pessoa - PB": {"city": "João Pessoa", "state": "PB"},
    "Curitiba - PR": {"city": "Curitiba", "state": "PR"},
    "Recife - PE": {"city": "Recife", "state": "PE"},
    "Teresina - PI": {"city": "Teresina", "state": "PI"},
    "Rio de Janeiro - RJ": {"city": "Rio de Janeiro", "state": "RJ"},
    "Natal - RN": {"city": "Natal", "state": "RN"},
    "Porto Alegre - RS": {"city": "Porto Alegre", "state": "RS"},
    "Porto Velho - RO": {"city": "Porto Velho", "state": "RO"},
    "Boa Vista - RR": {"city": "Boa Vista", "state": "RR"},
    "Florianópolis - SC": {"city": "Florianópolis", "state": "SC"},
    "São Paulo - SP": {"city": "São Paulo", "state": "SP"},
    "Aracaju - SE": {"city": "Aracaju", "state": "SE"},
    "Palmas - TO": {"city": "Palmas", "state": "TO"},
}

# -----------------------------
# Select City
# -----------------------------
st.title("🌤️ Brazil Weather Dashboard")
selected_city = st.selectbox("Select a city:", list(cities.keys()))

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

# Correct local time in GMT-3
now_br = datetime.now(BR_TZ).strftime("%d/%m/%Y %H:%M")

# -----------------------------
# Extract Hourly Forecast
# -----------------------------
today = weather_json["weather"][0]["hourly"]
times = []
temps = []

for entry in today:
    hour = str(entry["time"]).zfill(4)
    hour_fmt = f"{hour[:2]}:{hour[2:]}"
    temp_c = float(entry["tempC"])
    times.append(hour_fmt)
    temps.append(temp_c)

df = pd.DataFrame({"Time": times, "Temperature (°C)": temps})

# -----------------------------
# Display Current Conditions
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
# Plot
# -----------------------------
st.subheader("📈 Temperature Today")
st.line_chart(df.set_index("Time"))
