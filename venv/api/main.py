from slowapi import Limiter
from slowapi.extension import _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from config.conf import get_data
from security.sec import get_current_user, require_roles, decrypt_data, encrypt_data
from fastapi import FastAPI, APIRouter, HTTPException, status, Request, Response, Depends
from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from services.users import add_user, del_user, login_user
from database.db import veryfy_and_activate_user, Users, MenuCategories, MenuItems, MenuOptions, Orders, OrderItems, Logs, async_session
from log.log_generator import create_log
from services.cart import cart_manager, is_past_cutoff
from datetime import datetime, timezone, timedelta
import jwt
from sqlalchemy import select, update

app = FastAPI(title="School Catering API")
router = APIRouter(prefix="/api", tags=["School Catering API"])

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    client_ip = request.client.host if request.client else "Unknown IP"
    create_log(level="warning", message=f"Przekroczono limit zapytań dla IP: {client_ip}")
    return _rate_limit_exceeded_handler(request, exc)

# Pydantic models
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

class UserOut(BaseModel):
    id: int
    name: str
    last_name: str
    email: str
    role: str
    is_active: bool

class CategoryCreate(BaseModel):
    name: str

class MenuItemCreate(BaseModel):
    category_id: int
    name: str
    descryption: Optional[str] = None
    image_url: Optional[str] = None
    price: float
    prep_price: Optional[float] = None
    stock: int = 100

class MenuOptionCreate(BaseModel):
    menu_item_id: int
    option_type: str
    option_name: str
    add_to_price: float

class CartAddRequest(BaseModel):
    item_id: int
    quantity: int = 1
    option_ids: Optional[List[int]] = None

class CartRemoveRequest(BaseModel):
    item_id: int
    quantity: Optional[int] = None
    option_ids: Optional[List[int]] = None

class RoleUpdateRequest(BaseModel):
    role: str

@app.get("/")
async def test():
    return {"message": "everything works"}

@router.post("/add_user", status_code=status.HTTP_201_CREATED)
@router.post("/register", status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def add_usr(user: UserCreate, request: Request):
    try:
        operation_code = await add_user(
            name=user.name,
            last_name=user.last_name,
            email=str(user.email),
            password=user.password
        )
        if operation_code == 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Taki użytkownik już istnieje")
        elif operation_code == 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Hasło nie spełnia wymogów bezpieczeństwa (min 10 znaków, wielka/mała litera, cyfra, znak specjalny)")
        elif operation_code == -1:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Błąd bazy danych podczas tworzenia konta")
        return {"status": "success", "message": "Użytkownik został utworzony. Sprawdź e-mail z kodem aktywacyjnym."}
    except HTTPException:
        raise
    except Exception as e:
        create_log(level="error", message=f"Nie można utworzyć użytkownika: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Niespodziewany błąd serwera")

@router.post("/activate_user", status_code=status.HTTP_200_OK)
@router.post("/activate", status_code=status.HTTP_200_OK)
async def activate_usr(data: UserActivate):
    try:
        success = await veryfy_and_activate_user(email=str(data.email), code=data.code)
        if not success:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Podany kod jest nieprawidłowy, wygasł lub konto jest już aktywne.")
        return {"status": "success", "message": "Konto zostało pomyślnie aktywowane. Możesz się zalogować."}
    except HTTPException:
        raise
    except Exception as e:
        create_log(level="error", message=f"Błąd podczas aktywacji użytkownika {data.email}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Niespodziewany błąd serwera")

@router.post("/login", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def login_usr(data: UserLogin, request: Request, response: Response):
    try:
        result = await login_user(email=str(data.email), password=data.password)
        if result == 0:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nieprawidłowy email lub hasło")
        elif result == 2:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Nieprawidłowy email lub hasło")
        elif result == 1:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Konto nie jest aktywne. Zweryfikuj swój adres e-mail.")
        if isinstance(result, int):
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Wewnętrzny błąd logowania")

        payload = {
            "sub": str(result.id),
            "role": result.role,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30)
        }
        jwt_secret = get_data("JWT_SECRET_KEY")
        if not jwt_secret:
            jwt_secret = "6a47123711ea6ba224051b631961405b014c474d8a82424b978e8d93b740375a"
        token = jwt.encode(payload, jwt_secret, algorithm="HS256")

        response.set_cookie(
            key="access_token",
            value=token,
            httponly=True,
            secure=False,
            samesite="lax",
            max_age=1800
        )

        return {
            "status": "success",
            "message": "Zalogowano pomyślnie.",
            "user_role": result.role
        }
    except HTTPException:
        raise
    except Exception as e:
        create_log(level="error", message=f"Błąd logowania {data.email}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Niespodziewany błąd serwera")

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout_usr(response: Response):
    try:
        response.delete_cookie(key="access_token", httponly=True, secure=False, samesite="lax")
        return {"status": "success", "message": "Wylogowano pomyślnie."}
    except Exception as e:
        create_log(level="error", message=f"Błąd podczas wylogowywania: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Niespodziewany błąd serwera")

@router.get("/me", status_code=status.HTTP_200_OK)
@router.get("/auth/me", status_code=status.HTTP_200_OK)
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    user_obj = current_user["user_obj"]
    return {
        "status": "success",
        "message": "Autoryzacja powiodła się. Jesteś zalogowany!",
        "user_data": {
            "id": current_user["id"],
            "role": current_user["role"],
            "name": current_user["name"],
            "last_name": current_user["last_name"],
            "email": current_user["email"],
            "is_active": user_obj.is_active
        }
    }

# --- MENU ENDPOINTS ---
@router.get("/menu", status_code=status.HTTP_200_OK)
async def get_menu():
    async with async_session() as session:
        query_cats = select(MenuCategories)
        res_cats = await session.execute(query_cats)
        cats = res_cats.scalars().all()

        output = []
        for cat in cats:
            query_items = select(MenuItems).where(MenuItems.category_id == cat.id)
            res_items = await session.execute(query_items)
            items = res_items.scalars().all()

            cat_items = []
            for item in items:
                query_opts = select(MenuOptions).where(MenuOptions.menu_item_id == item.id)
                res_opts = await session.execute(query_opts)
                opts = res_opts.scalars().all()

                cat_items.append({
                    "id": item.id,
                    "sku": item.sku,
                    "name": item.name,
                    "descryption": item.descryption,
                    "image_url": item.image_url,
                    "price": float(item.price),
                    "prep_price": float(item.prep_price) if item.prep_price else None,
                    "is_avelible": item.is_avelible,
                    "stock": item.stock,
                    "options": [
                        {
                            "id": opt.id,
                            "option_type": opt.option_type,
                            "option_name": opt.option_name,
                            "add_to_price": float(opt.add_to_price),
                            "extra_price": float(opt.add_to_price)
                        } for opt in opts
                    ]
                })
            output.append({
                "id": cat.id,
                "name": cat.name,
                "items": cat_items
            })
        return {"status": "success", "categories": output}

@router.post("/menu/category", status_code=status.HTTP_201_CREATED)
async def add_category(data: CategoryCreate, current_user: dict = Depends(require_roles("admin", "rootadmin"))):
    async with async_session.begin() as session:
        cat = MenuCategories(name=data.name)
        session.add(cat)
    create_log(level="info", message=f"Administrator ID {current_user['id']} dodał kategorię menu: {data.name}")
    return {"status": "success", "message": "Dodano kategorię."}

@router.post("/menu/item", status_code=status.HTTP_201_CREATED)
async def add_menu_item(data: MenuItemCreate, current_user: dict = Depends(require_roles("admin", "rootadmin"))):
    async with async_session.begin() as session:
        item = MenuItems(
            category_id=data.category_id,
            name=data.name,
            descryption=data.descryption,
            image_url=data.image_url,
            price=data.price,
            prep_price=data.prep_price,
            is_avelible=True,
            stock=data.stock
        )
        session.add(item)
    create_log(level="info", message=f"Administrator ID {current_user['id']} dodał danie: {data.name}")
    return {"status": "success", "message": "Dodano danie."}

@router.post("/menu/option", status_code=status.HTTP_201_CREATED)
async def add_menu_option(data: MenuOptionCreate, current_user: dict = Depends(require_roles("admin", "rootadmin"))):
    async with async_session.begin() as session:
        opt = MenuOptions(
            menu_item_id=data.menu_item_id,
            option_type=data.option_type,
            option_name=data.option_name,
            add_to_price=data.add_to_price
        )
        session.add(opt)
    create_log(level="info", message=f"Administrator ID {current_user['id']} dodał opcję menu: {data.option_name}")
    return {"status": "success", "message": "Dodano opcję menu."}

# --- CART ENDPOINTS ---
@router.get("/cart", status_code=status.HTTP_200_OK)
async def get_cart(current_user: dict = Depends(get_current_user)):
    user_id = int(current_user["id"])
    cart = await cart_manager.get_cart(user_id)
    return {"status": "success", "cart": cart.to_dict()}

@router.post("/cart/add", status_code=status.HTTP_200_OK)
async def add_to_cart(data: CartAddRequest, current_user: dict = Depends(get_current_user)):
    if is_past_cutoff():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Minęła godzina graniczna (09:00 rano). System blokuje składanie nowych zamówień na dziś.")
    user_id = int(current_user["id"])
    success, msg = await cart_manager.add_item(user_id, data.item_id, data.quantity, data.option_ids)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    cart = await cart_manager.get_cart(user_id)
    return {"status": "success", "message": msg, "cart": cart.to_dict()}

@router.post("/cart/remove", status_code=status.HTTP_200_OK)
async def remove_from_cart(data: CartRemoveRequest, current_user: dict = Depends(get_current_user)):
    if is_past_cutoff():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Minęła godzina graniczna (09:00 rano). System blokuje zmiany w zamówieniach na dziś.")
    user_id = int(current_user["id"])
    success, msg = await cart_manager.remove_item(user_id, data.item_id, data.quantity, data.option_ids)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    cart = await cart_manager.get_cart(user_id)
    return {"status": "success", "message": msg, "cart": cart.to_dict()}

@router.post("/cart/clear", status_code=status.HTTP_200_OK)
@router.post("/cart/cancel", status_code=status.HTTP_200_OK)
async def clear_cart(current_user: dict = Depends(get_current_user)):
    if is_past_cutoff():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Minęła godzina graniczna (09:00 rano). System blokuje anulowanie/czyszczenie zamówienia na dziś.")
    user_id = int(current_user["id"])
    await cart_manager.clear_cart(user_id, reason="user_cleared")
    return {"status": "success", "message": "Koszyk wyczyszczony. Porcje powróciły do puli."}

@router.post("/cart/checkout", status_code=status.HTTP_201_CREATED)
@router.post("/orders", status_code=status.HTTP_201_CREATED)
async def checkout_order(current_user: dict = Depends(get_current_user)):
    if is_past_cutoff():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Minęła godzina graniczna (09:00 rano). System blokuje składanie nowych zamówień na dziś.")
    user_id = int(current_user["id"])
    cart = await cart_manager.checkout_and_empty(user_id)
    if not cart or not cart.items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Koszyk jest pusty lub wygasł.")

    total_price = cart.total_price()
    async with async_session.begin() as session:
        new_order = Orders(user_id=user_id, total_price=total_price, status="active")
        session.add(new_order)
        await session.flush()

        for citem in cart.items:
            o_item = OrderItems(
                order_id=new_order.id,
                menu_item_id=citem.item_id,
                quantity=citem.quantity,
                price=citem.price + citem.option_price,
                option_names=", ".join(citem.option_names) if citem.option_names else ""
            )
            session.add(o_item)
        await session.commit()

    create_log(level="info", message=f"Użytkownik ID {user_id} sfinalizował zamówienie ID {new_order.id} na kwotę {total_price:.2f} zł.")
    return {"status": "success", "message": "Zamówienie sfinalizowane pomyślnie.", "order_id": new_order.id}

# --- ORDERS ENDPOINTS ---
@router.get("/orders", status_code=status.HTTP_200_OK)
async def get_orders(current_user: dict = Depends(get_current_user)):
    user_id = int(current_user["id"])
    role = current_user["role"].lower().replace("_", "")

    async with async_session() as session:
        if role in ["admin", "rootadmin"]:
            query = select(Orders).order_by(Orders.created_at.desc())
        else:
            query = select(Orders).where(Orders.user_id == user_id).order_by(Orders.created_at.desc())
        res = await session.execute(query)
        orders = res.scalars().all()

        output = []
        for o in orders:
            query_items = select(OrderItems).where(OrderItems.order_id == o.id)
            res_items = await session.execute(query_items)
            o_items = res_items.scalars().all()

            output.append({
                "id": o.id,
                "user_id": o.user_id,
                "total_price": float(o.total_price),
                "status": o.status,
                "created_at": o.created_at.isoformat() if o.created_at else "",
                "items": [
                    {
                        "menu_item_id": i.menu_item_id,
                        "quantity": i.quantity,
                        "price": float(i.price),
                        "option_names": i.option_names
                    } for i in o_items
                ]
            })
        return {"status": "success", "orders": output}

@router.post("/orders/{order_id}/cancel", status_code=status.HTTP_200_OK)
async def cancel_order(order_id: int, current_user: dict = Depends(get_current_user)):
    if is_past_cutoff():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Minęła godzina graniczna (09:00 rano). System blokuje anulowanie istniejących zamówień na dziś.")
    user_id = int(current_user["id"])
    role = current_user["role"].lower().replace("_", "")

    async with async_session.begin() as session:
        order = await session.get(Orders, order_id)
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Zamówienie nie istnieje.")
        if order.status == "cancelled":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Zamówienie jest już anulowane.")
        if role not in ["admin", "rootadmin"] and order.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Brak uprawnień do anulowania tego zamówienia.")

        order.status = "cancelled"

        # Zwrot porcji do magazynu (stock + N)
        query_items = select(OrderItems).where(OrderItems.order_id == order_id)
        res_items = await session.execute(query_items)
        o_items = res_items.scalars().all()
        for item in o_items:
            query_upd = (
                update(MenuItems)
                .where(MenuItems.id == item.menu_item_id)
                .values(stock=MenuItems.stock + item.quantity)
            )
            await session.execute(query_upd)
        await session.commit()

    create_log(level="info", message=f"Zamówienie ID {order_id} zostało anulowane przez użytkownika ID {user_id}. Porcje powróciły na stan.")
    return {"status": "success", "message": "Zamówienie zostało anulowane."}

# --- ADMIN ENDPOINTS ---
@router.get("/admin/users", status_code=status.HTTP_200_OK)
async def admin_get_users(current_user: dict = Depends(require_roles("admin", "rootadmin"))):
    async with async_session() as session:
        query = select(Users)
        res = await session.execute(query)
        users = res.scalars().all()

        output = []
        for u in users:
            output.append(UserOut(
                id=u.id,
                name=decrypt_data(u.name_enc),
                last_name=decrypt_data(u.last_name_enc) if u.last_name_enc else "",
                email=decrypt_data(u.email_enc),
                role=u.role,
                is_active=u.is_active
            ).model_dump())
        return {"status": "success", "users": output}

@router.post("/admin/users/{user_id}/role", status_code=status.HTTP_200_OK)
async def admin_update_role(user_id: int, data: RoleUpdateRequest, current_user: dict = Depends(require_roles("admin", "rootadmin"))):
    allowed_roles = ["rootadmin", "admin", "teacher", "student", "user"]
    new_role = data.role.lower().replace("_", "")
    if new_role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Dozwolone role: {', '.join(allowed_roles)}")

    async with async_session.begin() as session:
        user = await session.get(Users, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Użytkownik nie istnieje.")
        user.role = new_role
        await session.commit()

    create_log(level="info", message=f"Administrator ID {current_user['id']} zmienił rolę użytkownika ID {user_id} na {new_role}")
    return {"status": "success", "message": f"Rola użytkownika zaktualizowana na: {new_role}"}

@router.get("/admin/logs", status_code=status.HTTP_200_OK)
async def admin_get_logs(current_user: dict = Depends(require_roles("admin", "rootadmin"))):
    async with async_session() as session:
        query = select(Logs).order_by(Logs.id.desc()).limit(100)
        res = await session.execute(query)
        logs = res.scalars().all()

        output = [
            {
                "id": l.id,
                "level": l.level,
                "message": l.message,
                "ip_address": l.ip_address,
                "created_at": l.created_at.isoformat() if l.created_at else ""
            } for l in logs
        ]
        return {"status": "success", "logs": output}

app.include_router(router=router)
