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
        
        # Create webhook embed showing participants with pagination
        try:
            webhook = await get_or_create_webhook(interaction.channel)
            
            # Create pagination view
            view = GiveawayParticipantsPaginationView(participants, self.giveaway_data, interaction.guild)
            embed = view.get_embed()
            
            # Send via webhook for better presentation
            await webhook.send(embed=embed, view=view, username="SnipeBot", 
                             avatar_url="https://cdn.discordapp.com/avatars/1234567890/avatar.png")
            
            await interaction.response.send_message("✅ Participant list sent above!", ephemeral=True)
            
        except Exception as e:
            # Fallback to regular response if webhook fails
            view = GiveawayParticipantsPaginationView(participants, self.giveaway_data, interaction.guild)
            embed = view.get_embed()
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# Events
@bot.event
async def on_ready():
    print(f'✅ {bot.user} is now online!')
    print(f'📊 Connected to {len(bot.guilds)} guilds')
    print(f'👥 Serving {len(bot.users)} users')
    
    # Start Flask server
    run_flask()
    
    try:
        synced = await bot.tree.sync()
        print(f'🔄 Synced {len(synced)} command(s)')
    except Exception as e:
        print(f'❌ Failed to sync commands: {e}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Count user messages for giveaway requirements
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    
    # Initialize channel storage if needed
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []
    
    # Check if content is offensive
    has_offensive = is_offensive_content(message.content) if message.content else False
    
    # Create message data
    message_data = {
        'content': message.content,
        'author': message.author,
        'time': datetime.utcnow(),
        'attachments': [att.url for att in message.attachments] if message.attachments else [],
        'has_offensive_content': has_offensive
    }
    
    # Add to front of list and maintain limit
    sniped_messages[channel_id].insert(0, message_data)
    if len(sniped_messages[channel_id]) > MAX_MESSAGES:
        sniped_messages[channel_id] = sniped_messages[channel_id][:MAX_MESSAGES]

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    channel_id = before.channel.id
    
    # Initialize channel storage if needed
    if channel_id not in edited_messages:
        edited_messages[channel_id] = []
    
    # Check if content is offensive
    has_offensive = is_offensive_content(before.content) if before.content else False
    
    # Create message data
    message_data = {
        'before': before.content,
        'after': after.content,
        'author': before.author,
        'time': datetime.utcnow(),
        'attachments': [att.url for att in before.attachments] if before.attachments else [],
        'has_offensive_content': has_offensive
    }
    
    # Add to front of list and maintain limit
    edited_messages[channel_id].insert(0, message_data)
    if len(edited_messages[channel_id]) > MAX_MESSAGES:
        edited_messages[channel_id] = edited_messages[channel_id][:MAX_MESSAGES]

@bot.event
async def on_member_update(before, after):
    # Check if nickname changed and user is namelocked
    if before.display_name != after.display_name and after.id in namelocked_users:
        # Check if user is immune to namelock
        if after.id not in namelock_immune_users:
            locked_nickname = namelocked_users[after.id]
            try:
                await after.edit(nick=locked_nickname, reason="User is namelocked")
            except discord.Forbidden:
                pass  # Bot doesn't have permission

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    # Check if user is blocked
    if is_user_blocked(user.id):
        return
    
    message_id = reaction.message.id
    
    # Check if this message has reaction roles
    if message_id in reaction_roles:
        emoji_str = str(reaction.emoji)
        if emoji_str in reaction_roles[message_id]:
            role_id = reaction_roles[message_id][emoji_str]
            guild = reaction.message.guild
            role = guild.get_role(role_id)
            member = guild.get_member(user.id)
            
            if role and member:
                try:
                    await member.add_roles(role, reason="Reaction role")
                except discord.Forbidden:
                    pass  # Bot doesn't have permission

@bot.event
async def on_reaction_remove(reaction, user):
    if user.bot:
        return
    
    # Check if user is blocked
    if is_user_blocked(user.id):
        return
    
    message_id = reaction.message.id
    
    # Check if this message has reaction roles
    if message_id in reaction_roles:
        emoji_str = str(reaction.emoji)
        if emoji_str in reaction_roles[message_id]:
            role_id = reaction_roles[message_id][emoji_str]
            guild = reaction.message.guild
            role = guild.get_role(role_id)
            member = guild.get_member(user.id)
            
            if role and member:
                try:
                    await member.remove_roles(role, reason="Reaction role removed")
                except discord.Forbidden:
                    pass  # Bot doesn't have permission

# ===== HELP COMMAND =====
@bot.command(name='help')
@not_blocked()
async def help_command(ctx):
    """Show bot commands with pagination"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# ===== MANAGE COMMAND =====
@bot.command(name='manage')
@is_specific_user()
async def manage_command(ctx):
    """Bot management panel (Bot owner only)"""
    view = ManagePaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# ===== MESSAGE COUNT COMMAND =====
@bot.command(name='mess')
@not_blocked()
async def mess_command(ctx, *, user_input: str):
    """Show user message count - supports partial name matching"""
    if not ctx.guild:
        await ctx.send("❌ This command can only be used in a server.")
        return
    
    # Try to find user by name using smart matching
    target_user = find_user_by_name(ctx.guild, user_input)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user matching '{user_input}'")
        return
    
    message_count = get_user_message_count(ctx.guild.id, target_user.id)
    
    embed = discord.Embed(
        title="📊 Message Count",
        description=f"**{target_user.display_name}** has sent **{message_count}** messages in this server",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)
    embed.set_footer(text=f"Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

# ===== REACTION ROLE COMMAND =====
@bot.command(name='create')
@is_moderator()
async def create_reaction_role(ctx, *, args: str):
    """Create reaction role message - ,create [content] [emoji] [role] [emoji] [role] ... [color]"""
    if not ctx.guild:
        await ctx.send("❌ This command can only be used in a server.")
        return
    
    # Parse arguments
    parts = args.split()
    if len(parts) < 4:  # Need at least content, emoji, role, color
        await ctx.send("❌ Usage: `,create [content] [emoji] [role] [emoji] [role] ... [color]`\nExample: `,create Please react 🦝 @Member 🎮 @Gamer red`")
        return
    
    # Extract color (last argument)
    color_str = parts[-1]
    color = parse_color(color_str)
    
    # Extract content (everything before emoji-role pairs and color)
    emoji_role_pairs = []
    content_parts = []
    
    i = 0
    while i < len(parts) - 1:  # -1 to exclude color
        part = parts[i]
        
        # Check if this looks like an emoji (contains emoji or is <:name:id>)
        if any(ord(char) > 127 for char in part) or part.startswith('<:') or part.startswith('<a:'):
            # This is an emoji, next part should be a role
            if i + 1 < len(parts) - 1:  # Make sure there's a role and we're not at color
                emoji = part
                role_mention = parts[i + 1]
                
                # Parse role
                role = None
                if role_mention.startswith('<@&') and role_mention.endswith('>'):
                    role_id = int(role_mention[3:-1])
                    role = ctx.guild.get_role(role_id)
                else:
                    # Try to find role by name
                    role = discord.utils.get(ctx.guild.roles, name=role_mention.replace('@', ''))
                
                if role:
                    emoji_role_pairs.append((emoji, role))
                    i += 2  # Skip emoji and role
                else:
                    content_parts.append(part)
                    i += 1
            else:
                content_parts.append(part)
                i += 1
        else:
            content_parts.append(part)
            i += 1
    
    if not emoji_role_pairs:
        await ctx.send("❌ No valid emoji-role pairs found!\nExample: `,create Please react 🦝 @Member 🎮 @Gamer red`")
        return
    
    if len(emoji_role_pairs) > 6:
        await ctx.send("❌ Maximum 6 reaction roles allowed per message!")
        return
    
    content = ' '.join(content_parts)
    if not content:
        content = "Please react to get your roles!"
    
    # Create embed
    embed = discord.Embed(
        title="🎭 Reaction Roles",
        description=content,
        color=color
    )
    
    # Add role information
    role_info = []
    for emoji, role in emoji_role_pairs:
        role_info.append(f"{emoji} → {role.mention}")
    
    embed.add_field(
        name="Available Roles",
        value="\n".join(role_info),
        inline=False
    )
    
    embed.set_footer(text="React below to get your roles!")
    
    # Send message
    message = await ctx.send(embed=embed)
    
    # Add reactions and store reaction roles
    reaction_roles[message.id] = {}
    
    for emoji, role in emoji_role_pairs:
        try:
            await message.add_reaction(emoji)
            reaction_roles[message.id][str(emoji)] = role.id
        except discord.HTTPException:
            await ctx.send(f"❌ Failed to add reaction {emoji}. Make sure it's a valid emoji.")
    
    await ctx.send(f"✅ Reaction role message created with {len(emoji_role_pairs)} roles!")

# ===== SLASH COMMAND: REACTION ROLE =====
@bot.tree.command(name="create", description="Create reaction role message")
@app_commands.describe(
    content="The message content",
    emoji1="First emoji",
    role1="First role",
    emoji2="Second emoji (optional)",
    role2="Second role (optional)", 
    emoji3="Third emoji (optional)",
    role3="Third role (optional)",
    emoji4="Fourth emoji (optional)",
    role4="Fourth role (optional)",
    emoji5="Fifth emoji (optional)",
    role5="Fifth role (optional)",
    emoji6="Sixth emoji (optional)",
    role6="Sixth role (optional)",
    color="Embed color (optional)"
)
@check_not_blocked()
@check_moderator()
async def slash_create_reaction_role(
    interaction: discord.Interaction,
    content: str,
    emoji1: str,
    role1: discord.Role,
    emoji2: Optional[str] = None,
    role2: Optional[discord.Role] = None,
    emoji3: Optional[str] = None,
    role3: Optional[discord.Role] = None,
    emoji4: Optional[str] = None,
    role4: Optional[discord.Role] = None,
    emoji5: Optional[str] = None,
    role5: Optional[discord.Role] = None,
    emoji6: Optional[str] = None,
    role6: Optional[discord.Role] = None,
    color: Optional[str] = "blue"
):
    """Create reaction role message via slash command"""
    
    # Collect emoji-role pairs
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
    
    # Parse color
    embed_color = parse_color(color)
    
    # Create embed
    embed = discord.Embed(
        title="🎭 Reaction Roles",
        description=content,
        color=embed_color
    )
    
    # Add role information
    role_info = []
    for emoji, role in emoji_role_pairs:
        role_info.append(f"{emoji} → {role.mention}")
    
    embed.add_field(
        name="Available Roles",
        value="\n".join(role_info),
        inline=False
    )
    
    embed.set_footer(text="React below to get your roles!")
    
    # Send message
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    # Add reactions and store reaction roles
    reaction_roles[message.id] = {}
    
    for emoji, role in emoji_role_pairs:
        try:
            await message.add_reaction(emoji)
            reaction_roles[message.id][str(emoji)] = role.id
        except discord.HTTPException:
            await interaction.followup.send(f"❌ Failed to add reaction {emoji}. Make sure it's a valid emoji.", ephemeral=True)
    
    await interaction.followup.send(f"✅ Reaction role message created with {len(emoji_role_pairs)} roles!", ephemeral=True)

# ===== SNIPE COMMANDS =====
@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe(ctx, message_number: int = 1, channel: Union[discord.TextChannel, discord.Thread] = None):
    """Show deleted message"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        embed = discord.Embed(
            title="❌ No Deleted Messages",
            description="No deleted messages found in this channel.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)
    
    if message_number < 1 or message_number > len(sniped_messages[channel_id]):
        embed = discord.Embed(
            title="❌ Invalid Message Number",
            description=f"Please choose a number between 1 and {len(sniped_messages[channel_id])}.",
            color=discord.Color.red()
        )
        return await ctx.send(embed=embed)
    
    msg = sniped_messages[channel_id][message_number - 1]
    
    # Check if user is moderator for filtering
    is_mod = (ctx.author.guild_permissions.administrator or
              ctx.author.guild_permissions.manage_messages or
              ctx.author.guild_permissions.moderate_members or
              ctx.author.guild_permissions.ban_members or
              ctx.author.id == ctx.guild.owner_id)
    
    # Filter content for non-moderators
    content = msg['content'] or "*No text content*"
    if msg.get('has_offensive_content', False) and not is_mod:
        content = filter_content(content)
    
    embed = discord.Embed(
        description=content,
        color=discord.Color.red(),
        timestamp=msg['time']
    )
    embed.set_author(name=msg['author'].display_name, icon_url=msg['author'].display_avatar.url)
    embed.set_footer(text=f"Message {message_number}/{len(sniped_messages[channel_id])} | Made with ❤ | Werrzzzy")
    
    # Handle media
    media_url = get_media_url(msg['content'], msg.get('attachments', []))
    if media_url:
        if media_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            embed.set_image(url=media_url)
        else:
            embed.add_field(name="Attachment", value=f"[Click here]({media_url})", inline=False)
    
    await ctx.send(embed=embed)

@bot.tree.command(name="snipe", description="Show deleted message")
@app_commands.describe(
    message_number="Which deleted message to show (1 = most recent)",
    channel="Channel to snipe from (optional)"
)
@check_not_blocked()
async def slash_snipe(interaction: discord.Interaction, message_number: int = 1, channel: Optional[Union[discord.TextChannel, discord.Thread]] = None):
    """Slash command version of snipe"""
    target_channel = channel or interaction.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        embed = discord.Embed(
            title="❌ No Deleted Messages",
            description="No deleted messages found in this channel.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)
    
    if message_number < 1 or message_number > len(sniped_messages[channel_id]):
        embed = discord.Embed(
            title="❌ Invalid Message Number",
            description=f"Please choose a number between 1 and {len(sniped_messages[channel_id])}.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed)
    
    msg = sniped_messages[channel_id][message_number - 1]
    
    # Check if user is moderator for filtering
    is_mod = (interaction.user.guild_permissions.administrator or
              interaction.user.guild_permissions.manage_messages or
              interaction.user.guild_permissions.moderate_members or
              interaction.user.guild_permissions.ban_members or
              interaction.user.id == interaction.guild.owner_id)
    
    # Filter content for non-moderators
    content = msg['content'] or "*No text content*"
    if msg.get('has_offensive_content', False) and not is_mod:
        content = filter_content(content)
    
    embed = discord.Embed(
        description=content,
        color=discord.Color.red(),
        timestamp=msg['time']
    )
    embed.set_author(name=msg['author'].display_name, icon_url=msg['author'].display_avatar.url)
    embed.set_footer(text=f"Message {message_number}/{len(sniped_messages[channel_id])} | Made with ❤ | Werrzzzy")
    
    # Handle media
    media_url = get_media_url(msg['content'], msg.get('attachments', []))
    if media_url:
        if media_url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
            embed.set_image(url=media_url)
        else:
            embed.add_field(name="Attachment", value=f"[Click here]({media_url})", inline=False)
    
    await interaction.response.send_message(embed=embed)

# Add other commands with both prefix and slash support...
# [The rest of the commands would follow the same pattern - each command having both a @bot.command and @bot.tree.command version]

# ===== BLOCK COMMAND =====
@bot.command(name='block')
@is_moderator()
async def block_user(ctx, *, user_input: str):
    """Block a user from using bot functions"""
    if not ctx.guild:
        await ctx.send("❌ This command can only be used in a server.")
        return
    
    # Try to find user by name using smart matching
    target_user = find_user_by_name(ctx.guild, user_input)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user matching '{user_input}'")
        return
    
    if target_user.id in blocked_users:
        await ctx.send(f"❌ {target_user.display_name} is already blocked.")
        return
    
    blocked_users.add(target_user.id)
    
    embed = discord.Embed(
        title="🚫 User Blocked",
        description=f"**{target_user.display_name}** has been blocked from using bot functions.",
        color=discord.Color.red()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="block", description="Block a user from using bot functions")
@app_commands.describe(user="User to block")
@check_not_blocked()
@check_moderator()
async def slash_block_user(interaction: discord.Interaction, user: discord.Member):
    """Slash command to block user"""
    if user.id in blocked_users:
        await interaction.response.send_message(f"❌ {user.display_name} is already blocked.")
        return
    
    blocked_users.add(user.id)
    
    embed = discord.Embed(
        title="🚫 User Blocked",
        description=f"**{user.display_name}** has been blocked from using bot functions.",
        color=discord.Color.red()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await interaction.response.send_message(embed=embed)

# ===== UNBLOCK COMMAND =====
@bot.tree.command(name="unblock", description="Unblock a user from using bot functions")
@app_commands.describe(user="User to unblock")
@check_specific_user()
async def slash_unblock_user(interaction: discord.Interaction, user: discord.Member):
    """Slash command to unblock user (Bot owner only)"""
    if user.id not in blocked_users:
        await interaction.response.send_message(f"❌ {user.display_name} is not blocked.")
        return
    
    blocked_users.remove(user.id)
    
    embed = discord.Embed(
        title="✅ User Unblocked",
        description=f"**{user.display_name}** can now use bot functions again.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await interaction.response.send_message(embed=embed)

# ===== NAMELOCK IMMUNE COMMAND =====
@bot.command(name='namelockimmune', aliases=['nli'])
@is_moderator()
async def namelock_immune(ctx, *, user_input: str):
    """Make user immune to namelock"""
    if not ctx.guild:
        await ctx.send("❌ This command can only be used in a server.")
        return
    
    # Try to find user by name using smart matching
    target_user = find_user_by_name(ctx.guild, user_input)
    
    if not target_user:
        await ctx.send(f"❌ Could not find user matching '{user_input}'")
        return
    
    if target_user.id in namelock_immune_users:
        namelock_immune_users.remove(target_user.id)
        embed = discord.Embed(
            title="🔓 Namelock Immunity Removed",
            description=f"**{target_user.display_name}** is no longer immune to namelock.",
            color=discord.Color.orange()
        )
    else:
        namelock_immune_users.add(target_user.id)
        embed = discord.Embed(
            title="🛡️ Namelock Immunity Granted",
            description=f"**{target_user.display_name}** is now immune to namelock.",
            color=discord.Color.green()
        )
    
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await ctx.send(embed=embed)

@bot.tree.command(name="namelockimmune", description="Toggle namelock immunity for a user")
@app_commands.describe(user="User to toggle immunity for")
@check_not_blocked()
@check_moderator()
async def slash_namelock_immune(interaction: discord.Interaction, user: discord.Member):
    """Slash command to toggle namelock immunity"""
    if user.id in namelock_immune_users:
        namelock_immune_users.remove(user.id)
        embed = discord.Embed(
            title="🔓 Namelock Immunity Removed",
            description=f"**{user.display_name}** is no longer immune to namelock.",
            color=discord.Color.orange()
        )
    else:
        namelock_immune_users.add(user.id)
        embed = discord.Embed(
            title="🛡️ Namelock Immunity Granted",
            description=f"**{user.display_name}** is now immune to namelock.",
            color=discord.Color.green()
        )
    
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await interaction.response.send_message(embed=embed)

# ===== GIVEAWAY REROLL COMMAND =====
@bot.command(name='gw')
@is_moderator()
async def giveaway_reroll(ctx, message_id: str):
    """Reroll giveaway winner using message ID"""
    try:
        msg_id = int(message_id)
    except ValueError:
        await ctx.send("❌ Invalid message ID. Please provide a valid number.")
        return
    
    if msg_id not in active_giveaways:
        await ctx.send("❌ No active giveaway found with that ID.")
        return
    
    giveaway_data = active_giveaways[msg_id]
    participants = giveaway_data.get('participants', [])
    
    if not participants:
        await ctx.send("❌ No participants in this giveaway to reroll.")
        return
    
    # Pick new winner
    winner_id = random.choice(participants)
    winner = ctx.guild.get_member(winner_id)
    
    embed = discord.Embed(
        title="🎉 Giveaway Rerolled!",
        description=f"**New Winner:** {winner.mention if winner else f'<@{winner_id}>'}\n**Prize:** {giveaway_data['prize']}",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

# ===== ENHANCED GIVEAWAY COMMAND =====
@bot.tree.command(name="giveaway", description="Create a new giveaway with requirements")
@app_commands.describe(
    channel="Channel to send the giveaway to",
    prize="What the winner will receive",
    duration="How long the giveaway runs (e.g., 1h, 30m, 1d)",
    winners="Number of winners (default: 1)",
    messages_required="Minimum messages required to join (optional)",
    required_role="Role required to join (optional)",
    blacklisted_role="Role that cannot join (optional)",
    time_in_server="Time required in server to join (e.g., 1d, 1h) (optional)"
)
@check_not_blocked()
@check_giveaway_host()
async def slash_giveaway_create(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    prize: str,
    duration: str,
    winners: int = 1,
    messages_required: Optional[int] = None,
    required_role: Optional[discord.Role] = None,
    blacklisted_role: Optional[discord.Role] = None,
    time_in_server: Optional[str] = None
):
    """Create a giveaway with individual requirement parameters"""
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds <= 0:
        await interaction.response.send_message("❌ Invalid duration! Use format like '1h', '30m', '1d'", ephemeral=True)
        return
    
    # Parse time in server requirement
    time_in_server_seconds = 0
    if time_in_server:
        time_in_server_seconds = parse_time_string(time_in_server)
        if time_in_server_seconds <= 0:
            await interaction.response.send_message("❌ Invalid time in server format! Use format like '1h', '30m', '1d'", ephemeral=True)
            return
    
    # Build requirements
    requirements = {}
    requirement_text = []
    
    if messages_required:
        requirements['messages'] = messages_required
        requirement_text.append(f"• {messages_required} messages in server")
    
    if required_role:
        requirements['required_role'] = required_role.name
        requirement_text.append(f"• Have {required_role.mention} role")
    
    if blacklisted_role:
        requirements['blacklisted_role'] = blacklisted_role.name
        requirement_text.append(f"• Cannot have {blacklisted_role.mention} role")
    
    if time_in_server_seconds > 0:
        requirements['time_in_server'] = time_in_server_seconds
        requirement_text.append(f"• Be in server for at least {format_duration(time_in_server_seconds)}")
    
    # Create giveaway embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Duration:** {format_duration(duration_seconds)}",
        color=discord.Color.gold()
    )
    
    if requirement_text:
        embed.add_field(
            name="📋 Requirements",
            value="\n".join(requirement_text),
            inline=False
        )
    
    embed.add_field(
        name="🎯 How to Enter",
        value="Click the 🎉 button below to join!",
        inline=False
    )
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    embed.add_field(
        name="⏰ Ends",
        value=f"<t:{int(end_time.timestamp())}:R>",
        inline=True
    )
    
    embed.set_footer(text=f"Hosted by {interaction.user.display_name} | Made with ❤ | Werrzzzy")
    
    # Send to specified channel
    giveaway_data = {
        'prize': prize,
        'winners': winners,
        'host': interaction.user.id,
        'requirements': requirements,
        'participants': [],
        'end_time': end_time
    }
    
    view = GiveawayView(giveaway_data)
    message = await channel.send(embed=embed, view=view)
    
    # Store giveaway data with message ID
    active_giveaways[message.id] = giveaway_data
    
    await interaction.response.send_message(f"✅ Giveaway created in {channel.mention}!", ephemeral=True)
    
    # Auto end giveaway after duration
    await asyncio.sleep(duration_seconds)
    
    # Check if giveaway still exists
    if message.id in active_giveaways:
        giveaway_data = active_giveaways[message.id]
        participants = giveaway_data.get('participants', [])
        
        if participants:
            # Pick winners
            num_winners = min(winners, len(participants))
            winners_list = random.sample(participants, num_winners)
            
            winner_mentions = []
            for winner_id in winners_list:
                winner = channel.guild.get_member(winner_id)
                winner_mentions.append(winner.mention if winner else f"<@{winner_id}>")
            
            # Create winner embed
            winner_embed = discord.Embed(
                title="🎊 Giveaway Ended!",
                description=f"**Prize:** {prize}\n**Winner{'s' if len(winners_list) > 1 else ''}:** {', '.join(winner_mentions)}",
                color=discord.Color.green()
            )
            winner_embed.set_footer(text="Made with ❤ | Werrzzzy")
            
            await channel.send(embed=winner_embed)
        else:
            # No participants
            no_winner_embed = discord.Embed(
                title="😢 Giveaway Ended",
                description=f"**Prize:** {prize}\nNo one participated in this giveaway.",
                color=discord.Color.red()
            )
            no_winner_embed.set_footer(text="Made with ❤ | Werrzzzy")
            
            await channel.send(embed=no_winner_embed)

# Run the bot
if __name__ == "__main__":
    try:
        bot.run(os.getenv('DISCORD_TOKEN'))
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
