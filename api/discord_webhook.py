import requests
import calendar

def send_fan_report(fan_rows, webhook_url, year, month, latest_day="Unknown"):
    if not webhook_url:
        print("No Webhook URL configured")
        return False

    header = f"{'In-Game Name':<20} | {'Fans':<12} | {'Expected':<12} | {'Status'}"
    divider = "-" * 60

    tags = []
    lines = []
    
    emoji_map = {
        'great': '⬆️ Great',
        'good': '↗️ Good',
        'normal': '➡️ Normal',
        'bad': '↘️ Bad',
        'awful': '⬇️ Awful'
    }
    
    for row in fan_rows:
        name_str = (row['name'][:17] + '...') if len(row['name']) > 20 else row['name']
        status_raw = row['status']
        status_str = emoji_map.get(status_raw, status_raw.capitalize())
        try:
            fan_m = f"{float(row['fan']) / 1000000:.1f}M"
        except:
            fan_m = str(row['fan'])

        try:
            expected_m = f"{float(row['expected']) / 1000000:.1f}M"
        except:
            expected_m = str(row['expected'])
            
        lines.append(f"{name_str:<20} | {fan_m:<12} | {expected_m:<12} | {status_str}{' (Exempt)' if row.get('exempt') else ''}")
        
        if status_raw == 'awful' and not row.get('exempt'):
            discord_id = row.get('discord_id')
            if discord_id:
                tags.append(f"<@{discord_id}>")

    action_msg = ""
    if tags:
        action_msg = "\n**Action Required:** " + " ".join(tags) + " You are falling behind your fan quotas! Please check your progress."

    # Formatting the month header
    main_header = f"# Fan Progress Report - {calendar.month_name[month]} {year} (Day {latest_day})\n"

    # Chunking logic (max 2000 chars)
    chunks = []
    current_chunk = [main_header, "```", header, divider]
    current_length = sum(len(x) for x in current_chunk) + len(current_chunk)
    
    for line in lines:
        if current_length + len(line) + 5 > 1900: # leave room for ``` and newlines
            current_chunk.append("```")
            chunks.append("\n".join(current_chunk))
            current_chunk = ["```", header, divider, line]
            current_length = sum(len(x) for x in current_chunk) + len(current_chunk)
        else:
            current_chunk.append(line)
            current_length += len(line) + 1
            
    current_chunk.append("```")
    chunks.append("\n".join(current_chunk))
    
    # Add the ping message to the last chunk if it fits, else as a new chunk
    if action_msg:
        if len(chunks[-1]) + len(action_msg) > 1900:
            chunks.append(action_msg)
        else:
            chunks[-1] += action_msg

    try:
        for chunk in chunks:
            response = requests.post(webhook_url, json={"content": chunk})
            response.raise_for_status()
        return True
    except Exception as e:
        print(f"Error sending to Discord: {e}")
        return False

def send_image(image_path, webhook_url):
    if not webhook_url:
        print("No Webhook URL configured")
        return False

    with open(image_path, 'rb') as f:
        files = {'file': (image_path, f)}
        try:
            response = requests.post(webhook_url, files=files)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"Error sending image to Discord: {e}")
            return False
