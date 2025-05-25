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

# ==================== EVENT HANDLERS ====================

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user}')
    
    # Start Flask app
    run_flask()
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    # Don't respond to bot messages or blocked users
    if message.author.bot or is_user_blocked(message.author.id):
        return
    
    # Increment message count for giveaway requirements
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    # Process commands
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    # Don't store bot messages
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    
    # Initialize storage if needed
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []
    
    # Check if content is offensive
    has_offensive = is_offensive_content(message.content) if message.content else False
    
    # Store message data
    message_data = {
        'content': message.content,
        'author': message.author,
        'channel': message.channel,
        'deleted_at': datetime.utcnow(),
        'attachments': [att.url for att in message.attachments] if message.attachments else [],
        'has_offensive_content': has_offensive
    }
    
    # Add to front of list (most recent first)
    sniped_messages[channel_id].insert(0, message_data)
    
    # Keep only the most recent MAX_MESSAGES
    if len(sniped_messages[channel_id]) > MAX_MESSAGES:
        sniped_messages[channel_id] = sniped_messages[channel_id][:MAX_MESSAGES]

@bot.event
async def on_message_edit(before, after):
    # Don't store bot messages or if content didn't change
    if before.author.bot or before.content == after.content:
        return
    
    channel_id = before.channel.id
    
    # Initialize storage if needed
    if channel_id not in edited_messages:
        edited_messages[channel_id] = []
    
    # Check if original content is offensive
    has_offensive = is_offensive_content(before.content) if before.content else False
    
    # Store message data
    message_data = {
        'before_content': before.content,
        'after_content': after.content,
        'author': before.author,
        'channel': before.channel,
        'edited_at': datetime.utcnow(),
        'has_offensive_content': has_offensive
    }
    
    # Add to front of list (most recent first)
    edited_messages[channel_id].insert(0, message_data)
    
    # Keep only the most recent MAX_MESSAGES
    if len(edited_messages[channel_id]) > MAX_MESSAGES:
        edited_messages[channel_id] = edited_messages[channel_id][:MAX_MESSAGES]

@bot.event
async def on_member_update(before, after):
    """Handle nickname changes for namelock functionality"""
    # Check if user is namelocked and not immune
    if (before.nick != after.nick and 
        after.id in namelocked_users and 
        after.id not in namelock_immune_users):
        
        locked_nickname = namelocked_users[after.id]
        
        # If nickname changed and doesn't match locked nickname
        if after.nick != locked_nickname:
            try:
                await after.edit(nick=locked_nickname, reason="User is namelocked")
            except discord.Forbidden:
                pass  # Can't change nickname (bot doesn't have permission or user has higher role)
            except discord.HTTPException:
                pass  # Other error occurred

# ==================== SNIPE COMMANDS ====================

@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe_command(ctx, channel_or_user: Optional[Union[discord.TextChannel, discord.Thread, discord.Member]] = None, index: int = 1):
    """Show the most recently deleted message (FILTERED for regular users)"""
    
    # Handle different argument types
    target_channel = ctx.channel
    target_user = None
    
    if isinstance(channel_or_user, (discord.TextChannel, discord.Thread)):
        target_channel = channel_or_user
    elif isinstance(channel_or_user, discord.Member):
        target_user = channel_or_user
    
    # Get messages from target channel
    messages = sniped_messages.get(target_channel.id, [])
    
    # Filter by user if specified
    if target_user:
        messages = [msg for msg in messages if msg['author'].id == target_user.id]
    
    if not messages:
        target_info = f" from {target_user.display_name}" if target_user else ""
        await ctx.send(f"❌ No deleted messages found in {target_channel.mention}{target_info}.")
        return
    
    # Validate index
    if index < 1 or index > len(messages):
        await ctx.send(f"❌ Invalid index. Please use a number between 1 and {len(messages)}.")
        return
    
    # Get the message at the specified index (1-indexed)
    msg = messages[index - 1]
    
    # Create embed for REGULAR users (ALWAYS FILTER)
    embed = discord.Embed(color=discord.Color.red())
    embed.set_author(name=f"{msg['author'].display_name} ({msg['author'].name})", 
                     icon_url=msg['author'].display_avatar.url)
    
    # Get content and ALWAYS filter for regular users
    content = msg['content'] or "*No text content*"
    if msg.get('has_offensive_content', False):
        content = filter_content(content)
    
    embed.description = content
    
    # Add media if present
    media_url = get_media_url(msg['content'], [])
    if media_url:
        embed.set_image(url=media_url)
    elif msg['attachments']:
        embed.set_image(url=msg['attachments'][0])
    
    # Add timestamp and channel info
    embed.timestamp = msg['deleted_at']
    embed.set_footer(text=f"#{target_channel.name} | Message {index}/{len(messages)} | Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="snipe", description="Show the most recently deleted message")
@check_not_blocked()
async def snipe_slash(interaction: discord.Interaction, 
                     channel: Optional[Union[discord.TextChannel, discord.Thread]] = None,
                     user: Optional[discord.Member] = None,
                     index: Optional[int] = 1):
    """Show the most recently deleted message (FILTERED for regular users)"""
    
    target_channel = channel or interaction.channel
    
    # Get messages from target channel
    messages = sniped_messages.get(target_channel.id, [])
    
    # Filter by user if specified
    if user:
        messages = [msg for msg in messages if msg['author'].id == user.id]
    
    if not messages:
        target_info = f" from {user.display_name}" if user else ""
        await interaction.response.send_message(f"❌ No deleted messages found in {target_channel.mention}{target_info}.", ephemeral=True)
        return
    
    # Validate index
    if index < 1 or index > len(messages):
        await interaction.response.send_message(f"❌ Invalid index. Please use a number between 1 and {len(messages)}.", ephemeral=True)
        return
    
    # Get the message at the specified index (1-indexed)
    msg = messages[index - 1]
    
    # Create embed for REGULAR users (ALWAYS FILTER)
    embed = discord.Embed(color=discord.Color.red())
    embed.set_author(name=f"{msg['author'].display_name} ({msg['author'].name})", 
                     icon_url=msg['author'].display_avatar.url)
    
    # Get content and ALWAYS filter for regular users
    content = msg['content'] or "*No text content*"
    if msg.get('has_offensive_content', False):
        content = filter_content(content)
    
    embed.description = content
    
    # Add media if present
    media_url = get_media_url(msg['content'], [])
    if media_url:
        embed.set_image(url=media_url)
    elif msg['attachments']:
        embed.set_image(url=msg['attachments'][0])
    
    # Add timestamp and channel info
    embed.timestamp = msg['deleted_at']
    embed.set_footer(text=f"#{target_channel.name} | Message {index}/{len(messages)} | Made with ❤ | Werrzzzy")
    
    await interaction.response.send_message(embed=embed)

@bot.command(name='snipepages', aliases=['sp'])
@not_blocked()
async def snipe_pages_command(ctx, channel_or_user: Optional[Union[discord.TextChannel, discord.Thread, discord.Member]] = None):
    """Show paginated list of deleted messages (FILTERED for regular users)"""
    
    # Handle different argument types
    target_channel = ctx.channel
    target_user = None
    
    if isinstance(channel_or_user, (discord.TextChannel, discord.Thread)):
        target_channel = channel_or_user
    elif isinstance(channel_or_user, discord.Member):
        target_user = channel_or_user
    
    # Get messages from target channel
    messages = sniped_messages.get(target_channel.id, [])
    
    # Filter by user if specified
    if target_user:
        messages = [msg for msg in messages if msg['author'].id == target_user.id]
    
    if not messages:
        target_info = f" from {target_user.display_name}" if target_user else ""
        await ctx.send(f"❌ No deleted messages found in {target_channel.mention}{target_info}.")
        return
    
    # Create pagination view for REGULAR users (FILTERED)
    view = RegularSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    await ctx.send(embed=embed, view=view)

@bot.tree.command(name="snipepages", description="Show paginated list of deleted messages")
@check_not_blocked()
async def snipe_pages_slash(interaction: discord.Interaction, 
                           channel: Optional[Union[discord.TextChannel, discord.Thread]] = None,
                           user: Optional[discord.Member] = None):
    """Show paginated list of deleted messages (FILTERED for regular users)"""
    
    target_channel = channel or interaction.channel
    
    # Get messages from target channel
    messages = sniped_messages.get(target_channel.id, [])
    
    # Filter by user if specified
    if user:
        messages = [msg for msg in messages if msg['author'].id == user.id]
    
    if not messages:
        target_info = f" from {user.display_name}" if user else ""
        await interaction.response.send_message(f"❌ No deleted messages found in {target_channel.mention}{target_info}.", ephemeral=True)
        return
    
    # Create pagination view for REGULAR users (FILTERED)
    view = RegularSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.command(name='snipeforce', aliases=['spf'])
@is_moderator()
async def snipe_force_command(ctx, channel_or_user: Optional[Union[discord.TextChannel, discord.Thread, discord.Member]] = None, index: int = 1):
    """Show deleted message without filtering (MODERATOR ONLY - UNFILTERED)"""
    
    # Handle different argument types
    target_channel = ctx.channel
    target_user = None
    
    if isinstance(channel_or_user, (discord.TextChannel, discord.Thread)):
        target_channel = channel_or_user
    elif isinstance(channel_or_user, discord.Member):
        target_user = channel_or_user
    
    # Get messages from target channel
    messages = sniped_messages.get(target_channel.id, [])
    
    # Filter by user if specified
    if target_user:
        messages = [msg for msg in messages if msg['author'].id == target_user.id]
    
    # For moderators, only show OFFENSIVE messages
    offensive_messages = [msg for msg in messages if msg.get('has_offensive_content', False)]
    
    if not offensive_messages:
        target_info = f" from {target_user.display_name}" if target_user else ""
        await ctx.send(f"❌ No offensive messages found in {target_channel.mention}{target_info}.")
        return
    
    # Validate index
    if index < 1 or index > len(offensive_messages):
        await ctx.send(f"❌ Invalid index. Please use a number between 1 and {len(offensive_messages)}.")
        return
    
    # Get the message at the specified index (1-indexed)
    msg = offensive_messages[index - 1]
    
    # Create embed for MODERATORS (UNFILTERED)
    embed = discord.Embed(color=discord.Color.dark_red())
    embed.set_author(name=f"{msg['author'].display_name} ({msg['author'].name})", 
                     icon_url=msg['author'].display_avatar.url)
    embed.description = "⚠️ **Warning:** This message contains offensive content."
    
    # Show raw content without filtering for moderators
    content = msg['content'] or "*No text content*"
    embed.add_field(name="Raw Content", value=content, inline=False)
    
    # Add media if present
    media_url = get_media_url(msg['content'], [])
    if media_url:
        embed.set_image(url=media_url)
    elif msg['attachments']:
        embed.set_image(url=msg['attachments'][0])
    
    # Add timestamp and channel info
    embed.timestamp = msg['deleted_at']
    embed.set_footer(text=f"MODERATOR VIEW | #{target_channel.name} | Message {index}/{len(offensive_messages)} | Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="snipeforce", description="Show deleted message without filtering (MODERATOR ONLY)")
@check_moderator()
async def snipe_force_slash(interaction: discord.Interaction, 
                           channel: Optional[Union[discord.TextChannel, discord.Thread]] = None,
                           user: Optional[discord.Member] = None,
                           index: Optional[int] = 1):
    """Show deleted message without filtering (MODERATOR ONLY - UNFILTERED)"""
    
    target_channel = channel or interaction.channel
    
    # Get messages from target channel
    messages = sniped_messages.get(target_channel.id, [])
    
    # Filter by user if specified
    if user:
        messages = [msg for msg in messages if msg['author'].id == user.id]
    
    # For moderators, only show OFFENSIVE messages
    offensive_messages = [msg for msg in messages if msg.get('has_offensive_content', False)]
    
    if not offensive_messages:
        target_info = f" from {user.display_name}" if user else ""
        await interaction.response.send_message(f"❌ No offensive messages found in {target_channel.mention}{target_info}.", ephemeral=True)
        return
    
    # Validate index
    if index < 1 or index > len(offensive_messages):
        await interaction.response.send_message(f"❌ Invalid index. Please use a number between 1 and {len(offensive_messages)}.", ephemeral=True)
        return
    
    # Get the message at the specified index (1-indexed)
    msg = offensive_messages[index - 1]
    
    # Create embed for MODERATORS (UNFILTERED)
    embed = discord.Embed(color=discord.Color.dark_red())
    embed.set_author(name=f"{msg['author'].display_name} ({msg['author'].name})", 
                     icon_url=msg['author'].display_avatar.url)
    embed.description = "⚠️ **Warning:** This message contains offensive content."
    
    # Show raw content without filtering for moderators
    content = msg['content'] or "*No text content*"
    embed.add_field(name="Raw Content", value=content, inline=False)
    
    # Add media if present
    media_url = get_media_url(msg['content'], [])
    if media_url:
        embed.set_image(url=media_url)
    elif msg['attachments']:
        embed.set_image(url=msg['attachments'][0])
    
    # Add timestamp and channel info
    embed.timestamp = msg['deleted_at']
    embed.set_footer(text=f"MODERATOR VIEW | #{target_channel.name} | Message {index}/{len(offensive_messages)} | Made with ❤ | Werrzzzy")
    
    await interaction.response.send_message(embed=embed)

@bot.command(name='snipeforcepages', aliases=['spfp'])
@is_moderator()
async def snipe_force_pages_command(ctx, channel_or_user: Optional[Union[discord.TextChannel, discord.Thread, discord.Member]] = None):
    """Show paginated list of offensive deleted messages (MODERATOR ONLY)"""
    
    # Handle different argument types
    target_channel = ctx.channel
    target_user = None
    
    if isinstance(channel_or_user, (discord.TextChannel, discord.Thread)):
        target_channel = channel_or_user
    elif isinstance(channel_or_user, discord.Member):
        target_user = channel_or_user
    
    # Get messages from target channel
    messages = sniped_messages.get(target_channel.id, [])
    
    # Filter by user if specified
    if target_user:
        messages = [msg for msg in messages if msg['author'].id == target_user.id]
    
    # For moderators, only show OFFENSIVE messages
    offensive_messages = [msg for msg in messages if msg.get('has_offensive_content', False)]
    
    if not offensive_messages:
        target_info = f" from {target_user.display_name}" if target_user else ""
        await ctx.send(f"❌ No offensive messages found in {target_channel.mention}{target_info}.")
        return
    
    # Create pagination view for MODERATORS (UNFILTERED OFFENSIVE CONTENT)
    view = ModeratorSnipePaginationView(offensive_messages, target_channel)
    embed = view.get_embed()
    
    await ctx.send(embed=embed, view=view)

@bot.tree.command(name="snipeforcepages", description="Show paginated list of offensive deleted messages (MODERATOR ONLY)")
@check_moderator()
async def snipe_force_pages_slash(interaction: discord.Interaction, 
                                 channel: Optional[Union[discord.TextChannel, discord.Thread]] = None,
                                 user: Optional[discord.Member] = None):
    """Show paginated list of offensive deleted messages (MODERATOR ONLY)"""
    
    target_channel = channel or interaction.channel
    
    # Get messages from target channel
    messages = sniped_messages.get(target_channel.id, [])
    
    # Filter by user if specified
    if user:
        messages = [msg for msg in messages if msg['author'].id == user.id]
    
    # For moderators, only show OFFENSIVE messages
    offensive_messages = [msg for msg in messages if msg.get('has_offensive_content', False)]
    
    if not offensive_messages:
        target_info = f" from {user.display_name}" if user else ""
        await interaction.response.send_message(f"❌ No offensive messages found in {target_channel.mention}{target_info}.", ephemeral=True)
        return
    
    # Create pagination view for MODERATORS (UNFILTERED OFFENSIVE CONTENT)
    view = ModeratorSnipePaginationView(offensive_messages, target_channel)
    embed = view.get_embed()
    
    await interaction.response.send_message(embed=embed, view=view)

# ==================== EDITSNIPE COMMANDS ====================

@bot.command(name='editsnipe', aliases=['es'])
@not_blocked()
async def editsnipe_command(ctx, channel_or_user: Optional[Union[discord.TextChannel, discord.Thread, discord.Member]] = None, index: int = 1):
    """Show the most recently edited message"""
    
    # Handle different argument types
    target_channel = ctx.channel
    target_user = None
    
    if isinstance(channel_or_user, (discord.TextChannel, discord.Thread)):
        target_channel = channel_or_user
    elif isinstance(channel_or_user, discord.Member):
        target_user = channel_or_user
    
    # Get messages from target channel
    messages = edited_messages.get(target_channel.id, [])
    
    # Filter by user if specified
    if target_user:
        messages = [msg for msg in messages if msg['author'].id == target_user.id]
    
    if not messages:
        target_info = f" from {target_user.display_name}" if target_user else ""
        await ctx.send(f"❌ No edited messages found in {target_channel.mention}{target_info}.")
        return
    
    # Validate index
    if index < 1 or index > len(messages):
        await ctx.send(f"❌ Invalid index. Please use a number between 1 and {len(messages)}.")
        return
    
    # Get the message at the specified index (1-indexed)
    msg = messages[index - 1]
    
    # Create embed
    embed = discord.Embed(color=discord.Color.orange())
    embed.set_author(name=f"{msg['author'].display_name} ({msg['author'].name})", 
                     icon_url=msg['author'].display_avatar.url)
    
    # Get content and filter if offensive for regular users
    before_content = msg['before_content'] or "*No text content*"
    after_content = msg['after_content'] or "*No text content*"
    
    if msg.get('has_offensive_content', False):
        before_content = filter_content(before_content)
        after_content = filter_content(after_content)
    
    embed.add_field(name="Before", value=before_content, inline=False)
    embed.add_field(name="After", value=after_content, inline=False)
    
    # Add timestamp and channel info
    embed.timestamp = msg['edited_at']
    embed.set_footer(text=f"#{target_channel.name} | Edit {index}/{len(messages)} | Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="editsnipe", description="Show the most recently edited message")
@check_not_blocked()
async def editsnipe_slash(interaction: discord.Interaction, 
                         channel: Optional[Union[discord.TextChannel, discord.Thread]] = None,
                         user: Optional[discord.Member] = None,
                         index: Optional[int] = 1):
    """Show the most recently edited message"""
    
    target_channel = channel or interaction.channel
    
    # Get messages from target channel
    messages = edited_messages.get(target_channel.id, [])
    
    # Filter by user if specified
    if user:
        messages = [msg for msg in messages if msg['author'].id == user.id]
    
    if not messages:
        target_info = f" from {user.display_name}" if user else ""
        await interaction.response.send_message(f"❌ No edited messages found in {target_channel.mention}{target_info}.", ephemeral=True)
        return
    
    # Validate index
    if index < 1 or index > len(messages):
        await interaction.response.send_message(f"❌ Invalid index. Please use a number between 1 and {len(messages)}.", ephemeral=True)
        return
    
    # Get the message at the specified index (1-indexed)
    msg = messages[index - 1]
    
    # Create embed
    embed = discord.Embed(color=discord.Color.orange())
    embed.set_author(name=f"{msg['author'].display_name} ({msg['author'].name})", 
                     icon_url=msg['author'].display_avatar.url)
    
    # Get content and filter if offensive for regular users
    before_content = msg['before_content'] or "*No text content*"
    after_content = msg['after_content'] or "*No text content*"
    
    if msg.get('has_offensive_content', False):
        before_content = filter_content(before_content)
        after_content = filter_content(after_content)
    
    embed.add_field(name="Before", value=before_content, inline=False)
    embed.add_field(name="After", value=after_content, inline=False)
    
    # Add timestamp and channel info
    embed.timestamp = msg['edited_at']
    embed.set_footer(text=f"#{target_channel.name} | Edit {index}/{len(messages)} | Made with ❤ | Werrzzzy")
    
    await interaction.response.send_message(embed=embed)

# ==================== MODERATION COMMANDS ====================

@bot.command(name='say')
@is_moderator()
async def say_command(ctx, *, content):
    """Make the bot say something"""
    await ctx.message.delete()
    await ctx.send(content)

@bot.tree.command(name="say", description="Make the bot say something")
@check_moderator()
async def say_slash(interaction: discord.Interaction, content: str):
    """Make the bot say something"""
    await interaction.response.send_message(content)

@bot.command(name='saywb')
@is_moderator()
async def say_webhook_command(ctx, color: str = None, *, content):
    """Send a message using webhook with optional color"""
    try:
        # Delete the command message
        await ctx.message.delete()
        
        # Get or create webhook
        webhook = await get_or_create_webhook(ctx.channel)
        
        # Parse color
        embed_color = parse_color(color) if color else discord.Color.default()
        
        # Create embed
        embed = discord.Embed(description=content, color=embed_color)
        
        # Send via webhook
        await webhook.send(embed=embed, username="SnipeBot", 
                          avatar_url="https://cdn.discordapp.com/avatars/1234567890/avatar.png")
        
    except Exception as e:
        await ctx.send(f"❌ Failed to send webhook message: {e}")

@bot.tree.command(name="saywb", description="Send a message using webhook with optional color")
@check_moderator()
async def say_webhook_slash(interaction: discord.Interaction, content: str, color: Optional[str] = None):
    """Send a message using webhook with optional color"""
    try:
        # Get or create webhook
        webhook = await get_or_create_webhook(interaction.channel)
        
        # Parse color
        embed_color = parse_color(color) if color else discord.Color.default()
        
        # Create embed
        embed = discord.Embed(description=content, color=embed_color)
        
        # Send via webhook
        await webhook.send(embed=embed, username="SnipeBot", 
                          avatar_url="https://cdn.discordapp.com/avatars/1234567890/avatar.png")
        
        await interaction.response.send_message("✅ Message sent via webhook!", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to send webhook message: {e}", ephemeral=True)

@bot.command(name='clear')
@is_moderator()
async def clear_command(ctx, amount: int = 10):
    """Clear messages from the channel"""
    if amount < 1 or amount > 100:
        await ctx.send("❌ Amount must be between 1 and 100.")
        return
    
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
        await ctx.send(f"✅ Deleted {len(deleted)-1} messages.", delete_after=5)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {e}")

@bot.tree.command(name="clear", description="Clear messages from the channel")
@check_moderator()
async def clear_slash(interaction: discord.Interaction, amount: int = 10):
    """Clear messages from the channel"""
    if amount < 1 or amount > 100:
        await interaction.response.send_message("❌ Amount must be between 1 and 100.", ephemeral=True)
        return
    
    try:
        deleted = await interaction.channel.purge(limit=amount)
        await interaction.response.send_message(f"✅ Deleted {len(deleted)} messages.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to delete messages.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {e}", ephemeral=True)

# ==================== NAMELOCK COMMANDS ====================

@bot.command(name='namelock', aliases=['nl'])
@has_manage_nicknames()
async def namelock_command(ctx, user: discord.Member, *, nickname: str = None):
    """Lock a user's nickname"""
    # Use current nickname if none provided
    if nickname is None:
        nickname = user.display_name
    
    # Add user to namelock
    namelocked_users[user.id] = nickname
    
    # Set the nickname
    try:
        await user.edit(nick=nickname, reason=f"Namelocked by {ctx.author}")
        await ctx.send(f"✅ {user.mention} has been namelocked to `{nickname}`.")
    except discord.Forbidden:
        await ctx.send(f"❌ I cannot change {user.mention}'s nickname (insufficient permissions).")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Failed to change nickname: {e}")

@bot.tree.command(name="namelock", description="Lock a user's nickname")
@check_admin_or_permissions(manage_nicknames=True)
async def namelock_slash(interaction: discord.Interaction, user: discord.Member, nickname: Optional[str] = None):
    """Lock a user's nickname"""
    # Use current nickname if none provided
    if nickname is None:
        nickname = user.display_name
    
    # Add user to namelock
    namelocked_users[user.id] = nickname
    
    # Set the nickname
    try:
        await user.edit(nick=nickname, reason=f"Namelocked by {interaction.user}")
        await interaction.response.send_message(f"✅ {user.mention} has been namelocked to `{nickname}`.")
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ I cannot change {user.mention}'s nickname (insufficient permissions).", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ Failed to change nickname: {e}", ephemeral=True)

@bot.command(name='unnamelock', aliases=['unl'])
@has_manage_nicknames()
async def unnamelock_command(ctx, user: discord.Member):
    """Remove namelock from a user"""
    if user.id not in namelocked_users:
        await ctx.send(f"❌ {user.mention} is not namelocked.")
        return
    
    # Remove from namelock
    del namelocked_users[user.id]
    await ctx.send(f"✅ {user.mention} has been unnamelocked.")

@bot.tree.command(name="unnamelock", description="Remove namelock from a user")
@check_admin_or_permissions(manage_nicknames=True)
async def unnamelock_slash(interaction: discord.Interaction, user: discord.Member):
    """Remove namelock from a user"""
    if user.id not in namelocked_users:
        await interaction.response.send_message(f"❌ {user.mention} is not namelocked.", ephemeral=True)
        return
    
    # Remove from namelock
    del namelocked_users[user.id]
    await interaction.response.send_message(f"✅ {user.mention} has been unnamelocked.")

@bot.command(name='namelockimmune', aliases=['nli'])
@has_manage_nicknames()
async def namelock_immune_command(ctx, user: discord.Member):
    """Make a user immune to namelock changes"""
    if user.id in namelock_immune_users:
        # Remove immunity
        namelock_immune_users.remove(user.id)
        await ctx.send(f"✅ {user.mention} is no longer immune to namelock changes.")
    else:
        # Add immunity
        namelock_immune_users.add(user.id)
        await ctx.send(f"✅ {user.mention} is now immune to namelock changes.")

@bot.tree.command(name="namelockimmune", description="Make a user immune to namelock changes")
@check_admin_or_permissions(manage_nicknames=True)
async def namelock_immune_slash(interaction: discord.Interaction, user: discord.Member):
    """Make a user immune to namelock changes"""
    if user.id in namelock_immune_users:
        # Remove immunity
        namelock_immune_users.remove(user.id)
        await interaction.response.send_message(f"✅ {user.mention} is no longer immune to namelock changes.")
    else:
        # Add immunity
        namelock_immune_users.add(user.id)
        await interaction.response.send_message(f"✅ {user.mention} is now immune to namelock changes.")

@bot.command(name='rename', aliases=['re'])
@has_manage_nicknames()
async def rename_command(ctx, user: discord.Member, *, nickname: str = None):
    """Change a user's nickname"""
    try:
        old_nick = user.display_name
        await user.edit(nick=nickname, reason=f"Renamed by {ctx.author}")
        new_nick = user.display_name
        await ctx.send(f"✅ Changed {user.mention}'s nickname from `{old_nick}` to `{new_nick}`.")
    except discord.Forbidden:
        await ctx.send(f"❌ I cannot change {user.mention}'s nickname (insufficient permissions).")
    except discord.HTTPException as e:
        await ctx.send(f"❌ Failed to change nickname: {e}")

@bot.tree.command(name="rename", description="Change a user's nickname")
@check_admin_or_permissions(manage_nicknames=True)
async def rename_slash(interaction: discord.Interaction, user: discord.Member, nickname: Optional[str] = None):
    """Change a user's nickname"""
    try:
        old_nick = user.display_name
        await user.edit(nick=nickname, reason=f"Renamed by {interaction.user}")
        new_nick = user.display_name
        await interaction.response.send_message(f"✅ Changed {user.mention}'s nickname from `{old_nick}` to `{new_nick}`.")
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ I cannot change {user.mention}'s nickname (insufficient permissions).", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"❌ Failed to change nickname: {e}", ephemeral=True)

# ==================== BLOCK COMMANDS ====================

@bot.command(name='block')
@is_specific_user()
async def block_command(ctx, user: discord.Member):
    """Block a user from using any bot functions (BOT OWNER ONLY)"""
    if user.id in blocked_users:
        # Unblock user
        blocked_users.remove(user.id)
        await ctx.send(f"✅ {user.mention} has been unblocked and can now use bot functions.")
    else:
        # Block user
        blocked_users.add(user.id)
        await ctx.send(f"🚫 {user.mention} has been blocked from using any bot functions.")

@bot.tree.command(name="block", description="Block a user from using any bot functions (BOT OWNER ONLY)")
@check_specific_user()
async def block_slash(interaction: discord.Interaction, user: discord.Member):
    """Block a user from using any bot functions (BOT OWNER ONLY)"""
    if user.id in blocked_users:
        # Unblock user
        blocked_users.remove(user.id)
        await interaction.response.send_message(f"✅ {user.mention} has been unblocked and can now use bot functions.")
    else:
        # Block user
        blocked_users.add(user.id)
        await interaction.response.send_message(f"🚫 {user.mention} has been blocked from using any bot functions.")

# ==================== GIVEAWAY COMMANDS ====================

@bot.tree.command(name="giveaway", description="Create a giveaway with specific requirements")
@check_giveaway_host()
async def giveaway_create_slash(interaction: discord.Interaction,
                               channel: discord.TextChannel,
                               prize: str,
                               duration: str,
                               winners: int = 1,
                               messages: Optional[int] = None,
                               required_role: Optional[discord.Role] = None,
                               blacklisted_role: Optional[discord.Role] = None,
                               time_in_server: Optional[str] = None):
    """Create a giveaway with individual requirement parameters"""
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds <= 0:
        await interaction.response.send_message("❌ Invalid duration format. Use format like `1h`, `30m`, `5d`.", ephemeral=True)
        return
    
    if winners < 1:
        await interaction.response.send_message("❌ Number of winners must be at least 1.", ephemeral=True)
        return
    
    # Parse time in server requirement
    time_in_server_seconds = 0
    if time_in_server:
        time_in_server_seconds = parse_time_string(time_in_server)
        if time_in_server_seconds <= 0:
            await interaction.response.send_message("❌ Invalid time-in-server format. Use format like `1h`, `30m`, `5d`.", ephemeral=True)
            return
    
    # Build requirements dictionary
    requirements = {}
    requirement_list = []
    
    if messages is not None:
        requirements['messages'] = messages
        requirement_list.append(f"• **{messages}** messages in server")
    
    if required_role:
        requirements['required_role'] = required_role.name
        requirement_list.append(f"• Must have **{required_role.name}** role")
    
    if blacklisted_role:
        requirements['blacklisted_role'] = blacklisted_role.name
        requirement_list.append(f"• Cannot have **{blacklisted_role.name}** role")
    
    if time_in_server_seconds > 0:
        requirements['time_in_server'] = time_in_server_seconds
        time_str = format_duration(time_in_server_seconds)
        requirement_list.append(f"• Must be in server for **{time_str}**")
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Create giveaway embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Hosted by:** {interaction.user.mention}",
        color=discord.Color.gold()
    )
    
    if requirement_list:
        embed.add_field(
            name="Requirements to Join:",
            value="\n".join(requirement_list),
            inline=False
        )
    else:
        embed.add_field(
            name="Requirements:",
            value="No requirements - anyone can join!",
            inline=False
        )
    
    embed.add_field(
        name="Duration:",
        value=f"Ends <t:{int(end_time.timestamp())}:R>",
        inline=False
    )
    
    embed.set_footer(text="Click the button below to join! | Made with ❤ | Werrzzzy")
    
    # Store giveaway data
    giveaway_data = {
        'prize': prize,
        'winners': winners,
        'host': interaction.user.id,
        'end_time': end_time,
        'requirements': requirements,
        'participants': [],
        'channel_id': channel.id,
        'guild_id': interaction.guild.id
    }
    
    # Create view
    view = GiveawayView(giveaway_data)
    
    # Send giveaway message to the specified channel
    try:
        giveaway_message = await channel.send(embed=embed, view=view)
        
        # Store giveaway with message ID as key
        active_giveaways[giveaway_message.id] = giveaway_data
        giveaway_data['message_id'] = giveaway_message.id
        
        await interaction.response.send_message(f"✅ Giveaway created successfully in {channel.mention}! Message ID: `{giveaway_message.id}`", ephemeral=True)
        
        # Schedule giveaway end
        asyncio.create_task(end_giveaway_after_delay(giveaway_message.id, duration_seconds))
        
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ I don't have permission to send messages in {channel.mention}.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to create giveaway: {e}", ephemeral=True)

async def end_giveaway_after_delay(message_id, delay_seconds):
    """End giveaway after specified delay"""
    await asyncio.sleep(delay_seconds)
    await end_giveaway(message_id)

async def end_giveaway(message_id):
    """End a giveaway and pick winners"""
    if message_id not in active_giveaways:
        return
    
    giveaway_data = active_giveaways[message_id]
    participants = giveaway_data.get('participants', [])
    winners_count = giveaway_data['winners']
    
    # Get channel and message
    try:
        channel = bot.get_channel(giveaway_data['channel_id'])
        if not channel:
            return
        
        message = await channel.fetch_message(message_id)
        
        # Create results embed
        embed = discord.Embed(
            title="🎉 GIVEAWAY ENDED 🎉",
            description=f"**Prize:** {giveaway_data['prize']}",
            color=discord.Color.red()
        )
        
        if not participants:
            embed.add_field(
                name="Winners:",
                value="No one participated in this giveaway 😢",
                inline=False
            )
        else:
            # Pick winners
            actual_winners = min(winners_count, len(participants))
            winners = random.sample(participants, actual_winners)
            
            winner_mentions = [f"<@{winner_id}>" for winner_id in winners]
            
            embed.add_field(
                name=f"Winner{'s' if actual_winners != 1 else ''}:",
                value="\n".join(winner_mentions),
                inline=False
            )
            
            embed.add_field(
                name="Total Participants:",
                value=str(len(participants)),
                inline=True
            )
        
        embed.set_footer(text="Giveaway has ended! | Made with ❤ | Werrzzzy")
        
        # Update message
        await message.edit(embed=embed, view=None)
        
        # Send winner announcement
        if participants:
            winner_text = ", ".join([f"<@{winner_id}>" for winner_id in winners])
            await channel.send(f"🎉 Congratulations {winner_text}! You won **{giveaway_data['prize']}**!")
        
    except Exception as e:
        print(f"Error ending giveaway {message_id}: {e}")

@bot.command(name='gw')
@is_moderator()
async def giveaway_reroll_command(ctx, message_id: str):
    """Reroll giveaway winners using message ID"""
    try:
        # Convert message_id to int
        msg_id = int(message_id)
        
        if msg_id not in active_giveaways:
            await ctx.send("❌ Giveaway not found. Make sure you're using the correct message ID.")
            return
        
        giveaway_data = active_giveaways[msg_id]
        participants = giveaway_data.get('participants', [])
        winners_count = giveaway_data['winners']
        
        if not participants:
            await ctx.send("❌ No participants to reroll from.")
            return
        
        # Pick new winners
        actual_winners = min(winners_count, len(participants))
        new_winners = random.sample(participants, actual_winners)
        
        # Create embed for reroll results
        embed = discord.Embed(
            title="🎲 GIVEAWAY REROLLED 🎲",
            description=f"**Prize:** {giveaway_data['prize']}",
            color=discord.Color.blue()
        )
        
        winner_mentions = [f"<@{winner_id}>" for winner_id in new_winners]
        
        embed.add_field(
            name=f"New Winner{'s' if actual_winners != 1 else ''}:",
            value="\n".join(winner_mentions),
            inline=False
        )
        
        embed.add_field(
            name="Total Participants:",
            value=str(len(participants)),
            inline=True
        )
        
        embed.set_footer(text="Giveaway rerolled by moderator | Made with ❤ | Werrzzzy")
        
        await ctx.send(embed=embed)
        
        # Send new winner announcement
        winner_text = ", ".join([f"<@{winner_id}>" for winner_id in new_winners])
        await ctx.send(f"🎉 Congratulations to the new winner(s) {winner_text}! You won **{giveaway_data['prize']}**!")
        
    except ValueError:
        await ctx.send("❌ Invalid message ID format. Please provide a valid number.")
    except Exception as e:
        await ctx.send(f"❌ Error rerolling giveaway: {e}")

@bot.tree.command(name="gwreroll", description="Reroll giveaway winners using message ID")
@check_moderator()
async def giveaway_reroll_slash(interaction: discord.Interaction, message_id: str):
    """Reroll giveaway winners using message ID"""
    try:
        # Convert message_id to int
        msg_id = int(message_id)
        
        if msg_id not in active_giveaways:
            await interaction.response.send_message("❌ Giveaway not found. Make sure you're using the correct message ID.", ephemeral=True)
            return
        
        giveaway_data = active_giveaways[msg_id]
        participants = giveaway_data.get('participants', [])
        winners_count = giveaway_data['winners']
        
        if not participants:
            await interaction.response.send_message("❌ No participants to reroll from.", ephemeral=True)
            return
        
        # Pick new winners
        actual_winners = min(winners_count, len(participants))
        new_winners = random.sample(participants, actual_winners)
        
        # Create embed for reroll results
        embed = discord.Embed(
            title="🎲 GIVEAWAY REROLLED 🎲",
            description=f"**Prize:** {giveaway_data['prize']}",
            color=discord.Color.blue()
        )
        
        winner_mentions = [f"<@{winner_id}>" for winner_id in new_winners]
        
        embed.add_field(
            name=f"New Winner{'s' if actual_winners != 1 else ''}:",
            value="\n".join(winner_mentions),
            inline=False
        )
        
        embed.add_field(
            name="Total Participants:",
            value=str(len(participants)),
            inline=True
        )
        
        embed.set_footer(text="Giveaway rerolled by moderator | Made with ❤ | Werrzzzy")
        
        await interaction.response.send_message(embed=embed)
        
        # Send new winner announcement
        winner_text = ", ".join([f"<@{winner_id}>" for winner_id in new_winners])
        await interaction.followup.send(f"🎉 Congratulations to the new winner(s) {winner_text}! You won **{giveaway_data['prize']}**!")
        
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID format. Please provide a valid number.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error rerolling giveaway: {e}", ephemeral=True)

# ==================== INFO COMMANDS ====================

@bot.command(name='uptime')
@not_blocked()
async def uptime_command(ctx):
    """Show bot uptime"""
    current_time = time.time()
    uptime_seconds = current_time - BOT_START_TIME
    uptime_str = format_uptime(uptime_seconds)
    
    embed = discord.Embed(
        title="🕐 Bot Uptime",
        description=f"I've been running for **{uptime_str}**",
        color=discord.Color.green()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="uptime", description="Show bot uptime")
@check_not_blocked()
async def uptime_slash(interaction: discord.Interaction):
    """Show bot uptime"""
    current_time = time.time()
    uptime_seconds = current_time - BOT_START_TIME
    uptime_str = format_uptime(uptime_seconds)
    
    embed = discord.Embed(
        title="🕐 Bot Uptime",
        description=f"I've been running for **{uptime_str}**",
        color=discord.Color.green()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await interaction.response.send_message(embed=embed)

@bot.command(name='ping')
@not_blocked()
async def ping_command(ctx):
    """Show bot latency"""
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: **{latency}ms**",
        color=discord.Color.green()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

@bot.tree.command(name="ping", description="Show bot latency")
@check_not_blocked()
async def ping_slash(interaction: discord.Interaction):
    """Show bot latency"""
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: **{latency}ms**",
        color=discord.Color.green()
    )
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await interaction.response.send_message(embed=embed)

# Start bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set!")
    else:
        bot.run(token)
