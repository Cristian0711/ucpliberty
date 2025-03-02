import discord
import bot.commands_body

from discord import app_commands
from bot.scraping_bot import ScrapingBot


def setup_commands(client: ScrapingBot):
    """Setup all bot commands."""

    @client.tree.command(name="scrape", description="Start the scraping process")
    async def scrape(interaction: discord.Interaction):
        await bot.commands_body.scrape_command(client, interaction)

    @client.tree.command(name="search", description="Get specific data like items or vehicles with a name")
    @app_commands.describe(param="The type of data to retrieve, example item or vehicle",
                           name="The name of the item or vehicle")
    @app_commands.choices(
        param=[
            discord.app_commands.Choice(name="item", value="item"),
            discord.app_commands.Choice(name="vehicle", value="vehicle"),
            discord.app_commands.Choice(name="player", value="player"),
        ]
    )
    async def search(interaction: discord.Interaction, param: str, name: str):
        await bot.commands_body.search_command(client, interaction, param, name)

    @client.tree.command(name="hello", description="Say hello to the bot")
    async def hello(interaction: discord.Interaction):
        await interaction.response.send_message(f"Hello, {interaction.user.mention}! 👋")
