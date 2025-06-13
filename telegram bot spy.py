import telebot
import random

BOT_TOKEN = ''

bot = telebot.TeleBot(BOT_TOKEN)

class Game:
    def __init__(self, chat_id, player_ids):
        self.chat_id = chat_id
        self.player_ids = player_ids
        self.location = None
        self.spy = None
        self.players_info = {}  # Словарь для хранения информации об игроках (имя, уведомлен/нет)
        self.game_started = False

    def start_game(self, locations):
        """
        Запускает игру.
        Выбирает локацию, шпиона, отправляет уведомления игрокам.
        """
        if not self.player_ids:
            bot.send_message(self.chat_id, "Недостаточно игроков для начала игры.")
            return False

        self.location = random.choice(locations)
        self.spy = random.choice(self.player_ids)

        for player_id in self.player_ids:
            try:
                user = bot.get_chat_member(self.chat_id, player_id).user
                self.players_info[player_id] = {'name': user.first_name, 'notified': False}  # Инициализируем информацию об игроке
            except telebot.apihelper.ApiTelegramException as e:
                print(f"Error getting user info: {e}")  # Логируем ошибки

        self.send_player_notifications()
        self.game_started = True
        return True

    def send_player_notifications(self):
        """
        Отправляет уведомления игрокам о их роли и локации.
        """
        for player_id in self.player_ids:
            try:
                if player_id == self.spy:
                    bot.send_message(player_id, "Ты шпион! Постарайся угадать локацию.")
                else:
                    bot.send_message(player_id, f"Ты не шпион. Локация: {self.location}")
                self.players_info[player_id]['notified'] = True # Отмечаем, что игрок уведомлен
            except telebot.apihelper.ApiTelegramException as e:
                # Обрабатываем ошибку, если бот не может написать пользователю напрямую
                print(f"Error sending message to user {player_id}: {e}")
                bot.send_message(self.chat_id, f"Не могу отправить сообщение игроку {self.players_info[player_id]['name']}. Пожалуйста, убедитесь, что он запустил бота и разрешил ему писать.")
                self.players_info[player_id]['notified'] = False  # Отмечаем, что не уведомлен

    def is_player_notified(self, player_id):
        """
        Проверяет, был ли уведомлен игрок.
        """
        return self.players_info.get(player_id, {}).get('notified', False)

    def end_game(self):
        """
        Завершает игру, сбрасывает состояние.
        """
        self.location = None
        self.spy = None
        self.players_info = {}
        self.game_started = False
        bot.send_message(self.chat_id, "Игра завершена.")

# Глобальные переменные
games = {}  # Словарь для хранения игр по chat_id
locations = [
    "Самолет",
    "Банк",
    "Школа",
    "Больница",
    "Ресторан",
    "Кинотеатр",
    "Пляж",
    "Космическая станция",
    "Подводная лодка",
    "Цирк"
]

# --- Обработчики команд ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я бот для игры в Шпиона. Используй /help для списка команд.")

@bot.message_handler(commands=['help'])
def help(message):
    help_text = """
Команды:
/start - Начать общение с ботом
/help - Показать это сообщение
/newgame - Начать новую игру (только для администраторов чата)
/startgame - Начать игру (только для администраторов чата)
/location - Получить список локаций
/endgame - Завершить игру (только для администраторов чата)
"""
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['newgame'])
def new_game(message):
    chat_id = message.chat.id
    try:
        # Проверяем, является ли пользователь администратором чата
        chat_member = bot.get_chat_member(chat_id, message.from_user.id)
        if chat_member.status in ['creator', 'administrator']:
            if chat_id in games:
                bot.reply_to(message, "Игра уже создана в этом чате.  Используйте /endgame, чтобы завершить текущую игру.")
                return

            # Создаем кнопки
            markup = telebot.types.InlineKeyboardMarkup()
            join_button = telebot.types.InlineKeyboardButton(text="Присоединиться", callback_data='join_game')
            markup.add(join_button)

            games[chat_id] = Game(chat_id, [])
            bot.send_message(chat_id, "Новая игра создана. Нажмите кнопку, чтобы присоединиться:", reply_markup=markup)
        else:
            bot.reply_to(message, "Только администраторы могут начинать игру.")
    except telebot.apihelper.ApiTelegramException as e:
        bot.reply_to(message, f"Не удалось проверить права администратора. Ошибка: {e}")


# Обработчик callback-запросов (нажатий на кнопки)
@bot.callback_query_handler(func=lambda call: call.data == 'join_game')
def join_game_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id

    if chat_id not in games:
        bot.answer_callback_query(call.id, "Игра не найдена.")
        return

    if user_id in games[chat_id].player_ids:
        bot.answer_callback_query(call.id, "Вы уже в игре.")  # Отвечаем на callback, чтобы убрать "часики" на кнопке
        return

    games[chat_id].player_ids.append(user_id)
    try:
        user = call.from_user
        bot.send_message(chat_id, f"{user.first_name} присоединился к игре.")
    except:
        bot.send_message(chat_id, "Новый игрок присоединился к игре.") #Fallback в случае ошибки с получением имени пользователя
    bot.answer_callback_query(call.id, "Вы присоединились к игре!") #Уведомление после нажатия кнопки

@bot.message_handler(commands=['startgame'])
def start_the_game(message):
    chat_id = message.chat.id

    if chat_id not in games:
        bot.reply_to(message, "Игра не создана. Используйте /newgame чтобы начать.")
        return

    try:
        # Проверяем, является ли пользователь администратором чата
        chat_member = bot.get_chat_member(chat_id, message.from_user.id)
        if chat_member.status in ['creator', 'administrator']:
            if games[chat_id].start_game(locations):
                bot.send_message(chat_id, "Игра началась!  Игроки получили свои роли.")
            else:
                bot.send_message(chat_id, "Не удалось начать игру.")

        else:
            bot.reply_to(message, "Только администраторы могут начинать игру.")
    except telebot.apihelper.ApiTelegramException as e:
        bot.reply_to(message, f"Не удалось проверить права администратора. Ошибка: {e}")

@bot.message_handler(commands=['location'])
def show_locations(message):
    bot.reply_to(message, f"Возможные локации: {', '.join(locations)}")

@bot.message_handler(commands=['endgame'])
def end_the_game(message):
    chat_id = message.chat.id

    if chat_id not in games:
        bot.reply_to(message, "Игра не создана.")
        return

    try:
        # Проверяем, является ли пользователь администратором чата
        chat_member = bot.get_chat_member(chat_id, message.from_user.id)
        if chat_member.status in ['creator', 'administrator']:
            games[chat_id].end_game()
            del games[chat_id]  # Удаляем игру из словаря
            bot.send_message(chat_id, "Игра завершена и удалена.")
        else:
            bot.reply_to(message, "Только администраторы могут завершить игру.")
    except telebot.apihelper.ApiTelegramException as e:
        bot.reply_to(message, f"Не удалось проверить права администратора. Ошибка: {e}")


# --- Запуск бота ---
if __name__ == '__main__':
    bot.infinity_polling()