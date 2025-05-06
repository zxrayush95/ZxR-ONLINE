import logging
import random
import time
import base64
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

LEARN_FILE = "learn.txt"
mode = {"learn": False, "work": False}
user_message_times = {}  # Anti-spam tracking
OWNER_USERNAME = "ZxRTYREN"  # Owner's username for verification

# GitHub Config
GITHUB_USERNAME = "zxrayush95"
GITHUB_REPO = "ZxR-ONLINE"
GITHUB_BRANCH = "main"
GITHUB_FILE_PATH = "learn.txt"
GITHUB_TOKEN = "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"  # Replace with your PAT (keep safe)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# GitHub file URL
def github_file_url():
    return f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}"

# Fetch learn.txt from GitHub
def fetch_learn_file():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    response = requests.get(github_file_url(), headers=headers)
    if response.status_code == 200:
        content = response.json()['content']
        decoded = base64.b64decode(content).decode("utf-8")
        with open(LEARN_FILE, "w", encoding="utf-8") as f:
            f.write(decoded)
        print("learn.txt fetched from GitHub.")
    else:
        print("Failed to fetch learn.txt from GitHub.")

# Update learn.txt to GitHub
def update_learn_file():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    get_resp = requests.get(github_file_url(), headers=headers)
    if get_resp.status_code != 200:
        print("Failed to get file SHA from GitHub.")
        return

    sha = get_resp.json()["sha"]

    with open(LEARN_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    encoded = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    data = {
        "message": "Update learn.txt",
        "content": encoded,
        "branch": GITHUB_BRANCH,
        "sha": sha
    }

    put_resp = requests.put(github_file_url(), headers=headers, json=data)
    if put_resp.status_code == 200:
        print("learn.txt updated to GitHub.")
    else:
        print("Failed to update learn.txt to GitHub.")

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot activated.\nUse /learn or /work.")

# Admin/owner check
async def is_admin_or_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)

    if user.username == OWNER_USERNAME:
        return True
    if member.status in ["administrator", "creator"]:
        return True
    return False

# /learn command
async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("Permission Denied: You are not authorized to use this command.")
        return
    mode["learn"] = True
    mode["work"] = False
    await update.message.reply_text("Learning mode enabled.")

# /work command
async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("Permission Denied: You are not authorized to use this command.")
        return
    mode["learn"] = False
    mode["work"] = True
    await update.message.reply_text("Work mode enabled. Bot is now learning and responding.")

# Anti-spam logic
def is_spamming(user_id):
    now = time.time()
    times = user_message_times.get(user_id, [])
    times = [t for t in times if now - t < 5]
    times.append(now)
    user_message_times[user_id] = times
    return len(times) >= 5

# Handle all messages
async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id

    if is_spamming(user_id):
        await message.reply_text("Spam Flood Restricted User For 5s")
        return

    learned = False

    # Learn sticker
    if message.sticker:
        with open(LEARN_FILE, "a", encoding="utf-8") as f:
            f.write("STICKER:" + message.sticker.file_id + "\n")
        learned = True

    # Learn text
    elif message.text:
        text = message.text.strip()
        with open(LEARN_FILE, "a", encoding="utf-8") as f:
            f.write("TEXT:" + text + "\n")
        learned = True

    if learned:
        update_learn_file()

    if mode["work"] and learned:
        try:
            with open(LEARN_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                lines = [line.strip() for line in lines if line.strip()]
                if not lines:
                    await message.reply_text("Nothing learned yet.")
                    return

                if message.text:
                    choices = [line for line in lines if not line.startswith("STICKER:") and line[5:] != message.text]
                    if choices:
                        reply = random.choice(choices)
                        await message.reply_text(reply[5:])
                    else:
                        await message.reply_text("I'm still learning more...")
                elif message.sticker:
                    stickers = [line for line in lines if line.startswith("STICKER:")]
                    if stickers:
                        sticker_id = random.choice(stickers)[8:]
                        await message.reply_sticker(sticker_id)
        except FileNotFoundError:
            await message.reply_text("No learn.txt found.")

# User tracking
known_users = []

async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in known_users:
        known_users.append(user_id)

# /tagall command
async def tagall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):
        await update.message.reply_text("Permission Denied: You are not authorized to use this command.")
        return

    if not known_users:
        await update.message.reply_text("No users found to tag.")
        return

    user_mentions = [f"@{user_id}" for user_id in known_users if user_id is not None]
    if not user_mentions:
        await update.message.reply_text("No users to mention.")
        return

    tag_message = " ".join(user_mentions)
    tag_message = f"||{tag_message}||"
    await update.message.reply_text(tag_message)

# Main
def main():
    fetch_learn_file()  # Load learn.txt from GitHub on startup
    bot_token = "7503492760:AAG-zV-QY5FMWsolAanwcfK8Nr8e3qCMMfg"  # Your actual token
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("learn", learn))
    app.add_handler(CommandHandler("work", work))
    app.add_handler(CommandHandler("tagall", tagall))
    app.add_handler(MessageHandler(filters.ALL, handle_all))
    app.add_handler(MessageHandler(filters.ALL, on_message))  # Add known users

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
