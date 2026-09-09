import requests
import os
import json

from typing import Tuple, Optional
from dotenv import load_dotenv

load_dotenv()
base_url = "https://api.chronogenesis.net"
chrono_genesis_token = os.getenv("CHRONO_GENESIS_TOKEN")
headers = {
    "Authorization": chrono_genesis_token,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
}

def get_last_updated_time(club_profile: dict) -> Optional[str]:
    club_friend_profile = club_profile.get("club_friend_profile", [])
    if not club_friend_profile:
        return None
    
    # iterate to get membership 3 (leader)
    for friend_profile in club_friend_profile:
        if friend_profile.get("membership") == 3:
            return friend_profile.get("updated_at", None)
        
    return None 

def fetch_club_profile() -> Tuple[bool, str]:
    response = requests.get(
        f"{base_url}/club_profile", 
        params={"circle_id": os.getenv("CLUB_ID")},
        headers=headers, 
    )

    if response.status_code == 200:
        data = response.json()
        if os.path.exists("../data/club_profile.json"):
            with open("../data/club_profile.json") as f:
                old_data = json.load(f)
            if get_last_updated_time(data) == get_last_updated_time(old_data):
                return False, "Data is already synced"
            os.rename("../data/club_profile.json", "../data/club_profile_old.json")

        with open("../data/club_profile.json", "w") as f:
            json.dump(data, f, indent=4)
        return True, ""
    else:
        print(f"Failed to fetch data: {response.status_code} - {response.text}")
        return False, "Failed to fetch club profile data"

if not os.path.exists("../data"):
    os.makedirs("../data")
if not os.path.exists("../data/club_profile.json"):
    choice = input("club_profile.json does not exist. Do you want to fetch it from the source? (Y/n): ")
    if choice.lower() == "y" or choice == "":
        updated, reason = fetch_club_profile()
        if not updated:
            print(f"Failed to fetch data: {reason}")

