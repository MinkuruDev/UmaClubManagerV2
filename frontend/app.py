import os
import requests
from flask import Flask, flash, flash, render_template, request, redirect, url_for
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "default_secret_key") 
api_url = "http://localhost:3636"

headers = {
    "Authorization": f"Bearer {os.environ.get('ADMIN_TOKEN')}"
}

@app.route('/')
def index():
    linked_members = []
    unlinked_members = []

    # load members from api
    try:
        response = requests.get(f"{api_url}/members")
        if response.status_code == 200:
            members_data = response.json()
            for m_id in members_data:
                m_data = members_data[m_id]
                if m_id != "discord_link" and m_id != "current_member":
                    if m_data.get("discord_id"):
                        linked_members.append({
                            "ingame_id": m_id,
                            "ingame_name": m_data.get("ingame_name", ""),
                            "discord_id": m_data.get("discord_id", ""),
                            "discord_username": m_data.get("discord_username", "")
                        })
                    else:
                        unlinked_members.append({
                            "ingame_id": m_id,
                            "ingame_name": m_data.get("ingame_name", ""),
                            "discord_id": m_data.get("discord_id", ""),
                            "discord_username": m_data.get("discord_username", "")
                        })
    except Exception as e:
        print(f"Error fetching members from API: {e}")

    return render_template('index.html', linked_members=linked_members, unlinked_members=unlinked_members)

@app.route('/add', methods=['POST'])
def add_member():
    ingame_id = request.form.get('ingame_id')
    ingame_name = request.form.get('ingame_name')
    discord_id = request.form.get('discord_id')
    discord_username = request.form.get('discord_username')

    data = {
        'ingame_id': ingame_id,
        'ingame_name': ingame_name,
        'discord_id': discord_id,
        'discord_username': discord_username
    }

    # calling the API to add the member
    try:
        response = requests.post(f"{api_url}/members/{ingame_id}", json=data, headers=headers)
        if response.status_code != 200:
            print(f"Error adding member via API: {response.text}")
        else:
            flash('Member added successfully', 'success')
    except Exception as e:
        print(f"Error adding member: {e}")

    return redirect(url_for('index'))

@app.route('/edit/<ingame_id>', methods=['POST'])
def edit_member(ingame_id):
    ingame_name = request.form.get('ingame_name')
    discord_id = request.form.get('discord_id')
    discord_username = request.form.get('discord_username')

    data = {
        'ingame_id': ingame_id,
        'ingame_name': ingame_name,
        'discord_id': discord_id,
        'discord_username': discord_username
    }

    # calling the API to update the member
    try:
        response = requests.post(f"{api_url}/members/{ingame_id}", json=data, headers=headers)
        if response.status_code != 200:
            print(f"Error updating member via API: {response.text}")
        else:
            flash('Member updated successfully', 'success')
    except Exception as e:
        print(f"Error updating member: {e}")

    return redirect(url_for('index'))

@app.route('/delete/<discord_id>', methods=['POST'])
def delete_member(discord_id):
    try:
        response = requests.delete(f"{api_url}/members/discord/{discord_id}", headers=headers)
        if response.status_code != 200:
            print(f"Error deleting member via API: {response.text}")
        else:
            flash('Member unlinked successfully', 'success')
    except Exception as e:
        print(f"Error deleting member: {e}")
    return redirect(url_for('index'))

@app.route('/fans')
def fans():
    month = request.args.get('month')
    year = request.args.get('year')
    month = int(month) if month else None
    year = int(year) if year else None

    # Get available months
    reqs = []
    latest_day = 0
    fan_rows = []

    if month and year:
        response = requests.get(f"{api_url}/fan_data/processed", params={"month": month, "year": year})
        if response.status_code == 200:
            reqs, latest_day, fan_rows = response.json()

    return render_template('fans.html', 
        selected_month=month, 
        selected_year=year,
        reqs=reqs,
        latest_day=latest_day,
        fan_rows=fan_rows
    )

@app.route('/add_requirement', methods=['POST'])
def add_requirement():
    year = request.form.get('year')
    month = request.form.get('month')
    try:
        day_start = request.form.get('day_start')
        day_end = request.form.get('day_end')
        daily_fan = request.form.get('daily_fan')

        response = requests.post(f"{api_url}/fan_data/requirements/{year}/{month}", data={
            "from_day": day_start,
            "to_day": day_end,
            "req": daily_fan
        }, headers=headers)

        if response.status_code != 200:
            print(f"Error adding requirement via API: {response.text}")
        else:
            flash('Requirement added successfully', 'success')

    except Exception as e:
        print(f"Error adding requirement: {e}")

    return redirect(url_for('fans', year=year, month=month))

@app.route('/delete_requirement', methods=['POST'])
def delete_requirement():
    try:
        year = request.form.get('year')
        month = request.form.get('month')
        from_day = request.form.get('from_day')
        to_day = request.form.get('to_day')
        req = request.form.get('req')

        response = requests.delete(f"{api_url}/fan_data/requirements/{year}/{month}", data={
            "from_day": from_day,
            "to_day": to_day,
            "req": req
        }, headers=headers)

        if response.status_code != 200:
            print(f"Error deleting requirement via API: {response.text}")
        else:
            flash('Requirement deleted successfully', 'success')

    except Exception as e:
        print(f"Error deleting requirement: {e}")
        
    return redirect(url_for('fans', year=year, month=month))

@app.route('/set_exemption', methods=['POST'])
def set_exemption():
    year = request.form.get('year')
    month = request.form.get('month')
    ingame_id = request.form.get('ingame_id')
    reason = request.form.get('reason')
    
    try:
        response = requests.post(f"{api_url}/fan_data/exemptions", data={
            "ingame_id": ingame_id,
            "reason": reason
        }, headers=headers)

        if response.status_code != 200:
            print(f"Error setting exemption via API: {response.text}")
        else:
            flash('Exemption set successfully', 'success')
    except Exception as e:
        print(f"Error handling exemption: {e}")
        
    return redirect(url_for('fans', year=year, month=month))

@app.route('/set_extra', methods=['POST'])
def set_extra():
    year = request.form.get('year')
    month = request.form.get('month')
    ingame_id = request.form.get('ingame_id')
    extra_str = request.form.get('extra')
    
    try:
        extra = int(extra_str)
        response = requests.post(f"{api_url}/fan_data/extra_requirements/{year}/{month}", data={
            "ingame_id": ingame_id,
            "extra": extra
        }, headers=headers)

        if response.status_code != 200:
            print(f"Error setting extra via API: {response.text}")
        else:
            flash('Extra set successfully', 'success')
    except ValueError:
        print(f"Invalid extra value: {extra_str}")
    except Exception as e:
        print(f"Error handling extra: {e}")
        
    return redirect(url_for('fans', year=year, month=month))

@app.route('/send_discord', methods=['POST'])
def send_discord():
    year = request.form.get('year')
    month = request.form.get('month')

    try:
        response = requests.post(f"{api_url}/fan_data/report_discord", params={'year': year, 'month': month}, headers=headers)
        if response.status_code != 200:
            print(f"Error sending report to Discord via API: {response.text}")
        else:
            flash('Report will be sent to Discord shortly', 'success')
    except Exception as e:
        print(f"Error sending report to Discord: {e}")
     
    return redirect(url_for('fans', year=year, month=month))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
