import json
import os
import csv
import member_manager
import datetime

from pathlib import Path

_FAN_DATA_DIR = "../data/fan"
os.makedirs(_FAN_DATA_DIR, exist_ok=True)

def load_from_raw_file(club_profile_path):
    with open(club_profile_path, 'r') as f:
        club_profile = json.load(f)

    now = datetime.datetime.now()
    if now.hour < 17:
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
        
if __name__ == "__main__":
    # Example usage: Load from a raw club profile JSON file and save to fan data
    club_profile_path = "../data/club_profile.json"  # Path to the raw club profile JSON file
    load_from_raw_file(club_profile_path)
    transform_json_to_csv("../data/fan/202607.json")
