import os
import fastapi
import source_data_api
import member_manager
import fan_counter

from fan_counter import fan_data
from member_manager import Member, members_data
from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException
from typing import Annotated

load_dotenv()
app = fastapi.FastAPI()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
DATA_DIR = "../data"

def require_admin(authorization: Annotated[str | None, Header(alias="Authorization")] = None):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="Admin token is not configured")
    if authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")
    
@app.get("/")
def read_root():
    return {"Application": "Uma Club Manager API", "Version": "2.0.0"}

@app.post("/full_update")
def full_update(_=Depends(require_admin)):
    updated, reason = source_data_api.fetch_club_profile()
    if not updated:
        raise HTTPException(503, reason)
    
    member_manager.load_from_raw_file(f"{DATA_DIR}/club_profile.json")
    member_manager.save_members_data()
    fan_counter.load_from_raw_file(f"{DATA_DIR}/club_profile.json")
    fan_counter.auto_load_fan_data()
    return {"message": "Full update completed successfully"}

@app.get("/members")
def get_members():
    return members_data

@app.get("/members/{member_id}")
def get_member(member_id: str):
    member = members_data.get(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@app.get("/members/discord/{discord_id}")
def get_member_by_discord_id(discord_id: str):
    discord_link = members_data.get("discord_link", {})
    if discord_id in discord_link:
        ingame_id = discord_link[discord_id]
        member = members_data.get(ingame_id)
        if member:
            return member
    raise HTTPException(status_code=404, detail=f"Member with Discord ID {discord_id} not found")

@app.post("/members/{member_id}")
def update_member(member_id: str, member: Member, _=Depends(require_admin)):
    if member_id not in members_data:
        member_manager.add_or_update_member(member_id, **member.model_dump())
        member_manager.save_members_data()
        return {"message": "Member created successfully", "member": member}

    if not (member.ingame_name or member.join_time or member.discord_id or member.discord_username):
        raise HTTPException(status_code=400, detail="No update fields provided")

    update_fields = {}
    if member.ingame_name is not None:
        update_fields["ingame_name"] = member.ingame_name
    if member.join_time is not None:
        update_fields["join_time"] = member.join_time
    if member.discord_id is not None:
        update_fields["discord_id"] = member.discord_id
    if member.discord_username is not None:
        update_fields["discord_username"] = member.discord_username

    member_manager.add_or_update_member(member_id, **update_fields)
    member_manager.save_members_data()
    return {"message": "Member updated successfully", "member": member}

@app.get("/fan_data")
def get_all_fan_data():
    return fan_data

@app.get("/fan_data/{ingame_id}")
def get_fan_data(ingame_id: str):
    if ingame_id not in fan_data:
        raise HTTPException(status_code=404, detail="Fan data not found")
    # Return the latest 30 days of fan data and monthly fan count of that ingame_id
    return {
        "fan_data": fan_data[ingame_id][:30],
        "monthly_fans": fan_data["total"].get(ingame_id, 0)
    }

if __name__ == "__main__":
    print(len(ADMIN_TOKEN))
