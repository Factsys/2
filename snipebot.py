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
async def on_message(message):
    """Track user messages and handle namelock"""
    if message.author.bot:
        return
    
    # Increment user message count
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    # Handle namelock
    if message.author.id in namelocked_users:
        locked_nickname = namelocked_users[message.author.id]
        if message.author.display_name != locked_nickname:
            try:
                await message.author.edit(nick=locked_nickname)
            except discord.Forbidden:
                pass
    
    await bot.process_commands(message)

@bot.event
async def on_member_update(before, after):
    """Enforce namelock on nickname changes"""
    if after.id in namelocked_users and after.id not in namelock_immune_users:
        locked_nickname = namelocked_users[after.id]
        if after.display_name != locked_nickname:
            try:
                await after.edit(nick=locked_nickname)
            except discord.Forbidden:
                pass

# ===== SLASH COMMANDS =====

@bot.tree.command(name="help", description="Show help information about the bot")
@check_not_blocked()
async def slash_help(interaction: discord.Interaction):
    view = HelpPaginationView()
    embed = view.get_embed()
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# FIXED: Snipe commands with proper media display
@bot.tree.command(name="snipe", description="Show the most recently deleted message in this channel")
@check_not_blocked()
async def slash_snipe(interaction: discord.Interaction, channel: discord.TextChannel = None):
    target_channel = channel or interaction.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("❌ No deleted messages found in this channel.", ephemeral=True)
        return
    
    message_data = sniped_messages[channel_id][0]  # Most recent
    
    # Get media URL and clean content
    media_url = get_media_url(message_data['content'], message_data['attachments'])
    display_content = clean_content_from_media(message_data['content'], media_url) if media_url else message_data['content']
    
    embed = discord.Embed(
        description=filter_content(display_content) if display_content else "*No text content*",
        color=discord.Color.blue(),
        timestamp=message_data['deleted_at']
    )
    
    embed.set_author(
        name=f"{message_data['author'].display_name}",
        icon_url=message_data['author'].display_avatar.url
    )
    
    # FIXED: Display media content as image/video
    if media_url:
        embed.set_image(url=media_url)
    
    embed.set_footer(text=f"Deleted in #{target_channel.name}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="editsnipe", description="Show the most recently edited message in this channel")
@check_not_blocked()
async def slash_editsnipe(interaction: discord.Interaction, channel: discord.TextChannel = None):
    target_channel = channel or interaction.channel
    channel_id = target_channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await interaction.response.send_message("❌ No edited messages found in this channel.", ephemeral=True)
        return
    
    edit_data = edited_messages[channel_id][0]  # Most recent
    
    embed = discord.Embed(
        color=discord.Color.orange(),
        timestamp=edit_data['edited_at']
    )
    
    embed.set_author(
        name=f"{edit_data['author'].display_name}",
        icon_url=edit_data['author'].display_avatar.url
    )
    
    embed.add_field(
        name="Before",
        value=filter_content(edit_data['before_content']) if edit_data['before_content'] else "*No content*",
        inline=False
    )
    
    embed.add_field(
        name="After",
        value=filter_content(edit_data['after_content']) if edit_data['after_content'] else "*No content*",
        inline=False
    )
    
    embed.set_footer(text=f"Edited in #{target_channel.name}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="snipelist", description="Show a paginated list of deleted messages")
@check_not_blocked()
async def slash_snipelist(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    target_channel = channel or interaction.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("❌ No deleted messages found in this channel.", ephemeral=True)
        return
    
    messages = sniped_messages[channel_id]
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Invalid page number. Available pages: 1-{total_pages}", ephemeral=True)
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🗑️ Deleted Messages in #{target_channel.name}",
        color=discord.Color.red(),
        description=f"Page {page}/{total_pages} • Showing {len(page_messages)} messages"
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = filter_content(msg['content']) if msg['content'] else "*No text content*"
        truncated = truncate_content(content, 100)
        
        time_str = msg['deleted_at'].strftime("%H:%M:%S")
        embed.add_field(
            name=f"{i}. {msg['author'].display_name} • {time_str}",
            value=truncated,
            inline=False
        )
    
    embed.set_footer(text=f"Total: {len(messages)} messages stored")
    
    await interaction.response.send_message(embed=embed)

# ENHANCED: Advanced giveaway command with all requested features
@bot.tree.command(name="giveaway", description="Create an advanced giveaway with requirements")
@app_commands.describe(
    duration="Duration (e.g., 1h, 30m, 1d)",
    winners="Number of winners",
    prize="Giveaway prize",
    channel="Channel to send giveaway (optional)",
    messagesreq="Minimum messages required to join (optional)",
    timeinserver="Time in server required (e.g., 1d, 1h) (optional)",
    rolereq="Required role to join (optional)",
    blacklistedrole="Blacklisted role (users with this role cannot join) (optional)",
    color="Embed color (optional)"
)
async def slash_giveaway(interaction: discord.Interaction, duration: str, winners: int, prize: str, 
                        channel: discord.TextChannel = None, messagesreq: int = None, 
                        timeinserver: str = None, rolereq: discord.Role = None, 
                        blacklistedrole: discord.Role = None, color: str = None):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
    if not can_host_giveaway(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to host giveaways.", ephemeral=True)
        return
    
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        await interaction.response.send_message("❌ Invalid duration format. Use examples like: 1h, 30m, 2d", ephemeral=True)
        return
    
    if winners < 1:
        await interaction.response.send_message("❌ Number of winners must be at least 1.", ephemeral=True)
        return
    
    # Parse time in server requirement
    time_in_server_seconds = 0
    if timeinserver:
        time_in_server_seconds = parse_time_string(timeinserver)
        if time_in_server_seconds == 0:
            await interaction.response.send_message("❌ Invalid time in server format. Use examples like: 1d, 2h, 30m", ephemeral=True)
            return
    
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    target_channel = channel or interaction.channel
    embed_color = parse_color(color) if color else discord.Color.gold()
    
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
        color=embed_color
    )
    
    # Add requirements if any
    requirements_text = []
    if messagesreq:
        requirements_text.append(f"📝 {messagesreq} messages minimum")
    if timeinserver:
        requirements_text.append(f"⏰ {timeinserver} in server minimum")
    if rolereq:
        requirements_text.append(f"🎭 {rolereq.mention} role required")
    if blacklistedrole:
        requirements_text.append(f"🚫 {blacklistedrole.mention} role not allowed")
    
    if requirements_text:
        embed.add_field(name="Requirements", value="\n".join(requirements_text), inline=False)
    
    embed.add_field(name="How to enter", value="React with 🎉 to enter!", inline=False)
    embed.set_footer(text=f"Hosted by {interaction.user.display_name}")
    
    await interaction.response.send_message(f"Giveaway created in {target_channel.mention}!", ephemeral=True)
    message = await target_channel.send(embed=embed)
    await message.add_reaction("🎉")
    
    # Store giveaway data with requirements
    requirements = {}
    if messagesreq:
        requirements['messages'] = messagesreq
    if time_in_server_seconds:
        requirements['time_in_server'] = time_in_server_seconds
    if rolereq:
        requirements['required_role'] = rolereq.name
    if blacklistedrole:
        requirements['blacklisted_role'] = blacklistedrole.name
    
    active_giveaways[message.id] = {
        'host_id': interaction.user.id,
        'guild_id': interaction.guild.id,
        'channel_id': target_channel.id,
        'end_time': end_time,
        'winners': winners,
        'prize': prize,
        'requirements': requirements,
        'participants': set()
    }

# ENHANCED: Create command with channel, context, and up to 10 emoji-role pairs
@bot.tree.command(name="create", description="Create reaction role message with up to 10 emoji-role pairs")
@app_commands.describe(
    channel="Channel to send the reaction role message",
    context="Message content (will be bold and bigger)",
    color="Embed color (optional)",
    emoji1="First emoji (supports Discord custom emojis)",
    role1="First role (@role, role name, or role ID)",
    emoji2="Second emoji (optional)",
    role2="Second role (@role, role name, or role ID) (optional)",
    emoji3="Third emoji (optional)",
    role3="Third role (@role, role name, or role ID) (optional)",
    emoji4="Fourth emoji (optional)",
    role4="Fourth role (@role, role name, or role ID) (optional)",
    emoji5="Fifth emoji (optional)",
    role5="Fifth role (@role, role name, or role ID) (optional)",
    emoji6="Sixth emoji (optional)",
    role6="Sixth role (@role, role name, or role ID) (optional)",
    emoji7="Seventh emoji (optional)",
    role7="Seventh role (@role, role name, or role ID) (optional)",
    emoji8="Eighth emoji (optional)",
    role8="Eighth role (@role, role name, or role ID) (optional)",
    emoji9="Ninth emoji (optional)",
    role9="Ninth role (@role, role name, or role ID) (optional)",
    emoji10="Tenth emoji (optional)",
    role10="Tenth role (@role, role name, or role ID) (optional)"
)
async def slash_create(interaction: discord.Interaction, 
                      channel: discord.TextChannel,
                      context: str, 
                      color: str = None,
                      emoji1: str = None, role1: str = None,
                      emoji2: str = None, role2: str = None,
                      emoji3: str = None, role3: str = None,
                      emoji4: str = None, role4: str = None,
                      emoji5: str = None, role5: str = None,
                      emoji6: str = None, role6: str = None,
                      emoji7: str = None, role7: str = None,
                      emoji8: str = None, role8: str = None,
                      emoji9: str = None, role9: str = None,
                      emoji10: str = None, role10: str = None):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You need Manage Roles permission to use this command.", ephemeral=True)
        return
    
    # Helper function to find role by name, ID, or mention
    def find_role(role_input):
        if not role_input:
            return None
        
        guild = interaction.guild
        
        # Try role mention format <@&123456789>
        if role_input.startswith('<@&') and role_input.endswith('>'):
            try:
                role_id = int(role_input[3:-1])
                return guild.get_role(role_id)
            except ValueError:
                pass
        
        # Try role ID (pure number)
        try:
            role_id = int(role_input)
            return guild.get_role(role_id)
        except ValueError:
            pass
        
        # Try role name (case insensitive)
        for role in guild.roles:
            if role.name.lower() == role_input.lower():
                return role
        
        return None
    
    # Collect emoji-role pairs
    emoji_role_pairs = []
    role_inputs = [role1, role2, role3, role4, role5, role6, role7, role8, role9, role10]
    emoji_inputs = [emoji1, emoji2, emoji3, emoji4, emoji5, emoji6, emoji7, emoji8, emoji9, emoji10]
    
    for emoji, role_input in zip(emoji_inputs, role_inputs):
        if emoji and role_input:
            role = find_role(role_input)
            if role:
                emoji_role_pairs.append((emoji, role))
            else:
                await interaction.response.send_message(f"❌ Could not find role: `{role_input}`. Please check the role name, ID, or mention.", ephemeral=True)
                return
    
    if not emoji_role_pairs:
        await interaction.response.send_message("❌ You must provide at least one emoji-role pair.", ephemeral=True)
        return
    
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Create clean embed with only the context (bold and bigger)
    embed = discord.Embed(
        description=f"**{context}**",  # Make text bold and bigger
        color=embed_color
    )
    
    # Send message to specified channel
    await interaction.response.send_message(f"✅ Reaction role message created in {channel.mention}!", ephemeral=True)
    message = await channel.send(embed=embed)
    
    # Store reaction role mapping
    role_mapping = {}
    for emoji, role in emoji_role_pairs:
        role_mapping[emoji] = role.id
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await interaction.followup.send(f"⚠️ Could not add reaction {emoji}. Make sure it's a valid emoji.", ephemeral=True)
    
    # Store in reaction roles system
    reaction_roles[message.id] = role_mapping

@bot.tree.command(name="namelock", description="Lock a user's nickname")
@app_commands.describe(user="User to namelock", nickname="Nickname to lock them to")
async def slash_namelock(interaction: discord.Interaction, user: discord.Member, nickname: str):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.manage_nicknames and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ You need Manage Nicknames permission to use this command.", ephemeral=True)
        return
    
    namelocked_users[user.id] = nickname
    
    try:
        await user.edit(nick=nickname)
        await interaction.response.send_message(f"✅ {user.mention} has been namelocked to **{nickname}**")
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ I don't have permission to change {user.mention}'s nickname.")

@bot.tree.command(name="unnamelock", description="Remove namelock from a user")
@app_commands.describe(user="User to remove namelock from")
async def slash_unnamelock(interaction: discord.Interaction, user: discord.Member):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.manage_nicknames and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ You need Manage Nicknames permission to use this command.", ephemeral=True)
        return
    
    if user.id in namelocked_users:
        del namelocked_users[user.id]
        await interaction.response.send_message(f"✅ Namelock removed from {user.mention}")
    else:
        await interaction.response.send_message(f"❌ {user.mention} is not namelocked.")

@bot.tree.command(name="block", description="Block a user from using bot functions")
@app_commands.describe(user="User to block")
async def slash_block(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != 776883692983156736:  # Bot owner only
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    blocked_users.add(user.id)
    await interaction.response.send_message(f"✅ {user.mention} has been blocked from using bot functions.")

@bot.tree.command(name="unblock", description="Unblock a user from using bot functions")
@app_commands.describe(user="User to unblock")
async def slash_unblock(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != 776883692983156736:  # Bot owner only
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if user.id in blocked_users:
        blocked_users.remove(user.id)
        await interaction.response.send_message(f"✅ {user.mention} has been unblocked.")
    else:
        await interaction.response.send_message(f"❌ {user.mention} is not blocked.")

@bot.tree.command(name="giveaway-host-role", description="Add or remove giveaway host roles")
@app_commands.describe(role="Role to add/remove", action="Add or remove the role")
@app_commands.choices(action=[
    app_commands.Choice(name="add", value="add"),
    app_commands.Choice(name="remove", value="remove")
])
async def slash_giveaway_host_role(interaction: discord.Interaction, role: discord.Role, action: str):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.administrator and interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = []
    
    if action == "add":
        if role.id not in giveaway_host_roles[guild_id]:
            giveaway_host_roles[guild_id].append(role.id)
            await interaction.response.send_message(f"✅ {role.mention} can now host giveaways.")
        else:
            await interaction.response.send_message(f"❌ {role.mention} is already a giveaway host role.")
    else:  # remove
        if role.id in giveaway_host_roles[guild_id]:
            giveaway_host_roles[guild_id].remove(role.id)
            await interaction.response.send_message(f"✅ {role.mention} can no longer host giveaways.")
        else:
            await interaction.response.send_message(f"❌ {role.mention} is not a giveaway host role.")

@bot.tree.command(name="stats", description="Show bot statistics")
@check_not_blocked()
async def slash_stats(interaction: discord.Interaction):
    uptime = format_uptime(time.time() - BOT_START_TIME)
    
    embed = discord.Embed(
        title="📊 Bot Statistics",
        color=discord.Color.green()
    )
    
    embed.add_field(name="Guilds", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Uptime", value=uptime, inline=True)
    
    embed.add_field(name="Sniped Messages", value=sum(len(msgs) if isinstance(msgs, list) else 1 for msgs in sniped_messages.values()), inline=True)
    embed.add_field(name="Active Giveaways", value=len(active_giveaways), inline=True)
    embed.add_field(name="Blocked Users", value=len(blocked_users), inline=True)
    
    embed.set_footer(text="Made with ❤ by Werrzzzy")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Add slash version of saywb
@bot.tree.command(name="saywb", description="Send a webhook message with optional color")
@app_commands.describe(
    message="Message to send",
    color="Color for the message (optional)"
)
async def slash_saywb(interaction: discord.Interaction, message: str, color: str = None):
    if is_user_blocked(interaction.user.id):
        await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        return
    
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need Manage Messages permission to use this command.", ephemeral=True)
        return
    
    try:
        webhook = await get_or_create_webhook(interaction.channel)
        
        embed_color = parse_color(color) if color else discord.Color.default()
        
        # Create embed with the message and color
        embed = discord.Embed(
            description=message,
            color=embed_color
        )
        
        await webhook.send(
            embed=embed,
            username=bot.user.display_name,
            avatar_url=bot.user.display_avatar.url
        )
        
        await interaction.response.send_message("✅ Message sent via webhook!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to create webhooks in this channel.", ephemeral=True)

# ===== PREFIX COMMANDS =====

# FIXED: Prefix snipe commands
@bot.command(aliases=['s'])
@not_blocked()
async def snipe(ctx, channel: discord.TextChannel = None):
    """Show the most recently deleted message in a channel"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel.")
        return
    
    message_data = sniped_messages[channel_id][0]  # Most recent
    
    # Get media URL and clean content
    media_url = get_media_url(message_data['content'], message_data['attachments'])
    display_content = clean_content_from_media(message_data['content'], media_url) if media_url else message_data['content']
    
    embed = discord.Embed(
        description=filter_content(display_content) if display_content else "*No text content*",
        color=discord.Color.blue(),
        timestamp=message_data['deleted_at']
    )
    
    embed.set_author(
        name=f"{message_data['author'].display_name}",
        icon_url=message_data['author'].display_avatar.url
    )
    
    # FIXED: Display media content as image/video
    if media_url:
        embed.set_image(url=media_url)
    
    embed.set_footer(text=f"Deleted in #{target_channel.name}")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['sp'])
@not_blocked()
async def snipelist(ctx, channel: discord.TextChannel = None, page: int = 1):
    """Show a paginated list of deleted messages with support for channels and threads"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel.")
        return
    
    messages = sniped_messages[channel_id]
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page number. Available pages: 1-{total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🗑️ Deleted Messages in #{target_channel.name}",
        color=discord.Color.red(),
        description=f"Page {page}/{total_pages} • Showing {len(page_messages)} messages"
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = filter_content(msg['content']) if msg['content'] else "*No text content*"
        truncated = truncate_content(content, 100)
        
        time_str = msg['deleted_at'].strftime("%H:%M:%S")
        embed.add_field(
            name=f"{i}. {msg['author'].display_name} • {time_str}",
            value=truncated,
            inline=False
        )
    
    embed.set_footer(text=f"Total: {len(messages)} messages stored")
    
    await ctx.send(embed=embed)

# FIXED: Snipe force command 
@bot.command(aliases=['spf', 'snipeforce', 'sf'])
@commands.has_permissions(manage_messages=True)
@not_blocked()
async def spforce(ctx, channel: discord.TextChannel = None, page: int = 1):
    """Show unfiltered deleted messages (moderator only)"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel.")
        return
    
    messages = sniped_messages[channel_id]
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page number. Available pages: 1-{total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔓 Unfiltered Deleted Messages in #{target_channel.name}",
        color=discord.Color.orange(),
        description=f"Page {page}/{total_pages} • Showing {len(page_messages)} messages (UNFILTERED)"
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = msg['content'] if msg['content'] else "*No text content*"  # No filtering
        truncated = truncate_content(content, 100)
        
        time_str = msg['deleted_at'].strftime("%H:%M:%S")
        embed.add_field(
            name=f"{i}. {msg['author'].display_name} • {time_str}",
            value=truncated,
            inline=False
        )
    
    embed.set_footer(text=f"Total: {len(messages)} messages stored • MODERATOR VIEW")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['spl'])
@not_blocked()
async def snipelinks(ctx, channel: discord.TextChannel = None, page: int = 1):
    """Show only deleted messages that contained links"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel.")
        return
    
    # Filter messages that contain links
    link_messages = [msg for msg in sniped_messages[channel_id] if has_links(msg['content'])]
    
    if not link_messages:
        await ctx.send("❌ No deleted messages with links found in this channel.")
        return
    
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page number. Available pages: 1-{total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = link_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔗 Deleted Links in #{target_channel.name}",
        color=discord.Color.purple(),
        description=f"Page {page}/{total_pages} • Showing {len(page_messages)} messages with links"
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = filter_content(msg['content']) if msg['content'] else "*No text content*"
        truncated = truncate_content(content, 100)
        
        time_str = msg['deleted_at'].strftime("%H:%M:%S")
        embed.add_field(
            name=f"{i}. {msg['author'].display_name} • {time_str}",
            value=truncated,
            inline=False
        )
    
    embed.set_footer(text=f"Total: {len(link_messages)} messages with links")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['es'])
@not_blocked()
async def editsnipe(ctx, channel: discord.TextChannel = None):
    """Show the most recently edited message in a channel"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await ctx.send("❌ No edited messages found in this channel.")
        return
    
    edit_data = edited_messages[channel_id][0]  # Most recent
    
    embed = discord.Embed(
        color=discord.Color.orange(),
        timestamp=edit_data['edited_at']
    )
    
    embed.set_author(
        name=f"{edit_data['author'].display_name}",
        icon_url=edit_data['author'].display_avatar.url
    )
    
    embed.add_field(
        name="Before",
        value=filter_content(edit_data['before_content']) if edit_data['before_content'] else "*No content*",
        inline=False
    )
    
    embed.add_field(
        name="After",
        value=filter_content(edit_data['after_content']) if edit_data['after_content'] else "*No content*",
        inline=False
    )
    
    embed.set_footer(text=f"Edited in #{target_channel.name}")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['nl'])
@commands.has_permissions(manage_nicknames=True)
@not_blocked()
async def namelock(ctx, user: discord.Member, *, nickname):
    """Lock a user's nickname"""
    namelocked_users[user.id] = nickname
    
    try:
        await user.edit(nick=nickname)
        await ctx.send(f"✅ {user.mention} has been namelocked to **{nickname}**")
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to change {user.mention}'s nickname.")

@bot.command()
@commands.has_permissions(manage_nicknames=True)
@not_blocked()
async def unl(ctx, user: discord.Member):
    """Remove namelock from a user (unl command)"""
    if user.id in namelocked_users:
        del namelocked_users[user.id]
        await ctx.send(f"✅ Namelock removed from {user.mention}")
    else:
        await ctx.send(f"❌ {user.mention} is not namelocked.")

@bot.command(aliases=['re'])
@commands.has_permissions(manage_nicknames=True)
@not_blocked()
async def rename(ctx, user: discord.Member, *, nickname):
    """Change a user's nickname"""
    try:
        await user.edit(nick=nickname)
        await ctx.send(f"✅ Changed {user.mention}'s nickname to **{nickname}**")
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to change {user.mention}'s nickname.")

@bot.command()
@not_blocked()
async def say(ctx, *, message):
    """Send a message as the bot"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ You need Manage Messages permission to use this command.")
        return
    
    await ctx.message.delete()
    await ctx.send(message)

@bot.command()
@not_blocked()
async def saywb(ctx, *, args):
    """Send a message via webhook with optional color: ,saywb [message] [color]"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ You need Manage Messages permission to use this command.")
        return
    
    # Parse message and color
    parts = args.rsplit(' ', 1)  # Split from the right to get the last word as potential color
    
    if len(parts) == 2:
        message, potential_color = parts
        # Check if the last part is a valid color
        test_color = parse_color(potential_color)
        if test_color != discord.Color.default() or potential_color.lower() in ['red', 'green', 'blue', 'yellow', 'purple', 'orange', 'pink', 'black', 'white', 'gray', 'grey', 'cyan', 'magenta', 'gold', 'silver', 'golden']:
            color = test_color
        else:
            # Not a color, treat entire args as message
            message = args
            color = discord.Color.default()
    else:
        message = args
        color = discord.Color.default()
    
    try:
        webhook = await get_or_create_webhook(ctx.channel)
        
        # Create embed with the message and color
        embed = discord.Embed(
            description=message,
            color=color
        )
        
        await webhook.send(
            embed=embed,
            username=bot.user.display_name,
            avatar_url=bot.user.display_avatar.url
        )
        await ctx.message.delete()
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to create webhooks in this channel.")

@bot.command()
@not_blocked()
async def mess(ctx, search_term: str, *, message):
    """DM a user globally across all servers"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ You need Manage Messages permission to use this command.")
        return
    
    # Find user globally across all servers
    user = find_user_globally(search_term)
    
    if not user:
        await ctx.send(f"❌ Could not find user matching '{search_term}' in any server.")
        return
    
    try:
        await user.send(f"**Message from {ctx.author.display_name} in {ctx.guild.name}:**\n{message}")
        await ctx.send(f"✅ Message sent to {user.display_name}")
    except discord.Forbidden:
        await ctx.send(f"❌ Could not send DM to {user.display_name}. They might have DMs disabled.")

@bot.command()
@commands.has_permissions(manage_roles=True)
@not_blocked()
async def role(ctx, user: discord.Member, *, role_name):
    """Add a role to a user"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"❌ Role '{role_name}' not found.")
        return
    
    if role in user.roles:
        await ctx.send(f"❌ {user.mention} already has the {role.mention} role.")
        return
    
    try:
        await user.add_roles(role)
        await ctx.send(f"✅ Added {role.mention} to {user.mention}")
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to add this role.")

@bot.command(aliases=['nli'])
@commands.has_permissions(administrator=True)
@not_blocked()
async def namelockimmune(ctx, user: discord.Member):
    """Make a user immune to namelock"""
    namelock_immune_users.add(user.id)
    await ctx.send(f"✅ {user.mention} is now immune to namelock.")

@bot.command()
@commands.check(lambda ctx: ctx.author.id == 776883692983156736)
@not_blocked()
async def block(ctx, user: discord.User):
    """Block a user from using bot functions (bot owner only)"""
    blocked_users.add(user.id)
    await ctx.send(f"✅ {user.mention} has been blocked from using bot functions.")

@bot.command()
@commands.check(lambda ctx: ctx.author.id == 776883692983156736)
@not_blocked()
async def manage(ctx):
    """Show bot management panel (bot owner only)"""
    view = ManagePaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

@bot.command()
@not_blocked()
async def help(ctx):
    """Show help information"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

@bot.command()
@not_blocked()
async def stats(ctx):
    """Show bot statistics"""
    uptime = format_uptime(time.time() - BOT_START_TIME)
    
    embed = discord.Embed(
        title="📊 Bot Statistics",
        color=discord.Color.green()
    )
    
    embed.add_field(name="Guilds", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Uptime", value=uptime, inline=True)
    
    embed.add_field(name="Sniped Messages", value=sum(len(msgs) if isinstance(msgs, list) else 1 for msgs in sniped_messages.values()), inline=True)
    embed.add_field(name="Active Giveaways", value=len(active_giveaways), inline=True)
    embed.add_field(name="Blocked Users", value=len(blocked_users), inline=True)
    
    embed.set_footer(text="Made with ❤ by Werrzzzy")
    
    await ctx.send(embed=embed)

@bot.command(aliases=['gw'])
@not_blocked()
async def giveaway_reroll(ctx, message_id: int):
    """Reroll a giveaway winner"""
    if not can_host_giveaway(ctx.author):
        await ctx.send("❌ You don't have permission to reroll giveaways.")
        return
    
    if message_id not in active_giveaways:
        await ctx.send("❌ Giveaway not found or already ended.")
        return
    
    try:
        message = await ctx.fetch_message(message_id)
        await end_giveaway(message_id)
        await ctx.send("✅ Giveaway rerolled!")
    except discord.NotFound:
        await ctx.send("❌ Could not find the giveaway message.")

@bot.command()
@commands.has_permissions(manage_roles=True)
@not_blocked()
async def create(ctx, *, args):
    """Create reaction role message: ,create [text] emoji @role [color]"""
    parts = args.split()
    
    if len(parts) < 3:
        await ctx.send("❌ Usage: `,create [text] emoji @role [color]`\nExample: `,create Get roles here! 🦝 @Member red`")
        return
    
    # Parse multiple emoji-role pairs
    role_mapping = {}
    color = discord.Color.default()
    
    # Find the text part (everything before the first emoji)
    text_parts = []
    emoji_start = 0
    
    for i, part in enumerate(parts):
        # Check if this part is an emoji (either unicode emoji or custom emoji format)
        if (len(part) == 1 and ord(part) > 127) or part.startswith('<:') or part.startswith('<a:'):
            emoji_start = i
            break
        text_parts.append(part)
    
    if not text_parts:
        text = "React to get roles!"
    else:
        text = ' '.join(text_parts)
    
    # Parse emoji-role pairs
    remaining_parts = parts[emoji_start:]
    i = 0
    while i < len(remaining_parts) - 1:
        emoji_str = remaining_parts[i]
        role_str = remaining_parts[i + 1]
        
        # Check if this is a role mention
        if role_str.startswith('<@&') and role_str.endswith('>'):
            role_id = int(role_str[3:-1])
            role = ctx.guild.get_role(role_id)
            
            if role:
                role_mapping[emoji_str] = role.id
                i += 2
            else:
                await ctx.send(f"❌ Role {role_str} not found.")
                return
        else:
            # Check if this is a color
            color = parse_color(role_str)
            i += 1
    
    if not role_mapping:
        await ctx.send("❌ No valid emoji-role pairs found.\nExample: `,create Get roles! 🦝 @Member 🎮 @Gamer red`")
        return
    
    # Create embed
    embed = discord.Embed(
        title="🎭 Reaction Roles",
        description=text,
        color=color
    )
    
    role_list = []
    for emoji, role_id in role_mapping.items():
        role = ctx.guild.get_role(role_id)
        if role:
            role_list.append(f"{emoji} - {role.mention}")
    
    embed.add_field(name="Available Roles", value='\n'.join(role_list), inline=False)
    embed.set_footer(text="React to get/remove roles!")
    
    # Send message and add reactions
    message = await ctx.send(embed=embed)
    
    # Store reaction role mapping
    reaction_roles[message.id] = role_mapping
    
    # Add reactions
    for emoji in role_mapping.keys():
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await ctx.send(f"❌ Could not add reaction {emoji}. Make sure it's a valid emoji.")

# Background task for giveaway checking
@tasks.loop(seconds=30)
async def giveaway_checker():
    """Check for ended giveaways"""
    current_time = datetime.utcnow()
    ended_giveaways = []
    
    for message_id, giveaway_data in active_giveaways.items():
        if current_time >= giveaway_data['end_time']:
            ended_giveaways.append(message_id)
    
    for message_id in ended_giveaways:
        await end_giveaway(message_id)

async def end_giveaway(message_id):
    """End a giveaway and pick winners"""
    if message_id not in active_giveaways:
        return
    
    giveaway_data = active_giveaways[message_id]
    
    try:
        guild = bot.get_guild(giveaway_data['guild_id'])
        channel = guild.get_channel(giveaway_data['channel_id'])
        message = await channel.fetch_message(message_id)
        
        # Get reactions
        for reaction in message.reactions:
            if str(reaction.emoji) == "🎉":
                participants = []
                async for user in reaction.users():
                    if not user.bot:
                        member = guild.get_member(user.id)
                        if member:
                            # Check requirements
                            meets_requirements, _ = check_giveaway_requirements(member, giveaway_data['requirements'])
                            if meets_requirements:
                                participants.append(user)
                
                if not participants:
                    embed = discord.Embed(
                        title="🎉 Giveaway Ended",
                        description=f"**Prize:** {giveaway_data['prize']}\n**Winners:** No valid participants",
                        color=discord.Color.red()
                    )
                    await channel.send(embed=embed)
                else:
                    # Pick winners
                    winners_count = min(giveaway_data['winners'], len(participants))
                    winners = random.sample(participants, winners_count)
                    
                    winner_mentions = [winner.mention for winner in winners]
                    
                    embed = discord.Embed(
                        title="🎉 Giveaway Ended",
                        description=f"**Prize:** {giveaway_data['prize']}\n**Winners:** {', '.join(winner_mentions)}",
                        color=discord.Color.gold()
                    )
                    
                    await channel.send(f"🎉 Congratulations {', '.join(winner_mentions)}! You won **{giveaway_data['prize']}**!")
                    await channel.send(embed=embed)
                
                break
        
        # Remove from active giveaways
        del active_giveaways[message_id]
        
    except Exception as e:
        print(f"Error ending giveaway {message_id}: {e}")
        # Still remove from active giveaways to prevent repeated attempts
        if message_id in active_giveaways:
            del active_giveaways[message_id]

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument. Use `,help` for command usage.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send(f"❌ Invalid argument. Use `,help` for command usage.")
    elif isinstance(error, commands.CheckFailure):
        # This catches the blocked user check
        if is_user_blocked(ctx.author.id):
            await ctx.send("❌ You are blocked from using bot functions.")
        else:
            await ctx.send("❌ You don't have permission to use this command.")
    else:
        print(f"Unhandled error: {error}")

# Error handling for slash commands
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        if is_user_blocked(interaction.user.id):
            await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
        print(f"Unhandled slash command error: {error}")

# Run the bot
if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("Error: DISCORD_BOT_TOKEN environment variable not set")
        exit(1)
    
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("Error: Invalid bot token")
    except Exception as e:
        print(f"Error starting bot: {e}")
