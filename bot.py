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

# 🌐 ২৪ ঘণ্টা সার্ভার সজাগ রাখার জন্য
from keep_alive import keep_alive

# --- কনফিগারেশন ---
BOT_TOKEN = "8690240616:AAFzk942XkVODDA9EYtY1eDaIrs5B9XjNX4" # ⚠️ আপনার টোকেন দিন
SUPPORT_CHANNEL_LINK = "https://t.me/Grp_Sale_999"
UPDATES_CHANNEL_LINK = "https://t.me/+Ial-E3ydfKQzMjc1"

# 👑 আপনার গড-লেভেল এডমিন আইডি
ADMIN_ID = 6836865426

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
DB_NAME = "fast_accepter.db"

# --- ২ ভাষার ডিকশনারি (English & Bengali) ---
TEXTS = {
    'en': {
        'start_msg': "✨ <b>I'm Alive and Super Fast!</b> 🚀\n\nI can approve new join requests in your channels or groups automatically in <b>0.1 seconds</b>.\n\n✅ Just add me as an Administrator in your channel or group with <i>'Invite Users'</i> permission.\n\n👇 <b>Use the below buttons to add me to your chat:</b>",
        'btn_up_ch': "🤖 Bot Updates Channel",
        'btn_lang': "🌐 Language",
        'btn_help': "ℹ️ Help",
        'btn_add_ch': "↗️ Add me to a channel!",
        'btn_add_gr': "➕ Add me to a group!",
        'btn_settings': "⚙️ Settings & My Channels",
        'menu_text': "⚙️ <b>Settings & My Channels:</b>\nSelect an option below to manage your bot and channels:",
        'btn_id': "🆔 My ID", 
        'btn_guide': "📖 Guidelines", 
        'btn_on_my_ch': "📢 My Channels",
        'btn_stats': "📊 Bot Stats", 
        'btn_support': "🎧 Support", 
        'btn_back': "🔙 Back",
        'id_text': "👤 <b>Your Profile:</b>\n\n📝 Name: {name}\n🆔 User ID: <code>{id}</code>",
        'guide_text': "📖 <b>Guidelines:</b>\n\n1. Add this bot to your channel/group as an admin.\n2. Ensure the bot has 'Invite Users' permission.\n3. The bot will automatically accept all new join requests in 0.1 seconds.\n4. You can broadcast messages and view stats from the settings menu.",
        'help_text': "ℹ️ <b>Help Menu - Commands List:</b>\n\n/start - Open the main menu of the bot.\n/admin - Open the Super Admin Dashboard (Only for the owner).\n\n<i>Use the inline buttons for navigation and managing your channels easily!</i>",
        'lang_msg': "✅ <b>Language successfully set to English!</b>"
    },
    'bn': {
        'start_msg': "✨ <b>আমি এলাইভ এবং সুপার ফাস্ট!</b> 🚀\n\nআমি আপনার চ্যানেল বা গ্রুপে আসা নতুন জয়েন রিকোয়েস্ট মাত্র <b>০.১ সেকেন্ডে</b> অটোমেটিক এপ্রুভ করতে পারি।\n\n✅ আমাকে শুধু আপনার চ্যানেল বা গ্রুপে <i>'Invite Users'</i> পারমিশন দিয়ে এডমিন বানিয়ে দিন।\n\n👇 <b>আমাকে আপনার চ্যাটে এড করতে নিচের বাটনগুলো ব্যবহার করুন:</b>",
        'btn_up_ch': "🤖 Bot Updates Channel",
        'btn_lang': "🌐 ভাষা (Language)",
        'btn_help': "ℹ️ হেল্প (Help)",
        'btn_add_ch': "↗️ Add me to a channel!",
        'btn_add_gr': "➕ Add me to a group!",
        'btn_settings': "⚙️ Settings & My Channels",
        'menu_text': "⚙️ <b>সেটিংস ও আমার চ্যানেলসমূহ:</b>\nআপনার চ্যানেল এবং বট ম্যানেজ করতে নিচের অপশনগুলো ব্যবহার করুন:",
        'btn_id': "🆔 আমার আইডি", 
        'btn_guide': "📖 গাইডলাইন", 
        'btn_on_my_ch': "📢 আমার চ্যানেলসমূহ",
        'btn_stats': "📊 বটের স্ট্যাটাস", 
        'btn_support': "🎧 সাপোর্ট", 
        'btn_back': "🔙 ব্যাক",
        'id_text': "👤 <b>আপনার প্রোফাইল:</b>\n\n📝 নাম: {name}\n🆔 ইউজার আইডি: <code>{id}</code>",
        'guide_text': "📖 <b>গাইডলাইন:</b>\n\n১. এই বটটিকে আপনার চ্যানেল/গ্রুপে এডমিন করুন।\n২. বটকে অবশ্যই 'Invite Users' পারমিশন দিন।\n৩. বট অটোমেটিকভাবে সব জয়েন রিকোয়েস্ট ০.১ সেকেন্ডে এপ্রুভ করবে।\n৪. আপনি সেটিংস থেকে সব কিছু কন্ট্রোল করতে পারবেন।",
        'help_text': "ℹ️ <b>হেল্প মেনু - কমান্ড লিস্ট:</b>\n\n/start - বটের মেইন মেনু ওপেন করার জন্য।\n/admin - সুপার এডমিন ড্যাশবোর্ড ওপেন করার জন্য (শুধু মালিকের জন্য)।\n\n<i>সহজে চ্যানেল ম্যানেজ করতে বটের বাটনগুলো ব্যবহার করুন!</i>",
        'lang_msg': "✅ <b>ভাষা সফলভাবে বাংলায় পরিবর্তন করা হয়েছে!</b>"
    }
}

def get_t(user_id, key):
    with sqlite3.connect(DB_NAME) as conn:
        row = conn.execute("SELECT lang FROM bot_users WHERE user_id = ?", (user_id,)).fetchone()
        lang = row[0] if row and row[0] in TEXTS else 'en' # ডিফল্ট English
    return TEXTS.get(lang, TEXTS['en']).get(key, TEXTS['en'].get(key, ""))

# --- ডাটাবেজ সেটআপ ---
def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS channels (
            chat_id INTEGER PRIMARY KEY, chat_title TEXT, owner_id INTEGER, 
            auto_accept INTEGER DEFAULT 1, auto_reject INTEGER DEFAULT 0, welcome_msg TEXT DEFAULT NULL
        )''')
        conn.execute("CREATE TABLE IF NOT EXISTS pending_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id INTEGER, user_id INTEGER, UNIQUE(chat_id, user_id))")
        conn.execute("CREATE TABLE IF NOT EXISTS bot_users (user_id INTEGER PRIMARY KEY, first_name TEXT, joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP, lang TEXT DEFAULT 'en')")
        conn.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, value INTEGER DEFAULT 0)")
        conn.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_accepted', 0)")
        conn.execute("INSERT OR IGNORE INTO stats (key, value) VALUES ('total_messages', 0)")
        try: conn.execute("ALTER TABLE bot_users ADD COLUMN lang TEXT DEFAULT 'en'")
        except: pass
        conn.commit()
init_db()

def save_user(user_id, first_name):
    with sqlite3.connect(DB_NAME) as conn: conn.execute("INSERT OR IGNORE INTO bot_users (user_id, first_name) VALUES (?, ?)", (user_id, first_name))

# --- স্টার্ট ফাংশন (New Layout) ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id, user.first_name)
    context.user_data['state'] = None
    bot_uname = context.bot.username

    txt = get_t(user.id, 'start_msg')
    
    kb = [
        [InlineKeyboardButton(get_t(user.id, 'btn_up_ch'), url=UPDATES_CHANNEL_LINK)],
        [InlineKeyboardButton(get_t(user.id, 'btn_lang'), callback_data="change_lang"), InlineKeyboardButton(get_t(user.id, 'btn_help'), callback_data="help_menu")],
        [InlineKeyboardButton(get_t(user.id, 'btn_add_ch'), url=f"https://t.me/{bot_uname}?startchannel=true&admin=invite_users")],
        [InlineKeyboardButton(get_t(user.id, 'btn_add_gr'), url=f"https://t.me/{bot_uname}?startgroup=true&admin=invite_users")],
        [InlineKeyboardButton(get_t(user.id, 'btn_settings'), callback_data="settings_menu")]
    ]

    if update.message: await update.message.reply_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else: await update.callback_query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

# --- এডমিন প্যানেল ---
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == ADMIN_ID:
        await show_admin_panel(update, context)
    else:
        await update.message.reply_text("❌ You are not authorized!")

async def show_admin_panel(update_or_message, context):
    context.user_data['state'] = None
    
    with sqlite3.connect(DB_NAME) as conn:
        acc = conn.execute("SELECT value FROM stats WHERE key = 'total_accepted'").fetchone()[0]
        msg_count = conn.execute("SELECT value FROM stats WHERE key = 'total_messages'").fetchone()[0]
        ch = conn.execute("SELECT COUNT(*) FROM channels").fetchone()[0]
        usr = conn.execute("SELECT COUNT(*) FROM bot_users").fetchone()[0]
        pend = conn.execute("SELECT COUNT(*) FROM pending_requests").fetchone()[0]

    text = (
        f"👑 <b>Super Admin Dashboard</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: <b>{usr}</b>\n"
        f"💬 Total Messages: <b>{msg_count}</b>\n"
        f"📢 Total Channels: <b>{ch}</b>\n"
        f"⏳ Pending Requests: <b>{pend}</b>\n"
        f"✅ Total Approved: <b>{acc}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👇 <i>Select an action:</i>"
    )
    kb = [
        [InlineKeyboardButton("📣 User Broadcast", callback_data="admin_bc_usr")],
        [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ]
    
    if hasattr(update_or_message, 'reply_text'): 
        await update_or_message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    elif hasattr(update_or_message, 'message') and update_or_message.message:
        await update_or_message.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
    else: 
        await update_or_message.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

# --- টেক্সট ইনপুট রাউটার ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    user_id = update.effective_user.id
    is_admin = (user_id == ADMIN_ID)
    
    # Message stats update
    with sqlite3.connect(DB_NAME) as conn: 
        conn.execute("UPDATE stats SET value = value + 1 WHERE key = 'total_messages'")
        conn.commit()

    if state == 'WAITING_BC_USR_MSG' and is_admin:
        with sqlite3.connect(DB_NAME) as conn: users = [u[0] for u in conn.execute("SELECT user_id FROM bot_users").fetchall()]
        msg = await update.message.reply_text(f"⏳ Sending to {len(users)} users...")
        success = 0
        for uid in users:
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
                success += 1
                await asyncio.sleep(0.05)
            except: pass
        await msg.edit_text(f"✅ Broadcast Successful! ({success}/{len(users)})")
        await show_admin_panel(update, context)
        
    elif state and state.startswith("WAITING_WELCOME_"):
        chat_id = int(state.split("_")[2])
        with sqlite3.connect(DB_NAME) as conn: 
            conn.execute("UPDATE channels SET welcome_msg = ? WHERE chat_id = ?", (update.message.text, chat_id))
            conn.commit()
        context.user_data['state'] = None
        await update.message.reply_text("✅ <b>Welcome message saved!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

    elif state and state.startswith("USR_BC_"):
        chat_id = int(state.split("_")[2])
        try:
            await context.bot.copy_message(chat_id=chat_id, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)
            await update.message.reply_text("✅ <b>Message successfully posted to your channel!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)
        except Exception:
            await update.message.reply_text("❌ <b>Failed!</b> Make sure the bot has post permissions.", parse_mode=ParseMode.HTML)
        context.user_data['state'] = None

# --- বাটন হ্যান্ডলার ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if not data.startswith("ap_"): context.user_data['state'] = None

    if data == "main_menu":
        await start_command(update, context)
        
    elif data == "help_menu":
        txt = get_t(user_id, 'help_text')
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="main_menu")]]), parse_mode=ParseMode.HTML)
    
    elif data == "settings_menu":
        kb = [
            [InlineKeyboardButton(get_t(user_id, 'btn_id'), callback_data="show_id"), InlineKeyboardButton(get_t(user_id, 'btn_guide'), callback_data="show_guide")],
            [InlineKeyboardButton(get_t(user_id, 'btn_on_my_ch'), callback_data="user_channels"), InlineKeyboardButton(get_t(user_id, 'btn_stats'), callback_data="show_stats")],
            [InlineKeyboardButton(get_t(user_id, 'btn_support'), url=SUPPORT_CHANNEL_LINK)],
            [InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="main_menu")]
        ]
        await query.edit_message_text(get_t(user_id, 'menu_text'), reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data == "show_id":
        txt = get_t(user_id, 'id_text').format(name=query.from_user.first_name, id=user_id)
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="settings_menu")]]), parse_mode=ParseMode.HTML)
        
    elif data == "show_guide":
        txt = get_t(user_id, 'guide_text')
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="settings_menu")]]), parse_mode=ParseMode.HTML)

    elif data == "show_stats":
        with sqlite3.connect(DB_NAME) as conn:
            acc = conn.execute("SELECT value FROM stats WHERE key = 'total_accepted'").fetchone()[0]
            usr = conn.execute("SELECT COUNT(*) FROM bot_users").fetchone()[0]
            msg_count = conn.execute("SELECT value FROM stats WHERE key = 'total_messages'").fetchone()[0]
        txt = f"📊 <b>Bot Stats:</b>\n\n👥 Total Users: {usr}\n✅ Total Accepted globally: {acc}\n💬 Total Users Message: {msg_count}"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="settings_menu")]]), parse_mode=ParseMode.HTML)

    elif data == "change_lang":
        kb = [
            [InlineKeyboardButton("🇬🇧 English", callback_data="lng_en"), InlineKeyboardButton("🇧🇩 বাংলা", callback_data="lng_bn")],
            [InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="main_menu")]
        ]
        await query.edit_message_text("🌐 <b>Select your Language:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("lng_"):
        lang = data.split("_")[1]
        with sqlite3.connect(DB_NAME) as conn: 
            conn.execute("UPDATE bot_users SET lang = ? WHERE user_id = ?", (lang, user_id))
            conn.commit()
        await query.answer(get_t(user_id, 'lang_msg'), show_alert=True)
        await start_command(update, context)

    # User Channel Management
    elif data == "user_channels":
        with sqlite3.connect(DB_NAME) as conn:
            channels = conn.execute("SELECT chat_id, chat_title FROM channels WHERE owner_id = ?", (user_id,)).fetchall()
        if not channels:
            await query.edit_message_text("❌ <b>No channels found!</b>\nAdd me as an Admin to your channel first.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="settings_menu")]]), parse_mode=ParseMode.HTML)
            return
        kb = [[InlineKeyboardButton(f"📢 {t}", callback_data=f"manage_{cid}")] for cid, t in channels]
        kb.append([InlineKeyboardButton(get_t(user_id, 'btn_back'), callback_data="settings_menu")])
        await query.edit_message_text("📋 <b>Your Connected Channels:</b>", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("manage_"):
        chat_id = int(data.split("_")[1])
        with sqlite3.connect(DB_NAME) as conn:
            ch = conn.execute("SELECT * FROM channels WHERE chat_id = ?", (chat_id,)).fetchone()
            pend = len(conn.execute("SELECT user_id FROM pending_requests WHERE chat_id = ?", (chat_id,)).fetchall())
        if not ch: return
        
        try: members_count = await context.bot.get_chat_member_count(chat_id)
        except: members_count = "Unknown"

        # Auto Accept Status Logic
        ac_status = ch[3]
        kb = [
            [InlineKeyboardButton(f"⚡ Approve All Pending ({pend})", callback_data=f"apprv_all_{chat_id}")],
            [InlineKeyboardButton("🟢 Auto Accept ON" if ac_status else "Auto Accept ON", callback_data=f"tgl_ac_on_{chat_id}"), 
             InlineKeyboardButton("🔴 Auto Accept OFF" if not ac_status else "Auto Accept OFF", callback_data=f"tgl_ac_off_{chat_id}")],
            [InlineKeyboardButton("✉️ Edit Welcome", callback_data=f"set_wel_{chat_id}"), InlineKeyboardButton("📊 Channel Stats", callback_data=f"ch_stats_{chat_id}")],
            [InlineKeyboardButton("📝 Post to this Channel", callback_data=f"usr_post_{chat_id}")],
            [InlineKeyboardButton("🔙 Back", callback_data="user_channels")]
        ]
        txt = f"⚙️ <b>Control Panel: {ch[1]}</b> 👇\n\n🆔 Channel ID: <code>{chat_id}</code>\n👥 Live Members: {members_count}\n⏳ Pending Requests: {pend}"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)

    elif data.startswith("tgl_ac_on_"):
        chat_id = int(data.split("_")[3])
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("UPDATE channels SET auto_accept = 1, auto_reject = 0 WHERE chat_id = ?", (chat_id,))
            conn.commit()
        # Refresh the current menu
        query.data = f"manage_{chat_id}"
        await button_handler(update, context)

    elif data.startswith("tgl_ac_off_"):
        chat_id = int(data.split("_")[3])
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("UPDATE channels SET auto_accept = 0 WHERE chat_id = ?", (chat_id,))
            conn.commit()
        query.data = f"manage_{chat_id}"
        await button_handler(update, context)
        
    elif data.startswith("ch_stats_"):
        chat_id = int(data.split("_")[2])
        try: members_count = await context.bot.get_chat_member_count(chat_id)
        except: members_count = "Unknown"
        with sqlite3.connect(DB_NAME) as conn: pend = len(conn.execute("SELECT user_id FROM pending_requests WHERE chat_id = ?", (chat_id,)).fetchall())
        txt = f"📊 <b>Channel Stats:</b>\n\n👥 Total Members: {members_count}\n⏳ Pending Requests: {pend}\n\n<i>Note: Old pending requests before adding the bot cannot be fetched by API.</i>"
        await query.edit_message_text(txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

    elif data.startswith("usr_post_"):
        chat_id = int(data.split("_")[2])
        context.user_data['state'] = f'USR_BC_{chat_id}'
        await query.edit_message_text("📝 <b>Post to your channel:</b>\n\nSend the message or photo you want to post.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

    elif data.startswith("set_wel_"):
        chat_id = int(data.split("_")[2])
        context.user_data['state'] = f'WAITING_WELCOME_{chat_id}'
        await query.edit_message_text("📝 <b>Enter new Welcome Message:</b>\n(Use <code>{user}</code> for name and <code>{channel}</code> for channel title)", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

    elif data.startswith("apprv_all_"):
        chat_id = int(data.split("_")[2])
        with sqlite3.connect(DB_NAME) as conn: pend = [r[0] for r in conn.execute("SELECT user_id FROM pending_requests WHERE chat_id = ?", (chat_id,)).fetchall()]
        if not pend: return await query.answer("No pending requests to approve!", show_alert=True)
        await query.edit_message_text(f"⏳ Accepting requests... (0/{len(pend)})")
        for uid in pend:
            try:
                await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=uid)
                with sqlite3.connect(DB_NAME) as conn: 
                    conn.execute("UPDATE stats SET value = value + 1 WHERE key = 'total_accepted'")
                    conn.commit()
                await asyncio.sleep(0.1)
            except: pass
        with sqlite3.connect(DB_NAME) as conn: 
            conn.execute("DELETE FROM pending_requests WHERE chat_id = ?", (chat_id,))
            conn.commit()
        await query.edit_message_text("🎉 <b>All requests approved!</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=f"manage_{chat_id}")]]), parse_mode=ParseMode.HTML)

    # Admin Functions
    elif data == "admin_bc_usr":
        context.user_data['state'] = 'WAITING_BC_USR_MSG'
        await query.edit_message_text("👥 <b>User Broadcast:</b>\n\nSend message:", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")]]))

    elif data == "admin_close":
        await query.message.delete()

# --- জয়েন রিকোয়েস্ট লজিক (New Promo Message) ---
async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    chat_id, user_id, user_name, title = req.chat.id, req.from_user.id, req.from_user.first_name, req.chat.title
    with sqlite3.connect(DB_NAME) as conn: ch = conn.execute("SELECT auto_accept, auto_reject, welcome_msg FROM channels WHERE chat_id=?", (chat_id,)).fetchone()
    auto_acc, auto_rej, msg = ch if ch else (1, 0, None) 

    if auto_acc:
        try:
            await context.bot.approve_chat_join_request(chat_id, user_id)
            with sqlite3.connect(DB_NAME) as conn: 
                conn.execute("UPDATE stats SET value = value + 1 WHERE key = 'total_accepted'")
                conn.commit()
            try:
                # Promotional Message on Join
                promo_msg = (
                    f"🎉 <b>{user_name}</b> 👋\n\n"
                    f"✅ Your join request to <b>{title}</b> has been successfully approved!\n\n"
                    f"🔥 <b>A Special Gift for You:</b>\n"
                    f"Do you want to download videos and music (MP3) from TikTok, Facebook, YouTube, or Instagram without any <i>Watermark</i>?\n\n"
                    f"👇 <i>Use our Premium Downloader Bot for completely free:</i>\n"
                    f"👉 @AllInOneDL_AIBot"
                )
                final_msg = msg.replace("{user}", user_name).replace("{channel}", title) if msg else promo_msg
                
                bot_uname = context.bot.username
                kb = [
                    [InlineKeyboardButton("📥 Open Video Downloader Bot", url="https://t.me/AllInOneDL_AIBot")],
                    [InlineKeyboardButton("↗️ Add me to a channel!", url=f"https://t.me/{bot_uname}?startchannel=true&admin=invite_users")],
                    [InlineKeyboardButton("➕ Add me to a group!", url=f"https://t.me/{bot_uname}?startgroup=true&admin=invite_users")]
                ]
                await context.bot.send_message(user_id, final_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.HTML)
            except: pass
        except: pass
    elif auto_rej:
        try: await context.bot.decline_chat_join_request(chat_id, user_id)
        except: pass
    else:
        with sqlite3.connect(DB_NAME) as conn: 
            conn.execute("INSERT OR IGNORE INTO pending_requests (chat_id, user_id) VALUES (?, ?)", (chat_id, user_id))
            conn.commit()

# --- চ্যানেল ট্র্যাকার ---
async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    res = update.my_chat_member
    if res.new_chat_member.status in ["administrator", "member"]:
        with sqlite3.connect(DB_NAME) as conn: 
            conn.execute('''INSERT INTO channels (chat_id, chat_title, owner_id) VALUES (?, ?, ?) ON CONFLICT(chat_id) DO UPDATE SET chat_title=?, owner_id=?''', (res.chat.id, res.chat.title, res.from_user.id, res.chat.title, res.from_user.id))
            conn.commit()
        try: await context.bot.send_message(res.from_user.id, f"✅ <b>{res.chat.title}</b> added successfully!\n\n(Auto-Accept is ON by default)", parse_mode=ParseMode.HTML)
        except: pass

def main():
    keep_alive()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("admin", admin_command))  
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_text))
    
    print("🚀 Super Fast Accept Bot (v8.0) is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
