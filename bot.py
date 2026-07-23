import sqlite3
import logging
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
    ChatJoinRequestHandler, ChatMemberHandler, MessageHandler, filters, ContextTypes
)

# 🌐 ২৪ ঘণ্টা সার্ভার সজাগ রাখার জন্য নতুন লাইন যুক্ত করা হলো:
from keep_alive import keep_alive

# --- কনফিগারেশন ---
BOT_TOKEN = "8690240616:AAHKOqszJs7aGjSl2kvCnrGczxf6JYh__AQ"
MAIN_CHANNEL_LINK = "https://t.me/+GOw-gR6YlixiOTE9"

ADMIN_USERNAME = "saddamadmin"
ADMIN_PASSWORD = "saddamadmin1234"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
DB_NAME = "bot_database.db"

# --- মাল্টি-ল্যাঙ্গুয়েজ ডিকশনারি ---
TEXTS = {
    'bn': {
        'welcome': "✨ <b>হ্যালো {name}!</b> 👋\n\n🔥 <b>আমাদের প্রিমিয়াম Auto Accept & Manager Bot-এ আপনাকে স্বাগতম!</b>\n\n💡 <b>বটটি কীভাবে কাজ করে?</b>\nআপনার টেলিগ্রাম চ্যানেল বা গ্রুপে আমাকে <b>Admin</b> বানিয়ে দিন। এরপর আপনার চ্যানেলের সমস্ত জয়েন রিকোয়েস্ট আমি একাই অটোমেটিক একসেপ্ট করবো।\n\n👇 <i>নিচের বাটনগুলো ব্যবহার করে বটের ফিচার উপভোগ করুন:</i>",
        'btn_main_ch': "🚀 মেইন চ্যানেল", 
        'btn_menu': "⚙️ মেনু (সব ফিচার)", 
        'btn_add': "➕ চ্যানেল/গ্রুপে এড করুন", 
        'btn_lang': "🌐 ভাষা / Language",
        'menu_text': "⚙️ <b>মেইন মেনু:</b>\nআপনার পছন্দের অপশনটি বেছে নিন:",
        'btn_id': "🆔 আমার ইউজার আইডি", 
        'btn_my_ch': "📢 আমার চ্যানেলসমূহ", 
        'btn_stats': "📊 বটের পরিসংখ্যান", 
        'btn_help': "📖 গাইডলাইন", 
        'btn_back': "🔙 ব্যাক",
        'id_text': "👤 <b>আপনার প্রোফাইল তথ্য:</b>\n\n📝 নাম: {name}\n🆔 ইউজার আইডি: <code>{id}</code>\n\n<i>(এই আইডিটি কপি করে সংরক্ষণ করতে পারেন)</i>",
        'lang_msg': "✅ <b>ভাষা সফলভাবে বাংলায় পরিবর্তন করা হয়েছে!</b>"
    },
    'en': {
        'welcome': "✨ <b>Hello {name}!</b> 👋\n\n🔥 <b>Welcome to the Premium Auto Accept & Manager Bot!</b>\n\n💡 <b>How does it work?</b>\nMake me an <b>Admin</b> in your Telegram channel/group, and I will automatically handle all join requests for you.\n\n👇 <i>Use the buttons below to navigate:</i>",
        'btn_main_ch': "🚀 Main Channel", 
        'btn_menu': "⚙️ Menu (All Features)", 
        'btn_add': "➕ Add to Channel/Group", 
        'btn_lang': "🌐 Language",
        'menu_text': "⚙️ <b>Main Menu:</b>\nChoose an option below:",
        'btn_id': "🆔 My User ID", 
        'btn_my_ch': "📢 My Channels", 
        'btn_stats': "📊 Bot Stats", 
        'btn_help': "📖 Help Guide", 
        'btn_back': "🔙 Back",
        'id_text': "👤 <b>Your Profile Info:</b>\n\n📝 Name: {name}\n🆔 User ID: <code>{id}</code>",
        'lang_msg': "✅ <b>Language successfully changed to English!</b>"
    }
}
# বাকি ভাষাগুলো 
TEXTS['ar'] = TEXTS['en'].copy()
TEXTS['ar']['lang_msg'] = "✅ <b>تم تغيير اللغة بنجاح!</b>"
TEXTS['hi'] = TEXTS['en'].copy()
TEXTS['hi']['lang_msg'] = "✅ <b>भाषा सफलतापूर्वक बदल दी गई है!</b>"
TEXTS['es'] = TEXTS['en'].copy()
TEXTS['es']['lang_msg'] = "✅ <b>¡Idioma cambiado a Español!</b>"
TEXTS['ru'] = TEXTS['en'].copy()
TEXTS['ru']['lang_msg'] = "✅ <b>Язык изменен на русский!</b>"

def get_t(user_id, key):
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute("SELECT lang FROM bot_users WHERE user_id = ?", (user_id,)).fetchone()
        lang = row[0] if row else 'bn'
    return TEXTS.get(lang, TEXTS['en']).get(key, TEXTS['en'].get(key, ""))

# --- ডাটাবেজ সেটআপ ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS channels (
            chat_id INTEGER PRIMARY KEY, chat_title TEXT, owner_id INTEGER, 
            auto_accept INTEGER DEFAULT 1, auto_reject INTEGER DEFAULT 0, welcome_msg TEXT DEFAULT NULL
        )''')
        conn.execute("CREATE TABLE IF NOT EXISTS pending_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user_id INTEGER, UNIQUE(chat_id, user_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS bot_users (user_id INTEGER PRIMARY KEY, first_name TEXT, joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        conn.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER DEFAULT 0)")
        conn.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_accepted', 0)")
        conn.execute('''CREATE TABLE IF NOT EXISTS auto_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, msg_id INTEGER, from_chat_id INTEGER, 
            target_type TEXT, target_id INTEGER, interval_hours INTEGER, last_sent INTEGER DEFAULT 0
        )''')
        try:
            conn.execute("ALTER TABLE bot_users ADD COLUMN lang TEXT DEFAULT 'bn'")
        except:
            pass
        conn.commit()

init_db()

# --- Helpers ---
def save_user(user_id, first_name):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("INSERT OR IGNORE INTO bot_users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))

def get_all_users():
    with sqlite3.connect(DB_NAME) as conn:
        return [r[0] for r in conn.execute("SELECT user_id FROM bot_users").fetchall()]

def get_all_channels():
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT chat_id, chat_title, owner_id FROM channels").fetchall()

def save_channel(chat_id, title, owner_id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''INSERT INTO channels (chat_id, chat_title, owner_id) 
            VALUES (?, ?, ?) ON CONFLICT(chat_id) DO UPDATE SET chat_title=?, owner_id=?''', (chat_id, title, owner_id, title, owner_id))

def get_channel(chat_id):
    with sqlite3.connect(DB_NAME) as conn:
        return conn.execute("SELECT * FROM channels WHERE chat_id = ?", (chat_id,)).fetchone()

# --- অটো-পোস্ট ব্যাকগ্রাউন্ড জব ---
async def check_auto_posts(context: ContextTypes.DEFAULT_TYPE):
    now = int(time.time())
    with sqlite3.connect(DB_NAME) as conn:
        posts = conn.execute("SELECT id, msg_id, from_chat_id, target_type, target_id, interval_hours, last_sent FROM auto_posts").fetchall()
        for p in posts:
            p_id, msg_id, from_chat, target_type, target_id, interval, last_sent = p
            if now - last_sent >= (interval * 3600):
                targets = []
                if target_type == "all_ch":
                    targets = [c[0] for c in conn.execute("SELECT chat_id FROM channels").fetchall()]
                elif target_type == "all_us":
                    targets = [u[0] for u in conn.execute("SELECT user_id FROM bot_users").fetchall()]
                elif target_type == "spec_ch":
                    targets = [target_id]
                
                for t_id in targets:
                    try:
                        await context.bot.copy_message(chat_id=t_id, from_chat_id=from_chat, message_id=msg_id)
                    except:
                        pass
                
                conn.execute("UPDATE auto_posts SET last_sent = ? WHERE id = ?", (now, p_id))
        conn.commit()

# --- ইউজার UI ফাংশন ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.first_name)
    context.user_data['state'] = None
    bot_uname = context.bot.username

    text = get_t(user.id, 'welcome').format(name=user.first_name)
    keyboard = [
        [InlineKeyboardButton(get_t(user.id, 'btn_main_ch'), url=MAIN_CHANNEL_LINK)],
        [InlineKeyboardButton(get_t(user.id, 'btn_menu'), callback_data="open_menu")],
        [
            InlineKeyboardButton(get_t(user.id, 'btn_add'), url=f"https://t.me/{bot_uname}?startgroup=true"), 
            InlineKeyboardButton(get_t(user.id, 'btn_lang'), callback_data="change_lang")
        ]
    ]
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# --- এডমিন প্যানেল ফাংশন ---
async def saddamadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = 'WAITING_ADMIN_USER'
    await update.message.reply_text("👑 <b>সিক্রেট এডমিন প্যানেল লগিন:</b>\n\nআপনার <b>Username</b> দিন:", parse_mode=ParseMode.HTML)

async def show_admin_panel(update_or_message, context):
    context.user_data['is_admin'] = True
    context.user_data['state'] = None
    
    text = "👑 <b>সুপার এডমিন প্রো ড্যাশবোর্ড</b>\n━━━━━━━━━━━━━━━━━━\n👇 <i>অ্যাকশন বেছে নিন:</i>"
    keyboard = [
        [InlineKeyboardButton("📡 চ্যানেল ট্র্যাকার ও লিস্ট", callback_data="admin_ch_list"), InlineKeyboardButton("⏰ অটো-পোস্ট", callback_data="admin_autopost")],
        [InlineKeyboardButton("📣 সব চ্যানেলে ব্রডকাস্ট", callback_data="admin_bc_ch"), InlineKeyboardButton("📝 নির্দিষ্ট চ্যানেলে পোস্ট", callback_data="admin_post_spec")],
        [InlineKeyboardButton("👥 ইউজার ব্রডকাস্ট", callback_data="admin_bc_usr")],
        [InlineKeyboardButton("❌ লগআউট", callback_data="admin_logout")]
    ]
    if hasattr(update_or_message, 'reply_text'):
        await update_or_message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
    else:
        await update_or_message.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)

# --- টেক্সট ইনপুট রাউটার ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    text = update.message.text

    if state == 'WAITING_ADMIN_USER':
        if text == ADMIN_USERNAME:
            context.user_data['state'] = 'WAITING_ADMIN_PASS'
            await update.message.reply_text("✅ <b>ইউজারনেম সঠিক!</b>\nPassword দিন:", parse_mode=ParseMode.HTML)
        else:
            context.user_data['state'] = None
            await update.message.reply_text("❌ ভুল ইউজারনেম!")
            
    elif state == 'WAITING_ADMIN_PASS':
        if text == ADMIN_PASSWORD:
            await show_admin_panel(update.message, context)
        else:
            context.user_data['state'] = None
            await update.message.reply_text("❌ ভুল পাসওয়ার্ড!")

    elif state == 'WAITING_BC_USR_MSG' and context.user_data.get('is_admin'):
        users = get_all_users()
        await update.message.reply_text(f"⏳ {len(users)} জন ইউজারের কাছে পাঠানো হচ্ছে...")
        for uid in users:
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            except:
                pass
        await update.message.reply_text("✅ <b>ব্রডকাস্ট সফল!</b>", parse_mode=ParseMode.HTML)
        await show_admin_panel(update.message, context)

    elif state == 'WAITING_BC_CH_MSG' and context.user_data.get('is_admin'):
        channels = get_all_channels()
        await update.message.reply_text(f"⏳ {len(channels)} টি চ্যানেলে পাঠানো হচ্ছে...")
        for ch in channels:
            try:
                await context.bot.copy_message(chat_id=ch[0], from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            except:
                pass
        await update.message.reply_text("✅ <b>সব চ্যানেলে পোস্ট সফল!</b>", parse_mode=ParseMode.HTML)
        await show_admin_panel(update.message, context)

    elif state == 'WAITING_SPEC_CH_ID' and context.user_data.get('is_admin'):
        context.user_data['spec_ch_id'] = text
        context.user_data['state'] = 'WAITING_SPEC_CH_MSG'
        await update.message.reply_text("✅ চ্যানেল আইডি সেট হয়েছে। এবার মেসেজ বা ছবি পাঠান:")

    elif state == 'WAITING_SPEC_CH_MSG' and context.user_data.get('is_admin'):
        try:
            await context.bot.copy_message(chat_id=context.user_data['spec_ch_id'], from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            await update.message.reply_text("✅ <b>নির্দিষ্ট চ্যানেলে পোস্ট সফল!</b>", parse_mode=ParseMode.HTML)
        except Exception as e:
            await update.message.reply_text(f"❌ এরর: {e}")
        await show_admin_panel(update.message, context)

    elif state == 'WAITING_AUTOPOST_MSG' and context.user_data.get('is_admin'):
        context.user_data['ap_msg_id'] = update.message.message_id
        context.user_data['ap_from'] = update.effective_chat.id
        context.user_data['state'] = 'WAITING_AUTOPOST_TARGET'
        kb = [
            [InlineKeyboardButton("📢 সব চ্যানেলে", callback_data="ap_all_ch"), InlineKeyboardButton("👥 সব ইউজারকে", callback_data="ap_all_us")],
            [InlineKeyboardButton("📝 নির্দিষ্ট চ্যানেলে", callback_data="ap_spec_ch")]
        ]
        await update.message.reply_text("✅ মেসেজ সেভ হয়েছে।\nকোথায় অটো-পোস্ট হবে তা সিলেক্ট করুন:", reply_markup=InlineKeyboardMarkup(kb))

    elif state == 'WAITING_AUTOPOST_TIME' and context.user_data.get('is_admin'):
        if text.isdigit():
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("INSERT INTO auto_posts (msg_id, from_chat_id, target_type, target_id, interval_hours) VALUES (?, ?, ?, ?, ?)", 
                             (context.user_data['ap_msg_id'], context.user_data['ap_from'], context.user_data['ap_type'], context.user_data.get('ap_target_id', 0), int(text)))
            await update.message.reply_text(f"✅ <b>সফল!</b> প্রতি {text} ঘন্টা পরপর পোস্টটি অটোমেটিক যাবে।", parse_mode=ParseMode.HTML)
            await show_admin_panel(update.message, context)
        else:
            await update.message.reply_text("❌ সঠিক সংখ্যা লিখুন (যেমন: 12)")
        
    elif state == 'WAITING_AUTOPOST_SPEC_ID' and context.user_data.get('is_admin'):
        context.user_data['ap_target_id'] = text
        context.user_data['state'] = 'WAITING_AUTOPOST_TIME'
        await update.message.reply_text("✅ চ্যানেল আইডি সেভ। কত ঘন্টা পরপর যাবে? (যেমন: 12)")

    elif state and state.startswith("WAITING_WELCOME_"):
        chat_id = int(state.split("_")[2])
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("UPDATE channels SET welcome_msg = ? WHERE chat_id = ?", (text, chat_id))
        context.user_data['state'] = None
        await update.message.reply_text("✅ <b>কাস্টম ওয়েলকাম মেসেজ সেভ হয়েছে!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

# --- বাটন হ্যান্ডলার ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if not data.startswith("ap_"):
        context.user_data['state'] = None

    if data == "main_menu":
        await start_command(update, context)
    
    elif data == "open_menu":
        kb = [
            [InlineKeyboardButton(get_t(user_id, 'btn_id'), callback_data="show_id"), InlineKeyboardButton(get_t(user_id, 'btn_my_ch'), callback_data="my_channels")],
            [InlineKeyboardButton(get_t(user_id, 'btn_stats'), callback_data="bot_stats"), InlineKeyboardButton(get_t(user_id, 'btn_help'), callback_data="help_guide")],
            [InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="main_menu")]
        ]
        await query.edit_message_text(get_t(user_id, 'menu_text'), reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "show_id":
        txt = get_t(user_id, 'id_text').format(name=query.from_user.first_name, id=user_id)
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="open_menu")]]), parse_mode=ParseMode.HTML)

    elif data == "change_lang":
        kb = [
            [InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lng_bn"), InlineKeyboardButton("🇬🇧 English", callback_data="lng_en")],
            [InlineKeyboardButton("🇸🇦 العربية", callback_data="lng_ar"), InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lng_hi")],
            [InlineKeyboardButton("🇪🇸 Español", callback_data="lng_es"), InlineKeyboardButton("🇷🇺 Русский", callback_data="lng_ru")],
            [InlineKeyboardButton("🔙 ব্যাক", callback_data="main_menu")]
        ]
        await query.edit_message_text("🌐 <b>Select Language:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("lng_"):
        lang = data.split("_")[1]
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("UPDATE bot_users SET lang = ? WHERE user_id = ?", (lang, user_id))
        await query.answer(get_t(user_id, 'lang_msg'), show_alert=True)
        await start_command(update, context)

    elif data == "admin_cancel":
        await show_admin_panel(query, context)
    
    elif data == "admin_ch_list":
        channels = get_all_channels()
        txt = f"📡 <b>মোট চ্যানেল/গ্রুপ:</b> {len(channels)} টি\n\n"
        with sqlite3.connect(DB_NAME) as conn:
            for ch in channels:
                usr = conn.execute("SELECT first_name FROM bot_users WHERE user_id = ?", (ch[2],)).fetchone()
                uname = usr[0] if usr else "Unknown"
                txt += f"📢 {ch[1]} (<code>{ch[0]}</code>)\n👤 এড করেছে: {uname} (<code>{ch[2]}</code>)\n\n"
        await query.edit_message_text(txt if channels else "কোনো চ্যানেল নেই!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_cancel")]]), parse_mode=ParseMode.HTML)

    elif data == "admin_post_spec":
        context.user_data['state'] = 'WAITING_SPEC_CH_ID'
        await query.edit_message_text("📝 <b>নির্দিষ্ট চ্যানেলে পোস্ট:</b>\n\nচ্যানেল বা গ্রুপের ID লিখে সেন্ড করুন (যেমন: -100123456):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="admin_cancel")]]))

    elif data == "admin_bc_ch":
        context.user_data['state'] = 'WAITING_BC_CH_MSG'
        await query.edit_message_text("📣 <b>সব চ্যানেলে ব্রডকাস্ট:</b>\n\nযেকোনো মেসেজ বা ছবি পাঠান:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="admin_cancel")]]))

    elif data == "admin_bc_usr":
        context.user_data['state'] = 'WAITING_BC_USR_MSG'
        await query.edit_message_text("👥 <b>ইউজার ব্রডকাস্ট:</b>\n\nযেকোনো মেসেজ পাঠান:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="admin_cancel")]]))

    elif data == "admin_autopost":
        context.user_data['state'] = 'WAITING_AUTOPOST_MSG'
        await query.edit_message_text("⏰ <b>অটো-পোস্ট সেটআপ:</b>\n\nযে মেসেজটি অটোমেটিক পাঠাতে চান সেটি লিখে বা ফরওয়ার্ড করে দিন:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="admin_cancel")]]))

    elif data.startswith("ap_"):
        context.user_data['ap_type'] = data
        if data == "ap_spec_ch":
            context.user_data['state'] = 'WAITING_AUTOPOST_SPEC_ID'
            await query.edit_message_text("📝 নির্দিষ্ট চ্যানেল/গ্রুপের ID লিখে সেন্ড করুন:")
        else:
            context.user_data['state'] = 'WAITING_AUTOPOST_TIME'
            await query.edit_message_text("⏰ কত ঘন্টা পরপর পোস্ট হবে? (যেমন: 12 বা 24 লিখে সেন্ড করুন)")

    elif data == "admin_logout":
        context.user_data['is_admin'] = False
        await query.edit_message_text("✅ <b>এডমিন থেকে লগআউট হয়েছেন।</b>", parse_mode=ParseMode.HTML)
        
    elif data == "bot_stats":
        with sqlite3.connect(DB_NAME) as conn:
            acc = conn.execute("SELECT value FROM stats WHERE key = 'total_accepted'").fetchone()[0]
            ch = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
            usr = conn.execute("SELECT COUNT(*) FROM bot_users").fetchone()[0]
        txt = f"📊 <b>লাইভ পরিসংখ্যান:</b>\n\n👥 মোট ইউজার: {usr} জন\n📢 মোট চ্যানেল: {ch} টি\n✅ মোট এপ্রুভড: {acc} জন"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="open_menu")]]), parse_mode=ParseMode.HTML)

    elif data == "help_guide":
        txt = "📖 <b>গাইডলাইন:</b>\n১. চ্যানেল সেটিংসে যান।\n২. এই বটকে Admin বানান (Add members permission দিন)।\n৩. বটের মেনু থেকে আপনার চ্যানেল দেখতে পাবেন।\n৪. Auto Accept অন করুন।"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="open_menu")]]), parse_mode=ParseMode.HTML)

    elif data == "my_channels":
        with sqlite3.connect(DB_NAME) as conn:
            channels = conn.execute("SELECT chat_id, chat_title FROM channels WHERE owner_id = ?", (user_id,)).fetchall()
        if not channels:
            await query.edit_message_text("❌ <b>আপনার কোনো চ্যানেল নেই!</b> আগে আমাকে চ্যানেলে এডমিন করুন।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="open_menu")]]), parse_mode=ParseMode.HTML)
            return
        kb = [[InlineKeyboardButton(f"📢 {t}", callback_data=f"manage_{cid}")] for cid, t in channels]
        kb.append([InlineKeyboardButton("🔙 ব্যাক", callback_data="open_menu")])
        await query.edit_message_text("📋 <b>আপনার চ্যানেলসমূহ:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("manage_"):
        chat_id = int(data.split("_")[1])
        ch = get_channel(chat_id)
        if not ch: return
        with sqlite3.connect(DB_NAME) as conn:
            pend = len(conn.execute("SELECT user_id FROM pending_requests WHERE chat_id = ?", (chat_id,)).fetchall())
        btn_ac = "🟢 ON" if ch[3] else "🔴 OFF"
        btn_rj = "🟢 ON" if ch[4] else "🔴 OFF"
        kb = [
            [InlineKeyboardButton(f"Auto Accept: {btn_ac}", callback_data=f"tgl_ac_{chat_id}"), InlineKeyboardButton(f"Auto Reject: {btn_rj}", callback_data=f"tgl_rj_{chat_id}")],
            [InlineKeyboardButton(f"✉️ Welcome Message", callback_data=f"set_wel_{chat_id}")],
            [InlineKeyboardButton(f"⚡ Approve Pending ({pend})", callback_data=f"apprv_all_{chat_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="my_channels")]
        ]
        await query.edit_message_text(f"⚙️ <b>কন্ট্রোল:</b> {ch[1]}\n\n🔹 Pending: {pend}", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("tgl_ac_"):
        chat_id = int(data.split("_")[2])
        val = 0 if get_channel(chat_id)[3] else 1
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("UPDATE channels SET auto_accept = ?, auto_reject = 0 WHERE chat_id = ?", (val, chat_id))
        await button_handler(update, context)

    elif data.startswith("tgl_rj_"):
        chat_id = int(data.split("_")[2])
        val = 0 if get_channel(chat_id)[4] else 1
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("UPDATE channels SET auto_reject = ?, auto_accept = 0 WHERE chat_id = ?", (val, chat_id))
        await button_handler(update, context)

    elif data.startswith("set_wel_"):
        chat_id = int(data.split("_")[2])
        context.user_data['state'] = f'WAITING_WELCOME_{chat_id}'
        await query.edit_message_text("📝 <b>নতুন ওয়েলকাম মেসেজ লিখুন:</b>\n(নামের জন্য <code>{user}</code> এবং চ্যানেলের নামের জন্য <code>{channel}</code> ব্যবহার করুন)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

    elif data.startswith("apprv_all_"):
        chat_id = int(data.split("_")[2])
        with sqlite3.connect(DB_NAME) as conn:
            pend = [r[0] for r in conn.execute("SELECT user_id FROM pending_requests WHERE chat_id = ?", (chat_id,)).fetchall()]
        if not pend:
            await query.answer("কোনো রিকোয়েস্ট নেই!", show_alert=True)
            return
        await query.edit_message_text(f"⏳ একসেপ্ট করা হচ্ছে... (0/{len(pend)})")
        for uid in pend:
            try:
                await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=uid)
                with sqlite3.connect(DB_NAME) as conn:
                    conn.execute("UPDATE stats SET value = value + 1 WHERE key = 'total_accepted'")
                await asyncio.sleep(0.1)
            except:
                pass
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("DELETE FROM pending_requests WHERE chat_id = ?", (chat_id,))
        await query.edit_message_text("🎉 <b>সব রিকোয়েস্ট এপ্রুভ হয়েছে!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

# --- জয়েন রিকোয়েস্ট লজিক ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    chat_id, user_id, user_name, title = req.chat.id, req.from_user.id, req.from_user.first_name, req.chat.title
    ch = get_channel(chat_id)
    auto_acc, auto_rej, msg = (ch[3], ch[4], ch[5]) if ch else (1, 0, None)

    if auto_acc:
        try:
            await context.bot.approve_chat_join_request(chat_id, user_id)
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("UPDATE stats SET value = value + 1 WHERE key = 'total_accepted'")
            try:
                final_msg = msg.replace("{user}", user_name).replace("{channel}", title) if msg else f"হ্যালো <b>{user_name}</b>!\n<b>{title}</b>-এ আপনাকে স্বাগতম!"
                await context.bot.send_message(user_id, final_msg, parse_mode=ParseMode.HTML)
            except:
                pass
        except:
            pass
    elif auto_rej:
        try:
            await context.bot.decline_chat_join_request(chat_id, user_id)
        except:
            pass
    else:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("INSERT OR IGNORE INTO pending_requests (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))

# --- চ্যানেল ট্র্যাকার ---
async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = update.my_chat_member
    if res.new_chat_member.status in ["administrator", "member"]:
        save_channel(res.chat.id, res.chat.title, res.from_user.id)
        try:
            await context.bot.send_message(res.from_user.id, f"✅ <b>{res.chat.title}</b> চ্যানেলটি সফলভাবে যুক্ত হয়েছে!", parse_mode=ParseMode.HTML)
        except:
            pass

def main():
    # 🌐 সার্ভার জাগিয়ে রাখার ফাংশন কল করা হলো
    keep_alive()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # ব্যাকগ্রাউন্ড অটো-পোস্ট জব চালু করা (প্রতি ২ মিনিটে চেক করবে)
    app.job_queue.run_repeating(check_auto_posts, interval=120)

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("saddamadmin", saddamadmin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_text))
    
    print("🚀 Auto Accept Ultra Pro (v5.0) is running 24/7...")
    app.run_polling()

if __name__ == '__main__':
    main()
