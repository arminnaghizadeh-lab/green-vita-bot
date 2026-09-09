"""Minimal async client for Bale Bot API."""

from __future__ import annotations

import re
from typing import Any

import httpx


class BaleApiError(RuntimeError):
    """Raised when Bale Bot API returns an error."""


def _clean_bale_text(text: str) -> str:
    """Normalize escaped newlines and remove raw HTML tags."""

    # تبدیل نویسه‌های خام escape شده به newline/tab واقعی
    text = text.replace("\\n", "\n")
    text = text.replace("\\r", "\r")
    text = text.replace("\\t", "\t")

    # حذف تگ‌های HTML که Bale در پیام plain-text نباید نشان دهد
    text = re.sub(r"<[^>]+>", "", text)

    # حذف فاصله‌های اضافی انتهای خطوط
    text = "\n".join(line.rstrip() for line in text.splitlines())

    # حداکثر یک خط خالی پشت‌سرهم
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


class BaleClient:
    def __init__(
        self,
        token: str,
        *,
        base_url: str = "https://tapi.bale.ai/bot",
        timeout: float = 35.0,
    ) -> None:
        token = token.strip()
        if not token:
            raise ValueError("BALE_BOT_TOKEN is empty")

        self._token = token
        self._base_url = f"{base_url.rstrip('/')}{token}"
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BaleClient":
        self._client = httpx.AsyncClient(
            timeout=self._timeout,
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def call(
        self,
        method: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        if self._client is None:
            raise RuntimeError("BaleClient must be used inside async context manager")

        request_kwargs: dict[str, Any] = {}

        if params is not None:
            request_kwargs["params"] = params

        if json is not None:
            # همه پیام‌های Bale از یک مسیر پاک‌سازی می‌شوند.
            if method == "sendMessage" and isinstance(json.get("text"), str):
                json = dict(json)
                json["text"] = _clean_bale_text(json["text"])

            request_kwargs["json"] = json

        response = await self._client.post(
            f"{self._base_url}/{method}",
            **request_kwargs,
        )

        try:
            data = response.json()
        except ValueError as exc:
            raise BaleApiError(
                f"Bale returned non-JSON response (HTTP {response.status_code})"
            ) from exc

        if response.is_error:
            description = data.get("description") or "HTTP error from Bale API"
            error_code = data.get("error_code")
            suffix = f" (code={error_code})" if error_code is not None else ""
            raise BaleApiError(
                f"HTTP {response.status_code}: {description}{suffix}"
            )

        if not data.get("ok", False):
            description = data.get("description") or "Unknown Bale API error"
            error_code = data.get("error_code")
            suffix = f" (code={error_code})" if error_code is not None else ""
            raise BaleApiError(f"{description}{suffix}")

        return data.get("result")

    async def get_me(self) -> dict[str, Any]:
        result = await self.call("getMe")
        return result or {}

    async def get_updates(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        timeout: int = 30,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "limit": limit,
            "timeout": timeout,
        }

        if offset > 0:
            params["offset"] = offset

        result = await self.call("getUpdates", params=params)
        return result or []

    async def get_file(self, file_id: str) -> dict[str, Any]:
        result = await self.call(
            "getFile",
            params={"file_id": file_id},
        )
        return result or {}

    async def download_file(self, file_id: str) -> bytes:
        file_info = await self.get_file(file_id)

        file_path = file_info.get("file_path")
        if not file_path:
            raise BaleApiError("Bale getFile returned no file_path")

        if self._client is None:
            raise RuntimeError(
                "BaleClient must be used inside async context manager"
            )

        file_url = f"https://tapi.bale.ai/file/bot{self._token}/{file_path}"

        response = await self._client.get(file_url)

        if response.is_error:
            raise BaleApiError(
                f"HTTP {response.status_code} while downloading Bale file"
            )

        return response.content


    async def send_message(
        self,
        *,
        chat_id: int,
        text: str,
        reply_markup: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
        }

        if reply_markup is not None:
            payload["reply_markup"] = reply_markup

        result = await self.call(
            "sendMessage",
            json=payload,
        )
        return result or {}
