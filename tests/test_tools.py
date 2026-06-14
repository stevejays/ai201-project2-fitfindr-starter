from tools import search_listings, suggest_outfit, create_fit_card


# --- search_listings ---

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

def test_search_blank_description():
    assert search_listings("", size=None, max_price=50) == []


# --- create_fit_card (failure mode: empty outfit string, no API call) ---

def test_fit_card_empty_outfit():
    item = {"title": "Test Tee", "price": 20.0, "platform": "depop"}
    result = create_fit_card("", item)
    assert isinstance(result, str)
    assert len(result) > 0
    assert "missing" in result.lower()

def test_fit_card_whitespace_outfit():
    item = {"title": "Test Tee", "price": 20.0, "platform": "depop"}
    result = create_fit_card("   ", item)
    assert "missing" in result.lower()