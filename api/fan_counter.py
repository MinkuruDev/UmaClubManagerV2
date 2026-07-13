import json
import os

_FAN_DATA_DIR = "../data/fan"
os.makedirs(_FAN_DATA_DIR, exist_ok=True)

def load_from_raw_file(club_profile_path):
    with open(club_profile_path, 'r') as f:
        club_profile = json.load(f)

    monthly_history = club_profile.get('club_monthly_history')
    previous_year_month = monthly_history[0].get("year_month") 
    month = previous_year_month % 100
    year = int(previous_year_month / 100)
    if month == 12:
        year += 1
        month = 1
    else:
        month += 1

    saving_data = {"total": {}}
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

    current_year_month = f"{year}{month:02d}"
    output_file_path = os.path.join(_FAN_DATA_DIR, f"{current_year_month}.json")
    with open(output_file_path, 'w') as f:
        json.dump(saving_data, f, indent=4)

fan_data = {}
def auto_load_fan_data():
    global fan_data
    # Load 2 latest fan data files
    # keep only the total of lastest month
    # Daily data is sorted by date
    fan_files = sorted([f for f in os.listdir(_FAN_DATA_DIR) if f.endswith('.json')], reverse=True)[:2]
    lastest_file = fan_files[0]
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

if __name__ == "__main__":
    # Example usage: Load from a raw club profile JSON file and save to fan data
    club_profile_path = "../data/club_profile.json"  # Path to the raw club profile JSON file
    load_from_raw_file(club_profile_path)
