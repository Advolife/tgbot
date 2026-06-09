from sqlalchemy import select
from app.db.engine import get_session_factory
from app.db.models import Lead

async def get_or_create_lead(tg_user_id, username, full_name):
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Lead).where(Lead.tg_user_id == tg_user_id, Lead.status == "in_progress").order_by(Lead.created_at.desc()).limit(1)
        lead = (await session.execute(stmt)).scalar_one_or_none()
        if lead is None:
            lead = Lead(tg_user_id=tg_user_id, username=username, full_name=full_name)
            session.add(lead)
            await session.commit()
            await session.refresh(lead)
        return lead

async def update_lead_field(lead_id, field, value):
    allowed = {"skolko_dlitsa_stress", "hochet_meditasiy", "dolg", "gor_hol", "nomer"}
    if field not in allowed:
        raise ValueError(f"Недопустимое поле: {field}")
    factory = get_session_factory()
    async with factory() as session:
        lead = await session.get(Lead, lead_id)
        if lead:
            setattr(lead, field, value)
            await session.commit()

async def mark_completed(lead_id):
    factory = get_session_factory()
    async with factory() as session:
        lead = await session.get(Lead, lead_id)
        if lead:
            lead.status = "completed"
            await session.commit()
            await session.refresh(lead)
            return lead
    return None

async def reset_lead(tg_user_id):
    factory = get_session_factory()
    async with factory() as session:
        stmt = select(Lead).where(Lead.tg_user_id == tg_user_id, Lead.status == "in_progress")
        for lead in (await session.execute(stmt)).scalars():
            lead.status = "abandoned"
        await session.commit()
