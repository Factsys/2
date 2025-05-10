import discord
from discord.ext import commands
from discord import app_commands
import os
from flask import Flask
from threading import Thread
import re
import asyncio
import logging
import random
import time

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('snipebot')

# Flask app to keep the bot running on Render
app = Flask('')

@app.route('/')
def home():
    return "SnipeBot is running!"

def run_flask():
    port = int(os.getenv("PORT", 8080))
    server = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": port}, daemon=True)
    server.start()

# Enable intents
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

# Custom rate limit handling
class RateLimitHandler(discord.Client):
    async def on_error(self, event_method, *args, **kwargs):
        error = args[0] if args else None
        if isinstance(error, discord.errors.HTTPException) and error.status == 429:
            retry_after = error.retry_after
            logger.warning(f"Rate limited! Retrying after {retry_after} seconds")
            await asyncio.sleep(retry_after)
        else:
            await super().on_error(event_method, *args, **kwargs)

# Initialize bot with custom rate limit handling
class SnipeBot(commands.Bot):
    async def setup_hook(self):
        # Add rate limit retry logic
        self._connection.http._global_over = asyncio.Event()
        self._connection.http._global_over.set()
        
        # Override the regular request to handle rate limits better
        original_request = self._connection.http.request
        
        async def request_with_retry(*args, **kwargs):
            max_retries = 5
            backoff = 1
            
            for attempt in range(max_retries):
                try:
                    return await original_request(*args, **kwargs)
                except discord.errors.HTTPException as e:
                    if e.status == 429:
                        retry_after = e.retry_after + (random.random() * 0.5)  # Add jitter
                        logger.warning(f"Rate limited! Attempt {attempt+1}/{max_retries}, retrying after {retry_after:.2f}s")
                        await asyncio.sleep(retry_after)
                        # Exponential backoff
                        backoff = min(backoff * 2, 60)  # Cap at 60s
                    else:
                        raise
                
                # For non-429 network errors
                except Exception as e:
                    logger.error(f"Network error: {e}. Attempt {attempt+1}/{max_retries}, retrying after {backoff}s")
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)  # Cap at 60s
            
            # If we've exhausted retries, give up and log a more severe error
            logger.critical(f"Failed after {max_retries} attempts. Giving up on request: {args}")
            raise Exception(f"Failed after {max_retries} attempts")
        
        # Replace the request method with our custom version
        self._connection.http.request = request_with_retry

bot = SnipeBot(command_prefix=",", intents=intents)
bot.remove_command('help')
sniped_messages = {}

# Helper function to handle media URLs
def get_media_url(content, attachments):
    if not content:
        content = ""
        
    # Check for tenor links
    tenor_match = re.search(r'https?://(?:www\.)?tenor\.com/view/[^\s]+', content)
    if tenor_match:
        return tenor_match.group(0)
    
    # Check for Twitter/X GIF links
    twitter_match = re.search(r'https?://(?:www\.)?twitter\.com/[^\s]+\.gif', content)
    if twitter_match:
        return twitter_match.group(0)
    
    # Check for discord attachment links with .gif extension
    gif_match = re.search(r'https?://(?:cdn|media)\.discordapp\.(?:com|net)/[^\s]+\.gif[^\s]*', content)
    if gif_match:
        return gif_match.group(0)
    
    # Check for direct GIF links
    direct_gif_match = re.search(r'https?://[^\s]+\.gif[^\s]*', content)
    if direct_gif_match:
        return direct_gif_match.group(0)
    
    # If there are attachments, return the URL of the first one
    if attachments:
        return attachments[0].url
    
    return None

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
