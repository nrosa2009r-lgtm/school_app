import pytest
import asyncio
import time
import os
from datetime import datetime, time as dt_time, timezone
from security.sec import (
    encrypt_data, decrypt_data, blind_index, hash_password, verify_password,
    password_validator, check_password_strength, require_roles
)
from database.db import create_db, Users, MenuCategories, MenuItems, MenuOptions, Orders, async_session, is_exist
from services.users import add_user, login_user, del_user
from services.cart import cart_manager, CartItem, is_past_cutoff, CUTOFF_HOUR
from log.log_generator import create_log
from fastapi.testclient import TestClient
from api.main import app

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    db_path = "venv/database/database.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    asyncio.run(create_db())

def test_encryption_and_blind_index():
    raw_email = "Student.Test@School.Edu"
    encrypted = encrypt_data(raw_email)
    assert encrypted != raw_email
    assert decrypt_data(encrypted) == raw_email

    idx1 = blind_index(raw_email)
    idx2 = blind_index("student.test@school.edu")
    assert idx1 == idx2
    assert len(idx1) == 64  # SHA-256 hex output

@pytest.mark.asyncio
async def test_password_validator_and_strength():
    assert await password_validator("short") == False
    assert await password_validator("alllowercase123!") == False
    assert await password_validator("NoSpecialChar123456") == False
    assert await password_validator("StrongP@ssw0rd!2026") == True

    valid, color, score = check_password_strength("StrongP@ssw0rd!2026")
    assert valid == True
    assert color == "green"
    assert score == 100

@pytest.mark.asyncio
async def test_user_domain_and_rbac():
    # Test creating user and activating
    res = await add_user("Jan", "Kowalski", "jan.kowalski@school.edu", "StrongP@ssw0rd!2026")
    assert res == 2

    # Check database persistence and encryption
    async with async_session() as session:
        from sqlalchemy import select
        u = (await session.execute(select(Users).where(Users.email_hash == blind_index("jan.kowalski@school.edu")))).scalars().first()
        assert u is not None
        assert decrypt_data(u.name_enc) == "Jan"
        assert decrypt_data(u.email_enc) == "jan.kowalski@school.edu"
        assert u.is_active == False
        
        # Activate manually for test
        u.is_active = True
        await session.commit()

    # Test login
    user_login_res = await login_user("jan.kowalski@school.edu", "StrongP@ssw0rd!2026")
    assert not isinstance(user_login_res, int)
    assert user_login_res.role == "user"

@pytest.mark.asyncio
async def test_cart_atomic_reservation_and_ttl():
    # Find a menu item to test cart reservation
    async with async_session() as session:
        from sqlalchemy import select
        item = (await session.execute(select(MenuItems))).scalars().first()
        assert item is not None
        initial_stock = item.stock
        item_id = item.id

    user_id = 9999
    success, msg = await cart_manager.add_item(user_id, item_id, quantity=2)
    assert success == True

    # Verify atomic stock reservation in DB
    async with async_session() as session:
        updated_item = await session.get(MenuItems, item_id)
        assert updated_item.stock == initial_stock - 2

    # Test removing from cart restores stock
    success_rem, msg_rem = await cart_manager.remove_item(user_id, item_id, quantity=2)
    assert success_rem == True

    async with async_session() as session:
        restored_item = await session.get(MenuItems, item_id)
        assert restored_item.stock == initial_stock

@pytest.mark.asyncio
async def test_cart_ttl_expiration():
    async with async_session() as session:
        from sqlalchemy import select
        item = (await session.execute(select(MenuItems))).scalars().first()
        item_id = item.id
        initial_stock = item.stock

    user_id = 8888
    await cart_manager.add_item(user_id, item_id, quantity=1)
    
    # Simulate cart expiration
    cart = await cart_manager.get_cart(user_id)
    cart.last_updated = time.time() - 301.0  # 5 minut 1 sekunda temu

    # Next get_cart or check should trigger cleanup and restore stock
    expired_cart = await cart_manager.get_cart(user_id)
    assert len(expired_cart.items) == 0

    async with async_session() as session:
        restored_item = await session.get(MenuItems, item_id)
        assert restored_item.stock == initial_stock

def test_api_endpoints_and_auth():
    client = TestClient(app)
    
    # Check root
    resp = client.get("/")
    assert resp.status_code == 200

    # Check protected route without token
    resp_me = client.get("/api/me")
    assert resp_me.status_code == 401

    # Check menu open route
    resp_menu = client.get("/api/menu")
    assert resp_menu.status_code == 200
    data = resp_menu.json()
    assert "categories" in data
    assert len(data["categories"]) > 0

def test_cutoff_time_logic():
    # Test cutoff logic helper
    before_cutoff = datetime(2026, 7, 12, 8, 30, 0)
    after_cutoff = datetime(2026, 7, 12, 9, 15, 0)
    assert is_past_cutoff(before_cutoff) == False
    assert is_past_cutoff(after_cutoff) == True

def test_logger():
    create_log("info", "Test log from pytest", ip_address="127.0.0.1")
    assert True
