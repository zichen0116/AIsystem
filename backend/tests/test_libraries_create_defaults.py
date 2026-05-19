import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from app.api.libraries import create_library
from app.schemas.library import KnowledgeLibraryCreate


@pytest.mark.asyncio
async def test_admin_create_library_defaults_to_system():
    db = AsyncMock()
    db.add = Mock()
    current_user = SimpleNamespace(id=1, is_admin=True)
    data = KnowledgeLibraryCreate(
        name="System Library",
        description="Admin-created library",
        tags=["tag-a"],
    )

    response = await create_library(data=data, current_user=current_user, db=db)

    assert response["is_system"] is True
    assert response["is_public"] is False
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_non_admin_create_library_stays_personal_even_if_payload_requests_system():
    db = AsyncMock()
    db.add = Mock()
    current_user = SimpleNamespace(id=2, is_admin=False)
    data = KnowledgeLibraryCreate(
        name="Personal Library",
        description="Teacher-created library",
        tags=["tag-b"],
        is_system=True,
        is_public=True,
    )

    response = await create_library(data=data, current_user=current_user, db=db)

    assert response["is_system"] is False
    assert response["is_public"] is False
    db.add.assert_called_once()
