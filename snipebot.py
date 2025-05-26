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

# Giveaway View with Join and List buttons
class GiveawayView(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__(timeout=None)
        self.giveaway_id = giveaway_id
    
    @discord.ui.button(label="Join", style=discord.ButtonStyle.green, emoji="🎉")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_user_blocked(interaction.user.id):
            await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
            return
        
        if self.giveaway_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway is no longer active.", ephemeral=True)
            return
        
        giveaway = active_giveaways[self.giveaway_id]
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
        
        if self.giveaway_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway is no longer active.", ephemeral=True)
            return
        
        giveaway = active_giveaways[self.giveaway_id]
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

# Help Pagination View
class HelpPaginationView(discord.ui.View):
    def __init__(self, timeout=300):
        super().__init__(timeout=timeout)
        self.current_page = 0
        self.pages = [
            {
                "title": "📜 FACTSY Commands - Page 1",
                "fields": [
                    ("**Message Tracking**", "`,snipe` `,s [1-100]` - Show deleted message by number\n`,editsnipe` `,es` - Show last edited message\n`,sp [channel] [page]` - List all deleted messages\n`,spforce` `,spf` - Show censored messages\n`,spl [channel] [page]` - Show deleted links only", False),
                    ("**Moderation**", "`,namelock` `,nl` - Lock user's nickname\n`,unl` - Unlock user's nickname\n`,rename` `,re` - Change user's nickname\n`,say` - Send normal message\n`,saywb` `/saywb` - Send embed message", False)
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
                    ("**Reaction Roles**", "`,create` - Create reaction role message\n`/create` - Clean reaction roles with 1-6 options", False),
                    ("**Bot Owner**", "`,manage` - Bot management panel\n`/unblock` - Unblock user from bot\n`/ping` - Show bot latency", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 4",
                "fields": [
                    ("**Info**", "All commands support both prefix (,) and slash (/) versions\nModerators can use most commands\nBlocked users cannot use any bot functions", False),
                    ("**Usage Examples**", "`,s 5` - Show 5th deleted message\n`/saywb #general My Title My Description red` - Send embed\n`,gw 123456789` - Reroll giveaway", False)
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
        'jump_url': message.jump_url,
        'is_censored': is_offensive_content(message.content)  # Track if message was censored
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
    """Handle namelock enforcement"""
    # Check if user is namelocked and their nickname changed
    if after.id in namelocked_users:
        locked_nickname = namelocked_users[after.id]
        if after.display_name != locked_nickname:
            try:
                await after.edit(nick=locked_nickname, reason="Namelock enforcement")
            except discord.Forbidden:
                pass

@bot.event
async def on_message(message):
    """Count user messages and process commands"""
    if message.author.bot:
        return
    
    # Increment message count for the user
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    # Process commands
    await bot.process_commands(message)

# Background task to check giveaway endings
@tasks.loop(minutes=1)
async def giveaway_checker():
    """Check for ended giveaways every minute"""
    current_time = datetime.utcnow()
    ended_giveaways = []
    
    for message_id, giveaway_data in active_giveaways.items():
        if current_time >= giveaway_data['end_time']:
            ended_giveaways.append(message_id)
    
    for message_id in ended_giveaways:
        await end_giveaway(message_id)

async def end_giveaway(message_id):
    """End a giveaway and select winners"""
    if message_id not in active_giveaways:
        return
    
    giveaway_data = active_giveaways[message_id]
    channel = bot.get_channel(giveaway_data['channel_id'])
    
    if not channel:
        del active_giveaways[message_id]
        return
    
    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        del active_giveaways[message_id]
        return
    
    participants = giveaway_data['participants']
    winners_count = giveaway_data['winners']
    
    if not participants:
        # No participants
        embed = discord.Embed(
            title="🎉 Giveaway Ended",
            description=f"**Prize:** {giveaway_data['prize']}\n**Winners:** No participants",
            color=discord.Color.red()
        )
        embed.set_footer(text="Hosted by " + giveaway_data['host_name'])
        
        await message.edit(embed=embed, view=None)
        del active_giveaways[message_id]
        return
    
    # Select winners
    winners = random.sample(participants, min(winners_count, len(participants)))
    
    # Create winner announcement
    winner_mentions = []
    for winner_id in winners:
        user = bot.get_user(winner_id)
        if user:
            winner_mentions.append(user.mention)
        else:
            winner_mentions.append(f"<@{winner_id}>")
    
    embed = discord.Embed(
        title="🎉 Giveaway Ended",
        description=f"**Prize:** {giveaway_data['prize']}\n**Winner{'s' if len(winners) > 1 else ''}:** {', '.join(winner_mentions)}",
        color=discord.Color.gold()
    )
    embed.add_field(name="Participants", value=str(len(participants)), inline=True)
    embed.set_footer(text="Hosted by " + giveaway_data['host_name'])
    
    await message.edit(embed=embed, view=None)
    
    # Send congratulations message
    congrats_message = f"🎉 Congratulations {', '.join(winner_mentions)}! You won **{giveaway_data['prize']}**!"
    await channel.send(congrats_message)
    
    # Remove from active giveaways
    del active_giveaways[message_id]

# FIXED: Enhanced snipe command with number support (,s 1-100)
@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe(ctx, number: int = 1):
    """Show deleted message by number (1 = most recent, 2 = second most recent, etc.)"""
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel.")
        return
    
    messages = sniped_messages[channel_id]
    
    # Validate number range
    if number < 1 or number > len(messages):
        await ctx.send(f"❌ Invalid number. Available range: 1-{len(messages)}")
        return
    
    # Get the message (number-1 because list is 0-indexed)
    message_data = messages[number - 1]
    
    # Check if message should be filtered and user is not moderator
    if message_data.get('is_censored', False) and not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ This message was censored and cannot be displayed.")
        return
    
    # Get media URL and clean content
    media_url = get_media_url(message_data['content'], message_data['attachments'])
    cleaned_content = clean_content_from_media(message_data['content'], media_url)
    
    # Create simplified embed
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.blue()
    )
    
    # Add content if available
    if cleaned_content:
        embed.description = cleaned_content
    
    # Add user mention
    embed.add_field(name="User", value=message_data['author'].mention, inline=True)
    
    # Set media as image if available
    if media_url:
        embed.set_image(url=media_url)
    
    await ctx.send(embed=embed)

@bot.command(name='editsnipe', aliases=['es'])
@not_blocked()
async def editsnipe(ctx):
    """Show last edited message"""
    channel_id = ctx.channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await ctx.send("❌ No edited messages found in this channel.")
        return
    
    edit_data = edited_messages[channel_id][0]  # Most recent
    
    embed = discord.Embed(
        title="📝 Edited Message",
        color=discord.Color.orange()
    )
    
    embed.add_field(name="Before", value=edit_data['before_content'][:1024] if edit_data['before_content'] else "*No content*", inline=False)
    embed.add_field(name="After", value=edit_data['after_content'][:1024] if edit_data['after_content'] else "*No content*", inline=False)
    embed.add_field(name="User", value=edit_data['author'].mention, inline=True)
    
    timestamp = edit_data['edited_at'].strftime("%m/%d/%Y %H:%M:%S")
    embed.set_footer(text=f"Edited at {timestamp}")
    
    await ctx.send(embed=embed)

# FIXED: ,sp command - shows all deleted messages (not censored)
@bot.command(name='sp')
@not_blocked()
async def snipe_list(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List all deleted messages (non-censored only)"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send(f"❌ No deleted messages found in {target_channel.mention}.")
        return
    
    # Filter out censored messages for regular users
    messages = sniped_messages[channel_id]
    if not ctx.author.guild_permissions.manage_messages:
        messages = [msg for msg in messages if not msg.get('is_censored', False)]
    
    if not messages:
        await ctx.send(f"❌ No non-censored deleted messages found in {target_channel.mention}.")
        return
    
    # Create pagination
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page number. Available pages: 1-{total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(messages))
    page_messages = messages[start_idx:end_idx]
    
    embeds = []
    for p in range(total_pages):
        p_start = p * MESSAGES_PER_PAGE
        p_end = min(p_start + MESSAGES_PER_PAGE, len(messages))
        p_messages = messages[p_start:p_end]
        
        embed = discord.Embed(
            title=f"📜 Deleted Messages - {target_channel.name}",
            color=discord.Color.blue()
        )
        
        message_list = []
        for i, msg in enumerate(p_messages, start=p_start + 1):
            content = truncate_content(msg['content'])
            message_list.append(f"{i}. **{msg['author'].display_name}**: {content}")
        
        embed.description = "\n".join(message_list)
        embed.set_footer(text=f"Page {p + 1} of {total_pages} | Use ,s [number] to view full message")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[page-1], view=view)

# FIXED: ,spf command - shows only censored messages (moderator only)
@bot.command(name='spforce', aliases=['spf'])
@not_blocked()
@commands.has_permissions(manage_messages=True)
async def snipe_force(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List censored deleted messages (moderator only)"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send(f"❌ No deleted messages found in {target_channel.mention}.")
        return
    
    # Filter only censored messages
    messages = [msg for msg in sniped_messages[channel_id] if msg.get('is_censored', False)]
    
    if not messages:
        await ctx.send(f"❌ No censored deleted messages found in {target_channel.mention}.")
        return
    
    # Create pagination
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page number. Available pages: 1-{total_pages}")
        return
    
    embeds = []
    for p in range(total_pages):
        p_start = p * MESSAGES_PER_PAGE
        p_end = min(p_start + MESSAGES_PER_PAGE, len(messages))
        p_messages = messages[p_start:p_end]
        
        embed = discord.Embed(
            title=f"🔞 Censored Messages - {target_channel.name}",
            color=discord.Color.red()
        )
        
        message_list = []
        for i, msg in enumerate(p_messages, start=p_start + 1):
            filtered_content = filter_content(msg['content'])
            content = truncate_content(filtered_content)
            message_list.append(f"{i}. **{msg['author'].display_name}**: {content}")
        
        embed.description = "\n".join(message_list)
        embed.set_footer(text=f"Page {p + 1} of {total_pages} | Moderator Only")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[page-1], view=view)

# FIXED: ,spl command - shows only messages with links
@bot.command(name='spl')
@not_blocked()
async def snipe_links(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List deleted messages that contained links"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send(f"❌ No deleted messages found in {target_channel.mention}.")
        return
    
    # Filter messages with links (non-censored for regular users)
    messages = sniped_messages[channel_id]
    if not ctx.author.guild_permissions.manage_messages:
        messages = [msg for msg in messages if not msg.get('is_censored', False)]
    
    # Filter only messages with links
    link_messages = [msg for msg in messages if has_links(msg['content']) or msg['attachments']]
    
    if not link_messages:
        await ctx.send(f"❌ No deleted messages with links found in {target_channel.mention}.")
        return
    
    # Create pagination
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page number. Available pages: 1-{total_pages}")
        return
    
    embeds = []
    for p in range(total_pages):
        p_start = p * MESSAGES_PER_PAGE
        p_end = min(p_start + MESSAGES_PER_PAGE, len(link_messages))
        p_messages = link_messages[p_start:p_end]
        
        embed = discord.Embed(
            title=f"🔗 Deleted Links - {target_channel.name}",
            color=discord.Color.green()
        )
        
        message_list = []
        for i, msg in enumerate(p_messages, start=p_start + 1):
            content = truncate_content(msg['content'])
            message_list.append(f"{i}. **{msg['author'].display_name}**: {content}")
        
        embed.description = "\n".join(message_list)
        embed.set_footer(text=f"Page {p + 1} of {total_pages} | Links Only")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[page-1], view=view)

@bot.command(name='namelock', aliases=['nl'])
@not_blocked()
@commands.has_permissions(manage_nicknames=True)
async def namelock(ctx, member: discord.Member, *, nickname):
    """Lock a user's nickname"""
    # Check if user is immune to namelock
    if member.id in namelock_immune_users:
        await ctx.send(f"❌ {member.mention} is immune to namelock.")
        return
    
    if member.guild_permissions.administrator and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Cannot namelock administrators.")
        return
    
    try:
        await member.edit(nick=nickname, reason=f"Namelocked by {ctx.author}")
        namelocked_users[member.id] = nickname
        await ctx.send(f"✅ {member.mention} has been namelocked to **{nickname}**")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname.")

@bot.command(name='unl')
@not_blocked()
@commands.has_permissions(manage_nicknames=True)
async def unlock_name(ctx, member: discord.Member):
    """Unlock a user's nickname"""
    if member.id not in namelocked_users:
        await ctx.send(f"❌ {member.mention} is not namelocked.")
        return
    
    try:
        del namelocked_users[member.id]
        await ctx.send(f"✅ {member.mention} has been unlocked from namelock.")
    except Exception as e:
        await ctx.send(f"❌ Error unlocking user: {e}")

@bot.command(name='rename', aliases=['re'])
@not_blocked()
@commands.has_permissions(manage_nicknames=True)
async def rename(ctx, member: discord.Member, *, new_name):
    """Change a user's nickname"""
    if member.guild_permissions.administrator and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Cannot rename administrators.")
        return
    
    try:
        old_name = member.display_name
        await member.edit(nick=new_name, reason=f"Renamed by {ctx.author}")
        await ctx.send(f"✅ Renamed **{old_name}** to **{new_name}**")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname.")

@bot.command(name='say')
@not_blocked()
@commands.has_permissions(manage_messages=True)
async def say(ctx, *, message):
    """Send a message as the bot"""
    await ctx.message.delete()
    await ctx.send(message)

@bot.command(name='saywb')
@not_blocked()
@commands.has_permissions(manage_messages=True)
async def say_webhook(ctx, *, args):
    """Send a webhook message with color - Usage: ,saywb <message> [color]"""
    parts = args.rsplit(' ', 1)
    if len(parts) == 2 and parts[1] in ['red', 'green', 'blue', 'yellow', 'purple', 'orange', 'pink', 'black', 'white', 'gray', 'grey', 'cyan', 'magenta', 'gold', 'silver', 'golden'] or (parts[1].startswith('#') and len(parts[1]) in [4, 7]):
        message = parts[0]
        color_str = parts[1]
    else:
        message = args
        color_str = 'blue'
    
    try:
        webhook = await get_or_create_webhook(ctx.channel)
        await webhook.send(
            content=message,
            username=ctx.author.display_name,
            avatar_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        await ctx.message.delete()
    except Exception as e:
        await ctx.send(f"❌ Error sending webhook message: {e}")

# ENHANCED: /saywb slash command with embed support
@bot.tree.command(name="saywb", description="Send an embed message")
@check_not_blocked()
@app_commands.describe(
    channel="Channel to send the message to (optional)",
    title="Title of the embed",
    description="Description of the embed", 
    color="Color of the embed (optional)"
)
async def slash_saywb(
    interaction: discord.Interaction, 
    title: str, 
    description: str,
    channel: Optional[discord.TextChannel] = None,
    color: Optional[str] = None
):
    """Send embed message like Discohook"""
    # Check permissions
    if not interaction.user.guild_permissions.manage_messages and not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ You need Manage Messages permission to use this command.", ephemeral=True)
        return
    
    target_channel = channel or interaction.channel
    embed_color = parse_color(color) if color else discord.Color.blue()
    
    # Create embed (no webhook needed, just clean embed)
    embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color
    )
    
    try:
        await target_channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Embed sent to {target_channel.mention}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error sending embed: {e}", ephemeral=True)

# FIXED: /ping command
@bot.tree.command(name="ping", description="Show bot latency")
@check_not_blocked()
async def slash_ping(interaction: discord.Interaction):
    """Show bot latency"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot Latency: **{latency}ms**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.command(name='block')
@not_blocked()
async def block_user(ctx, *, user_query):
    """Block a user from using bot functions (Bot owner only)"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    # Try to find user by ID first
    try:
        user_id = int(user_query)
        user = bot.get_user(user_id)
    except ValueError:
        # Search by name
        user = find_user_globally(user_query)
    
    if not user:
        await ctx.send("❌ User not found.")
        return
    
    if user.id in blocked_users:
        await ctx.send(f"❌ {user.name} is already blocked.")
        return
    
    blocked_users.add(user.id)
    await ctx.send(f"✅ {user.name} has been blocked from using bot functions.")

@bot.tree.command(name="unblock", description="Unblock a user from bot functions")
@check_not_blocked()
async def slash_unblock(interaction: discord.Interaction, user: discord.User):
    """Unblock a user from using bot functions (Bot owner only)"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if user.id not in blocked_users:
        await interaction.response.send_message(f"❌ {user.name} is not blocked.", ephemeral=True)
        return
    
    blocked_users.remove(user.id)
    await interaction.response.send_message(f"✅ {user.name} has been unblocked.", ephemeral=True)

@bot.command(name='mess')
@not_blocked()
async def message_user(ctx, user_query, *, message):
    """Send a DM to a user globally (Bot owner only)"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    # Try to find user by ID first
    try:
        user_id = int(user_query)
        user = bot.get_user(user_id)
    except ValueError:
        # Search by name
        user = find_user_globally(user_query)
    
    if not user:
        await ctx.send("❌ User not found.")
        return
    
    try:
        await user.send(message)
        await ctx.send(f"✅ Message sent to {user.name}")
    except discord.Forbidden:
        await ctx.send(f"❌ Cannot send DM to {user.name} (DMs disabled)")
    except Exception as e:
        await ctx.send(f"❌ Error sending message: {e}")

@bot.command(name='role')
@not_blocked()
@commands.has_permissions(manage_roles=True)
async def add_role(ctx, member: discord.Member, *, role_name):
    """Add a role to a user"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"❌ Role '{role_name}' not found.")
        return
    
    if role in member.roles:
        await ctx.send(f"❌ {member.mention} already has the {role.name} role.")
        return
    
    try:
        await member.add_roles(role, reason=f"Added by {ctx.author}")
        await ctx.send(f"✅ Added {role.name} role to {member.mention}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to add that role.")

@bot.command(name='namelockimmune', aliases=['nli'])
@not_blocked()
async def namelock_immune(ctx, member: discord.Member):
    """Make a user immune to namelock (Bot owner only)"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    if member.id in namelock_immune_users:
        namelock_immune_users.remove(member.id)
        await ctx.send(f"✅ {member.mention} is no longer immune to namelock.")
    else:
        namelock_immune_users.add(member.id)
        await ctx.send(f"✅ {member.mention} is now immune to namelock.")

@bot.command(name='gw')
@not_blocked()
@commands.has_permissions(manage_messages=True)
async def reroll_giveaway(ctx, message_id: int):
    """Reroll a giveaway winner"""
    if message_id not in active_giveaways:
        await ctx.send("❌ Giveaway not found or already ended.")
        return
    
    giveaway_data = active_giveaways[message_id]
    participants = giveaway_data['participants']
    
    if not participants:
        await ctx.send("❌ No participants to reroll.")
        return
    
    # Select new winner
    new_winner_id = random.choice(participants)
    new_winner = bot.get_user(new_winner_id)
    
    if new_winner:
        await ctx.send(f"🎉 New winner: {new_winner.mention} for **{giveaway_data['prize']}**!")
    else:
        await ctx.send(f"🎉 New winner: <@{new_winner_id}> for **{giveaway_data['prize']}**!")

@bot.tree.command(name="giveaway", description="Create an advanced giveaway")
@check_not_blocked()
@app_commands.describe(
    prize="What to give away",
    duration="Duration (e.g., 1h, 30m, 2d)",
    winners="Number of winners (default: 1)",
    required_messages="Minimum messages required to join",
    time_in_server="Time in server required (e.g., 1d, 2w)",
    required_role="Role required to join",
    blacklisted_role="Role that cannot join"
)
async def slash_giveaway(
    interaction: discord.Interaction,
    prize: str,
    duration: str,
    winners: int = 1,
    required_messages: Optional[int] = None,
    time_in_server: Optional[str] = None,
    required_role: Optional[str] = None,
    blacklisted_role: Optional[str] = None
):
    """Create an advanced giveaway with requirements"""
    # Check if user can host giveaways
    if not can_host_giveaway(interaction.user) and not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ You don't have permission to host giveaways.", ephemeral=True)
        return
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        await interaction.response.send_message("❌ Invalid duration format. Use format like: 1h, 30m, 2d", ephemeral=True)
        return
    
    if duration_seconds < 60:  # Minimum 1 minute
        await interaction.response.send_message("❌ Giveaway duration must be at least 1 minute.", ephemeral=True)
        return
    
    if winners < 1 or winners > 10:
        await interaction.response.send_message("❌ Number of winners must be between 1 and 10.", ephemeral=True)
        return
    
    # Parse requirements
    requirements = {}
    if required_messages:
        requirements['messages'] = required_messages
    if time_in_server:
        time_seconds = parse_time_string(time_in_server)
        if time_seconds > 0:
            requirements['time_in_server'] = time_seconds
    if required_role:
        requirements['required_role'] = required_role
    if blacklisted_role:
        requirements['blacklisted_role'] = blacklisted_role
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Create giveaway embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
        color=discord.Color.gold()
    )
    
    if requirements:
        req_text = []
        if 'messages' in requirements:
            req_text.append(f"• {requirements['messages']} messages in server")
        if 'time_in_server' in requirements:
            req_text.append(f"• {format_duration(requirements['time_in_server'])} in server")
        if 'required_role' in requirements:
            req_text.append(f"• Have role: {requirements['required_role']}")
        if 'blacklisted_role' in requirements:
            req_text.append(f"• Cannot have role: {requirements['blacklisted_role']}")
        
        embed.add_field(name="Requirements", value="\n".join(req_text), inline=False)
    
    embed.set_footer(text=f"Hosted by {interaction.user.display_name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
    
    # Create giveaway view
    view = GiveawayView(None)  # Will be set after message is sent
    
    await interaction.response.send_message(embed=embed, view=view)
    message = await interaction.original_response()
    
    # Update view with message ID
    view.giveaway_id = message.id
    
    # Store giveaway data
    active_giveaways[message.id] = {
        'prize': prize,
        'end_time': end_time,
        'winners': winners,
        'participants': [],
        'requirements': requirements,
        'host_id': interaction.user.id,
        'host_name': interaction.user.display_name,
        'channel_id': interaction.channel.id
    }

@bot.tree.command(name="giveaway-host-role", description="Set roles that can host giveaways")
@check_not_blocked()
@app_commands.describe(
    action="Add or remove role",
    role="Role to add/remove"
)
async def slash_giveaway_host_role(
    interaction: discord.Interaction,
    action: str,
    role: discord.Role
):
    """Set roles that can host giveaways (Admin only)"""
    if not interaction.user.guild_permissions.administrator and not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = []
    
    if action.lower() == "add":
        if role.id not in giveaway_host_roles[guild_id]:
            giveaway_host_roles[guild_id].append(role.id)
            await interaction.response.send_message(f"✅ {role.name} can now host giveaways.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {role.name} is already a giveaway host role.", ephemeral=True)
    
    elif action.lower() == "remove":
        if role.id in giveaway_host_roles[guild_id]:
            giveaway_host_roles[guild_id].remove(role.id)
            await interaction.response.send_message(f"✅ {role.name} can no longer host giveaways.", ephemeral=True)
        else:
            await interaction.response.send_message(f"❌ {role.name} is not a giveaway host role.", ephemeral=True)
    
    else:
        await interaction.response.send_message("❌ Action must be 'add' or 'remove'.", ephemeral=True)

@bot.command(name='create')
@not_blocked()
@commands.has_permissions(manage_roles=True)
async def create_reaction_roles(ctx, *, args):
    """Create reaction role message - Usage: ,create [title] [emoji1] [role1] [emoji2] [role2] ..."""
    parts = args.split()
    
    if len(parts) < 3:
        await ctx.send("❌ Usage: `,create [title] [emoji1] [role1] [emoji2] [role2] ...`")
        return
    
    title = parts[0]
    role_pairs = parts[1:]
    
    if len(role_pairs) % 2 != 0:
        await ctx.send("❌ Each emoji must have a corresponding role.")
        return
    
    # Parse emoji-role pairs
    role_mapping = {}
    embed_description = []
    
    for i in range(0, len(role_pairs), 2):
        emoji = role_pairs[i]
        role_name = role_pairs[i + 1]
        
        # Find role
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ Role '{role_name}' not found.")
            return
        
        role_mapping[emoji] = role.id
        embed_description.append(f"{emoji} - {role.mention}")
    
    # Create embed
    embed = discord.Embed(
        title=title,
        description="\n".join(embed_description),
        color=discord.Color.blue()
    )
    embed.set_footer(text="React to get roles!")
    
    # Send message and add reactions
    message = await ctx.send(embed=embed)
    
    for emoji in role_mapping.keys():
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await ctx.send(f"❌ Failed to add reaction {emoji}")
            return
    
    # Store reaction role data
    reaction_roles[message.id] = role_mapping
    await ctx.send("✅ Reaction roles created successfully!")

# FIXED: /create slash command with 1-6 emoji-role pairs
@bot.tree.command(name="create", description="Create reaction roles")
@check_not_blocked()
@app_commands.describe(
    channel="Channel to send the message",
    title="Title of the reaction role message",
    emoji1="First emoji", role1="First role",
    emoji2="Second emoji (optional)", role2="Second role (optional)",
    emoji3="Third emoji (optional)", role3="Third role (optional)",
    emoji4="Fourth emoji (optional)", role4="Fourth role (optional)",
    emoji5="Fifth emoji (optional)", role5="Fifth role (optional)",
    emoji6="Sixth emoji (optional)", role6="Sixth role (optional)"
)
async def slash_create_reaction_roles(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    title: str,
    emoji1: str, role1: discord.Role,
    emoji2: Optional[str] = None, role2: Optional[discord.Role] = None,
    emoji3: Optional[str] = None, role3: Optional[discord.Role] = None,
    emoji4: Optional[str] = None, role4: Optional[discord.Role] = None,
    emoji5: Optional[str] = None, role5: Optional[discord.Role] = None,
    emoji6: Optional[str] = None, role6: Optional[discord.Role] = None
):
    """Create reaction roles with 1-6 emoji-role pairs"""
    # Check permissions
    if not interaction.user.guild_permissions.manage_roles and not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ You need Manage Roles permission to use this command.", ephemeral=True)
        return
    
    # Build emoji-role pairs
    pairs = [(emoji1, role1)]
    
    if emoji2 and role2:
        pairs.append((emoji2, role2))
    if emoji3 and role3:
        pairs.append((emoji3, role3))
    if emoji4 and role4:
        pairs.append((emoji4, role4))
    if emoji5 and role5:
        pairs.append((emoji5, role5))
    if emoji6 and role6:
        pairs.append((emoji6, role6))
    
    # Create role mapping and description
    role_mapping = {}
    embed_description = []
    
    for emoji, role in pairs:
        role_mapping[emoji] = role.id
        embed_description.append(f"{emoji} - {role.mention}")
    
    # Create embed
    embed = discord.Embed(
        title=title,
        description="\n".join(embed_description),
        color=discord.Color.blue()
    )
    embed.set_footer(text="React to get roles!")
    
    try:
        # Send message and add reactions
        message = await channel.send(embed=embed)
        
        for emoji in role_mapping.keys():
            await message.add_reaction(emoji)
        
        # Store reaction role data
        reaction_roles[message.id] = role_mapping
        
        await interaction.response.send_message(f"✅ Reaction roles created in {channel.mention}!", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error creating reaction roles: {e}", ephemeral=True)

@bot.command(name='help')
@not_blocked()
async def help_command(ctx):
    """Show help menu with pagination"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

@bot.command(name='manage')
@not_blocked()
async def manage_command(ctx):
    """Bot management panel (Bot owner only)"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    view = ManagePaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument provided.")
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"❌ Command on cooldown. Try again in {error.retry_after:.2f} seconds.")
    else:
        print(f"Unexpected error: {error}")

# Run the bot
if __name__ == "__main__":
    # Get token from environment variable
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("ERROR: DISCORD_BOT_TOKEN environment variable not found!")
        exit(1)
    
    bot.run(TOKEN)
