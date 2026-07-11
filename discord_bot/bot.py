import discord
import os
import aiohttp 
import requests

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

client.run(TOKEN)
