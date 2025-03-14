from flask import Flask, render_template
import requests
from datetime import datetime
import pytz
import os

app = Flask(__name__)

# ✅ API Key (Use Render Environment Variables)
API_KEY = os.getenv("API_KEY")  # Ensure this matches the environment variable name in Render
API_URL = f"https://api.the-odds-api.com/v4/sports/upcoming/odds?apiKey={API_KEY}&regions=us&oddsFormat=american"

# ✅ Mapping of Bookmaker Names to URLs (Updated and Verified)
BOOKMAKER_URLS = {
    "Bovada": "https://www.bovada.lv",
    "BetRivers": "https://www.betrivers.com",
    "Caesars": "https://www.caesars.com/sportsbook",
    "BetMGM": "https://sports.kansas.betmgm.com",  # Updated to Kansas-specific URL
    "LowVig.ag": "https://www.lowvig.ag",
    "MyBookie.ag": "https://www.mybookie.ag",
    "BetUS": "https://www.betus.com.pa",
    "DraftKings": "https://www.draftkings.com",
    "Fanatics": "https://www.fanatics.com",
    "FanDuel": "https://www.fanduel.com"
}

# ✅ Convert UTC Time to Central Time (CT)
def convert_to_central_time(utc_time):
    try:
        utc_zone = pytz.utc
        central_zone = pytz.timezone("America/Chicago")
        utc_dt = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
        ct_dt = utc_dt.replace(tzinfo=utc_zone).astimezone(central_zone)
        return ct_dt.strftime("%Y-%m-%d %I:%M %p CT")
    except Exception as e:
        print(f"❌ Error Converting Time: {e}")
        return utc_time  # Return original time if conversion fails

# ✅ Function to Fetch Odds from API
def get_odds():
    try:
        response = requests.get(API_URL, timeout=10)  # Add timeout to prevent hanging
        response.raise_for_status()  # Raise an exception for HTTP errors
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API Request Failed: {e}")
        return []

# ✅ Function to Find Arbitrage Opportunities
def find_arbitrage_opportunities():
    odds_data = get_odds()
    opportunities = []

    for event in odds_data:
        try:
            match = f"{event['home_team']} vs {event['away_team']}"
            sport = event['sport_title']
            event_time = convert_to_central_time(event["commence_time"])

            home_odds = []
            away_odds = []

            for bookmaker in event.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    if market["key"] == "h2h":  # Only consider head-to-head markets
                        for outcome in market.get("outcomes", []):
                            if outcome["name"] == event["home_team"]:
                                home_odds.append({
                                    "site": bookmaker["title"],
                                    "odds": outcome["price"],
                                    "url": BOOKMAKER_URLS.get(bookmaker["title"], "#")
                                })
                            elif outcome["name"] == event["away_team"]:
                                away_odds.append({
                                    "site": bookmaker["title"],
                                    "odds": outcome["price"],
                                    "url": BOOKMAKER_URLS.get(bookmaker["title"], "#")
                                })

            # Calculate implied probabilities and check for arbitrage
            for home in home_odds:
                for away in away_odds:
                    implied_prob_home = 1 / home["odds"] if home["odds"] > 0 else 0
                    implied_prob_away = 1 / away["odds"] if away["odds"] > 0 else 0
                    total_implied_prob = implied_prob_home + implied_prob_away

                    if total_implied_prob < 1:
                        opportunities.append({
                            "match": match,
                            "sport": sport,
                            "event_time": event_time,
                            "home_site": home["site"],
                            "home_odds": home["odds"],
                            "home_url": home["url"],
                            "away_site": away["site"],
                            "away_odds": away["odds"],
                            "away_url": away["url"],
                            "arbitrage_percentage": round((1 - total_implied_prob) * 100, 2)
                        })
        except KeyError as e:
            print(f"❌ Missing Key in Event Data: {e}")
            continue

    return opportunities

# ✅ Web App Route (Displays Data)
@app.route("/")
def index():
    try:
        data = find_arbitrage_opportunities()
        return render_template("index.html", opportunities=data)
    except Exception as e:
        print(f"❌ Error Rendering Template: {e}")
        return "An error occurred while processing your request.", 500

# ✅ Flask App Runner for Render Deployment
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)  # Disable debug in production