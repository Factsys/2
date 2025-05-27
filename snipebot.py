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
namelocked_users = {}
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
                description=f"**🎊 Congratulations {new_winner.mention}!**\n**Prize:** {self.giveaway_data['prize']}",
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
                    ("**Giveaways**", "`,gw [id]` `/gw` - Reroll giveaway winner\n`/giveaway` - Create advanced giveaway with requirements\n`/giveaway_host [@role]` - Set giveaway host roles", False),
                    ("**Management**", "`,block` `/block` - Block user from bot\n`,mess` `/mess` - DM user globally\n`,role` `/role` - Add role to user\n`,namelockimmune` `,nli` `/namelockimmune` - Make user immune", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 3",
                "fields": [
                    ("**Reaction Roles**", "`,create` `/create` - Create reaction roles with title (1-6 options)", False),
                    ("**Bot Features**", "`,manage` `/manage` - Bot management panel\n`/unblock` - Unblock user from bot\n`/ping` - Show bot latency\n`/prefix` - Change server prefix", False)
                ]
            },
            {
                "title": "📜 FACTSY Commands - Page 4",
                "fields": [
                    ("**Info**", "All commands support both prefix and slash (/) versions\nModerators can use most commands\nBlocked users cannot use any bot functions\nAdvanced giveaway requirements system included", False),
                    ("**Usage Examples**", "`,s 5` - Show 5th deleted message\n`/saywb #general My Title My Description red` - Send embed\n`/giveaway MyPrize 1h 2 messages:10 rolereq:Member` - Advanced giveaway\n`/create My Title red 🎮 Gamer` - Reaction role", False)
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
    print(f'{bot.user} has landed and is ready!')
    print(f'Bot is in {len(bot.guilds)} servers')
    
    # Start the giveaway timer
    giveaway_timer.start()
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# FIXED: Giveaway timer task that properly ends giveaways
@tasks.loop(seconds=10)
async def giveaway_timer():
    """Check for ended giveaways and process them"""
    current_time = datetime.utcnow()
    ended_giveaways = []
    
    for message_id, giveaway in active_giveaways.items():
        if current_time >= giveaway['end_time']:
            ended_giveaways.append(message_id)
    
    for message_id in ended_giveaways:
        giveaway = active_giveaways[message_id]
        channel = bot.get_channel(giveaway['channel_id'])
        
        if not channel:
            del active_giveaways[message_id]
            continue
        
        participants = giveaway['participants']
        
        if not participants:
            # No participants
            embed = discord.Embed(
                title="🎉 Giveaway Ended",
                description=f"**Prize:** {giveaway['prize']}\n**Winner:** No participants 😢",
                color=discord.Color.red()
            )
            try:
                await channel.send(embed=embed)
            except:
                pass
        else:
            # Select winners
            winners_count = min(giveaway['winners'], len(participants))
            winners = random.sample(participants, winners_count)
            
            winner_mentions = []
            for winner_id in winners:
                winner = bot.get_user(winner_id)
                if winner:
                    winner_mentions.append(winner.mention)
                    # Send DM to winner
                    try:
                        await winner.send(f"🎉 **Congratulations!** You won **{giveaway['prize']}** in {channel.guild.name}!")
                    except:
                        pass
            
            winner_text = ", ".join(winner_mentions) if winner_mentions else "Unknown winners"
            
            embed = discord.Embed(
                title="🎉 Giveaway Ended!",
                description=f"**Prize:** {giveaway['prize']}\n**Winners:** {winner_text}",
                color=discord.Color.green()
            )
            
            # Add reroll view
            view = RerollView(giveaway)
            
            try:
                # Send winner announcement with reroll button
                await channel.send(f"{winner_text} 🎊", embed=embed, view=view)
            except:
                pass
        
        # Remove from active giveaways
        del active_giveaways[message_id]

@giveaway_timer.before_loop
async def before_giveaway_timer():
    await bot.wait_until_ready()

# ENHANCED: Message delete event with FIXED media handling and clean snipe display
@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return
    
    if message.guild is None:
        return
    
    increment_user_message_count(message.guild.id, message.author.id)
    
    channel_id = message.channel.id
    
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []
    
    # FIXED: Enhanced media detection with proper attachment handling
    media_urls = get_media_url(message.content, message.attachments)
    cleaned_content = clean_content_from_media(message.content, media_urls)
    
    # Check if message contains offensive content
    is_offensive = is_offensive_content(message.content) if message.content else False
    filtered_content = filter_content(message.content) if message.content else None
    
    # Store snipe data with enhanced information
    snipe_data = {
        'author': message.author,
        'author_id': message.author.id,
        'content': message.content,
        'cleaned_content': cleaned_content,
        'filtered_content': filtered_content,
        'is_offensive': is_offensive,
        'media_urls': media_urls,
        'timestamp': message.created_at,
        'channel': message.channel,
        'has_links': has_links(message.content),
        'message_type': 'normal'
    }
    
    # Categorize message type for filtering
    if media_urls:
        snipe_data['message_type'] = 'media'
    elif has_links(message.content):
        snipe_data['message_type'] = 'link'
    elif is_offensive:
        snipe_data['message_type'] = 'filtered'
    
    sniped_messages[channel_id].append(snipe_data)
    
    if len(sniped_messages[channel_id]) > MAX_MESSAGES:
        sniped_messages[channel_id].pop(0)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    if before.guild is None:
        return
    
    if before.content == after.content:
        return
    
    channel_id = before.channel.id
    
    if channel_id not in edited_messages:
        edited_messages[channel_id] = []
    
    edit_data = {
        'author': before.author,
        'author_id': before.author.id,
        'before_content': before.content,
        'after_content': after.content,
        'timestamp': after.edited_at or datetime.utcnow(),
        'channel': before.channel
    }
    
    edited_messages[channel_id].append(edit_data)
    
    if len(edited_messages[channel_id]) > MAX_MESSAGES:
        edited_messages[channel_id].pop(0)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
        
        # Check for namelocked users
        if message.author.id in namelocked_users:
            if message.author.id not in namelock_immune_users:
                guild = message.guild
                member = guild.get_member(message.author.id)
                if member:
                    locked_nick = namelocked_users[message.author.id]
                    if member.display_name != locked_nick:
                        try:
                            await member.edit(nick=locked_nick)
                        except discord.Forbidden:
                            pass
    
    await bot.process_commands(message)

# ENHANCED: Snipe command with clean display (only context and original owner)
@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe_command(ctx, number: int = 1):
    """Show deleted messages with clean display - ENHANCED"""
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("🔍 No deleted messages found in this channel.")
        return
    
    if number < 1 or number > len(sniped_messages[channel_id]):
        await ctx.send(f"❌ Invalid number. Use 1-{len(sniped_messages[channel_id])}")
        return
    
    snipe_data = sniped_messages[channel_id][-number]
    
    # CLEAN DISPLAY: Only show context and original owner
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.blue(),
        timestamp=snipe_data['timestamp']
    )
    
    # Show original owner
    embed.set_author(
        name=f"{snipe_data['author'].display_name}",
        icon_url=snipe_data['author'].display_avatar.url
    )
    
    # Show context (filtered content for offensive messages)
    if snipe_data['is_offensive']:
        if snipe_data['filtered_content']:
            embed.add_field(name="Content", value=snipe_data['filtered_content'], inline=False)
    else:
        if snipe_data['cleaned_content']:
            embed.add_field(name="Content", value=snipe_data['cleaned_content'], inline=False)
    
    # Show media visually if present
    if snipe_data['media_urls']:
        for media in snipe_data['media_urls']:
            if media['type'] in ['image', 'gif', 'tenor_gif']:
                embed.set_image(url=media['url'])
                break
            elif media['type'] == 'video':
                embed.add_field(name="Video", value=f"[View Video]({media['url']})", inline=False)
                break
    
    await ctx.send(embed=embed)

# ENHANCED: SPF command to show only filtered/offensive messages
@bot.command(name='spf')
@not_blocked()
async def snipe_filtered_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """Show only filtered/offensive deleted messages - ENHANCED"""
    if not channel:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send(f"🔍 No deleted messages found in {channel.mention}.")
        return
    
    # Filter only offensive messages
    filtered_messages = [msg for msg in sniped_messages[channel_id] if msg['is_offensive']]
    
    if not filtered_messages:
        await ctx.send(f"🔍 No filtered messages found in {channel.mention}.")
        return
    
    total_pages = math.ceil(len(filtered_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page. Use 1-{total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(filtered_messages))
    page_messages = filtered_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🚫 Filtered Messages in {channel.name}",
        color=discord.Color.red()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        # Show UNFILTERED content in SPF
        content = msg['content'] if msg['content'] else "*No text content*"
        content = truncate_content(content, 100)
        
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} | Total: {len(filtered_messages)}")
    
    # Add pagination if needed
    if total_pages > 1:
        embeds = []
        for p in range(1, total_pages + 1):
            page_embed = await create_spf_page_embed(filtered_messages, p, channel)
            embeds.append(page_embed)
        
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[page-1], view=view)
    else:
        await ctx.send(embed=embed)

async def create_spf_page_embed(filtered_messages, page, channel):
    """Helper function to create SPF page embeds"""
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(filtered_messages))
    page_messages = filtered_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🚫 Filtered Messages in {channel.name}",
        color=discord.Color.red()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = msg['content'] if msg['content'] else "*No text content*"
        content = truncate_content(content, 100)
        
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    total_pages = math.ceil(len(filtered_messages) / MESSAGES_PER_PAGE)
    embed.set_footer(text=f"Page {page} of {total_pages} | Total: {len(filtered_messages)}")
    
    return embed

# ENHANCED: SP command with pagination using < > emoji buttons
@bot.command(name='sp')
@not_blocked()
async def snipe_list_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List normal deleted messages with pagination - ENHANCED"""
    if not channel:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send(f"🔍 No deleted messages found in {channel.mention}.")
        return
    
    # Filter normal messages (not links, not offensive)
    normal_messages = [msg for msg in sniped_messages[channel_id] 
                      if not msg['has_links'] and not msg['is_offensive']]
    
    if not normal_messages:
        await ctx.send(f"🔍 No normal messages found in {channel.mention}.")
        return
    
    total_pages = math.ceil(len(normal_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page. Use 1-{total_pages}")
        return
    
    # Create embeds for all pages
    embeds = []
    for p in range(1, total_pages + 1):
        page_embed = await create_sp_page_embed(normal_messages, p, channel)
        embeds.append(page_embed)
    
    # Show with pagination if more than 1 page
    if total_pages > 1:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[page-1], view=view)
    else:
        await ctx.send(embed=embeds[0])

async def create_sp_page_embed(normal_messages, page, channel):
    """Helper function to create SP page embeds"""
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(normal_messages))
    page_messages = normal_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"📜 Normal Messages in {channel.name}",
        color=discord.Color.blue()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = msg['cleaned_content'] if msg['cleaned_content'] else "*No text content*"
        content = truncate_content(content, 100)
        
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    total_pages = math.ceil(len(normal_messages) / MESSAGES_PER_PAGE)
    embed.set_footer(text=f"Page {page} of {total_pages} | Total: {len(normal_messages)}")
    
    return embed

# ENHANCED: SPL command for link messages with pagination
@bot.command(name='spl')
@not_blocked()
async def snipe_links_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """Show deleted link messages with pagination - ENHANCED"""
    if not channel:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send(f"🔍 No deleted messages found in {channel.mention}.")
        return
    
    # Filter link messages
    link_messages = [msg for msg in sniped_messages[channel_id] if msg['has_links']]
    
    if not link_messages:
        await ctx.send(f"🔍 No link messages found in {channel.mention}.")
        return
    
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page. Use 1-{total_pages}")
        return
    
    # Create embeds for all pages
    embeds = []
    for p in range(1, total_pages + 1):
        page_embed = await create_spl_page_embed(link_messages, p, channel)
        embeds.append(page_embed)
    
    # Show with pagination if more than 1 page
    if total_pages > 1:
        view = PaginationView(embeds)
        await ctx.send(embed=embeds[page-1], view=view)
    else:
        await ctx.send(embed=embeds[0])

async def create_spl_page_embed(link_messages, page, channel):
    """Helper function to create SPL page embeds"""
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(link_messages))
    page_messages = link_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔗 Link Messages in {channel.name}",
        color=discord.Color.green()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = msg['content'] if msg['content'] else "*No text content*"
        content = truncate_content(content, 100)
        
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    embed.set_footer(text=f"Page {page} of {total_pages} | Total: {len(link_messages)}")
    
    return embed

@bot.command(name='editsnipe', aliases=['es'])
@not_blocked()
async def editsnipe_command(ctx):
    """Show last edited message"""
    channel_id = ctx.channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await ctx.send("🔍 No edited messages found in this channel.")
        return
    
    edit_data = edited_messages[channel_id][-1]
    
    embed = discord.Embed(
        title="📝 Last Edited Message",
        color=discord.Color.orange(),
        timestamp=edit_data['timestamp']
    )
    
    embed.set_author(
        name=edit_data['author'].display_name,
        icon_url=edit_data['author'].display_avatar.url
    )
    
    if edit_data['before_content']:
        embed.add_field(name="Before", value=edit_data['before_content'][:1024], inline=False)
    
    if edit_data['after_content']:
        embed.add_field(name="After", value=edit_data['after_content'][:1024], inline=False)
    
    await ctx.send(embed=embed)

# FIXED: Namelock command with proper nickname handling
@bot.command(name='namelock', aliases=['nl'])
@not_blocked()
async def namelock_command(ctx, member: discord.Member, *, nickname):
    """Lock a user's nickname - FIXED to use actual nickname parameter"""
    if not (ctx.author.guild_permissions.manage_nicknames or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to manage nicknames.")
        return
    
    if member.id in namelock_immune_users:
        await ctx.send("❌ This user is immune to namelocking.")
        return
    
    try:
        # FIXED: Use the actual nickname parameter instead of "test"
        await member.edit(nick=nickname)
        namelocked_users[member.id] = nickname
        
        embed = discord.Embed(
            title="🔒 User Namelocked",
            description=f"**User:** {member.mention}\n**Locked Nickname:** {nickname}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='unl')
@not_blocked()
async def unlock_namelock_command(ctx, member: discord.Member):
    """Unlock a user's nickname"""
    if not (ctx.author.guild_permissions.manage_nicknames or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to manage nicknames.")
        return
    
    if member.id not in namelocked_users:
        await ctx.send("❌ This user is not namelocked.")
        return
    
    del namelocked_users[member.id]
    
    embed = discord.Embed(
        title="🔓 User Unlocked",
        description=f"**User:** {member.mention}\nNickname lock removed.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command(name='rename', aliases=['re'])
@not_blocked()
async def rename_command(ctx, member: discord.Member, *, nickname):
    """Change a user's nickname"""
    if not (ctx.author.guild_permissions.manage_nicknames or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to manage nicknames.")
        return
    
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname)
        
        embed = discord.Embed(
            title="✏️ Nickname Changed",
            color=discord.Color.blue()
        )
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Old Nickname", value=old_nick, inline=True)
        embed.add_field(name="New Nickname", value=nickname, inline=True)
        
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='namelockimmune', aliases=['nli'])
@not_blocked()
async def namelock_immune_command(ctx, member: discord.Member):
    """Make a user immune to namelocking"""
    if not (ctx.author.guild_permissions.administrator or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You need administrator permissions to use this command.")
        return
    
    if member.id in namelock_immune_users:
        await ctx.send("❌ This user is already immune to namelocking.")
        return
    
    namelock_immune_users.add(member.id)
    
    embed = discord.Embed(
        title="🛡️ User Made Immune",
        description=f"**User:** {member.mention}\nThis user is now immune to namelocking.",
        color=discord.Color.gold()
    )
    await ctx.send(embed=embed)

@bot.command(name='say')
@not_blocked()
async def say_command(ctx, *, message):
    """Send a message as the bot"""
    if not (ctx.author.guild_permissions.manage_messages or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    try:
        await ctx.message.delete()
    except:
        pass
    
    await ctx.send(message)

# ENHANCED: SAYWB command with channel parameter
@bot.command(name='saywb')
@not_blocked()
async def saywb_command(ctx, channel: discord.TextChannel = None, color: str = None, *, content):
    """Send embed message with optional channel, title, and description - ENHANCED"""
    if not (ctx.author.guild_permissions.manage_messages or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to use this command.")
        return
    
    if not channel:
        channel = ctx.channel
    
    # Parse content for title and description
    parts = content.split('|', 1) if '|' in content else [content]
    title = parts[0].strip() if parts[0].strip() else None
    description = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    
    # If no separator, treat as description only
    if not title and not description:
        description = content
        title = None
    
    embed_color = parse_color(color) if color else discord.Color.default()
    
    embed = discord.Embed(color=embed_color)
    
    if title:
        embed.title = title
    if description:
        embed.description = description
    
    try:
        await ctx.message.delete()
    except:
        pass
    
    try:
        await channel.send(embed=embed)
        if channel != ctx.channel:
            await ctx.send(f"✅ Embed sent to {channel.mention}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to send messages in that channel.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='block')
@not_blocked()
async def block_command(ctx, user: discord.User):
    """Block a user from using the bot"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    if user.id == BOT_OWNER_ID:
        await ctx.send("❌ Cannot block the bot owner.")
        return
    
    if user.id in blocked_users:
        await ctx.send("❌ This user is already blocked.")
        return
    
    blocked_users.add(user.id)
    
    embed = discord.Embed(
        title="🚫 User Blocked",
        description=f"**User:** {user.mention}\nThis user can no longer use bot functions.",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed)

@bot.command(name='mess')
@not_blocked()
async def mess_command(ctx, *, message):
    """Send a DM to a user globally"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    # Extract username from message
    parts = message.split(' ', 1)
    if len(parts) < 2:
        await ctx.send("❌ Usage: `,mess <username> <message>`")
        return
    
    username = parts[0]
    dm_message = parts[1]
    
    user = find_user_globally(username)
    if not user:
        await ctx.send(f"❌ User '{username}' not found.")
        return
    
    try:
        await user.send(dm_message)
        await ctx.send(f"✅ Message sent to {user.mention}")
    except discord.Forbidden:
        await ctx.send(f"❌ Cannot send DM to {user.mention} (DMs might be disabled)")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='role')
@not_blocked()
async def role_command(ctx, member: discord.Member, *, role_name):
    """Add a role to a user"""
    if not (ctx.author.guild_permissions.manage_roles or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to manage roles.")
        return
    
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        await ctx.send(f"❌ Role '{role_name}' not found.")
        return
    
    try:
        if role in member.roles:
            await member.remove_roles(role)
            action = "removed from"
        else:
            await member.add_roles(role)
            action = "added to"
        
        embed = discord.Embed(
            title="🎭 Role Updated",
            description=f"Role **{role.name}** has been {action} {member.mention}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage this role.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

# ENHANCED: Create command with title support instead of context
@bot.command(name='create')
@not_blocked()
async def create_reaction_roles(ctx, title, color: str = None, *role_pairs):
    """Create reaction roles with title - ENHANCED"""
    if not (ctx.author.guild_permissions.manage_roles or is_bot_owner(ctx.author.id)):
        await ctx.send("❌ You don't have permission to manage roles.")
        return
    
    if len(role_pairs) % 2 != 0:
        await ctx.send("❌ You must provide emoji and role pairs. Example: `,create \"My Title\" red 🎮 @Gamer 🎵 @Music`")
        return
    
    if len(role_pairs) > 12:  # Max 6 pairs (emoji + role)
        await ctx.send("❌ Maximum 6 emoji-role pairs allowed.")
        return
    
    if len(role_pairs) == 0:
        await ctx.send("❌ You must provide at least one emoji-role pair.")
        return
    
    # Parse emoji-role pairs
    role_mappings = {}
    for i in range(0, len(role_pairs), 2):
        emoji = role_pairs[i]
        role_mention = role_pairs[i + 1]
        
        # Try to find the role
        role = None
        if role_mention.startswith('<@&') and role_mention.endswith('>'):
            role_id = int(role_mention[3:-1])
            role = ctx.guild.get_role(role_id)
        else:
            role = discord.utils.get(ctx.guild.roles, name=role_mention.lstrip('@'))
        
        if not role:
            await ctx.send(f"❌ Role '{role_mention}' not found.")
            return
        
        role_mappings[emoji] = role.id
    
    # Create embed with title
    embed_color = parse_color(color) if color else discord.Color.default()
    
    embed = discord.Embed(
        title=title,
        color=embed_color
    )
    
    # Add role information
    role_info = []
    for emoji, role_id in role_mappings.items():
        role = ctx.guild.get_role(role_id)
        if role:
            role_info.append(f"{emoji} - {role.name}")
    
    embed.description = "\n".join(role_info)
    embed.set_footer(text="Click the emoji buttons below to get roles!")
    
    # Create view with buttons
    view = ReactionRoleView(role_mappings)
    
    try:
        await ctx.message.delete()
    except:
        pass
    
    await ctx.send(embed=embed, view=view)

@bot.command(name='gw')
@not_blocked()
async def giveaway_reroll(ctx, message_id: int = None):
    """Reroll a giveaway winner"""
    if not (is_bot_owner(ctx.author.id) or ctx.author.guild_permissions.administrator or can_host_giveaway(ctx.author)):
        await ctx.send("❌ You don't have permission to reroll giveaways.")
        return
    
    if not message_id:
        await ctx.send("❌ Please provide a message ID. Usage: `,gw <message_id>`")
        return
    
    if message_id not in active_giveaways:
        await ctx.send("❌ Giveaway not found or already ended.")
        return
    
    giveaway = active_giveaways[message_id]
    participants = giveaway['participants']
    
    if not participants:
        await ctx.send("❌ No participants in this giveaway.")
        return
    
    new_winner_id = random.choice(participants)
    new_winner = bot.get_user(new_winner_id)
    
    if new_winner:
        embed = discord.Embed(
            title="🎉 Giveaway Rerolled!",
            description=f"**🎊 Congratulations {new_winner.mention}!**\n**Prize:** {giveaway['prize']}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Rerolled by {ctx.author.name}")
        
        await ctx.send(f"{new_winner.mention} 🎊", embed=embed)
        
        # Send DM to new winner
        try:
            await new_winner.send(f"🎉 **Congratulations!** You won **{giveaway['prize']}** in {ctx.guild.name}!")
        except:
            pass
    else:
        await ctx.send("❌ Could not find the new winner.")

@bot.command(name='manage')
@not_blocked()
async def manage_command(ctx):
    """Bot management panel"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    uptime = format_uptime(time.time() - BOT_START_TIME)
    
    embed = discord.Embed(
        title="🤖 FACTSY Management Panel",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="📊 Statistics", 
                   value=f"**Servers:** {len(bot.guilds)}\n**Users:** {len(bot.users)}\n**Uptime:** {uptime}", 
                   inline=True)
    
    embed.add_field(name="🔧 Storage", 
                   value=f"**Blocked Users:** {len(blocked_users)}\n**Namelocked Users:** {len(namelocked_users)}\n**Active Giveaways:** {len(active_giveaways)}", 
                   inline=True)
    
    embed.add_field(name="📝 Messages", 
                   value=f"**Sniped Channels:** {len(sniped_messages)}\n**Edited Channels:** {len(edited_messages)}\n**Webhooks:** {len(channel_webhooks)}", 
                   inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name='help')
@not_blocked()
async def help_command(ctx):
    """Show help menu with pagination"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# Slash Commands

@bot.tree.command(name="snipe", description="Show deleted messages by number")
@check_not_blocked()
async def snipe_slash(interaction: discord.Interaction, number: int = 1):
    """Slash version of snipe command"""
    channel_id = interaction.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("🔍 No deleted messages found in this channel.", ephemeral=True)
        return
    
    if number < 1 or number > len(sniped_messages[channel_id]):
        await interaction.response.send_message(f"❌ Invalid number. Use 1-{len(sniped_messages[channel_id])}", ephemeral=True)
        return
    
    snipe_data = sniped_messages[channel_id][-number]
    
    # CLEAN DISPLAY: Only show context and original owner
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.blue(),
        timestamp=snipe_data['timestamp']
    )
    
    # Show original owner
    embed.set_author(
        name=f"{snipe_data['author'].display_name}",
        icon_url=snipe_data['author'].display_avatar.url
    )
    
    # Show context (filtered content for offensive messages)
    if snipe_data['is_offensive']:
        if snipe_data['filtered_content']:
            embed.add_field(name="Content", value=snipe_data['filtered_content'], inline=False)
    else:
        if snipe_data['cleaned_content']:
            embed.add_field(name="Content", value=snipe_data['cleaned_content'], inline=False)
    
    # Show media visually if present
    if snipe_data['media_urls']:
        for media in snipe_data['media_urls']:
            if media['type'] in ['image', 'gif', 'tenor_gif']:
                embed.set_image(url=media['url'])
                break
            elif media['type'] == 'video':
                embed.add_field(name="Video", value=f"[View Video]({media['url']})", inline=False)
                break
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="editsnipe", description="Show last edited message")
@check_not_blocked()
async def editsnipe_slash(interaction: discord.Interaction):
    """Slash version of editsnipe command"""
    channel_id = interaction.channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await interaction.response.send_message("🔍 No edited messages found in this channel.", ephemeral=True)
        return
    
    edit_data = edited_messages[channel_id][-1]
    
    embed = discord.Embed(
        title="📝 Last Edited Message",
        color=discord.Color.orange(),
        timestamp=edit_data['timestamp']
    )
    
    embed.set_author(
        name=edit_data['author'].display_name,
        icon_url=edit_data['author'].display_avatar.url
    )
    
    if edit_data['before_content']:
        embed.add_field(name="Before", value=edit_data['before_content'][:1024], inline=False)
    
    if edit_data['after_content']:
        embed.add_field(name="After", value=edit_data['after_content'][:1024], inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sp", description="List normal deleted messages")
@check_not_blocked()
async def sp_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """Slash version of sp command"""
    if not channel:
        channel = interaction.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message(f"🔍 No deleted messages found in {channel.mention}.", ephemeral=True)
        return
    
    # Filter normal messages (not links, not offensive)
    normal_messages = [msg for msg in sniped_messages[channel_id] 
                      if not msg['has_links'] and not msg['is_offensive']]
    
    if not normal_messages:
        await interaction.response.send_message(f"🔍 No normal messages found in {channel.mention}.", ephemeral=True)
        return
    
    total_pages = math.ceil(len(normal_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Invalid page. Use 1-{total_pages}", ephemeral=True)
        return
    
    # Create embeds for all pages
    embeds = []
    for p in range(1, total_pages + 1):
        page_embed = await create_sp_page_embed(normal_messages, p, channel)
        embeds.append(page_embed)
    
    # Show with pagination if more than 1 page
    if total_pages > 1:
        view = PaginationView(embeds)
        await interaction.response.send_message(embed=embeds[page-1], view=view)
    else:
        await interaction.response.send_message(embed=embeds[0])

@bot.tree.command(name="spf", description="Show filtered/offensive deleted messages")
@check_not_blocked()
async def spf_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """Slash version of spf command"""
    if not channel:
        channel = interaction.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message(f"🔍 No deleted messages found in {channel.mention}.", ephemeral=True)
        return
    
    # Filter only offensive messages
    filtered_messages = [msg for msg in sniped_messages[channel_id] if msg['is_offensive']]
    
    if not filtered_messages:
        await interaction.response.send_message(f"🔍 No filtered messages found in {channel.mention}.", ephemeral=True)
        return
    
    total_pages = math.ceil(len(filtered_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Invalid page. Use 1-{total_pages}", ephemeral=True)
        return
    
    # Create embeds for all pages
    embeds = []
    for p in range(1, total_pages + 1):
        page_embed = await create_spf_page_embed(filtered_messages, p, channel)
        embeds.append(page_embed)
    
    # Show with pagination if more than 1 page
    if total_pages > 1:
        view = PaginationView(embeds)
        await interaction.response.send_message(embed=embeds[page-1], view=view)
    else:
        await interaction.response.send_message(embed=embeds[0])

@bot.tree.command(name="spl", description="Show deleted link messages")
@check_not_blocked()
async def spl_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """Slash version of spl command"""
    if not channel:
        channel = interaction.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message(f"🔍 No deleted messages found in {channel.mention}.", ephemeral=True)
        return
    
    # Filter link messages
    link_messages = [msg for msg in sniped_messages[channel_id] if msg['has_links']]
    
    if not link_messages:
        await interaction.response.send_message(f"🔍 No link messages found in {channel.mention}.", ephemeral=True)
        return
    
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Invalid page. Use 1-{total_pages}", ephemeral=True)
        return
    
    # Create embeds for all pages
    embeds = []
    for p in range(1, total_pages + 1):
        page_embed = await create_spl_page_embed(link_messages, p, channel)
        embeds.append(page_embed)
    
    # Show with pagination if more than 1 page
    if total_pages > 1:
        view = PaginationView(embeds)
        await interaction.response.send_message(embed=embeds[page-1], view=view)
    else:
        await interaction.response.send_message(embed=embeds[0])

@bot.tree.command(name="namelock", description="Lock a user's nickname")
@check_not_blocked()
async def namelock_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    """Slash version of namelock command - FIXED"""
    if not (interaction.user.guild_permissions.manage_nicknames or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to manage nicknames.", ephemeral=True)
        return
    
    if member.id in namelock_immune_users:
        await interaction.response.send_message("❌ This user is immune to namelocking.", ephemeral=True)
        return
    
    try:
        # FIXED: Use the actual nickname parameter
        await member.edit(nick=nickname)
        namelocked_users[member.id] = nickname
        
        embed = discord.Embed(
            title="🔒 User Namelocked",
            description=f"**User:** {member.mention}\n**Locked Nickname:** {nickname}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change this user's nickname.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="unl", description="Unlock a user's nickname")
@check_not_blocked()
async def unl_slash(interaction: discord.Interaction, member: discord.Member):
    """Slash version of unlock namelock command"""
    if not (interaction.user.guild_permissions.manage_nicknames or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to manage nicknames.", ephemeral=True)
        return
    
    if member.id not in namelocked_users:
        await interaction.response.send_message("❌ This user is not namelocked.", ephemeral=True)
        return
    
    del namelocked_users[member.id]
    
    embed = discord.Embed(
        title="🔓 User Unlocked",
        description=f"**User:** {member.mention}\nNickname lock removed.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rename", description="Change a user's nickname")
@check_not_blocked()
async def rename_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    """Slash version of rename command"""
    if not (interaction.user.guild_permissions.manage_nicknames or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to manage nicknames.", ephemeral=True)
        return
    
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname)
        
        embed = discord.Embed(
            title="✏️ Nickname Changed",
            color=discord.Color.blue()
        )
        embed.add_field(name="User", value=member.mention, inline=True)
        embed.add_field(name="Old Nickname", value=old_nick, inline=True)
        embed.add_field(name="New Nickname", value=nickname, inline=True)
        
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change this user's nickname.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="say", description="Send a message as the bot")
@check_not_blocked()
async def say_slash(interaction: discord.Interaction, message: str):
    """Slash version of say command"""
    if not (interaction.user.guild_permissions.manage_messages or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.send_message(message)

# ENHANCED: SAYWB slash command with channel parameter and better parsing
@bot.tree.command(name="saywb", description="Send embed message with optional channel, title, and description")
@check_not_blocked()
async def saywb_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, color: str = None, title: str = None, description: str = None):
    """Enhanced slash version of saywb command"""
    if not (interaction.user.guild_permissions.manage_messages or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        return
    
    if not channel:
        channel = interaction.channel
    
    if not title and not description:
        await interaction.response.send_message("❌ You must provide either a title or description.", ephemeral=True)
        return
    
    embed_color = parse_color(color) if color else discord.Color.default()
    
    embed = discord.Embed(color=embed_color)
    
    if title:
        embed.title = title
    if description:
        embed.description = description
    
    try:
        await channel.send(embed=embed)
        if channel != interaction.channel:
            await interaction.response.send_message(f"✅ Embed sent to {channel.mention}", ephemeral=True)
        else:
            await interaction.response.send_message("✅ Embed sent!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to send messages in that channel.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# ENHANCED: Create slash command with title support
@bot.tree.command(name="create", description="Create reaction roles with title and emoji-role pairs")
@check_not_blocked()
async def create_slash(interaction: discord.Interaction, title: str, color: str = None, 
                      emoji1: str = None, role1: discord.Role = None,
                      emoji2: str = None, role2: discord.Role = None,
                      emoji3: str = None, role3: discord.Role = None,
                      emoji4: str = None, role4: discord.Role = None,
                      emoji5: str = None, role5: discord.Role = None,
                      emoji6: str = None, role6: discord.Role = None):
    """Enhanced create command with title support"""
    if not (interaction.user.guild_permissions.manage_roles or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to manage roles.", ephemeral=True)
        return
    
    # Collect emoji-role pairs
    pairs = [
        (emoji1, role1), (emoji2, role2), (emoji3, role3),
        (emoji4, role4), (emoji5, role5), (emoji6, role6)
    ]
    
    role_mappings = {}
    for emoji, role in pairs:
        if emoji and role:
            role_mappings[emoji] = role.id
    
    if not role_mappings:
        await interaction.response.send_message("❌ You must provide at least one emoji-role pair.", ephemeral=True)
        return
    
    # Create embed with title
    embed_color = parse_color(color) if color else discord.Color.default()
    
    embed = discord.Embed(
        title=title,
        color=embed_color
    )
    
    # Add role information
    role_info = []
    for emoji, role_id in role_mappings.items():
        role = interaction.guild.get_role(role_id)
        if role:
            role_info.append(f"{emoji} - {role.name}")
    
    embed.description = "\n".join(role_info)
    embed.set_footer(text="Click the emoji buttons below to get roles!")
    
    # Create view with buttons
    view = ReactionRoleView(role_mappings)
    
    await interaction.response.send_message(embed=embed, view=view)

# ENHANCED: Giveaway slash command with advanced requirements and image support
@bot.tree.command(name="giveaway", description="Create advanced giveaway with requirements and optional image")
@check_not_blocked()
async def giveaway_slash(interaction: discord.Interaction, 
                        title: str, 
                        duration: str, 
                        winners: int = 1,
                        message_req: int = None,
                        role_req: discord.Role = None,
                        blacklisted_role: discord.Role = None,
                        image_url: str = None):
    """Enhanced giveaway command with advanced requirements"""
    if not (is_bot_owner(interaction.user.id) or 
            interaction.user.guild_permissions.administrator or 
            can_host_giveaway(interaction.user)):
        await interaction.response.send_message("❌ You don't have permission to host giveaways.", ephemeral=True)
        return
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds <= 0:
        await interaction.response.send_message("❌ Invalid duration. Use format like: 1h, 30m, 2d, 45s", ephemeral=True)
        return
    
    if winners < 1 or winners > 20:
        await interaction.response.send_message("❌ Winners must be between 1 and 20.", ephemeral=True)
        return
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Build requirements
    requirements = {}
    if message_req:
        requirements['messages'] = message_req
    if role_req:
        requirements['required_role'] = role_req.name
    if blacklisted_role:
        requirements['blacklisted_role'] = blacklisted_role.name
    
    # Create giveaway embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="Prize", value=title, inline=True)
    embed.add_field(name="Duration", value=format_duration(duration_seconds), inline=True)
    embed.add_field(name="Winners", value=str(winners), inline=True)
    
    # Add requirements if any
    if requirements:
        req_text = []
        if 'messages' in requirements:
            req_text.append(f"• Must have {requirements['messages']} messages")
        if 'required_role' in requirements:
            req_text.append(f"• Must have role: {requirements['required_role']}")
        if 'blacklisted_role' in requirements:
            req_text.append(f"• Cannot have role: {requirements['blacklisted_role']}")
        
        embed.add_field(name="Requirements", value="\n".join(req_text), inline=False)
    
    embed.add_field(name="⏰ Ends", value=f"<t:{int(end_time.timestamp())}:R>", inline=False)
    embed.add_field(name="How to Enter", value="Click Join to participate!", inline=False)
    
    # Add image if provided
    if image_url:
        embed.set_image(url=image_url)
    
    embed.set_footer(text=f"Hosted by {interaction.user.display_name}")
    
    # Send the giveaway
    await interaction.response.send_message("🎉 **GIVEAWAY STARTING!** 🎉")
    
    # FIXED: Get the followup message and create view with proper message ID
    followup_msg = await interaction.followup.send(embed=embed, wait=True)
    
    # FIXED: Create view with the actual message ID
    view = GiveawayView(followup_msg.id)
    
    # FIXED: Edit the message to add the view
    await followup_msg.edit(embed=embed, view=view)
    
    # Store giveaway data
    active_giveaways[followup_msg.id] = {
        'prize': title,
        'host_id': interaction.user.id,
        'channel_id': interaction.channel.id,
        'guild_id': interaction.guild.id,
        'end_time': end_time,
        'winners': winners,
        'participants': [],
        'requirements': requirements
    }

@bot.tree.command(name="giveaway_host", description="Set roles that can host giveaways")
@check_not_blocked()
async def giveaway_host_slash(interaction: discord.Interaction, role: discord.Role):
    """Set giveaway host roles"""
    if not (interaction.user.guild_permissions.administrator or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = []
    
    if role.id in giveaway_host_roles[guild_id]:
        giveaway_host_roles[guild_id].remove(role.id)
        action = "removed from"
    else:
        giveaway_host_roles[guild_id].append(role.id)
        action = "added to"
    
    embed = discord.Embed(
        title="🎉 Giveaway Host Role Updated",
        description=f"Role **{role.name}** has been {action} giveaway host roles.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="gw", description="Reroll a giveaway winner")
@check_not_blocked()
async def gw_slash(interaction: discord.Interaction, message_id: str):
    """Slash version of giveaway reroll command"""
    if not (is_bot_owner(interaction.user.id) or 
            interaction.user.guild_permissions.administrator or 
            can_host_giveaway(interaction.user)):
        await interaction.response.send_message("❌ You don't have permission to reroll giveaways.", ephemeral=True)
        return
    
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
        return
    
    if msg_id not in active_giveaways:
        await interaction.response.send_message("❌ Giveaway not found or already ended.", ephemeral=True)
        return
    
    giveaway = active_giveaways[msg_id]
    participants = giveaway['participants']
    
    if not participants:
        await interaction.response.send_message("❌ No participants in this giveaway.", ephemeral=True)
        return
    
    new_winner_id = random.choice(participants)
    new_winner = bot.get_user(new_winner_id)
    
    if new_winner:
        embed = discord.Embed(
            title="🎉 Giveaway Rerolled!",
            description=f"**🎊 Congratulations {new_winner.mention}!**\n**Prize:** {giveaway['prize']}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Rerolled by {interaction.user.name}")
        
        await interaction.response.send_message(f"{new_winner.mention} 🎊", embed=embed)
        
        # Send DM to new winner
        try:
            await new_winner.send(f"🎉 **Congratulations!** You won **{giveaway['prize']}** in {interaction.guild.name}!")
        except:
            pass
    else:
        await interaction.response.send_message("❌ Could not find the new winner.", ephemeral=True)

@bot.tree.command(name="block", description="Block a user from using the bot")
@check_not_blocked()
async def block_slash(interaction: discord.Interaction, user: discord.User):
    """Slash version of block command"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if user.id == BOT_OWNER_ID:
        await interaction.response.send_message("❌ Cannot block the bot owner.", ephemeral=True)
        return
    
    if user.id in blocked_users:
        await interaction.response.send_message("❌ This user is already blocked.", ephemeral=True)
        return
    
    blocked_users.add(user.id)
    
    embed = discord.Embed(
        title="🚫 User Blocked",
        description=f"**User:** {user.mention}\nThis user can no longer use bot functions.",
        color=discord.Color.red()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="unblock", description="Unblock a user from using the bot")
async def unblock_slash(interaction: discord.Interaction, user: discord.User):
    """Unblock a user from using the bot"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if user.id not in blocked_users:
        await interaction.response.send_message("❌ This user is not blocked.", ephemeral=True)
        return
    
    blocked_users.remove(user.id)
    
    embed = discord.Embed(
        title="✅ User Unblocked",
        description=f"**User:** {user.mention}\nThis user can now use bot functions again.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mess", description="Send a DM to a user globally")
@check_not_blocked()
async def mess_slash(interaction: discord.Interaction, user: discord.User, message: str):
    """Slash version of mess command"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ Message sent to {user.mention}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Cannot send DM to {user.mention} (DMs might be disabled)", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="role", description="Add or remove a role from a user")
@check_not_blocked()
async def role_slash(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    """Slash version of role command"""
    if not (interaction.user.guild_permissions.manage_roles or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You don't have permission to manage roles.", ephemeral=True)
        return
    
    try:
        if role in member.roles:
            await member.remove_roles(role)
            action = "removed from"
        else:
            await member.add_roles(role)
            action = "added to"
        
        embed = discord.Embed(
            title="🎭 Role Updated",
            description=f"Role **{role.name}** has been {action} {member.mention}",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage this role.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="namelockimmune", description="Make a user immune to namelocking")
@check_not_blocked()
async def namelockimmune_slash(interaction: discord.Interaction, member: discord.Member):
    """Slash version of namelock immune command"""
    if not (interaction.user.guild_permissions.administrator or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        return
    
    if member.id in namelock_immune_users:
        namelock_immune_users.remove(member.id)
        action = "removed from"
        color = discord.Color.red()
    else:
        namelock_immune_users.add(member.id)
        action = "added to"
        color = discord.Color.gold()
    
    embed = discord.Embed(
        title="🛡️ Namelock Immunity Updated",
        description=f"**User:** {member.mention}\nThis user has been {action} namelock immunity.",
        color=color
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Show bot latency")
async def ping_slash(interaction: discord.Interaction):
    """Show bot latency"""
    latency = round(bot.latency * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"Bot latency: **{latency}ms**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="prefix", description="Change server prefix")
@check_not_blocked()
async def prefix_slash(interaction: discord.Interaction, new_prefix: str):
    """Change server prefix"""
    if not (interaction.user.guild_permissions.administrator or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need administrator permissions to change the prefix.", ephemeral=True)
        return
    
    if len(new_prefix) > 5:
        await interaction.response.send_message("❌ Prefix cannot be longer than 5 characters.", ephemeral=True)
        return
    
    custom_prefixes[interaction.guild.id] = new_prefix
    
    embed = discord.Embed(
        title="✅ Prefix Changed",
        description=f"Server prefix has been changed to: **{new_prefix}**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="manage", description="Bot management panel")
@check_not_blocked()
async def manage_slash(interaction: discord.Interaction):
    """Slash version of manage command"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    uptime = format_uptime(time.time() - BOT_START_TIME)
    
    embed = discord.Embed(
        title="🤖 FACTSY Management Panel",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="📊 Statistics", 
                   value=f"**Servers:** {len(bot.guilds)}\n**Users:** {len(bot.users)}\n**Uptime:** {uptime}", 
                   inline=True)
    
    embed.add_field(name="🔧 Storage", 
                   value=f"**Blocked Users:** {len(blocked_users)}\n**Namelocked Users:** {len(namelocked_users)}\n**Active Giveaways:** {len(active_giveaways)}", 
                   inline=True)
    
    embed.add_field(name="📝 Messages", 
                   value=f"**Sniped Channels:** {len(sniped_messages)}\n**Edited Channels:** {len(edited_messages)}\n**Webhooks:** {len(channel_webhooks)}", 
                   inline=True)
    
    await interaction.response.send_message(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("❌ I don't have the required permissions to execute this command.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found.")
    elif isinstance(error, commands.ChannelNotFound):
        await ctx.send("❌ Channel not found.")
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send("❌ Role not found.")
    else:
        print(f"An error occurred: {error}")

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if interaction.response.is_done():
        return
    
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message("❌ I don't have the required permissions to execute this command.", ephemeral=True)
    else:
        await interaction.response.send_message("❌ An error occurred while processing the command.", ephemeral=True)
        print(f"Slash command error: {error}")

# Start the bot
if __name__ == "__main__":
    run_flask()
    bot.run(os.getenv('DISCORD_TOKEN'))
