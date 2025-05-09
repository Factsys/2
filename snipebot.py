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

# Enable intents for bot functionality
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

# Initialize bot
bot = commands.Bot(command_prefix=",", intents=intents)
bot.remove_command('help')  # Remove default help command
sniped_messages = {}  # Store deleted messages

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()  # Sync slash commands with Discord
        print(f"Synced {len(synced)} slash commands!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f"Bot is online as {bot.user}!")
    await bot.change_presence(activity=discord.Game(name="Type /help or ,help for commands"))

# Event to capture deleted messages
@bot.event
async def on_message_delete(message):
    if message.author.bot:  # Ignore bot messages
        return

    # Store the deleted message in the channel's sniped messages list
    if message.channel.id not in sniped_messages:
        sniped_messages[message.channel.id] = []
    
    sniped_messages[message.channel.id].append({
        "content": message.content,
        "author": message.author,
        "attachments": message.attachments,
        "time": message.created_at
    })

    # Keep only the last 10 sniped messages per channel
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
    if channel.id not in sniped_messages or len(sniped_messages[channel.id]) == 0:
        await interaction.response.send_message("No recently deleted messages in this channel.", ephemeral=True)
        return

    snipe = sniped_messages[channel.id][-1]
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.gold()
    )
    embed.add_field(name="**Content:**", value=snipe['content'] if snipe['content'] else "*No text content*", inline=False)
    embed.add_field(name="**Deleted by:**", value=snipe['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)

    # Check for attachments and add them to the embed
    if snipe["attachments"]:
        for attachment in snipe["attachments"]:
            if any(attachment.url.endswith(ext) for ext in ["png", "jpg", "jpeg", "gif", "webp"]):
                embed.set_image(url=attachment.url)
                break

    await interaction.response.send_message(embed=embed)

# Command: ,snipe (Alias: ,s)
@bot.command(aliases=["snipe"])
async def s(ctx, page: int = 1):
    channel_id = ctx.channel.id
    if channel_id not in sniped_messages or len(sniped_messages[channel_id]) == 0:
        embed = discord.Embed(
            title="❌ No Deleted Messages",
            description="There are no recently deleted messages in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Ensure the requested page is within range
    if page < 1 or page > len(sniped_messages[channel_id]):
        embed = discord.Embed(
            title="⚠️ Invalid Page Number",
            description=f"Please provide a valid page number between 1 and {len(sniped_messages[channel_id])}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    # Get the sniped message for the requested page
    snipe = sniped_messages[channel_id][-page]
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.gold()
    )
    embed.add_field(name="**Content:**", value=snipe['content'] if snipe['content'] else "*No text content*", inline=False)
    embed.add_field(name="**Deleted by:**", value=snipe['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"SnipeBot | Page {page} of {len(sniped_messages[channel_id])}")

    # Check for attachments (images, GIFs, or other media) and embed them
    if snipe["attachments"]:
        for attachment in snipe["attachments"]:
            if any(attachment.url.endswith(ext) for ext in ["png", "jpg", "jpeg", "gif", "webp"]):
                embed.set_image(url=attachment.url)
                break
            elif attachment.url:
                embed.add_field(name="**Attachment:**", value=f"[View Attachment]({attachment.url})", inline=False)

    await ctx.send(embed=embed)

# Command: ,mess (DM a user)
@bot.command()
@commands.has_permissions(manage_guild=True)
async def mess(ctx, member: discord.Member, *, message):
    try:
        await member.send(message)
        embed = discord.Embed(
            title="✅ Message Sent",
            description=f"Your message was successfully sent to {member.mention}.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Message Failed",
            description="Unable to send the message. The user might have DMs disabled.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# Command: ,help
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="❓ SnipeBot Help",
        description="Here are the available commands for SnipeBot:",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="`,snipe` or `,s [page]`",
        value="Displays recently deleted messages. Use pages to navigate through multiple deleted messages.\nExample: `,s 1`, `,s 2`",
        inline=False
    )
    embed.add_field(
        name="`,mess @User [message]`",
        value="DMs the specified message to the user. Requires the 'Manage Server' permission.\nExample: `,mess @User Please follow the rules.`",
        inline=False
    )
    embed.add_field(
        name="`,help`",
        value="Displays this help message.",
        inline=False
    )
    embed.set_footer(text="SnipeBot | Werzzzy Discord Bot")
    await ctx.send(embed=embed)

# Run Flask and the bot
if __name__ == "__main__":
    run_flask()  # Start the Flask server for Render
    bot.run(os.getenv("DISCORD_TOKEN"))  # Use the token from environment variables
