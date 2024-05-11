import json
import os
import traceback

from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.keyboards import *
from bot.utils.states import *
from bot.database.methods import *
from bot.utils import normalize_city
from bot.handlers.bot_messages import *


async def register_job_seeker(user_tgid, user_tgname, user_fullname, state: FSMContext):
    """
    Регистрация соискателя.
    :param user_tgid: Telegram ID пользователя
    :param user_tgname: Telegram username пользователя
    :param user_fullname: Полное имя пользователя
    """
    # Здесь код для регистрации соискателя в базе данных:
    # await db.save_user(user_tgid, user_tgname, user_fullname, user_type="JOB_SEEKER")

    # Вместо прямого вызова функций proc_age и process_location будем устанавливать состояния FSM
    await state.set_state(UserForm.fio)

# Вопрос про ФИО для соискателя
@router.message(UserForm.fio)
async def process_fio(msg: Message, state: FSMContext):
    await state.update_data(fio=msg.text)
    # Продолжаем диалог
    await state.set_state(UserForm.age)
    await msg.answer("Сколько тебе полных лет?\nНапример: 21", reply_markup=None)

# Вопрос про возраст для соискателя
@router.message(UserForm.age)
async def process_age(msg: Message, state: FSMContext):
    if int(msg.text) >= 14:
        if not msg.text.isdigit() or not (0 < int(msg.text) < 99):
            await msg.answer("Неверный формат возраста. Пожалуйста, введите возраст цифрами. Пример: 18", reply_markup=rmk)
            return
    elif msg.text == "писят два":
        await msg.answer("Отсылочка )))\nЛадно, давай повторим..", reply_markup=rmk)
        await state.set_state(UserForm.age)

        await msg.answer("Сколько тебе полных лет?\nНапример: 21", reply_markup=rmk)
        return
    else:
        await msg.answer('''К сожалению, в России можно работать только с 14 лет.
Но время летит быстро!
Мы будем тебя ждать ❤️''', reply_markup=rmk)
        await msg.answer("Но если ты просто ошибся с возрастом, то ты можешь его изменить", reply_markup=await get_change_age())
        return
    
    await state.update_data(age=msg.text)
    
    await msg.answer("В каком городе планируешь работать?", reply_markup=await get_location_keyboard())
    await state.set_state(UserForm.location)

# Если вдруг пользователь ошибся
@router.callback_query(lambda c: c.data == 'change_age')
async def change_age(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer("Давайте попробуем еще раз")
    await callback_query.message.answer("Сколько тебе полных лет?\nНапример: 21", reply_markup=rmk)
    await state.set_state(UserForm.age)

# Наши Солевые и Московские друзья :)
@router.callback_query(lambda c: c.data == 'msk' or c.data == 'spb')
async def process_location_msk_spb(callback_query: CallbackQuery, state: FSMContext):
    location = callback_query.data 
    if callback_query.data == 'msk':  
        location = 'msk'
        location_text = 'Москва'
    else:
        location = 'spb'
        location_text = 'Санкт-Петербург'

    data = await state.get_data()
    data['location_text'] = location_text
    data['location'] = location
    await state.update_data(location=location)
    await callback_query.message.answer("Ты гражданин какой страны?", reply_markup=await get_citizenship_keyboard())

# Наши не Солевые и Московские друзья :(
@router.callback_query(lambda c: c.data == 'other_location')
async def change_location_other(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("Напиши город:", reply_markup=rmk)
    await state.set_state(UserForm.location_retry)

# Наши не Солевые и Московские друзья и их добавление в бд :(
@router.message(UserForm.location_retry)
async def process_location(msg: Message, state: FSMContext):
    location_text = msg.text
    normalized_location = await normalize_city(location_text)

    if normalized_location is None:
        await msg.answer("К сожалению, мы не можем разобрать, что это за город. Пожалуйста, введи его снова.")
        return
    
    data = await state.get_data()
    data['location_text'] = location_text
    data['location'] = normalized_location
    await state.update_data(location=location_text)
    #await state.update_data(location=normalized_location)
    await msg.answer("Ты гражданин какой страны?", reply_markup=await get_citizenship_keyboard())

# Варик без расчленения
'''
@router.message(UserForm.location)
async def process_location(msg: Message, state: FSMContext):
    location = msg.text
    normalized_location = await normalize_city(location)
    data = await state.get_data()
    data['location_text'] = msg.text

    await state.update_data(location=location)
    await update_user_location(msg.from_user.id, normalized_location)
    await state.update_data(location=normalized_location)
    await state.set_state(UserForm.user_what_is_your_name)
    await msg.answer("Как к тебе обращаться? (Эта информация скрыта от остальных пользователей)", reply_markup=rmk)
'''

# Скипаем вопрос "Как обращаться к тебе?" 
'''
@router.message(UserForm.user_what_is_your_name)
async def procName(msg: Message, state: FSMContext):
    await state.update_data(user_what_is_your_name=msg.text)
    data = await state.get_data()
    data['user_what_is_your_name'] = msg.text
    await update_user_name(msg.from_user.id, msg.text)
    await state.set_state(UserForm.resume_start)
    await state.set_state(UserForm.fullname)
    await msg.answer("Отлично! Давай теперь заполним твое резюме.\nНапиши ФИО. (Пример: Константин Гурий Павлович)")
    
    
@router.message(UserForm.fullname)
async def resume_start(msg: Message, state: FSMContext):
    await state.update_data(fullname=msg.text)
    data = await state.get_data()
    await update_user_fullname(msg.from_user.id, data.get('fullname'))
    await msg.answer("Откуда ты? (Напиши текстом если среди вариантов ниже нет твоего)", reply_markup=await get_citizenship_keyboard())
    await state.set_state(UserForm.citizenship)
'''
    
# Наши Солевые и Московские друзья :)
@router.callback_query(lambda c: c.data == 'citizen_Russian_Federation')
async def process_citizen_Russian_Federation(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("Выбери желаемую должность:", reply_markup=await get_position_keyboard())

    data = await state.get_data()
    data['citizenship'] = "ru"
    await state.update_data(citizenship="ru")  # Update the state data
    await state.set_state(UserForm.desired_position)  # Set the next state directly

# Наши не Солевые и Московские друзья :(
@router.callback_query(lambda c: c.data == 'other_citizen')
async def change_other_citizen(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await callback_query.message.answer("Гражданином какой страны ты являешься?\nНапример: Казахстан", reply_markup=rmk)
    data = await state.get_data()
    data['citizenship'] = callback_query.message.text
    await state.set_state(UserForm.citizenship)

# Выбор должности
@router.message(UserForm.citizenship)
async def process_citizenship(msg: Message, state: FSMContext):
    await state.update_data(citizenship=msg.text)
    await msg.answer("Выбери желаемую должность:", reply_markup=await get_position_keyboard())
    await state.set_state(UserForm.desired_position)

# Предпочтиаемая зарплата
@router.message(UserForm.desired_position)
async def process_desired_position(msg: Message, state: FSMContext):
    await state.update_data(desired_position=msg.text)
    await state.set_state(UserForm.user_desired_salary_level)
    await msg.answer("Какую зарплату ты бы хотел получать?\nНапример: 50 000", reply_markup=rmk)

# Занятость соискателя (Полная или частичная)
@router.message(UserForm.user_desired_salary_level)
async def process_user_desired_salary_level(msg: Message, state: FSMContext):
    await state.update_data(user_desired_salary_level=msg.text)
    await msg.answer("Какая занятость тебя интересует ?", reply_markup=await get_employment_keyboard())

# Выбор и отправка занятости , а так же вопрос опыте работы
@router.callback_query(lambda c: c.data == 'full_employment' or c.data == 'part-time_employment')
async def process_desired_positionv1(callback_query: CallbackQuery, state: FSMContext):
    message = callback_query.message
    if callback_query.data == 'full_employment':
        new_user_employment_type = 'Полная занятость'
    else:
        new_user_employment_type = 'Частичная занятость'

    await state.update_data(user_employment_type=new_user_employment_type)
    await state.set_state(UserForm.work_experience)
    await message.answer("Был ли у тебя опыт работы?", reply_markup=await get_yes_no_keyboard())

# proc_experience, распрашиваем про опыт если есть, либо скпиаем если нет :(
@router.message(UserForm.work_experience)
async def proc_experience(msg: Message, state: FSMContext):
    if msg.text.lower() == 'да':
        await state.set_state(UserForm.experience_details)
        await msg.answer("Отлично! Расскажите о своем опыте работы. Напишите название предыдущего места работы.", reply_markup=rmk)
    elif msg.text.lower() == 'нет':
        await state.update_data(work_experience="Нет опыта работы")
        await state.set_state(UserForm.additional_info)
        await msg.answer("У тебя есть навыки, с которыми то хотел бы поделиться?", reply_markup=rmk)
    else:
        await msg.answer("Пожалуйста, ответьте 'да' или 'нет'.", reply_markup=rmk)

# Сохраняем данные о названии Компании и задаем вопрос про период работы
@router.message(UserForm.experience_details)
async def process_experience_details(msg: Message, state: FSMContext):
    await state.update_data(company_name=msg.text)
    await state.set_state(UserForm.experience_period)
    await msg.answer("Введите период работы в формате: 11.2020-09.2022", reply_markup=rmk)

# Сохраняем данные о периоде работы и задаем вопрос про должность
@router.message(UserForm.experience_period)
async def process_experience_period(msg: Message, state: FSMContext):
    await state.update_data(experience_period=msg.text)
    await state.set_state(UserForm.experience_position)
    await msg.answer("Какую должность ты занимал?", reply_markup=rmk)

# Сохраняем данные о должности и задаем вопрос про опыт в опыте?? Вот это игра слов, вот это я молодец )))
@router.message(UserForm.experience_position)
async def process_experience_position(msg: Message, state: FSMContext):
    await state.update_data(experience_position=msg.text)
    await state.set_state(UserForm.experience_duties)
    await msg.answer("Расскажи, какие у тебя были обязанности на этой работе? Старайся отвечать на этот вопрос максимально кратко и лаконично, при этом не упуская главной сути", reply_markup=rmk)
    await msg.answer("Например: Я варил для моих посетителей – котиков, самое лучшее молоко, с пенкой. А в конце смены, я подметал полы от следов лапок, и вел учет, сколько кошачьей мяты поступило в кассу, а сколько было потрачено", reply_markup=rmk)

# Сохраняем данные о должности и задаем вопрос про опыт в опыте?? Вот это игра слов, вот это я молодец )))
@router.message(UserForm.experience_duties)
async def process_experience_duties(msg: Message, state: FSMContext):
    await state.update_data(experience_duties=msg.text)
    await state.set_state(UserForm.experience_another)
    await msg.answer("Был ли у вас другой опыт работы?", reply_markup=await get_yes_no_keyboard())

# process_experience_another
@router.message(UserForm.experience_another)
async def process_experience_another(msg: Message, state: FSMContext):
    if msg.text.lower() == 'да':
        await state.set_state(UserForm.experience_details)
        await msg.answer("Отлично! Напишите название предыдущего места работы.", reply_markup=rmk)
    elif msg.text.lower() == 'нет':
        data = await state.get_data()
        experience_data = {
            "company_name": data.get("company_name"),
            "experience_period": data.get("experience_period"),
            "experience_position": data.get("experience_position"),
            "experience_duties": data.get("experience_duties")
        }
        await state.update_data(experience_data=experience_data)
        # Сохранение опыта работы
        await state.set_state(UserForm.additional_info)
        await msg.answer("Все круги ада пройдены! 👹\nТеперь финишная прямая.", reply_markup=rmk)
        await msg.answer("Хочешь ли ты добавить дополнительную информацию информацию о себе?", reply_markup=await get_yes_no_keyboard())

    else:
        await msg.answer("Пожалуйста, ответьте 'да' или 'нет'.", reply_markup=await get_yes_no_keyboard())

# process_additional_info
@router.message(UserForm.additional_info)
async def process_additional_info(msg: Message, state: FSMContext):
    if msg.text.lower() == 'да':
        await state.set_state(UserForm.additional_info_details)
        await msg.answer("Здесь ты можешь рассказать о своих навыках и умениях", reply_markup=rmk)
    elif msg.text.lower() == 'нет':
        await state.set_state(UserForm.photo_upload)
        await msg.answer("Чего-то не хватает. Соли? Перца? Фотографии! Ждем твое фото 🔥", reply_markup=rmk)
    else:
        await msg.answer("Пожалуйста, ответьте 'да' или 'нет'.", reply_markup=await get_yes_no_keyboard())

# process_additional_info_details
@router.message(UserForm.additional_info_details)
async def process_additional_info_details(msg: Message, state: FSMContext):
    additional_info = msg.text
    await state.update_data(additional_info=additional_info)

    await state.set_state(UserForm.photo_upload)
    await msg.answer("Чего-то не хватает. Соли? Перца? Фотографии! Ждем твое фото 🔥", reply_markup=await get_skip_button())

'''
# Выбор должности
@router.message(UserForm.user_additional_info)
async def process_user_additional_info(msg: Message, state: FSMContext):
    data = await state.get_data()
    await update_user_additional_info(msg.from_user.id, data['user_additional_info'])
    await msg.answer("Хочешь ли ты добавить дополнительную информацию информацию о себе?", reply_markup=await get_position_keyboard())
    await state.set_state(UserForm.desired_position)
'''

@router.callback_query(lambda c: c.data == 'skip')
async def skip_photo(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.answer()
    await state.set_state(UserForm.resume_check)


'''
# Отправка фото на сервер
@router.message(UserForm.photo_upload)
async def photo_upload_and_resume_check(msg: Message, state: FSMContext):
    if msg.photo:
        try:
            username = msg.from_user.username
            user_folder = f"img/{username}"
            os.makedirs(user_folder, exist_ok=True)  # Создаем папку для пользователя, если ее нет
            file_info = await bot.get_file(msg.photo[-1].file_id)
            file_path = file_info.file_path
            file_name = "photo.jpg"  # Имя файла фотографии
            file_save_path = os.path.join(user_folder, file_name)
            await bot.download_file(file_path, file_save_path)
            await state.update_data(photo_path=file_save_path)

            # Формируем текст резюме
            data = await state.get_data()
            resume = f"<b>ФИО:</b> {data['fio']}\n" \
                     f"<b>Гражданство:</b> {data['citizenship']}\n" \
                     f"<b>Желаемая позиция:</b> {data['desired_position']}\n" \
                     "<b>Опыт работы:</b>\n"
            experience_data = {
                "company_name": data.get("company_name"),
                "experience_period": data.get("experience_period"),
                "experience_position": data.get("experience_position"),
                "experience_duties": data.get("experience_duties")
            }
            resume += str(experience_data)

            desired_salary = data.get('user_desired_salary_level', 'Не указано')
            employment_type = data.get('user_employment_type', 'Не указано')

            resume += f"<b>Желаемая зарплата:</b> {desired_salary}\n" \
                      f"<b>Желаемая занятость:</b> {employment_type}\n"

            # Отправляем текст резюме с фотографией
            await msg.answer_photo(photo=open(file_save_path, 'rb'), caption=f"Ваше резюме:\n\n{resume}\n\nЖелаете что-нибудь подправить или начать заново?",
                                    parse_mode='HTML', reply_markup=await get_save_restart_keyboard())
        except aiogram.client.errors.TelegramAPIError as e:
            if e.error_code == 404:
                await msg.answer("Файл не найден. Пожалуйста, попробуйте загрузить его еще раз.")
                return
            else:
                raise e
    else:
        await msg.answer("Пожалуйста, загрузите фотографию.")



'''


@router.message(UserForm.photo_upload)
async def photo_upload_and_resume_check(msg: Message, state: FSMContext):
    if msg.photo:
        try:
            username = msg.from_user.username
            user_folder = f"img/{username}"
            os.makedirs(user_folder, exist_ok=True)
            file_info = await bot.get_file(msg.photo[-1].file_id)
            file_path = file_info.file_path

            file_name = "photo.jpg"
            file_save_path = os.path.join(user_folder, file_name)
            await bot.download_file(file_path, file_save_path)
            await state.update_data(photo_path=file_save_path)
            await msg.answer("Твое резюме готово!\nВот как вот оно выглядит:")

            data = await state.get_data()

            resume = f"<b>{data['desired_position']}</b>\n" \
                    f"<u>{data['fio']}</u>\n" \
                    f"Возраст: {data['age']}\n" \
                    f"Город: {data.get('location_text', 'Не указано')}\n" \
                    f"Гражданство: {data['citizenship']}\n" \
                    f"Желаемый уровень з/п: {data['user_desired_salary_level']}\n" \
                    f"Занятость: {data.get('user_employment_type', 'Не указано')}\n\n" \
                    f"<i>Опыт работы:</i>\n" \
                    
            experience = data.get('experience_data', {})
            if experience: 
                        resume += f"<b>{experience.get('company_name', 'Не указано')}</b>\n" \
                                f"Период работы: {experience.get('experience_period', 'Не указано')}\n" \
                                f"Должность: {experience.get('experience_position', 'Не указано')}\n" \
                                f"Основные обязанности: {experience.get('experience_duties', 'Не указано')}\n\n" \
                        
            else:
                resume += "Не указано\n"
            
            additional_info = data.get('user_additional_info', 'Не указано')
            resume += f"<i>Дополнительная информация:</i> {additional_info}\n"

            await bot.send_photo(msg.chat.id, photo=types.FSInputFile(file_save_path), caption=resume, reply_markup=await get_save_restart_keyboard())



        except Exception as e:
            print(f"An error occurred while processing the photo: {e}")
            traceback.print_exc()
            await msg.answer("Произошла ошибка при загрузке фотографии. Попробуйте еще раз.")
    else:
        await msg.answer("Хм, кажется это не фото..")
        return




@router.message(UserForm.resume_check)
async def process_resume_check(msg: Message, state: FSMContext):
    data = await state.get_data()

    resume = f"<b>{data['desired_position']}</b>\n" \
             f"<u>{data['fio']}</u>\n" \
             f"Возраст: {data['age']}\n" \
             f"Город: {data['location_text']}\n" \
             f"Гражданство: {data['citizenship']}\n" \
             f"Желаемый уровень з/п: {data['user_desired_salary_level']}\n" \
             f"Занятость: {data.get('user_employment_type', 'Не указано')}\n\n" \
             f"<i>Опыт работы:</i>\n" \
             
    experience = json.loads(data['experience_data'])
    if isinstance(experience, dict):  # Проверяем, что опыт работы представлен словарем (ихвильних)
        resume += f"<b>{experience.get('company_name', 'Не указано')}</b>\n" \
                  f"Период работы: {experience.get('experience_period', 'Не указано')}\n" \
                  f"Должность: {experience.get('experience_position', 'Не указано')}\n" \
                  f"Основные обязанности: {experience.get('experience_duties', 'Не указано')}\n" \
                  
    else:
        resume += "Не указано\n"
    
    additional_info = data.get('user_additional_info', 'Не указано')
    resume += f"<i>Дополнительная информация:</i> {additional_info}\n"
    photo_path = data.get("photo_path")
    if photo_path:
        resume += f"Фото: {photo_path}\n"
    
    await msg.answer(f"Ваше резюме:\n\n{resume}\n\nЖелаете что-нибудь подправить или начать заново?", 
                     reply_markup=await get_save_restart_keyboard())


@router.callback_query()
async def proc_con(callback_query: CallbackQuery, state: FSMContext):
    if callback_query.data == 'save_resume' or callback_query.message.text.lower() in ['да', 'save_resume', 'сохранить', '/save_resume', 'Сохранить']:
        await state.set_state(UserForm.resume_confirmation)
        await state.update_data(resume_confirmation="Отправлено")
        await callback_query.message.answer("Резюме отправлено на модерацию.\nВ среднем, она выполняется за 5-10 минут.\nА пока можно пойти и выпить чаю ☕️\nты этого точно заслуживаешь!")
        await main_menu_user(callback_query.from_user.id, callback_query.message.message_id)

    elif callback_query.data == 'restart_resume' or callback_query.message.text.lower() in ['нет', 'restart_resume', 'отмена', '/restart_resume', 'Отмена']:
        await restart_resume(callback_query.message, state)
    elif callback_query.data == 'edit_resume':
        await callback_query.message.answer("Что именно ты хочешь изменить?")

    else: 
        await process_resume_confirmation(callback_query.message, state)
        
    await state.clear()



async def restart_resume(msg: Message, state: FSMContext):
    await state.reset_state()
    await msg.answer("Процесс заполнения резюме начат заново.")
    await process_fio(msg=msg, state=state)
    await UserForm.fullname.set()
    


@router.message(UserForm.resume_confirmation)
async def process_resume_confirmation(msg: Message, state: FSMContext):
    if msg.text.lower()=='да':
        await msg.answer("Резюме отправлено на модерацию.\nВ среднем, она выполняется за 10 минут.\nА пока можно пойти и выпить чаю ☕️\nты этого точно заслуживаешь!")
        await main_menu_user(msg.from_user.id, msg.message_id)
    else: 
        await msg.answer("Хорошо, давайте перезаполним резюме.")
        await process_fio(msg=msg, state=state)
    await state.clear()