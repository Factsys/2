import discord
from discord.ext import commands
from discord import app_commands
import os
from flask import Flask
from threading import Thread
import re
import math
import difflib
import time
import asyncio
import random
from datetime import datetime, timedelta
from typing import Optional, List, Union

# Flask app to keep the bot running on Render
app = Flask('')

@app.route('/')
def home():
    return "SnipeBot is running!"

def run_flask():
    port = int(os.getenv("PORT", 8080))
    server = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": port}, daemon=True)
    server.start()

# Bot start time for uptime tracking
BOT_START_TIME = time.time()

# Step 1: Normalize weird characters to plain letters
def normalize_text(text: str) -> str:
    if not text:
        return ""
    
    substitutions = {
        '@': 'a', '4': 'a',
        '1': 'i', '!': 'i', '|': 'i',
        '3': 'e',
        '$': 's',
        '0': 'o',
        '+': 't',
        '7': 't',
        '9': 'g',
        '*': '',
        '.': '',
        '/': '',
        '\\': '',
        '-': '',
        '_': '',
        ',': '',
        ' ': '',
    }
    for symbol, replacement in substitutions.items():
        text = text.replace(symbol, replacement)
    return text.lower()

# Step 2: Offensive word filters (regex-based)
FILTER_PATTERNS = [
    r"n[i1l][g69q][g69a@4][a@4]?",     # n-word
    r"f[uüv][c(kq)][k]?",              # f-word
    r"r[e3][t+][a@4][r]{1,2}[d]*",     # r-word
    r"b[i1!|][t+][c(kq)][h]+",         # b-word
    r"s[h][i1!|][t+]",                 # shit
    r"r[a@4][p][e3]",                  # rape
    r"a[s$]{2,}[h]*[o0]*[l1!|]*[e]*",  # a-hole
    r"d[i1!|][c(kq)][k]+",             # dick
    r"c[uüv][n][t]+",                  # c-word
    r"p[o0][r]+[n]+",                  # porn
    r"w[h][o0][r]+[e3]+",              # whore
    r"s[l1][uüv][t]+",                 # slut
    r"f[a@4][gq69]+",                  # fag
    r"k[i1l|!][l1][l1]y[o0][uüv][r]+[s$][e3][l1]+[f]+", # kill yourself
    r"ky[s$]+"                         # kys
]

# Check if content contains offensive words
def is_offensive_content(content):
    if not content:
        return False
    
    normalized = normalize_text(content)
    for pattern in FILTER_PATTERNS:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            return True
    
    return False

# Replace offensive words with asterisks
def filter_content(content):
    if not content:
        return content
    
    # Find all words in the content
    words = []
    for word in content.split():
        # Check if the normalized version of the word matches any filter
        if is_offensive_content(word):
            # Replace the entire word with asterisks
            words.append('*' * len(word))
        else:
            words.append(word)
    
    return ' '.join(words)

# Helper function to parse color from hex string
def parse_color(color_str):
    """Parse color from hex string (e.g., #ff0000, ff0000, red)"""
    if not color_str:
        return discord.Color.default()
    
    # Remove # if present
    if color_str.startswith('#'):
        color_str = color_str[1:]
    
    # Handle common color names
    color_names = {
        'red': 0xff0000,
        'green': 0x00ff00,
        'blue': 0x0000ff,
        'yellow': 0xffff00,
        'purple': 0x800080,
        'orange': 0xffa500,
        'pink': 0xffc0cb,
        'black': 0x000000,
        'white': 0xffffff,
        'gray': 0x808080,
        'grey': 0x808080,
        'cyan': 0x00ffff,
        'magenta': 0xff00ff,
        'gold': 0xffd700,
        'silver': 0xc0c0c0,
        'golden': 0xffd700
    }
    
    if color_str.lower() in color_names:
        return discord.Color(color_names[color_str.lower()])
    
    # Try to parse as hex
    try:
        if len(color_str) == 6:
            return discord.Color(int(color_str, 16))
        elif len(color_str) == 3:
            # Convert 3-digit hex to 6-digit
            expanded = ''.join([c*2 for c in color_str])
            return discord.Color(int(expanded, 16))
    except ValueError:
        pass
    
    return discord.Color.default()

# Helper function to parse time string (e.g., "1h", "30m", "5d")
def parse_time_string(time_str):
    """Parse time string and return seconds"""
    if not time_str:
        return 0
    
    time_units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800
    }
    
    # Extract number and unit
    match = re.match(r'^(\d+)([smhdw])$', time_str.lower())
    if match:
        number, unit = match.groups()
        return int(number) * time_units[unit]
    
    return 0

# Helper function to format time duration
def format_duration(seconds):
    """Format seconds into readable duration"""
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m"
    elif seconds < 86400:
        return f"{seconds // 3600}h"
    else:
        return f"{seconds // 86400}d"

# Smart user finder function (like Dyno) - ENHANCED
def find_user_by_name(guild, search_term):
    """Find user by partial name match, similar to Dyno bot"""
    if not guild:
        return None
    
    search_term = search_term.lower()
    
    # First, try exact matches
    for member in guild.members:
        if member.display_name.lower() == search_term or member.name.lower() == search_term:
            return member
    
    # Then try partial matches
    matches = []
    for member in guild.members:
        if search_term in member.display_name.lower() or search_term in member.name.lower():
            matches.append(member)
    
    if matches:
        # Use difflib to find the closest match
        names = [m.display_name.lower() for m in matches] + [m.name.lower() for m in matches]
        closest = difflib.get_close_matches(search_term, names, n=1, cutoff=0.3)
        if closest:
            closest_name = closest[0]
            for member in matches:
                if member.display_name.lower() == closest_name or member.name.lower() == closest_name:
                    return member
        return matches[0]  # Return first match if no close match found
    
    return None

# Global user finder (across all servers bot is in)
def find_user_globally(search_term):
    """Find user across all servers the bot is in"""
    search_term = search_term.lower()
    
    # First, try exact matches
    for guild in bot.guilds:
        for member in guild.members:
            if member.display_name.lower() == search_term or member.name.lower() == search_term:
                return member
    
    # Then try partial matches
    matches = []
    for guild in bot.guilds:
        for member in guild.members:
            if search_term in member.display_name.lower() or search_term in member.name.lower():
                if member not in matches:  # Avoid duplicates
                    matches.append(member)
    
    if matches:
        # Use difflib to find the closest match
        names = [m.display_name.lower() for m in matches] + [m.name.lower() for m in matches]
        closest = difflib.get_close_matches(search_term, names, n=1, cutoff=0.3)
        if closest:
            closest_name = closest[0]
            for member in matches:
                if member.display_name.lower() == closest_name or member.name.lower() == closest_name:
                    return member
        return matches[0]  # Return first match if no close match found
    
    return None

# Enable intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True

# Initialize bot
bot = commands.Bot(command_prefix=",", intents=intents)
bot.remove_command('help')
sniped_messages = {}
edited_messages = {}

# Store webhooks for reuse
channel_webhooks = {}

# Store namelocked users: {user_id: locked_nickname}
namelocked_users = {}

# Store namelock immune users: {user_id}
namelock_immune_users = set()

# Store blocked users (cannot use any bot functions): {user_id}
blocked_users = set()

# Store active giveaways: {message_id: giveaway_data}
active_giveaways = {}

# Store user message counts: {guild_id: {user_id: count}}
user_message_counts = {}

# Store giveaway host roles: {guild_id: [role_ids]}
giveaway_host_roles = {}

# Store reaction roles: {message_id: {emoji: role_id}}
reaction_roles = {}

# ENHANCED: Increased storage capacity to support 100 pages
MAX_MESSAGES = 100  # Increased from 10 to 100
MESSAGES_PER_PAGE = 10  # Number of messages to show per page in list view

# Helper function to check if user is blocked
def is_user_blocked(user_id):
    """Check if a user is blocked from using bot functions"""
    return user_id in blocked_users

# Helper function to handle media URLs
def get_media_url(content, attachments):
    # Check for tenor links
    tenor_match = re.search(r'https?://(?:www\.)?tenor\.com/view/[^\s]+', content or "")
    if tenor_match:
        return tenor_match.group(0)
    
    # Check for Twitter/X GIF links
    twitter_match = re.search(r'https?://(?:www\.)?twitter\.com/[^\s]+\.gif', content or "")
    if twitter_match:
        return twitter_match.group(0)
    
    # Check for discord attachment links with .gif extension
    gif_match = re.search(r'https?://(?:cdn|media)\.discordapp\.(?:com|net)/[^\s]+\.gif[^\s]*', content or "")
    if gif_match:
        return gif_match.group(0)
    
    # Check for direct GIF links
    direct_gif_match = re.search(r'https?://[^\s]+\.gif[^\s]*', content or "")
    if direct_gif_match:
        return direct_gif_match.group(0)
    
    # If there are attachments, return the URL of the first one
    if attachments:
        return attachments[0].url
    
    return None

# Helper function to truncate long messages for list view
def truncate_content(content, max_length=50):
    if not content:
        return "*No text content*"
    if len(content) <= max_length:
        return content
    return content[:max_length-3] + "..."

# Helper function to format uptime
def format_uptime(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if seconds > 0 or not parts:
        parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
    
    return ", ".join(parts)

# Helper function to get or create webhook for channel
async def get_or_create_webhook(channel):
    """Get existing webhook or create a new one for the channel"""
    # Check if we already have a webhook for this channel
    if channel.id in channel_webhooks:
        webhook = channel_webhooks[channel.id]
        try:
            # Test if webhook still exists
            await webhook.fetch()
            return webhook
        except discord.NotFound:
            # Webhook was deleted, remove from cache
            del channel_webhooks[channel.id]
    
    # Look for existing SnipeBot webhook in the channel
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.name == "SnipeBot Webhook":
            channel_webhooks[channel.id] = webhook
            return webhook
    
    # Create new webhook
    webhook = await channel.create_webhook(name="SnipeBot Webhook")
    channel_webhooks[channel.id] = webhook
    return webhook

# Helper function to count user messages
def get_user_message_count(guild_id, user_id):
    """Get message count for a user in a guild"""
    if guild_id not in user_message_counts:
        return 0
    return user_message_counts[guild_id].get(user_id, 0)

# Helper function to increment user message count
def increment_user_message_count(guild_id, user_id):
    """Increment message count for a user in a guild"""
    if guild_id not in user_message_counts:
        user_message_counts[guild_id] = {}
    
    if user_id not in user_message_counts[guild_id]:
        user_message_counts[guild_id][user_id] = 0
    
    user_message_counts[guild_id][user_id] += 1

# Helper function to check if user can host giveaways
def can_host_giveaway(member):
    """Check if a member can host giveaways"""
    # Check if user is guild owner or administrator
    if member.guild_permissions.administrator or member.id == member.guild.owner_id:
        return True
    
    # Check if guild has giveaway host roles set
    guild_id = member.guild.id
    if guild_id not in giveaway_host_roles:
        return False
    
    # Check if user has any of the giveaway host roles
    user_role_ids = [role.id for role in member.roles]
    return any(role_id in user_role_ids for role_id in giveaway_host_roles[guild_id])

# Helper function to check if user meets giveaway requirements
def check_giveaway_requirements(member, requirements):
    """Check if a member meets all giveaway requirements"""
    if not requirements:
        return True, []
    
    failed_requirements = []
    guild = member.guild
    
    # Check message requirement
    if 'messages' in requirements:
        user_count = get_user_message_count(guild.id, member.id)
        required_messages = requirements['messages']
        if user_count < required_messages:
            failed_requirements.append(f"Need {required_messages} messages (has {user_count})")
    
    # Check required role
    if 'required_role' in requirements:
        role_name = requirements['required_role']
        if not any(role.name.lower() == role_name.lower() for role in member.roles):
            failed_requirements.append(f"Need role: {role_name}")
    
    # Check blacklisted role
    if 'blacklisted_role' in requirements:
        role_name = requirements['blacklisted_role']
        if any(role.name.lower() == role_name.lower() for role in member.roles):
            failed_requirements.append(f"Cannot have role: {role_name}")
    
    return len(failed_requirements) == 0, failed_requirements

# Custom check that blocks users completely
def not_blocked():
    async def predicate(ctx):
        # If user is blocked, they cannot use ANY bot functions
        if is_user_blocked(ctx.author.id):
            return False
        return True
    return commands.check(predicate)

def check_not_blocked():
    async def predicate(interaction: discord.Interaction):
        # If user is blocked, they cannot use ANY bot functions
        if is_user_blocked(interaction.user.id):
            return False
        return True
    return app_commands.check(predicate)

# Custom check that allows administrators and owners to bypass permission requirements
def has_permission_or_is_admin():
    async def predicate(ctx):
        # Check if user is blocked first
        if is_user_blocked(ctx.author.id):
            return False
        # Check if user is guild owner
        if ctx.guild and ctx.author.id == ctx.guild.owner_id:
            return True
        # Check if user is administrator
        if ctx.guild and ctx.author.guild_permissions.administrator:
            return True
        # Otherwise check for the specific permission in the command
        return await commands.has_permissions().predicate(ctx)
    return commands.check(predicate)

# Custom check for manage nicknames permission
def has_manage_nicknames():
    async def predicate(ctx):
        # Check if user is blocked first
        if is_user_blocked(ctx.author.id):
            return False
        if not ctx.guild:
            return False
        # Check if user is guild owner
        if ctx.author.id == ctx.guild.owner_id:
            return True
        # Check if user has manage nicknames permission
        return ctx.author.guild_permissions.manage_nicknames
    return commands.check(predicate)

# Custom check for slash commands that allows administrators and owners to bypass
def check_admin_or_permissions(**perms):
    async def predicate(interaction: discord.Interaction):
        # Check if user is blocked first
        if is_user_blocked(interaction.user.id):
            return False
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

# Custom check specifically for moderator permissions
def is_moderator():
    async def predicate(ctx):
        # Check if user is blocked first
        if is_user_blocked(ctx.author.id):
            return False
        if not ctx.guild:
            return False
        # Check if user is guild owner
        if ctx.author.id == ctx.guild.owner_id:
            return True
        # Check if user is moderator or administrator
        return (ctx.author.guild_permissions.administrator or
                ctx.author.guild_permissions.manage_messages or
                ctx.author.guild_permissions.moderate_members or
                ctx.author.guild_permissions.ban_members)
    return commands.check(predicate)

# Custom check for slash commands for moderator permissions
def check_moderator():
    async def predicate(interaction: discord.Interaction):
        # Check if user is blocked first
        if is_user_blocked(interaction.user.id):
            return False
        if not interaction.guild:
            return False
        # Check if user is guild owner
        if interaction.user.id == interaction.guild.owner_id:
            return True
        # Check if user is moderator or administrator
        return (interaction.user.guild_permissions.administrator or
                interaction.user.guild_permissions.manage_messages or
                interaction.user.guild_permissions.moderate_members or
                interaction.user.guild_permissions.ban_members)
    return app_commands.check(predicate)

# Custom check for giveaway hosting
def check_giveaway_host():
    async def predicate(interaction: discord.Interaction):
        # Check if user is blocked first
        if is_user_blocked(interaction.user.id):
            return False
        if not interaction.guild:
            return False
        return can_host_giveaway(interaction.user)
    return app_commands.check(predicate)

# Custom check for specific user ID (bot owner commands)
def is_specific_user():
    async def predicate(ctx):
        return ctx.author.id == 776883692983156736
    return commands.check(predicate)

def check_specific_user():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == 776883692983156736
    return app_commands.check(predicate)

# ===== EVENTS =====

@bot.event
async def on_ready():
    print(f'{bot.user.name} has logged in!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    try:
        # Sync slash commands with Discord
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s)")
        
        # List all synced commands
        for command in synced:
            print(f"- /{command.name}")
            
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    # Ignore bot messages
    if message.author.bot:
        return
    
    # Store message for snipe functionality
    sniped_messages[message.channel.id] = {
        'content': message.content,
        'author': message.author,
        'timestamp': message.created_at,
        'attachments': [att.url for att in message.attachments] if message.attachments else []
    }
    
    # Count messages for giveaway requirements
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    # Handle namelock
    if message.author.id in namelocked_users and message.guild:
        if message.author.id not in namelock_immune_users:
            locked_nickname = namelocked_users[message.author.id]
            try:
                if message.author.display_name != locked_nickname:
                    await message.author.edit(nick=locked_nickname, reason="User is namelocked")
            except discord.Forbidden:
                pass
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    # Store deleted message for snipe
    media_url = get_media_url(message.content, message.attachments)
    
    sniped_messages[message.channel.id] = {
        'content': message.content,
        'author': message.author,
        'timestamp': message.created_at,
        'attachments': [att.url for att in message.attachments] if message.attachments else [],
        'media_url': media_url,
        'deleted': True,
        'delete_time': datetime.utcnow()
    }

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    # Store edited message for editsnipe
    edited_messages[before.channel.id] = {
        'before_content': before.content,
        'after_content': after.content,
        'author': before.author,
        'timestamp': before.created_at,
        'edited_at': after.edited_at
    }

@bot.event
async def on_member_update(before, after):
    # Handle namelock when user tries to change nickname
    if before.nick != after.nick and after.id in namelocked_users:
        if after.id not in namelock_immune_users:
            locked_nickname = namelocked_users[after.id]
            try:
                if after.display_name != locked_nickname:
                    await after.edit(nick=locked_nickname, reason="User is namelocked")
            except discord.Forbidden:
                pass

# ===== HELPER FUNCTION FOR GIVEAWAY END =====

async def end_giveaway(message_id):
    if message_id not in active_giveaways:
        return
    
    giveaway = active_giveaways[message_id]
    channel = bot.get_channel(giveaway['channel_id'])
    
    if not channel:
        del active_giveaways[message_id]
        return
    
    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        del active_giveaways[message_id]
        return
    
    # Get participants from reactions
    participants = []
    for reaction in message.reactions:
        if str(reaction.emoji) == giveaway.get('emoji', '🎉'):
            async for user in reaction.users():
                if not user.bot and user.id not in participants:
                    # Check requirements
                    if message.guild:
                        member = message.guild.get_member(user.id)
                        if member:
                            meets_req, _ = check_giveaway_requirements(member, giveaway.get('requirements'))
                            if meets_req:
                                participants.append(user.id)
    
    # Select winners
    winners_count = min(giveaway['winners'], len(participants))
    if winners_count == 0:
        embed = discord.Embed(
            title="🎉 Giveaway Ended!",
            description=f"**Prize:** {giveaway['prize']}\n\n❌ No valid participants!",
            color=discord.Color.red()
        )
    else:
        winners = random.sample(participants, winners_count)
        winner_mentions = []
        for winner_id in winners:
            user = bot.get_user(winner_id)
            if user:
                winner_mentions.append(user.mention)
        
        embed = discord.Embed(
            title="🎉 Giveaway Ended!",
            description=f"**Prize:** {giveaway['prize']}\n\n**Winner{'s' if len(winners) > 1 else ''}:** {', '.join(winner_mentions)}",
            color=discord.Color.gold()
        )
    
    await message.edit(embed=embed, view=None)
    
    # Remove from active giveaways
    del active_giveaways[message_id]

# ===== PREFIX COMMANDS =====

@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe_command(ctx):
    """Show the last deleted message in this channel"""
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages:
        await ctx.send("❌ Nothing to snipe in this channel!")
        return
    
    msg_data = sniped_messages[channel_id]
    
    # Create embed
    embed = discord.Embed(
        description=msg_data['content'] or "*No text content*",
        color=discord.Color.red(),
        timestamp=msg_data['timestamp']
    )
    
    embed.set_author(
        name=msg_data['author'].display_name,
        icon_url=msg_data['author'].display_avatar.url
    )
    
    if msg_data.get('deleted'):
        embed.set_footer(text="Message deleted")
    else:
        embed.set_footer(text="Last message")
    
    # Handle attachments/media
    if msg_data.get('media_url'):
        if any(msg_data['media_url'].lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            embed.set_image(url=msg_data['media_url'])
        else:
            embed.add_field(name="Attachment", value=msg_data['media_url'], inline=False)
    elif msg_data.get('attachments'):
        for i, attachment in enumerate(msg_data['attachments'][:3]):  # Limit to 3 attachments
            embed.add_field(name=f"Attachment {i+1}", value=attachment, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='editsnipe', aliases=['es'])
@not_blocked()
async def editsnipe_command(ctx):
    """Show the last edited message in this channel"""
    channel_id = ctx.channel.id
    
    if channel_id not in edited_messages:
        await ctx.send("❌ No edited messages to snipe in this channel!")
        return
    
    msg_data = edited_messages[channel_id]
    
    embed = discord.Embed(color=discord.Color.orange(), timestamp=msg_data['timestamp'])
    
    embed.set_author(
        name=msg_data['author'].display_name,
        icon_url=msg_data['author'].display_avatar.url
    )
    
    embed.add_field(
        name="Before",
        value=msg_data['before_content'] or "*No content*",
        inline=False
    )
    
    embed.add_field(
        name="After", 
        value=msg_data['after_content'] or "*No content*",
        inline=False
    )
    
    edit_time = msg_data.get('edited_at', msg_data['timestamp'])
    embed.set_footer(text=f"Edited at {edit_time.strftime('%H:%M:%S')}")
    
    await ctx.send(embed=embed)

@bot.command(name='snipepages', aliases=['sp'])
@not_blocked()
async def snipepages_command(ctx, page: int = 1):
    """List all deleted messages with pagination"""
    if not sniped_messages:
        await ctx.send("❌ No sniped messages available!")
        return
    
    # Get all sniped messages for this guild
    guild_messages = []
    for channel_id, msg_data in sniped_messages.items():
        channel = bot.get_channel(channel_id)
        if channel and channel.guild.id == ctx.guild.id:
            guild_messages.append((channel, msg_data))
    
    if not guild_messages:
        await ctx.send("❌ No sniped messages in this server!")
        return
    
    # Sort by timestamp (newest first)
    guild_messages.sort(key=lambda x: x[1]['timestamp'], reverse=True)
    
    # Pagination
    total_pages = math.ceil(len(guild_messages) / MESSAGES_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = guild_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"📋 Sniped Messages - Page {page}/{total_pages}",
        color=discord.Color.blue()
    )
    
    for i, (channel, msg_data) in enumerate(page_messages, start=start_idx + 1):
        content = truncate_content(msg_data['content'])
        timestamp = msg_data['timestamp'].strftime('%m/%d %H:%M')
        
        embed.add_field(
            name=f"{i}. {msg_data['author'].display_name} in #{channel.name}",
            value=f"{content}\n*{timestamp}*",
            inline=False
        )
    
    embed.set_footer(text=f"Use ,sp [page] to view other pages")
    await ctx.send(embed=embed)

@bot.command(name='spforce', aliases=['spf'])
@is_moderator()
async def spforce_command(ctx):
    """Moderator-only unfiltered snipe"""
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages:
        await ctx.send("❌ Nothing to snipe in this channel!")
        return
    
    msg_data = sniped_messages[channel_id]
    
    # Show unfiltered content (no content filtering)
    embed = discord.Embed(
        title="🔧 Force Snipe (Unfiltered)",
        description=msg_data['content'] or "*No text content*",
        color=discord.Color.red(),
        timestamp=msg_data['timestamp']
    )
    
    embed.set_author(
        name=msg_data['author'].display_name,
        icon_url=msg_data['author'].display_avatar.url
    )
    
    embed.set_footer(text="Moderator Force Snipe")
    
    # Handle attachments/media
    if msg_data.get('media_url'):
        if any(msg_data['media_url'].lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            embed.set_image(url=msg_data['media_url'])
        else:
            embed.add_field(name="Attachment", value=msg_data['media_url'], inline=False)
    elif msg_data.get('attachments'):
        for i, attachment in enumerate(msg_data['attachments'][:3]):
            embed.add_field(name=f"Attachment {i+1}", value=attachment, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='mess')
@is_moderator()
async def mess_command(ctx, *, args):
    """DM a user globally - Usage: ,mess [user] [message]"""
    if not args:
        await ctx.send("❌ Usage: `,mess [user] [message]`")
        return
    
    # Split args into user and message
    parts = args.split(' ', 1)
    if len(parts) < 2:
        await ctx.send("❌ Usage: `,mess [user] [message]`")
        return
    
    user_search, message = parts
    
    # Find user globally across all servers
    target_user = find_user_globally(user_search)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user: `{user_search}`")
        return
    
    try:
        # Send DM to user
        await target_user.send(message)
        await ctx.send(f"✅ Message sent to {target_user.display_name} ({target_user.mention})")
    except discord.Forbidden:
        await ctx.send(f"❌ Could not send DM to {target_user.display_name}. They may have DMs disabled.")
    except Exception as e:
        await ctx.send(f"❌ Failed to send message: {str(e)}")

@bot.command(name='say')
@is_moderator()
async def say_command(ctx, *, message):
    """Make the bot say something normally"""
    if not message:
        await ctx.send("❌ Please provide a message to send.")
        return
    
    # Delete the command message
    try:
        await ctx.message.delete()
    except:
        pass
    
    # Send the message normally
    await ctx.send(message)

@bot.command(name='saywb')
@is_moderator()
async def saywb_command(ctx, *, args):
    """Send message via webhook - Usage: ,saywb [message] [color]"""
    if not args:
        await ctx.send("❌ Usage: `,saywb [message] [color]`")
        return
    
    # Parse arguments
    parts = args.rsplit(' ', 1)  # Split from the right to get color as last argument
    
    if len(parts) == 2 and (parts[1].startswith('#') or parts[1].lower() in ['red', 'green', 'blue', 'yellow', 'purple', 'orange', 'pink']):
        message, color_str = parts
        color = parse_color(color_str)
    else:
        message = args
        color = discord.Color.default()
    
    try:
        # Get or create webhook
        webhook = await get_or_create_webhook(ctx.channel)
        
        # Create embed with color
        embed = discord.Embed(
            description=message,
            color=color
        )
        
        # Send via webhook
        await webhook.send(
            embed=embed,
            username=ctx.author.display_name,
            avatar_url=ctx.author.display_avatar.url
        )
        
        # Delete command message
        try:
            await ctx.message.delete()
        except:
            pass
            
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to create webhooks in this channel.")
    except Exception as e:
        await ctx.send(f"❌ Failed to send webhook message: {str(e)}")

@bot.command(name='namelock', aliases=['nl'])
@has_manage_nicknames()
async def namelock_command(ctx, user_search, *, nickname):
    """Lock a user's nickname"""
    if not user_search:
        await ctx.send("❌ Usage: `,namelock [user] [nickname]`")
        return
    
    # Find user
    user = find_user_by_name(ctx.guild, user_search)
    if not user:
        await ctx.send(f"❌ Could not find user: `{user_search}`")
        return
    
    # Check if user is immune
    if user.id in namelock_immune_users:
        await ctx.send(f"❌ {user.display_name} is immune to namelock.")
        return
    
    # Set namelock
    namelocked_users[user.id] = nickname
    
    try:
        await user.edit(nick=nickname, reason=f"Namelocked by {ctx.author}")
        await ctx.send(f"✅ Namelocked {user.display_name} to `{nickname}`")
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to change {user.display_name}'s nickname.")

@bot.command(name='unl')
@has_manage_nicknames()
async def unlock_command(ctx, user_search):
    """Unlock a user from namelock"""
    if not user_search:
        await ctx.send("❌ Usage: `,unl [user]`")
        return
    
    # Find user
    user = find_user_by_name(ctx.guild, user_search)
    if not user:
        await ctx.send(f"❌ Could not find user: `{user_search}`")
        return
    
    # Check if user is namelocked
    if user.id not in namelocked_users:
        await ctx.send(f"❌ {user.display_name} is not namelocked.")
        return
    
    # Remove from namelock
    del namelocked_users[user.id]
    
    await ctx.send(f"✅ Unlocked {user.display_name} from namelock. They can now change their nickname freely.")

@bot.command(name='rename', aliases=['re'])
@has_manage_nicknames()
async def rename_command(ctx, user_search, *, nickname):
    """Change a user's nickname"""
    if not user_search:
        await ctx.send("❌ Usage: `,rename [user] [nickname]`")
        return
    
    # Find user
    user = find_user_by_name(ctx.guild, user_search)
    if not user:
        await ctx.send(f"❌ Could not find user: `{user_search}`")
        return
    
    try:
        old_nick = user.display_name
        await user.edit(nick=nickname, reason=f"Renamed by {ctx.author}")
        await ctx.send(f"✅ Renamed {old_nick} to `{nickname}`")
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to change {user.display_name}'s nickname.")

@bot.command(name='role')
@is_moderator()
async def role_command(ctx, user_search, *, role_search):
    """Add/remove role from user with smart search"""
    if not user_search or not role_search:
        await ctx.send("❌ Usage: `,role [user] [role]`")
        return
    
    # Find user
    user = find_user_by_name(ctx.guild, user_search)
    if not user:
        await ctx.send(f"❌ Could not find user: `{user_search}`")
        return
    
    # Find role
    role = None
    role_search_lower = role_search.lower()
    
    # Try exact match first
    for r in ctx.guild.roles:
        if r.name.lower() == role_search_lower:
            role = r
            break
    
    # Try partial match
    if not role:
        matches = [r for r in ctx.guild.roles if role_search_lower in r.name.lower()]
        if matches:
            # Use difflib for closest match
            role_names = [r.name.lower() for r in matches]
            closest = difflib.get_close_matches(role_search_lower, role_names, n=1, cutoff=0.3)
            if closest:
                for r in matches:
                    if r.name.lower() == closest[0]:
                        role = r
                        break
            else:
                role = matches[0]
    
    if not role:
        await ctx.send(f"❌ Could not find role: `{role_search}`")
        return
    
    try:
        if role in user.roles:
            # Remove role
            await user.remove_roles(role, reason=f"Role removed by {ctx.author}")
            await ctx.send(f"✅ Removed role `{role.name}` from {user.display_name}")
        else:
            # Add role
            await user.add_roles(role, reason=f"Role added by {ctx.author}")
            await ctx.send(f"✅ Added role `{role.name}` to {user.display_name}")
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to manage the role `{role.name}`.")

@bot.command(name='block')
@is_moderator()
async def block_command(ctx, user_search):
    """Block a user from using bot functions"""
    if not user_search:
        await ctx.send("❌ Usage: `,block [user]`")
        return
    
    # Find user globally
    user = find_user_globally(user_search)
    if not user:
        await ctx.send(f"❌ Could not find user: `{user_search}`")
        return
    
    if user.id in blocked_users:
        await ctx.send(f"❌ {user.display_name} is already blocked.")
        return
    
    blocked_users.add(user.id)
    await ctx.send(f"✅ Blocked {user.display_name} from using bot functions.")

@bot.command(name='namelockimmune', aliases=['nli'])
@is_moderator()
async def namelock_immune_command(ctx, user_search):
    """Make a user immune to namelock"""
    if not user_search:
        await ctx.send("❌ Usage: `,nli [user]`")
        return
    
    # Find user
    user = find_user_by_name(ctx.guild, user_search)
    if not user:
        await ctx.send(f"❌ Could not find user: `{user_search}`")
        return
    
    if user.id in namelock_immune_users:
        # Remove immunity
        namelock_immune_users.remove(user.id)
        await ctx.send(f"✅ Removed namelock immunity from {user.display_name}")
    else:
        # Add immunity
        namelock_immune_users.add(user.id)
        # Remove from namelock if they're locked
        if user.id in namelocked_users:
            del namelocked_users[user.id]
        await ctx.send(f"✅ Made {user.display_name} immune to namelock")

@bot.command(name='gw')
@is_moderator()
async def giveaway_reroll_command(ctx, message_id: int):
    """Reroll a giveaway winner"""
    if message_id not in active_giveaways:
        await ctx.send("❌ No active giveaway found with that ID.")
        return
    
    # End the giveaway (which picks new winners)
    await end_giveaway(message_id)
    await ctx.send("✅ Giveaway rerolled!")

@bot.command(name='manage')
@is_specific_user()
async def manage_command(ctx):
    """Bot management panel (bot owner only)"""
    embed = discord.Embed(
        title="🔧 Bot Management Panel",
        color=discord.Color.green()
    )
    
    embed.add_field(
        name="**Statistics**",
        value=f"**Guilds:** {len(bot.guilds)}\n**Users:** {len(bot.users)}\n**Uptime:** {format_uptime(time.time() - BOT_START_TIME)}",
        inline=False
    )
    
    embed.add_field(
        name="**Storage**",
        value=f"**Sniped Messages:** {len(sniped_messages)}\n**Blocked Users:** {len(blocked_users)}\n**Active Giveaways:** {len(active_giveaways)}",
        inline=False
    )
    
    embed.add_field(
        name="**Features**",
        value=f"**Namelock Users:** {len(namelocked_users)}\n**Immune Users:** {len(namelock_immune_users)}\n**Reaction Roles:** {len(reaction_roles)}",
        inline=False
    )
    
    embed.set_footer(text="Managed by Werrzzzy")
    
    await ctx.send(embed=embed)

@bot.command(name='help')
@not_blocked()
async def help_command(ctx):
    """Show help commands with pagination"""
    embed = discord.Embed(
        title="📜 SnipeBot Commands - Page 1",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="**Message Tracking**",
        value="`,snipe` `,s` - Show last deleted message\n`,editsnipe` `,es` - Show last edited message\n`,snipepages` `,sp` - List all deleted messages\n`,spforce` `,spf` - Moderator-only unfiltered snipe",
        inline=False
    )
    
    embed.add_field(
        name="**Moderation**",
        value="`,namelock` `,nl` - Lock user's nickname\n`,unl` - Unlock user from namelock\n`,rename` `,re` - Change user's nickname\n`,role` - Add/remove role from user\n`,say` - Send normal message\n`,saywb` - Send message via webhook",
        inline=False
    )
    
    embed.add_field(
        name="**Other Commands**",
        value="`,mess` - DM user globally\n`,block` - Block user from bot\n`,nli` - Toggle namelock immunity\n`,gw` - Reroll giveaway\n`/giveaway` - Create giveaway\n`/unblock` - Unblock user",
        inline=False
    )
    
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

# ===== SLASH COMMANDS =====

@bot.tree.command(name="snipe", description="Show the last deleted message in this channel")
@check_not_blocked()
async def snipe_slash(interaction: discord.Interaction):
    """Show the last deleted message in this channel"""
    channel_id = interaction.channel.id
    
    if channel_id not in sniped_messages:
        await interaction.response.send_message("❌ Nothing to snipe in this channel!", ephemeral=True)
        return
    
    msg_data = sniped_messages[channel_id]
    
    # Create embed
    embed = discord.Embed(
        description=msg_data['content'] or "*No text content*",
        color=discord.Color.red(),
        timestamp=msg_data['timestamp']
    )
    
    embed.set_author(
        name=msg_data['author'].display_name,
        icon_url=msg_data['author'].display_avatar.url
    )
    
    if msg_data.get('deleted'):
        embed.set_footer(text="Message deleted")
    else:
        embed.set_footer(text="Last message")
    
    # Handle attachments/media
    if msg_data.get('media_url'):
        if any(msg_data['media_url'].lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            embed.set_image(url=msg_data['media_url'])
        else:
            embed.add_field(name="Attachment", value=msg_data['media_url'], inline=False)
    elif msg_data.get('attachments'):
        for i, attachment in enumerate(msg_data['attachments'][:3]):  # Limit to 3 attachments
            embed.add_field(name=f"Attachment {i+1}", value=attachment, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="editsnipe", description="Show the last edited message in this channel")
@check_not_blocked()
async def editsnipe_slash(interaction: discord.Interaction):
    """Show the last edited message in this channel"""
    channel_id = interaction.channel.id
    
    if channel_id not in edited_messages:
        await interaction.response.send_message("❌ No edited messages to snipe in this channel!", ephemeral=True)
        return
    
    msg_data = edited_messages[channel_id]
    
    embed = discord.Embed(color=discord.Color.orange(), timestamp=msg_data['timestamp'])
    
    embed.set_author(
        name=msg_data['author'].display_name,
        icon_url=msg_data['author'].display_avatar.url
    )
    
    embed.add_field(
        name="Before",
        value=msg_data['before_content'] or "*No content*",
        inline=False
    )
    
    embed.add_field(
        name="After", 
        value=msg_data['after_content'] or "*No content*",
        inline=False
    )
    
    edit_time = msg_data.get('edited_at', msg_data['timestamp'])
    embed.set_footer(text=f"Edited at {edit_time.strftime('%H:%M:%S')}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clearsnipe", description="Clear sniped messages for this channel")
@app_commands.describe(scope="Choose what to clear: 'channel' (default) or 'all'")
@check_admin_or_permissions(manage_messages=True)
async def clearsnipe_slash(interaction: discord.Interaction, scope: str = "channel"):
    """Clear sniped messages"""
    if scope.lower() == "all":
        # Clear all sniped messages in the server
        channels_cleared = 0
        for channel_id in list(sniped_messages.keys()):
            channel = bot.get_channel(channel_id)
            if channel and channel.guild.id == interaction.guild.id:
                del sniped_messages[channel_id]
                channels_cleared += 1
        
        for channel_id in list(edited_messages.keys()):
            channel = bot.get_channel(channel_id)
            if channel and channel.guild.id == interaction.guild.id:
                del edited_messages[channel_id]
        
        await interaction.response.send_message(f"✅ Cleared sniped messages from {channels_cleared} channels in this server.")
    
    else:
        # Clear only this channel
        channel_id = interaction.channel.id
        cleared_snipe = channel_id in sniped_messages
        cleared_edit = channel_id in edited_messages
        
        if cleared_snipe:
            del sniped_messages[channel_id]
        if cleared_edit:
            del edited_messages[channel_id]
        
        if cleared_snipe or cleared_edit:
            await interaction.response.send_message("✅ Cleared sniped messages for this channel.")
        else:
            await interaction.response.send_message("❌ No sniped messages to clear in this channel.")

@bot.tree.command(name="mess", description="Send a DM to a user globally")
@app_commands.describe(user="User to send DM to", message="Message to send")
@check_moderator()
async def mess_slash(interaction: discord.Interaction, user: str, message: str):
    """DM a user globally"""
    # Find user globally across all servers
    target_user = find_user_globally(user)
    
    if not target_user:
        await interaction.response.send_message(f"❌ Could not find user: `{user}`", ephemeral=True)
        return
    
    try:
        # Send DM to user
        await target_user.send(message)
        await interaction.response.send_message(f"✅ Message sent to {target_user.display_name} ({target_user.mention})", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Could not send DM to {target_user.display_name}. They may have DMs disabled.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to send message: {str(e)}", ephemeral=True)

@bot.tree.command(name="say", description="Make the bot say something")
@app_commands.describe(message="Message to send")
@check_moderator()
async def say_slash(interaction: discord.Interaction, message: str):
    """Make the bot say something normally"""
    await interaction.response.send_message(message)

@bot.tree.command(name="saywb", description="Send message via webhook with optional color")
@app_commands.describe(message="Message to send", color="Embed color (hex code or color name)")
@check_moderator()
async def saywb_slash(interaction: discord.Interaction, message: str, color: str = None):
    """Send message via webhook"""
    try:
        # Get or create webhook
        webhook = await get_or_create_webhook(interaction.channel)
        
        # Parse color
        embed_color = parse_color(color) if color else discord.Color.default()
        
        # Create embed with color
        embed = discord.Embed(
            description=message,
            color=embed_color
        )
        
        # Send via webhook
        await webhook.send(
            embed=embed,
            username=interaction.user.display_name,
            avatar_url=interaction.user.display_avatar.url
        )
        
        await interaction.response.send_message("✅ Message sent via webhook!", ephemeral=True)
            
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to create webhooks in this channel.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to send webhook message: {str(e)}", ephemeral=True)

@bot.tree.command(name="namelock", description="Lock a user's nickname")
@app_commands.describe(user="User to namelock", nickname="Nickname to lock them to")
@check_admin_or_permissions(manage_nicknames=True)
async def namelock_slash(interaction: discord.Interaction, user: str, nickname: str):
    """Lock a user's nickname"""
    # Find user
    target_user = find_user_by_name(interaction.guild, user)
    if not target_user:
        await interaction.response.send_message(f"❌ Could not find user: `{user}`", ephemeral=True)
        return
    
    # Check if user is immune
    if target_user.id in namelock_immune_users:
        await interaction.response.send_message(f"❌ {target_user.display_name} is immune to namelock.", ephemeral=True)
        return
    
    # Set namelock
    namelocked_users[target_user.id] = nickname
    
    try:
        await target_user.edit(nick=nickname, reason=f"Namelocked by {interaction.user}")
        await interaction.response.send_message(f"✅ Namelocked {target_user.display_name} to `{nickname}`")
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ I don't have permission to change {target_user.display_name}'s nickname.", ephemeral=True)

@bot.tree.command(name="unlock", description="Unlock a user from namelock")
@app_commands.describe(user="User to unlock from namelock")
@check_admin_or_permissions(manage_nicknames=True)
async def unlock_slash(interaction: discord.Interaction, user: str):
    """Unlock a user from namelock"""
    # Find user
    target_user = find_user_by_name(interaction.guild, user)
    if not target_user:
        await interaction.response.send_message(f"❌ Could not find user: `{user}`", ephemeral=True)
        return
    
    # Check if user is namelocked
    if target_user.id not in namelocked_users:
        await interaction.response.send_message(f"❌ {target_user.display_name} is not namelocked.", ephemeral=True)
        return
    
    # Remove from namelock
    del namelocked_users[target_user.id]
    
    await interaction.response.send_message(f"✅ Unlocked {target_user.display_name} from namelock. They can now change their nickname freely.")

@bot.tree.command(name="rename", description="Change a user's nickname")
@app_commands.describe(user="User to rename", nickname="New nickname")
@check_admin_or_permissions(manage_nicknames=True)
async def rename_slash(interaction: discord.Interaction, user: str, nickname: str):
    """Change a user's nickname"""
    # Find user
    target_user = find_user_by_name(interaction.guild, user)
    if not target_user:
        await interaction.response.send_message(f"❌ Could not find user: `{user}`", ephemeral=True)
        return
    
    try:
        old_nick = target_user.display_name
        await target_user.edit(nick=nickname, reason=f"Renamed by {interaction.user}")
        await interaction.response.send_message(f"✅ Renamed {old_nick} to `{nickname}`")
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ I don't have permission to change {target_user.display_name}'s nickname.", ephemeral=True)

@bot.tree.command(name="role", description="Add or remove a role from a user")
@app_commands.describe(user="User to modify roles for", role="Role to add/remove")
@check_moderator()
async def role_slash(interaction: discord.Interaction, user: str, role: str):
    """Add/remove role from user with smart search"""
    # Find user
    target_user = find_user_by_name(interaction.guild, user)
    if not target_user:
        await interaction.response.send_message(f"❌ Could not find user: `{user}`", ephemeral=True)
        return
    
    # Find role
    target_role = None
    role_search_lower = role.lower()
    
    # Try exact match first
    for r in interaction.guild.roles:
        if r.name.lower() == role_search_lower:
            target_role = r
            break
    
    # Try partial match
    if not target_role:
        matches = [r for r in interaction.guild.roles if role_search_lower in r.name.lower()]
        if matches:
            # Use difflib for closest match
            role_names = [r.name.lower() for r in matches]
            closest = difflib.get_close_matches(role_search_lower, role_names, n=1, cutoff=0.3)
            if closest:
                for r in matches:
                    if r.name.lower() == closest[0]:
                        target_role = r
                        break
            else:
                target_role = matches[0]
    
    if not target_role:
        await interaction.response.send_message(f"❌ Could not find role: `{role}`", ephemeral=True)
        return
    
    try:
        if target_role in target_user.roles:
            # Remove role
            await target_user.remove_roles(target_role, reason=f"Role removed by {interaction.user}")
            await interaction.response.send_message(f"✅ Removed role `{target_role.name}` from {target_user.display_name}")
        else:
            # Add role
            await target_user.add_roles(target_role, reason=f"Role added by {interaction.user}")
            await interaction.response.send_message(f"✅ Added role `{target_role.name}` to {target_user.display_name}")
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ I don't have permission to manage the role `{target_role.name}`.", ephemeral=True)

@bot.tree.command(name="block", description="Block a user from using bot functions")
@app_commands.describe(user="User to block")
@check_moderator()
async def block_slash(interaction: discord.Interaction, user: str):
    """Block a user from using bot functions"""
    # Find user globally
    target_user = find_user_globally(user)
    if not target_user:
        await interaction.response.send_message(f"❌ Could not find user: `{user}`", ephemeral=True)
        return
    
    if target_user.id in blocked_users:
        await interaction.response.send_message(f"❌ {target_user.display_name} is already blocked.", ephemeral=True)
        return
    
    blocked_users.add(target_user.id)
    await interaction.response.send_message(f"✅ Blocked {target_user.display_name} from using bot functions.")

@bot.tree.command(name="unblock", description="Unblock a user from using bot functions")
@app_commands.describe(user="User to unblock")
@check_specific_user()
async def unblock_slash(interaction: discord.Interaction, user: str):
    """Unblock a user from using bot functions"""
    # Find user globally
    target_user = find_user_globally(user)
    if not target_user:
        await interaction.response.send_message(f"❌ Could not find user: `{user}`", ephemeral=True)
        return
    
    if target_user.id not in blocked_users:
        await interaction.response.send_message(f"❌ {target_user.display_name} is not blocked.", ephemeral=True)
        return
    
    blocked_users.remove(target_user.id)
    await interaction.response.send_message(f"✅ Unblocked {target_user.display_name}.")

@bot.tree.command(name="giveaway", description="Create a giveaway")
@app_commands.describe(
    duration="Duration (e.g., 1h, 30m, 1d)",
    winners="Number of winners (default: 1)",
    prize="What is being given away",
    channel="Channel for the giveaway (default: current channel)",
    required_role="Role required to enter (optional)",
    blacklisted_role="Role that cannot enter (optional)",
    required_messages="Minimum messages required to enter (optional)"
)
@check_giveaway_host()
async def giveaway_slash(
    interaction: discord.Interaction,
    duration: str,
    prize: str,
    winners: int = 1,
    channel: discord.TextChannel = None,
    required_role: discord.Role = None,
    blacklisted_role: discord.Role = None,
    required_messages: int = None
):
    """Create a giveaway"""
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        await interaction.response.send_message("❌ Invalid duration format. Use formats like: 1h, 30m, 1d", ephemeral=True)
        return
    
    if duration_seconds < 60:  # Minimum 1 minute
        await interaction.response.send_message("❌ Duration must be at least 1 minute.", ephemeral=True)
        return
    
    if duration_seconds > 7 * 24 * 3600:  # Maximum 7 days
        await interaction.response.send_message("❌ Duration cannot exceed 7 days.", ephemeral=True)
        return
    
    # Validate winners count
    if winners < 1 or winners > 20:
        await interaction.response.send_message("❌ Number of winners must be between 1 and 20.", ephemeral=True)
        return
    
    # Use current channel if none specified
    if channel is None:
        channel = interaction.channel
    
    # Check bot permissions in target channel
    bot_member = channel.guild.me
    if not channel.permissions_for(bot_member).send_messages:
        await interaction.response.send_message(f"❌ I don't have permission to send messages in {channel.mention}.", ephemeral=True)
        return
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Build requirements
    requirements = {}
    req_text = []
    
    if required_role:
        requirements['required_role'] = required_role.name
        req_text.append(f"Must have role: {required_role.mention}")
    
    if blacklisted_role:
        requirements['blacklisted_role'] = blacklisted_role.name
        req_text.append(f"Cannot have role: {blacklisted_role.mention}")
    
    if required_messages:
        requirements['messages'] = required_messages
        req_text.append(f"Must have at least {required_messages} messages")
    
    # Create giveaway embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
        color=discord.Color.gold(),
        timestamp=end_time
    )
    
    embed.set_footer(text=f"Hosted by {interaction.user.display_name} • Ends at")
    
    if req_text:
        embed.add_field(name="Requirements", value="\n".join(req_text), inline=False)
    
    embed.add_field(name="How to Enter", value="React with 🎉 to enter!", inline=False)
    
    await interaction.response.send_message(f"✅ Giveaway created in {channel.mention}!")
    
    # Send giveaway message
    giveaway_msg = await channel.send(embed=embed)
    await giveaway_msg.add_reaction("🎉")
    
    # Store giveaway data
    active_giveaways[giveaway_msg.id] = {
        'host': interaction.user.id,
        'prize': prize,
        'winners': winners,
        'end_time': end_time,
        'channel_id': channel.id,
        'requirements': requirements,
        'emoji': '🎉'
    }
    
    # Schedule giveaway end
    await asyncio.sleep(duration_seconds)
    
    # End giveaway
    if giveaway_msg.id in active_giveaways:
        await end_giveaway(giveaway_msg.id)

@bot.tree.command(name="giveaway-host-role", description="Set roles that can host giveaways")
@app_commands.describe(role="Role that can host giveaways")
@check_admin_or_permissions(administrator=True)
async def giveaway_host_role_slash(interaction: discord.Interaction, role: discord.Role):
    """Set roles that can host giveaways"""
    guild_id = interaction.guild.id
    
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = []
    
    if role.id in giveaway_host_roles[guild_id]:
        # Remove role
        giveaway_host_roles[guild_id].remove(role.id)
        await interaction.response.send_message(f"✅ Removed {role.mention} from giveaway host roles.")
    else:
        # Add role
        giveaway_host_roles[guild_id].append(role.id)
        await interaction.response.send_message(f"✅ Added {role.mention} to giveaway host roles.")

# Start Flask server
run_flask()

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN'))
