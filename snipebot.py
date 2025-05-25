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
        'silver': 0xc0c0c0
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
                    ("**Bot Owner**", "`,manage` - Bot management panel\n`/unblock` - Unblock user from bot", False),
                    ("**Info**", "All commands support both prefix (,) and slash (/) versions\nModerators can use most commands\nBlocked users cannot use any bot functions", False)
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

# Giveaway Participants Pagination View
class GiveawayParticipantsPaginationView(discord.ui.View):
    def __init__(self, participants, giveaway_data, guild, timeout=300):
        super().__init__(timeout=timeout)
        self.participants = participants
        self.giveaway_data = giveaway_data
        self.guild = guild
        self.current_page = 0
        self.participants_per_page = 10
        self.total_pages = math.ceil(len(participants) / self.participants_per_page)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        # Update button states based on current page
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def get_embed(self):
        # Calculate start and end indices for current page
        start_idx = self.current_page * self.participants_per_page
        end_idx = min(start_idx + self.participants_per_page, len(self.participants))
        page_participants = self.participants[start_idx:end_idx]
        
        # Create embed
        embed = discord.Embed(
            title=f"📋 Giveaway Participants (Page {self.current_page + 1}/{self.total_pages})",
            description=f"These are the members that have participated in the giveaway of **{self.giveaway_data['prize']}**:",
            color=discord.Color.blue()
        )
        
        # Build numbered list of participants
        participant_list = []
        for i, user_id in enumerate(page_participants, start=start_idx + 1):
            member = self.guild.get_member(user_id)
            if member:
                # Format like: "1. @leaf | @leaf_username (1 entry)"
                entry_count = self.giveaway_data.get('participant_entries', {}).get(str(user_id), 1)
                participant_list.append(f"{i}. @{member.display_name} | @{member.name} ({entry_count} entry)")
            else:
                participant_list.append(f"{i}. <@{user_id}> (1 entry)")
        
        if participant_list:
            embed.add_field(
                name="Participants",
                value="\n".join(participant_list),
                inline=False
            )
        else:
            embed.add_field(
                name="No Participants",
                value="No one has joined this giveaway yet.",
                inline=False
            )
        
        embed.add_field(
            name="Total Participants",
            value=str(len(self.participants)),
            inline=True
        )
        
        # Add page information
        embed.set_footer(
            text=f"Page {self.current_page + 1} of {self.total_pages} | Made with ❤ | Werrzzzy"
        )
        
        return embed
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user is blocked
        if is_user_blocked(interaction.user.id):
            return  # Silently ignore blocked users
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user is blocked
        if is_user_blocked(interaction.user.id):
            return  # Silently ignore blocked users
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()

# REGULAR Pagination View for ,sp (FILTERED CONTENT - ALL MESSAGES)
class RegularSnipePaginationView(discord.ui.View):
    def __init__(self, messages, channel, timeout=300):
        super().__init__(timeout=timeout)
        self.messages = messages
        self.channel = channel
        self.current_page = 0
        self.total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        # Update button states based on current page
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def get_embed(self):
        # Calculate start and end indices for current page
        start_idx = self.current_page * MESSAGES_PER_PAGE
        end_idx = min(start_idx + MESSAGES_PER_PAGE, len(self.messages))
        page_messages = self.messages[start_idx:end_idx]
        
        # Create embed for REGULAR users
        embed = discord.Embed(
            title="📜 Deleted Messages List",
            color=discord.Color.gold()
        )
        
        if not page_messages:
            embed.add_field(
                name="No Messages",
                value="No deleted messages found in this channel.",
                inline=False
            )
        else:
            # Build numbered list of messages - ALWAYS FILTER FOR REGULAR USERS
            message_list = []
            for i, msg in enumerate(page_messages, start=start_idx + 1):
                content = msg['content'] or "*No text content*"
                
                # ALWAYS filter offensive content for regular users
                if msg.get('has_offensive_content', False):
                    content = filter_content(content)
                
                # Truncate content for list view
                content = truncate_content(content, 80)
                
                # Format: "1. Hi {username}"
                message_entry = f"{i}. {content} **-{msg['author'].display_name}**"
                message_list.append(message_entry)
            
            embed.add_field(
                name="Messages",
                value="\n".join(message_list),
                inline=False
            )
        
        # Add page information
        embed.set_footer(
            text=f"Page {self.current_page + 1} of {self.total_pages} | Total: {len(self.messages)} | Made with ❤ | Werrzzzy"
        )
        
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

# MODERATOR Pagination View for ,spforce (ONLY OFFENSIVE MESSAGES)
class ModeratorSnipePaginationView(discord.ui.View):
    def __init__(self, messages, channel, timeout=300):
        super().__init__(timeout=timeout)
        self.messages = messages
        self.channel = channel
        self.current_page = 0
        self.total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        # Update button states based on current page
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def get_embed(self):
        # Calculate start and end indices for current page
        start_idx = self.current_page * MESSAGES_PER_PAGE
        end_idx = min(start_idx + MESSAGES_PER_PAGE, len(self.messages))
        page_messages = self.messages[start_idx:end_idx]
        
        # Create embed for MODERATORS
        embed = discord.Embed(
            title="🔒 Moderator Snipe Pages (Unfiltered)",
            color=discord.Color.dark_red()
        )
        embed.description = "⚠️ **Warning:** Some messages may contain offensive content."
        
        if not page_messages:
            embed.add_field(
                name="No Messages",
                value="No offensive messages found in this channel.",
                inline=False
            )
        else:
            # Build numbered list of messages - SHOW RAW OFFENSIVE CONTENT FOR MODERATORS
            message_list = []
            for i, msg in enumerate(page_messages, start=start_idx + 1):
                content = msg['content'] or "*No text content*"
                
                # NEVER filter content for moderators - show everything raw
                
                # Truncate content for list view
                content = truncate_content(content, 80)
                
                # Format: "1. Hi {username}"
                message_entry = f"{i}. {content} **-{msg['author'].display_name}**"
                message_list.append(message_entry)
            
            embed.add_field(
                name="Messages",
                value="\n".join(message_list),
                inline=False
            )
        
        # Add page information
        embed.set_footer(
            text=f"MOD Page {self.current_page + 1} of {self.total_pages} | Total: {len(self.messages)} | Made with ❤ | Werrzzzy"
        )
        
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

# EDITED Messages Pagination View
class EditedSnipePaginationView(discord.ui.View):
    def __init__(self, messages, channel, timeout=300):
        super().__init__(timeout=timeout)
        self.messages = messages
        self.channel = channel
        self.current_page = 0
        self.total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        # Update button states based on current page
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def get_embed(self):
        # Calculate start and end indices for current page
        start_idx = self.current_page * MESSAGES_PER_PAGE
        end_idx = min(start_idx + MESSAGES_PER_PAGE, len(self.messages))
        page_messages = self.messages[start_idx:end_idx]
        
        # Create embed for edited messages
        embed = discord.Embed(
            title="✏️ Edited Messages List",
            color=discord.Color.orange()
        )
        
        if not page_messages:
            embed.add_field(
                name="No Messages",
                value="No edited messages found in this channel.",
                inline=False
            )
        else:
            # Build numbered list of messages
            message_list = []
            for i, msg in enumerate(page_messages, start=start_idx + 1):
                before = msg['before'] or "*No text content*"
                after = msg['after'] or "*No text content*"
                
                # Filter content for regular users
                if msg.get('has_offensive_content', False):
                    before = filter_content(before)
                    after = filter_content(after)
                
                # Truncate content for list view
                before = truncate_content(before, 40)
                after = truncate_content(after, 40)
                
                # Format: "1. old → new {username}"
                message_entry = f"{i}. {before} → {after} **-{msg['author'].display_name}**"
                message_list.append(message_entry)
            
            embed.add_field(
                name="Messages",
                value="\n".join(message_list),
                inline=False
            )
        
        # Add page information
        embed.set_footer(
            text=f"Page {self.current_page + 1} of {self.total_pages} | Total: {len(self.messages)} | Made with ❤ | Werrzzzy"
        )
        
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

# Event listeners
@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    print(f"Bot is in {len(bot.guilds)} guilds")
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    
    run_flask()

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    
    # Initialize channel storage if it doesn't exist
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []
    
    # Create message data
    message_data = {
        'content': message.content,
        'author': message.author,
        'attachments': [att.url for att in message.attachments],
        'timestamp': message.created_at,
        'has_offensive_content': is_offensive_content(message.content)
    }
    
    # Add to beginning of list (most recent first)
    sniped_messages[channel_id].insert(0, message_data)
    
    # Keep only the most recent MAX_MESSAGES
    if len(sniped_messages[channel_id]) > MAX_MESSAGES:
        sniped_messages[channel_id] = sniped_messages[channel_id][:MAX_MESSAGES]

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
    
    channel_id = before.channel.id
    
    # Initialize channel storage if it doesn't exist
    if channel_id not in edited_messages:
        edited_messages[channel_id] = []
    
    # Create edited message data
    message_data = {
        'before': before.content,
        'after': after.content,
        'author': before.author,
        'timestamp': before.created_at,
        'has_offensive_content': is_offensive_content(before.content) or is_offensive_content(after.content)
    }
    
    # Add to beginning of list (most recent first)
    edited_messages[channel_id].insert(0, message_data)
    
    # Keep only the most recent MAX_MESSAGES
    if len(edited_messages[channel_id]) > MAX_MESSAGES:
        edited_messages[channel_id] = edited_messages[channel_id][:MAX_MESSAGES]

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Increment user message count for giveaway tracking
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_member_update(before, after):
    # Check if nickname changed and user is namelocked
    if before.display_name != after.display_name and after.id in namelocked_users:
        # Check if user is immune to namelock
        if after.id in namelock_immune_users:
            return
        
        locked_nickname = namelocked_users[after.id]
        try:
            await after.edit(nick=locked_nickname, reason="User is namelocked")
        except discord.Forbidden:
            pass  # Bot doesn't have permission to change nickname

# PREFIX COMMANDS

# Help command with pagination
@bot.command(name='help')
@not_blocked()
async def help_command(ctx):
    """Show bot commands with pagination"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# Message count command
@bot.command(name='mess')
@not_blocked()
async def message_count(ctx, *, user_input=None):
    """Show user's message count using smart user finding"""
    if not user_input:
        # Show command author's message count
        target_user = ctx.author
    else:
        # Try to find user by ID first
        try:
            user_id = int(user_input.strip('<@!>'))
            target_user = ctx.guild.get_member(user_id)
        except ValueError:
            # Use smart user finding for partial names
            target_user = find_user_by_name(ctx.guild, user_input)
        
        if not target_user:
            await ctx.send("❌ User not found! Try using their full name, partial name, or mention them.")
            return
    
    message_count = get_user_message_count(ctx.guild.id, target_user.id)
    
    embed = discord.Embed(
        title="📊 Message Count",
        description=f"**{target_user.display_name}** has sent **{message_count}** messages in this server.",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=target_user.display_avatar.url)
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

# Management command
@bot.command(name='manage')
@is_specific_user()
async def manage_command(ctx):
    """Bot management panel"""
    uptime = time.time() - BOT_START_TIME
    uptime_str = format_uptime(uptime)
    
    embed = discord.Embed(
        title="🔧 Manage by Werrzzzy",
        color=discord.Color.green()
    )
    embed.add_field(name="📊 Bot Stats", value=f"Uptime: {uptime_str}\nGuilds: {len(bot.guilds)}\nUsers: {len(bot.users)}", inline=False)
    embed.add_field(name="💾 Data Stats", value=f"Blocked Users: {len(blocked_users)}\nNamelocked Users: {len(namelocked_users)}\nActive Giveaways: {len(active_giveaways)}", inline=False)
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

# Snipe command
@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe(ctx, channel: Optional[Union[discord.TextChannel, discord.Thread]] = None):
    """Show the last deleted message"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        embed = discord.Embed(
            title="📜 No Messages Found",
            description="There are no deleted messages to show in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    msg = sniped_messages[channel_id][0]  # Get most recent
    content = msg['content'] or "*No text content*"
    
    # Check if user is moderator
    is_mod = (ctx.author.guild_permissions.administrator or
              ctx.author.guild_permissions.manage_messages or
              ctx.author.guild_permissions.moderate_members or
              ctx.author.guild_permissions.ban_members or
              ctx.author.id == ctx.guild.owner_id)
    
    # Filter content for non-moderators
    if not is_mod and msg.get('has_offensive_content', False):
        content = filter_content(content)
    
    embed = discord.Embed(
        title="📜 Deleted Message",
        description=content,
        color=discord.Color.gold(),
        timestamp=msg['timestamp']
    )
    embed.set_author(name=msg['author'].display_name, icon_url=msg['author'].display_avatar.url)
    embed.set_footer(text=f"In #{target_channel.name} | Made with ❤ | Werrzzzy")
    
    # Handle media
    media_url = get_media_url(msg['content'], [])
    if media_url:
        embed.set_image(url=media_url)
    elif msg['attachments']:
        embed.set_image(url=msg['attachments'][0])
    
    await ctx.send(embed=embed)

# Edit snipe command
@bot.command(name='editsnipe', aliases=['es'])
@not_blocked()
async def editsnipe(ctx, channel: Optional[Union[discord.TextChannel, discord.Thread]] = None):
    """Show the last edited message"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        embed = discord.Embed(
            title="✏️ No Edited Messages Found",
            description="There are no edited messages to show in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    msg = edited_messages[channel_id][0]  # Get most recent
    before_content = msg['before'] or "*No text content*"
    after_content = msg['after'] or "*No text content*"
    
    # Check if user is moderator
    is_mod = (ctx.author.guild_permissions.administrator or
              ctx.author.guild_permissions.manage_messages or
              ctx.author.guild_permissions.moderate_members or
              ctx.author.guild_permissions.ban_members or
              ctx.author.id == ctx.guild.owner_id)
    
    # Filter content for non-moderators
    if not is_mod and msg.get('has_offensive_content', False):
        before_content = filter_content(before_content)
        after_content = filter_content(after_content)
    
    embed = discord.Embed(
        title="✏️ Edited Message",
        color=discord.Color.orange(),
        timestamp=msg['timestamp']
    )
    embed.add_field(name="Before", value=before_content, inline=False)
    embed.add_field(name="After", value=after_content, inline=False)
    embed.set_author(name=msg['author'].display_name, icon_url=msg['author'].display_avatar.url)
    embed.set_footer(text=f"In #{target_channel.name} | Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

# Snipe pages command
@bot.command(name='snipepages', aliases=['sp'])
@not_blocked()
async def snipe_pages(ctx, channel: Optional[Union[discord.TextChannel, discord.Thread]] = None):
    """Show paginated list of deleted messages"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        embed = discord.Embed(
            title="📜 No Messages Found",
            description="There are no deleted messages to show in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    messages = sniped_messages[channel_id]
    view = RegularSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# Snipe force command (moderator only)
@bot.command(name='spforce', aliases=['spf'])
@is_moderator()
async def snipe_force(ctx, channel: Optional[Union[discord.TextChannel, discord.Thread]] = None):
    """Show unfiltered deleted messages (moderator only)"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        embed = discord.Embed(
            title="📜 No Messages Found",
            description="There are no deleted messages to show in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Filter to only show offensive messages
    offensive_messages = [msg for msg in sniped_messages[channel_id] if msg.get('has_offensive_content', False)]
    
    if not offensive_messages:
        embed = discord.Embed(
            title="🔒 No Offensive Messages Found",
            description="There are no flagged messages to show in this channel.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
        return
    
    view = ModeratorSnipePaginationView(offensive_messages, target_channel)
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# Namelock command
@bot.command(name='namelock', aliases=['nl'])
@has_manage_nicknames()
async def namelock(ctx, member: discord.Member, *, nickname=None):
    """Lock a user's nickname"""
    # Check if user is immune to namelock
    if member.id in namelock_immune_users:
        await ctx.send(f"❌ {member.display_name} is immune to namelock!")
        return
    
    if nickname is None:
        nickname = member.display_name
    
    try:
        await member.edit(nick=nickname, reason=f"Namelocked by {ctx.author}")
        namelocked_users[member.id] = nickname
        
        embed = discord.Embed(
            title="🔒 User Namelocked",
            description=f"**{member.display_name}** has been namelocked to: `{nickname}`",
            color=discord.Color.red()
        )
        embed.set_footer(text="Made with ❤ | Werrzzzy")
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname!")

# Rename command
@bot.command(name='rename', aliases=['re'])
@has_manage_nicknames()
async def rename(ctx, member: discord.Member, *, nickname=None):
    """Change a user's nickname"""
    try:
        await member.edit(nick=nickname, reason=f"Renamed by {ctx.author}")
        
        embed = discord.Embed(
            title="✏️ User Renamed",
            description=f"**{member.display_name}** has been renamed to: `{nickname or 'No nickname'}`",
            color=discord.Color.green()
        )
        embed.set_footer(text="Made with ❤ | Werrzzzy")
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname!")

# Namelock immune command
@bot.command(name='namelockimmune', aliases=['nli'])
@is_moderator()
async def namelock_immune(ctx, member: discord.Member):
    """Make a user immune to namelock"""
    if member.id in namelock_immune_users:
        namelock_immune_users.remove(member.id)
        # Remove from namelocked users if they're there
        if member.id in namelocked_users:
            del namelocked_users[member.id]
        
        embed = discord.Embed(
            title="🛡️ Namelock Immunity Removed",
            description=f"**{member.display_name}** is no longer immune to namelock.",
            color=discord.Color.orange()
        )
    else:
        namelock_immune_users.add(member.id)
        # Remove from namelocked users if they're there
        if member.id in namelocked_users:
            del namelocked_users[member.id]
        
        embed = discord.Embed(
            title="🛡️ Namelock Immunity Added",
            description=f"**{member.display_name}** is now immune to namelock.",
            color=discord.Color.green()
        )
    
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await ctx.send(embed=embed)

# Say webhook command
@bot.command(name='saywb')
@is_moderator()
async def say_webhook(ctx, color=None, *, content):
    """Send a message via webhook with optional color"""
    try:
        webhook = await get_or_create_webhook(ctx.channel)
        
        if color:
            embed_color = parse_color(color)
            embed = discord.Embed(description=content, color=embed_color)
            await webhook.send(embed=embed, username="SnipeBot", avatar_url=bot.user.display_avatar.url)
        else:
            await webhook.send(content, username="SnipeBot", avatar_url=bot.user.display_avatar.url)
        
        # Delete the command message
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
            
    except Exception as e:
        await ctx.send(f"❌ Error sending webhook message: {e}")

# Block command
@bot.command(name='block')
@is_moderator()
async def block_user(ctx, member: discord.Member):
    """Block a user from using bot functions"""
    if member.id in blocked_users:
        await ctx.send(f"❌ {member.display_name} is already blocked!")
        return
    
    blocked_users.add(member.id)
    
    embed = discord.Embed(
        title="🚫 User Blocked",
        description=f"**{member.display_name}** has been blocked from using bot functions.",
        color=discord.Color.red()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await ctx.send(embed=embed)

# Giveaway reroll command
@bot.command(name='gw')
@is_moderator()
async def giveaway_reroll(ctx, message_id: str):
    """Reroll a giveaway winner using message ID"""
    try:
        msg_id = int(message_id)
    except ValueError:
        await ctx.send("❌ Invalid message ID!")
        return
    
    if msg_id not in active_giveaways:
        await ctx.send("❌ Giveaway not found! Make sure you're using the correct message ID.")
        return
    
    giveaway_data = active_giveaways[msg_id]
    participants = giveaway_data.get('participants', [])
    
    if not participants:
        await ctx.send("❌ No participants in this giveaway!")
        return
    
    # Pick random winner(s)
    winners_count = giveaway_data.get('winners', 1)
    if len(participants) < winners_count:
        winners = participants.copy()
    else:
        winners = random.sample(participants, winners_count)
    
    # Create winner announcement
    winner_mentions = []
    for winner_id in winners:
        member = ctx.guild.get_member(winner_id)
        if member:
            winner_mentions.append(member.mention)
        else:
            winner_mentions.append(f"<@{winner_id}>")
    
    embed = discord.Embed(
        title="🎉 Giveaway Rerolled!",
        description=f"**Prize:** {giveaway_data['prize']}\n**New Winner(s):** {', '.join(winner_mentions)}",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

# SLASH COMMANDS

# Unblock slash command
@bot.tree.command(name="unblock", description="Unblock a user from using bot functions")
@app_commands.describe(user="The user to unblock")
@check_specific_user()
async def unblock_slash(interaction: discord.Interaction, user: discord.Member):
    """Unblock a user from using bot functions"""
    if user.id not in blocked_users:
        await interaction.response.send_message(f"❌ {user.display_name} is not blocked!", ephemeral=True)
        return
    
    blocked_users.remove(user.id)
    
    embed = discord.Embed(
        title="✅ User Unblocked",
        description=f"**{user.display_name}** has been unblocked and can now use bot functions.",
        color=discord.Color.green()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await interaction.response.send_message(embed=embed)

# Giveaway creation command with individual parameters
@bot.tree.command(name="giveaway", description="Create a new giveaway")
@app_commands.describe(
    channel="Channel to send the giveaway to",
    prize="What the winner will receive",
    duration="How long the giveaway will run (e.g., 1h, 30m, 1d)",
    winners="Number of winners (default: 1)",
    messages="Minimum messages required to join",
    required_role="Role required to join (role name)",
    blacklisted_role="Role that cannot join (role name)",
    time_in_server="Time user must be in server (e.g., 1d, 1h)"
)
@check_giveaway_host()
async def giveaway_create(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    prize: str,
    duration: str,
    winners: int = 1,
    messages: Optional[int] = None,
    required_role: Optional[str] = None,
    blacklisted_role: Optional[str] = None,
    time_in_server: Optional[str] = None
):
    """Create a new giveaway with specific requirements"""
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds <= 0:
        await interaction.response.send_message("❌ Invalid duration! Use format like `1h`, `30m`, `1d`", ephemeral=True)
        return
    
    # Validate winners count
    if winners < 1:
        await interaction.response.send_message("❌ Number of winners must be at least 1!", ephemeral=True)
        return
    
    # Build requirements
    requirements = {}
    requirements_text = []
    
    if messages is not None and messages > 0:
        requirements['messages'] = messages
        requirements_text.append(f"📝 **{messages}** messages in server")
    
    if required_role:
        requirements['required_role'] = required_role
        requirements_text.append(f"👥 Must have **{required_role}** role")
    
    if blacklisted_role:
        requirements['blacklisted_role'] = blacklisted_role
        requirements_text.append(f"🚫 Cannot have **{blacklisted_role}** role")
    
    if time_in_server:
        time_seconds = parse_time_string(time_in_server)
        if time_seconds > 0:
            requirements['time_in_server'] = time_seconds
            requirements_text.append(f"⏰ Must be in server for **{format_duration(time_seconds)}**")
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Create giveaway embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
        color=discord.Color.gold()
    )
    
    if requirements_text:
        embed.add_field(
            name="📋 Requirements to Join",
            value="\n".join(requirements_text),
            inline=False
        )
    else:
        embed.add_field(
            name="📋 Requirements to Join",
            value="No requirements - anyone can join!",
            inline=False
        )
    
    embed.add_field(
        name="📊 Participants",
        value="0",
        inline=True
    )
    
    embed.set_footer(text=f"Hosted by {interaction.user.display_name} | Made with ❤ | Werrzzzy")
    
    # Create giveaway data
    giveaway_data = {
        'prize': prize,
        'winners': winners,
        'end_time': end_time,
        'requirements': requirements,
        'participants': [],
        'host': interaction.user.id,
        'channel': channel.id
    }
    
    # Send giveaway message
    view = GiveawayView(giveaway_data)
    message = await channel.send(embed=embed, view=view)
    
    # Store giveaway data with message ID
    active_giveaways[message.id] = giveaway_data
    
    # Schedule giveaway end
    asyncio.create_task(end_giveaway_after_delay(message.id, duration_seconds, channel, giveaway_data))
    
    await interaction.response.send_message(f"✅ Giveaway created in {channel.mention}! Message ID: `{message.id}`", ephemeral=True)

async def end_giveaway_after_delay(message_id, duration, channel, giveaway_data):
    """End giveaway after specified duration"""
    await asyncio.sleep(duration)
    
    # Check if giveaway still exists
    if message_id not in active_giveaways:
        return
    
    participants = giveaway_data.get('participants', [])
    
    if not participants:
        embed = discord.Embed(
            title="🎉 Giveaway Ended",
            description=f"**Prize:** {giveaway_data['prize']}\n**Winner:** No participants",
            color=discord.Color.red()
        )
        embed.set_footer(text="Made with ❤ | Werrzzzy")
        await channel.send(embed=embed)
        return
    
    # Pick winner(s)
    winners_count = giveaway_data.get('winners', 1)
    if len(participants) < winners_count:
        winners = participants.copy()
    else:
        winners = random.sample(participants, winners_count)
    
    # Create winner announcement
    winner_mentions = []
    for winner_id in winners:
        member = channel.guild.get_member(winner_id)
        if member:
            winner_mentions.append(member.mention)
        else:
            winner_mentions.append(f"<@{winner_id}>")
    
    embed = discord.Embed(
        title="🎉 Giveaway Ended!",
        description=f"**Prize:** {giveaway_data['prize']}\n**Winner(s):** {', '.join(winner_mentions)}",
        color=discord.Color.gold()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await channel.send(embed=embed)

# Giveaway host role command
@bot.tree.command(name="giveaway-host-role", description="Set roles that can host giveaways")
@app_commands.describe(role="Role to add/remove as giveaway host")
@check_admin_or_permissions(administrator=True)
async def giveaway_host_role(interaction: discord.Interaction, role: discord.Role):
    """Set roles that can host giveaways"""
    guild_id = interaction.guild.id
    
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = []
    
    if role.id in giveaway_host_roles[guild_id]:
        giveaway_host_roles[guild_id].remove(role.id)
        embed = discord.Embed(
            title="🎉 Giveaway Host Role Removed",
            description=f"**{role.name}** can no longer host giveaways.",
            color=discord.Color.red()
        )
    else:
        giveaway_host_roles[guild_id].append(role.id)
        embed = discord.Embed(
            title="🎉 Giveaway Host Role Added",
            description=f"**{role.name}** can now host giveaways.",
            color=discord.Color.green()
        )
    
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await interaction.response.send_message(embed=embed)

# Start the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("Error: DISCORD_BOT_TOKEN environment variable not set!")
        exit(1)
    bot.run(token)
