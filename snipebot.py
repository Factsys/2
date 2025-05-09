import discord
from discord.ext import commands
from discord import app_commands
import os
from flask import Flask
from threading import Thread

# Flask app to keep the bot running on Render
app = Flask('')

@app.route('/')
def home():
    return "SnipeBot is running!"

def run_flask():
    port = os.getenv("PORT", 8080)
    server = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": port}, daemon=True)
    server.start()

# Enable intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

# Initialize bot
bot = commands.Bot(command_prefix=",", intents=intents)
bot.remove_command('help')
sniped_messages = {}

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f"Bot is online as {bot.user}!")
    await bot.change_presence(activity=discord.Game(name="Type /help or ,help for commands"))

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    if message.channel.id not in sniped_messages:
        sniped_messages[message.channel.id] = []
    
    sniped_messages[message.channel.id].append({
        "content": message.content,
        "author": message.author,
        "attachments": message.attachments,
        "time": message.created_at
    })

    if len(sniped_messages[message.channel.id]) > 10:
        sniped_messages[message.channel.id].pop(0)

# Slash Command: /ping
@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! Latency: {round(bot.latency * 1000)}ms")

# Slash Command: /snipe
@bot.tree.command(name="snipe", description="Displays the most recently deleted message")
async def snipe_slash(interaction: discord.Interaction):
    channel = interaction.channel
    if channel.id not in sniped_messages or not sniped_messages[channel.id]:
        await interaction.response.send_message("No recently deleted messages in this channel.", ephemeral=True)
        return

    snipe = sniped_messages[channel.id][-1]
    embed = discord.Embed(title="📜 Sniped Message", color=discord.Color.gold())
    embed.add_field(name="**Content:**", value=snipe['content'] or "*No text content*", inline=False)
    embed.add_field(name="**Deleted by:**", value=snipe['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)

    if snipe["attachments"]:
        for attachment in snipe["attachments"]:
            url = attachment.url
            if url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                embed.set_image(url=url)
                break
            elif url:
                embed.add_field(name="**Attachment:**", value=f"[View Attachment]({url})", inline=False)

    await interaction.response.send_message(embed=embed)

# Slash Command: /mess (ephemeral)
@bot.tree.command(name="mess", description="DM a user with a message (admin only)")
@app_commands.describe(member="User to DM", message="The message to send")
@app_commands.checks.has_permissions(manage_guild=True)
async def mess(interaction: discord.Interaction, member: discord.Member, message: str):
    try:
        await member.send(message)
        embed = discord.Embed(
            title="✅ Message Sent",
            description=f"Message sent to {member.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Failed to Send",
            description="Could not send DM. User may have DMs disabled.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Slash Command: /maintainer (public)
@bot.tree.command(name="maintainer", description="Shows who maintains the bot")
async def maintainer(interaction: discord.Interaction):
    embed = discord.Embed(
        title="👤 Bot Maintainer",
        description="This bot is maintained and developed by Werzzzy.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="SnipeBot by Werzzzy")
    await interaction.response.send_message(embed=embed)

# Text Command: ,snipe / ,s
@bot.command(aliases=["snipe"])
async def s(ctx, page: int = 1):
    channel_id = ctx.channel.id
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        embed = discord.Embed(
            title="❌ No Deleted Messages",
            description="There are no recently deleted messages in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if page < 1 or page > len(sniped_messages[channel_id]):
        embed = discord.Embed(
            title="⚠️ Invalid Page Number",
            description=f"Page must be between 1 and {len(sniped_messages[channel_id])}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    snipe = sniped_messages[channel_id][-page]
    embed = discord.Embed(title="📜 Sniped Message", color=discord.Color.gold())
    embed.add_field(name="**Content:**", value=snipe['content'] or "*No text content*", inline=False)
    embed.add_field(name="**Deleted by:**", value=snipe['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"SnipeBot | Page {page} of {len(sniped_messages[channel_id])}")

    if snipe["attachments"]:
        for attachment in snipe["attachments"]:
            url = attachment.url
            if url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                embed.set_image(url=url)
                break
            elif url:
                embed.add_field(name="**Attachment:**", value=f"[View Attachment]({url})", inline=False)

    await ctx.send(embed=embed)

# Text Command: ,mess
@bot.command()
@commands.has_permissions(manage_guild=True)
async def mess(ctx, member: discord.Member, *, message):
    try:
        await member.send(message)
        embed = discord.Embed(
            title="✅ Message Sent",
            description=f"Your message was sent to {member.mention}.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Failed to Send",
            description="Could not send DM. User may have DMs disabled.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# Text Command: ,help
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="❓ SnipeBot Help",
        description="Available commands:",
        color=discord.Color.blurple()
    )
    embed.add_field(name="`,snipe` or `,s [page]`", value="Show recently deleted messages.", inline=False)
    embed.add_field(name="`,mess @user [message]`", value="Send a DM (admin only).", inline=False)
    embed.add_field(name="`,help`", value="Show this help message.", inline=False)
    embed.set_footer(text="SnipeBot by Werzzzy")
    await ctx.send(embed=embed)

# Start everything
if __name__ == "__main__":
    run_flask()
    bot.run(os.getenv("DISCORD_TOKEN"))
