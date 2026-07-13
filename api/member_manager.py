import json
import os

from pydantic import BaseModel

class Member(BaseModel):
    ingame_id: str
    ingame_name: str = None
    join_time: str = None
    discord_id: str = None
    discord_username: str = None

_MEMBER_DATA_PATH = "../data/members_profile.json"
os.makedirs("../data", exist_ok=True)

def load_members_data():
    if not os.path.exists(_MEMBER_DATA_PATH):
        return {}
    with open(_MEMBER_DATA_PATH, 'r') as f:
        members_data = json.load(f)
    return members_data
members_data = load_members_data()

def save_members_data():
    with open(_MEMBER_DATA_PATH, 'w') as f:
        json.dump(members_data, f, indent=4)

def add_or_update_member(id, **kwargs):
    id = str(id)
    if id in members_data:
        # print(f"Updating member with ID: {id}")
        members_data[id].update(kwargs)
    else:
        # print(f"Adding new member with ID: {id}")
        members_data[id] = kwargs
    
    if "discord_id" in kwargs and kwargs["discord_id"]:
        discord_id = str(kwargs["discord_id"])
        if "discord_link" not in members_data:
            members_data["discord_link"] = {}
        members_data["discord_link"][discord_id] = id

def load_from_raw_file(club_profile_path):
    with open(club_profile_path, 'r') as f:
        club_profile = json.load(f)

    for member in club_profile.get('club_friend_profile', []):
        ingame_id = member.get('friend_viewer_id')
        if ingame_id:
            add_or_update_member(str(ingame_id),
                ingame_id=str(ingame_id),
                ingame_name=member.get('name'),
                join_time=member.get('join_time'),
            )
    
    current_member = club_profile['club'][0]['circle_user_array']
    current_member.sort()
    members_data["current_member"] = current_member

if __name__ == "__main__":
    # Example usage: Load from a raw club profile JSON file and save to members.json
    club_profile_path = "../data/club_profile.json"  # Path to the raw club profile JSON file
    load_from_raw_file(club_profile_path)
    save_members_data()
