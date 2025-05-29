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

# Helper function to resolve channel/thread by name
async def resolve_channel_or_thread(guild, channel_input):
    """Resolve channel or thread by name (supports #channelname syntax)"""
    if not channel_input:
        return None
    
    # Remove # if present
    channel_name = channel_input.lstrip('#').lower()
    
    # First check regular channels
    for channel in guild.text_channels:
        if channel.name.lower() == channel_name:
            return channel
    
    # Then check threads in all channels
    for channel in guild.text_channels:
        try:
            # Check active threads
            for thread in channel.threads:
                if thread.name.lower() == channel_name:
                    return thread
            
            # Check archived threads
            async for thread in channel.archived_threads():
                if thread.name.lower() == channel_name:
                    return thread
        except discord.Forbidden:
            continue
    
    return None

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
    
    @discord.ui.button(label="Remove", style=discord.ButtonStyle.danger, emoji="❌")
    async def remove_participant(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RemoveUserModal(self.message_id)
        await interaction.response.send_modal(modal)

# REACTION ROLE VIEW
class ReactionRoleView(discord.ui.View):
    def __init__(self, message_id, guild_id):
        super().__init__(timeout=None)
        self.message_id = message_id
        self.guild_id = guild_id
    
    @discord.ui.button(label="Get Role", style=discord.ButtonStyle.green, emoji="✅")
    async def get_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_user_blocked(interaction.user.id):
            await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
            return
        
        if self.guild_id not in reaction_roles or self.message_id not in reaction_roles[self.guild_id]:
            await interaction.response.send_message("❌ This reaction role is no longer active.", ephemeral=True)
            return
        
        role_id = reaction_roles[self.guild_id][self.message_id]
        role = interaction.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message("❌ Role not found.", ephemeral=True)
            return
        
        member = interaction.user
        
        if role in member.roles:
            try:
                await member.remove_roles(role)
                await interaction.response.send_message(f"✅ Removed role **{role.name}**!", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ I don't have permission to remove that role.", ephemeral=True)
        else:
            try:
                await member.add_roles(role)
                await interaction.response.send_message(f"✅ Added role **{role.name}**!", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ I don't have permission to give that role.", ephemeral=True)

# Events
@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    for guild in bot.guilds:
        logger.info(f'- {guild.name} (id: {guild.id})')
    
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} command(s)")
    except Exception as e:
        logger.error(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Track message count for giveaway requirements
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    # Handle namelock enforcement
    if message.author.id in namelocked_users and message.author.id not in namelock_immune_users:
        namelock_info = namelocked_users[message.author.id]
        if message.guild and message.guild.id == namelock_info['guild_id']:
            locked_nickname = namelock_info['nickname']
            member = message.guild.get_member(message.author.id)
            if member and member.display_name != locked_nickname:
                try:
                    await member.edit(nick=locked_nickname)
                    logger.info(f"Enforced namelock for {member.name} -> {locked_nickname}")
                except discord.Forbidden:
                    logger.warning(f"Cannot enforce namelock for {member.name} - insufficient permissions")
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []
    
    message_data = {
        'content': message.content,
        'author': message.author,
        'timestamp': message.created_at,
        'attachments': message.attachments,
        'embeds': message.embeds,
        'channel': message.channel
    }
    
    sniped_messages[channel_id].insert(0, message_data)
    
    if len(sniped_messages[channel_id]) > MAX_MESSAGES:
        sniped_messages[channel_id] = sniped_messages[channel_id][:MAX_MESSAGES]

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    if before.content == after.content:
        return
    
    channel_id = before.channel.id
    
    if channel_id not in edited_messages:
        edited_messages[channel_id] = []
    
    edit_data = {
        'before': before.content,
        'after': after.content,
        'author': before.author,
        'timestamp': before.created_at,
        'edit_timestamp': after.edited_at or datetime.utcnow(),
        'channel': before.channel
    }
    
    edited_messages[channel_id].insert(0, edit_data)
    
    if len(edited_messages[channel_id]) > MAX_MESSAGES:
        edited_messages[channel_id] = edited_messages[channel_id][:MAX_MESSAGES]

# Enhanced snipe commands with clickable usernames and thread support

@bot.command(name='sp', help='Show deleted messages from current or specified channel/thread')
async def snipe_messages(ctx, channel_input=None, page: int = 1):
    """Enhanced snipe command with thread support and clickable usernames"""
    if is_user_blocked(ctx.author.id):
        return
    
    # Handle specific channel/thread
    if channel_input:
        target_channel = await resolve_channel_or_thread(ctx.guild, channel_input)
        if not target_channel:
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description=f"Could not find channel or thread: `{channel_input}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        channel_id = target_channel.id
        if isinstance(target_channel, discord.Thread):
            location_text = f"#{target_channel.parent.name} → {target_channel.name}"
        else:
            location_text = f"#{target_channel.name}"
    else:
        # Use current channel/thread
        channel_id = ctx.channel.id
        target_channel = ctx.channel
        if isinstance(ctx.channel, discord.Thread):
            location_text = f"#{ctx.channel.parent.name} → {ctx.channel.name}"
        else:
            location_text = f"#{ctx.channel.name}"
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        embed = discord.Embed(
            title="👻 No Sniped Messages",
            description=f"No deleted messages found in {location_text}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    messages = sniped_messages[channel_id]
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    embed = discord.Embed(
        title=f"👻 Deleted Messages - {location_text}",
        color=discord.Color.red()
    )
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = messages[start_idx:end_idx]
    
    content_lines = []
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        author = msg['author']
        content = msg['content'] or "*No text content*"
        
        # Make username clickable
        content_lines.append(f"**{i}. {author.mention}**")
        content_lines.append(f"{content}")
        content_lines.append("")  # Empty line for spacing
    
    embed.description = "\n".join(content_lines)
    embed.set_footer(text=f"Page {page} of {total_pages} | {len(messages)} total messages")
    
    await ctx.send(embed=embed)

@bot.command(name='spl', help='Show deleted links from current or specified channel/thread')
async def snipe_links(ctx, channel_input=None, page: int = 1):
    """Enhanced snipe links command with thread support and clickable usernames"""
    if is_user_blocked(ctx.author.id):
        return
    
    # Handle specific channel/thread
    if channel_input:
        target_channel = await resolve_channel_or_thread(ctx.guild, channel_input)
        if not target_channel:
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description=f"Could not find channel or thread: `{channel_input}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        channel_id = target_channel.id
        if isinstance(target_channel, discord.Thread):
            location_text = f"#{target_channel.parent.name} → {target_channel.name}"
        else:
            location_text = f"#{target_channel.name}"
    else:
        # Use current channel/thread
        channel_id = ctx.channel.id
        if isinstance(ctx.channel, discord.Thread):
            location_text = f"#{ctx.channel.parent.name} → {ctx.channel.name}"
        else:
            location_text = f"#{ctx.channel.name}"
    
    if channel_id not in sniped_messages:
        embed = discord.Embed(
            title="🔗 No Link Messages",
            description=f"No deleted messages with links found in {location_text}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # Filter messages to show ONLY those with media/links
    media_messages = []
    for msg in sniped_messages[channel_id]:
        has_media = False
        
        if msg.get('attachments'):
            has_media = True
        
        if msg.get('content'):
            media_urls = get_media_url(msg['content'], [])
            if media_urls:
                has_media = True
        
        if has_media:
            media_messages.append(msg)
    
    if not media_messages:
        embed = discord.Embed(
            title="🔗 No Link Messages",
            description=f"No deleted messages with links found in {location_text}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # Sort by timestamp
    media_messages.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Pagination
    total_pages = math.ceil(len(media_messages) / MESSAGES_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    embed = discord.Embed(
        title=f"🔗 Deleted Link Messages - {location_text}",
        color=discord.Color.blue()
    )
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = media_messages[start_idx:end_idx]
    
    content_lines = []
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        author = msg['author']
        content = msg['content'] or ""
        
        # Extract links
        links = []
        if msg.get('attachments'):
            for attachment in msg['attachments']:
                links.append(attachment.url)
        
        if msg.get('content'):
            media_urls = get_media_url(msg['content'], [])
            if media_urls:
                for media in media_urls:
                    if media.get('source') == 'embedded':
                        links.append(media['url'])
        
        # Make username clickable
        content_lines.append(f"**{i}. {author.mention}**")
        if content and content.strip():
            content_lines.append(content)
        
        for link in links:
            content_lines.append(link)
        
        content_lines.append("")  # Empty line for spacing
    
    embed.description = "\n".join(content_lines)
    embed.set_footer(text=f"Page {page} of {total_pages} | {len(media_messages)} total messages")
    
    await ctx.send(embed=embed)

@bot.command(name='spf', help='Show clean messages from current or specified channel/thread')
async def snipe_filtered(ctx, channel_input=None, page: int = 1):
    """Enhanced snipe filtered command with thread support and clickable usernames"""
    if is_user_blocked(ctx.author.id):
        return
    
    # Handle specific channel/thread
    if channel_input:
        target_channel = await resolve_channel_or_thread(ctx.guild, channel_input)
        if not target_channel:
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description=f"Could not find channel or thread: `{channel_input}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        channel_id = target_channel.id
        if isinstance(target_channel, discord.Thread):
            location_text = f"#{target_channel.parent.name} → {target_channel.name}"
        else:
            location_text = f"#{target_channel.name}"
    else:
        # Use current channel/thread
        channel_id = ctx.channel.id
        if isinstance(ctx.channel, discord.Thread):
            location_text = f"#{ctx.channel.parent.name} → {ctx.channel.name}"
        else:
            location_text = f"#{ctx.channel.name}"
    
    if channel_id not in sniped_messages:
        embed = discord.Embed(
            title="✅ No Clean Messages",
            description=f"No clean messages found in {location_text}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # Filter clean messages (non-offensive)
    clean_messages = []
    for msg in sniped_messages[channel_id]:
        if not is_offensive_content(msg.get('content', '')):
            clean_messages.append(msg)
    
    if not clean_messages:
        embed = discord.Embed(
            title="✅ No Clean Messages",
            description=f"No clean messages found in {location_text}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # Sort by timestamp
    clean_messages.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Pagination
    total_pages = math.ceil(len(clean_messages) / MESSAGES_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    embed = discord.Embed(
        title=f"✅ Clean Messages - {location_text}",
        color=discord.Color.green()
    )
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = clean_messages[start_idx:end_idx]
    
    content_lines = []
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        author = msg['author']
        content = msg['content'] or "*No text content*"
        
        # Make username clickable
        content_lines.append(f"**{i}. {author.mention}**")
        content_lines.append(content)
        content_lines.append("")  # Empty line for spacing
    
    embed.description = "\n".join(content_lines)
    embed.set_footer(text=f"Page {page} of {total_pages} | {len(clean_messages)} total messages")
    
    await ctx.send(embed=embed)

# NEW ENHANCED "ALL" COMMANDS

@bot.command(name='spall', help='Show ALL deleted messages from all channels and threads')
async def snipe_all_messages(ctx, page: int = 1):
    """Show ALL deleted messages from ALL channels and threads"""
    if is_user_blocked(ctx.author.id):
        return
    
    # Collect from all channels and threads
    all_messages = []
    
    for channel_id, messages in sniped_messages.items():
        channel_obj = bot.get_channel(channel_id)
        if channel_obj and channel_obj.guild == ctx.guild:
            for msg in messages:
                msg_copy = msg.copy()
                if isinstance(channel_obj, discord.Thread):
                    msg_copy['source_info'] = f"#{channel_obj.parent.name} → {channel_obj.name}"
                else:
                    msg_copy['source_info'] = f"#{channel_obj.name}"
                all_messages.append(msg_copy)
    
    # Sort by timestamp
    all_messages.sort(key=lambda x: x['timestamp'], reverse=True)
    
    if not all_messages:
        embed = discord.Embed(
            title="👻 No Deleted Messages",
            description="No deleted messages found in any channel.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # Pagination
    total_pages = math.ceil(len(all_messages) / MESSAGES_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    embed = discord.Embed(
        title="👻 Deleted Messages - All Channels",
        color=discord.Color.purple()
    )
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = all_messages[start_idx:end_idx]
    
    content_lines = []
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        author = msg['author']
        content = msg['content'] or "*No text content*"
        
        content_lines.append(f"**{i}. {author.mention}**")
        content_lines.append(f"{content}")
        content_lines.append(f"📍 {msg['source_info']}")
        content_lines.append("")  # Empty line for spacing
    
    embed.description = "\n".join(content_lines)
    embed.set_footer(text=f"Page {page} of {total_pages} | {len(all_messages)} total messages")
    
    await ctx.send(embed=embed)

@bot.command(name='splall', help='Show deleted links from all channels or specific channel/thread')
async def snipe_links_all(ctx, channel_input=None, page: int = 1):
    """Show deleted links from all channels or specific channel/thread"""
    if is_user_blocked(ctx.author.id):
        return
    
    if channel_input:
        # Show links from specific channel/thread
        target_channel = await resolve_channel_or_thread(ctx.guild, channel_input)
        if not target_channel:
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description=f"Could not find channel or thread: `{channel_input}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        channel_id = target_channel.id
        if isinstance(target_channel, discord.Thread):
            location_text = f"#{target_channel.parent.name} → {target_channel.name}"
        else:
            location_text = f"#{target_channel.name}"
        
        if channel_id not in sniped_messages:
            embed = discord.Embed(
                title="🔗 No Link Messages",
                description=f"No deleted messages with links found in {location_text}.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        # Filter messages with media/links from specific channel
        media_messages = []
        for msg in sniped_messages[channel_id]:
            has_media = False
            
            if msg.get('attachments'):
                has_media = True
            
            if msg.get('content'):
                media_urls = get_media_url(msg['content'], [])
                if media_urls:
                    has_media = True
            
            if has_media:
                media_messages.append(msg)
        
        title = f"🔗 Deleted Link Messages - {location_text}"
        show_source = False
        
    else:
        # Show links from ALL channels and threads
        media_messages = []
        
        for channel_id, messages in sniped_messages.items():
            channel_obj = bot.get_channel(channel_id)
            if channel_obj and channel_obj.guild == ctx.guild:
                for msg in messages:
                    has_media = False
                    
                    if msg.get('attachments'):
                        has_media = True
                    
                    if msg.get('content'):
                        media_urls = get_media_url(msg['content'], [])
                        if media_urls:
                            has_media = True
                    
                    if has_media:
                        msg_copy = msg.copy()
                        if isinstance(channel_obj, discord.Thread):
                            msg_copy['source_info'] = f"#{channel_obj.parent.name} → {channel_obj.name}"
                        else:
                            msg_copy['source_info'] = f"#{channel_obj.name}"
                        media_messages.append(msg_copy)
        
        title = "🔗 Deleted Link Messages - All Channels"
        show_source = True
    
    if not media_messages:
        embed = discord.Embed(
            title="🔗 No Link Messages",
            description="No deleted messages with links found.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # Sort by timestamp
    media_messages.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Pagination
    total_pages = math.ceil(len(media_messages) / MESSAGES_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    embed = discord.Embed(
        title=title,
        color=discord.Color.blue()
    )
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = media_messages[start_idx:end_idx]
    
    content_lines = []
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        author = msg['author']
        content = msg['content'] or ""
        
        # Extract links
        links = []
        if msg.get('attachments'):
            for attachment in msg['attachments']:
                links.append(attachment.url)
        
        if msg.get('content'):
            media_urls = get_media_url(msg['content'], [])
            if media_urls:
                for media in media_urls:
                    if media.get('source') == 'embedded':
                        links.append(media['url'])
        
        content_lines.append(f"**{i}. {author.mention}**")
        if content and content.strip():
            content_lines.append(content)
        
        for link in links:
            content_lines.append(link)
        
        if show_source and 'source_info' in msg:
            content_lines.append(f"📍 {msg['source_info']}")
        
        content_lines.append("")  # Empty line for spacing
    
    embed.description = "\n".join(content_lines)
    embed.set_footer(text=f"Page {page} of {total_pages} | {len(media_messages)} total messages")
    
    await ctx.send(embed=embed)

@bot.command(name='spfall', help='Show clean messages from all channels or specific channel/thread')
async def snipe_filtered_all(ctx, channel_input=None, page: int = 1):
    """Show clean messages from all channels or specific channel/thread"""
    if is_user_blocked(ctx.author.id):
        return
    
    if channel_input:
        # Show clean messages from specific channel/thread
        target_channel = await resolve_channel_or_thread(ctx.guild, channel_input)
        if not target_channel:
            embed = discord.Embed(
                title="❌ Channel Not Found",
                description=f"Could not find channel or thread: `{channel_input}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        channel_id = target_channel.id
        if isinstance(target_channel, discord.Thread):
            location_text = f"#{target_channel.parent.name} → {target_channel.name}"
        else:
            location_text = f"#{target_channel.name}"
        
        if channel_id not in sniped_messages:
            embed = discord.Embed(
                title="✅ No Clean Messages",
                description=f"No clean messages found in {location_text}.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        # Filter clean messages from specific channel
        clean_messages = []
        for msg in sniped_messages[channel_id]:
            if not is_offensive_content(msg.get('content', '')):
                clean_messages.append(msg)
        
        title = f"✅ Clean Messages - {location_text}"
        show_source = False
        
    else:
        # Show clean messages from ALL channels and threads
        clean_messages = []
        
        for channel_id, messages in sniped_messages.items():
            channel_obj = bot.get_channel(channel_id)
            if channel_obj and channel_obj.guild == ctx.guild:
                for msg in messages:
                    if not is_offensive_content(msg.get('content', '')):
                        msg_copy = msg.copy()
                        if isinstance(channel_obj, discord.Thread):
                            msg_copy['source_info'] = f"#{channel_obj.parent.name} → {channel_obj.name}"
                        else:
                            msg_copy['source_info'] = f"#{channel_obj.name}"
                        clean_messages.append(msg_copy)
        
        title = "✅ Clean Messages - All Channels"
        show_source = True
    
    if not clean_messages:
        embed = discord.Embed(
            title="✅ No Clean Messages",
            description="No clean messages found.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    # Sort by timestamp
    clean_messages.sort(key=lambda x: x['timestamp'], reverse=True)
    
    # Pagination
    total_pages = math.ceil(len(clean_messages) / MESSAGES_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    embed = discord.Embed(
        title=title,
        color=discord.Color.green()
    )
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = clean_messages[start_idx:end_idx]
    
    content_lines = []
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        author = msg['author']
        content = msg['content'] or "*No text content*"
        
        content_lines.append(f"**{i}. {author.mention}**")
        content_lines.append(content)
        
        if show_source and 'source_info' in msg:
            content_lines.append(f"📍 {msg['source_info']}")
        
        content_lines.append("")  # Empty line for spacing
    
    embed.description = "\n".join(content_lines)
    embed.set_footer(text=f"Page {page} of {total_pages} | {len(clean_messages)} total messages")
    
    await ctx.send(embed=embed)

# Edit snipe command
@bot.command(name='editsnipe', aliases=['es'], help='Show recently edited messages')
async def edit_snipe(ctx, page: int = 1):
    """Show recently edited messages in the current channel"""
    if is_user_blocked(ctx.author.id):
        return
    
    channel_id = ctx.channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        embed = discord.Embed(
            title="📝 No Edited Messages",
            description="No edited messages found in this channel.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    messages = edited_messages[channel_id]
    total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
    page = max(1, min(page, total_pages))
    
    embed = discord.Embed(
        title=f"📝 Edited Messages - #{ctx.channel.name}",
        color=discord.Color.yellow()
    )
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = start_idx + MESSAGES_PER_PAGE
    page_messages = messages[start_idx:end_idx]
    
    for i, edit in enumerate(page_messages, start=start_idx + 1):
        author = edit['author']
        before = edit['before'] or "*No content*"
        after = edit['after'] or "*No content*"
        
        embed.add_field(
            name=f"{i}. {author.mention}",
            value=f"**Before:** {truncate_content(before, 100)}\n**After:** {truncate_content(after, 100)}",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} | {len(messages)} total edits")
    await ctx.send(embed=embed)

# Help command with updated commands
@bot.command(name='help')
async def help_command(ctx, command_name=None):
    """Show help information for commands"""
    if is_user_blocked(ctx.author.id):
        return
    
    if command_name:
        # Show help for specific command
        command = bot.get_command(command_name)
        if command:
            embed = discord.Embed(
                title=f"Help - {command.name}",
                description=command.help or "No description available.",
                color=discord.Color.blue()
            )
            
            # Add usage information
            usage = f"{get_prefix(bot, ctx.message)}{command.name}"
            if command.signature:
                usage += f" {command.signature}"
            embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
            
            # Add aliases
            if command.aliases:
                embed.add_field(name="Aliases", value=", ".join([f"`{alias}`" for alias in command.aliases]), inline=False)
        else:
            embed = discord.Embed(
                title="Command Not Found",
                description=f"No command named `{command_name}` found.",
                color=discord.Color.red()
            )
        
        await ctx.send(embed=embed)
        return
    
    # Show all commands grouped by category
    help_pages = [
        {
            "title": "📜 FACTSY Commands - Page 1",
            "fields": [
                ("**Message Snipe Commands**", 
                 "`,sp [channel] [page]` `/sp` - Show deleted messages\n"
                 "`,spl [channel] [page]` `/spl` - Show deleted links only\n"
                 "`,spf [channel] [page]` `/spf` - Show clean messages only\n"
                 "`,spall [page]` - Show deleted messages from ALL channels\n"
                 "`,splall [channel] [page]` - Show deleted links from all/specific channels\n"
                 "`,spfall [channel] [page]` - Show clean messages from all/specific channels\n"
                 "`,editsnipe [page]` `/es` - Show recently edited messages", False),
                ("**User Management**", 
                 "`,userinfo <user>` `/userinfo` - Show user information\n"
                 "`,avatar <user>` `/avatar` - Show user's avatar\n"
                 "`,whois <user>` - Show detailed user info", False),
            ]
        },
        {
            "title": "📜 FACTSY Commands - Page 2", 
            "fields": [
                ("**Moderation Commands**",
                 "`,namelock <user> <nickname>` - Lock user's nickname\n"
                 "`,unnamelock <user>` - Remove namelock\n"
                 "`,namelock_immune <user>` - Make user immune to namelock\n"
                 "`,remove_immunity <user>` - Remove namelock immunity\n"
                 "`,block <user>` - Block user from bot commands\n"
                 "`,unblock <user>` - Unblock user\n"
                 "`,prefix <new_prefix>` - Change bot prefix", False),
                ("**Utility Commands**",
                 "`,uptime` - Show bot uptime\n"
                 "`,ping` - Show bot latency\n"
                 "`,stats` - Show bot statistics", False),
            ]
        },
        {
            "title": "📜 FACTSY Commands - Page 3",
            "fields": [
                ("**Giveaway Commands**",
                 "`,giveaway` - Start a new giveaway (interactive)\n"
                 "`,giveaway_quick <time> <prize>` - Quick giveaway\n"
                 "`,giveaway_roles <role>` - Set giveaway host roles\n"
                 "`,end_giveaway <message_id>` - End a giveaway early\n"
                 "`,reroll <message_id>` - Reroll giveaway winner", False),
                ("**Message & Channel**",
                 "`,say <message>` - Make bot say something\n"
                 "`,embed <title> <description>` - Create embed\n"
                 "`,clear <amount>` - Delete messages\n"
                 "`,slowmode <seconds>` - Set channel slowmode", False),
            ]
        },
        {
            "title": "📜 FACTSY Commands - Page 4",
            "fields": [
                ("**Fun Commands**",
                 "`,8ball <question>` - Ask the magic 8-ball\n"
                 "`,coinflip` - Flip a coin\n"
                 "`,roll <sides>` - Roll a dice", False),
                ("**Reaction Roles**",
                 "`,reaction_role <role> <message>` - Create reaction role\n"
                 "`,list_reaction_roles` - List active reaction roles\n"
                 "`,remove_reaction_role <message_id>` - Remove reaction role", False),
                ("**Owner Only**",
                 "`,shutdown` - Shutdown the bot\n"
                 "`,restart` - Restart the bot", False),
            ]
        }
    ]
    
    embeds = []
    for page in help_pages:
        embed = discord.Embed(
            title=page["title"],
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for field_name, field_value, inline in page["fields"]:
            embed.add_field(name=field_name, value=field_value, inline=inline)
        
        embed.set_footer(text=f"Use ,help <command> for detailed info • Bot by FACTSY")
        embeds.append(embed)
    
    # Send paginated help
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

# User info commands
@bot.command(name='userinfo', help='Show information about a user')
async def user_info(ctx, user: discord.Member = None):
    """Show detailed information about a user"""
    if is_user_blocked(ctx.author.id):
        return
    
    if user is None:
        user = ctx.author
    
    # Calculate account age
    account_created = user.created_at
    account_age = datetime.utcnow() - account_created
    
    # Calculate server join time
    joined_at = user.joined_at
    if joined_at:
        time_in_server = datetime.utcnow() - joined_at
        join_position = sorted(ctx.guild.members, key=lambda m: m.joined_at or datetime.min).index(user) + 1
    else:
        time_in_server = None
        join_position = "Unknown"
    
    embed = discord.Embed(
        title=f"User Information - {user.display_name}",
        color=user.color if user.color != discord.Color.default() else discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    
    # Basic info
    embed.add_field(
        name="👤 Basic Info",
        value=f"**Username:** {user.name}\n"
              f"**Display Name:** {user.display_name}\n"
              f"**ID:** {user.id}\n"
              f"**Bot:** {'Yes' if user.bot else 'No'}",
        inline=True
    )
    
    # Account timing
    embed.add_field(
        name="⏰ Account Info",
        value=f"**Created:** {account_created.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
              f"**Account Age:** {format_duration(int(account_age.total_seconds()))}",
        inline=True
    )
    
    # Server info
    if joined_at:
        embed.add_field(
            name="🏠 Server Info",
            value=f"**Joined:** {joined_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                  f"**Time in Server:** {format_duration(int(time_in_server.total_seconds()))}\n"
                  f"**Join Position:** #{join_position}",
            inline=True
        )
    
    # Roles
    roles = [role.mention for role in user.roles[1:]]  # Exclude @everyone
    if roles:
        roles_text = ", ".join(roles) if len(", ".join(roles)) <= 1024 else f"{len(roles)} roles"
        embed.add_field(name=f"🎭 Roles ({len(roles)})", value=roles_text, inline=False)
    
    # Permissions
    perms = user.guild_permissions
    key_perms = []
    if perms.administrator:
        key_perms.append("Administrator")
    if perms.manage_guild:
        key_perms.append("Manage Server")
    if perms.manage_channels:
        key_perms.append("Manage Channels")
    if perms.manage_messages:
        key_perms.append("Manage Messages")
    if perms.kick_members:
        key_perms.append("Kick Members")
    if perms.ban_members:
        key_perms.append("Ban Members")
    
    if key_perms:
        embed.add_field(name="🔑 Key Permissions", value=", ".join(key_perms), inline=False)
    
    # Activity/Status
    if user.activity:
        activity_type = str(user.activity.type).replace("ActivityType.", "").title()
        embed.add_field(name="🎮 Activity", value=f"{activity_type}: {user.activity.name}", inline=True)
    
    embed.add_field(name="📱 Status", value=str(user.status).title(), inline=True)
    
    # Bot-specific stats
    message_count = get_user_message_count(ctx.guild.id, user.id)
    embed.add_field(name="📊 Bot Stats", value=f"**Messages Tracked:** {message_count}", inline=True)
    
    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='avatar', help='Show a user\'s avatar')
async def avatar_command(ctx, user: discord.Member = None):
    """Show a user's avatar"""
    if is_user_blocked(ctx.author.id):
        return
    
    if user is None:
        user = ctx.author
    
    embed = discord.Embed(
        title=f"{user.display_name}'s Avatar",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    embed.set_image(url=user.display_avatar.url)
    embed.add_field(name="Download Links", 
                    value=f"[PNG]({user.display_avatar.replace(format='png', size=1024).url}) | "
                          f"[JPG]({user.display_avatar.replace(format='jpg', size=1024).url}) | "
                          f"[WEBP]({user.display_avatar.replace(format='webp', size=1024).url})", 
                    inline=False)
    
    embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='whois', help='Show detailed user information')
async def whois_command(ctx, user: discord.Member = None):
    """Alias for userinfo command"""
    await user_info(ctx, user)

# Moderation commands
@bot.command(name='namelock', help='Lock a user\'s nickname (Admin only)')
@commands.has_permissions(administrator=True)
async def namelock_user(ctx, user: discord.Member, *, nickname):
    """Lock a user's nickname"""
    if is_user_blocked(ctx.author.id):
        return
    
    # Store namelock info
    namelocked_users[user.id] = {
        'guild_id': ctx.guild.id,
        'nickname': nickname
    }
    
    # Apply the nickname
    try:
        await user.edit(nick=nickname)
        
        embed = discord.Embed(
            title="🔒 User Namelocked",
            description=f"**User:** {user.mention}\n**Locked Nickname:** {nickname}",
            color=discord.Color.orange(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text=f"Locked by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        
        await ctx.send(embed=embed)
        logger.info(f"Namelocked {user.name} to '{nickname}' in {ctx.guild.name}")
        
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Permission Error",
            description="I don't have permission to change that user's nickname.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command(name='unnamelock', help='Remove namelock from a user (Admin only)')
@commands.has_permissions(administrator=True)
async def unnamelock_user(ctx, user: discord.Member):
    """Remove namelock from a user"""
    if is_user_blocked(ctx.author.id):
        return
    
    if user.id not in namelocked_users:
        embed = discord.Embed(
            title="❌ Not Namelocked",
            description=f"{user.mention} is not currently namelocked.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Remove from namelocked users
    del namelocked_users[user.id]
    
    embed = discord.Embed(
        title="🔓 Namelock Removed",
        description=f"**User:** {user.mention}\nNamelock has been removed.",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Unlocked by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)
    logger.info(f"Removed namelock from {user.name} in {ctx.guild.name}")

@bot.command(name='namelock_immune', help='Make a user immune to namelock enforcement (Admin only)')
@commands.has_permissions(administrator=True)
async def namelock_immune(ctx, user: discord.Member):
    """Make a user immune to namelock enforcement"""
    if is_user_blocked(ctx.author.id):
        return
    
    namelock_immune_users.add(user.id)
    
    embed = discord.Embed(
        title="🛡️ Namelock Immunity Granted",
        description=f"**User:** {user.mention}\nThis user is now immune to namelock enforcement.",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Granted by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='remove_immunity', help='Remove namelock immunity from a user (Admin only)')
@commands.has_permissions(administrator=True)
async def remove_immunity(ctx, user: discord.Member):
    """Remove namelock immunity from a user"""
    if is_user_blocked(ctx.author.id):
        return
    
    if user.id not in namelock_immune_users:
        embed = discord.Embed(
            title="❌ Not Immune",
            description=f"{user.mention} doesn't have namelock immunity.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    namelock_immune_users.remove(user.id)
    
    embed = discord.Embed(
        title="🛡️ Namelock Immunity Removed",
        description=f"**User:** {user.mention}\nNamelock immunity has been removed.",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Removed by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='block', help='Block a user from using bot commands (Owner only)')
async def block_user(ctx, user: discord.Member):
    """Block a user from using bot commands"""
    if not is_bot_owner(ctx.author.id):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only the bot owner can use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    blocked_users.add(user.id)
    
    embed = discord.Embed(
        title="🚫 User Blocked",
        description=f"**User:** {user.mention}\nThis user has been blocked from using bot commands.",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Blocked by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='unblock', help='Unblock a user (Owner only)')
async def unblock_user(ctx, user: discord.Member):
    """Unblock a user"""
    if not is_bot_owner(ctx.author.id):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only the bot owner can use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    if user.id not in blocked_users:
        embed = discord.Embed(
            title="❌ Not Blocked",
            description=f"{user.mention} is not currently blocked.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    blocked_users.remove(user.id)
    
    embed = discord.Embed(
        title="✅ User Unblocked",
        description=f"**User:** {user.mention}\nThis user has been unblocked.",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Unblocked by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='prefix', help='Change the bot prefix for this server (Admin only)')
@commands.has_permissions(administrator=True)
async def change_prefix(ctx, new_prefix):
    """Change the bot prefix for the current server"""
    if is_user_blocked(ctx.author.id):
        return
    
    if len(new_prefix) > 5:
        embed = discord.Embed(
            title="❌ Invalid Prefix",
            description="Prefix must be 5 characters or less.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    custom_prefixes[ctx.guild.id] = new_prefix
    
    embed = discord.Embed(
        title="✅ Prefix Changed",
        description=f"Bot prefix for this server has been changed to: `{new_prefix}`",
        color=discord.Color.green(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text=f"Changed by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

# Utility commands
@bot.command(name='uptime', help='Show bot uptime')
async def uptime_command(ctx):
    """Show how long the bot has been running"""
    if is_user_blocked(ctx.author.id):
        return
    
    current_time = time.time()
    uptime_seconds = current_time - BOT_START_TIME
    
    embed = discord.Embed(
        title="⏰ Bot Uptime",
        description=f"**Uptime:** {format_uptime(uptime_seconds)}",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    await ctx.send(embed=embed)

@bot.command(name='ping', help='Show bot latency')
async def ping_command(ctx):
    """Show bot latency"""
    if is_user_blocked(ctx.author.id):
        return
    
    latency = round(bot.latency * 1000, 2)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"**Latency:** {latency}ms",
        color=discord.Color.green() if latency < 100 else discord.Color.yellow() if latency < 200 else discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    
    await ctx.send(embed=embed)

@bot.command(name='stats', help='Show bot statistics')
async def stats_command(ctx):
    """Show bot statistics"""
    if is_user_blocked(ctx.author.id):
        return
    
    # Calculate stats
    total_members = sum(len(guild.members) for guild in bot.guilds)
    total_channels = sum(len(guild.channels) for guild in bot.guilds)
    total_sniped = sum(len(messages) for messages in sniped_messages.values())
    total_edited = sum(len(messages) for messages in edited_messages.values())
    
    embed = discord.Embed(
        title="📊 Bot Statistics",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(
        name="🌐 Server Stats",
        value=f"**Servers:** {len(bot.guilds)}\n"
              f"**Members:** {total_members:,}\n"
              f"**Channels:** {total_channels:,}",
        inline=True
    )
    
    embed.add_field(
        name="💬 Message Stats",
        value=f"**Sniped Messages:** {total_sniped:,}\n"
              f"**Edited Messages:** {total_edited:,}\n"
              f"**Active Giveaways:** {len(active_giveaways)}",
        inline=True
    )
    
    embed.add_field(
        name="⚙️ System",
        value=f"**Uptime:** {format_uptime(time.time() - BOT_START_TIME)}\n"
              f"**Latency:** {round(bot.latency * 1000, 2)}ms\n"
              f"**Discord.py:** {discord.__version__}",
        inline=True
    )
    
    await ctx.send(embed=embed)

# Giveaway commands (simplified version - add the full giveaway system here)
@bot.command(name='giveaway_quick', help='Start a quick giveaway')
@commands.has_permissions(administrator=True)
async def quick_giveaway(ctx, duration, *, prize):
    """Start a quick giveaway"""
    if is_user_blocked(ctx.author.id):
        return
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        embed = discord.Embed(
            title="❌ Invalid Duration",
            description="Please use format like: 1h, 30m, 2d, etc.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Create giveaway embed
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n"
                   f"**Duration:** {format_duration(duration_seconds)}\n"
                   f"**Ends:** <t:{int(end_time.timestamp())}:R>\n"
                   f"**Hosted by:** {ctx.author.mention}",
        color=discord.Color.gold(),
        timestamp=end_time
    )
    
    embed.set_footer(text="Click the button below to join!")
    
    # Send message with view
    view = GiveawayView(None)  # Will be set after message is sent
    message = await ctx.send(embed=embed, view=view)
    
    # Store giveaway data
    active_giveaways[message.id] = {
        'prize': prize,
        'end_time': end_time,
        'host': ctx.author.id,
        'channel': ctx.channel.id,
        'participants': [],
        'requirements': None
    }
    
    # Update view with message ID
    view.message_id = message.id

# Message commands
@bot.command(name='say', help='Make the bot say something (Admin only)')
@commands.has_permissions(administrator=True)
async def say_command(ctx, *, message):
    """Make the bot say something"""
    if is_user_blocked(ctx.author.id):
        return
    
    await ctx.message.delete()
    await ctx.send(message)

@bot.command(name='embed', help='Create an embed (Admin only)')
@commands.has_permissions(administrator=True)
async def embed_command(ctx, title, *, description):
    """Create an embed"""
    if is_user_blocked(ctx.author.id):
        return
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    embed.set_footer(text=f"Created by {ctx.author}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='clear', help='Delete messages (Admin only)')
@commands.has_permissions(manage_messages=True)
async def clear_messages(ctx, amount: int):
    """Delete a specified number of messages"""
    if is_user_blocked(ctx.author.id):
        return
    
    if amount <= 0 or amount > 100:
        embed = discord.Embed(
            title="❌ Invalid Amount",
            description="Please specify a number between 1 and 100.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include command message
    
    embed = discord.Embed(
        title="🗑️ Messages Cleared",
        description=f"Deleted {len(deleted) - 1} messages.",
        color=discord.Color.green()
    )
    
    msg = await ctx.send(embed=embed)
    await asyncio.sleep(3)
    await msg.delete()

# Fun commands
@bot.command(name='8ball', help='Ask the magic 8-ball a question')
async def eight_ball(ctx, *, question):
    """Ask the magic 8-ball a question"""
    if is_user_blocked(ctx.author.id):
        return
    
    responses = [
        "It is certain", "Reply hazy, try again", "Don't count on it",
        "It is decidedly so", "Ask again later", "My reply is no",
        "Without a doubt", "Better not tell you now", "My sources say no",
        "Yes definitely", "Cannot predict now", "Outlook not so good",
        "You may rely on it", "Concentrate and ask again", "Very doubtful"
    ]
    
    embed = discord.Embed(
        title="🎱 Magic 8-Ball",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="Question", value=question, inline=False)
    embed.add_field(name="Answer", value=random.choice(responses), inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name='coinflip', help='Flip a coin')
async def coin_flip(ctx):
    """Flip a coin"""
    if is_user_blocked(ctx.author.id):
        return
    
    result = random.choice(["Heads", "Tails"])
    emoji = "🪙" if result == "Heads" else "🌊"
    
    embed = discord.Embed(
        title=f"{emoji} Coin Flip",
        description=f"**Result:** {result}",
        color=discord.Color.gold()
    )
    
    await ctx.send(embed=embed)

@bot.command(name='roll', help='Roll a dice')
async def roll_dice(ctx, sides: int = 6):
    """Roll a dice with specified number of sides"""
    if is_user_blocked(ctx.author.id):
        return
    
    if sides < 2 or sides > 100:
        embed = discord.Embed(
            title="❌ Invalid Dice",
            description="Dice must have between 2 and 100 sides.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    result = random.randint(1, sides)
    
    embed = discord.Embed(
        title="🎲 Dice Roll",
        description=f"**Rolled a {sides}-sided dice**\n**Result:** {result}",
        color=discord.Color.blue()
    )
    
    await ctx.send(embed=embed)

# Owner-only commands
@bot.command(name='shutdown', help='Shutdown the bot (Owner only)')
async def shutdown_bot(ctx):
    """Shutdown the bot"""
    if not is_bot_owner(ctx.author.id):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only the bot owner can use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="🔌 Shutting Down",
        description="Bot is shutting down...",
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    
    await ctx.send(embed=embed)
    await bot.close()

# Error handling
@bot.event
async def on_command_error(ctx, error):
    """Handle command errors"""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignore unknown commands
    
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description="You don't have permission to use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="❌ Missing Arguments",
            description=f"Missing required argument: `{error.param.name}`",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    elif isinstance(error, commands.BadArgument):
        embed = discord.Embed(
            title="❌ Invalid Arguments",
            description="One or more arguments are invalid.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    else:
        logger.error(f"Unhandled error: {error}")
        embed = discord.Embed(
            title="❌ An Error Occurred",
            description="An unexpected error occurred while processing your command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# Keep the bot running
if __name__ == "__main__":
    run_flask()
    bot.run(os.getenv('DISCORD_TOKEN'))
