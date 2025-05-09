import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# Flask app to keep the bot running on Render
app = Flask('')

@app.route('/')
def home():
    return "SnipeBot is running!"

def run_flask():
    port = os.getenv("PORT", 8080)
    server = Thread(target=app.run, kwargs={"host": "0.0.0.0", "port": port}, daemon=True)
    server.start()

# Enable intents for bot functionality
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

# Initialize bot
bot = commands.Bot(command_prefix=",", intents=intents)
bot.remove_command('help')  # Remove default help command

# Store sniped messages (supporting multiple pages)
sniped_messages = {}

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}!")
    await bot.change_presence(activity=discord.Game(name="Type ,help for commands"))

# Event to capture deleted messages
@bot.event
async def on_message_delete(message):
    if message.author.bot:  # Ignore bot messages
        return

    # Store the deleted message in the channel's sniped messages list
    if message.channel.id not in sniped_messages:
        sniped_messages[message.channel.id] = []
    
    sniped_messages[message.channel.id].append({
        "content": message.content,
        "author": message.author,
        "attachments": message.attachments,
        "time": message.created_at
    })

    # Keep only the last 10 sniped messages per channel
    if len(sniped_messages[message.channel.id]) > 10:
        sniped_messages[message.channel.id].pop(0)

# Command to snipe deleted messages
@bot.command(aliases=["snipe"])
async def s(ctx, page: int = 1):
    channel_id = ctx.channel.id
    if channel_id not in sniped_messages or len(sniped_messages[channel_id]) == 0:
        embed = discord.Embed(
            title="❌ No Deleted Messages",
            description="There are no recently deleted messages in this channel.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    # Ensure the requested page is within range
    if page < 1 or page > len(sniped_messages[channel_id]):
        embed = discord.Embed(
            title="⚠️ Invalid Page Number",
            description=f"Please provide a valid page number between 1 and {len(sniped_messages[channel_id])}.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return

    # Get the sniped message for the requested page
    snipe = sniped_messages[channel_id][-page]  # Use negative indexing for easier pagination
    embed = discord.Embed(
        title="📜 Sniped Message",
        color=discord.Color.gold()
    )
    embed.add_field(name="**Content:**", value=snipe['content'] if snipe['content'] else "*No text content*", inline=False)
    embed.add_field(name="**Deleted by:**", value=snipe['author'].mention, inline=True)
    embed.add_field(name="**Time:**", value=snipe['time'].strftime('%Y-%m-%d %H:%M:%S'), inline=True)
    embed.set_footer(text=f"SnipeBot | Page {page} of {len(sniped_messages[channel_id])}")

    # Check for attachments (images or GIFs) and embed them
    if snipe["attachments"]:
        for attachment in snipe["attachments"]:
            if any(attachment.url.endswith(ext) for ext in ["png", "jpg", "jpeg", "gif", "webp"]):
                embed.set_image(url=attachment.url)  # Display the image or GIF visually
                break  # Only show the first valid attachment

    await ctx.send(embed=embed)

# Command to DM a user (now checks for "Manage Server" permission)
@bot.command()
@commands.has_permissions(manage_guild=True)
async def mess(ctx, member: discord.Member, *, message):
    try:
        await member.send(message)
        embed = discord.Embed(
            title="✅ Message Sent",
            description=f"Your message was successfully sent to {member.mention}.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Message Failed",
            description="Unable to send the message. The user might have DMs disabled.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# Command to change a user's nickname
@bot.command()
@commands.has_permissions(manage_nicknames=True)
async def re(ctx, member: discord.Member, *, new_nickname):
    try:
        await member.edit(nick=new_nickname)
        embed = discord.Embed(
            title="✅ Nickname Changed",
            description=f"{member.mention}'s nickname has been updated to **{new_nickname}**.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    except discord.Forbidden:
        embed = discord.Embed(
            title="❌ Permission Denied",
            description="I don't have permission to change this user's nickname.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

# Help command
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="❓ SnipeBot Help",
        description="Here are the available commands for SnipeBot:",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name="`,s` or `,snipe [page]`",
        value="Displays recently deleted messages. Use pages to navigate through multiple deleted messages.\nExample: `,s 1`, `,s 2`",
        inline=False
    )
    embed.add_field(
        name="`,mess @User [message]`",
        value="DMs the specified message to the user. Requires the 'Manage Server' permission.\nExample: `,mess @User Please follow the rules.`",
        inline=False
    )
    embed.add_field(
        name="`,re @User [NewNickname]`",
        value="Changes a user's nickname on the server. Requires the 'Manage Nicknames' permission.\nExample: `,re @User NewNickname`",
        inline=False
    )
    embed.add_field(
        name="`,help`",
        value="Displays this help message.",
        inline=False
    )
    embed.set_footer(text="SnipeBot | Premium Discord Bot")
    await ctx.send(embed=embed)

# Error handling for missing permissions
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description="You don't have the required permissions to use this command.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title="⚠️ Missing Argument",
            description="You're missing a required argument. Use `,help` for command usage.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    elif isinstance(error, commands.CommandNotFound):
        embed = discord.Embed(
            title="❓ Unknown Command",
            description="This command does not exist. Use `,help` to see the available commands.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
    else:
        raise error  # Raise other errors for debugging

# Run Flask and the bot
if __name__ == "__main__":
    run_flask()  # Start the Flask server for Render
    bot.run(os.getenv("DISCORD_TOKEN"))  # Use the token from environment variables
