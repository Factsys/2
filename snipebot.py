import discord
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=",", intents=intents)

snipes = {}

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_message_delete(message):
    if message.author.bot:
        return

    snipes[message.channel.id] = {
        "content": message.content,
        "author": message.author,
        "attachments": message.attachments,
        "time": message.created_at,
    }

@bot.command()
async def s(ctx):
    snipe = snipes.get(ctx.channel.id)
    if not snipe:
        return await ctx.send("There is nothing to snipe!")

    embed = discord.Embed(
        title="📜 Sniped Message",
        description=f"**Content:**\n{snipe['content'] or '*No text content*'}",
        color=discord.Color.gold(),
    )
    embed.add_field(name="Deleted by:", value=snipe["author"].mention, inline=True)
    embed.add_field(name="Time:", value=snipe["time"].strftime("%Y-%m-%d %H:%M:%S"), inline=True)

    image_url = None

    # Try attachments first
    if snipe["attachments"]:
        for attachment in snipe["attachments"]:
            if attachment.content_type and attachment.content_type.startswith("image"):
                image_url = attachment.url
                break
            if attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                image_url = attachment.url
                break

    # Fallback: Check content for image links
    if not image_url and snipe["content"]:
        if any(domain in snipe["content"] for domain in ["tenor.com", "giphy.com", ".gif"]):
            image_url = snipe["content"]

    if image_url:
        embed.set_image(url=image_url)

    await ctx.send(embed=embed)

@bot.tree.command(name="snipe", description="Show the last deleted message in the channel")
async def snipe_slash(interaction: discord.Interaction):
    snipe = snipes.get(interaction.channel.id)
    if not snipe:
        return await interaction.response.send_message("There is nothing to snipe!", ephemeral=True)

    embed = discord.Embed(
        title="📜 Sniped Message",
        description=f"**Content:**\n{snipe['content'] or '*No text content*'}",
        color=discord.Color.gold(),
    )
    embed.add_field(name="Deleted by:", value=snipe["author"].mention, inline=True)
    embed.add_field(name="Time:", value=snipe["time"].strftime("%Y-%m-%d %H:%M:%S"), inline=True)

    image_url = None

    # Try attachments first
    if snipe["attachments"]:
        for attachment in snipe["attachments"]:
            if attachment.content_type and attachment.content_type.startswith("image"):
                image_url = attachment.url
                break
            if attachment.url.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                image_url = attachment.url
                break

    # Fallback: Check content for image links
    if not image_url and snipe["content"]:
        if any(domain in snipe["content"] for domain in ["tenor.com", "giphy.com", ".gif"]):
            image_url = snipe["content"]

    if image_url:
        embed.set_image(url=image_url)

    await interaction.response.send_message(embed=embed)

bot.run("YOUR_TOKEN")
