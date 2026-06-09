import csv, io
from datetime import datetime
from aiogram import Bot
from aiogram.types import BufferedInputFile
from sqlalchemy import select
from app.db.engine import get_session_factory
from app.db.models import Lead

_LABELS = {
    "1-2_months":"1-2 месяца","3-6_months":"3-6 месяцев","6+_months":"от 6+ месяцев",
    "yes":"Да","no":"Нет","300-600k":"300-600 тыс ₽","600k-1m":"600к-1 млн ₽",
    "1m+":"более 1 млн ₽","1-3":"1-3 (не готов)","4-7":"4-7","8-10":"8-10 (готов)",
}

def _label(v): return _LABELS.get(v, v) if v else "—"

def format_lead(lead):
    return (
        "🔥 <b>Новый лид</b>\n\n"
        f"<b>Имя:</b> {lead.full_name or '—'}\n"
        f"<b>Username:</b> {'@'+lead.username if lead.username else '—'}\n"
        f"<b>TG ID:</b> <code>{lead.tg_user_id}</code>\n"
        f"<b>Телефон:</b> <code>{lead.nomer or '—'}</code>\n\n"
        f"<b>Длительность стресса:</b> {_label(lead.skolko_dlitsa_stress)}\n"
        f"<b>Медитация:</b> {_label(lead.hochet_meditasiy)}\n"
        f"<b>Долг:</b> {_label(lead.dolg)}\n"
        f"<b>Готовность:</b> {_label(lead.gor_hol)}\n\n"
        f"<i>{lead.created_at:%Y-%m-%d %H:%M UTC}</i>"
    )

async def notify_admin(bot, admin_chat_id, lead):
    await bot.send_message(admin_chat_id, format_lead(lead))

async def export_leads_csv(bot, chat_id):
    async with get_session_factory()() as session:
        leads = (await session.execute(select(Lead).order_by(Lead.created_at.desc()))).scalars().all()
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["id","created_at","status","tg_user_id","username","full_name","phone","duration","meditation","debt","readiness"])
    for l in leads:
        w.writerow([l.id, l.created_at.strftime("%Y-%m-%d %H:%M:%S"), l.status,
            l.tg_user_id, l.username or "", l.full_name or "", l.nomer or "",
            _label(l.skolko_dlitsa_stress), _label(l.hochet_meditasiy), _label(l.dolg), _label(l.gor_hol)])
    data = buf.getvalue().encode("utf-8-sig")
    await bot.send_document(chat_id, BufferedInputFile(data, f"leads_{datetime.utcnow():%Y%m%d_%H%M}.csv"))
