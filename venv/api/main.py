from fastapi import FastAPI, APIRouter,HTTPException,status
from pydantic import BaseModel,EmailStr,Field
from services.users import add_user,del_user
from log.log_generator import create_log

app = FastAPI(title="Users Menagment API")
router = APIRouter(
    prefix="/zsl_app",
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
        operation_code = await add_user(
            name=user.name,
            last_name=user.last_name,
            email=user.email,
            password=user.password
                       )
        if operation_code == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Taki urzytkownik już istnieje"
            )
        elif operation_code == 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hasło nie spełnia wymogów bezpieczeństwa"
            )
        elif operation_code == -1:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="błąd bazy danych podczas tworzena konta"
            )
        return {"status": "success", "message": "Użytkownik został utworzony."}
    except HTTPException:
        raise

    except Exception as e:

        create_log(level="error",message=f"Nie można utworzyć urzytkownika : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Niespodziewany błąd"
        )
    





app.include_router(router=router)        