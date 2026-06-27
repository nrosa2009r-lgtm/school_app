import asyncio
from log.log_generator import create_log
from sqlalchemy import ForeignKey, String, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
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
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    name: Mapped[str] = mapped_column( nullable=False)
    last_name: Mapped[str] = mapped_column( nullable=True)
    email: Mapped[str] = mapped_column( nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)   #rootadmin/admin/teacher/student
    password: Mapped[str] = mapped_column(String(256), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=False)
    u_class: Mapped[str] = mapped_column(nullable=True)

# Chcking is user exist
async def is_exist(data:str,parm:str) -> bool:
    column = getattr(Users, parm)

    query = select(Users)  
    
    async with async_session.begin() as session:
        result = await session.execute(query)
        users = result.scalars().all()
    
    # 2. Deszyfrujesz i sprawdzasz dopasowanie w Pythonie
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
        


