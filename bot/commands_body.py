import discord
from reactionmenu import ViewMenu, ViewSelect, ViewButton
from typing import List, Dict, Optional
from datetime import datetime


async def scrape_command(client, interaction: discord.Interaction) -> None:
    try:
        await interaction.response.defer()

        if not client.scraper:
            raise ValueError("Scraper not initialized")

        await client.scraper.scrape_all_players()
        await interaction.followup.send("Scraping completed successfully! 🕸️")

    except Exception as e:
        client.logger.error(f"Scraping failed: {e}")
        await interaction.followup.send(f"Scraping failed: {str(e)}")


def create_inventory_pages(player_data, player_name: str) -> List[discord.Embed]:
    """Create inventory pages for the menu."""
    pages = []

    # Main info embed
    main_embed = discord.Embed(
        title=f"📦 Inventory for {player_name}",
        color=discord.Color.blue()
    )
    main_embed.add_field(
        name="Last Updated",
        value=player_data.last_updated,
        inline=False
    )

    # Items embed(s)
    if player_data.items:
        items_per_page = 15
        sorted_items = sorted(
            player_data.items.values(),
            key=lambda x: (-x.count, x.name)
        )

        for i in range(0, len(sorted_items), items_per_page):
            items_chunk = sorted_items[i:i + items_per_page]
            embed = discord.Embed(
                title=f"📦 Items for {player_name}",
                color=discord.Color.blue()
            )

            for item in items_chunk:
                embed.add_field(
                    name=item.name,
                    value=f"Quantity: {item.count}",
                    inline=True
                )
            pages.append(embed)

    # Vehicles embed
    if player_data.vehicles:
        vehicles_embed = discord.Embed(
            title=f"🚗 Vehicles for {player_name}",
            color=discord.Color.green()
        )

        for vehicle in sorted(player_data.vehicles, key=lambda x: x.name):
            vehicles_embed.add_field(
                name=vehicle.name,
                value=f"Model Hash: {vehicle.model_hash}",
                inline=True
            )
        pages.append(vehicles_embed)

    return [main_embed] + pages


async def search_command_items_or_vehicles(client, interaction: discord.Interaction, param: str, name: str) -> None:
    menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)

    if param == "item":
        users_with_quantity = client.players_cache.find_users_with_item(name)
        embed_title = f"📦 Users with Item: {name}"
        embed_color = discord.Color.blue()
    else:  # vehicle
        users_with_quantity = client.players_cache.find_users_with_vehicle(name)
        embed_title = f"🚗 Users with Vehicle: {name}"
        embed_color = discord.Color.green()

    if not users_with_quantity:
        embed = discord.Embed(
            title=embed_title,
            description=f"❌ No users have the {param} '{name}'.",
            color=embed_color
        )
        await interaction.followup.send(embed=embed)
        return

    users_per_page = 15
    max_pages = 25  # Maximum pages allowed for the "Go to page..." dropdown
    total_pages = (len(users_with_quantity) + users_per_page - 1) // users_per_page  # Calculate total pages
    total_pages = min(total_pages, max_pages)

    sorted_users = sorted(
        users_with_quantity.items(),
        key=lambda x: (-x[1], x[0])  # Sort by quantity descending, then name ascending
    )

    for i in range(total_pages):
        start = i * users_per_page
        end = start + users_per_page
        users_chunk = sorted_users[start:end]

        embed = discord.Embed(
            title=embed_title,
            color=embed_color
        )

        for user, quantity in users_chunk:
            embed.add_field(
                name=user,
                value=f"Quantity: {quantity}",
                inline=True
            )

        menu.add_page(embed)

    # Add dropdown with limited options for "Go to page..."
    if total_pages > 1:
        menu.add_go_to_select(ViewSelect.GoTo(title="Go to page...", page_numbers=list(range(1, total_pages + 1))))
    menu.add_button(ViewButton.back())
    menu.add_button(ViewButton.next())
    await menu.start()


async def search_command_player(client: discord.Client, interaction: discord.Interaction, name: str) -> None:
    player_data = client.players_cache.get_player_inventory_as_string(name)

    if not player_data:
        embed = discord.Embed(
            title="Player Not Found",
            description=f"❌ Player '{name}' not found in database.",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=embed)
        return

    menu = ViewMenu(interaction, menu_type=ViewMenu.TypeEmbed)

    # Create and add all inventory pages
    pages = create_inventory_pages(player_data, name)
    for page in pages:
        menu.add_page(page)

    # Add navigation buttons
    menu.add_button(ViewButton.back())
    menu.add_button(ViewButton.next())
    if len(pages) > 2:
        menu.add_go_to_select(ViewSelect.GoTo(title="Go to page...", page_numbers=...))

    await menu.start()


async def search_command(client, interaction: discord.Interaction, param: str, name: str) -> None:
    try:
        await interaction.response.defer()

        if param == "player":
            await search_command_player(client, interaction, name)
        elif param in ["item", "vehicle"]:
            await search_command_items_or_vehicles(client, interaction, param, name)
        else:
            embed = discord.Embed(
                title="Invalid Parameter",
                description="❌ Use 'item', 'vehicle', or 'player' as the parameter.",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    except Exception as e:
        error_embed = discord.Embed(
            title="Error",
            description=f"❌ Command failed: {str(e)}",
            color=discord.Color.red()
        )
        client.logger.error(f"Command failed: {e}")
        await interaction.followup.send(embed=error_embed)