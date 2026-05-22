import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

BOT_TOKEN = "8862880187:AAEiiEwfOklNTMVdcQWOi2s2Dl6WZZPMljI"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальная база данных в оперативной памяти бота
# Структура: { user_id: { "weight_history": [...], "height": 178, "fat": 16.8, "age": 20 } }
USER_DATA = {}

# Состояния для калькулятора БЖУ
class CalForm(StatesGroup):
    goal = State()
    weight = State()
    height = State()
    age = State()
    fat_percentage = State()

# Состояние для быстрой записи веса
class TrackForm(StatesGroup):
    new_weight = State()

# Главное меню
def main_menu():
    kb = [
        [KeyboardButton(text="📊 Рассчитать БЖУ (Выбор цели)")],
        [KeyboardButton(text="📉 Записать текущий вес"), KeyboardButton(text="📈 Моя статистика")],
        [KeyboardButton(text="ℹ️ О концепции"), KeyboardButton(text="📋 Мои метрики")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Меню выбора целей
def goals_menu():
    kb = [
        [KeyboardButton(text="🔥 Похудение"), KeyboardButton(text="⚡ Рекомпозиция")],
        [KeyboardButton(text="💪 Набор массы")],
        [KeyboardButton(text="❌ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Функция для инициализации дефолтных параметров пользователя (твои базовые метрики)
def init_user_if_not_exists(user_id):
    if user_id not in USER_DATA:
        USER_DATA[user_id] = {
            "weight_history": [75.0],  # Исходный вес
            "height": 178.0,           # Исходный рост
            "fat": 16.8,               # Исходный процент жира
            "age": 20                  # Исходный возраст
        }

@dp.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено 🤝", reply_markup=main_menu())

@dp.message(F.text == "/start")
async def cmd_start(message: Message):
    user_id = message.from_user.id
    init_user_if_not_exists(user_id)
    
    text = (
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        f"Я бот НутриПланер. Помогу рассчитать БЖУ под любую цель и вести историю изменения веса 📊"
    )
    await message.answer(text, reply_markup=main_menu())

@dp.message(F.text == "ℹ️ О концепции")
async def about_concept(message: Message):
    text = (
        "💡 Наши режимы работы:\n\n"
        "🔥 Похудение — создаем дефицит калорий (~15-20%) для снижения общего веса.\n"
        "⚡ Рекомпозиция — небольшой дефицит и много белка, чтобы жечь жир и держать мышцы.\n"
        "💪 Набор массы — профицит калорий (~10-15%) и тренировки для роста мышц."
    )
    await message.answer(text)

@dp.message(F.text == "📋 Мои метрики")
async def user_metrics(message: Message):
    user_id = message.from_user.id
    init_user_if_not_exists(user_id)
    
    # Забираем актуальные сохраненные данные пользователя из нашей "базы"
    profile = USER_DATA[user_id]
    current_weight = profile["weight_history"][-1]
    
    text = (
        "📋 Твои актуальные сохраненные метрики:\n\n"
        f"• Рост: {profile['height']:.0f} см\n"
        f"• Вес: {current_weight:.1f} кг\n"
        f"• Процент жира: {profile['fat']:.1f}%\n"
        f"• Возраст: {profile['age']} лет\n\n"
        "Параметры обновляются автоматически при расчете БЖУ или быстрой записи веса! 👇"
    )
    await message.answer(text)

# --- БЛОК 1: КАЛЬКУЛЯТОР БЖУ С ВЫБОРОМ И СОХРАНЕНИЕМ ПАРАМЕТРОВ ---

@dp.message(F.text == "📊 Рассчитать БЖУ (Выбор цели)")
async def start_calculator(message: Message, state: FSMContext):
    await state.set_state(CalForm.goal)
    await message.answer("🎯 Выберите вашу цель:", reply_markup=goals_menu())

@dp.message(CalForm.goal, F.text.in_(["🔥 Похудение", "⚡ Рекомпозиция", "💪 Набор массы"]))
async def process_goal(message: Message, state: FSMContext):
    await state.update_data(goal=message.text)
    await state.set_state(CalForm.weight)
    await message.answer("⚖️ Шаг 1: Напиши свой вес в кг (например: 75)", reply_markup=main_menu())

@dp.message(CalForm.weight)
async def process_weight(message: Message, state: FSMContext):
    try:
        weight = float(message.text.replace(",", "."))
        await state.update_data(weight=weight)
        await state.set_state(CalForm.height)
        await message.answer("📏 Шаг 2: Напиши свой рост в см (например: 178)")
    except ValueError:
        await message.answer("❌ Напиши просто число (например: 75)")

@dp.message(CalForm.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = float(message.text.replace(",", "."))
        await state.update_data(height=height)
        await state.set_state(CalForm.age)
        await message.answer("🗓 Шаг 3: Напиши свой возраст (например: 20)")
    except ValueError:
        await message.answer("❌ Напиши просто число (например: 178)")

@dp.message(CalForm.age)
async def process_age(message: Message, state: FSMContext):
    try:
        age = int(message.text)
        await state.update_data(age=age)
        await state.set_state(CalForm.fat_percentage)
        await message.answer("📉 Шаг 4: Напиши процент жира в теле (если не знаешь, напиши 20)")
    except ValueError:
        await message.answer("❌ Напиши просто число (например: 20)")

@dp.message(CalForm.fat_percentage)
async def process_calc_final(message: Message, state: FSMContext):
    try:
        fat = float(message.text.replace(",", "."))
        await state.update_data(fat_percentage=fat)
        user_data = await state.get_data()
        await state.clear()

        user_id = message.from_user.id
        init_user_if_not_exists(user_id)

        goal = user_data['goal']
        w = user_data['weight']
        h = user_data['height']
        a = user_data['age']
        
        # СОХРАНЕНИЕ: Записываем все введенные параметры в профиль пользователя
        USER_DATA[user_id]["height"] = h
        USER_DATA[user_id]["fat"] = fat
        USER_DATA[user_id]["age"] = a
        USER_DATA[user_id]["weight_history"].append(w) # Добавляем вес в историю изменений

        lbm = w * (1 - fat / 100)
        bmr = 370 + (21.6 * lbm)
        maintenance = bmr * 1.2
        
        if goal == "🔥 Похудение":
            target_calories = int(maintenance * 0.8)
            proteins = int(w * 2.0)
            fats = int(w * 0.8)
        elif goal == "⚡ Рекомпозиция":
            target_calories = int(maintenance * 0.9)
            proteins = int(w * 2.2)
            fats = int(w * 0.9)
        else:
            target_calories = int(maintenance * 1.15)
            proteins = int(w * 1.8)
            fats = int(w * 1.0)
            
        carbs = int((target_calories - (proteins * 4) - (fats * 9)) / 4)

        text = (
            f"🎯 Твой расчет для цели [{goal}]:\n\n"
            f"• Калории: {target_calories} ккал/день\n"
            f"• Сухой вес тела: {lbm:.1f} кг\n\n"
            f"🍏 Белки: {proteins} г\n"
            f"🥑 Жиры: {fats} г\n"
            f"🍞 Углеводы: {carbs} г\n\n"
            f"✨ Все параметры успешно сохранены в «📋 Мои метрики»!"
        )
        await message.answer(text, reply_markup=main_menu())
    except ValueError:
        await message.answer("❌ Напиши просто число (например: 16)")

# --- БЛОК 2: СТАТИСТИКА И ИЗМЕНЕНИЕ ВЕСА ---

@dp.message(F.text == "📉 Записать текущий вес")
async def start_tracking(message: Message, state: FSMContext):
    await state.set_state(TrackForm.new_weight)
    await message.answer("⚖️ Напиши свой актуальный вес сегодня в кг:")

@dp.message(TrackForm.new_weight)
async def process_tracking(message: Message, state: FSMContext):
    try:
        new_weight = float(message.text.replace(",", "."))
        await state.clear()
        
        user_id = message.from_user.id
        init_user_if_not_exists(user_id)
        
        history = USER_DATA[user_id]["weight_history"]
        
        if len(history) > 0:
            diff = new_weight - history[-1]
            diff_text = f" ({'+' if diff > 0 else ''}{diff:.1f} кг с прошлого замера)"
        else:
            diff_text = ""
            
        # СОХРАНЕНИЕ: Обновляем вес в истории профиля пользователя
        USER_DATA[user_id]["weight_history"].append(new_weight)
            
        await message.answer(f"✅ Вес {new_weight} кг успешно записан!{diff_text}\nМетрики обновлены.", reply_markup=main_menu())
    except ValueError:
        await message.answer("❌ Напиши просто число (например: 74.5)")

@dp.message(F.text == "📈 Моя статистика")
async def show_statistics(message: Message):
    user_id = message.from_user.id
    init_user_if_not_exists(user_id)
    
    history = USER_DATA[user_id]["weight_history"]
    
    if not history or len(history) <= 1 and history[0] == 75.0:
        await message.answer("📈 У вас пока нет сохраненных замеров изменений веса. Нажмите «📉 Записать текущий вес»")
        return
        
    text = "📈 История изменения вашего веса:\n\n"
    for idx, weight in enumerate(history, 1):
        text += f"{idx}. {weight:.1f} кг\n"
        
    if len(history) > 1:
        total_diff = history[-1] - history[0]
        text += f"\n📊 Всего изменено: {'+' if total_diff > 0 else ''}{total_diff:.1f} кг за все время."
        
    await message.answer(text)

async def main():
    print("Бот обновлен и запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
