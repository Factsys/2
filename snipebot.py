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

# Help Pagination View
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
    
    msg_data = {
        'content': message.content,
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
async def snipe_command(ctx):
    """Show the last deleted message in this channel"""
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ Nothing to snipe in this channel!")
        return
    
    # Get the most recent message (index 0)
    msg_data = sniped_messages[channel_id][0]
    
    # Apply content filtering for normal snipe
    display_content = filter_content(msg_data['content']) if msg_data['content'] else "*No text content*"
    
    # Create embed
    embed = discord.Embed(
        description=display_content,
        color=discord.Color.red(),
        timestamp=msg_data['timestamp']
    )
    
    embed.set_author(
        name=msg_data['author'].display_name,
        icon_url=msg_data['author'].display_avatar.url
    )
    
    embed.set_footer(text="Message deleted")
    
    # Handle media/attachments - FIXED to show images properly
    if msg_data.get('media_url'):
        # Check if it's an image that should be displayed
        if any(msg_data['media_url'].lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            embed.set_image(url=msg_data['media_url'])
        else:
            embed.add_field(name="Attachment", value=msg_data['media_url'], inline=False)
    elif msg_data.get('attachments'):
        # Handle multiple attachments
        for i, attachment in enumerate(msg_data['attachments'][:3]):  # Limit to 3 attachments
            # Check if it's an image
            if any(attachment.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                if i == 0:  # Set first image as embed image
                    embed.set_image(url=attachment)
                else:
                    embed.add_field(name=f"Image {i+1}", value=attachment, inline=False)
            else:
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
    
    # Apply filtering to edited content
    before_filtered = filter_content(msg_data['before_content']) if msg_data['before_content'] else "*No content*"
    after_filtered = filter_content(msg_data['after_content']) if msg_data['after_content'] else "*No content*"
    
    embed.add_field(
        name="Before",
        value=before_filtered,
        inline=False
    )
    
    embed.add_field(
        name="After", 
        value=after_filtered,
        inline=False
    )
    
    edit_time = msg_data.get('edited_at', msg_data['timestamp'])
    embed.set_footer(text=f"Edited at {edit_time.strftime('%H:%M:%S')}")
    
    await ctx.send(embed=embed)

@bot.command(name='snipepages', aliases=['sp'])
@not_blocked()
async def snipepages_command(ctx, page: int = 1):
    """List all deleted messages with pagination (FILTERED)"""
    if not sniped_messages:
        await ctx.send("❌ No sniped messages available!")
        return
    
    # Get all sniped messages for this guild
    guild_messages = []
    for channel_id, msg_list in sniped_messages.items():
        channel = bot.get_channel(channel_id)
        if channel and channel.guild.id == ctx.guild.id:
            for msg_data in msg_list:
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
        # Apply content filtering
        filtered_content = filter_content(msg_data['content']) if msg_data['content'] else "*No text content*"
        truncated_content = truncate_content(filtered_content)
        
        field_name = f"{i}. #{channel.name} - {msg_data['author'].display_name}"
        field_value = f"**Content:** {truncated_content}\n**Time:** <t:{int(msg_data['timestamp'].timestamp())}:R>"
        
        if msg_data.get('media_url') or msg_data.get('attachments'):
            field_value += "\n📎 *Has attachments*"
        
        embed.add_field(name=field_name, value=field_value, inline=False)
    
    embed.set_footer(text=f"Total: {len(guild_messages)} messages | Use ,spforce for unfiltered content")
    
    await ctx.send(embed=embed)

@bot.command(name='spforce', aliases=['spf'])
@is_moderator()
async def spforce_command(ctx, page: int = 1):
    """List all deleted messages with pagination (UNFILTERED - Moderator only)"""
    if not sniped_messages:
        await ctx.send("❌ No sniped messages available!")
        return
    
    # Get all sniped messages for this guild
    guild_messages = []
    for channel_id, msg_list in sniped_messages.items():
        channel = bot.get_channel(channel_id)
        if channel and channel.guild.id == ctx.guild.id:
            for msg_data in msg_list:
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
        title=f"📋 Sniped Messages (UNFILTERED) - Page {page}/{total_pages}",
        color=discord.Color.red()
    )
    
    for i, (channel, msg_data) in enumerate(page_messages, start=start_idx + 1):
        # NO FILTERING - show raw content
        raw_content = msg_data['content'] if msg_data['content'] else "*No text content*"
        truncated_content = truncate_content(raw_content)
        
        field_name = f"{i}. #{channel.name} - {msg_data['author'].display_name}"
        field_value = f"**Content:** {truncated_content}\n**Time:** <t:{int(msg_data['timestamp'].timestamp())}:R>"
        
        if msg_data.get('media_url') or msg_data.get('attachments'):
            field_value += "\n📎 *Has attachments*"
        
        embed.add_field(name=field_name, value=field_value, inline=False)
    
    embed.set_footer(text=f"Total: {len(guild_messages)} messages | UNFILTERED CONTENT")
    
    await ctx.send(embed=embed)

@bot.command(name='spl')
@not_blocked()
async def snipe_links_command(ctx, page: int = 1):
    """List deleted messages that contained links only"""
    if not sniped_messages:
        await ctx.send("❌ No sniped messages available!")
        return
    
    # Get all sniped messages with links for this guild
    guild_messages = []
    for channel_id, msg_list in sniped_messages.items():
        channel = bot.get_channel(channel_id)
        if channel and channel.guild.id == ctx.guild.id:
            for msg_data in msg_list:
                # Check if message has links
                if has_links(msg_data['content']) or msg_data.get('media_url') or msg_data.get('attachments'):
                    guild_messages.append((channel, msg_data))
    
    if not guild_messages:
        await ctx.send("❌ No deleted messages with links found in this server!")
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
        title=f"🔗 Deleted Links - Page {page}/{total_pages}",
        color=discord.Color.green()
    )
    
    for i, (channel, msg_data) in enumerate(page_messages, start=start_idx + 1):
        # Apply content filtering
        filtered_content = filter_content(msg_data['content']) if msg_data['content'] else "*No text content*"
        truncated_content = truncate_content(filtered_content)
        
        field_name = f"{i}. #{channel.name} - {msg_data['author'].display_name}"
        field_value = f"**Content:** {truncated_content}\n**Time:** <t:{int(msg_data['timestamp'].timestamp())}:R>"
        
        if msg_data.get('media_url'):
            field_value += f"\n🔗 **Media:** {msg_data['media_url']}"
        elif msg_data.get('attachments'):
            field_value += f"\n📎 **Attachments:** {len(msg_data['attachments'])}"
        
        embed.add_field(name=field_name, value=field_value, inline=False)
    
    embed.set_footer(text=f"Total: {len(guild_messages)} messages with links")
    
    await ctx.send(embed=embed)

@bot.command(name='mess')
@not_blocked()
async def message_user_command(ctx, user_search, *, message):
    """DM a user globally across all servers"""
    # Find user globally
    target_user = find_user_globally(user_search)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user '{user_search}' in any server I'm in.")
        return
    
    try:
        # Send DM to the user
        dm_embed = discord.Embed(
            title="📨 Message from a server member",
            description=message,
            color=discord.Color.blue()
        )
        dm_embed.set_footer(text=f"Sent by {ctx.author.display_name} from {ctx.guild.name}")
        dm_embed.timestamp = datetime.utcnow()
        
        await target_user.send(embed=dm_embed)
        
        # Confirm to sender
        await ctx.send(f"✅ Message sent to {target_user.display_name} ({target_user.mention})")
        
    except discord.Forbidden:
        await ctx.send(f"❌ Could not send DM to {target_user.display_name}. They may have DMs disabled.")
    except Exception as e:
        await ctx.send(f"❌ Failed to send message: {str(e)}")

@bot.command(name='unl')
@has_manage_nicknames()
async def unlock_namelock_command(ctx, *, user_search):
    """Remove user from namelock system so they can change their name again"""
    target_user = find_user_by_name(ctx.guild, user_search)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user '{user_search}' in this server.")
        return
    
    if target_user.id not in namelocked_users:
        await ctx.send(f"❌ {target_user.display_name} is not namelocked.")
        return
    
    # Remove from namelock
    del namelocked_users[target_user.id]
    
    # Also remove from immune list if they're there
    if target_user.id in namelock_immune_users:
        namelock_immune_users.remove(target_user.id)
    
    embed = discord.Embed(
        title="🔓 Namelock Removed",
        description=f"{target_user.mention} can now change their nickname freely.",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Action by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.command(name='create')
@has_permission_or_is_admin()
async def create_reaction_role(ctx, *, args):
    """Create reaction role message: ,create [text] [color] [emoji] [role] [emoji] [role]..."""
    if not args:
        await ctx.send("❌ Usage: `,create [text] [color] [emoji] [role] [emoji] [role]...`\nExample: `,create Get roles! red 🦝 @Member 🎉 @VIP`")
        return
    
    try:
        # Parse arguments
        parts = args.split()
        if len(parts) < 4:
            await ctx.send("❌ Not enough arguments. Usage: `,create [text] [color] [emoji] [role] [emoji] [role]...`")
            return
        
        # Extract text (everything before color)
        # Find where color starts by looking for hex colors or color names
        color_names = ['red', 'green', 'blue', 'yellow', 'purple', 'orange', 'pink', 'black', 'white', 'gray', 'grey', 'cyan', 'magenta', 'gold', 'silver', 'golden']
        
        text_parts = []
        color_index = -1
        
        for i, part in enumerate(parts):
            # Check if this part is a color
            if (part.lower() in color_names or 
                (part.startswith('#') and len(part) in [4, 7]) or
                (len(part) in [3, 6] and all(c in '0123456789abcdefABCDEF' for c in part))):
                color_index = i
                break
            text_parts.append(part)
        
        if color_index == -1:
            await ctx.send("❌ Could not find color in arguments. Supported colors: red, green, blue, yellow, purple, orange, pink, black, white, gray, cyan, magenta, gold, silver, or hex codes.")
            return
        
        text = ' '.join(text_parts)
        color_str = parts[color_index]
        
        # Parse emoji-role pairs
        remaining_parts = parts[color_index + 1:]
        if len(remaining_parts) < 2 or len(remaining_parts) % 2 != 0:
            await ctx.send("❌ Invalid emoji-role pairs. Format: [emoji] [role] [emoji] [role]...")
            return
        
        role_mapping = {}
        
        for i in range(0, len(remaining_parts), 2):
            emoji = remaining_parts[i]
            role_mention = remaining_parts[i + 1]
            
            # Parse role
            role = None
            if role_mention.startswith('<@&') and role_mention.endswith('>'):
                role_id = int(role_mention[3:-1])
                role = ctx.guild.get_role(role_id)
            else:
                # Search by name
                role = discord.utils.get(ctx.guild.roles, name=role_mention.replace('@', ''))
            
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
        
        # Add role information
        role_info = []
        for emoji, role_id in role_mapping.items():
            role = ctx.guild.get_role(role_id)
            if role:
                role_info.append(f"{emoji} - {role.mention}")
        
        embed.add_field(name="Available Roles", value="\n".join(role_info), inline=False)
        embed.set_footer(text="React with emojis to get roles!")
        
        # Send message
        message = await ctx.send(embed=embed)
        
        # Add reactions
        for emoji in role_mapping.keys():
            try:
                await message.add_reaction(emoji)
            except discord.HTTPException:
                await ctx.send(f"❌ Could not add reaction {emoji}. Make sure it's a valid emoji.")
                return
        
        # Store reaction role data
        reaction_roles[message.id] = role_mapping
        
        await ctx.send(f"✅ Reaction role message created with {len(role_mapping)} roles!")
        
    except Exception as e:
        await ctx.send(f"❌ Error creating reaction roles: {str(e)}")

@bot.command(name='help')
@not_blocked()
async def help_command(ctx):
    """Show help with emoji pagination"""
    view = HelpPaginationView()
    embed = view.get_embed()
    
    await ctx.send(embed=embed, view=view)

@bot.command(name='namelock', aliases=['nl'])
@has_manage_nicknames()
async def namelock_command(ctx, user_search, *, nickname):
    """Lock a user's nickname"""
    target_user = find_user_by_name(ctx.guild, user_search)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user '{user_search}' in this server.")
        return
    
    if target_user.id == ctx.guild.owner_id:
        await ctx.send("❌ Cannot namelock the server owner.")
        return
    
    if target_user.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("❌ You cannot namelock someone with a higher or equal role.")
        return
    
    try:
        await target_user.edit(nick=nickname, reason=f"Namelocked by {ctx.author}")
        namelocked_users[target_user.id] = nickname
        
        embed = discord.Embed(
            title="🔒 User Namelocked",
            description=f"{target_user.mention} has been namelocked to `{nickname}`",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Action by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname.")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name='rename', aliases=['re'])
@has_manage_nicknames()
async def rename_command(ctx, user_search, *, new_nickname):
    """Change a user's nickname"""
    target_user = find_user_by_name(ctx.guild, user_search)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user '{user_search}' in this server.")
        return
    
    if target_user.id == ctx.guild.owner_id:
        await ctx.send("❌ Cannot rename the server owner.")
        return
    
    if target_user.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("❌ You cannot rename someone with a higher or equal role.")
        return
    
    try:
        old_nick = target_user.display_name
        await target_user.edit(nick=new_nickname, reason=f"Renamed by {ctx.author}")
        
        embed = discord.Embed(
            title="✏️ User Renamed",
            description=f"{target_user.mention} renamed from `{old_nick}` to `{new_nickname}`",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Action by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname.")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name='say')
@is_moderator()
async def say_command(ctx, *, message):
    """Send a message as the bot"""
    await ctx.message.delete()
    await ctx.send(message)

@bot.command(name='saywb')
@is_moderator()
async def say_webhook_command(ctx, *, message):
    """Send a message via webhook (looks like the user sent it)"""
    try:
        webhook = await get_or_create_webhook(ctx.channel)
        await webhook.send(
            content=message,
            username=ctx.author.display_name,
            avatar_url=ctx.author.display_avatar.url
        )
        await ctx.message.delete()
    except Exception as e:
        await ctx.send(f"❌ Error sending webhook message: {str(e)}")

@bot.command(name='role')
@has_permission_or_is_admin()
async def role_command(ctx, user_search, *, role_name):
    """Add a role to a user"""
    target_user = find_user_by_name(ctx.guild, user_search)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user '{user_search}' in this server.")
        return
    
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"❌ Could not find role '{role_name}' in this server.")
        return
    
    if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("❌ You cannot assign a role higher than or equal to your highest role.")
        return
    
    try:
        if role in target_user.roles:
            await target_user.remove_roles(role, reason=f"Role removed by {ctx.author}")
            action = "removed from"
            color = discord.Color.red()
        else:
            await target_user.add_roles(role, reason=f"Role added by {ctx.author}")
            action = "added to"
            color = discord.Color.green()
        
        embed = discord.Embed(
            title="🎭 Role Updated",
            description=f"Role `{role.name}` {action} {target_user.mention}",
            color=color
        )
        embed.set_footer(text=f"Action by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage that role.")
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}")

@bot.command(name='namelockimmune', aliases=['nli'])
@is_specific_user()
async def namelock_immune_command(ctx, *, user_search):
    """Make a user immune to namelock (bot owner only)"""
    target_user = find_user_by_name(ctx.guild, user_search)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user '{user_search}' in this server.")
        return
    
    if target_user.id in namelock_immune_users:
        namelock_immune_users.remove(target_user.id)
        status = "removed from"
        color = discord.Color.red()
    else:
        namelock_immune_users.add(target_user.id)
        status = "added to"
        color = discord.Color.green()
    
    embed = discord.Embed(
        title="🛡️ Namelock Immunity",
        description=f"{target_user.mention} {status} namelock immunity list",
        color=color
    )
    embed.set_footer(text=f"Action by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.command(name='block')
@is_specific_user()
async def block_user_command(ctx, *, user_search):
    """Block a user from using any bot functions (bot owner only)"""
    target_user = find_user_by_name(ctx.guild, user_search)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user '{user_search}' in this server.")
        return
    
    if target_user.id == ctx.author.id:
        await ctx.send("❌ You cannot block yourself.")
        return
    
    blocked_users.add(target_user.id)
    
    embed = discord.Embed(
        title="🚫 User Blocked",
        description=f"{target_user.mention} has been blocked from using bot functions",
        color=discord.Color.red()
    )
    embed.set_footer(text=f"Action by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.command(name='gw')
@not_blocked()
async def giveaway_reroll_command(ctx, message_id: int):
    """Reroll a giveaway winner"""
    if message_id not in active_giveaways:
        await ctx.send("❌ No active giveaway found with that ID.")
        return
    
    giveaway = active_giveaways[message_id]
    
    # Check if user can reroll giveaways
    if not can_host_giveaway(ctx.author):
        await ctx.send("❌ You don't have permission to reroll giveaways.")
        return
    
    try:
        channel = bot.get_channel(giveaway['channel_id'])
        message = await channel.fetch_message(message_id)
        
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
        
        if not participants:
            await ctx.send("❌ No valid participants to reroll!")
            return
        
        # Select new winner
        winner_id = random.choice(participants)
        winner = bot.get_user(winner_id)
        
        if winner:
            await ctx.send(f"🎉 **Giveaway Rerolled!**\nNew winner: {winner.mention} for **{giveaway['prize']}**")
        else:
            await ctx.send("❌ Could not find the selected winner.")
            
    except discord.NotFound:
        await ctx.send("❌ Giveaway message not found.")
        del active_giveaways[message_id]
    except Exception as e:
        await ctx.send(f"❌ Error rerolling giveaway: {str(e)}")

@bot.command(name='manage')
@is_specific_user()
async def manage_command(ctx):
    """Bot management panel (bot owner only)"""
    view = ManagePaginationView()
    embed = view.get_embed()
    
    await ctx.send(embed=embed, view=view)

# ===== SLASH COMMANDS =====

@bot.tree.command(name="giveaway", description="Create a new giveaway")
@app_commands.describe(
    prize="What is being given away",
    duration="How long the giveaway lasts (e.g., 1h, 30m, 1d)",
    winners="Number of winners (default: 1)",
    emoji="Emoji to react with (default: 🎉)",
    required_messages="Minimum messages required to enter",
    required_role="Role required to enter",
    blacklisted_role="Role that cannot enter"
)
@check_giveaway_host()
@check_not_blocked()
async def giveaway_slash(
    interaction: discord.Interaction,
    prize: str,
    duration: str,
    winners: int = 1,
    emoji: str = "🎉",
    required_messages: Optional[int] = None,
    required_role: Optional[discord.Role] = None,
    blacklisted_role: Optional[discord.Role] = None
):
    """Create a new giveaway"""
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        await interaction.response.send_message("❌ Invalid duration format. Use format like: 1h, 30m, 1d", ephemeral=True)
        return
    
    if duration_seconds < 60:
        await interaction.response.send_message("❌ Giveaway duration must be at least 1 minute.", ephemeral=True)
        return
    
    if winners < 1 or winners > 50:
        await interaction.response.send_message("❌ Number of winners must be between 1 and 50.", ephemeral=True)
        return
    
    # Create giveaway embed
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    embed = discord.Embed(
        title="🎉 GIVEAWAY! 🎉",
        description=f"**Prize:** {prize}\n\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>\n\nReact with {emoji} to enter!",
        color=discord.Color.gold()
    )
    
    # Add requirements
    requirements = {}
    req_text = []
    
    if required_messages:
        requirements['messages'] = required_messages
        req_text.append(f"• Must have at least {required_messages} messages")
    
    if required_role:
        requirements['required_role'] = required_role.name
        req_text.append(f"• Must have the {required_role.mention} role")
    
    if blacklisted_role:
        requirements['blacklisted_role'] = blacklisted_role.name
        req_text.append(f"• Cannot have the {blacklisted_role.mention} role")
    
    if req_text:
        embed.add_field(name="Requirements", value="\n".join(req_text), inline=False)
    
    embed.set_footer(text=f"Hosted by {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    # Add reaction
    try:
        await message.add_reaction(emoji)
    except discord.HTTPException:
        await interaction.followup.send("❌ Invalid emoji. Using default 🎉", ephemeral=True)
        emoji = "🎉"
        await message.add_reaction(emoji)
    
    # Store giveaway data
    active_giveaways[message.id] = {
        'prize': prize,
        'winners': winners,
        'end_time': end_time,
        'host_id': interaction.user.id,
        'channel_id': interaction.channel.id,
        'emoji': emoji,
        'requirements': requirements
    }
    
    # Schedule giveaway end
    await asyncio.sleep(duration_seconds)
    await end_giveaway(message.id)

@bot.tree.command(name="giveaway-host-role", description="Set roles that can host giveaways")
@app_commands.describe(role="Role to add/remove from giveaway host roles")
@check_admin_or_permissions(administrator=True)
@check_not_blocked()
async def giveaway_host_role_slash(interaction: discord.Interaction, role: discord.Role):
    """Set roles that can host giveaways"""
    
    guild_id = interaction.guild.id
    
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = []
    
    if role.id in giveaway_host_roles[guild_id]:
        giveaway_host_roles[guild_id].remove(role.id)
        action = "removed from"
        color = discord.Color.red()
    else:
        giveaway_host_roles[guild_id].append(role.id)
        action = "added to"
        color = discord.Color.green()
    
    embed = discord.Embed(
        title="🎉 Giveaway Host Roles",
        description=f"{role.mention} {action} giveaway host roles",
        color=color
    )
    embed.set_footer(text=f"Action by {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="create", description="Create reaction role message")
@app_commands.describe(
    text="Text for the reaction role message",
    color="Color for the embed (red, blue, green, etc. or hex)",
    emoji1="First emoji", role1="First role",
    emoji2="Second emoji", role2="Second role",
    emoji3="Third emoji", role3="Third role",
    emoji4="Fourth emoji", role4="Fourth role",
    emoji5="Fifth emoji", role5="Fifth role",
    emoji6="Sixth emoji", role6="Sixth role"
)
@check_admin_or_permissions(manage_roles=True)
@check_not_blocked()
async def create_reaction_role_slash(
    interaction: discord.Interaction,
    text: str,
    color: str,
    emoji1: str, role1: discord.Role,
    emoji2: Optional[str] = None, role2: Optional[discord.Role] = None,
    emoji3: Optional[str] = None, role3: Optional[discord.Role] = None,
    emoji4: Optional[str] = None, role4: Optional[discord.Role] = None,
    emoji5: Optional[str] = None, role5: Optional[discord.Role] = None,
    emoji6: Optional[str] = None, role6: Optional[discord.Role] = None
):
    """Create reaction role message with up to 6 emoji-role pairs"""
    
    # Build role mapping
    role_mapping = {emoji1: role1.id}
    
    pairs = [
        (emoji2, role2), (emoji3, role3), (emoji4, role4),
        (emoji5, role5), (emoji6, role6)
    ]
    
    for emoji, role in pairs:
        if emoji and role:
            role_mapping[emoji] = role.id
    
    # Create embed
    embed_color = parse_color(color)
    embed = discord.Embed(
        title="🎭 Reaction Roles",
        description=text,
        color=embed_color
    )
    
    # Add role information
    role_info = []
    for emoji, role_id in role_mapping.items():
        role = interaction.guild.get_role(role_id)
        if role:
            role_info.append(f"{emoji} - {role.mention}")
    
    embed.add_field(name="Available Roles", value="\n".join(role_info), inline=False)
    embed.set_footer(text="React with emojis to get roles!")
    
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    # Add reactions
    for emoji in role_mapping.keys():
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await interaction.followup.send(f"❌ Could not add reaction {emoji}. Make sure it's a valid emoji.", ephemeral=True)
            return
    
    # Store reaction role data
    reaction_roles[message.id] = role_mapping
    
    await interaction.followup.send(f"✅ Reaction role message created with {len(role_mapping)} roles!", ephemeral=True)

@bot.tree.command(name="unblock", description="Unblock a user from using bot functions")
@app_commands.describe(user="User to unblock")
@check_specific_user()
async def unblock_slash(interaction: discord.Interaction, user: discord.User):
    """Unblock a user from using bot functions (bot owner only)"""
    
    if user.id not in blocked_users:
        await interaction.response.send_message(f"❌ {user.display_name} is not blocked.", ephemeral=True)
        return
    
    blocked_users.remove(user.id)
    
    embed = discord.Embed(
        title="✅ User Unblocked",
        description=f"{user.mention} has been unblocked and can now use bot functions",
        color=discord.Color.green()
    )
    embed.set_footer(text=f"Action by {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)

# ===== RUN BOT =====

if __name__ == "__main__":
    run_flask()
    try:
        bot.run(os.getenv("DISCORD_BOT_TOKEN"))
    except Exception as e:
        print(f"Error running bot: {e}")
