# 🐎 UmaClubManagerV2

**UmaClubManagerV2** is a automated management system for **Umamusume Pretty Derby** clubs/circles. It synchronizes circle profile data, tracks daily member fan gains, enforces fan quotas, generates visual performance analytics, and integrates directly with Discord through both a Slash Command Discord Bot and Webhooks.

---

## 🌟 Key Features

- 🔄 **Automated Data Sync**: Fetches live club profiles and member fan statistics via the ChronoGenesis API.
- 📊 **Fan Tracking & Quotas**: Computes daily fan gains, tracks monthly progress against customizable target ranges, supports individual extra requirements, and handles member exemptions.
- ⚡ **FastAPI Backend**: Provides high-performance REST endpoints for member management, data querying, fan calculations, and dynamic chart rendering.
- 🎨 **Flask Web Dashboard**: Interactive administrative panel to link Discord accounts with in-game IDs, set fan quotas, and view monthly fan report cards.
- 🤖 **Discord Bot**: Discord bot supporting Slash Commands for members to view personal profile cards, compare fan gains, and view daily club ranking charts.
- 📢 **Automated Webhook Reporting**: Automatically or Manually send reports to Discord, alerts underperforming member.
- 📈 **Dynamic Analytics Charts**: Generates customized Matplotlib plots (club ranking, daily/monthly fan gains, multi-member comparisons).

---

## 🏗️ Architecture Overview

```
                        ┌─────────────────────────────────┐
                        │      ChronoGenesis API          │
                        └────────────────┬────────────────┘
                                         │ Data Sync
                                         ▼
┌──────────────────┐            ┌──────────────────┐            ┌──────────────────┐
│  Flask Dashboard ├───────────►│  FastAPI Backend |◄───────────┤   Discord Bot    │
│  (Port 5000)     │            │   (Port 3636)    │            │ (Slash Commands) │
└──────────────────┘            └────────┬─────────┘            └──────────────────┘
                                         │
                                         ├───► Dynamic Matplotlib Charts
                                         ├───► Webhook Notifications & Screenshots
                                         └───► Local JSON Storage
```

---

## 📂 Project Structure

```
UmaClubManagerV2/
├── api/                   # FastAPI backend service
│   ├── app.py             # API entrypoint, routes, and admin auth
│   ├── chart_service.py   # Matplotlib chart generation routines
│   ├── discord_webhook.py # Discord webhook notification formatting & sending
│   ├── fan_counter.py     # Fan calculation, daily quota, & exemption logic
│   ├── member_manager.py  # Member profile & Discord account mapping
│   ├── screenshoot.py     # Headless browser screenshot generator (Playwright/CloakBrowser)
│   └── source_data_api.py # ChronoGenesis API data fetcher
├── discord_bot/           # Discord bot application
│   └── bot.py             # Discord.py bot with slash commands & embedded cards
├── frontend/              # Flask web management interface
│   ├── app.py             # Flask application & routes
│   ├── static/            # Static web assets (CSS/JS)
│   └── templates/         # HTML templates
├── data/                  # Data directory
├── Screenshots/           # Automated report screenshots output directory
├── auto_report.sh         # Shell script for CRON / scheduled reporting
├── project.toml           # Project FastAPI setup & entrypoint configuration
└── requirements.txt       # Python dependencies
```

---

## 📋 Requirements & Dependencies

- If you running on a **VPS**: `1GB Memory`
- **Python**: `3.10+`
- **Dependencies**: see `requirements.txt`

---

## ⚙️ Configuration & Environment Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/MinkuruDev/UmaClubManagerV2.git
   cd UmaClubManagerV2
   ```

2. **Create and Activate Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   For Windows (powershell):
   ```powershell
   python3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If you are using PowerShell and get an error saying *script execution is disabled on this system*, try:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Setup Environment Variables**:
   Create a `.env` file in the root directory (refer to `.env.example`):
   - `DISCORD_WEBHOOK`: In the Discord channel you want to send daily fan report, create a webhook and copy webhook link
   - `DISCORD_TOKEN`: Go to [Discord developer application](https://discord.com/developers/applications) create your bot and get token
   - `CLUB_ID`: Your club ID
   - `CHRONO_GENESIS_TOKEN`: See the announcement in [ChronoGenesis](https://chronogenesis.net/) website and contact ChronoGenesis dev team for your club token
   - `ADMIN_TOKEN` and `FLASK_SECRET_KEY`: You can throw random string here. [Generate random base64 string](https://www.convertsimple.com/random-base64-generator/)

---

## 🚀 Running the Application

⚠️**IMPORTANT**: 
For each components, create a `tmux` session or a seperate terminal, then activate python venv for each session

### 1. Start the API Backend
The backend runs on FastAPI (port `3636`):
```bash
cd api
fastapi run app.py --port 3636
```

### 2. Start the Web Dashboard
The Flask frontend runs on port `5000`:
```bash
cd frontend
python3 app.py
```
Access the dashboard in your browser at `http://localhost:5000`. Go to dasboard and click [Sync Data] to fetch data from ChronoGenesis

If you running on VPS, Tunneling port 5000 to your localhost:
```bash
ssh <username>@<server_ip> -L 5000:127.0.0.1:5000 
```

### 3. Start the Discord Bot
Run the Discord bot service:
```bash
cd discord_bot
python bot.py
```

**If a club leader want to using bot command with leader permission, go to web dashboard and link IGL game account with Discord account first**

### 4. Automated Daily Sync & Report Script

⚠️ **This can not run on Windows**

To run an automated data update and send fan reports to Discord:
```bash
chmod +x auto_report.sh
sudo mkdir -p /var/log/uma-club/
sudo chown <username> /var/log/uma-club/ 
crontab -e
```

Put this to crontab file:
```
05 17 * * * /home/<username>/UmaClubManagerV2/auto_report.sh >> /var/log/uma-club/report.log 2>&1
```

⚠️**IMPORTANT**: 
Set report time match your System time. In my case UTC+7, data is updated in 17:00 daily (10:00 for UTC), then you should wait at least 2 minutes for ChronoGenesis to update data

You also can run report script manually (without activating venv):
```bash
./auto_report.sh
```

---

## 🤖 Discord Bot Commands

| Command | Permission | Description |
| :--- | :--- | :--- |
| `/ping` | Everyone | Check bot responsiveness |
| `/profile` | Everyone | Display personal in-game fan stats, club rank, & averages (3d/7d/30d) |
| `/club_ranking_chart` | Everyone | Display monthly club ranking chart |
| `/club_daily_fan_gain_chart` | Everyone | Display 30-day daily fan gain chart for the club |
| `/member_monthy_gain_chart` | Everyone | Display monthly fan gain chart for all members |
| `/member_daily_gain` | Everyone | Compare 30-day daily fan gains with up to 4 other members |
| `/member_cumulative_gain` | Everyone | Compare cumulative monthly fan gains with up to 4 other members |
| `/link_discord` | Leader Only | Link a member's Discord account to their in-game ID |
| `/unlink_discord` | Leader Only | Unlink a Discord account from an in-game ID |
| `/update_username` | Leader Only | Sync Discord usernames across all linked members |
| `/send_fan_report` | Leader Only | Trigger an immediate fan progress report to the configured webhook |

---

## 🛠️ Main API Endpoint

You can find detial about endpoint in `http://localhost:3636/docs`

- **GET `/`** - Service health & version info
- **GET `/members/{member_id}`** - Get detailed profile for a specific member
- **POST `/members/{member_id}`** *(Admin)* - Update or create member data
- **POST `/full_update`** *(Admin)* - Fetch latest circle data from ChronoGenesis and reprocess stats
- **GET `/fan_data/processed`** - Retrieve calculated fan status, requirements, and rankings
- **POST `/fan_data/report_discord`** *(Admin)* - Asynchronously send fan status report & report screenshot to Discord webhook
- **GET `/chart/{chart_type}`** - Render dynamic PNG charts (`club_ranking`, `club_daily_fan_gain`, `member_monthly_fan_gain`, `member_daily_fan_gain`, `member_cumulative_fan_gain`)

---

## 📜 License

This project is open source and available under the [MIT License](LICENSE).

---

## 🛠️ Troubleshooting 

If you have trouble when setup or using, please DM discord `minkuru_`

## 📝 Contributing

Feel free to contribute, There is something i want to do but too lazy:
- Docker compose
- Custom underperform alert setting
- Multi club support
