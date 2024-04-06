import logging
import asyncio
import json
from random import uniform

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ParseMode
from aiogram.dispatcher.filters import Text

from bot.user_registration import register_job_seeker, register_employer
from bot.keyboards import get_position_keyboard, get_yes_no_keyboard, get_save_restart_keyboard, get_choose_rule, get_choose_menu_employer_buttons, get_choose_menu_user_buttons, get_location_keyboard, get_resume_button, get_citizenship_keyboard, get_send_or_dislike_resume_keyboard
from bot.cities import CITIES
from bot.format_data import format_vacancy

from database.db_connector import update_user_citizenship, update_user_fullname, update_user_desired_position, update_user_experience, update_user_skills, send_resume, update_user_citizenship, get_user_data, get_employer_data, update_user_location, add_user_info_to_db, update_user_age, update_user_description, update_user_name
from database.db_connector import add_user_to_db_type_user, add_user_to_db_type_employer
from database.db_connector import get_random_vacancy_for_user

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
    experience_description = State()
    search_vacancies = State()
    dislike_resume = State()

class CommandState(StatesGroup):
    COMMAND_PROCESSING = State()

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
        
    await bot.send_message(message.chat.id, '''Привет я кот Миша.\n
Я выполняю здесь самую главную функцию: помогаю соискателям и работодателям найти друг друга. 
Представь, у каждого есть работа, а в мире царит гармония – мяу, красота. Для этого я здесь.''', reply_markup=None)
    await asyncio.sleep(4)
    await message.answer("Давай теперь познакомимся поближе. Кто ты?", reply_markup=await get_choose_rule())
    await UserForm.next()

async def main_menu_user(user_id, message_id):
    main_text = "Искать вакансии\n"
    main_text += "Личный кабинет\n"
    main_text += "Редактировать резюме\n"
    main_text += "О боте\n"
    await bot.send_message(user_id, main_text, reply_markup=await get_choose_menu_user_buttons(), disable_notification=True)

async def main_menu_employer(user_id, message_id):
    main_text = "Искать вакансии:\n"
    main_text += "Личный кабинет\n"
    main_text += "Редактировать резюме\n"
    main_text += "О боте\n"
    await bot.send_message(user_id, main_text, reply_markup=await get_choose_menu_employer_buttons(), disable_notification=True)

@dp.callback_query_handler(lambda c: c.data in ["job_seeker", "employer"], state="*")
async def process_user_type(callback_query: types.CallbackQuery, state: FSMContext):
    await CommandState.COMMAND_PROCESSING.set()

    user_type = callback_query.data
    user_id = callback_query.from_user.id
    
    employer_id = callback_query.from_user.id
    employer_username = callback_query.from_user.username

    user = callback_query.from_user.first_name if not callback_query.from_user.full_name else callback_query.from_user.username
    user_name = callback_query.from_user.username
    
    await state.update_data(user_type=user_type)

    if user_type == "job_seeker":
        await register_job_seeker(callback_query.message, callback_query.from_user.id, callback_query.from_user.username, callback_query.from_user.username)
        await callback_query.message.answer("Хорошо, давай теперь познакомимся. Напиши свой возраст:", reply_markup=None)
        await UserForm.regStart.set()

    elif user_type == "employer":
        await register_employer(callback_query.message, callback_query.from_user.id, callback_query.from_user.username, callback_query.from_user.username)
    await UserForm.next()

@dp.message_handler(state=UserForm.age)
async def process_age(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if int(message.text) >= 16:
            if not message.text.isdigit() or not (0 < int(message.text) < 99):
                await message.answer("Неверный формат возраста. Пожалуйста, введите возраст цифрами. Пример: 18", reply_markup=None)
                return
            data['age'] = message.text
        else:
            await message.answer("Извините, но для использования этого сервиса вам должно быть 16 лет или старше. Тем не менее, обратите внимание, что многие работодатели предпочитают нанимать людей старше 16 лет из-за их более широкого опыта и профессионализма.", reply_markup=None)
            return
    await update_user_age(message.from_user.id, data['age'])
    await UserForm.location.set()
    await message.answer("Из какого ты города?")
    await message.answer("Выбери из списка или напиши свой вариант:", reply_markup=await get_location_keyboard())

async def normalize_city(city_name):
    print(f"Searching for city: {city_name}")
    for key, variants in CITIES.items():
        if city_name.lower() in variants:
            print(f"Found city: {key}")
            return key
    return None

@dp.callback_query_handler(lambda query: query.data.startswith('location_'), state=UserForm.location)
async def process_location(callback_query: types.CallbackQuery, state: FSMContext):
    location = callback_query.data.split('_')[1]  # Разбиваем и в базу записывается только spb / moscow / sochi
    normalized_location = await normalize_city(location)

    if normalized_location:
        async with state.proxy() as data:
            data['location'] = normalized_location
        await update_user_location(callback_query.from_user.id, normalized_location)
        await UserForm.nickname.set()
        await callback_query.message.answer("Как к тебе обращаться? (Эта информация скрыта от остальных пользователей)", reply_markup=None)
    else:
        await callback_query.message.answer("Указанный город не найден в списке доступных городов.", reply_markup=None)

@dp.message_handler(state=UserForm.nickname)
async def process_nickname(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['nickname'] = message.text
    await update_user_name(message.from_user.id, data['nickname'])
    #await UserForm.description.set()
    #await message.answer("Напиши краткое описание о себе.", reply_markup=None)

    await message.answer("Отлично! Давай теперь заполним твое резюме.", reply_markup=None)
    await asyncio.sleep(1)
    await message.answer("Напиши ФИО. (Пример: Константин Гурий Павлович)")
    await UserForm.resume_start.set()
    await UserForm.fullname.set()

'''
@dp.message_handler(state=UserForm.description)
async def process_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    await update_user_description(message.from_user.id, data['description'])
    await add_user_info_to_db(message.from_user.id, data.get('nickname'), data.get('age'), data.get('description'))
    await message.answer("Отлично! Давай теперь заполним твое резюме. Если вдруг у тебя имеется личное резюме, ты сможешь его прикрепить после в личном кабинете.", reply_markup=None)
    await message.answer("Напиши ФИО. (Пример: Константин Гурий Павлович)")
    await UserForm.resume_start.set()
    await UserForm.fullname.set()
'''

@dp.message_handler(state=UserForm.fullname)
async def resume_start(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['fullname'] = message.text
    await update_user_fullname(message.from_user.id, data['fullname'])
    await message.answer("Откуда ты? (Напиши текстом если среди вариантов ниже нет твоего)", reply_markup=await get_citizenship_keyboard())
    await UserForm.citizenship.set()

# Шаг 3: Ответ на вопрос о национальности
@dp.message_handler(state=UserForm.citizenship)
async def citizenship(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['citizenship'] = message.text
    await update_user_citizenship(message.from_user.id, data['citizenship'])
    await message.answer("Кем бы вы хотели работать? (Напиши текстом если среди вариантов ниже нет твоего)", reply_markup=await get_position_keyboard())
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
    await message.answer("Отлично! Расскажите о своем опыте работы. Напишите название предыдущего места работы.", reply_markup=None)
    
# Шаг 6.2: Если нет опыта работы
@dp.message_handler(lambda message: message.text.lower() == 'нет', state=UserForm.work_experience)
async def process_experience_no(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['experience'] = "Нет опыта работы"
    await update_user_experience(message.from_user.id, data['experience'])
    await UserForm.skills.set()
    await message.answer("Какими навыками вы обладаете?", reply_markup=types.ReplyKeyboardRemove())

# Продолжение для описания опыта работы
@dp.message_handler(state=UserForm.experience_details)
async def process_experience_details(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['experience'].append({
            'company_name': message.text,
            'description': None  # Добавьте дополнительный запрос для описания работы
        })
    await message.answer("Опишите вашу работу в данной компании.", reply_markup=types.ReplyKeyboardRemove())  # Убрать клавиатуру
    await UserForm.experience_description.set()

# Дополнительный запрос для описания работы
@dp.message_handler(state=UserForm.experience_description)
async def process_experience_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if 'experience' not in data or not data['experience']:
            await message.answer("Произошла ошибка при обработке опыта работы. Пожалуйста, попробуйте снова.")
            return
        current_experience = data['experience'][-1]  # Получаем текущий опыт работы
        current_experience['description'] = message.text  # Добавляем описание работы
        data['experience'][-1] = current_experience  # Обновляем опыт работы в списке
    
    await message.answer("Есть ли еще места работы, о которых вы хотите рассказать?", reply_markup=await get_yes_no_keyboard())
    await UserForm.experience_another.set()

# Повторяющиеся вопросы, если есть другой опыт работы
@dp.message_handler(lambda message: message.text.lower() == 'да', state=UserForm.experience_another)
async def process_experience_another_yes(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        # Создаем словарь для нового опыта работы
        new_experience = {
            'company_name': message.text,
            'description': None
        }
        # Добавляем новый опыт работы в список всех опытов
        data['experience'].append(new_experience)
    await UserForm.experience_details.set()
    await message.answer("Опишите вашу работу в данной компании.", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda message: message.text.lower() == 'нет', state=UserForm.experience_another)
async def process_experience_another_no(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        # Преобразуем опыт работы в JSON и отправляем в базу данных
        experience_json = json.dumps(data['experience'])
    await update_user_experience(message.from_user.id, experience_json)
    await UserForm.skills.set()
    await message.answer("Какими навыками вы обладаете?", reply_markup=types.ReplyKeyboardRemove())
    
@dp.message_handler(state=UserForm.skills)
async def process_skills(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['skills'] = message.text
    await update_user_skills(message.from_user.id, data['skills'])
    await state.update_data(experience=data.get('experience'), skills=data.get('skills'))
    await UserForm.resume_check.set()
    await process_resume_check(message, state)

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
            await message.answer(f"Ваше резюме:\n{resume}", reply_markup=None)
            await UserForm.resume_confirmation.set()
            await message.answer("Спасибо за регистрацию.")
        else:
            await message.answer("Желаете что-нибудь подправить или начать заново?", reply_markup=await get_save_restart_keyboard())
    await state.finish()

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

@dp.message_handler(lambda message: message.text == "/search" or message.text == "🔍 Искать Вакансии")
async def search_vacancies(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)

    if user_data:
        random_vacancy = await get_random_vacancy_for_user(user_id)

        if random_vacancy:
            formatted_vacancy = await format_vacancy(random_vacancy)
            await message.answer(
                formatted_vacancy,
                parse_mode="HTML",
                reply_markup=await get_send_or_dislike_resume_keyboard()
            )
        else:
            await message.answer(
                "К сожалению, не удалось найти вакансии. Попробуйте еще раз позже.",
                reply_markup=None
            )
    else:
        await message.answer(
                "Похоже что ты не зарегистрирован в системе. Самое время пройти регистраицю! /start",
                reply_markup=None
            )

@dp.message_handler(lambda message: message.text == "👎", state="*")
async def dislike_resume(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)

    if user_data:
        random_vacancy = await get_random_vacancy_for_user(user_id)

        if random_vacancy:
            formatted_vacancy = await format_vacancy(random_vacancy)
            await message.answer(
                formatted_vacancy,
                parse_mode="HTML",
                reply_markup=await get_send_or_dislike_resume_keyboard()
            )
        else:
            await message.answer(
                "К сожалению, не удалось найти вакансии. Попробуйте еще раз позже.",
                reply_markup=None
            )

@dp.message_handler(lambda message: message.text == '✉', state="*")
async def send_resume(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)

    if user_data:
        await message.answer("Резюме отправлено!\n\nТеперь можно перейти к просмотру анкет дальше!")
        await search_vacancies(message)

@dp.message_handler(lambda message: message.text == "😴", state="*")
async def personal_sleep(message: types.Message):
    await message.answer("Отлично! Самое время сделать перерв 😁", reply_markup=await get_choose_menu_user_buttons())

@dp.message_handler(lambda message: message.text == "👤 Личный кабинет", state="*")
async def personal_cabinet(message: types.Message):
    user_id = message.from_user.id

    user_data = await get_user_data(user_id)

    if user_data:
        fullname = user_data.get("fullname")
        age = user_data.get("age")
        description = user_data.get("description")
        location = user_data.get("location")
        status = "Ищу работу"
        experience_json = user_data.get("experience")
        skills = user_data.get("skills")

        if isinstance(experience_json, str):
            experience_list = json.loads(experience_json)
        else:
            experience_list = experience_json

        if isinstance(experience_list, list):
            # Форматирование опыта работы для вывода
            experience_text = "\n".join([f"Место работы: {exp['company_name']}\nОписание: {exp['description']}" for exp in experience_list])
        else:
            experience_text = "Нет данных об опыте работы"

        user_info_text = f"ФИО: {fullname}\nВозраст: {age}\nОписание: {description}\nМестоположение: {location}\nНавыки: {skills}\nСтатус: {status}\n\nОпыт работы:\n{experience_text}"

        await message.answer(f'Вот так будет видеть твою анкету работодатель:\n\n{user_info_text}', reply_markup=await get_resume_button())
    else:
        await message.answer("Информация о пользователе не найдена.", reply_markup=None)

@dp.message_handler(lambda message: message.text == "↩️ Назад", state="*")
async def back_to_main_menu(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)
    if user_data:
        name = user_data.get("name")
        await main_menu_user(user_id, name)
    else:
        await message.answer("Информация о пользователе не найдена. Пройдите регистрацию нажав на команду /start", reply_markup=None)

@dp.message_handler(lambda message: message.text == "ℹ️ О боте", state="*")
async def about_bot(message: types.Message):
    about_text = "Данный бот был создан для помощи компаниям в сфере общепита быстрее найти работников."
    await message.answer(about_text)

@dp.message_handler(lambda message: message.text == "✏️ Редактировать резюме", state="*")
async def about_bot(message: types.Message):
    await message.answer("Желаете что-нибудь подправить или начать заново?", reply_markup=await get_save_restart_keyboard())

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

    await message.answer(help_text, reply_markup=None)

@dp.message_handler(commands=['about'], state="*")
async def help_command(message: types.Message):
    user_id = message.from_user.id
    user_data = await get_user_data(user_id)

    if user_data:
        await main_menu_user(message.from_user.id, message.message_id)
        await message.answer('help_text', reply_markup=None)
    else:
        await message.answer('SuckMyDickBROOO', reply_markup=None)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
