"""هندلر /about — معرفی کلینیک گیاه‌پزشکی گرین‌ویتا (placeholder)."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router(name="about")

ABOUT_TEXT = (
    "🌿 <b>کلینیک گیاه‌پزشکی گرین‌ویتا</b>\n\n"
    "دستیار هوشمند گرین‌ویتا با هدف کمک به علاقمندان گل و گیاه ساخته شده تا "
    "تشخیص بیماری، مراقبت روزانه و مشاوره تخصصی گیاهان را ساده‌تر کند.\n\n"
    "این نسخه، اسکلت اولیه پروژه است — امکانات کامل به‌تدریج اضافه می‌شود."
)


@router.message(Command("about"))
async def handle_about(message: Message) -> None:
    await message.answer(ABOUT_TEXT)
