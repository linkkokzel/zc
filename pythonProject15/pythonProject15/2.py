import requests
import random
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters
)
from googletrans import Translator
import os
from dotenv import load_dotenv

# Вставьте сюда токен вашего бота от @BotFather
TELEGRAM_TOKEN = '7912178851:AAH7a4ejDRUqwaaSV75QME-k0FJCSNMCrxQ'

translator = Translator()

# --- Функции перевода ---
def translate_to_en(text: str) -> str:
    try:
        return translator.translate(text, dest='en').text
    except Exception:
        return text

# --- Форматирование информации о стране ---
def format_country_info(country):
    name = country.get('name', {}).get('common', 'Нет данных')
    capital = country.get('capital', ['Нет данных'])[0]
    population = country.get('population', 'Нет данных')
    languages = ', '.join(country.get('languages', {}).values()) or 'Нет данных'
    flag_url = country.get('flags', {}).get('png', '')
    currencies = country.get('currencies', {})
    currency = ', '.join([f"{v.get('name', '')} ({k})" for k, v in currencies.items()]) if currencies else 'Нет данных'
    region = country.get('region', 'Нет данных')
    return (
        f"🌍 <b>{name}</b>\n"
        f"🏙 Столица: {capital}\n"
        f"👥 Население: {population}\n"
        f"🗣 Языки: {languages}\n"
        f"💰 Валюта: {currency}\n"
        f"🌐 Регион: {region}\n"
        f"🏳️ Флаг: <a href='{flag_url}'>ссылка</a>"
    )

# --- Получение информации о стране по названию ---
def get_country_info_by_name(name: str) -> str:
    name_en = translate_to_en(name)
    url = f'https://restcountries.com/v3.1/name/{name_en}'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return format_country_info(data[0])
    except Exception:
        return "❌ Страна не найдена или произошла ошибка."

# --- Получение информации о стране по столице ---
def get_country_info_by_capital(capital: str) -> str:
    capital_en = translate_to_en(capital)
    url = f'https://restcountries.com/v3.1/capital/{capital_en}'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return format_country_info(data[0])
    except Exception:
        return "❌ Страна по такой столице не найдена или произошла ошибка."

# --- Получение случайного факта для игры ---
def get_random_country_fact():
    url = 'https://restcountries.com/v3.1/all'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        countries = response.json()
        country = random.choice(countries)
        name = country.get('name', {}).get('common', 'Нет данных')
        facts = []
        if 'capital' in country:
            facts.append(f"Столица — {country['capital'][0]}")
        if 'region' in country:
            facts.append(f"Регион — {country['region']}")
        if 'languages' in country:
            lang = list(country['languages'].values())[0]
            facts.append(f"Один из языков — {lang}")
        if 'currencies' in country:
            curr = list(country['currencies'].values())[0].get('name', '')
            facts.append(f"Валюта — {curr}")
        if not facts:
            facts.append("Это независимая страна.")
        fact = random.choice(facts)
        return name, fact
    except Exception:
        return None, "Ошибка при получении факта."

# --- Хендлеры ---

GAME_ANSWER = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я помогу узнать информацию о странах.\n"
        "Команды:\n"
        "/info <страна> — информация о стране\n"
        "/capital <столица> — поиск страны по столице\n"
        "/game — игра «Угадай страну по факту»\n"
        "Можно писать на русском или английском."
    )

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите название страны после /info.")
        return
    name = ' '.join(context.args)
    result = get_country_info_by_name(name)
    await update.message.reply_html(result, disable_web_page_preview=False)

async def capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Пожалуйста, укажите название столицы после /capital.")
        return
    capital_name = ' '.join(context.args)
    result = get_country_info_by_capital(capital_name)
    await update.message.reply_html(result, disable_web_page_preview=False)

async def game_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country, fact = get_random_country_fact()
    if not country:
        await update.message.reply_text("Не удалось получить факт. Попробуйте позже.")
        return
    GAME_ANSWER[user_id] = country.lower()
    await update.message.reply_text(
        f"Угадай страну по факту:\n<b>{fact}</b>\n\nНапиши свой ответ.",
        parse_mode="HTML"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    if user_id in GAME_ANSWER:
        guess = text.lower()
        answer = GAME_ANSWER[user_id].lower()
        guess_en = translate_to_en(guess).lower()
        if guess == answer or guess_en == answer:
            await update.message.reply_text(f"✅ Верно! Это была страна: {answer.title()}")
        else:
            await update.message.reply_text("❌ Неправильно! Попробуй ещё раз или напиши /game для нового вопроса.")
        del GAME_ANSWER[user_id]
    else:
        # Если не в игре — ищем страну по названию или столице
        result = get_country_info_by_name(text)
        if "не найдена" in result.lower():
            result = get_country_info_by_capital(text)
        await update.message.reply_html(result, disable_web_page_preview=False)

# --- Запуск бота ---

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("capital", capital))
    app.add_handler(CommandHandler("game", game_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    app.run_polling()


load_dotenv()
API_KEY = os.getenv('API_KEY')
if __name__ == '__main__':
    main()