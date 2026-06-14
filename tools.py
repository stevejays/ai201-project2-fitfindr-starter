"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    # 1. Load every listing from the dataset.
    listings = load_listings()

    # Guard: nothing to match against if the description is blank.
    if not description or not description.strip():
        return []

    # Break the query into lowercase words. "vintage graphic tee" ->
    # {"vintage", "graphic", "tee"}
    query_words = set(description.lower().split())

    scored = []  # (score, listing) pairs for everything that matches

    for listing in listings:
        # 2a. Price filter (hard — must be exact). None = no ceiling.
        if max_price is not None and listing["price"] > max_price:
            continue

        # 2b. Size filter (soft substring match: "M" matches "S/M").
        # None = any size.
        if size is not None:
            if size.lower() not in listing["size"].lower():
                continue

        # 3. Score by keyword overlap. Build one searchable blob from the
        # fields most likely to hold relevant words.
        searchable_text = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
        ]).lower()

        score = sum(1 for word in query_words if word in searchable_text)

        # 4. Drop listings with no keyword overlap.
        if score == 0:
            continue

        scored.append((score, listing))

    # 5. Sort by score, highest first; return just the listing dicts.
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [listing for score, listing in scored][:8]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    # Replace this with your implementation

    # ── PART 1: Branch on input (before any API call) ──
    # The required failure mode: an empty wardrobe. Decide the path in plain
    # Python first; the LLM only handles the language part.
    items = wardrobe.get("items", [])
    has_wardrobe = len(items) > 0

    # ── PART 2: Render the structured data into readable text ──
    # The model can't see the dicts — turn the fields that matter for styling
    # into clear text.
    item_desc = (
        f"{new_item['title']} "
        f"(category: {new_item['category']}, "
        f"colors: {', '.join(new_item['colors'])}, "
        f"style: {', '.join(new_item['style_tags'])})"
    )

    # ── PART 3: Build the right prompt for the branch ──
    if has_wardrobe:
        # Render each wardrobe piece as a readable line.
        wardrobe_lines = "\n".join(
            f"- {it['name']} ({it['category']}, {', '.join(it['colors'])})"
            for it in items
        )
        system_msg = (
            "You are a sharp, practical personal stylist who helps people style "
            "secondhand finds using clothes they already own. You suggest specific, "
            "wearable combinations — never generic advice."
        )
        user_msg = (
            f"I'm considering buying this thrifted item:\n{item_desc}\n\n"
            f"Here's what's already in my wardrobe:\n{wardrobe_lines}\n\n"
            "Suggest 2 complete outfits built around the new item, using specific "
            "pieces from my wardrobe by name. Format each outfit exactly like this:\n\n"
            "Outfit 1: [vibe in 3-5 words]\n"
            "- New item: [the thrifted piece]\n"
            "- [other pieces, each named from my wardrobe]\n"
            "Why it works: [one sentence]\n\n"
            "Then Outfit 2 in the same format."
        )
    else:
        # Empty-wardrobe fallback: pieces AND vibe (your choice).
        system_msg = (
            "You are a sharp, practical personal stylist helping someone who hasn't "
            "told you what's in their closet yet."
        )
        user_msg = (
            f"I'm considering buying this thrifted item:\n{item_desc}\n\n"
            "I haven't entered my wardrobe yet. Give me general styling guidance:\n"
            "1. The overall vibe and aesthetic this piece fits.\n"
            "2. What types of pieces (not specific brands) would pair well with it "
            "to build a complete outfit.\n"
            "Keep it concrete and practical."
        )

    # ── PART 4: Guarded API call (the required error handling) ──
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,  # some creativity, but still grounded
        )
        # ── PART 5: Extract and return the text ──
        return response.choices[0].message.content.strip()

    except Exception as e:
        # Never crash the agent. Return a usable fallback string.
        return (
            f"Couldn't generate outfit suggestions right now ({e}). "
            f"As a starting point, {new_item['title']} works well with neutral "
            f"basics and pieces that echo its {', '.join(new_item['style_tags'][:2])} vibe."
        )


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.
    Returns a 2-4 sentence caption. If outfit is empty/missing, returns a
    descriptive error string -- does NOT raise.
    """
    # PART 1: Guard the outfit STRING (outfit is text, not a wardrobe).
    if not outfit or not outfit.strip():
        return "Couldn't create a fit card because the outfit information is missing."

    # PART 2: Render the item details the caption should mention.
    item_name = new_item.get("title", "this piece")
    price = new_item.get("price", "?")
    platform = new_item.get("platform", "secondhand")

    # PART 3: One prompt, asking for a single caption.
    system_msg = (
        "You write short, authentic outfit captions for social media -- the kind "
        "a real person posts with an OOTD photo. Casual, specific, a little playful. "
        "Never sound like a product listing or an ad."
    )
    user_msg = (
        f"I just thrifted this: {item_name} (${price}, found on {platform}).\n\n"
        f"Here's how I'm styling it:\n{outfit}\n\n"
        "Write a 2-4 sentence caption for my post. Mention the item name, the price, "
        "and the platform naturally -- once each. Capture the vibe of the outfit in "
        "specific terms. Keep it casual and real, like something I'd actually caption."
    )

    # PART 4: Guarded call -- higher temperature so captions vary each time.
    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.95,
        )
        # PART 5: Extract and return.
        return response.choices[0].message.content.strip()
    except Exception as e:
        return (
            f"Just thrifted this {item_name} for ${price} on {platform} -- "
            f"obsessed. (Caption generator hit an error: {e})"
        )


if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe

    print("=== Step 1: search ===")
    results = search_listings("vintage graphic tee", max_price=30.0)
    top_item = results[0]
    print(f"Top: {top_item['title']}\n")

    print("=== Step 2: suggest_outfit ===")
    outfit = suggest_outfit(top_item, get_example_wardrobe())
    print(outfit)

    print("\n=== Step 3: create_fit_card ===")
    print(create_fit_card(outfit, top_item))

    print("\n=== Guard test: empty outfit ===")
    print(create_fit_card("", top_item))
