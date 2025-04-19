import os
import logging
from typing import Optional
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
from aiogram.utils.markdown import html_decoration as hd

# Для работы с PDF
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
API_TOKEN = "7810891694:AAFQWbhhUd28qQa7Iutt5-k5oOewOnzUz88"
GIGACHAT_CREDENTIALS = "MTlmNjg5ZTYtNzRhNS00NzFjLTg4NzEtM2I2OThmNDdkNTk4OmY3OWJkODU0LTRiMGUtNDg3ZC1iMzEzLTNlODc4ZjYxNGRmZQ=="  # Авторизационные данные (логин/пароль или токен)

# Инициализация бота
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация GigaChat
gigachat = GigaChat(credentials=GIGACHAT_CREDENTIALS, verify_ssl_certs=False)


# Состояния для FSM
class WasteCalculation(StatesGroup):
    waiting_for_waste_class = State()
    waiting_for_waste_amount = State()


# Загрузка и обработка PDF документов
def load_documents():
    pdf_paths = [
        "data/registration_guide.pdf",
        "data/tariffs.pdf",
        "data/digital_signature_manual.pdf"
    ]

    docs = []
    for path in pdf_paths:
        try:
            loader = PyPDFLoader(path)
            docs.extend(loader.load())
        except Exception as e:
            logger.error(f"Failed to load {path}: {e}")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    return text_splitter.split_documents(docs)


# Инициализация векторного хранилища
try:
    documents = load_documents()
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    )
    vector_db = FAISS.from_documents(documents, embeddings)
except Exception as e:
    logger.error(f"Vector DB initialization failed: {e}")
    raise


# Клавиатуры
def main_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📝 Регистрация в ФГИС ОПВК")],
            [types.KeyboardButton(text="💳 Расчет стоимости утилизации")],
            [types.KeyboardButton(text="🔧 Настройка электронной подписи")],
            [types.KeyboardButton(text="ℹ️ Справка")]
        ],
        resize_keyboard=True
    )


async def ask_gigachat(question: str, context: str) -> Optional[str]:
    try:
        messages = Messages(
            role=MessagesRole.USER,
            content=f"Контекст:\n{context}\n\nВопрос: {question}\n\nОтветь строго по предоставленным документам. Если информации нет, скажи 'Информация не найдена'."
        )

        response = gigachat.chat(
            Chat(
                messages=[messages],
                temperature=0.3,
                max_tokens=1000
            )
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"GigaChat API error: {e}")
        return None


# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот-помощник для работы с ФГИС ОПВК.\n\n"
        "Вы можете:\n"
        "- Использовать кнопки меню\n"
        "- Задать любой вопрос о системе текстом",
        reply_markup=main_menu_keyboard()
    )


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "ℹ️ <b>Помощь по боту:</b>\n\n"
        "• Используйте кнопки меню для быстрого доступа\n"
        "• Задавайте вопросы текстом - я найду ответ в документах\n\n"
        "Примеры вопросов:\n"
        "- Как зарегистрироваться в системе?\n"
        "- Какие нужны документы?\n"
        "- Сколько стоит утилизация 5 тонн отходов II класса?",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )


# Обработчики кнопок меню
@dp.message(F.text == "📝 Регистрация в ФГИС ОПВК")
async def registration_guide(message: types.Message):
    await message.answer(
        "📄 <b>Регистрация в ФГИС ОПВК</b>\n\n"
        "Для регистрации вам потребуется:\n"
        "1. Действующий ИНН\n"
        "2. Электронная подпись\n"
        "3. Контактные данные\n\n"
        "Задайте конкретный вопрос о регистрации или нажмите /help",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )


@dp.message(F.text == "💳 Расчет стоимости утилизации")
async def start_calculation(message: types.Message, state: FSMContext):
    await message.answer(
        "Выберите класс отходов:",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[
                [types.KeyboardButton(text="I класс")],
                [types.KeyboardButton(text="II класс")],
                [types.KeyboardButton(text="🔙 Назад")]
            ],
            resize_keyboard=True
        )
    )
    await state.set_state(WasteCalculation.waiting_for_waste_class)


@dp.message(F.text == "🔧 Настройка электронной подписи")
async def digital_signature_guide(message: types.Message):
    await message.answer(
        "🔐 <b>Электронная подпись для ФГИС ОПВК</b>\n\n"
        "Требования:\n"
        "1. Квалифицированная ЭП\n"
        "2. Сертифицированный носитель (Рутокен, JaCarta)\n"
        "3. Установленное ПО КриптоПро CSP\n\n"
        "Задайте вопрос об ЭП для получения подробной инструкции",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )


# Обработка состояний FSM
@dp.message(WasteCalculation.waiting_for_waste_class)
async def choose_waste_class(message: types.Message, state: FSMContext):
    if message.text == "🔙 Назад":
        await state.clear()
        await message.answer("Главное меню:", reply_markup=main_menu_keyboard())
        return

    if message.text not in ["I класс", "II класс"]:
        await message.answer("Пожалуйста, выберите класс из предложенных вариантов.")
        return

    await state.update_data(waste_class=message.text)
    await message.answer(
        "Введите объем отходов (в тоннах):",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(WasteCalculation.waiting_for_waste_amount)


@dp.message(WasteCalculation.waiting_for_waste_amount)
async def calculate_cost(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное положительное число (например: 5.2).")
        return

    data = await state.get_data()
    waste_class = data['waste_class']
    rates = {"I класс": 222907.36, "II класс": 62468.26}
    cost = rates[waste_class] * amount

    await message.answer(
        f"💰 <b>Стоимость утилизации:</b>\n\n"
        f"• Класс отходов: {waste_class}\n"
        f"• Объем: {amount} тонн\n"
        f"• Итого: {cost:,.2f} руб. (без НДС)\n\n"
        f"<i>Расчет произведен по официальным тарифам ФГИС ОПВК</i>",
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )
    await state.clear()


# Обработка произвольных текстовых запросов с GigaChat
@dp.message(F.text)
async def handle_text_query(message: types.Message, state: FSMContext):
    # Пропускаем если пользователь в состоянии FSM
    current_state = await state.get_state()
    if current_state:
        return

    query = message.text.strip()
    if not query or len(query) > 500:
        await message.answer("Пожалуйста, введите вопрос (максимум 500 символов).")
        return

    try:
        # Индикатор "бот печатает"
        await bot.send_chat_action(message.chat.id, "typing")

        # Поиск релевантных фрагментов в PDF
        docs = vector_db.similarity_search(query, k=3)
        context = "\n\n---\n\n".join([d.page_content for d in docs])

        # Генерация ответа через GigaChat
        answer = await ask_gigachat(
            question=query,
            context=f"Документация ФГИС ОПВК:\n{context}"
        )

        if not answer:
            raise ValueError("Пустой ответ от GigaChat API")

        # Форматирование ответа
        response = (
            f"📄 <b>Ответ по вашему запросу:</b>\n\n"
            f"{answer}\n\n"
            f"<i>Информация основана на официальных документах ФГИС ОПВК</i>"
        )

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        response = (
            "⚠️ Произошла ошибка при обработке запроса.\n\n"
            "Попробуйте:\n"
            "1. Переформулировать вопрос\n"
            "2. Использовать кнопки меню\n"
            "3. Повторить попытку позже"
        )

    await message.answer(
        response,
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.HTML
    )


# Запуск бота
async def main():
    logger.info("Starting bot...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())