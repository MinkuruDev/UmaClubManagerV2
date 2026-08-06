import pandas as pd
import matplotlib.pyplot as plt
import app as api
import io

from matplotlib.ticker import FuncFormatter
from datetime import timedelta

def fan_formatter(x, _):
    return f"{x/1_000_000:.0f}M"

def to_png_byte() -> bytes:
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_bytes = buf.getvalue()
    plt.close()
    return image_bytes

def club_ranking(**_):
    data = api.get_fan_data("club_ranking", 69)["fan_data"]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    club_name = api.get_raw_data("club,0,name")

    if not df.empty:
        latest_period = df["date"].max().to_period("M")
        df = df[df["date"].dt.to_period("M") == latest_period]

    df.plot(
        x="date",
        y="rank",
        kind="line",
        figsize=(10, 7),
        title=f"Club Ranking: {club_name}"
    )
    plt.gca().invert_yaxis()
    return to_png_byte()

def club_daily_fan_gain(**_):
    data = api.get_fan_data("club_ranking")["fan_data"]
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    club_name = api.get_raw_data("club,0,name")
    
    df.plot(
        x="date",
        y="fan",
        kind="line",
        figsize=(10, 7),
        title=f"{club_name} Daily Fan Gain"
    )

    plt.gca().yaxis.set_major_formatter(
        FuncFormatter(fan_formatter)
    )
    plt.ylabel("Fans")
    plt.tight_layout()
    return to_png_byte()

def _get_member_fan_dataframe(kwargs):
    fan_data = api.get_all_fan_data()
    members_data = api.get_members()
    raw_members = kwargs.get("members")

    # Parse members parameter (list, comma-separated string, single string, or None)
    input_members = []
    if raw_members:
        if isinstance(raw_members, str):
            input_members = [m.strip() for m in raw_members.split(",") if m.strip()]
        elif isinstance(raw_members, list):
            for m in raw_members:
                if isinstance(m, str):
                    input_members.extend([x.strip() for x in m.split(",") if x.strip()])
                elif m is not None:
                    input_members.append(str(m).strip())

    # Map input member identifiers (discord_id -> ingame_id)
    discord_link = members_data.get("discord_link", {})
    resolved_ids = []
    for m_id in input_members:
        resolved_id = discord_link.get(m_id, m_id)
        if resolved_id not in resolved_ids:
            resolved_ids.append(resolved_id)

    # Ranking by sorting total from fan_data (ignore 'club_ranking' and former members)
    try:
        current_members = api.get_raw_data("club,0,circle_user_array")
        current_ids = set(str(m) for m in current_members) if isinstance(current_members, list) else None
    except Exception:
        current_ids = None

    total_dict = api.get_fan_data("total")["fan_data"]
    if current_ids is not None:
        member_totals = {k: v for k, v in total_dict.items() if k != "club_ranking" and str(k) in current_ids}
    else:
        member_totals = {k: v for k, v in total_dict.items() if k != "club_ranking"}
    ranked_ids = sorted(member_totals.keys(), key=lambda k: member_totals[k], reverse=True)

    # Determine selected members based on rules:
    # 1. No members: grab top 5 in ranking
    # 2. 1 member: get 4 other closest to their rank (total 5)
    # 3. 2 or more: only make chart for those members
    if len(resolved_ids) == 0:
        selected_ids = ranked_ids[:5]
    elif len(resolved_ids) == 1:
        target_id = resolved_ids[0]
        if target_id in ranked_ids:
            target_idx = ranked_ids.index(target_id)
            other_indices = [i for i in range(len(ranked_ids)) if i != target_idx]
            closest_indices = sorted(other_indices, key=lambda i: (abs(i - target_idx), i))[:4]
            selected_indices = sorted([target_idx] + closest_indices)
            selected_ids = [ranked_ids[i] for i in selected_indices]
        else:
            selected_ids = [target_id] + [r for r in ranked_ids if r != target_id][:4]
    else:
        selected_ids = [m for m in resolved_ids if m in fan_data or m in member_totals]

    if not selected_ids:
        return None

    # Map ingame_id -> ingame_name
    name_count = {}
    for m_id in selected_ids:
        member_obj = members_data.get(m_id)
        name = member_obj.get("ingame_name", m_id) if isinstance(member_obj, dict) else m_id
        name_count[name] = name_count.get(name, 0) + 1

    labels = {}
    for m_id in selected_ids:
        member_obj = members_data.get(m_id)
        name = member_obj.get("ingame_name", m_id) if isinstance(member_obj, dict) else m_id
        if name_count[name] > 1:
            labels[m_id] = f"{name} ({m_id})"
        else:
            labels[m_id] = name

    # Build date-wise data for plotting
    date_data = {}
    for m_id in selected_ids:
        member_records = fan_data.get(m_id, [])
        label = labels[m_id]
        if isinstance(member_records, list):
            for rec in member_records:
                date = rec.get("date")
                fan = rec.get("fan")
                if date and fan is not None:
                    if date not in date_data:
                        date_data[date] = {}
                    date_data[date][label] = fan

    if not date_data:
        return None

    df = pd.DataFrame.from_dict(date_data, orient="index")
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    column_order = [labels[m_id] for m_id in selected_ids if labels[m_id] in df.columns]
    df = df[column_order]
    return df

def member_daily_fan_gain(**kwargs):
    df = _get_member_fan_dataframe(kwargs)
    club_name = api.get_raw_data("club,0,name")

    if df is None or df.empty:
        plt.figure(figsize=(10, 5))
        plt.title(f"{club_name} Member Daily Fan Gain")
        plt.tight_layout()
        return to_png_byte()

    # Ensure datetime index
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)

    # Keep only the last 30 days
    last_date = df.index.max()
    df = df[df.index >= last_date - timedelta(days=29)]

    df.plot(
        kind="line",
        figsize=(10, 5),
        title=f"{club_name} Member Daily Fan Gain"
    )
    plt.gca().yaxis.set_major_formatter(
        FuncFormatter(fan_formatter)
    )
    plt.ylabel("Fans")
    plt.tight_layout()
    return to_png_byte()

def member_cumulative_fan_gain(**kwargs):
    df = _get_member_fan_dataframe(kwargs)
    club_name = api.get_raw_data("club,0,name")
    
    if df is None or df.empty:
        plt.figure(figsize=(10, 7))
        plt.title(f"{club_name} Member Cumulative Fan Count")
        plt.tight_layout()
        return to_png_byte()

    latest_period = df.index.max().to_period("M")
    df = df[df.index.to_period("M") == latest_period]

    df_cum = df.fillna(0).cumsum()

    df_cum.plot(
        kind="line",
        figsize=(10, 7),
        title=f"{club_name} Member Cumulative Fan Count"
    )
    plt.gca().yaxis.set_major_formatter(
        FuncFormatter(fan_formatter)
    )
    plt.ylabel("Fans")
    plt.tight_layout()
    return to_png_byte()

def member_monthly_fan_gain(**_):
    members_data = api.get_members()
    total_dict = api.get_fan_data("total")["fan_data"]
    club_name = api.get_raw_data("club,0,name")

    try:
        current_members = api.get_raw_data("club,0,circle_user_array")
        current_ids = set(str(m) for m in current_members) if isinstance(current_members, list) else None
    except Exception:
        current_ids = None

    if current_ids is not None:
        member_totals = {k: v for k, v in total_dict.items() if k != "club_ranking" and str(k) in current_ids}
    else:
        member_totals = {k: v for k, v in total_dict.items() if k != "club_ranking"}

    if not member_totals:
        plt.figure(figsize=(10, 6))
        plt.title("Monthly Member Fan Gain")
        plt.tight_layout()
        return to_png_byte()

    # Map ingame_id -> ingame_name with disambiguation if duplicate
    name_count = {}
    for m_id in member_totals.keys():
        member_obj = members_data.get(m_id)
        name = member_obj.get("ingame_name", m_id) if isinstance(member_obj, dict) else m_id
        name_count[name] = name_count.get(name, 0) + 1

    labels = {}
    for m_id in member_totals.keys():
        member_obj = members_data.get(m_id)
        name = member_obj.get("ingame_name", m_id) if isinstance(member_obj, dict) else m_id
        if name_count[name] > 1:
            labels[m_id] = f"{name} ({m_id})"
        else:
            labels[m_id] = name

    # Series sorted ascending so highest fan count appears at top of barh
    plot_data = {labels[m_id]: fans for m_id, fans in member_totals.items()}
    s = pd.Series(plot_data).sort_values(ascending=True)

    fig, ax = plt.subplots(figsize=(10, max(6, len(s) * 0.35)))
    s.plot(
        kind="barh",
        ax=ax,
        title=f"Monthly Member Fan Gain in {club_name}"
    )
    ax.xaxis.set_major_formatter(
        FuncFormatter(fan_formatter)
    )
    plt.xlabel("Fans")
    plt.tight_layout()
    return to_png_byte()

CHART_MAPPING = {
    "club_ranking": club_ranking,
    "club_daily_fan_gain": club_daily_fan_gain,
    "member_daily_fan_gain": member_daily_fan_gain,
    "member_cumulative_fan_gain": member_cumulative_fan_gain,
    "member_monthly_fan_gain": member_monthly_fan_gain,
}

