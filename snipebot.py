import discord
from discord.ext import commands
from discord import app_commands
import os
from flask import Flask
from threading import Thread
import re
import math
import difflib
import time

# Flask app to keep the bot running on Render
app = Flask('')

@app.route('/')
def home():
    return "SnipeBot is running!"

def run_flask():
    port = int(os.getenv("PORT", 8080))
    server = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": port}, daemon=True)
    server.start()

# Bot start time for uptime tracking
BOT_START_TIME = time.time()

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
        'silver': 0xc0c0c0
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

# Smart user finder function (like Dyno)
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

# Enable intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

# Initialize bot
bot = commands.Bot(command_prefix=",", intents=intents)
bot.remove_command('help')
sniped_messages = {}
edited_messages = {}

# Store webhooks for reuse
channel_webhooks = {}

# Store namelocked users: {user_id: locked_nickname}
namelocked_users = {}

# ENHANCED: Increased storage capacity to support 100 pages
MAX_MESSAGES = 100  # Increased from 10 to 100
MESSAGES_PER_PAGE = 10  # Number of messages to show per page in list view

# Helper function to handle media URLs
def get_media_url(content, attachments):
    # Check for tenor links
    tenor_match = re.search(r'https?://(?:www\.)?tenor\.com/view/[^\s]+', content or "")
    if tenor_match:
        return tenor_match.group(0)
    
    # Check for Twitter/X GIF links
    twitter_match = re.search(r'https?://(?:www\.)?twitter\.com/[^\s]+\.gif', content or "")
    if twitter_match:
        return twitter_match.group(0)
    
    # Check for discord attachment links with .gif extension
    gif_match = re.search(r'https?://(?:cdn|media)\.discordapp\.(?:com|net)/[^\s]+\.gif[^\s]*', content or "")
    if gif_match:
        return gif_match.group(0)
    
    # Check for direct GIF links
    direct_gif_match = re.search(r'https?://[^\s]+\.gif[^\s]*', content or "")
    if direct_gif_match:
        return direct_gif_match.group(0)
    
    # If there are attachments, return the URL of the first one
    if attachments:
        return attachments[0].url
    
    return None

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
    
    # Look for existing SnipeBot webhook in the channel
    webhooks = await channel.webhooks()
    for webhook in webhooks:
        if webhook.name == "SnipeBot Webhook":
            channel_webhooks[channel.id] = webhook
            return webhook
    
    # Create new webhook
    webhook = await channel.create_webhook(name="SnipeBot Webhook")
    channel_webhooks[channel.id] = webhook
    return webhook

# Custom check that allows administrators and owners to bypass permission requirements
def has_permission_or_is_admin():
    async def predicate(ctx):
        # Check if user is guild owner
        if ctx.guild and ctx.author.id == ctx.guild.owner_id:
            return True
        # Check if user is administrator
        if ctx.guild and ctx.author.guild_permissions.administrator:
            return True
        # Otherwise check for the specific permission in the command
        return await commands.has_permissions().predicate(ctx)
    return commands.check(predicate)

# Custom check for manage nicknames permission
def has_manage_nicknames():
    async def predicate(ctx):
        if not ctx.guild:
            return False
        # Check if user is guild owner
        if ctx.author.id == ctx.guild.owner_id:
            return True
        # Check if user has manage nicknames permission
        return ctx.author.guild_permissions.manage_nicknames
    return commands.check(predicate)

# Custom check for slash commands that allows administrators and owners to bypass
def check_admin_or_permissions(**perms):
    async def predicate(interaction: discord.Interaction):
        # Check if user is guild owner
        if interaction.guild and interaction.user.id == interaction.guild.owner_id:
            return True
        # Check if user is administrator
        if interaction.guild and interaction.user.guild_permissions.administrator:
            return True
        # Otherwise check for the specific permission
        for perm, value in perms.items():
            if value and not getattr(interaction.user.guild_permissions, perm):
                raise app_commands.MissingPermissions([perm])
        return True
    return app_commands.check(predicate)

# Custom check specifically for moderator permissions
def is_moderator():
    async def predicate(ctx):
        if not ctx.guild:
            return False
        # Check if user is guild owner
        if ctx.author.id == ctx.guild.owner_id:
            return True
        # Check if user is moderator or administrator
        return (ctx.author.guild_permissions.administrator or
                ctx.author.guild_permissions.manage_messages or
                ctx.author.guild_permissions.moderate_members or
                ctx.author.guild_permissions.ban_members)
    return commands.check(predicate)

# Custom check for slash commands for moderator permissions
def check_moderator():
    async def predicate(interaction: discord.Interaction):
        if not interaction.guild:
            return False
        # Check if user is guild owner
        if interaction.user.id == interaction.guild.owner_id:
            return True
        # Check if user is moderator or administrator
        return (interaction.user.guild_permissions.administrator or
                interaction.user.guild_permissions.manage_messages or
                interaction.user.guild_permissions.moderate_members or
                interaction.user.guild_permissions.ban_members)
    return app_commands.check(predicate)

# Custom check for specific user ID
def is_specific_user():
    async def predicate(ctx):
        return ctx.author.id == 776883692983156736
    return commands.check(predicate)

def check_specific_user():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == 776883692983156736
    return app_commands.check(predicate)

# REGULAR Pagination View for ,sp (FILTERED CONTENT - ALL MESSAGES)
class RegularSnipePaginationView(discord.ui.View):
    def __init__(self, messages, channel, timeout=300):
        super().__init__(timeout=timeout)
        self.messages = messages
        self.channel = channel
        self.current_page = 0
        self.total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        # Update button states based on current page
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def get_embed(self):
        # Calculate start and end indices for current page
        start_idx = self.current_page * MESSAGES_PER_PAGE
        end_idx = min(start_idx + MESSAGES_PER_PAGE, len(self.messages))
        page_messages = self.messages[start_idx:end_idx]
        
        # Create embed for REGULAR users
        embed = discord.Embed(
            title="📜 Deleted Messages List",
            color=discord.Color.gold()
        )
        
        if not page_messages:
            embed.add_field(
                name="No Messages",
                value="No deleted messages found in this channel.",
                inline=False
            )
        else:
            # Build numbered list of messages - ALWAYS FILTER FOR REGULAR USERS
            message_list = []
            for i, msg in enumerate(page_messages, start=start_idx + 1):
                content = msg['content'] or "*No text content*"
                
                # ALWAYS filter offensive content for regular users
                if msg.get('has_offensive_content', False):
                    content = filter_content(content)
                
                # Truncate content for list view
                content = truncate_content(content, 80)
                
                # Format: "1. Hi {username}"
                message_entry = f"{i}. {content} **-{msg['author'].display_name}**"
                message_list.append(message_entry)
            
            embed.add_field(
                name="Messages",
                value="\n".join(message_list),
                inline=False
            )
        
        # Add page information
        embed.set_footer(
            text=f"Page {self.current_page + 1} of {self.total_pages} | Total: {len(self.messages)} | Made with ❤ | Werrzzzy"
        )
        
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

# MODERATOR Pagination View for ,spforce (ONLY OFFENSIVE MESSAGES)
class ModeratorSnipePaginationView(discord.ui.View):
    def __init__(self, messages, channel, timeout=300):
        super().__init__(timeout=timeout)
        self.messages = messages
        self.channel = channel
        self.current_page = 0
        self.total_pages = math.ceil(len(messages) / MESSAGES_PER_PAGE)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        # Update button states based on current page
        self.previous_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
    
    def get_embed(self):
        # Calculate start and end indices for current page
        start_idx = self.current_page * MESSAGES_PER_PAGE
        end_idx = min(start_idx + MESSAGES_PER_PAGE, len(self.messages))
        page_messages = self.messages[start_idx:end_idx]
        
        # Create embed for MODERATORS
        embed = discord.Embed(
            title="🔒 Moderator Snipe Pages (Unfiltered)",
            color=discord.Color.dark_red()
        )
        embed.description = "⚠️ **Warning:** Some messages may contain offensive content."
        
        if not page_messages:
            embed.add_field(
                name="No Messages",
                value="No offensive messages found in this channel.",
                inline=False
            )
        else:
            # Build numbered list of messages - SHOW RAW OFFENSIVE CONTENT FOR MODERATORS
            message_list = []
            for i, msg in enumerate(page_messages, start=start_idx + 1):
                content = msg['content'] or "*No text content*"
                
                # NEVER filter content for moderators - show everything raw
                
                # Truncate content for list view
                content = truncate_content(content, 80)
                
                # Format: "1. Hi {username}"
                message_entry = f"{i}. {content} **-{msg['author'].display_name}**"
                message_list.append(message_entry)
            
            embed.add_field(
                name="Messages",
                value="\n".join(message_list),
                inline=False
            )
        
        # Add page information
        embed.set_footer(
            text=f"MOD Page {self.current_page + 1} of {self.total_pages} | Total: {len(self.messages)} | Made with ❤ | Werrzzzy"
        )
        
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

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands!")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
    print(f"Bot is online as {bot.user}!")
    await bot.change_presence(activity=discord.Game(name="Type /help or ,help for commands"))

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    if message.channel.id not in sniped_messages:
        sniped_messages[message.channel.id] = []
    
    # Try to find who deleted the message from audit logs
    deleted_by = message.author  # Default to message author (self-delete)
    
    try:
        # Check audit logs to see if someone else deleted it
        async for entry in message.guild.audit_logs(limit=10, action=discord.AuditLogAction.message_delete):
            # Check if this audit log entry is for our deleted message
            if (entry.target.id == message.author.id and 
                entry.created_at > message.created_at and
                (discord.utils.utcnow() - entry.created_at).total_seconds() < 5):  # Within 5 seconds
                deleted_by = entry.user
                break
    except (discord.Forbidden, discord.HTTPException, AttributeError):
        # If we can't access audit logs or there's an error, assume self-delete
        pass
    
    # Add offensive content flag to saved messages
    sniped_messages[message.channel.id].append({
        "content": message.content,
        "author": message.author,
        "deleted_by": deleted_by,
        "attachments": message.attachments,
        "time": message.created_at,
        "has_offensive_content": is_offensive_content(message.content)
    })

    # ENHANCED: Increased limit to 100 messages
    if len(sniped_messages[message.channel.id]) > MAX_MESSAGES:
        sniped_messages[message.channel.id].pop(0)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    if before.content == after.content:
        return  # No actual edit if content is the same (embed loading, etc.)
    
    if before.channel.id not in edited_messages:
        edited_messages[before.channel.id] = []
    
    # Add offensive content flags to saved messages
    edited_messages[before.channel.id].append({
        "before_content": before.content,
        "after_content": after.content,
        "author": before.author,
        "attachments": before.attachments,
        "time": after.edited_at or discord.utils.utcnow(),
        "before_has_offensive_content": is_offensive_content(before.content),
        "after_has_offensive_content": is_offensive_content(after.content)
    })
    
    # ENHANCED: Increased limit to 100 messages
    if len(edited_messages[before.channel.id]) > MAX_MESSAGES:
        edited_messages[before.channel.id].pop(0)

@bot.event
async def on_member_update(before, after):
    """Handle namelock enforcement when user changes nickname"""
    if before.display_name != after.display_name:
        # Check if user is namelocked
        if after.id in namelocked_users:
            locked_nickname = namelocked_users[after.id]
            if after.display_name != locked_nickname:
                try:
                    # Revert to locked nickname
                    await after.edit(nick=locked_nickname, reason="Namelock enforcement")
                except discord.Forbidden:
                    pass  # Bot doesn't have permission
                except Exception:
                    pass  # Other errors

# ========== SLASH COMMANDS ==========

@bot.tree.command(name="snipe", description="Displays the most recently deleted message")
@app_commands.describe(page="Page number (1-100)", channel="Channel to check (optional)")
async def snipe_slash(interaction: discord.Interaction, page: int = 1, channel: discord.TextChannel = None):
    target_channel = channel or interaction.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await interaction.response.send_message(f"No recently deleted messages in {target_channel.mention}.", ephemeral=True)
        return

    if page < 1 or page > len(sniped_messages[target_channel.id]):
        await interaction.response.send_message(f"Page must be between 1 and {len(sniped_messages[target_channel.id])}.", ephemeral=True)
        return

    snipe = sniped_messages[target_channel.id][-page]
    embed = discord.Embed(title="📜 Sniped Message", color=discord.Color.gold())
    
    # Filter content if it contains offensive words
    content = snipe['content'] or "*No text content*"
    if snipe.get('has_offensive_content', False):
        content = filter_content(content)
    
    embed.add_field(name="**Content:**", value=content, inline=False)
    
    # Show who deleted the message - if same person or can't detect, show author name
    deleted_by = snipe.get('deleted_by', snipe['author'])
    embed.add_field(name="**Deleted by:**", value=deleted_by.display_name, inline=True)
    
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.add_field(name="**Channel:**", value=target_channel.mention, inline=True)
    embed.set_footer(text=f"Page {page} of {len(sniped_messages[target_channel.id])} | Made with ❤ | Werrzzzy")

    # Handle attachments and media links (IMAGES/GIFS/VIDEOS)
    media_url = get_media_url(snipe['content'], snipe['attachments'])
    
    if media_url:
        embed.set_image(url=media_url)
    elif snipe["attachments"]:
        for attachment in snipe["attachments"]:
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.url)
                break
            if attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                embed.set_image(url=attachment.url)
                break

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sp", description="Display a paginated list of deleted messages")
@app_commands.describe(channel="Channel to check (optional)")
async def sp_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
    target_channel = channel or interaction.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await interaction.response.send_message(f"No recently deleted messages in {target_channel.mention}.", ephemeral=True)
        return

    # Reverse the messages to show newest first
    messages = list(reversed(sniped_messages[target_channel.id]))
    
    # Use REGULAR pagination view (filtered content)
    view = RegularSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    # Update embed title to show channel
    embed.title = f"📜 Deleted Messages List - {target_channel.name}"
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="snipepages", description="Display a paginated list of deleted messages")
@app_commands.describe(channel="Channel to check (optional)")
async def snipepages_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
    target_channel = channel or interaction.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await interaction.response.send_message(f"No recently deleted messages in {target_channel.mention}.", ephemeral=True)
        return

    # Reverse the messages to show newest first
    messages = list(reversed(sniped_messages[target_channel.id]))
    
    # Use REGULAR pagination view (filtered content)
    view = RegularSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    # Update embed title to show channel
    embed.title = f"📜 Deleted Messages List - {target_channel.name}"
    
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="spforce", description="Display unfiltered offensive messages only (mod only)")
@app_commands.describe(channel="Channel to check (optional)")
@check_moderator()
async def spforce_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
    target_channel = channel or interaction.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await interaction.response.send_message(f"No recently deleted messages in {target_channel.mention}.", ephemeral=True)
        return

    # Filter to only show messages with offensive content
    offensive_messages = [msg for msg in sniped_messages[target_channel.id] if msg.get('has_offensive_content', False)]
    
    if not offensive_messages:
        await interaction.response.send_message(f"No offensive messages found in {target_channel.mention}.", ephemeral=True)
        return
    
    # Reverse the messages to show newest first
    messages = list(reversed(offensive_messages))
    
    # Use MODERATOR pagination view (unfiltered content)
    view = ModeratorSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    # Update embed title to show channel
    embed.title = f"🔒 Moderator Snipe Pages (Unfiltered) - {target_channel.name}"
    
    await interaction.response.send_message(embed=embed, view=view)

# NEW: /spf shortcut for spforce
@bot.tree.command(name="spf", description="Shortcut for spforce - Display unfiltered offensive messages only (mod only)")
@app_commands.describe(channel="Channel to check (optional)")
@check_moderator()
async def spf_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
    await spforce_slash(interaction, channel)

@bot.tree.command(name="say", description="Make the bot say something (mod only)")
@app_commands.describe(message="The message for the bot to say")
@check_moderator()
async def say_slash(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("Message sent!", ephemeral=True)
    await interaction.followup.send(message)

# NEW: /saywb webhook command
@bot.tree.command(name="saywb", description="Make the bot say something using webhook (mod only)")
@app_commands.describe(
    message="The message for the bot to say",
    color="Optional color (hex code, color name, or 3/6 digit hex)"
)
@check_moderator()
async def saywb_slash(interaction: discord.Interaction, message: str, color: str = None):
    try:
        # Get or create webhook
        webhook = await get_or_create_webhook(interaction.channel)
        
        # Parse color
        embed_color = parse_color(color) if color else discord.Color.default()
        
        # Create embed
        embed = discord.Embed(description=message, color=embed_color)
        
        # Send via webhook
        await webhook.send(embed=embed, username="SnipeBot", avatar_url=bot.user.avatar.url if bot.user.avatar else None)
        
        await interaction.response.send_message("Webhook message sent!", ephemeral=True)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage webhooks in this channel.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="rename", description="Change someone's nickname (requires manage nicknames)")
@app_commands.describe(member="The member to rename", new_nickname="The new nickname")
@check_admin_or_permissions(manage_nicknames=True)
async def rename_slash(interaction: discord.Interaction, member: discord.Member, new_nickname: str):
    try:
        old_nick = member.display_name
        await member.edit(nick=new_nickname)
        embed = discord.Embed(title="✅ Nickname Changed", color=discord.Color.green())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Old Nickname", value=old_nick, inline=True)
        embed.add_field(name="New Nickname", value=new_nickname, inline=True)
        embed.set_footer(text="Made with ❤ | Werrzzzy")
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change this user's nickname.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# NEW: /re shortcut for rename
@bot.tree.command(name="re", description="Shortcut for rename - Change someone's nickname (requires manage nicknames)")
@app_commands.describe(member="The member to rename", new_nickname="The new nickname")
@check_admin_or_permissions(manage_nicknames=True)
async def re_slash(interaction: discord.Interaction, member: discord.Member, new_nickname: str):
    await rename_slash(interaction, member, new_nickname)

@bot.tree.command(name="message", description="Send a message to a user (mod only)")
@app_commands.describe(user_search="Username or partial name to find", message="The message to send")
@check_moderator()
async def message_slash(interaction: discord.Interaction, user_search: str, message: str):
    try:
        # Try to find user by ID first
        try:
            user = bot.get_user(int(user_search))
        except ValueError:
            user = None
        
        # If not found by ID, search by name
        if not user:
            user = find_user_by_name(interaction.guild, user_search)
        
        if not user:
            await interaction.response.send_message(f"❌ No user found matching '{user_search}'.", ephemeral=True)
            return
        
        # Send simple message (no embed/webhook design)
        await user.send(message)
        await interaction.response.send_message(f"✅ Message sent to {user.display_name}!", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ Could not send message to this user (they may have DMs disabled).", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# NEW: /mess shortcut for message
@bot.tree.command(name="mess", description="Shortcut for message - Send a message to a user (mod only)")
@app_commands.describe(user_search="Username or partial name to find", message="The message to send")
@check_moderator()
async def mess_slash(interaction: discord.Interaction, user_search: str, message: str):
    await message_slash(interaction, user_search, message)

# NEW: Namelock commands
@bot.tree.command(name="namelock", description="Lock a user's nickname (mod only)")
@app_commands.describe(member="The member to namelock", nickname="The nickname to lock them to")
@check_admin_or_permissions(manage_nicknames=True)
async def namelock_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    try:
        # Set the nickname first
        old_nick = member.display_name
        await member.edit(nick=nickname)
        
        # Add to namelock dictionary
        namelocked_users[member.id] = nickname
        
        embed = discord.Embed(title="🔒 Nickname Locked", color=discord.Color.orange())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Old Nickname", value=old_nick, inline=True)
        embed.add_field(name="Locked Nickname", value=nickname, inline=True)
        embed.add_field(name="Note", value="User cannot change their nickname until unlocked.", inline=False)
        embed.set_footer(text="Made with ❤ | Werrzzzy")
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to change this user's nickname.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# NEW: /nl shortcut for namelock
@bot.tree.command(name="nl", description="Shortcut for namelock - Lock a user's nickname (mod only)")
@app_commands.describe(member="The member to namelock", nickname="The nickname to lock them to")
@check_admin_or_permissions(manage_nicknames=True)
async def nl_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    await namelock_slash(interaction, member, nickname)

@bot.tree.command(name="unl", description="Unlock a user's nickname (mod only)")
@app_commands.describe(member="The member to unlock")
@check_admin_or_permissions(manage_nicknames=True)
async def unl_slash(interaction: discord.Interaction, member: discord.Member):
    if member.id in namelocked_users:
        locked_nickname = namelocked_users[member.id]
        del namelocked_users[member.id]
        
        embed = discord.Embed(title="🔓 Nickname Unlocked", color=discord.Color.green())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Was Locked To", value=locked_nickname, inline=True)
        embed.add_field(name="Note", value="User can now change their nickname freely.", inline=False)
        embed.set_footer(text="Made with ❤ | Werrzzzy")
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ {member.display_name} is not namelocked.", ephemeral=True)

@bot.tree.command(name="clear", description="Clear all sniped messages (admin only)")
@check_admin_or_permissions(manage_messages=True)
async def clear_slash(interaction: discord.Interaction):
    channel = interaction.channel
    snipe_count = len(sniped_messages.get(channel.id, []))
    edit_count = len(edited_messages.get(channel.id, []))
    
    if channel.id in sniped_messages:
        sniped_messages[channel.id] = []
    if channel.id in edited_messages:
        edited_messages[channel.id] = []
    
    embed = discord.Embed(title="✅ Messages Cleared", color=discord.Color.green())
    embed.add_field(name="Deleted Messages Cleared", value=str(snipe_count), inline=True)
    embed.add_field(name="Edited Messages Cleared", value=str(edit_count), inline=True)
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="editsnipe", description="Display the most recently edited message")
@app_commands.describe(page="Page number (1-100)")
async def editsnipe_slash(interaction: discord.Interaction, page: int = 1):
    channel = interaction.channel
    if channel.id not in edited_messages or not edited_messages[channel.id]:
        await interaction.response.send_message("No recently edited messages in this channel.", ephemeral=True)
        return

    if page < 1 or page > len(edited_messages[channel.id]):
        await interaction.response.send_message(f"Page must be between 1 and {len(edited_messages[channel.id])}.", ephemeral=True)
        return

    edit = edited_messages[channel.id][-page]
    embed = discord.Embed(title="📝 Edit Snipe", color=discord.Color.blue())
    
    # Filter content if it contains offensive words
    before_content = edit['before_content'] or "*No text content*"
    after_content = edit['after_content'] or "*No text content*"
    
    if edit.get('before_has_offensive_content', False):
        before_content = filter_content(before_content)
    if edit.get('after_has_offensive_content', False):
        after_content = filter_content(after_content)
    
    embed.add_field(name="**Before:**", value=before_content, inline=False)
    embed.add_field(name="**After:**", value=after_content, inline=False)
    embed.add_field(name="**Author:**", value=edit['author'].display_name, inline=True)
    embed.add_field(name="**Time:**", value=edit['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"Page {page} of {len(edited_messages[channel.id])} | Made with ❤ | Werrzzzy")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="manage", description="View bot management info")
async def manage_slash(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Bot Management", color=discord.Color.blurple())
    embed.add_field(name="Bot Owner", value="<@776883692983156736>", inline=True)
    embed.add_field(name="Bot ID", value=str(bot.user.id), inline=True)
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="Check bot latency")
async def ping_slash(interaction: discord.Interaction):
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
    embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await interaction.response.send_message(embed=embed)

# NEW: /time command (restricted to specific user)
@bot.tree.command(name="time", description="Show bot uptime (restricted access)")
@check_specific_user()
async def time_slash(interaction: discord.Interaction):
    current_time = time.time()
    uptime_seconds = current_time - BOT_START_TIME
    uptime_formatted = format_uptime(uptime_seconds)
    
    embed = discord.Embed(title="⏰ Bot Uptime", color=discord.Color.blue())
    embed.add_field(name="Uptime", value=uptime_formatted, inline=False)
    embed.add_field(name="Exact Seconds", value=f"{int(uptime_seconds)} seconds", inline=False)
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========== PREFIX COMMANDS ==========

# UPDATED HELP COMMAND with proper spacing and organization
@bot.command(name="help")
async def help_command(ctx):
    """Display bot commands help"""
    embed = discord.Embed(
        title="🤖 SnipeBot Commands",
        description="*A Discord bot for tracking deleted and edited messages with content filtering.*",
        color=discord.Color.blue()
    )
    
    # Snipe Commands
    embed.add_field(
        name="📜 Snipe Commands",
        value=(
            "` ,snipe [page]` — View a deleted message\n"
            "` ,s [page]` — Shortcut for ,snipe\n"
            "` ,sp` — View all deleted message pages\n"
            "` ,snipepages` — Same as ,sp\n"
            "` ,spforce` — View unfiltered deleted messages (Mods only)"
        ),
        inline=False
    )
    
    # Edit Snipe Commands
    embed.add_field(
        name="✏️ Edit Snipe Commands",
        value=(
            "` ,editsnipe [page]` — View an edited message\n"
            "` ,es [page]` — Shortcut for ,editsnipe"
        ),
        inline=False
    )
    
    # Moderation Commands
    embed.add_field(
        name="🛡️ Moderation Commands (Mods only)",
        value=(
            "` ,say <message>` — Make the bot send a message\n"
            "` ,message <user> <msg>` — Send a DM to a user\n"
            "` ,rename <user> <nickname>` — Change a user's nickname\n"
            "` ,clear` — Clear all sniped messages"
        ),
        inline=False
    )

    # Management Commands
    embed.add_field(
        name="👨‍💻 Management Commands",
        value=(
            "` ,manage` — View bot management info\n"
            "` ,ping` — Check bot latency\n"
            "` ,help` — Show this command list"
        ),
        inline=False
    )
    
    embed.set_footer(text="Made with ❤ by Werrzzzy")
    await ctx.send(embed=embed)

@bot.command(name="snipe")
async def snipe_command(ctx, page: int = 1, channel: discord.TextChannel = None):
    """Display a sniped message by page number"""
    target_channel = channel or ctx.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await ctx.send(f"No recently deleted messages in {target_channel.mention}.")
        return

    if page < 1 or page > len(sniped_messages[target_channel.id]):
        await ctx.send(f"Page must be between 1 and {len(sniped_messages[target_channel.id])}.")
        return

    snipe = sniped_messages[target_channel.id][-page]
    embed = discord.Embed(title="📜 Sniped Message", color=discord.Color.gold())
    
    # Filter content if it contains offensive words
    content = snipe['content'] or "*No text content*"
    if snipe.get('has_offensive_content', False):
        content = filter_content(content)
    
    embed.add_field(name="**Content:**", value=content, inline=False)
    
    # Show who deleted the message - if same person or can't detect, show author name
    deleted_by = snipe.get('deleted_by', snipe['author'])
    embed.add_field(name="**Deleted by:**", value=deleted_by.display_name, inline=True)
    
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    if channel:
        embed.add_field(name="**Channel:**", value=target_channel.mention, inline=True)
    embed.set_footer(text=f"Page {page} of {len(sniped_messages[target_channel.id])} | Made with ❤ | Werrzzzy")

    # Handle attachments and media links (IMAGES/GIFS/VIDEOS)
    media_url = get_media_url(snipe['content'], snipe['attachments'])
    
    if media_url:
        embed.set_image(url=media_url)
    elif snipe["attachments"]:
        for attachment in snipe["attachments"]:
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.url)
                break
            if attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                embed.set_image(url=attachment.url)
                break

    await ctx.send(embed=embed)

# NEW: ,s shortcut command for snipe
@bot.command(name="s")
async def s_command(ctx, page: int = 1, channel: discord.TextChannel = None):
    """Shortcut for snipe command"""
    await snipe_command(ctx, page, channel)

@bot.command(name="sp")
async def sp_command(ctx, channel: discord.TextChannel = None):
    """Display paginated list of all deleted messages"""
    target_channel = channel or ctx.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await ctx.send(f"No recently deleted messages in {target_channel.mention}.")
        return

    # Reverse the messages to show newest first
    messages = list(reversed(sniped_messages[target_channel.id]))
    
    # Use REGULAR pagination view (filtered content)
    view = RegularSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    # Update embed title to show channel if specified
    if channel:
        embed.title = f"📜 Deleted Messages List - {target_channel.name}"
    
    await ctx.send(embed=embed, view=view)

@bot.command(name="snipepages")
async def snipepages_command(ctx, channel: discord.TextChannel = None):
    """Display paginated list of all deleted messages"""
    target_channel = channel or ctx.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await ctx.send(f"No recently deleted messages in {target_channel.mention}.")
        return

    # Reverse the messages to show newest first
    messages = list(reversed(sniped_messages[target_channel.id]))
    
    # Use REGULAR pagination view (filtered content)
    view = RegularSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    # Update embed title to show channel if specified
    if channel:
        embed.title = f"📜 Deleted Messages List - {target_channel.name}"
    
    await ctx.send(embed=embed, view=view)

# MODIFIED: ,spforce now shows ONLY offensive messages
@bot.command(name="spforce")
@is_moderator()
async def spforce_command(ctx, channel: discord.TextChannel = None):
    """Display paginated list of ONLY offensive deleted messages (moderator only)"""
    target_channel = channel or ctx.channel
    
    if target_channel.id not in sniped_messages or not sniped_messages[target_channel.id]:
        await ctx.send(f"No recently deleted messages in {target_channel.mention}.")
        return

    # Filter to only show messages with offensive content
    offensive_messages = [msg for msg in sniped_messages[target_channel.id] if msg.get('has_offensive_content', False)]
    
    if not offensive_messages:
        await ctx.send(f"No offensive messages found in {target_channel.mention}.")
        return
    
    # Reverse the messages to show newest first
    messages = list(reversed(offensive_messages))
    
    # Use MODERATOR pagination view (unfiltered content)
    view = ModeratorSnipePaginationView(messages, target_channel)
    embed = view.get_embed()
    
    # Update embed title to show channel if specified
    if channel:
        embed.title = f"🔒 Moderator Snipe Pages (Unfiltered) - {target_channel.name}"
    
    await ctx.send(embed=embed, view=view)

# NEW: ,spf shortcut for spforce
@bot.command(name="spf")
@is_moderator()
async def spf_command(ctx, channel: discord.TextChannel = None):
    """Shortcut for spforce command"""
    await spforce_command(ctx, channel)

@bot.command(name="editsnipe")
async def editsnipe_command(ctx, page: int = 1):
    """Display an edit sniped message by page number"""
    channel = ctx.channel
    if channel.id not in edited_messages or not edited_messages[channel.id]:
        await ctx.send("No recently edited messages in this channel.")
        return

    if page < 1 or page > len(edited_messages[channel.id]):
        await ctx.send(f"Page must be between 1 and {len(edited_messages[channel.id])}.")
        return

    edit = edited_messages[channel.id][-page]
    embed = discord.Embed(title="📝 Edit Snipe", color=discord.Color.blue())
    
    # Filter content if it contains offensive words
    before_content = edit['before_content'] or "*No text content*"
    after_content = edit['after_content'] or "*No text content*"
    
    if edit.get('before_has_offensive_content', False):
        before_content = filter_content(before_content)
    if edit.get('after_has_offensive_content', False):
        after_content = filter_content(after_content)
    
    embed.add_field(name="**Before:**", value=before_content, inline=False)
    embed.add_field(name="**After:**", value=after_content, inline=False)
    embed.add_field(name="**Author:**", value=edit['author'].display_name, inline=True)
    embed.add_field(name="**Time:**", value=edit['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"Page {page} of {len(edited_messages[channel.id])} | Made with ❤ | Werrzzzy")
    
    await ctx.send(embed=embed)

@bot.command(name="es")
async def es_command(ctx, page: int = 1):
    """Shortcut for editsnipe command"""
    await editsnipe_command(ctx, page)

@bot.command(name="say")
@is_moderator()
async def say_command(ctx, *, message):
    """Make the bot say something (moderator only)"""
    await ctx.message.delete()  # Delete the command message
    await ctx.send(message)

# NEW: ,saywb webhook command
@bot.command(name="saywb")
@is_moderator()
async def saywb_command(ctx, color=None, *, message):
    """Make the bot say something using webhook (moderator only)"""
    try:
        # Delete the command message
        await ctx.message.delete()
        
        # If color is provided but message starts with a color-like string
        if color and not message:
            # User might have provided: ,saywb red hello world
            # In this case, treat everything after 'red' as the message
            parts = ctx.message.content.split(None, 2)
            if len(parts) >= 3:
                color = parts[1]
                message = parts[2]
            else:
                message = color
                color = None
        elif color and not color.startswith('#') and len(color) > 10:
            # If 'color' is too long, it's probably part of the message
            message = f"{color} {message}"
            color = None
        
        # Get or create webhook
        webhook = await get_or_create_webhook(ctx.channel)
        
        # Parse color
        embed_color = parse_color(color) if color else discord.Color.default()
        
        # Create embed
        embed = discord.Embed(description=message, color=embed_color)
        
        # Send via webhook
        await webhook.send(embed=embed, username="SnipeBot", avatar_url=bot.user.avatar.url if bot.user.avatar else None)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to manage webhooks in this channel.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name="rename")
@has_manage_nicknames()
async def rename_command(ctx, user_search, *, new_nickname):
    """Change someone's nickname (requires manage nicknames permission)"""
    try:
        # Try to find user by ID first
        try:
            member = ctx.guild.get_member(int(user_search))
        except ValueError:
            member = None
        
        # If not found by ID, search by name
        if not member:
            member = find_user_by_name(ctx.guild, user_search)
        
        if not member:
            await ctx.send(f"❌ No member found matching '{user_search}'.")
            return
        
        old_nick = member.display_name
        await member.edit(nick=new_nickname)
        embed = discord.Embed(title="✅ Nickname Changed", color=discord.Color.green())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Old Nickname", value=old_nick, inline=True)
        embed.add_field(name="New Nickname", value=new_nickname, inline=True)
        embed.set_footer(text="Made with ❤ | Werrzzzy")
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

# NEW: ,re shortcut for rename
@bot.command(name="re")
@has_manage_nicknames()
async def re_command(ctx, user_search, *, new_nickname):
    """Shortcut for rename command"""
    await rename_command(ctx, user_search, new_nickname)

@bot.command(name="message")
@is_moderator()
async def message_command(ctx, user_search, *, message):
    """Send a DM to a user (moderator only)"""
    try:
        # Try to find user by ID first
        try:
            user = bot.get_user(int(user_search))
        except ValueError:
            user = None
        
        # If not found by ID, search by name in guild
        if not user:
            user = find_user_by_name(ctx.guild, user_search)
        
        if not user:
            await ctx.send(f"❌ No user found matching '{user_search}'.")
            return
        
        # Send simple message (no embed/webhook design)
        await user.send(message)
        await ctx.send(f"✅ Message sent to {user.display_name}!")
    except discord.Forbidden:
        await ctx.send("❌ Could not send message to this user (they may have DMs disabled).")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

# NEW: ,mess shortcut for message
@bot.command(name="mess")
@is_moderator()
async def mess_command(ctx, user_search, *, message):
    """Shortcut for message command"""
    await message_command(ctx, user_search, message)

# NEW: Namelock commands
@bot.command(name="namelock")
@has_manage_nicknames()
async def namelock_command(ctx, user_search, *, nickname):
    """Lock a user's nickname (requires manage nicknames permission)"""
    try:
        # Try to find user by ID first
        try:
            member = ctx.guild.get_member(int(user_search))
        except ValueError:
            member = None
        
        # If not found by ID, search by name
        if not member:
            member = find_user_by_name(ctx.guild, user_search)
        
        if not member:
            await ctx.send(f"❌ No member found matching '{user_search}'.")
            return
        
        # Set the nickname first
        old_nick = member.display_name
        await member.edit(nick=nickname)
        
        # Add to namelock dictionary
        namelocked_users[member.id] = nickname
        
        embed = discord.Embed(title="🔒 Nickname Locked", color=discord.Color.orange())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Old Nickname", value=old_nick, inline=True)
        embed.add_field(name="Locked Nickname", value=nickname, inline=True)
        embed.add_field(name="Note", value="User cannot change their nickname until unlocked.", inline=False)
        embed.set_footer(text="Made with ❤ | Werrzzzy")
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to change this user's nickname.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

# NEW: ,nl shortcut for namelock
@bot.command(name="nl")
@has_manage_nicknames()
async def nl_command(ctx, user_search, *, nickname):
    """Shortcut for namelock command"""
    await namelock_command(ctx, user_search, nickname)

@bot.command(name="unl")
@has_manage_nicknames()
async def unl_command(ctx, user_search):
    """Unlock a user's nickname (requires manage nicknames permission)"""
    try:
        # Try to find user by ID first
        try:
            member = ctx.guild.get_member(int(user_search))
        except ValueError:
            member = None
        
        # If not found by ID, search by name
        if not member:
            member = find_user_by_name(ctx.guild, user_search)
        
        if not member:
            await ctx.send(f"❌ No member found matching '{user_search}'.")
            return
        
        if member.id in namelocked_users:
            locked_nickname = namelocked_users[member.id]
            del namelocked_users[member.id]
            
            embed = discord.Embed(title="🔓 Nickname Unlocked", color=discord.Color.green())
            embed.add_field(name="Member", value=member.mention, inline=True)
            embed.add_field(name="Was Locked To", value=locked_nickname, inline=True)
            embed.add_field(name="Note", value="User can now change their nickname freely.", inline=False)
            embed.set_footer(text="Made with ❤ | Werrzzzy")
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"❌ {member.display_name} is not namelocked.")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name="clear")
@has_permission_or_is_admin()
async def clear_command(ctx):
    """Clear all sniped messages (admin only)"""
    channel = ctx.channel
    snipe_count = len(sniped_messages.get(channel.id, []))
    edit_count = len(edited_messages.get(channel.id, []))
    
    if channel.id in sniped_messages:
        sniped_messages[channel.id] = []
    if channel.id in edited_messages:
        edited_messages[channel.id] = []
    
    embed = discord.Embed(title="✅ Messages Cleared", color=discord.Color.green())
    embed.add_field(name="Deleted Messages Cleared", value=str(snipe_count), inline=True)
    embed.add_field(name="Edited Messages Cleared", value=str(edit_count), inline=True)
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await ctx.send(embed=embed)

@bot.command(name="manage")
async def manage_command(ctx):
    """Display bot management info"""
    embed = discord.Embed(title="🤖 Bot Management", color=discord.Color.blurple())
    embed.add_field(name="Bot Owner", value="<@776883692983156736>", inline=True)
    embed.add_field(name="Bot ID", value=str(bot.user.id), inline=True)
    embed.add_field(name="Servers", value=str(len(bot.guilds)), inline=True)
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_command(ctx):
    """Check bot latency"""
    latency = round(bot.latency * 1000)
    embed = discord.Embed(title="🏓 Pong!", color=discord.Color.green())
    embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await ctx.send(embed=embed)

# NEW: ,time command (restricted to specific user)
@bot.command(name="time")
@is_specific_user()
async def time_command(ctx):
    """Show bot uptime (restricted to specific user)"""
    current_time = time.time()
    uptime_seconds = current_time - BOT_START_TIME
    uptime_formatted = format_uptime(uptime_seconds)
    
    embed = discord.Embed(title="⏰ Bot Uptime", color=discord.Color.blue())
    embed.add_field(name="Uptime", value=uptime_formatted, inline=False)
    embed.add_field(name="Exact Seconds", value=f"{int(uptime_seconds)} seconds", inline=False)
    embed.set_footer(text="Made with ❤ | Werrzzzy")
    await ctx.send(embed=embed)

# Start Flask server and run bot
if __name__ == "__main__":
    run_flask()
    bot.run(os.getenv("TOKEN"))
