import os
import random
import telebot
import configure
import sqlite3
from telebot import types
import threading
from SimpleQIWI import *
from datetime import datetime, timedelta

client = telebot.TeleBot(configure.config["tokenbot"])
db = sqlite3.connect("baza.db", check_same_thread=False)
sql = db.cursor()
lock = threading.Lock()
api = QApi(token=configure.config["tokenqiwi"], phone=configure.config["phoneqiwi"])

pay_help_str = f"[Оплата картой]({configure.config['pay_card_url']})\n[Оплата qiwi]({configure.config['pay_qiwi_url']})"
download_str = f"[Скачать для windows](https://openvpn.net/downloads/openvpn-connect-v3-windows.msi)\n[Скачать для mac](https://openvpn.net/downloads/openvpn-connect-v3-macos.dmg)\n[Скачать для android](https://play.google.com/store/apps/details?id=net.openvpn.openvpn)\n[Скачать для iphone](https://itunes.apple.com/us/app/openvpn-connect/id590379981?mt=8)"
help_str = f"[Настройка для windows]({configure.config['help_windows_url']})\n[Настройка для mac]({configure.config['help_mac_url']})\n[Настройка для android]({configure.config['help_android_url']})\n[Настройка для iphone]({configure.config['help_windows_url']})"

trial_minutes = 30

sql.execute(
    """CREATE TABLE IF NOT EXISTS users (id BIGINT, access INT, die_to text, payments INT)"""
)
sql.execute(
    """CREATE TABLE IF NOT EXISTS vpns (id INT, name TEXT, flag TEXT, use INT)"""
)
db.commit()


def check_license(uid, cid):
    user = sql.execute(f"SELECT * FROM users WHERE id = {uid}").fetchall()[0]
    current_date = datetime.today()
    die_to = datetime.strptime(user[2], "%Y-%m-%d %H:%M:%S.%f")
    if current_date < die_to:
        return True
    client.send_message(cid, f"⛔️ Лицензия закончилась!")
    return False


def get_buy_url(uid, price):
    publicKey = configure.config["publickey"]
    link = f"https://oplata.qiwi.com/create?publicKey={publicKey}&amount={price}&comment={uid}"
    return link


def check_payment(payid, price):
    for payments in api.payments["data"]:
        if (
            (payments["comment"] == payid)
            and (payments["status"] == "SUCCESS")
            and (payments["sum"]["amount"] == price)
        ):
            return True


def set_license(date_str, uid, days):
    die_to = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
    new_die_to = die_to + timedelta(days=days)
    sql.execute(
        f"UPDATE users SET payments = payments + 1, die_to = '{new_die_to}' WHERE id = {uid}"
    )
    db.commit()


@client.message_handler(commands=["start"])
def start(message):
    try:
        cid = message.chat.id
        uid = message.from_user.id
        current_date = datetime.today() + timedelta(minutes=trial_minutes)
        if sql.execute(f"SELECT id FROM users WHERE id = {uid}").fetchone() is None:
            sql.execute(f"INSERT INTO users VALUES ({uid}, 0, '{current_date}', 0)")
            client.send_message(
                cid,
                f"✋ Добро пожаловать!\n\nЭтот бот поможет вам установить vpn на ваши устройства\nБез лицензии вы можете получать случайный сервер раз в день\n\n⏳ Нажмите на /profile для просмотра вашей лицензии\n📕 Нажмите на /manuals для помощи активации лицензии и настройке vpn подключения\n🗿 Нажмите на /about для получения информации о vpn, боте и создателях бота\n🧾 Нажмите на /help для получения списка всех функций\n\nКстати слева есть кнопка *≡ Меню*, там тоже список всех команд",
                parse_mode="Markdown",
            )
            db.commit()
        else:
            client.send_message(
                cid,
                f"🤝 Вы уже зарегистрированы!\n\n⏳ Нажмите на /profile для просмотра вашей лицензии\n📕 Нажмите на /manuals для помощи активации лицензии и настройке vpn подключения\n🗿 Нажмите на /about для получения информации о vpn, боте и создателях бота\n🧾 Нажмите на /help для получения списка всех функций",
                parse_mode="Markdown",
            )
    except:
        client.send_message(cid, f"🚫 Ошибка при выполнении команды")


@client.message_handler(commands=["servers"])
def buy(message):
    try:
        cid = message.chat.id
        uid = message.from_user.id
        if not check_license(uid, cid):
            return
        text = "🌏 Выберите сервер"
        rmk = types.InlineKeyboardMarkup(row_width=2)
        buttons = []
        for servers in sql.execute(f"SELECT * FROM vpns"):
            if not os.listdir(f"vpns/{servers[0]}"):
                continue
            buttons.append(
                types.InlineKeyboardButton(
                    text=f"{servers[1]} {servers[2]}",
                    callback_data=f"select_{servers[0]}",
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
        if call.data.partition("_")[0] == "select":
            if not check_license(call.from_user.id, call.message.chat.id):
                return
            vpnid = int(call.data.partition("_")[2])
            for servers in sql.execute(f"SELECT * FROM vpns WHERE id = {vpnid}"):
                configs_dir = f"vpns/{str(servers[0])}"
                config_file = open(
                    os.path.join(configs_dir, random.choice(os.listdir(configs_dir)))
                )
                client.send_document(
                    call.message.chat.id,
                    config_file,
                    caption=f"{servers[1]} {servers[2]}\n\nНажмите на /manuals для просмотра видео по настройке vpn",
                    visible_file_name=f"{servers[1]}.ovpn".replace(" ", "").lower(),
                    parse_mode="Markdown",
                )
                sql.execute(f"UPDATE vpns SET use = use + 1 WHERE id = {vpnid}")
                db.commit()
        client.answer_callback_query(callback_query_id=call.id)
    except:
        client.send_message(call.message.chat.id, f"🚫 Ошибка при выполнении команды")


@client.message_handler(commands=["profile", "myinfo", "myprofile"])
def myprofile(message):
    try:
        cid = message.chat.id
        uid = message.from_user.id
        info = sql.execute(f"SELECT * FROM users WHERE id = {uid}").fetchone()
        if info[1] == 0:
            accessname = "Пользователь"
        elif info[1] == 1:
            accessname = "Администратор"
        elif info[1] == 777:
            accessname = "Разработчик"
        client.send_message(
            cid,
            f"*📇 Ваш профиль*\n\n*👤 Ваш ID:* {info[0]}\n*⏳ Ваша лицензия до:* {':'.join(info[2].split(':')[:-1])}\n*👑 Ваш уровень доступа:* {accessname}",
            parse_mode="Markdown",
        )
    except:
        client.send_message(cid, f"🚫 Ошибка при выполнении команды")


@client.message_handler(commands=["buy", "license"])
def buy(message):
    try:
        cid = message.chat.id
        uid = message.from_user.id
        info = sql.execute(f"SELECT * FROM users WHERE id = {uid}").fetchone()
        text = f"🛒 *Купить лицензию через qiwi или картой*\n\n⏳ Ваша лицензия до:* {':'.join(info[2].split(':')[:-1])}\n\n*"
        payid = str(uid) + str(info[3])
        rmk = types.InlineKeyboardMarkup()
        day1 = types.InlineKeyboardButton(text="1️⃣ = 25₽", url=get_buy_url(payid, 25))
        day3 = types.InlineKeyboardButton(text="3️⃣ = 75₽", url=get_buy_url(payid, 75))
        day7 = types.InlineKeyboardButton(
            text="7️⃣ = 150₽", url=get_buy_url(payid, 150)
        )
        day14 = types.InlineKeyboardButton(
            text="1️⃣4️⃣ = 300₽", url=get_buy_url(payid, 300)
        )
        day30 = types.InlineKeyboardButton(
            text="3️⃣0️⃣ = 600₽", url=get_buy_url(payid, 600)
        )
        success = types.InlineKeyboardButton(
            text="✅ я оплатил!", callback_data="success_pay"
        )
        rmk.add(day1, day3, day7, day14, day30)
        rmk.add(success)
        client.send_message(
            cid,
            f"{text}1. Оплатите количество дней\n2. Нажмите *✅ я оплатил*",
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
            user = sql.execute(f"SELECT * FROM users WHERE id = {uid}").fetchone()
            payid = str(uid) + str(user[3])
            if check_payment(payid, 25):
                set_license(user[2], uid, 1)
                client.send_message(
                    cid,
                    f"✅ Лицензия оплачена на 1 день!\n\nНажмите /servers для выбор сервера",
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
                return
            if check_payment(payid, 75):
                set_license(user[2], uid, 3)
                client.send_message(
                    cid,
                    f"✅ Лицензия оплачена на 3 дня!\n\nНажмите /servers для выбор сервера",
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
                return
            if check_payment(payid, 150):
                set_license(user[2], uid, 7)
                client.send_message(
                    cid,
                    f"✅ Лицензия оплачена на 7 дней!\n\nНажмите /servers для выбор сервера",
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
                return
            if check_payment(payid, 300):
                set_license(user[2], uid, 14)
                client.send_message(
                    cid,
                    f"✅ Лицензия оплачена на 14 дней!\n\nНажмите /servers для выбор сервера",
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
                return
            if check_payment(payid, 600):
                set_license(user[2], uid, 30)
                client.send_message(
                    cid,
                    f"✅ Лицензия оплачена на 30 дней!\n\nНажмите /servers для выбор сервера",
                    parse_mode="Markdown",
                    disable_web_page_preview=True,
                )
                return
        client.send_message(cid, "🚫 Оплата не найдена!")
        client.answer_callback_query(callback_query_id=call.id)

    except:
        client.send_message(call.message.chat.id, f"🚫 Ошибка при выполнении команды")


@client.message_handler(commands=["help"])
def helpcmd(message):
    cid = message.chat.id
    uid = message.from_user.id
    with lock:
        sql.execute(f"SELECT * FROM users WHERE id = {uid}")
        getaccess = sql.fetchone()[1]
    if getaccess >= 1:
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


@client.message_handler(commands=["manuals"])
def myprofile(message):
    try:
        cid = message.chat.id
        uid = message.from_user.id
        client.send_message(
            cid,
            f"*📺 Видео инструкции и полезные ссылки*\n\n*💳 Как оплатить лицензию*\n{pay_help_str}\n\n*⬇️ Скачать необходимую программу*\n{download_str}\n\n*🛠 Как настроить*\n{help_str}",
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
    except:
        client.send_message(cid, f"🚫 Ошибка при выполнении команды")


client.polling(none_stop=True, interval=0)
