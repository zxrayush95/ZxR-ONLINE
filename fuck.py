import logging
import random
import time
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)

LEARN_FILE = "learn.txt"
mode = {"learn": False, "work": False}
user_message_times = {}  # Anti-spam tracking
OWNER_USERNAME = "ZxRTYREN"  # Owner's username for verification

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot activated.\nUse /learn or /work.")

# Verify if user is admin or owner
# Verify if user is admin or owner
async def is_admin_or_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    chat = update.effective_chat
    member = await context.bot.get_chat_member(chat.id, user.id)
    
    # Check if user is the owner (username match)
    if user.username == OWNER_USERNAME:
        return True
    
    # Check if user is an admin
    if member.status in ["administrator", "creator"]:
        return True
    
    return False
    
# /learn command (admin/owner only)
# /learn command (admin/owner only)
async def learn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):  # pass context here
        await update.message.reply_text("Permission Denied: You are not authorized to use this command.")
        return
    
    mode["learn"] = True
    mode["work"] = False
    await update.message.reply_text("Learning mode enabled.")

# /work command (admin/owner only)
async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin_or_owner(update, context):  # pass context here
        await update.message.reply_text("Permission Denied: You are not authorized to use this command.")
        return
    
    mode["learn"] = False
    mode["work"] = True
    await update.message.reply_text("Work mode enabled. Bot is now learning and responding.")

# Anti-spam check
def is_spamming(user_id):
    now = time.time()
    times = user_message_times.get(user_id, [])
    times = [t for t in times if now - t < 5]  # Keep messages from last 5 seconds
    times.append(now)
    user_message_times[user_id] = times
    return len(times) >= 5

# Message handler
async def handle_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id

    # Anti-spam filter
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

    # Reply if in work mode
    if mode["work"] and learned:
        try:
            with open(LEARN_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                lines = [line.strip() for line in lines if line.strip()]
                if not lines:
                    await message.reply_text("Nothing learned yet.")
                    return

                # Choose a different reply than what user sent (text only)
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

# /tagall command
# List to store known users
known_users = []

# When a user sends a message, add them to the known users list
# List to store known user IDs
known_users = []

# Function to handle incoming messages and add users to the list
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

    # Generate user mentions from the known_users list
    user_mentions = [f"@{user_id}" for user_id in known_users if user_id is not None]
    
    # If there are no valid users, return early
    if not user_mentions:
        await update.message.reply_text("No users to mention.")
        return

    # Join the mentions into a single string and apply spoiler formatting
    tag_message = " ".join(user_mentions)
    tag_message = f"||{tag_message}||"  # Spoiler the message

    # Send the tag-all message
    await update.message.reply_text(tag_message)

# Main bot runner
def main():
    bot_token = "7503492760:AAG-zV-QY5FMWsolAanwcfK8Nr8e3qCMMfg"  # Replace with your real bot token
    app = ApplicationBuilder().token(bot_token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("learn", learn))
    app.add_handler(CommandHandler("work", work))
    app.add_handler(CommandHandler("tagall", tagall))
    app.add_handler(MessageHandler(filters.ALL, handle_all))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()