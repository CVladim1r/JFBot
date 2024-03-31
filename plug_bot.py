import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher.filters import Text
from random import randint
from config import TOKEN_PLUG

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN_PLUG)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

async def send_with_interval(message: types.Message, text: str, delay: int = 1):
    for line in text.split('\n\n'):
        await asyncio.sleep(delay)
        await message.answer(line)

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton(text="Что будет уметь бот?")
    markup.add(button)

    # Отправляем приветственное сообщение с интервалом
    await send_with_interval(
        message,
        "Привет, спасибо, что перешел по ссылке, мы рады каждому! ❤️\n\n"
        "Данный бот пока находится на этапе разработки, но через неделю, ты сможешь воспользоваться его функционалом!\n\n"
        "Мы обязательно отправим тебе уведомление, когда бот начнет свою работу 😊",
    )

@dp.message_handler(Text(equals="Что будет уметь бот?"))
async def send_description(message: types.Message):
    await send_with_interval(
        message,
        "В этом боте, сойдутся две стороны, которые постоянно ищут друг друга: соискатель и работодатель. 🌚🌝\n\n"
        "Соискатель - 🌚, сможет составить резюме и смотреть вакансии от работодателей.\n\n"
        "Работодатель - 🌝, сможет размещать вакансии, а также просматривать резюме от соискателей.\n\n"
        "Просматривая резюме или вакансии, ты сможешь отмечать в 👍 понравившиеся тебе и 👎, если тебе что-то не понравилось.\n\n"
        "А теперь, осталось ждать, когда произойдет тот самый ⚡ мэтч ⚡\n\n"
        "(Спасибо вам за оказанное доверие, если вы желаете, чтоб проект был закончен скорее, то у вас есть возможность финансовой помощи)",
        1
    )

@dp.message_handler(commands=['info'])
async def send_description_info(message: types.Message):
    await send_with_interval(
        message,
        "В этом боте, сойдутся две стороны, которые постоянно ищут друг друга: соискатель и работодатель. 🌚🌝\n\n"
        "Соискатель - 🌚, сможет составить резюме и смотреть вакансии от работодателей.\n\n"
        "Работодатель - 🌝, сможет размещать вакансии, а также просматривать резюме от соискателей.\n\n"
        "Просматривая резюме или вакансии, ты сможешь отмечать в 👍 понравившиеся тебе и 👎, если тебе что-то не понравилось.\n\n"
        "А теперь, осталось ждать, когда произойдет тот самый ⚡ мэтч ⚡\n\n"
        "(Спасибо вам за оказанное доверие, если вы желаете, чтоб проект был закончен скорее, то у вас есть возможность финансовой помощи)",
        1
    )
    
if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(dp, skip_updates=True)