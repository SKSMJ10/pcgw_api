import re

def sluggify(text: str) -> str:
    text = text.lower()
    slugged = re.sub(r"[^\w-]+", "-", text)
    slugged = slugged.strip("-")
    return slugged
