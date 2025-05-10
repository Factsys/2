import discord
from discord.ext import commands
from discord import app_commands
import os
from flask import Flask
from threading import Thread
import re

# Flask app to keep the bot running on Render
app = Flask('')

@app.route('/')
def home():
    return "SnipeBot is running!"

def run_flask():
    port = int(os.getenv("PORT", 8080))
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

# Helper function to handle media URLs
def get_media_url(content, attachments):
    # Check for tenor links
    tenor_match = re.search(r'https?://(?:www\.)?tenor\.com/view/[^\s]+', content)
    if tenor_match:
        return tenor_match.group(0)
    
    # Check for Twitter/X GIF links
    twitter_match = re.search(r'https?://(?:www\.)?twitter\.com/[^\s]+\.gif', content)
    if twitter_match:
        return twitter_match.group(0)
    
    # Check for discord attachment links with .gif extension
    gif_match = re.search(r'https?://(?:cdn|media)\.discordapp\.(?:com|net)/[^\s]+\.gif[^\s]*', content)
    if gif_match:
        return gif_match.group(0)
    
    # Check for direct GIF links
    direct_gif_match = re.search(r'https?://[^\s]+\.gif[^\s]*', content)
    if direct_gif_match:
        return direct_gif_match.group(0)
    
    # If there are attachments, return the URL of the first one
    if attachments:
        return attachments[0].url
    
    return None

# Custom check that allows administrators and owners to bypass permission requirements
def has_permission_or_is_admin():
    async def predicate(ctx):
        # Check if user is guild owner
        if ctx.guild and ctx.author.id == ctx.guild.owner_id:
            return True
        # Check if user is administrator
        if ctx.guild and ctx.author.guild_permissions.administrator:
            return True
        # Otherwise check for the specific permission in the command
        return await commands.has_permissions().predicate(ctx)
    return commands.check(predicate)

# Custom check for slash commands that allows administrators and owners to bypass
def check_admin_or_permissions(**perms):
    async def predicate(interaction: discord.Interaction):
        # Check if user is guild owner
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            return True
        # Check if user is administrator
        if interaction.guild and interaction.user.guild_permissions.administrator:
            return True
        # Otherwise check for the specific permission
        for perm, value in perms.items():
            if value and not getattr(interaction.user.guild_permissions, perm):
                raise app_commands.MissingPermissions([perm])
        return True
    return app_commands.check(predicate)

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

@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! Latency: {round(bot.latency * 1000)}ms")

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

    # Handle attachments and media links
    media_url = get_media_url(snipe['content'], snipe['attachments'])
    
    if media_url:
        embed.set_image(url=media_url)
    elif snipe["attachments"]:
        for attachment in snipe["attachments"]:
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.url)
                break
            if attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                embed.set_image(url=attachment.url)
                break

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mess", description="DM a user with a message (requires timeout members permission)")
@app_commands.describe(member="User to DM", message="The message to send")
@check_admin_or_permissions(moderate_members=True)  # Admin/owner bypass check
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

@bot.tree.command(name="reset", description="Reset all sniped messages (requires administrator permission)")
@check_admin_or_permissions(administrator=True)  # Admin/owner bypass check
async def reset_slash(interaction: discord.Interaction):
    channel_id = interaction.channel.id
    if channel_id in sniped_messages:
        sniped_messages[channel_id] = []
        embed = discord.Embed(
            title="🗑️ Snipe Reset",
            description="All sniped messages in this channel have been cleared.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="ℹ️ Nothing to Reset",
            description="There were no sniped messages to clear.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rename", description="Change a user's nickname (requires manage nicknames permission)")
@app_commands.describe(member="User to rename", nickname="New nickname")
@check_admin_or_permissions(manage_nicknames=True)  # Admin/owner bypass check
async def rename_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname)
        embed = discord.Embed(
            title="✅ Nickname Changed",
            description=f"Changed {member.mention}'s nickname from '{old_nick}' to '{nickname}'.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Failed",
            description="I don't have permission to change that user's nickname.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException as e:
        embed = discord.Embed(
            title="❌ Error",
            description=f"Failed to change nickname: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="maintainer", description="Shows who maintains the bot")
async def maintainer(interaction: discord.Interaction):
    embed = discord.Embed(
        title="👤 Bot Maintainer",
        description="This bot is maintained and developed by Werzzzy.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="SnipeBot by Werzzzy")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Show bot commands")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="❓ SnipeBot Help",
        description="Available commands:",
        color=discord.Color.blurple()
    )
    embed.add_field(name="`,snipe` or `,s [page]`", value="Show recently deleted messages.", inline=False)
    embed.add_field(name="`,mess @user [message]`", value="Send a DM (requires timeout members permission).", inline=False)
    embed.add_field(name="`,re @user [nickname]`", value="Change a user's nickname (requires manage nicknames permission).", inline=False)
    embed.add_field(name="`,reset`", value="Reset all sniped messages (requires administrator permission).", inline=False)
    embed.add_field(name="`,help` or `/help`", value="Show this help message.", inline=False)
    embed.set_footer(text="SnipeBot by Werzzzy | Server owner and administrators bypass all permission requirements")
    await interaction.response.send_message(embed=embed)

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

    # Handle attachments and media links
    media_url = get_media_url(snipe['content'], snipe['attachments'])
    
    if media_url:
        embed.set_image(url=media_url)
    elif snipe["attachments"]:
        for attachment in snipe["attachments"]:
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.url)
                break
            if attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                embed.set_image(url=attachment.url)
                break

    await ctx.send(embed=embed)

@bot.command()
@has_permission_or_is_admin()  # Admin/owner bypass
@commands.has_permissions(moderate_members=True)
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

@bot.command()
@has_permission_or_is_admin()  # Admin/owner bypass
@commands.has_permissions(administrator=True)
async def reset(ctx):
    channel_id = ctx.channel.id
    if channel_id in sniped_messages:
        sniped_messages[channel_id] = []
        embed = discord.Embed(
            title="🗑️ Snipe Reset",
            description="All sniped messages in this channel have been cleared.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="ℹ️ Nothing to Reset",
            description="There were no sniped messages to clear.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

@bot.command(aliases=["re"])
@has_permission_or_is_admin()  # Admin/owner bypass
@commands.has_permissions(manage_nicknames=True)
async def rename(ctx, member: discord.Member, *, nickname):
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname)
        embed = discord.Embed(
            title="✅ Nickname Changed",
            description=f"Changed {member.mention}'s nickname from '{old_nick}' to '{nickname}'.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Failed",
            description="I don't have permission to change that user's nickname.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except discord.HTTPException as e:
        embed = discord.Embed(
            title="❌ Error",
            description=f"Failed to change nickname: {str(e)}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="❓ SnipeBot Help",
        description="Available commands:",
        color=discord.Color.blurple()
    )
    embed.add_field(name="`,snipe` or `,s [page]`", value="Show recently deleted messages.", inline=False)
    embed.add_field(name="`,mess @user [message]`", value="Send a DM (requires timeout members permission).", inline=False)
    embed.add_field(name="`,re @user [nickname]`", value="Change a user's nickname (requires manage nicknames permission).", inline=False)
    embed.add_field(name="`,reset`", value="Reset all sniped messages (requires administrator permission).", inline=False)
    embed.add_field(name="`,help` or `/help`", value="Show this help message.", inline=False)
    embed.set_footer(text="SnipeBot by Werzzzy | Server owner and administrators bypass all permission requirements")
    await ctx.send(embed=embed)

# Add error handlers for permission errors
@mess.error
@rename.error
@reset.error
async def permission_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You don't have the required permissions to use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=10)

# Start everything
if __name__ == "__main__":
    run_flask()
    bot.run(os.getenv("DISCORD_TOKEN"))
