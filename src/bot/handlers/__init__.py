from aiogram import Router

from src.bot.handlers import about, diagnosis, help, identification, start


def get_root_router() -> Router:
    """
    همه‌ی روترهای هندلرها را در یک روتر ریشه ترکیب می‌کند.

    ترتیب مهم است: identification قبل از diagnosis ثبت می‌شود چون هندلر عکسِ
    آن به state خاص محدود است (IdentificationStates.waiting_photo)، در حالی که
    هندلر عکسِ diagnosis روی همه‌ی حالت‌ها فعال است — باید اول شانس بررسی را
    به هندلر محدودتر بدهیم.
    """
    root = Router(name="root")
    root.include_router(start.router)
    root.include_router(help.router)
    root.include_router(about.router)
    root.include_router(identification.router)
    root.include_router(diagnosis.router)
    return root
