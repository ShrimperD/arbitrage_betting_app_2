import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import requests
from datetime import datetime
import pytz
import threading

app = Flask(__name__)
socketio = SocketIO(app)

# ✅ API Key (Use Render Environment Variables)
API_KEY = "f1e5ca6d70e837026e976e7f5a94f058"  # Add your API key here
API_URL = f"https://api.the-odds-api.com/v4/sports/upcoming/odds?apiKey={API_KEY}&regions=us&oddsFormat=american"

# ✅ Mapping of Bookmaker Names to URLs (Updated and Verified)
BOOKMAKER_URLS = {
    "Bovada": "https://www.bovada.lv",
    "BetRivers": "https://www.betrivers.com",
    "Caesars": "https://www.caesars.com/sportsbook",
    "BetMGM": "https://sports.ks.betmgm.com",
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
        return utc_time

# ✅ Function to Fetch Odds from API
def get_odds():
    try:
        response = requests.get(API_URL, timeout=10)
        response.raise_for_status()
        print("API Response:", response.json())  # Debug: Print the API response
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
                    if market["key"] == "h2h":
                        for outcome in market.get("outcomes", []):
                            if outcome["name"] == event["home_team"]:
                                home_odds.append({
                                    "site": bookmaker["title"],
                                    "odds": outcome["price"],
                                    "url": f"{BOOKMAKER_URLS.get(bookmaker['title'], '#')}/event/{event['id']}"
                                })
                            elif outcome["name"] == event["away_team"]:
                                away_odds.append({
                                    "site": bookmaker["title"],
                                    "odds": outcome["price"],
                                    "url": f"{BOOKMAKER_URLS.get(bookmaker['title'], '#')}/event/{event['id']}"
                                })

            for home in home_odds:
                for away in away_odds:
                    # Convert American odds to implied probabilities
                    def american_to_implied_probability(odds):
                        if odds > 0:
                            return 100 / (odds + 100)
                        else:
                            return abs(odds) / (abs(odds) + 100)

                    implied_prob_home = american_to_implied_probability(home["odds"])
                    implied_prob_away = american_to_implied_probability(away["odds"])
                    total_implied_prob = implied_prob_home + implied_prob_away

                    if total_implied_prob < 1:
                        arbitrage_percentage = (1 - total_implied_prob) * 100
                        potential_profit = (arbitrage_percentage / 100) * 100  # For $100 stake
                        profit_percentage = (potential_profit / 100) * 100  # Profit percentage

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
                            "profit_percentage": round(profit_percentage, 2),  # Add profit percentage
                            "potential_profit": round(potential_profit, 2)
                        })

                        # Debug: Print arbitrage opportunities
                        print(f"Arbitrage Opportunity: {match} | Profit %: {profit_percentage}% | Potential Profit: ${potential_profit}")
        except KeyError as e:
            print(f"❌ Missing Key in Event Data: {e}")
            continue

    opportunities.sort(key=lambda x: x["profit_percentage"], reverse=True)
    return opportunities

# ✅ Web App Route (Displays Data)
@app.route("/")
def index():
    try:
        data = find_arbitrage_opportunities()
        filter_percentage = request.args.get("filter", default=0, type=float)
        filtered_data = [opp for opp in data if opp["profit_percentage"] >= filter_percentage]

        # Debug: Print filtered data
        print(f"Filtered Data (Profit % ≥ {filter_percentage}%): {filtered_data}")

        return render_template("index.html", opportunities=filtered_data, filter_percentage=filter_percentage)
    except Exception as e:
        print(f"❌ Error Rendering Template: {e}")
        return "An error occurred while processing your request.", 500

# ✅ SocketIO Event for Real-Time Updates
@socketio.on('connect')
def handle_connect():
    emit('update_opportunities', find_arbitrage_opportunities())

# ✅ Background Thread for Periodic Updates
def background_thread():
    while True:
        socketio.sleep(30)  # Update every 30 seconds
        opportunities = find_arbitrage_opportunities()
        socketio.emit('update_opportunities', opportunities)

# ✅ Start Background Thread
threading.Thread(target=background_thread, daemon=True).start()

# ✅ Flask App Runner for Render Deployment
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)