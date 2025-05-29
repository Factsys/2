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

# FIXED: Reroll View for ended giveaways
class RerollView(discord.ui.View):
    def __init__(self, giveaway_data):
        super().__init__(timeout=None)
        self.giveaway_data = giveaway_data
    
    @discord.ui.button(label="Reroll", style=discord.ButtonStyle.primary, emoji="🔄")
    async def reroll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (is_bot_owner(interaction.user.id) or 
                interaction.user.guild_permissions.administrator or 
                can_host_giveaway(interaction.user)):
            await interaction.response.send_message("❌ You don't have permission to reroll giveaways.", ephemeral=True)
            return
        
        participants = self.giveaway_data['participants']
        if not participants:
            await interaction.response.send_message("❌ No participants to reroll.", ephemeral=True)
            return
        
        new_winner_id = random.choice(participants)
        new_winner = bot.get_user(new_winner_id)
        
        if new_winner:
            embed = discord.Embed(
                title="🎉 Giveaway Rerolled!",
                description=f"**🎊 Congratulations {new_winner.mention}!**\nYou won **{self.giveaway_data['prize']}**!",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Rerolled by {interaction.user.name}")
            
            # Send winner notification
            try:
                await new_winner.send(f"🎉 **Congratulations!** You won **{self.giveaway_data['prize']}** in {interaction.guild.name}!")
            except:
                pass
            
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ Could not find the new winner.", ephemeral=True)

# FIXED: Reaction Role View for /create command
class ReactionRoleView(discord.ui.View):
    def __init__(self, role_mappings):
        super().__init__(timeout=None)
        self.role_mappings = role_mappings
        
        # Add buttons for each role mapping
        for emoji, role_id in role_mappings.items():
            button = discord.ui.Button(
                emoji=emoji,
                style=discord.ButtonStyle.secondary,
                custom_id=f"reaction_role_{role_id}"
            )
            button.callback = self.role_button_callback
            self.add_item(button)
    
    async def role_button_callback(self, interaction: discord.Interaction):
        if is_user_blocked(interaction.user.id):
            await interaction.response.send_message("❌ You are blocked from using bot functions.", ephemeral=True)
            return
        
        # Extract role ID from custom_id
        role_id = int(interaction.data['custom_id'].split('_')[-1])
        role = interaction.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message("❌ Role not found.", ephemeral=True)
            return
        
        member = interaction.guild.get_member(interaction.user.id)
        if not member:
            await interaction.response.send_message("❌ Member not found.", ephemeral=True)
            return
        
        try:
            if role in member.roles:
                # Remove role
                await member.remove_roles(role)
                await interaction.response.send_message(f"✅ Removed role **{role.name}**", ephemeral=True)
            else:
                # Add role
                await member.add_roles(role)
                await interaction.response.send_message(f"✅ Added role **{role.name}**", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to manage this role.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# Help View
class HelpPaginationView(discord.ui.View):
    def __init__(self, timeout=300):
        super().__init__(timeout=timeout)
        self.current_page = 0
        self.pages = [
            {
                "title": "📜 FACTSY Commands - Page 1",
                "fields": [
                    ("**Message Tracking**", "`,snipe` `,s [1-100]` `/snipe` - Show deleted message by number\n`,editsnipe` `,es` `/editsnipe` - Show last edited message\n`,sp [channel] [page]` `/sp` - List normal deleted messages\n`,spf [channel] [page]` `/spf` - Show filtered/censored messages only\n`,spl [channel] [page]` `/spl` - Show deleted links only", False),
                    ("**Moderation**", "`,namelock` `,nl` `/namelock` - Lock user's nickname\n`,unl` `/unl` - Unlock user's nickname\n`,rename` `,re` `/rename` - Change user's nickname\n`,say` `/say` - Send normal message\n`,saywb` `/saywb` - Send embed message", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 2", 
                "fields": [
                    ("**Giveaways**", "`,gw [id]` `/gw` - Reroll giveaway winner\n`/giveaway` - Create advanced giveaway\n`/giveaway_host [@role]` - Set giveaway host roles", False),
                    ("**Management**", "`,block` `/block` - Block user from bot\n`,mess` `/mess` - DM user globally\n`,role` `/role` - Add role to user\n`,namelockimmune` `,nli` `/namelockimmune` - Make user immune", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 3",
                "fields": [
                    ("**Reaction Roles**", "`,create` `/create` - Create reaction roles (1-6 options)", False),
                    ("**Bot Features**", "`,manage` `/manage` - Bot management panel\n`/unblock` - Unblock user from bot\n`/ping` - Show bot latency\n`/prefix` - Change server prefix", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 4",
                "fields": [
                    ("**Info**", "All commands support both prefix and slash (/) versions\nModerators can use most commands\nBlocked users cannot use any bot functions\nSeconds support added to durations (e.g., 30s)", False),
                    ("**Usage Examples**", "`,s 5` - Show 5th deleted message\n`/saywb #general My Title My Description red` - Send embed\n`/prefix !` - Change prefix to !\n`,sp #general` - Show normal deleted messages in channel", False)
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
        embed = discord.Embed(title=page_data["title"], color=discord.Color.blue())
        
        for name, value, inline in page_data["fields"]:
            embed.add_field(name=name, value=value, inline=inline)
        
        embed.set_footer(text=f"Page {self.current_page + 1} of {self.total_pages} | Made with ❤ | Werrzzzy")
        return embed
    
    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.secondary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()
    
    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.secondary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        else:
            await interaction.response.defer()

# Bot events
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    run_flask()
    
    # Start the giveaway check task
    check_giveaways.start()
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    # Increment message count for giveaway requirements
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    await bot.process_commands(message)

# FIXED: Enhanced on_message_delete event with proper media handling
@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    
    # Initialize channel if not exists
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []
    
    # Get media URLs and content
    media_urls = get_media_url(message.content, message.attachments)
    cleaned_content = clean_content_from_media(message.content, media_urls) if media_urls else message.content
    
    # Determine message type
    msg_type = "normal"
    if is_offensive_content(message.content):
        msg_type = "filtered"
    elif has_links(message.content) and not media_urls:
        msg_type = "link"
    
    # Store the sniped message
    sniped_data = {
        'content': cleaned_content,
        'original_content': message.content,  # Store original for ,spf
        'author': message.author,
        'channel': message.channel,
        'time': datetime.utcnow(),
        'media_urls': media_urls,
        'message_type': msg_type,
        'is_offensive': is_offensive_content(message.content),
        'has_links': has_links(message.content)
    }
    
    # Add to beginning of list and limit to MAX_MESSAGES
    sniped_messages[channel_id].insert(0, sniped_data)
    if len(sniped_messages[channel_id]) > MAX_MESSAGES:
        sniped_messages[channel_id] = sniped_messages[channel_id][:MAX_MESSAGES]

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    if before.content == after.content:
        return
    
    channel_id = before.channel.id
    
    # Initialize channel if not exists
    if channel_id not in edited_messages:
        edited_messages[channel_id] = []
    
    # Store the edited message
    edited_data = {
        'before_content': before.content,
        'after_content': after.content,
        'author': before.author,
        'channel': before.channel,
        'time': datetime.utcnow()
    }
    
    # Add to beginning of list and limit to MAX_MESSAGES
    edited_messages[channel_id].insert(0, edited_data)
    if len(edited_messages[channel_id]) > MAX_MESSAGES:
        edited_messages[channel_id] = edited_messages[channel_id][:MAX_MESSAGES]

# FIXED: Enhanced member update event for namelock functionality
@bot.event
async def on_member_update(before, after):
    # Check if nickname changed and user is namelocked
    if before.nick != after.nick and after.id in namelocked_users:
        namelock_data = namelocked_users[after.id]
        
        # Check if this is the correct guild
        if namelock_data['guild_id'] == after.guild.id:
            locked_nickname = namelock_data['nickname']
            
            # If nickname changed from locked nickname, revert it
            if after.nick != locked_nickname:
                try:
                    await after.edit(nick=locked_nickname, reason="Nickname locked by FACTSY")
                    print(f"Reverted nickname for {after.name} to {locked_nickname}")
                except discord.Forbidden:
                    print(f"Cannot revert nickname for {after.name} - insufficient permissions")
                except Exception as e:
                    print(f"Error reverting nickname for {after.name}: {e}")

# Task to check giveaways
@tasks.loop(seconds=10)
async def check_giveaways():
    """Check for expired giveaways every 10 seconds"""
    current_time = datetime.utcnow()
    expired_giveaways = []
    
    for message_id, giveaway in active_giveaways.items():
        if current_time >= giveaway['end_time']:
            expired_giveaways.append(message_id)
    
    for message_id in expired_giveaways:
        await end_giveaway(message_id)

async def end_giveaway(message_id):
    """End a giveaway and select winners"""
    if message_id not in active_giveaways:
        return
    
    giveaway = active_giveaways[message_id]
    participants = giveaway['participants']
    winner_count = giveaway['winner_count']
    
    try:
        # Get the original message
        channel = bot.get_channel(giveaway['channel_id'])
        if not channel:
            del active_giveaways[message_id]
            return
        
        original_message = await channel.fetch_message(message_id)
        
        if not participants:
            # No participants
            embed = discord.Embed(
                title="🎉 Giveaway Ended",
                description=f"**Prize:** {giveaway['prize']}\n\n❌ No one participated in this giveaway!",
                color=discord.Color.red()
            )
            await original_message.edit(embed=embed, view=None)
            del active_giveaways[message_id]
            return
        
        # Select winners
        if len(participants) <= winner_count:
            winners = participants.copy()
        else:
            winners = random.sample(participants, winner_count)
        
        # Create winner announcement
        winner_mentions = []
        for winner_id in winners:
            winner_user = bot.get_user(winner_id)
            if winner_user:
                winner_mentions.append(winner_user.mention)
                # Send DM to winner
                try:
                    await winner_user.send(f"🎉 **Congratulations!** You won **{giveaway['prize']}** in {channel.guild.name}!")
                except:
                    pass
        
        winner_text = ", ".join(winner_mentions) if winner_mentions else "Unknown users"
        
        # Update original message
        embed = discord.Embed(
            title="🎉 Giveaway Ended!",
            description=f"**Prize:** {giveaway['prize']}\n**Winners:** {winner_text}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Ended • {len(participants)} participants")
        
        # Add reroll view
        reroll_view = RerollView(giveaway)
        await original_message.edit(embed=embed, view=reroll_view)
        
        # Send winner announcement message
        announcement_embed = discord.Embed(
            title="🎊 Congratulations!",
            description=f"**{winner_text}** won **{giveaway['prize']}**!",
            color=discord.Color.gold()
        )
        
        await channel.send(embed=announcement_embed, view=RerollView(giveaway))
        
        # Remove from active giveaways
        del active_giveaways[message_id]
        
    except discord.NotFound:
        # Message was deleted
        del active_giveaways[message_id]
    except Exception as e:
        print(f"Error ending giveaway {message_id}: {e}")

@check_giveaways.before_loop
async def before_check_giveaways():
    await bot.wait_until_ready()

# Prefix commands
@bot.command(name='help', aliases=['h'])
@not_blocked()
async def help_command(ctx):
    """Show bot help"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe_command(ctx, number: int = 1):
    """Snipe deleted messages by number"""
    if number < 1 or number > MAX_MESSAGES:
        await ctx.send(f"❌ Please provide a number between 1 and {MAX_MESSAGES}")
        return
    
    channel_id = ctx.channel.id
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel!")
        return
    
    if number > len(sniped_messages[channel_id]):
        await ctx.send(f"❌ Only {len(sniped_messages[channel_id])} deleted messages available!")
        return
    
    # Get the message (number is 1-indexed)
    sniped_msg = sniped_messages[channel_id][number - 1]
    
    # FIXED: Clean format as requested - (context) - {user} or just {user} if no context
    author_name = f"{sniped_msg['author'].name}"
    
    if sniped_msg['content'] and sniped_msg['content'].strip():
        # Filter the content for display
        filtered_content = filter_content(sniped_msg['content'])
        description = f"({filtered_content}) - {author_name}"
    else:
        description = author_name
    
    embed = discord.Embed(
        title="📜 Sniped Message",
        description=description,
        color=discord.Color.blue()
    )
    
    # Add media if present
    if sniped_msg['media_urls']:
        for media in sniped_msg['media_urls']:
            if media['type'] in ['image', 'gif', 'tenor_gif', 'giphy_gif']:
                embed.set_image(url=media['url'])
                break
    
    # Set timestamp
    embed.timestamp = sniped_msg['time']
    embed.set_footer(text=f"Message #{number}")
    
    await ctx.send(embed=embed)

@bot.command(name='editsnipe', aliases=['es'])
@not_blocked()
async def editsnipe_command(ctx):
    """Show last edited message"""
    channel_id = ctx.channel.id
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await ctx.send("❌ No edited messages found in this channel!")
        return
    
    edited_msg = edited_messages[channel_id][0]
    
    embed = discord.Embed(title="📝 Edit Snipe", color=discord.Color.orange())
    embed.add_field(name="Before", value=edited_msg['before_content'][:1024] if edited_msg['before_content'] else "*No content*", inline=False)
    embed.add_field(name="After", value=edited_msg['after_content'][:1024] if edited_msg['after_content'] else "*No content*", inline=False)
    embed.set_author(name=edited_msg['author'].display_name, icon_url=edited_msg['author'].display_avatar.url)
    embed.timestamp = edited_msg['time']
    
    await ctx.send(embed=embed)

@bot.command(name='sp')
@not_blocked()
async def snipe_pages_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """Show paginated list of normal deleted messages"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in that channel!")
        return
    
    # Filter for normal messages only
    normal_messages = [msg for msg in sniped_messages[channel_id] if msg['message_type'] == 'normal']
    
    if not normal_messages:
        await ctx.send("❌ No normal deleted messages found!")
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(normal_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        page = 1
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(normal_messages))
    page_messages = normal_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"📜 Normal Deleted Messages - {target_channel.name}",
        color=discord.Color.blue()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = msg['content'] or "*No text content*"
        if len(content) > 100:
            content = content[:97] + "..."
        
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} | {len(normal_messages)} total messages")
    
    # Add pagination if needed
    if total_pages > 1:
        # Create all embeds for pagination
        embeds = []
        for p in range(1, total_pages + 1):
            p_start_idx = (p - 1) * MESSAGES_PER_PAGE
            p_end_idx = min(p_start_idx + MESSAGES_PER_PAGE, len(normal_messages))
            p_page_messages = normal_messages[p_start_idx:p_end_idx]
            
            p_embed = discord.Embed(
                title=f"📜 Normal Deleted Messages - {target_channel.name}",
                color=discord.Color.blue()
            )
            
            for i, msg in enumerate(p_page_messages, start=p_start_idx + 1):
                content = msg['content'] or "*No text content*"
                if len(content) > 100:
                    content = content[:97] + "..."
                
                p_embed.add_field(
                    name=f"{i}. {msg['author'].display_name}",
                    value=content,
                    inline=False
                )
            
            p_embed.set_footer(text=f"Page {p} of {total_pages} | {len(normal_messages)} total messages")
            embeds.append(p_embed)
        
        view = PaginationView(embeds)
        view.current_page = page - 1
        view.update_buttons()
        await ctx.send(embed=embeds[page - 1], view=view)
    else:
        await ctx.send(embed=embed)

@bot.command(name='spf')
@not_blocked()
async def snipe_filtered_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """Show paginated list of filtered/offensive deleted messages"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in that channel!")
        return
    
    # Filter for offensive messages only
    filtered_messages = [msg for msg in sniped_messages[channel_id] if msg['message_type'] == 'filtered']
    
    if not filtered_messages:
        await ctx.send("❌ No filtered deleted messages found!")
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(filtered_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        page = 1
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(filtered_messages))
    page_messages = filtered_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔒 Filtered Deleted Messages - {target_channel.name}",
        color=discord.Color.red()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        # Show original unfiltered content for ,spf
        content = msg['original_content'] or "*No text content*"
        if len(content) > 100:
            content = content[:97] + "..."
        
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} | {len(filtered_messages)} total messages")
    
    # Add pagination if needed
    if total_pages > 1:
        # Create all embeds for pagination
        embeds = []
        for p in range(1, total_pages + 1):
            p_start_idx = (p - 1) * MESSAGES_PER_PAGE
            p_end_idx = min(p_start_idx + MESSAGES_PER_PAGE, len(filtered_messages))
            p_page_messages = filtered_messages[p_start_idx:p_end_idx]
            
            p_embed = discord.Embed(
                title=f"🔒 Filtered Deleted Messages - {target_channel.name}",
                color=discord.Color.red()
            )
            
            for i, msg in enumerate(p_page_messages, start=p_start_idx + 1):
                content = msg['original_content'] or "*No text content*"
                if len(content) > 100:
                    content = content[:97] + "..."
                
                p_embed.add_field(
                    name=f"{i}. {msg['author'].display_name}",
                    value=content,
                    inline=False
                )
            
            p_embed.set_footer(text=f"Page {p} of {total_pages} | {len(filtered_messages)} total messages")
            embeds.append(p_embed)
        
        view = PaginationView(embeds)
        view.current_page = page - 1
        view.update_buttons()
        await ctx.send(embed=embeds[page - 1], view=view)
    else:
        await ctx.send(embed=embed)

@bot.command(name='spl')
@not_blocked()
async def snipe_links_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """Show paginated list of deleted link messages"""
    target_channel = channel or ctx.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in that channel!")
        return
    
    # Filter for link messages only
    link_messages = [msg for msg in sniped_messages[channel_id] if msg['message_type'] == 'link']
    
    if not link_messages:
        await ctx.send("❌ No deleted link messages found!")
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        page = 1
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(link_messages))
    page_messages = link_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔗 Deleted Link Messages - {target_channel.name}",
        color=discord.Color.purple()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = msg['content'] or "*No text content*"
        if len(content) > 100:
            content = content[:97] + "..."
        
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} | {len(link_messages)} total messages")
    
    # Add pagination if needed
    if total_pages > 1:
        # Create all embeds for pagination
        embeds = []
        for p in range(1, total_pages + 1):
            p_start_idx = (p - 1) * MESSAGES_PER_PAGE
            p_end_idx = min(p_start_idx + MESSAGES_PER_PAGE, len(link_messages))
            p_page_messages = link_messages[p_start_idx:p_end_idx]
            
            p_embed = discord.Embed(
                title=f"🔗 Deleted Link Messages - {target_channel.name}",
                color=discord.Color.purple()
            )
            
            for i, msg in enumerate(p_page_messages, start=p_start_idx + 1):
                content = msg['content'] or "*No text content*"
                if len(content) > 100:
                    content = content[:97] + "..."
                
                p_embed.add_field(
                    name=f"{i}. {msg['author'].display_name}",
                    value=content,
                    inline=False
                )
            
            p_embed.set_footer(text=f"Page {p} of {total_pages} | {len(link_messages)} total messages")
            embeds.append(p_embed)
        
        view = PaginationView(embeds)
        view.current_page = page - 1
        view.update_buttons()
        await ctx.send(embed=embeds[page - 1], view=view)
    else:
        await ctx.send(embed=embed)

# FIXED: Namelock command with proper nickname handling
@bot.command(name='namelock', aliases=['nl'])
@not_blocked()
async def namelock_command(ctx, member: discord.Member, *, nickname):
    """Lock a user's nickname"""
    if not (ctx.author.guild_permissions.manage_nicknames or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to manage nicknames!")
        return
    
    if member.id in namelock_immune_users:
        await ctx.send("❌ This user is immune to namelock!")
        return
    
    if member.id == ctx.guild.owner_id:
        await ctx.send("❌ Cannot namelock the server owner!")
        return
    
    # FIXED: Use the actual nickname parameter instead of hardcoded "test"
    try:
        await member.edit(nick=nickname, reason=f"Namelocked by {ctx.author}")
        
        # Store namelock data
        namelocked_users[member.id] = {
            'guild_id': ctx.guild.id,
            'nickname': nickname
        }
        
        await ctx.send(f"✅ **{member.display_name}** has been namelocked to `{nickname}`")
    
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='unl')
@not_blocked()
async def nameunlock_command(ctx, member: discord.Member):
    """Unlock a user's nickname"""
    if not (ctx.author.guild_permissions.manage_nicknames or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to manage nicknames!")
        return
    
    if member.id not in namelocked_users:
        await ctx.send("❌ This user is not namelocked!")
        return
    
    # Remove from namelocked users
    del namelocked_users[member.id]
    
    await ctx.send(f"✅ **{member.display_name}** has been unlocked from namelock")

@bot.command(name='rename', aliases=['re'])
@not_blocked()
async def rename_command(ctx, member: discord.Member, *, nickname=None):
    """Change a user's nickname"""
    if not (ctx.author.guild_permissions.manage_nicknames or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to manage nicknames!")
        return
    
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname, reason=f"Renamed by {ctx.author}")
        new_nick = member.display_name
        
        await ctx.send(f"✅ Renamed **{old_nick}** to **{new_nick}**")
    
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='say')
@not_blocked()
async def say_command(ctx, *, message):
    """Send a message as the bot"""
    if not (ctx.author.guild_permissions.manage_messages or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    try:
        await ctx.message.delete()
    except:
        pass
    
    await ctx.send(message)

@bot.command(name='saywb')
@not_blocked()
async def saywb_command(ctx, channel: discord.TextChannel, color: str = None, title: str = None, *, description: str = None):
    """Send an embed message - FIXED with channel parameter"""
    if not (ctx.author.guild_permissions.manage_messages or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to use this command!")
        return
    
    # FIXED: Require at least title or description
    if not title and not description:
        await ctx.send("❌ Please provide at least a title or description!")
        return
    
    # Parse color
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Create embed
    embed = discord.Embed(color=embed_color)
    
    if title:
        embed.title = title
    
    if description:
        embed.description = description
    
    try:
        await ctx.message.delete()
    except:
        pass
    
    # FIXED: Send to specified channel
    await channel.send(embed=embed)
    await ctx.send(f"✅ Message sent to {channel.mention}", delete_after=5)

@bot.command(name='create')
@not_blocked()
async def create_reaction_roles(ctx, title: str, color: str = None, *role_mappings):
    """Create reaction roles with title - FIXED format"""
    if not (ctx.author.guild_permissions.manage_roles or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to manage roles!")
        return
    
    if len(role_mappings) < 2 or len(role_mappings) % 2 != 0:
        await ctx.send("❌ Please provide emoji-role pairs! Format: `/create [title] [color] [emoji1] [role1] [emoji2] [role2]...`")
        return
    
    if len(role_mappings) > 12:  # Max 6 pairs (6 * 2 = 12)
        await ctx.send("❌ Maximum 6 emoji-role pairs allowed!")
        return
    
    # Parse role mappings
    role_map = {}
    for i in range(0, len(role_mappings), 2):
        emoji = role_mappings[i]
        role_name = role_mappings[i + 1]
        
        # Find role
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if not role:
            await ctx.send(f"❌ Role `{role_name}` not found!")
            return
        
        role_map[emoji] = role.id
    
    # Parse color
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Create embed with title
    embed = discord.Embed(
        title=title,
        description="Click the buttons below to get/remove roles:",
        color=embed_color
    )
    
    # Add role information
    role_info = []
    for emoji, role_id in role_map.items():
        role = ctx.guild.get_role(role_id)
        if role:
            role_info.append(f"{emoji} - {role.name}")
    
    embed.add_field(name="Available Roles", value="\n".join(role_info), inline=False)
    
    # Create view with buttons
    view = ReactionRoleView(role_map)
    
    try:
        await ctx.message.delete()
    except:
        pass
    
    await ctx.send(embed=embed, view=view)

@bot.command(name='block')
@not_blocked()
async def block_user_command(ctx, user: discord.User):
    """Block a user from using the bot"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command!")
        return
    
    if user.id == BOT_OWNER_ID:
        await ctx.send("❌ Cannot block the bot owner!")
        return
    
    if user.id in blocked_users:
        await ctx.send("❌ User is already blocked!")
        return
    
    blocked_users.add(user.id)
    await ctx.send(f"✅ **{user.name}** has been blocked from using the bot")

@bot.command(name='gw')
@not_blocked()
async def giveaway_reroll_command(ctx, message_id: int):
    """Reroll a giveaway winner"""
    if not (is_bot_owner(ctx.author.id) or ctx.author.guild_permissions.administrator or can_host_giveaway(ctx.author)):
        await ctx.send("❌ You don't have permission to reroll giveaways!")
        return
    
    # Find giveaway in active giveaways or try to reroll ended giveaway
    try:
        message = await ctx.channel.fetch_message(message_id)
        # For now, just send an info message
        await ctx.send("🔄 Use the Reroll button on the giveaway message to reroll winners!")
    except discord.NotFound:
        await ctx.send("❌ Giveaway message not found!")

@bot.command(name='mess')
@not_blocked()
async def message_user_command(ctx, user_search: str, *, message):
    """Send a DM to a user globally"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command!")
        return
    
    # Try to find user by ID first, then by name
    target_user = None
    try:
        user_id = int(user_search)
        target_user = bot.get_user(user_id)
    except ValueError:
        target_user = find_user_globally(user_search)
    
    if not target_user:
        await ctx.send("❌ User not found!")
        return
    
    try:
        await target_user.send(message)
        await ctx.send(f"✅ Message sent to **{target_user.name}**")
    except discord.Forbidden:
        await ctx.send("❌ Cannot send DM to this user!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='role')
@not_blocked()
async def add_role_command(ctx, member: discord.Member, *, role_name):
    """Add a role to a user"""
    if not (ctx.author.guild_permissions.manage_roles or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to manage roles!")
        return
    
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"❌ Role `{role_name}` not found!")
        return
    
    try:
        await member.add_roles(role, reason=f"Added by {ctx.author}")
        await ctx.send(f"✅ Added role **{role.name}** to **{member.display_name}**")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage this role!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='namelockimmune', aliases=['nli'])
@not_blocked()
async def namelock_immune_command(ctx, member: discord.Member):
    """Make a user immune to namelock"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command!")
        return
    
    if member.id in namelock_immune_users:
        await ctx.send("❌ User is already namelock immune!")
        return
    
    namelock_immune_users.add(member.id)
    await ctx.send(f"✅ **{member.display_name}** is now immune to namelock")

@bot.command(name='manage')
@not_blocked()
async def manage_command(ctx):
    """Show bot management panel"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command!")
        return
    
    uptime_seconds = time.time() - BOT_START_TIME
    uptime_str = format_uptime(uptime_seconds)
    
    embed = discord.Embed(title="🔧 Bot Management Panel", color=discord.Color.blue())
    embed.add_field(name="📊 Statistics", value=f"**Guilds:** {len(bot.guilds)}\n**Users:** {len(bot.users)}\n**Uptime:** {uptime_str}", inline=False)
    embed.add_field(name="🚫 Blocked Users", value=f"{len(blocked_users)} users", inline=True)
    embed.add_field(name="🔒 Namelocked Users", value=f"{len(namelocked_users)} users", inline=True)
    embed.add_field(name="🎉 Active Giveaways", value=f"{len(active_giveaways)} giveaways", inline=True)
    
    await ctx.send(embed=embed)

# Slash commands
@bot.tree.command(name="snipe", description="Show deleted message by number")
@check_not_blocked()
async def snipe_slash(interaction: discord.Interaction, number: int = 1):
    """Snipe deleted messages by number"""
    await interaction.response.defer()
    
    if number < 1 or number > MAX_MESSAGES:
        await interaction.followup.send(f"❌ Please provide a number between 1 and {MAX_MESSAGES}")
        return
    
    channel_id = interaction.channel.id
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.followup.send("❌ No deleted messages found in this channel!")
        return
    
    if number > len(sniped_messages[channel_id]):
        await interaction.followup.send(f"❌ Only {len(sniped_messages[channel_id])} deleted messages available!")
        return
    
    # Get the message (number is 1-indexed)
    sniped_msg = sniped_messages[channel_id][number - 1]
    
    # FIXED: Clean format as requested - (context) - {user} or just {user} if no context
    author_name = f"{sniped_msg['author'].name}"
    
    if sniped_msg['content'] and sniped_msg['content'].strip():
        # Filter the content for display
        filtered_content = filter_content(sniped_msg['content'])
        description = f"({filtered_content}) - {author_name}"
    else:
        description = author_name
    
    embed = discord.Embed(
        title="📜 Sniped Message",
        description=description,
        color=discord.Color.blue()
    )
    
    # Add media if present
    if sniped_msg['media_urls']:
        for media in sniped_msg['media_urls']:
            if media['type'] in ['image', 'gif', 'tenor_gif', 'giphy_gif']:
                embed.set_image(url=media['url'])
                break
    
    # Set timestamp
    embed.timestamp = sniped_msg['time']
    embed.set_footer(text=f"Message #{number}")
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="editsnipe", description="Show last edited message")
@check_not_blocked()
async def editsnipe_slash(interaction: discord.Interaction):
    """Show last edited message"""
    await interaction.response.defer()
    
    channel_id = interaction.channel.id
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await interaction.followup.send("❌ No edited messages found in this channel!")
        return
    
    edited_msg = edited_messages[channel_id][0]
    
    embed = discord.Embed(title="📝 Edit Snipe", color=discord.Color.orange())
    embed.add_field(name="Before", value=edited_msg['before_content'][:1024] if edited_msg['before_content'] else "*No content*", inline=False)
    embed.add_field(name="After", value=edited_msg['after_content'][:1024] if edited_msg['after_content'] else "*No content*", inline=False)
    embed.set_author(name=edited_msg['author'].display_name, icon_url=edited_msg['author'].display_avatar.url)
    embed.timestamp = edited_msg['time']
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="sp", description="Show paginated list of normal deleted messages")
@check_not_blocked()
async def sp_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """Show paginated list of normal deleted messages"""
    await interaction.response.defer()
    
    target_channel = channel or interaction.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.followup.send("❌ No deleted messages found in that channel!")
        return
    
    # Filter for normal messages only
    normal_messages = [msg for msg in sniped_messages[channel_id] if msg['message_type'] == 'normal']
    
    if not normal_messages:
        await interaction.followup.send("❌ No normal deleted messages found!")
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(normal_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        page = 1
    
    # Create all embeds for pagination
    embeds = []
    for p in range(1, total_pages + 1):
        p_start_idx = (p - 1) * MESSAGES_PER_PAGE
        p_end_idx = min(p_start_idx + MESSAGES_PER_PAGE, len(normal_messages))
        p_page_messages = normal_messages[p_start_idx:p_end_idx]
        
        p_embed = discord.Embed(
            title=f"📜 Normal Deleted Messages - {target_channel.name}",
            color=discord.Color.blue()
        )
        
        for i, msg in enumerate(p_page_messages, start=p_start_idx + 1):
            content = msg['content'] or "*No text content*"
            if len(content) > 100:
                content = content[:97] + "..."
            
            p_embed.add_field(
                name=f"{i}. {msg['author'].display_name}",
                value=content,
                inline=False
            )
        
        p_embed.set_footer(text=f"Page {p} of {total_pages} | {len(normal_messages)} total messages")
        embeds.append(p_embed)
    
    if len(embeds) == 1:
        await interaction.followup.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        view.current_page = page - 1
        view.update_buttons()
        await interaction.followup.send(embed=embeds[page - 1], view=view)

@bot.tree.command(name="spf", description="Show paginated list of filtered deleted messages")
@check_not_blocked()
async def spf_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """Show paginated list of filtered/offensive deleted messages"""
    await interaction.response.defer()
    
    target_channel = channel or interaction.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.followup.send("❌ No deleted messages found in that channel!")
        return
    
    # Filter for offensive messages only
    filtered_messages = [msg for msg in sniped_messages[channel_id] if msg['message_type'] == 'filtered']
    
    if not filtered_messages:
        await interaction.followup.send("❌ No filtered deleted messages found!")
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(filtered_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        page = 1
    
    # Create all embeds for pagination
    embeds = []
    for p in range(1, total_pages + 1):
        p_start_idx = (p - 1) * MESSAGES_PER_PAGE
        p_end_idx = min(p_start_idx + MESSAGES_PER_PAGE, len(filtered_messages))
        p_page_messages = filtered_messages[p_start_idx:p_end_idx]
        
        p_embed = discord.Embed(
            title=f"🔒 Filtered Deleted Messages - {target_channel.name}",
            color=discord.Color.red()
        )
        
        for i, msg in enumerate(p_page_messages, start=p_start_idx + 1):
            # Show original unfiltered content for spf
            content = msg['original_content'] or "*No text content*"
            if len(content) > 100:
                content = content[:97] + "..."
            
            p_embed.add_field(
                name=f"{i}. {msg['author'].display_name}",
                value=content,
                inline=False
            )
        
        p_embed.set_footer(text=f"Page {p} of {total_pages} | {len(filtered_messages)} total messages")
        embeds.append(p_embed)
    
    if len(embeds) == 1:
        await interaction.followup.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        view.current_page = page - 1
        view.update_buttons()
        await interaction.followup.send(embed=embeds[page - 1], view=view)

@bot.tree.command(name="spl", description="Show paginated list of deleted link messages")
@check_not_blocked()
async def spl_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """Show paginated list of deleted link messages"""
    await interaction.response.defer()
    
    target_channel = channel or interaction.channel
    channel_id = target_channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.followup.send("❌ No deleted messages found in that channel!")
        return
    
    # Filter for link messages only
    link_messages = [msg for msg in sniped_messages[channel_id] if msg['message_type'] == 'link']
    
    if not link_messages:
        await interaction.followup.send("❌ No deleted link messages found!")
        return
    
    # Create paginated embeds
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        page = 1
    
    # Create all embeds for pagination
    embeds = []
    for p in range(1, total_pages + 1):
        p_start_idx = (p - 1) * MESSAGES_PER_PAGE
        p_end_idx = min(p_start_idx + MESSAGES_PER_PAGE, len(link_messages))
        p_page_messages = link_messages[p_start_idx:p_end_idx]
        
        p_embed = discord.Embed(
            title=f"🔗 Deleted Link Messages - {target_channel.name}",
            color=discord.Color.purple()
        )
        
        for i, msg in enumerate(p_page_messages, start=p_start_idx + 1):
            content = msg['content'] or "*No text content*"
            if len(content) > 100:
                content = content[:97] + "..."
            
            p_embed.add_field(
                name=f"{i}. {msg['author'].display_name}",
                value=content,
                inline=False
            )
        
        p_embed.set_footer(text=f"Page {p} of {total_pages} | {len(link_messages)} total messages")
        embeds.append(p_embed)
    
    if len(embeds) == 1:
        await interaction.followup.send(embed=embeds[0])
    else:
        view = PaginationView(embeds)
        view.current_page = page - 1
        view.update_buttons()
        await interaction.followup.send(embed=embeds[page - 1], view=view)

# FIXED: Namelock slash command with proper nickname parameter
@bot.tree.command(name="namelock", description="Lock a user's nickname")
@check_not_blocked()
async def namelock_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    """Lock a user's nickname"""
    if not (interaction.user.guild_permissions.manage_nicknames or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to manage nicknames!", ephemeral=True)
        return
    
    if member.id in namelock_immune_users:
        await interaction.response.send_message("❌ This user is immune to namelock!", ephemeral=True)
        return
    
    if member.id == interaction.guild.owner_id:
        await interaction.response.send_message("❌ Cannot namelock the server owner!", ephemeral=True)
        return
    
    # FIXED: Use the actual nickname parameter instead of hardcoded "test"
    try:
        await member.edit(nick=nickname, reason=f"Namelocked by {interaction.user}")
        
        # Store namelock data
        namelocked_users[member.id] = {
            'guild_id': interaction.guild.id,
            'nickname': nickname
        }
        
        await interaction.response.send_message(f"✅ **{member.display_name}** has been namelocked to `{nickname}`")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change this user's nickname!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="unl", description="Unlock a user's nickname")
@check_not_blocked()
async def nameunlock_slash(interaction: discord.Interaction, member: discord.Member):
    """Unlock a user's nickname"""
    if not (interaction.user.guild_permissions.manage_nicknames or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to manage nicknames!", ephemeral=True)
        return
    
    if member.id not in namelocked_users:
        await interaction.response.send_message("❌ This user is not namelocked!", ephemeral=True)
        return
    
    # Remove from namelocked users
    del namelocked_users[member.id]
    
    await interaction.response.send_message(f"✅ **{member.display_name}** has been unlocked from namelock")

@bot.tree.command(name="rename", description="Change a user's nickname")
@check_not_blocked()
async def rename_slash(interaction: discord.Interaction, member: discord.Member, nickname: str = None):
    """Change a user's nickname"""
    if not (interaction.user.guild_permissions.manage_nicknames or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to manage nicknames!", ephemeral=True)
        return
    
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname, reason=f"Renamed by {interaction.user}")
        new_nick = member.display_name
        
        await interaction.response.send_message(f"✅ Renamed **{old_nick}** to **{new_nick}**")
    
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change this user's nickname!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="say", description="Send a message as the bot")
@check_not_blocked()
async def say_slash(interaction: discord.Interaction, message: str):
    """Send a message as the bot"""
    if not (interaction.user.guild_permissions.manage_messages or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    await interaction.response.send_message("✅ Message sent!", ephemeral=True)
    await interaction.channel.send(message)

# FIXED: Enhanced saywb slash command with channel parameter and optional title/description
@bot.tree.command(name="saywb", description="Send an embed message to a channel")
@check_not_blocked()
async def saywb_slash(interaction: discord.Interaction, channel: discord.TextChannel, color: str = None, title: str = None, description: str = None):
    """Send an embed message - FIXED with channel parameter and optional title/description"""
    if not (interaction.user.guild_permissions.manage_messages or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to use this command!", ephemeral=True)
        return
    
    # FIXED: Require at least title or description
    if not title and not description:
        await interaction.response.send_message("❌ Please provide at least a title or description!", ephemeral=True)
        return
    
    # Parse color with enhanced support
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Create embed
    embed = discord.Embed(color=embed_color)
    
    if title:
        embed.title = title
    
    if description:
        embed.description = description
    
    # Send to specified channel
    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ Message sent to {channel.mention}", ephemeral=True)

# FIXED: Enhanced create slash command with title and color support
@bot.tree.command(name="create", description="Create reaction roles with title")
@check_not_blocked()
async def create_slash(interaction: discord.Interaction, title: str, color: str = None, 
                      emoji1: str = None, role1: discord.Role = None,
                      emoji2: str = None, role2: discord.Role = None,
                      emoji3: str = None, role3: discord.Role = None,
                      emoji4: str = None, role4: discord.Role = None,
                      emoji5: str = None, role5: discord.Role = None,
                      emoji6: str = None, role6: discord.Role = None):
    """Create reaction roles with title - FIXED format"""
    if not (interaction.user.guild_permissions.manage_roles or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to manage roles!", ephemeral=True)
        return
    
    # Collect role mappings
    role_mappings = []
    if emoji1 and role1:
        role_mappings.append((emoji1, role1))
    if emoji2 and role2:
        role_mappings.append((emoji2, role2))
    if emoji3 and role3:
        role_mappings.append((emoji3, role3))
    if emoji4 and role4:
        role_mappings.append((emoji4, role4))
    if emoji5 and role5:
        role_mappings.append((emoji5, role5))
    if emoji6 and role6:
        role_mappings.append((emoji6, role6))
    
    if not role_mappings:
        await interaction.response.send_message("❌ Please provide at least one emoji-role pair!", ephemeral=True)
        return
    
    # Create role map
    role_map = {}
    for emoji, role in role_mappings:
        role_map[emoji] = role.id
    
    # Parse color with enhanced support
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Create embed with title
    embed = discord.Embed(
        title=title,
        description="Click the buttons below to get/remove roles:",
        color=embed_color
    )
    
    # Add role information
    role_info = []
    for emoji, role in role_mappings:
        role_info.append(f"{emoji} - {role.name}")
    
    embed.add_field(name="Available Roles", value="\n".join(role_info), inline=False)
    
    # Create view with buttons
    view = ReactionRoleView(role_map)
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="block", description="Block a user from using the bot")
@check_not_blocked()
async def block_slash(interaction: discord.Interaction, user: discord.User):
    """Block a user from using the bot"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command!", ephemeral=True)
        return
    
    if user.id == BOT_OWNER_ID:
        await interaction.response.send_message("❌ Cannot block the bot owner!", ephemeral=True)
        return
    
    if user.id in blocked_users:
        await interaction.response.send_message("❌ User is already blocked!", ephemeral=True)
        return
    
    blocked_users.add(user.id)
    await interaction.response.send_message(f"✅ **{user.name}** has been blocked from using the bot")

@bot.tree.command(name="unblock", description="Unblock a user from using the bot")
async def unblock_slash(interaction: discord.Interaction, user: discord.User):
    """Unblock a user from using the bot"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command!", ephemeral=True)
        return
    
    if user.id not in blocked_users:
        await interaction.response.send_message("❌ User is not blocked!", ephemeral=True)
        return
    
    blocked_users.remove(user.id)
    await interaction.response.send_message(f"✅ **{user.name}** has been unblocked")

# FIXED: Enhanced giveaway command with advanced requirements and image support
@bot.tree.command(name="giveaway", description="Create a giveaway with advanced requirements")
@check_not_blocked()
async def giveaway_slash(interaction: discord.Interaction, 
                        title: str,
                        duration: str,
                        winners: int = 1,
                        message_req: int = None,
                        role_req: discord.Role = None,
                        blacklisted_role: discord.Role = None,
                        image: str = None):
    """Create an advanced giveaway with requirements and image support"""
    if not (is_bot_owner(interaction.user.id) or 
            interaction.user.guild_permissions.administrator or 
            can_host_giveaway(interaction.user)):
        await interaction.response.send_message("❌ You don't have permission to host giveaways!", ephemeral=True)
        return
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        await interaction.response.send_message("❌ Invalid duration! Use format like: 10s, 5m, 1h, 2d", ephemeral=True)
        return
    
    if duration_seconds < 10:
        await interaction.response.send_message("❌ Minimum giveaway duration is 10 seconds!", ephemeral=True)
        return
    
    if winners < 1 or winners > 20:
        await interaction.response.send_message("❌ Number of winners must be between 1 and 20!", ephemeral=True)
        return
    
    # Create requirements
    requirements = {}
    if message_req and message_req > 0:
        requirements['messages'] = message_req
    
    if role_req:
        requirements['required_role'] = role_req.name
    
    if blacklisted_role:
        requirements['blacklisted_role'] = blacklisted_role.name
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Create embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="Prize", value=title, inline=False)
    embed.add_field(name="Duration", value=format_duration(duration_seconds), inline=True)
    embed.add_field(name="Winners", value=str(winners), inline=True)
    
    # Add requirements if any
    if requirements:
        req_text = []
        if 'messages' in requirements:
            req_text.append(f"• Minimum {requirements['messages']} messages")
        if 'required_role' in requirements:
            req_text.append(f"• Must have role: {requirements['required_role']}")
        if 'blacklisted_role' in requirements:
            req_text.append(f"• Cannot have role: {requirements['blacklisted_role']}")
        
        embed.add_field(name="Requirements", value="\n".join(req_text), inline=False)
    
    embed.add_field(name="⏰ Ends", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
    embed.add_field(name="How to Join", value="Click Join to participate!", inline=False)
    
    # Add image if provided
    if image:
        # Check if it's a valid URL
        if image.startswith('http'):
            embed.set_image(url=image)
        else:
            await interaction.response.send_message("❌ Invalid image URL! Must start with http:// or https://", ephemeral=True)
            return
    
    await interaction.response.send_message("✅ Creating giveaway...", ephemeral=True)
    
    # Send giveaway message with buttons
    giveaway_message = await interaction.channel.send(embed=embed)
    
    # FIXED: Create view with proper message ID and attach it
    view = GiveawayView(giveaway_message.id)
    await giveaway_message.edit(embed=embed, view=view)
    
    # Store giveaway data
    active_giveaways[giveaway_message.id] = {
        'prize': title,
        'end_time': end_time,
        'winner_count': winners,
        'host_id': interaction.user.id,
        'channel_id': interaction.channel.id,
        'participants': [],
        'requirements': requirements if requirements else None
    }
    
    await interaction.edit_original_response(content="✅ Giveaway created successfully!")

@bot.tree.command(name="giveaway_host", description="Set roles that can host giveaways")
@check_not_blocked()
async def giveaway_host_slash(interaction: discord.Interaction, role: discord.Role):
    """Set roles that can host giveaways"""
    if not (interaction.user.guild_permissions.administrator or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need administrator permissions to use this command!", ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = set()
    
    if role.id in giveaway_host_roles[guild_id]:
        giveaway_host_roles[guild_id].remove(role.id)
        await interaction.response.send_message(f"✅ Removed **{role.name}** from giveaway host roles")
    else:
        giveaway_host_roles[guild_id].add(role.id)
        await interaction.response.send_message(f"✅ Added **{role.name}** to giveaway host roles")

@bot.tree.command(name="giveaways", description="Show active giveaways")
@check_not_blocked()
async def giveaways_slash(interaction: discord.Interaction):
    """Show active giveaways"""
    if not active_giveaways:
        await interaction.response.send_message("❌ No active giveaways!", ephemeral=True)
        return
    
    embed = discord.Embed(title="🎉 Active Giveaways", color=discord.Color.blue())
    
    guild_giveaways = []
    for message_id, giveaway in active_giveaways.items():
        if giveaway['channel_id'] in [c.id for c in interaction.guild.channels]:
            channel = bot.get_channel(giveaway['channel_id'])
            if channel:
                time_left = giveaway['end_time'] - datetime.utcnow()
                if time_left.total_seconds() > 0:
                    guild_giveaways.append(f"**{giveaway['prize']}** in {channel.mention}\nEnds <t:{int(giveaway['end_time'].timestamp())}:R>\nParticipants: {len(giveaway['participants'])}")
    
    if not guild_giveaways:
        await interaction.response.send_message("❌ No active giveaways in this server!", ephemeral=True)
        return
    
    embed.description = "\n\n".join(guild_giveaways)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="mess", description="Send a DM to a user globally")
@check_not_blocked()
async def mess_slash(interaction: discord.Interaction, user: discord.User, message: str):
    """Send a DM to a user globally"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command!", ephemeral=True)
        return
    
    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ Message sent to **{user.name}**", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Cannot send DM to this user!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="role", description="Add a role to a user")
@check_not_blocked()
async def role_slash(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    """Add a role to a user"""
    if not (interaction.user.guild_permissions.manage_roles or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to manage roles!", ephemeral=True)
        return
    
    try:
        await member.add_roles(role, reason=f"Added by {interaction.user}")
        await interaction.response.send_message(f"✅ Added role **{role.name}** to **{member.display_name}**")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage this role!", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="namelockimmune", description="Make a user immune to namelock")
@check_not_blocked()
async def namelock_immune_slash(interaction: discord.Interaction, member: discord.Member):
    """Make a user immune to namelock"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command!", ephemeral=True)
        return
    
    if member.id in namelock_immune_users:
        namelock_immune_users.remove(member.id)
        await interaction.response.send_message(f"✅ **{member.display_name}** is no longer immune to namelock")
    else:
        namelock_immune_users.add(member.id)
        await interaction.response.send_message(f"✅ **{member.display_name}** is now immune to namelock")

@bot.tree.command(name="manage", description="Show bot management panel")
@check_not_blocked()
async def manage_slash(interaction: discord.Interaction):
    """Show bot management panel"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command!", ephemeral=True)
        return
    
    uptime_seconds = time.time() - BOT_START_TIME
    uptime_str = format_uptime(uptime_seconds)
    
    embed = discord.Embed(title="🔧 Bot Management Panel", color=discord.Color.blue())
    embed.add_field(name="📊 Statistics", value=f"**Guilds:** {len(bot.guilds)}\n**Users:** {len(bot.users)}\n**Uptime:** {uptime_str}", inline=False)
    embed.add_field(name="🚫 Blocked Users", value=f"{len(blocked_users)} users", inline=True)
    embed.add_field(name="🔒 Namelocked Users", value=f"{len(namelocked_users)} users", inline=True)
    embed.add_field(name="🎉 Active Giveaways", value=f"{len(active_giveaways)} giveaways", inline=True)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="ping", description="Show bot latency")
async def ping_slash(interaction: discord.Interaction):
    """Show bot latency"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", description=f"Bot latency: **{latency}ms**", color=discord.Color.green())
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="prefix", description="Change server prefix")
@check_not_blocked()
async def prefix_slash(interaction: discord.Interaction, new_prefix: str):
    """Change server prefix"""
    if not (interaction.user.guild_permissions.administrator or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need administrator permissions to change the prefix!", ephemeral=True)
        return
    
    if len(new_prefix) > 5:
        await interaction.response.send_message("❌ Prefix cannot be longer than 5 characters!", ephemeral=True)
        return
    
    custom_prefixes[interaction.guild.id] = new_prefix
    await interaction.response.send_message(f"✅ Server prefix changed to `{new_prefix}`")

# Run the bot
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))

# Import and setup enhanced commands
try:
    from enhanced_commands import setup_enhanced_commands
    setup_enhanced_commands(
        bot, 
        sniped_messages, 
        MESSAGES_PER_PAGE, 
        detect_media_type, 
        get_media_url, 
        is_offensive_content, 
        is_user_blocked
    )
    print("✅ Enhanced commands loaded!")
except Exception as e:
    print(f"❌ Error loading enhanced commands: {e}")

