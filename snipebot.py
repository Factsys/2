import discord
from discord.ext import commands
from discord import app_commands
import os
import re
import aiohttp
import logging
import datetime
import asyncio
from typing import Dict, List, Optional, Tuple
from bs4 import BeautifulSoup
from flask import Flask, render_template
from threading import Thread

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Flask app to keep the bot running
app = Flask('')

@app.route('/')
def home():
    """Display the home page"""
    return "SnipeBot is running!"

def run_flask():
    port = int(os.getenv("PORT", 8080))
    server = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": port}, daemon=True)
    server.start()

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
    r"f[uÃ¼v][c(kq)][k]?",              # f-word
    r"r[e3][t+][a@4][r]{1,2}[d]*",     # r-word
    r"b[i1!|][t+][c(kq)][h]+",         # b-word
    r"s[h][i1!|][t+]",                 # shit
    r"r[a@4][p][e3]",                  # rape
    r"a[s$]{2,}[h]*[o0]*[l1!|]*[e]*",  # a-hole
    r"d[i1!|][c(kq)][k]+",             # dick
    r"c[uÃ¼v][n][t]+",                  # c-word
    r"p[o0][r]+[n]+",                  # porn
    r"w[h][o0][r]+[e3]+",              # whore
    r"s[l1][uÃ¼v][t]+",                 # slut
    r"f[a@4][gq69]+",                  # fag
    r"k[i1l|!][l1][l1]y[o0][uÃ¼v][r]+[s$][e3][l1]+[f]+", # kill yourself
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

# Tenor Handler class
class TenorHandler:
    def __init__(self):
        """Initialize the TenorHandler."""
        # Regular expression patterns
        self.tenor_pattern = re.compile(r'https?://tenor\.com/view/[\w-]+-\d+')
        self.gif_id_pattern = re.compile(r'https?://tenor\.com/view/[\w-]+-(\d+)')
    
    async def extract_gif_url(self, tenor_url: str) -> Optional[str]:
        """
        Extract the actual GIF URL from a Tenor link.
        
        Args:
            tenor_url: The Tenor URL to extract the GIF from
            
        Returns:
            The actual GIF URL, or None if extraction failed
        """
        # First, try the API method
        try:
            gif_url = await self._extract_via_api(tenor_url)
            if gif_url:
                return gif_url
        except Exception as e:
            logger.warning(f"API extraction failed: {e}, trying fallback method")
        
        # If API method fails, try the fallback (scraping)
        try:
            return await self._extract_via_scraping(tenor_url)
        except Exception as e:
            logger.error(f"Error extracting GIF URL via scraping: {e}")
            return None
    
    async def _extract_via_api(self, tenor_url: str) -> Optional[str]:
        """
        Extract the GIF URL using Tenor's API.
        
        Args:
            tenor_url: The Tenor URL to extract the GIF from
            
        Returns:
            The GIF URL, or None if extraction failed
        """
        # Extract the GIF ID from the URL
        match = self.gif_id_pattern.match(tenor_url)
        if not match:
            return None
        
        gif_id = match.group(1)
        
        # Construct the API URL
        api_url = f"https://tenor.googleapis.com/v2/posts?ids={gif_id}&key=AIzaSyDbC3ahfcjkHZVFX2Jd75L1UUXVvYUrSQ0&client_key=tenor_web"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status != 200:
                    logger.warning(f"API request failed with status {response.status}")
                    return None
                
                data = await response.json()
                
                # Extract the GIF URL from the response
                try:
                    results = data.get('results', [])
                    if not results:
                        return None
                    
                    media_formats = results[0].get('media_formats', {})
                    # Try to get different formats in order of preference
                    for format_type in ['gif', 'mediumgif', 'tinygif', 'mp4', 'webm']:
                        if format_type in media_formats:
                            return media_formats[format_type]['url']
                    
                    return None
                except (KeyError, IndexError) as e:
                    logger.warning(f"Failed to extract GIF URL from API response: {e}")
                    return None
    
    async def _extract_via_scraping(self, tenor_url: str) -> Optional[str]:
        """
        Extract the GIF URL by scraping the Tenor page.
        
        Args:
            tenor_url: The Tenor URL to extract the GIF from
            
        Returns:
            The GIF URL, or None if extraction failed
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(tenor_url) as response:
                if response.status != 200:
                    logger.warning(f"Scraping request failed with status {response.status}")
                    return None
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Look for the GIF URL in various places
                # 1. Try to find it in meta tags
                og_image = soup.find('meta', property='og:image')
                if og_image and og_image.get('content'):
                    return og_image['content']
                
                # 2. Try to find it in <img> tags
                gif_imgs = soup.find_all('img', class_='Gif-image')
                if gif_imgs:
                    for img in gif_imgs:
                        if 'src' in img.attrs:
                            return img['src']
                
                # 3. Try to find it in <source> tags
                sources = soup.find_all('source')
                for source in sources:
                    if 'src' in source.attrs and source['src'].endswith(('.gif', '.mp4', '.webm')):
                        return source['src']
                
                # 4. Look for any script tags with JSON data
                for script in soup.find_all('script', type='application/json'):
                    try:
                        import json
                        data = json.loads(script.string)
                        if 'src' in data and data['src'].endswith(('.gif', '.mp4', '.webm')):
                            return data['src']
                    except:
                        pass
                
                logger.warning("Could not extract GIF URL from Tenor page")
                return None

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
        try:
            return attachments[0].url
        except (AttributeError, IndexError):
            if isinstance(attachments, list) and len(attachments) > 0:
                return attachments[0]
    
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

# Create tenor handler instance
tenor_handler = TenorHandler()

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
    
    # Check if there's a Tenor link in the message
    tenor_gif_url = None
    
    if message.content:
        tenor_match = re.search(r'https?://(?:www\.)?tenor\.com/view/[^\s]+', message.content)
        if tenor_match:
            tenor_url = tenor_match.group(0)
            try:
                # Extract the actual GIF URL using the handler
                tenor_gif_url = await tenor_handler.extract_gif_url(tenor_url)
            except Exception as e:
                print(f"Error extracting Tenor GIF URL: {e}")
    
    # Add offensive content flag to saved messages
    sniped_messages[message.channel.id].append({
        "content": message.content,
        "author": message.author,
        "attachments": message.attachments,
        "time": message.created_at,
        "has_offensive_content": is_offensive_content(message.content),
        "tenor_gif_url": tenor_gif_url  # Store the actual GIF URL
    })

    if len(sniped_messages[message.channel.id]) > 10:
        sniped_messages[message.channel.id].pop(0)

@bot.event
async def on_message_edit(before, after):
    if before.author.bot:
        return
    
    if before.content == after.content:
        return  # No actual edit if content is the same (embed loading, etc.)
    
    if before.channel.id not in edited_messages:
        edited_messages[before.channel.id] = []
    
    # Check if there's a Tenor link in the message
    tenor_gif_url = None
    
    if after.content:
        tenor_match = re.search(r'https?://(?:www\.)?tenor\.com/view/[^\s]+', after.content)
        if tenor_match:
            tenor_url = tenor_match.group(0)
            try:
                # Extract the actual GIF URL using the handler
                tenor_gif_url = await tenor_handler.extract_gif_url(tenor_url)
            except Exception as e:
                print(f"Error extracting Tenor GIF URL: {e}")
    
    # Add offensive content flags to saved messages
    edited_messages[before.channel.id].append({
        "before_content": before.content,
        "after_content": after.content,
        "author": before.author,
        "attachments": before.attachments,
        "time": after.edited_at or discord.utils.utcnow(),
        "before_has_offensive_content": is_offensive_content(before.content),
        "after_has_offensive_content": is_offensive_content(after.content),
        "tenor_gif_url": tenor_gif_url  # Store the actual GIF URL
    })
    
    if len(edited_messages[before.channel.id]) > 10:
        edited_messages[before.channel.id].pop(0)

@bot.tree.command(name="ping", description="Check the bot's latency")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.tree.command(name="snipe", description="Displays the most recently deleted message")
@app_commands.describe(page="Page number (optional)")
async def snipe_slash(interaction: discord.Interaction, page: int = 1):
    channel = interaction.channel
    if channel.id not in sniped_messages or not sniped_messages[channel.id]:
        await interaction.response.send_message("No recently deleted messages in this channel.", ephemeral=True)
        return

    if page < 1 or page > len(sniped_messages[channel.id]):
        await interaction.response.send_message(f"Page must be between 1 and {len(sniped_messages[channel.id])}.", ephemeral=True)
        return

    snipe = sniped_messages[channel.id][-page]
    embed = discord.Embed(title="ðŸ“œ Sniped Message", color=discord.Color.gold())
    
    # Filter content if it contains offensive words
    content = snipe['content'] or "*No text content*"
    if snipe.get('has_offensive_content', False):
        content = filter_content(content)
    
    embed.add_field(name="**Content:**", value=content, inline=False)
    embed.add_field(name="**Deleted by:**", value=snipe['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"SnipeBot | Page {page} of {len(sniped_messages[channel.id])}")

    # Handle Tenor GIF URLs directly
    if snipe.get('tenor_gif_url'):
        embed.set_image(url=snipe['tenor_gif_url'])
    else:
        # Fall back to other media handling methods
        media_url = get_media_url(snipe['content'], snipe['attachments'])
        
        if media_url:
            if 'tenor.com/view/' in media_url:
                # For Tenor links not processed earlier, try to extract GIF now
                try:
                    gif_url = await tenor_handler.extract_gif_url(media_url)
                    if gif_url:
                        embed.set_image(url=gif_url)
                except Exception as e:
                    print(f"Error extracting Tenor GIF URL on display: {e}")
            else:
                # For non-Tenor media
                embed.set_image(url=media_url)
        elif snipe["attachments"]:
            for attachment in snipe["attachments"]:
                if hasattr(attachment, 'content_type') and attachment.content_type and attachment.content_type.startswith("image"):
                    embed.set_image(url=attachment.url)
                    break
                if hasattr(attachment, 'url') and attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    embed.set_image(url=attachment.url)
                    break

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="snipeforce", description="Display unfiltered deleted messages (mod only)")
@app_commands.describe(page="Page number (optional)")
@check_moderator()
async def snipeforce_slash(interaction: discord.Interaction, page: int = 1):
    channel = interaction.channel
    if channel.id not in sniped_messages or not sniped_messages[channel.id]:
        await interaction.response.send_message("No recently deleted messages in this channel.", ephemeral=True)
        return

    if page < 1 or page > len(sniped_messages[channel.id]):
        await interaction.response.send_message(f"Page must be between 1 and {len(sniped_messages[channel.id])}.", ephemeral=True)
        return

    snipe = sniped_messages[channel.id][-page]
    embed = discord.Embed(title="ðŸ”’ Moderator Snipe (Unfiltered)", color=discord.Color.dark_red())
    
    # Show unfiltered content
    content = snipe['content'] or "*No text content*"
    if snipe.get('has_offensive_content', False):
        embed.description = "âš ï¸ **Warning:** This message contains offensive content."
    
    embed.add_field(name="**Content:**", value=content, inline=False)
    embed.add_field(name="**Deleted by:**", value=snipe['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"SnipeBot MOD | Page {page} of {len(sniped_messages[channel.id])}")

    # Handle Tenor GIF URLs directly
    if snipe.get('tenor_gif_url'):
        embed.set_image(url=snipe['tenor_gif_url'])
    else:
        # Fall back to other media handling methods
        media_url = get_media_url(snipe['content'], snipe['attachments'])
        
        if media_url:
            if 'tenor.com/view/' in media_url:
                # For Tenor links not processed earlier, try to extract GIF now
                try:
                    gif_url = await tenor_handler.extract_gif_url(media_url)
                    if gif_url:
                        embed.set_image(url=gif_url)
                except Exception as e:
                    print(f"Error extracting Tenor GIF URL on display: {e}")
            else:
                # For non-Tenor media
                embed.set_image(url=media_url)
        elif snipe["attachments"]:
            for attachment in snipe["attachments"]:
                if hasattr(attachment, 'content_type') and attachment.content_type and attachment.content_type.startswith("image"):
                    embed.set_image(url=attachment.url)
                    break
                if hasattr(attachment, 'url') and attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    embed.set_image(url=attachment.url)
                    break

    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="snipeedit", description="Displays the most recently edited message")
@app_commands.describe(page="Page number (optional)")
async def snipeedit_slash(interaction: discord.Interaction, page: int = 1):
    channel = interaction.channel
    if channel.id not in edited_messages or not edited_messages[channel.id]:
        await interaction.response.send_message("No recently edited messages in this channel.", ephemeral=True)
        return
    
    if page < 1 or page > len(edited_messages[channel.id]):
        await interaction.response.send_message(f"Page must be between 1 and {len(edited_messages[channel.id])}.", ephemeral=True)
        return
    
    edit = edited_messages[channel.id][-page]
    embed = discord.Embed(title="âœï¸ Edited Message", color=discord.Color.blue())
    
    # Filter content if it contains offensive words
    before_content = edit['before_content'] or "*No text content*"
    after_content = edit['after_content'] or "*No text content*"
    
    if edit.get('before_has_offensive_content', False):
        before_content = filter_content(before_content)
    
    if edit.get('after_has_offensive_content', False):
        after_content = filter_content(after_content)
    
    embed.add_field(name="**Before:**", value=before_content, inline=False)
    embed.add_field(name="**After:**", value=after_content, inline=False)
    embed.add_field(name="**Edited by:**", value=edit['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=edit['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"SnipeBot | Page {page} of {len(edited_messages[channel.id])}")
    
    # Handle Tenor GIF URLs directly
    if edit.get('tenor_gif_url'):
        embed.set_image(url=edit['tenor_gif_url'])
    else:
        # Fall back to other media handling methods
        media_url = get_media_url(edit['after_content'], edit['attachments'])
        
        if media_url:
            if 'tenor.com/view/' in media_url:
                # For Tenor links not processed earlier, try to extract GIF now
                try:
                    gif_url = await tenor_handler.extract_gif_url(media_url)
                    if gif_url:
                        embed.set_image(url=gif_url)
                except Exception as e:
                    print(f"Error extracting Tenor GIF URL on display: {e}")
            else:
                # For non-Tenor media
                embed.set_image(url=media_url)
        elif edit["attachments"]:
            for attachment in edit["attachments"]:
                if hasattr(attachment, 'content_type') and attachment.content_type and attachment.content_type.startswith("image"):
                    embed.set_image(url=attachment.url)
                    break
                if hasattr(attachment, 'url') and attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    embed.set_image(url=attachment.url)
                    break
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="snipeeditforce", description="Display unfiltered edited messages (mod only)")
@app_commands.describe(page="Page number (optional)")
@check_moderator()
async def snipeeditforce_slash(interaction: discord.Interaction, page: int = 1):
    channel = interaction.channel
    if channel.id not in edited_messages or not edited_messages[channel.id]:
        await interaction.response.send_message("No recently edited messages in this channel.", ephemeral=True)
        return
    
    if page < 1 or page > len(edited_messages[channel.id]):
        await interaction.response.send_message(f"Page must be between 1 and {len(edited_messages[channel.id])}.", ephemeral=True)
        return
    
    edit = edited_messages[channel.id][-page]
    embed = discord.Embed(title="ðŸ”’ Moderator Edit Snipe (Unfiltered)", color=discord.Color.dark_red())
    
    # Show unfiltered content
    before_content = edit['before_content'] or "*No text content*"
    after_content = edit['after_content'] or "*No text content*"
    
    has_offensive = edit.get('before_has_offensive_content', False) or edit.get('after_has_offensive_content', False)
    if has_offensive:
        embed.description = "âš ï¸ **Warning:** This message contains offensive content."
    
    embed.add_field(name="**Before:**", value=before_content, inline=False)
    embed.add_field(name="**After:**", value=after_content, inline=False)
    embed.add_field(name="**Edited by:**", value=edit['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=edit['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"SnipeBot MOD | Page {page} of {len(edited_messages[channel.id])}")
    
    # Handle Tenor GIF URLs directly
    if edit.get('tenor_gif_url'):
        embed.set_image(url=edit['tenor_gif_url'])
    else:
        # Fall back to other media handling methods
        media_url = get_media_url(edit['after_content'], edit['attachments'])
        
        if media_url:
            if 'tenor.com/view/' in media_url:
                # For Tenor links not processed earlier, try to extract GIF now
                try:
                    gif_url = await tenor_handler.extract_gif_url(media_url)
                    if gif_url:
                        embed.set_image(url=gif_url)
                except Exception as e:
                    print(f"Error extracting Tenor GIF URL on display: {e}")
            else:
                # For non-Tenor media
                embed.set_image(url=media_url)
        elif edit["attachments"]:
            for attachment in edit["attachments"]:
                if hasattr(attachment, 'content_type') and attachment.content_type and attachment.content_type.startswith("image"):
                    embed.set_image(url=attachment.url)
                    break
                if hasattr(attachment, 'url') and attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    embed.set_image(url=attachment.url)
                    break
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="mess", description="DM a user with a message (requires timeout members permission)")
@app_commands.describe(member="User to DM", message="The message to send")
@check_admin_or_permissions(moderate_members=True)  # Admin/owner bypass check
async def mess(interaction: discord.Interaction, member: discord.Member, message: str):
    try:
        await member.send(message)
        embed = discord.Embed(
            title="âœ… Message Sent",
            description=f"Message sent to {member.mention}.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.Forbidden:
        embed = discord.Embed(
            title="âŒ Failed to Send",
            description="Could not send DM. User may have DMs disabled.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="reset", description="Reset all sniped and edited messages (requires administrator permission)")
@check_admin_or_permissions(administrator=True)  # Admin/owner bypass check
async def reset_slash(interaction: discord.Interaction):
    channel_id = interaction.channel.id
    sniped_reset = False
    edited_reset = False
    
    if channel_id in sniped_messages:
        sniped_messages[channel_id] = []
        sniped_reset = True
        
    if channel_id in edited_messages:
        edited_messages[channel_id] = []
        edited_reset = True
        
    if sniped_reset or edited_reset:
        embed = discord.Embed(
            title="ðŸ—‘ï¸ Reset Complete",
            description="Cleared sniped and edited messages in this channel.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        embed = discord.Embed(
            title="â„¹ï¸ Nothing to Reset",
            description="There were no sniped or edited messages to clear.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rename", description="Change a user's nickname (requires manage nicknames permission)")
@app_commands.describe(member="User to rename", nickname="New nickname")
@check_admin_or_permissions(manage_nicknames=True)  # Admin/owner bypass check
async def rename_slash(interaction: discord.Interaction, member: discord.Member, nickname: str):
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname)
        embed = discord.Embed(
            title="âœ… Nickname Changed",
            description=f"Changed {member.mention}'s nickname from '{old_nick}' to '{nickname}'.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="âŒ Failed",
            description="I don't have permission to change that user's nickname.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except discord.HTTPException as e:
        embed = discord.Embed(
            title="âŒ Error",
            description=f"Failed to change nickname: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="filter", description="Check if the content filter is enabled")
async def filter_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="ðŸ›¡ï¸ Content Filter Status",
        description="The content filter is active. Offensive words in sniped messages will be hidden with asterisks.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Moderator Commands",
        value="Moderators can use `/snipeforce` and `/snipeeditforce` to view unfiltered content.",
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="maintainer", description="Shows who maintains the bot")
async def maintainer(interaction: discord.Interaction):
    embed = discord.Embed(
        title="ðŸ‘¤ Bot Maintainer",
        description="This bot is maintained and developed by Werzzzy.",
        color=discord.Color.blue()
    )
    embed.set_footer(text="SnipeBot by Werzzzy")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="help", description="Show bot commands")
async def help_slash(interaction: discord.Interaction):
    embed = discord.Embed(
        title="â“ SnipeBot Help",
        description="Available commands:",
        color=discord.Color.blurple()
    )
    embed.add_field(name="`,snipe` or `/snipe [page]`", value="Show recently deleted messages with content filtering.", inline=False)
    embed.add_field(name="`,snipeforce` or `/snipeforce [page]`", value="Show unfiltered deleted messages (moderator only).", inline=False)
    embed.add_field(name="`,snipeedit` or `/snipeedit [page]`", value="Show edited messages with content filtering.", inline=False)
    embed.add_field(name="`,snipeeditforce` or `/snipeeditforce [page]`", value="Show unfiltered edited messages (moderator only).", inline=False)
    embed.add_field(name="`,mess @user [message]` or `/mess`", value="Send a DM to a user (requires timeout members permission).", inline=False)
    embed.add_field(name="`,rename @user [nickname]` or `/rename`", value="Change a user's nickname (requires manage nicknames permission).", inline=False)
    embed.add_field(name="`,reset` or `/reset`", value="Reset all sniped and edited messages (requires administrator permission).", inline=False)
    embed.add_field(name="`,filter` or `/filter`", value="Check content filter status.", inline=False)
    embed.add_field(name="`,help` or `/help`", value="Show this help message.", inline=False)
    embed.set_footer(text="SnipeBot by Werzzzy | Server owner and administrators bypass all permission requirements")
    await interaction.response.send_message(embed=embed)

@bot.command(aliases=["s"])
async def snipe(ctx, page: int = 1):
    channel_id = ctx.channel.id
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        embed = discord.Embed(
            title="âŒ No Deleted Messages",
            description="There are no recently deleted messages in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if page < 1 or page > len(sniped_messages[channel_id]):
        embed = discord.Embed(
            title="âš ï¸ Invalid Page Number",
            description=f"Page must be between 1 and {len(sniped_messages[channel_id])}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    snipe = sniped_messages[channel_id][-page]
    embed = discord.Embed(title="ðŸ“œ Sniped Message", color=discord.Color.gold())
    
    # Filter content if it contains offensive words
    content = snipe['content'] or "*No text content*"
    if snipe.get('has_offensive_content', False):
        content = filter_content(content)
    
    embed.add_field(name="**Content:**", value=content, inline=False)
    embed.add_field(name="**Deleted by:**", value=snipe['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"SnipeBot | Page {page} of {len(sniped_messages[channel_id])}")

    # Handle Tenor GIF URLs directly
    if snipe.get('tenor_gif_url'):
        embed.set_image(url=snipe['tenor_gif_url'])
    else:
        # Fall back to other media handling methods
        media_url = get_media_url(snipe['content'], snipe['attachments'])
        
        if media_url:
            if 'tenor.com/view/' in media_url:
                # For Tenor links not processed earlier, try to extract GIF now
                try:
                    gif_url = await tenor_handler.extract_gif_url(media_url)
                    if gif_url:
                        embed.set_image(url=gif_url)
                except Exception as e:
                    print(f"Error extracting Tenor GIF URL on display: {e}")
            else:
                # For non-Tenor media
                embed.set_image(url=media_url)
        elif snipe["attachments"]:
            for attachment in snipe["attachments"]:
                if hasattr(attachment, 'content_type') and attachment.content_type and attachment.content_type.startswith("image"):
                    embed.set_image(url=attachment.url)
                    break
                if hasattr(attachment, 'url') and attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    embed.set_image(url=attachment.url)
                    break

    await ctx.send(embed=embed)

@bot.command()
@is_moderator()
async def snipeforce(ctx, page: int = 1):
    channel_id = ctx.channel.id
    if channel_id not in sniped_messages or not sniped_messages[channel_id]:
        embed = discord.Embed(
            title="âŒ No Deleted Messages",
            description="There are no recently deleted messages in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if page < 1 or page > len(sniped_messages[channel_id]):
        embed = discord.Embed(
            title="âš ï¸ Invalid Page Number",
            description=f"Page must be between 1 and {len(sniped_messages[channel_id])}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    snipe = sniped_messages[channel_id][-page]
    embed = discord.Embed(title="ðŸ”’ Moderator Snipe (Unfiltered)", color=discord.Color.dark_red())
    
    # Show unfiltered content
    content = snipe['content'] or "*No text content*"
    if snipe.get('has_offensive_content', False):
        embed.description = "âš ï¸ **Warning:** This message contains offensive content."
    
    embed.add_field(name="**Content:**", value=content, inline=False)
    embed.add_field(name="**Deleted by:**", value=snipe['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"SnipeBot MOD | Page {page} of {len(sniped_messages[channel_id])}")

    # Handle Tenor GIF URLs directly
    if snipe.get('tenor_gif_url'):
        embed.set_image(url=snipe['tenor_gif_url'])
    else:
        # Fall back to other media handling methods
        media_url = get_media_url(snipe['content'], snipe['attachments'])
        
        if media_url:
            if 'tenor.com/view/' in media_url:
                # For Tenor links not processed earlier, try to extract GIF now
                try:
                    gif_url = await tenor_handler.extract_gif_url(media_url)
                    if gif_url:
                        embed.set_image(url=gif_url)
                except Exception as e:
                    print(f"Error extracting Tenor GIF URL on display: {e}")
            else:
                # For non-Tenor media
                embed.set_image(url=media_url)
        elif snipe["attachments"]:
            for attachment in snipe["attachments"]:
                if hasattr(attachment, 'content_type') and attachment.content_type and attachment.content_type.startswith("image"):
                    embed.set_image(url=attachment.url)
                    break
                if hasattr(attachment, 'url') and attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    embed.set_image(url=attachment.url)
                    break

    await ctx.send(embed=embed)

@bot.command(aliases=["se"])
async def snipeedit(ctx, page: int = 1):
    channel_id = ctx.channel.id
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        embed = discord.Embed(
            title="âŒ No Edited Messages",
            description="There are no recently edited messages in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if page < 1 or page > len(edited_messages[channel_id]):
        embed = discord.Embed(
            title="âš ï¸ Invalid Page Number",
            description=f"Page must be between 1 and {len(edited_messages[channel_id])}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    edit = edited_messages[channel_id][-page]
    embed = discord.Embed(title="âœï¸ Edited Message", color=discord.Color.blue())
    
    # Filter content if it contains offensive words
    before_content = edit['before_content'] or "*No text content*"
    after_content = edit['after_content'] or "*No text content*"
    
    if edit.get('before_has_offensive_content', False):
        before_content = filter_content(before_content)
    
    if edit.get('after_has_offensive_content', False):
        after_content = filter_content(after_content)
    
    embed.add_field(name="**Before:**", value=before_content, inline=False)
    embed.add_field(name="**After:**", value=after_content, inline=False)
    embed.add_field(name="**Edited by:**", value=edit['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=edit['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"SnipeBot | Page {page} of {len(edited_messages[channel_id])}")
    
    # Handle Tenor GIF URLs directly
    if edit.get('tenor_gif_url'):
        embed.set_image(url=edit['tenor_gif_url'])
    else:
        # Fall back to other media handling methods
        media_url = get_media_url(edit['after_content'], edit['attachments'])
        
        if media_url:
            if 'tenor.com/view/' in media_url:
                # For Tenor links not processed earlier, try to extract GIF now
                try:
                    gif_url = await tenor_handler.extract_gif_url(media_url)
                    if gif_url:
                        embed.set_image(url=gif_url)
                except Exception as e:
                    print(f"Error extracting Tenor GIF URL on display: {e}")
            else:
                # For non-Tenor media
                embed.set_image(url=media_url)
        elif edit["attachments"]:
            for attachment in edit["attachments"]:
                if hasattr(attachment, 'content_type') and attachment.content_type and attachment.content_type.startswith("image"):
                    embed.set_image(url=attachment.url)
                    break
                if hasattr(attachment, 'url') and attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    embed.set_image(url=attachment.url)
                    break
    
    await ctx.send(embed=embed)

@bot.command()
@is_moderator()
async def snipeeditforce(ctx, page: int = 1):
    channel_id = ctx.channel.id
    if channel_id not in edited_messages or not edited_messages[channel_id]:
        embed = discord.Embed(
            title="âŒ No Edited Messages",
            description="There are no recently edited messages in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    if page < 1 or page > len(edited_messages[channel_id]):
        embed = discord.Embed(
            title="âš ï¸ Invalid Page Number",
            description=f"Page must be between 1 and {len(edited_messages[channel_id])}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    edit = edited_messages[channel_id][-page]
    embed = discord.Embed(title="ðŸ”’ Moderator Edit Snipe (Unfiltered)", color=discord.Color.dark_red())
    
    # Show unfiltered content
    before_content = edit['before_content'] or "*No text content*"
    after_content = edit['after_content'] or "*No text content*"
    
    has_offensive = edit.get('before_has_offensive_content', False) or edit.get('after_has_offensive_content', False)
    if has_offensive:
        embed.description = "âš ï¸ **Warning:** This message contains offensive content."
    
    embed.add_field(name="**Before:**", value=before_content, inline=False)
    embed.add_field(name="**After:**", value=after_content, inline=False)
    embed.add_field(name="**Edited by:**", value=edit['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=edit['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"SnipeBot MOD | Page {page} of {len(edited_messages[channel_id])}")
    
    # Handle Tenor GIF URLs directly
    if edit.get('tenor_gif_url'):
        embed.set_image(url=edit['tenor_gif_url'])
    else:
        # Fall back to other media handling methods
        media_url = get_media_url(edit['after_content'], edit['attachments'])
        
        if media_url:
            if 'tenor.com/view/' in media_url:
                # For Tenor links not processed earlier, try to extract GIF now
                try:
                    gif_url = await tenor_handler.extract_gif_url(media_url)
                    if gif_url:
                        embed.set_image(url=gif_url)
                except Exception as e:
                    print(f"Error extracting Tenor GIF URL on display: {e}")
            else:
                # For non-Tenor media
                embed.set_image(url=media_url)
        elif edit["attachments"]:
            for attachment in edit["attachments"]:
                if hasattr(attachment, 'content_type') and attachment.content_type and attachment.content_type.startswith("image"):
                    embed.set_image(url=attachment.url)
                    break
                if hasattr(attachment, 'url') and attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    embed.set_image(url=attachment.url)
                    break
    
    await ctx.send(embed=embed)

@bot.command()
@has_permission_or_is_admin()
@commands.has_permissions(moderate_members=True)
async def mess(ctx, member: discord.Member, *, message: str):
    try:
        await member.send(message)
        embed = discord.Embed(
            title="âœ… Message Sent",
            description=f"Message sent to {member.mention}.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="âŒ Failed to Send",
            description="Could not send DM. User may have DMs disabled.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command()
@has_permission_or_is_admin()
@commands.has_permissions(administrator=True)
async def reset(ctx):
    channel_id = ctx.channel.id
    sniped_reset = False
    edited_reset = False
    
    if channel_id in sniped_messages:
        sniped_messages[channel_id] = []
        sniped_reset = True
        
    if channel_id in edited_messages:
        edited_messages[channel_id] = []
        edited_reset = True
        
    if sniped_reset or edited_reset:
        embed = discord.Embed(
            title="ðŸ—‘ï¸ Reset Complete",
            description="Cleared sniped and edited messages in this channel.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            title="â„¹ï¸ Nothing to Reset",
            description="There were no sniped or edited messages to clear.",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

@bot.command()
@has_permission_or_is_admin()
@commands.has_permissions(manage_nicknames=True)
async def rename(ctx, member: discord.Member, *, nickname: str):
    try:
        old_nick = member.display_name
        await member.edit(nick=nickname)
        embed = discord.Embed(
            title="âœ… Nickname Changed",
            description=f"Changed {member.mention}'s nickname from '{old_nick}' to '{nickname}'.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="âŒ Failed",
            description="I don't have permission to change that user's nickname.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    except discord.HTTPException as e:
        embed = discord.Embed(
            title="âŒ Error",
            description=f"Failed to change nickname: {str(e)}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

@bot.command()
async def filter(ctx):
    embed = discord.Embed(
        title="ðŸ›¡ï¸ Content Filter Status",
        description="The content filter is active. Offensive words in sniped messages will be hidden with asterisks.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Moderator Commands",
        value="Moderators can use `snipeforce` and `snipeeditforce` to view unfiltered content.",
        inline=False
    )
    await ctx.send(embed=embed)

@bot.command(aliases=["h"])
async def help(ctx):
    embed = discord.Embed(
        title="â“ SnipeBot Help",
        description="Available commands:",
        color=discord.Color.blurple()
    )
    embed.add_field(name="`,snipe` or `/snipe [page]`", value="Show recently deleted messages with content filtering.", inline=False)
    embed.add_field(name="`,snipeforce` or `/snipeforce [page]`", value="Show unfiltered deleted messages (moderator only).", inline=False)
    embed.add_field(name="`,snipeedit` or `/snipeedit [page]`", value="Show edited messages with content filtering.", inline=False)
    embed.add_field(name="`,snipeeditforce` or `/snipeeditforce [page]`", value="Show unfiltered edited messages (moderator only).", inline=False)
    embed.add_field(name="`,mess @user [message]` or `/mess`", value="Send a DM to a user (requires timeout members permission).", inline=False)
    embed.add_field(name="`,rename @user [nickname]` or `/rename`", value="Change a user's nickname (requires manage nicknames permission).", inline=False)
    embed.add_field(name="`,reset` or `/reset`", value="Reset all sniped and edited messages (requires administrator permission).", inline=False)
    embed.add_field(name="`,filter` or `/filter`", value="Check content filter status.", inline=False)
    embed.add_field(name="`,help` or `/help`", value="Show this help message.", inline=False)
    embed.set_footer(text="SnipeBot by Werzzzy | Server owner and administrators bypass all permission requirements")
    await ctx.send(embed=embed)

# For error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You don't have the required permissions to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        # Ignore command not found errors
        pass
    else:
        # Log the error
        logger.error(f"Command error: {error}")

# Run the Flask server
run_flask()

# Run the bot (replace TOKEN with your actual Discord token)
if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("Error: No Discord token found in environment variables. Please set the DISCORD_TOKEN.")
    else:
        bot.run(token)
