import discord
from discord.ext import commands
from discord.utils import get

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

# Set up the bot
bot = commands.Bot(command_prefix=",", intents=intents)
bot.remove_command('help')  # Remove default help command

# Sniped messages storage
sniped_messages = {}

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}!")
    await bot.change_presence(activity=discord.Game(name="Type ,help for commands"))

# Event to store deleted messages
@bot.event
async def on_message_delete(message):
    if message.author.bot:  # Ignore bot messages
        return
    sniped_messages[message.channel.id] = {
        "content": message.content,
        "author": message.author,
        "time": message.created_at
    }

# ,s or ,snipe command
@bot.command(aliases=["snipe"])
async def s(ctx, page: int = 1):
    channel_id = ctx.channel.id
    if channel_id not in sniped_messages:
        await ctx.send("No recently deleted messages in this channel.")
        return

    snipe = sniped_messages[channel_id]
    embed = discord.Embed(
        title="Sniped Message",
        description=f"**Content:** {snipe['content']}\n"
                    f"**Author:** {snipe['author']}\n"
                    f"**Time:** {snipe['time'].strftime('%Y-%m-%d %H:%M:%S')}",
        color=discord.Color.gold()
    )
    embed.set_footer(text="SnipeBot | Page 1 of 1")
    await ctx.send(embed=embed)

# ,mess command
@bot.command()
@commands.has_any_role("Moderator", "Administrator", "Helper")
async def mess(ctx, member: discord.Member, *, message):
    try:
        await member.send(message)
        await ctx.send(f"Message successfully sent to {member.mention}.")
    except discord.Forbidden:
        await ctx.send("Unable to send the message. The user might have DMs disabled.")

# ,re command
@bot.command()
@commands.has_any_role("Moderator", "Administrator")
async def re(ctx, member: discord.Member, *, new_nickname):
    try:
        await member.edit(nick=new_nickname)
        await ctx.send(f"{member.mention}'s nickname has been updated to **{new_nickname}**.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to change this user's nickname.")

# ,help command
@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="SnipeBot Commands",
        description="Here are the available commands for SnipeBot:",
        color=discord.Color.blurple()
    )
    embed.add_field(
        name=",s or ,snipe [page]",
        value="Displays deleted messages. If deleted by another user, shows the content. If deleted by the author, indicates 'Author deleted their own message.'\nExample: ,s 1, ,s 2",
        inline=False
    )
    embed.add_field(
        name=",mess @User [message]",
        value="DMs the specified message to the user. Only usable by Moderators, Administrators, or Helpers.\nExample: ,mess @User Please follow the rules.",
        inline=False
    )
    embed.add_field(
        name=",re @User [NewNickname]",
        value="Changes a user's nickname on the server. Only usable by Moderators or Administrators.\nExample: ,re @User NewNickname",
        inline=False
    )
    embed.add_field(
        name=",help",
        value="Displays this help message.",
        inline=False
    )
    embed.set_footer(text="SnipeBot | Premium Discord Bot")
    await ctx.send(embed=embed)

# Error handling for missing permissions
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("You don't have the required role to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Missing required argument. Use ,help for command usage.")
    elif isinstance(error, commands.CommandNotFound):
        await ctx.send("Unknown command. Use ,help to see the available commands.")
    else:
        raise error  # Raise other errors for debugging

# Run the bot
bot.run("MTM2MTYwODE4OTk3MTM5ODg0Ng.Gbpk7e.9p70KSOCFjIdlUI0DPCKlo1t5yaiKfreKq2MLE")  # Replace YOUR_BOT_TOKEN with your bot token
