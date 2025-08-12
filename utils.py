import logging
from pathlib import Path
from aiogram.types import Message
import aiofiles

logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


async def save_file(message: Message) -> str:
    """
    Сохраняет документ или фото в папку uploads.
    Возвращает путь к сохранённому файлу.
    """
    if message.document:
        # Документы
        file_id = message.document.file_id
        file_name = message.document.file_name
    elif message.photo:
        # Фото
        photo = message.photo[-1]  # самое большое
        file_id = photo.file_id
        file_name = f"{message.from_user.id}_{photo.file_unique_id}.jpg"
    else:
        raise ValueError("Сообщение не содержит документа или фото.")

    # Получаем файл
    file = await message.bot.get_file(file_id)
    file_stream = await message.bot.download_file(file.file_path)  # это BinaryIO

    # Сохраняем файл в uploads
    path = Path("uploads") / file_name
    path.parent.mkdir(exist_ok=True)

    async with aiofiles.open(path, "wb") as f:
        await f.write(file_stream.read())  # читаем напрямую из BinaryIO

    logging.info(f"Файл сохранён: {path}")
    return str(path)



