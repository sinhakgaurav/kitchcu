"""Media upload tests — live-capture kitchen photos."""

import io
import os

import pytest
from httpx import AsyncClient

from ckac_common.storage import reset_media_storage

os.environ.setdefault("MEDIA_STORAGE_BACKEND", "local")


@pytest.fixture(autouse=True)
def _local_media_storage():
    os.environ["MEDIA_STORAGE_BACKEND"] = "local"
    reset_media_storage()
    yield
    reset_media_storage()


def _jpeg_bytes() -> bytes:
    # Minimal valid JPEG (1x1)
    return (
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xc4\x00\xb5\x10\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01}\x01\x02\x03\x00\x04\x11\x05\x12!1A\x06\x13Qa\x07\"q\x142\x81\x91\xa1\x08#B\xb1\xc1\x15R\xd1\xf0$3br\x82\t\n\x16\x17\x18\x19\x1a%&'()*456789:CDEFGHIJSTUVWXYZcdefghijstuvwxyz\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xfb\xd5\x7f\xff\xd9"
    )


@pytest.mark.asyncio
async def test_media_upload_live_capture(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("capture.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")}
    data = {
        "is_live_capture": "true",
        "context": "ingredient",
        "captured_at": "2026-07-13T10:00:00Z",
    }

    res = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/media/upload",
        headers=headers,
        files=files,
        data=data,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["is_live_capture"] is True
    assert body["content_type"] == "image/jpeg"
    assert body["url"].startswith("file://")
    assert body["captured_at"] == "2026-07-13T10:00:00Z"


@pytest.mark.asyncio
async def test_media_upload_rejects_empty(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, token = kitchen_ctx
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}

    res = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/media/upload",
        headers=headers,
        files=files,
        data={"context": "prep_step"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_media_upload_requires_kitchen_owner(client: AsyncClient, kitchen_ctx):
    _, kitchen_id, _ = kitchen_ctx
    files = {"file": ("capture.jpg", io.BytesIO(_jpeg_bytes()), "image/jpeg")}

    res = await client.post(
        f"/api/v1/kitchens/{kitchen_id}/media/upload",
        files=files,
        data={"context": "dish"},
    )
    assert res.status_code == 401
