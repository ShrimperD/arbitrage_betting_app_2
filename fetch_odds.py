import requests
import json
import time

# Replace with your API key
API_KEY = "f1e5ca6d70e837026e976e7f5a94f058"

# List of sports to fetch
SPORTS = [
    "basketball_nba", 
    "americanfootball_nfl", 
    "baseball_mlb", 
    "icehockey_nhl", 
    "soccer_epl", 
    "soccer_uefa_champs_league"
]

# API URL
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/{}/odds/"

# Fetch odds for each sport
odds_data = []
for sport in SPORTS:
    try:
        response = requests.get(
            ODDS_API_URL.format(sport),
            params={"apiKey": API_KEY, "markets": "h2h", "regions": "us"}
        )
        if response.status_code == 200:
            data = response.json()
            odds_data.extend(data)
            print(f"✅ Successfully fetched odds for {sport}")
        else:
            print(f"⚠️ Error fetching {sport}: {response.text}")
    except Exception as e:
        print(f"❌ Failed to fetch {sport}: {e}")

# Save to odds.json
with open("odds.json", "w") as f:
    json.dump(odds_data, f, indent=4)

print("✅ Odds data updated successfully!")
