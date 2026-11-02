import re
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from aiolimiter import AsyncLimiter


def sluggify(text: str) -> str:
    text = text.lower()
    slugged = re.sub(r"[^\w]+", "-", text)
    slugged = slugged.strip("-")
    return slugged


limiter = AsyncLimiter(max_rate=1, time_period=1)


def is_transient(exception: Exception) -> bool:
    if isinstance(exception, httpx.RequestError):
        return True
    if isinstance(exception, httpx.HTTPStatusError):
        return (
            exception.response.status_code == 429
            or exception.response.status_code >= 500
        )
    return False


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(1, min=2, max=10),
    retry=retry_if_exception(is_transient),
    reraise=True,
)
async def request_with_retries(
    client: httpx.AsyncClient, method: str, url: str, **kwargs
) -> httpx.Response:
    async with limiter:
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        return response
