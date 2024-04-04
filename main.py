import logging
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from bot.user_registration import register_job_seeker, register_employer

from keyboards import get_position_keyboard, get_yes_no_keyboard, get_save_restart_keyboard

from database.db_connector import update_user_citizenship, update_user_experience_details, update_user_fullname, update_user_desired_position, update_user_experience, update_user_skills, send_resume, update_user_citizenship, get_user_data, get_employer_data, update_user_location, add_user_info_to_db, update_user_age, update_user_description, update_user_name
from database.db_connector import add_user_to_db_type_user, add_user_to_db_type_employer
from config import TOKEN

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

class UserForm(StatesGroup):
    nickname = State()
    regStart = State()
    age = State()
    description = State()
    company_name = State()
    location = State()
    fullname = State() 
    citizenship = State()
    desired_position = State()
    work_experience = State()
    experience_details = State()
    experience_another = State()
    resume_check = State()
    resume_confirmation = State()
    resume_start = State()
    skills = State()
    resume_edit = State()

@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.username
    name = ""
    user = message.from_user.first_name if not message.from_user.username else message.from_user.username
    
    if not user_name:
        user_name = str(user_id)
        
    user_data = await get_user_data(user_id)
    employer_data = await get_employer_data(user_id)

    if employer_data:
        name = employer_data.get("name")
        await main_menu_employer(message.from_user.id, message.message_id)

        return
    elif user_data:
        name = user_data.get("name")
        user_type = user_data.get("user_type")
        if user_type == "USER":
            await main_menu_user(message.from_user.id, message.message_id)
            return
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Соискатель", callback_data="job_seeker"))
    keyboard.add(InlineKeyboardButton("Работодатель", callback_data="employer"))
    await bot.send_message(message.chat.id, '''Привет я кот Миша.\n
Я выполняю здесь самую главную функцию: помогаю соискателям и работодателям найти друг друга. 
Представь, у каждого есть работа, а в мире царит гармония – мяу, красота. Для этого я здесь.''')
    await asyncio.sleep(5)
    await message.answer("Давай теперь познакомимся поближе. Кто ты?", reply_markup=keyboard)
    await UserForm.next()

async def main_menu_user(user_id, message_id):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔍 Искать Вакансии"))
    keyboard.add(KeyboardButton("👤 Личный кабинет"))
    keyboard.add(KeyboardButton("✏️ Редактировать резюме"))
    keyboard.add(KeyboardButton("ℹ️ О боте"))

    main_text = "Искать вакансии:\n"
    main_text += "Личный кабинет\n"
    main_text += "Редактировать резюме\n"
    main_text += "О боте\n"

    await bot.send_message(user_id, main_text, reply_markup=keyboard)


async def main_menu_employer(user_id):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔍 Опубликовать вакансию"))
    keyboard.add(KeyboardButton("👤 Информация о компании"))
    keyboard.add(KeyboardButton("ℹ️ О боте"))

    main_text = "Искать вакансии:\n"
    main_text += "Личный кабинет\n"
    main_text += "Редактировать резюме\n"
    main_text += "О боте\n"

    await bot.send_message(user_id, f"{main_text}", reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data in ["job_seeker", "employer"], state="*")
async def process_user_type(callback_query: types.CallbackQuery, state: FSMContext):
    user_type = callback_query.data
    user_id = callback_query.from_user.id
    
    employer_id = callback_query.from_user.id
    employer_username = callback_query.from_user.username

    user = callback_query.from_user.first_name if not callback_query.from_user.full_name else callback_query.from_user.username
    user_name = callback_query.from_user.username
    
    await state.update_data(user_type=user_type)

    if user_type == "job_seeker":
        await add_user_to_db_type_user(callback_query.message, user_id, user, user_name, None)
        await register_job_seeker(callback_query.message, callback_query.from_user.id, callback_query.from_user.username, callback_query.from_user.username)
        await callback_query.message.answer("Давай создадим резюме. Напиши свой возраст:")
        await UserForm.regStart.set()

    elif user_type == "employer":
        await add_user_to_db_type_employer(callback_query.message, employer_id, employer_username, user, None)
        await register_employer(callback_query.message, callback_query.from_user.id, callback_query.from_user.username, callback_query.from_user.username)
        await callback_query.message.answer("Спасибо за регистрацию.")
        await main_menu_employer(callback_query.message.from_user.id, callback_query.message.message_id)
        
    await UserForm.next()






@dp.message_handler(state=UserForm.age)
async def process_age(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if not message.text.isdigit() or not (0 < int(message.text) < 99):
            await message.answer("Неверный формат возраста. Пожалуйста, введите возраст цифрами. Пример: 18")
            return
        data['age'] = message.text
    await update_user_age(message.from_user.id, data['age'])
    await UserForm.location.set()
    await message.answer("Какой ваш город?")
    await message.answer("Выберите город из списка:", reply_markup=await get_location_keyboard())

async def get_location_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("Санкт-Петербург", callback_data="location_spb"),
        InlineKeyboardButton("Москва", callback_data="location_moscow"),
        InlineKeyboardButton("Сочи", callback_data="location_sochi")
    )
    return keyboard

@dp.callback_query_handler(lambda query: query.data.startswith('location_'), state=UserForm.location)
async def process_location(callback_query: types.CallbackQuery, state: FSMContext):
    location = callback_query.data.split('_')[1]  # Разбиваем и в базу записывается только spb / moscow / sochi
    async with state.proxy() as data:
        data['location'] = location
    await update_user_location(callback_query.from_user.id, location)
    await UserForm.nickname.set()
    await callback_query.message.answer("Как к тебе обращаться?")

@dp.message_handler(state=UserForm.nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['nickname'] = message.text
    await update_user_name(message.from_user.id, data['nickname'])
    await UserForm.description.set()
    await message.answer("Напиши краткое описание о себе.")

@dp.message_handler(state=UserForm.description)
async def process_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    await update_user_description(message.from_user.id, data['description'])
    await add_user_info_to_db(message.from_user.id, data.get('nickname'), data.get('age'), data.get('description'))
    await message.answer("А теперь давай продолжим составление резюме...")
    await message.answer("Напиши ФИО:")
    await UserForm.resume_start.set()
    await UserForm.fullname.set()


@dp.message_handler(state=UserForm.fullname)
async def resume_start(message: types.Message, state: FSMContext):
    await message.answer("Напиши ФИО:")
    async with state.proxy() as data:
        data['fullname'] = message.text
    await update_user_fullname(message.from_user.id, data['fullname'])
    await message.answer("Какая у вас национальность?")
    await UserForm.citizenship.set()

# Шаг 3: Ответ на вопрос о национальности
@dp.message_handler(state=UserForm.citizenship)
async def citizenship(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['citizenship'] = message.text
    await update_user_citizenship(message.from_user.id, data['citizenship'])
    await message.answer("Кем бы вы хотели работать?", reply_markup=await get_position_keyboard())
    await UserForm.desired_position.set()


# Шаг 6: Выбор желаемой позиции
@dp.message_handler(state=UserForm.desired_position)
async def process_desired_position(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['desired_position'] = message.text
    await update_user_desired_position(message.from_user.id, data['desired_position'])
    await UserForm.work_experience.set()
    await message.answer("У вас есть опыт работы?", reply_markup=await get_yes_no_keyboard())

# Шаг 6.1: Если есть опыт работы
@dp.message_handler(lambda message: message.text.lower() == 'да', state=UserForm.work_experience)
async def process_experience_yes(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['experience'] = []
    await UserForm.experience_details.set()
    await message.answer("Отлично! Расскажите о своем опыте работы. Напишите название предыдущего места работы.")
    
# Шаг 6.2: Если нет опыта работы
@dp.message_handler(lambda message: message.text.lower() == 'нет', state=UserForm.work_experience)
async def process_experience_no(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['experience'] = "Нет опыта работы"
    await update_user_experience(message.from_user.id, data['experience'])
    await UserForm.skills.set()
    await message.answer("Какими навыками вы обладаете?")

# Продолжение для описания опыта работы
@dp.message_handler(state=UserForm.experience_details)
async def process_experience_details(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['experience'].append(message.text)
    await message.answer("Есть ли еще места работы, о которых вы хотите рассказать?", reply_markup=await get_yes_no_keyboard())
    await UserForm.experience_another.set()

# Повторяющиеся вопросы, если есть другой опыт работы
@dp.message_handler(lambda message: message.text.lower() == 'да', state=UserForm.experience_another)
async def process_experience_another_yes(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['experience_details'] = []
    await UserForm.experience_details.set()
    await message.answer("Как называлось ваше предыдущее место работы?")

@dp.message_handler(lambda message: message.text.lower() == 'нет', state=UserForm.experience_another)
async def process_experience_another_no(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['experience'] = '\n'.join(data['experience'])
    await update_user_experience_details(message.from_user.id, data['experience'])
    await UserForm.skills.set()
    await message.answer("Какими навыками вы обладаете?")
    
@dp.message_handler(state=UserForm.skills)
async def process_skills(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['skills'] = message.text

    resume = f"Имя: {data['fullname']}\n" \
                     f"Гражданство: {data['citizenship']}\n" \
                     f"Желаемая позиция: {data['desired_position']}\n" \
                     f"Опыт работы: {data.get('experience')}\n" \
                     f"Навыки: {data.get('skills')}"
    await update_user_skills(message.from_user.id, data['skills'])
    await message.answer(f"Ваше резюме:\n{resume}", reply_markup=await get_yes_no_keyboard())

    await state.update_data(experience=data.get('experience'), skills=data.get('skills'))
    await UserForm.fullname.set()
    
    await process_resume_check(message, state)  # Добавлен переход на process_resume_check


# Проверка резюме и возможность перезаполнения
@dp.message_handler(state=UserForm.resume_check)
async def process_resume_check(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.text.lower() in ['да', 'save_resume', 'сохранить', '/save_resume', 'Сохранить']:
            resume = f"Имя: {data['fullname']}\n" \
                     f"Гражданство: {data['citizenship']}\n" \
                     f"Желаемая позиция: {data['desired_position']}\n" \
                     f"Опыт работы: {data.get('experience')}\n" \
                     f"Навыки: {data.get('skills')}"
            await message.answer(f"Ваше резюме:\n{resume}", reply_markup=await get_yes_no_keyboard())
            await main_menu_user(message.from_user.id, message.message_id)
            await UserForm.resume_confirmation.set()
        else:
            await message.answer("Желаете что-нибудь подправить или начать заново?", reply_markup=await get_save_restart_keyboard())
            await UserForm.resume_edit.set()

# Отправка резюме
@dp.message_handler(state=UserForm.resume_confirmation)
async def process_resume_confirmation(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.text.lower() == 'да':
            await send_resume(message.from_user.id, data)
            await message.answer("Резюме успешно отправлено!")
            await main_menu_user(message.from_user.id, message.message_id)
        else:
            await message.answer("Хорошо, давайте перезаполним резюме.")
            await resume_start(message=message, state=state)
    await state.finish()

@dp.message_handler(state=UserForm.resume_edit)
async def process_resume_edit(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.text.lower() == 'да':
            await resume_start(message=message, state=state)
        else:
            await message.answer("Хорошо, оставляем как есть.")
    await state.finish()

@dp.message_handler(state=[UserForm.resume_confirmation, UserForm.resume_edit])
async def process_invalid_input(message: types.Message):
    await message.answer("Пожалуйста, введите 'да' или 'нет'.")




@dp.message_handler(lambda message: message.text == "ℹ️ О боте", state="*")
async def about_bot(message: types.Message):
    about_text = "Данный бот был создан для помощи компаниям в сфере общепита быстрее найти работников."
    await message.answer(about_text)

@dp.message_handler(lambda message: message.text == "👤 Личный кабинет", state="*")
async def personal_cabinet(message: types.Message):
    user_id = message.from_user.id

    user_data = await get_user_data(user_id)

    if user_data:
        name = user_data.get("name")
        age = user_data.get("age")
        description = user_data.get("description")
        location = user_data.get("location")
        user_type = user_data.get("user_type")

        if user_type == "USER":
            status = "Ищущий работу"
        else:
            status = "Работодатель"

        user_info_text = f"Имя: {name}\nВозраст: {age}\nОписание: {description}\nМестоположение: {location}\nСтатус: {status}"

        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add(KeyboardButton("Заполнить анкету заново"))
        keyboard.add(KeyboardButton("Изменить описание"))
        keyboard.add(KeyboardButton("Смотреть вакансии"))
        keyboard.add(KeyboardButton("Назад"))

        await message.answer(user_info_text, reply_markup=keyboard)
    else:
        await message.answer("Информация о пользователе не найдена.")

@dp.message_handler(lambda message: message.text == "Назад", state="*")
async def back_to_main_menu(message: types.Message):
    user_id = message.from_user.id

    user_data = await get_user_data(user_id)

    if user_data:
        name = user_data.get("name")
        await main_menu_user(user_id, name)
    else:
        await message.answer("Информация о пользователе не найдена. Пройдите регистрацию нажав на команду /start")



# Команды доступные для любого типа пользователя
@dp.message_handler(commands=['help'], state="*")
async def help_command(message: types.Message):
    help_text = "Список доступных команд:\n"
    help_text += "/start - Начать диалог с ботом\n"
    help_text += "/help - Получить список доступных команд\n"
    help_text += "Личный кабинет - Просмотреть информацию о пользователе\n"
    help_text += "Искать Вакансии - Поиск вакансий\n"
    help_text += "Редактировать резюме - Изменить информацию о себе\n"
    help_text += "О боте - Информация о боте\n"

    await message.answer(help_text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
