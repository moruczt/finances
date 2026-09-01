import os
from typing import Literal

from pydantic import create_model
from openai import AsyncOpenAI

from utils import log

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

_client = None
def get_client():
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None
        _client = AsyncOpenAI(api_key=api_key)
    return _client

async def suggest_category(raw_data:dict, categories:dict) -> int|None:
    """Ask OpenAI to pick the single best matching category id for a raw transaction row,
    constrained to the given set of valid category ids (so it can never suggest a category
    that doesn't exist). Returns None if no suggestion could be made - no API key configured,
    nothing to choose from, or the request failed."""
    client = get_client()
    if client is None or not categories:
        return None

    CategorySuggestion = create_model(
        "CategorySuggestion",
        category_id=(Literal[tuple(categories.keys())], ...),
    )

    category_list = "\n".join(f"{cid}: {path}" for cid, path in categories.items())
    prompt = (
        "You are categorizing a personal finance transaction into one of a fixed set of "
        "accounting categories, based on a raw bank export row. Pick the single best "
        "matching category id.\n\n"
        f"Available categories (id: path):\n{category_list}\n\n"
        f"Raw transaction data:\n{raw_data}"
    )

    try:
        response = await client.chat.completions.parse(
            model=OPENAI_MODEL,
            messages=[{"role":"user", "content":prompt}],
            response_format=CategorySuggestion,
        )
        parsed = response.choices[0].message.parsed
        return parsed.category_id if parsed else None
    except Exception as err:
        log(f"OpenAI category suggestion failed: {err}", "warning")
        return None
