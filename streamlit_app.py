import streamlit as st
import pandas as pd
import altair as alt
import requests
from datetime import datetime
import pytz

# -----------------------------------------------------------
# Streamlit configuration
# -----------------------------------------------------------
st.set_page_config(page_title="Brazil Rainfall Dashboard", layout="wide")
st.title("Rainfall in Brazilian Capitals (INMET)")

# Brazilian timezone
tz_br = pytz.timezone("America/Sao_Paulo")
now_br = datetime.now(tz_br)

st.write(f"Current time in Brazil: **{now_br.strftime('%d/%m/%Y %H:%M')}**")

# -----------------------------------------------------------
# Capital cities mapped to INMET station codes
# -----------------------------------------------------------
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

# -----------------------------------------------------------
# Fetch data from INMET for today's date
# -----------------------------------------------------------
url = f"https://apitempo.inmet.gov.br/estacao/{now_br.year}-{now_br.month:02d}-{now_br.day:02d}"

try:
    response = requests.get(url, timeout=10)
    data = response.json()
except Exception:
    st.error("Could not fetch data.")
    st.stop()

# -----------------------------------------------------------
# Filter the chosen station
# -----------------------------------------------------------
df = pd.DataFrame([x for x in data if x["CD_ESTACAO"] == station_id])

if df.empty:
    st.warning("No INMET data found for today for this station.")
    st.stop()

# -----------------------------------------------------------
# Debug table — raw timestamp values exactly as returned by INMET
# -----------------------------------------------------------
st.subheader("Raw INMET timestamps (debug)")
st.dataframe(df[["DT_MEDICAO", "HR_MEDICAO"]])

# -----------------------------------------------------------
# Datetime cleaning and timezone conversion
# -----------------------------------------------------------
df["datetime"] = pd.to_datetime(df["DT_MEDICAO"] + " " + df["HR_MEDICAO"], errors="coerce")

# INMET timestamps are UTC — convert to Brazil time
df["datetime"] = df["datetime"].dt.tz_localize("UTC").dt.tz_convert(tz_br)

# Convert rainfall to numeric
df["rain_mm"] = pd.to_numeric(df["CHUVA"], errors="coerce").fillna(0)

# Sort chronologically
df = df.sort_values("datetime")

# Table-friendly datetime
df["Time (Brazil)"] = df["datetime"].dt.strftime("%d/%m %H:%M")

# -----------------------------------------------------------
# Line chart
# -----------------------------------------------------------
chart = (
    alt.Chart(df)
    .mark_line(point=True)
    .encode(
        x=alt.X(
            "datetime:T",
            title="Time (Brazil)",
            axis=alt.Axis(format="%H:%M")  # 24h format
        ),
        y=alt.Y("rain_mm:Q", title="Rainfall (mm)"),
        tooltip=[
            alt.Tooltip("datetime:T", title="Time (Brazil)", format="%H:%M"),
            alt.Tooltip("rain_mm:Q", title="Rain (mm)")
        ]
    )
    .properties(height=350)
)

st.altair_chart(chart, use_container_width=True)

# -----------------------------------------------------------
# Final table
# -----------------------------------------------------------
st.subheader("Rainfall Table")
st.dataframe(
    df[["Time (Brazil)", "rain_mm"]].rename(columns={"rain_mm": "Rainfall (mm)"})
)
