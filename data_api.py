import requests
import os
import json

from dotenv import load_dotenv

load_dotenv()
base_url = "https://api.chronogenesis.net"
chrono_genesis_token = os.getenv("CHRONO_GENESIS_TOKEN")
headers = {
    "Authorization": chrono_genesis_token,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
}

response = requests.get(
    f"{base_url}/club_profile", 
    params={"circle_id": os.getenv("CLUB_ID")},
    headers=headers, 
)

if response.status_code == 200:
    data = response.json()
    with open("club_profile.json", "w") as f:
        json.dump(data, f, indent=2)
else:
    print(f"Failed to fetch data: {response.status_code} - {response.text}")
