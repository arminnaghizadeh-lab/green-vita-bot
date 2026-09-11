"""Handlerهای سراسری منوی اصلی تلگرام.

دکمه‌های منوی اصلی باید در تمام FSM stateها اولویت داشته باشند.
در صورت انتخاب هر دکمه، state فعلی پاک می‌شود و handler مقصد اجرا می‌شود.
"""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from src.bot.handlers.about import handle_about
from src.bot.handlers.diagnosis import (
    handle_diagnose_command,
    handle_direct_expert_visit,
)
from src.bot.handlers.help import handle_help
from src.bot.handlers.identification import handle_identify_command
from src.bot.handlers.plants import handle_my_plants
from src.bot.handlers.start import handle_start
from src.bot.keyboards.main_menu import (
    BTN_ABOUT,
    BTN_DIAGNOSE,
    BTN_EXPERT_VISIT,
    BTN_HELP,
    BTN_IDENTIFY,
    BTN_MY_PLANTS,
    BTN_START,
)

router = Router(name="main_menu")


async def _clear_state(state: FSMContext) -> None:
    await state.clear()


@router.message(CommandStart())
@router.message(F.text == BTN_START)
async def main_menu_start(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await _clear_state(state)
    await handle_start(message, session, state)


@router.message(Command("diagnose"))
@router.message(F.text == BTN_DIAGNOSE)
async def main_menu_diagnose(
    message: Message,
    state: FSMContext,
) -> None:
    await _clear_state(state)
    await handle_diagnose_command(message)


@router.message(Command("identify"))
@router.message(F.text == BTN_IDENTIFY)
async def main_menu_identify(
    message: Message,
    state: FSMContext,
) -> None:
    await _clear_state(state)
    await handle_identify_command(message, state)


@router.message(F.text == BTN_EXPERT_VISIT)
async def main_menu_expert_visit(
    message: Message,
    state: FSMContext,
) -> None:
    await _clear_state(state)
    await handle_direct_expert_visit(message, state)


@router.message(Command("plants"))
@router.message(F.text == BTN_MY_PLANTS)
async def main_menu_plants(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await _clear_state(state)
    await handle_my_plants(message, session)


@router.message(Command("about"))
@router.message(F.text == BTN_ABOUT)
async def main_menu_about(
    message: Message,
    state: FSMContext,
) -> None:
    await _clear_state(state)
    await handle_about(message)


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def main_menu_help(
    message: Message,
    state: FSMContext,
) -> None:
    await _clear_state(state)
    await handle_help(message)
