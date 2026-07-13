from app.whatsapp import extract_messages


def test_empty_payload():
    assert extract_messages({}) == []
