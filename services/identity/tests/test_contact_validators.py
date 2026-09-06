"""Shared contact-field validators (`ckac_common.validators`).

These rules are enforced identically by identity, order, and notification, so a
number rejected at owner registration cannot slip in via an order or a ticket.
Covers the tracker items BUG_01–BUG_04 and ID-06/07/11–14.
"""

import pytest

from ckac_common.validators import (
    normalize_display_name,
    normalize_email,
    normalize_india_phone,
    normalize_optional_email,
    normalize_optional_india_phone,
    normalize_optional_person_name,
    normalize_person_name,
)


# ------------------------------------------------------------------------ phone


@pytest.mark.parametrize(
    "raw",
    [
        "9876543210",  # bare national
        "+919876543210",  # E.164
        "919876543210",  # dial code, no plus
        "0091 9876543210",  # IDD prefix
        "09876543210",  # domestic trunk prefix
        "98765 43210",  # spaced
        "+91-98765-43210",  # hyphenated
        "(+91) 9876543210",  # bracketed
    ],
)
def test_accepts_every_shape_of_the_same_number(raw: str):
    """The country code is inferred, so all of these are one number."""
    assert normalize_india_phone(raw) == "+919876543210"


@pytest.mark.parametrize(
    "raw",
    [
        "987654321011",  # 12 digits, not a 91 prefix — BUG_01 / BUG_02
        "98765432101",  # 11 digits, no trunk 0
        "987654321",  # 9 digits
        "+14155552671",  # foreign country code
        "+442071838750",  # foreign country code
        "1234567890",  # starts with 1
        "5876543210",  # starts with 5
        "0000000000",
        "abcdefghij",
        "",
        "   ",
    ],
)
def test_rejects_wrong_length_and_non_india_numbers(raw: str):
    with pytest.raises(ValueError):
        normalize_india_phone(raw)


@pytest.mark.parametrize("leading", ["6", "7", "8", "9"])
def test_all_valid_india_mobile_prefixes_accepted(leading: str):
    assert normalize_india_phone(f"{leading}123456789") == f"+91{leading}123456789"


@pytest.mark.parametrize("leading", ["0", "1", "2", "3", "4", "5"])
def test_non_mobile_leading_digits_rejected(leading: str):
    with pytest.raises(ValueError):
        normalize_india_phone(f"{leading}123456789")


def test_optional_phone_passes_blank_through():
    assert normalize_optional_india_phone(None) is None
    assert normalize_optional_india_phone("") is None
    assert normalize_optional_india_phone("   ") is None
    assert normalize_optional_india_phone("9876543210") == "+919876543210"


def test_optional_phone_still_rejects_a_bad_value():
    with pytest.raises(ValueError):
        normalize_optional_india_phone("987654321011")


# ------------------------------------------------------------------------- name


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Priya Sharma", "Priya Sharma"),
        ("  Priya Sharma  ", "Priya Sharma"),
        ("O'Brien", "O'Brien"),
        ("Jean-Luc", "Jean-Luc"),
        ("Dr. Rao", "Dr. Rao"),
    ],
)
def test_accepts_real_names(raw: str, expected: str):
    assert normalize_person_name(raw) == expected


@pytest.mark.parametrize(
    "name",
    [
        "प्रिया शर्मा",  # Hindi / Marathi
        "কৃষ্ণা দাস",  # Bengali
        "பிரியா",  # Tamil
        "ప్రియ",  # Telugu
        "ਪ੍ਰਿਯਾ",  # Punjabi
        "પ્રિયા",  # Gujarati
        "ಪ್ರಿಯಾ",  # Kannada
        "പ്രിയ",  # Malayalam
    ],
)
def test_accepts_indic_names_with_combining_marks(name: str):
    """Indic vowels are combining marks — rejecting them locks out most of India."""
    assert normalize_person_name(name) == name


@pytest.mark.parametrize(
    "raw",
    [
        "12345",  # BUG_04 / ID-06 / ID-11 — numeric name
        "Priya1",  # digits mixed in
        "Priya@Sharma",  # symbol
        "<script>x</script>",
        "P",  # too short
        "",
        "   ",
        "A" * 121,  # over the length cap
    ],
)
def test_rejects_numeric_and_malformed_names(raw: str):
    with pytest.raises(ValueError):
        normalize_person_name(raw)


def test_optional_name_passes_blank_through():
    assert normalize_optional_person_name(None) is None
    assert normalize_optional_person_name("  ") is None
    assert normalize_optional_person_name("Priya") == "Priya"


# ----------------------------------------------------------------- display name


def test_display_name_keeps_identity_assigned_placeholders():
    """OTP signups get a `Customer 0481` label that rides along on every order.

    Rejecting digits here once broke customer checkout outright, so this stays
    pinned: display labels are looser than names a person types.
    """
    assert normalize_display_name("Customer 0481") == "Customer 0481"
    assert normalize_display_name("Table 12 pickup") == "Table 12 pickup"


def test_display_name_trims_and_drops_empties():
    assert normalize_display_name("  Priya  ") == "Priya"
    assert normalize_display_name("   ") is None
    assert normalize_display_name(None) is None


def test_display_name_strips_control_characters():
    assert normalize_display_name("Priya\x00\x07") == "Priya"


def test_display_name_rejects_overlong_input():
    with pytest.raises(ValueError):
        normalize_display_name("x" * 121)


# ------------------------------------------------------------------------ email


def test_email_is_lowercased():
    """BUG_03 — an uppercase address must not round-trip as typed."""
    assert normalize_email("Priya@KitchCU.DEV") == "priya@kitchcu.dev"
    assert normalize_email("  Priya@KitchCU.dev  ") == "priya@kitchcu.dev"


@pytest.mark.parametrize(
    "raw",
    [
        "not-an-email",
        "a@b",  # no dot-separated TLD — browsers accept this, we do not
        "@example.com",
        "priya@",
        "priya @example.com",
        "",
        f"{'a' * 250}@example.com",
    ],
)
def test_rejects_malformed_emails(raw: str):
    with pytest.raises(ValueError):
        normalize_email(raw)


def test_optional_email_passes_blank_through():
    assert normalize_optional_email(None) is None
    assert normalize_optional_email("") is None
    assert normalize_optional_email("Priya@Example.com") == "priya@example.com"


# -------------------------------------------------------------- wired to APIs
#
# `app.schemas` re-exports these helpers, so the endpoints below prove the
# service really uses the shared module rather than a private copy that has
# drifted from it.


@pytest.mark.parametrize(
    "raw",
    ["9876543210", "+919876543210", "919876543210", "0091 9876543210", "09876543210"],
)
@pytest.mark.asyncio
async def test_owner_register_normalizes_every_phone_shape(client, raw: str):
    response = await client.post(
        "/api/v1/owners/register", json={"phone": raw, "name": "Priya Sharma"}
    )
    assert response.status_code == 201
    assert response.json()["phone"] == "+919876543210"


@pytest.mark.parametrize("raw", ["987654321011", "98765432101", "+14155552671", "0123456789"])
@pytest.mark.asyncio
async def test_owner_register_rejects_undeliverable_phone(client, raw: str):
    response = await client.post(
        "/api/v1/owners/register", json={"phone": raw, "name": "Priya Sharma"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_owner_register_rejects_numeric_name(client, unique_phone: str):
    """Registration is a human typing their own name — strict person-name rules."""
    response = await client.post(
        "/api/v1/owners/register", json={"phone": unique_phone, "name": "Priya 42"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_owner_register_lowercases_email(client, unique_phone: str):
    response = await client.post(
        "/api/v1/owners/register",
        json={"phone": unique_phone, "name": "Priya Sharma", "email": "Priya@KitchCU.DEV"},
    )
    assert response.status_code == 201
    assert response.json()["email"] == "priya@kitchcu.dev"


@pytest.mark.asyncio
async def test_referral_lead_lowercases_contact_email(client):
    phone = "9111119001"
    await client.post("/api/v1/auth/customer/whatsapp/request", json={"phone": phone})
    token = (
        await client.post(
            "/api/v1/auth/customer/whatsapp/verify",
            json={"phone": phone, "otp": "123456"},
        )
    ).json()["access_token"]

    created = await client.post(
        "/api/v1/customers/me/referrals/kitchens",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "kitchen_name": "Spice Home",
            "contact_name": "Owner",
            "contact_phone": "09111119002",
            "contact_email": "Owner@KitchCU.DEV",
            "city": "Pune",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["contact_email"] == "owner@kitchcu.dev"
    assert created.json()["contact_phone"] == "+919111119002"
