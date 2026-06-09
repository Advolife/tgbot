from aiogram import Bot
_bot = None
def set_bot(bot: Bot): global _bot; _bot = bot
def get_bot() -> Bot:
    if _bot is None: raise RuntimeError("Bot не инициализирован")
    return _bot
