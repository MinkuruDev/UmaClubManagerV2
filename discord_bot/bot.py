import discord
import os
import aiohttp 
import requests
import io

from discord import app_commands
from dotenv import load_dotenv
load_dotenv()

intents = discord.Intents.default()
intents.members = True  # Enable the members intent
client = discord.Client(intents=intents)
TOKEN = os.getenv("DISCORD_TOKEN")
tree = app_commands.CommandTree(client)

api_session = requests.Session()
api_url = "http://localhost:3636"
admin_bearer_token = os.getenv("ADMIN_TOKEN")
api_session.headers.update({
    "Authorization": f"Bearer {admin_bearer_token}",
})

def is_leader(discord_id: str) -> bool:
    try:
        response = api_session.get(f"{api_url}/members/discord/{discord_id}")
        if response.status_code == 200:
            member_data = response.json()
            return member_data.get("leader", False)
        else:
            print(f"Failed to fetch member data for Discord ID {discord_id}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Error while checking leader status for Discord ID {discord_id}: {e}")
        return False

@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user}')

@tree.command(name="ping", description="Check if the bot is online")
async def ping(ctx: discord.Interaction):
    await ctx.response.defer()
    await ctx.followup.send("Pong!")

class LinkConfirmView(discord.ui.View):
    def __init__(self, expected_user_id: int, timeout: float = 60.0):
        super().__init__(timeout=timeout)
        self.expected_user_id = expected_user_id
        self.confirmed = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.expected_user_id:
            await interaction.response.send_message("You cannot interact with this button.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.confirmed = False
        self.stop()
        await interaction.response.defer()

@tree.command(name="link_discord", description="Link member Discord account to the in-game profile")
async def link_discord(ctx: discord.Interaction, user: discord.User, ingame_id: str):
    await ctx.response.defer(ephemeral=True)
    # check if leader
    if not is_leader(str(ctx.user.id)):
        await ctx.followup.send("You are not authorized to link Discord accounts. Only leaders can perform this action.", ephemeral=True)
        return
    
    try:
        response = api_session.get(f"{api_url}/members/{ingame_id}")
    except Exception as e:
        await ctx.followup.send(f"Error connecting to backend API: {e}", ephemeral=True)
        return

    if response.status_code == 404:
        prompt_text = f"No member found with in-game ID: {ingame_id}. Would you like to link Discord account {user} anyway?"
        member_data = {
            "ingame_id": ingame_id,
            "ingame_name": None,
            "discord_id": str(user.id),
            "discord_username": str(user)
        }
    elif response.status_code == 200:
        member_data = response.json()
        ingame_name = member_data.get('ingame_name', None)
        prompt_text = f"Member found: {ingame_name}. Would you like to link Discord account {user} to in-game ID {ingame_id}?"
        member_data['discord_id'] = str(user.id)
        member_data['discord_username'] = str(user)
    else:
        await ctx.followup.send(f"Failed to fetch member details from backend (HTTP {response.status_code}): {response.text}", ephemeral=True)
        return

    view = LinkConfirmView(expected_user_id=ctx.user.id)
    confirm_msg = await ctx.followup.send(content=prompt_text, view=view, ephemeral=True)
    
    await view.wait()
    
    if view.confirmed is None:
        await confirm_msg.edit(content="Linking process timed out.", view=None)
    elif view.confirmed is False:
        await confirm_msg.edit(content="Linking process cancelled.", view=None)
    else:
        await confirm_msg.edit(content="Linking confirmed. Processing...", view=None)
        try:
            update_response = api_session.post(f"{api_url}/members/{ingame_id}", json=member_data)
            if update_response.status_code == 200:
                await confirm_msg.edit(content=f"Successfully linked Discord account {user.mention} to in-game ID {ingame_id}.", view=None)
            else:
                await confirm_msg.edit(content=f"Failed to link Discord account {user.mention} to in-game ID {ingame_id}. Error: {update_response.text}", view=None)
        except Exception as e:
            await confirm_msg.edit(content=f"Error occurred while updating link: {e}", view=None)

@tree.command(name="unlink_discord", description="Unlink a Discord account from an in-game profile")
async def unlink_discord(ctx: discord.Interaction, user: discord.User):
    await ctx.response.defer(ephemeral=True)

    if not is_leader(str(ctx.user.id)):
        await ctx.followup.send("You are not authorized to unlink Discord accounts. Only leaders can perform this action.", ephemeral=True)
        return

    # Check that the user is actually linked
    try:
        response = api_session.get(f"{api_url}/members/discord/{user.id}")
    except Exception as e:
        await ctx.followup.send(f"Error connecting to backend API: {e}", ephemeral=True)
        return

    if response.status_code == 404:
        await ctx.followup.send(f"{user.name} is not linked to any in-game profile.", ephemeral=True)
        return
    elif response.status_code != 200:
        await ctx.followup.send(f"Failed to fetch member info (HTTP {response.status_code}): {response.text}", ephemeral=True)
        return

    member = response.json()
    ingame_name = member.get("ingame_name") or "Unknown"
    ingame_id = member.get("ingame_id") or "Unknown"

    view = LinkConfirmView(expected_user_id=ctx.user.id)
    confirm_msg = await ctx.followup.send(
        content=f"Are you sure you want to unlink {user} from in-game profile **{ingame_name}** (ID: {ingame_id})?",
        view=view,
        ephemeral=True
    )
    await view.wait()

    if view.confirmed is None:
        await confirm_msg.edit(content="Unlink process timed out.", view=None)
    elif view.confirmed is False:
        await confirm_msg.edit(content="Unlink process cancelled.", view=None)
    else:
        await confirm_msg.edit(content="Unlinking... Please wait.", view=None)
        try:
            delete_response = api_session.delete(f"{api_url}/members/discord/{user.id}")
            if delete_response.status_code == 200:
                await confirm_msg.edit(content="Unlink confirmed.", view=None)
                await confirm_msg.edit(f"Successfully unlinked {user.mention} from in-game profile **{ingame_name}** (ID: `{ingame_id}`).")
            else:
                await confirm_msg.edit(content=f"Failed to unlink (HTTP {delete_response.status_code}): {delete_response.text}", view=None)
        except Exception as e:
            await confirm_msg.edit(content=f"Error occurred while unlinking: {e}", view=None)

@tree.command(name="update_username", description="Update the Discord username for all linked member")
async def update_username(ctx: discord.Interaction):
    await ctx.response.defer(ephemeral=True)
    if not is_leader(str(ctx.user.id)):
        await ctx.followup.send("You are not authorized to update usernames. Only leaders can perform this action.", ephemeral=True)
        return

    api_session.post(f"{api_url}/full_update")
    try:
        response = api_session.get(f"{api_url}/members")
    except Exception as e:
        await ctx.followup.send(f"Error connecting to backend API: {e}", ephemeral=True)
        return

    if response.status_code != 200:
        await ctx.followup.send(f"Failed to fetch members from backend (HTTP {response.status_code}): {response.text}", ephemeral=True)
        return

    members = response.json()
    del members["discord_link"]
    del members["current_member"]
    
    updated_count = 0
    for member in members.values():
        discord_id = member.get("discord_id")
        if discord_id:
            try:
                discord_user = ctx.guild.get_member(int(discord_id))
                if discord_user:
                    member["discord_username"] = str(discord_user)
                    update_response = api_session.post(f"{api_url}/members/{member['ingame_id']}", json=member)
                    if update_response.status_code == 200:
                        updated_count += 1
            except Exception as e:
                print(f"Error fetching Discord user with ID {discord_id}: {e}")

    await ctx.followup.send(f"Updated Discord usernames for {updated_count} members.", ephemeral=True)

@tree.command(name="profile", description="View profile and fan progress")
async def profile(ctx: discord.Interaction):
    await ctx.response.defer()

    # Fetch member info by Discord ID
    response = api_session.get(f"{api_url}/members/discord/{ctx.user.id}")
    if response.status_code != 200:
        await ctx.followup.send(f"No linked in-game profile found. Please ask leader to link your account.", ephemeral=True)
        return
    member = response.json()

    # Fetch fan data for the member
    ingame_id = member.get("ingame_id") 
    response = api_session.get(f"{api_url}/fan_data/{ingame_id}")
    if response.status_code != 200:
        await ctx.followup.send(f"Failed to fetch fan data (HTTP {response.status_code}): {response.text}", ephemeral=True)
        return
    fan_result = response.json()

    # Fetch total fan data for ranking
    response = api_session.get(f"{api_url}/fan_data/total")
    if response.status_code != 200:
        await ctx.followup.send(f"Failed to fetch fan data (HTTP {response.status_code}): {response.text}", ephemeral=True)
        return
    total = response.json()["fan_data"]
    mem_fan = total[ingame_id]
    rank = 0
    for fan in total.values():
        if mem_fan < fan:
            rank += 1

    daily_data = fan_result.get("fan_data", [])   # sorted newest to oldest
    monthly_fans = fan_result.get("monthly_fans", 0)
    ingame_name = member.get("ingame_name") or "Unknown"
    club_name = api_session.get(f"{api_url}/raw?fields=club,0,name").json()

    embed = discord.Embed(
        title=f"📊 Profile: {ingame_name}",
        color=discord.Color.from_rgb(255, 182, 193),
    )
    embed.set_thumbnail(url=ctx.user.display_avatar.url)
    embed.set_footer(text=f"Discord: {ctx.user}", icon_url=ctx.user.display_avatar.url)

    # Format a fan number: divide by 1M, round to 2 dp, append M
    def fmt_fans(n: float) -> str:
        return f"{n / 1_000_000:.2f}M"

    # Club section
    embed.add_field(
        name=f"🥕 Club: {club_name}",
        value=""
    )

    # Latest day fan
    if daily_data:
        latest = daily_data[0]
        embed.add_field(
            name="📅 Latest Day",
            value=f"**{fmt_fans(latest['fan'])}** fans (_{latest['date']}_)",
            inline=False
        )
    else:
        embed.add_field(name="📅 Latest Day", value="No data available", inline=False)

    # embed.add_field(name="\u200b", value="**── This Month ──**", inline=False)
    embed.add_field(name="📈 Monthly Total", value=f"**{fmt_fans(monthly_fans)}** fans\nRanking in club: **#{rank}**", inline=False)

    # Period totals and averages
    def period_stats(n: int):
        """Return (total, average) for the most recent n days, or None if not enough data."""
        if len(daily_data) < n:
            return None
        slice_ = daily_data[:n]
        total = sum(d["fan"] for d in slice_)
        avg = total / n
        return total, avg

    embed.add_field(name="\u200b", value="**── Fan Periods ──**", inline=False)

    for days, label in [(3, "3 Days"), (7, "7 Days"), (30, "30 Days")]:
        result = period_stats(days)
        if result is not None:
            total, avg = result
            embed.add_field(
                name=f"🗓️ Last {label}",
                value=f"Total: **{fmt_fans(total)}**\nAvg/day: **{fmt_fans(avg)}**",
                inline=True
            )
        else:
            embed.add_field(
                name=f"🗓️ Last {label}",
                value=f"_Not enough data ({len(daily_data)}/{days} days)_",
                inline=True
            )

    await ctx.followup.send(embed=embed)

@tree.command(name="club_ranking_chart", description="Show club ranking chart in this month")
async def club_ranking_chart(ctx: discord.Interaction):
    await ctx.response.defer()
    response = api_session.get(f"{api_url}/chart/club_ranking")
    image_stream = io.BytesIO(response.content)
    image_file = discord.File(fp=image_stream, filename="club_ranking.png")
    await ctx.followup.send(file=image_file)

@tree.command(name="club_daily_fan_gain_chart", description="Show club daily fan gain chart in last 30 days")
async def club_daily_fan(ctx: discord.Interaction):
    await ctx.response.defer()
    response = api_session.get(f"{api_url}/chart/club_daily_fan_gain")
    image_stream = io.BytesIO(response.content)
    image_file = discord.File(fp=image_stream, filename="club_daily_fan_gain.png")
    await ctx.followup.send(file=image_file)
    
@tree.command(name="member_monthy_gain_chart", description="Show all member total fan gain in this month")
async def club_daily_fan(ctx: discord.Interaction):
    await ctx.response.defer()
    response = api_session.get(f"{api_url}/chart/member_monthly_fan_gain")
    image_stream = io.BytesIO(response.content)
    image_file = discord.File(fp=image_stream, filename="member_monthly_fan_gain.png")
    await ctx.followup.send(file=image_file)

@tree.command(name="member_daily_gain", description="Show daily fan gain of last 30 days with other member")
@app_commands.describe(
    mem1 = "Other member to compare with, up to 4 other members",
    mem2 = "Other member to compare with, up to 4 other members",
    mem3 = "Other member to compare with, up to 4 other members",
    mem4 = "Other member to compare with, up to 4 other members"
)
async def member_daily_gain(
    ctx: discord.Interaction,
    mem1: discord.Member = None,
    mem2: discord.Member = None,
    mem3: discord.Member = None,
    mem4: discord.Member = None
):
    await ctx.response.defer()
    selected_member = [mem for mem in [mem1, mem2, mem3, mem4] if mem is not None]
    selected_member.append(ctx.user)
    ids = ",".join([str(member.id) for member in selected_member])
    response = api_session.get(f"{api_url}/chart/member_daily_fan_gain?members={ids}")
    image_stream = io.BytesIO(response.content)
    image_file = discord.File(fp=image_stream, filename="member_daily_fan_gain.png")
    await ctx.followup.send(file=image_file)

@tree.command(name="member_cumulative_gain", description="Show cumulative fan gain this month with other member")
@app_commands.describe(
    mem1 = "Other member to compare with, up to 4 other members",
    mem2 = "Other member to compare with, up to 4 other members",
    mem3 = "Other member to compare with, up to 4 other members",
    mem4 = "Other member to compare with, up to 4 other members"
)
async def member_cumulative_gain(
    ctx: discord.Interaction,
    mem1: discord.Member = None,
    mem2: discord.Member = None,
    mem3: discord.Member = None,
    mem4: discord.Member = None
):
    await ctx.response.defer()
    selected_member = [mem for mem in [mem1, mem2, mem3, mem4] if mem is not None]
    selected_member.append(ctx.user)
    ids = ",".join([str(member.id) for member in selected_member])
    response = api_session.get(f"{api_url}/chart/member_cumulative_fan_gain?members={ids}")
    image_stream = io.BytesIO(response.content)
    image_file = discord.File(fp=image_stream, filename="member_cumulative_fan_gain.png")
    await ctx.followup.send(file=image_file)

client.run(TOKEN)
