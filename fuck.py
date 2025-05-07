import logging
import random
import time
import base64
import requests
from telegram import Update, MessageEntity
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

LEARN_FILE = "learn.txt"
ADMIN_LEARN_FILE = "admin.txt"
ADMIN_LIST_FILE = "admins.txt"
mode = {"learn": False, "work": False, "admin_learn": False}
user_message_times = {}
OWNER_USERNAME = "ZxRTYREN"

# GitHub Config
GITHUB_USERNAME = "zxrayush95"
GITHUB_REPO = "ZxR-ONLINE"
GITHUB_BRANCH = "main"
GITHUB_TOKEN = "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"

# Custom logging format
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def log_operation(operation, details):
    """Custom log function for important operations with color formatting"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    # Define color codes for formatting
    BOLD = "\033[1m"
    CYAN = "\033[36m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    RESET = "\033[0m"

    # Operation name in bold cyan
    print(f"\n{BOLD}{CYAN}[{timestamp}] {operation.upper()}{RESET}")
    print("-" * 50)

    # Loop through the details and display them with appropriate formatting
    for key, value in details.items():
        if key == "user":
            color = CYAN + BOLD
        elif key == "status" and isinstance(value, str):
            if "failed" in value.lower():
                color = RED + BOLD
            elif "success" in value.lower():
                color = GREEN + BOLD
            else:
                color = CYAN + BOLD
        else:
            color = CYAN + BOLD
        print(f"{color}{key}: {value}{RESET}")
    print("-" * 50 + "\n")

def github_file_url(filename):
    return f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{filename}"

def create_file_if_missing(filename, content):
    url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{filename}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 404:
        log_operation("file creation", {
            "file": filename,
            "status": "not found, creating...",
            "content": content[:100] + "..." if len(content) > 100 else content
        })
        data = {
            "message": f"Create {filename}",
            "content": base64.b64encode(content.encode()).decode(),
            "branch": GITHUB_BRANCH
        }
        create_response = requests.put(url, headers=headers, json=data)
        if create_response.status_code in [201, 200]:
            log_operation("file created", {
                "file": filename,
                "status": "success"
            })
        else:
            log_operation("file creation failed", {
                "file": filename,
                "status": create_response.status_code,
                "response": create_response.text
            })
    elif response.status_code == 200:
        log_operation("file check", {
            "file": filename,
            "status": "already exists"
        })
    else:
        log_operation("file check error", {
            "file": filename,
            "status": response.status_code,
            "response": response.text
        })

def fetch_file_from_github(filename):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(github_file_url(filename), headers=headers)
    if response.status_code == 200:
        content = base64.b64decode(response.json()['content']).decode("utf-8")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        log_operation("file fetched", {
            "file": filename,
            "status": "success",
            "lines": len(content.splitlines())
        })
    else:
        log_operation("file fetch failed", {
            "file": filename,
            "status": response.status_code,
            "response": response.text
        })
        with open(filename, "w", encoding="utf-8") as f:
            f.write("")
        if filename == ADMIN_LIST_FILE:
            create_file_if_missing(ADMIN_LIST_FILE, "")
        elif filename == ADMIN_LEARN_FILE:
            create_file_if_missing(ADMIN_LEARN_FILE, "")

def update_file_to_github(filename):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    get_resp = requests.get(github_file_url(filename), headers=headers)
    sha = get_resp.json()["sha"] if get_resp.status_code == 200 else None
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    data = {
        "message": f"Update {filename}",
        "content": encoded,
        "branch": GITHUB_BRANCH
    }
    if sha:
        data["sha"] = sha
    put_resp = requests.put(github_file_url(filename), headers=headers, json=data)
    if put_resp.status_code == 200:
        log_operation("file updated", {
            "file": filename,
            "status": "success",
            "lines": len(content.splitlines()),
            "changes": "see file content"
        })
    else:
        log_operation("file update failed", {
            "file": filename,
            "status": put_resp.status_code,
            "response": put_resp.text
        })

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    log_operation("command received", {
        "command": "/start",
        "user": f"{user.username} ({user.id})",
        "chat": update.effective_chat.title if update.effective_chat.type != "private" else "private chat"
    })
    await update.message.reply_text("Bot activated. Use /learn, /work, /adminteach.")

def is_spamming(user_id):
    now = time.time()
    times = [t for t in user_message_times.get(user_id, []) if now - t < 5]
    times.append(now)
    user_message_times[user_id] = times
    if len(times) >= 5:
        log_operation("spam detected", {
            "user_id": user_id,
            "messages": len(times),
            "action": "flood restricted for 5s"
        })
        return True
    return False

async def is_admin_or_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)
    is_admin = False
    
    if user.username == OWNER_USERNAME:
        is_admin = True
    elif member.status in ["administrator", "creator"]:
        is_admin = True
    elif user.username and user.username in get_admins():
        is_admin = True
        
    log_operation("admin check", {
        "user": f"{user.username} ({user.id})",
        "status": "admin/owner" if is_admin else "regular user",
        "chat": chat.title if chat.type != "private" else "private chat"
    })
    
    return is_admin

def get_admins():
    try:
        with open(ADMIN_LIST_FILE, "r", encoding="utf-8") as f:
            admins = [line.strip() for line in f.readlines() if line.strip()]
            log_operation("admins list", {
                "total_admins": len(admins),
                "admins": ", ".join(admins) if admins else "none"
            })
            return admins
    except Exception as e:
        log_operation("admins list error", {
            "error": str(e)
        })
        return []

def add_admin(username):
    admins = get_admins()
    if username not in admins:
        admins.append(username)
        with open(ADMIN_LIST_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(admins))
        update_file_to_github(ADMIN_LIST_FILE)
        log_operation("admin added", {
            "username": username,
            "total_admins_now": len(admins)
        })

async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("Permission Denied.")
        return
    mode["learn"] = True
    mode["work"] = False
    mode["admin_learn"] = False
    log_operation("mode change", {
        "user": update.message.from_user.username,
        "new_mode": "learn",
        "status": "enabled"
    })
    await update.message.reply_text("Learning mode enabled.")

async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("Permission Denied.")
        return
    # Enable both work and learn modes
    mode["work"] = True
    mode["learn"] = True  # Enable learning as well
    mode["admin_learn"] = False  # Optionally disable admin learning if required

    log_operation("mode change", {
        "user": update.message.from_user.username,
        "new_modes": "work + learn",
        "status": "enabled"
    })

    await update.message.reply_text("Work mode and Learn mode are both enabled. Both work and learning are active.")
    
    # Optionally, load the learned content if the learn mode is enabled
    if mode["learn"]:
        filename = LEARN_FILE  # Default to the learn file
        with open(filename, "r", encoding="utf-8") as f:
            learned_content = f.read()
            if learned_content:
                log_operation("learned content", {
                    "status": "loaded",
                    "content_snippet": learned_content[:100]  # Show first 100 characters
                })
                await update.message.reply_text(f"Learned content available:\n{learned_content[:100]}")

async def adminteach(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("Permission Denied.")
        return
    mode["admin_learn"] = True
    log_operation("mode change", {
        "user": update.message.from_user.username,
        "new_mode": "admin_learn",
        "status": "enabled"
    })
    await update.message.reply_text("Admin teaching mode enabled.")

async def toat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode["admin_learn"] = False
    log_operation("mode change", {
        "user": update.message.from_user.username,
        "new_mode": "admin_learn",
        "status": "disabled"
    })
    await update.message.reply_text("Admin teaching mode disabled.")

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.username != OWNER_USERNAME:
        await update.message.reply_text("Only the owner can add admins.")
        return
    if context.args:
        username = context.args[0].lstrip("@")
        add_admin(username)
        await update.message.reply_text(f"@{username} added as admin.")
    else:
        await update.message.reply_text("Usage: /addadmin @username")

async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = message.from_user
    user_id = user.id
    text = message.text or ""
    chat_title = update.effective_chat.title if update.effective_chat.type != "private" else "Private Chat"
    
    if is_spamming(user_id):
        await message.reply_text("Spam Flood Restricted User For 5s")
        return

    if user.username == OWNER_USERNAME and "@ZxRTYREN" in text:
        await message.reply_text("😽 My Owner: @ZxRTYREN")
        log_operation("owner mention", {
            "user": f"{user.username} ({user.id})",
            "chat": chat_title,
            "response": "owner mention reply"
        })
        return
    if "@zx_owner" in text:
        await message.reply_text("😎 Bade Log Hai Krten Honge")
        log_operation("special mention", {
            "user": f"{user.username} ({user.id})",
            "chat": chat_title,
            "response": "special mention reply"
        })
        return

    learned = False
    filename = LEARN_FILE
    is_admin = await is_admin_or_owner(update, context)

    if is_admin:
        if mode["admin_learn"]:
            filename = ADMIN_LEARN_FILE

    if mode["learn"] or mode["admin_learn"]:
        learned_content = ""
        with open(filename, "a", encoding="utf-8") as f:
            if message.sticker:
                content = "STICKER:" + message.sticker.file_id + "\n"
                f.write(content)
                learned_content = "sticker added"
            elif text:
                content = "TEXT:" + text.strip() + "\n"
                f.write(content)
                learned_content = text[:50] + "..." if len(text) > 50 else text
            learned = True

        if learned:
            update_file_to_github(filename)
            log_operation("content learned", {
                "file": filename,
                "user": f"{user.username} ({user.id})",
                "chat": chat_title,
                "content": learned_content,
                "mode": "admin_learn" if mode["admin_learn"] else "learn"
            })

    if mode["work"]:
        lines = []
        if is_admin:
            try:
                with open(ADMIN_LEARN_FILE, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
            except Exception as e:
                log_operation("file read error", {
                    "file": ADMIN_LEARN_FILE,
                    "error": str(e)
                })
        else:
            try:
                with open(LEARN_FILE, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f.readlines() if line.strip()]
            except Exception as e:
                log_operation("file read error", {
                    "file": LEARN_FILE,
                    "error": str(e)
                })

        if lines:
            response = None
            if message.text:
                choices = [line for line in lines if line.startswith("TEXT:") and line[5:] != message.text]
                if choices:
                    response_text = random.choice(choices)[5:]
                    await message.reply_text(response_text)
                    response = response_text[:50] + "..." if len(response_text) > 50 else response_text
            elif message.sticker:
                choices = [line for line in lines if line.startswith("STICKER:")]
                if choices:
                    sticker_id = random.choice(choices)[8:]
                    await message.reply_sticker(sticker_id)
                    response = f"sticker: {sticker_id[:20]}..."
            
            if response:
                log_operation("bot response", {
                    "user": f"{user.username} ({user.id})",
                    "chat": chat_title,
                    "request": text[:50] + "..." if len(text) > 50 else text if text else "sticker",
                    "response": response,
                    "is_admin": is_admin,
                    "source_file": ADMIN_LEARN_FILE if is_admin else LEARN_FILE
                })

async def tagall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("Permission Denied.")
        return
    mentions = [f"@{admin}" for admin in get_admins()]
    if mentions:
        await update.message.reply_text("||" + " ".join(mentions) + "||")
        log_operation("tagall command", {
            "user": update.message.from_user.username,
            "chat": update.effective_chat.title if update.effective_chat.type != "private" else "private chat",
            "admins_tagged": len(mentions)
        })
    else:
        await update.message.reply_text("No admins to tag.")
        log_operation("tagall command", {
            "user": update.message.from_user.username,
            "chat": update.effective_chat.title if update.effective_chat.type != "private" else "private chat",
            "status": "no admins to tag"
        })

import logging
import httpx
def suppress_httpx_logs():
    """
    Suppresses HTTP request logs from the httpx library by setting the logging level to WARNING or higher.
    """
    # Set the logging level of httpx to WARNING to suppress INFO logs
    logging.getLogger('httpx').setLevel(logging.WARNING)

def main():
    # Suppress httpx logs
    suppress_httpx_logs()

    # Initial file operations
    for file in [LEARN_FILE, ADMIN_LEARN_FILE, ADMIN_LIST_FILE]:
        fetch_file_from_github(file)

    # Ensure that admin.txt and admins.txt are created if missing
    create_file_if_missing(ADMIN_LIST_FILE, "")
    create_file_if_missing(ADMIN_LEARN_FILE, "")

    bot_token = "7503492760:AAG-zV-QY5FMWsolAanwcfK8Nr8e3qCMMfg"
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("learn", learn))
    app.add_handler(CommandHandler("work", work))
    app.add_handler(CommandHandler("adminteach", adminteach))
    app.add_handler(CommandHandler("toat", toat))
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("tagall", tagall))
    app.add_handler(MessageHandler(filters.ALL, handle_all))

    log_operation("bot startup", {
        "status": "running",
        "files_initialized": f"{LEARN_FILE}, {ADMIN_LEARN_FILE}, {ADMIN_LIST_FILE}"
    })
    app.run_polling()

if __name__ == "__main__":
    main()
