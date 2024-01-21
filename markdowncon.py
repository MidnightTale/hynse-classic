import json
import aiohttp
import asyncio
import os

CACHE_DIR = 'cache'

async def get_username_from_uuid(session, uuid):
    cache_file = f'{CACHE_DIR}/{uuid}.json'

    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as cache_file:
                data = json.load(cache_file)
            return {'name': data.get('name', 'Unknown')}
        except Exception as e:
            print(f"Error loading cache file: {e}")
            return {'name': 'Unknown'}

    try:
        async with session.get(f'https://sessionserver.mojang.com/session/minecraft/profile/{uuid}', timeout=10) as response:
            response.raise_for_status()
            data = await response.json()

            if data is None or 'name' not in data:
                return {'name': 'Unknown'}

            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(cache_file, 'w', encoding='utf-8') as cache_file:
                json.dump(data, cache_file)

            return {'name': data['name']}
    except aiohttp.ClientError as e:
        print(f"Error fetching username: {e}")
        return {'name': 'Unknown'}



async def process_waystone(session, waystone):
    try:
        owner_uuid = waystone.get('owner', 'N/A')
        owner_data = await get_username_from_uuid(session, owner_uuid)
        if owner_data is None:
            print(f"Error getting data for waystone {waystone['id']}: owner_data is None")
            return ''

        owner_username = owner_data.get('name', 'Unknown')
        head_image_url = f'https://api.creepernation.net/head/{owner_uuid}'

        teleport_command = (
            f"/execute in minecraft:{waystone['pos']['world']} run tp @s "
            f"{waystone['pos']['x']} {waystone['pos']['y']} {waystone['pos']['z']}"
        )

        result = (
            f"## {waystone['name']}\n"
            f"![{owner_username}'s Head]({head_image_url})\n"
            f"- **ID:** {waystone['id']}\n"
            f"- **Owner (UUID):** {owner_uuid}\n"
            f"- **Owner (Username):** {owner_username}\n"
            f"- **Position:** {waystone['pos']['x']}, {waystone['pos']['y']}, {waystone['pos']['z']} ({waystone['pos']['world']})\n"
            f"- **RNG Block:** {waystone.get('rngBlock', 'N/A')}\n"
            f"```mcfunction\n{teleport_command}\n```\n\n"
        )

        await asyncio.sleep(1)  # Add a delay between requests
        return result
    except Exception as e:
        print(f"Error processing waystone {waystone['id']}: {e}")
        return ''


async def convert_to_markdown(waystones_data):
    markdown_content = "# Waystones\n\n"

    async with aiohttp.ClientSession() as session:
        tasks = []
        if waystones_data:
            for waystone in waystones_data:
                task = process_waystone(session, waystone)
                tasks.append(task)
                print(f"Converting waystone {waystone['id']}")

        results = await asyncio.gather(*tasks)

    markdown_content += ''.join(results)

    return markdown_content

try:
    with open(r'./waystones.json', 'r', encoding='utf-8') as json_file:
        waystones_data = json.load(json_file)

    loop = asyncio.get_event_loop()
    markdown_output = loop.run_until_complete(convert_to_markdown(waystones_data))

    with open('waystones.md', 'w', encoding='utf-8') as md_file:
        md_file.write(markdown_output)

    print("Conversion complete. Check 'waystones.md' for the output.")
except Exception as e:
    print(f"An error occurred: {e}")
