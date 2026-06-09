import logging
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Contact, Message
from app import texts
from app.config import Config
from app.db import repo
from app.services import notifier
from app.services.keyboards import options_kb, phone_request_kb, remove_kb
from app.services.phone import normalize_russian_phone
from app.services.scheduler import cancel_nudge, nudge_job_id, schedule_nudge
from app.states import Quiz

log = logging.getLogger(__name__)
router = Router()

def _username(m): return (m.from_user.first_name or m.from_user.username or "друг") if m.from_user else "друг"
async def _save(state, field, value):
    d = await state.get_data()
    if d.get("lead_id"): await repo.update_lead_field(d["lead_id"], field, value)
def _plan(cfg, user_id, step, *, long=False):
    schedule_nudge(nudge_job_id(user_id, step), cfg.timer_long_sec if long else cfg.timer_short_sec,
        "app.handlers.quiz:run_nudge", user_id=user_id, step=step)
def _cancel(user_id, step): cancel_nudge(nudge_job_id(user_id, step))
async def _rm_kb(msg):
    try: await msg.edit_reply_markup(reply_markup=None)
    except TelegramBadRequest: pass

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, cfg: Config):
    if not message.from_user: return
    await state.clear()
    for s in ("duration","meditation","debt","readiness","phone"): _cancel(message.from_user.id, s)
    lead = await repo.get_or_create_lead(message.from_user.id, message.from_user.username, message.from_user.full_name)
    await state.update_data(lead_id=lead.id)
    await state.set_state(Quiz.waiting_duration)
    await message.answer(texts.Q_DURATION.format(username=_username(message)), reply_markup=options_kb(texts.DURATION_OPTIONS, "dur"))
    _plan(cfg, message.from_user.id, "duration")

@router.message(Command("help"))
async def cmd_help(message: Message): await message.answer(texts.HELP_TEXT)

@router.message(Command("reset"))
async def cmd_reset(message: Message, state: FSMContext):
    if not message.from_user: return
    await state.clear()
    await repo.reset_lead(message.from_user.id)
    for s in ("duration","meditation","debt","readiness","phone"): _cancel(message.from_user.id, s)
    await message.answer(texts.RESET_TEXT, reply_markup=remove_kb())

@router.callback_query(Quiz.waiting_duration, F.data.startswith("dur:"))
async def on_duration(cb: CallbackQuery, state: FSMContext, cfg: Config):
    if not cb.data or not cb.from_user or not isinstance(cb.message, Message): return
    await _save(state, "skolko_dlitsa_stress", cb.data.split(":",1)[1])
    _cancel(cb.from_user.id, "duration"); await cb.answer(); await _rm_kb(cb.message)
    await state.set_state(Quiz.waiting_meditation)
    kb = options_kb(texts.MEDITATION_OPTIONS, "med")
    if texts.MEDITATION_VIDEO_FILE_ID:
        await cb.bot.send_video(cb.from_user.id, video=texts.MEDITATION_VIDEO_FILE_ID, caption=texts.Q_MEDITATION, reply_markup=kb)
    else:
        await cb.bot.send_message(cb.from_user.id, texts.Q_MEDITATION, reply_markup=kb)
    _plan(cfg, cb.from_user.id, "meditation")

@router.callback_query(Quiz.waiting_meditation, F.data.startswith("med:"))
async def on_meditation(cb: CallbackQuery, state: FSMContext, cfg: Config):
    if not cb.data or not cb.from_user or not isinstance(cb.message, Message): return
    await _save(state, "hochet_meditasiy", cb.data.split(":",1)[1])
    _cancel(cb.from_user.id, "meditation"); await cb.answer(); await _rm_kb(cb.message)
    await state.set_state(Quiz.waiting_debt)
    await cb.bot.send_message(cb.from_user.id, texts.Q_DEBT, reply_markup=options_kb(texts.DEBT_OPTIONS, "debt"))
    _plan(cfg, cb.from_user.id, "debt")

@router.callback_query(Quiz.waiting_debt, F.data.startswith("debt:"))
async def on_debt(cb: CallbackQuery, state: FSMContext, cfg: Config):
    if not cb.data or not cb.from_user or not isinstance(cb.message, Message): return
    await _save(state, "dolg", cb.data.split(":",1)[1])
    _cancel(cb.from_user.id, "debt"); await cb.answer(); await _rm_kb(cb.message)
    await state.set_state(Quiz.waiting_readiness)
    await cb.bot.send_message(cb.from_user.id, texts.Q_READINESS, reply_markup=options_kb(texts.READINESS_OPTIONS, "rdy"))
    _plan(cfg, cb.from_user.id, "readiness")

@router.callback_query(Quiz.waiting_readiness, F.data.startswith("rdy:"))
async def on_readiness(cb: CallbackQuery, state: FSMContext, cfg: Config):
    if not cb.data or not cb.from_user or not isinstance(cb.message, Message): return
    await _save(state, "gor_hol", cb.data.split(":",1)[1])
    _cancel(cb.from_user.id, "readiness"); await cb.answer(); await _rm_kb(cb.message)
    await state.set_state(Quiz.waiting_phone)
    await cb.bot.send_message(cb.from_user.id, texts.Q_PHONE.format(username=_username(cb)), reply_markup=phone_request_kb())
    _plan(cfg, cb.from_user.id, "phone", long=True)

@router.message(Quiz.waiting_phone, F.contact)
async def on_phone_contact(message: Message, state: FSMContext, cfg: Config):
    c: Contact = message.contact
    if not c or not message.from_user: return
    if c.user_id and c.user_id != message.from_user.id: await message.answer(texts.PHONE_INVALID); return
    phone = normalize_russian_phone(c.phone_number)
    if not phone: await message.answer(texts.PHONE_INVALID); return
    await _finalize(message, state, cfg, phone)

@router.message(Quiz.waiting_phone, F.text)
async def on_phone_text(message: Message, state: FSMContext, cfg: Config):
    if not message.text or not message.from_user: return
    phone = normalize_russian_phone(message.text)
    if not phone: await message.answer(texts.PHONE_INVALID); return
    await _finalize(message, state, cfg, phone)

async def _finalize(message, state, cfg, phone):
    await _save(state, "nomer", phone)
    _cancel(message.from_user.id, "phone")
    d = await state.get_data()
    if d.get("lead_id"):
        lead = await repo.mark_completed(d["lead_id"])
        if lead:
            try: await notifier.notify_admin(message.bot, cfg.admin_chat_id, lead)
            except Exception: log.exception("Ошибка отправки лида")
    await state.set_state(Quiz.done)
    await message.answer(texts.FINAL_THANKS, reply_markup=remove_kb())

@router.message(Command("export"))
async def cmd_export(message: Message, cfg: Config):
    if not message.from_user or message.from_user.id not in cfg.admin_user_ids: return
    try: await notifier.export_leads_csv(message.bot, message.chat.id)
    except Exception: log.exception("Ошибка экспорта"); await message.answer("Ошибка. Смотри логи.")

@router.message(F.text)
async def fallback(message: Message, state: FSMContext):
    if await state.get_state() is None:
        await message.answer("Напишите /start чтобы начать. /help — все команды.")
    else:
        await message.answer("Пожалуйста, выберите вариант с помощью кнопок выше.")

async def run_nudge(user_id: int, step: str):
    from sqlalchemy import select
    from app.db.engine import get_session_factory
    from app.db.models import Lead
    from app.services.bot_ctx import get_bot
    bot = get_bot()
    name = "друг"
    async with get_session_factory()() as session:
        lead = (await session.execute(select(Lead).where(Lead.tg_user_id==user_id).order_by(Lead.created_at.desc()).limit(1))).scalar_one_or_none()
        if lead:
            if lead.status == "completed": return
            name = (lead.full_name or "").split()[0] or lead.username or "друг"
    tpl = {"duration": texts.NUDGE_AFTER_DURATION, "meditation": texts.NUDGE_AFTER_MEDITATION,
           "debt": texts.NUDGE_AFTER_MEDITATION, "readiness": texts.NUDGE_AFTER_MEDITATION,
           "phone": texts.NUDGE_AFTER_PHONE_PROMPT}.get(step)
    if tpl:
        try: await bot.send_message(user_id, tpl.format(username=name))
        except Exception: log.warning("Дожим не отправлен: %s %s", user_id, step)
