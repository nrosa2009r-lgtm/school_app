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
    total_price: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["Users"] = relationship()
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

    # Step 2: Check and seed sample menu if empty
    async with async_session() as session:
        query_cat = select(MenuCategories)
        res_cat = await session.execute(query_cat)
        if not res_cat.scalars().first():
            c1 = MenuCategories(name="Dania główne")
            c2 = MenuCategories(name="Zupy")
            c3 = MenuCategories(name="Napoje")
            session.add_all([c1, c2, c3])
            await session.commit()

            async with async_session() as session2:
                q_c = select(MenuCategories)
                r_c = await session2.execute(q_c)
                all_cats = {c.name: c.id for c in r_c.scalars().all()}

                i1 = MenuItems(category_id=all_cats["Dania główne"], sku=1001, name="Kotlet schabowy z ziemniakami", descryption="Tradycyjny polski obiad z zestawem surówek", price=18.50, prep_price=12.00, is_avelible=True, stock=50)
                i2 = MenuItems(category_id=all_cats["Dania główne"], sku=1002, name="Spaghetti Bolognese", descryption="Makaron z sosem pomidorowo-mięsnym", price=16.00, prep_price=10.00, is_avelible=True, stock=40)
                i3 = MenuItems(category_id=all_cats["Zupy"], sku=1003, name="Rosół z makaronem", descryption="Długo gotowany bulion z domowym makaronem", price=8.50, prep_price=5.00, is_avelible=True, stock=60)
                i4 = MenuItems(category_id=all_cats["Napoje"], sku=1004, name="Kompot owocowy 0.3l", descryption="Słodki napój z owoców sadu", price=3.50, prep_price=1.50, is_avelible=True, stock=100)
                session2.add_all([i1, i2, i3, i4])
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
                create_log(level="info", message="Zainicjalizowano przykładowe menu.")

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
