import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils import markdown as md
from aiogram.enums import ParseMode

# Настройки бота
API_TOKEN = '7810891694:AAFQWbhhUd28qQa7Iutt5-k5oOewOnzUz88'  # Замените на свой токен
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# Состояния для FSM
class WasteCalculation(StatesGroup):
    waiting_for_waste_class = State()
    waiting_for_waste_amount = State()


# Клавиатура главного меню
def main_menu_keyboard():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="📝 Регистрация в ФГИС ОПВК")],
            [types.KeyboardButton(text="💳 Расчет стоимости утилизации")],
            [types.KeyboardButton(text="🔧 Настройка электронной подписи")],
            [types.KeyboardButton(text="ℹ️ Справка")],
            [types.KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )


# Команда /start
@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я твой цифровой помощник для работы с ФГИС ОПВК. Выбери действие:",
        reply_markup=main_menu_keyboard()
    )


# Обработка кнопки "Главное меню"
@dp.message(lambda message: message.text == "🏠 Главное меню")
async def return_to_main_menu(message: types.Message, state: FSMContext):
    await state.clear()  # Очищаем состояние FSM
    await message.answer(
        "Главное меню:",
        reply_markup=main_menu_keyboard()
    )


# Остальные обработчики
@dp.message(lambda message: message.text == "📝 Регистрация в ФГИС ОПВК")
async def registration_guide(message: types.Message):
    guide_text = md.text(
        md.bold("📌 Пошаговая инструкция по регистрации:"),
        md.text("1. Перейдите на", md.hlink("официальный сайт ФГИС ОПВК", "https://qisopvk.ru")),
        "2. Заполните форму регистрации (ИНН, контактные данные).",
        "3. Подтвердите email и настройте электронную подпись.",
        "4. Загрузите документы для верификации.",
        md.text("\nПодробнее:", md.hlink("Инструкция PDF",
                                         "https://gisopvk.ru/media/files/filepublic/d/a/a/daa6eeceb30a1625.%D0%BA%D0%B0%D0%BA-%D0%BF%D1%80%D0%BE%D0%BF%D0%B8%D1%81%D0%B0%D1%82%D1%8C-%D0%BF%D1%80%D0%B0%D0%B2%D0%B0-%D0%B4%D0%BE%D1%81%D1%82%D1%83%D0%BF%D0%B0-%D1%81%D0%BE%D1%82%D1%80%D1%83%D0%B4%D0%BD%D0%B8%D0%BA%D1%83.pdf")),
        sep="\n\n"
    )
    await message.answer(guide_text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())


@dp.message(lambda message: message.text == "🔧 Настройка электронной подписи")
async def digital_signature_guide(message: types.Message):
    guide_text = md.text(
        md.bold("🔐 Как настроить электронную подпись (ЭП):"),
        "1. Получите ЭП в аккредитованном удостоверяющем центре.",
        "2. Установите ПО для работы с ЭП (например, КриптоПро).",
        "3. Настройте браузер для поддержки ЭП.",
        md.text("\nПодробнее:", md.hlink("Памятка по ЭП",
                                         "https://gisopvk.ru/media/files/filepublic/8/d/8/8d8c960b707c8b38.%D0%BF%D0%B0%D0%BC%D1%8F%D1%82%D0%BA%D0%B0-%D1%8D%D0%BF_1.pdf")),
        sep="\n\n"
    )
    await message.answer(guide_text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())


# Расчет стоимости
@dp.message(lambda message: message.text == "💳 Расчет стоимости утилизации")
async def start_calculation(message: types.Message, state: FSMContext):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="I класс")],
            [types.KeyboardButton(text="II класс")],
            [types.KeyboardButton(text="🏠 Главное меню")]
        ],
        resize_keyboard=True
    )
    await message.answer("Выберите класс отходов:", reply_markup=keyboard)
    await state.set_state(WasteCalculation.waiting_for_waste_class)


@dp.message(WasteCalculation.waiting_for_waste_class)
async def choose_waste_class(message: types.Message, state: FSMContext):
    if message.text == "🏠 Главное меню":
        await return_to_main_menu(message, state)
        return

    if message.text not in ["I класс", "II класс"]:
        await message.answer("Пожалуйста, выберите класс из предложенных вариантов.", reply_markup=main_menu_keyboard())
        return

    await state.update_data(waste_class=message.text)
    await message.answer("Введите объем отходов (в тоннах):", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(WasteCalculation.waiting_for_waste_amount)


@dp.message(WasteCalculation.waiting_for_waste_amount)
async def calculate_cost(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число (например, 5.2).", reply_markup=main_menu_keyboard())
        return

    data = await state.get_data()
    waste_class = data['waste_class']

    rates = {
        "I класс": 222907.36,
        "II класс": 62468.26
    }
    cost = rates[waste_class] * amount
    await message.answer(
        md.text(
            md.bold("💰 Стоимость утилизации:"),
            md.text(f"• Класс отходов: {waste_class}"),
            md.text(f"• Объем: {amount} тонн"),
            md.text(f"• Итого: {cost:,.2f} руб. (без НДС)"),
            sep="\n\n"
        ),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()  # Возвращаем меню после расчета
    )
    await state.clear()

@dp.message(lambda message: message.text == "ℹ️ Справка")
async def show_help(message: types.Message):
    help_text = md.text(
        md.bold("📚 Справка по боту:"),
        md.text("Я помогаю работать с ФГИС ОПВК. Вот что я умею:"),
        md.text("• 📝 Регистрация в системе — пошаговая инструкция"),
        md.text("• 💳 Расчет стоимости утилизации отходов I/II класса"),
        md.text("• 🔧 Настройка электронной подписи — руководство"),
        md.text("\nПросто выберите нужный пункт в меню."),
        sep="\n\n"
    )
    await message.answer(help_text, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())

# Запуск бота
async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    import asyncio

    asyncio.run(main())