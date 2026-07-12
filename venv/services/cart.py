import asyncio
import time
from datetime import datetime, time as dt_time, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy import update, select
from database.db import async_session, MenuItems, MenuOptions
from log.log_generator import create_log

CUTOFF_HOUR = 9
CUTOFF_MINUTE = 0

def is_past_cutoff(now: Optional[datetime] = None) -> bool:
    if now is None:
        now = datetime.now()
    return now.time() >= dt_time(CUTOFF_HOUR, CUTOFF_MINUTE)

class CartItem:
    def __init__(self, item_id: int, quantity: int, name: str, price: float, option_ids: List[int] = None, option_names: List[str] = None, option_price: float = 0.0):
        self.item_id = item_id
        self.quantity = quantity
        self.name = name
        self.price = price
        self.option_ids = option_ids or []
        self.option_names = option_names or []
        self.option_price = option_price

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "quantity": self.quantity,
            "name": self.name,
            "price": self.price,
            "option_ids": self.option_ids,
            "option_names": self.option_names,
            "option_price": self.option_price,
            "item_total": (self.price + self.option_price) * self.quantity
        }

class Cart:
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.items: List[CartItem] = []
        self.last_updated: float = time.time()
        self.ttl: float = 300.0  # 5 minut TTL

    def is_expired(self) -> bool:
        return (time.time() - self.last_updated) > self.ttl

    def total_price(self) -> float:
        return sum((item.price + item.option_price) * item.quantity for item in self.items)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "items": [item.to_dict() for item in self.items],
            "total_price": self.total_price(),
            "expires_in_seconds": max(0, int(self.ttl - (time.time() - self.last_updated)))
        }

class CartManager:
    def __init__(self):
        self._carts: Dict[int, Cart] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

    def start_cleanup_loop(self):
        if self._cleanup_task is None or self._cleanup_task.done():
            try:
                loop = asyncio.get_running_loop()
                self._cleanup_task = loop.create_task(self._background_cleanup())
            except RuntimeError:
                pass

    async def _background_cleanup(self):
        while True:
            try:
                await asyncio.sleep(30)
                await self.check_expired_carts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                create_log(level="error", message=f"Błąd w pętli czyszczenia koszyków: {str(e)}")

    async def check_expired_carts(self):
        async with self._lock:
            expired_user_ids = [uid for uid, cart in self._carts.items() if cart.is_expired()]
        for uid in expired_user_ids:
            await self.clear_cart(uid, reason="expired")

    async def get_cart(self, user_id: int) -> Cart:
        async with self._lock:
            cart = self._carts.get(user_id)
        if cart and cart.is_expired():
            await self.clear_cart(user_id, reason="expired")
            async with self._lock:
                cart = self._carts.get(user_id)
        if not cart:
            async with self._lock:
                cart = self._carts.setdefault(user_id, Cart(user_id))
        return cart

    async def add_item(self, user_id: int, item_id: int, quantity: int = 1, option_ids: List[int] = None) -> Tuple[bool, str]:
        if quantity <= 0:
            return False, "Ilość musi być większa od 0."

        # Atomowa rezerwacja porcji ze stanu magazynowego (stock = stock - N WHERE stock >= N)
        async with async_session() as session:
            query = (
                update(MenuItems)
                .where(MenuItems.id == item_id, MenuItems.stock >= quantity)
                .values(stock=MenuItems.stock - quantity)
            )
            result = await session.execute(query)
            if result.rowcount == 0:
                await session.rollback()
                return False, "Brak wystarczającej liczby porcji w magazynie (lub danie nie istnieje)."

            item = await session.get(MenuItems, item_id)
            if not item or not item.is_avelible:
                await session.rollback()
                return False, "Danie jest niedostępne."

            option_names = []
            option_price = 0.0
            if option_ids:
                for oid in option_ids:
                    opt = await session.get(MenuOptions, oid)
                    if opt and opt.menu_item_id == item_id:
                        option_names.append(opt.option_name)
                        option_price += float(opt.add_to_price)

            await session.commit()

        async with self._lock:
            if user_id not in self._carts or self._carts[user_id].is_expired():
                self._carts[user_id] = Cart(user_id)
            cart = self._carts[user_id]
            cart.last_updated = time.time()

            found = False
            for citem in cart.items:
                if citem.item_id == item_id and sorted(citem.option_ids) == sorted(option_ids or []):
                    citem.quantity += quantity
                    found = True
                    break
            if not found:
                cart.items.append(CartItem(
                    item_id=item_id,
                    quantity=quantity,
                    name=item.name,
                    price=float(item.price),
                    option_ids=option_ids or [],
                    option_names=option_names,
                    option_price=option_price
                ))

        create_log(level="info", message=f"Zarezerwowano {quantity}x danie ID {item_id} w koszyku użytkownika ID {user_id}.")
        return True, "Dodano do koszyka i zarezerwowano porcje."

    async def remove_item(self, user_id: int, item_id: int, quantity: Optional[int] = None, option_ids: List[int] = None) -> Tuple[bool, str]:
        async with self._lock:
            cart = self._carts.get(user_id)
            if not cart:
                return False, "Koszyk jest pusty."

            target_item = None
            target_idx = -1
            for idx, citem in enumerate(cart.items):
                if citem.item_id == item_id and (option_ids is None or sorted(citem.option_ids) == sorted(option_ids)):
                    target_item = citem
                    target_idx = idx
                    break

            if not target_item:
                return False, "Danie nie znajduje się w koszyku."

            remove_qty = quantity if quantity is not None and quantity > 0 else target_item.quantity
            if remove_qty > target_item.quantity:
                remove_qty = target_item.quantity

            target_item.quantity -= remove_qty
            if target_item.quantity <= 0:
                cart.items.pop(target_idx)
            cart.last_updated = time.time()

        # Zwolnienie rezerwacji w bazie
        async with async_session() as session:
            query = (
                update(MenuItems)
                .where(MenuItems.id == item_id)
                .values(stock=MenuItems.stock + remove_qty)
            )
            await session.execute(query)
            await session.commit()

        create_log(level="info", message=f"Zwolniono rezerwację {remove_qty}x danie ID {item_id} dla użytkownika ID {user_id}.")
        return True, "Usunięto z koszyka."

    async def clear_cart(self, user_id: int, reason: str = "cancelled") -> bool:
        async with self._lock:
            cart = self._carts.pop(user_id, None)
        if not cart or not cart.items:
            return True

        async with async_session() as session:
            for citem in cart.items:
                query = (
                    update(MenuItems)
                    .where(MenuItems.id == citem.item_id)
                    .values(stock=MenuItems.stock + citem.quantity)
                )
                await session.execute(query)
            await session.commit()

        create_log(level="info", message=f"Wyczyszczono koszyk użytkownika ID {user_id} ({reason}). Zwolniono wszystkie rezerwacje.")
        return True

    async def checkout_and_empty(self, user_id: int) -> Optional[Cart]:
        async with self._lock:
            cart = self._carts.pop(user_id, None)
        return cart

cart_manager = CartManager()
