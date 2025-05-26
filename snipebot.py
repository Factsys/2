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

# ENHANCED: Store up to 100 deleted messages per channel
sniped_messages = {}  # {channel_id: [list of messages]}
edited_messages = {}
blacklisted_users = {}  # Format: {guild_id: [user_id1, user_id2, ...]}

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

# FIXED: Enhanced media URL detection
def get_media_url(content, attachments):
    """Get media URL from content or attachments with enhanced detection"""
    # Priority 1: Check for attachments first (Discord files)
    if attachments:
        for attachment in attachments:
            if any(attachment.filename.lower().endswith(ext) for ext in ['.gif', '.png', '.jpg', '.jpeg', '.webp', '.mp4', '.mov']):
                return attachment.url
    
    # Priority 2: Check for various media links in content
    if content:
        # Tenor GIFs
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

# Custom check that allows administrators and owners to bypass permission requirements
def has_permission_or_is_admin():
    async def predicate(ctx):
        # Check if user is blacklisted
        if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
            return False  # Silently fail for blacklisted users
            
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
        # Check if user is blacklisted
        if interaction.guild and interaction.guild.id in blacklisted_users and interaction.user.id in blacklisted_users[interaction.guild.id]:
            # Silently fail - we'll return False but not raise an exception
            # This allows the command to silently fail for blacklisted users
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

# Help Pagination View
class HelpPaginationView(discord.ui.View):
    def __init__(self, timeout=300):
        super().__init__(timeout=timeout)
        self.current_page = 0
        self.pages = [
            {
                "title": "📜 FACTSY Commands - Page 1",
                "fields": [
                    ("**Message Tracking**", "`,snipe` `,s` - Show last deleted message\n`,editsnipe` `,es` - Show last edited message\n`,sp [channel] [page]` - List all deleted messages\n`,spforce` `,spf` - Moderator-only unfiltered snipe\n`,spl [channel] [page]` - Show deleted links only", False),
                    ("**Moderation**", "`,namelock` `,nl` - Lock user's nickname\n`,unl` - Unlock user's nickname\n`,rename` `,re` - Change user's nickname\n`,say` - Send normal message\n`,saywb` - Send webhook message with color", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 2", 
                "fields": [
                    ("**Giveaways**", "`,gw [id]` - Reroll giveaway winner\n`/giveaway` - Create advanced giveaway\n`/giveaway-host-role` - Set host roles", False),
                    ("**Management**", "`,block` - Block user from bot\n`,mess` - DM user globally\n`,role` - Add role to user\n`,namelockimmune` `,nli` - Make user immune to namelock", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 3",
                "fields": [
                    ("**Reaction Roles**", "`,create` - Create reaction role message\n`/create` - Clean reaction roles with 1-10 options", False),
                    ("**Bot Owner**", "`,manage` - Bot management panel\n`/unblock` - Unblock user from bot", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 4",
                "fields": [
                    ("**Info**", "All commands support both prefix (,) and slash (/) versions\nModerators can use most commands\nBlocked users cannot use any bot functions", False),
                    ("**Usage Examples**", "`,mess wer hello` - DM user with partial name\n`,saywb Hello world! red` - Send colored webhook message\n`,gw 123456789` - Reroll giveaway", False)
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
        'attachments': [att.url for att in message.attachments],
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
async def on_member_update(before, after):
    """Track nickname changes for namelock enforcement"""
    # Only check if the nickname changed
    if before.nick == after.nick:
        return
    
    user_id = after.id
    
    # Check if user is namelocked
    if user_id in namelocked_users:
        locked_nick = namelocked_users[user_id]
        
        # Check if user is immune to namelock
        if user_id in namelock_immune_users:
            return
        
        # If the user's new nickname doesn't match the locked one, change it back
        if after.nick != locked_nick:
            try:
                await after.edit(nick=locked_nick, reason="Namelock enforcement")
                print(f"Enforced namelock for {after.name} (ID: {user_id})")
            except discord.Forbidden:
                print(f"Cannot enforce namelock for {after.name} - insufficient permissions")
            except Exception as e:
                print(f"Error enforcing namelock for {after.name}: {e}")

@bot.event
async def on_message(message):
    """Process messages and track message counts"""
    # Don't respond to bots
    if message.author.bot:
        return
    
    # Check if user is blocked from using any bot functions
    if is_user_blocked(message.author.id):
        return
    
    # Count messages for stats
    if message.guild:
        guild_id = message.guild.id
        user_id = message.author.id
        increment_user_message_count(guild_id, user_id)
    
    # Process commands
    await bot.process_commands(message)

# Background task to check giveaways
@tasks.loop(seconds=30)
async def giveaway_checker():
    """Check for ended giveaways every 30 seconds"""
    current_time = datetime.utcnow()
    ended_giveaways = []
    
    for message_id, giveaway_data in active_giveaways.items():
        end_time = giveaway_data['end_time']
        if current_time >= end_time:
            ended_giveaways.append(message_id)
    
    for message_id in ended_giveaways:
        await end_giveaway(message_id)

async def end_giveaway(message_id):
    """End a giveaway and pick winners"""
    if message_id not in active_giveaways:
        return
    
    giveaway_data = active_giveaways[message_id]
    
    try:
        # Get the message
        channel = bot.get_channel(giveaway_data['channel_id'])
        if not channel:
            del active_giveaways[message_id]
            return
            
        message = await channel.fetch_message(message_id)
        if not message:
            del active_giveaways[message_id]
            return
        
        # Get participants (users who reacted with 🎉)
        participants = []
        for reaction in message.reactions:
            if str(reaction.emoji) == "🎉":
                async for user in reaction.users():
                    if not user.bot and user.id != bot.user.id:
                        # Check if user meets requirements
                        if message.guild:
                            member = message.guild.get_member(user.id)
                            if member:
                                meets_req, _ = check_giveaway_requirements(member, giveaway_data.get('requirements'))
                                if meets_req:
                                    participants.append(member)
                        else:
                            participants.append(user)
                break
        
        # Pick winners
        winners = []
        num_winners = min(giveaway_data['winners'], len(participants))
        
        if participants and num_winners > 0:
            winners = random.sample(participants, num_winners)
        
        # Create result embed
        embed = discord.Embed(title="🎉 Giveaway Ended!", color=discord.Color.red())
        embed.add_field(name="Prize", value=giveaway_data['prize'], inline=False)
        
        if winners:
            winner_mentions = ", ".join([winner.mention for winner in winners])
            embed.add_field(name=f"Winner{'s' if len(winners) > 1 else ''}", value=winner_mentions, inline=False)
            embed.add_field(name="Participants", value=str(len(participants)), inline=True)
        else:
            embed.add_field(name="Winners", value="No valid participants", inline=False)
        
        embed.add_field(name="Hosted by", value=f"<@{giveaway_data['host_id']}>", inline=True)
        embed.set_footer(text="Giveaway ended")
        embed.timestamp = datetime.utcnow()
        
        # Update the original message
        await message.edit(embed=embed)
        
        # Send winner announcement
        if winners:
            winner_text = f"🎉 Congratulations {winner_mentions}! You won **{giveaway_data['prize']}**!"
            await channel.send(winner_text)
        
        # Remove from active giveaways
        del active_giveaways[message_id]
        
    except Exception as e:
        print(f"Error ending giveaway {message_id}: {e}")
        # Remove from active giveaways anyway to prevent repeated errors
        if message_id in active_giveaways:
            del active_giveaways[message_id]

# SLASH COMMANDS

@bot.tree.command(name="ping", description="Check bot latency and status")
@check_not_blocked()
async def ping_slash(interaction: discord.Interaction):
    # Check for blacklist first
    if interaction.guild and interaction.guild.id in blacklisted_users and interaction.user.id in blacklisted_users[interaction.guild.id]:
        return  # Silently ignore
        
    latency = round(bot.latency * 1000)
    uptime = format_uptime(time.time() - BOT_START_TIME)
    
    embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
    embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
    embed.add_field(name="Uptime", value=uptime, inline=True)
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="snipe", description="Show recently deleted messages")
@app_commands.describe(
    page="Page number (1-10)",
    list_view="Show multiple messages",
    channel="Channel to snipe from",
    user="Show messages from specific user only"
)
@check_not_blocked()
async def snipe_slash(interaction: discord.Interaction, page: int = 1, list_view: bool = False, channel: discord.TextChannel = None, user: discord.Member = None):
    # Check for blacklist first
    if interaction.guild and interaction.guild.id in blacklisted_users and interaction.user.id in blacklisted_users[interaction.guild.id]:
        return  # Silently ignore
        
    target_channel = channel or interaction.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await interaction.response.send_message(f"No recently deleted messages in {target_channel.mention}.", ephemeral=True)
        return
    
    messages = sniped_messages[target_channel.id]
    
    # Filter by user if specified
    if user:
        messages = [msg for msg in messages if msg['author'].id == user.id]
        if not messages:
            await interaction.response.send_message(f"No recently deleted messages from {user.mention} in {target_channel.mention}.", ephemeral=True)
            return
    
    if list_view:
        # Show list view
        max_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
        
        if page < 1 or page > max_pages:
            await interaction.response.send_message(f"Page must be between 1 and {max_pages}.", ephemeral=True)
            return
        
        start_idx = (page - 1) * MESSAGES_PER_PAGE
        end_idx = min(start_idx + MESSAGES_PER_PAGE, len(messages))
        page_messages = messages[start_idx:end_idx]
        
        embed = discord.Embed(title=f"📜 Recently Deleted Messages - {target_channel.name}", color=discord.Color.gold())
        
        for i, msg in enumerate(page_messages, start_idx + 1):
            content = msg['content']
            
            # Apply content filter for regular users
            if not interaction.user.guild_permissions.manage_messages:
                content = filter_content(content)
            
            # Handle attachments
            attachment_info = ""
            if msg['attachments']:
                attachment_info = f" [📎 {len(msg['attachments'])} attachment(s)]"
            
            # Format timestamp
            timestamp = msg['deleted_at'].strftime("%H:%M:%S")
            
            field_value = f"**Content:** {truncate_content(content) or '*No content*'}{attachment_info}\n**Time:** {timestamp}"
            
            embed.add_field(
                name=f"{i}. {msg['author'].display_name}",
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text=f"Page {page} of {max_pages} | Total: {len(messages)} messages")
        
    else:
        # Single message view
        if page < 1 or page > len(messages):
            await interaction.response.send_message(f"Page must be between 1 and {len(messages)}.", ephemeral=True)
            return
        
        msg = messages[page - 1]
        content = msg['content']
        
        # Apply content filter for regular users
        if not interaction.user.guild_permissions.manage_messages:
            content = filter_content(content)
        
        embed = discord.Embed(title="📜 Sniped Message", color=discord.Color.gold())
        embed.add_field(name="Content", value=content or "*No text content*", inline=False)
        embed.add_field(name="Author", value=msg['author'].mention, inline=True)
        embed.add_field(name="Channel", value=target_channel.mention, inline=True)
        embed.add_field(name="Deleted", value=msg['deleted_at'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
        
        # Handle attachments
        if msg['attachments']:
            attachment_list = "\n".join([f"[{att.split('/')[-1]}]({att})" for att in msg['attachments'][:5]])
            if len(msg['attachments']) > 5:
                attachment_list += f"\n... and {len(msg['attachments']) - 5} more"
            embed.add_field(name="Attachments", value=attachment_list, inline=False)
            
            # Set first image as embed image
            for att in msg['attachments']:
                if any(ext in att.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    embed.set_image(url=att)
                    break
        
        embed.set_footer(text=f"Message {page} of {len(messages)}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="snipeedit", description="Show recently edited messages")
@app_commands.describe(
    page="Page number",
    list_view="Show multiple messages",
    channel="Channel to check",
    user="Show edits from specific user only"
)
@check_not_blocked()
async def snipeedit_slash(interaction: discord.Interaction, page: int = 1, list_view: bool = False, channel: discord.TextChannel = None, user: discord.Member = None):
    # Check for blacklist first
    if interaction.guild and interaction.guild.id in blacklisted_users and interaction.user.id in blacklisted_users[interaction.guild.id]:
        return  # Silently ignore
        
    target_channel = channel or interaction.channel
    
    if target_channel.id not in edited_messages or not edited_messages[target_channel.id]:
        await interaction.response.send_message(f"No recently edited messages in {target_channel.mention}.", ephemeral=True)
        return
    
    messages = edited_messages[target_channel.id]
    
    # Filter by user if specified
    if user:
        messages = [msg for msg in messages if msg['author'].id == user.id]
        if not messages:
            await interaction.response.send_message(f"No recently edited messages from {user.mention} in {target_channel.mention}.", ephemeral=True)
            return
    
    if list_view:
        # Show list view
        max_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
        
        if page < 1 or page > max_pages:
            await interaction.response.send_message(f"Page must be between 1 and {max_pages}.", ephemeral=True)
            return
        
        start_idx = (page - 1) * MESSAGES_PER_PAGE
        end_idx = min(start_idx + MESSAGES_PER_PAGE, len(messages))
        page_messages = messages[start_idx:end_idx]
        
        embed = discord.Embed(title=f"✏️ Recently Edited Messages - {target_channel.name}", color=discord.Color.blue())
        
        for i, msg in enumerate(page_messages, start_idx + 1):
            before_content = truncate_content(msg['before_content'])
            after_content = truncate_content(msg['after_content'])
            timestamp = msg['edited_at'].strftime("%H:%M:%S")
            
            field_value = f"**Before:** {before_content}\n**After:** {after_content}\n**Time:** {timestamp}"
            
            embed.add_field(
                name=f"{i}. {msg['author'].display_name}",
                value=field_value,
                inline=False
            )
        
        embed.set_footer(text=f"Page {page} of {max_pages} | Total: {len(messages)} edits")
        
    else:
        # Single edit view
        if page < 1 or page > len(messages):
            await interaction.response.send_message(f"Page must be between 1 and {len(messages)}.", ephemeral=True)
            return
        
        msg = messages[page - 1]
        
        embed = discord.Embed(title="✏️ Edited Message", color=discord.Color.blue())
        embed.add_field(name="Before", value=msg['before_content'] or "*No content*", inline=False)
        embed.add_field(name="After", value=msg['after_content'] or "*No content*", inline=False)
        embed.add_field(name="Author", value=msg['author'].mention, inline=True)
        embed.add_field(name="Channel", value=target_channel.mention, inline=True)
        embed.add_field(name="Edited", value=msg['edited_at'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
        
        embed.set_footer(text=f"Edit {page} of {len(messages)}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="giveaway", description="Create an advanced giveaway")
@app_commands.describe(
    duration="Duration (e.g., 1h, 30m, 2d)",
    winners="Number of winners",
    prize="What are you giving away?",
    requirements="Requirements (optional)"
)
@check_not_blocked()
async def giveaway_slash(interaction: discord.Interaction, duration: str, winners: int, prize: str, requirements: str = None):
    # Check for blacklist first
    if interaction.guild and interaction.guild.id in blacklisted_users and interaction.user.id in blacklisted_users[interaction.guild.id]:
        return  # Silently ignore
        
    # Check if user can host giveaways
    if not can_host_giveaway(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to host giveaways.", ephemeral=True)
        return
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds < 60:  # Minimum 1 minute
        await interaction.response.send_message("❌ Duration must be at least 1 minute.", ephemeral=True)
        return
    
    if duration_seconds > 2592000:  # Maximum 30 days
        await interaction.response.send_message("❌ Duration cannot exceed 30 days.", ephemeral=True)
        return
    
    # Validate winners
    if winners < 1 or winners > 20:
        await interaction.response.send_message("❌ Number of winners must be between 1 and 20.", ephemeral=True)
        return
    
    # Parse requirements
    req_dict = {}
    if requirements:
        req_parts = requirements.split(',')
        for part in req_parts:
            part = part.strip()
            if part.startswith('messages:'):
                try:
                    req_dict['messages'] = int(part.split(':')[1])
                except ValueError:
                    pass
            elif part.startswith('time:'):
                time_req = part.split(':', 1)[1]
                req_dict['time_in_server'] = parse_time_string(time_req)
            elif part.startswith('role:'):
                req_dict['required_role'] = part.split(':', 1)[1]
            elif part.startswith('no-role:'):
                req_dict['blacklisted_role'] = part.split(':', 1)[1]
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Create giveaway embed
    embed = discord.Embed(title="🎉 GIVEAWAY 🎉", color=discord.Color.gold())
    embed.add_field(name="Prize", value=prize, inline=False)
    embed.add_field(name="Winners", value=str(winners), inline=True)
    embed.add_field(name="Ends", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
    embed.add_field(name="Hosted by", value=interaction.user.mention, inline=True)
    
    if req_dict:
        req_text = []
        if 'messages' in req_dict:
            req_text.append(f"• {req_dict['messages']} messages")
        if 'time_in_server' in req_dict:
            req_text.append(f"• {format_duration(req_dict['time_in_server'])} in server")
        if 'required_role' in req_dict:
            req_text.append(f"• Role: {req_dict['required_role']}")
        if 'blacklisted_role' in req_dict:
            req_text.append(f"• Cannot have role: {req_dict['blacklisted_role']}")
        
        if req_text:
            embed.add_field(name="Requirements", value="\n".join(req_text), inline=False)
    
    embed.add_field(name="How to enter", value="React with 🎉 to enter!", inline=False)
    embed.set_footer(text="Good luck!")
    embed.timestamp = end_time
    
    # Send the giveaway
    await interaction.response.send_message(embed=embed)
    giveaway_msg = await interaction.original_response()
    await giveaway_msg.add_reaction("🎉")
    
    # Store giveaway data
    active_giveaways[giveaway_msg.id] = {
        'prize': prize,
        'winners': winners,
        'end_time': end_time,
        'host_id': interaction.user.id,
        'channel_id': interaction.channel.id,
        'requirements': req_dict
    }

@bot.tree.command(name="giveaway-host-role", description="Set roles that can host giveaways")
@app_commands.describe(role="Role to add/remove from giveaway hosts")
@app_commands.default_permissions(administrator=True)
@check_not_blocked()
async def giveaway_host_role_slash(interaction: discord.Interaction, role: discord.Role):
    # Check for blacklist first
    if interaction.guild and interaction.guild.id in blacklisted_users and interaction.user.id in blacklisted_users[interaction.guild.id]:
        return  # Silently ignore
        
    guild_id = interaction.guild.id
    
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = []
    
    if role.id in giveaway_host_roles[guild_id]:
        # Remove role
        giveaway_host_roles[guild_id].remove(role.id)
        await interaction.response.send_message(f"✅ Removed {role.mention} from giveaway host roles.", ephemeral=True)
    else:
        # Add role
        giveaway_host_roles[guild_id].append(role.id)
        await interaction.response.send_message(f"✅ Added {role.mention} to giveaway host roles.", ephemeral=True)

@bot.tree.command(name="create", description="Create a reaction role message with up to 10 options")
@app_commands.describe(
    title="Title of the reaction role message",
    description="Description text",
    color="Embed color (hex or name)"
)
@app_commands.default_permissions(manage_roles=True)
@check_not_blocked()
async def create_reaction_roles_slash(interaction: discord.Interaction, title: str, description: str = None, color: str = "blue"):
    # Check for blacklist first
    if interaction.guild and interaction.guild.id in blacklisted_users and interaction.user.id in blacklisted_users[interaction.guild.id]:
        return  # Silently ignore
        
    # Parse color
    embed_color = parse_color(color)
    
    # Create the embed
    embed = discord.Embed(title=title, color=embed_color)
    if description:
        embed.description = description
    
    # Create a modal for role selection
    class RoleSelectionModal(discord.ui.Modal, title="Reaction Role Setup"):
        def __init__(self):
            super().__init__()
            
            # Add text inputs for up to 10 role-emoji pairs
            self.role_inputs = []
            for i in range(1, 11):
                text_input = discord.ui.TextInput(
                    label=f"Option {i} (emoji:@role)",
                    placeholder=f"🎮:@Gamer or leave empty",
                    required=False,
                    max_length=100
                )
                self.add_item(text_input)
                self.role_inputs.append(text_input)
        
        async def on_submit(self, modal_interaction: discord.Interaction):
            role_mapping = {}
            embed_fields = []
            
            for i, text_input in enumerate(self.role_inputs, 1):
                if not text_input.value:
                    continue
                
                try:
                    # Parse input (emoji:@role or emoji:role_name)
                    if ':' not in text_input.value:
                        continue
                    
                    emoji_part, role_part = text_input.value.split(':', 1)
                    emoji = emoji_part.strip()
                    
                    # Find role
                    role = None
                    if role_part.startswith('<@&') and role_part.endswith('>'):
                        # Role mention
                        role_id = int(role_part[3:-1])
                        role = modal_interaction.guild.get_role(role_id)
                    elif role_part.startswith('@'):
                        # @role format
                        role_name = role_part[1:].strip()
                        role = discord.utils.get(modal_interaction.guild.roles, name=role_name)
                    else:
                        # Plain role name
                        role_name = role_part.strip()
                        role = discord.utils.get(modal_interaction.guild.roles, name=role_name)
                    
                    if role and emoji:
                        role_mapping[emoji] = role.id
                        embed_fields.append((emoji, role.mention))
                
                except (ValueError, IndexError):
                    continue
            
            if not role_mapping:
                await modal_interaction.response.send_message("❌ No valid role-emoji pairs found.", ephemeral=True)
                return
            
            # Update embed with role options
            for emoji, role_mention in embed_fields:
                embed.add_field(name=f"{emoji} {role_mention}", value="React to get this role", inline=False)
            
            # Send the message
            await modal_interaction.response.send_message(embed=embed)
            msg = await modal_interaction.original_response()
            
            # Add reactions and store mapping
            for emoji in role_mapping.keys():
                try:
                    await msg.add_reaction(emoji)
                except:
                    pass
            
            reaction_roles[msg.id] = role_mapping
    
    # Show the modal
    modal = RoleSelectionModal()
    await interaction.response.send_modal(modal)

@bot.tree.command(name="unblock", description="Unblock a user from using bot functions (BOT OWNER ONLY)")
@app_commands.describe(user="User to unblock")
async def unblock_slash(interaction: discord.Interaction, user: discord.User):
    # BOT OWNER ONLY - Replace with your Discord ID
    if interaction.user.id != 1201554061863776276:  # Replace with your Discord ID
        await interaction.response.send_message("❌ This command is for bot owner only.", ephemeral=True)
        return
    
    if user.id in blocked_users:
        blocked_users.remove(user.id)
        await interaction.response.send_message(f"✅ Unblocked {user.mention} from using bot functions.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ {user.mention} is not blocked.", ephemeral=True)

@bot.tree.command(name="blacklist", description="Blacklist a user from using bot commands")
@app_commands.describe(user="User to blacklist")
@check_admin_or_permissions(administrator=True)  # Only admins can blacklist
async def blacklist_slash(interaction: discord.Interaction, user: discord.Member):
    # Make sure the guild exists in our dict
    if interaction.guild.id not in blacklisted_users:
        blacklisted_users[interaction.guild.id] = []
    
    # Check if user is already blacklisted
    if user.id in blacklisted_users[interaction.guild.id]:
        embed = discord.Embed(
            title="⚠️ Already Blacklisted",
            description=f"{user.mention} is already blacklisted.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Check if user is server owner or an admin
    if user.id == interaction.guild.owner_id:
        embed = discord.Embed(
            title="❌ Cannot Blacklist",
            description="You cannot blacklist the server owner.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    if user.guild_permissions.administrator and user.id != interaction.user.id:
        embed = discord.Embed(
            title="⚠️ Warning",
            description=f"You are blacklisting an administrator ({user.mention}).",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Add user to blacklist
    blacklisted_users[interaction.guild.id].append(user.id)
    
    embed = discord.Embed(
        title="✅ User Blacklisted",
        description=f"{user.mention} has been blacklisted from using bot commands.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unblacklist", description="Remove a user from the blacklist")
@app_commands.describe(user="User to unblacklist")
@check_admin_or_permissions(administrator=True)  # Only admins can unblacklist
async def unblacklist_slash(interaction: discord.Interaction, user: discord.Member):
    # Check if guild has any blacklisted users
    if interaction.guild.id not in blacklisted_users or not blacklisted_users[interaction.guild.id]:
        embed = discord.Embed(
            title="ℹ️ No Blacklisted Users",
            description="There are no blacklisted users in this server.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Check if user is blacklisted
    if user.id not in blacklisted_users[interaction.guild.id]:
        embed = discord.Embed(
            title="ℹ️ Not Blacklisted",
            description=f"{user.mention} is not blacklisted.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Remove user from blacklist
    blacklisted_users[interaction.guild.id].remove(user.id)
    
    embed = discord.Embed(
        title="✅ User Unblacklisted",
        description=f"{user.mention} has been removed from the blacklist.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="blacklisted", description="View all blacklisted users")
@check_admin_or_permissions(administrator=True)  # Only admins can view blacklist
async def blacklisted_slash(interaction: discord.Interaction):
    # Check if guild has any blacklisted users
    if interaction.guild.id not in blacklisted_users or not blacklisted_users[interaction.guild.id]:
        embed = discord.Embed(
            title="ℹ️ No Blacklisted Users",
            description="There are no blacklisted users in this server.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Create list of blacklisted users
    blacklist_text = ""
    for user_id in blacklisted_users[interaction.guild.id]:
        user = interaction.guild.get_member(user_id)
        if user:
            blacklist_text += f"• {user.mention} ({user.name})\n"
        else:
            blacklist_text += f"• Unknown User (ID: {user_id})\n"
    
    embed = discord.Embed(
        title="⛔ Blacklisted Users",
        description=blacklist_text,
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)

# TEXT COMMANDS

@bot.command(aliases=['s'])
@not_blocked()
async def snipe(ctx, channel: discord.TextChannel = None, page: int = 1):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    target_channel = channel or ctx.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await ctx.send(f"No recently deleted messages in {target_channel.mention}.")
        return
    
    messages = sniped_messages[target_channel.id]
    
    if page < 1 or page > len(messages):
        await ctx.send(f"Page must be between 1 and {len(messages)}.")
        return
    
    msg = messages[page - 1]
    content = msg['content']
    
    # Apply content filter for regular users
    if not ctx.author.guild_permissions.manage_messages:
        content = filter_content(content)
    
    embed = discord.Embed(title="📜 Sniped Message", color=discord.Color.gold())
    embed.add_field(name="Content", value=content or "*No text content*", inline=False)
    embed.add_field(name="Author", value=msg['author'].mention, inline=True)
    embed.add_field(name="Channel", value=target_channel.mention, inline=True)
    embed.add_field(name="Deleted", value=msg['deleted_at'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    
    # Handle attachments
    if msg['attachments']:
        attachment_list = "\n".join([f"[{att.split('/')[-1]}]({att})" for att in msg['attachments'][:3]])
        if len(msg['attachments']) > 3:
            attachment_list += f"\n... and {len(msg['attachments']) - 3} more"
        embed.add_field(name="Attachments", value=attachment_list, inline=False)
        
        # Set first image as embed image
        for att in msg['attachments']:
            if any(ext in att.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                embed.set_image(url=att)
                break
    
    embed.set_footer(text=f"Message {page} of {len(messages)}")
    await ctx.send(embed=embed)

@bot.command(aliases=['es'])
@not_blocked()
async def editsnipe(ctx, channel: discord.TextChannel = None, page: int = 1):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    target_channel = channel or ctx.channel
    
    if target_channel.id not in edited_messages or not edited_messages[target_channel.id]:
        await ctx.send(f"No recently edited messages in {target_channel.mention}.")
        return
    
    messages = edited_messages[target_channel.id]
    
    if page < 1 or page > len(messages):
        await ctx.send(f"Page must be between 1 and {len(messages)}.")
        return
    
    msg = messages[page - 1]
    
    embed = discord.Embed(title="✏️ Edited Message", color=discord.Color.blue())
    embed.add_field(name="Before", value=msg['before_content'] or "*No content*", inline=False)
    embed.add_field(name="After", value=msg['after_content'] or "*No content*", inline=False)
    embed.add_field(name="Author", value=msg['author'].mention, inline=True)
    embed.add_field(name="Channel", value=target_channel.mention, inline=True)
    embed.add_field(name="Edited", value=msg['edited_at'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    
    embed.set_footer(text=f"Edit {page} of {len(messages)}")
    await ctx.send(embed=embed)

@bot.command(aliases=['sp'])
@not_blocked()
async def snipe_list(ctx, channel: discord.TextChannel = None, page: int = 1):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    target_channel = channel or ctx.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await ctx.send(f"No recently deleted messages in {target_channel.mention}.")
        return
    
    messages = sniped_messages[target_channel.id]
    
    # Show list view
    max_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > max_pages:
        await ctx.send(f"Page must be between 1 and {max_pages}.")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(messages))
    page_messages = messages[start_idx:end_idx]
    
    embed = discord.Embed(title=f"📜 Recently Deleted Messages - {target_channel.name}", color=discord.Color.gold())
    
    for i, msg in enumerate(page_messages, start_idx + 1):
        content = msg['content']
        
        # Apply content filter for regular users
        if not ctx.author.guild_permissions.manage_messages:
            content = filter_content(content)
        
        # Handle attachments
        attachment_info = ""
        if msg['attachments']:
            attachment_info = f" [📎 {len(msg['attachments'])} attachment(s)]"
        
        # Format timestamp
        timestamp = msg['deleted_at'].strftime("%H:%M:%S")
        
        field_value = f"**Content:** {truncate_content(content) or '*No content*'}{attachment_info}\n**Time:** {timestamp}"
        
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=field_value,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {max_pages} | Total: {len(messages)} messages")
    await ctx.send(embed=embed)

@bot.command(aliases=['spf'])
@not_blocked()
@commands.has_permissions(manage_messages=True)
async def snipe_force(ctx, channel: discord.TextChannel = None, page: int = 1):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Moderator-only snipe that shows unfiltered content"""
    target_channel = channel or ctx.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await ctx.send(f"No recently deleted messages in {target_channel.mention}.")
        return
    
    messages = sniped_messages[target_channel.id]
    
    if page < 1 or page > len(messages):
        await ctx.send(f"Page must be between 1 and {len(messages)}.")
        return
    
    msg = messages[page - 1]
    
    embed = discord.Embed(title="📜 Sniped Message (Unfiltered)", color=discord.Color.red())
    embed.add_field(name="Content", value=msg['content'] or "*No text content*", inline=False)
    embed.add_field(name="Author", value=msg['author'].mention, inline=True)
    embed.add_field(name="Channel", value=target_channel.mention, inline=True)
    embed.add_field(name="Deleted", value=msg['deleted_at'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    
    # Handle attachments
    if msg['attachments']:
        attachment_list = "\n".join([f"[{att.split('/')[-1]}]({att})" for att in msg['attachments'][:3]])
        if len(msg['attachments']) > 3:
            attachment_list += f"\n... and {len(msg['attachments']) - 3} more"
        embed.add_field(name="Attachments", value=attachment_list, inline=False)
        
        # Set first image as embed image
        for att in msg['attachments']:
            if any(ext in att.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                embed.set_image(url=att)
                break
    
    embed.set_footer(text=f"Message {page} of {len(messages)} | Moderator View")
    await ctx.send(embed=embed)

@bot.command(aliases=['spl'])
@not_blocked()
async def snipe_links(ctx, channel: discord.TextChannel = None, page: int = 1):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Show only deleted messages that contained links"""
    target_channel = channel or ctx.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await ctx.send(f"No recently deleted messages in {target_channel.mention}.")
        return
    
    # Filter messages that contain links
    link_messages = [msg for msg in sniped_messages[target_channel.id] if has_links(msg['content'])]
    
    if not link_messages:
        await ctx.send(f"No recently deleted messages with links in {target_channel.mention}.")
        return
    
    if page < 1 or page > len(link_messages):
        await ctx.send(f"Page must be between 1 and {len(link_messages)}.")
        return
    
    msg = link_messages[page - 1]
    content = msg['content']
    
    # Apply content filter for regular users
    if not ctx.author.guild_permissions.manage_messages:
        content = filter_content(content)
    
    embed = discord.Embed(title="🔗 Sniped Link Message", color=discord.Color.blue())
    embed.add_field(name="Content", value=content or "*No text content*", inline=False)
    embed.add_field(name="Author", value=msg['author'].mention, inline=True)
    embed.add_field(name="Channel", value=target_channel.mention, inline=True)
    embed.add_field(name="Deleted", value=msg['deleted_at'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    
    embed.set_footer(text=f"Link message {page} of {len(link_messages)}")
    await ctx.send(embed=embed)

@bot.command()
@not_blocked()
async def help(ctx):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

@bot.command(aliases=['nl'])
@not_blocked()
@commands.has_permissions(manage_nicknames=True)
async def namelock(ctx, member: discord.Member, *, nickname: str = None):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Lock a user's nickname"""
    if not nickname:
        nickname = member.display_name
    
    # Set the nickname first
    try:
        await member.edit(nick=nickname, reason=f"Namelock by {ctx.author}")
        namelocked_users[member.id] = nickname
        
        embed = discord.Embed(
            title="🔒 Nickname Locked",
            description=f"Locked {member.mention}'s nickname to **{nickname}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to change {member.mention}'s nickname.")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
@not_blocked()
@commands.has_permissions(manage_nicknames=True)
async def unl(ctx, member: discord.Member):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Unlock a user's nickname"""
    if member.id in namelocked_users:
        del namelocked_users[member.id]
        
        embed = discord.Embed(
            title="🔓 Nickname Unlocked",
            description=f"Unlocked {member.mention}'s nickname",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"❌ {member.mention} is not namelocked.")

@bot.command(aliases=['re'])
@not_blocked()
@has_permission_or_is_admin()
@commands.has_permissions(manage_nicknames=True)
async def rename(ctx, member: discord.Member, *, nickname: str):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Change a user's nickname"""
    old_nick = member.display_name
    
    try:
        await member.edit(nick=nickname, reason=f"Rename by {ctx.author}")
        
        embed = discord.Embed(
            title="✅ Nickname Changed",
            description=f"Changed {member.mention}'s nickname from **{old_nick}** to **{nickname}**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to change {member.mention}'s nickname.")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
@not_blocked()
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Send a normal message"""
    # Delete the command message
    try:
        await ctx.message.delete()
    except:
        pass
    
    await ctx.send(message)

@bot.command()
@not_blocked()
@commands.has_permissions(manage_messages=True)
async def saywb(ctx, *, content):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Send a webhook message with optional color"""
    # Parse content for color
    parts = content.rsplit(' ', 1)
    if len(parts) == 2:
        message, potential_color = parts
        color = parse_color(potential_color)
        if color != discord.Color.default():
            # Valid color found
            content = message
        else:
            # Not a valid color, include in message
            color = discord.Color.default()
    else:
        color = discord.Color.default()
    
    try:
        # Delete the command message
        await ctx.message.delete()
    except:
        pass
    
    try:
        webhook = await get_or_create_webhook(ctx.channel)
        if webhook:
            embed = discord.Embed(description=content, color=color)
            await webhook.send(embed=embed, username=ctx.author.display_name, avatar_url=ctx.author.avatar.url if ctx.author.avatar else None)
        else:
            await ctx.send("❌ Could not create webhook.")
    except Exception as e:
        await ctx.send(f"❌ Error sending webhook: {str(e)}")

@bot.command()
@not_blocked()
async def gw(ctx, message_id: int):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Reroll a giveaway"""
    # Check if user can manage giveaways
    if not (ctx.author.guild_permissions.manage_messages or can_host_giveaway(ctx.author)):
        await ctx.send("❌ You don't have permission to reroll giveaways.")
        return
    
    try:
        message = await ctx.fetch_message(message_id)
    except discord.NotFound:
        await ctx.send("❌ Message not found.")
        return
    
    # Check if message has 🎉 reactions
    giveaway_reaction = None
    for reaction in message.reactions:
        if str(reaction.emoji) == "🎉":
            giveaway_reaction = reaction
            break
    
    if not giveaway_reaction:
        await ctx.send("❌ This message doesn't appear to be a giveaway.")
        return
    
    # Get participants
    participants = []
    async for user in giveaway_reaction.users():
        if not user.bot and user.id != bot.user.id:
            member = ctx.guild.get_member(user.id)
            if member:
                participants.append(member)
    
    if not participants:
        await ctx.send("❌ No valid participants found.")
        return
    
    # Pick a random winner
    winner = random.choice(participants)
    
    embed = discord.Embed(
        title="🎉 Giveaway Rerolled!",
        description=f"**New Winner:** {winner.mention}",
        color=discord.Color.gold()
    )
    embed.add_field(name="Rerolled by", value=ctx.author.mention, inline=True)
    embed.add_field(name="Participants", value=str(len(participants)), inline=True)
    embed.timestamp = datetime.utcnow()
    
    await ctx.send(embed=embed)

@bot.command()
@not_blocked()
async def mess(ctx, user_identifier, *, message):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Send a DM to a user globally (across all servers)"""
    if not ctx.author.guild_permissions.moderate_members:
        await ctx.send("❌ You need moderate members permission to use this command.")
        return
    
    # Try to find user by ID first
    user = None
    try:
        user_id = int(user_identifier)
        user = bot.get_user(user_id)
    except ValueError:
        # Not an ID, try to find by name globally
        user = find_user_globally(user_identifier)
    
    if not user:
        await ctx.send(f"❌ Could not find user: {user_identifier}")
        return
    
    try:
        await user.send(f"Message from {ctx.author} ({ctx.guild.name}):\n\n{message}")
        await ctx.send(f"✅ Message sent to {user.mention}")
    except discord.Forbidden:
        await ctx.send(f"❌ Could not send DM to {user.mention}. They may have DMs disabled.")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
@not_blocked()
@commands.has_permissions(manage_roles=True)
async def role(ctx, member: discord.Member, *, role_name):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Add or remove a role from a member"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    
    if not role:
        await ctx.send(f"❌ Role '{role_name}' not found.")
        return
    
    try:
        if role in member.roles:
            await member.remove_roles(role, reason=f"Role management by {ctx.author}")
            await ctx.send(f"✅ Removed role **{role.name}** from {member.mention}")
        else:
            await member.add_roles(role, reason=f"Role management by {ctx.author}")
            await ctx.send(f"✅ Added role **{role.name}** to {member.mention}")
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to manage the role **{role.name}**.")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command()
@not_blocked()
async def block(ctx, user_identifier):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Block a user from using bot functions (BOT OWNER ONLY)"""
    # BOT OWNER ONLY - Replace with your Discord ID
    if ctx.author.id != 1201554061863776276:  # Replace with your Discord ID
        await ctx.send("❌ This command is for bot owner only.")
        return
    
    # Try to find user
    user = None
    try:
        user_id = int(user_identifier)
        user = bot.get_user(user_id)
    except ValueError:
        user = find_user_globally(user_identifier)
    
    if not user:
        await ctx.send(f"❌ Could not find user: {user_identifier}")
        return
    
    if user.id in blocked_users:
        await ctx.send(f"❌ {user.mention} is already blocked.")
        return
    
    blocked_users.add(user.id)
    await ctx.send(f"✅ Blocked {user.mention} from using bot functions.")

@bot.command(aliases=['nli'])
@not_blocked()
@commands.has_permissions(administrator=True)
async def namelockimmune(ctx, member: discord.Member):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Make a user immune to namelock"""
    if member.id in namelock_immune_users:
        namelock_immune_users.remove(member.id)
        await ctx.send(f"✅ Removed namelock immunity from {member.mention}")
    else:
        namelock_immune_users.add(member.id)
        await ctx.send(f"✅ Added namelock immunity to {member.mention}")

@bot.command()
@not_blocked()
async def manage(ctx):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Bot management panel (BOT OWNER ONLY)"""
    # BOT OWNER ONLY - Replace with your Discord ID
    if ctx.author.id != 1201554061863776276:  # Replace with your Discord ID
        await ctx.send("❌ This command is for bot owner only.")
        return
    
    view = ManagePaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

@bot.command()
@not_blocked()
@commands.has_permissions(manage_roles=True)
async def create(ctx, *, args):
    # Check for blacklist first
    if ctx.guild and ctx.guild.id in blacklisted_users and ctx.author.id in blacklisted_users[ctx.guild.id]:
        return  # Silently ignore
        
    """Create a reaction role message"""
    # Parse arguments (title | description | emoji:role | emoji:role ...)
    parts = args.split(' | ')
    
    if len(parts) < 3:
        await ctx.send("❌ Usage: `,create title | description | emoji:@role | emoji:@role ...`")
        return
    
    title = parts[0]
    description = parts[1]
    role_parts = parts[2:]
    
    # Create embed
    embed = discord.Embed(title=title, description=description, color=discord.Color.blue())
    
    role_mapping = {}
    
    for role_part in role_parts:
        if ':' not in role_part:
            continue
        
        try:
            emoji, role_mention = role_part.split(':', 1)
            emoji = emoji.strip()
            
            # Parse role mention
            if role_mention.startswith('<@&') and role_mention.endswith('>'):
                role_id = int(role_mention[3:-1])
                role = ctx.guild.get_role(role_id)
            else:
                # Try to find role by name
                role_name = role_mention.strip().lstrip('@')
                role = discord.utils.get(ctx.guild.roles, name=role_name)
            
            if role:
                role_mapping[emoji] = role.id
                embed.add_field(name=f"{emoji} {role.name}", value="React to get this role", inline=False)
        
        except (ValueError, IndexError):
            continue
    
    if not role_mapping:
        await ctx.send("❌ No valid emoji:role pairs found.")
        return
    
    # Send message and add reactions
    msg = await ctx.send(embed=embed)
    
    for emoji in role_mapping.keys():
        try:
            await msg.add_reaction(emoji)
        except:
            pass
    
    # Store mapping
    reaction_roles[msg.id] = role_mapping

@bot.command(aliases=["bl"])
@has_permission_or_is_admin()
@commands.has_permissions(administrator=True)
async def blacklist(ctx, user: discord.Member):
    # Make sure the guild exists in our dict
    if ctx.guild.id not in blacklisted_users:
        blacklisted_users[ctx.guild.id] = []
    
    # Check if user is already blacklisted
    if user.id in blacklisted_users[ctx.guild.id]:
        embed = discord.Embed(
            title="⚠️ Already Blacklisted",
            description=f"{user.mention} is already blacklisted.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # Check if user is server owner or an admin
    if user.id == ctx.guild.owner_id:
        embed = discord.Embed(
            title="❌ Cannot Blacklist",
            description="You cannot blacklist the server owner.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    if user.guild_permissions.administrator and user.id != ctx.author.id:
        embed = discord.Embed(
            title="⚠️ Warning",
            description=f"You are blacklisting an administrator ({user.mention}).",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # Add user to blacklist
    blacklisted_users[ctx.guild.id].append(user.id)
    
    embed = discord.Embed(
        title="✅ User Blacklisted",
        description=f"{user.mention} has been blacklisted from using bot commands.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(aliases=["ubl"])
@has_permission_or_is_admin()
@commands.has_permissions(administrator=True)
async def unblacklist(ctx, user: discord.Member):
    # Check if guild has any blacklisted users
    if ctx.guild.id not in blacklisted_users or not blacklisted_users[ctx.guild.id]:
        embed = discord.Embed(
            title="ℹ️ No Blacklisted Users",
            description="There are no blacklisted users in this server.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    # Check if user is blacklisted
    if user.id not in blacklisted_users[ctx.guild.id]:
        embed = discord.Embed(
            title="ℹ️ Not Blacklisted",
            description=f"{user.mention} is not blacklisted.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    # Remove user from blacklist
    blacklisted_users[ctx.guild.id].remove(user.id)
    
    embed = discord.Embed(
        title="✅ User Unblacklisted",
        description=f"{user.mention} has been removed from the blacklist.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(aliases=["bls"])
@has_permission_or_is_admin()
@commands.has_permissions(administrator=True)
async def blacklisted(ctx):
    # Check if guild has any blacklisted users
    if ctx.guild.id not in blacklisted_users or not blacklisted_users[ctx.guild.id]:
        embed = discord.Embed(
            title="ℹ️ No Blacklisted Users",
            description="There are no blacklisted users in this server.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    # Create list of blacklisted users
    blacklist_text = ""
    for user_id in blacklisted_users[ctx.guild.id]:
        user = ctx.guild.get_member(user_id)
        if user:
            blacklist_text += f"• {user.mention} ({user.name})\n"
        else:
            blacklist_text += f"• Unknown User (ID: {user_id})\n"
    
    embed = discord.Embed(
        title="⛔ Blacklisted Users",
        description=blacklist_text,
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

# Add error handlers for permission errors
@mess.error
@rename.error
@namelock.error
@role.error
@create.error
@blacklist.error
@unblacklist.error
@blacklisted.error
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
    # Get the Discord token from environment variables
    discord_token = os.getenv("DISCORD_TOKEN")
    if not discord_token:
        print("Error: DISCORD_TOKEN environment variable not found!")
        exit(1)
    bot.run(discord_token)
