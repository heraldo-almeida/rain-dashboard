from flask import Flask, render_template, Response
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime, timedelta
import random

app = Flask(__name__)

# ---------------------------------------
# Mock weather data generator
# Replace this with your real sensor/API
# ---------------------------------------
def generate_weather_data(days=365):
    data = []
    today = datetime.now()
    for i in range(days):
        date = today - timedelta(days=i)
        precipitation = max(0, random.gauss(3, 2))  # mm/day
        data.append({
            "date": date,
            "precipitation": precipitation
        })
    return list(reversed(data))

weather_data = generate_weather_data()

# ---------------------------------------
# Rain Emoji Indicator
# ---------------------------------------
def rain_emoji(current_precip):
    if current_precip == 0:
        return "☀️ Not raining"
    elif current_precip <= 2.5:
        return "🌦️ Mild rain"
    else:
        return "🌧️ Strong rain"

# ---------------------------------------
# Generate line plot (last 7 days)
# ---------------------------------------
def create_last7_plot():
    last7 = weather_data[-7:]

    dates = [d["date"].strftime("%b %d") for d in last7]
    values = [d["precipitation"] for d in last7]

    plt.figure(figsize=(5, 3))
    plt.plot(dates, values, linewidth=2)
    plt.title("Rainfall — Last 7 Days")
    plt.xlabel("Date")
    plt.ylabel("Precipitation (mm)")
    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    return base64.b64encode(img.getvalue()).decode()

# ---------------------------------------
# Generate bar plot (last 12 months)
# ---------------------------------------
def create_last12months_plot():
    last12 = weather_data[-365:]

    # aggregate monthly totals
    monthly = {}
    for entry in last12:
        key = entry["date"].strftime("%Y-%m")
        monthly[key] = monthly.get(key, 0) + entry["precipitation"]

    months = list(monthly.keys())
    totals = list(monthly.values())

    plt.figure(figsize=(6, 3))
    plt.bar(months, totals)
    plt.xticks(rotation=45, ha='right')
    plt.title("Precipitation — Last 12 Months")
    plt.xlabel("Month")
    plt.ylabel("Total Precipitation (mm)")
    plt.tight_layout()

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    return base64.b64encode(img.getvalue()).decode()

# ---------------------------------------
# Routes
# ---------------------------------------
@app.route("/")
def index():
    last7_img = create_last7_plot()
    last12_img = create_last12months_plot()

    current_precip = weather_data[-1]["precipitation"]
    emoji = rain_emoji(current_precip)

    return render_template(
        "index.html",
        last7_plot=last7_img,
        last12_plot=last12_img,
        emoji_status=emoji,
        current_precip=round(current_precip, 2)
    )

# ---------------------------------------
# Run
# ---------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
