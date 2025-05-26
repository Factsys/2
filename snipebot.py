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

# ENHANCED: Media URL detection with visual support for Tenor and videos
def get_media_url(content, attachments):
    """Get media URL from content or attachments with enhanced detection"""
    if attachments:
        for attachment in attachments:
            return attachment.url
    
    if content:
        tenor_match = re.search(r'https?://(?:www\.)?tenor\.com/view/[^\s]+', content)
        if tenor_match:
            return tenor_match.group(0)
        
        giphy_match = re.search(r'https?://(?:www\.)?giphy\.com/gifs/[^\s]+', content)
        if giphy_match:
            return giphy_match.group(0)
        
        discord_media_match = re.search(r'https?://(?:cdn|media)\.discordapp\.(?:com|net)/[^\s]+\.(gif|png|jpg|jpeg|webp|mp4|mov)[^\s]*', content)
        if discord_media_match:
            return discord_media_match.group(0)
        
        direct_media_match = re.search(r'https?://[^\s]+\.(gif|png|jpg|jpeg|webp|mp4|mov)[^\s]*', content)
        if direct_media_match:
            return direct_media_match.group(0)
        
        youtube_match = re.search(r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[^\s]+', content)
        if youtube_match:
            return youtube_match.group(0)
        
        twitter_match = re.search(r'https?://(?:www\.)?(?:twitter\.com|x\.com)/[^\s]+', content)
        if twitter_match:
            return twitter_match.group(0)
    
    return None

def clean_content_from_media(content, media_url):
    """Remove media URLs from content to avoid duplication"""
    if not content or not media_url:
        return content
    
    cleaned_content = content.replace(media_url, '').strip()
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
                            description=f"**Winner:** {winner.mention}\n**Prize:** {giveaway['prize']}",
                            color=discord.Color.green()
                        )
                        embed.set_footer(text="Giveaway has ended!")
                        
                        view = discord.ui.View(timeout=None)
                        reroll_button = discord.ui.Button(label="Reroll", style=discord.ButtonStyle.primary, emoji="🔄")
                        
                        async def reroll_callback(interaction):
                            if not (is_bot_owner(interaction.user.id) or 
                                    interaction.user.guild_permissions.administrator or 
                                    can_host_giveaway(interaction.user)):
                                await interaction.response.send_message("❌ You don't have permission to reroll giveaways.", ephemeral=True)
                                return
                            
                            if participants:
                                new_winner_id = random.choice(participants)
                                new_winner = bot.get_user(new_winner_id)
                                if new_winner:
                                    new_embed = discord.Embed(
                                        title="🎉 Giveaway Rerolled!",
                                        description=f"**New Winner:** {new_winner.mention}\n**Prize:** {giveaway['prize']}",
                                        color=discord.Color.green()
                                    )
                                    new_embed.set_footer(text=f"Rerolled by {interaction.user.name}")
                                    await interaction.response.edit_message(embed=new_embed, view=view)
                        
                        reroll_button.callback = reroll_callback
                        view.add_item(reroll_button)
                        await message.edit(embed=embed, view=view)
                else:
                    embed = discord.Embed(
                        title="🎉 Giveaway Ended!",
                        description=f"**No participants**\n**Prize:** {giveaway['prize']}",
                        color=discord.Color.red()
                    )
                    await message.edit(embed=embed, view=None)
        except:
            pass
        
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

@bot.event
async def on_message_delete(message):
    """Store deleted messages for snipe command - FIXED for filtering"""
    if message.author.bot:
        return
    
    channel_id = message.channel.id
    
    if channel_id not in sniped_messages:
        sniped_messages[channel_id] = []
    
    # FIXED: Store message with filtering info
    is_filtered = is_offensive_content(message.content) if message.content else False
    has_link = has_links(message.content) if message.content else False
    
    message_data = {
        'content': message.content,
        'author': message.author,
        'created_at': message.created_at,
        'deleted_at': datetime.utcnow(),
        'attachments': [att.url for att in message.attachments] if message.attachments else [],
        'embeds': message.embeds,
        'jump_url': message.jump_url,
        'is_filtered': is_filtered,
        'has_links': has_link
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
    if message.author.bot:
        return
    
    # Increment message count for user
    if message.guild:
        increment_user_message_count(message.guild.id, message.author.id)
    
    # Process namelock for users not immune
    if (message.guild and 
        message.author.id in namelocked_users and 
        message.author.id not in namelock_immune_users):
        
        locked_nickname = namelocked_users[message.author.id]
        
        try:
            member = message.guild.get_member(message.author.id)
            if member and member.display_name != locked_nickname:
                await member.edit(nick=locked_nickname)
        except discord.Forbidden:
            pass
    
    await bot.process_commands(message)

@bot.event
async def on_member_update(before, after):
    """Handle nickname changes for namelocked users"""
    if (after.id in namelocked_users and 
        after.id not in namelock_immune_users and
        before.display_name != after.display_name):
        
        locked_nickname = namelocked_users[after.id]
        
        if after.display_name != locked_nickname:
            try:
                await after.edit(nick=locked_nickname)
            except discord.Forbidden:
                pass

@bot.event
async def on_raw_reaction_add(payload):
    """Handle reaction role additions"""
    if payload.user_id == bot.user.id:
        return
    
    message_id = payload.message_id
    if message_id not in reaction_roles:
        return
    
    emoji_str = str(payload.emoji)
    if emoji_str not in reaction_roles[message_id]:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    member = guild.get_member(payload.user_id)
    if not member:
        return
    
    role_id = reaction_roles[message_id][emoji_str]
    role = guild.get_role(role_id)
    
    if role and role not in member.roles:
        try:
            await member.add_roles(role)
        except discord.Forbidden:
            pass

@bot.event
async def on_raw_reaction_remove(payload):
    """Handle reaction role removals"""
    if payload.user_id == bot.user.id:
        return
    
    message_id = payload.message_id
    if message_id not in reaction_roles:
        return
    
    emoji_str = str(payload.emoji)
    if emoji_str not in reaction_roles[message_id]:
        return
    
    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return
    
    member = guild.get_member(payload.user_id)
    if not member:
        return
    
    role_id = reaction_roles[message_id][emoji_str]
    role = guild.get_role(role_id)
    
    if role and role in member.roles:
        try:
            await member.remove_roles(role)
        except discord.Forbidden:
            pass

# FIXED SNIPE COMMAND - Shows images visually
@bot.command(name="snipe", aliases=["s"])
@not_blocked()
async def snipe_command(ctx, number: int = 1):
    """Show deleted message by number (1-100) - FIXED for images"""
    channel_id = ctx.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send("❌ No deleted messages found in this channel.")
        return
    
    if number < 1 or number > len(sniped_messages[channel_id]):
        await ctx.send(f"❌ Invalid number. Use 1-{len(sniped_messages[channel_id])}")
        return
    
    # Get message (number is 1-indexed, list is 0-indexed)
    message_data = sniped_messages[channel_id][number - 1]
    
    # Create embed
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.blue()
    )
    
    # FIXED: Handle content with filtering
    display_content = None
    if message_data['content']:
        # Filter offensive content if present
        if message_data.get('is_filtered', False):
            display_content = filter_content(message_data['content'])
        else:
            display_content = message_data['content']
        
        # Clean content from media URLs to avoid duplication
        media_url = get_media_url(display_content, message_data['attachments'])
        cleaned_content = clean_content_from_media(display_content, media_url)
        
        if cleaned_content:
            embed.description = cleaned_content
    
    # FIXED: Always show the image/media even if there's no text
    media_url = get_media_url(message_data['content'], message_data['attachments'])
    if media_url:
        # For images, use embed.set_image for visual display
        if any(ext in media_url.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            embed.set_image(url=media_url)
        # For Tenor/other GIFs, show as visual too
        elif 'tenor.com' in media_url or 'giphy.com' in media_url:
            embed.set_image(url=media_url)
        else:
            # For other media, add as field
            embed.add_field(name="Media", value=media_url, inline=False)
    
    # FIXED: If no content and no description set, add placeholder
    if not embed.description and not media_url:
        embed.description = "*Image/Media only message*"
    
    # Add author mention at the end
    embed.add_field(name="Author", value=f"{message_data['author'].mention}", inline=True)
    
    await ctx.send(embed=embed)

# FIXED SP COMMAND - Normal messages only (no filtered, no links only)
@bot.command(name="sp")
@not_blocked()
async def sp_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List normal deleted messages (no filtered/censored, no links-only) with pagination"""
    if channel is None:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send(f"❌ No deleted messages found in {channel.mention}.")
        return
    
    # FIXED: Filter to show only NORMAL messages (not filtered, not link-only)
    normal_messages = []
    for msg in sniped_messages[channel_id]:
        # Only show if NOT filtered and NOT link-only
        if not msg.get('is_filtered', False) and not msg.get('has_links', False):
            normal_messages.append(msg)
    
    if not normal_messages:
        await ctx.send(f"❌ No normal deleted messages found in {channel.mention}.")
        return
    
    # Create paginated list
    total_pages = math.ceil(len(normal_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page. Use 1-{total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(page * MESSAGES_PER_PAGE, len(normal_messages))
    page_messages = normal_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"📜 Normal Deleted Messages - {channel.name}",
        description=f"Showing normal messages (page {page}/{total_pages})",
        color=discord.Color.blue()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = truncate_content(msg['content'])
        author_name = msg['author'].display_name
        embed.add_field(
            name=f"{i}. {author_name}",
            value=f"{content} - {msg['author'].mention}",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} • Use ,s [number] to view full message")
    await ctx.send(embed=embed)

# FIXED SPF COMMAND - Filtered messages only
@bot.command(name="spf", aliases=["spforce"])
@not_blocked()
async def spf_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List filtered/censored deleted messages only with pagination"""
    if channel is None:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send(f"❌ No deleted messages found in {channel.mention}.")
        return
    
    # FIXED: Filter to show only FILTERED messages
    filtered_messages = []
    for msg in sniped_messages[channel_id]:
        if msg.get('is_filtered', False):
            filtered_messages.append(msg)
    
    if not filtered_messages:
        await ctx.send(f"❌ No filtered deleted messages found in {channel.mention}.")
        return
    
    # Create paginated list
    total_pages = math.ceil(len(filtered_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page. Use 1-{total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(page * MESSAGES_PER_PAGE, len(filtered_messages))
    page_messages = filtered_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔒 Filtered Deleted Messages - {channel.name}",
        description=f"Showing filtered/censored messages (page {page}/{total_pages})",
        color=discord.Color.red()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        # Show filtered content with asterisks
        filtered_content = filter_content(msg['content']) if msg['content'] else "*No text content*"
        content = truncate_content(filtered_content)
        author_name = msg['author'].display_name
        embed.add_field(
            name=f"{i}. {author_name}",
            value=f"{content} - {msg['author'].mention}",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} • These messages contained offensive content")
    await ctx.send(embed=embed)

# FIXED SPL COMMAND - Links only
@bot.command(name="spl")
@not_blocked()
async def spl_command(ctx, channel: discord.TextChannel = None, page: int = 1):
    """List deleted messages with links only with pagination"""
    if channel is None:
        channel = ctx.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await ctx.send(f"❌ No deleted messages found in {channel.mention}.")
        return
    
    # FIXED: Filter to show only messages WITH LINKS
    link_messages = []
    for msg in sniped_messages[channel_id]:
        if msg.get('has_links', False):
            link_messages.append(msg)
    
    if not link_messages:
        await ctx.send(f"❌ No deleted messages with links found in {channel.mention}.")
        return
    
    # Create paginated list
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await ctx.send(f"❌ Invalid page. Use 1-{total_pages}")
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(page * MESSAGES_PER_PAGE, len(link_messages))
    page_messages = link_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔗 Deleted Messages with Links - {channel.name}",
        description=f"Showing messages with links (page {page}/{total_pages})",
        color=discord.Color.green()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = truncate_content(msg['content'])
        author_name = msg['author'].display_name
        embed.add_field(
            name=f"{i}. {author_name}",
            value=f"{content} - {msg['author'].mention}",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} • These messages contained links")
    await ctx.send(embed=embed)

# Edit snipe command
@bot.command(name="editsnipe", aliases=["es"])
@not_blocked()
async def editsnipe_command(ctx):
    """Show the last edited message"""
    channel_id = ctx.channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await ctx.send("❌ No edited messages found in this channel.")
        return
    
    edit_data = edited_messages[channel_id][0]
    
    embed = discord.Embed(title="📝 Edit Snipe", color=discord.Color.orange())
    embed.add_field(name="Before", value=edit_data['before_content'] or "*No content*", inline=False)
    embed.add_field(name="After", value=edit_data['after_content'] or "*No content*", inline=False)
    embed.add_field(name="Author", value=f"{edit_data['author'].mention}", inline=True)
    
    await ctx.send(embed=embed)

# Help command
@bot.command(name="help")
@not_blocked()
async def help_command(ctx):
    """Show help with pagination"""
    view = HelpPaginationView()
    embed = view.get_embed()
    await ctx.send(embed=embed, view=view)

# Say command
@bot.command(name="say")
@commands.has_permissions(manage_messages=True)
@not_blocked()
async def say_command(ctx, *, message):
    """Send a message as the bot"""
    await ctx.message.delete()
    await ctx.send(message)

# Say with embed command
@bot.command(name="saywb")
@commands.has_permissions(manage_messages=True)
@not_blocked()
async def saywb_command(ctx, channel: discord.TextChannel, title, description, color="blue"):
    """Send an embed message"""
    embed_color = parse_color(color)
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color
    )
    
    await ctx.message.delete()
    await channel.send(embed=embed)

# Block command
@bot.command(name="block")
@commands.has_permissions(administrator=True)
@not_blocked()
async def block_command(ctx, user: discord.User):
    """Block a user from using bot functions"""
    if is_bot_owner(user.id):
        await ctx.send("❌ Cannot block the bot owner.")
        return
    
    if user.id in blocked_users:
        await ctx.send(f"❌ {user.mention} is already blocked.")
        return
    
    blocked_users.add(user.id)
    await ctx.send(f"✅ {user.mention} has been blocked from using bot functions.")

# Namelock command
@bot.command(name="namelock", aliases=["nl"])
@commands.has_permissions(manage_nicknames=True)
@not_blocked()
async def namelock_command(ctx, member: discord.Member, *, nickname):
    """Lock a user's nickname"""
    if is_bot_owner(member.id):
        await ctx.send("❌ Cannot namelock the bot owner.")
        return
    
    if member.id in namelock_immune_users:
        await ctx.send(f"❌ {member.mention} is immune to namelock.")
        return
    
    try:
        await member.edit(nick=nickname)
        namelocked_users[member.id] = nickname
        await ctx.send(f"✅ {member.mention} has been namelocked to `{nickname}`")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname.")

# Unlock namelock command
@bot.command(name="unl")
@commands.has_permissions(manage_nicknames=True)
@not_blocked()
async def unlock_namelock_command(ctx, member: discord.Member):
    """Unlock a user's nickname"""
    if member.id not in namelocked_users:
        await ctx.send(f"❌ {member.mention} is not namelocked.")
        return
    
    del namelocked_users[member.id]
    await ctx.send(f"✅ {member.mention} has been unlocked from namelock.")

# Namelock immune command
@bot.command(name="namelockimmune", aliases=["nli"])
@commands.has_permissions(administrator=True)
@not_blocked()
async def namelock_immune_command(ctx, member: discord.Member):
    """Make a user immune to namelock"""
    if member.id in namelock_immune_users:
        await ctx.send(f"❌ {member.mention} is already immune to namelock.")
        return
    
    namelock_immune_users.add(member.id)
    
    # Remove from namelocked users if they are currently locked
    if member.id in namelocked_users:
        del namelocked_users[member.id]
    
    await ctx.send(f"✅ {member.mention} is now immune to namelock.")

# Rename command
@bot.command(name="rename", aliases=["re"])
@commands.has_permissions(manage_nicknames=True)
@not_blocked()
async def rename_command(ctx, member: discord.Member, *, nickname):
    """Change a user's nickname"""
    try:
        await member.edit(nick=nickname)
        await ctx.send(f"✅ {member.mention} has been renamed to `{nickname}`")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change that user's nickname.")

# Role command
@bot.command(name="role")
@commands.has_permissions(manage_roles=True)
@not_blocked()
async def role_command(ctx, member: discord.Member, *, role_name):
    """Add or remove a role from a user"""
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    
    if not role:
        await ctx.send(f"❌ Role `{role_name}` not found.")
        return
    
    if role in member.roles:
        try:
            await member.remove_roles(role)
            await ctx.send(f"✅ Removed role `{role.name}` from {member.mention}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage that role.")
    else:
        try:
            await member.add_roles(role)
            await ctx.send(f"✅ Added role `{role.name}` to {member.mention}")
        except discord.Forbidden:
            await ctx.send("❌ I don't have permission to manage that role.")

# Mess command (DM globally)
@bot.command(name="mess")
@commands.has_permissions(administrator=True)
@not_blocked()
async def mess_command(ctx, *, search_term):
    """Send a DM to a user globally"""
    user = find_user_globally(search_term)
    
    if not user:
        await ctx.send(f"❌ Could not find user: `{search_term}`")
        return
    
    # Ask for message to send
    await ctx.send(f"Found {user.mention} ({user.name}). What message do you want to send?")
    
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel
    
    try:
        message = await bot.wait_for('message', check=check, timeout=60.0)
        
        try:
            await user.send(f"**Message from {ctx.author}:**\n{message.content}")
            await ctx.send(f"✅ Message sent to {user.mention}")
        except discord.Forbidden:
            await ctx.send(f"❌ Could not send DM to {user.mention} (DMs disabled)")
    
    except asyncio.TimeoutError:
        await ctx.send("❌ Timed out waiting for message.")

# Giveaway reroll command
@bot.command(name="gw")
@not_blocked()
async def giveaway_reroll_command(ctx, message_id: int):
    """Reroll a giveaway winner"""
    if not (is_bot_owner(ctx.author.id) or 
            ctx.author.guild_permissions.administrator or 
            can_host_giveaway(ctx.author)):
        await ctx.send("❌ You don't have permission to reroll giveaways.")
        return
    
    if message_id not in active_giveaways:
        await ctx.send("❌ Giveaway not found or already ended.")
        return
    
    giveaway = active_giveaways[message_id]
    participants = giveaway['participants']
    
    if not participants:
        await ctx.send("❌ No participants in this giveaway.")
        return
    
    # Pick new winner
    winner_id = random.choice(participants)
    winner = bot.get_user(winner_id)
    
    if winner:
        await ctx.send(f"🎉 **Giveaway Rerolled!**\n**New Winner:** {winner.mention}\n**Prize:** {giveaway['prize']}")
    else:
        await ctx.send("❌ Could not find the selected winner.")

# Create reaction roles command
@bot.command(name="create")
@commands.has_permissions(administrator=True)
@not_blocked()
async def create_reaction_roles_command(ctx, *, args):
    """Create reaction roles (format: emoji:role emoji:role ...)"""
    parts = args.split()
    
    if len(parts) > 12:  # 6 emoji:role pairs maximum
        await ctx.send("❌ Maximum 6 emoji-role pairs allowed.")
        return
    
    if len(parts) % 2 != 0:
        await ctx.send("❌ Invalid format. Use: emoji:role emoji:role ...")
        return
    
    role_mappings = {}
    embed = discord.Embed(
        title="🎭 Reaction Roles",
        description="React with the emojis below to get roles:",
        color=discord.Color.purple()
    )
    
    for i in range(0, len(parts), 2):
        emoji_part = parts[i]
        role_part = parts[i + 1]
        
        # Parse role (remove @ if present)
        role_name = role_part.replace('@', '')
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        
        if not role:
            await ctx.send(f"❌ Role `{role_name}` not found.")
            return
        
        role_mappings[emoji_part] = role.id
        embed.add_field(
            name=f"{emoji_part} {role.name}",
            value="React to get this role",
            inline=True
        )
    
    message = await ctx.send(embed=embed)
    
    # Add reactions
    for emoji in role_mappings.keys():
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await ctx.send(f"❌ Could not add reaction {emoji}")
            return
    
    # Store reaction role mapping
    reaction_roles[message.id] = role_mappings
    await ctx.send("✅ Reaction roles created successfully!")

# Manage command
@bot.command(name="manage")
@commands.has_permissions(administrator=True)
@not_blocked()
async def manage_command(ctx):
    """Bot management panel"""
    embed = discord.Embed(
        title="🔧 FACTSY Management Panel",
        description="Bot statistics and management options",
        color=discord.Color.gold()
    )
    
    # Bot stats
    total_servers = len(bot.guilds)
    total_users = len(set(bot.get_all_members()))
    uptime = format_uptime(time.time() - BOT_START_TIME)
    
    embed.add_field(name="📊 Statistics", 
                   value=f"**Servers:** {total_servers}\n**Users:** {total_users}\n**Uptime:** {uptime}", 
                   inline=True)
    
    # Blocked users count
    blocked_count = len(blocked_users)
    namelocked_count = len(namelocked_users)
    
    embed.add_field(name="🚫 Moderation", 
                   value=f"**Blocked Users:** {blocked_count}\n**Namelocked Users:** {namelocked_count}", 
                   inline=True)
    
    # Message tracking stats
    total_sniped = sum(len(messages) for messages in sniped_messages.values())
    total_edited = sum(len(messages) for messages in edited_messages.values())
    
    embed.add_field(name="📜 Message Tracking", 
                   value=f"**Sniped Messages:** {total_sniped}\n**Edited Messages:** {total_edited}", 
                   inline=True)
    
    embed.set_footer(text="FACTSY Bot Management | Made with ❤ by Werrzzzy")
    
    await ctx.send(embed=embed)

# Slash Commands
@bot.tree.command(name="ping", description="Check bot latency")
@check_not_blocked()
async def ping_slash(interaction: discord.Interaction):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latency: {latency}ms")

@bot.tree.command(name="snipe", description="Show deleted message by number")
@app_commands.describe(number="Message number (1-100)")
@check_not_blocked()
async def snipe_slash(interaction: discord.Interaction, number: int = 1):
    """Show deleted message by number"""
    channel_id = interaction.channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message("❌ No deleted messages found in this channel.", ephemeral=True)
        return
    
    if number < 1 or number > len(sniped_messages[channel_id]):
        await interaction.response.send_message(f"❌ Invalid number. Use 1-{len(sniped_messages[channel_id])}", ephemeral=True)
        return
    
    # Get message (number is 1-indexed, list is 0-indexed)
    message_data = sniped_messages[channel_id][number - 1]
    
    # Create embed
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.blue()
    )
    
    # FIXED: Handle content with filtering
    display_content = None
    if message_data['content']:
        # Filter offensive content if present
        if message_data.get('is_filtered', False):
            display_content = filter_content(message_data['content'])
        else:
            display_content = message_data['content']
        
        # Clean content from media URLs to avoid duplication
        media_url = get_media_url(display_content, message_data['attachments'])
        cleaned_content = clean_content_from_media(display_content, media_url)
        
        if cleaned_content:
            embed.description = cleaned_content
    
    # FIXED: Always show the image/media even if there's no text
    media_url = get_media_url(message_data['content'], message_data['attachments'])
    if media_url:
        # For images, use embed.set_image for visual display
        if any(ext in media_url.lower() for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
            embed.set_image(url=media_url)
        # For Tenor/other GIFs, show as visual too
        elif 'tenor.com' in media_url or 'giphy.com' in media_url:
            embed.set_image(url=media_url)
        else:
            # For other media, add as field
            embed.add_field(name="Media", value=media_url, inline=False)
    
    # FIXED: If no content and no description set, add placeholder
    if not embed.description and not media_url:
        embed.description = "*Image/Media only message*"
    
    # Add author mention at the end
    embed.add_field(name="Author", value=f"{message_data['author'].mention}", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="editsnipe", description="Show the last edited message")
@check_not_blocked()
async def editsnipe_slash(interaction: discord.Interaction):
    """Show the last edited message"""
    channel_id = interaction.channel.id
    
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        await interaction.response.send_message("❌ No edited messages found in this channel.", ephemeral=True)
        return
    
    edit_data = edited_messages[channel_id][0]
    
    embed = discord.Embed(title="📝 Edit Snipe", color=discord.Color.orange())
    embed.add_field(name="Before", value=edit_data['before_content'] or "*No content*", inline=False)
    embed.add_field(name="After", value=edit_data['after_content'] or "*No content*", inline=False)
    embed.add_field(name="Author", value=f"{edit_data['author'].mention}", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sp", description="List normal deleted messages")
@app_commands.describe(
    channel="Channel to check (optional)",
    page="Page number"
)
@check_not_blocked()
async def sp_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """List normal deleted messages"""
    if channel is None:
        channel = interaction.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message(f"❌ No deleted messages found in {channel.mention}.", ephemeral=True)
        return
    
    # Filter to show only NORMAL messages (not filtered, not link-only)
    normal_messages = []
    for msg in sniped_messages[channel_id]:
        if not msg.get('is_filtered', False) and not msg.get('has_links', False):
            normal_messages.append(msg)
    
    if not normal_messages:
        await interaction.response.send_message(f"❌ No normal deleted messages found in {channel.mention}.", ephemeral=True)
        return
    
    # Create paginated list
    total_pages = math.ceil(len(normal_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Invalid page. Use 1-{total_pages}", ephemeral=True)
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(page * MESSAGES_PER_PAGE, len(normal_messages))
    page_messages = normal_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"📜 Normal Deleted Messages - {channel.name}",
        description=f"Showing normal messages (page {page}/{total_pages})",
        color=discord.Color.blue()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = truncate_content(msg['content'])
        author_name = msg['author'].display_name
        embed.add_field(
            name=f"{i}. {author_name}",
            value=f"{content} - {msg['author'].mention}",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} • Use /snipe [number] to view full message")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="spf", description="List filtered/censored deleted messages")
@app_commands.describe(
    channel="Channel to check (optional)",
    page="Page number"
)
@check_not_blocked()
async def spf_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """List filtered/censored deleted messages"""
    if channel is None:
        channel = interaction.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message(f"❌ No deleted messages found in {channel.mention}.", ephemeral=True)
        return
    
    # Filter to show only FILTERED messages
    filtered_messages = []
    for msg in sniped_messages[channel_id]:
        if msg.get('is_filtered', False):
            filtered_messages.append(msg)
    
    if not filtered_messages:
        await interaction.response.send_message(f"❌ No filtered deleted messages found in {channel.mention}.", ephemeral=True)
        return
    
    # Create paginated list
    total_pages = math.ceil(len(filtered_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Invalid page. Use 1-{total_pages}", ephemeral=True)
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(page * MESSAGES_PER_PAGE, len(filtered_messages))
    page_messages = filtered_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔒 Filtered Deleted Messages - {channel.name}",
        description=f"Showing filtered/censored messages (page {page}/{total_pages})",
        color=discord.Color.red()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        # Show filtered content with asterisks
        filtered_content = filter_content(msg['content']) if msg['content'] else "*No text content*"
        content = truncate_content(filtered_content)
        author_name = msg['author'].display_name
        embed.add_field(
            name=f"{i}. {author_name}",
            value=f"{content} - {msg['author'].mention}",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} • These messages contained offensive content")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="spl", description="List deleted messages with links")
@app_commands.describe(
    channel="Channel to check (optional)",
    page="Page number"
)
@check_not_blocked()
async def spl_slash(interaction: discord.Interaction, channel: discord.TextChannel = None, page: int = 1):
    """List deleted messages with links"""
    if channel is None:
        channel = interaction.channel
    
    channel_id = channel.id
    
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        await interaction.response.send_message(f"❌ No deleted messages found in {channel.mention}.", ephemeral=True)
        return
    
    # Filter to show only messages WITH LINKS
    link_messages = []
    for msg in sniped_messages[channel_id]:
        if msg.get('has_links', False):
            link_messages.append(msg)
    
    if not link_messages:
        await interaction.response.send_message(f"❌ No deleted messages with links found in {channel.mention}.", ephemeral=True)
        return
    
    # Create paginated list
    total_pages = math.ceil(len(link_messages) / MESSAGES_PER_PAGE)
    
    if page < 1 or page > total_pages:
        await interaction.response.send_message(f"❌ Invalid page. Use 1-{total_pages}", ephemeral=True)
        return
    
    start_idx = (page - 1) * MESSAGES_PER_PAGE
    end_idx = min(page * MESSAGES_PER_PAGE, len(link_messages))
    page_messages = link_messages[start_idx:end_idx]
    
    embed = discord.Embed(
        title=f"🔗 Deleted Messages with Links - {channel.name}",
        description=f"Showing messages with links (page {page}/{total_pages})",
        color=discord.Color.green()
    )
    
    for i, msg in enumerate(page_messages, start=start_idx + 1):
        content = truncate_content(msg['content'])
        author_name = msg['author'].display_name
        embed.add_field(
            name=f"{i}. {author_name}",
            value=f"{content} - {msg['author'].mention}",
            inline=False
        )
    
    embed.set_footer(text=f"Page {page} of {total_pages} • These messages contained links")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="say", description="Send a message as the bot")
@app_commands.describe(message="The message to send")
@check_not_blocked()
async def say_slash(interaction: discord.Interaction, message: str):
    """Send a message as the bot"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need Manage Messages permission to use this command.", ephemeral=True)
        return
    
    await interaction.response.send_message("✅ Message sent!", ephemeral=True)
    await interaction.followup.send(message)

@bot.tree.command(name="saywb", description="Send an embed message")
@app_commands.describe(
    channel="Channel to send the message to",
    title="Embed title",
    description="Embed description",
    color="Embed color (hex, name, or default)"
)
@check_not_blocked()
async def saywb_slash(interaction: discord.Interaction, channel: discord.TextChannel, title: str, description: str, color: str = "blue"):
    """Send an embed message"""
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ You need Manage Messages permission to use this command.", ephemeral=True)
        return
    
    embed_color = parse_color(color)
    
    embed = discord.Embed(
        title=title,
        description=description,
        color=embed_color
    )
    
    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ Embed sent to {channel.mention}!", ephemeral=True)

# FIXED GIVEAWAY SLASH COMMAND
@bot.tree.command(name="giveaway", description="Create a giveaway with advanced options")
@app_commands.describe(
    prize="The prize for the giveaway",
    duration="Duration (e.g., 1h, 30m, 5d, 60s)",
    winners="Number of winners (default: 1)",
    channel="Channel to host the giveaway (optional)",
    required_messages="Minimum messages required to join",
    time_in_server="Minimum time in server (e.g., 1d, 5h)",
    required_role="Required role name to join",
    blacklisted_role="Blacklisted role name (cannot join)"
)
@check_not_blocked()
async def giveaway_slash(
    interaction: discord.Interaction,
    prize: str,
    duration: str,
    winners: int = 1,
    channel: discord.TextChannel = None,
    required_messages: int = None,
    time_in_server: str = None,
    required_role: str = None,
    blacklisted_role: str = None
):
    """Create an advanced giveaway - FIXED"""
    
    # Check permissions
    if not can_host_giveaway(interaction.user):
        await interaction.response.send_message("❌ You don't have permission to host giveaways.", ephemeral=True)
        return
    
    # FIXED: Acknowledge the interaction immediately
    await interaction.response.defer()
    
    # Parse duration
    duration_seconds = parse_time_string(duration)
    if duration_seconds <= 0:
        await interaction.followup.send("❌ Invalid duration format. Use formats like: 1h, 30m, 5d, 60s")
        return
    
    # Set channel
    if not channel:
        channel = interaction.channel
    
    # Build requirements
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
    
    # Create embed
    embed = discord.Embed(
        title="🎉 Giveaway",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
        color=discord.Color.gold()
    )
    
    if requirements:
        req_text = []
        if 'messages' in requirements:
            req_text.append(f"• {requirements['messages']} messages")
        if 'time_in_server' in requirements:
            req_text.append(f"• {format_duration(requirements['time_in_server'])} in server")
        if 'required_role' in requirements:
            req_text.append(f"• Role: {requirements['required_role']}")
        if 'blacklisted_role' in requirements:
            req_text.append(f"• Cannot have role: {requirements['blacklisted_role']}")
        
        embed.add_field(name="Requirements", value="\n".join(req_text), inline=False)
    
    embed.set_footer(text=f"Hosted by {interaction.user.name}")
    
    # FIXED: Send message and get the message object
    message = await channel.send(embed=embed)
    
    # FIXED: Create view with the actual message ID
    view = GiveawayView(message.id)
    await message.edit(embed=embed, view=view)
    
    # Store giveaway data
    active_giveaways[message.id] = {
        'prize': prize,
        'winners': winners,
        'end_time': end_time,
        'channel_id': channel.id,
        'host_id': interaction.user.id,
        'participants': [],
        'requirements': requirements
    }
    
    await interaction.followup.send(f"✅ Giveaway created in {channel.mention}!")

# NEW: Giveaway host role command
@bot.tree.command(name="giveaway_host", description="Set roles that can host giveaways")
@app_commands.describe(role="Role to give giveaway hosting permissions")
@check_not_blocked()
async def giveaway_host_slash(interaction: discord.Interaction, role: discord.Role):
    """Set giveaway host roles"""
    if not (interaction.user.guild_permissions.administrator or is_bot_owner(interaction.user.id)):
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    guild_id = interaction.guild.id
    
    if guild_id not in giveaway_host_roles:
        giveaway_host_roles[guild_id] = []
    
    if role.id in giveaway_host_roles[guild_id]:
        # Remove role
        giveaway_host_roles[guild_id].remove(role.id)
        await interaction.response.send_message(f"✅ Removed {role.mention} from giveaway host roles.", ephemeral=True)
    else:
        # Add role
        giveaway_host_roles[guild_id].append(role.id)
        await interaction.response.send_message(f"✅ Added {role.mention} to giveaway host roles.", ephemeral=True)

@bot.tree.command(name="gw", description="Reroll a giveaway winner")
@app_commands.describe(message_id="Message ID of the giveaway")
@check_not_blocked()
async def gw_slash(interaction: discord.Interaction, message_id: str):
    """Reroll a giveaway winner"""
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
    
    # Pick new winner
    winner_id = random.choice(participants)
    winner = bot.get_user(winner_id)
    
    if winner:
        await interaction.response.send_message(f"🎉 **Giveaway Rerolled!**\n**New Winner:** {winner.mention}\n**Prize:** {giveaway['prize']}")
    else:
        await interaction.response.send_message("❌ Could not find the selected winner.", ephemeral=True)

@bot.tree.command(name="block", description="Block a user from using bot functions")
@app_commands.describe(user="User to block")
@check_not_blocked()
async def block_slash(interaction: discord.Interaction, user: discord.User):
    """Block a user from using bot functions"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    if is_bot_owner(user.id):
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
    """Unblock a user from using bot functions"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    if user.id not in blocked_users:
        await interaction.response.send_message(f"❌ {user.mention} is not blocked.", ephemeral=True)
        return
    
    blocked_users.remove(user.id)
    await interaction.response.send_message(f"✅ {user.mention} has been unblocked.")

@bot.tree.command(name="namelock", description="Lock a user's nickname")
@app_commands.describe(
    member="Member to namelock",
    nickname="Nickname to lock them to"
)
@check_not_blocked()
async def namelock_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    """Lock a user's nickname"""
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("❌ You need Manage Nicknames permission to use this command.", ephemeral=True)
        return
    
    if is_bot_owner(member.id):
        await interaction.response.send_message("❌ Cannot namelock the bot owner.", ephemeral=True)
        return
    
    if member.id in namelock_immune_users:
        await interaction.response.send_message(f"❌ {member.mention} is immune to namelock.", ephemeral=True)
        return
    
    try:
        await member.edit(nick=nickname)
        namelocked_users[member.id] = nickname
        await interaction.response.send_message(f"✅ {member.mention} has been namelocked to `{nickname}`")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change that user's nickname.", ephemeral=True)

@bot.tree.command(name="unl", description="Unlock a user's nickname")
@app_commands.describe(member="Member to unlock")
@check_not_blocked()
async def unl_slash(interaction: discord.Interaction, member: discord.Member):
    """Unlock a user's nickname"""
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("❌ You need Manage Nicknames permission to use this command.", ephemeral=True)
        return
    
    if member.id not in namelocked_users:
        await interaction.response.send_message(f"❌ {member.mention} is not namelocked.", ephemeral=True)
        return
    
    del namelocked_users[member.id]
    await interaction.response.send_message(f"✅ {member.mention} has been unlocked from namelock.")

@bot.tree.command(name="namelockimmune", description="Make a user immune to namelock")
@app_commands.describe(member="Member to make immune")
@check_not_blocked()
async def namelockimmune_slash(interaction: discord.Interaction, member: discord.Member):
    """Make a user immune to namelock"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    if member.id in namelock_immune_users:
        await interaction.response.send_message(f"❌ {member.mention} is already immune to namelock.", ephemeral=True)
        return
    
    namelock_immune_users.add(member.id)
    
    # Remove from namelocked users if they are currently locked
    if member.id in namelocked_users:
        del namelocked_users[member.id]
    
    await interaction.response.send_message(f"✅ {member.mention} is now immune to namelock.")

@bot.tree.command(name="rename", description="Change a user's nickname")
@app_commands.describe(
    member="Member to rename",
    nickname="New nickname"
)
@check_not_blocked()
async def rename_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    """Change a user's nickname"""
    if not interaction.user.guild_permissions.manage_nicknames:
        await interaction.response.send_message("❌ You need Manage Nicknames permission to use this command.", ephemeral=True)
        return
    
    try:
        await member.edit(nick=nickname)
        await interaction.response.send_message(f"✅ {member.mention} has been renamed to `{nickname}`")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change that user's nickname.", ephemeral=True)

@bot.tree.command(name="role", description="Add or remove a role from a user")
@app_commands.describe(
    member="Member to modify",
    role="Role to add/remove"
)
@check_not_blocked()
async def role_slash(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    """Add or remove a role from a user"""
    if not interaction.user.guild_permissions.manage_roles:
        await interaction.response.send_message("❌ You need Manage Roles permission to use this command.", ephemeral=True)
        return
    
    if role in member.roles:
        try:
            await member.remove_roles(role)
            await interaction.response.send_message(f"✅ Removed role `{role.name}` from {member.mention}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to manage that role.", ephemeral=True)
    else:
        try:
            await member.add_roles(role)
            await interaction.response.send_message(f"✅ Added role `{role.name}` to {member.mention}")
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to manage that role.", ephemeral=True)

@bot.tree.command(name="mess", description="Send a DM to a user")
@app_commands.describe(
    user="User to message",
    message="Message to send"
)
@check_not_blocked()
async def mess_slash(interaction: discord.Interaction, user: discord.User, message: str):
    """Send a DM to a user"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    try:
        await user.send(f"**Message from {interaction.user}:**\n{message}")
        await interaction.response.send_message(f"✅ Message sent to {user.mention}", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"❌ Could not send DM to {user.mention} (DMs disabled)", ephemeral=True)

@bot.tree.command(name="create", description="Create reaction roles")
@app_commands.describe(
    emoji1="First emoji", role1="First role",
    emoji2="Second emoji (optional)", role2="Second role (optional)",
    emoji3="Third emoji (optional)", role3="Third role (optional)",
    emoji4="Fourth emoji (optional)", role4="Fourth role (optional)",
    emoji5="Fifth emoji (optional)", role5="Fifth role (optional)",
    emoji6="Sixth emoji (optional)", role6="Sixth role (optional)"
)
@check_not_blocked()
async def create_slash(
    interaction: discord.Interaction,
    emoji1: str, role1: discord.Role,
    emoji2: str = None, role2: discord.Role = None,
    emoji3: str = None, role3: discord.Role = None,
    emoji4: str = None, role4: discord.Role = None,
    emoji5: str = None, role5: discord.Role = None,
    emoji6: str = None, role6: discord.Role = None
):
    """Create reaction roles"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    # Build role mappings
    role_mappings = {emoji1: role1.id}
    embed = discord.Embed(
        title="🎭 Reaction Roles",
        description="React with the emojis below to get roles:",
        color=discord.Color.purple()
    )
    
    embed.add_field(name=f"{emoji1} {role1.name}", value="React to get this role", inline=True)
    
    # Add optional pairs
    pairs = [(emoji2, role2), (emoji3, role3), (emoji4, role4), (emoji5, role5), (emoji6, role6)]
    for emoji, role in pairs:
        if emoji and role:
            role_mappings[emoji] = role.id
            embed.add_field(name=f"{emoji} {role.name}", value="React to get this role", inline=True)
    
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    # Add reactions
    for emoji in role_mappings.keys():
        try:
            await message.add_reaction(emoji)
        except discord.HTTPException:
            await interaction.followup.send(f"❌ Could not add reaction {emoji}", ephemeral=True)
            return
    
    # Store reaction role mapping
    reaction_roles[message.id] = role_mappings
    await interaction.followup.send("✅ Reaction roles created successfully!", ephemeral=True)

@bot.tree.command(name="manage", description="Bot management panel")
@check_not_blocked()
async def manage_slash(interaction: discord.Interaction):
    """Bot management panel"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🔧 FACTSY Management Panel",
        description="Bot statistics and management options",
        color=discord.Color.gold()
    )
    
    # Bot stats
    total_servers = len(bot.guilds)
    total_users = len(set(bot.get_all_members()))
    uptime = format_uptime(time.time() - BOT_START_TIME)
    
    embed.add_field(name="📊 Statistics", 
                   value=f"**Servers:** {total_servers}\n**Users:** {total_users}\n**Uptime:** {uptime}", 
                   inline=True)
    
    # Blocked users count
    blocked_count = len(blocked_users)
    namelocked_count = len(namelocked_users)
    
    embed.add_field(name="🚫 Moderation", 
                   value=f"**Blocked Users:** {blocked_count}\n**Namelocked Users:** {namelocked_count}", 
                   inline=True)
    
    # Message tracking stats
    total_sniped = sum(len(messages) for messages in sniped_messages.values())
    total_edited = sum(len(messages) for messages in edited_messages.values())
    
    embed.add_field(name="📜 Message Tracking", 
                   value=f"**Sniped Messages:** {total_sniped}\n**Edited Messages:** {total_edited}", 
                   inline=True)
    
    embed.set_footer(text="FACTSY Bot Management | Made with ❤ by Werrzzzy")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="prefix", description="Change the server prefix")
@app_commands.describe(new_prefix="New prefix to set")
@check_not_blocked()
async def prefix_slash(interaction: discord.Interaction, new_prefix: str):
    """Change the server prefix"""
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ You need Administrator permission to use this command.", ephemeral=True)
        return
    
    if len(new_prefix) > 5:
        await interaction.response.send_message("❌ Prefix must be 5 characters or less.", ephemeral=True)
        return
    
    custom_prefixes[interaction.guild.id] = new_prefix
    await interaction.response.send_message(f"✅ Server prefix changed to `{new_prefix}`")

# Run the bot
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: DISCORD_TOKEN environment variable not found!")
        exit(1)
    bot.run(token)
