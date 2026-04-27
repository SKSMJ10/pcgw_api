import re
from aiolimiter import AsyncLimiter

def sluggify(text: str) -> str:
    text = text.lower()
    slugged = re.sub(r"[^\w-]+", "-", text)
    slugged = slugged.strip("-")
    return slugged

limiter = AsyncLimiter(max_rate= 6, time_period= 60)