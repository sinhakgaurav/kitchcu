from app.parser import match_dishes, parse_message_text


def test_parse_quantity_and_dish():
    result = parse_message_text("2 paneer tikka\n1 butter naan")
    assert len(result.lines) == 2
    assert result.lines[0].quantity == 2
    assert result.lines[0].dish_name == "paneer tikka"
    assert result.lines[1].quantity == 1


def test_parse_x_notation():
    result = parse_message_text("paneer tikka x 3")
    assert result.lines[0].quantity == 3
    assert result.lines[0].dish_name == "paneer tikka"


def test_special_notes_extracted():
    result = parse_message_text("2 biryani\nno onion please")
    assert len(result.lines) == 1
    assert "no onion please" in result.special_notes


def test_match_dishes_fuzzy():
    parsed = parse_message_text("2 paneer tikka")
    menu = [{"id": "abc", "name": "Paneer Tikka", "price": 199, "prep_time_min": 25}]
    matched = match_dishes(parsed, menu)
    assert matched.matched_items[0].matched is True
    assert matched.matched_items[0].dish_id == "abc"


def test_unmatched_line_flagged():
    parsed = parse_message_text("2 mystery dish")
    menu = [{"id": "abc", "name": "Paneer Tikka", "price": 199, "prep_time_min": 25}]
    matched = match_dishes(parsed, menu)
    assert matched.matched_items == []
    assert "2 mystery dish" in matched.unmatched_lines
