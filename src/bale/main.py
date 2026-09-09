"""Green Vita Bale bot entrypoint."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.bale.client import BaleApiError, BaleClient
from src.bale.handlers import dispatch_callback, dispatch_message
from src.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger("green-vita-bale")


def _message_from_update(
    update: dict[str, Any],
) -> dict[str, Any] | None:
    message = update.get("message")
    return message if isinstance(message, dict) else None


def _callback_from_update(
    update: dict[str, Any],
) -> dict[str, Any] | None:
    callback = update.get("callback_query")
    return callback if isinstance(callback, dict) else None


async def handle_message(
    client: BaleClient,
    message: dict[str, Any],
) -> None:
    chat = message.get("chat") or {}
    chat_id = chat.get("id")

    if chat_id is None:
        logger.warning("Ignoring Bale message without chat id")
        return

    await dispatch_message(
        client,
        message,
        int(chat_id),
    )


async def handle_callback(
    client: BaleClient,
    callback: dict[str, Any],
) -> None:
    callback_id = callback.get("id")
    data = str(callback.get("data") or "")

    callback_message = callback.get("message") or {}
    chat = callback_message.get("chat") or {}
    chat_id = chat.get("id")

    if callback_id:
        try:
            await client.call(
                "answerCallbackQuery",
                json={
                    "callback_query_id": str(callback_id),
                },
            )
        except BaleApiError as exc:
            logger.warning(
                "Could not answer Bale callback id=%s: %s",
                callback_id,
                exc,
            )

    if chat_id is None:
        logger.warning(
            "Ignoring Bale callback without chat id: data=%s",
            data,
        )
        return

    sender = callback.get("from") or {}

    message = {
        "from": sender,
        "chat": chat,
        "text": "",
    }

    logger.info(
        "Bale callback received: data=%s chat_id=%s",
        data,
        chat_id,
    )

    await dispatch_callback(
        client,
        message,
        int(chat_id),
        data,
    )


async def run_bale() -> None:
    settings = get_settings()

    if not settings.bale_bot_token:
        raise RuntimeError("BALE_BOT_TOKEN is not configured")

    offset = 0

    async with BaleClient(
        settings.bale_bot_token,
        base_url=settings.bale_api_base_url,
    ) as client:
        me = await client.get_me()

        logger.info(
            "Bale bot connected: id=%s username=%s",
            me.get("id"),
            me.get("username"),
        )

        logger.info("Starting Bale long polling...")

        while True:
            try:
                updates = await client.get_updates(
                    offset=offset,
                    limit=100,
                    timeout=10,
                )

                for update in updates:
                    update_id = update.get("update_id")

                    if isinstance(update_id, int):
                        offset = max(offset, update_id + 1)

                    message = _message_from_update(update)
                    callback = _callback_from_update(update)

                    try:
                        if message is not None:
                            await handle_message(
                                client,
                                message,
                            )
                        elif callback is not None:
                            await handle_callback(
                                client,
                                callback,
                            )

                    except Exception:
                        logger.exception(
                            "Failed to process Bale update_id=%s",
                            update_id,
                        )

            except (BaleApiError, asyncio.TimeoutError) as exc:
                logger.error(
                    "Bale API/polling error: %s; retrying in 5 seconds",
                    exc,
                )
                await asyncio.sleep(5)

            except Exception:
                logger.exception(
                    "Unexpected Bale worker error; retrying in 5 seconds"
                )
                await asyncio.sleep(5)


def main() -> None:
    asyncio.run(run_bale())


if __name__ == "__main__":
    main()
