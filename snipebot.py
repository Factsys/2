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

# Event handlers
@bot.event
async def on_ready():
    run_flask()
    print(f"{bot.user} has connected to Discord!")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []
    
    media_urls = get_media_url(message.content, message.attachments)
    cleaned_content = clean_content_from_media(message.content, media_urls)
    
    snipe_data = {
        'author': message.author,
        'content': cleaned_content,
        'timestamp': datetime.utcnow(),
        'channel': message.channel,
        'guild': message.guild,
        'media_urls': media_urls,
        'has_links': has_links(message.content),
        'is_offensive': is_offensive_content(message.content)
    }
    
    sniped_messages[channel_id].append(snipe_data)
    
    if len(sniped_messages[channel_id]) > MAX_MESSAGES:
        sniped_messages[channel_id] = sniped_messages[channel_id][-MAX_MESSAGES:]

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    if before.content == after.content:
        return
    
    channel_id = before.channel.id
    
    if channel_id not in edited_messages:
        edited_messages[channel_id] = []
    
    before_media_urls = get_media_url(before.content, before.attachments)
    after_media_urls = get_media_url(after.content, after.attachments)
    
    before_cleaned = clean_content_from_media(before.content, before_media_urls)
    after_cleaned = clean_content_from_media(after.content, after_media_urls)
    
    edit_data = {
        'author': before.author,
        'before_content': before_cleaned,
        'after_content': after_cleaned,
        'before_media_urls': before_media_urls,
        'after_media_urls': after_media_urls,
        'timestamp': datetime.utcnow(),
        'channel': before.channel,
        'guild': before.guild,
        'before_has_links': has_links(before.content),
        'after_has_links': has_links(after.content),
        'before_is_offensive': is_offensive_content(before.content),
        'after_is_offensive': is_offensive_content(after.content)
    }
    
    edited_messages[channel_id].append(edit_data)
    
    if len(edited_messages[channel_id]) > MAX_MESSAGES:
        edited_messages[channel_id] = edited_messages[channel_id][-MAX_MESSAGES:]

@bot.event
async def on_member_update(before, after):
    user_id = before.id
    
    if user_id in namelocked_users:
        namelock_data = namelocked_users[user_id]
        guild_id = namelock_data['guild_id']
        locked_nickname = namelock_data['nickname']
        
        if before.guild.id == guild_id:
            if after.display_name != locked_nickname:
                try:
                    await after.edit(nick=locked_nickname, reason="User is name-locked")
                except discord.Forbidden:
                    pass

@bot.event
async def on_member_join(member):
    user_id = member.id
    
    if user_id in namelocked_users:
        namelock_data = namelocked_users[user_id]
        guild_id = namelock_data['guild_id']
        locked_nickname = namelock_data['nickname']
        
        if member.guild.id == guild_id:
            try:
                await member.edit(nick=locked_nickname, reason="User is name-locked")
            except discord.Forbidden:
                pass

# Helper function to create snipe embeds
def create_snipe_embed(snipe_data, index, total):
    author = snipe_data['author']
    content = snipe_data['content']
    timestamp = snipe_data['timestamp']
    media_urls = snipe_data['media_urls']
    
    embed = discord.Embed(
        color=discord.Color.red(),
        timestamp=timestamp
    )
    
    embed.set_author(
        name=f"{author.display_name} ({author.name})",
        icon_url=author.display_avatar.url
    )
    
    embed.set_footer(text=f"Message {index + 1} of {total}")
    
    if content and len(content.strip()) > 0:
        if len(content) > 2048:
            content = content[:2045] + "..."
        embed.description = content
    else:
        embed.description = "*No text content*"
    
    if media_urls:
        media_info = []
        for i, media in enumerate(media_urls[:5]):
            media_type = media.get('type', 'unknown')
            
            if media_type in ['image', 'gif']:
                if i == 0:
                    embed.set_image(url=media['url'])
                media_info.append(f"🖼️ [{media_type.title()}]({media['url']})")
            elif media_type == 'video':
                media_info.append(f"🎥 [Video]({media['url']})")
            elif media_type == 'audio':
                media_info.append(f"🎵 [Audio]({media['url']})")
            elif media_type in ['youtube_video']:
                media_info.append(f"📺 [YouTube]({media['url']})")
            elif media_type in ['tenor_gif', 'giphy_gif']:
                if i == 0:
                    embed.set_image(url=media['url'])
                media_info.append(f"🎭 [GIF]({media['url']})")
            else:
                media_info.append(f"🔗 [Link]({media['url']})")
        
        if len(media_urls) > 5:
            media_info.append(f"... and {len(media_urls) - 5} more")
        
        if media_info:
            embed.add_field(name="Media", value="\n".join(media_info), inline=False)
    
    return embed

# Helper function to create edit embeds
def create_edit_embed(edit_data, index, total):
    author = edit_data['author']
    before_content = edit_data['before_content']
    after_content = edit_data['after_content']
    timestamp = edit_data['timestamp']
    before_media_urls = edit_data['before_media_urls']
    after_media_urls = edit_data['after_media_urls']
    
    embed = discord.Embed(
        color=discord.Color.orange(),
        timestamp=timestamp
    )
    
    embed.set_author(
        name=f"{author.display_name} ({author.name})",
        icon_url=author.display_avatar.url
    )
    
    embed.set_footer(text=f"Edit {index + 1} of {total}")
    
    before_text = before_content if before_content else "*No text content*"
    after_text = after_content if after_content else "*No text content*"
    
    if len(before_text) > 1000:
        before_text = before_text[:997] + "..."
    if len(after_text) > 1000:
        after_text = after_text[:997] + "..."
    
    embed.add_field(name="Before", value=before_text, inline=False)
    embed.add_field(name="After", value=after_text, inline=False)
    
    if before_media_urls or after_media_urls:
        media_info = []
        
        if before_media_urls:
            media_info.append("**Before Media:**")
            for media in before_media_urls[:3]:
                media_type = media.get('type', 'unknown')
                media_info.append(f"🔗 [{media_type.title()}]({media['url']})")
        
        if after_media_urls:
            media_info.append("**After Media:**")
            for media in after_media_urls[:3]:
                media_type = media.get('type', 'unknown')
                media_info.append(f"🔗 [{media_type.title()}]({media['url']})")
                
                if media_type in ['image', 'gif', 'tenor_gif', 'giphy_gif']:
                    embed.set_image(url=media['url'])
        
        if media_info:
            embed.add_field(name="Media", value="\n".join(media_info), inline=False)
    
    return embed

# NEW: Helper function to get all messages for global snipe commands
def get_all_messages_data(filter_type="all"):
    """Get all messages across all channels with filtering"""
    all_messages = []
    
    for channel_id, messages in sniped_messages.items():
        for msg in messages:
            if filter_type == "links" and not msg.get('has_links', False):
                continue
            elif filter_type == "filtered" and not msg.get('is_offensive', False):
                continue
            
            # Add channel info to the message data
            msg_copy = msg.copy()
            msg_copy['channel_id'] = channel_id
            all_messages.append(msg_copy)
    
    # Sort by timestamp (newest first)
    all_messages.sort(key=lambda x: x['timestamp'], reverse=True)
    return all_messages

# Existing snipe commands (keeping all of them)
@bot.command(name='sp')
@not_blocked()
async def snipe(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        embed = discord.Embed(
            title="🔍 No Deleted Messages",
            description=f"No recently deleted messages in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    messages = sniped_messages[channel_id]
    embeds = []
    
    for i, snipe_data in enumerate(messages):
        embed = create_snipe_embed(snipe_data, i, len(messages))
        embed.title = f"🔍 Deleted Message in {channel.name}"
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='spl')
@not_blocked()
async def snipe_links(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages:
        embed = discord.Embed(
            title="🔗 No Deleted Messages with Links",
            description=f"No recently deleted messages with links in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    link_messages = [msg for msg in sniped_messages[channel_id] if msg.get('has_links', False)]
    
    if not link_messages:
        embed = discord.Embed(
            title="🔗 No Deleted Messages with Links",
            description=f"No recently deleted messages with links in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    embeds = []
    
    for i, snipe_data in enumerate(link_messages):
        embed = create_snipe_embed(snipe_data, i, len(link_messages))
        embed.title = f"🔗 Deleted Message with Links in {channel.name}"
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='spf')
@not_blocked()
async def snipe_filtered(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages:
        embed = discord.Embed(
            title="🚫 No Deleted Filtered Messages",
            description=f"No recently deleted filtered messages in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    filtered_messages = [msg for msg in sniped_messages[channel_id] if msg.get('is_offensive', False)]
    
    if not filtered_messages:
        embed = discord.Embed(
            title="🚫 No Deleted Filtered Messages",
            description=f"No recently deleted filtered messages in {channel.mention}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    embeds = []
    
    for i, snipe_data in enumerate(filtered_messages):
        embed = create_snipe_embed(snipe_data, i, len(filtered_messages))
        embed.title = f"🚫 Deleted Filtered Message in {channel.name}"
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

# NEW: Global snipe commands
@bot.command(name='spa')
@not_blocked()
async def snipe_all(ctx):
    """Show all deleted messages across all channels"""
    all_messages = get_all_messages_data("all")
    
    if not all_messages:
        embed = discord.Embed(
            title="🔍 No Deleted Messages",
            description="No recently deleted messages found across all channels",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    embeds = []
    
    for i, snipe_data in enumerate(all_messages):
        embed = create_snipe_embed(snipe_data, i, len(all_messages))
        channel_name = snipe_data['channel'].name if snipe_data['channel'] else "Unknown Channel"
        embed.title = f"🔍 Deleted Message in #{channel_name}"
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='spla')
@not_blocked()
async def snipe_links_all(ctx):
    """Show all deleted messages with links across all channels"""
    all_messages = get_all_messages_data("links")
    
    if not all_messages:
        embed = discord.Embed(
            title="🔗 No Deleted Messages with Links",
            description="No recently deleted messages with links found across all channels",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    embeds = []
    
    for i, snipe_data in enumerate(all_messages):
        embed = create_snipe_embed(snipe_data, i, len(all_messages))
        channel_name = snipe_data['channel'].name if snipe_data['channel'] else "Unknown Channel"
        embed.title = f"🔗 Deleted Message with Links in #{channel_name}"
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

@bot.command(name='spfa')
@not_blocked()
async def snipe_filtered_all(ctx):
    """Show all deleted filtered messages across all channels"""
    all_messages = get_all_messages_data("filtered")
    
    if not all_messages:
        embed = discord.Embed(
            title="🚫 No Deleted Filtered Messages",
            description="No recently deleted filtered messages found across all channels",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    embeds = []
    
    for i, snipe_data in enumerate(all_messages):
        embed = create_snipe_embed(snipe_data, i, len(all_messages))
        channel_name = snipe_data['channel'].name if snipe_data['channel'] else "Unknown Channel"
        embed.title = f"🚫 Deleted Filtered Message in #{channel_name}"
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

# NEW: Clear command
@bot.command(name='clear')
@not_blocked()
async def clear_snipe_data(ctx):
    """Clear all sniped message data (owner/authorized only)"""
    if not has_bot_permissions(ctx.author.id):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="Only the bot owner or authorized users can use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Clear all data
    sniped_messages.clear()
    edited_messages.clear()
    
    embed = discord.Embed(
        title="🗑️ Data Cleared",
        description="All sniped message data has been cleared successfully.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='editsnipe', aliases=['es'])
@not_blocked()
async def edit_snipe(ctx, channel: discord.TextChannel = None):
    if channel is None:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        embed = discord.Embed(
            title="📝 No Edited Messages",
            description=f"No recently edited messages in {channel.mention}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    messages = edited_messages[channel_id]
    embeds = []
    
    for i, edit_data in enumerate(messages):
        embed = create_edit_embed(edit_data, i, len(messages))
        embed.title = f"📝 Edited Message in {channel.name}"
        embeds.append(embed)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

# Moderation Commands
@bot.command(name='timeout')
@not_blocked()
@commands.has_permissions(moderate_members=True)
async def timeout_user(ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
    """Timeout a user for a specified duration"""
    if member.id == ctx.author.id:
        await ctx.send("❌ You cannot timeout yourself!")
        return
    
    if member.guild_permissions.administrator:
        await ctx.send("❌ Cannot timeout administrators!")
        return
    
    # Parse duration
    seconds = parse_time_string(duration)
    if seconds <= 0 or seconds > 2419200:  # Max 28 days
        await ctx.send("❌ Invalid duration! Use format like `1h`, `30m`, `1d` (max 28 days)")
        return
    
    try:
        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        await member.timeout(until, reason=reason)
        
        duration_str = format_duration(seconds)
        embed = discord.Embed(
            title="⏰ User Timed Out",
            description=f"**{member.mention}** has been timed out for **{duration_str}**",
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Until", value=f"<t:{int(until.timestamp())}:F>", inline=True)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to timeout this user!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='untimeout')
@not_blocked()
@commands.has_permissions(moderate_members=True)
async def untimeout_user(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Remove timeout from a user"""
    try:
        await member.timeout(None, reason=reason)
        
        embed = discord.Embed(
            title="✅ Timeout Removed",
            description=f"**{member.mention}** is no longer timed out",
            color=discord.Color.green()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to modify this user's timeout!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='kick')
@not_blocked()
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick_user(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a user from the server"""
    if member.id == ctx.author.id:
        await ctx.send("❌ You cannot kick yourself!")
        return
    
    if member.guild_permissions.administrator:
        await ctx.send("❌ Cannot kick administrators!")
        return
    
    try:
        await member.kick(reason=reason)
        
        embed = discord.Embed(
            title="👢 User Kicked",
            description=f"**{member}** has been kicked from the server",
            color=discord.Color.orange()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to kick this user!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='ban')
@not_blocked()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban_user(ctx, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a user from the server"""
    if member.id == ctx.author.id:
        await ctx.send("❌ You cannot ban yourself!")
        return
    
    if member.guild_permissions.administrator:
        await ctx.send("❌ Cannot ban administrators!")
        return
    
    try:
        await member.ban(reason=reason)
        
        embed = discord.Embed(
            title="🔨 User Banned",
            description=f"**{member}** has been banned from the server",
            color=discord.Color.red()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to ban this user!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='unban')
@not_blocked()
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def unban_user(ctx, user_id: int, *, reason: str = "No reason provided"):
    """Unban a user by their ID"""
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=reason)
        
        embed = discord.Embed(
            title="✅ User Unbanned",
            description=f"**{user}** has been unbanned from the server",
            color=discord.Color.green()
        )
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
        
    except discord.NotFound:
        await ctx.send("❌ User not found or not banned!")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to unban users!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='purge')
@not_blocked()
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def purge_messages(ctx, amount: int):
    """Delete a specified number of messages"""
    if amount <= 0 or amount > 100:
        await ctx.send("❌ Please specify a number between 1 and 100!")
        return
    
    try:
        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 to include the command message
        
        embed = discord.Embed(
            title="🗑️ Messages Purged",
            description=f"Successfully deleted **{len(deleted) - 1}** messages",
            color=discord.Color.green()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        
        # Send confirmation and delete it after 5 seconds
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(5)
        await msg.delete()
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

# Namelock Commands
@bot.command(name='namelock')
@not_blocked()
@commands.has_permissions(manage_nicknames=True)
@commands.bot_has_permissions(manage_nicknames=True)
async def namelock(ctx, member: discord.Member, *, nickname: str):
    """Lock a user's nickname"""
    if len(nickname) > 32:
        await ctx.send("❌ Nickname too long! Maximum 32 characters.")
        return
    
    if member.id in namelock_immune_users:
        await ctx.send("❌ This user is immune to namelocking!")
        return
    
    try:
        await member.edit(nick=nickname, reason=f"Name locked by {ctx.author}")
        
        namelocked_users[member.id] = {
            'guild_id': ctx.guild.id,
            'nickname': nickname
        }
        
        embed = discord.Embed(
            title="🔒 User Name Locked",
            description=f"**{member.mention}** has been name-locked",
            color=discord.Color.orange()
        )
        embed.add_field(name="Locked Nickname", value=nickname, inline=True)
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='unnamelock')
@not_blocked()
@commands.has_permissions(manage_nicknames=True)
async def unnamelock(ctx, member: discord.Member):
    """Remove namelock from a user"""
    if member.id not in namelocked_users:
        await ctx.send("❌ This user is not name-locked!")
        return
    
    del namelocked_users[member.id]
    
    embed = discord.Embed(
        title="🔓 Name Lock Removed",
        description=f"**{member.mention}** is no longer name-locked",
        color=discord.Color.green()
    )
    embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
    
    await ctx.send(embed=embed)

# Block Commands (Owner Only)
@bot.command(name='block')
async def block_user(ctx, user: discord.User):
    """Block a user from using bot functions (Owner only)"""
    if not is_bot_owner(ctx.author.id):
        return
    
    if user.id == BOT_OWNER_ID:
        await ctx.send("❌ Cannot block the bot owner!")
        return
    
    blocked_users.add(user.id)
    
    embed = discord.Embed(
        title="🚫 User Blocked",
        description=f"**{user}** has been blocked from using bot functions",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command(name='unblock')
async def unblock_user(ctx, user: discord.User):
    """Unblock a user (Owner only)"""
    if not is_bot_owner(ctx.author.id):
        return
    
    if user.id not in blocked_users:
        await ctx.send("❌ This user is not blocked!")
        return
    
    blocked_users.remove(user.id)
    
    embed = discord.Embed(
        title="✅ User Unblocked",
        description=f"**{user}** has been unblocked",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# Webhook Commands
@bot.command(name='say')
@not_blocked()
@commands.has_permissions(manage_messages=True)
async def webhook_say(ctx, *, message):
    """Send a message as a webhook"""
    try:
        await ctx.message.delete()
        webhook = await get_or_create_webhook(ctx.channel)
        await webhook.send(
            content=message,
            username=ctx.author.display_name,
            avatar_url=ctx.author.display_avatar.url
        )
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}", delete_after=5)

@bot.command(name='sayembed')
@not_blocked()
@commands.has_permissions(manage_messages=True)
async def webhook_say_embed(ctx, color: str = None, *, message):
    """Send an embed message as a webhook"""
    try:
        await ctx.message.delete()
        
        embed_color = parse_color(color) if color else discord.Color.blue()
        embed = discord.Embed(description=message, color=embed_color)
        
        webhook = await get_or_create_webhook(ctx.channel)
        await webhook.send(
            embed=embed,
            username=ctx.author.display_name,
            avatar_url=ctx.author.display_avatar.url
        )
    except Exception as e:
        await ctx.send(f"❌ Error: {str(e)}", delete_after=5)

# Giveaway Commands
@bot.command(name='giveaway', aliases=['gstart'])
@not_blocked()
async def start_giveaway(ctx, duration: str, winners: int, *, prize: str):
    """Start a giveaway"""
    if not can_host_giveaway(ctx.author):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="You don't have permission to host giveaways!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    # Parse duration
    seconds = parse_time_string(duration)
    if seconds <= 0:
        await ctx.send("❌ Invalid duration! Use format like `1h`, `30m`, `1d`")
        return
    
    if winners <= 0 or winners > 20:
        await ctx.send("❌ Number of winners must be between 1 and 20!")
        return
    
    if len(prize) > 256:
        await ctx.send("❌ Prize description too long! Maximum 256 characters.")
        return
    
    end_time = datetime.utcnow() + timedelta(seconds=seconds)
    
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Duration:** {format_duration(seconds)}",
        color=discord.Color.blue()
    )
    embed.add_field(name="Hosted by", value=ctx.author.mention, inline=True)
    embed.add_field(name="Ends at", value=f"<t:{int(end_time.timestamp())}:F>", inline=True)
    embed.set_footer(text="Click the button below to join!")
    
    message = await ctx.send(embed=embed, view=GiveawayView(None))
    
    # Store giveaway data
    active_giveaways[message.id] = {
        'host': ctx.author.id,
        'channel': ctx.channel.id,
        'guild': ctx.guild.id,
        'prize': prize,
        'winners': winners,
        'end_time': end_time,
        'participants': [],
        'requirements': None
    }
    
    # Update the view with the correct message ID
    view = GiveawayView(message.id)
    await message.edit(view=view)

@bot.command(name='gend')
@not_blocked()
async def end_giveaway(ctx, message_id: int):
    """End a giveaway early"""
    if message_id not in active_giveaways:
        await ctx.send("❌ Giveaway not found!")
        return
    
    giveaway = active_giveaways[message_id]
    
    # Check permissions
    if not (ctx.author.id == giveaway['host'] or 
            is_bot_owner(ctx.author.id) or 
            ctx.author.guild_permissions.administrator):
        await ctx.send("❌ You can only end giveaways you hosted!")
        return
    
    await end_giveaway_logic(message_id)
    await ctx.send("✅ Giveaway ended!")

async def end_giveaway_logic(message_id):
    """Logic to end a giveaway and pick winners"""
    if message_id not in active_giveaways:
        return
    
    giveaway = active_giveaways[message_id]
    channel = bot.get_channel(giveaway['channel'])
    
    if not channel:
        del active_giveaways[message_id]
        return
    
    try:
        message = await channel.fetch_message(message_id)
    except discord.NotFound:
        del active_giveaways[message_id]
        return
    
    participants = giveaway['participants']
    winners_count = min(giveaway['winners'], len(participants))
    
    if winners_count == 0:
        embed = discord.Embed(
            title="🎉 Giveaway Ended",
            description=f"**Prize:** {giveaway['prize']}\n**Winner:** No valid participants",
            color=discord.Color.red()
        )
        await message.edit(embed=embed, view=None)
        del active_giveaways[message_id]
        return
    
    winners = random.sample(participants, winners_count)
    winner_mentions = []
    
    for winner_id in winners:
        user = bot.get_user(winner_id)
        if user:
            winner_mentions.append(user.mention)
        else:
            winner_mentions.append(f"<@{winner_id}>")
    
    embed = discord.Embed(
        title="🎉 Giveaway Ended",
        description=f"**Prize:** {giveaway['prize']}\n**Winner{'s' if len(winners) > 1 else ''}:** {', '.join(winner_mentions)}",
        color=discord.Color.gold()
    )
    embed.set_footer(text=f"Ended at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    
    await message.edit(embed=embed, view=None)
    
    # Notify winners
    winner_text = ', '.join(winner_mentions)
    await channel.send(f"🎉 Congratulations {winner_text}! You won **{giveaway['prize']}**!")
    
    del active_giveaways[message_id]

# Background task to check for ended giveaways
@tasks.loop(seconds=30)
async def check_giveaways():
    current_time = datetime.utcnow()
    ended_giveaways = []
    
    for message_id, giveaway in active_giveaways.items():
        if current_time >= giveaway['end_time']:
            ended_giveaways.append(message_id)
    
    for message_id in ended_giveaways:
        await end_giveaway_logic(message_id)

@check_giveaways.before_loop
async def before_check_giveaways():
    await bot.wait_until_ready()

check_giveaways.start()

# Utility Commands
@bot.command(name='avatar', aliases=['av'])
@not_blocked()
async def avatar(ctx, user: discord.User = None):
    """Get a user's avatar"""
    if user is None:
        user = ctx.author
    
    embed = discord.Embed(
        title=f"{user.display_name}'s Avatar",
        color=discord.Color.blue()
    )
    embed.set_image(url=user.display_avatar.url)
    
    await ctx.send(embed=embed)

@bot.command(name='userinfo', aliases=['ui'])
@not_blocked()
async def user_info(ctx, user: discord.User = None):
    """Get information about a user"""
    if user is None:
        user = ctx.author
    
    embed = discord.Embed(
        title="User Information",
        color=discord.Color.blue()
    )
    
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Username", value=f"{user.name}", inline=True)
    embed.add_field(name="Display Name", value=user.display_name, inline=True)
    embed.add_field(name="ID", value=user.id, inline=True)
    embed.add_field(name="Created", value=f"<t:{int(user.created_at.timestamp())}:F>", inline=True)
    
    if isinstance(user, discord.Member):
        embed.add_field(name="Joined", value=f"<t:{int(user.joined_at.timestamp())}:F>", inline=True)
        embed.add_field(name="Roles", value=f"{len(user.roles) - 1}", inline=True)
        
        # Message count
        if ctx.guild:
            msg_count = get_user_message_count(ctx.guild.id, user.id)
            embed.add_field(name="Messages Sent", value=str(msg_count), inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='serverinfo', aliases=['si'])
@not_blocked()
async def server_info(ctx):
    """Get information about the server"""
    guild = ctx.guild
    
    embed = discord.Embed(
        title="Server Information",
        color=discord.Color.blue()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="Name", value=guild.name, inline=True)
    embed.add_field(name="ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:F>", inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
    embed.add_field(name="Boosts", value=guild.premium_subscription_count, inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='ping')
@not_blocked()
async def ping(ctx):
    """Get bot latency"""
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: **{latency}ms**",
        color=discord.Color.green()
    )
    
    await ctx.send(embed=embed)

@bot.command(name='uptime')
@not_blocked()
async def uptime(ctx):
    """Get bot uptime"""
    current_time = time.time()
    uptime_seconds = current_time - BOT_START_TIME
    uptime_str = format_uptime(uptime_seconds)
    
    embed = discord.Embed(
        title="⏰ Bot Uptime",
        description=f"I've been online for **{uptime_str}**",
        color=discord.Color.blue()
    )
    
    await ctx.send(embed=embed)

# Prefix Commands
@bot.command(name='prefix')
@not_blocked()
@commands.has_permissions(manage_guild=True)
async def set_prefix(ctx, new_prefix: str = None):
    """Set or view the bot prefix for this server"""
    if new_prefix is None:
        current_prefix = custom_prefixes.get(ctx.guild.id, ",")
        embed = discord.Embed(
            title="Current Prefix",
            description=f"The current prefix for this server is: `{current_prefix}`",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        return
    
    if len(new_prefix) > 5:
        await ctx.send("❌ Prefix cannot be longer than 5 characters!")
        return
    
    custom_prefixes[ctx.guild.id] = new_prefix
    
    embed = discord.Embed(
        title="✅ Prefix Updated",
        description=f"Server prefix has been changed to: `{new_prefix}`",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

# NEW: Permissions slash command (Owner only)
@bot.tree.command(name="perms", description="Grant bot permissions to a user (Owner only)")
@app_commands.describe(user="The user to grant permissions to")
async def perms_command(interaction: discord.Interaction, user: discord.User):
    """Grant bot permissions to a user (Owner only)"""
    if not is_bot_owner(interaction.user.id):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="Only the bot owner can use this command.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if user.id == BOT_OWNER_ID:
        embed = discord.Embed(
            title="❌ Invalid Action",
            description="The bot owner already has all permissions.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if user.id in authorized_users:
        embed = discord.Embed(
            title="❌ Already Authorized",
            description=f"**{user.display_name}** already has bot permissions.",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Add user to authorized users
    authorized_users.add(user.id)
    
    embed = discord.Embed(
        title="✅ Permissions Granted",
        description=f"**{user.display_name}** has been granted full bot permissions.",
        color=discord.Color.green()
    )
    embed.add_field(name="Granted by", value=interaction.user.mention, inline=True)
    embed.add_field(name="User ID", value=str(user.id), inline=True)
    
    await interaction.response.send_message(embed=embed)

# Owner slash command
@bot.tree.command(name="owner", description="Owner-only command for bot management")
async def owner_command(interaction: discord.Interaction):
    """Owner-only command for bot management"""
    if not is_bot_owner(interaction.user.id):
        embed = discord.Embed(
            title="❌ Access Denied", 
            description="This command is restricted to the bot owner.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="👑 Owner Panel",
        description="Welcome to the owner management panel!",
        color=discord.Color.gold()
    )
    embed.add_field(name="Bot Status", value="✅ Online", inline=True)
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    embed.add_field(name="Users", value=len(bot.users), inline=True)
    embed.add_field(name="Authorized Users", value=len(authorized_users), inline=True)
    embed.add_field(name="Blocked Users", value=len(blocked_users), inline=True)
    embed.add_field(name="Active Giveaways", value=len(active_giveaways), inline=True)
    
    uptime_seconds = time.time() - BOT_START_TIME
    embed.add_field(name="Uptime", value=format_uptime(uptime_seconds), inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Help Command
@bot.command(name='help')
@not_blocked()
async def help_command(ctx):
    """Show help information"""
    embeds = []
    
    # Page 1: Basic Commands
    embed1 = discord.Embed(
        title="📜 FACTSY Commands - Page 1",
        description="Basic bot commands and information",
        color=discord.Color.blue()
    )
    embed1.add_field(
        name="🔍 Snipe Commands",
        value=(
            "`sp [channel]` - Show deleted messages in channel\n"
            "`spl [channel]` - Show deleted messages with links\n"
            "`spf [channel]` - Show deleted filtered messages\n"
            "`spa` - Show ALL deleted messages\n"
            "`spla` - Show ALL deleted messages with links\n"
            "`spfa` - Show ALL deleted filtered messages\n"
            "`es [channel]` - Show edited messages\n"
            "`clear` - Clear all snipe data (authorized only)"
        ),
        inline=False
    )
    embed1.add_field(
        name="🔧 Utility Commands", 
        value=(
            "`ping` - Check bot latency\n"
            "`uptime` - Show bot uptime\n"
            "`avatar [user]` - Get user's avatar\n"
            "`userinfo [user]` - Get user information\n"
            "`serverinfo` - Get server information\n"
            "`prefix [new_prefix]` - Set/view server prefix"
        ),
        inline=False
    )
    embed1.set_footer(text="Page 1/3 • Use reactions to navigate")
    embeds.append(embed1)
    
    # Page 2: Moderation Commands
    embed2 = discord.Embed(
        title="📜 FACTSY Commands - Page 2", 
        description="Moderation and management commands",
        color=discord.Color.orange()
    )
    embed2.add_field(
        name="👮 Moderation Commands",
        value=(
            "`timeout <user> <duration> [reason]` - Timeout a user\n"
            "`untimeout <user> [reason]` - Remove timeout\n"
            "`kick <user> [reason]` - Kick a user\n"
            "`ban <user> [reason]` - Ban a user\n"
            "`unban <user_id> [reason]` - Unban a user\n"
            "`purge <amount>` - Delete messages (1-100)"
        ),
        inline=False
    )
    embed2.add_field(
        name="🔒 Namelock Commands",
        value=(
            "`namelock <user> <nickname>` - Lock user's nickname\n"
            "`unnamelock <user>` - Remove namelock"
        ),
        inline=False
    )
    embed2.add_field(
        name="🗣️ Webhook Commands",
        value=(
            "`say <message>` - Send message as webhook\n"
            "`sayembed [color] <message>` - Send embed as webhook"
        ),
        inline=False
    )
    embed2.set_footer(text="Page 2/3 • Use reactions to navigate")
    embeds.append(embed2)
    
    # Page 3: Advanced Commands
    embed3 = discord.Embed(
        title="📜 FACTSY Commands - Page 3",
        description="Advanced features and owner commands", 
        color=discord.Color.purple()
    )
    embed3.add_field(
        name="🎉 Giveaway Commands",
        value=(
            "`giveaway <duration> <winners> <prize>` - Start giveaway\n"
            "`gend <message_id>` - End giveaway early"
        ),
        inline=False
    )
    embed3.add_field(
        name="👑 Owner/Authorized Commands",
        value=(
            "`block <user>` - Block user from bot (owner)\n"
            "`unblock <user>` - Unblock user (owner)\n"
            "`/perms <user>` - Grant bot permissions (owner)\n"
            "`/owner` - Owner management panel (owner)"
        ),
        inline=False
    )
    embed3.add_field(
        name="ℹ️ Information",
        value=(
            "**Duration Format:** `1s`, `30m`, `2h`, `1d`, `1w`\n"
            "**Color Format:** Hex codes (#ff0000) or names (red, blue)\n"
            "**Bot Owner:** <@776883692983156736>"
        ),
        inline=False
    )
    embed3.set_footer(text="Page 3/3 • Use reactions to navigate")
    embeds.append(embed3)
    
    if len(embeds) == 1:
        await ctx.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[0], view=view)

# Error handlers
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description="You don't have the required permissions to use this command!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=10)
    elif isinstance(error, commands.BotMissingPermissions):
        embed = discord.Embed(
            title="❌ Bot Missing Permissions", 
            description="I don't have the required permissions to execute this command!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=10)
    elif isinstance(error, commands.MemberNotFound):
        embed = discord.Embed(
            title="❌ User Not Found",
            description="Could not find the specified user!",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed, delete_after=10)
    elif isinstance(error, commands.CheckFailure):
        # This handles blocked users
        pass
    else:
        print(f"Unhandled error: {error}")

# Run the bot
if __name__ == "__main__":
    # Get token from environment variable
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("Error: DISCORD_TOKEN environment variable not set!")
        exit(1)
    
    bot.run(TOKEN)
