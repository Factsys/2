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

# Store active giveaways: {message_id: giveaway_data}
active_giveaways = {}

# Store user message counts: {guild_id: {user_id: count}}
user_message_counts = {}

# Store giveaway host roles: {guild_id: [role_ids]}
giveaway_host_roles = {}

# ENHANCED: Increased storage capacity to support 100 pages
MAX_MESSAGES = 100  # Increased from 10 to 100
MESSAGES_PER_PAGE = 10  # Number of messages to show per page in list view

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
def check_giveaway_requirements(member, requirements, guild):
    """Check if a member meets all giveaway requirements"""
    if not requirements:
        return True, []
    
    failed_requirements = []
    
    for req_type, req_value in requirements:
        if req_type == "messages":
            user_count = get_user_message_count(guild.id, member.id)
            if user_count < req_value:
                failed_requirements.append(f"Need {req_value} messages (has {user_count})")
        
        elif req_type == "role":
            if not any(role.name.lower() == req_value.lower() for role in member.roles):
                failed_requirements.append(f"Need role: {req_value}")
        
        elif req_type == "time-in-server":
            if member.joined_at:
                time_in_server = (datetime.utcnow() - member.joined_at.replace(tzinfo=None)).total_seconds()
                if time_in_server < req_value:
                    required_time = format_duration(req_value)
                    actual_time = format_duration(int(time_in_server))
                    failed_requirements.append(f"Need {required_time} in server (has {actual_time})")
            else:
                failed_requirements.append("Cannot verify join date")
        
        elif req_type == "roleblacklisted":
            if any(role.name.lower() == req_value.lower() for role in member.roles):
                failed_requirements.append(f"Cannot have role: {req_value}")
    
    return len(failed_requirements) == 0, failed_requirements

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

# Custom check for manage nicknames permission
def has_manage_nicknames():
    async def predicate(ctx):
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
        if not interaction.guild:
            return False
        return can_host_giveaway(interaction.user)
    return app_commands.check(predicate)

# Custom check for specific user ID
def is_specific_user():
    async def predicate(ctx):
        return ctx.author.id == 776883692983156736
    return commands.check(predicate)

def check_specific_user():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == 776883692983156736
    return app_commands.check(predicate)

# Giveaway Join View
class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_data):
        super().__init__(timeout=None)
        self.giveaway_data = giveaway_data
    
    @discord.ui.button(label="🎉 Join Giveaway", style=discord.ButtonStyle.primary, custom_id="join_giveaway")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild
        
        # Check if user already joined
        if user.id in self.giveaway_data.get('participants', []):
            await interaction.response.send_message("❌ You've already joined this giveaway!", ephemeral=True)
            return
        
        # Check requirements
        requirements = self.giveaway_data.get('requirements', [])
        meets_reqs, failed_reqs = check_giveaway_requirements(user, requirements, guild)
        
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
        self.go_to_page_button.disabled = self.total_pages <= 1
    
    def get_embed(self):
        # Calculate start and end indices for current page
        start_idx = self.current_page * self.participants_per_page
        end_idx = min(start_idx + self.participants_per_page, len(self.participants))
        page_participants = self.participants[start_idx:end_idx]
        
        # Create embed
        embed = discord.Embed(
            title=f"Giveaway Participants (Page {self.current_page + 1}/{self.total_pages})",
            description=f"These are the members that have participated in the giveaway of **{self.giveaway_data['prize']}**:",
            color=discord.Color.blue()
        )
        
        # Build numbered list of participants
        participant_list = []
        for i, user_id in enumerate(page_participants, start=start_idx + 1):
            member = self.guild.get_member(user_id)
            if member:
                # Format like: "1. @leaf | @ for help (1 entry)"
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
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.get_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(label="Go To Page", style=discord.ButtonStyle.secondary)
    async def go_to_page_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # This would need a modal for page input, keeping it simple for now
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

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f"Bot is online as {bot.user}!")
    await bot.change_presence(activity=discord.Game(name="Type /help or ,help for commands"))
    
    # Start giveaway task
    bot.loop.create_task(giveaway_task())

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

    if message.channel.id not in sniped_messages:
        sniped_messages[message.channel.id] = []
    
    # Try to find who deleted the message from audit logs
    deleted_by = message.author  # Default to message author (self-delete)
    
    try:
        # Check audit logs to see if someone else deleted it
        async for entry in message.guild.audit_logs(limit=10, action=discord.AuditLogAction.message_delete):
            # Check if this audit log entry is for our deleted message
            if (entry.target.id == message.author.id and 
                entry.created_at > message.created_at and
                (discord.utils.utcnow() - entry.created_at).total_seconds() < 5):  # Within 5 seconds
                deleted_by = entry.user
                break
    except (discord.Forbidden, discord.HTTPException, AttributeError):
        # If we can't access audit logs or there's an error, assume self-delete
        pass
    
    # Add offensive content flag to saved messages
    sniped_messages[message.channel.id].append({
        "content": message.content,
        "author": message.author,
        "deleted_by": deleted_by,
        "attachments": message.attachments,
        "time": message.created_at,
        "has_offensive_content": is_offensive_content(message.content)
    })

    # ENHANCED: Increased limit to 100 messages
    if len(sniped_messages[message.channel.id]) > MAX_MESSAGES:
        sniped_messages[message.channel.id].pop(0)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    if before.content == after.content:
        return  # No actual edit if content is the same (embed loading, etc.)
    
    if before.channel.id not in edited_messages:
        edited_messages[before.channel.id] = []
    
    # Add offensive content flags to saved messages
    edited_messages[before.channel.id].append({
        "before_content": before.content,
        "after_content": after.content,
        "author": before.author,
        "attachments": before.attachments,
        "time": after.edited_at or discord.utils.utcnow(),
        "before_has_offensive_content": is_offensive_content(before.content),
        "after_has_offensive_content": is_offensive_content(after.content)
    })
    
    # ENHANCED: Increased limit to 100 messages
    if len(edited_messages[before.channel.id]) > MAX_MESSAGES:
        edited_messages[before.channel.id].pop(0)

@bot.event
async def on_member_update(before, after):
    """Handle namelock enforcement when user changes nickname"""
    if before.display_name != after.display_name:
        # Check if user is namelocked
        if after.id in namelocked_users:
            locked_nickname = namelocked_users[after.id]
            if after.display_name != locked_nickname:
                try:
                    # Revert to locked nickname
                    await after.edit(nick=locked_nickname, reason="Namelock enforcement")
                except discord.Forbidden:
                    pass  # Bot doesn't have permission
                except Exception:
                    pass  # Other errors

# Background task to handle giveaway endings
async def giveaway_task():
    """Background task to check and end giveaways"""
    while True:
        try:
            current_time = datetime.utcnow()
            ended_giveaways = []
            
            for message_id, giveaway_data in active_giveaways.items():
                if current_time >= giveaway_data['end_time']:
                    ended_giveaways.append(message_id)
            
            for message_id in ended_giveaways:
                await end_giveaway_automatically(message_id)
            
            await asyncio.sleep(10)  # Check every 10 seconds
        except Exception as e:
            print(f"Error in giveaway task: {e}")
            await asyncio.sleep(30)

async def end_giveaway_automatically(message_id):
    """Automatically end a giveaway"""
    try:
        if message_id not in active_giveaways:
            return
        
        giveaway_data = active_giveaways[message_id]
        channel = bot.get_channel(giveaway_data['channel_id'])
        if not channel:
            return
        
        try:
            message = await channel.fetch_message(message_id)
        except discord.NotFound:
            del active_giveaways[message_id]
            return
        
        participants = giveaway_data.get('participants', [])
        winners_count = giveaway_data.get('winners', 1)
        
        # Select winners
        if participants:
            winners = random.sample(participants, min(winners_count, len(participants)))
            winner_mentions = [f"<@{winner}>" for winner in winners]
            
            # Create winner announcement embed
            embed = discord.Embed(
                title="🎉 Giveaway Ended!",
                description=f"**Prize:** {giveaway_data['prize']}\n\n**Winner(s):** {', '.join(winner_mentions)}",
                color=discord.Color.gold()
            )
        else:
            embed = discord.Embed(
                title="🎉 Giveaway Ended!",
                description=f"**Prize:** {giveaway_data['prize']}\n\n**Winner:** No participants",
                color=discord.Color.red()
            )
            winner_mentions = []
        
        embed.add_field(name="Total Participants", value=str(len(participants)), inline=True)
        embed.add_field(name="Ended at", value=f"<t:{int(datetime.utcnow().timestamp())}:F>", inline=True)
        embed.set_footer(text="Congratulations to the winner(s)!")
        
        await message.edit(embed=embed, view=None)
        
        # Send winner announcement
        if winner_mentions:
            await channel.send(f"🎉 Congratulations {', '.join(winner_mentions)}! You won **{giveaway_data['prize']}**!")
        
        # Remove from active giveaways
        del active_giveaways[message_id]
        
    except Exception as e:
        print(f"Error ending giveaway {message_id}: {e}")

# ========== SLASH COMMANDS ==========

@bot.tree.command(name="snipe", description="Displays the most recently deleted message")
@app_commands.describe(page="Page number (1-100)", channel="Channel or thread to check (optional)")
async def snipe_slash(interaction: discord.Interaction, page: int = 1, channel: Union[discord.TextChannel, discord.Thread] = None):
    target_channel = channel or interaction.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await interaction.response.send_message(f"No recently deleted messages in {target_channel.mention}.", ephemeral=True)
        return

    if page < 1 or page > len(sniped_messages[target_channel.id]):
        await interaction.response.send_message(f"Page must be between 1 and {len(sniped_messages[target_channel.id])}.", ephemeral=True)
        return

    snipe = sniped_messages[target_channel.id][-page]
    embed = discord.Embed(title="📜 Sniped Message", color=discord.Color.gold())
    
    # Filter content if it contains offensive words
    content = snipe['content'] or "*No text content*"
    if snipe.get('has_offensive_content', False):
        content = filter_content(content)
    
    embed.add_field(name="**Content:**", value=content, inline=False)
    
    # Show who deleted the message - if same person or can't detect, show author name
    deleted_by = snipe.get('deleted_by', snipe['author'])
    embed.add_field(name="**Deleted by:**", value=deleted_by.display_name, inline=True)
    
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.add_field(name="**Channel:**", value=target_channel.mention, inline=True)
    embed.set_footer(text=f"Page {page} of {len(sniped_messages[target_channel.id])} | Made with ❤ | Werrzzzy")

    # Handle attachments and media links (IMAGES/GIFS/VIDEOS)
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

@bot.tree.command(name="sp", description="Display a paginated list of deleted messages")
@app_commands.describe(channel="Channel or thread to check (optional)")
async def sp_slash(interaction: discord.Interaction, channel: Union[discord.TextChannel, discord.Thread] = None):
    target_channel = channel or interaction.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await interaction.response.send_message(f"No recently deleted messages in {target_channel.mention}.", ephemeral=True)
        return

    # Reverse the messages to show newest first
    messages = list(reversed(sniped_messages[target_channel.id]))
    
    # Use REGULAR pagination view (filtered content)
    view = RegularSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    # Update embed title to show channel
    embed.title = f"📜 Deleted Messages List - {target_channel.name}"
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="spforce", description="Display unfiltered offensive messages only (mod only)")
@app_commands.describe(channel="Channel or thread to check (optional)")
@check_moderator()
async def spforce_slash(interaction: discord.Interaction, channel: Union[discord.TextChannel, discord.Thread] = None):
    target_channel = channel or interaction.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await interaction.response.send_message(f"No recently deleted messages in {target_channel.mention}.", ephemeral=True)
        return

    # Filter to only show messages with offensive content
    offensive_messages = [msg for msg in sniped_messages[target_channel.id] if msg.get('has_offensive_content', False)]
    
    if not offensive_messages:
        await interaction.response.send_message(f"No offensive messages found in {target_channel.mention}.", ephemeral=True)
        return
    
    # Reverse the messages to show newest first
    messages = list(reversed(offensive_messages))
    
    # Use MODERATOR pagination view (unfiltered content)
    view = ModeratorSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    # Update embed title to show channel
    embed.title = f"🔒 Moderator Snipe Pages - {target_channel.name} (Unfiltered)"
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="namelock", description="Lock a user's nickname")
@app_commands.describe(user="User to namelock", nickname="Nickname to lock them to")
@check_admin_or_permissions(manage_nicknames=True)
async def namelock_slash(interaction: discord.Interaction, user: discord.Member, nickname: str):
    if len(nickname) > 32:
        await interaction.response.send_message("❌ Nickname must be 32 characters or less.", ephemeral=True)
        return
    
    try:
        await user.edit(nick=nickname, reason=f"Namelocked by {interaction.user}")
        namelocked_users[user.id] = nickname
        
        embed = discord.Embed(
            title="✅ User Namelocked",
            description=f"{user.mention} has been namelocked to `{nickname}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change this user's nickname.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="nl", description="Lock a user's nickname (short for namelock)")
@app_commands.describe(user="User to namelock", nickname="Nickname to lock them to")
@check_admin_or_permissions(manage_nicknames=True)
async def nl_slash(interaction: discord.Interaction, user: discord.Member, nickname: str):
    await namelock_slash(interaction, user, nickname)

@bot.tree.command(name="unl", description="Unlock a user's nickname")
@app_commands.describe(user="User to unlock")
@check_admin_or_permissions(manage_nicknames=True)
async def unl_slash(interaction: discord.Interaction, user: discord.Member):
    if user.id not in namelocked_users:
        await interaction.response.send_message("❌ This user is not namelocked.", ephemeral=True)
        return
    
    del namelocked_users[user.id]
    
    embed = discord.Embed(
        title="✅ User Unlocked",
        description=f"{user.mention} can now change their nickname freely",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rename", description="Rename a user")
@app_commands.describe(user="User to rename", nickname="New nickname")
@check_admin_or_permissions(manage_nicknames=True)
async def rename_slash(interaction: discord.Interaction, user: discord.Member, nickname: str):
    if len(nickname) > 32:
        await interaction.response.send_message("❌ Nickname must be 32 characters or less.", ephemeral=True)
        return
    
    old_nick = user.display_name
    
    try:
        await user.edit(nick=nickname, reason=f"Renamed by {interaction.user}")
        
        embed = discord.Embed(
            title="✅ User Renamed",
            description=f"{user.mention} renamed from `{old_nick}` to `{nickname}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change this user's nickname.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="re", description="Rename a user (short for rename)")
@app_commands.describe(user="User to rename", nickname="New nickname")
@check_admin_or_permissions(manage_nicknames=True)
async def re_slash(interaction: discord.Interaction, user: discord.Member, nickname: str):
    await rename_slash(interaction, user, nickname)

@bot.tree.command(name="message", description="Send a message as the bot")
@app_commands.describe(content="Message to send")
@check_moderator()
async def message_slash(interaction: discord.Interaction, content: str):
    await interaction.response.send_message(content)

@bot.tree.command(name="mess", description="Send a message as the bot (short for message)")
@app_commands.describe(content="Message to send")
@check_moderator()
async def mess_slash(interaction: discord.Interaction, content: str):
    await message_slash(interaction, content)

@bot.tree.command(name="saywb", description="Send a message via webhook with custom color")
@app_commands.describe(color="Color (hex, name, or default)", content="Message content")
@check_moderator()
async def saywb_slash(interaction: discord.Interaction, color: str, content: str):
    try:
        webhook = await get_or_create_webhook(interaction.channel)
        
        embed_color = parse_color(color)
        embed = discord.Embed(description=content, color=embed_color)
        
        await webhook.send(embed=embed, username="SnipeBot", avatar_url=bot.user.display_avatar.url)
        await interaction.response.send_message("✅ Message sent via webhook!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error sending webhook: {str(e)}", ephemeral=True)

# ========== GIVEAWAY COMMANDS ==========

@bot.tree.command(name="giveaway", description="Create a giveaway with requirements")
@app_commands.describe(
    prize="What the winner will receive",
    duration="How long the giveaway runs (e.g., 1h, 30m, 2d)",
    winners="Number of winners (default: 1)",
    requirements="Requirements (e.g., 'messages 50, role @Member, time-in-server 1d')",
    channel="Channel to post the giveaway (optional)"
)
@check_giveaway_host()
async def giveaway_slash(interaction: discord.Interaction, prize: str, duration: str, winners: int = 1, requirements: str = None, channel: Union[discord.TextChannel, discord.Thread] = None):
    target_channel = channel or interaction.channel
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        await interaction.response.send_message("❌ Invalid duration format. Use format like: 1h, 30m, 2d", ephemeral=True)
        return
    
    if winners < 1 or winners > 20:
        await interaction.response.send_message("❌ Number of winners must be between 1 and 20.", ephemeral=True)
        return
    
    # Parse requirements
    parsed_requirements = []
    if requirements:
        req_parts = [req.strip() for req in requirements.split(',')]
        for req in req_parts:
            req = req.strip()
            if req.startswith('messages '):
                try:
                    msg_count = int(req.split()[1])
                    parsed_requirements.append(('messages', msg_count))
                except (IndexError, ValueError):
                    await interaction.response.send_message(f"❌ Invalid messages requirement: {req}", ephemeral=True)
                    return
            elif req.startswith('role '):
                role_name = req[5:].strip().lstrip('@')
                parsed_requirements.append(('role', role_name))
            elif req.startswith('time-in-server '):
                time_str = req.split()[1]
                time_seconds = parse_time_string(time_str)
                if time_seconds == 0:
                    await interaction.response.send_message(f"❌ Invalid time format: {time_str}", ephemeral=True)
                    return
                parsed_requirements.append(('time-in-server', time_seconds))
            elif req.startswith('roleblacklisted '):
                role_name = req[15:].strip().lstrip('@')
                parsed_requirements.append(('roleblacklisted', role_name))
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Create embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="Winners", value=str(winners), inline=True)
    embed.add_field(name="Ends", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
    embed.add_field(name="Hosted by", value=interaction.user.mention, inline=True)
    
    if parsed_requirements:
        req_text = []
        for req_type, req_value in parsed_requirements:
            if req_type == "messages":
                req_text.append(f"• At least {req_value} messages in server")
            elif req_type == "role":
                req_text.append(f"• Must have role: {req_value}")
            elif req_type == "time-in-server":
                req_text.append(f"• Must be in server for: {format_duration(req_value)}")
            elif req_type == "roleblacklisted":
                req_text.append(f"• Cannot have role: {req_value}")
        
        embed.add_field(name="Requirements", value="\n".join(req_text), inline=False)
    
    embed.set_footer(text="Click the button below to join!")
    
    # Create giveaway data
    giveaway_data = {
        'prize': prize,
        'host_id': interaction.user.id,
        'channel_id': target_channel.id,
        'end_time': end_time,
        'winners': winners,
        'requirements': parsed_requirements,
        'participants': []
    }
    
    # Send message with view
    view = GiveawayView(giveaway_data)
    
    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()
    
    # Store giveaway data
    active_giveaways[message.id] = giveaway_data

@bot.tree.command(name="giveawaylist", description="List participants of a giveaway")
@app_commands.describe(message_id="ID of the giveaway message")
async def giveawaylist_slash(interaction: discord.Interaction, message_id: str):
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
        return
    
    if msg_id not in active_giveaways:
        await interaction.response.send_message("❌ Giveaway not found or already ended.", ephemeral=True)
        return
    
    giveaway_data = active_giveaways[msg_id]
    participants = giveaway_data.get('participants', [])
    
    if not participants:
        embed = discord.Embed(
            title="Giveaway Participants",
            description=f"No one has joined the giveaway of **{giveaway_data['prize']}** yet.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Create pagination view
    view = GiveawayParticipantsPaginationView(participants, giveaway_data, interaction.guild)
    embed = view.get_embed()
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@bot.tree.command(name="giveawayremove", description="Remove a user from a giveaway")
@app_commands.describe(message_id="ID of the giveaway message", user="User to remove from giveaway")
@check_giveaway_host()
async def giveawayremove_slash(interaction: discord.Interaction, message_id: str, user: discord.Member):
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
        return
    
    if msg_id not in active_giveaways:
        await interaction.response.send_message("❌ Giveaway not found or already ended.", ephemeral=True)
        return
    
    giveaway_data = active_giveaways[msg_id]
    
    # Check if user is the host or has permission
    if (interaction.user.id != giveaway_data['host_id'] and 
        not interaction.user.guild_permissions.administrator and
        interaction.user.id != interaction.guild.owner_id):
        await interaction.response.send_message("❌ You can only remove participants from your own giveaways.", ephemeral=True)
        return
    
    participants = giveaway_data.get('participants', [])
    
    if user.id not in participants:
        await interaction.response.send_message(f"❌ {user.mention} is not participating in this giveaway.", ephemeral=True)
        return
    
    # Remove user
    participants.remove(user.id)
    
    embed = discord.Embed(
        title="✅ User Removed",
        description=f"{user.mention} has been removed from the giveaway of **{giveaway_data['prize']}**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="giveawayreroll", description="Reroll winners of a giveaway")
@app_commands.describe(message_id="ID of the giveaway message")
@check_giveaway_host()
async def giveawayreroll_slash(interaction: discord.Interaction, message_id: str):
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
        return
    
    if msg_id not in active_giveaways:
        await interaction.response.send_message("❌ Giveaway not found. Note: Only active giveaways can be rerolled.", ephemeral=True)
        return
    
    giveaway_data = active_giveaways[msg_id]
    
    # Check if user is the host or has permission
    if (interaction.user.id != giveaway_data['host_id'] and 
        not interaction.user.guild_permissions.administrator and
        interaction.user.id != interaction.guild.owner_id):
        await interaction.response.send_message("❌ You can only reroll your own giveaways.", ephemeral=True)
        return
    
    participants = giveaway_data.get('participants', [])
    winners_count = giveaway_data.get('winners', 1)
    
    if not participants:
        await interaction.response.send_message("❌ No participants to reroll.", ephemeral=True)
        return
    
    # Select new winners
    winners = random.sample(participants, min(winners_count, len(participants)))
    winner_mentions = [f"<@{winner}>" for winner in winners]
    
    embed = discord.Embed(
        title="🎉 Giveaway Rerolled!",
        description=f"**Prize:** {giveaway_data['prize']}\n\n**New Winner(s):** {', '.join(winner_mentions)}",
        color=discord.Color.gold()
    )
    embed.add_field(name="Rerolled by", value=interaction.user.mention, inline=True)
    
    await interaction.response.send_message(embed=embed)
    
    # Send winner announcement
    await interaction.followup.send(f"🎉 Congratulations {', '.join(winner_mentions)}! You won **{giveaway_data['prize']}** (Reroll)!")

@bot.tree.command(name="giveawayend", description="End a giveaway early")
@app_commands.describe(message_id="ID of the giveaway message")
@check_giveaway_host()
async def giveawayend_slash(interaction: discord.Interaction, message_id: str):
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
        return
    
    if msg_id not in active_giveaways:
        await interaction.response.send_message("❌ Giveaway not found or already ended.", ephemeral=True)
        return
    
    giveaway_data = active_giveaways[msg_id]
    
    # Check if user is the host or has permission
    if (interaction.user.id != giveaway_data['host_id'] and 
        not interaction.user.guild_permissions.administrator and
        interaction.user.id != interaction.guild.owner_id):
        await interaction.response.send_message("❌ You can only end your own giveaways.", ephemeral=True)
        return
    
    # End the giveaway
    await end_giveaway_automatically(msg_id)
    
    await interaction.response.send_message("✅ Giveaway ended successfully!", ephemeral=True)

@bot.tree.command(name="giveawayhost", description="Set roles that can host giveaways")
@app_commands.describe(role="Role to add as giveaway host")
@check_admin_or_permissions(administrator=True)
async def giveawayhost_slash(interaction: discord.Interaction, role: discord.Role):
    guild_id = interaction.guild.id
    
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = []
    
    if role.id in giveaway_host_roles[guild_id]:
        await interaction.response.send_message(f"❌ {role.mention} is already a giveaway host role.", ephemeral=True)
        return
    
    giveaway_host_roles[guild_id].append(role.id)
    
    embed = discord.Embed(
        title="✅ Giveaway Host Role Added",
        description=f"{role.mention} can now host giveaways",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# ========== PREFIX COMMANDS ==========

@bot.command(name="snipe", aliases=["s"])
async def snipe_prefix(ctx, page: int = 1, channel: Union[discord.TextChannel, discord.Thread] = None):
    target_channel = channel or ctx.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await ctx.send(f"No recently deleted messages in {target_channel.mention}.")
        return

    if page < 1 or page > len(sniped_messages[target_channel.id]):
        await ctx.send(f"Page must be between 1 and {len(sniped_messages[target_channel.id])}.")
        return

    snipe = sniped_messages[target_channel.id][-page]
    embed = discord.Embed(title="📜 Sniped Message", color=discord.Color.gold())
    
    # Filter content if it contains offensive words
    content = snipe['content'] or "*No text content*"
    if snipe.get('has_offensive_content', False):
        content = filter_content(content)
    
    embed.add_field(name="**Content:**", value=content, inline=False)
    
    # Show who deleted the message
    deleted_by = snipe.get('deleted_by', snipe['author'])
    embed.add_field(name="**Deleted by:**", value=deleted_by.display_name, inline=True)
    
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.add_field(name="**Channel:**", value=target_channel.mention, inline=True)
    embed.set_footer(text=f"Page {page} of {len(sniped_messages[target_channel.id])} | Made with ❤ | Werrzzzy")

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

@bot.command(name="sp")
async def sp_prefix(ctx, channel: Union[discord.TextChannel, discord.Thread] = None):
    target_channel = channel or ctx.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await ctx.send(f"No recently deleted messages in {target_channel.mention}.")
        return

    # Reverse the messages to show newest first
    messages = list(reversed(sniped_messages[target_channel.id]))
    
    # Use REGULAR pagination view (filtered content)
    view = RegularSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    # Update embed title to show channel
    embed.title = f"📜 Deleted Messages List - {target_channel.name}"
    
    await ctx.send(embed=embed, view=view)

@bot.command(name="spforce", aliases=["spf"])
@is_moderator()
async def spforce_prefix(ctx, channel: Union[discord.TextChannel, discord.Thread] = None):
    target_channel = channel or ctx.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await ctx.send(f"No recently deleted messages in {target_channel.mention}.")
        return

    # Filter to only show messages with offensive content
    offensive_messages = [msg for msg in sniped_messages[target_channel.id] if msg.get('has_offensive_content', False)]
    
    if not offensive_messages:
        await ctx.send(f"No offensive messages found in {target_channel.mention}.")
        return
    
    # Reverse the messages to show newest first
    messages = list(reversed(offensive_messages))
    
    # Use MODERATOR pagination view (unfiltered content)
    view = ModeratorSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    # Update embed title to show channel
    embed.title = f"🔒 Moderator Snipe Pages - {target_channel.name} (Unfiltered)"
    
    await ctx.send(embed=embed, view=view)

@bot.command(name="namelock", aliases=["nl"])
@has_manage_nicknames()
async def namelock_prefix(ctx, user: discord.Member, *, nickname: str):
    if len(nickname) > 32:
        await ctx.send("❌ Nickname must be 32 characters or less.")
        return
    
    try:
        await user.edit(nick=nickname, reason=f"Namelocked by {ctx.author}")
        namelocked_users[user.id] = nickname
        
        embed = discord.Embed(
            title="✅ User Namelocked",
            description=f"{user.mention} has been namelocked to `{nickname}`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name="unl")
@has_manage_nicknames()
async def unl_prefix(ctx, user: discord.Member):
    if user.id not in namelocked_users:
        await ctx.send("❌ This user is not namelocked.")
        return
    
    del namelocked_users[user.id]
    
    embed = discord.Embed(
        title="✅ User Unlocked",
        description=f"{user.mention} can now change their nickname freely",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name="rename", aliases=["re"])
@has_manage_nicknames()
async def rename_prefix(ctx, user: discord.Member, *, nickname: str):
    if len(nickname) > 32:
        await ctx.send("❌ Nickname must be 32 characters or less.")
        return
    
    old_nick = user.display_name
    
    try:
        await user.edit(nick=nickname, reason=f"Renamed by {ctx.author}")
        
        embed = discord.Embed(
            title="✅ User Renamed",
            description=f"{user.mention} renamed from `{old_nick}` to `{nickname}`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name="message", aliases=["mess"])
@is_moderator()
async def message_prefix(ctx, *, content: str):
    await ctx.send(content)

@bot.command(name="saywb")
@is_moderator()
async def saywb_prefix(ctx, color: str, *, content: str):
    try:
        webhook = await get_or_create_webhook(ctx.channel)
        
        embed_color = parse_color(color)
        embed = discord.Embed(description=content, color=embed_color)
        
        await webhook.send(embed=embed, username="SnipeBot", avatar_url=bot.user.display_avatar.url)
        await ctx.message.delete()  # Delete the command message
    except Exception as e:
        await ctx.send(f"❌ Error sending webhook: {str(e)}")

@bot.command(name="editsnipe", aliases=["es"])
async def editsnipe_prefix(ctx, page: int = 1):
    if ctx.channel.id not in edited_messages or not edited_messages[ctx.channel.id]:
        await ctx.send("No recently edited messages in this channel.")
        return

    if page < 1 or page > len(edited_messages[ctx.channel.id]):
        await ctx.send(f"Page must be between 1 and {len(edited_messages[ctx.channel.id])}.")
        return

    edit = edited_messages[ctx.channel.id][-page]
    embed = discord.Embed(title="📝 Edit Sniped Message", color=discord.Color.orange())
    
    # Filter content for before and after
    before_content = edit['before_content'] or "*No text content*"
    after_content = edit['after_content'] or "*No text content*"
    
    if edit.get('before_has_offensive_content', False):
        before_content = filter_content(before_content)
    if edit.get('after_has_offensive_content', False):
        after_content = filter_content(after_content)
    
    embed.add_field(name="**Before:**", value=before_content[:1024], inline=False)
    embed.add_field(name="**After:**", value=after_content[:1024], inline=False)
    embed.add_field(name="**Author:**", value=edit['author'].display_name, inline=True)
    embed.add_field(name="**Time:**", value=edit['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"Page {page} of {len(edited_messages[ctx.channel.id])} | Made with ❤ | Werrzzzy")

    await ctx.send(embed=embed)

@bot.command(name="help")
async def help_prefix(ctx):
    embed = discord.Embed(
        title="SnipeBot Commands",
        description="Here are all available commands:",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📜 Message Commands",
        value="`/snipe [page] [channel]` - View deleted messages\n"
              "`/sp [channel]` - View paginated deleted messages\n"
              "`/spforce [channel]` - View offensive messages (mods only)\n"
              "`/editsnipe [page]` - View edited messages",
        inline=False
    )
    
    embed.add_field(
        name="🔒 Moderation Commands",
        value="`/namelock <user> <nickname>` - Lock a user's nickname\n"
              "`/nl <user> <nickname>` - Short for namelock\n"
              "`/unl <user>` - Unlock a user's nickname\n"
              "`/rename <user> <nickname>` - Rename a user\n"
              "`/re <user> <nickname>` - Short for rename",
        inline=False
    )
    
    embed.add_field(
        name="💬 Messaging Commands",
        value="`/message <content>` - Send message as bot\n"
              "`/mess <content>` - Short for message\n"
              "`/saywb <color> <content>` - Send via webhook",
        inline=False
    )
    
    embed.add_field(
        name="🎉 Giveaway Commands",
        value="`/giveaway` - Create a giveaway\n"
              "`/giveawaylist <id>` - List participants\n"
              "`/giveawayremove <id> <user>` - Remove participant\n"
              "`/giveawayreroll <id>` - Reroll winners\n"
              "`/giveawayend <id>` - End giveaway early\n"
              "`/giveawayhost <role>` - Set host role",
        inline=False
    )
    
    embed.add_field(
        name="ℹ️ Info",
        value="All commands work with both `/` (slash) and `,` (prefix)\n"
              "Supports channels and threads for message commands",
        inline=False
    )
    
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

@bot.command(name="uptime")
async def uptime_prefix(ctx):
    current_time = time.time()
    uptime_seconds = current_time - BOT_START_TIME
    uptime_str = format_uptime(uptime_seconds)
    
    embed = discord.Embed(
        title="🤖 Bot Uptime",
        description=f"**Uptime:** {uptime_str}",
        color=discord.Color.green()
    )
    
    embed.add_field(name="Active Giveaways", value=str(len(active_giveaways)), inline=True)
    embed.add_field(name="Tracked Channels", value=str(len(sniped_messages)), inline=True)
    embed.add_field(name="Namelocked Users", value=str(len(namelocked_users)), inline=True)
    
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

# Start Flask in a separate thread
run_flask()

# Run the bot
if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
