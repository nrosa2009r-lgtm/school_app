import asyncio
from typing import List, Optional
from datetime import datetime, timezone
import time
from log.log_generator import create_log
from sqlalchemy import ForeignKey, String, select, delete, update, DateTime, Numeric, DECIMAL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from config.conf import get_data

db_url = get_data("DATABASE_URL")
if not db_url:
    db_url = "sqlite+aiosqlite:///venv/database/database.db"

engine = create_async_engine(db_url, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Users(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False, autoincrement=True)
    name_enc: Mapped[str] = mapped_column(String(512), nullable=False)
    last_name_enc: Mapped[str] = mapped_column(String(512), nullable=True)
    
    email_enc: Mapped[str] = mapped_column(String(512), nullable=False)
    email_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    password: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active: Mapped[bool] = mapped_column(default=False)
    u_class: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    activation_code_enc: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    code_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    @property
    def name(self) -> str:
        return self.name_enc

    @name.setter
    def name(self, value: str):
        self.name_enc = value

    @property
    def last_name(self) -> Optional[str]:
        return self.last_name_enc

    @last_name.setter
    def last_name(self, value: Optional[str]):
        self.last_name_enc = value

    @property
    def email(self) -> str:
        return self.email_enc

    @email.setter
    def email(self, value: str):
        self.email_enc = value

    @property
    def activation_code(self) -> Optional[str]:
        return self.activation_code_enc

    @activation_code.setter
    def activation_code(self, value: Optional[str]):
        self.activation_code_enc = value

class MenuCategories(Base):
    __tablename__ = "menu_categories"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)

    items: Mapped[List["MenuItems"]] = relationship(back_populates="category", cascade="all,delete-orphan")

MenuCategory = MenuCategories

class MenuItems(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("menu_categories.id"), nullable=False)
    sku: Mapped[int] = mapped_column(nullable=False, unique=True, default=lambda: int(time.time() * 1000) % 1000000000)
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    descryption: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    price: Mapped[DECIMAL] = mapped_column(Numeric(10, 2), nullable=False)
    prep_price: Mapped[Optional[DECIMAL]] = mapped_column(Numeric(10, 2), nullable=True)
    is_avelible: Mapped[bool] = mapped_column(default=True)
    stock: Mapped[int] = mapped_column(default=100, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    category: Mapped["MenuCategories"] = relationship(back_populates="items")
    options: Mapped[List["MenuOptions"]] = relationship(back_populates="menu_item", cascade="all,delete-orphan")

MenuItem = MenuItems

class MenuOptions(Base):
    __tablename__ = "menu_options"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    option_type: Mapped[str] = mapped_column(nullable=False)
    option_name: Mapped[str] = mapped_column(unique=True, nullable=False)
    add_to_price: Mapped[float] = mapped_column(nullable=False)

    menu_item: Mapped["MenuItems"] = relationship(back_populates="options")

    @property
    def extra_price(self) -> float:
        return self.add_to_price

    @extra_price.setter
    def extra_price(self, value: float):
        self.add_to_price = value

MenuOption = MenuOptions

class Logs(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    level: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)
    ip_address: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

class Orders(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    school_id: Mapped[Optional[int]] = mapped_column(ForeignKey("schools.id"), nullable=True)
    total_price: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    payment_method: Mapped[str] = mapped_column(String(20), default="cash")
    qr_code: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    qr_verified: Mapped[bool] = mapped_column(default=False)
    order_date: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["Users"] = relationship()
    school: Mapped[Optional["Schools"]] = relationship(back_populates="orders")
    items: Mapped[List["OrderItems"]] = relationship(back_populates="order", cascade="all,delete-orphan")

Order = Orders

class OrderItems(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False)
    price: Mapped[float] = mapped_column(nullable=False)
    option_names: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    order: Mapped["Orders"] = relationship(back_populates="items")
    menu_item: Mapped["MenuItems"] = relationship()

OrderItem = OrderItems


# ===== ENTERPRISE MODELS =====

class Schools(Base):
    """Multi-Tenant: każda szkoła ma własne menu, godziny odcięcia i użytkowników."""
    __tablename__ = "schools"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    subdomain: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cutoff_hour: Mapped[int] = mapped_column(default=9)
    cutoff_minute: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    allow_advance_ordering: Mapped[bool] = mapped_column(default=True)
    max_advance_days: Mapped[int] = mapped_column(default=5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    orders: Mapped[List["Orders"]] = relationship(back_populates="school")


class UserSchoolLink(Base):
    """Powiązanie użytkownika ze szkołą (multi-tenant)."""
    __tablename__ = "user_school_links"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)


class Allergens(Base):
    """Alergeny przypisane do dań w menu."""
    __tablename__ = "allergens"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    allergen_name: Mapped[str] = mapped_column(String(100), nullable=False)  # np. "gluten", "orzechy", "laktoza"


class DietaryTags(Base):
    """Tagi dietetyczne dla dań (wegetariańskie, wegańskie, bezglutenowe itp.)."""
    __tablename__ = "dietary_tags"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    tag_name: Mapped[str] = mapped_column(String(100), nullable=False)  # np. "wegetariańskie", "wegańskie", "bez glutenu"


class TOTPSecrets(Base):
    """Przechowuje sekrety TOTP dla administratorów (2FA)."""
    __tablename__ = "totp_secrets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    secret_enc: Mapped[str] = mapped_column(String(512), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class SetupWizardState(Base):
    """Śledzi postęp kreatora pierwszego uruchomienia."""
    __tablename__ = "setup_wizard_state"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    step: Mapped[int] = mapped_column(default=0)  # 0=nie rozpoczęto, 1-5=kolejne kroki, 99=ukończono
    school_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    admin_email: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cutoff_hour: Mapped[int] = mapped_column(default=9)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)



class DailySchedule(Base):
    """Kalendarz posiłków - przyporządkowuje dania do konkretnych dni."""
    __tablename__ = "daily_schedule"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.id"), nullable=False)
    school_id: Mapped[int] = mapped_column(ForeignKey("schools.id"), nullable=False)
    serving_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    available_from: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    available_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    max_orders: Mapped[int] = mapped_column(default=100)



async def is_exist(data: str, parm: str) -> bool:
    async with async_session() as session:
        if parm == "email":
            from security.sec import blind_index
            target_hash = blind_index(data)
            query = select(Users).where(Users.email_hash == target_hash)
            result = await session.execute(query)
            return result.scalars().first() is not None
        elif parm == "name":
            from security.sec import decrypt_data
            query = select(Users)
            result = await session.execute(query)
            users = result.scalars().all()
            for user in users:
                try:
                    if decrypt_data(user.name_enc) == data:
                        return True
                except Exception:
                    continue
    return False

async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        create_log(level="info", message="Pomyślnie utworzono bazę danych")

    # Step 1: Check and create root admin
    async with async_session() as session:
        if await is_exist("nrpl350@gmail.com", "email") or await is_exist("root_admin", "name"):
            create_log(level="info", message="root_admin już istnieje!")
        else:
            from security.sec import encrypt_data, blind_index, hash_password
            root = Users(
                name_enc=encrypt_data("root_admin"),
                last_name_enc=encrypt_data("admin"),
                email_enc=encrypt_data("nrpl350@gmail.com"),
                email_hash=blind_index("nrpl350@gmail.com"),
                role="rootadmin",
                password=hash_password("12345678"),
                is_active=True
            )
            session.add(root)
            await session.commit()
            create_log(level="info", message="Utworzono root_admina")

    # Step 1.5: Check and seed default school
    async with async_session() as session:
        query_school = select(Schools)
        res_school = await session.execute(query_school)
        if not res_school.scalars().first():
            default_school = Schools(
                name="Szkoła Podstawowa nr 1",
                subdomain="sp1",
                address="ul. Szkolna 1, 00-001 Warszawa",
                cutoff_hour=9,
                cutoff_minute=0
            )
            session.add(default_school)
            await session.commit()
            create_log(level="info", message="Utworzono domyślną szkołę.")

    # Step 2: Check and seed sample menu if empty
    async with async_session() as session:
        query_cat = select(MenuCategories)
        res_cat = await session.execute(query_cat)
        if not res_cat.scalars().first():
            c1 = MenuCategories(name="Dania główne")
            c2 = MenuCategories(name="Zupy")
            c3 = MenuCategories(name="Napoje")
            c4 = MenuCategories(name="Desery")
            session.add_all([c1, c2, c3, c4])
            await session.commit()

            async with async_session() as session2:
                q_c = select(MenuCategories)
                r_c = await session2.execute(q_c)
                all_cats = {c.name: c.id for c in r_c.scalars().all()}

                i1 = MenuItems(category_id=all_cats["Dania główne"], sku=1001, name="Kotlet schabowy z ziemniakami", descryption="Tradycyjny polski obiad z zestawem surówek", price=18.50, prep_price=12.00, is_avelible=True, stock=50)
                i2 = MenuItems(category_id=all_cats["Dania główne"], sku=1002, name="Spaghetti Bolognese", descryption="Makaron z sosem pomidorowo-mięsnym", price=16.00, prep_price=10.00, is_avelible=True, stock=40)
                i3 = MenuItems(category_id=all_cats["Zupy"], sku=1003, name="Rosół z makaronem", descryption="Długo gotowany bulion z domowym makaronem", price=8.50, prep_price=5.00, is_avelible=True, stock=60)
                i4 = MenuItems(category_id=all_cats["Napoje"], sku=1004, name="Kompot owocowy 0.3l", descryption="Słodki napój z owoców sadu", price=3.50, prep_price=1.50, is_avelible=True, stock=100)
                i5 = MenuItems(category_id=all_cats["Dania główne"], sku=1005, name="Sałatka grecka z fetą", descryption="Lekka sałatka z oliwkami, pomidorem i serem feta", price=14.00, prep_price=7.00, is_avelible=True, stock=30)
                i6 = MenuItems(category_id=all_cats["Desery"], sku=1006, name="Brownie czekoladowe", descryption="Wilgotne ciasto czekoladowe z orzechami", price=7.50, prep_price=3.50, is_avelible=True, stock=25)
                session2.add_all([i1, i2, i3, i4, i5, i6])
                await session2.commit()

            async with async_session() as session3:
                q_i = select(MenuItems)
                r_i = await session3.execute(q_i)
                all_items = {i.name: i.id for i in r_i.scalars().all()}

                o1 = MenuOptions(menu_item_id=all_items["Spaghetti Bolognese"], option_type="Gluten", option_name="Bez glutenu (makaron kukurydziany)", add_to_price=3.50)
                o2 = MenuOptions(menu_item_id=all_items["Kotlet schabowy z ziemniakami"], option_type="Mięso", option_name="Podwójna porcja mięsa", add_to_price=6.00)
                o3 = MenuOptions(menu_item_id=all_items["Kompot owocowy 0.3l"], option_type="Cukier", option_name="Bez dodatku cukru", add_to_price=0.00)
                session3.add_all([o1, o2, o3])
                await session3.commit()

            async with async_session() as session4:
                a1 = Allergens(menu_item_id=all_items["Kotlet schabowy z ziemniakami"], allergen_name="gluten")
                a2 = Allergens(menu_item_id=all_items["Spaghetti Bolognese"], allergen_name="gluten")
                a3 = Allergens(menu_item_id=all_items["Spaghetti Bolognese"], allergen_name="laktoza")
                a4 = Allergens(menu_item_id=all_items["Brownie czekoladowe"], allergen_name="orzechy")
                a5 = Allergens(menu_item_id=all_items["Brownie czekoladowe"], allergen_name="gluten")
                a6 = Allergens(menu_item_id=all_items["Brownie czekoladowe"], allergen_name="laktoza")
                a7 = Allergens(menu_item_id=all_items["Sałatka grecka z fetą"], allergen_name="laktoza")
                session4.add_all([a1, a2, a3, a4, a5, a6, a7])
                await session4.commit()

            async with async_session() as session5:
                d1 = DietaryTags(menu_item_id=all_items["Sałatka grecka z fetą"], tag_name="wegetariańskie")
                d2 = DietaryTags(menu_item_id=all_items["Kompot owocowy 0.3l"], tag_name="wegańskie")
                d3 = DietaryTags(menu_item_id=all_items["Kompot owocowy 0.3l"], tag_name="bez glutenu")
                d4 = DietaryTags(menu_item_id=all_items["Brownie czekoladowe"], tag_name="wegetariańskie")
                session5.add_all([d1, d2, d3, d4])
                await session5.commit()

            create_log(level="info", message="Zainicjalizowano przykładowe menu z alergenami i tagami dietetycznymi.")

            # Step 2.5: Seed daily schedule for the current week
            from datetime import date, timedelta
            today = date.today()
            monday = today - timedelta(days=today.weekday())
            async with async_session() as session6:
                q_school = select(Schools)
                r_school = await session6.execute(q_school)
                school = r_school.scalars().first()
                if school:
                    for day_offset in range(5):  # Pon-Pt
                        serving_date = (monday + timedelta(days=day_offset)).isoformat()
                        # Przypisz różne dania główne do różnych dni
                        if day_offset == 0:
                            items_for_day = ["Kotlet schabowy z ziemniakami", "Rosół z makaronem"]
                        elif day_offset == 1:
                            items_for_day = ["Spaghetti Bolognese", "Brownie czekoladowe"]
                        elif day_offset == 2:
                            items_for_day = ["Sałatka grecka z fetą", "Kompot owocowy 0.3l"]
                        elif day_offset == 3:
                            items_for_day = ["Kotlet schabowy z ziemniakami", "Spaghetti Bolognese"]
                        else:
                            items_for_day = ["Sałatka grecka z fetą", "Rosół z makaronem", "Brownie czekoladowe"]

                        for iname in items_for_day:
                            if iname in all_items:
                                session6.add(DailySchedule(
                                    menu_item_id=all_items[iname],
                                    school_id=school.id,
                                    serving_date=serving_date
                                ))
                    await session6.commit()
                    create_log(level="info", message="Utworzono harmonogram posiłków na bieżący tydzień.")

async def get_user_data_for_del(email: str) -> tuple[int | None, str | None]:
    from security.sec import blind_index
    target_hash = blind_index(email)
    query = select(Users.id, Users.password).where(Users.email_hash == target_hash)
    async with async_session() as session:
        result = await session.execute(query)
        row = result.first()
        if row:
            return row[0], row[1]
    return None, None

async def dell_in_db(user_id: int):
    query = delete(Users).where(Users.id == user_id)
    async with async_session() as session:
        await session.execute(query)
        await session.commit()

async def veryfy_and_activate_user(email: str, code: str) -> bool:
    from security.sec import blind_index, decrypt_data
    target_hash = blind_index(email)
    query = select(Users).where(Users.email_hash == target_hash, Users.is_active == False)
    async with async_session() as session:
        result = await session.execute(query)
        target_user = result.scalars().first()
        if not target_user:
            create_log(level="warning", message=f"Próba aktywacji konta, które nie istnieje lub jest już aktywne: {email}")
            return False
        try:
            decrypted_code = decrypt_data(target_user.activation_code_enc)
        except Exception:
            create_log(level="error", message=f"Nie udało się odszyfrować kodu dla: {email}")
            return False
        if decrypted_code != code:
            create_log(level="warning", message=f"Podano niepoprawny kod aktywacyjny dla: {email}")
            return False
        now = datetime.now(timezone.utc)
        expires_at = target_user.code_expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at and now > expires_at:
            create_log(level="warning", message=f"Kod aktywacyjny dla {email} wygasł.")
            return False
        target_user.is_active = True
        target_user.activation_code_enc = None
        target_user.code_expires_at = None
        await session.commit()
        create_log(level="info", message=f"Konto użytkownika {email} zostało pomyślnie aktywowane.")
        return True

async def get_login_data(email: str) -> Optional[Users]:
    from security.sec import blind_index
    target_hash = blind_index(email)
    query = select(Users).where(Users.email_hash == target_hash)
    async with async_session() as session:
        result = await session.execute(query)
        return result.scalars().first()
