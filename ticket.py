import discord
from discord import app_commands
from discord.ext import commands
import os

# Store the support role for tickets per guild
support_roles = {}

class TicketTypeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(label="🎟️ Please choose an option", style=discord.ButtonStyle.primary, custom_id="ticket_choose")
    async def choose_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            view=TicketOptionSelectView(),
            ephemeral=True
        )

class TicketOptionSelectView(discord.ui.View):
    @discord.ui.select(
        placeholder="Select ticket type...",
        options=[
            discord.SelectOption(label="Premium Question", value="premium", emoji="💎"),
            discord.SelectOption(label="Macro Question", value="macro", emoji="📝")
        ],
        custom_id="ticket_type_select"
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.Select):
        ticket_type = select.values[0]
        await interaction.response.send_modal(TicketReasonModal(ticket_type))

class TicketReasonModal(discord.ui.Modal, title="Ticket Reason"):
    def __init__(self, ticket_type):
        super().__init__()
        self.ticket_type = ticket_type
    reason = discord.ui.TextInput(
        label="Why are you creating this ticket?",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )
    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        category_id = 1355771895806693426
        category = guild.get_channel(category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message("❌ Ticket category not found.", ephemeral=True)
            return
        support_role_id = support_roles.get(guild.id)
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        }
        if support_role_id:
            support_role = guild.get_role(support_role_id)
            if support_role:
                overwrites[support_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)
        channel_name = f"ticket-{user.name.lower()}"
        ticket_channel = await guild.create_text_channel(
            channel_name,
            category=category,
            overwrites=overwrites,
            topic=f"{user} | {self.ticket_type.title()} | {self.reason.value}"
        )
        embed = discord.Embed(
            title=f"{self.ticket_type.title()} Ticket",
            description=f"**User:** {user.mention}\n**Reason:** {self.reason.value}",
            color=discord.Color.green()
        )
        await ticket_channel.send(content=f"{user.mention}", embed=embed)
        await interaction.response.send_message(f"✅ Ticket created: {ticket_channel.mention}", ephemeral=True)

def setup_ticket_commands(bot):
    @bot.tree.command(name="cmr", description="Set the support role for tickets")
    @app_commands.describe(role="Role to give access to tickets")
    async def cmr_slash(interaction: discord.Interaction, role: discord.Role):
        support_roles[interaction.guild.id] = role.id
        await interaction.response.send_message(f"✅ Set support role for tickets: {role.mention}", ephemeral=True)

    @bot.tree.command(name="ct", description="Create a ticket embed with button")
    async def ct_slash(interaction: discord.Interaction, channel: discord.TextChannel = None):
        target_channel = channel or interaction.channel
        embed = discord.Embed(
            title="Ticket System",
            description="Click the button below to create a ticket.",
            color=discord.Color.blurple()
        )
        await target_channel.send(embed=embed, view=TicketTypeView())
        await interaction.response.send_message("✅ Ticket panel sent!", ephemeral=True)
