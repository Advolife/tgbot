import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def _required(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise RuntimeError(f"Не задана переменная окружения: {name}")
    return val

def _int_list(name: str) -> list[int]:
    raw = os.getenv(name, "")
    return [int(x.strip()) for x in raw.split(",") if x.strip()]

@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_chat_id: int
    admin_user_ids: list[int]
    database_url: str
    timer_short_sec: int = 5 * 60
    timer_long_sec: int = 60 * 60

def load_config() -> Config:
    return Config(
        bot_token=_required("BOT_TOKEN"),
        admin_chat_id=int(_required("ADMIN_CHAT_ID")),
        admin_user_ids=_int_list("ADMIN_USER_IDS"),
        database_url=_required("DATABASE_URL"),
        timer_short_sec=int(os.getenv("TIMER_SHORT_SEC", 5 * 60)),
        timer_long_sec=int(os.getenv("TIMER_LONG_SEC", 60 * 60)),
    )
