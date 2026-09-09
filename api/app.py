import datetime
import json
import os
import fastapi
import source_data_api
import member_manager
import fan_counter

from pathlib import Path
from fastapi.responses import FileResponse, Response
from fastapi import Request, Form
from member_manager import Member 
from dotenv import load_dotenv
from fastapi import Depends, Header, HTTPException, BackgroundTasks
from typing import Annotated
from chart_service import CHART_MAPPING
from discord_webhook import send_fan_report, send_image
from screenshoot import take_screenshot

load_dotenv()
app = fastapi.FastAPI()
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")
DATA_DIR = "../data"

def require_admin(authorization: Annotated[str | None, Header(alias="Authorization")] = None):
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="Admin token is not configured")
    if authorization != f"Bearer {ADMIN_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

raw_data = {}
def load_raw_data():
    global raw_data
    path = f"{DATA_DIR}/club_profile.json"
    if not os.path.exists(path):
        return
    with open(path) as f:
        raw_data = json.load(f)
load_raw_data()

def latest_game_date():
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if now.hour < 10:
        report_day = now - datetime.timedelta(days=2)
    else:
        report_day = now - datetime.timedelta(days=1)
    month = report_day.month
    year = report_day.year
    day = report_day.day
    return year, month, day
    
@app.get("/")
def read_root():
    return {"Application": "Uma Club Manager API", "Version": "2.0.0"}

@app.get("/raw")
def get_raw_data(fields: str = ""):
    try:
        if not fields:
            return raw_data
        
        data = raw_data
        for field in fields.split(","):
            if isinstance(data, dict):
                data = data[field]
            elif isinstance(data, list):
                field = int(field)
                data = data[field]
        return data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=e)

@app.post("/full_update")
def full_update(_=Depends(require_admin)):
    updated, reason = source_data_api.fetch_club_profile()
    if not updated:
        raise HTTPException(status_code=503, detail=reason)
    
    load_raw_data()
    member_manager.load_from_raw_file(f"{DATA_DIR}/club_profile.json")
    member_manager.save_members_data()
    fan_counter.load_from_raw_file(f"{DATA_DIR}/club_profile.json")
    fan_counter.auto_load_fan_data()
    return {"message": "Full update completed successfully"}

@app.get("/members")
def get_members():
    return member_manager.members_data

@app.get("/members/{member_id}")
def get_member(member_id: str):
    member = member_manager.members_data.get(member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member

@app.get("/members/discord/{discord_id}")
def get_member_by_discord_id(discord_id: str):
    discord_link = member_manager.members_data.get("discord_link", {})
    if discord_id in discord_link:
        ingame_id = discord_link[discord_id]
        member = member_manager.members_data.get(ingame_id)
        if member:
            return member
    raise HTTPException(status_code=404, detail=f"Member with Discord ID {discord_id} not found")

@app.delete("/members/discord/{discord_id}")
def unlink_discord(discord_id: str, _=Depends(require_admin)):
    discord_link = member_manager.members_data.get("discord_link", {})
    if discord_id in discord_link:
        ingame_id = discord_link[discord_id]
        member = member_manager.members_data.get(ingame_id)
        if member:
            member.pop("discord_id", None)
            member.pop("discord_username", None)
            del discord_link[discord_id]
            member_manager.save_members_data()
            return {"message": f"Discord ID {discord_id} unlinked from in-game ID {ingame_id}"}
    raise HTTPException(status_code=404, detail=f"Member with Discord ID {discord_id} not found")

@app.post("/members/{member_id}")
def update_member(member_id: str, member: Member, _=Depends(require_admin)):
    if member_id not in member_manager.members_data:
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

@app.get("/csv")
def get_csv_fan_data(yyyymm: str = None):
    if not yyyymm:
        fan_dir = Path("../data/fan")
        latest_json = max(fan_dir.glob("*/*.json"))
        yyyymm = latest_json.relative_to(fan_dir).with_suffix("").as_posix()

    json_path = Path("../data/fan") / f"{yyyymm}.json"
    csv_path = json_path.with_suffix(".csv")
    fan_counter.transform_json_to_csv(str(json_path))

    return FileResponse(
        path=str(csv_path),
        filename=f"{Path(yyyymm).name}.csv",
        media_type="text/csv",
    )

@app.get("/fan_data")
def get_all_fan_data(year: int = None, month: int = None):
    if year is not None and month is not None:
        return fan_counter.load_specific_fan_data(year, month)
    return fan_counter.fan_data

@app.get("/fan_data/requirements/{year}/{month}")
def get_fan_requirements(year: int, month: int):
    return fan_counter.get_fan_requirements(year, month)

@app.post("/fan_data/requirements/{year}/{month}")
def set_fan_requirements(year: int, month: int, from_day: Annotated[int, Form()], to_day: Annotated[int, Form()], req: Annotated[int, Form()], _=Depends(require_admin)):
    fan_counter.set_fan_requirements(year, month, from_day, to_day, req)
    return {"message": "Fan requirements set successfully"}

@app.delete("/fan_data/requirements/{year}/{month}")
def delete_fan_requirements(year: int, month: int, from_day: Annotated[int, Form()], to_day: Annotated[int, Form()], req: Annotated[int, Form()], _=Depends(require_admin)):
    fan_counter.delete_fan_requirements(year, month, from_day, to_day, req)
    return {"message": "Fan requirements deleted successfully"}

@app.post("/fan_data/extra_requirements/{year}/{month}")
def set_extra_fan_requirements(year: int, month: int, ingame_id: Annotated[str, Form()], extra: Annotated[int, Form()], _=Depends(require_admin)):
    fan_counter.set_extra_fan_requirements(year, month, ingame_id, extra)
    return {"message": "Extra fan requirements set successfully"}

@app.get("/fan_data/exemptions")
def get_exemptions():
    return fan_counter.get_exemptions()

@app.post("/fan_data/exemptions")
def set_exemption(ingame_id: Annotated[str, Form()], reason: Annotated[str, Form()], _=Depends(require_admin)):
    fan_counter.set_exemption(ingame_id, reason)
    return {"message": "Exemption set successfully"}

@app.get("/fan_data/processed")
def get_processed_fan_data(year: int = None, month: int = None):
    if year is None or month is None:
        year, month, _ = latest_game_date()
    return fan_counter.process_fan_data(year, month)

@app.post("/fan_data/report_discord")
def report_fan_data_to_discord(background_tasks: BackgroundTasks, year: int = None, month: int = None, _=Depends(require_admin)):
    if year is None or month is None:
        year, month, _ = latest_game_date()
    async def send_report():
        _, latest_day, fan_rows = fan_counter.process_fan_data(year, month)
        webhook_url = os.environ.get("DISCORD_WEBHOOK")
        send_fan_report(fan_rows, webhook_url, year, month, latest_day)
        screenshot_path = await take_screenshot(year, month)
        if screenshot_path:
            send_image(screenshot_path, webhook_url)
    background_tasks.add_task(send_report)
    return {"message": "Fan report is scheduled to be sent to Discord"}

@app.get("/fan_data/{ingame_id}")
def get_fan_data(ingame_id: str, limit: int = 30):
    if ingame_id not in fan_counter.fan_data:
        raise HTTPException(status_code=404, detail="Fan data not found")
    # Return the latest 30 days of fan data and monthly fan count of that ingame_id
    return {
        "fan_data": fan_counter.fan_data[ingame_id][:limit] \
            if isinstance(fan_counter.fan_data[ingame_id], list) \
            else fan_counter.fan_data[ingame_id],
        "monthly_fans": fan_counter.fan_data["total"].get(ingame_id, 0)
    }

@app.get("/chart/{chart_type}")
def get_chart(chart_type: str, request: Request):
    query_kwargs = dict(request.query_params)
    for key in query_kwargs.keys():
        if "," in query_kwargs[key]:
            arr = query_kwargs[key].split(",")
            query_kwargs[key] = arr
    if chart_type not in CHART_MAPPING:
        raise HTTPException(status_code=404, detail=f"Chart type not found: {chart_type}")

    return Response(
        CHART_MAPPING[chart_type](**query_kwargs),
        media_type="image/png"
    )

if __name__ == "__main__":
    print(len(ADMIN_TOKEN))
