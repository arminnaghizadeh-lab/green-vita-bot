"""FSM states — فلوهای تشخیص بیماری، شناسایی گیاه، و پرونده گیاه."""

from aiogram.fsm.state import State, StatesGroup


class DiagnosisStates(StatesGroup):
    waiting_plant_name = State()     # منتظر اسم/نوع گیاه پس از دریافت عکس
    waiting_plant_details = State()  # منتظر توضیحات اضافه (اختیاری)


class IdentificationStates(StatesGroup):
    waiting_photo = State()  # منتظر عکس برای شناسایی گونه گیاه


class PlantStates(StatesGroup):
    waiting_name = State()     # منتظر اسم گیاه هنگام ثبت پرونده جدید
    waiting_species = State()  # منتظر نوع/گونه (اختیاری)


class ExpertVisitStates(StatesGroup):
    waiting_name = State()   # نام و نام خانوادگی برای تماس
    waiting_phone = State()  # شماره تلفن برای تماس
