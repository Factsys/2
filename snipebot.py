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

# Helper function to handle media URLs and extract from content
def get_media_url(content, attachments):
    # Priority 1: Check for attachments first (Discord files)
    if attachments:
        return attachments[0].url
    
    # Priority 2: Check for tenor links in content
    if content:
        tenor_match = re.search(r'https?://(?:www\.)?tenor\.com/view/[^\s]+', content)
        if tenor_match:
            return tenor_match.group(0)
        
        # Check for Twitter/X GIF links
        twitter_match = re.search(r'https?://(?:www\.)?twitter\.com/[^\s]+\.gif', content)
        if twitter_match:
            return twitter_match.group(0)
        
        # Check for discord attachment links with media extensions
        discord_media_match = re.search(r'https?://(?:cdn|media)\.discordapp\.(?:com|net)/[^\s]+\.(gif|png|jpg|jpeg|webp|mp4|mov)[^\s]*', content)
        if discord_media_match:
            return discord_media_match.group(0)
        
        # Check for direct media links
        direct_media_match = re.search(r'https?://[^\s]+\.(gif|png|jpg|jpeg|webp|mp4|mov)[^\s]*', content)
        if direct_media_match:
            return direct_media_match.group(0)
    
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

# Help Pagination View (unchanged)
class HelpPaginationView(discord.ui.View):
    def __init__(self, timeout=300):
        super().__init__(timeout=timeout)
        self.current_page = 0
        self.pages = [
            {
                "title": "📜 SnipeBot Commands - Page 1",
                "fields": [
                    ("**Message Tracking**", "`,snipe` `,s` - Show last deleted message\n`,editsnipe` `,es` - Show last edited message\n`,sp` - List all deleted messages\n`,spforce` `,spf` - Moderator-only unfiltered snipe\n`,spl` - Show deleted links only", False),
                    ("**Moderation**", "`,namelock` `,nl` - Lock user's nickname\n`,unl` - Unlock user's nickname\n`,rename` `,re` - Change user's nickname\n`,say` - Send normal message\n`,saywb` - Send message via webhook", False)
                ]
            },
            {
                "title": "📜 SnipeBot Commands - Page 2", 
                "fields": [
                    ("**Giveaways**", "`,gw [id]` - Reroll giveaway winner\n`/giveaway` - Create new giveaway\n`/giveaway-host-role` - Set host roles", False),
                    ("**Management**", "`,block` - Block user from bot\n`,mess` - DM user globally\n`,role` - Add role to user\n`,namelockimmune` `,nli` - Make user immune to namelock", False)
                ]
            },
            {
                "title": "📜 SnipeBot Commands - Page 3",
                "fields": [
                    ("**Reaction Roles**", "`,create` - Create reaction role message\n`/create` - Slash version of reaction roles", False),
                    ("**Bot Owner**", "`,manage` - Bot management panel\n`/unblock` - Unblock user from bot", False)
                ]
            },
            {
                "title": "📜 SnipeBot Commands - Page 4",
                "fields": [
                    ("**Info**", "All commands support both prefix (,) and slash (/) versions\nModerators can use most commands\nBlocked users cannot use any bot functions", False),
                    ("**Usage Examples**", "`,mess wer hello` - DM user with partial name\n`,create [text] 🦝 @Role red` - Create reaction role\n`,gw 123456789` - Reroll giveaway", False)
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

# Management Pagination View (unchanged)
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
                        await member.remove_roles(role, reason="Reaction role removed")
                    except discord.Forbidden:
                        pass

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
    
    # Store deleted message for snipe (up to 100 per channel)
    channel_id = message.channel.id
    media_url = get_media_url(message.content, message.attachments)
    
    # Clean content by removing media URLs to avoid duplication
    cleaned_content = clean_content_from_media(message.content, media_url)
    
    msg_data = {
        'content': cleaned_content,  # Use cleaned content
        'author': message.author,
        'timestamp': message.created_at,
        'attachments': [att.url for att in message.attachments] if message.attachments else [],
        'media_url': media_url,
        'deleted': True,
        'delete_time': datetime.utcnow()
    }
    
    # Initialize channel list if not exists
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []
    
    # Add to beginning of list (newest first)
    sniped_messages[channel_id].insert(0, msg_data)
    
    # Keep only the last MAX_MESSAGES
    if len(sniped_messages[channel_id]) > MAX_MESSAGES:
        sniped_messages[channel_id] = sniped_messages[channel_id][:MAX_MESSAGES]

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
async def snipe_command(ctx, page: int = 1):
    """Show deleted messages with page support"""
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ Nothing to snipe in this channel!")
        return
    
    messages = sniped_messages[channel_id]
    total_messages = len(messages)
    
    # Validate page number (1-100)
    if page < 1 or page > min(total_messages, 100):
        await ctx.send(f"❌ Invalid page number! Available pages: 1-{min(total_messages, 100)}")
        return
    
    # Get the specific message (page 1 = index 0)
    msg_data = messages[page - 1]
    
    # Create embed
    embed = discord.Embed(
        color=discord.Color.red(),
        timestamp=msg_data['timestamp']
    )
    
    # Add content if it exists and apply filtering
    if msg_data['content']:
        filtered_content = filter_content(msg_data['content'])
        embed.description = filtered_content
    else:
        embed.description = "*No text content*"
    
    embed.set_author(
        name=msg_data['author'].display_name,
        icon_url=msg_data['author'].display_avatar.url
    )
    
    # Handle media display - SET AS IMAGE, not as field
    if msg_data.get('media_url'):
        # Check if it's an image/gif that can be displayed
        if any(msg_data['media_url'].lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            embed.set_image(url=msg_data['media_url'])
        else:
            # For non-image media, still try to set as image (Discord will handle it)
            embed.set_image(url=msg_data['media_url'])
    
    embed.set_footer(text=f"Message deleted | Page {page}/{min(total_messages, 100)}")
    
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
    
    # Apply filtering to both before and after content
    before_content = filter_content(msg_data['before_content']) if msg_data['before_content'] else "*No content*"
    after_content = filter_content(msg_data['after_content']) if msg_data['after_content'] else "*No content*"
    
    embed.add_field(
        name="Before",
        value=before_content,
        inline=False
    )
    
    embed.add_field(
        name="After", 
        value=after_content,
        inline=False
    )
    
    edit_time = msg_data.get('edited_at', msg_data['timestamp'])
    embed.set_footer(text=f"Edited at {edit_time.strftime('%H:%M:%S')}")
    
    await ctx.send(embed=embed)

@bot.command(name='sp')
@not_blocked()
async def snipepages_command(ctx, page: int = 1):
    """List all deleted messages with pagination"""
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No sniped messages in this channel!")
        return
    
    messages = sniped_messages[channel_id]
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    
    # Validate page number
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page number! Available pages: 1-{total_pages}")
        return
    
    # Get messages for this page
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"📋 Deleted Messages - Page {page}/{total_pages}",
        color=discord.Color.blue()
    )
    
    for i, msg_data in enumerate(page_messages, start=start_idx + 1):
        # Apply content filtering
        content = filter_content(msg_data['content']) if msg_data['content'] else "*No text*"
        truncated_content = truncate_content(content, 100)
        
        embed.add_field(
            name=f"{i}. {msg_data['author'].display_name}",
            value=truncated_content,
            inline=False
        )
    
    embed.set_footer(text=f"Use ,s [number] to view specific message")
    
    await ctx.send(embed=embed)

@bot.command(name='spforce', aliases=['spf'])
@is_moderator()
async def spforce_command(ctx, page: int = 1):
    """Moderator-only: Show unfiltered deleted messages"""
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No sniped messages in this channel!")
        return
    
    messages = sniped_messages[channel_id]
    total_messages = len(messages)
    
    # Validate page number (1-100)
    if page < 1 or page > min(total_messages, 100):
        await ctx.send(f"❌ Invalid page number! Available pages: 1-{min(total_messages, 100)}")
        return
    
    # Get the specific message (page 1 = index 0)
    msg_data = messages[page - 1]
    
    # Create embed
    embed = discord.Embed(
        color=discord.Color.dark_red(),
        timestamp=msg_data['timestamp']
    )
    
    # Add content WITHOUT filtering (raw content)
    if msg_data['content']:
        embed.description = msg_data['content']  # NO FILTERING
    else:
        embed.description = "*No text content*"
    
    embed.set_author(
        name=msg_data['author'].display_name,
        icon_url=msg_data['author'].display_avatar.url
    )
    
    # Handle media display
    if msg_data.get('media_url'):
        if any(msg_data['media_url'].lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            embed.set_image(url=msg_data['media_url'])
        else:
            embed.set_image(url=msg_data['media_url'])
    
    embed.set_footer(text=f"🔸 UNFILTERED 🔸 | Page {page}/{min(total_messages, 100)}")
    
    await ctx.send(embed=embed)

@bot.command(name='spl')
@not_blocked()
async def snipelinks_command(ctx, page: int = 1):
    """Show only deleted messages that contained links"""
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No sniped messages in this channel!")
        return
    
    # Filter messages that contain links
    link_messages = []
    for msg_data in sniped_messages[channel_id]:
        if has_links(msg_data['content']) or msg_data.get('media_url') or msg_data.get('attachments'):
            link_messages.append(msg_data)
    
    if not link_messages:
        await ctx.send("❌ No deleted messages with links found!")
        return
    
    total_messages = len(link_messages)
    
    # Validate page number
    if page < 1 or page > min(total_messages, 100):
        await ctx.send(f"❌ Invalid page number! Available pages: 1-{min(total_messages, 100)}")
        return
    
    # Get the specific message (page 1 = index 0)
    msg_data = link_messages[page - 1]
    
    # Create embed
    embed = discord.Embed(
        color=discord.Color.purple(),
        timestamp=msg_data['timestamp']
    )
    
    # Add content with filtering
    if msg_data['content']:
        filtered_content = filter_content(msg_data['content'])
        embed.description = filtered_content
    else:
        embed.description = "*No text content*"
    
    embed.set_author(
        name=msg_data['author'].display_name,
        icon_url=msg_data['author'].display_avatar.url
    )
    
    # Handle media display
    if msg_data.get('media_url'):
        if any(msg_data['media_url'].lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            embed.set_image(url=msg_data['media_url'])
        else:
            embed.set_image(url=msg_data['media_url'])
    
    embed.set_footer(text=f"🔗 Links Only | Page {page}/{min(total_messages, 100)}")
    
    await ctx.send(embed=embed)

@bot.command(name='mess')
@not_blocked()
async def mess_command(ctx, user_query: str, *, message: str):
    """DM a user globally across all servers"""
    # Find user globally across all servers
    target_user = find_user_globally(user_query)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user: `{user_query}`")
        return
    
    try:
        # Create DM embed
        embed = discord.Embed(
            title="📩 Direct Message",
            description=message,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        embed.set_author(
            name=f"From {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        
        embed.set_footer(text=f"Sent from {ctx.guild.name}")
        
        # Send DM
        await target_user.send(embed=embed)
        
        # Confirm to sender
        await ctx.send(f"✅ DM sent to **{target_user.display_name}** ({target_user.name})")
        
    except discord.Forbidden:
        await ctx.send(f"❌ Could not DM **{target_user.display_name}** - they may have DMs disabled")
    except Exception as e:
        await ctx.send(f"❌ Failed to send DM: {str(e)}")

@bot.command(name='unl')
@has_manage_nicknames()
async def unlock_namelock_command(ctx, *, user_query: str):
    """Remove user from namelock system"""
    # Find user in current guild
    target_user = find_user_by_name(ctx.guild, user_query)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user: `{user_query}`")
        return
    
    if target_user.id not in namelocked_users:
        await ctx.send(f"❌ **{target_user.display_name}** is not namelocked!")
        return
    
    # Remove from namelock
    del namelocked_users[target_user.id]
    
    await ctx.send(f"✅ **{target_user.display_name}** has been unlocked from namelock and can now change their name freely!")

@bot.command(name='create')
@has_permission_or_is_admin()
async def create_reaction_role_command(ctx, *, args):
    """Create reaction role message with multiple emoji-role pairs"""
    # Parse arguments: text color emoji role emoji role...
    parts = args.split()
    
    if len(parts) < 4:
        await ctx.send("❌ Usage: `,create [text] [color] [emoji] [role] [emoji] [role]...`")
        return
    
    # Extract text and color
    text = parts[0]
    color_str = parts[1]
    
    # Parse emoji-role pairs
    emoji_role_pairs = parts[2:]
    if len(emoji_role_pairs) % 2 != 0:
        await ctx.send("❌ Each emoji must have a corresponding role!")
        return
    
    # Create pairs
    role_mapping = {}
    for i in range(0, len(emoji_role_pairs), 2):
        emoji = emoji_role_pairs[i]
        role_mention = emoji_role_pairs[i + 1]
        
        # Parse role
        role = None
        if role_mention.startswith('<@&') and role_mention.endswith('>'):
            role_id = int(role_mention[3:-1])
            role = ctx.guild.get_role(role_id)
        else:
            # Try to find role by name
            role = discord.utils.get(ctx.guild.roles, name=role_mention)
        
        if not role:
            await ctx.send(f"❌ Could not find role: {role_mention}")
            return
        
        role_mapping[emoji] = role.id
    
    # Create embed
    color = parse_color(color_str)
    embed = discord.Embed(
        title="🎭 Reaction Roles",
        description=text,
        color=color
    )
    
    # Add emoji-role info
    role_info = []
    for emoji, role_id in role_mapping.items():
        role = ctx.guild.get_role(role_id)
        if role:
            role_info.append(f"{emoji} - {role.mention}")
    
    embed.add_field(
        name="React to get roles:",
        value="\n".join(role_info),
        inline=False
    )
    
    # Send message
    message = await ctx.send(embed=embed)
    
    # Add reactions
    for emoji in role_mapping.keys():
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await ctx.send(f"❌ Could not add reaction: {emoji}")
    
    # Store reaction role mapping
    reaction_roles[message.id] = role_mapping
    
    await ctx.send(f"✅ Reaction role message created with {len(role_mapping)} roles!")

@bot.command(name='help')
@not_blocked()
async def help_command(ctx):
    """Show paginated help with emoji navigation"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

@bot.command(name='manage')
@is_specific_user()
async def manage_command(ctx):
    """Bot management panel"""
    view = ManagePaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# Continue with the rest of the commands... (namelock, role, block, etc.)
# [Rest of the commands remain the same as before]

# ===== SLASH COMMANDS =====
# [All slash commands remain the same as before]

# ===== RUN THE BOT =====

if __name__ == "__main__":
    run_flask()
    
    # Get bot token from environment
    TOKEN = os.getenv("DISCORD_BOT_TOKEN")
    if not TOKEN:
        print("Error: DISCORD_BOT_TOKEN environment variable not set!")
        exit(1)
    
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error starting bot: {e}")
