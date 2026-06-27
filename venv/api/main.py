from fastapi import FastAPI, APIRouter,HTTPException,status
from pydantic import BaseModel,EmailStr,Field
from services.users import add_user,del_user
from log.log_generator import create_log

app = FastAPI(title="Users Menagment API")
router = APIRouter(
    prefix="/home",
    tags=["User/Users"]
)

class UserCreate(BaseModel):
    name: str = Field(...,min_length=3, max_length=50)
    last_name: str = Field(...,min_length=2)
    email:EmailStr
    password:str

@app.get("/")
async def test():
    return {"message":"evertyhing work"}


@router.post("/add_user",status_code=status.HTTP_201_CREATED)
async def add_usr(user: UserCreate):
    try:
        await add_user(name=user.name,
                       last_name=user.last_name,
                       email=user.email,
                       password=user.password
                       )
        return {"message":"Urzytkownik został pomyślnie stworzony"}
    except Exception as e:

        create_log(level="error",message=f"Nie można utworzyć urzytkownika : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Błąd podczas tworzenia konta, emalil jest zajęty."
        )
    





app.include_router(router=router)        