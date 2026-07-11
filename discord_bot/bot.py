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



@client.event
async def on_ready():
    await tree.sync()
    print(f'Logged in as {client.user}')

@tree.command(name="ping", description="Check if the bot is online")
async def ping(ctx: discord.Interaction):
    await ctx.response.defer()
    await ctx.followup.send("Pong!")

@tree.command(name="link_discord", description="Link member Discord account to the in-game profile")
async def link_discord(ctx: discord.Interaction, user: discord.User, ingame_id: str):
    await ctx.response.defer()
    response = api_session.get(f"{api_url}/members/{ingame_id}")
    if response.status_code == 404:
        await ctx.followup.send(f"No member found with in-game ID: {ingame_id}")
        return
    await ctx.followup.send(f"Member found: {response.text}. Linking Discord account {user} to in-game ID {ingame_id}.")
    member_data = response.json()
    member_data['discord_id'] = str(user.id)
    member_data['discord_username'] = str(user)
    update_response = api_session.post(f"{api_url}/members/{ingame_id}", json=member_data)
    if update_response.status_code == 200:
        await ctx.followup.send(f"Successfully linked Discord account {user} to in-game ID {ingame_id}.")
    else:
        await ctx.followup.send(f"Failed to link Discord account {user} to in-game ID {ingame_id}. Error: {update_response.text}")

client.run(TOKEN)
