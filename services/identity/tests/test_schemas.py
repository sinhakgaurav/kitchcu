import uuid

import pytest
from pydantic import ValidationError

from app.schemas import (
    OwnerRegisterRequest,
    create_access_token,
    generate_kitchen_code,
)
from ckac_common.database import SessionLocal


class TestOwnerRegisterRequest:
    def test_normalizes_ten_digit_phone(self):
        req = OwnerRegisterRequest(phone="9876543210", name="Raj")
        assert req.phone == "+919876543210"

    def test_keeps_e164_phone(self):
        req = OwnerRegisterRequest(phone="+919876543210", name="Raj")
        assert req.phone == "+919876543210"

    def test_rejects_short_phone(self):
        with pytest.raises(ValidationError):
            OwnerRegisterRequest(phone="12345", name="Raj")

    def test_rejects_overlong_national_phone(self):
        with pytest.raises(ValidationError):
            OwnerRegisterRequest(phone="987654321011", name="Raj")

    def test_rejects_short_name(self):
        with pytest.raises(ValidationError):
            OwnerRegisterRequest(phone="9876543210", name="R")

    def test_rejects_numeric_name(self):
        with pytest.raises(ValidationError):
            OwnerRegisterRequest(phone="9876543210", name="123456")

    def test_rejects_name_with_digits(self):
        with pytest.raises(ValidationError):
            OwnerRegisterRequest(phone="9876543210", name="Pooja123")

    def test_normalizes_email_lowercase(self):
        req = OwnerRegisterRequest(
            phone="9876543210", name="Raj Kumar", email="POOJA020@GMAIL.COM"
        )
        assert req.email == "pooja020@gmail.com"

    def test_allows_name_with_apostrophe(self):
        req = OwnerRegisterRequest(phone="9876543210", name="O'Brien")
        assert req.name == "O'Brien"


class TestCreateAccessToken:
    def test_returns_bearer_token(self):
        owner_id = uuid.uuid4()
        token = create_access_token(owner_id, "+919876543210")
        assert token.token_type == "bearer"
        assert token.access_token
        assert token.expires_in > 0


@pytest.mark.asyncio
async def test_generate_kitchen_code_pune():
    async with SessionLocal() as session:
        code1 = await generate_kitchen_code(session, "Pune")
        assert code1 == "CKPNQ001"

        from app.models import Kitchen
        from geoalchemy2.elements import WKTElement

        session.add(
            Kitchen(
                owner_id=uuid.uuid4(),
                code=code1,
                name="Dummy",
                location=WKTElement("POINT(73.8 18.5)", srid=4326),
            )
        )
        await session.flush()

        code2 = await generate_kitchen_code(session, "Pune")
        assert code2 == "CKPNQ002"


@pytest.mark.asyncio
async def test_generate_kitchen_code_unknown_city():
    async with SessionLocal() as session:
        code = await generate_kitchen_code(session, "Solapur")
        assert code.startswith("CKSOL")
        assert code.endswith("001")
