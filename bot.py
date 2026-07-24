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
from telegram.error import BadRequest

# 🌐 ২৪ ঘণ্টা সার্ভার সজাগ রাখার জন্য
from keep_alive import keep_alive

# --- কনফিগারেশন ---
BOT_TOKEN = "8690240616:AAFzk942XkVODDA9EYtY1eDaIrs5B9XjNX4"
MAIN_CHANNEL_LINK = "https://t.me/+GOw-gR6YlixiOTE9"  # জয়েন করার লিংক

# ⚠️ এখানে আপনার মেইন চ্যানেলের আসল ID বসান (শুরুতে -100 থাকতে হবে)
MAIN_CHANNEL_ID = "-1004301389904" 

ADMIN_USERNAME = "saddamadmin"
ADMIN_PASSWORD = "saddamadmin1234"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
DB_NAME = "bot_database.db"

# --- মাল্টি-ল্যাঙ্গুয়েজ ডিকশনারি ---
TEXTS = {
    'bn': {
        'verify_req': "🛑 <b>অ্যাক্সেস ডিনাইড!</b>\n\nআমাদের বটের প্রিমিয়াম ফিচারগুলো ব্যবহার করতে হলে প্রথমে আপনাকে আমাদের <b>মেইন চ্যানেলে</b> জয়েন করতে হবে।\n\n১. <b>'🤖 I am not a robot'</b> বাটনে ক্লিক করে জয়েন করুন।\n২. তারপর ফিরে এসে <b>'✅ Verify'</b> বাটনে ক্লিক করুন।",
        'btn_robot': "🤖 I am not a robot", 
        'btn_verify': "✅ Verify",
        'welcome_main': "🎉 <b>ভেরিফিকেশন সফল!</b>\n\n✨ <b>হ্যালো {name}!</b> 👋\n🔥 <b>Premium Auto Accept & Manager Bot</b>-এ আপনাকে স্বাগতম!\n\n👇 <i>নিচের বাটনগুলো থেকে আপনার অপশন বেছে নিন:</i>",
        'btn_all_menu': "⚙️ All Menu", 
        'btn_how_use': "❓ How to use", 
        'btn_lang': "🌐 Language", 
        'btn_on_my_ch': "📢 On My Channel",
        'menu_text': "⚙️ <b>অল মেনু (All Menu):</b>\nআপনার প্রয়োজনীয় অপশনটি সিলেক্ট করুন:",
        'btn_id': "🆔 My ID", 
        'btn_guide': "📖 Guidelines", 
        'btn_stats': "📊 Bot Stats", 
        'btn_premium': "💎 Premium Features", 
        'btn_support': "🎧 Support", 
        'btn_back': "🔙 Back",
        'id_text': "👤 <b>আপনার প্রোফাইল:</b>\n\n📝 নাম: {name}\n🆔 ইউজার আইডি: <code>{id}</code>",
        'lang_msg': "✅ <b>ভাষা সফলভাবে বাংলায় পরিবর্তন করা হয়েছে!</b>"
    },
    'en': {
        'verify_req': "🛑 <b>Access Denied!</b>\n\nTo use our premium bot, you must join our <b>Main Channel</b> first.\n\n1. Click <b>'🤖 I am not a robot'</b> to join.\n2. Come back and click <b>'✅ Verify'</b>.",
        'btn_robot': "🤖 I am not a robot", 
        'btn_verify': "✅ Verify",
        'welcome_main': "🎉 <b>Verification Successful!</b>\n\n✨ <b>Hello {name}!</b> 👋\n🔥 Welcome to the <b>Premium Auto Accept Bot</b>!\n\n👇 <i>Choose an option below:</i>",
        'btn_all_menu': "⚙️ All Menu", 
        'btn_how_use': "❓ How to use", 
        'btn_lang': "🌐 Language", 
        'btn_on_my_ch': "📢 On My Channel",
        'menu_text': "⚙️ <b>All Menu:</b>\nSelect an option:",
        'btn_id': "🆔 My ID", 
        'btn_guide': "📖 Guidelines", 
        'btn_stats': "📊 Bot Stats", 
        'btn_premium': "💎 Premium Features", 
        'btn_support': "🎧 Support", 
        'btn_back': "🔙 Back",
        'id_text': "👤 <b>Your Profile:</b>\n\n📝 Name: {name}\n🆔 User ID: <code>{id}</code>",
        'lang_msg': "✅ <b>Language successfully changed to English!</b>"
    }
}
# অটো-কপি অন্যান্য ভাষার জন্য
for lang in ['ar', 'hi', 'es', 'ru']:
    TEXTS[lang] = TEXTS['en'].copy()
TEXTS['hi']['lang_msg'] = "✅ <b>भाषा सफलतापूर्वक बदल दी गई है!</b>"
TEXTS['ar']['lang_msg'] = "✅ <b>تم تغيير اللغة بنجاح!</b>"

def get_t(user_id, key):
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute("SELECT lang FROM bot_users WHERE user_id = ?", (user_id,)).fetchone()
        lang = row[0] if row and row[0] in TEXTS else 'bn'
    return TEXTS.get(lang, TEXTS['en']).get(key, TEXTS['en'].get(key, ""))

# --- ডাটাবেজ সেটআপ ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS channels (
            chat_id INTEGER PRIMARY KEY, chat_title TEXT, owner_id INTEGER, 
            auto_accept INTEGER DEFAULT 1, auto_reject INTEGER DEFAULT 0, welcome_msg TEXT DEFAULT NULL
        )''')
        conn.execute("CREATE TABLE IF NOT EXISTS pending_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user_id INTEGER, UNIQUE(chat_id, user_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS bot_users (user_id INTEGER PRIMARY KEY, first_name TEXT, joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, lang TEXT DEFAULT 'bn')")
        conn.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER DEFAULT 0)")
        conn.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_accepted', 0)")
        conn.execute('''CREATE TABLE IF NOT EXISTS auto_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, msg_id INTEGER, from_chat_id INTEGER, 
            target_type TEXT, target_id INTEGER, interval_hours INTEGER, last_sent INTEGER DEFAULT 0
        )''')
        # Config table for dynamic texts
        conn.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, text_value TEXT)")
        conn.execute("INSERT OR IGNORE INTO config (key, text_value) VALUES ('guide_text', '📌 Please follow the rules...')")
        conn.execute("INSERT OR IGNORE INTO config (key, text_value) VALUES ('how_to_use', '💡 Add this bot as an Admin in your channel with Add Member permission.')")
        conn.execute("INSERT OR IGNORE INTO config (key, text_value) VALUES ('video_link', 'https://youtube.com/')")
        try: conn.execute("ALTER TABLE bot_users ADD COLUMN lang TEXT DEFAULT 'bn'")
        except: pass
        conn.commit()
init_db()

# --- Helpers ---
def save_user(user_id, first_name):
    with sqlite3.connect(DB_NAME) as conn: conn.execute("INSERT OR IGNORE INTO bot_users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))

def get_config(key):
    with sqlite3.connect(DB_NAME) as conn: return conn.execute("SELECT text_value FROM config WHERE key = ?", (key,)).fetchone()[0]

def set_config(key, val):
    with sqlite3.connect(DB_NAME) as conn: conn.execute("UPDATE config SET text_value = ? WHERE key = ?", (val, key))

# --- অটো-পোস্ট ব্যাকগ্রাউন্ড জব ---
async def check_auto_posts(context: ContextTypes.DEFAULT_TYPE):
    now = int(time.time())
    with sqlite3.connect(DB_NAME) as conn:
        posts = conn.execute("SELECT id, msg_id, from_chat_id, target_type, target_id, interval_hours, last_sent FROM auto_posts").fetchall()
        for p in posts:
            p_id, msg_id, from_chat, target_type, target_id, interval, last_sent = p
            if now - last_sent >= (interval * 3600):
                targets = [c[0] for c in conn.execute("SELECT chat_id FROM channels").fetchall()] if target_type == "all_ch" else \
                          [u[0] for u in conn.execute("SELECT user_id FROM bot_users").fetchall()] if target_type == "all_us" else [target_id]
                for t_id in targets:
                    try: await context.bot.copy_message(chat_id=t_id, from_chat_id=from_chat, message_id=msg_id)
                    except: pass
                conn.execute("UPDATE auto_posts SET last_sent = ? WHERE id = ?", (now, p_id))
        conn.commit()

# --- স্টার্ট ও ভেরিফাই ফাংশন ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.first_name)
    context.user_data['state'] = None

    # Check Force Sub
    try:
        member = await context.bot.get_chat_member(MAIN_CHANNEL_ID, user.id)
        if member.status in ['left', 'kicked']:
            raise BadRequest("Not joined")
        await show_main_menu(update, context) # If joined, show menu
    except Exception as e:
        # If not joined or bot is not admin in main channel
        txt = get_t(user.id, 'verify_req')
        kb = [
            [InlineKeyboardButton(get_t(user.id, 'btn_robot'), url=MAIN_CHANNEL_LINK)],
            [InlineKeyboardButton(get_t(user.id, 'btn_verify'), callback_data="verify_sub")]
        ]
        if update.message: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
        else: await update.callback_query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

async def show_main_menu(update_or_cb, context: ContextTypes.DEFAULT_TYPE):
    user_id = update_or_cb.from_user.id if hasattr(update_or_cb, 'from_user') else update_or_cb.effective_user.id
    name = update_or_cb.from_user.first_name if hasattr(update_or_cb, 'from_user') else update_or_cb.effective_user.first_name
    txt = get_t(user_id, 'welcome_main').format(name=name)
    kb = [
        [InlineKeyboardButton(get_t(user_id, 'btn_all_menu'), callback_data="menu_all"), InlineKeyboardButton(get_t(user_id, 'btn_how_use'), callback_data="menu_how")],
        [InlineKeyboardButton(get_t(user_id, 'btn_lang'), callback_data="change_lang"), InlineKeyboardButton(get_t(user_id, 'btn_on_my_ch'), callback_data="user_channels")]
    ]
    markup = InlineKeyboardMarkup(kb)
    if hasattr(update_or_cb, 'message') and update_or_cb.message:
        await update_or_cb.message.reply_text(txt, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        await update_or_cb.edit_message_text(txt, reply_markup=markup, parse_mode=ParseMode.HTML)

# --- এডমিন প্যানেল ---
async def saddamadmin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['state'] = 'WAITING_ADMIN_USER'
    await update.message.reply_text("👑 <b>সিক্রেট এডমিন লগিন:</b>\nUsername দিন:", parse_mode=ParseMode.HTML)

async def show_admin_panel(update_or_message, context):
    context.user_data['is_admin'] = True
    context.user_data['state'] = None
    
    with sqlite3.connect(DB_NAME) as conn:
        acc = conn.execute("SELECT value FROM stats WHERE key = 'total_accepted'").fetchone()[0]
        ch = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        usr = conn.execute("SELECT COUNT(*) FROM bot_users").fetchone()[0]
        pend = conn.execute("SELECT COUNT(*) FROM pending_requests").fetchone()[0]

    text = f"👑 <b>সুপার এডমিন ড্যাশবোর্ড</b>\n━━━━━━━━━━━━━━━━━━\n👥 মোট ইউজার: {usr}\n📢 মোট চ্যানেল: {ch}\n⏳ মোট পেন্ডিং: {pend}\n✅ মোট এপ্রুভ: {acc}\n━━━━━━━━━━━━━━━━━━\n👇 <i>অ্যাকশন বেছে নিন:</i>"
    kb = [
        [InlineKeyboardButton("📡 চ্যানেল ট্র্যাকার", callback_data="admin_ch_list"), InlineKeyboardButton("⏰ অটো-পোস্ট", callback_data="admin_autopost")],
        [InlineKeyboardButton("📣 চ্যানেল ব্রডকাস্ট", callback_data="admin_bc_ch"), InlineKeyboardButton("👥 ইউজার ব্রডকাস্ট", callback_data="admin_bc_usr")],
        [InlineKeyboardButton("📝 নির্দিষ্ট চ্যানেলে পোস্ট", callback_data="admin_post_spec")],
        [InlineKeyboardButton("✏️ Guidelines এডিট", callback_data="edit_guide"), InlineKeyboardButton("✏️ How to Use এডিট", callback_data="edit_how")],
        [InlineKeyboardButton("🎥 Video Link এডিট", callback_data="edit_vid"), InlineKeyboardButton("❌ লগআউট", callback_data="admin_logout")]
    ]
    if hasattr(update_or_message, 'reply_text'): await update_or_message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else: await update_or_message.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

# --- টেক্সট ইনপুট রাউটার (Dynamic State Manager) ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    text = update.message.text
    is_admin = context.user_data.get('is_admin')

    if state == 'WAITING_ADMIN_USER':
        if text == ADMIN_USERNAME:
            context.user_data['state'] = 'WAITING_ADMIN_PASS'
            await update.message.reply_text("✅ Username সঠিক! Password দিন:")
        else:
            context.user_data['state'] = None
            await update.message.reply_text("❌ ভুল ইউজারনেম!")
            
    elif state == 'WAITING_ADMIN_PASS':
        if text == ADMIN_PASSWORD: await show_admin_panel(update.message, context)
        else:
            context.user_data['state'] = None
            await update.message.reply_text("❌ ভুল পাসওয়ার্ড!")

    elif state == 'EDIT_GUIDE' and is_admin:
        set_config('guide_text', text)
        await update.message.reply_text("✅ Guidelines আপডেট হয়েছে!")
        await show_admin_panel(update.message, context)
        
    elif state == 'EDIT_HOW' and is_admin:
        set_config('how_to_use', text)
        await update.message.reply_text("✅ How to use আপডেট হয়েছে!")
        await show_admin_panel(update.message, context)
        
    elif state == 'EDIT_VID' and is_admin:
        set_config('video_link', text)
        await update.message.reply_text("✅ Video Link আপডেট হয়েছে!")
        await show_admin_panel(update.message, context)

    elif state == 'WAITING_BC_USR_MSG' and is_admin:
        with sqlite3.connect(DB_NAME) as conn: users = [u[0] for u in conn.execute("SELECT user_id FROM bot_users").fetchall()]
        msg = await update.message.reply_text(f"⏳ {len(users)} জনের কাছে পাঠানো হচ্ছে...")
        success = 0
        for uid in users:
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
                success += 1
            except: pass
        await msg.edit_text(f"✅ ব্রডকাস্ট সফল! ({success}/{len(users)})")
        await show_admin_panel(update.message, context)

    elif state == 'WAITING_BC_CH_MSG' and is_admin:
        with sqlite3.connect(DB_NAME) as conn: channels = [c[0] for c in conn.execute("SELECT chat_id FROM channels").fetchall()]
        msg = await update.message.reply_text(f"⏳ {len(channels)} টি চ্যানেলে পাঠানো হচ্ছে...")
        for ch in channels:
            try: await context.bot.copy_message(chat_id=ch, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            except: pass
        await msg.edit_text("✅ সব চ্যানেলে পোস্ট সফল!")
        await show_admin_panel(update.message, context)

    elif state == 'WAITING_SPEC_CH_ID' and is_admin:
        context.user_data['spec_ch_id'] = text
        context.user_data['state'] = 'WAITING_SPEC_CH_MSG'
        await update.message.reply_text("✅ চ্যানেল আইডি সেট হয়েছে। এবার মেসেজ বা ছবি পাঠান:")

    elif state == 'WAITING_SPEC_CH_MSG' and is_admin:
        try:
            await context.bot.copy_message(chat_id=context.user_data['spec_ch_id'], from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            await update.message.reply_text("✅ নির্দিষ্ট চ্যানেলে পোস্ট সফল!")
        except Exception as e: await update.message.reply_text(f"❌ এরর: {e}")
        await show_admin_panel(update.message, context)

    elif state == 'WAITING_AUTOPOST_MSG' and is_admin:
        context.user_data['ap_msg_id'] = update.message.message_id
        context.user_data['ap_from'] = update.effective_chat.id
        context.user_data['state'] = 'WAITING_AUTOPOST_TARGET'
        kb = [[InlineKeyboardButton("📢 সব চ্যানেলে", callback_data="ap_all_ch"), InlineKeyboardButton("👥 সব ইউজারকে", callback_data="ap_all_us")],
              [InlineKeyboardButton("📝 নির্দিষ্ট চ্যানেলে", callback_data="ap_spec_ch")]]
        await update.message.reply_text("✅ মেসেজ সেভ। কোথায় অটো-পোস্ট হবে?", reply_markup=InlineKeyboardMarkup(kb))

    elif state == 'WAITING_AUTOPOST_TIME' and is_admin:
        if text.isdigit():
            with sqlite3.connect(DB_NAME) as conn:
                conn.execute("INSERT INTO auto_posts (msg_id, from_chat_id, target_type, target_id, interval_hours) VALUES (?, ?, ?, ?, ?)", 
                             (context.user_data['ap_msg_id'], context.user_data['ap_from'], context.user_data['ap_type'], context.user_data.get('ap_target_id', 0), int(text)))
            await update.message.reply_text(f"✅ সফল! প্রতি {text} ঘন্টা পরপর পোস্ট হবে।")
            await show_admin_panel(update.message, context)
        else: await update.message.reply_text("❌ সংখ্যা লিখুন (যেমন: 12)")
        
    elif state == 'WAITING_AUTOPOST_SPEC_ID' and is_admin:
        context.user_data['ap_target_id'] = text
        context.user_data['state'] = 'WAITING_AUTOPOST_TIME'
        await update.message.reply_text("✅ আইডি সেভ। কত ঘন্টা পরপর যাবে?")

    # User States
    elif state and state.startswith("WAITING_WELCOME_"):
        chat_id = int(state.split("_")[2])
        with sqlite3.connect(DB_NAME) as conn: conn.execute("UPDATE channels SET welcome_msg = ? WHERE chat_id = ?", (text, chat_id))
        context.user_data['state'] = None
        await update.message.reply_text("✅ <b>ওয়েলকাম মেসেজ সেভ হয়েছে!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

    elif state and state.startswith("USR_BC_"):
        chat_id = int(state.split("_")[2])
        try:
            await context.bot.copy_message(chat_id=chat_id, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            await update.message.reply_text("✅ <b>আপনার চ্যানেলে মেসেজ সফলভাবে পোস্ট হয়েছে!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)
        except Exception as e:
            await update.message.reply_text(f"❌ <b>ব্যর্থ হয়েছে!</b> বটকে চ্যানেলে মেসেজ সেন্ড করার পারমিশন দেওয়া আছে কিনা চেক করুন।", parse_mode=ParseMode.HTML)
        context.user_data['state'] = None

# --- বাটন হ্যান্ডলার ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if not data.startswith("ap_"): context.user_data['state'] = None

    # Verification
    if data == "verify_sub":
        try:
            member = await context.bot.get_chat_member(MAIN_CHANNEL_ID, user_id)
            if member.status in ['left', 'kicked']: await query.answer("❌ আপনি এখনো জয়েন করেননি!", show_alert=True)
            else: await show_main_menu(query, context)
        except:
            await show_main_menu(query, context) # Fallback if bot is not admin in main channel

    # Menu Buttons
    elif data == "main_menu":
        await show_main_menu(query, context)
    
    elif data == "menu_all":
        kb = [
            [InlineKeyboardButton(get_t(user_id, 'btn_id'), callback_data="show_id"), InlineKeyboardButton(get_t(user_id, 'btn_guide'), callback_data="show_guide")],
            [InlineKeyboardButton(get_t(user_id, 'btn_stats'), callback_data="show_stats"), InlineKeyboardButton(get_t(user_id, 'btn_premium'), callback_data="show_premium")],
            [InlineKeyboardButton(get_t(user_id, 'btn_support'), url=SUPPORT_CHANNEL_LINK), InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="main_menu")]
        ]
        await query.edit_message_text(get_t(user_id, 'menu_text'), reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "menu_how":
        txt = get_config('how_to_use')
        vid = get_config('video_link')
        kb = [[InlineKeyboardButton("▶️ Watch Video", url=vid)], [InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="main_menu")]]
        await query.edit_message_text(f"💡 <b>How to Use:</b>\n\n{txt}", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "show_id":
        txt = get_t(user_id, 'id_text').format(name=query.from_user.first_name, id=user_id)
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="menu_all")]]), parse_mode=ParseMode.HTML)
        
    elif data == "show_guide":
        txt = get_config('guide_text')
        await query.edit_message_text(f"📖 <b>Guidelines:</b>\n\n{txt}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="menu_all")]]), parse_mode=ParseMode.HTML)

    elif data == "show_stats":
        with sqlite3.connect(DB_NAME) as conn:
            acc = conn.execute("SELECT value FROM stats WHERE key = 'total_accepted'").fetchone()[0]
            usr = conn.execute("SELECT COUNT(*) FROM bot_users").fetchone()[0]
        txt = f"📊 <b>System Stats:</b>\n\n👥 Total Users: {usr}\n✅ Total Accepted globally: {acc}"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="menu_all")]]), parse_mode=ParseMode.HTML)

    elif data == "show_premium":
        await query.answer("💎 Premium is activated for your account!", show_alert=True)

    elif data == "change_lang":
        kb = [[InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lng_bn"), InlineKeyboardButton("🇬🇧 English", callback_data="lng_en")],
              [InlineKeyboardButton("🇸🇦 العربية", callback_data="lng_ar"), InlineKeyboardButton("🇮🇳 हिन्दी", callback_data="lng_hi")],
              [InlineKeyboardButton("🇪🇸 Español", callback_data="lng_es"), InlineKeyboardButton("🇷🇺 Русский", callback_data="lng_ru")],
              [InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="main_menu")]]
        await query.edit_message_text("🌐 <b>Select your Language:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("lng_"):
        lang = data.split("_")[1]
        with sqlite3.connect(DB_NAME) as conn: conn.execute("UPDATE bot_users SET lang = ? WHERE user_id = ?", (lang, user_id))
        await query.answer(get_t(user_id, 'lang_msg'), show_alert=True)
        await show_main_menu(query, context)

    # User Channel Management
    elif data == "user_channels":
        with sqlite3.connect(DB_NAME) as conn:
            channels = conn.execute("SELECT chat_id, chat_title FROM channels WHERE owner_id = ?", (user_id,)).fetchall()
        if not channels:
            await query.edit_message_text("❌ <b>কোনো চ্যানেল নেই!</b>\nআগে আপনার চ্যানেলে আমাকে Admin করুন।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="main_menu")]]), parse_mode=ParseMode.HTML)
            return
        kb = [[InlineKeyboardButton(f"📢 {t}", callback_data=f"manage_{cid}")] for cid, t in channels]
        kb.append([InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="main_menu")])
        await query.edit_message_text("📋 <b>আপনার সংযুক্ত চ্যানেলসমূহ:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("manage_"):
        chat_id = int(data.split("_")[1])
        with sqlite3.connect(DB_NAME) as conn:
            ch = conn.execute("SELECT * FROM channels WHERE chat_id = ?", (chat_id,)).fetchone()
            pend = len(conn.execute("SELECT user_id FROM pending_requests WHERE chat_id = ?", (chat_id,)).fetchall())
        if not ch: return
        
        try: members_count = await context.bot.get_chat_member_count(chat_id)
        except: members_count = "Unknown"

        btn_ac = "🟢 ON" if ch[3] else "🔴 OFF"
        kb = [
            [InlineKeyboardButton(f"⚡ Approve Pending ({pend})", callback_data=f"apprv_all_{chat_id}")],
            [InlineKeyboardButton(f"Auto Accept: {btn_ac}", callback_data=f"tgl_ac_{chat_id}"), InlineKeyboardButton("✉️ Edit Welcome", callback_data=f"set_wel_{chat_id}")],
            [InlineKeyboardButton("📝 Post to this Channel", callback_data=f"usr_post_{chat_id}")],
            [InlineKeyboardButton("🔙 Back to List", callback_data="user_channels")]
        ]
        txt = f"⚙️ <b>কন্ট্রোল প্যানেল:</b> {ch[1]}\n\n🆔 চ্যানেল আইডি: <code>{chat_id}</code>\n👥 লাইভ মেম্বার: {members_count}\n⏳ পেন্ডিং রিকোয়েস্ট: {pend} জন"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("usr_post_"):
        chat_id = int(data.split("_")[2])
        context.user_data['state'] = f'USR_BC_{chat_id}'
        await query.edit_message_text("📝 <b>আপনার চ্যানেলে পোস্ট করুন:</b>\n\nযে মেসেজ বা ছবিটি পাঠাতে চান সেটি এখানে লিখে সেন্ড করুন।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

    elif data.startswith("tgl_ac_"):
        chat_id = int(data.split("_")[2])
        with sqlite3.connect(DB_NAME) as conn:
            val = 0 if conn.execute("SELECT auto_accept FROM channels WHERE chat_id=?", (chat_id,)).fetchone()[0] else 1
            conn.execute("UPDATE channels SET auto_accept = ? WHERE chat_id = ?", (val, chat_id))
        await button_handler(update, context)

    elif data.startswith("set_wel_"):
        chat_id = int(data.split("_")[2])
        context.user_data['state'] = f'WAITING_WELCOME_{chat_id}'
        await query.edit_message_text("📝 <b>নতুন ওয়েলকাম মেসেজ লিখুন:</b>\n(নামের জন্য <code>{user}</code> এবং চ্যানেলের নামের জন্য <code>{channel}</code> ব্যবহার করুন)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

    elif data.startswith("apprv_all_"):
        chat_id = int(data.split("_")[2])
        with sqlite3.connect(DB_NAME) as conn: pend = [r[0] for r in conn.execute("SELECT user_id FROM pending_requests WHERE chat_id = ?", (chat_id,)).fetchall()]
        if not pend: return await query.answer("কোনো পেন্ডিং রিকোয়েস্ট নেই!", show_alert=True)
        await query.edit_message_text(f"⏳ একসেপ্ট করা হচ্ছে... (0/{len(pend)})")
        for uid in pend:
            try:
                await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=uid)
                with sqlite3.connect(DB_NAME) as conn: conn.execute("UPDATE stats SET value = value + 1 WHERE key = 'total_accepted'")
                await asyncio.sleep(0.1)
            except: pass
        with sqlite3.connect(DB_NAME) as conn: conn.execute("DELETE FROM pending_requests WHERE chat_id = ?", (chat_id,))
        await query.edit_message_text("🎉 <b>সব রিকোয়েস্ট এপ্রুভ হয়েছে!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

    # Admin Functions
    elif data == "admin_cancel": await show_admin_panel(query, context)
    
    elif data == "edit_guide":
        context.user_data['state'] = 'EDIT_GUIDE'
        await query.edit_message_text("✏️ নতুন Guidelines মেসেজটি লিখে পাঠান:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel")]]))
    elif data == "edit_how":
        context.user_data['state'] = 'EDIT_HOW'
        await query.edit_message_text("✏️ নতুন How to use মেসেজটি লিখে পাঠান:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel")]]))
    elif data == "edit_vid":
        context.user_data['state'] = 'EDIT_VID'
        await query.edit_message_text("🎥 নতুন YouTube/Video লিংকটি পাঠান:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel")]]))

    elif data == "admin_ch_list":
        with sqlite3.connect(DB_NAME) as conn: channels = conn.execute("SELECT chat_id, chat_title, owner_id FROM channels").fetchall()
        txt = f"📡 <b>মোট চ্যানেল/গ্রুপ:</b> {len(channels)} টি\n\n"
        for ch in channels:
            with sqlite3.connect(DB_NAME) as conn: uname = conn.execute("SELECT first_name FROM bot_users WHERE user_id=?", (ch[2],)).fetchone()
            txt += f"📢 {ch[1]} (<code>{ch[0]}</code>)\n👤 Admin: {uname[0] if uname else 'Unknown'} (<code>{ch[2]}</code>)\n\n"
        await query.edit_message_text(txt if channels else "কোনো চ্যানেল নেই!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ব্যাক", callback_data="admin_cancel")]]), parse_mode=ParseMode.HTML)

    elif data == "admin_post_spec":
        context.user_data['state'] = 'WAITING_SPEC_CH_ID'
        await query.edit_message_text("📝 <b>নির্দিষ্ট চ্যানেলে পোস্ট:</b>\n\nচ্যানেলের ID লিখে সেন্ড করুন (যেমন: -100123456):", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="admin_cancel")]]))
    elif data == "admin_bc_ch":
        context.user_data['state'] = 'WAITING_BC_CH_MSG'
        await query.edit_message_text("📣 <b>সব চ্যানেলে ব্রডকাস্ট:</b>\n\nমেসেজ বা ছবি পাঠান:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="admin_cancel")]]))
    elif data == "admin_bc_usr":
        context.user_data['state'] = 'WAITING_BC_USR_MSG'
        await query.edit_message_text("👥 <b>ইউজার ব্রডকাস্ট:</b>\n\nমেসেজ পাঠান:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="admin_cancel")]]))
    elif data == "admin_autopost":
        context.user_data['state'] = 'WAITING_AUTOPOST_MSG'
        await query.edit_message_text("⏰ <b>অটো-পোস্ট সেটআপ:</b>\n\nঅটোমেটিক পোস্ট করার জন্য মেসেজটি দিন:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="admin_cancel")]]))

    elif data.startswith("ap_"):
        context.user_data['ap_type'] = data
        if data == "ap_spec_ch":
            context.user_data['state'] = 'WAITING_AUTOPOST_SPEC_ID'
            await query.edit_message_text("📝 নির্দিষ্ট চ্যানেল/গ্রুপের ID লিখে সেন্ড করুন:")
        else:
            context.user_data['state'] = 'WAITING_AUTOPOST_TIME'
            await query.edit_message_text("⏰ কত ঘন্টা পরপর পোস্ট হবে? (যেমন: 12 বা 24)")

    elif data == "admin_logout":
        context.user_data['is_admin'] = False
        await query.edit_message_text("✅ <b>লগআউট সফল।</b>", parse_mode=ParseMode.HTML)

# --- জয়েন রিকোয়েস্ট লজিক ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    chat_id, user_id, user_name, title = req.chat.id, req.from_user.id, req.from_user.first_name, req.chat.title
    with sqlite3.connect(DB_NAME) as conn: ch = conn.execute("SELECT auto_accept, auto_reject, welcome_msg FROM channels WHERE chat_id=?", (chat_id,)).fetchone()
    auto_acc, auto_rej, msg = ch if ch else (1, 0, None) # Default 1 (ON)

    if auto_acc:
        try:
            await context.bot.approve_chat_join_request(chat_id, user_id)
            with sqlite3.connect(DB_NAME) as conn: conn.execute("UPDATE stats SET value = value + 1 WHERE key = 'total_accepted'")
            try:
                final_msg = msg.replace("{user}", user_name).replace("{channel}", title) if msg else f"হ্যালো <b>{user_name}</b>!\n<b>{title}</b>-এ আপনাকে স্বাগতম!"
                await context.bot.send_message(user_id, final_msg, parse_mode=ParseMode.HTML)
            except: pass
        except: pass
    elif auto_rej:
        try: await context.bot.decline_chat_join_request(chat_id, user_id)
        except: pass
    else:
        with sqlite3.connect(DB_NAME) as conn: conn.execute("INSERT OR IGNORE INTO pending_requests (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))

# --- চ্যানেল ট্র্যাকার ---
async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = update.my_chat_member
    if res.new_chat_member.status in ["administrator", "member"]:
        with sqlite3.connect(DB_NAME) as conn: 
            conn.execute('''INSERT INTO channels (chat_id, chat_title, owner_id) VALUES (?, ?, ?) ON CONFLICT(chat_id) DO UPDATE SET chat_title=?, owner_id=?''', (res.chat.id, res.chat.title, res.from_user.id, res.chat.title, res.from_user.id))
        try: await context.bot.send_message(res.from_user.id, f"✅ <b>{res.chat.title}</b> চ্যানেলটি বটের সাথে যুক্ত হয়েছে!\n\n(অটো-একসেপ্ট বাই ডিফল্ট ON করা আছে।)", parse_mode=ParseMode.HTML)
        except: pass

def main():
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.job_queue.run_repeating(check_auto_posts, interval=120)

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("saddamadmin", saddamadmin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_text))
    
    print("🚀 Auto Accept Ultra Pro (v6.0) is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
