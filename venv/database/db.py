import asyncio
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from config.get_variable import db_url

# Inicjalizacja asynchronicznego silnika i fabryki sesji
engine = create_async_engine(db_url, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    password: Mapped[str] = mapped_column(String(256), nullable=False)

# Funkcja tworząca tabele w bazie danych
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
