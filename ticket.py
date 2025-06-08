import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import Button, View, Modal, TextInput

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

# Store role mappings
role_mappings = {}

class TicketModal(Modal):
    def __init__(self, ticket_type: str):
        super().__init__(title="Ticket Reason")
        self.ticket_type = ticket_type
        
        self.reason = TextInput(
            label="Why are you creating this ticket?",
            placeholder="Please explain your reason...",
            required=True,
            style=discord.TextStyle.paragraph
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        # Get the category
        category = interaction.guild.get_channel(1355771895806693426)
        
        # Create the ticket channel
        ticket_channel = await category.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
        )
        
        # Add role permissions if they exist
        if interaction.guild.id in role_mappings:
            role = interaction.guild.get_role(role_mappings[interaction.guild.id])
            if role:
                await ticket_channel.set_permissions(role, read_messages=True, send_messages=True)
        
        # Create the ticket embed
        embed = discord.Embed(
            title=f"Ticket: {self.ticket_type}",
            description=f"Created by {interaction.user.mention}\n\n**Reason:**\n{self.reason.value}",
            color=discord.Color.blue()
        )
        
        await ticket_channel.send(embed=embed)
        await interaction.response.send_message(f"Ticket created! Please check {ticket_channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Premium Question", style=discord.ButtonStyle.primary, emoji="🎟️")
    async def premium_question(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal("Premium Question"))

    @discord.ui.button(label="Macro Question", style=discord.ButtonStyle.primary, emoji="🎟️")
    async def macro_question(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(TicketModal("Macro Question"))

@bot.tree.command(name="cmr", description="Set the role that will have access to ticket channels")
@app_commands.describe(role="The role to give access to ticket channels")
async def set_ticket_role(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
        return
    
    role_mappings[interaction.guild.id] = role.id
    await interaction.response.send_message(f"Ticket role set to {role.mention}", ephemeral=True)

@bot.tree.command(name="ct", description="Create a ticket panel")
@app_commands.describe(channel="The channel to send the ticket panel to")
async def create_ticket_panel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("You don't have permission to use this command!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🎟️ Ticket System",
        description="Please choose an option below to create a ticket.",
        color=discord.Color.blue()
    )
    
    view = TicketView()
    await channel.send(embed=embed, view=view)
    await interaction.response.send_message("Ticket panel created!", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# Replace 'YOUR_BOT_TOKEN' with your actual bot token
bot.run('YOUR_BOT_TOKEN')
