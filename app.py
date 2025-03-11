from flask import Flask, jsonify, render_template, request
import requests
from datetime import datetime
import pytz
import os

app = Flask(__name__)

# ✅ API Key (Use Render Environment Variables)
API_KEY = os.getenv("API_KEY")  
API_URL = f"https://api.the-odds-api.com/v4/sports/upcoming/odds?apiKey={API_KEY}&regions=us&oddsFormat=american"

# ✅ Convert UTC Time to Central Time (CT)
def convert_to_central_time(utc_time):
    utc_zone = pytz.utc
    central_zone = pytz.timezone("America/Chicago")
    utc_dt = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
    ct_dt = utc_dt.replace(tzinfo=utc_zone).astimezone(central_zone)
    return ct_dt.strftime("%Y-%m-%d %I:%M %p CT")

# ✅ Function to Fetch Odds from API
def get_odds():
    try:
        response = requests.get(API_URL)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"❌ Error Fetching Odds: {response.status_code} - {response.text}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"❌ API Request Failed: {e}")
        return []

# ✅ Function to Find Arbitrage Opportunities
def find_arbitrage_opportunities(sort_by="arb_percent"):
    odds_data = get_odds()
    opportunities = []

    for event in odds_data:
        match = f"{event['home_team']} vs {event['away_team']}"
        sport = event['sport_title']
        event_time = convert_to_central_time(event["commence_time"])

        best_home = {"site": None, "odds": None}
        best_away = {"site": None, "odds": None}

        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] in ["h2h", "spreads", "totals"]:
                    for outcome in market.get("outcomes", []):
                        if outcome["name"] == event["home_team"]:
                            if best_home["odds"] is None or outcome["price"] > best_home["odds"]:
                                best_home = {"site": bookmaker["title"], "odds": outcome["price"]}
                        elif outcome["name"] == event["away_team"]:
                            if best_away["odds"] is None or outcome["price"] < best_away["odds"]:
                                best_away = {"site": bookmaker["title"], "odds": outcome["price"]}

        if best_home["site"] and best_away["site"] and best_home["odds"] and best_away["odds"]:
            try:
                arb_percent = (1 / (best_home["odds"] / 100 + 1)) + (1 / (1 - best_away["odds"] / 100))
                arb_percent = (1 - arb_percent) * 100

                if arb_percent > 0:
                    opportunities.append({
                        "match": match,
                        "sport": sport,
                        "date": event_time,
                        "home_site": best_home["site"],
                        "home_odds": best_home["odds"],
                        "away_site": best_away["site"],
                        "away_odds": best_away["odds"],
                        "arb_percent": round(arb_percent, 2)
                    })
            except ZeroDivisionError:
                print(f"⚠️ Skipping calculation due to division by zero for match: {match}")

    if sort_by == "time":
        opportunities.sort(key=lambda x: datetime.strptime(x["date"], "%Y-%m-%d %I:%M %p CT"))
    elif sort_by == "arb_percent":
        opportunities.sort(key=lambda x: x["arb_percent"], reverse=True)
    elif sort_by == "profit":
        opportunities.sort(key=lambda x: (x["home_odds"] + x["away_odds"]), reverse=True)

    return opportunities

# ✅ API Route to Fetch Sorted Arbitrage Opportunities
@app.route("/arbitrage")
def arbitrage():
    sort_by = request.args.get("sort", "arb_percent")
    return jsonify(find_arbitrage_opportunities(sort_by))

# ✅ Web App Route (Displays Data)
@app.route("/")
def index():
    sort_by = request.args.get("sort", "arb_percent")
    data = find_arbitrage_opportunities(sort_by)
    return render_template("index.html", opportunities=data, sort_by=sort_by)

# ✅ Flask App Runner for Render Deployment
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
