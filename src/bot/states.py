"""FSM states — فلوهای تشخیص بیماری و شناسایی گیاه از روی عکس."""

from aiogram.fsm.state import State, StatesGroup


class DiagnosisStates(StatesGroup):
    waiting_plant_name = State()     # منتظر اسم/نوع گیاه پس از دریافت عکس
    waiting_plant_details = State()  # منتظر توضیحات اضافه (اختیاری)


class IdentificationStates(StatesGroup):
    waiting_photo = State()  # منتظر عکس برای شناسایی گونه گیاه
