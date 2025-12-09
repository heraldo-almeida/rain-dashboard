import streamlit as st
import pandas as pd
import altair as alt
import requests
from datetime import datetime
import pytz

st.set_page_config(page_title="Brazil Rainfall Dashboard", layout="wide")

st.title("Rainfall in Brazilian Capitals (INMET)")

# --- Brazilian timezone ---
tz_br = pytz.timezone("America/Sao_Paulo")
now_br = datetime.now(tz_br)

st.write(f"Current time in Brazil: **{now_br.strftime('%d/%m/%Y %H:%M')}**")


# --- State capitals and IDs ---
capitals = {
    "Rio de Janeiro": "A652",
    "São Paulo": "A701",
    "Belo Horizonte": "A507",
    "Brasília": "A001",
    "Salvador": "A402",
    "Curitiba": "A807",
    "Fortaleza": "A304",
    "Manaus": "A101",
    "Porto Alegre": "A803",
    "Recife": "A301",
}

city = st.selectbox("Select a capital city:", list(capitals.keys()))
station_id = capitals[city]

url = f"https://apitempo.inmet.gov.br/estacao/{now_br.year}-{now_br.month:02d}-{now_br.day:02d}"

# --- Fetch data ---
try:
    response = requests.get(url, timeout=10)
    data = response.json()
except Exception:
    st.error("Could not fetch data.")
    st.stop()

# --- Filter only the selected station ---
df = pd.DataFrame([x for x in data if x["CD_ESTACAO"] == station_id])

if df.empty:
    st.warning("No data available for this station today.")
    st.stop()

# --- Clean datetime ---
df["datetime"] = pd.to_datetime(df["DT_MEDICAO"] + " " + df["HR_MEDICAO"])
df["datetime"] = df["datetime"].dt.tz_localize("UTC").dt.tz_convert(tz_br)

# --- Rainfall column ---
df["rain_mm"] = pd.to_numeric(df["CHUVA"], errors="coerce").fillna(0)

# Sort chronologically
df = df.sort_values("datetime")

# --- 24h TIME column for table ---
df["Time (Brazil)"] = df["datetime"].dt.strftime("%d/%m %H:%M")

# --- Chart ---
chart = (
    alt.Chart(df)
    .mark_line(point=True)
    .encode(
        x=alt.X("datetime:T",
                title="Time (Brazil)",
                axis=alt.Axis(format="%H:%M")),  # 24h format
        y=alt.Y("rain_mm:Q", title="Rainfall (mm)"),
        tooltip=[
            alt.Tooltip("datetime:T", title="Time (Brazil)", format="%H:%M"),
            alt.Tooltip("rain_mm:Q", title="Rain (mm)")
        ]
    )
    .properties(height=350)
)

st.altair_chart(chart, use_container_width=True)

# Table view
st.dataframe(df[["Time (Brazil)", "rain_mm"]].rename(columns={"rain_mm": "Rainfall (mm)"}))
