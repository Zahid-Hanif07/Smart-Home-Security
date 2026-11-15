import os
from uuid import uuid4

os.environ.setdefault('TEST_ISOLATED_MODE', '1')

from fastapi.testclient import TestClient

from app.api.main import app
from app.config.backend_settings import settings
from app.repositories.home_repository import home_repository
from app.repositories.room_repository import room_repository
from app.services.backend_store import backend_store
from app.models.home import HomeCreate
import jwt


client = TestClient(app)


def token(user_id):
    return jwt.encode({'sub': str(user_id), 'exp': 4102444800}, settings.SUPABASE_JWT_SECRET, algorithm='HS256')


def test_owner_gets_only_rooms_for_owned_home():
    backend_store.clear()
    owner = uuid4()
    other = uuid4()
    home = home_repository.create_home(owner, HomeCreate(name='A', address=None))
    other_home = home_repository.create_home(other, HomeCreate(name='B', address=None))
    room_repository.seed_in_memory_room(uuid4(), home['id'], 'Living Room')
    room_repository.seed_in_memory_room(uuid4(), other_home['id'], 'Secret Room')

    response = client.get(f"/api/homes/{home['id']}/rooms", headers={'Authorization': f'Bearer {token(owner)}'})
    assert response.status_code == 200
    assert [item['name'] for item in response.json()['rooms']] == ['Living Room']
    assert client.get(f"/api/homes/{other_home['id']}/rooms", headers={'Authorization': f'Bearer {token(owner)}'}).status_code == 403
    assert client.get(f"/api/homes/{home['id']}/rooms").status_code == 401
    backend_store.clear()
