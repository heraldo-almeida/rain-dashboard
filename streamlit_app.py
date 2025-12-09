import streamlit as st
import pandas as pd
import requests
import pytz
from datetime import datetime, timedelta
import plotly.graph_objects as go
import plotly.express as px

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
# BRAZIL STATE CAPITALS (FOR HEATMAP)
# =========================================================
BRAZIL_STATES_CAPITALS = {
    "Acre": (-9.97499, -67.8243),              # Rio Branco
    "Alagoas": (-9.66599, -35.7350),           # Maceió
    "Amapá": (0.03493, -51.0694),              # Macapá
    "Amazonas": (-3.11866, -60.0212),          # Manaus
    "Bahia": (-12.9777, -38.5016),             # Salvador
    "Ceará": (-3.71664, -38.5423),             # Fortaleza
    "Distrito Federal": (-15.7939, -47.8828),  # Brasília
    "Espírito Santo": (-20.3155, -40.3128),    # Vitória
    "Goiás": (-16.6869, -49.2648),             # Goiânia
    "Maranhão": (-2.53874, -44.2825),          # São Luís
    "Mato Grosso": (-15.6010, -56.0974),       # Cuiabá
    "Mato Grosso do Sul": (-20.4697, -54.6201),# Campo Grande
    "Minas Gerais": (-19.9167, -43.9345),      # Belo Horizonte
    "Pará": (-1.4558, -48.5039),               # Belém
    "Paraíba": (-7.11509, -34.8641),           # João Pessoa
    "Paraná": (-25.4284, -49.2733),            # Curitiba
    "Pernambuco": (-8.0476, -34.8770),         # Recife
    "Piauí": (-5.09194, -42.8034),             # Teresina
    "Rio de Janeiro": (-22.9068, -43.1729),    # Rio de Janeiro
    "Rio Grande do Norte": (-5.7950, -35.2094),# Natal
    "Rio Grande do Sul": (-30.0346, -51.2177), # Porto Alegre
    "Rondônia": (-8.76077, -63.8999),          # Porto Velho
    "Roraima": (2.82384, -60.6753),            # Boa Vista
    "Santa Catarina": (-27.5945, -48.5477),    # Florianópolis
    "São Paulo": (-23.5505, -46.6333),         # São Paulo
    "Sergipe": (-10.9472, -37.0731),           # Aracaju
    "Tocantins": (-10.2491, -48.3243),         # Palmas
}

BRAZIL_GEOJSON_URL = (
    "https://raw.githubusercontent.com/codeforamerica/"
    "click_that_hood/master/public/data/brazil-states.geojson"
)

# =========================================================
# HELPERS
# =========================================================
def rain_emoji(value: float) -> str:
    """Three-stage emoji based on latest precipitation in mm/hour."""
    if value <= 0:
        return "☀️ Not raining"
    elif value <= 2:
        return "🌧️ Mild rain"
    else:
        return "⛈️ Strong rain"


@st.cache_data(show_spinner=False)
def get_hourly_precip(lat: float, lon: float) -> pd.DataFrame:
    """7 past days + 2 future days hourly precipitation."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&hourly=precipitation&past_days=7&forecast_days=2"
        "&timezone=America%2FSao_Paulo"
    )
    data = requests.get(url).json()
    df = pd.DataFrame(data["hourly"])
    df["time"] = pd.to_datetime(df["time"])
    return df


@st.cache_data(show_spinner=False)
def get_monthly_precip(lat: float, lon: float) -> pd.DataFrame:
    """
    Last 12 months total precipitation using the climate API.
    Uses a 2-year window then keeps the last 12 monthly values.
    """
    now = datetime.utcnow()
    end_date = now.date()
    start_date = (now - timedelta(days=730)).date()

    url = (
        "https://climate-api.open-meteo.com/v1/climate?"
        f"latitude={lat}&longitude={lon}"
        f"&start_date={start_date}&end_date={end_date}"
        "&monthly=precipitation_sum"
    )
    data = requests.get(url).json()
    if "monthly" not in data:
        return pd.DataFrame(columns=["month", "precip"])

    months = data["monthly"].get("time", [])
    precip = data["monthly"].get("precipitation_sum", [])
    if not months:
        return pd.DataFrame(columns=["month", "precip"])

    df = pd.DataFrame({"month": pd.to_datetime(months), "precip": precip})
    df = df.sort_values("month").tail(12)
    return df


@st.cache_data(show_spinner=False)
def load_brazil_geojson():
    """Load Brazil states GeoJSON used for choropleth."""
    resp = requests.get(BRAZIL_GEOJSON_URL)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(show_spinner=False)
def get_state_precip(days: int) -> pd.DataFrame:
    """
    Total precipitation over the last `days` days for each Brazilian state,
    using daily precipitation_sum.
    """
    records = []
    for state, (lat, lon) in BRAZIL_STATES_CAPITALS.items():
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&daily=precipitation_sum&past_days={days}&forecast_days=0"
            "&timezone=America%2FSao_Paulo"
        )
        data = requests.get(url).json()
        vals = data.get("daily", {}).get("precipitation_sum", [])
        total = float(sum(vals)) if vals else 0.0
        records.append({"state": state, "precip": total})
    return pd.DataFrame(records)


def build_brazil_heatmap(days: int):
    df_states = get_state_precip(days)
    geojson = load_brazil_geojson()
    max_precip = max(df_states["precip"].max(), 1.0)

    fig = px.choropleth(
        df_states,
        geojson=geojson,
        locations="state",
        featureidkey="properties.name",
        color="precip",
        color_continuous_scale=[
            [0.0, "rgba(0,0,0,0)"],
            [0.3, "green"],
            [0.6, "blue"],
            [1.0, "darkblue"],
        ],
        range_color=(0, max_precip),
    )
    fig.update_geos(fitbounds="locations", visible=False)
    fig.update_layout(
        margin=dict(l=0, r=0, t=40, b=0),
        coloraxis_colorbar_title="mm",
        title=f"Brazil – Total Precipitation in Last {days} Days",
    )
    return fig


# =========================================================
# UI – CITY SELECTION
# =========================================================
city = st.selectbox("Select city", CITY_NAMES)
lat, lon = CITIES[city]

with st.spinner("Loading hourly data..."):
    df_hourly = get_hourly_precip(lat, lon)

with st.spinner("Loading monthly data..."):
    df_monthly = get_monthly_precip(lat, lon)

now_br = datetime.now(BR_TZ)
hist_mask = df_hourly["time"] <= now_br
df_hist = df_hourly[hist_mask]
df_forecast = df_hourly[~hist_mask]

if not df_hist.empty:
    latest_precip = float(df_hist.iloc[-1]["precipitation"])
else:
    latest_precip = float(df_hourly.iloc[-1]["precipitation"])

status = rain_emoji(latest_precip)

st.subheader(f"{city} — Current rain status: {status}")
st.caption(f"Last observed hourly precipitation: {latest_precip:.2f} mm (local time)")

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
    title="Hourly Precipitation – Last 7 Days (History + Forecast)",
    xaxis_title="Time (America/Sao_Paulo)",
    yaxis_title="mm",
    hovermode="x unified",
)
st.plotly_chart(fig_hourly, use_container_width=True)

# =========================================================
# 12-MONTH BAR CHART
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
# BRAZIL HEATMAP (LAST N DAYS, DEFAULT 7)
# =========================================================
st.subheader("Brazil Precipitation Heatmap")

days_heatmap = st.slider("Number of days for heatmap", min_value=3, max_value=14, value=7)

with st.spinner("Building Brazil precipitation heatmap..."):
    fig_heat = build_brazil_heatmap(days_heatmap)

st.plotly_chart(fig_heat, use_container_width=True)

# =========================================================
# OPTIONAL DEBUG TABLE
# =========================================================
with st.expander("Debug – raw hourly data"):
    st.dataframe(df_hourly)
