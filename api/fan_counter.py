import json
import os
import csv
import calendar
import member_manager
import datetime

from pathlib import Path

_FAN_DATA_DIR = "../data/fan"
_EXEMPTIONS_PATH = "../data/exemptions.json"
os.makedirs(_FAN_DATA_DIR, exist_ok=True)

def process_fan_data(year: int, month: int):
    """
    Compute fan status for a given year/month using JSON data files.
    Returns (reqs, latest_day, fan_rows).

    Data sources:
      - members:      ../data/members_profile.json  (via member_manager)
      - exemptions:   ../data/exemptions.json       (via get_exemptions)
      - requirements: ../data/requirements/{year}.json  (via get_fan_requirements)
      - fan data:     ../data/fan/{year}/{month:02d}.json (via load_specific_fan_data)
    """
    days_in_month = calendar.monthrange(year, month)[1]

    exemptions_dict = get_exemptions()

    month_data = get_fan_requirements(year, month)
    reqs = month_data.get("requirements", [])
    extras_dict = month_data.get("extra", {})

    # Build daily quota map: day -> required fan
    daily_quota_map = {}
    for req in reqs:
        for d in range(req["from"], req["to"] + 1):
            daily_quota_map[d] = req["req"]

    # --- Load fan data from JSON API file ---
    fan_json = load_specific_fan_data(year, month)
    if not fan_json:
        return reqs, 0, []

    totals = fan_json.get("total", {})

    # --- Determine latest_day (global: max day across all members) ---
    all_dates = set()
    for key, records in fan_json.items():
        if key in ("total", "club_ranking"):
            continue
        if isinstance(records, list):
            for rec in records:
                all_dates.add(rec["date"])
    if not all_dates:
        return reqs, 0, []

    sorted_dates = sorted(all_dates)
    latest_day = int(sorted_dates[-1].split("-")[-1])

    expected_total = sum(daily_quota_map.get(d, 0) for d in range(1, latest_day + 1))
    current_daily_req = daily_quota_map.get(latest_day, 0)

    # --- Build fan rows ---
    member_data = member_manager.members_data
    raw_rows = []

    for ingame_id, records in fan_json.items():
        if ingame_id in ("total", "club_ranking"):
            continue
        if not isinstance(records, list):
            continue
        if int(ingame_id) not in member_data["current_member"]:
            continue

        m_data = member_data.get(ingame_id, {})
        name = m_data.get("ingame_name", ingame_id)
        discord_id = m_data.get("discord_id")

        # Accumulate fan total for this member from daily gains
        fan_val = totals.get(ingame_id, 0)

        # Find member's latest day gain
        member_latest_gain = sorted(records, key=lambda x: x["date"], reverse=True)[0]["fan"] if records else 0

        raw_rows.append({
            "ingame_id": ingame_id,
            "name": name,
            "discord_id": discord_id,
            "fan": fan_val,
            "expected": expected_total,
            "current_daily_req": current_daily_req,
            "exempt": exemptions_dict.get(ingame_id),
            "latest_day": member_latest_gain,
        })

    for row in raw_rows:
        fan = row["fan"]
        base_expected = row["expected"]
        base_req_day = row["current_daily_req"]
        ingame_id = row["ingame_id"]

        extra = extras_dict.get(ingame_id, 0)

        if extra > 0:
            effective_expected = round(base_expected + (extra / float(days_in_month)) * latest_day)
            effective_req_day = base_req_day + (extra / float(days_in_month))
        else:
            effective_expected = max(0, base_expected + extra)
            effective_req_day = base_req_day

        deficit = effective_expected - fan
        status = "normal"

        if extra > 0:
            if base_expected > 0 and (fan - extra) >= base_expected * 2:
                status = "great"
            elif base_expected > 0 and (fan - extra) >= base_expected * 1.5:
                status = "good"
            elif deficit > effective_req_day * 3:
                status = "awful"
            elif 0 < deficit <= effective_req_day * 3:
                status = "bad"
        else:
            if base_expected > 0 and fan >= base_expected * 2:
                status = "great"
            elif base_expected > 0 and fan >= base_expected * 1.5:
                status = "good"
            elif deficit > effective_req_day * 3:
                status = "awful"
            elif 0 < deficit <= effective_req_day * 3:
                status = "bad"

        if latest_day > 25 and status == "bad":
            status = "awful"

        row["status"] = status
        row["expected"] = effective_expected
        row["extra"] = extra

    raw_rows.sort(key=lambda x: x["fan"], reverse=True)
    return reqs, latest_day, raw_rows

def load_from_raw_file(club_profile_path):
    with open(club_profile_path, 'r') as f:
        club_profile = json.load(f)

    now = datetime.datetime.now(tz=datetime.timezone.utc)
    if now.hour < 10:
        report_day = now - datetime.timedelta(days=2)
    else:
        report_day = now - datetime.timedelta(days=1)
    month = report_day.month
    year = report_day.year

    saving_data = {"total": {}}
    club_daily_history = club_profile.get('club_daily_history', [])
    for club_daily in club_daily_history:
        if 'club_ranking' not in saving_data:
            saving_data['club_ranking'] = []
        club_history = saving_data['club_ranking']
        actual_date = club_daily.get('actual_date')
        daily_fan = club_daily.get('interpolated_fan_gain')
        rank = club_daily.get('rank')
        club_history.append({
            "date": f"{year}-{month:02d}-{actual_date:02d}",
            "fan": daily_fan,
            "rank": rank
        })
        total_history = saving_data["total"].get('club_ranking', 0)
        saving_data["total"]['club_ranking'] = total_history + daily_fan

    history_data = club_profile.get('club_friend_history', [])
    for member_daily in history_data:
        ingame_id = str(member_daily.get('friend_viewer_id'))
        if ingame_id not in saving_data:
            saving_data[ingame_id] = []
        member_history = saving_data[ingame_id]
        actual_date = member_daily.get('actual_date')
        daily_fan = member_daily.get('adjusted_interpolated_fan_gain')
        member_history.append({
            "date": f"{year}-{month:02d}-{actual_date:02d}",
            "fan": daily_fan
        })
        total_history = saving_data["total"].get(ingame_id, 0)
        saving_data["total"][ingame_id] = total_history + daily_fan

    current_year_month = f"{year}/{month:02d}"
    os.makedirs(os.path.join(_FAN_DATA_DIR, f"{year}"), exist_ok=True)
    output_file_path = os.path.join(_FAN_DATA_DIR, f"{current_year_month}.json")
    with open(output_file_path, 'w') as f:
        json.dump(saving_data, f, indent=4)

fan_data = {}
def auto_load_fan_data():
    global fan_data
    # Load 2 latest fan data files
    # keep only the total of lastest month
    # Daily data is sorted by date
    fan_files = sorted((
        p.relative_to(_FAN_DATA_DIR).as_posix()
        for p in Path(_FAN_DATA_DIR).glob("*/*.json")
    ),reverse=True,)[:2]
    lastest_file = fan_files[0] if fan_files else None
    if not lastest_file:
        return
    previous_file = fan_files[1] if len(fan_files) > 1 else None
    with open(os.path.join(_FAN_DATA_DIR, lastest_file), 'r') as f:
        fan_data = json.load(f)
    
    if previous_file:
        with open(os.path.join(_FAN_DATA_DIR, previous_file), 'r') as f:
            previous_fan_data = json.load(f)
            del previous_fan_data["total"]
        # Merge previous month data into the total of latest month
        for ingame_id, daily_data in previous_fan_data.items():
            if ingame_id not in fan_data:
                fan_data[ingame_id] = []
            fan_data[ingame_id].extend(daily_data)

    for ingame_id, daily_data in fan_data.items():
        if ingame_id != "total":
            daily_data.sort(key=lambda x: x["date"], reverse=True)
    # print(fan_data["205831989943"])

auto_load_fan_data()

def transform_json_to_csv(json_file_path, output_csv_path = None):
    with open(json_file_path) as jf:
        json_data = json.load(jf)

    # 1. Collect all unique dates from the member data
    all_dates = set()
    for key, records in json_data.items():
        if key in ["total", "club_ranking"]:
            continue
        for record in records:
            all_dates.add(record["date"])
            
    # Sort dates chronologically to use as column headers
    sorted_dates = sorted(list(all_dates))
    
    only_day = []
    for date in sorted_dates:
        day = date.split("-")[-1]
        only_day.append(f"Day {day}")

    # Define CSV headers
    headers = ["Trainer ID", "Name"] + only_day
    csv_rows = []
    
    # 2. Process each member's data
    for member_id, records in json_data.items():
        if member_id in ["total", "club_ranking"]:
            continue
            
        # Resolve the member name
        try:
            name = member_manager.members_data[member_id]["ingame_name"]
        except (KeyError, AttributeError, TypeError):
            name = f"Unknown ({member_id})"
            
        # Initialize the row with Trainer ID and Name
        row = {
            "Trainer ID": member_id,
            "Name": name
        }
        
        # Create a dictionary mapping date -> fan count for this specific member
        member_fan_data = {record["date"]: record["fan"] for record in records}
        
        # Fill in the fan counts for each date column
        accumative_fan = 0
        for date in sorted_dates:
            if isinstance(accumative_fan, str):
                accumative_fan = 0
            if member_fan_data.get(date, None) is None:
                accumative_fan = ''
            else:
                accumative_fan += member_fan_data[date]
            
            # FIX: Format the key to match the headers ("Day XX")
            day = date.split("-")[-1]
            day_header = f"Day {day}"
            row[day_header] = accumative_fan
            
        csv_rows.append(row)

    if not output_csv_path:
        output_csv_path = json_file_path[0:-5] + ".csv"
    with open(output_csv_path, mode="w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(csv_rows)

def load_specific_fan_data(year: int, month: int):
    # Construct the file path based on year and month
    json_file_path = f"../data/fan/{year}/{month:02d}.json"
    if not os.path.exists(json_file_path):
        return {}
    with open(json_file_path) as jf:
        json_data = json.load(jf)
    return json_data

def get_fan_requirements(year: int, month: int):
    json_file_path = f"../data/requirements/{year}.json"
    if not os.path.exists(json_file_path):
        return {}
    with open(json_file_path) as jf:
        json_data = json.load(jf)
    
    return json_data.get(f"{month:02d}", {})

def set_fan_requirements(year: int, month: int, from_day: int, to_day: int, req: int):
    json_file_path = f"../data/requirements/{year}.json"
    if os.path.exists(json_file_path):
        with open(json_file_path) as jf:
            json_data = json.load(jf)
    else:
        json_data = {}
    
    if f"{month:02d}" not in json_data:
        json_data[f"{month:02d}"] = {}
    if "requirements" not in json_data[f"{month:02d}"]:
        json_data[f"{month:02d}"]["requirements"] = []
    
    json_data[f"{month:02d}"]["requirements"].append({
        "from": from_day,
        "to": to_day,
        "req": req
    })
    with open(json_file_path, 'w') as jf:
        json.dump(json_data, jf, indent=4)

def set_extra_fan_requirements(year: int, month: int, id: str, extra_req: int):
    json_file_path = f"../data/requirements/{year}.json"
    if os.path.exists(json_file_path):
        with open(json_file_path) as jf:
            json_data = json.load(jf)
    else:
        json_data = {}
    
    if f"{month:02d}" not in json_data:
        json_data[f"{month:02d}"] = {}
    if "extra" not in json_data[f"{month:02d}"]:
        json_data[f"{month:02d}"]["extra"] = {}
    
    json_data[f"{month:02d}"]["extra"][id] = extra_req
    with open(json_file_path, 'w') as jf:
        json.dump(json_data, jf, indent=4)

def delete_fan_requirements(year: int, month: int, from_day: int, to_day: int, reqirement: int):
    json_file_path = f"../data/requirements/{year}.json"
    if not os.path.exists(json_file_path):
        return
    with open(json_file_path) as jf:
        json_data = json.load(jf)
    
    if f"{month:02d}" in json_data and "requirements" in json_data[f"{month:02d}"]:
        json_data[f"{month:02d}"]["requirements"] = [
            req for req in json_data[f"{month:02d}"]["requirements"]
            if not (req["from"] == from_day and req["to"] == to_day and req["req"] == reqirement)
        ]
        with open(json_file_path, 'w') as jf:
            json.dump(json_data, jf, indent=4)

def get_exemptions():
    if not os.path.exists(_EXEMPTIONS_PATH):
        return {}
    with open(_EXEMPTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def set_exemption(id: str, reason: str):
    json_file_path = f"../data/exemptions.json"
    if os.path.exists(json_file_path):
        with open(json_file_path) as jf:
            json_data = json.load(jf)
    else:
        json_data = {}
    
    json_data[id] = reason
    with open(json_file_path, 'w', encoding='utf-8') as jf:
        json.dump(json_data, jf, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    # Example usage: Load from a raw club profile JSON file and save to fan data
    club_profile_path = "../data/club_profile.json"  # Path to the raw club profile JSON file
    load_from_raw_file(club_profile_path)
