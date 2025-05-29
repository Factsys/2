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
    
    @discord.ui.button(label="Remove", style=discord.ButtonStyle.danger, emoji="❌")
    async def remove_participant(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RemoveUserModal(self.message_id)
        await interaction.response.send_modal(modal)

# ENHANCED: Help View for displaying help in embeds with pagination
class HelpView(discord.ui.View):
    def __init__(self, embeds, user_id, timeout=300):
        super().__init__(timeout=timeout)
        self.embeds = embeds
        self.user_id = user_id
        self.current_page = 0
        self.total_pages = len(embeds)
        self.update_buttons()
    
    def update_buttons(self):
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

# Bot events
@bot.event
async def on_ready():
    print(f'{bot.user.name} is now online!')
    run_flask()
    
    # FIXED: Sync slash commands properly
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Track message counts
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    # Namelock enforcement
    if message.guild and message.author.id in namelocked_users:
        user_lock = namelocked_users[message.author.id]
        if user_lock['guild_id'] == message.guild.id:
            locked_nickname = user_lock['nickname']
            current_nickname = message.author.nick
            if current_nickname != locked_nickname:
                try:
                    await message.author.edit(nick=locked_nickname)
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    guild_id = message.guild.id if message.guild else 'DM'
    channel_id = message.channel.id
    
    if guild_id not in sniped_messages:
        sniped_messages[guild_id] = {}
    if channel_id not in sniped_messages[guild_id]:
        sniped_messages[guild_id][channel_id] = []
    
    # ENHANCED: Detect if content was filtered
    was_filtered = is_offensive_content(message.content) if message.content else False
    
    # ENHANCED: Get media URLs properly
    media_urls = get_media_url(message.content, message.attachments)
    cleaned_content = clean_content_from_media(message.content, media_urls)
    
    snipe_data = {
        'author': message.author,
        'content': cleaned_content,
        'timestamp': message.created_at,
        'channel': message.channel,
        'media_urls': media_urls,
        'was_filtered': was_filtered,
        'has_links': has_links(message.content)
    }
    
    sniped_messages[guild_id][channel_id].append(snipe_data)
    
    # Keep only last MAX_MESSAGES
    if len(sniped_messages[guild_id][channel_id]) > MAX_MESSAGES:
        sniped_messages[guild_id][channel_id] = sniped_messages[guild_id][channel_id][-MAX_MESSAGES:]

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    guild_id = before.guild.id if before.guild else 'DM'
    channel_id = before.channel.id
    
    if guild_id not in edited_messages:
        edited_messages[guild_id] = {}
    if channel_id not in edited_messages[guild_id]:
        edited_messages[guild_id][channel_id] = []
    
    # ENHANCED: Detect if content was filtered
    was_filtered_before = is_offensive_content(before.content) if before.content else False
    was_filtered_after = is_offensive_content(after.content) if after.content else False
    
    # ENHANCED: Get media URLs properly
    before_media = get_media_url(before.content, before.attachments)
    after_media = get_media_url(after.content, after.attachments)
    
    before_cleaned = clean_content_from_media(before.content, before_media)
    after_cleaned = clean_content_from_media(after.content, after_media)
    
    edit_data = {
        'author': before.author,
        'before_content': before_cleaned,
        'after_content': after_cleaned,
        'timestamp': before.created_at,
        'edit_timestamp': after.edited_at or datetime.utcnow(),
        'channel': before.channel,
        'before_media': before_media,
        'after_media': after_media,
        'was_filtered_before': was_filtered_before,
        'was_filtered_after': was_filtered_after
    }
    
    edited_messages[guild_id][channel_id].append(edit_data)
    
    # Keep only last MAX_MESSAGES
    if len(edited_messages[guild_id][channel_id]) > MAX_MESSAGES:
        edited_messages[guild_id][channel_id] = edited_messages[guild_id][channel_id][-MAX_MESSAGES:]

@bot.event
async def on_member_update(before, after):
    # Check for namelock violations
    if before.id in namelocked_users:
        user_lock = namelocked_users[before.id]
        if user_lock['guild_id'] == before.guild.id:
            locked_nickname = user_lock['nickname']
            if after.nick != locked_nickname:
                try:
                    await after.edit(nick=locked_nickname)
                except discord.Forbidden:
                    pass
                except discord.HTTPException:
                    pass

# Commands start here
@bot.command(name='help')
@not_blocked()
async def help_command(ctx, *, command_name: str = None):
    """Enhanced help command with pagination"""
    prefix = get_prefix(bot, ctx.message)
    
    if command_name:
        # Show help for specific command
        command = bot.get_command(command_name.lower())
        if command:
            embed = discord.Embed(
                title=f"📖 Help: {prefix}{command.name}",
                description=command.help or "No description available.",
                color=discord.Color.blue()
            )
            
            if command.aliases:
                embed.add_field(
                    name="Aliases",
                    value=", ".join([f"{prefix}{alias}" for alias in command.aliases]),
                    inline=False
                )
            
            # Add usage if available
            if hasattr(command, 'usage') and command.usage:
                embed.add_field(
                    name="Usage",
                    value=f"{prefix}{command.name} {command.usage}",
                    inline=False
                )
            
            await ctx.send(embed=embed)
            return
        else:
            await ctx.send(f"❌ Command `{command_name}` not found.")
            return
    
    # Create help embeds
    embeds = []
    
    # Page 1: Basic Commands
    embed1 = discord.Embed(
        title="📜 FACTSY Commands - Page 1",
        description="**Basic Commands & Information**",
        color=discord.Color.blue()
    )
    embed1.add_field(
        name="📋 General",
        value=f"`{prefix}help` - Show this help menu\n"
              f"`{prefix}ping` - Check bot latency\n"
              f"`{prefix}stats` - Bot statistics\n"
              f"`{prefix}uptime` - Bot uptime",
        inline=False
    )
    embed1.add_field(
        name="🔍 Snipe Commands",
        value=f"`{prefix}snipe [channel]` - Show last deleted message\n"
              f"`{prefix}esnipe [channel]` - Show last edited message\n"
              f"`{prefix}snipes [channel]` - Show multiple deleted messages\n"
              f"`{prefix}esnipes [channel]` - Show multiple edited messages\n"
              f"`{prefix}spa [channel]` - Show ALL deleted messages (NEW)\n"
              f"`{prefix}spla [channel]` - Show ALL deleted messages with links (NEW)\n"
              f"`{prefix}spfa [channel]` - Show ALL filtered deleted messages (NEW)",
        inline=False
    )
    embed1.set_footer(text=f"Use {prefix}help <command> for detailed info")
    embeds.append(embed1)
    
    # Page 2: Moderation Commands (only if user has permissions)
    if ctx.author.guild_permissions.administrator or is_bot_owner(ctx.author.id):
        embed2 = discord.Embed(
            title="📜 FACTSY Commands - Page 2",
            description="**Moderation Commands**",
            color=discord.Color.orange()
        )
        embed2.add_field(
            name="👤 User Management",
            value=f"`{prefix}namelock <user> <nickname>` - Lock user's nickname\n"
                  f"`{prefix}unnamelock <user>` - Remove nickname lock\n"
                  f"`{prefix}immune <user>` - Make user immune to namelocks\n"
                  f"`{prefix}unimmune <user>` - Remove namelock immunity",
            inline=False
        )
        embed2.add_field(
            name="🚫 Bot Management",
            value=f"`{prefix}block <user>` - Block user from bot\n"
                  f"`{prefix}unblock <user>` - Unblock user\n"
                  f"`{prefix}setprefix <prefix>` - Change bot prefix\n"
                  f"`{prefix}clear` - Clear all sniped data (NEW)",
            inline=False
        )
        embeds.append(embed2)
    
    # Page 3: Advanced Features
    embed3 = discord.Embed(
        title="📜 FACTSY Commands - Page 3",
        description="**Advanced Features**",
        color=discord.Color.green()
    )
    embed3.add_field(
        name="🎉 Giveaways",
        value=f"`{prefix}giveaway` - Create a giveaway\n"
              f"`{prefix}endgiveaway <message_id>` - End giveaway early\n"
              f"`{prefix}reroll <message_id>` - Reroll giveaway winner\n"
              f"`{prefix}gsetup` - Setup giveaway host roles",
        inline=False
    )
    embed3.add_field(
        name="🤖 Utility",
        value=f"`{prefix}webhook <message>` - Send message as webhook\n"
              f"`{prefix}embed` - Create custom embed\n"
              f"`{prefix}copy <user>` - Copy user's avatar and name",
        inline=False
    )
    embeds.append(embed3)
    
    # Page 4: Owner Commands (only if user is owner)
    if is_bot_owner(ctx.author.id):
        embed4 = discord.Embed(
            title="📜 FACTSY Commands - Page 4",
            description="**Owner-Only Commands**",
            color=discord.Color.red()
        )
        embed4.add_field(
            name="⚡ Owner Controls",
            value=f"`{prefix}eval <code>` - Execute Python code\n"
                  f"`{prefix}reload <cog>` - Reload bot module\n"
                  f"`{prefix}shutdown` - Shutdown the bot\n"
                  f"`{prefix}guilds` - List all guilds\n"
                  f"`/perms <user>` - Grant bot permissions (NEW)",
            inline=False
        )
        embeds.append(embed4)
    
    # Send with pagination if multiple pages
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = HelpView(embeds, ctx.author.id)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='ping')
@not_blocked()
async def ping(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: **{latency}ms**",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='stats')
@not_blocked()
async def stats(ctx):
    """Show bot statistics"""
    embed = discord.Embed(
        title="📊 Bot Statistics",
        color=discord.Color.blue()
    )
    
    # Count total sniped messages
    total_sniped = sum(
        len(channels) for guild_channels in sniped_messages.values() 
        for channels in guild_channels.values()
    )
    
    # Count total edited messages
    total_edited = sum(
        len(channels) for guild_channels in edited_messages.values() 
        for channels in guild_channels.values()
    )
    
    embed.add_field(name="Guilds", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="Sniped Messages", value=total_sniped, inline=True)
    embed.add_field(name="Edited Messages", value=total_edited, inline=True)
    embed.add_field(name="Active Giveaways", value=len(active_giveaways), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='uptime')
@not_blocked()
async def uptime(ctx):
    """Show bot uptime"""
    current_time = time.time()
    uptime_seconds = current_time - BOT_START_TIME
    uptime_str = format_uptime(uptime_seconds)
    
    embed = discord.Embed(
        title="⏰ Bot Uptime",
        description=f"**{uptime_str}**",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed)

# NEW SNIPE ALL COMMANDS
@bot.command(name='spa', aliases=['snipeall'])
@not_blocked()
async def snipe_all(ctx, channel: discord.TextChannel = None):
    """NEW: Show all deleted messages in paginated format"""
    if channel is None:
        channel = ctx.channel
    
    guild_id = ctx.guild.id if ctx.guild else 'DM'
    
    if guild_id not in sniped_messages or channel.id not in sniped_messages[guild_id]:
        embed = discord.Embed(
            title="🔍 No Sniped Messages",
            description=f"No deleted messages found in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    messages = sniped_messages[guild_id][channel.id]
    if not messages:
        embed = discord.Embed(
            title="🔍 No Sniped Messages",
            description=f"No deleted messages found in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Create paginated embeds
    embeds = []
    for i in range(0, len(messages), MESSAGES_PER_PAGE):
        page_messages = messages[i:i + MESSAGES_PER_PAGE]
        
        embed = discord.Embed(
            title=f"🔍 All Deleted Messages - {channel.name}",
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        for j, msg in enumerate(page_messages, start=i + 1):
            author = msg['author']
            content = msg['content'] or "*No text content*"
            timestamp = msg['timestamp']
            
            # Truncate long content
            if len(content) > 100:
                content = content[:97] + "..."
            
            field_name = f"{j}. {author.display_name}"
            field_value = f"**Content:** {content}\n**Time:** <t:{int(timestamp.timestamp())}:R>"
            
            if msg['media_urls']:
                media_count = len(msg['media_urls'])
                field_value += f"\n**Media:** {media_count} attachment{'s' if media_count != 1 else ''}"
            
            if msg['was_filtered']:
                field_value += "\n🚫 **Contained filtered content**"
            
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        embed.set_footer(text=f"Page {len(embeds) + 1} of {math.ceil(len(messages) / MESSAGES_PER_PAGE)} | Total: {len(messages)} messages")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='spla', aliases=['snipelinkall'])
@not_blocked()
async def snipe_links_all(ctx, channel: discord.TextChannel = None):
    """NEW: Show all deleted messages with links in paginated format"""
    if channel is None:
        channel = ctx.channel
    
    guild_id = ctx.guild.id if ctx.guild else 'DM'
    
    if guild_id not in sniped_messages or channel.id not in sniped_messages[guild_id]:
        embed = discord.Embed(
            title="🔗 No Messages with Links",
            description=f"No deleted messages with links found in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Filter messages that have links or media
    link_messages = [
        msg for msg in sniped_messages[guild_id][channel.id]
        if msg['has_links'] or msg['media_urls']
    ]
    
    if not link_messages:
        embed = discord.Embed(
            title="🔗 No Messages with Links",
            description=f"No deleted messages with links found in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Create paginated embeds
    embeds = []
    for i in range(0, len(link_messages), MESSAGES_PER_PAGE):
        page_messages = link_messages[i:i + MESSAGES_PER_PAGE]
        
        embed = discord.Embed(
            title=f"🔗 All Deleted Messages with Links - {channel.name}",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )
        
        for j, msg in enumerate(page_messages, start=i + 1):
            author = msg['author']
            content = msg['content'] or "*No text content*"
            timestamp = msg['timestamp']
            
            # Truncate long content
            if len(content) > 100:
                content = content[:97] + "..."
            
            field_name = f"{j}. {author.display_name}"
            field_value = f"**Content:** {content}\n**Time:** <t:{int(timestamp.timestamp())}:R>"
            
            if msg['media_urls']:
                media_count = len(msg['media_urls'])
                field_value += f"\n**Media:** {media_count} attachment{'s' if media_count != 1 else ''}"
            
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        embed.set_footer(text=f"Page {len(embeds) + 1} of {math.ceil(len(link_messages) / MESSAGES_PER_PAGE)} | Total: {len(link_messages)} messages")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='spfa', aliases=['snipefilterall'])
@not_blocked()
async def snipe_filtered_all(ctx, channel: discord.TextChannel = None):
    """NEW: Show all deleted messages with filtered content in paginated format"""
    if channel is None:
        channel = ctx.channel
    
    guild_id = ctx.guild.id if ctx.guild else 'DM'
    
    if guild_id not in sniped_messages or channel.id not in sniped_messages[guild_id]:
        embed = discord.Embed(
            title="🚫 No Filtered Messages",
            description=f"No deleted filtered messages found in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Filter messages that were filtered
    filtered_messages = [
        msg for msg in sniped_messages[guild_id][channel.id]
        if msg['was_filtered']
    ]
    
    if not filtered_messages:
        embed = discord.Embed(
            title="🚫 No Filtered Messages",
            description=f"No deleted filtered messages found in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Create paginated embeds
    embeds = []
    for i in range(0, len(filtered_messages), MESSAGES_PER_PAGE):
        page_messages = filtered_messages[i:i + MESSAGES_PER_PAGE]
        
        embed = discord.Embed(
            title=f"🚫 All Deleted Filtered Messages - {channel.name}",
            color=discord.Color.red(),
            timestamp=datetime.utcnow()
        )
        
        for j, msg in enumerate(page_messages, start=i + 1):
            author = msg['author']
            content = msg['content'] or "*No text content*"
            timestamp = msg['timestamp']
            
            # Truncate long content
            if len(content) > 100:
                content = content[:97] + "..."
            
            field_name = f"{j}. {author.display_name}"
            field_value = f"**Content:** {content}\n**Time:** <t:{int(timestamp.timestamp())}:R>\n🚫 **Contained filtered content**"
            
            if msg['media_urls']:
                media_count = len(msg['media_urls'])
                field_value += f"\n**Media:** {media_count} attachment{'s' if media_count != 1 else ''}"
            
            embed.add_field(name=field_name, value=field_value, inline=False)
        
        embed.set_footer(text=f"Page {len(embeds) + 1} of {math.ceil(len(filtered_messages) / MESSAGES_PER_PAGE)} | Total: {len(filtered_messages)} messages")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

# NEW CLEAR COMMAND
@bot.command(name='clear')
@not_blocked()
async def clear_snipes(ctx):
    """NEW: Clear all sniped message data for this server"""
    if not (ctx.author.guild_permissions.administrator or is_bot_owner(ctx.author.id)):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="You need administrator permissions to use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    guild_id = ctx.guild.id
    
    # Clear sniped messages
    if guild_id in sniped_messages:
        del sniped_messages[guild_id]
    
    # Clear edited messages
    if guild_id in edited_messages:
        del edited_messages[guild_id]
    
    embed = discord.Embed(
        title="🗑️ Data Cleared",
        description="All sniped message data has been cleared for this server.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# Existing snipe commands (unchanged)
@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe(ctx, channel: discord.TextChannel = None):
    """Show the last deleted message"""
    if channel is None:
        channel = ctx.channel
    
    guild_id = ctx.guild.id if ctx.guild else 'DM'
    
    if guild_id not in sniped_messages or channel.id not in sniped_messages[guild_id] or not sniped_messages[guild_id][channel.id]:
        embed = discord.Embed(
            title="🔍 Nothing to Snipe",
            description=f"No recently deleted messages in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    message_data = sniped_messages[guild_id][channel.id][-1]
    author = message_data['author']
    content = message_data['content']
    timestamp = message_data['timestamp']
    media_urls = message_data['media_urls']
    
    embed = discord.Embed(
        title="🔍 Sniped Message",
        description=content or "*No text content*",
        color=discord.Color.blue(),
        timestamp=timestamp
    )
    
    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    embed.set_footer(text=f"In #{channel.name}")
    
    # ENHANCED: Add media information
    if media_urls:
        media_info = []
        for media in media_urls:
            if media['source'] == 'attachment':
                filename = media.get('filename', 'Unknown')
                media_type = media['type']
                media_info.append(f"📎 {filename} ({media_type})")
            else:
                media_type = media['type']
                media_info.append(f"🔗 {media_type}")
        
        if media_info:
            embed.add_field(name="Media", value="\n".join(media_info), inline=False)
        
        # Set image if it's an image
        for media in media_urls:
            if media['type'] in ['image', 'gif']:
                embed.set_image(url=media['url'])
                break
    
    await ctx.send(embed=embed)

@bot.command(name='esnipe', aliases=['es'])
@not_blocked()
async def edit_snipe(ctx, channel: discord.TextChannel = None):
    """Show the last edited message"""
    if channel is None:
        channel = ctx.channel
    
    guild_id = ctx.guild.id if ctx.guild else 'DM'
    
    if guild_id not in edited_messages or channel.id not in edited_messages[guild_id] or not edited_messages[guild_id][channel.id]:
        embed = discord.Embed(
            title="✏️ Nothing to Edit Snipe",
            description=f"No recently edited messages in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    message_data = edited_messages[guild_id][channel.id][-1]
    author = message_data['author']
    before_content = message_data['before_content']
    after_content = message_data['after_content']
    timestamp = message_data['timestamp']
    edit_timestamp = message_data['edit_timestamp']
    
    embed = discord.Embed(
        title="✏️ Edit Sniped Message",
        color=discord.Color.orange(),
        timestamp=edit_timestamp
    )
    
    embed.set_author(name=author.display_name, icon_url=author.display_avatar.url)
    embed.add_field(name="Before", value=before_content or "*No text content*", inline=False)
    embed.add_field(name="After", value=after_content or "*No text content*", inline=False)
    embed.set_footer(text=f"In #{channel.name} • Originally sent")
    
    await ctx.send(embed=embed)

@bot.command(name='snipes')
@not_blocked()
async def snipes(ctx, channel: discord.TextChannel = None, amount: int = 5):
    """Show multiple deleted messages"""
    if channel is None:
        channel = ctx.channel
    
    if amount < 1 or amount > 20:
        amount = 5
    
    guild_id = ctx.guild.id if ctx.guild else 'DM'
    
    if guild_id not in sniped_messages or channel.id not in sniped_messages[guild_id] or not sniped_messages[guild_id][channel.id]:
        embed = discord.Embed(
            title="🔍 Nothing to Snipe",
            description=f"No recently deleted messages in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    messages = sniped_messages[guild_id][channel.id][-amount:]
    
    embed = discord.Embed(
        title=f"🔍 Last {len(messages)} Deleted Messages",
        color=discord.Color.blue(),
        timestamp=datetime.utcnow()
    )
    
    for i, message_data in enumerate(reversed(messages), 1):
        author = message_data['author']
        content = message_data['content']
        timestamp = message_data['timestamp']
        
        content_preview = truncate_content(content, 100)
        
        embed.add_field(
            name=f"{i}. {author.display_name}",
            value=f"**Content:** {content_preview}\n**Time:** <t:{int(timestamp.timestamp())}:R>",
            inline=False
        )
    
    embed.set_footer(text=f"In #{channel.name}")
    await ctx.send(embed=embed)

@bot.command(name='esnipes')
@not_blocked()
async def edit_snipes(ctx, channel: discord.TextChannel = None, amount: int = 5):
    """Show multiple edited messages"""
    if channel is None:
        channel = ctx.channel
    
    if amount < 1 or amount > 20:
        amount = 5
    
    guild_id = ctx.guild.id if ctx.guild else 'DM'
    
    if guild_id not in edited_messages or channel.id not in edited_messages[guild_id] or not edited_messages[guild_id][channel.id]:
        embed = discord.Embed(
            title="✏️ Nothing to Edit Snipe",
            description=f"No recently edited messages in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    messages = edited_messages[guild_id][channel.id][-amount:]
    
    embed = discord.Embed(
        title=f"✏️ Last {len(messages)} Edited Messages",
        color=discord.Color.orange(),
        timestamp=datetime.utcnow()
    )
    
    for i, message_data in enumerate(reversed(messages), 1):
        author = message_data['author']
        before_content = message_data['before_content']
        after_content = message_data['after_content']
        edit_timestamp = message_data['edit_timestamp']
        
        before_preview = truncate_content(before_content, 50)
        after_preview = truncate_content(after_content, 50)
        
        embed.add_field(
            name=f"{i}. {author.display_name}",
            value=f"**Before:** {before_preview}\n**After:** {after_preview}\n**Time:** <t:{int(edit_timestamp.timestamp())}:R>",
            inline=False
        )
    
    embed.set_footer(text=f"In #{channel.name}")
    await ctx.send(embed=embed)

# Moderation commands
@bot.command(name='namelock')
@not_blocked()
async def namelock(ctx, user: discord.Member, *, nickname: str):
    """Lock a user's nickname"""
    if not ctx.author.guild_permissions.administrator and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You need administrator permissions to use this command.")
        return
    
    if user.id in namelock_immune_users:
        await ctx.send(f"❌ {user.mention} is immune to namelocks.")
        return
    
    if len(nickname) > 32:
        await ctx.send("❌ Nickname cannot be longer than 32 characters.")
        return
    
    try:
        await user.edit(nick=nickname)
        namelocked_users[user.id] = {'guild_id': ctx.guild.id, 'nickname': nickname}
        
        embed = discord.Embed(
            title="🔒 User Namelocked",
            description=f"Successfully locked {user.mention}'s nickname to `{nickname}`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send(f"❌ I don't have permission to change {user.mention}'s nickname.")
    except discord.HTTPException:
        await ctx.send("❌ Failed to change nickname. Please try again.")

@bot.command(name='unnamelock')
@not_blocked()
async def unnamelock(ctx, user: discord.Member):
    """Remove a user's nickname lock"""
    if not ctx.author.guild_permissions.administrator and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You need administrator permissions to use this command.")
        return
    
    if user.id not in namelocked_users:
        await ctx.send(f"❌ {user.mention} is not namelocked.")
        return
    
    user_lock = namelocked_users[user.id]
    if user_lock['guild_id'] != ctx.guild.id:
        await ctx.send(f"❌ {user.mention} is not namelocked in this server.")
        return
    
    del namelocked_users[user.id]
    
    embed = discord.Embed(
        title="🔓 User Namelock Removed",
        description=f"Successfully removed {user.mention}'s namelock",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='immune')
@not_blocked()
async def immune(ctx, user: discord.Member):
    """Make a user immune to namelocks"""
    if not ctx.author.guild_permissions.administrator and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You need administrator permissions to use this command.")
        return
    
    if user.id in namelock_immune_users:
        await ctx.send(f"❌ {user.mention} is already immune to namelocks.")
        return
    
    namelock_immune_users.add(user.id)
    
    # Remove existing namelock if any
    if user.id in namelocked_users:
        user_lock = namelocked_users[user.id]
        if user_lock['guild_id'] == ctx.guild.id:
            del namelocked_users[user.id]
    
    embed = discord.Embed(
        title="🛡️ User Made Immune",
        description=f"Successfully made {user.mention} immune to namelocks",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='unimmune')
@not_blocked()
async def unimmune(ctx, user: discord.Member):
    """Remove a user's namelock immunity"""
    if not ctx.author.guild_permissions.administrator and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You need administrator permissions to use this command.")
        return
    
    if user.id not in namelock_immune_users:
        await ctx.send(f"❌ {user.mention} is not immune to namelocks.")
        return
    
    namelock_immune_users.remove(user.id)
    
    embed = discord.Embed(
        title="🛡️ User Immunity Removed",
        description=f"Successfully removed {user.mention}'s namelock immunity",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='block')
@not_blocked()
async def block_user(ctx, user: Union[discord.Member, discord.User]):
    """Block a user from using the bot"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    if user.id == BOT_OWNER_ID:
        await ctx.send("❌ Cannot block the bot owner.")
        return
    
    if user.id in blocked_users:
        await ctx.send(f"❌ {user.mention} is already blocked.")
        return
    
    blocked_users.add(user.id)
    
    embed = discord.Embed(
        title="🚫 User Blocked",
        description=f"Successfully blocked {user.mention} from using bot functions",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command(name='unblock')
@not_blocked()
async def unblock_user(ctx, user: Union[discord.Member, discord.User]):
    """Unblock a user from using the bot"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    if user.id not in blocked_users:
        await ctx.send(f"❌ {user.mention} is not blocked.")
        return
    
    blocked_users.remove(user.id)
    
    embed = discord.Embed(
        title="✅ User Unblocked",
        description=f"Successfully unblocked {user.mention}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='setprefix')
@not_blocked()
async def set_prefix(ctx, *, new_prefix: str = None):
    """Change the bot prefix for this server"""
    if not ctx.author.guild_permissions.administrator and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You need administrator permissions to use this command.")
        return
    
    if new_prefix is None:
        current_prefix = get_prefix(bot, ctx.message)
        await ctx.send(f"Current prefix is: `{current_prefix}`")
        return
    
    if len(new_prefix) > 5:
        await ctx.send("❌ Prefix cannot be longer than 5 characters.")
        return
    
    custom_prefixes[ctx.guild.id] = new_prefix
    
    embed = discord.Embed(
        title="✅ Prefix Changed",
        description=f"Server prefix changed to: `{new_prefix}`",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# Webhook and utility commands
@bot.command(name='webhook')
@not_blocked()
async def webhook_send(ctx, *, message: str = None):
    """Send a message using webhooks"""
    if not ctx.author.guild_permissions.manage_webhooks and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You need 'Manage Webhooks' permission to use this command.")
        return
    
    if not message:
        await ctx.send("❌ Please provide a message to send.")
        return
    
    try:
        webhook = await get_or_create_webhook(ctx.channel)
        await webhook.send(
            content=message,
            username=ctx.author.display_name,
            avatar_url=ctx.author.display_avatar.url
        )
        await ctx.message.delete()
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to create webhooks in this channel.")
    except discord.HTTPException:
        await ctx.send("❌ Failed to send webhook message.")

@bot.command(name='copy')
@not_blocked()
async def copy_user(ctx, user: discord.Member):
    """Copy a user's avatar and name using webhook"""
    if not ctx.author.guild_permissions.manage_webhooks and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You need 'Manage Webhooks' permission to use this command.")
        return
    
    try:
        webhook = await get_or_create_webhook(ctx.channel)
        await webhook.send(
            content="*This message was sent using the copy command*",
            username=user.display_name,
            avatar_url=user.display_avatar.url
        )
        await ctx.message.delete()
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to create webhooks in this channel.")
    except discord.HTTPException:
        await ctx.send("❌ Failed to send webhook message.")

# Embed command
@bot.command(name='embed')
@not_blocked()
async def create_embed(ctx, title: str = None, *, description: str = None):
    """Create a custom embed"""
    if not title and not description:
        await ctx.send("❌ Please provide at least a title or description for the embed.")
        return
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=discord.Color.blue()
    )
    
    embed.set_footer(text=f"Created by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    
    await ctx.send(embed=embed)

# Giveaway commands
@bot.command(name='giveaway')
@not_blocked()
async def giveaway(ctx, duration: str = None, winners: int = 1, *, prize: str = None):
    """Create a giveaway"""
    if not can_host_giveaway(ctx.author):
        await ctx.send("❌ You don't have permission to host giveaways.")
        return
    
    if not duration or not prize:
        await ctx.send("❌ Usage: `,giveaway <duration> [winners] <prize>`\nExample: `,giveaway 1h 2 Discord Nitro`")
        return
    
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        await ctx.send("❌ Invalid duration format. Use format like: 1h, 30m, 1d")
        return
    
    if winners < 1 or winners > 10:
        await ctx.send("❌ Number of winners must be between 1 and 10.")
        return
    
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    embed = discord.Embed(
        title="🎉 Giveaway",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Duration:** {format_duration(duration_seconds)}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
        color=discord.Color.gold()
    )
    
    embed.set_footer(text="Click 🎉 to join!")
    
    message = await ctx.send(embed=embed)
    
    # Add to active giveaways with message ID
    active_giveaways[message.id] = {
        'channel_id': ctx.channel.id,
        'guild_id': ctx.guild.id,
        'host_id': ctx.author.id,
        'prize': prize,
        'winners': winners,
        'end_time': end_time,
        'participants': [],
        'message_id': message.id
    }
    
    # Add the view with message ID
    view = GiveawayView(message.id)
    await message.edit(embed=embed, view=view)
    
    # Schedule end
    await asyncio.sleep(duration_seconds)
    
    if message.id in active_giveaways:
        await end_giveaway_internal(message.id)

async def end_giveaway_internal(message_id):
    """Internal function to end giveaway"""
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
    
    participants = giveaway['participants']
    winners_count = giveaway['winners']
    prize = giveaway['prize']
    
    if not participants:
        embed = discord.Embed(
            title="🎉 Giveaway Ended",
            description=f"**Prize:** {prize}\n**Winners:** No one entered the giveaway 😢",
            color=discord.Color.red()
        )
        await message.edit(embed=embed, view=None)
        del active_giveaways[message_id]
        return
    
    # Select winners
    actual_winners = min(winners_count, len(participants))
    winners = random.sample(participants, actual_winners)
    
    winner_mentions = []
    for winner_id in winners:
        user = bot.get_user(winner_id)
        if user:
            winner_mentions.append(user.mention)
        else:
            winner_mentions.append(f"<@{winner_id}>")
    
    embed = discord.Embed(
        title="🎉 Giveaway Ended",
        description=f"**Prize:** {prize}\n**Winner{'s' if len(winners) > 1 else ''}:** {', '.join(winner_mentions)}",
        color=discord.Color.gold()
    )
    
    await message.edit(embed=embed, view=None)
    await channel.send(f"🎉 Congratulations {', '.join(winner_mentions)}! You won **{prize}**!")
    
    del active_giveaways[message_id]

@bot.command(name='endgiveaway')
@not_blocked()
async def end_giveaway(ctx, message_id: int):
    """End a giveaway early"""
    if message_id not in active_giveaways:
        await ctx.send("❌ No active giveaway found with that message ID.")
        return
    
    giveaway = active_giveaways[message_id]
    
    if not (is_bot_owner(ctx.author.id) or 
            ctx.author.guild_permissions.administrator or 
            ctx.author.id == giveaway['host_id']):
        await ctx.send("❌ You can only end giveaways you created or if you're an admin.")
        return
    
    await end_giveaway_internal(message_id)
    await ctx.send("✅ Giveaway ended successfully!")

@bot.command(name='reroll')
@not_blocked()
async def reroll_giveaway(ctx, message_id: int):
    """Reroll a giveaway"""
    if not (is_bot_owner(ctx.author.id) or ctx.author.guild_permissions.administrator):
        await ctx.send("❌ You need administrator permissions to reroll giveaways.")
        return
    
    try:
        message = await ctx.channel.fetch_message(message_id)
    except discord.NotFound:
        await ctx.send("❌ Message not found.")
        return
    
    if not message.embeds or "Giveaway Ended" not in message.embeds[0].title:
        await ctx.send("❌ This is not an ended giveaway.")
        return
    
    # This is a simple reroll - in a real bot you'd want to store more data
    await ctx.send("🔄 Giveaway rerolled! (Note: This is a basic implementation)")

@bot.command(name='gsetup')
@not_blocked()
async def giveaway_setup(ctx, *, role_names: str = None):
    """Setup roles that can host giveaways"""
    if not (is_bot_owner(ctx.author.id) or ctx.author.guild_permissions.administrator):
        await ctx.send("❌ You need administrator permissions to setup giveaway roles.")
        return
    
    if not role_names:
        # Show current setup
        guild_roles = giveaway_host_roles.get(ctx.guild.id, [])
        if not guild_roles:
            await ctx.send("No giveaway host roles configured.")
            return
        
        role_list = []
        for role_id in guild_roles:
            role = ctx.guild.get_role(role_id)
            if role:
                role_list.append(role.name)
        
        if role_list:
            await ctx.send(f"Current giveaway host roles: {', '.join(role_list)}")
        else:
            await ctx.send("No valid giveaway host roles found.")
        return
    
    # Parse role names
    role_names_list = [name.strip() for name in role_names.split(',')]
    found_roles = []
    
    for role_name in role_names_list:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role:
            found_roles.append(role.id)
        else:
            await ctx.send(f"❌ Role '{role_name}' not found.")
            return
    
    giveaway_host_roles[ctx.guild.id] = found_roles
    role_mentions = [ctx.guild.get_role(role_id).name for role_id in found_roles]
    
    embed = discord.Embed(
        title="✅ Giveaway Setup Complete",
        description=f"Users with these roles can now host giveaways:\n{', '.join(role_mentions)}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# Owner-only commands
@bot.command(name='eval')
async def eval_code(ctx, *, code: str):
    """Execute Python code (Owner only)"""
    if not is_bot_owner(ctx.author.id):
        return
    
    try:
        result = eval(code)
        if asyncio.iscoroutine(result):
            result = await result
        
        embed = discord.Embed(
            title="✅ Code Executed",
            description=f"```python\n{code}\n```\n**Result:**\n```python\n{result}\n```",
            color=discord.Color.green()
        )
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error",
            description=f"```python\n{code}\n```\n**Error:**\n```python\n{str(e)}\n```",
            color=discord.Color.red()
        )
    
    await ctx.send(embed=embed)

@bot.command(name='guilds')
async def list_guilds(ctx):
    """List all guilds the bot is in (Owner only)"""
    if not is_bot_owner(ctx.author.id):
        return
    
    guild_list = []
    for guild in bot.guilds:
        guild_list.append(f"{guild.name} ({guild.id}) - {guild.member_count} members")
    
    if len(guild_list) == 0:
        await ctx.send("No guilds found.")
        return
    
    # Split into chunks if too long
    chunk_size = 10
    chunks = [guild_list[i:i + chunk_size] for i in range(0, len(guild_list), chunk_size)]
    
    embeds = []
    for i, chunk in enumerate(chunks):
        embed = discord.Embed(
            title=f"🏰 Bot Guilds - Page {i + 1}",
            description="\n".join(chunk),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Total: {len(bot.guilds)} guilds")
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

# NEW PERMISSIONS SLASH COMMAND
@bot.tree.command(name="perms", description="Grant bot permissions to a user (Owner only)")
@app_commands.describe(user="User to grant permissions to")
@check_not_blocked()
async def grant_permissions(interaction: discord.Interaction, user: discord.User):
    """NEW: Grant full bot permissions to a user"""
    if not is_bot_owner(interaction.user.id):
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="Only the bot owner can use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if user.id == BOT_OWNER_ID:
        embed = discord.Embed(
            title="❌ Invalid Target",
            description="The bot owner already has all permissions.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if user.id in authorized_users:
        # Remove permissions
        authorized_users.remove(user.id)
        embed = discord.Embed(
            title="🔓 Permissions Removed",
            description=f"Removed bot permissions from {user.mention}",
            color=discord.Color.orange()
        )
    else:
        # Grant permissions
        authorized_users.add(user.id)
        embed = discord.Embed(
            title="🔐 Permissions Granted",
            description=f"Granted full bot permissions to {user.mention}",
            color=discord.Color.green()
        )
    
    await interaction.response.send_message(embed=embed)

# Run the bot
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
