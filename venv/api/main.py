from slowapi import Limiter
from slowapi.extension import _rate_limit_exceeded_handler 
from slowapi.util import get_remote_address
from config.conf import get_data
from slowapi.errors import RateLimitExceeded
from fastapi import FastAPI, APIRouter, HTTPException, status, Request, Response
from pydantic import BaseModel, EmailStr, Field
from services.users import add_user, del_user, login_user
from database.db import veryfy_and_activate_user, Users  # Dodano import klasyfikacji bazy danych
from log.log_generator import create_log
from datetime import datetime, timezone, timedelta
import jwt

app = FastAPI(title="Users Menagment API")
router = APIRouter(
    prefix="/api",
    tags=["Actions for User"]
)

# limity
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    create_log(level="warning", message=f"Przekroczono limit zapytań dla IP: {request.client.host}")
    return _rate_limit_exceeded_handler(request, exc)


class UserCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    last_name: str = Field(..., min_length=2)
    email: EmailStr
    password: str

class UserActivate(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)


class UserLogin(BaseModel):
    email: EmailStr
    password: str

@app.get("/")
async def test():
    return {"message": "evertyhing work"}


@router.post("/add_user", status_code=status.HTTP_201_CREATED)
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
        create_log(level="error", message=f"Nie można utworzyć urzytkownika : {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Niespodziewany błąd"
        )

@router.post("/activate_user", status_code=status.HTTP_200_OK)
async def activate_usr(data: UserActivate):
    try:
        succes = await veryfy_and_activate_user(email=data.email, code=data.code)

        if not succes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Podany kod jest nieprawidłowy, wygasł lub konto jest już aktywne."
            )
        return {"status": "success", "message": "Konto zostało pomyślnie aktywowane. Możesz się zalogować."}
    except HTTPException:
        raise
    except Exception as e:
        create_log(level="error", message=f"Błąd podczas aktywacji użytkownika {data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Niespodziewany błąd serwera"
        )


@router.post("/login", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def login_usr(data: UserLogin, request: Request, response: Response):
    try:
        resoult = await login_user(email=data.email, password=data.password)

        if resoult == 0 or resoult == 2:
            # NAJPIERW logujemy do pliku tekstowego
            create_log(level="warning", message=f"Użytkownik {data.email} podał nieprawidłowy email lub hasło.")
            # DOPIERO POTEM przerywamy działanie za pomocą raise
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Nieprawidłowy email lub hasło"   
            )

        elif resoult == 1:
            create_log(level="warning", message=f"Użytkownik {data.email} próbował wejść na nieaktywne konto.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Konto nie jest aktywne. Zweryfikuj swój adres e-mail."
            )

        # Usunięcie błędu Pylance (Type Guard)
        # Informujemy edytor kodu, że w tym miejscu resoult to na 100% instancja Users, a nie int
        if isinstance(resoult, int):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Wewnętrzny błąd przetwarzania logowania"
            )

        payload = {
            "sub": str(resoult.id),
            "role": resoult.role,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
        jwt_secret = get_data("JWT_SECRET_KEY")
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,       # Blokuje dostęp skryptom JS (ochrona przed XSS)
            secure=False,        # Ustaw na True na produkcji (wymaga HTTPS)
            samesite="lax",      # Zabezpieczenie przed CSRF przy standardowej nawigacji
            max_age=1800         # Żywotność ciasteczka w sekundach (30 minut)
        )

        return {
            "status": "success", 
            "message": "Zalogowano pomyślnie.",
            "user_role": resoult.role  # Przekazujemy rolę, by Flet wiedział, jakie UI załadować
        }

    except HTTPException:
        raise
    except Exception as e:
        create_log(level="error", message=f"Błąd podczas logowania {data.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Niespodziewany błąd serwera"
        )


app.include_router(router=router)