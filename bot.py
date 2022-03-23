import os
import random
import telebot
from telebot import types
from SimpleQIWI import *
from datetime import datetime, timedelta
from dotenv import dotenv_values
from pymongo import MongoClient
import sys

if "-docker" in sys.argv:
    mongo_client = MongoClient(os.getenv("DB_HOST"), int(os.getenv("DB_PORT")))
    db = mongo_client[os.getenv("DB_NAME")]
    client = telebot.TeleBot(os.getenv("TOKEN_BOT"))
    api = QApi(token=os.getenv("TOKEN_QIWI"), phone=os.getenv("PHONE_QIWI"))
    public_key_qiwi = os.getenv("PUBLIC_KEY_QIWI")
    download_str = f"[Скачать для windows](https://openvpn.net/downloads/openvpn-connect-v3-windows.msi)\n[Скачать для mac](https://openvpn.net/downloads/openvpn-connect-v3-macos.dmg)\n[Скачать для android](https://play.google.com/store/apps/details?id=net.openvpn.openvpn)\n[Скачать для iphone](https://itunes.apple.com/us/app/openvpn-connect/id590379981?mt=8)"
    help_str = f"[Настройка для windows]({os.getenv('HELP_WINDOWS_URL')})\n[Настройка для mac]({os.getenv('HELP_MAC_URL')})\n[Настройка для android]({os.getenv('HELP_ANDROID_URL')})\n[Настройка для iphone]({os.getenv('HELP_IPHONE_URL')})"
    pay_help_str = f"[Оплата картой]({os.getenv('CARD_PAY_URL_HELP')})\n[Оплата qiwi]({os.getenv('QIWI_PAY_URL_HELP')})"
    channel = os.getenv("CHANNEL")
else:
    config = dotenv_values(".env")
    mongo_client = MongoClient("localhost", int(config["DB_PORT"]))
    db = mongo_client[config["DB_NAME"]]
    client = telebot.TeleBot(config["TOKEN_BOT"])
    api = QApi(token=config["TOKEN_QIWI"], phone=config["PHONE_QIWI"])
    public_key_qiwi = config["PUBLIC_KEY_QIWI"]
    download_str = f"[Скачать для windows](https://openvpn.net/downloads/openvpn-connect-v3-windows.msi)\n[Скачать для mac](https://openvpn.net/downloads/openvpn-connect-v3-macos.dmg)\n[Скачать для android](https://play.google.com/store/apps/details?id=net.openvpn.openvpn)\n[Скачать для iphone](https://itunes.apple.com/us/app/openvpn-connect/id590379981?mt=8)"
    help_str = f"[Настройка для windows]({config['HELP_WINDOWS_URL']})\n[Настройка для mac]({config['HELP_MAC_URL']})\n[Настройка для android]({config['HELP_ANDROID_URL']})\n[Настройка для iphone]({config['HELP_IPHONE_URL']})"
    pay_help_str = f"[Оплата картой]({config['CARD_PAY_URL_HELP']})\n[Оплата qiwi]({config['QIWI_PAY_URL_HELP']})"
    channel = config["CHANNEL"]

users_collection = db.users


def get_buy_url(uid, price):
    link = f"https://oplata.qiwi.com/create?publicKey={public_key_qiwi}&amount={price}&comment={uid}"
    return link


def check_license(uid, cid):
    user = users_collection.find_one({"_id": uid})
    if not user["license"]:
        client.send_message(cid, f"⛔️ Лицензия неактивна!\n\nНажмите /buy для оплаты")
        return False
    return True


def check_payment(payid, price):
    for payments in api.payments["data"]:
        if (
            (payments["comment"] == payid)
            and (payments["status"] == "SUCCESS")
            and (payments["sum"]["amount"] == price)
        ):
            return True


@client.message_handler(commands=["start"])
def start(message):
    try:
        cid = message.chat.id
        uid = message.from_user.id
        if users_collection.find_one({"_id": uid}) is None:
            users_collection.insert_one(
                {"_id": uid, "access": 0, "payments": 0, "license": False}
            )
            client.send_message(
                cid,
                f"✋ *Добро пожаловать!*\n\nЭтот бот поможет вам установить vpn на ваши устройства\n\n📲 Подпишитесь на наш канал @withVpnChannel\n\n📕 Нажмите на /manuals для помощи по настройке vpn подключения\n🗿 Нажмите на /about для получения информации о vpn, боте и создателях бота\n💳 Нажмите на /buy для покупки лицензии\n🧾 Нажмите на /help для получения списка всех функций\n\nКстати слева есть кнопка *≡ Меню*, там тоже список всех команд",
                parse_mode="Markdown",
            )
        else:
            client.send_message(
                cid,
                f"🤝 *Вы уже зарегистрированы!*\n\n📕 Нажмите на /manuals для помощи по настройке vpn подключения\n🗿 Нажмите на /about для получения информации о vpn, боте и создателях бота\n🧾 Нажмите на /help для получения списка всех функций",
                parse_mode="Markdown",
            )
    except:
        client.send_message(cid, f"🚫 Ошибка при выполнении команды")


@client.message_handler(commands=["servers"])
def servers(message):
    try:
        cid = message.chat.id
        uid = message.from_user.id
        if os.path.exists("vpns/lock"):
            client.send_message(
                cid, f"🔄 Список обновляется, нажмите на /servers через пару секунд"
            )
            return
        if not check_license(uid, cid):
            return
        text = f"🌏 *Выберите сервер*"
        rmk = types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        for server in os.listdir("vpns/old"):
            if (server == ".DS_Store") or not os.listdir(f"vpns/old/{server}"):
                continue
            buttons.append(
                types.InlineKeyboardButton(
                    text=f"{server}",
                    callback_data=f"select_{server}",
                ),
            )
        rmk.add(*buttons)
        client.send_message(
            cid,
            text,
            parse_mode="Markdown",
            reply_markup=rmk,
        )
    except:
        client.send_message(cid, f"🚫 Ошибка при выполнении команды")


@client.callback_query_handler(lambda call: call.data.partition("_")[0] == "select")
def select_callback(call):
    try:
        if os.path.exists("vpns/lock"):
            client.send_message(
                call.message.chat.id,
                f"🔄 Список обновляется, нажмите на /servers через пару секунд",
            )
            return
        if call.data.partition("_")[0] == "select":
            if not check_license(call.from_user.id, call.message.chat.id):
                return
            server = call.data.partition("_")[2]
            configs_dir = f"vpns/old/{server}"
            config_file = open(
                os.path.join(configs_dir, random.choice(os.listdir(configs_dir)))
            )
            client.send_document(
                call.message.chat.id,
                config_file,
                caption=f"{server}\n\nНажмите на /manuals для просмотра видео по настройке vpn",
                visible_file_name=f"{datetime.now().strftime('%d%m%Y_%H%M')}_{server.replace(' ','')}.ovpn".lower(),
                parse_mode="Markdown",
            )
        client.answer_callback_query(callback_query_id=call.id)
    except:
        client.send_message(call.message.chat.id, f"🚫 Ошибка при выполнении команды")


@client.message_handler(commands=["profile", "myinfo", "myprofile"])
def myprofile(message):
    try:
        cid = message.chat.id
        uid = message.from_user.id
        user = users_collection.find_one({"_id": uid})
        license = "неактивна"
        if user["access"] == 0:
            accessname = "Пользователь"
        elif user["access"] == 1:
            accessname = "Администратор"
        elif user["access"] == 777:
            accessname = "Разработчик"
        if user["license"]:
            license = "активна"
        client.send_message(
            cid,
            f"*📇 Ваш профиль*\n\n👤 Ваш ID: `{user['_id']}`\n👑 Ваш уровень доступа: *{accessname}*\n🎟 Ваша лицензия: *{license}*",
            parse_mode="Markdown",
        )
    except:
        client.send_message(cid, f"🚫 Ошибка при выполнении команды")


@client.message_handler(commands=["buy"])
def buy(message):
    try:
        cid = message.chat.id
        uid = message.from_user.id
        user = users_collection.find_one({"_id": uid})
        text = f"😇 *Оплатить через qiwi или картой*\n\n"
        payid = str(uid) + str(user["payments"])
        rmk = types.InlineKeyboardMarkup()
        sum300 = types.InlineKeyboardButton(text="300₽", url=get_buy_url(payid, 300))
        success = types.InlineKeyboardButton(
            text="✅ я оплатил!", callback_data="success_pay"
        )
        rmk.add(sum300)
        rmk.add(success)
        client.send_message(
            cid,
            f"{text}1. Оплатите лицензию\n2. Нажмите *✅ я оплатил*",
            parse_mode="Markdown",
            reply_markup=rmk,
        )
    except:
        client.send_message(cid, f"🚫 Ошибка при выполнении команды")


@client.callback_query_handler(lambda call: call.data == "success_pay")
def success_pay(call):
    try:
        if call.data == "success_pay":
            uid = call.from_user.id
            cid = call.message.chat.id
            user = users_collection.find_one({"_id": uid})
            payid = str(uid) + str(user["payments"])
            if check_payment(payid, 300):
                client.send_message(
                    cid,
                    f"✅ Лицензия оплачена!\n\nНажмите /servers для выбор сервера",
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
                return
        client.send_message(cid, "🚫 Оплата не найдена!")
        client.answer_callback_query(callback_query_id=call.id)

    except:
        client.send_message(call.message.chat.id, f"🚫 Ошибка при выполнении команды")


@client.message_handler(commands=["help"])
def help(message):
    try:
        cid = message.chat.id
        uid = message.from_user.id
        user = users_collection.find_one({"_id": uid})
        if user["access"] >= 1:
            client.send_message(
                cid,
                "*🧾 Список команд*\n\n/start - старт бота\n/profile - ваш профиль\n/buy - купить лицензию\n/manuals - инструкции\n/servers - показать vpn сервера\n/support - написать в поддержку\n/about - о боте и создателях\n/help - список команд",
                parse_mode="Markdown",
            )
        else:
            client.send_message(
                cid,
                "*🧾 Список команд*\n\n/start - старт бота\n/profile - ваш профиль\n/buy - купить лицензию\n/manuals - инструкции\n/servers - показать vpn сервера\n/support - написать в поддержку\n/about - о боте и создателях\n/help - список команд",
                parse_mode="Markdown",
            )
    except:
        client.send_message(cid, f"🚫 Ошибка при выполнении команды")


@client.message_handler(commands=["support"])
def support(message):
    try:
        cid = message.chat.id
        client.send_message(
            cid,
            f"*🆘 Поддержка*\n\n📬 По всем вопросам просьба писать сюда: @withVpn",
            parse_mode="Markdown",
        )
    except:
        client.send_message(cid, f"🚫 Ошибка при выполнении команды")


@client.message_handler(commands=["about"])
def about(message):
    try:
        cid = message.chat.id
        client.send_message(
            cid,
            f"*ℹ️ О нас*\n\n🛰 A long time ago, in a galaxy far, far away…",
            parse_mode="Markdown",
        )
    except:
        client.send_message(cid, f"🚫 Ошибка при выполнении команды")


@client.message_handler(commands=["manuals"])
def manuals(message):
    try:
        cid = message.chat.id
        uid = message.from_user.id
        client.send_message(
            cid,
            f"*📺 Полезные ссылки и видео инструкции*\n\n*⬇️ Скачать необходимую программу*\n{download_str}\n\n*🛠 Как настроить*\n{help_str}",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except:
        client.send_message(cid, f"🚫 Ошибка при выполнении команды")


client.infinity_polling(timeout=10, long_polling_timeout=5)
