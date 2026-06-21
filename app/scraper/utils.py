import re
from aiolimiter import AsyncLimiter
import httpx


def sluggify(text: str) -> str:
    text = text.lower()
    slugged = re.sub(r"[^\w]+", "-", text)
    slugged = slugged.strip("-")
    return slugged


limiter = AsyncLimiter(max_rate=1, time_period=2)


def is_transient(exception: Exception) -> bool:
    if isinstance(exception, httpx.RequestError):
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        return exception.response.status_code >= 500
    return False
