from flask import Flask, jsonify, render_template, request
import requests
from datetime import datetime
import pytz
import os
from flask_caching import Cache

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

# ✅ Configuration
API_KEY = "f1e5ca6d70e837026e976e7f5a94f058"  # Your API key
API_URL = "https://api.the-odds-api.com/v4/sports/upcoming/odds"
CACHE_TIMEOUT = 30  # Seconds

# ✅ Helpers
def convert_american_to_probability(odds):
    """Convert American odds to implied probability"""
    if odds > 0:
        return 100 / (odds + 100)
    else:
        return abs(odds) / (abs(odds) + 100)

def convert_to_central_time(utc_time):
    """Convert UTC time to Central Time (CT)"""
    try:
        utc_dt = datetime.fromisoformat(utc_time.replace('Z', '+00:00'))
        central_zone = pytz.timezone("America/Chicago")
        ct_dt = utc_dt.astimezone(central_zone)
        return ct_dt.strftime("%Y-%m-%d %I:%M %p CT")
    except Exception as e:
        print(f"⚠️ Time conversion error: {e}")
        return utc_time

# ✅ API Calls with Retries
@cache.cached(timeout=CACHE_TIMEOUT)
def get_odds():
    """Fetch odds from the API"""
    try:
        response = requests.get(
            API_URL,
            params={
                "apiKey": API_KEY,
                "regions": "us",
                "oddsFormat": "american",
                "markets": "h2h,spreads,totals"
            }
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        return []

# ✅ Core Logic
def find_arbitrage_opportunities(sort_by="arb_percent"):
    """Find and calculate arbitrage opportunities"""
    opportunities = []
    
    for event in get_odds():
        try:
            # Get best odds for both teams
            best_odds = {'home': None, 'away': None}
            
            for bookmaker in event.get("bookmakers", []):
                for market in bookmaker.get("markets", []):
                    for outcome in market.get("outcomes", []):
                        # Track best odds for each team
                        if outcome["name"] == event["home_team"]:
                            if not best_odds['home'] or outcome["price"] > best_odds['home']['price']:
                                best_odds['home'] = {
                                    'price': outcome["price"],
                                    'site': bookmaker["title"],
                                    'url': bookmaker.get("link", "#")  # Add link to sportsbook
                                }
                        elif outcome["name"] == event["away_team"]:
                            if not best_odds['away'] or outcome["price"] > best_odds['away']['price']:
                                best_odds['away'] = {
                                    'price': outcome["price"],
                                    'site': bookmaker["title"],
                                    'url': bookmaker.get("link", "#")  # Add link to sportsbook
                                }

            # Calculate arbitrage
            if best_odds['home'] and best_odds['away']:
                home_prob = convert_american_to_probability(best_odds['home']['price'])
                away_prob = convert_american_to_probability(best_odds['away']['price'])
                total_prob = home_prob + away_prob
                
                if total_prob < 100:
                    arb_percent = (100 - total_prob)
                    profit = (100 / total_prob - 1) * 100  # Profit percentage
                    
                    opportunities.append({
                        "match": f"{event['home_team']} vs {event['away_team']}",
                        "sport": event['sport_title'],
                        "date": convert_to_central_time(event["commence_time"]),
                        "home_site": best_odds['home']['site'],
                        "home_odds": best_odds['home']['price'],
                        "home_url": best_odds['home']['url'],  # Add URL
                        "away_site": best_odds['away']['site'],
                        "away_odds": best_odds['away']['price'],
                        "away_url": best_odds['away']['url'],  # Add URL
                        "arb_percent": round(arb_percent, 2),
                        "profit": round(profit, 2)
                    })
                    
        except Exception as e:
            print(f"⚠️ Error processing event: {str(e)}")
            continue

    # Sorting
    sort_options = {
        "time": lambda x: datetime.strptime(x["date"], "%Y-%m-%d %I:%M %p CT"),
        "arb_percent": lambda x: -x["arb_percent"],
        "profit": lambda x: -x["profit"]
    }
    
    return sorted(opportunities, key=sort_options.get(sort_by, "arb_percent"))

# ✅ Routes
@app.route("/arbitrage")
def arbitrage():
    sort_by = request.args.get("sort", "arb_percent")
    return jsonify(find_arbitrage_opportunities(sort_by))

@app.route("/")
def index():
    sort_by = request.args.get("sort", "arb_percent")
    return render_template("index.html", 
                         opportunities=find_arbitrage_opportunities(sort_by),
                         sort_by=sort_by)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))