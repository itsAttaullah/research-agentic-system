"""Shared HTTP client for network tools with hard size and timeout limits."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from sra.core.errors import ToolExecutionError


@dataclass(frozen=True, slots=True)
class HttpResponse:
    url: str
    status_code: int
    content_type: str
    text: str
    content: bytes


class HttpGateway:
    """Thin wrapper around httpx with research-safe defaults."""

    def __init__(
        self,
        *,
        user_agent: str = "StrategicResearchAgent/0.1 (+research; respectful-bot)",
        default_timeout: float = 30.0,
    ) -> None:
        self._user_agent = user_agent
        self._default_timeout = default_timeout

    async def get(
        self,
        url: str,
        *,
        timeout_seconds: float | None = None,
        max_response_bytes: int = 2_000_000,
        headers: dict[str, str] | None = None,
        params: dict[str, str | int] | None = None,
    ) -> HttpResponse:
        request_headers = {"User-Agent": self._user_agent, "Accept": "*/*"}
        if headers:
            request_headers.update(headers)

        timeout = timeout_seconds if timeout_seconds is not None else self._default_timeout
        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=timeout,
                headers=request_headers,
            ) as client:
                response = await client.get(url, params=params)
        except httpx.TimeoutException as exc:
            raise ToolExecutionError(
                f"HTTP request timed out for {url}",
                details={"url": url},
            ) from exc
        except httpx.HTTPError as exc:
            raise ToolExecutionError(
                f"HTTP request failed for {url}: {exc}",
                details={"url": url},
            ) from exc

        content = response.content
        if len(content) > max_response_bytes:
            raise ToolExecutionError(
                f"Response exceeded max_response_bytes ({max_response_bytes})",
                details={"url": url, "bytes": len(content)},
            )

        content_type = response.headers.get("content-type", "")
        try:
            text = response.text
        except Exception:  # noqa: BLE001 - binary payloads are common for PDFs
            text = ""

        return HttpResponse(
            url=str(response.url),
            status_code=response.status_code,
            content_type=content_type,
            text=text,
            content=content,
        )

    async def get_json(
        self,
        url: str,
        *,
        timeout_seconds: float | None = None,
        max_response_bytes: int = 2_000_000,
        headers: dict[str, str] | None = None,
        params: dict[str, str | int] | None = None,
    ) -> tuple[HttpResponse, object]:
        response = await self.get(
            url,
            timeout_seconds=timeout_seconds,
            max_response_bytes=max_response_bytes,
            headers=headers,
            params=params,
        )
        if response.status_code >= 400:
            raise ToolExecutionError(
                f"HTTP {response.status_code} from {url}",
                details={"status_code": response.status_code, "body": response.text[:500]},
            )
        try:
            payload = httpx.Response(
                response.status_code,
                content=response.content,
                headers={"content-type": response.content_type},
            ).json()
        except ValueError as exc:
            raise ToolExecutionError(
                f"Expected JSON from {url}",
                details={"body_preview": response.text[:500]},
            ) from exc
        return response, payload
