import telebot

# Замените 'YOUR_TELEGRAM_BOT_TOKEN' на токен вашего бота, полученный у BotFather
TOKEN = 8169183380:AAEp2I0Bb_Ljnzd4n8gMaDbVPLuFCi6BFDk

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

bot.infinity_polling()
