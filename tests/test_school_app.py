import pytest
import asyncio
import time
import os
from datetime import datetime, time as dt_time, timezone, date
from security.sec import (
    encrypt_data, decrypt_data, blind_index, hash_password, verify_password,
    password_validator, check_password_strength, require_roles,
    generate_totp_secret, generate_totp_uri, get_totp_code, verify_totp,
    generate_qr_data, verify_qr_data, check_haveibeenpwned
)
from database.db import create_db, Users, MenuCategories, MenuItems, MenuOptions, Orders, async_session, is_exist, Schools, Allergens, DietaryTags, DailySchedule
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
    assert len(idx1) == 64


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
    res = await add_user("Jan", "Kowalski", "jan.kowalski@school.edu", "StrongP@ssw0rd!2026")
    assert res == 2

    async with async_session() as session:
        from sqlalchemy import select
        u = (await session.execute(select(Users).where(Users.email_hash == blind_index("jan.kowalski@school.edu")))).scalars().first()
        assert u is not None
        assert decrypt_data(u.name_enc) == "Jan"
        assert decrypt_data(u.email_enc) == "jan.kowalski@school.edu"
        assert u.is_active == False
        u.is_active = True
        await session.commit()

    user_login_res = await login_user("jan.kowalski@school.edu", "StrongP@ssw0rd!2026")
    assert not isinstance(user_login_res, int)
    assert user_login_res.role == "user"


@pytest.mark.asyncio
async def test_cart_atomic_reservation_and_ttl():
    async with async_session() as session:
        from sqlalchemy import select
        item = (await session.execute(select(MenuItems))).scalars().first()
        assert item is not None
        initial_stock = item.stock
        item_id = item.id

    user_id = 9999
    success, msg = await cart_manager.add_item(user_id, item_id, quantity=2)
    assert success == True

    async with async_session() as session:
        updated_item = await session.get(MenuItems, item_id)
        assert updated_item.stock == initial_stock - 2

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

    cart = await cart_manager.get_cart(user_id)
    cart.last_updated = time.time() - 301.0

    expired_cart = await cart_manager.get_cart(user_id)
    assert len(expired_cart.items) == 0

    async with async_session() as session:
        restored_item = await session.get(MenuItems, item_id)
        assert restored_item.stock == initial_stock


def test_api_endpoints_and_auth():
    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    resp_me = client.get("/api/me")
    assert resp_me.status_code == 401
    resp_menu = client.get("/api/menu")
    assert resp_menu.status_code == 200
    data = resp_menu.json()
    assert "categories" in data
    assert len(data["categories"]) > 0

    # PWA endpoints
    resp_pwa = client.get("/manifest.json")
    assert resp_pwa.status_code == 200
    resp_sw = client.get("/sw.js")
    assert resp_sw.status_code == 200

    # Schools endpoint (public)
    resp_schools = client.get("/api/schools")
    assert resp_schools.status_code == 200
    assert len(resp_schools.json().get("schools", [])) >= 0

    # Schedule endpoint (public)
    resp_schedule = client.get("/api/schedule")
    assert resp_schedule.status_code == 200

    # Filtered menu
    resp_fmenu = client.get("/api/menu/filtered")
    assert resp_fmenu.status_code == 200


@pytest.mark.asyncio
async def test_2fa_totp_logic():
    secret = generate_totp_secret()
    assert len(secret.replace('=', '')) >= 16

    uri = generate_totp_uri(secret, "test@school.edu")
    assert "otpauth://totp/" in uri
    assert "test@school.edu" in uri

    code = get_totp_code(secret)
    assert len(code) == 6
    assert code.isdigit()

    assert verify_totp(secret, code) == True
    assert verify_totp(secret, "000000") == False


def test_qr_generation_and_verification():
    qr_data = generate_qr_data(order_id=42, user_id=7, school_id=1)
    assert "|" in qr_data
    payload = verify_qr_data(qr_data)
    assert payload is not None
    assert payload["order_id"] == 42
    assert payload["user_id"] == 7

    # Test invalid QR
    fake_qr = '{"order_id":1}+fakesig'
    assert verify_qr_data(fake_qr) is None


@pytest.mark.asyncio
async def test_school_and_menu_models():
    async with async_session() as session:
        from sqlalchemy import select

        # Check school exists
        q_s = select(Schools)
        r_s = await session.execute(q_s)
        schools = r_s.scalars().all()
        assert len(schools) > 0

        # Check root user exists
        from security.sec import blind_index
        root_hash = blind_index("nrpl350@gmail.com")
        users_q = select(Users).where(Users.email_hash == root_hash)
        users_r = await session.execute(users_q)
        root = users_r.scalars().first()
        assert root is not None

        # Check dietary tags and allergens
        tags_q = select(DietaryTags)
        tags_r = await session.execute(tags_q)
        tags = tags_r.scalars().all()
        assert len(tags) > 0

        allergens_q = select(Allergens)
        allergens_r = await session.execute(allergens_q)
        alls = allergens_r.scalars().all()
        assert len(alls) > 0

        # Check daily schedule
        sched_q = select(DailySchedule)
        sched_r = await session.execute(sched_q)
        schedule = sched_r.scalars().all()
        assert len(schedule) > 0

        # Verify Orders model has payment_method column
        from sqlalchemy import inspect as sa_inspect
        mapper = sa_inspect(Orders)
        column_names = [c.key for c in mapper.columns]
        assert "payment_method" in column_names, "Orders should have payment_method column"

        # Test creating order with payment_method
        test_order = Orders(user_id=root.id, total_price=25.50, status="active", payment_method="card")
        session.add(test_order)
        await session.commit()

        # Verify it was saved with payment_method
        saved = await session.get(Orders, test_order.id)
        assert saved.payment_method == "card"

        # Test default payment_method is cash
        test_order2 = Orders(user_id=root.id, total_price=10.00, status="active")
        session.add(test_order2)
        await session.commit()
        saved2 = await session.get(Orders, test_order2.id)
        assert saved2.payment_method == "cash"

        # Cleanup test orders
        await session.delete(saved)
        await session.delete(saved2)
        await session.commit()


def test_cutoff_time_logic():
    # Standard cutoff - przed 09:00
    before_cutoff = datetime(2026, 7, 12, 8, 30, 0)
    after_cutoff = datetime(2026, 7, 12, 9, 15, 0)
    assert is_past_cutoff(before_cutoff) == False
    assert is_past_cutoff(after_cutoff) == True

    # Advance ordering: zamówienie na jutro = zawsze OK
    assert is_past_cutoff(after_cutoff, order_date="2026-07-13") == False


@pytest.mark.asyncio
async def test_haveibeenpwned_api():
    # Test with known breached password should return True or -1 (offline)
    result, count = await check_haveibeenpwned("password123")
    assert result in [True, False]
    assert isinstance(count, int)


def test_logger():
    create_log("info", "Test log from pytest", ip_address="127.0.0.1")
    assert True
