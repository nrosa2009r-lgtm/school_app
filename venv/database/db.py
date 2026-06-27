import asyncio
from log.log_generator import create_log
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from config.conf import get_data

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
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    last_name: Mapped[str] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)   #rootadmin/admin/teacher/student
    password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False)
    u_class: Mapped[str] = mapped_column(String(10),nullable=True)

async def is_exist(data:str,parm:str) -> bool:
    column = getattr(Users, parm)
    query = select(Users).where(column == data)
    async with async_session.begin() as session:
        result = await session.execute(query)
        user = result.scalars().first()
    return user is not None
# Create db file
async def create_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        create_log(level="info",message="Pomyślnie utworzono bazę danych")
    
    async with async_session.begin() as session:
        if await is_exist("root_admin","role"):
            create_log(level="error",message=f"root_admin już istneje!!!")
        else:
            root = Users(name="root_admin",email="nrpl350@gmail.com",role="root_admin",password="12345678",is_active=True)
            session.add(root)
            create_log(level="info",message="Utworzono root_admina")
        


