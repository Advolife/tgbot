from aiogram.fsm.state import State, StatesGroup

class Quiz(StatesGroup):
    waiting_duration = State()
    waiting_meditation = State()
    waiting_debt = State()
    waiting_readiness = State()
    waiting_phone = State()
    done = State()
