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

# Smart user finder function (like Dyno)
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
    
    # Check time in server
    if 'time_in_server' in requirements:
        if member.joined_at:
            time_in_server = (datetime.utcnow() - member.joined_at.replace(tzinfo=None)).total_seconds()
            required_time = requirements['time_in_server']
            if time_in_server < required_time:
                required_time_str = format_duration(required_time)
                actual_time_str = format_duration(int(time_in_server))
                failed_requirements.append(f"Need {required_time_str} in server (has {actual_time_str})")
        else:
            failed_requirements.append("Cannot verify join date")
    
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
                    ("**Message Tracking**", "`,snipe` `,s` - Show last deleted message\n`,editsnipe` `,es` - Show last edited message\n`,snipepages` `,sp` - List all deleted messages\n`,spforce` `,spf` - Moderator-only unfiltered snipe", False),
                    ("**Moderation**", "`,namelock` `,nl` - Lock user's nickname\n`,rename` `,re` - Change user's nickname\n`,saywb` - Send message via webhook", False)
                ]
            },
            {
                "title": "📜 SnipeBot Commands - Page 2", 
                "fields": [
                    ("**Giveaways**", "`,gw [id]` - Reroll giveaway winner\n`/giveaway` - Create new giveaway\n`/giveaway-host-role` - Set host roles", False),
                    ("**Management**", "`,block` - Block user from bot\n`,namelockimmune` `,nli` - Make user immune to namelock\n`,mess [user]` - Show user message count", False)
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
                    ("**Usage Examples**", "`,mess wer` - Find user with partial name\n`,create [text] 🦝 @Role red` - Create reaction role\n`,gw 123456789` - Reroll giveaway", False)
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
                    ("**Storage**", f"**Sniped Messages:** {sum(len(msgs) for msgs in sniped_messages.values())}\n**Blocked Users:** {len(blocked_users)}\n**Active Giveaways:** {len(active_giveaways)}", False)
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

# Giveaway Join View with List button
class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_data):
        super().__init__(timeout=None)
        self.giveaway_data = giveaway_data
    
    @discord.ui.button(label="🎉 Join Giveaway", style=discord.ButtonStyle.primary, custom_id="join_giveaway")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild
        
        # Check if user is blocked
        if is_user_blocked(user.id):
            return  # Silently ignore blocked users
        
        # Check if user already joined
        if user.id in self.giveaway_data.get('participants', []):
            await interaction.response.send_message("❌ You've already joined this giveaway!", ephemeral=True)
            return
        
        # Check requirements
        requirements = self.giveaway_data.get('requirements', {})
        meets_reqs, failed_reqs = check_giveaway_requirements(user, requirements)
        
        if not meets_reqs:
            failed_text = "\n".join(f"• {req}" for req in failed_reqs)
            embed = discord.Embed(
                title="❌ Requirements Not Met",
                description=f"You don't meet the following requirements:\n{failed_text}",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Add user to participants
        if 'participants' not in self.giveaway_data:
            self.giveaway_data['participants'] = []
        self.giveaway_data['participants'].append(user.id)
        
        await interaction.response.send_message("✅ Successfully joined the giveaway! Good luck!", ephemeral=True)
    
    @discord.ui.button(label="📋 List Participants", style=discord.ButtonStyle.secondary, custom_id="list_participants")
    async def list_participants(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user is blocked
        if is_user_blocked(interaction.user.id):
            return  # Silently ignore blocked users
        
        participants = self.giveaway_data.get('participants', [])
        
        if not participants:
            embed = discord.Embed(
                title="📋 Giveaway Participants",
                description="No one has joined this giveaway yet.",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create pagination view for participants
        participant_list = []
        for user_id in participants:
            user = bot.get_user(user_id)
            if user:
                participant_list.append(f"• {user.display_name} ({user.mention})")
            else:
                participant_list.append(f"• Unknown User (ID: {user_id})")
        
        # Split into pages of 10
        pages = []
        for i in range(0, len(participant_list), 10):
            page_participants = participant_list[i:i+10]
            pages.append("\n".join(page_participants))
        
        if len(pages) == 1:
            embed = discord.Embed(
                title="📋 Giveaway Participants",
                description=pages[0],
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Total: {len(participants)} participants")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            # TODO: Implement pagination for multiple pages
            embed = discord.Embed(
                title="📋 Giveaway Participants",
                description=pages[0] + f"\n\n*Showing first 10 of {len(participants)} participants*",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

# Bot event handlers
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

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    message_id = reaction.message.id
    
    # Handle giveaway reactions
    if message_id in active_giveaways:
        giveaway = active_giveaways[message_id]
        
        # Check if reaction is the giveaway emoji
        if str(reaction.emoji) == giveaway.get('emoji', '🎉'):
            # Check if user meets requirements
            if reaction.message.guild:
                member = reaction.message.guild.get_member(user.id)
                if member:
                    meets_req, failed_req = check_giveaway_requirements(member, giveaway.get('requirements'))
                    if not meets_req:
                        # Remove reaction if user doesn't meet requirements
                        try:
                            await reaction.remove(user)
                            # Optionally DM user about failed requirements
                            try:
                                await user.send(f"You don't meet the requirements for this giveaway:\n" + "\n".join(failed_req))
                            except:
                                pass
                        except:
                            pass
    
    # Handle reaction roles
    if message_id in reaction_roles:
        emoji_str = str(reaction.emoji)
        if emoji_str in reaction_roles[message_id]:
            role_id = reaction_roles[message_id][emoji_str]
            guild = reaction.message.guild
            if guild:
                role = guild.get_role(role_id)
                member = guild.get_member(user.id)
                if role and member:
                    try:
                        await member.add_roles(role, reason="Reaction role")
                    except discord.Forbidden:
                        pass

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return
    
    message_id = reaction.message.id
    
    # Handle reaction roles removal
    if message_id in reaction_roles:
        emoji_str = str(reaction.emoji)
        if emoji_str in reaction_roles[message_id]:
            role_id = reaction_roles[message_id][emoji_str]
            guild = reaction.message.guild
            if guild:
                role = guild.get_role(role_id)
                member = guild.get_member(user.id)
                if role and member:
                    try:
                        await member.remove_roles(role, reason="Reaction role removed")
                    except discord.Forbidden:
                        pass

# Slash Commands Start Here

# Snipe command
@bot.tree.command(name="snipe", description="Show the last deleted message in this channel")
async def snipe(interaction: discord.Interaction):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
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

# Edit snipe command
@bot.tree.command(name="editsnipe", description="Show the last edited message in this channel")
async def editsnipe(interaction: discord.Interaction):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
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

# Clear snipe command
@bot.tree.command(name="clearsnipe", description="Clear sniped messages for this channel")
@app_commands.describe(scope="Choose what to clear: 'channel' (default) or 'all'")
async def clearsnipe(interaction: discord.Interaction, scope: str = "channel"):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
    # Check permissions
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need 'Manage Messages' permission to use this command.", ephemeral=True)
        return
    
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

# Giveaway command
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
async def giveaway(
    interaction: discord.Interaction,
    duration: str,
    prize: str,
    winners: int = 1,
    channel: discord.TextChannel = None,
    required_role: discord.Role = None,
    blacklisted_role: discord.Role = None,
    required_messages: int = None
):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
    # Check if user can host giveaways
    if not can_host_giveaway(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to host giveaways.", ephemeral=True)
        return
    
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

# Giveaway host role command
@bot.tree.command(name="giveaway-host-role", description="Set roles that can host giveaways")
@app_commands.describe(
    action="Add or remove roles",
    role="Role to add/remove"
)
@app_commands.choices(action=[
    app_commands.Choice(name="add", value="add"),
    app_commands.Choice(name="remove", value="remove"),
    app_commands.Choice(name="list", value="list"),
    app_commands.Choice(name="clear", value="clear")
])
async def giveaway_host_role(interaction: discord.Interaction, action: str, role: discord.Role = None):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
    # Check permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permission to use this command.", ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    
    if action == "list":
        if guild_id not in giveaway_host_roles or not giveaway_host_roles[guild_id]:
            await interaction.response.send_message("❌ No giveaway host roles set for this server.", ephemeral=True)
            return
        
        roles = []
        for role_id in giveaway_host_roles[guild_id]:
            role_obj = interaction.guild.get_role(role_id)
            if role_obj:
                roles.append(role_obj.mention)
        
        if roles:
            embed = discord.Embed(
                title="🎉 Giveaway Host Roles",
                description="\n".join(roles),
                color=discord.Color.gold()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ No valid giveaway host roles found.", ephemeral=True)
    
    elif action == "clear":
        if guild_id in giveaway_host_roles:
            del giveaway_host_roles[guild_id]
        await interaction.response.send_message("✅ Cleared all giveaway host roles for this server.")
    
    elif action in ["add", "remove"]:
        if not role:
            await interaction.response.send_message("❌ You must specify a role for this action.", ephemeral=True)
            return
        
        if guild_id not in giveaway_host_roles:
            giveaway_host_roles[guild_id] = []
        
        if action == "add":
            if role.id not in giveaway_host_roles[guild_id]:
                giveaway_host_roles[guild_id].append(role.id)
                await interaction.response.send_message(f"✅ Added {role.mention} as a giveaway host role.")
            else:
                await interaction.response.send_message(f"❌ {role.mention} is already a giveaway host role.", ephemeral=True)
        
        elif action == "remove":
            if role.id in giveaway_host_roles[guild_id]:
                giveaway_host_roles[guild_id].remove(role.id)
                await interaction.response.send_message(f"✅ Removed {role.mention} from giveaway host roles.")
            else:
                await interaction.response.send_message(f"❌ {role.mention} is not a giveaway host role.", ephemeral=True)

# Block command
@bot.tree.command(name="block", description="Block a user from using bot functions")
@app_commands.describe(user="User to block")
async def block_user(interaction: discord.Interaction, user: discord.User):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
    # Check permissions
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permission to use this command.", ephemeral=True)
        return
    
    if user.id == interaction.user.id:
        await interaction.response.send_message("❌ You cannot block yourself.", ephemeral=True)
        return
    
    if user.id in blocked_users:
        await interaction.response.send_message(f"❌ {user.mention} is already blocked.", ephemeral=True)
        return
    
    blocked_users.add(user.id)
    await interaction.response.send_message(f"✅ Blocked {user.mention} from using bot functions.")

# Unblock command
@bot.tree.command(name="unblock", description="Unblock a user from using bot functions")
@app_commands.describe(user="User to unblock")
async def unblock_user(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != 776883692983156736:  # Bot owner only
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if user.id not in blocked_users:
        await interaction.response.send_message(f"❌ {user.mention} is not blocked.", ephemeral=True)
        return
    
    blocked_users.remove(user.id)
    await interaction.response.send_message(f"✅ Unblocked {user.mention}.")

# Create reaction role command
@bot.tree.command(name="create", description="Create a reaction role message")
@app_commands.describe(
    text="Message content",
    emoji="Emoji for the reaction",
    role="Role to assign",
    color="Embed color (hex or color name)"
)
async def create_reaction_role(
    interaction: discord.Interaction,
    text: str,
    emoji: str,
    role: discord.Role,
    color: str = "blue"
):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
    # Check permissions
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You need 'Manage Roles' permission to use this command.", ephemeral=True)
        return
    
    # Check if bot can manage the role
    bot_member = interaction.guild.me
    if role.position >= bot_member.top_role.position:
        await interaction.response.send_message("❌ I cannot manage this role. Make sure my role is higher than the target role.", ephemeral=True)
        return
    
    # Parse color
    embed_color = parse_color(color)
    
    # Create embed
    embed = discord.Embed(
        description=text,
        color=embed_color
    )
    
    embed.add_field(
        name="React to get role:",
        value=f"{emoji} {role.mention}",
        inline=False
    )
    
    await interaction.response.send_message("✅ Reaction role message created!")
    
    # Send the reaction role message
    message = await interaction.followup.send(embed=embed)
    await message.add_reaction(emoji)
    
    # Store reaction role data
    reaction_roles[message.id] = {str(emoji): role.id}

# Helper function to end giveaway
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
    
    # Get all users who reacted with the giveaway emoji
    participants = []
    for reaction in message.reactions:
        if str(reaction.emoji) == giveaway.get('emoji', '🎉'):
            async for user in reaction.users():
                if not user.bot and user.id not in participants:
                    # Check if user meets requirements
                    if message.guild:
                        member = message.guild.get_member(user.id)
                        if member:
                            meets_req, _ = check_giveaway_requirements(member, giveaway.get('requirements'))
                            if meets_req:
                                participants.append(user.id)
    
    # Clean up
    del active_giveaways[message_id]
    
    # Select winners
    num_winners = min(giveaway['winners'], len(participants))
    
    if num_winners == 0:
        embed = discord.Embed(
            title="🎉 Giveaway Ended",
            description=f"**Prize:** {giveaway['prize']}\n\n❌ No valid participants found!",
            color=discord.Color.red()
        )
    else:
        winners = random.sample(participants, num_winners)
        winner_mentions = []
        
        for winner_id in winners:
            winner = bot.get_user(winner_id)
            if winner:
                winner_mentions.append(winner.mention)
        
        if len(winner_mentions) == 1:
            winners_text = f"🎊 **Winner:** {winner_mentions[0]}"
        else:
            winners_text = f"🎊 **Winners:**\n" + "\n".join(f"• {winner}" for winner in winner_mentions)
        
        embed = discord.Embed(
            title="🎉 Giveaway Ended",
            description=f"**Prize:** {giveaway['prize']}\n\n{winners_text}",
            color=discord.Color.gold()
        )
    
    host = bot.get_user(giveaway['host'])
    if host:
        embed.set_footer(text=f"Hosted by {host.display_name}")
    
    await message.edit(embed=embed, view=None)
    
    # Send winner announcement
    if num_winners > 0:
        await channel.send(f"🎉 Congratulations {', '.join(winner_mentions)}! You won **{giveaway['prize']}**!")

# Regular commands (prefix commands) start here

@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe_cmd(ctx):
    """Show the last deleted message in this channel"""
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages:
        await ctx.send("❌ Nothing to snipe in this channel!")
        return
    
    msg_data = sniped_messages[channel_id]
    
    # Filter content if not moderator
    content = msg_data['content']
    if not ctx.author.guild_permissions.manage_messages:
        content = filter_content(content)
    
    # Create embed
    embed = discord.Embed(
        description=content or "*No text content*",
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
        for i, attachment in enumerate(msg_data['attachments'][:3]):
            embed.add_field(name=f"Attachment {i+1}", value=attachment, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='editsnipe', aliases=['es'])
@not_blocked()
async def editsnipe_cmd(ctx):
    """Show the last edited message in this channel"""
    channel_id = ctx.channel.id
    
    if channel_id not in edited_messages:
        await ctx.send("❌ No edited messages to snipe in this channel!")
        return
    
    msg_data = edited_messages[channel_id]
    
    # Filter content if not moderator
    before_content = msg_data['before_content']
    after_content = msg_data['after_content']
    
    if not ctx.author.guild_permissions.manage_messages:
        before_content = filter_content(before_content)
        after_content = filter_content(after_content)
    
    embed = discord.Embed(color=discord.Color.orange(), timestamp=msg_data['timestamp'])
    
    embed.set_author(
        name=msg_data['author'].display_name,
        icon_url=msg_data['author'].display_avatar.url
    )
    
    embed.add_field(
        name="Before",
        value=before_content or "*No content*",
        inline=False
    )
    
    embed.add_field(
        name="After", 
        value=after_content or "*No content*",
        inline=False
    )
    
    edit_time = msg_data.get('edited_at', msg_data['timestamp'])
    embed.set_footer(text=f"Edited at {edit_time.strftime('%H:%M:%S')}")
    
    await ctx.send(embed=embed)

@bot.command(name='help')
@not_blocked()
async def help_cmd(ctx):
    """Show bot help with pagination"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

@bot.command(name='manage')
@is_specific_user()
async def manage_cmd(ctx):
    """Bot management panel (bot owner only)"""
    view = ManagePaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

@bot.command(name='namelock', aliases=['nl'])
@has_manage_nicknames()
async def namelock_cmd(ctx, user_input: str = None, *, nickname: str = None):
    """Lock a user's nickname"""
    if not ctx.guild:
        await ctx.send("❌ This command can only be used in a server.")
        return
    
    if not user_input:
        await ctx.send("❌ Please specify a user to namelock.")
        return
    
    # Find user
    member = None
    try:
        # Try to parse as user ID or mention
        user_id = int(user_input.strip('<@!>'))
        member = ctx.guild.get_member(user_id)
    except ValueError:
        # Try to find by name
        member = find_user_by_name(ctx.guild, user_input)
    
    if not member:
        await ctx.send(f"❌ Could not find user: {user_input}")
        return
    
    # Check permissions
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("❌ You cannot namelock this user (role hierarchy).")
        return
    
    if member.id == ctx.guild.owner_id:
        await ctx.send("❌ You cannot namelock the server owner.")
        return
    
    # If no nickname provided, use current display name
    if not nickname:
        nickname = member.display_name
    
    # Apply namelock
    try:
        await member.edit(nick=nickname, reason=f"Namelocked by {ctx.author}")
        namelocked_users[member.id] = nickname
        
        embed = discord.Embed(
            title="🔒 User Namelocked",
            description=f"**User:** {member.mention}\n**Locked Name:** {nickname}",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Namelocked by {ctx.author.display_name}")
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname.")

@bot.command(name='rename', aliases=['re'])
@has_manage_nicknames()
async def rename_cmd(ctx, user_input: str = None, *, nickname: str = None):
    """Change a user's nickname"""
    if not ctx.guild:
        await ctx.send("❌ This command can only be used in a server.")
        return
    
    if not user_input:
        await ctx.send("❌ Please specify a user to rename.")
        return
    
    # Find user
    member = None
    try:
        user_id = int(user_input.strip('<@!>'))
        member = ctx.guild.get_member(user_id)
    except ValueError:
        member = find_user_by_name(ctx.guild, user_input)
    
    if not member:
        await ctx.send(f"❌ Could not find user: {user_input}")
        return
    
    # Check permissions
    if member.top_role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
        await ctx.send("❌ You cannot rename this user (role hierarchy).")
        return
    
    if member.id == ctx.guild.owner_id:
        await ctx.send("❌ You cannot rename the server owner.")
        return
    
    old_nick = member.display_name
    
    # Apply rename
    try:
        await member.edit(nick=nickname, reason=f"Renamed by {ctx.author}")
        
        embed = discord.Embed(
            title="✏️ User Renamed",
            color=discord.Color.blue()
        )
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Old Name", value=old_nick, inline=True)
        embed.add_field(name="New Name", value=nickname or member.name, inline=True)
        embed.set_footer(text=f"Renamed by {ctx.author.display_name}")
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname.")

@bot.command(name='block')
@has_permission_or_is_admin()
async def block_cmd(ctx, user_input: str = None):
    """Block a user from using bot functions"""
    if not user_input:
        await ctx.send("❌ Please specify a user to block.")
        return
    
    # Find user
    user = None
    try:
        user_id = int(user_input.strip('<@!>'))
        user = bot.get_user(user_id)
    except ValueError:
        # Try to find by name in current guild
        if ctx.guild:
            member = find_user_by_name(ctx.guild, user_input)
            if member:
                user = member
    
    if not user:
        await ctx.send(f"❌ Could not find user: {user_input}")
        return
    
    if user.id == ctx.author.id:
        await ctx.send("❌ You cannot block yourself.")
        return
    
    if user.id in blocked_users:
        await ctx.send(f"❌ {user.mention} is already blocked.")
        return
    
    blocked_users.add(user.id)
    await ctx.send(f"✅ Blocked {user.mention} from using bot functions.")

@bot.command(name='namelockimmune', aliases=['nli'])
@is_specific_user()
async def namelock_immune_cmd(ctx, user_input: str = None):
    """Make a user immune to namelock (bot owner only)"""
    if not user_input:
        await ctx.send("❌ Please specify a user.")
        return
    
    # Find user
    user = None
    try:
        user_id = int(user_input.strip('<@!>'))
        user = bot.get_user(user_id)
    except ValueError:
        if ctx.guild:
            member = find_user_by_name(ctx.guild, user_input)
            if member:
                user = member
    
    if not user:
        await ctx.send(f"❌ Could not find user: {user_input}")
        return
    
    if user.id in namelock_immune_users:
        namelock_immune_users.remove(user.id)
        await ctx.send(f"✅ Removed namelock immunity from {user.mention}.")
    else:
        namelock_immune_users.add(user.id)
        await ctx.send(f"✅ Made {user.mention} immune to namelock.")

@bot.command(name='mess')
@not_blocked()
async def message_count_cmd(ctx, user_input: str = None):
    """Show user's message count"""
    if not ctx.guild:
        await ctx.send("❌ This command can only be used in a server.")
        return
    
    # If no user specified, show own count
    if not user_input:
        user = ctx.author
    else:
        # Find user
        user = None
        try:
            user_id = int(user_input.strip('<@!>'))
            user = ctx.guild.get_member(user_id)
        except ValueError:
            user = find_user_by_name(ctx.guild, user_input)
        
        if not user:
            await ctx.send(f"❌ Could not find user: {user_input}")
            return
    
    count = get_user_message_count(ctx.guild.id, user.id)
    
    embed = discord.Embed(
        title="📊 Message Count",
        description=f"**User:** {user.mention}\n**Messages:** {count:,}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='create')
@not_blocked()
@commands.has_permissions(manage_roles=True)
async def create_reaction_role_cmd(ctx, *, args: str = None):
    """Create a reaction role message"""
    if not ctx.guild:
        await ctx.send("❌ This command can only be used in a server.")
        return
    
    if not args:
        await ctx.send("❌ Usage: `,create [text] [emoji] [role] [color]`\nExample: `,create Get your role here! 🦝 @Member blue`")
        return
    
    # Parse arguments
    parts = args.split()
    if len(parts) < 3:
        await ctx.send("❌ Usage: `,create [text] [emoji] [role] [color]`\nExample: `,create Get your role here! 🦝 @Member blue`")
        return
    
    # Extract color if provided (last argument)
    color = "blue"
    if len(parts) >= 4:
        color = parts[-1]
        parts = parts[:-1]
    
    # Extract role (second to last argument)
    role_mention = parts[-1]
    emoji = parts[-2]
    
    # Everything else is the text
    text = " ".join(parts[:-2])
    
    # Parse role
    role = None
    try:
        role_id = int(role_mention.strip('<@&>'))
        role = ctx.guild.get_role(role_id)
    except ValueError:
        # Try to find role by name
        for guild_role in ctx.guild.roles:
            if guild_role.name.lower() == role_mention.lower():
                role = guild_role
                break
    
    if not role:
        await ctx.send(f"❌ Could not find role: {role_mention}")
        return
    
    # Check if bot can manage the role
    bot_member = ctx.guild.me
    if role.position >= bot_member.top_role.position:
        await ctx.send("❌ I cannot manage this role. Make sure my role is higher than the target role.")
        return
    
    # Parse color
    embed_color = parse_color(color)
    
    # Create embed
    embed = discord.Embed(
        description=text,
        color=embed_color
    )
    
    embed.add_field(
        name="React to get role:",
        value=f"{emoji} {role.mention}",
        inline=False
    )
    
    # Send the reaction role message
    message = await ctx.send(embed=embed)
    await message.add_reaction(emoji)
    
    # Store reaction role data
    reaction_roles[message.id] = {str(emoji): role.id}

@bot.command(name='saywb')
@is_moderator()
async def say_webhook_cmd(ctx, *, message_content: str = None):
    """Send a message via webhook"""
    if not message_content:
        await ctx.send("❌ Please provide a message to send.")
        return
    
    try:
        webhook = await get_or_create_webhook(ctx.channel)
        await webhook.send(message_content, username="SnipeBot", avatar_url=bot.user.display_avatar.url)
        await ctx.message.delete()
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage webhooks in this channel.")
    except Exception as e:
        await ctx.send(f"❌ Failed to send webhook message: {str(e)}")

@bot.command(name='gw')
@not_blocked()
async def giveaway_reroll_cmd(ctx, message_id: str = None):
    """Reroll a giveaway winner"""
    if not message_id:
        await ctx.send("❌ Please provide a giveaway message ID.")
        return
    
    try:
        msg_id = int(message_id)
    except ValueError:
        await ctx.send("❌ Invalid message ID.")
        return
    
    # Check if user can host giveaways
    if not can_host_giveaway(ctx.author):
        await ctx.send("❌ You don't have permission to reroll giveaways.")
        return
    
    try:
        message = await ctx.channel.fetch_message(msg_id)
    except discord.NotFound:
        await ctx.send("❌ Message not found.")
        return
    
    # Check if it's a giveaway message
    if not message.embeds or "GIVEAWAY" not in message.embeds[0].title:
        await ctx.send("❌ This is not a giveaway message.")
        return
    
    # Get participants from reactions
    participants = []
    for reaction in message.reactions:
        if str(reaction.emoji) == "🎉":
            async for user in reaction.users():
                if not user.bot:
                    if ctx.guild:
                        member = ctx.guild.get_member(user.id)
                        if member:
                            participants.append(user)
    
    if not participants:
        await ctx.send("❌ No participants found.")
        return
    
    # Select new winner
    winner = random.choice(participants)
    
    await ctx.send(f"🎉 New winner: {winner.mention}! Congratulations!")

# Start Flask server
run_flask()

# Run the bot
bot.run(os.getenv('DISCORD_TOKEN'))
