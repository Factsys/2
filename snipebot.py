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
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# NEW: Authorized users who can use all bot functions
authorized_users = set()

# Store custom prefixes: {guild_id: prefix}
custom_prefixes = {}

def get_prefix(bot, message):
    """Get custom prefix for guild or default"""
    if message.guild and message.guild.id in custom_prefixes:
        return custom_prefixes[message.guild.id]
    return ","

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
    
    words = []
    for word in content.split():
        if is_offensive_content(word):
            words.append('*' * len(word))
        else:
            words.append(word)
    
    return ' '.join(words)

# ENHANCED: Helper function to parse color with support for hex codes
def parse_color(color_str):
    """Parse color from hex string (e.g., #ff0000, ff0000, red) - ENHANCED with hex code support"""
    if not color_str:
        return discord.Color.default()
    
    # Remove # if present
    if color_str.startswith('#'):
        color_str = color_str[1:]
    
    # Color names mapping
    color_names = {
        'red': 0xff0000, 'green': 0x00ff00, 'blue': 0x0000ff, 'yellow': 0xffff00,
        'purple': 0x800080, 'orange': 0xffa500, 'pink': 0xffc0cb, 'black': 0x000000,
        'white': 0xffffff, 'gray': 0x808080, 'grey': 0x808080, 'cyan': 0x00ffff,
        'magenta': 0xff00ff, 'gold': 0xffd700, 'silver': 0xc0c0c0, 'golden': 0xffd700,
        'lime': 0x00ff00, 'navy': 0x000080, 'maroon': 0x800000, 'olive': 0x808000,
        'aqua': 0x00ffff, 'teal': 0x008080, 'fuchsia': 0xff00ff, 'brown': 0xa52a2a
    }
    
    # Check if it's a named color
    if color_str.lower() in color_names:
        return discord.Color(color_names[color_str.lower()])
    
    # Try to parse as hex code
    try:
        if len(color_str) == 6:
            # Full hex code (e.g., ff0000)
            return discord.Color(int(color_str, 16))
        elif len(color_str) == 3:
            # Short hex code (e.g., f00 -> ff0000)
            expanded = ''.join([c*2 for c in color_str])
            return discord.Color(int(expanded, 16))
    except ValueError:
        pass
    
    return discord.Color.default()

# ENHANCED: Helper function to parse time string with seconds support
def parse_time_string(time_str):
    """Parse time string and return seconds - now supports seconds"""
    if not time_str:
        return 0
    
    time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400, 'w': 604800}
    
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

# Smart user finder function
def find_user_by_name(guild, search_term):
    """Find user by partial name match"""
    if not guild:
        return None
    
    search_term = search_term.lower()
    
    for member in guild.members:
        if member.display_name.lower() == search_term or member.name.lower() == search_term:
            return member
    
    matches = []
    for member in guild.members:
        if search_term in member.display_name.lower() or search_term in member.name.lower():
            matches.append(member)
    
    if matches:
        names = [m.display_name.lower() for m in matches] + [m.name.lower() for m in matches]
        closest = difflib.get_close_matches(search_term, names, n=1, cutoff=0.3)
        if closest:
            closest_name = closest[0]
            for member in matches:
                if member.display_name.lower() == closest_name or member.name.lower() == closest_name:
                    return member
        return matches[0]
    
    return None

# Global user finder
def find_user_globally(search_term):
    """Find user across all servers the bot is in"""
    search_term = search_term.lower()
    
    for guild in bot.guilds:
        for member in guild.members:
            if member.display_name.lower() == search_term or member.name.lower() == search_term:
                return member
    
    matches = []
    for guild in bot.guilds:
        for member in guild.members:
            if search_term in member.display_name.lower() or search_term in member.name.lower():
                if member not in matches:
                    matches.append(member)
    
    if matches:
        names = [m.display_name.lower() for m in matches] + [m.name.lower() for m in matches]
        closest = difflib.get_close_matches(search_term, names, n=1, cutoff=0.3)
        if closest:
            closest_name = closest[0]
            for member in matches:
                if member.display_name.lower() == closest_name or member.name.lower() == closest_name:
                    return member
        return matches[0]
    
    return None

# Enable intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True
intents.reactions = True

# Initialize bot with dynamic prefix
bot = commands.Bot(command_prefix=get_prefix, intents=intents)
bot.remove_command('help')

# Storage dictionaries
sniped_messages = {}
edited_messages = {}
channel_webhooks = {}
namelocked_users = {}  # Format: {user_id: {'guild_id': guild_id, 'nickname': 'locked_nickname'}}
namelock_immune_users = set()
blocked_users = set()
active_giveaways = {}
user_message_counts = {}
giveaway_host_roles = {}
reaction_roles = {}

MAX_MESSAGES = 100
MESSAGES_PER_PAGE = 10

# Helper functions
def is_user_blocked(user_id):
    return user_id in blocked_users

def is_bot_owner(user_id):
    return user_id == BOT_OWNER_ID

# NEW: Check if user has permissions (owner or authorized)
def has_bot_permissions(user_id):
    return is_bot_owner(user_id) or user_id in authorized_users

# ADVANCED MEDIA TYPE DETECTION - FIXED AND ENHANCED
def detect_media_type(url):
    """Detect media type from URL with advanced detection"""
    if not url:
        return "unknown"
    
    url_lower = url.lower()
    
    # Image formats
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.svg']
    if any(ext in url_lower for ext in image_extensions):
        if '.gif' in url_lower:
            return "gif"
        return "image"
    
    # Video formats
    video_extensions = ['.mp4', '.mov', '.avi', '.webm', '.mkv', '.flv', '.wmv']
    if any(ext in url_lower for ext in video_extensions):
        return "video"
    
    # Audio formats
    audio_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a']
    if any(ext in url_lower for ext in audio_extensions):
        return "audio"
    
    # Platform-specific detection
    if 'tenor.com' in url_lower or 'tenor.co' in url_lower:
        return "tenor_gif"
    elif 'giphy.com' in url_lower:
        return "giphy_gif"
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return "youtube_video"
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return "twitter_media"
    elif 'instagram.com' in url_lower:
        return "instagram_media"
    elif 'tiktok.com' in url_lower:
        return "tiktok_video"
    elif 'reddit.com' in url_lower or 'redd.it' in url_lower:
        return "reddit_media"
    elif 'discord' in url_lower and ('cdn.discord' in url_lower or 'media.discord' in url_lower):
        return "discord_attachment"
    
    return "link"

# ENHANCED: Media URL detection with FIXED attachment handling
def get_media_url(content, attachments):
    """Get media URL from content or attachments with enhanced detection - FIXED"""
    media_urls = []
    
    # FIXED: Process attachments FIRST and handle them properly
    if attachments:
        for attachment in attachments:
            logger.info(f"Found attachment: {attachment.filename} - {attachment.url}")
            media_urls.append({
                'url': attachment.url,
                'type': detect_media_type(attachment.url),
                'filename': attachment.filename,
                'size': attachment.size,
                'source': 'attachment'
            })
    
    # Then process content for embedded links
    if content:
        # Tenor detection
        tenor_matches = re.finditer(r'https?://(?:www\.)?tenor\.com/view/[^\s]+', content)
        for match in tenor_matches:
            url = match.group(0)
            media_urls.append({
                'url': url,
                'type': 'tenor_gif',
                'source': 'embedded'
            })
        
        # Giphy detection
        giphy_matches = re.finditer(r'https?://(?:www\.)?giphy\.com/gifs/[^\s]+', content)
        for match in giphy_matches:
            url = match.group(0)
            media_urls.append({
                'url': url,
                'type': 'giphy_gif',
                'source': 'embedded'
            })
        
        # Discord media detection
        discord_matches = re.finditer(r'https?://(?:cdn|media)\.discordapp\.(?:com|net)/[^\s]+\.(gif|png|jpg|jpeg|webp|mp4|mov)[^\s]*', content)
        for match in discord_matches:
            url = match.group(0)
            media_urls.append({
                'url': url,
                'type': detect_media_type(url),
                'source': 'embedded'
            })
        
        # Direct media links
        direct_matches = re.finditer(r'https?://[^\s]+\.(gif|png|jpg|jpeg|webp|mp4|mov|mp3|wav|ogg)[^\s]*', content)
        for match in direct_matches:
            url = match.group(0)
            media_urls.append({
                'url': url,
                'type': detect_media_type(url),
                'source': 'embedded'
            })
        
        # YouTube detection
        youtube_matches = re.finditer(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^\s]+', content)
        for match in youtube_matches:
            url = match.group(0)
            media_urls.append({
                'url': url,
                'type': 'youtube_video',
                'source': 'embedded'
            })
        
        # Twitter/X detection
        twitter_matches = re.finditer(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[^\s]+', content)
        for match in twitter_matches:
            url = match.group(0)
            media_urls.append({
                'url': url,
                'type': 'twitter_media',
                'source': 'embedded'
            })
    
    return media_urls if media_urls else None

def clean_content_from_media(content, media_urls):
    """Remove media URLs from content to avoid duplication - ENHANCED"""
    if not content or not media_urls:
        return content
    
    cleaned_content = content
    for media in media_urls:
        if media['source'] == 'embedded':
            cleaned_content = cleaned_content.replace(media['url'], '').strip()
    
    cleaned_content = re.sub(r'\s+', ' ', cleaned_content).strip()
    return cleaned_content if cleaned_content else None

def has_links(content):
    if not content:
        return False
    url_pattern = r'https?://[^\s]+'
    return bool(re.search(url_pattern, content))

def truncate_content(content, max_length=50):
    if not content:
        return "*No text content*"
    if len(content) <= max_length:
        return content
    return content[:max_length-3] + "..."

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

async def get_or_create_webhook(channel):
    """Get existing webhook or create a new one for the channel"""
    if channel.id in channel_webhooks:
        webhook = channel_webhooks[channel.id]
        try:
            await webhook.fetch()
            return webhook
        except discord.NotFound:
            del channel_webhooks[channel.id]
    
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.name == "FACTSY Webhook":
            channel_webhooks[channel.id] = webhook
            return webhook
    
    webhook = await channel.create_webhook(name="FACTSY Webhook")
    channel_webhooks[channel.id] = webhook
    return webhook

def get_user_message_count(guild_id, user_id):
    if guild_id not in user_message_counts:
        return 0
    return user_message_counts[guild_id].get(user_id, 0)

def increment_user_message_count(guild_id, user_id):
    if guild_id not in user_message_counts:
        user_message_counts[guild_id] = {}
    
    if user_id not in user_message_counts[guild_id]:
        user_message_counts[guild_id][user_id] = 0
    
    user_message_counts[guild_id][user_id] += 1

def can_host_giveaway(member):
    """Check if a member can host giveaways"""
    if is_bot_owner(member.id):
        return True
    
    if member.guild_permissions.administrator or member.id == member.guild.owner_id:
        return True
    
    guild_id = member.guild.id
    if guild_id not in giveaway_host_roles:
        return False
    
    user_role_ids = [role.id for role in member.roles]
    return any(role_id in user_role_ids for role_id in giveaway_host_roles[guild_id])

def check_giveaway_requirements(member, requirements):
    """Check if a member meets all giveaway requirements"""
    if not requirements:
        return True, []
    
    failed_requirements = []
    guild = member.guild
    
    if 'messages' in requirements:
        user_count = get_user_message_count(guild.id, member.id)
        required_messages = requirements['messages']
        if user_count < required_messages:
            failed_requirements.append(f"Need {required_messages} messages (has {user_count})")
    
    if 'time_in_server' in requirements:
        join_time = member.joined_at
        if join_time:
            time_in_server = (datetime.utcnow() - join_time).total_seconds()
            required_time = requirements['time_in_server']
            if time_in_server < required_time:
                required_str = format_duration(required_time)
                current_str = format_duration(int(time_in_server))
                failed_requirements.append(f"Need {required_str} in server (has {current_str})")
    
    if 'required_role' in requirements:
        role_name = requirements['required_role']
        if not any(role.name.lower() == role_name.lower() for role in member.roles):
            failed_requirements.append(f"Need role: {role_name}")
    
    if 'blacklisted_role' in requirements:
        role_name = requirements['blacklisted_role']
        if any(role.name.lower() == role_name.lower() for role in member.roles):
            failed_requirements.append(f"Cannot have role: {role_name}")
    
    return len(failed_requirements) == 0, failed_requirements

# Custom checks
def not_blocked():
    async def predicate(ctx):
        if is_user_blocked(ctx.author.id):
            return False
        return True
    return commands.check(predicate)

def check_not_blocked():
    async def predicate(interaction: discord.Interaction):
        if is_user_blocked(interaction.user.id):
            return False
        return True
    return app_commands.check(predicate)

# Views
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

# FIXED: Remove User Modal for giveaway participant removal
class RemoveUserModal(discord.ui.Modal, title="Remove Participant"):
    def __init__(self, message_id):
        super().__init__()
        self.message_id = message_id

    user_input = discord.ui.TextInput(
        label="User to Remove",
        placeholder="Enter username, ID, or @mention",
        required=True,
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        if self.message_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway is no longer active.", ephemeral=True)
            return

        giveaway = active_giveaways[self.message_id]
        user_input = self.user_input.value.strip()

        # Try to parse user mention, ID, or username
        target_user = None
        user_id = None

        # Check if it's a mention
        mention_match = re.match(r'<@!?(\d+)>', user_input)
        if mention_match:
            user_id = int(mention_match.group(1))
            target_user = bot.get_user(user_id)
        else:
            # Try to parse as ID
            try:
                user_id = int(user_input)
                target_user = bot.get_user(user_id)
            except ValueError:
                # Try to find by username
                target_user = find_user_globally(user_input)
                if target_user:
                    user_id = target_user.id

        if not target_user or user_id not in giveaway['participants']:
            await interaction.response.send_message("❌ User not found in giveaway participants.", ephemeral=True)
            return

        # Remove user from participants
        giveaway['participants'].remove(user_id)
        await interaction.response.send_message(f"✅ Removed **{target_user.name}** from the giveaway.", ephemeral=True)

# FIXED: Giveaway View with proper message ID handling, requirements, and remove functionality
class GiveawayView(discord.ui.View):
    def __init__(self, message_id):
        super().__init__(timeout=None)
        self.message_id = message_id
    
    @discord.ui.button(label="Join", style=discord.ButtonStyle.green, emoji="🎉")
    async def join_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_user_blocked(interaction.user.id):
            await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
            return
        
        if self.message_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway is no longer active.", ephemeral=True)
            return
        
        giveaway = active_giveaways[self.message_id]
        user_id = interaction.user.id
        
        if user_id in giveaway['participants']:
            await interaction.response.send_message("❌ You are already participating in this giveaway!", ephemeral=True)
            return
        
        # FIXED: Check requirements properly
        if 'requirements' in giveaway and giveaway['requirements']:
            guild_member = interaction.guild.get_member(user_id)
            if guild_member:
                meets_requirements, failed_reqs = check_giveaway_requirements(guild_member, giveaway['requirements'])
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
        
        if self.message_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway is no longer active.", ephemeral=True)
            return
        
        giveaway = active_giveaways[self.message_id]
        participants = giveaway['participants']
        
        if not participants:
            await interaction.response.send_message("📋 No participants yet!", ephemeral=True)
            return
        
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
        
        # FIXED: Add Remove button for admins
        if (is_bot_owner(interaction.user.id) or 
            interaction.user.guild_permissions.administrator or 
            can_host_giveaway(interaction.user)):
            
            if len(embeds) == 1:
                view = RemoveParticipantView(self.message_id)
                await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)
            else:
                view = PaginationWithRemoveView(embeds, self.message_id)
                await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)
        else:
            if len(embeds) == 1:
                await interaction.response.send_message(embed=embeds[0], ephemeral=True)
            else:
                view = PaginationView(embeds)
                await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)

# FIXED: Remove Participant View
class RemoveParticipantView(discord.ui.View):
    def __init__(self, message_id):
        super().__init__(timeout=300)
        self.message_id = message_id
    
    @discord.ui.button(label="Remove", style=discord.ButtonStyle.danger, emoji="❌")
    async def remove_participant(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RemoveUserModal(self.message_id)
        await interaction.response.send_modal(modal)

# FIXED: Pagination with Remove View
class PaginationWithRemoveView(discord.ui.View):
    def __init__(self, embeds, message_id, timeout=300):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.message_id = message_id
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

# Events
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    # FIXED: Start the giveaway task AFTER the bot is ready
    if not check_giveaways.is_running():
        check_giveaways.start()
    
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
    
    guild_id = message.guild.id if message.guild else "DM"
    channel_id = message.channel.id
    
    if guild_id not in sniped_messages:
        sniped_messages[guild_id] = {}
    if channel_id not in sniped_messages[guild_id]:
        sniped_messages[guild_id][channel_id] = []
    
    # Get media URLs from content and attachments
    media_urls = get_media_url(message.content, message.attachments)
    cleaned_content = clean_content_from_media(message.content, media_urls)
    
    snipe_data = {
        'content': cleaned_content,
        'author': {
            'name': message.author.display_name,
            'id': message.author.id,
            'avatar_url': str(message.author.display_avatar.url)
        },
        'timestamp': message.created_at,
        'media_urls': media_urls,
        'has_offensive': is_offensive_content(message.content),
        'has_links': has_links(message.content),
        'channel_name': message.channel.name if hasattr(message.channel, 'name') else 'Unknown'
    }
    
    sniped_messages[guild_id][channel_id].append(snipe_data)
    
    # Keep only the latest MAX_MESSAGES
    if len(sniped_messages[guild_id][channel_id]) > MAX_MESSAGES:
        sniped_messages[guild_id][channel_id] = sniped_messages[guild_id][channel_id][-MAX_MESSAGES:]

@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
        return
    
    guild_id = before.guild.id if before.guild else "DM"
    channel_id = before.channel.id
    
    if guild_id not in edited_messages:
        edited_messages[guild_id] = {}
    if channel_id not in edited_messages[guild_id]:
        edited_messages[guild_id][channel_id] = []
    
    # Get media URLs from both versions
    before_media = get_media_url(before.content, before.attachments)
    after_media = get_media_url(after.content, after.attachments)
    
    before_cleaned = clean_content_from_media(before.content, before_media)
    after_cleaned = clean_content_from_media(after.content, after_media)
    
    edit_data = {
        'before': {
            'content': before_cleaned,
            'media_urls': before_media
        },
        'after': {
            'content': after_cleaned,
            'media_urls': after_media
        },
        'author': {
            'name': before.author.display_name,
            'id': before.author.id,
            'avatar_url': str(before.author.display_avatar.url)
        },
        'timestamp': after.edited_at or datetime.utcnow(),
        'has_offensive': is_offensive_content(before.content) or is_offensive_content(after.content),
        'channel_name': before.channel.name if hasattr(before.channel, 'name') else 'Unknown'
    }
    
    edited_messages[guild_id][channel_id].append(edit_data)
    
    # Keep only the latest MAX_MESSAGES
    if len(edited_messages[guild_id][channel_id]) > MAX_MESSAGES:
        edited_messages[guild_id][channel_id] = edited_messages[guild_id][channel_id][-MAX_MESSAGES:]

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Increment user message count for giveaway requirements
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    # Handle namelock
    if message.author.id in namelocked_users and message.author.id not in namelock_immune_users:
        namelock_data = namelocked_users[message.author.id]
        if message.guild and message.guild.id == namelock_data['guild_id']:
            locked_nickname = namelock_data['nickname']
            current_nickname = message.author.display_name
            
            if current_nickname != locked_nickname:
                try:
                    member = message.guild.get_member(message.author.id)
                    if member and member.top_role < message.guild.me.top_role:
                        await member.edit(nick=locked_nickname, reason="Namelock enforcement")
                except discord.Forbidden:
                    pass
                except Exception as e:
                    logger.error(f"Error enforcing namelock: {e}")
    
    await bot.process_commands(message)

# FIXED: Tasks - moved here and properly structured
@tasks.loop(minutes=1)
async def check_giveaways():
    """Check for expired giveaways and end them"""
    try:
        current_time = datetime.utcnow()
        expired_giveaways = []
        
        for message_id, giveaway in active_giveaways.items():
            if current_time >= giveaway['end_time']:
                expired_giveaways.append(message_id)
        
        for message_id in expired_giveaways:
            giveaway = active_giveaways[message_id]
            
            try:
                channel = bot.get_channel(giveaway['channel_id'])
                if not channel:
                    continue
                
                message = await channel.fetch_message(message_id)
                if not message:
                    continue
                
                participants = giveaway['participants']
                winners_count = giveaway['winners']
                
                if participants:
                    winners = random.sample(participants, min(winners_count, len(participants)))
                    winner_mentions = []
                    
                    for winner_id in winners:
                        user = bot.get_user(winner_id)
                        if user:
                            winner_mentions.append(user.mention)
                    
                    if winner_mentions:
                        winner_text = ", ".join(winner_mentions)
                        result_embed = discord.Embed(
                            title="🎉 Giveaway Ended!",
                            description=f"**Prize:** {giveaway['prize']}\n**Winner(s):** {winner_text}",
                            color=discord.Color.gold(),
                            timestamp=current_time
                        )
                        result_embed.add_field(
                            name="Participants",
                            value=str(len(participants)),
                            inline=True
                        )
                        result_embed.set_footer(text="Giveaway ended")
                        
                        await message.edit(embed=result_embed, view=None)
                        await channel.send(f"🎊 Congratulations {winner_text}! You won **{giveaway['prize']}**!")
                    else:
                        no_winner_embed = discord.Embed(
                            title="😔 Giveaway Ended - No Valid Winners",
                            description=f"**Prize:** {giveaway['prize']}\nNo valid winners could be determined.",
                            color=discord.Color.red(),
                            timestamp=current_time
                        )
                        await message.edit(embed=no_winner_embed, view=None)
                else:
                    no_participants_embed = discord.Embed(
                        title="😔 Giveaway Ended - No Participants",
                        description=f"**Prize:** {giveaway['prize']}\nNo one participated in this giveaway.",
                        color=discord.Color.red(),
                        timestamp=current_time
                    )
                    await message.edit(embed=no_participants_embed, view=None)
                
            except Exception as e:
                logger.error(f"Error ending giveaway {message_id}: {e}")
            
            # Remove from active giveaways
            del active_giveaways[message_id]
            
    except Exception as e:
        logger.error(f"Error in check_giveaways task: {e}")

# Slash Commands

# NEW: /perms command - Only owner can use this
@bot.tree.command(name="perms", description="Grant bot permissions to a user (Owner only)")
@app_commands.describe(user="The user to grant permissions to")
async def perms(interaction: discord.Interaction, user: discord.Member):
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if user.id == BOT_OWNER_ID:
        await interaction.response.send_message("❌ The bot owner already has all permissions.", ephemeral=True)
        return
    
    if user.id in authorized_users:
        await interaction.response.send_message(f"❌ {user.mention} already has bot permissions.", ephemeral=True)
        return
    
    authorized_users.add(user.id)
    
    embed = discord.Embed(
        title="✅ Permissions Granted",
        description=f"{user.mention} has been granted full bot permissions.",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="User", value=f"{user.name} ({user.id})", inline=True)
    embed.add_field(name="Granted by", value=interaction.user.mention, inline=True)
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="owner", description="Bot owner only commands")
@app_commands.describe(
    action="Action to perform",
    user="User to target (for some actions)",
    value="Value to set (for some actions)"
)
@app_commands.choices(action=[
    app_commands.Choice(name="block", value="block"),
    app_commands.Choice(name="unblock", value="unblock"),
    app_commands.Choice(name="immune", value="immune"),
    app_commands.Choice(name="unimmune", value="unimmune"),
    app_commands.Choice(name="stats", value="stats"),
    app_commands.Choice(name="botinfo", value="botinfo")
])
async def owner(interaction: discord.Interaction, action: str, user: discord.Member = None, value: str = None):
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if action == "block":
        if not user:
            await interaction.response.send_message("❌ Please specify a user to block.", ephemeral=True)
            return
        
        if user.id == BOT_OWNER_ID:
            await interaction.response.send_message("❌ Cannot block the bot owner.", ephemeral=True)
            return
        
        if user.id in blocked_users:
            await interaction.response.send_message(f"❌ {user.mention} is already blocked.", ephemeral=True)
            return
        
        blocked_users.add(user.id)
        await interaction.response.send_message(f"✅ Blocked {user.mention} from using bot functions.", ephemeral=True)
    
    elif action == "unblock":
        if not user:
            await interaction.response.send_message("❌ Please specify a user to unblock.", ephemeral=True)
            return
        
        if user.id not in blocked_users:
            await interaction.response.send_message(f"❌ {user.mention} is not blocked.", ephemeral=True)
            return
        
        blocked_users.remove(user.id)
        await interaction.response.send_message(f"✅ Unblocked {user.mention}.", ephemeral=True)
    
    elif action == "immune":
        if not user:
            await interaction.response.send_message("❌ Please specify a user to make immune.", ephemeral=True)
            return
        
        if user.id in namelock_immune_users:
            await interaction.response.send_message(f"❌ {user.mention} is already namelock immune.", ephemeral=True)
            return
        
        namelock_immune_users.add(user.id)
        await interaction.response.send_message(f"✅ Made {user.mention} immune to namelock.", ephemeral=True)
    
    elif action == "unimmune":
        if not user:
            await interaction.response.send_message("❌ Please specify a user to remove immunity.", ephemeral=True)
            return
        
        if user.id not in namelock_immune_users:
            await interaction.response.send_message(f"❌ {user.mention} is not namelock immune.", ephemeral=True)
            return
        
        namelock_immune_users.remove(user.id)
        await interaction.response.send_message(f"✅ Removed namelock immunity from {user.mention}.", ephemeral=True)
    
    elif action == "stats":
        total_sniped = sum(len(channels) for guild in sniped_messages.values() for channels in guild.values())
        total_edited = sum(len(channels) for guild in edited_messages.values() for channels in guild.values())
        total_blocked = len(blocked_users)
        total_immune = len(namelock_immune_users)
        total_namelocked = len(namelocked_users)
        total_giveaways = len(active_giveaways)
        
        embed = discord.Embed(
            title="📊 Bot Statistics",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Sniped Messages", value=str(total_sniped), inline=True)
        embed.add_field(name="Edited Messages", value=str(total_edited), inline=True)
        embed.add_field(name="Active Giveaways", value=str(total_giveaways), inline=True)
        embed.add_field(name="Blocked Users", value=str(total_blocked), inline=True)
        embed.add_field(name="Immune Users", value=str(total_immune), inline=True)
        embed.add_field(name="Namelocked Users", value=str(total_namelocked), inline=True)
        embed.add_field(name="Guilds", value=str(len(bot.guilds)), inline=True)
        embed.add_field(name="Authorized Users", value=str(len(authorized_users)), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    elif action == "botinfo":
        uptime_seconds = time.time() - BOT_START_TIME
        uptime_str = format_uptime(uptime_seconds)
        
        embed = discord.Embed(
            title="🤖 Bot Information",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Bot Name", value=bot.user.name, inline=True)
        embed.add_field(name="Bot ID", value=str(bot.user.id), inline=True)
        embed.add_field(name="Uptime", value=uptime_str, inline=True)
        embed.add_field(name="Discord.py Version", value=discord.__version__, inline=True)
        embed.add_field(name="Python Version", value=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", inline=True)
        embed.set_thumbnail(url=bot.user.display_avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Prefix Commands

# NEW: Helper function to create snipe embeds for all commands
def create_snipe_embeds(messages, title, filter_func=None, guild=None):
    """Create embeds for snipe messages with optional filtering"""
    if not messages:
        embed = discord.Embed(
            title=title,
            description="No messages found.",
            color=discord.Color.red()
        )
        return [embed]
    
    # Apply filter if provided
    if filter_func:
        messages = [msg for msg in messages if filter_func(msg)]
        
        if not messages:
            embed = discord.Embed(
                title=title,
                description="No messages found matching the criteria.",
                color=discord.Color.red()
            )
            return [embed]
    
    # Sort by timestamp (newest first)
    messages.sort(key=lambda x: x['timestamp'], reverse=True)
    
    embeds = []
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    
    for page in range(total_pages):
        start_idx = page * MESSAGES_PER_PAGE
        end_idx = min((page + 1) * MESSAGES_PER_PAGE, len(messages))
        page_messages = messages[start_idx:end_idx]
        
        embed = discord.Embed(
            title=title,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for i, msg in enumerate(page_messages, start=start_idx + 1):
            # Format timestamp
            time_str = msg['timestamp'].strftime("%m/%d %H:%M")
            
            # Build message info
            content_preview = truncate_content(msg.get('content'))
            if msg.get('has_offensive'):
                content_preview = filter_content(content_preview)
            
            # Channel info (for global commands)
            channel_info = ""
            if 'channel_name' in msg:
                channel_info = f" in #{msg['channel_name']}"
            
            # Media info
            media_info = ""
            if msg.get('media_urls'):
                media_count = len(msg['media_urls'])
                media_types = set(media['type'] for media in msg['media_urls'])
                if len(media_types) == 1:
                    media_type = list(media_types)[0]
                    if media_type == 'image':
                        media_info = f" 📷 {media_count} image{'s' if media_count > 1 else ''}"
                    elif media_type == 'gif':
                        media_info = f" 🎞️ {media_count} GIF{'s' if media_count > 1 else ''}"
                    elif media_type == 'video':
                        media_info = f" 🎥 {media_count} video{'s' if media_count > 1 else ''}"
                    else:
                        media_info = f" 📎 {media_count} file{'s' if media_count > 1 else ''}"
                else:
                    media_info = f" 📎 {media_count} file{'s' if media_count > 1 else ''}"
            
            field_name = f"{i}. {msg['author']['name']}{channel_info}"
            field_value = f"{content_preview}{media_info}\n*{time_str}*"
            
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        embed.set_footer(text=f"Page {page + 1}/{total_pages} • Total: {len(messages)} messages")
        embeds.append(embed)
    
    return embeds

# Existing snipe commands (,sp, ,spl, ,spf)
@bot.command(name='sp')
@not_blocked()
async def snipe(ctx, channel: discord.TextChannel = None):
    """Snipe deleted messages from a specific channel"""
    target_channel = channel or ctx.channel
    guild_id = ctx.guild.id
    channel_id = target_channel.id
    
    if guild_id not in sniped_messages or channel_id not in sniped_messages[guild_id]:
        await ctx.send("No deleted messages found in this channel.")
        return
    
    messages = sniped_messages[guild_id][channel_id]
    title = f"🔍 Deleted Messages in #{target_channel.name}"
    
    embeds = create_snipe_embeds(messages, title)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='spl')
@not_blocked()
async def snipe_links(ctx, channel: discord.TextChannel = None):
    """Snipe deleted messages with links from a specific channel"""
    target_channel = channel or ctx.channel
    guild_id = ctx.guild.id
    channel_id = target_channel.id
    
    if guild_id not in sniped_messages or channel_id not in sniped_messages[guild_id]:
        await ctx.send("No deleted messages found in this channel.")
        return
    
    messages = sniped_messages[guild_id][channel_id]
    title = f"🔗 Deleted Messages with Links in #{target_channel.name}"
    
    def link_filter(msg):
        return msg.get('has_links', False)
    
    embeds = create_snipe_embeds(messages, title, link_filter)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='spf')
@not_blocked()
async def snipe_filtered(ctx, channel: discord.TextChannel = None):
    """Snipe deleted messages with filtered content from a specific channel"""
    target_channel = channel or ctx.channel
    guild_id = ctx.guild.id
    channel_id = target_channel.id
    
    if guild_id not in sniped_messages or channel_id not in sniped_messages[guild_id]:
        await ctx.send("No deleted messages found in this channel.")
        return
    
    messages = sniped_messages[guild_id][channel_id]
    title = f"🚫 Deleted Messages with Filtered Content in #{target_channel.name}"
    
    def filter_func(msg):
        return msg.get('has_offensive', False)
    
    embeds = create_snipe_embeds(messages, title, filter_func)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

# NEW: Global snipe commands (,spa, ,spla, ,spfa)
@bot.command(name='spa')
@not_blocked()
async def snipe_all(ctx):
    """Snipe all deleted messages from all channels in the server"""
    guild_id = ctx.guild.id
    
    if guild_id not in sniped_messages:
        await ctx.send("No deleted messages found in this server.")
        return
    
    # Collect all messages from all channels
    all_messages = []
    for channel_id, messages in sniped_messages[guild_id].items():
        all_messages.extend(messages)
    
    if not all_messages:
        await ctx.send("No deleted messages found in this server.")
        return
    
    title = f"🔍 All Deleted Messages in {ctx.guild.name}"
    embeds = create_snipe_embeds(all_messages, title)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='spla')
@not_blocked()
async def snipe_links_all(ctx):
    """Snipe all deleted messages with links from all channels in the server"""
    guild_id = ctx.guild.id
    
    if guild_id not in sniped_messages:
        await ctx.send("No deleted messages found in this server.")
        return
    
    # Collect all messages from all channels
    all_messages = []
    for channel_id, messages in sniped_messages[guild_id].items():
        all_messages.extend(messages)
    
    if not all_messages:
        await ctx.send("No deleted messages found in this server.")
        return
    
    title = f"🔗 All Deleted Messages with Links in {ctx.guild.name}"
    
    def link_filter(msg):
        return msg.get('has_links', False)
    
    embeds = create_snipe_embeds(all_messages, title, link_filter)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='spfa')
@not_blocked()
async def snipe_filtered_all(ctx):
    """Snipe all deleted messages with filtered content from all channels in the server"""
    guild_id = ctx.guild.id
    
    if guild_id not in sniped_messages:
        await ctx.send("No deleted messages found in this server.")
        return
    
    # Collect all messages from all channels
    all_messages = []
    for channel_id, messages in sniped_messages[guild_id].items():
        all_messages.extend(messages)
    
    if not all_messages:
        await ctx.send("No deleted messages found in this server.")
        return
    
    title = f"🚫 All Deleted Messages with Filtered Content in {ctx.guild.name}"
    
    def filter_func(msg):
        return msg.get('has_offensive', False)
    
    embeds = create_snipe_embeds(all_messages, title, filter_func)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

# NEW: Clear command
@bot.command(name='clear')
@not_blocked()
async def clear_snipes(ctx):
    """Clear all sniped message data (Owner and authorized users only)"""
    if not has_bot_permissions(ctx.author.id):
        await ctx.send("❌ Only the bot owner and authorized users can use this command.")
        return
    
    # Clear all snipe data
    sniped_messages.clear()
    edited_messages.clear()
    
    embed = discord.Embed(
        title="🗑️ Data Cleared",
        description="All sniped and edited message data has been cleared.",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Cleared by", value=ctx.author.mention, inline=True)
    embed.set_footer(text="All snipe data has been permanently deleted")
    
    await ctx.send(embed=embed)

# Continue with all other existing commands...
@bot.command(name='editsnipe', aliases=['es'])
@not_blocked()
async def edit_snipe(ctx, channel: discord.TextChannel = None):
    """Snipe edited messages"""
    target_channel = channel or ctx.channel
    guild_id = ctx.guild.id
    channel_id = target_channel.id
    
    if guild_id not in edited_messages or channel_id not in edited_messages[guild_id]:
        await ctx.send("No edited messages found in this channel.")
        return
    
    messages = edited_messages[guild_id][channel_id]
    
    if not messages:
        await ctx.send("No edited messages found in this channel.")
        return
    
    # Sort by timestamp (newest first)
    messages.sort(key=lambda x: x['timestamp'], reverse=True)
    
    embeds = []
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    
    for page in range(total_pages):
        start_idx = page * MESSAGES_PER_PAGE
        end_idx = min((page + 1) * MESSAGES_PER_PAGE, len(messages))
        page_messages = messages[start_idx:end_idx]
        
        embed = discord.Embed(
            title=f"✏️ Edited Messages in #{target_channel.name}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        
        for i, msg in enumerate(page_messages, start=start_idx + 1):
            time_str = msg['timestamp'].strftime("%m/%d %H:%M")
            
            before_content = truncate_content(msg['before'].get('content'))
            after_content = truncate_content(msg['after'].get('content'))
            
            if msg.get('has_offensive'):
                before_content = filter_content(before_content)
                after_content = filter_content(after_content)
            
            field_name = f"{i}. {msg['author']['name']}"
            field_value = f"**Before:** {before_content}\n**After:** {after_content}\n*{time_str}*"
            
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        embed.set_footer(text=f"Page {page + 1}/{total_pages} • Total: {len(messages)} messages")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='help')
@not_blocked()
async def help_command(ctx, page: int = 1):
    """Show help information"""
    
    # Define help pages
    help_pages = [
        {
            "title": "📜 FACTSY Commands - Page 1",
            "fields": [
                ("🔍 **Snipe Commands**", "`,sp [channel]` - View deleted messages\n`,spl [channel]` - View deleted messages with links\n`,spf [channel]` - View deleted messages with filtered content\n`,spa` - View ALL deleted messages in server\n`,spla` - View ALL deleted messages with links\n`,spfa` - View ALL deleted messages with filtered content", False),
                ("✏️ **Edit Commands**", "`,editsnipe [channel]` / `,es [channel]` - View edited messages", False),
                ("🗑️ **Clear Commands**", "`,clear` - Clear all snipe data (Owner/Authorized only)", False)
            ]
        },
        {
            "title": "📜 FACTSY Commands - Page 2", 
            "fields": [
                ("🎉 **Giveaway Commands**", "`,gstart <time> <winners> <prize>` - Start a giveaway\n`,gend <message_id>` - End a giveaway early\n`,greroll <message_id>` - Reroll giveaway winners\n`,glist` - List active giveaways", False),
                ("⚙️ **Settings Commands**", "`,prefix <new_prefix>` - Change bot prefix\n`,grole <add/remove> <role>` - Manage giveaway host roles", False)
            ]
        },
        {
            "title": "📜 FACTSY Commands - Page 3",
            "fields": [
                ("🔒 **Namelock Commands**", "`,namelock <user> [nickname]` - Lock user's nickname\n`,unnamelock <user>` - Remove namelock\n`,namelocklist` - List namelocked users", False),
                ("🤖 **Utility Commands**", "`,userinfo [user]` - Get user information\n`,serverinfo` - Get server information\n`,botinfo` - Get bot information\n`,uptime` - Show bot uptime", False)
            ]
        },
        {
            "title": "📜 FACTSY Commands - Page 4",
            "fields": [
                ("🎭 **Fun Commands**", "`,impersonate <user> <message>` - Send message as another user\n`,embed <title> | <description> | [color]` - Create custom embed\n`,avatar [user]` - Get user's avatar\n`,say <message>` - Make bot say something", False),
                ("📊 **Slash Commands**", "`/owner` - Owner-only commands\n`/perms <user>` - Grant bot permissions (Owner only)", False)
            ]
        }
    ]
    
    # Validate page number
    if page < 1 or page > len(help_pages):
        page = 1
    
    page_data = help_pages[page - 1]
    
    embed = discord.Embed(
        title=page_data["title"],
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    for field in page_data["fields"]:
        embed.add_field(name=field[0], value=field[1], inline=field[2])
    
    embed.set_footer(text=f"Page {page}/{len(help_pages)} | Use ,help <page> to navigate")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='userinfo', aliases=['ui'])
@not_blocked()
async def user_info(ctx, user: discord.Member = None):
    """Get information about a user"""
    target_user = user or ctx.author
    
    # Calculate join position
    join_position = 1
    if target_user.joined_at:
        for member in ctx.guild.members:
            if member.joined_at and member.joined_at < target_user.joined_at:
                join_position += 1
    
    # Get message count
    message_count = get_user_message_count(ctx.guild.id, target_user.id)
    
    embed = discord.Embed(
        title=f"User Information - {target_user.display_name}",
        color=target_user.color if target_user.color != discord.Color.default() else discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    embed.set_thumbnail(url=target_user.display_avatar.url)
    
    # Basic info
    embed.add_field(name="Username", value=f"{target_user.name}#{target_user.discriminator}", inline=True)
    embed.add_field(name="Display Name", value=target_user.display_name, inline=True)
    embed.add_field(name="User ID", value=str(target_user.id), inline=True)
    
    # Dates
    account_age = datetime.utcnow() - target_user.created_at
    embed.add_field(name="Account Created", value=f"{target_user.created_at.strftime('%B %d, %Y')}\n({account_age.days} days ago)", inline=True)
    
    if target_user.joined_at:
        server_age = datetime.utcnow() - target_user.joined_at
        embed.add_field(name="Joined Server", value=f"{target_user.joined_at.strftime('%B %d, %Y')}\n({server_age.days} days ago)", inline=True)
        embed.add_field(name="Join Position", value=f"#{join_position}", inline=True)
    
    # Status info
    status_emoji = {"online": "🟢", "idle": "🟡", "dnd": "🔴", "offline": "⚫"}
    embed.add_field(name="Status", value=f"{status_emoji.get(str(target_user.status), '❓')} {str(target_user.status).title()}", inline=True)
    embed.add_field(name="Messages Sent", value=str(message_count), inline=True)
    embed.add_field(name="Bot", value="Yes" if target_user.bot else "No", inline=True)
    
    # Roles (top 10)
    roles = [role.mention for role in target_user.roles[1:]]  # Exclude @everyone
    if roles:
        roles_text = ", ".join(roles[:10])
        if len(roles) > 10:
            roles_text += f" and {len(roles) - 10} more..."
        embed.add_field(name=f"Roles ({len(roles)})", value=roles_text, inline=False)
    
    # Special badges
    badges = []
    if target_user.id == ctx.guild.owner_id:
        badges.append("👑 Server Owner")
    if target_user.guild_permissions.administrator:
        badges.append("⚡ Administrator")
    if target_user.premium_since:
        badges.append("💎 Server Booster")
    if is_bot_owner(target_user.id):
        badges.append("🔧 Bot Owner")
    if target_user.id in authorized_users:
        badges.append("🛡️ Authorized User")
    if target_user.id in namelocked_users:
        badges.append("🔒 Namelocked")
    if target_user.id in namelock_immune_users:
        badges.append("🛡️ Namelock Immune")
    if target_user.id in blocked_users:
        badges.append("❌ Blocked")
    
    if badges:
        embed.add_field(name="Badges", value="\n".join(badges), inline=False)
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.command(name='serverinfo', aliases=['si'])
@not_blocked()
async def server_info(ctx):
    """Get information about the server"""
    guild = ctx.guild
    
    # Count members by status
    online = sum(1 for member in guild.members if member.status == discord.Status.online)
    idle = sum(1 for member in guild.members if member.status == discord.Status.idle)
    dnd = sum(1 for member in guild.members if member.status == discord.Status.dnd)
    offline = sum(1 for member in guild.members if member.status == discord.Status.offline)
    
    # Count bots and humans
    bots = sum(1 for member in guild.members if member.bot)
    humans = len(guild.members) - bots
    
    embed = discord.Embed(
        title=f"Server Information - {guild.name}",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    # Basic info
    embed.add_field(name="Server Name", value=guild.name, inline=True)
    embed.add_field(name="Server ID", value=str(guild.id), inline=True)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    
    # Creation date
    creation_age = datetime.utcnow() - guild.created_at
    embed.add_field(name="Created", value=f"{guild.created_at.strftime('%B %d, %Y')}\n({creation_age.days} days ago)", inline=True)
    
    # Member counts
    embed.add_field(name="Total Members", value=str(guild.member_count), inline=True)
    embed.add_field(name="Humans/Bots", value=f"{humans}/{bots}", inline=True)
    
    # Status counts
    embed.add_field(name="Member Status", value=f"🟢 {online} 🟡 {idle} 🔴 {dnd} ⚫ {offline}", inline=True)
    
    # Channel counts
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    categories = len(guild.categories)
    embed.add_field(name="Channels", value=f"💬 {text_channels} 🔊 {voice_channels} 📁 {categories}", inline=True)
    
    # Other info
    embed.add_field(name="Roles", value=str(len(guild.roles)), inline=True)
    embed.add_field(name="Boost Level", value=f"Level {guild.premium_tier} ({guild.premium_subscription_count} boosts)", inline=True)
    embed.add_field(name="Verification Level", value=str(guild.verification_level).title(), inline=True)
    
    # Features
    if guild.features:
        features_text = ", ".join([feature.replace("_", " ").title() for feature in guild.features[:5]])
        if len(guild.features) > 5:
            features_text += f" and {len(guild.features) - 5} more..."
        embed.add_field(name="Server Features", value=features_text, inline=False)
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.command(name='botinfo', aliases=['bi'])
@not_blocked()
async def bot_info(ctx):
    """Get information about the bot"""
    uptime_seconds = time.time() - BOT_START_TIME
    uptime_str = format_uptime(uptime_seconds)
    
    # Calculate total members across all guilds
    total_members = sum(guild.member_count for guild in bot.guilds)
    
    # Calculate total sniped messages
    total_sniped = sum(len(messages) for guild in sniped_messages.values() for messages in guild.values())
    total_edited = sum(len(messages) for guild in edited_messages.values() for messages in guild.values())
    
    embed = discord.Embed(
        title="🤖 FACTSY Bot Information",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    # Basic info
    embed.add_field(name="Bot Name", value=bot.user.name, inline=True)
    embed.add_field(name="Bot ID", value=str(bot.user.id), inline=True)
    embed.add_field(name="Uptime", value=uptime_str, inline=True)
    
    # Statistics
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="Total Users", value=str(total_members), inline=True)
    embed.add_field(name="Active Giveaways", value=str(len(active_giveaways)), inline=True)
    
    # Data
    embed.add_field(name="Sniped Messages", value=str(total_sniped), inline=True)
    embed.add_field(name="Edited Messages", value=str(total_edited), inline=True)
    embed.add_field(name="Authorized Users", value=str(len(authorized_users)), inline=True)
    
    # Technical info
    embed.add_field(name="Discord.py Version", value=discord.__version__, inline=True)
    embed.add_field(name="Python Version", value="3.11+", inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    
    embed.add_field(name="Features", value="• Message Sniping\n• Giveaway System\n• Namelock System\n• User Management\n• Advanced Filtering", inline=False)
    
    embed.set_footer(text=f"Created by Bot Owner • Requested by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.command(name='uptime')
@not_blocked()
async def uptime(ctx):
    """Show bot uptime"""
    uptime_seconds = time.time() - BOT_START_TIME
    uptime_str = format_uptime(uptime_seconds)
    
    embed = discord.Embed(
        title="⏰ Bot Uptime",
        description=f"The bot has been running for **{uptime_str}**",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    
    embed.set_footer(text=f"Started at {datetime.fromtimestamp(BOT_START_TIME).strftime('%B %d, %Y at %H:%M:%S')}")
    
    await ctx.send(embed=embed)

@bot.command(name='avatar', aliases=['av'])
@not_blocked()
async def avatar(ctx, user: discord.Member = None):
    """Get a user's avatar"""
    target_user = user or ctx.author
    
    embed = discord.Embed(
        title=f"{target_user.display_name}'s Avatar",
        color=target_user.color if target_user.color != discord.Color.default() else discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    embed.set_image(url=target_user.display_avatar.url)
    embed.add_field(name="Direct Link", value=f"[Click Here]({target_user.display_avatar.url})", inline=False)
    embed.set_footer(text=f"Requested by {ctx.author.display_name}")
    
    await ctx.send(embed=embed)

@bot.command(name='say')
@not_blocked()
async def say(ctx, *, message):
    """Make the bot say something"""
    if is_user_blocked(ctx.author.id):
        return
    
    # Delete the original command message
    try:
        await ctx.message.delete()
    except:
        pass
    
    # Filter offensive content
    if is_offensive_content(message):
        filtered_message = filter_content(message)
        await ctx.send(filtered_message)
    else:
        await ctx.send(message)

@bot.command(name='embed')
@not_blocked()
async def create_embed(ctx, *, content):
    """Create a custom embed - Format: title | description | [color]"""
    parts = content.split(' | ')
    
    if len(parts) < 2:
        await ctx.send("❌ Format: `,embed title | description | [color]`")
        return
    
    title = parts[0].strip()
    description = parts[1].strip()
    color = parse_color(parts[2].strip()) if len(parts) > 2 else discord.Color.blue()
    
    # Filter offensive content
    if is_offensive_content(title):
        title = filter_content(title)
    if is_offensive_content(description):
        description = filter_content(description)
    
    embed = discord.Embed(
        title=title[:256],  # Discord title limit
        description=description[:4096],  # Discord description limit
        color=color,
        timestamp=datetime.utcnow()
    )
    
    embed.set_footer(text=f"Created by {ctx.author.display_name}")
    
    # Delete the original command message
    try:
        await ctx.message.delete()
    except:
        pass
    
    await ctx.send(embed=embed)

@bot.command(name='impersonate', aliases=['imp'])
@not_blocked()
async def impersonate(ctx, user: discord.Member, *, message):
    """Impersonate another user using webhooks"""
    if not ctx.channel.permissions_for(ctx.guild.me).manage_webhooks:
        await ctx.send("❌ I need the 'Manage Webhooks' permission to use this command.")
        return
    
    # Filter offensive content
    if is_offensive_content(message):
        message = filter_content(message)
    
    try:
        webhook = await get_or_create_webhook(ctx.channel)
        
        # Delete the original command message
        try:
            await ctx.message.delete()
        except:
            pass
        
        await webhook.send(
            content=message,
            username=user.display_name,
            avatar_url=user.display_avatar.url,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True)
        )
        
    except Exception as e:
        await ctx.send(f"❌ Error sending webhook message: {e}")

@bot.command(name='namelock', aliases=['nl'])
@not_blocked()
async def namelock(ctx, user: discord.Member, *, nickname=None):
    """Lock a user's nickname"""
    if not (ctx.author.guild_permissions.manage_nicknames or is_bot_owner(ctx.author.id) or ctx.author.id in authorized_users):
        await ctx.send("❌ You need the 'Manage Nicknames' permission to use this command.")
        return
    
    if not ctx.guild.me.guild_permissions.manage_nicknames:
        await ctx.send("❌ I need the 'Manage Nicknames' permission to lock nicknames.")
        return
    
    if user.top_role >= ctx.guild.me.top_role:
        await ctx.send("❌ I cannot namelock this user due to role hierarchy.")
        return
    
    if user.id == ctx.guild.owner_id:
        await ctx.send("❌ Cannot namelock the server owner.")
        return
    
    if user.id in namelock_immune_users:
        await ctx.send("❌ This user is immune to namelock.")
        return
    
    # Use provided nickname or current display name
    target_nickname = nickname or user.display_name
    
    # Filter offensive content from nickname
    if is_offensive_content(target_nickname):
        target_nickname = filter_content(target_nickname)
    
    # Apply the nickname
    try:
        await user.edit(nick=target_nickname, reason=f"Namelocked by {ctx.author}")
        
        # Store namelock data
        namelocked_users[user.id] = {
            'guild_id': ctx.guild.id,
            'nickname': target_nickname
        }
        
        embed = discord.Embed(
            title="🔒 User Namelocked",
            description=f"{user.mention} has been namelocked.",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Locked Nickname", value=target_nickname, inline=True)
        embed.add_field(name="Locked by", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname.")
    except Exception as e:
        await ctx.send(f"❌ Error applying namelock: {e}")

@bot.command(name='unnamelock', aliases=['unl'])
@not_blocked()
async def unnamelock(ctx, user: discord.Member):
    """Remove namelock from a user"""
    if not (ctx.author.guild_permissions.manage_nicknames or is_bot_owner(ctx.author.id) or ctx.author.id in authorized_users):
        await ctx.send("❌ You need the 'Manage Nicknames' permission to use this command.")
        return
    
    if user.id not in namelocked_users:
        await ctx.send("❌ This user is not namelocked.")
        return
    
    # Remove from namelock
    del namelocked_users[user.id]
    
    embed = discord.Embed(
        title="🔓 Namelock Removed",
        description=f"{user.mention} is no longer namelocked.",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Unlocked by", value=ctx.author.mention, inline=True)
    embed.set_thumbnail(url=user.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='namelocklist', aliases=['nll'])
@not_blocked()
async def namelock_list(ctx):
    """List all namelocked users in the server"""
    if not namelocked_users:
        await ctx.send("No users are currently namelocked.")
        return
    
    # Filter for this guild
    guild_namelocked = {uid: data for uid, data in namelocked_users.items() if data['guild_id'] == ctx.guild.id}
    
    if not guild_namelocked:
        await ctx.send("No users are currently namelocked in this server.")
        return
    
    embed = discord.Embed(
        title=f"🔒 Namelocked Users in {ctx.guild.name}",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    
    namelock_list = []
    for user_id, data in guild_namelocked.items():
        user = bot.get_user(user_id)
        if user:
            namelock_list.append(f"• {user.mention} → `{data['nickname']}`")
        else:
            namelock_list.append(f"• Unknown User ({user_id}) → `{data['nickname']}`")
    
    embed.description = "\n".join(namelock_list)
    embed.set_footer(text=f"Total: {len(namelock_list)} users")
    
    await ctx.send(embed=embed)

@bot.command(name='prefix')
@not_blocked()
async def change_prefix(ctx, new_prefix=None):
    """Change the bot's prefix for this server"""
    if not (ctx.author.guild_permissions.manage_guild or is_bot_owner(ctx.author.id) or ctx.author.id in authorized_users):
        await ctx.send("❌ You need the 'Manage Server' permission to change the prefix.")
        return
    
    if not new_prefix:
        current_prefix = custom_prefixes.get(ctx.guild.id, ",")
        await ctx.send(f"Current prefix: `{current_prefix}`\nUsage: `,prefix <new_prefix>`")
        return
    
    if len(new_prefix) > 5:
        await ctx.send("❌ Prefix cannot be longer than 5 characters.")
        return
    
    # Set new prefix
    custom_prefixes[ctx.guild.id] = new_prefix
    
    embed = discord.Embed(
        title="✅ Prefix Changed",
        description=f"Server prefix has been changed to `{new_prefix}`",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Changed by", value=ctx.author.mention, inline=True)
    embed.add_field(name="Example", value=f"`{new_prefix}help`", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='gstart')
@not_blocked()
async def giveaway_start(ctx, duration, winners: int, *, prize):
    """Start a giveaway"""
    if not can_host_giveaway(ctx.author):
        await ctx.send("❌ You don't have permission to host giveaways.")
        return
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        await ctx.send("❌ Invalid duration format. Use format like: 1m, 1h, 1d")
        return
    
    if duration_seconds < 10:  # Minimum 10 seconds
        await ctx.send("❌ Giveaway duration must be at least 10 seconds.")
        return
    
    if duration_seconds > 604800:  # Maximum 1 week
        await ctx.send("❌ Giveaway duration cannot exceed 1 week.")
        return
    
    if winners < 1 or winners > 20:
        await ctx.send("❌ Number of winners must be between 1 and 20.")
        return
    
    # Filter prize for offensive content
    if is_offensive_content(prize):
        prize = filter_content(prize)
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Create giveaway embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>\n**Hosted by:** {ctx.author.mention}",
        color=discord.Color.gold(),
        timestamp=end_time
    )
    embed.add_field(name="How to Enter", value="Click the 🎉 button below to join!", inline=False)
    embed.set_footer(text="Ends at")
    
    # Send giveaway message
    message = await ctx.send(embed=embed)
    
    # Create view with message ID
    view = GiveawayView(message.id)
    await message.edit(embed=embed, view=view)
    
    # Store giveaway data
    active_giveaways[message.id] = {
        'guild_id': ctx.guild.id,
        'channel_id': ctx.channel.id,
        'host_id': ctx.author.id,
        'prize': prize,
        'winners': winners,
        'end_time': end_time,
        'participants': [],
        'requirements': None
    }
    
    await ctx.message.delete()  # Delete the command message

@bot.command(name='gend')
@not_blocked()
async def giveaway_end(ctx, message_id: int):
    """End a giveaway early"""
    if message_id not in active_giveaways:
        await ctx.send("❌ Giveaway not found or already ended.")
        return
    
    giveaway = active_giveaways[message_id]
    
    # Check permissions
    if not (ctx.author.id == giveaway['host_id'] or 
            ctx.author.guild_permissions.administrator or 
            is_bot_owner(ctx.author.id) or
            ctx.author.id in authorized_users):
        await ctx.send("❌ You can only end giveaways you hosted, or you need admin permissions.")
        return
    
    try:
        channel = bot.get_channel(giveaway['channel_id'])
        message = await channel.fetch_message(message_id)
        
        participants = giveaway['participants']
        winners_count = giveaway['winners']
        
        if participants:
            winners = random.sample(participants, min(winners_count, len(participants)))
            winner_mentions = []
            
            for winner_id in winners:
                user = bot.get_user(winner_id)
                if user:
                    winner_mentions.append(user.mention)
            
            if winner_mentions:
                winner_text = ", ".join(winner_mentions)
                result_embed = discord.Embed(
                    title="🎉 Giveaway Ended Early!",
                    description=f"**Prize:** {giveaway['prize']}\n**Winner(s):** {winner_text}",
                    color=discord.Color.gold(),
                    timestamp=datetime.utcnow()
                )
                result_embed.add_field(name="Participants", value=str(len(participants)), inline=True)
                result_embed.add_field(name="Ended by", value=ctx.author.mention, inline=True)
                result_embed.set_footer(text="Giveaway ended early")
                
                await message.edit(embed=result_embed, view=None)
                await ctx.send(f"🎊 Congratulations {winner_text}! You won **{giveaway['prize']}**!")
            else:
                no_winner_embed = discord.Embed(
                    title="😔 Giveaway Ended - No Valid Winners",
                    description=f"**Prize:** {giveaway['prize']}\nNo valid winners could be determined.",
                    color=discord.Color.red(),
                    timestamp=datetime.utcnow()
                )
                await message.edit(embed=no_winner_embed, view=None)
                await ctx.send("Giveaway ended with no valid winners.")
        else:
            no_participants_embed = discord.Embed(
                title="😔 Giveaway Ended - No Participants",
                description=f"**Prize:** {giveaway['prize']}\nNo one participated in this giveaway.",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await message.edit(embed=no_participants_embed, view=None)
            await ctx.send("Giveaway ended with no participants.")
        
        # Remove from active giveaways
        del active_giveaways[message_id]
        
    except Exception as e:
        await ctx.send(f"❌ Error ending giveaway: {e}")

@bot.command(name='greroll')
@not_blocked()
async def giveaway_reroll(ctx, message_id: int):
    """Reroll a giveaway"""
    try:
        message = await ctx.channel.fetch_message(message_id)
        
        # Check if message has giveaway embed
        if not message.embeds:
            await ctx.send("❌ This message doesn't contain a giveaway.")
            return
        
        embed = message.embeds[0]
        if "giveaway" not in embed.title.lower():
            await ctx.send("❌ This message doesn't contain a giveaway.")
            return
        
        # Check permissions (allow admins and bot owners to reroll any giveaway)
        if not (ctx.author.guild_permissions.administrator or 
                is_bot_owner(ctx.author.id) or
                ctx.author.id in authorized_users):
            await ctx.send("❌ You need administrator permissions to reroll giveaways.")
            return
        
        # Extract prize from embed (this is a simplified approach)
        description = embed.description
        prize_match = re.search(r'\*\*Prize:\*\* (.+)', description)
        prize = prize_match.group(1) if prize_match else "Unknown Prize"
        
        # Get participants from giveaway data if available, otherwise ask for manual entry
        if message_id in active_giveaways:
            participants = active_giveaways[message_id]['participants']
            winners_count = active_giveaways[message_id]['winners']
        else:
            # For ended giveaways, we'll reroll with 1 winner
            # In a real implementation, you might want to store this data persistently
            await ctx.send("❌ Cannot reroll ended giveaways automatically. Participant data not available.")
            return
        
        if not participants:
            await ctx.send("❌ No participants to reroll from.")
            return
        
        # Select new winner(s)
        new_winners = random.sample(participants, min(winners_count, len(participants)))
        winner_mentions = []
        
        for winner_id in new_winners:
            user = bot.get_user(winner_id)
            if user:
                winner_mentions.append(user.mention)
        
        if winner_mentions:
            winner_text = ", ".join(winner_mentions)
            
            # Create reroll embed
            reroll_embed = discord.Embed(
                title="🎉 Giveaway Rerolled!",
                description=f"**Prize:** {prize}\n**New Winner(s):** {winner_text}",
                color=discord.Color.purple(),
                timestamp=datetime.utcnow()
            )
            reroll_embed.add_field(name="Rerolled by", value=ctx.author.mention, inline=True)
            reroll_embed.set_footer(text="Giveaway rerolled")
            
            await message.edit(embed=reroll_embed, view=None)
            await ctx.send(f"🎊 New winner(s): {winner_text}! Congratulations on winning **{prize}**!")
        else:
            await ctx.send("❌ Could not determine valid winners for reroll.")
            
    except discord.NotFound:
        await ctx.send("❌ Message not found.")
    except Exception as e:
        await ctx.send(f"❌ Error rerolling giveaway: {e}")

@bot.command(name='glist')
@not_blocked()
async def giveaway_list(ctx):
    """List active giveaways"""
    if not active_giveaways:
        await ctx.send("No active giveaways.")
        return
    
    # Filter giveaways for this guild
    guild_giveaways = {mid: data for mid, data in active_giveaways.items() if data['guild_id'] == ctx.guild.id}
    
    if not guild_giveaways:
        await ctx.send("No active giveaways in this server.")
        return
    
    embed = discord.Embed(
        title="🎉 Active Giveaways",
        color=discord.Color.gold(),
        timestamp=datetime.utcnow()
    )
    
    for message_id, giveaway in guild_giveaways.items():
        channel = bot.get_channel(giveaway['channel_id'])
        host = bot.get_user(giveaway['host_id'])
        
        channel_name = channel.name if channel else "Unknown Channel"
        host_name = host.display_name if host else "Unknown Host"
        
        time_left = giveaway['end_time'] - datetime.utcnow()
        time_left_str = format_duration(int(time_left.total_seconds()))
        
        participants_count = len(giveaway['participants'])
        
        field_value = f"**Prize:** {giveaway['prize']}\n**Channel:** #{channel_name}\n**Host:** {host_name}\n**Participants:** {participants_count}\n**Time Left:** {time_left_str}\n**Message ID:** {message_id}"
        
        embed.add_field(name=f"Giveaway #{len(embed.fields) + 1}", value=field_value, inline=False)
    
    embed.set_footer(text=f"Total active giveaways: {len(guild_giveaways)}")
    
    await ctx.send(embed=embed)

@bot.command(name='grole')
@not_blocked()
async def giveaway_role(ctx, action, role: discord.Role = None):
    """Manage roles that can host giveaways"""
    if not (ctx.author.guild_permissions.administrator or is_bot_owner(ctx.author.id) or ctx.author.id in authorized_users):
        await ctx.send("❌ You need administrator permissions to manage giveaway roles.")
        return
    
    if action.lower() not in ['add', 'remove', 'list']:
        await ctx.send("❌ Action must be 'add', 'remove', or 'list'.")
        return
    
    guild_id = ctx.guild.id
    
    if action.lower() == 'list':
        if guild_id not in giveaway_host_roles or not giveaway_host_roles[guild_id]:
            await ctx.send("No roles are set for giveaway hosting.")
            return
        
        role_mentions = []
        for role_id in giveaway_host_roles[guild_id]:
            role_obj = ctx.guild.get_role(role_id)
            if role_obj:
                role_mentions.append(role_obj.mention)
        
        if role_mentions:
            embed = discord.Embed(
                title="🎉 Giveaway Host Roles",
                description="\n".join(role_mentions),
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("No valid roles found.")
        return
    
    if not role:
        await ctx.send("❌ Please specify a role.")
        return
    
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = set()
    
    if action.lower() == 'add':
        if role.id in giveaway_host_roles[guild_id]:
            await ctx.send(f"❌ {role.mention} is already a giveaway host role.")
            return
        
        giveaway_host_roles[guild_id].add(role.id)
        await ctx.send(f"✅ Added {role.mention} as a giveaway host role.")
    
    elif action.lower() == 'remove':
        if role.id not in giveaway_host_roles[guild_id]:
            await ctx.send(f"❌ {role.mention} is not a giveaway host role.")
            return
        
        giveaway_host_roles[guild_id].remove(role.id)
        await ctx.send(f"✅ Removed {role.mention} from giveaway host roles.")

# Error handlers
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ Invalid argument provided.")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("❌ You are blocked from using bot functions.")
    else:
        print(f"Unhandled error: {error}")

# Run the bot
if __name__ == "__main__":
    import sys
    
    try:
        run_flask()
        token = os.getenv('DISCORD_TOKEN')
        if not token:
            print("Error: DISCORD_TOKEN environment variable not set")
            sys.exit(1)
        bot.run(token)
    except Exception as e:
        print(f"Error starting bot: {e}")
        sys.exit(1)
