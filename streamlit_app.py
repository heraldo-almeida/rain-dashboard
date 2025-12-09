import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta

st.set_page_config(page_title="Brazil Rain Dashboard", layout="wide")

st.title("🌧️ Rainfall Dashboard – Brazil State Capitals")

# --------------------------------------------------------------------
# 1. CAPITALS WITH COORDINATES (Open-Meteo works with lat/lon)
# --------------------------------------------------------------------
capitals = {
    "Aracaju (SE)": (-10.9472, -37.0731),
    "Belém (PA)": (-1.4558, -48.5039),
    "Belo Horizonte (MG)": (-19.9167, -43.9345),
    "Boa Vista (RR)": (2.8235, -60.6758),
    "Brasília (DF)": (-15.7939, -47.8828),
    "Campo Grande (MS)": (-20.4697, -54.6200),
    "Cuiabá (MT)": (-15.6010, -56.0974),
    "Curitiba (PR)": (-25.4284, -49.2733),
    "Florianópolis (SC)": (-27.5945, -48.5477),
    "Fortaleza (CE)": (-3.7319, -38.5267),
    "Goiânia (GO)": (-16.6864, -49.2643),
    "João Pessoa (PB)": (-7.1195, -34.8450),
    "Macapá (AP)": (0.0349, -51.0694),
    "Maceió (AL)": (-9.6499, -35.7089),
    "Manaus (AM)": (-3.1190, -60.0217),
    "Natal (RN)": (-5.7950, -35.2094),
    "Palmas (TO)": (-10.2491, -48.3243),
    "Porto Alegre (RS)": (-30.0346, -51.2177),
    "Porto Velho (RO)": (-8.7612, -63.9004),
    "Recife (PE)": (-8.0476, -34.8770),
    "Rio Branco (AC)": (-9.9740, -67.8243),
    "Rio de Janeiro (RJ)": (-22.9068, -43.1729),
    "Salvador (BA)": (-12.9777, -38.5016),
    "São Luís (MA)": (-2.5390, -44.2825),
    "São Paulo (SP)": (-23.5505, -46.6333),
    "Teresina (PI)": (-5.0892, -42.8016),
    "Vitória (ES)": (-20.3155, -40.3128)
}

city = st.selectbox("Select a capital:", list(capitals.keys()))

lat, lon = capitals[city]

# --------------------------------------------------------------------
# 2. FETCH RAINFALL VIA OPEN-METEO
# --------------------------------------------------------------------
end = datetime.utcnow()
start = end - timedelta(hours=24)

url = (
    "https://api.open-meteo.com/v1/forecast?"
    f"latitude={lat}&longitude={lon}"
    "&hourly=precipitation"
    f"&start_date={start.strftime('%Y-%m-%d')}"
    f"&end_date={end.strftime('%Y-%m-%d')}"
)

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()

    times = data["hourly"]["time"]
    rain = data["hourly"]["precipitation"]

    df = pd.DataFrame({
        "Time (UTC)": pd.to_datetime(times),
        "Rainfall (mm)": rain
    })

    # ----------------------------------------------------------------
    # 3. DISPLAY RESULTS
    # ----------------------------------------------------------------
    st.subheader(f"Rainfall in the last 24 hours – {city}")

    st.metric("Total rainfall (mm)", f"{df['Rainfall (mm)'].sum():.2f}")

    st.line_chart(df.set_index("Time (UTC)"))

    st.dataframe(df)

except Exception as e:
    st.error(f"Could not fetch data: {e}")
