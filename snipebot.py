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

# FIXED: Giveaway View with proper message ID handling and requirements
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
        
        if len(embeds) == 1:
            await interaction.response.send_message(embed=embeds[0], ephemeral=True)
        else:
            view = PaginationView(embeds)
            await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)

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

# Background task to check giveaways
@tasks.loop(seconds=30)
async def giveaway_checker():
    current_time = datetime.utcnow()
    ended_giveaways = []
    
    for message_id, giveaway in active_giveaways.items():
        if current_time >= giveaway['end_time']:
            ended_giveaways.append(message_id)
    
    for message_id in ended_giveaways:
        giveaway = active_giveaways[message_id]
        participants = giveaway['participants']
        
        try:
            channel = bot.get_channel(giveaway['channel_id'])
            if channel:
                message = await channel.fetch_message(message_id)
                
                if participants:
                    winner_id = random.choice(participants)
                    winner = bot.get_user(winner_id)
                    
                    if winner:
                        # FIXED: Create winner announcement with reroll button
                        embed = discord.Embed(
                            title="🎉 Giveaway Ended!",
                            description=f"**🎊 Congratulations {winner.mention}!**\n**You won:** {giveaway['prize']}",
                            color=discord.Color.green()
                        )
                        embed.set_footer(text="Giveaway has ended!")
                        
                        # Send winner notification
                        try:
                            await winner.send(f"🎉 **Congratulations!** You won **{giveaway['prize']}** in {channel.guild.name}!")
                        except:
                            pass
                        
                        # Add reroll view
                        reroll_view = RerollView(giveaway)
                        await message.edit(embed=embed, view=reroll_view)
                else:
                    embed = discord.Embed(
                        title="🎉 Giveaway Ended!",
                        description=f"**No participants**\n**Prize:** {giveaway['prize']}",
                        color=discord.Color.red()
                    )
                    await message.edit(embed=embed, view=None)
        except Exception as e:
            logger.error(f"Error in giveaway checker: {e}")
        
        # Remove from active giveaways
        del active_giveaways[message_id]

# Bot events
@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    run_flask()
    giveaway_checker.start()
    
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} slash command(s) globally")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

# FIXED: Message deletion event handler with proper attachment handling and filtration
@bot.event
async def on_message_delete(message):
    """Store deleted messages for snipe command - FIXED for all media types and filtration"""
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []
    
    # Log the deletion event
    logger.info(f"Message deleted in channel {channel_id} by {message.author}: content='{message.content}', attachments={len(message.attachments)}")
    
    # FIXED: Process all media types properly
    media_urls = get_media_url(message.content, message.attachments)
    
    # Log media detection
    if media_urls:
        for media in media_urls:
            logger.info(f"Detected media: {media['type']} - {media['url'][:50]}...")
    
    # Clean content from embedded URLs (but keep attachment info separate)
    cleaned_content = clean_content_from_media(message.content, media_urls)
    
    # FIXED: Determine filtering and link status
    is_filtered = is_offensive_content(message.content) if message.content else False
    has_link = has_links(message.content) if message.content else False
    
    # FIXED: Store message data with complete media information and filtration
    message_data = {
        'content': cleaned_content,
        'original_content': message.content,  # Keep original for spf command
        'filtered_content': filter_content(message.content) if message.content else None,  # Store filtered version
        'author': message.author,
        'created_at': message.created_at,
        'guild_id': message.guild.id if message.guild else None,
        'channel_id': channel_id,
        'message_id': message.id,
        'media_urls': media_urls,  # FIXED: Store all media information
        'is_filtered': is_filtered,
        'has_link': has_link,
        'attachment_count': len(message.attachments),
        'media_types': [media['type'] for media in media_urls] if media_urls else []
    }
    
    # Add to the beginning of the list (most recent first)
    sniped_messages[channel_id].insert(0, message_data)
    
    # Keep only the last MAX_MESSAGES
    if len(sniped_messages[channel_id]) > MAX_MESSAGES:
        sniped_messages[channel_id] = sniped_messages[channel_id][:MAX_MESSAGES]
    
    # Log successful storage
    logger.info(f"Successfully stored deleted message with {len(media_urls) if media_urls else 0} media items")

@bot.event
async def on_message_edit(before, after):
    """Store edited messages for editsnipe command"""
    if before.author.bot or before.content == after.content:
        return
    
    channel_id = before.channel.id
    
    if channel_id not in edited_messages:
        edited_messages[channel_id] = []
    
    edit_data = {
        'before_content': before.content,
        'after_content': after.content,
        'author': before.author,
        'edited_at': datetime.utcnow(),
        'guild_id': before.guild.id if before.guild else None,
        'channel_id': channel_id
    }
    
    edited_messages[channel_id].insert(0, edit_data)
    
    if len(edited_messages[channel_id]) > MAX_MESSAGES:
        edited_messages[channel_id] = edited_messages[channel_id][:MAX_MESSAGES]

@bot.event
async def on_message(message):
    """Count user messages for giveaway requirements"""
    if message.author.bot:
        return
    
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    await bot.process_commands(message)

# FIXED: Enhanced snipe command with clean design and user name
@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe_command(ctx, *, args=None):
    """Show deleted message by number - FIXED with clean design and user filtering"""
    channel = ctx.channel
    page = 1
    
    # Parse arguments
    if args:
        parts = args.split()
        if len(parts) == 1:
            # Could be either channel or page number
            if parts[0].isdigit():
                page = int(parts[0])
            else:
                # Try to parse as channel
                try:
                    channel_id = int(parts[0].strip('<>#'))
                    channel = bot.get_channel(channel_id)
                    if not channel:
                        await ctx.send("❌ Channel not found")
                        return
                except:
                    await ctx.send("❌ Invalid channel or page number")
                    return
        elif len(parts) == 2:
            # Channel and page
            try:
                channel_id = int(parts[0].strip('<>#'))
                channel = bot.get_channel(channel_id)
                page = int(parts[1])
                if not channel:
                    await ctx.send("❌ Channel not found")
                    return
            except:
                await ctx.send("❌ Invalid channel or page number")
                return
    
    if page < 1 or page > MAX_MESSAGES:
        await ctx.send(f"❌ Please provide a page number between 1 and {MAX_MESSAGES}")
        return
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel")
        return
    
    if page > len(sniped_messages[channel_id]):
        await ctx.send(f"❌ Only {len(sniped_messages[channel_id])} deleted messages available")
        return
    
    # Get the message (index is page - 1)
    message_data = sniped_messages[channel_id][page - 1]
    
    # FIXED: Create clean embed with user name
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.red(),
        timestamp=message_data['created_at']
    )
    
    # FIXED: Add clean description with user name
    author = message_data['author']
    description_parts = []
    
    # Add content if exists (use filtered content if message was filtered for normal snipe)
    if message_data['content']:
        if message_data['is_filtered']:
            # Show filtered version for normal snipe
            content_to_show = message_data['filtered_content'] or message_data['content']
        else:
            content_to_show = message_data['content']
        description_parts.append(content_to_show)
    
    # Combine description
    if description_parts:
        embed.description = " - ".join(description_parts)
    
    # FIXED: Add user information as field
    embed.add_field(
        name="👤 Message Author",
        value=f"{author.mention} ({author.display_name})",
        inline=False
    )
    
    # FIXED: Display media visually if exists
    if message_data['media_urls']:
        primary_media = message_data['media_urls'][0]
        if primary_media['type'] in ['image', 'gif', 'tenor_gif', 'giphy_gif', 'discord_attachment']:
            embed.set_image(url=primary_media['url'])
    
    # Add page info in footer
    total_messages = len(sniped_messages[channel_id])
    embed.set_footer(text=f"Message {page} of {total_messages} | Deleted from #{channel.name}")
    
    await ctx.send(embed=embed)

# FIXED: Enhanced spf command to show only filtered content in original form
@bot.command(name='spf')
@not_blocked()
async def snipe_filtered_command(ctx, channel: Optional[discord.TextChannel] = None, page: int = 1):
    """Show filtered/censored deleted messages only - FIXED to show original unfiltered content"""
    if not channel:
        channel = ctx.channel
    
    if page < 1:
        page = 1
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages:
        await ctx.send("❌ No deleted messages found in this channel")
        return
    
    # FIXED: Filter only messages that contain offensive content
    filtered_messages = [msg for msg in sniped_messages[channel_id] if msg['is_filtered']]
    
    if not filtered_messages:
        await ctx.send("❌ No filtered messages found in this channel")
        return
    
    total_pages = math.ceil(len(filtered_messages) / MESSAGES_PER_PAGE)
    
    if page > total_pages:
        await ctx.send(f"❌ Page {page} doesn't exist. Max page: {total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(filtered_messages))
    page_messages = filtered_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🚫 Filtered Messages - #{channel.name}",
        color=discord.Color.red()
    )
    
    for i, msg_data in enumerate(page_messages, start=start_idx + 1):
        author = msg_data['author']
        # FIXED: Show original unfiltered content for spf
        content = msg_data['original_content'] or "No text content"
        content = content[:100] + "..." if len(content) > 100 else content
        
        embed.add_field(
            name=f"{i}. {author.display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} • {len(filtered_messages)} filtered messages")
    
    # Add pagination if needed
    if total_pages > 1:
        view = PaginationView([embed])  # Would need to create all embeds for full pagination
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send(embed=embed)

# FIXED: Enhanced sp command with pagination
@bot.command(name='sp')
@not_blocked()
async def snipe_pages_command(ctx, channel: Optional[discord.TextChannel] = None, page: int = 1):
    """List normal deleted messages with pagination"""
    if not channel:
        channel = ctx.channel
    
    if page < 1:
        page = 1
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages:
        await ctx.send("❌ No deleted messages found in this channel")
        return
    
    # Filter normal messages (non-filtered, non-link)
    normal_messages = [msg for msg in sniped_messages[channel_id] if not msg['is_filtered'] and not msg['has_link']]
    
    if not normal_messages:
        await ctx.send("❌ No normal messages found in this channel")
        return
    
    total_pages = math.ceil(len(normal_messages) / MESSAGES_PER_PAGE)
    
    if page > total_pages:
        await ctx.send(f"❌ Page {page} doesn't exist. Max page: {total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(normal_messages))
    page_messages = normal_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"📝 Normal Messages - #{channel.name}",
        color=discord.Color.blue()
    )
    
    for i, msg_data in enumerate(page_messages, start=start_idx + 1):
        author = msg_data['author']
        content = msg_data['content'] or "No text content"
        content = content[:100] + "..." if len(content) > 100 else content
        
        embed.add_field(
            name=f"{i}. {author.display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} • {len(normal_messages)} normal messages")
    
    # FIXED: Add pagination with arrow emojis
    if total_pages > 1:
        embeds = []
        for p in range(1, total_pages + 1):
            start = (p - 1) * MESSAGES_PER_PAGE
            end = min(start + MESSAGES_PER_PAGE, len(normal_messages))
            messages = normal_messages[start:end]
            
            page_embed = discord.Embed(
                title=f"📝 Normal Messages - #{channel.name}",
                color=discord.Color.blue()
            )
            
            for i, msg_data in enumerate(messages, start=start + 1):
                author = msg_data['author']
                content = msg_data['content'] or "No text content"
                content = content[:100] + "..." if len(content) > 100 else content
                
                page_embed.add_field(
                    name=f"{i}. {author.display_name}",
                    value=content,
                    inline=False
                )
            
            page_embed.set_footer(text=f"Page {p} of {total_pages} • {len(normal_messages)} normal messages")
            embeds.append(page_embed)
        
        view = PaginationView(embeds)
        view.current_page = page - 1
        view.update_buttons()
        await ctx.send(embed=embeds[page - 1], view=view)
    else:
        await ctx.send(embed=embed)

# FIXED: Enhanced spl command with pagination
@bot.command(name='spl')
@not_blocked()
async def snipe_links_command(ctx, channel: Optional[discord.TextChannel] = None, page: int = 1):
    """Show deleted links only with pagination"""
    if not channel:
        channel = ctx.channel
    
    if page < 1:
        page = 1
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages:
        await ctx.send("❌ No deleted messages found in this channel")
        return
    
    # Filter messages with links
    link_messages = [msg for msg in sniped_messages[channel_id] if msg['has_link']]
    
    if not link_messages:
        await ctx.send("❌ No messages with links found in this channel")
        return
    
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    
    if page > total_pages:
        await ctx.send(f"❌ Page {page} doesn't exist. Max page: {total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(link_messages))
    page_messages = link_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔗 Link Messages - #{channel.name}",
        color=discord.Color.green()
    )
    
    for i, msg_data in enumerate(page_messages, start=start_idx + 1):
        author = msg_data['author']
        content = msg_data['original_content'] or "No text content"
        content = content[:100] + "..." if len(content) > 100 else content
        
        embed.add_field(
            name=f"{i}. {author.display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} • {len(link_messages)} link messages")
    
    # FIXED: Add pagination with arrow emojis
    if total_pages > 1:
        embeds = []
        for p in range(1, total_pages + 1):
            start = (p - 1) * MESSAGES_PER_PAGE
            end = min(start + MESSAGES_PER_PAGE, len(link_messages))
            messages = link_messages[start:end]
            
            page_embed = discord.Embed(
                title=f"🔗 Link Messages - #{channel.name}",
                color=discord.Color.green()
            )
            
            for i, msg_data in enumerate(messages, start=start + 1):
                author = msg_data['author']
                content = msg_data['original_content'] or "No text content"
                content = content[:100] + "..." if len(content) > 100 else content
                
                page_embed.add_field(
                    name=f"{i}. {author.display_name}",
                    value=content,
                    inline=False
                )
            
            page_embed.set_footer(text=f"Page {p} of {total_pages} • {len(link_messages)} link messages")
            embeds.append(page_embed)
        
        view = PaginationView(embeds)
        view.current_page = page - 1
        view.update_buttons()
        await ctx.send(embed=embeds[page - 1], view=view)
    else:
        await ctx.send(embed=embed)

# EditSnipe command
@bot.command(name='editsnipe', aliases=['es'])
@not_blocked()
async def editsnipe_command(ctx):
    """Show last edited message"""
    channel_id = ctx.channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await ctx.send("❌ No edited messages found in this channel")
        return
    
    edit_data = edited_messages[channel_id][0]
    
    embed = discord.Embed(
        title="✏️ Edit Sniped Message",
        color=discord.Color.orange(),
        timestamp=edit_data['edited_at']
    )
    
    author = edit_data['author']
    embed.set_author(
        name=f"{author.display_name} ({author.name})",
        icon_url=author.display_avatar.url
    )
    
    embed.add_field(
        name="📝 Before",
        value=edit_data['before_content'][:1024] if edit_data['before_content'] else "*No content*",
        inline=False
    )
    
    embed.add_field(
        name="✏️ After",
        value=edit_data['after_content'][:1024] if edit_data['after_content'] else "*No content*",
        inline=False
    )
    
    embed.set_footer(text=f"Edited in #{ctx.channel.name}")
    
    await ctx.send(embed=embed)

# FIXED: Enhanced /saywb command with channel parameter and hex code support
@bot.tree.command(name="saywb", description="Send an embed message to a specific channel")
@app_commands.describe(
    channel="Channel to send the message to",
    color="Embed color (hex code like #ff0000 or color name like red)",
    title="Embed title (optional)",
    description="Embed description (optional)"
)
@check_not_blocked()
async def saywb_slash(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    color: str = None,
    title: str = None,
    description: str = None
):
    """Send an embed message to a specific channel - FIXED with channel parameter and hex support"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need Manage Messages permission to use this command.", ephemeral=True)
        return
    
    # FIXED: Validate that at least title or description is provided
    if not title and not description:
        await interaction.response.send_message("❌ You must provide at least a title or description.", ephemeral=True)
        return
    
    # FIXED: Parse color with hex code support
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Create embed
    embed = discord.Embed(color=embed_color)
    
    if title:
        embed.title = title
    
    if description:
        embed.description = description
    
    # Set footer
    embed.set_footer(text=f"Sent by {interaction.user.display_name}")
    
    try:
        await channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Embed sent to {channel.mention}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to send messages in that channel.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# FIXED: Enhanced /create command for reaction roles with title and hex support
@bot.tree.command(name="create", description="Create reaction roles with up to 6 emoji-role pairs")
@app_commands.describe(
    title="Title for the reaction role embed",
    color="Embed color (hex code like #ff0000 or color name like red)",
    emoji1="First emoji", role1="First role",
    emoji2="Second emoji", role2="Second role",
    emoji3="Third emoji", role3="Third role",
    emoji4="Fourth emoji", role4="Fourth role",
    emoji5="Fifth emoji", role5="Fifth role",
    emoji6="Sixth emoji", role6="Sixth role"
)
@check_not_blocked()
async def create_reaction_roles(
    interaction: discord.Interaction,
    title: str,
    emoji1: str, role1: discord.Role,
    color: str = None,
    emoji2: str = None, role2: discord.Role = None,
    emoji3: str = None, role3: discord.Role = None,
    emoji4: str = None, role4: discord.Role = None,
    emoji5: str = None, role5: discord.Role = None,
    emoji6: str = None, role6: discord.Role = None
):
    """Create reaction roles - FIXED with title and hex color support"""
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You need Manage Roles permission to use this command.", ephemeral=True)
        return
    
    # FIXED: Parse color with hex code support
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Build role mappings
    role_mappings = {emoji1: role1.id}
    
    if emoji2 and role2:
        role_mappings[emoji2] = role2.id
    if emoji3 and role3:
        role_mappings[emoji3] = role3.id
    if emoji4 and role4:
        role_mappings[emoji4] = role4.id
    if emoji5 and role5:
        role_mappings[emoji5] = role5.id
    if emoji6 and role6:
        role_mappings[emoji6] = role6.id
    
    # FIXED: Create embed with title design
    embed = discord.Embed(
        title=title,
        color=embed_color
    )
    
    # Add role information
    role_text = []
    for emoji, role_id in role_mappings.items():
        role = interaction.guild.get_role(role_id)
        if role:
            role_text.append(f"{emoji} - {role.mention}")
    
    embed.description = "\n".join(role_text)
    embed.set_footer(text="Click the buttons below to get/remove roles")
    
    # FIXED: Create view with reaction buttons
    view = ReactionRoleView(role_mappings)
    
    try:
        await interaction.response.send_message(embed=embed, view=view)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# FIXED: Enhanced /giveaway command with proper view and ending functionality
@bot.tree.command(name="giveaway", description="Create a giveaway")
@app_commands.describe(
    prize="What the winner will receive",
    duration="Duration (e.g., 1m, 1h, 1d)",
    winners="Number of winners (default: 1)",
    requirements="Requirements to join (optional)"
)
@check_not_blocked()
async def giveaway_slash(
    interaction: discord.Interaction,
    prize: str,
    duration: str,
    winners: int = 1,
    requirements: str = None
):
    """Create a giveaway - FIXED with proper ending and reroll functionality"""
    if not can_host_giveaway(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to host giveaways.", ephemeral=True)
        return
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        await interaction.response.send_message("❌ Invalid duration format. Use formats like: 1m, 1h, 1d", ephemeral=True)
        return
    
    if duration_seconds < 10:
        await interaction.response.send_message("❌ Minimum giveaway duration is 10 seconds.", ephemeral=True)
        return
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Create giveaway embed
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n**Duration:** {format_duration(duration_seconds)}\n**Winners:** {winners}",
        color=discord.Color.gold()
    )
    
    if requirements:
        embed.add_field(name="📋 Requirements", value=requirements, inline=False)
    
    embed.add_field(name="⏰ Ends", value=f"<t:{int(end_time.timestamp())}:R>", inline=True)
    embed.set_footer(text="Click Join to participate!")
    
    # Send initial response
    await interaction.response.send_message(embed=embed)
    
    # Get the message
    message = await interaction.original_response()
    
    # FIXED: Create giveaway view with Join and List buttons
    view = GiveawayView(message.id)
    
    # Store giveaway data
    giveaway_data = {
        'prize': prize,
        'end_time': end_time,
        'winners': winners,
        'requirements': requirements,
        'participants': [],
        'channel_id': interaction.channel.id,
        'guild_id': interaction.guild.id,
        'host_id': interaction.user.id
    }
    
    active_giveaways[message.id] = giveaway_data
    
    # FIXED: Edit message with view (Join and List buttons)
    await message.edit(embed=embed, view=view)

# Other slash commands and remaining functionality...

# Prefix command equivalents
@bot.command(name='saywb')
@not_blocked()
async def saywb_prefix(ctx, channel: discord.TextChannel = None, color: str = None, *, content: str = None):
    """Send an embed message - prefix version"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ You need Manage Messages permission to use this command.")
        return
    
    if not channel:
        channel = ctx.channel
    
    if not content:
        await ctx.send("❌ You must provide content for the embed.")
        return
    
    # Split content into title and description
    parts = content.split(' | ', 1)
    title = parts[0] if parts else None
    description = parts[1] if len(parts) > 1 else None
    
    if not title and not description:
        await ctx.send("❌ You must provide at least a title or description.")
        return
    
    # Parse color
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Create embed
    embed = discord.Embed(color=embed_color)
    
    if title:
        embed.title = title
    
    if description:
        embed.description = description
    
    embed.set_footer(text=f"Sent by {ctx.author.display_name}")
    
    try:
        await channel.send(embed=embed)
        await ctx.send(f"✅ Embed sent to {channel.mention}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to send messages in that channel.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

# Say command
@bot.command(name='say')
@not_blocked()
async def say_command(ctx, *, message: str):
    """Send a message"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ You need Manage Messages permission to use this command.")
        return
    
    try:
        await ctx.channel.send(message)
        await ctx.message.delete()
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to delete messages or send messages.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="say", description="Send a message")
@app_commands.describe(message="Message to send")
@check_not_blocked()
async def say_slash(interaction: discord.Interaction, message: str):
    """Send a message - slash version"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need Manage Messages permission to use this command.", ephemeral=True)
        return
    
    try:
        await interaction.response.send_message(message)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# Block commands
@bot.command(name='block')
@not_blocked()
async def block_command(ctx, user: discord.User):
    """Block a user from using bot functions"""
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
    await ctx.send(f"✅ {user.mention} has been blocked from using bot functions.")

@bot.tree.command(name="block", description="Block a user from using bot functions")
@app_commands.describe(user="User to block")
@check_not_blocked()
async def block_slash(interaction: discord.Interaction, user: discord.User):
    """Block a user - slash version"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if user.id == BOT_OWNER_ID:
        await interaction.response.send_message("❌ Cannot block the bot owner.", ephemeral=True)
        return
    
    if user.id in blocked_users:
        await interaction.response.send_message(f"❌ {user.mention} is already blocked.", ephemeral=True)
        return
    
    blocked_users.add(user.id)
    await interaction.response.send_message(f"✅ {user.mention} has been blocked from using bot functions.")

@bot.tree.command(name="unblock", description="Unblock a user from using bot functions")
@app_commands.describe(user="User to unblock")
@check_not_blocked()
async def unblock_slash(interaction: discord.Interaction, user: discord.User):
    """Unblock a user - slash version"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if user.id not in blocked_users:
        await interaction.response.send_message(f"❌ {user.mention} is not blocked.", ephemeral=True)
        return
    
    blocked_users.remove(user.id)
    await interaction.response.send_message(f"✅ {user.mention} has been unblocked.")

# Namelock commands
@bot.command(name='namelock', aliases=['nl'])
@not_blocked()
async def namelock_command(ctx, member: discord.Member, *, nickname: str):
    """Lock a user's nickname"""
    if not ctx.author.guild_permissions.manage_nicknames:
        await ctx.send("❌ You need Manage Nicknames permission to use this command.")
        return
    
    if member.id in namelock_immune_users:
        await ctx.send(f"❌ {member.mention} is immune to namelocking.")
        return
    
    if member.top_role >= ctx.author.top_role and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You cannot namelock someone with a higher or equal role.")
        return
    
    try:
        await member.edit(nick=nickname)
        namelocked_users[member.id] = nickname
        await ctx.send(f"✅ {member.mention} has been namelocked to **{nickname}**")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="namelock", description="Lock a user's nickname")
@app_commands.describe(member="Member to namelock", nickname="Nickname to lock them to")
@check_not_blocked()
async def namelock_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    """Lock a user's nickname - slash version"""
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("❌ You need Manage Nicknames permission to use this command.", ephemeral=True)
        return
    
    if member.id in namelock_immune_users:
        await interaction.response.send_message(f"❌ {member.mention} is immune to namelocking.", ephemeral=True)
        return
    
    if member.top_role >= interaction.user.top_role and not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ You cannot namelock someone with a higher or equal role.", ephemeral=True)
        return
    
    try:
        await member.edit(nick=nickname)
        namelocked_users[member.id] = nickname
        await interaction.response.send_message(f"✅ {member.mention} has been namelocked to **{nickname}**")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change this user's nickname.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.command(name='unl')
@not_blocked()
async def unnamelock_command(ctx, member: discord.Member):
    """Unlock a user's nickname"""
    if not ctx.author.guild_permissions.manage_nicknames:
        await ctx.send("❌ You need Manage Nicknames permission to use this command.")
        return
    
    if member.id not in namelocked_users:
        await ctx.send(f"❌ {member.mention} is not namelocked.")
        return
    
    try:
        del namelocked_users[member.id]
        await ctx.send(f"✅ {member.mention} has been un-namelocked.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="unl", description="Unlock a user's nickname")
@app_commands.describe(member="Member to unlock")
@check_not_blocked()
async def unnamelock_slash(interaction: discord.Interaction, member: discord.Member):
    """Unlock a user's nickname - slash version"""
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("❌ You need Manage Nicknames permission to use this command.", ephemeral=True)
        return
    
    if member.id not in namelocked_users:
        await interaction.response.send_message(f"❌ {member.mention} is not namelocked.", ephemeral=True)
        return
    
    try:
        del namelocked_users[member.id]
        await interaction.response.send_message(f"✅ {member.mention} has been un-namelocked.")
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# Rename command
@bot.command(name='rename', aliases=['re'])
@not_blocked()
async def rename_command(ctx, member: discord.Member, *, nickname: str):
    """Change a user's nickname"""
    if not ctx.author.guild_permissions.manage_nicknames:
        await ctx.send("❌ You need Manage Nicknames permission to use this command.")
        return
    
    if member.top_role >= ctx.author.top_role and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You cannot rename someone with a higher or equal role.")
        return
    
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname)
        await ctx.send(f"✅ Changed {member.mention}'s nickname from **{old_nick}** to **{nickname}**")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="rename", description="Change a user's nickname")
@app_commands.describe(member="Member to rename", nickname="New nickname")
@check_not_blocked()
async def rename_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    """Change a user's nickname - slash version"""
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("❌ You need Manage Nicknames permission to use this command.", ephemeral=True)
        return
    
    if member.top_role >= interaction.user.top_role and not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ You cannot rename someone with a higher or equal role.", ephemeral=True)
        return
    
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname)
        await interaction.response.send_message(f"✅ Changed {member.mention}'s nickname from **{old_nick}** to **{nickname}**")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change this user's nickname.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# Namelock immune commands
@bot.command(name='namelockimmune', aliases=['nli'])
@not_blocked()
async def namelock_immune_command(ctx, member: discord.Member):
    """Make a user immune to namelocking"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    if member.id in namelock_immune_users:
        namelock_immune_users.remove(member.id)
        await ctx.send(f"✅ {member.mention} is no longer immune to namelocking.")
    else:
        namelock_immune_users.add(member.id)
        await ctx.send(f"✅ {member.mention} is now immune to namelocking.")

@bot.tree.command(name="namelockimmune", description="Toggle namelock immunity for a user")
@app_commands.describe(member="Member to toggle immunity for")
@check_not_blocked()
async def namelock_immune_slash(interaction: discord.Interaction, member: discord.Member):
    """Toggle namelock immunity - slash version"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if member.id in namelock_immune_users:
        namelock_immune_users.remove(member.id)
        await interaction.response.send_message(f"✅ {member.mention} is no longer immune to namelocking.")
    else:
        namelock_immune_users.add(member.id)
        await interaction.response.send_message(f"✅ {member.mention} is now immune to namelocking.")

# Role command
@bot.command(name='role')
@not_blocked()
async def role_command(ctx, member: discord.Member, role: discord.Role):
    """Add or remove a role from a member"""
    if not ctx.author.guild_permissions.manage_roles:
        await ctx.send("❌ You need Manage Roles permission to use this command.")
        return
    
    if role >= ctx.author.top_role and not is_bot_owner(ctx.author.id):
        await ctx.send("❌ You cannot manage a role higher than or equal to your highest role.")
        return
    
    try:
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"✅ Removed role **{role.name}** from {member.mention}")
        else:
            await member.add_roles(role)
            await ctx.send(f"✅ Added role **{role.name}** to {member.mention}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage this role.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="role", description="Add or remove a role from a member")
@app_commands.describe(member="Member to modify", role="Role to add/remove")
@check_not_blocked()
async def role_slash(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    """Add or remove a role - slash version"""
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You need Manage Roles permission to use this command.", ephemeral=True)
        return
    
    if role >= interaction.user.top_role and not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ You cannot manage a role higher than or equal to your highest role.", ephemeral=True)
        return
    
    try:
        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(f"✅ Removed role **{role.name}** from {member.mention}")
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f"✅ Added role **{role.name}** to {member.mention}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage this role.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# Mess command (global DM)
@bot.command(name='mess')
@not_blocked()
async def mess_command(ctx, user: discord.User, *, message: str):
    """Send a DM to a user globally"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    try:
        await user.send(f"**Message from {ctx.author}:**\n{message}")
        await ctx.send(f"✅ Message sent to {user}")
    except discord.Forbidden:
        await ctx.send(f"❌ Could not send message to {user} (DMs disabled or blocked)")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="mess", description="Send a DM to a user globally")
@app_commands.describe(user="User to message", message="Message to send")
@check_not_blocked()
async def mess_slash(interaction: discord.Interaction, user: discord.User, message: str):
    """Send a DM globally - slash version"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    try:
        await user.send(f"**Message from {interaction.user}:**\n{message}")
        await interaction.response.send_message(f"✅ Message sent to {user}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Could not send message to {user} (DMs disabled or blocked)", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# Giveaway host role management
@bot.tree.command(name="giveaway_host", description="Set roles that can host giveaways")
@app_commands.describe(role="Role to add/remove from giveaway hosts")
@check_not_blocked()
async def giveaway_host_slash(interaction: discord.Interaction, role: discord.Role):
    """Manage giveaway host roles"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = set()
    
    if role.id in giveaway_host_roles[guild_id]:
        giveaway_host_roles[guild_id].remove(role.id)
        await interaction.response.send_message(f"✅ Removed **{role.name}** from giveaway host roles.")
    else:
        giveaway_host_roles[guild_id].add(role.id)
        await interaction.response.send_message(f"✅ Added **{role.name}** to giveaway host roles.")

# Reroll giveaway command
@bot.command(name='gw')
@not_blocked()
async def giveaway_reroll_command(ctx, message_id: int):
    """Reroll a giveaway winner"""
    if not can_host_giveaway(ctx.author):
        await ctx.send("❌ You don't have permission to reroll giveaways.")
        return
    
    try:
        message = await ctx.channel.fetch_message(message_id)
        
        # This would need to check if it's a valid giveaway message
        # For now, just send a basic response
        await ctx.send("🔄 Giveaway reroll functionality - use the reroll button on ended giveaways.")
        
    except discord.NotFound:
        await ctx.send("❌ Message not found.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.tree.command(name="gw", description="Reroll a giveaway winner")
@app_commands.describe(message_id="ID of the giveaway message to reroll")
@check_not_blocked()
async def giveaway_reroll_slash(interaction: discord.Interaction, message_id: str):
    """Reroll a giveaway - slash version"""
    if not can_host_giveaway(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to reroll giveaways.", ephemeral=True)
        return
    
    try:
        msg_id = int(message_id)
        message = await interaction.channel.fetch_message(msg_id)
        
        await interaction.response.send_message("🔄 Giveaway reroll functionality - use the reroll button on ended giveaways.", ephemeral=True)
        
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ Message not found.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# Ping command
@bot.tree.command(name="ping", description="Check bot latency")
@check_not_blocked()
async def ping_slash(interaction: discord.Interaction):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: **{latency}ms**")

# Prefix command
@bot.tree.command(name="prefix", description="Change server prefix")
@app_commands.describe(new_prefix="New prefix for the server")
@check_not_blocked()
async def prefix_slash(interaction: discord.Interaction, new_prefix: str):
    """Change server prefix"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need Administrator permission to change the prefix.", ephemeral=True)
        return
    
    if len(new_prefix) > 5:
        await interaction.response.send_message("❌ Prefix cannot be longer than 5 characters.", ephemeral=True)
        return
    
    custom_prefixes[interaction.guild.id] = new_prefix
    await interaction.response.send_message(f"✅ Server prefix changed to `{new_prefix}`")

# Help command
@bot.command(name='help')
@not_blocked()
async def help_command(ctx):
    """Show help information"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

@bot.tree.command(name="help", description="Show help information")
@check_not_blocked()
async def help_slash(interaction: discord.Interaction):
    """Show help information - slash version"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await interaction.response.send_message(embed=embed, view=view)

# Manage command
@bot.command(name='manage')
@not_blocked()
async def manage_command(ctx):
    """Bot management panel"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    uptime = time.time() - BOT_START_TIME
    
    embed = discord.Embed(
        title="🔧 Bot Management Panel",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📊 Statistics",
        value=f"**Guilds:** {len(bot.guilds)}\n**Users:** {len(bot.users)}\n**Uptime:** {format_uptime(uptime)}",
        inline=True
    )
    
    embed.add_field(
        name="🚫 Blocked Users",
        value=f"**Count:** {len(blocked_users)}",
        inline=True
    )
    
    embed.add_field(
        name="🎉 Active Giveaways",
        value=f"**Count:** {len(active_giveaways)}",
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.tree.command(name="manage", description="Bot management panel")
@check_not_blocked()
async def manage_slash(interaction: discord.Interaction):
    """Bot management panel - slash version"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    uptime = time.time() - BOT_START_TIME
    
    embed = discord.Embed(
        title="🔧 Bot Management Panel",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📊 Statistics",
        value=f"**Guilds:** {len(bot.guilds)}\n**Users:** {len(bot.users)}\n**Uptime:** {format_uptime(uptime)}",
        inline=True
    )
    
    embed.add_field(
        name="🚫 Blocked Users",
        value=f"**Count:** {len(blocked_users)}",
        inline=True
    )
    
    embed.add_field(
        name="🎉 Active Giveaways",
        value=f"**Count:** {len(active_giveaways)}",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Event handler for namelock enforcement
@bot.event
async def on_member_update(before, after):
    """Enforce namelocks"""
    if before.nick != after.nick and after.id in namelocked_users:
        locked_nickname = namelocked_users[after.id]
        if after.nick != locked_nickname:
            try:
                await after.edit(nick=locked_nickname)
            except:
                pass

# Slash command for snipe
@bot.tree.command(name="snipe", description="Show deleted message by number")
@app_commands.describe(number="Message number to show (1-100)")
@check_not_blocked()
async def snipe_slash(interaction: discord.Interaction, number: int = 1):
    """Show deleted message - slash version"""
    if number < 1 or number > MAX_MESSAGES:
        await interaction.response.send_message(f"❌ Please provide a number between 1 and {MAX_MESSAGES}", ephemeral=True)
        return
    
    channel_id = interaction.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("❌ No deleted messages found in this channel", ephemeral=True)
        return
    
    if number > len(sniped_messages[channel_id]):
        await interaction.response.send_message(f"❌ Only {len(sniped_messages[channel_id])} deleted messages available", ephemeral=True)
        return
    
    # Get the message (index is number - 1)
    message_data = sniped_messages[channel_id][number - 1]
    
    # Create clean embed with user name
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.red(),
        timestamp=message_data['created_at']
    )
    
    # Add clean description with user name
    author = message_data['author']
    description_parts = []
    
    # Add content if exists (use filtered content if message was filtered)
    if message_data['content']:
        if message_data['is_filtered']:
            content_to_show = message_data['filtered_content'] or message_data['content']
        else:
            content_to_show = message_data['content']
        description_parts.append(content_to_show)
    
    # Combine description
    if description_parts:
        embed.description = " - ".join(description_parts)
    
    # Add user information as field
    embed.add_field(
        name="👤 Message Author",
        value=f"{author.mention} ({author.display_name})",
        inline=False
    )
    
    # Display media visually if exists
    if message_data['media_urls']:
        primary_media = message_data['media_urls'][0]
        if primary_media['type'] in ['image', 'gif', 'tenor_gif', 'giphy_gif', 'discord_attachment']:
            embed.set_image(url=primary_media['url'])
    
    # Add page info in footer
    total_messages = len(sniped_messages[channel_id])
    embed.set_footer(text=f"Message {number} of {total_messages} | Deleted from #{interaction.channel.name}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="editsnipe", description="Show last edited message")
@check_not_blocked()
async def editsnipe_slash(interaction: discord.Interaction):
    """Show last edited message - slash version"""
    channel_id = interaction.channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await interaction.response.send_message("❌ No edited messages found in this channel", ephemeral=True)
        return
    
    edit_data = edited_messages[channel_id][0]
    
    embed = discord.Embed(
        title="✏️ Edit Sniped Message",
        color=discord.Color.orange(),
        timestamp=edit_data['edited_at']
    )
    
    author = edit_data['author']
    embed.set_author(
        name=f"{author.display_name} ({author.name})",
        icon_url=author.display_avatar.url
    )
    
    embed.add_field(
        name="📝 Before",
        value=edit_data['before_content'][:1024] if edit_data['before_content'] else "*No content*",
        inline=False
    )
    
    embed.add_field(
        name="✏️ After",
        value=edit_data['after_content'][:1024] if edit_data['after_content'] else "*No content*",
        inline=False
    )
    
    embed.set_footer(text=f"Edited in #{interaction.channel.name}")
    
    await interaction.response.send_message(embed=embed)

# Test command for media detection
@bot.command(name='mediatest')
@not_blocked()
async def media_test(ctx):
    """Test media detection on recent messages"""
    if not ctx.channel.history:
        await ctx.send("❌ No message history available")
        return
    
    messages = []
    async for message in ctx.channel.history(limit=10):
        if message.author != bot.user:
            messages.append(message)
    
    if not messages:
        await ctx.send("❌ No recent messages found")
        return
    
    embed = discord.Embed(title="🔍 Media Detection Test", color=discord.Color.blue())
    
    for i, message in enumerate(messages[:3], 1):
        media_urls = get_media_url(message.content, message.attachments)
        if media_urls:
            media_types = [media['type'] for media in media_urls]
            embed.add_field(
                name=f"Message {i}",
                value=f"**Types**: {', '.join(media_types)}\n**Count**: {len(media_urls)}",
                inline=True
            )
    
    await ctx.send(embed=embed)

# Run the bot
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
