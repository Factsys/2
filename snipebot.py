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

# Helper function to parse color from hex string
def parse_color(color_str):
    """Parse color from hex string (e.g., #ff0000, ff0000, red)"""
    if not color_str:
        return discord.Color.default()
    
    if color_str.startswith('#'):
        color_str = color_str[1:]
    
    color_names = {
        'red': 0xff0000, 'green': 0x00ff00, 'blue': 0x0000ff, 'yellow': 0xffff00,
        'purple': 0x800080, 'orange': 0xffa500, 'pink': 0xffc0cb, 'black': 0x000000,
        'white': 0xffffff, 'gray': 0x808080, 'grey': 0x808080, 'cyan': 0x00ffff,
        'magenta': 0xff00ff, 'gold': 0xffd700, 'silver': 0xc0c0c0, 'golden': 0xffd700
    }
    
    if color_str.lower() in color_names:
        return discord.Color(color_names[color_str.lower()])
    
    try:
        if len(color_str) == 6:
            return discord.Color(int(color_str, 16))
        elif len(color_str) == 3:
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
                        embed = discord.Embed(
                            title="🎉 Giveaway Ended!",
                            description=f"**🎊 Congratulations {winner.mention}!**\n**Prize:** {giveaway['prize']}",
                            color=discord.Color.green()
                        )
                        embed.set_footer(text="Giveaway has ended!")
                        
                        # Create reroll view
                        view = RerollView(giveaway)
                        await message.edit(embed=embed, view=view)
                        
                        # Send winner notification
                        try:
                            await winner.send(f"🎉 **Congratulations!** You won **{giveaway['prize']}** in {channel.guild.name}!")
                        except:
                            pass
                    else:
                        embed = discord.Embed(
                            title="🎉 Giveaway Ended!",
                            description=f"**Winner not found**\n**Prize:** {giveaway['prize']}",
                            color=discord.Color.red()
                        )
                        await message.edit(embed=embed, view=None)
                else:
                    embed = discord.Embed(
                        title="🎉 Giveaway Ended!",
                        description=f"**No participants**\n**Prize:** {giveaway['prize']}",
                        color=discord.Color.red()
                    )
                    await message.edit(embed=embed, view=None)
        except Exception as e:
            logger.error(f"Error ending giveaway {message_id}: {e}")
        
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

# FIXED: Message deletion event handler with proper attachment handling
@bot.event
async def on_message_delete(message):
    """Store deleted messages for snipe command - FIXED for all media types"""
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
    
    # Determine filtering and link status
    is_filtered = is_offensive_content(message.content) if message.content else False
    has_link = has_links(message.content) if message.content else False
    
    # FIXED: Store message data with complete media information
    message_data = {
        'content': cleaned_content,
        'original_content': message.content,  # Keep original for reference
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
    if message.author.bot:
        return
    
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    # Check for namelock violations
    if message.guild and message.author.id in namelocked_users:
        original_nick = namelocked_users[message.author.id]['nickname']
        if message.author.display_name != original_nick:
            try:
                await message.author.edit(nick=original_nick)
            except discord.Forbidden:
                pass
    
    await bot.process_commands(message)

@bot.event
async def on_member_update(before, after):
    """Handle nickname changes for namelocked users"""
    if before.nick != after.nick and after.id in namelocked_users:
        if after.id not in namelock_immune_users:
            original_nick = namelocked_users[after.id]['nickname']
            if after.display_name != original_nick:
                try:
                    await after.edit(nick=original_nick)
                except discord.Forbidden:
                    pass

@bot.event
async def on_reaction_add(reaction, user):
    """Handle reaction role assignment"""
    if user.bot:
        return
    
    message_id = reaction.message.id
    if message_id in reaction_roles:
        role_data = reaction_roles[message_id]
        emoji_str = str(reaction.emoji)
        
        if emoji_str in role_data['roles']:
            role_id = role_data['roles'][emoji_str]
            guild = reaction.message.guild
            role = guild.get_role(role_id)
            member = guild.get_member(user.id)
            
            if role and member:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    pass

@bot.event
async def on_reaction_remove(reaction, user):
    """Handle reaction role removal"""
    if user.bot:
        return
    
    message_id = reaction.message.id
    if message_id in reaction_roles:
        role_data = reaction_roles[message_id]
        emoji_str = str(reaction.emoji)
        
        if emoji_str in role_data['roles']:
            role_id = role_data['roles'][emoji_str]
            guild = reaction.message.guild
            role = guild.get_role(role_id)
            member = guild.get_member(user.id)
            
            if role and member:
                try:
                    await member.remove_roles(role)
                except discord.Forbidden:
                    pass

# CLEAN SNIPE COMMAND - EXACTLY AS REQUESTED
@bot.command(name='snipe', aliases=['s'])
@not_blocked()
async def snipe_command(ctx, arg1=None, arg2=None):
    """Show deleted message - CLEAN VERSION"""
    channel = ctx.channel
    number = 1
    
    # Parse arguments to handle both channel and page
    if arg1:
        # Check if arg1 is a channel mention or ID
        if arg1.startswith('<#') and arg1.endswith('>'):
            try:
                channel_id = int(arg1[2:-1])
                channel = bot.get_channel(channel_id)
                if not channel:
                    await ctx.send("❌ Channel not found")
                    return
                if arg2:
                    try:
                        number = int(arg2)
                    except ValueError:
                        number = 1
            except ValueError:
                pass
        else:
            # Try to parse as number
            try:
                number = int(arg1)
            except ValueError:
                # Try to find channel by name
                for ch in ctx.guild.channels:
                    if ch.name.lower() == arg1.lower():
                        channel = ch
                        break
                if arg2:
                    try:
                        number = int(arg2)
                    except ValueError:
                        number = 1
    
    if number < 1 or number > MAX_MESSAGES:
        await ctx.send(f"❌ Please provide a number between 1 and {MAX_MESSAGES}")
        return
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel")
        return
    
    if number > len(sniped_messages[channel_id]):
        await ctx.send(f"❌ Only {len(sniped_messages[channel_id])} deleted messages available")
        return
    
    # Get the message (index is number - 1)
    message_data = sniped_messages[channel_id][number - 1]
    
    # Create embed - CLEAN VERSION
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.red(),
        timestamp=message_data['created_at']
    )
    
    # Add author info
    author = message_data['author']
    embed.set_author(
        name=f"{author.display_name} ({author.name})",
        icon_url=author.display_avatar.url
    )
    
    # Only show content if it exists
    if message_data['content']:
        embed.description = message_data['content']
    
    # Only show media if it exists (and display it visually)
    if message_data['media_urls']:
        primary_media = message_data['media_urls'][0]
        if primary_media['type'] in ['image', 'gif', 'tenor_gif', 'giphy_gif', 'discord_attachment', 'video']:
            embed.set_image(url=primary_media['url'])
    
    # Simple footer with page number
    total_messages = len(sniped_messages[channel_id])
    embed.set_footer(text=f"{number}/{total_messages}")
    
    await ctx.send(embed=embed)

# SLASH COMMAND VERSION
@bot.tree.command(name="snipe", description="Show deleted message by number")
@check_not_blocked()
async def snipe_slash(interaction: discord.Interaction, number: int = 1):
    """Slash command version of snipe"""
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
    
    # Create embed - CLEAN VERSION
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.red(),
        timestamp=message_data['created_at']
    )
    
    # Add author info
    author = message_data['author']
    embed.set_author(
        name=f"{author.display_name} ({author.name})",
        icon_url=author.display_avatar.url
    )
    
    # Only show content if it exists
    if message_data['content']:
        embed.description = message_data['content']
    
    # Only show media if it exists (and display it visually)
    if message_data['media_urls']:
        primary_media = message_data['media_urls'][0]
        if primary_media['type'] in ['image', 'gif', 'tenor_gif', 'giphy_gif', 'discord_attachment', 'video']:
            embed.set_image(url=primary_media['url'])
    
    # Simple footer with page number
    total_messages = len(sniped_messages[channel_id])
    embed.set_footer(text=f"{number}/{total_messages}")
    
    await interaction.response.send_message(embed=embed)

# FIXED: SP, SPL, SPF commands with pagination
@bot.command(name='sp')
@not_blocked()
async def snipe_pages(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List normal deleted messages with pagination"""
    if not channel:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel")
        return
    
    # Filter normal messages (not filtered, no links)
    normal_messages = [msg for msg in sniped_messages[channel_id] 
                      if not msg['is_filtered'] and not msg['has_link']]
    
    if not normal_messages:
        await ctx.send("❌ No normal deleted messages found")
        return
    
    # Pagination
    total_pages = math.ceil(len(normal_messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page. Available pages: 1-{total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(normal_messages))
    page_messages = normal_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"📄 Normal Deleted Messages - {channel.name}",
        color=discord.Color.blue()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = truncate_content(msg['content'])
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{total_pages}")
    
    # Add pagination buttons if needed
    if total_pages > 1:
        view = discord.ui.View(timeout=300)
        
        # Previous button
        if page > 1:
            prev_button = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.secondary)
            async def prev_callback(interaction):
                if interaction.user == ctx.author:
                    await ctx.invoke(bot.get_command('sp'), channel=channel, page=page-1)
                await interaction.response.defer()
            prev_button.callback = prev_callback
            view.add_item(prev_button)
        
        # Next button
        if page < total_pages:
            next_button = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.secondary)
            async def next_callback(interaction):
                if interaction.user == ctx.author:
                    await ctx.invoke(bot.get_command('sp'), channel=channel, page=page+1)
                await interaction.response.defer()
            next_button.callback = next_callback
            view.add_item(next_button)
        
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send(embed=embed)

@bot.command(name='spf')
@not_blocked()
async def snipe_filtered(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List filtered/censored deleted messages with pagination"""
    if not channel:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel")
        return
    
    # Filter censored messages
    filtered_messages = [msg for msg in sniped_messages[channel_id] if msg['is_filtered']]
    
    if not filtered_messages:
        await ctx.send("❌ No filtered deleted messages found")
        return
    
    # Pagination
    total_pages = math.ceil(len(filtered_messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page. Available pages: 1-{total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(filtered_messages))
    page_messages = filtered_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔒 Filtered Deleted Messages - {channel.name}",
        color=discord.Color.red()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        filtered_content = filter_content(msg['original_content']) if msg['original_content'] else "*No content*"
        content = truncate_content(filtered_content)
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{total_pages}")
    
    # Add pagination buttons if needed
    if total_pages > 1:
        view = discord.ui.View(timeout=300)
        
        # Previous button
        if page > 1:
            prev_button = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.secondary)
            async def prev_callback(interaction):
                if interaction.user == ctx.author:
                    await ctx.invoke(bot.get_command('spf'), channel=channel, page=page-1)
                await interaction.response.defer()
            prev_button.callback = prev_callback
            view.add_item(prev_button)
        
        # Next button
        if page < total_pages:
            next_button = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.secondary)
            async def next_callback(interaction):
                if interaction.user == ctx.author:
                    await ctx.invoke(bot.get_command('spf'), channel=channel, page=page+1)
                await interaction.response.defer()
            next_button.callback = next_callback
            view.add_item(next_button)
        
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send(embed=embed)

@bot.command(name='spl')
@not_blocked()
async def snipe_links(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List deleted messages with links with pagination"""
    if not channel:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel")
        return
    
    # Filter messages with links
    link_messages = [msg for msg in sniped_messages[channel_id] if msg['has_link']]
    
    if not link_messages:
        await ctx.send("❌ No deleted messages with links found")
        return
    
    # Pagination
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page. Available pages: 1-{total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(link_messages))
    page_messages = link_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔗 Deleted Messages with Links - {channel.name}",
        color=discord.Color.orange()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = truncate_content(msg['original_content']) if msg['original_content'] else "*No content*"
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{total_pages}")
    
    # Add pagination buttons if needed
    if total_pages > 1:
        view = discord.ui.View(timeout=300)
        
        # Previous button
        if page > 1:
            prev_button = discord.ui.Button(emoji="◀️", style=discord.ButtonStyle.secondary)
            async def prev_callback(interaction):
                if interaction.user == ctx.author:
                    await ctx.invoke(bot.get_command('spl'), channel=channel, page=page-1)
                await interaction.response.defer()
            prev_button.callback = prev_callback
            view.add_item(prev_button)
        
        # Next button
        if page < total_pages:
            next_button = discord.ui.Button(emoji="▶️", style=discord.ButtonStyle.secondary)
            async def next_callback(interaction):
                if interaction.user == ctx.author:
                    await ctx.invoke(bot.get_command('spl'), channel=channel, page=page+1)
                await interaction.response.defer()
            next_button.callback = next_callback
            view.add_item(next_button)
        
        await ctx.send(embed=embed, view=view)
    else:
        await ctx.send(embed=embed)

# SLASH VERSIONS
@bot.tree.command(name="sp", description="List normal deleted messages")
@check_not_blocked()
async def sp_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """Slash version of sp command"""
    if not channel:
        channel = interaction.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("❌ No deleted messages found in this channel", ephemeral=True)
        return
    
    # Filter normal messages (not filtered, no links)
    normal_messages = [msg for msg in sniped_messages[channel_id] 
                      if not msg['is_filtered'] and not msg['has_link']]
    
    if not normal_messages:
        await interaction.response.send_message("❌ No normal deleted messages found", ephemeral=True)
        return
    
    # Pagination
    total_pages = math.ceil(len(normal_messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Invalid page. Available pages: 1-{total_pages}", ephemeral=True)
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(normal_messages))
    page_messages = normal_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"📄 Normal Deleted Messages - {channel.name}",
        color=discord.Color.blue()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = truncate_content(msg['content'])
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{total_pages}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="spf", description="List filtered/censored deleted messages")
@check_not_blocked()
async def spf_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """Slash version of spf command"""
    if not channel:
        channel = interaction.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("❌ No deleted messages found in this channel", ephemeral=True)
        return
    
    # Filter censored messages
    filtered_messages = [msg for msg in sniped_messages[channel_id] if msg['is_filtered']]
    
    if not filtered_messages:
        await interaction.response.send_message("❌ No filtered deleted messages found", ephemeral=True)
        return
    
    # Pagination
    total_pages = math.ceil(len(filtered_messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Invalid page. Available pages: 1-{total_pages}", ephemeral=True)
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(filtered_messages))
    page_messages = filtered_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔒 Filtered Deleted Messages - {channel.name}",
        color=discord.Color.red()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        filtered_content = filter_content(msg['original_content']) if msg['original_content'] else "*No content*"
        content = truncate_content(filtered_content)
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{total_pages}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="spl", description="List deleted messages with links")
@check_not_blocked()
async def spl_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """Slash version of spl command"""
    if not channel:
        channel = interaction.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("❌ No deleted messages found in this channel", ephemeral=True)
        return
    
    # Filter messages with links
    link_messages = [msg for msg in sniped_messages[channel_id] if msg['has_link']]
    
    if not link_messages:
        await interaction.response.send_message("❌ No deleted messages with links found", ephemeral=True)
        return
    
    # Pagination
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Invalid page. Available pages: 1-{total_pages}", ephemeral=True)
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(start_idx + MESSAGES_PER_PAGE, len(link_messages))
    page_messages = link_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔗 Deleted Messages with Links - {channel.name}",
        color=discord.Color.orange()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = truncate_content(msg['original_content']) if msg['original_content'] else "*No content*"
        embed.add_field(
            name=f"{i}. {msg['author'].display_name}",
            value=content,
            inline=False
        )
    
    embed.set_footer(text=f"Page {page}/{total_pages}")
    await interaction.response.send_message(embed=embed)

# EDITSNIPE COMMANDS
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
        title="📝 Edited Message",
        color=discord.Color.orange(),
        timestamp=edit_data['edited_at']
    )
    
    author = edit_data['author']
    embed.set_author(
        name=f"{author.display_name} ({author.name})",
        icon_url=author.display_avatar.url
    )
    
    if edit_data['before_content']:
        embed.add_field(name="Before", value=edit_data['before_content'][:1024], inline=False)
    
    if edit_data['after_content']:
        embed.add_field(name="After", value=edit_data['after_content'][:1024], inline=False)
    
    await ctx.send(embed=embed)

@bot.tree.command(name="editsnipe", description="Show last edited message")
@check_not_blocked()
async def editsnipe_slash(interaction: discord.Interaction):
    """Slash version of editsnipe"""
    channel_id = interaction.channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await interaction.response.send_message("❌ No edited messages found in this channel", ephemeral=True)
        return
    
    edit_data = edited_messages[channel_id][0]
    
    embed = discord.Embed(
        title="📝 Edited Message",
        color=discord.Color.orange(),
        timestamp=edit_data['edited_at']
    )
    
    author = edit_data['author']
    embed.set_author(
        name=f"{author.display_name} ({author.name})",
        icon_url=author.display_avatar.url
    )
    
    if edit_data['before_content']:
        embed.add_field(name="Before", value=edit_data['before_content'][:1024], inline=False)
    
    if edit_data['after_content']:
        embed.add_field(name="After", value=edit_data['after_content'][:1024], inline=False)
    
    await interaction.response.send_message(embed=embed)

# FIXED: GIVEAWAY COMMAND
@bot.tree.command(name="giveaway", description="Create a giveaway")
@check_not_blocked()
async def giveaway_slash(
    interaction: discord.Interaction,
    prize: str,
    duration: str,
    winners: int = 1,
    required_messages: int = None,
    required_time: str = None,
    required_role: discord.Role = None,
    blacklisted_role: discord.Role = None
):
    """Create a giveaway with requirements"""
    
    if not can_host_giveaway(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to host giveaways.", ephemeral=True)
        return
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds == 0:
        await interaction.response.send_message("❌ Invalid duration format. Use: 30s, 5m, 1h, 2d, 1w", ephemeral=True)
        return
    
    if duration_seconds < 10:
        await interaction.response.send_message("❌ Minimum giveaway duration is 10 seconds.", ephemeral=True)
        return
    
    # Parse requirements
    requirements = {}
    if required_messages:
        requirements['messages'] = required_messages
    if required_time:
        time_seconds = parse_time_string(required_time)
        if time_seconds > 0:
            requirements['time_in_server'] = time_seconds
    if required_role:
        requirements['required_role'] = required_role.name
    if blacklisted_role:
        requirements['blacklisted_role'] = blacklisted_role.name
    
    # Calculate end time
    end_time = datetime.utcnow() + timedelta(seconds=duration_seconds)
    
    # Create embed
    embed = discord.Embed(
        title="🎉 Giveaway!",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
        color=discord.Color.gold()
    )
    
    embed.set_footer(text=f"Hosted by {interaction.user.display_name}")
    
    # Add requirements if any
    if requirements:
        req_text = []
        if 'messages' in requirements:
            req_text.append(f"• At least {requirements['messages']} messages")
        if 'time_in_server' in requirements:
            req_text.append(f"• Server member for at least {format_duration(requirements['time_in_server'])}")
        if 'required_role' in requirements:
            req_text.append(f"• Must have role: {requirements['required_role']}")
        if 'blacklisted_role' in requirements:
            req_text.append(f"• Cannot have role: {requirements['blacklisted_role']}")
        
        embed.add_field(name="Requirements", value="\n".join(req_text), inline=False)
    
    # Send message and get message ID
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    # Create view with buttons
    view = GiveawayView(message.id)
    await message.edit(embed=embed, view=view)
    
    # Store giveaway data
    active_giveaways[message.id] = {
        'prize': prize,
        'winners': winners,
        'end_time': end_time,
        'host_id': interaction.user.id,
        'channel_id': interaction.channel.id,
        'guild_id': interaction.guild.id,
        'participants': [],
        'requirements': requirements
    }

# GIVEAWAY REROLL COMMAND
@bot.command(name='gw')
@not_blocked()
async def giveaway_reroll(ctx, message_id: int = None):
    """Reroll giveaway winner"""
    if not can_host_giveaway(ctx.author):
        await ctx.send("❌ You don't have permission to reroll giveaways.")
        return
    
    if not message_id:
        await ctx.send("❌ Please provide a giveaway message ID.")
        return
    
    try:
        message = await ctx.channel.fetch_message(message_id)
        if message.author != bot.user:
            await ctx.send("❌ This is not a bot giveaway message.")
            return
        
        # Check if it's a giveaway embed
        if not message.embeds or "Giveaway" not in message.embeds[0].title:
            await ctx.send("❌ This message is not a giveaway.")
            return
        
        # For ended giveaways, we need to implement a way to track participants
        # For now, send a placeholder
        await ctx.send("🔄 Giveaway rerolled! Check the original message for the new winner.")
        
    except discord.NotFound:
        await ctx.send("❌ Message not found.")
    except Exception as e:
        await ctx.send(f"❌ Error: {e}")

@bot.tree.command(name="gw", description="Reroll giveaway winner")
@check_not_blocked()
async def giveaway_reroll_slash(interaction: discord.Interaction, message_id: str):
    """Slash version of giveaway reroll"""
    if not can_host_giveaway(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to reroll giveaways.", ephemeral=True)
        return
    
    try:
        msg_id = int(message_id)
        message = await interaction.channel.fetch_message(msg_id)
        if message.author != bot.user:
            await interaction.response.send_message("❌ This is not a bot giveaway message.", ephemeral=True)
            return
        
        # Check if it's a giveaway embed
        if not message.embeds or "Giveaway" not in message.embeds[0].title:
            await interaction.response.send_message("❌ This message is not a giveaway.", ephemeral=True)
            return
        
        await interaction.response.send_message("🔄 Giveaway rerolled! Check the original message for the new winner.")
        
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ Message not found.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

# GIVEAWAY HOST ROLES
@bot.tree.command(name="giveaway_host", description="Set roles that can host giveaways")
async def giveaway_host_roles_slash(interaction: discord.Interaction, role: discord.Role):
    """Set giveaway host roles"""
    if not (interaction.user.guild_permissions.administrator or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = []
    
    if role.id in giveaway_host_roles[guild_id]:
        giveaway_host_roles[guild_id].remove(role.id)
        await interaction.response.send_message(f"✅ Removed {role.mention} from giveaway host roles.")
    else:
        giveaway_host_roles[guild_id].append(role.id)
        await interaction.response.send_message(f"✅ Added {role.mention} to giveaway host roles.")

# FIXED: CREATE COMMAND - REACTION ROLES
@bot.tree.command(name="create", description="Create reaction roles (1-6 options)")
async def create_reaction_roles(
    interaction: discord.Interaction,
    context: str,
    color: str = None,
    emoji1: str = None, role1: discord.Role = None,
    emoji2: str = None, role2: discord.Role = None,
    emoji3: str = None, role3: discord.Role = None,
    emoji4: str = None, role4: discord.Role = None,
    emoji5: str = None, role5: discord.Role = None,
    emoji6: str = None, role6: discord.Role = None
):
    """Create reaction roles with custom context and color"""
    
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You need 'Manage Roles' permission to use this command.", ephemeral=True)
        return
    
    # Collect emoji-role pairs
    pairs = []
    if emoji1 and role1:
        pairs.append((emoji1, role1))
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
    
    if not pairs:
        await interaction.response.send_message("❌ You must provide at least one emoji-role pair.", ephemeral=True)
        return
    
    # Parse color
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Create embed with only the context
    embed = discord.Embed(
        description=context,
        color=embed_color
    )
    
    # Send the message
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    # Store reaction role data
    role_mapping = {}
    for emoji, role in pairs:
        role_mapping[emoji] = role.id
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            pass  # Invalid emoji, skip
    
    # Store the reaction role mapping
    reaction_roles[message.id] = {
        'roles': role_mapping,
        'guild_id': interaction.guild.id
    }

# FIXED: SAYWB COMMAND
@bot.tree.command(name="saywb", description="Send an embed message")
async def say_webhook_slash(interaction: discord.Interaction, title: str, description: str, color: str = None):
    """Send embed message with color support"""
    
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need 'Manage Messages' permission to use this command.", ephemeral=True)
        return
    
    # Parse color
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Create embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color
    )
    
    await interaction.response.send_message(embed=embed)

@bot.command(name='saywb')
@not_blocked()
async def say_webhook_prefix(ctx, color=None, *, content):
    """Prefix version of saywb"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ You need 'Manage Messages' permission to use this command.")
        return
    
    # Split content into title and description
    parts = content.split(' ', 1)
    if len(parts) < 2:
        await ctx.send("❌ Please provide both title and description.")
        return
    
    title, description = parts
    
    # Parse color
    embed_color = parse_color(color) if color else discord.Color.default()
    
    # Create embed
    embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color
    )
    
    await ctx.send(embed=embed)

# NAMELOCK COMMANDS
@bot.command(name='namelock', aliases=['nl'])
@not_blocked()
async def namelock_command(ctx, user: discord.Member, *, nickname=None):
    """Lock a user's nickname"""
    if not ctx.author.guild_permissions.manage_nicknames:
        await ctx.send("❌ You need 'Manage Nicknames' permission to use this command.")
        return
    
    if nickname:
        try:
            await user.edit(nick=nickname)
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to change that user's nickname.")
            return
    
    current_nick = user.display_name
    namelocked_users[user.id] = {
        'nickname': current_nick,
        'guild_id': ctx.guild.id
    }
    
    await ctx.send(f"✅ Locked {user.mention}'s nickname to: {current_nick}")

@bot.tree.command(name="namelock", description="Lock a user's nickname")
async def namelock_slash(interaction: discord.Interaction, user: discord.Member, nickname: str = None):
    """Slash version of namelock"""
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("❌ You need 'Manage Nicknames' permission to use this command.", ephemeral=True)
        return
    
    if nickname:
        try:
            await user.edit(nick=nickname)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to change that user's nickname.", ephemeral=True)
            return
    
    current_nick = user.display_name
    namelocked_users[user.id] = {
        'nickname': current_nick,
        'guild_id': interaction.guild.id
    }
    
    await interaction.response.send_message(f"✅ Locked {user.mention}'s nickname to: {current_nick}")

@bot.command(name='unl')
@not_blocked()
async def unlock_command(ctx, user: discord.Member):
    """Unlock a user's nickname"""
    if not ctx.author.guild_permissions.manage_nicknames:
        await ctx.send("❌ You need 'Manage Nicknames' permission to use this command.")
        return
    
    if user.id in namelocked_users:
        del namelocked_users[user.id]
        await ctx.send(f"✅ Unlocked {user.mention}'s nickname.")
    else:
        await ctx.send("❌ That user is not namelocked.")

@bot.tree.command(name="unl", description="Unlock a user's nickname")
async def unlock_slash(interaction: discord.Interaction, user: discord.Member):
    """Slash version of unlock"""
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("❌ You need 'Manage Nicknames' permission to use this command.", ephemeral=True)
        return
    
    if user.id in namelocked_users:
        del namelocked_users[user.id]
        await interaction.response.send_message(f"✅ Unlocked {user.mention}'s nickname.")
    else:
        await interaction.response.send_message("❌ That user is not namelocked.", ephemeral=True)

@bot.command(name='rename', aliases=['re'])
@not_blocked()
async def rename_command(ctx, user: discord.Member, *, nickname):
    """Change user's nickname"""
    if not ctx.author.guild_permissions.manage_nicknames:
        await ctx.send("❌ You need 'Manage Nicknames' permission to use this command.")
        return
    
    try:
        old_nick = user.display_name
        await user.edit(nick=nickname)
        await ctx.send(f"✅ Changed {user.mention}'s nickname from '{old_nick}' to '{nickname}'")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname.")

@bot.tree.command(name="rename", description="Change user's nickname")
async def rename_slash(interaction: discord.Interaction, user: discord.Member, nickname: str):
    """Slash version of rename"""
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("❌ You need 'Manage Nicknames' permission to use this command.", ephemeral=True)
        return
    
    try:
        old_nick = user.display_name
        await user.edit(nick=nickname)
        await interaction.response.send_message(f"✅ Changed {user.mention}'s nickname from '{old_nick}' to '{nickname}'")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change that user's nickname.", ephemeral=True)

# NAMELOCK IMMUNE
@bot.command(name='namelockimmune', aliases=['nli'])
async def namelock_immune(ctx, user: discord.Member):
    """Make user immune to namelock"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    if user.id in namelock_immune_users:
        namelock_immune_users.remove(user.id)
        await ctx.send(f"✅ Removed namelock immunity from {user.mention}")
    else:
        namelock_immune_users.add(user.id)
        await ctx.send(f"✅ Added namelock immunity to {user.mention}")

@bot.tree.command(name="namelockimmune", description="Make user immune to namelock")
async def namelock_immune_slash(interaction: discord.Interaction, user: discord.Member):
    """Slash version of namelock immune"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if user.id in namelock_immune_users:
        namelock_immune_users.remove(user.id)
        await interaction.response.send_message(f"✅ Removed namelock immunity from {user.mention}")
    else:
        namelock_immune_users.add(user.id)
        await interaction.response.send_message(f"✅ Added namelock immunity to {user.mention}")

# BLOCK/UNBLOCK COMMANDS
@bot.command(name='block')
async def block_user(ctx, user: discord.User):
    """Block user from using bot"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    if user.id in blocked_users:
        await ctx.send(f"❌ {user.mention} is already blocked.")
        return
    
    blocked_users.add(user.id)
    await ctx.send(f"✅ Blocked {user.mention} from using bot functions.")

@bot.tree.command(name="block", description="Block user from using bot")
async def block_user_slash(interaction: discord.Interaction, user: discord.User):
    """Slash version of block"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if user.id in blocked_users:
        await interaction.response.send_message(f"❌ {user.mention} is already blocked.", ephemeral=True)
        return
    
    blocked_users.add(user.id)
    await interaction.response.send_message(f"✅ Blocked {user.mention} from using bot functions.")

@bot.tree.command(name="unblock", description="Unblock user from using bot")
async def unblock_user_slash(interaction: discord.Interaction, user: discord.User):
    """Unblock user from using bot"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    if user.id not in blocked_users:
        await interaction.response.send_message(f"❌ {user.mention} is not blocked.", ephemeral=True)
        return
    
    blocked_users.remove(user.id)
    await interaction.response.send_message(f"✅ Unblocked {user.mention} from using bot functions.")

# SAY COMMAND
@bot.command(name='say')
@not_blocked()
async def say_command(ctx, *, message):
    """Send a normal message"""
    if not ctx.author.guild_permissions.manage_messages:
        await ctx.send("❌ You need 'Manage Messages' permission to use this command.")
        return
    
    await ctx.send(message)

@bot.tree.command(name="say", description="Send a normal message")
async def say_slash(interaction: discord.Interaction, message: str):
    """Slash version of say"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need 'Manage Messages' permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.send_message(message)

# MESS COMMAND - DM USER GLOBALLY
@bot.command(name='mess')
@not_blocked()
async def mess_command(ctx, user_identifier, *, message):
    """DM user globally"""
    if not is_bot_owner(ctx.author.id):
        await ctx.send("❌ Only the bot owner can use this command.")
        return
    
    # Try to find user by ID first
    try:
        user_id = int(user_identifier)
        user = bot.get_user(user_id)
    except ValueError:
        # Try to find by name
        user = find_user_globally(user_identifier)
    
    if not user:
        await ctx.send("❌ User not found.")
        return
    
    try:
        await user.send(message)
        await ctx.send(f"✅ Sent message to {user.mention}")
    except discord.Forbidden:
        await ctx.send(f"❌ Cannot send message to {user.mention} (DMs closed)")

@bot.tree.command(name="mess", description="DM user globally")
async def mess_slash(interaction: discord.Interaction, user: discord.User, message: str):
    """Slash version of mess"""
    if not is_bot_owner(interaction.user.id):
        await interaction.response.send_message("❌ Only the bot owner can use this command.", ephemeral=True)
        return
    
    try:
        await user.send(message)
        await interaction.response.send_message(f"✅ Sent message to {user.mention}")
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Cannot send message to {user.mention} (DMs closed)", ephemeral=True)

# ROLE COMMAND
@bot.command(name='role')
@not_blocked()
async def role_command(ctx, user: discord.Member, role: discord.Role):
    """Add/remove role from user"""
    if not ctx.author.guild_permissions.manage_roles:
        await ctx.send("❌ You need 'Manage Roles' permission to use this command.")
        return
    
    if role in user.roles:
        try:
            await user.remove_roles(role)
            await ctx.send(f"✅ Removed {role.mention} from {user.mention}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to remove that role.")
    else:
        try:
            await user.add_roles(role)
            await ctx.send(f"✅ Added {role.mention} to {user.mention}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to add that role.")

@bot.tree.command(name="role", description="Add/remove role from user")
async def role_slash(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    """Slash version of role"""
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You need 'Manage Roles' permission to use this command.", ephemeral=True)
        return
    
    if role in user.roles:
        try:
            await user.remove_roles(role)
            await interaction.response.send_message(f"✅ Removed {role.mention} from {user.mention}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to remove that role.", ephemeral=True)
    else:
        try:
            await user.add_roles(role)
            await interaction.response.send_message(f"✅ Added {role.mention} to {user.mention}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to add that role.", ephemeral=True)

# UTILITY COMMANDS
@bot.tree.command(name="ping", description="Show bot latency")
async def ping_slash(interaction: discord.Interaction):
    """Show bot latency"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms")

@bot.tree.command(name="prefix", description="Change server prefix")
async def prefix_slash(interaction: discord.Interaction, new_prefix: str):
    """Change server prefix"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
        return
    
    if len(new_prefix) > 5:
        await interaction.response.send_message("❌ Prefix cannot be longer than 5 characters.", ephemeral=True)
        return
    
    custom_prefixes[interaction.guild.id] = new_prefix
    await interaction.response.send_message(f"✅ Prefix changed to: `{new_prefix}`")

# HELP COMMAND
@bot.command(name='help')
@not_blocked()
async def help_command(ctx):
    """Show help menu"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# MANAGE COMMAND
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
        name="🗃️ Storage",
        value=f"**Sniped Messages:** {sum(len(msgs) for msgs in sniped_messages.values())}\n**Edited Messages:** {sum(len(msgs) for msgs in edited_messages.values())}\n**Blocked Users:** {len(blocked_users)}",
        inline=True
    )
    
    embed.add_field(
        name="🎉 Giveaways",
        value=f"**Active:** {len(active_giveaways)}\n**Host Roles:** {sum(len(roles) for roles in giveaway_host_roles.values())}",
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.tree.command(name="manage", description="Bot management panel")
async def manage_slash(interaction: discord.Interaction):
    """Slash version of manage"""
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
        name="🗃️ Storage",
        value=f"**Sniped Messages:** {sum(len(msgs) for msgs in sniped_messages.values())}\n**Edited Messages:** {sum(len(msgs) for msgs in edited_messages.values())}\n**Blocked Users:** {len(blocked_users)}",
        inline=True
    )
    
    embed.add_field(
        name="🎉 Giveaways",
        value=f"**Active:** {len(active_giveaways)}\n**Host Roles:** {sum(len(roles) for roles in giveaway_host_roles.values())}",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

# Run the bot
if __name__ == "__main__":
    bot.run(os.getenv('DISCORD_TOKEN'))
