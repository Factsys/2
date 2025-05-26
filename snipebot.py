import discord
from discord.ext import commands, tasks
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
    return "FACTSY Bot is running!"

def run_flask():
    port = int(os.getenv("PORT", 8080))
    server = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": port}, daemon=True)
    server.start()

# Bot start time for uptime tracking
BOT_START_TIME = time.time()

# Bot owner ID
BOT_OWNER_ID = 776883692983156736

# Store custom prefixes: {guild_id: prefix}
custom_prefixes = {}

def get_prefix(bot, message):
    """Get custom prefix for guild or default"""
    if message.guild and message.guild.id in custom_prefixes:
        return custom_prefixes[message.guild.id]
    return ","

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

# ENHANCED: Helper function to parse time string with seconds support
def parse_time_string(time_str):
    """Parse time string and return seconds - now supports seconds"""
    if not time_str:
        return 0
    
    time_units = {
        's': 1,        # seconds
        'm': 60,       # minutes
        'h': 3600,     # hours
        'd': 86400,    # days
        'w': 604800    # weeks
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

# Initialize bot with dynamic prefix
bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.remove_command('help')

# ENHANCED: Store up to 100 deleted messages per channel
sniped_messages = {}  # {channel_id: [list of messages]}
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
MAX_MESSAGES = 100  # Store up to 100 deleted messages per channel
MESSAGES_PER_PAGE = 10  # Number of messages to show per page in list view

# Helper function to check if user is blocked
def is_user_blocked(user_id):
    """Check if a user is blocked from using bot functions"""
    return user_id in blocked_users

# Helper function to check if user is bot owner
def is_bot_owner(user_id):
    """Check if user is the bot owner"""
    return user_id == BOT_OWNER_ID

# ENHANCED: Media URL detection with visual support for Tenor and videos
def get_media_url(content, attachments):
    """Get media URL from content or attachments with enhanced detection"""
    # Priority 1: Check for attachments first (Discord files)
    if attachments:
        for attachment in attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['.gif', '.png', '.jpg', '.jpeg', '.webp', '.mp4', '.mov']):
                return attachment.url
    
    # Priority 2: Check for various media links in content
    if content:
        # Tenor GIFs - these will show as visual moving images
        tenor_match = re.search(r'https?://(?:www\.)?tenor\.com/view/[^\s]+', content)
        if tenor_match:
            return tenor_match.group(0)
        
        # Giphy GIFs
        giphy_match = re.search(r'https?://(?:www\.)?giphy\.com/gifs/[^\s]+', content)
        if giphy_match:
            return giphy_match.group(0)
        
        # Discord CDN media links
        discord_media_match = re.search(r'https?://(?:cdn|media)\.discordapp\.(?:com|net)/[^\s]+\.(gif|png|jpg|jpeg|webp|mp4|mov)[^\s]*', content)
        if discord_media_match:
            return discord_media_match.group(0)
        
        # Direct media links
        direct_media_match = re.search(r'https?://[^\s]+\.(gif|png|jpg|jpeg|webp|mp4|mov)[^\s]*', content)
        if direct_media_match:
            return direct_media_match.group(0)
        
        # YouTube links
        youtube_match = re.search(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^\s]+', content)
        if youtube_match:
            return youtube_match.group(0)
        
        # Twitter/X media
        twitter_match = re.search(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[^\s]+', content)
        if twitter_match:
            return twitter_match.group(0)
    
    return None

# Helper function to remove media URLs from content
def clean_content_from_media(content, media_url):
    """Remove media URLs from content to avoid duplication"""
    if not content or not media_url:
        return content
    
    # Remove the media URL from content
    cleaned_content = content.replace(media_url, '').strip()
    
    # Clean up any extra whitespace or newlines
    cleaned_content = re.sub(r'\s+', ' ', cleaned_content).strip()
    
    return cleaned_content if cleaned_content else None

# Helper function to check if message contains links
def has_links(content):
    if not content:
        return False
    # Check for any URL pattern
    url_pattern = r'https?://[^\s]+'
    return bool(re.search(url_pattern, content))

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
    
    # Look for existing FACTSY webhook in the channel
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.name == "FACTSY Webhook":
            channel_webhooks[channel.id] = webhook
            return webhook
    
    # Create new webhook
    webhook = await channel.create_webhook(name="FACTSY Webhook")
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
    # Check if user is bot owner
    if is_bot_owner(member.id):
        return True
    
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

# ENHANCED: Giveaway requirements checker with time in server support
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
    
    # Check time in server requirement
    if 'time_in_server' in requirements:
        join_time = member.joined_at
        if join_time:
            time_in_server = (datetime.utcnow() - join_time).total_seconds()
            required_time = requirements['time_in_server']
            if time_in_server < required_time:
                required_str = format_duration(required_time)
                current_str = format_duration(int(time_in_server))
                failed_requirements.append(f"Need {required_str} in server (has {current_str})")
    
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

# Enhanced pagination view with arrow buttons
class PaginationView(discord.ui.View):
    def __init__(self, embeds, timeout=300):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.current_page = 0
        self.total_pages = len(embeds)
        self.update_buttons()
    
    def update_buttons(self):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
        else:
            await interaction.response.defer()

# FIXED: Giveaway View with proper message ID handling
class GiveawayView(discord.ui.View):
    def __init__(self, message_id):
        super().__init__(timeout=None)
        self.message_id = message_id
    
    @discord.ui.button(label="Join", style=discord.ButtonStyle.green, emoji="🎉")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_user_blocked(interaction.user.id):
            await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
            return
        
        # FIXED: Use message_id to find giveaway
        if self.message_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway is no longer active.", ephemeral=True)
            return
        
        giveaway = active_giveaways[self.message_id]
        user_id = interaction.user.id
        
        if user_id in giveaway['participants']:
            await interaction.response.send_message("❌ You are already participating in this giveaway!", ephemeral=True)
            return
        
        # Check requirements
        if 'requirements' in giveaway:
            meets_requirements, failed_reqs = check_giveaway_requirements(interaction.user, giveaway['requirements'])
            if not meets_requirements:
                failed_text = "\n".join([f"• {req}" for req in failed_reqs])
                await interaction.response.send_message(f"❌ **You don't meet the requirements:**\n{failed_text}", ephemeral=True)
                return
        
        # Add user to participants
        giveaway['participants'].append(user_id)
        await interaction.response.send_message("✅ You have successfully joined the giveaway!", ephemeral=True)
    
    @discord.ui.button(label="List", style=discord.ButtonStyle.secondary, emoji="📋")
    async def list_participants(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_user_blocked(interaction.user.id):
            await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
            return
        
        # FIXED: Use message_id to find giveaway
        if self.message_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway is no longer active.", ephemeral=True)
            return
        
        giveaway = active_giveaways[self.message_id]
        participants = giveaway['participants']
        
        if not participants:
            await interaction.response.send_message("📋 No participants yet!", ephemeral=True)
            return
        
        # Create paginated participant list
        participants_per_page = 10
        total_pages = math.ceil(len(participants) / participants_per_page)
        embeds = []
        
        for page in range(total_pages):
            start_idx = page * participants_per_page
            end_idx = min((page + 1) * participants_per_page, len(participants))
            page_participants = participants[start_idx:end_idx]
            
            embed = discord.Embed(
                title=f"🎉 Giveaway Participants",
                description=f"**Prize:** {giveaway['prize']}\n**Total Participants:** {len(participants)}",
                color=discord.Color.blue()
            )
            
            participant_list = []
            for i, user_id in enumerate(page_participants, start=start_idx + 1):
                user = bot.get_user(user_id)
                if user:
                    participant_list.append(f"{i}. {user.mention} ({user.name})")
                else:
                    participant_list.append(f"{i}. Unknown User")
            
            embed.add_field(name="Participants", value="\n".join(participant_list), inline=False)
            embed.set_footer(text=f"Page {page + 1} of {total_pages}")
            embeds.append(embed)
        
        if len(embeds) == 1:
            await interaction.response.send_message(embed=embeds[0], ephemeral=True)
        else:
            view = PaginationView(embeds)
            await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)

# Giveaway Reroll View
class GiveawayRerollView(discord.ui.View):
    def __init__(self, message_id, winner):
        super().__init__(timeout=300)
        self.message_id = message_id
        self.winner = winner
    
    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.primary, emoji="🔄")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check permissions
        if not (is_bot_owner(interaction.user.id) or 
                interaction.user.guild_permissions.administrator or 
                can_host_giveaway(interaction.user)):
            await interaction.response.send_message("❌ You don't have permission to reroll giveaways.", ephemeral=True)
            return
        
        if self.message_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway is no longer active.", ephemeral=True)
            return
        
        giveaway = active_giveaways[self.message_id]
        participants = giveaway['participants']
        
        if not participants:
            await interaction.response.send_message("❌ No participants to reroll from.", ephemeral=True)
            return
        
        # Pick new winner
        new_winner_id = random.choice(participants)
        new_winner = bot.get_user(new_winner_id)
        
        if new_winner:
            embed = discord.Embed(
                title="🎉 Giveaway Rerolled!",
                description=f"**New Winner:** {new_winner.mention}\n**Prize:** {giveaway['prize']}",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Rerolled by {interaction.user.name}")
            
            # Create new reroll view
            new_view = GiveawayRerollView(self.message_id, new_winner)
            await interaction.response.edit_message(embed=embed, view=new_view)
        else:
            await interaction.response.send_message("❌ Could not find the new winner.", ephemeral=True)

# Help Pagination View
class HelpPaginationView(discord.ui.View):
    def __init__(self, timeout=300):
        super().__init__(timeout=timeout)
        self.current_page = 0
        self.pages = [
            {
                "title": "📜 FACTSY Commands - Page 1",
                "fields": [
                    ("**Message Tracking**", "`,snipe` `,s [1-100]` `/snipe` - Show deleted message by number\n`,editsnipe` `,es` `/editsnipe` - Show last edited message\n`,sp [channel] [page]` `/sp` - List all deleted messages\n`,spforce` `,spf` `/spforce` - Show censored messages\n`,spl [channel] [page]` `/spl` - Show deleted links only", False),
                    ("**Moderation**", "`,namelock` `,nl` `/namelock` - Lock user's nickname\n`,unl` `/unl` - Unlock user's nickname\n`,rename` `,re` `/rename` - Change user's nickname\n`,say` `/say` - Send normal message\n`,saywb` `/saywb` - Send embed message", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 2", 
                "fields": [
                    ("**Giveaways**", "`,gw [id]` `/gw` - Reroll giveaway winner\n`/giveaway` - Create advanced giveaway\n`/giveaway-host-role` - Set host roles", False),
                    ("**Management**", "`,block` `/block` - Block user from bot\n`,mess` `/mess` - DM user globally\n`,role` `/role` - Add role to user\n`,namelockimmune` `,nli` `/namelockimmune` - Make user immune", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 3",
                "fields": [
                    ("**Reaction Roles**", "`,create` `/create` - Create reaction roles (1-6 options)", False),
                    ("**Bot Features**", "`,manage` `/manage` - Bot management panel\n`/unblock` - Unblock user from bot\n`/ping` - Show bot latency\n`/prefix` - Change server prefix", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 4",
                "fields": [
                    ("**Info**", "All commands support both prefix and slash (/) versions\nModerators can use most commands\nBlocked users cannot use any bot functions\nSeconds support added to durations (e.g., 30s)", False),
                    ("**Usage Examples**", "`,s 5` - Show 5th deleted message\n`/saywb #general My Title My Description red` - Send embed\n`/prefix !` - Change prefix to !\n`/gw 123456789` - Reroll giveaway", False)
                ]
            }
        ]
        self.total_pages = len(self.pages)
        self.update_buttons()
    
    def update_buttons(self):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def get_embed(self):
        page_data = self.pages[self.current_page]
        embed = discord.Embed(
            title=page_data["title"],
            color=discord.Color.blue()
        )
        
        for name, value, inline in page_data["fields"]:
            embed.add_field(name=name, value=value, inline=inline)
        
        embed.set_footer(text=f"Page {self.current_page + 1} of {self.total_pages} | Made with ❤ | Werrzzzy")
        return embed
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

# Management Pagination View
class ManagePaginationView(discord.ui.View):
    def __init__(self, timeout=300):
        super().__init__(timeout=timeout)
        self.current_page = 0
        self.pages = [
            {
                "title": "🔧 Bot Management - Page 1",
                "fields": [
                    ("**Statistics**", f"**Guilds:** {len(bot.guilds)}\n**Users:** {len(bot.users)}\n**Uptime:** {format_uptime(time.time() - BOT_START_TIME)}", False),
                    ("**Storage**", f"**Sniped Messages:** {sum(len(msgs) if isinstance(msgs, list) else 1 for msgs in sniped_messages.values())}\n**Blocked Users:** {len(blocked_users)}\n**Active Giveaways:** {len(active_giveaways)}", False)
                ]
            },
            {
                "title": "🔧 Bot Management - Page 2",
                "fields": [
                    ("**Features**", f"**Namelock Users:** {len(namelocked_users)}\n**Immune Users:** {len(namelock_immune_users)}\n**Reaction Roles:** {len(reaction_roles)}", False),
                    ("**Commands**", "Use `,block [user]` to block users\nUse `/unblock [user]` to unblock users\nUse `,nli [user]` for namelock immunity", False)
                ]
            }
        ]
        self.total_pages = len(self.pages)
        self.update_buttons()
    
    def update_buttons(self):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def get_embed(self):
        page_data = self.pages[self.current_page]
        embed = discord.Embed(
            title=page_data["title"],
            color=discord.Color.green()
        )
        
        for name, value, inline in page_data["fields"]:
            embed.add_field(name=name, value=value, inline=inline)
        
        embed.set_footer(text=f"Manage by Werrzzzy | Page {self.current_page + 1} of {self.total_pages}")
        return embed
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

# Reaction Role Management View
class ReactionRoleView(discord.ui.View):
    def __init__(self, role_mapping):
        super().__init__(timeout=None)
        self.role_mapping = role_mapping  # {emoji: role_id}

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Check if user is blocked
        if is_user_blocked(interaction.user.id):
            await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
            return False
        return True

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    # Check if this is a reaction role message
    message_id = reaction.message.id
    if message_id in reaction_roles:
        emoji_str = str(reaction.emoji)
        if emoji_str in reaction_roles[message_id]:
            role_id = reaction_roles[message_id][emoji_str]
            guild = reaction.message.guild
            if guild:
                role = guild.get_role(role_id)
                member = guild.get_member(user.id)
                if role and member and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Reaction role")
                    except discord.Forbidden:
                        pass

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return
    
    # Check if this is a reaction role message
    message_id = reaction.message.id
    if message_id in reaction_roles:
        emoji_str = str(reaction.emoji)
        if emoji_str in reaction_roles[message_id]:
            role_id = reaction_roles[message_id][emoji_str]
            guild = reaction.message.guild
            if guild:
                role = guild.get_role(role_id)
                member = guild.get_member(user.id)
                if role and member and role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Reaction role removal")
                    except discord.Forbidden:
                        pass

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    # Start Flask server
    run_flask()
    
    # Start background tasks
    giveaway_checker.start()
    
    # FIXED: Proper slash command syncing for application support
    try:
        # Sync slash commands globally (this is what makes them appear on the bot's profile)
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash command(s) globally")
        
        # The bot profile will now show application support with "/" commands
        print("Application support (/) is now active on bot profile!")
        
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

@bot.event
async def on_message_delete(message):
    """Store deleted messages for snipe command"""
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []
    
    # Store message data
    message_data = {
        'content': message.content,
        'author': message.author,
        'created_at': message.created_at,
        'deleted_at': datetime.utcnow(),
        'attachments': [att.url for att in message.attachments] if message.attachments else [],
        'embeds': message.embeds,
        'jump_url': message.jump_url
    }
    
    # Add to the beginning of the list (most recent first)
    sniped_messages[channel_id].insert(0, message_data)
    
    # Keep only the last MAX_MESSAGES
    if len(sniped_messages[channel_id]) > MAX_MESSAGES:
        sniped_messages[channel_id] = sniped_messages[channel_id][:MAX_MESSAGES]

@bot.event
async def on_message_edit(before, after):
    """Store edited messages for editsnipe command"""
    if before.author.bot or before.content == after.content:
        return
    
    channel_id = before.channel.id
    
    if channel_id not in edited_messages:
        edited_messages[channel_id] = []
    
    # Store edit data
    edit_data = {
        'before_content': before.content,
        'after_content': after.content,
        'author': before.author,
        'edited_at': datetime.utcnow(),
        'message_id': before.id,
        'jump_url': after.jump_url
    }
    
    # Add to the beginning of the list (most recent first)
    edited_messages[channel_id].insert(0, edit_data)
    
    # Keep only the last MAX_MESSAGES
    if len(edited_messages[channel_id]) > MAX_MESSAGES:
        edited_messages[channel_id] = edited_messages[channel_id][:MAX_MESSAGES]

@bot.event
async def on_message(message):
    """Track message counts and handle namelocked users"""
    if message.author.bot:
        return
    
    # Increment message count
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    # Check for namelocked users and reset their nickname if changed
    if message.guild and message.author.id in namelocked_users:
        locked_nickname = namelocked_users[message.author.id]
        if message.author.display_name != locked_nickname:
            try:
                await message.author.edit(nick=locked_nickname, reason="User is namelocked")
            except discord.Forbidden:
                pass
    
    await bot.process_commands(message)

@bot.event
async def on_member_update(before, after):
    """Handle nickname changes for namelocked users"""
    if before.nick != after.nick and before.id in namelocked_users:
        # User is namelocked but changed their nickname
        if before.id not in namelock_immune_users:  # Check if they're not immune
            locked_nickname = namelocked_users[before.id]
            if after.nick != locked_nickname:
                try:
                    await after.edit(nick=locked_nickname, reason="User is namelocked")
                except discord.Forbidden:
                    pass

# Background task to check giveaways
@tasks.loop(seconds=30)
async def giveaway_checker():
    """Check for ended giveaways and pick winners"""
    current_time = datetime.utcnow()
    ended_giveaways = []
    
    for message_id, giveaway_data in active_giveaways.items():
        end_time = giveaway_data['end_time']
        if current_time >= end_time and not giveaway_data.get('ended', False):
            ended_giveaways.append(message_id)
    
    for message_id in ended_giveaways:
        giveaway_data = active_giveaways[message_id]
        participants = giveaway_data['participants']
        
        try:
            # Get the message
            channel = bot.get_channel(giveaway_data['channel_id'])
            if not channel:
                continue
            
            message = await channel.fetch_message(message_id)
            if not message:
                continue
            
            # Pick winner
            if participants:
                winner_id = random.choice(participants)
                winner = bot.get_user(winner_id)
                
                if winner:
                    # Create winner embed
                    embed = discord.Embed(
                        title="🎉 Giveaway Ended!",
                        description=f"**Winner:** {winner.mention}\n**Prize:** {giveaway_data['prize']}",
                        color=discord.Color.green()
                    )
                    embed.add_field(name="Participants", value=str(len(participants)), inline=True)
                    embed.set_footer(text=f"Ended at")
                    embed.timestamp = current_time
                    
                    # Add reroll button
                    view = GiveawayRerollView(message_id, winner)
                    await message.edit(embed=embed, view=view)
                    
                    # Send winner notification
                    try:
                        await winner.send(f"🎉 Congratulations! You won **{giveaway_data['prize']}** in {giveaway_data.get('guild_name', 'a server')}!")
                    except:
                        pass  # DM failed
                else:
                    # Winner not found
                    embed = discord.Embed(
                        title="🎉 Giveaway Ended!",
                        description=f"**Winner:** Unknown User\n**Prize:** {giveaway_data['prize']}",
                        color=discord.Color.orange()
                    )
                    embed.add_field(name="Participants", value=str(len(participants)), inline=True)
                    embed.set_footer(text=f"Ended at")
                    embed.timestamp = current_time
                    
                    view = GiveawayRerollView(message_id, None)
                    await message.edit(embed=embed, view=view)
            else:
                # No participants
                embed = discord.Embed(
                    title="🎉 Giveaway Ended!",
                    description=f"**Winner:** No participants\n**Prize:** {giveaway_data['prize']}",
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"Ended at")
                embed.timestamp = current_time
                
                await message.edit(embed=embed, view=None)
            
            # Mark as ended
            giveaway_data['ended'] = True
            
        except Exception as e:
            print(f"Error processing giveaway {message_id}: {e}")
            continue

# FIXED: Snipe command with image support and numbering
@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe_command(ctx, number: int = 1):
    """Show a specific deleted message by number (1-100)"""
    
    if number < 1 or number > 100:
        await ctx.send("❌ Please provide a number between 1 and 100.")
        return
    
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages to snipe in this channel.")
        return
    
    messages = sniped_messages[channel_id]
    
    if number > len(messages):
        await ctx.send(f"❌ Only {len(messages)} deleted message(s) available.")
        return
    
    # Get the specific message (number - 1 because list is 0-indexed)
    message_data = messages[number - 1]
    
    # Get media URL and clean content
    media_url = get_media_url(message_data['content'], message_data['attachments'])
    cleaned_content = clean_content_from_media(message_data['content'], media_url)
    
    # Check if message is filtered (for normal users)
    is_filtered = is_offensive_content(message_data['content'])
    
    # Only show filtered content to moderators with spforce
    if is_filtered and not (ctx.author.guild_permissions.manage_messages or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ This message contains filtered content. Use `,spforce` if you have permissions.")
        return
    
    # Create simple embed with user mention
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.blue()
    )
    
    # Add content if available
    if cleaned_content:
        embed.description = f"{cleaned_content}\n\n{message_data['author'].mention}"
    else:
        embed.description = f"{message_data['author'].mention}"
    
    # Add media if available
    if media_url:
        if any(media_url.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            embed.set_image(url=media_url)
        else:
            # For other media types like Tenor, add as field
            embed.add_field(name="Media", value=f"[View Media]({media_url})", inline=False)
    
    await ctx.send(embed=embed)

# ENHANCED: Slash command for snipe
@bot.tree.command(name="snipe", description="Show a specific deleted message by number (1-100)")
@app_commands.describe(number="Which deleted message to show (1-100)")
@check_not_blocked()
async def snipe_slash(interaction: discord.Interaction, number: int = 1):
    """Show a specific deleted message by number (1-100)"""
    
    if number < 1 or number > 100:
        await interaction.response.send_message("❌ Please provide a number between 1 and 100.", ephemeral=True)
        return
    
    channel_id = interaction.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("❌ No deleted messages to snipe in this channel.", ephemeral=True)
        return
    
    messages = sniped_messages[channel_id]
    
    if number > len(messages):
        await interaction.response.send_message(f"❌ Only {len(messages)} deleted message(s) available.", ephemeral=True)
        return
    
    # Get the specific message (number - 1 because list is 0-indexed)
    message_data = messages[number - 1]
    
    # Get media URL and clean content
    media_url = get_media_url(message_data['content'], message_data['attachments'])
    cleaned_content = clean_content_from_media(message_data['content'], media_url)
    
    # Check if message is filtered (for normal users)
    is_filtered = is_offensive_content(message_data['content'])
    
    # Only show filtered content to moderators with spforce
    if is_filtered and not (interaction.user.guild_permissions.manage_messages or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ This message contains filtered content. Use `/spforce` if you have permissions.", ephemeral=True)
        return
    
    # Create simple embed with user mention
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.blue()
    )
    
    # Add content if available
    if cleaned_content:
        embed.description = f"{cleaned_content}\n\n{message_data['author'].mention}"
    else:
        embed.description = f"{message_data['author'].mention}"
    
    # Add media if available
    if media_url:
        if any(media_url.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            embed.set_image(url=media_url)
        else:
            # For other media types like Tenor, add as field
            embed.add_field(name="Media", value=f"[View Media]({media_url})", inline=False)
    
    await interaction.response.send_message(embed=embed)

# ENHANCED: SP command (normal deleted messages)
@bot.command(name='sp')
@not_blocked()
async def sp_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List all normal deleted messages with pagination"""
    
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages in this channel.")
        return
    
    messages = sniped_messages[channel_id]
    
    # Filter out offensive content for normal users
    if not (ctx.author.guild_permissions.manage_messages or is_bot_owner(ctx.author.id)):
        messages = [msg for msg in messages if not is_offensive_content(msg['content'])]
    
    if not messages:
        await ctx.send("❌ No viewable deleted messages in this channel.")
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Page must be between 1 and {total_pages}.")
        return
    
    embeds = []
    for p in range(total_pages):
        start_idx = p * MESSAGES_PER_PAGE
        end_idx = min((p + 1) * MESSAGES_PER_PAGE, len(messages))
        page_messages = messages[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"📜 Deleted Messages - {target_channel.name}",
            color=discord.Color.blue()
        )
        
        message_list = []
        for i, msg in enumerate(page_messages, start=start_idx + 1):
            content = truncate_content(msg['content'])
            author = msg['author'].name
            message_list.append(f"{i}. **{author}:** {content}")
        
        embed.description = "\n".join(message_list)
        embed.set_footer(text=f"Page {p + 1} of {total_pages} | Use ,s [number] to view full message")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[page - 1], view=view)

# ENHANCED: Slash command for SP
@bot.tree.command(name="sp", description="List all normal deleted messages with pagination")
@app_commands.describe(
    channel="Channel to check (optional)",
    page="Page number to view"
)
@check_not_blocked()
async def sp_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """List all normal deleted messages with pagination"""
    
    target_channel = channel or interaction.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("❌ No deleted messages in this channel.", ephemeral=True)
        return
    
    messages = sniped_messages[channel_id]
    
    # Filter out offensive content for normal users
    if not (interaction.user.guild_permissions.manage_messages or is_bot_owner(interaction.user.id)):
        messages = [msg for msg in messages if not is_offensive_content(msg['content'])]
    
    if not messages:
        await interaction.response.send_message("❌ No viewable deleted messages in this channel.", ephemeral=True)
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Page must be between 1 and {total_pages}.", ephemeral=True)
        return
    
    embeds = []
    for p in range(total_pages):
        start_idx = p * MESSAGES_PER_PAGE
        end_idx = min((p + 1) * MESSAGES_PER_PAGE, len(messages))
        page_messages = messages[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"📜 Deleted Messages - {target_channel.name}",
            color=discord.Color.blue()
        )
        
        message_list = []
        for i, msg in enumerate(page_messages, start=start_idx + 1):
            content = truncate_content(msg['content'])
            author = msg['author'].name
            message_list.append(f"{i}. **{author}:** {content}")
        
        embed.description = "\n".join(message_list)
        embed.set_footer(text=f"Page {p + 1} of {total_pages} | Use /snipe [number] to view full message")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await interaction.response.send_message(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await interaction.response.send_message(embed=embeds[page - 1], view=view)

# ENHANCED: SPF/SPFORCE command (censored messages for moderators)
@bot.command(name='spforce', aliases=['spf'])
@not_blocked()
async def spforce_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List censored deleted messages (moderators only)"""
    
    # Check permissions
    if not (ctx.author.guild_permissions.manage_messages or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You need Manage Messages permission to use this command.")
        return
    
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages in this channel.")
        return
    
    messages = sniped_messages[channel_id]
    
    # Filter to show only offensive content
    censored_messages = [msg for msg in messages if is_offensive_content(msg['content'])]
    
    if not censored_messages:
        await ctx.send("❌ No censored messages in this channel.")
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(censored_messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Page must be between 1 and {total_pages}.")
        return
    
    embeds = []
    for p in range(total_pages):
        start_idx = p * MESSAGES_PER_PAGE
        end_idx = min((p + 1) * MESSAGES_PER_PAGE, len(censored_messages))
        page_messages = censored_messages[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"🚫 Censored Messages - {target_channel.name}",
            color=discord.Color.red()
        )
        
        message_list = []
        for i, msg in enumerate(page_messages, start=start_idx + 1):
            content = truncate_content(filter_content(msg['content']))  # Show filtered version
            author = msg['author'].name
            message_list.append(f"{i}. **{author}:** {content}")
        
        embed.description = "\n".join(message_list)
        embed.set_footer(text=f"Page {p + 1} of {total_pages} | Moderator view")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[page - 1], view=view)

# ENHANCED: Slash command for SPFORCE
@bot.tree.command(name="spforce", description="List censored deleted messages (moderators only)")
@app_commands.describe(
    channel="Channel to check (optional)",
    page="Page number to view"
)
@check_not_blocked()
async def spforce_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """List censored deleted messages (moderators only)"""
    
    # Check permissions
    if not (interaction.user.guild_permissions.manage_messages or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need Manage Messages permission to use this command.", ephemeral=True)
        return
    
    target_channel = channel or interaction.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("❌ No deleted messages in this channel.", ephemeral=True)
        return
    
    messages = sniped_messages[channel_id]
    
    # Filter to show only offensive content
    censored_messages = [msg for msg in messages if is_offensive_content(msg['content'])]
    
    if not censored_messages:
        await interaction.response.send_message("❌ No censored messages in this channel.", ephemeral=True)
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(censored_messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Page must be between 1 and {total_pages}.", ephemeral=True)
        return
    
    embeds = []
    for p in range(total_pages):
        start_idx = p * MESSAGES_PER_PAGE
        end_idx = min((p + 1) * MESSAGES_PER_PAGE, len(censored_messages))
        page_messages = censored_messages[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"🚫 Censored Messages - {target_channel.name}",
            color=discord.Color.red()
        )
        
        message_list = []
        for i, msg in enumerate(page_messages, start=start_idx + 1):
            content = truncate_content(filter_content(msg['content']))  # Show filtered version
            author = msg['author'].name
            message_list.append(f"{i}. **{author}:** {content}")
        
        embed.description = "\n".join(message_list)
        embed.set_footer(text=f"Page {p + 1} of {total_pages} | Moderator view")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await interaction.response.send_message(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await interaction.response.send_message(embed=embeds[page - 1], view=view)

# ENHANCED: SPL command (deleted links only)
@bot.command(name='spl')
@not_blocked()
async def spl_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List deleted messages that contain links only"""
    
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages in this channel.")
        return
    
    messages = sniped_messages[channel_id]
    
    # Filter to show only messages with links
    link_messages = [msg for msg in messages if has_links(msg['content'])]
    
    if not link_messages:
        await ctx.send("❌ No deleted messages with links in this channel.")
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Page must be between 1 and {total_pages}.")
        return
    
    embeds = []
    for p in range(total_pages):
        start_idx = p * MESSAGES_PER_PAGE
        end_idx = min((p + 1) * MESSAGES_PER_PAGE, len(link_messages))
        page_messages = link_messages[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"🔗 Deleted Links - {target_channel.name}",
            color=discord.Color.orange()
        )
        
        message_list = []
        for i, msg in enumerate(page_messages, start=start_idx + 1):
            content = truncate_content(msg['content'])
            author = msg['author'].name
            message_list.append(f"{i}. **{author}:** {content}")
        
        embed.description = "\n".join(message_list)
        embed.set_footer(text=f"Page {p + 1} of {total_pages} | Links only")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[page - 1], view=view)

# ENHANCED: Slash command for SPL
@bot.tree.command(name="spl", description="List deleted messages that contain links only")
@app_commands.describe(
    channel="Channel to check (optional)",
    page="Page number to view"
)
@check_not_blocked()
async def spl_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """List deleted messages that contain links only"""
    
    target_channel = channel or interaction.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("❌ No deleted messages in this channel.", ephemeral=True)
        return
    
    messages = sniped_messages[channel_id]
    
    # Filter to show only messages with links
    link_messages = [msg for msg in messages if has_links(msg['content'])]
    
    if not link_messages:
        await interaction.response.send_message("❌ No deleted messages with links in this channel.", ephemeral=True)
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Page must be between 1 and {total_pages}.", ephemeral=True)
        return
    
    embeds = []
    for p in range(total_pages):
        start_idx = p * MESSAGES_PER_PAGE
        end_idx = min((p + 1) * MESSAGES_PER_PAGE, len(link_messages))
        page_messages = link_messages[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"🔗 Deleted Links - {target_channel.name}",
            color=discord.Color.orange()
        )
        
        message_list = []
        for i, msg in enumerate(page_messages, start=start_idx + 1):
            content = truncate_content(msg['content'])
            author = msg['author'].name
            message_list.append(f"{i}. **{author}:** {content}")
        
        embed.description = "\n".join(message_list)
        embed.set_footer(text=f"Page {p + 1} of {total_pages} | Links only")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await interaction.response.send_message(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await interaction.response.send_message(embed=embeds[page - 1], view=view)

# Edit snipe command
@bot.command(name='editsnipe', aliases=['es'])
@not_blocked()
async def editsnipe_command(ctx):
    """Show the last edited message"""
    
    channel_id = ctx.channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await ctx.send("❌ No edited messages to snipe in this channel.")
        return
    
    edit_data = edited_messages[channel_id][0]  # Most recent
    
    embed = discord.Embed(title="📝 Edit Sniped", color=discord.Color.orange())
    embed.add_field(name="Before", value=edit_data['before_content'] or "*No content*", inline=False)
    embed.add_field(name="After", value=edit_data['after_content'] or "*No content*", inline=False)
    embed.set_footer(text=f"{edit_data['author']} • {edit_data['edited_at'].strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    await ctx.send(embed=embed)

# ENHANCED: Slash command for editsnipe
@bot.tree.command(name="editsnipe", description="Show the last edited message")
@check_not_blocked()
async def editsnipe_slash(interaction: discord.Interaction):
    """Show the last edited message"""
    
    channel_id = interaction.channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await interaction.response.send_message("❌ No edited messages to snipe in this channel.", ephemeral=True)
        return
    
    edit_data = edited_messages[channel_id][0]  # Most recent
    
    embed = discord.Embed(title="📝 Edit Sniped", color=discord.Color.orange())
    embed.add_field(name="Before", value=edit_data['before_content'] or "*No content*", inline=False)
    embed.add_field(name="After", value=edit_data['after_content'] or "*No content*", inline=False)
    embed.set_footer(text=f"{edit_data['author']} • {edit_data['edited_at'].strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    await interaction.response.send_message(embed=embed)

# ENHANCED: SAYWB command with embed support
@bot.command(name='saywb')
@not_blocked()
async def saywb_command(ctx, *, message):
    """Send webhook message with color"""
    if not ctx.author.guild_permissions.manage_messages and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You need Manage Messages permission to use this command.")
        return
    
    try:
        webhook = await get_or_create_webhook(ctx.channel)
        
        # Simple webhook message
        await webhook.send(
            content=message,
            username=ctx.author.display_name,
            avatar_url=ctx.author.display_avatar.url
        )
        
        # Delete the command message
        try:
            await ctx.message.delete()
        except:
            pass
            
    except Exception as e:
        await ctx.send(f"❌ Failed to send webhook message: {e}")

# ENHANCED: Slash command for SAYWB with embed formatting like Discohook
@bot.tree.command(name="saywb", description="Send embed message to channel")
@app_commands.describe(
    channel="Channel to send message to (optional)",
    title="Embed title",
    description="Embed description", 
    color="Embed color (hex or color name, optional)"
)
@check_not_blocked()
async def saywb_slash(interaction: discord.Interaction, title: str, description: str, channel: discord.TextChannel = None, color: str = None):
    """Send embed message with enhanced formatting like Discohook"""
    
    # Check permissions
    if not (interaction.user.guild_permissions.manage_messages or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need Manage Messages permission to use this command.", ephemeral=True)
        return
    
    target_channel = channel or interaction.channel
    
    # Parse color
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Create embed with enhanced formatting (like Discohook)
    embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color
    )
    
    try:
        # Send directly as bot (no webhook, no profile picture)
        await target_channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Embed sent to {target_channel.mention}", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to send embed: {e}", ephemeral=True)

# ENHANCED: GW command for giveaway reroll
@bot.command(name='gw')
@not_blocked()
async def gw_command(ctx, message_id: int):
    """Reroll a giveaway winner"""
    
    # Check permissions
    if not (is_bot_owner(ctx.author.id) or 
            ctx.author.guild_permissions.administrator or 
            can_host_giveaway(ctx.author)):
        await ctx.send("❌ You don't have permission to reroll giveaways.")
        return
    
    if message_id not in active_giveaways:
        await ctx.send("❌ Giveaway not found or no longer active.")
        return
    
    giveaway = active_giveaways[message_id]
    participants = giveaway['participants']
    
    if not participants:
        await ctx.send("❌ No participants to reroll from.")
        return
    
    # Pick new winner
    winner_id = random.choice(participants)
    winner = bot.get_user(winner_id)
    
    if winner:
        embed = discord.Embed(
            title="🎉 Giveaway Rerolled!",
            description=f"**New Winner:** {winner.mention}\n**Prize:** {giveaway['prize']}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Rerolled by {ctx.author.name}")
        
        # Add reroll button
        view = GiveawayRerollView(message_id, winner)
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send("❌ Could not find the winner.")

# ENHANCED: Slash command for GW
@bot.tree.command(name="gw", description="Reroll a giveaway winner")
@app_commands.describe(message_id="ID of the giveaway message")
@check_not_blocked()
async def gw_slash(interaction: discord.Interaction, message_id: str):
    """Reroll a giveaway winner"""
    
    # Check permissions
    if not (is_bot_owner(interaction.user.id) or 
            interaction.user.guild_permissions.administrator or 
            can_host_giveaway(interaction.user)):
        await interaction.response.send_message("❌ You don't have permission to reroll giveaways.", ephemeral=True)
        return
    
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
        return
    
    if msg_id not in active_giveaways:
        await interaction.response.send_message("❌ Giveaway not found or no longer active.", ephemeral=True)
        return
    
    giveaway = active_giveaways[msg_id]
    participants = giveaway['participants']
    
    if not participants:
        await interaction.response.send_message("❌ No participants to reroll from.", ephemeral=True)
        return
    
    # Pick new winner
    winner_id = random.choice(participants)
    winner = bot.get_user(winner_id)
    
    if winner:
        embed = discord.Embed(
            title="🎉 Giveaway Rerolled!",
            description=f"**New Winner:** {winner.mention}\n**Prize:** {giveaway['prize']}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Rerolled by {interaction.user.name}")
        
        # Add reroll button
        view = GiveawayRerollView(msg_id, winner)
        await interaction.response.send_message(embed=embed, view=view)
    else:
        await interaction.response.send_message("❌ Could not find the winner.", ephemeral=True)

# ENHANCED: Ping command
@bot.tree.command(name="ping", description="Show bot latency")
@check_not_blocked()
async def ping_slash(interaction: discord.Interaction):
    """Show bot latency"""
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"**Latency:** {latency}ms",
        color=discord.Color.green() if latency < 100 else discord.Color.orange() if latency < 200 else discord.Color.red()
    )
    
    await interaction.response.send_message(embed=embed)

# ENHANCED: Prefix command
@bot.tree.command(name="prefix", description="Change server prefix")
@app_commands.describe(new_prefix="New prefix for the server (1 character)")
@check_not_blocked()
async def prefix_slash(interaction: discord.Interaction, new_prefix: str):
    """Change server prefix"""
    
    # Check permissions
    if not (interaction.user.guild_permissions.administrator or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need Administrator permission to change the prefix.", ephemeral=True)
        return
    
    if len(new_prefix) != 1:
        await interaction.response.send_message("❌ Prefix must be exactly 1 character.", ephemeral=True)
        return
    
    # Update prefix
    custom_prefixes[interaction.guild.id] = new_prefix
    
    embed = discord.Embed(
        title="✅ Prefix Updated",
        description=f"Server prefix changed to: `{new_prefix}`",
        color=discord.Color.green()
    )
    
    await interaction.response.send_message(embed=embed)

# ENHANCED: Create reaction roles command (fixed)
@bot.tree.command(name="create", description="Create reaction roles with 1-6 emoji-role pairs")
@app_commands.describe(
    channel="Channel to send the reaction role message",
    content="Message content",
    emoji1="First emoji", role1="First role",
    emoji2="Second emoji (optional)", role2="Second role (optional)",
    emoji3="Third emoji (optional)", role3="Third role (optional)",
    emoji4="Fourth emoji (optional)", role4="Fourth role (optional)",
    emoji5="Fifth emoji (optional)", role5="Fifth role (optional)",
    emoji6="Sixth emoji (optional)", role6="Sixth role (optional)"
)
@check_not_blocked()
async def create_slash(interaction: discord.Interaction, 
                      channel: discord.TextChannel, 
                      content: str,
                      emoji1: str, role1: discord.Role,
                      emoji2: str = None, role2: discord.Role = None,
                      emoji3: str = None, role3: discord.Role = None,
                      emoji4: str = None, role4: discord.Role = None,
                      emoji5: str = None, role5: discord.Role = None,
                      emoji6: str = None, role6: discord.Role = None):
    """Create reaction roles with 1-6 emoji-role pairs"""
    
    # Check permissions
    if not (interaction.user.guild_permissions.manage_roles or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need Manage Roles permission to use this command.", ephemeral=True)
        return
    
    # Build emoji-role mapping
    emoji_role_pairs = [(emoji1, role1)]
    
    if emoji2 and role2:
        emoji_role_pairs.append((emoji2, role2))
    if emoji3 and role3:
        emoji_role_pairs.append((emoji3, role3))
    if emoji4 and role4:
        emoji_role_pairs.append((emoji4, role4))
    if emoji5 and role5:
        emoji_role_pairs.append((emoji5, role5))
    if emoji6 and role6:
        emoji_role_pairs.append((emoji6, role6))
    
    # Create embed
    embed = discord.Embed(
        title="🎭 Reaction Roles",
        description=content,
        color=discord.Color.blue()
    )
    
    role_list = []
    for emoji, role in emoji_role_pairs:
        role_list.append(f"{emoji} - {role.mention}")
    
    embed.add_field(name="Available Roles", value="\n".join(role_list), inline=False)
    embed.set_footer(text="React with the emoji to get the role!")
    
    try:
        # Send message
        message = await channel.send(embed=embed)
        
        # Add reactions
        role_mapping = {}
        for emoji, role in emoji_role_pairs:
            try:
                await message.add_reaction(emoji)
                role_mapping[emoji] = role.id
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to add reaction {emoji}: {e}", ephemeral=True)
                return
        
        # Store reaction role mapping
        reaction_roles[message.id] = role_mapping
        
        await interaction.response.send_message(f"✅ Reaction role message created in {channel.mention}", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to create reaction role message: {e}", ephemeral=True)

# Help command
@bot.command(name='help')
@not_blocked()
async def help_command(ctx):
    """Show help with pagination"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# ENHANCED: Slash command for help
@bot.tree.command(name="help", description="Show all bot commands with pagination")
@check_not_blocked()
async def help_slash(interaction: discord.Interaction):
    """Show help with pagination"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await interaction.response.send_message(embed=embed, view=view)

# Management command (bot owner only)
@bot.command(name='manage')
@not_blocked()
async def manage_command(ctx):
    """Bot management panel (owner only)"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ This command is restricted to the bot owner.")
        return
    
    view = ManagePaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# ENHANCED: Slash command for manage
@bot.tree.command(name="manage", description="Bot management panel (owner only)")
@check_not_blocked()
async def manage_slash(interaction: discord.Interaction):
    """Bot management panel (owner only)"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ This command is restricted to the bot owner.", ephemeral=True)
        return
    
    view = ManagePaginationView()
    embed = view.get_embed()
    await interaction.response.send_message(embed=embed, view=view)

# Block user command (bot owner only)
@bot.command(name='block')
@not_blocked()
async def block_command(ctx, *, user_input):
    """Block a user from using bot functions"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ This command is restricted to the bot owner.")
        return
    
    # Try to find user
    try:
        user_id = int(user_input)
        user = bot.get_user(user_id)
    except ValueError:
        user = find_user_globally(user_input)
    
    if not user:
        await ctx.send("❌ User not found.")
        return
    
    if user.id in blocked_users:
        await ctx.send(f"❌ {user.name} is already blocked.")
        return
    
    blocked_users.add(user.id)
    await ctx.send(f"✅ {user.name} has been blocked from using bot functions.")

# ENHANCED: Slash command for block
@bot.tree.command(name="block", description="Block a user from using bot functions (owner only)")
@app_commands.describe(user="User to block")
@check_not_blocked()
async def block_slash(interaction: discord.Interaction, user: discord.User):
    """Block a user from using bot functions"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ This command is restricted to the bot owner.", ephemeral=True)
        return
    
    if user.id in blocked_users:
        await interaction.response.send_message(f"❌ {user.name} is already blocked.", ephemeral=True)
        return
    
    blocked_users.add(user.id)
    await interaction.response.send_message(f"✅ {user.name} has been blocked from using bot functions.")

# Unblock user command (bot owner only)
@bot.tree.command(name="unblock", description="Unblock a user from using bot functions (owner only)")
@app_commands.describe(user="User to unblock")
async def unblock_slash(interaction: discord.Interaction, user: discord.User):
    """Unblock a user from using bot functions"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ This command is restricted to the bot owner.", ephemeral=True)
        return
    
    if user.id not in blocked_users:
        await interaction.response.send_message(f"❌ {user.name} is not blocked.", ephemeral=True)
        return
    
    blocked_users.remove(user.id)
    await interaction.response.send_message(f"✅ {user.name} has been unblocked.")

# ENHANCED: Giveaway command with seconds support
@bot.tree.command(name="giveaway", description="Create a giveaway with requirements")
@app_commands.describe(
    duration="Duration (e.g., 1h, 30m, 45s)",
    winners="Number of winners",
    prize="Giveaway prize",
    required_messages="Required message count (optional)",
    time_in_server="Time in server required (e.g., 1d, 2h) (optional)",
    required_role="Required role name (optional)",
    blacklisted_role="Blacklisted role name (optional)"
)
@check_not_blocked()
async def giveaway_slash(interaction: discord.Interaction, 
                        duration: str, 
                        winners: int, 
                        prize: str,
                        required_messages: int = None,
                        time_in_server: str = None,
                        required_role: str = None,
                        blacklisted_role: str = None):
    """Create a giveaway with requirements and seconds support"""
    
    # Check if user can host giveaways
    if not can_host_giveaway(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to host giveaways.", ephemeral=True)
        return
    
    # Parse duration with seconds support
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        await interaction.response.send_message("❌ Invalid duration format. Use format like: 1h, 30m, 45s", ephemeral=True)
        return
    
    if winners < 1 or winners > 10:
        await interaction.response.send_message("❌ Number of winners must be between 1 and 10.", ephemeral=True)
        return
    
    # Build requirements
    requirements = {}
    requirement_text = []
    
    if required_messages:
        requirements['messages'] = required_messages
        requirement_text.append(f"📝 {required_messages} messages")
    
    if time_in_server:
        time_seconds = parse_time_string(time_in_server)
        if time_seconds > 0:
            requirements['time_in_server'] = time_seconds
            requirement_text.append(f"⏰ {format_duration(time_seconds)} in server")
    
    if required_role:
        requirements['required_role'] = required_role
        requirement_text.append(f"✅ Role: {required_role}")
    
    if blacklisted_role:
        requirements['blacklisted_role'] = blacklisted_role
        requirement_text.append(f"❌ Cannot have role: {blacklisted_role}")
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Create embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
        color=discord.Color.gold()
    )
    
    if requirement_text:
        embed.add_field(name="Requirements", value="\n".join(requirement_text), inline=False)
    
    embed.set_footer(text=f"Hosted by {interaction.user.name}")
    embed.timestamp = end_time
    
    # Send message with buttons
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    # Add giveaway view
    view = GiveawayView(message.id)
    await message.edit(embed=embed, view=view)
    
    # Store giveaway data
    active_giveaways[message.id] = {
        'prize': prize,
        'winners': winners,
        'end_time': end_time,
        'host_id': interaction.user.id,
        'channel_id': interaction.channel.id,
        'guild_id': interaction.guild.id,
        'guild_name': interaction.guild.name,
        'participants': [],
        'requirements': requirements if requirements else None,
        'ended': False
    }

# Add other commands with slash support
@bot.command(name='say')
@not_blocked()
async def say_command(ctx, *, message):
    """Send a normal message"""
    if not ctx.author.guild_permissions.manage_messages and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You need Manage Messages permission to use this command.")
        return
    
    await ctx.send(message)
    try:
        await ctx.message.delete()
    except:
        pass

@bot.tree.command(name="say", description="Send a normal message")
@app_commands.describe(message="Message to send")
@check_not_blocked()
async def say_slash(interaction: discord.Interaction, message: str):
    """Send a normal message"""
    if not (interaction.user.guild_permissions.manage_messages or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need Manage Messages permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.send_message(message)

# Add other enhanced commands...
@bot.command(name='namelock', aliases=['nl'])
@not_blocked()
async def namelock_command(ctx, user: discord.Member, *, nickname):
    """Lock a user's nickname"""
    if not ctx.author.guild_permissions.manage_nicknames and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You need Manage Nicknames permission to use this command.")
        return
    
    try:
        await user.edit(nick=nickname, reason=f"Namelocked by {ctx.author}")
        namelocked_users[user.id] = nickname
        await ctx.send(f"✅ {user.mention} has been namelocked to `{nickname}`")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname.")

@bot.tree.command(name="namelock", description="Lock a user's nickname")
@app_commands.describe(user="User to namelock", nickname="Nickname to lock to")
@check_not_blocked()
async def namelock_slash(interaction: discord.Interaction, user: discord.Member, nickname: str):
    """Lock a user's nickname"""
    if not (interaction.user.guild_permissions.manage_nicknames or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need Manage Nicknames permission to use this command.", ephemeral=True)
        return
    
    try:
        await user.edit(nick=nickname, reason=f"Namelocked by {interaction.user}")
        namelocked_users[user.id] = nickname
        await interaction.response.send_message(f"✅ {user.mention} has been namelocked to `{nickname}`")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change that user's nickname.", ephemeral=True)

# Run the bot with environment variable
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN environment variable not found!")
        exit(1)
    
    bot.run(token)
