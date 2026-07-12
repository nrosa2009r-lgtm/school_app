import httpx
from config.conf import get_data
import http.cookiejar
from typing import List, Optional

class ApiClientActions:
    def __init__(self, base_url: str = None):
        if not base_url:
            base_url = get_data("SERVER_IP") or "http://127.0.0.1:8000"
        self.base_url = base_url
        cookie_jar = http.cookiejar.CookieJar()
        self.client = httpx.AsyncClient(base_url=self.base_url, cookies=cookie_jar, timeout=10.0)

    async def login(self, email: str, password: str) -> dict:
        try:
            response = await self.client.post(
                "/api/login",
                json={"email": email.strip().lower(), "password": password}
            )
            if response.status_code == 200:
                return response.json()
            else:
                try:
                    data = response.json()
                    return {"status": "error", "message": data.get("detail", "Błąd logowania")}
                except Exception:
                    return {"status": "error", "message": f"Błąd serwera: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def register(self, name: str, last_name: str, email: str, password: str) -> dict:
        try:
            response = await self.client.post(
                "/api/register",
                json={"name": name.strip(), "last_name": last_name.strip(), "email": email.strip().lower(), "password": password}
            )
            if response.status_code in [200, 201]:
                return response.json()
            else:
                try:
                    data = response.json()
                    return {"status": "error", "message": data.get("detail", "Błąd rejestracji")}
                except Exception:
                    return {"status": "error", "message": f"Błąd serwera: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def activate(self, email: str, code: str) -> dict:
        try:
            response = await self.client.post(
                "/api/activate",
                json={"email": email.strip().lower(), "code": code.strip()}
            )
            if response.status_code == 200:
                return response.json()
            else:
                try:
                    data = response.json()
                    return {"status": "error", "message": data.get("detail", "Błąd aktywacji")}
                except Exception:
                    return {"status": "error", "message": f"Błąd serwera: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def get_profile(self) -> dict:
        try:
            response = await self.client.get("/api/auth/me")
            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "message": "Brak autoryzacji"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def logout(self) -> dict:
        try:
            response = await self.client.post("/api/logout")
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Błąd wylogowywania"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def get_menu(self) -> dict:
        try:
            response = await self.client.get("/api/menu")
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Nie udało się pobrać menu"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def get_cart(self) -> dict:
        try:
            response = await self.client.get("/api/cart")
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Nie udało się pobrać koszyka"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def add_to_cart(self, item_id: int, quantity: int = 1, option_ids: Optional[List[int]] = None) -> dict:
        try:
            response = await self.client.post(
                "/api/cart/add",
                json={"item_id": item_id, "quantity": quantity, "option_ids": option_ids or []}
            )
            if response.status_code in [200, 201]:
                return response.json()
            else:
                try:
                    data = response.json()
                    return {"status": "error", "message": data.get("detail", "Nie udało się dodać do koszyka")}
                except Exception:
                    return {"status": "error", "message": f"Błąd serwera: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def remove_from_cart(self, item_id: int, quantity: Optional[int] = None, option_ids: Optional[List[int]] = None) -> dict:
        try:
            response = await self.client.post(
                "/api/cart/remove",
                json={"item_id": item_id, "quantity": quantity, "option_ids": option_ids or []}
            )
            if response.status_code == 200:
                return response.json()
            else:
                try:
                    data = response.json()
                    return {"status": "error", "message": data.get("detail", "Nie udało się usunąć z koszyka")}
                except Exception:
                    return {"status": "error", "message": f"Błąd serwera: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def clear_cart(self) -> dict:
        try:
            response = await self.client.post("/api/cart/clear")
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Nie udało się wyczyścić koszyka"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def checkout(self) -> dict:
        try:
            response = await self.client.post("/api/cart/checkout")
            if response.status_code in [200, 201]:
                return response.json()
            else:
                try:
                    data = response.json()
                    return {"status": "error", "message": data.get("detail", "Błąd finalizacji zamówienia")}
                except Exception:
                    return {"status": "error", "message": f"Błąd serwera: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def get_orders(self) -> dict:
        try:
            response = await self.client.get("/api/orders")
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Nie udało się pobrać zamówień"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def cancel_order(self, order_id: int) -> dict:
        try:
            response = await self.client.post(f"/api/orders/{order_id}/cancel")
            if response.status_code == 200:
                return response.json()
            else:
                try:
                    data = response.json()
                    return {"status": "error", "message": data.get("detail", "Nie udało się anulować zamówienia")}
                except Exception:
                    return {"status": "error", "message": f"Błąd serwera: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def admin_get_users(self) -> dict:
        try:
            response = await self.client.get("/api/admin/users")
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Brak dostępu lub błąd serwera"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def admin_update_user_role(self, user_id: int, role: str) -> dict:
        try:
            response = await self.client.post(
                f"/api/admin/users/{user_id}/role",
                json={"role": role}
            )
            if response.status_code == 200:
                return response.json()
            else:
                try:
                    data = response.json()
                    return {"status": "error", "message": data.get("detail", "Błąd zmiany roli")}
                except Exception:
                    return {"status": "error", "message": f"Błąd serwera: {response.status_code}"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def admin_get_logs(self) -> dict:
        try:
            response = await self.client.get("/api/admin/logs")
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "message": "Brak dostępu lub błąd logów"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def admin_add_category(self, name: str) -> dict:
        try:
            response = await self.client.post("/api/menu/category", json={"name": name})
            if response.status_code in [200, 201]:
                return response.json()
            return {"status": "error", "message": "Nie udało się dodać kategorii"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def admin_add_item(self, category_id: int, name: str, price: float, stock: int = 100, descryption: str = "") -> dict:
        try:
            response = await self.client.post(
                "/api/menu/item",
                json={"category_id": category_id, "name": name, "price": price, "stock": stock, "descryption": descryption}
            )
            if response.status_code in [200, 201]:
                return response.json()
            return {"status": "error", "message": "Nie udało się dodać dania"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def admin_add_option(self, menu_item_id: int, option_name: str, add_to_price: float, option_type: str = "Opcja") -> dict:
        try:
            response = await self.client.post(
                "/api/menu/option",
                json={"menu_item_id": menu_item_id, "option_name": option_name, "add_to_price": add_to_price, "option_type": option_type}
            )
            if response.status_code in [200, 201]:
                return response.json()
            return {"status": "error", "message": "Nie udało się dodać opcji"}
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def close(self):
        await self.client.aclose()

api_client = ApiClientActions()
