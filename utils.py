import logging
from pathlib import Path
from aiogram.types import Message
import aiofiles

logging.basicConfig(filename='bot.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def save_file(message: Message) -> str:
    file_id = message.document.file_id
    file_name = message.document.file_name
    file = await message.bot.get_file(file_id)
    file_bytes = await message.bot.download_file(file.file_path)

    path = Path("uploads") / file_name
    path.parent.mkdir(exist_ok=True)

    async with aiofiles.open(path, "wb") as f:
        await f.write(file_bytes.read())

    return str(path)

