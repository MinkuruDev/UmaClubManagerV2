import os

import fastapi
from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException
from typing import Annotated

try:
    from . import member_manager
    from .member_manager import Member, members_data
except ImportError:  # pragma: no cover - allows running the file directly
    import member_manager
    from member_manager import Member, members_data

load_dotenv()
app = fastapi.FastAPI()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

def require_admin(authorization: Annotated[str | None, Header(alias="Authorization")] = None):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="Admin token is not configured")
    if authorization != f"Bearer {ADMIN_TOKEN}":
        print(f"Unauthorized access attempt with token: {authorization}")
        raise HTTPException(status_code=401, detail="Unauthorized")
    
@app.get("/")
def read_root():
    return {"Application": "Uma Club Manager API", "Version": "2.0.0"}

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
    for member in members_data.values():
        if member.get("discord_id") == discord_id:
            return member
    raise HTTPException(status_code=404, detail="Member not found or not linked to Discord")

@app.post("/members/{member_id}")
def update_member(member_id: str, member: Member, _=Depends(require_admin)):
    if member_id not in members_data:
        member_manager.add_or_update_member(member_id, **member.model_dump())
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

if __name__ == "__main__":
    print(len(ADMIN_TOKEN))
