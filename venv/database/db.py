import asyncio
from typing import List, Optional
from datetime import datetime,timezone
from log.log_generator import create_log
from sqlalchemy import ForeignKey, String, select,delete,update,DateTime,Numeric,DECIMAL
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column,relationship
from config.conf import get_data
from security.sec import decrypt_data, hash_password,encrypt_data

# Create engine and session
db_url = get_data("DATABASE_URL")
engine = create_async_engine(db_url, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

# Create Database Structure
class Users(Base):
    __tablename__ = "users"
    # Users parameters
    id: Mapped[int] = mapped_column(primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column( nullable=False)
    last_name: Mapped[str] = mapped_column( nullable=True)
    email: Mapped[str] = mapped_column( nullable=False, unique=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)   #rootadmin/admin/teacher/student
    password: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active: Mapped[bool] = mapped_column(default=False)
    u_class: Mapped[str] = mapped_column(nullable=True)

    activation_code: Mapped[Optional[str]] = mapped_column(nullable=True)
    code_expires_at: Mapped[Optional[str]] = mapped_column(DateTime,nullable=True)

class MenuCategories(Base):
    __tablename__ = "menu_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)

    items: Mapped[List["MenuItems"]] = relationship(back_populates="category")

class MenuItems(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("menu_categories.id"),nullable=False)
    sku:Mapped[int] = mapped_column(nullable=False,unique=True,autoincrement=True)
    name:Mapped[str] = mapped_column(nullable=False,unique=True)
    descryption:Mapped[Optional[str]] = mapped_column(String(500))
    image_url: Mapped[Optional[str]] = mapped_column(String(256))
    price:Mapped[DECIMAL] = mapped_column(Numeric(10,2),nullable=False)
    prep_price:Mapped[DECIMAL] = mapped_column(Numeric(10,2),nullable=True)
    is_avelible:Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    category: Mapped["MenuCategories"] = relationship(back_populates="items")
    options:Mapped[List["MenuOptions"]] = relationship(back_populates="menu_item",cascade="all,delete-orphan")
class MenuOptions(Base):
    __tablename__ = "menu_options"

    id:Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    menu_item_id:Mapped[int] = mapped_column(ForeignKey("menu_items.id"))
    option_type:Mapped[str] = mapped_column(nullable=False)
    option_name:Mapped[str] = mapped_column(unique=True,nullable=False)
    add_to_price:Mapped[float] = mapped_column(nullable=False)

    menu_item: Mapped["MenuItems"] = relationship(back_populates="options")


# Chcking is user exist
async def is_exist(data:str,parm:str) -> bool:

    query = select(Users)  
    
    async with async_session.begin() as session:
        result = await session.execute(query)
        users = result.scalars().all()
    
    #Serching in db
    for user in users:
        encrypted_value = getattr(user, parm)
        try:
            if decrypt_data(encrypted_value) == data:
                return True
        except Exception:
            continue 
            
    return False

        


# Create db file
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        create_log(level="info",message="Pomyślnie utworzono bazę danych")



    # Creating root admin
    async with async_session.begin() as session:
        if await is_exist("root_admin","name"):
            create_log(level="error",message=f"root_admin już istneje!!!")
        else:
            root = Users(name=encrypt_data("root_admin"),
                         email=encrypt_data("nrpl350@gmail.com"),
                         role="root_admin",
                         password=hash_password("12345678"),
                         is_active=True)
            session.add(root)
            create_log(level="info",message="Utworzono root_admina")
        
# Return password of user based on unique mail
async def get_user_data_for_del(email: str) -> tuple[int | None, str | None]:
    query = select(Users.id, Users.email, Users.password)
    
    async with async_session() as session:
        result = await session.execute(query)
        rows = result.all()  # [(id, encrypted_email, password), ...]
        
    for db_id, db_email, db_password in rows:
        try:
            if decrypt_data(db_email) == email:
                return db_id, db_password  # Zwracamy ID oraz Hasło
        except Exception:
            continue
            
    return None, None


# Delete user in db
async def dell_in_db(user_id :int):
    query = delete(Users).where(Users.id == user_id)

    async with async_session() as session:
        await session.execute(query)
        await session.commit()


async def veryfy_and_activate_user(email:str,code:str) ->bool:
    query = select(Users).where(Users.is_active ==False)

    async with async_session() as session:
        result = await session.execute(query)
        inactivate_users = result.scalars().all()

        target_user = None

        for user in inactivate_users:
            try:
                if decrypt_data(user.email) == email:
                    target_user = user
                    break
            except Exception:
                continue
        
        if not target_user:
            create_log(level="warning", message=f"Próba aktywacji konta, które nie istnieje lub jest już aktywne: {email}")
            return False

        
        # Odszyfrowujemy kod z bazy danych i porównujemy z surowym kodem od użytkownika
        try:
             decrypted_code = decrypt_data(target_user.activation_code)
        except Exception:
            create_log(level="error", message=f"Nie udało się odszyfrować kodu dla: {email}")
            return False

        if decrypted_code != code:
            create_log(level="warning", message=f"Podano niepoprawny kod aktywacyjny dla: {email}")
            return False

        

        now = datetime.now(timezone.utc)

        expires_at = target_user.code_expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if now > expires_at:
            create_log(level="warning", message=f"Kod aktywacyjny dla {email} wygasł.")
            return False

        target_user.is_active = True
        target_user.activation_code = None 
        target_user.code_expires_at = None

        await session.commit()
        create_log(level="info", message=f"Konto użytkownika {email} zostało pomyślnie aktywowane.")
        return True
    
async def get_login_data(email:str) -> Optional[Users]:
    query = select(Users)

    async with async_session() as session:
        result await session.execute(query)
        users = result.scalars().all()

        
    for user in users:
        try:
            if decrypt_data(user.email) == email:
                return user
        except Exception:
            continue

    return None
        