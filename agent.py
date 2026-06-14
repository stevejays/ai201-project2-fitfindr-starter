"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.
"""

import json

from tools import search_listings, suggest_outfit, create_fit_card


# -- session state ------------------------------------------------------------

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.
    The session dict is the single source of truth for everything that happens
    during a run.
    """
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# -- query parsing (LLM) ------------------------------------------------------

def _parse_query(query: str) -> dict:
    """
    Use the LLM to extract search parameters from a natural-language query.
    Returns {"description": str, "size": str|None, "max_price": float|None}.
    On any failure, falls back to the raw query as the description so the
    agent can still attempt a search (graceful degradation).
    """
    from tools import _get_groq_client

    system_msg = (
        "You extract structured search parameters from a shopping request. "
        "Respond with ONLY a JSON object, no markdown, no explanation."
    )
    user_msg = (
        f'Extract search parameters from this request:\n"{query}"\n\n'
        "Return a JSON object with exactly these keys:\n"
        '- "description": a short phrase of what they want (string)\n'
        '- "size": the size if mentioned, else null (string or null)\n'
        '- "max_price": the price ceiling as a number if mentioned, else null\n\n'
        'Example: {"description": "vintage graphic tee", "size": "M", "max_price": 30.0}'
    )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0,
        )
        raw = response.choices[0].message.content.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        parsed = json.loads(raw)
        return {
            "description": parsed.get("description") or query,
            "size": parsed.get("size"),
            "max_price": (
                float(parsed["max_price"])
                if parsed.get("max_price") is not None
                else None
            ),
        }
    except Exception:
        return {"description": query, "size": None, "max_price": None}


# -- planning loop ------------------------------------------------------------

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.
    Check session["error"] first -- if not None, the run ended early.
    """
    # Step 1: initialize the session.
    session = _new_session(query, wardrobe)

    # Step 2: parse the query into search parameters.
    session["parsed"] = _parse_query(query)

    # Step 3: search. This is the planning branch.
    session["search_results"] = search_listings(
        description=session["parsed"]["description"],
        size=session["parsed"]["size"],
        max_price=session["parsed"]["max_price"],
    )
    if not session["search_results"]:
        mp = session["parsed"]["max_price"]
        session["error"] = (
            f"No listings found for '{session['parsed']['description']}'"
            + (f" under ${mp}" if mp else "")
            + ". Try broadening your search or raising your budget."
        )
        return session

    # Step 4: select the top result. State flows forward.
    session["selected_item"] = session["search_results"][0]

    # Step 5: suggest an outfit (item + wardrobe flow in).
    session["outfit_suggestion"] = suggest_outfit(
        session["selected_item"], session["wardrobe"]
    )

    # Step 6: create the fit card (outfit + item flow in).
    session["fit_card"] = create_fit_card(
        session["outfit_suggestion"], session["selected_item"]
    )

    # Step 7: done.
    return session


# -- CLI test -----------------------------------------------------------------

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")