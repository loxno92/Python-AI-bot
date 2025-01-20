import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, CallbackContext, CallbackQueryHandler
from telegram.ext import Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, Update
import openai


TELEGRAM_BOT_TOKEN = ""
OPENAI_API_KEY = ""
openai.api_key = OPENAI_API_KEY

(TEMP) = range(1)
user_settings = {}

texts = {
    "en": {
        "start_message": "Hello! I'm a bot that can answer your questions. Just write me your question.",
        "help_message": "Just write me your question, and I'll try to answer it.",
        "settings_message": "⚙️ Bot Settings",
        "change_language": "Change Language",
        "set_temperature": "Set Creativity",
        "language_prompt": "Choose your language:",
        "temperature_prompt": "Enter the temperature value (0-1):",
        "temperature_set": "Creativity set to {}.",
        "temperature_invalid": "Please enter a value between 0 and 1.",
        "temperature_numeric_error": "Please enter a valid numeric value.",
        "cancel_message": "Action cancelled.",
        "openai_error": "Sorry, there was a problem processing your question.",
        "language_set": "Language set to {}.",
        "back_to_settings": "Back to Settings",
    },
    "ru": {
        "start_message": "Привет! Я бот, который может отвечать на вопросы. Просто напиши мне свой вопрос.",
        "help_message": "Просто напиши мне свой вопрос, и я постараюсь ответить.",
        "settings_message": "⚙️ Настройки бота",
        "change_language": "Сменить язык",
        "set_temperature": "Настроить креативность",
        "language_prompt": "Выберите ваш язык:",
        "temperature_prompt": "Введите значение температуры (0-1):",
        "temperature_set": "Креативность установлена на {}.",
        "temperature_invalid": "Пожалуйста, введите значение от 0 до 1.",
        "temperature_numeric_error": "Пожалуйста, введите корректное числовое значение.",
        "cancel_message": "Действие отменено.",
        "openai_error": "Извини, возникла проблема с обработкой твоего вопроса.",
        "language_set": "Язык установлен на {}.",
        "back_to_settings": "Назад в настройки",
    },
}

def get_text(user_id, key):
    language = user_settings.get(user_id, {}).get("language", "en")
    return texts.get(language, texts["en"]).get(key, texts["en"][key])

def settings(update, context: CallbackContext):
    user_id = update.message.from_user.id
    language = user_settings.get(user_id, {}).get("language", "en")
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "change_language"), callback_data='change_language')],
        [InlineKeyboardButton(get_text(user_id, "set_temperature"), callback_data='set_temperature')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(get_text(user_id, "settings_message"), reply_markup=reply_markup)

def change_language(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    keyboard = [
        [InlineKeyboardButton("English", callback_data='lang_en'),
         InlineKeyboardButton("Русский", callback_data='lang_ru')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(get_text(user_id, "language_prompt"), reply_markup=reply_markup)

def set_language_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    language_code = query.data.split('_')[1]
    user_settings[user_id]["language"] = language_code
    query.edit_message_text(get_text(user_id, "language_set").format(language_code))
    show_settings_buttons(update, context)

def set_temperature_start(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    query.edit_message_text(get_text(user_id, "temperature_prompt"))
    return TEMP

def process_temperature(update, context: CallbackContext):
    user_id = update.message.from_user.id
    try:
        temperature = float(update.message.text)
        if 0 <= temperature <= 1:
            user_settings[user_id]["temperature"] = temperature
            update.message.reply_text(get_text(user_id, "temperature_set").format(temperature))
            show_settings_buttons(update, context)
            return ConversationHandler.END
        else:
            update.message.reply_text(get_text(user_id, "temperature_invalid"))
            return TEMP
    except ValueError:
        update.message.reply_text(get_text(user_id, "temperature_numeric_error"))
        return TEMP

def show_settings_buttons(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    language = user_settings.get(user_id, {}).get("language", "en")
    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "change_language"), callback_data='change_language')],
        [InlineKeyboardButton(get_text(user_id, "set_temperature"), callback_data='set_temperature')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        update.callback_query.message.reply_text(get_text(user_id, "settings_message"), reply_markup=reply_markup)
    else:
        update.message.reply_text(get_text(user_id, "settings_message"), reply_markup=reply_markup)

def start(update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id not in user_settings:
        user_settings[user_id] = {"language": "en", "temperature": 0.7, "context": []}

    keyboard = [
        [telegram.KeyboardButton("⚙️ Settings")],
        [telegram.KeyboardButton("❓ Help")]
    ]
    reply_markup = telegram.ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text(get_text(user_id, "start_message"), reply_markup=reply_markup)

def help_command(update, context):
    user_id = update.message.from_user.id
    update.message.reply_text(get_text(user_id, "help_message"))

def handle_message(update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_text = update.message.text

    if user_id not in user_settings:
        user_settings[user_id] = {"language": "en", "temperature": 0.7, "context": []}

    if user_text == "⚙️ Settings":
        return settings(update, context)
    elif user_text == "❓ Help":
        return help_command(update, context)

    language = user_settings[user_id]["language"]
    temperature = user_settings[user_id]["temperature"]
    context_history = user_settings[user_id]["context"]

    context_history.append({"role": "user", "content": user_text})

    if len(context_history) > 10:
        context_history.pop(0)

    response = get_openai_response(context_history, language, temperature)

    context_history.append({"role": "assistant", "content": response})
    user_settings[user_id]["context"] = context_history

    update.message.reply_text(response)

def get_openai_response(messages, language, temperature):
    try:
        messages_for_api = []
        messages_for_api.append({"role": "system", "content": f"You are a helpful assistant. Respond in {language}."})
        messages_for_api.extend(messages)

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages_for_api,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=temperature,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Ошибка при обращении к OpenAI API: {e}")
        return get_text(None, "openai_error")

def cancel(update, context):
    user_id = update.message.from_user.id
    update.message.reply_text(get_text(user_id, "cancel_message"))
    return ConversationHandler.END

def error(update, context):
    print(f"Update {update} вызвал ошибку {context.error}")

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("settings", settings))

    dp.add_handler(CallbackQueryHandler(change_language, pattern='^change_language$'))
    dp.add_handler(CallbackQueryHandler(set_language_callback, pattern='^lang_'))
    dp.add_handler(CallbackQueryHandler(set_temperature_start, pattern='^set_temperature$'))

    conv_handler_temp = ConversationHandler(
        entry_points=[CallbackQueryHandler(set_temperature_start, pattern='^set_temperature$')],
        states={
            TEMP: [MessageHandler(Filters.text & ~Filters.command, process_temperature)],
        },
        fallbacks=[],
    )
    dp.add_handler(conv_handler_temp)

    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()