# pyright: reportUnusedCoroutine=false
import flet as ft
import asyncio
import math
from ui.http_actions import api_client
from security.sec import check_password_strength

class ThemeManager:
    def __init__(self, page: ft.Page):
        self.page = page
        self.is_dark = False
        self.icon = ft.Icon(ft.Icons.LIGHT_MODE, size=24, rotate=ft.Rotate(0, ft.alignment.center), animate_rotation=ft.Animation(500, ft.AnimationCurve.EASE_OUT))
        self.button = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE,
            on_click=self.toggle_theme,
            tooltip="Przełącz motyw"
        )

    async def toggle_theme(self, e):
        self.is_dark = not self.is_dark
        if self.is_dark:
            self.page.theme_mode = ft.ThemeMode.DARK
            self.icon.icon = ft.Icons.DARK_MODE
            self.icon.rotate.angle += 2 * math.pi
        else:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            self.icon.icon = ft.Icons.LIGHT_MODE
            self.icon.rotate.angle += 2 * math.pi
        
        # Animacja z mikropauzą (progress bar lub subtelny efekt)
        self.page.update()
        await asyncio.sleep(0.05)
        self.page.update()

async def trigger_shake(control: ft.Control, page: ft.Page):
    control.offset = ft.Offset(-0.05, 0)
    page.update()
    await asyncio.sleep(0.06)
    control.offset = ft.Offset(0.05, 0)
    page.update()
    await asyncio.sleep(0.06)
    control.offset = ft.Offset(0, 0)
    page.update()

async def trigger_pulse(button: ft.Control, page: ft.Page):
    if hasattr(button, "scale"):
        button.scale = ft.Scale(0.92, alignment=ft.alignment.center)
        page.update()
        await asyncio.sleep(0.1)
        button.scale = ft.Scale(1.0, alignment=ft.alignment.center)
        page.update()

def create_shimmer_skeleton() -> ft.Column:
    return ft.Column([
        ft.Container(height=60, bgcolor=ft.Colors.GREY_300, border_radius=8, animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT), opacity=0.6),
        ft.Container(height=60, bgcolor=ft.Colors.GREY_300, border_radius=8, animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT), opacity=0.4),
        ft.Container(height=60, bgcolor=ft.Colors.GREY_300, border_radius=8, animate_opacity=ft.Animation(400, ft.AnimationCurve.EASE_IN_OUT), opacity=0.3),
    ], spacing=10)

async def main(page: ft.Page):
    page.title = "School Catering Application"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 480
    page.window.height = 760
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    theme_manager = ThemeManager(page)

    # Stan aplikacji
    app_state = {
        "role": "",
        "user_id": None,
        "email": "",
        "name": "",
        "cart_count": 0
    }

    # Główny kontener na widoki
    content_area = ft.Container(expand=True, padding=15)

    def create_nav_bar() -> ft.Row:
        nav_buttons = []
        if app_state["role"]:
            nav_buttons = [
                ft.TextButton("Menu", icon=ft.Icons.RESTAURANT_MENU, on_click=lambda e: page.go("/menu")),
                ft.TextButton(f"Koszyk ({app_state['cart_count']})", icon=ft.Icons.SHOPPING_CART, on_click=lambda e: page.go("/cart")),
                ft.TextButton("Zamówienia", icon=ft.Icons.RECEIPT_LONG, on_click=lambda e: page.go("/orders")),
            ]
            if app_state["role"] in ["admin", "rootadmin"]:
                nav_buttons.append(ft.TextButton("Admin", icon=ft.Icons.ADMIN_PANEL_SETTINGS, on_click=lambda e: page.go("/admin")))
            nav_buttons.append(ft.IconButton(icon=ft.Icons.LOGOUT, tooltip="Wyloguj", on_click=handle_logout))
        else:
            nav_buttons = [
                ft.TextButton("Logowanie", icon=ft.Icons.LOGIN, on_click=lambda e: page.go("/login")),
                ft.TextButton("Rejestracja", icon=ft.Icons.PERSON_ADD, on_click=lambda e: page.go("/register"))
            ]
        
        return ft.Row(
            controls=[
                ft.Text("🍽️ School Catering", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(controls=nav_buttons + [theme_manager.button], alignment=ft.MainAxisAlignment.END, expand=True)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )

    async def handle_logout(e):
        await api_client.logout()
        app_state["role"] = ""
        app_state["user_id"] = None
        page.go("/login")

    async def check_auth_guard(target_route: str) -> bool:
        if not app_state["role"] and target_route in ["/menu", "/cart", "/orders", "/admin"]:
            profile = await api_client.get_profile()
            if profile.get("status") == "success":
                user_data = profile.get("user_data", {})
                app_state["role"] = user_data.get("role", "user")
                app_state["user_id"] = user_data.get("id")
                app_state["email"] = user_data.get("email")
                app_state["name"] = user_data.get("name")
                # Pobierz stan koszyka
                cart_res = await api_client.get_cart()
                if cart_res.get("status") == "success":
                    items = cart_res.get("cart", {}).get("items", [])
                    app_state["cart_count"] = sum(i.get("quantity", 1) for i in items)
                return True
            else:
                page.go("/login")
                return False
        return True

    # --- WIDOK LOGOWANIA (/login) ---
    def build_login_view() -> ft.Column:
        email_field = ft.TextField(
            label="E-mail", width=320, prefix_icon=ft.Icons.EMAIL,
            offset=ft.Offset(0, 0), animate_offset=ft.Animation(100, ft.AnimationCurve.EASE_IN_OUT)
        )
        password_field = ft.TextField(
            label="Hasło", width=320, password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK,
            offset=ft.Offset(0, 0), animate_offset=ft.Animation(100, ft.AnimationCurve.EASE_IN_OUT)
        )
        error_message = ft.Text(value="", color=ft.Colors.RED_400, size=14)
        login_button = ft.ElevatedButton(
            content=ft.Text("Zaloguj się"), width=200, disabled=True,
            scale=ft.Scale(1.0, alignment=ft.alignment.center), animate_scale=ft.Animation(150, ft.AnimationCurve.BOUNCE_OUT)
        )

        async def validate_login_fields(e):
            login_button.disabled = not (email_field.value.strip() and password_field.value.strip())
            page.update()

        email_field.on_change = validate_login_fields
        password_field.on_change = validate_login_fields

        async def handle_login_submit(e):
            await trigger_pulse(login_button, page)
            login_button.disabled = True
            error_message.value = ""
            page.update()

            res = await api_client.login(email_field.value, password_field.value)
            if res.get("status") == "success":
                error_message.value = "Zalogowano pomyślnie!"
                error_message.color = ft.Colors.GREEN_400
                page.update()
                await asyncio.sleep(0.3)
                # Pobierz profil i przejdź do menu
                await check_auth_guard("/menu")
                page.go("/menu")
            else:
                error_message.value = res.get("message", "Błąd logowania")
                error_message.color = ft.Colors.RED_400
                login_button.disabled = False
                await trigger_shake(email_field, page)
                await trigger_shake(password_field, page)

        login_button.on_click = handle_login_submit

        return ft.Column([
            ft.Text("Logowanie do systemu", size=24, weight=ft.FontWeight.BOLD),
            error_message,
            email_field,
            password_field,
            login_button,
            ft.TextButton("Nie masz konta? Zarejestruj się", on_click=lambda e: page.go("/register"))
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)

    # --- WIDOK REJESTRACJI (/register) ---
    def build_register_view() -> ft.Column:
        name_field = ft.TextField(label="Imię", width=320, prefix_icon=ft.Icons.PERSON, offset=ft.Offset(0, 0), animate_offset=ft.Animation(100))
        last_name_field = ft.TextField(label="Nazwisko", width=320, prefix_icon=ft.Icons.PERSON_OUTLINE, offset=ft.Offset(0, 0), animate_offset=ft.Animation(100))
        email_field = ft.TextField(label="E-mail", width=320, prefix_icon=ft.Icons.EMAIL, offset=ft.Offset(0, 0), animate_offset=ft.Animation(100))
        password_field = ft.TextField(label="Hasło", width=320, password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK, offset=ft.Offset(0, 0), animate_offset=ft.Animation(100))
        
        strength_bar = ft.ProgressBar(width=320, value=0, color=ft.Colors.RED_400, bgcolor=ft.Colors.GREY_200)
        strength_text = ft.Text("Siła hasła: min 10 znaków, duże/małe litery, cyfra i znak specjalny", size=12, color=ft.Colors.GREY_600)
        
        error_msg = ft.Text("", color=ft.Colors.RED_400, size=14)
        register_btn = ft.ElevatedButton("Zarejestruj się", width=200, disabled=True, scale=ft.Scale(1.0), animate_scale=ft.Animation(150))

        async def on_password_change(e):
            pwd = password_field.value or ""
            valid, color_name, score = check_password_strength(pwd)
            strength_bar.value = score / 100.0
            color_map = {"red": ft.Colors.RED_400, "orange": ft.Colors.ORANGE_400, "yellow": ft.Colors.YELLOW_600, "green": ft.Colors.GREEN_500}
            strength_bar.color = color_map.get(color_name, ft.Colors.RED_400)
            if valid:
                strength_text.value = "Siła hasła: Silne!"
                strength_text.color = ft.Colors.GREEN_600
            else:
                strength_text.value = "Siła hasła: Słabe (min. 10 zn., wielka/mała litera, cyfra, znak spec.)"
                strength_text.color = ft.Colors.RED_400
            
            register_btn.disabled = not (valid and name_field.value.strip() and last_name_field.value.strip() and email_field.value.strip())
            page.update()

        name_field.on_change = on_password_change
        last_name_field.on_change = on_password_change
        email_field.on_change = on_password_change
        password_field.on_change = on_password_change

        async def handle_register_submit(e):
            await trigger_pulse(register_btn, page)
            register_btn.disabled = True
            error_msg.value = ""
            page.update()

            res = await api_client.register(name_field.value, last_name_field.value, email_field.value, password_field.value)
            if res.get("status") == "success":
                error_msg.value = "Zarejestrowano! Przekierowanie do aktywacji..."
                error_msg.color = ft.Colors.GREEN_400
                page.update()
                await asyncio.sleep(1.0)
                page.go("/login")
            else:
                error_msg.value = res.get("message", "Błąd rejestracji")
                error_msg.color = ft.Colors.RED_400
                register_btn.disabled = False
                await trigger_shake(password_field, page)

        register_btn.on_click = handle_register_submit

        return ft.Column([
            ft.Text("Rejestracja nowego konta", size=24, weight=ft.FontWeight.BOLD),
            error_msg,
            name_field,
            last_name_field,
            email_field,
            password_field,
            strength_bar,
            strength_text,
            register_btn,
            ft.TextButton("Masz już konto? Zaloguj się", on_click=lambda e: page.go("/login"))
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)

    # --- WIDOK MENU (/menu) ---
    async def build_menu_view() -> ft.Column:
        skeleton = create_shimmer_skeleton()
        container = ft.Column([ft.Text("Menu Stołówki Szkolnej", size=24, weight=ft.FontWeight.BOLD), skeleton])
        page.update()

        res = await api_client.get_menu()
        if res.get("status") != "success":
            return ft.Column([ft.Text("Błąd ładowania menu", color=ft.Colors.RED_400)])

        categories = res.get("categories", [])
        cat_controls = [ft.Text("Menu Stołówki Szkolnej", size=24, weight=ft.FontWeight.BOLD)]

        for cat in categories:
            cat_controls.append(ft.Text(cat["name"], size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600))
            items = cat.get("items", [])
            if not items:
                cat_controls.append(ft.Text("Brak dań w tej kategorii.", italic=True, color=ft.Colors.GREY_500))
            for item in items:
                stock_txt = f"Dostępnych porcji: {item['stock']}" if item['stock'] > 0 else "Wyprzedane"
                stock_color = ft.Colors.GREEN_600 if item['stock'] > 0 else ft.Colors.RED_500

                option_dropdown = ft.Dropdown(
                    label="Dodatki / Opcje", width=260,
                    options=[ft.dropdown.Option(str(o["id"]), f"{o['option_name']} (+{o['add_to_price']:.2f} zł)") for o in item.get("options", [])]
                ) if item.get("options") else None

                add_btn = ft.ElevatedButton(
                    "Dodaj do koszyka",
                    icon=ft.Icons.ADD_SHOPPING_CART,
                    disabled=(item["stock"] <= 0),
                    scale=ft.Scale(1.0), animate_scale=ft.Animation(150)
                )

                async def make_add_handler(btn, itm_id, opt_dd):
                    async def handler(e):
                        await trigger_pulse(btn, page)
                        opts = [int(opt_dd.value)] if (opt_dd and opt_dd.value) else []
                        r = await api_client.add_to_cart(itm_id, 1, opts)
                        if r.get("status") == "success":
                            app_state["cart_count"] = sum(i.get("quantity", 1) for i in r.get("cart", {}).get("items", []))
                            page.snack_bar = ft.SnackBar(ft.Text(f"Dodano do koszyka! (TTL: 5 min)"))
                            page.snack_bar.open = True
                            await page.on_route_change(ft.RouteChangeEvent(route="/menu"))
                        else:
                            page.snack_bar = ft.SnackBar(ft.Text(f"Błąd: {r.get('message')}"), bgcolor=ft.Colors.RED_400)
                            page.snack_bar.open = True
                            page.update()
                    return handler

                add_btn.on_click = await make_add_handler(add_btn, item["id"], option_dropdown)

                card = ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Column([
                            ft.Row([
                                ft.Text(item["name"], size=16, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{item['price']:.2f} zł", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(item["descryption"] or "", size=13, color=ft.Colors.GREY_700),
                            ft.Text(stock_txt, size=12, weight=ft.FontWeight.BOLD, color=stock_color),
                            option_dropdown if option_dropdown else ft.Container(),
                            add_btn
                        ], spacing=8)
                    )
                )
                cat_controls.append(card)

        return ft.Column(cat_controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # --- WIDOK KOSZYKA (/cart) ---
    async def build_cart_view() -> ft.Column:
        skeleton = create_shimmer_skeleton()
        container = ft.Column([ft.Text("Twój Koszyk (Rezerwacja 5 min)", size=24, weight=ft.FontWeight.BOLD), skeleton])
        page.update()

        res = await api_client.get_cart()
        if res.get("status") != "success":
            return ft.Column([ft.Text("Błąd ładowania koszyka", color=ft.Colors.RED_400)])

        cart = res.get("cart", {})
        items = cart.get("items", [])
        total_price = cart.get("total_price", 0.0)
        ttl_sec = cart.get("expires_in_seconds", 300)

        controls = [
            ft.Text("Twój Koszyk (Rezerwacja 5 min)", size=24, weight=ft.FontWeight.BOLD),
            ft.Text(f"Czas na finalizację: ~{ttl_sec // 60}m {ttl_sec % 60}s", size=14, color=ft.Colors.ORANGE_600, weight=ft.FontWeight.BOLD)
        ]

        if not items:
            controls.append(ft.Text("Koszyk jest pusty.", size=16, italic=True))
        else:
            for item in items:
                rem_btn = ft.IconButton(icon=ft.Icons.DELETE, icon_color=ft.Colors.RED_400)
                async def make_rem_handler(itm_id, opts):
                    async def h(e):
                        r = await api_client.remove_from_cart(itm_id, None, opts)
                        if r.get("status") == "success":
                            app_state["cart_count"] = sum(i.get("quantity", 1) for i in r.get("cart", {}).get("items", []))
                        await page.on_route_change(ft.RouteChangeEvent(route="/cart"))
                    return h
                rem_btn.on_click = await make_rem_handler(item["item_id"], item["option_ids"])

                card = ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"{item['quantity']}x {item['name']}", weight=ft.FontWeight.BOLD),
                                ft.Text("Opcje: " + ", ".join(item['option_names']) if item['option_names'] else "Brak opcji", size=12, color=ft.Colors.GREY_600),
                            ], expand=True),
                            ft.Text(f"{item['item_total']:.2f} zł", weight=ft.FontWeight.BOLD),
                            rem_btn
                        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                    )
                )
                controls.append(card)

            controls.append(ft.Divider())
            controls.append(ft.Row([
                ft.Text("RAZEM:", size=18, weight=ft.FontWeight.BOLD),
                ft.Text(f"{total_price:.2f} zł", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

            checkout_btn = ft.ElevatedButton("Finalizuj Zamówienie", icon=ft.Icons.CHECK, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE, scale=ft.Scale(1.0), animate_scale=ft.Animation(150))
            clear_btn = ft.OutlinedButton("Wyczyść koszyk (zwróć porcje)", icon=ft.Icons.CANCEL)

            async def handle_checkout(e):
                await trigger_pulse(checkout_btn, page)
                checkout_btn.disabled = True
                page.update()
                r = await api_client.checkout()
                if r.get("status") == "success":
                    app_state["cart_count"] = 0
                    page.snack_bar = ft.SnackBar(ft.Text("Zamówienie sfinalizowane pomyślnie!"), bgcolor=ft.Colors.GREEN_600)
                    page.snack_bar.open = True
                    page.go("/orders")
                else:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Błąd: {r.get('message')}"), bgcolor=ft.Colors.RED_400)
                    page.snack_bar.open = True
                    checkout_btn.disabled = False
                    page.update()

            async def handle_clear(e):
                await api_client.clear_cart()
                app_state["cart_count"] = 0
                await page.on_route_change(ft.RouteChangeEvent(route="/cart"))

            checkout_btn.on_click = handle_checkout
            clear_btn.on_click = handle_clear

            controls.append(ft.Row([clear_btn, checkout_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))

        return ft.Column(controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # --- WIDOK ZAMÓWIEŃ (/orders) ---
    async def build_orders_view() -> ft.Column:
        skeleton = create_shimmer_skeleton()
        container = ft.Column([ft.Text("Twoje Zamówienia", size=24, weight=ft.FontWeight.BOLD), skeleton])
        page.update()

        res = await api_client.get_orders()
        if res.get("status") != "success":
            return ft.Column([ft.Text("Błąd ładowania zamówień", color=ft.Colors.RED_400)])

        orders = res.get("orders", [])
        controls = [ft.Text("Historia Zamówień", size=24, weight=ft.FontWeight.BOLD)]

        if not orders:
            controls.append(ft.Text("Brak złożonych zamówień.", italic=True))
        else:
            for o in orders:
                status_color = ft.Colors.GREEN_600 if o["status"] == "active" else ft.Colors.RED_400
                cancel_btn = ft.OutlinedButton("Anuluj (do 09:00)", icon=ft.Icons.CANCEL) if o["status"] == "active" else None

                async def make_cancel_handler(oid):
                    async def h(e):
                        r = await api_client.cancel_order(oid)
                        if r.get("status") == "success":
                            page.snack_bar = ft.SnackBar(ft.Text("Zamówienie anulowane! Porcje powróciły na stan."), bgcolor=ft.Colors.GREEN_600)
                        else:
                            page.snack_bar = ft.SnackBar(ft.Text(f"Błąd: {r.get('message')}"), bgcolor=ft.Colors.RED_400)
                        page.snack_bar.open = True
                        await page.on_route_change(ft.RouteChangeEvent(route="/orders"))
                    return h

                if cancel_btn:
                    cancel_btn.on_click = await make_cancel_handler(o["id"])

                items_txt = "\n".join([f"- {i['quantity']}x danie ID {i['menu_item_id']} ({i['price']:.2f} zł) {i['option_names']}" for i in o.get("items", [])])

                card = ft.Card(
                    content=ft.Container(
                        padding=12,
                        content=ft.Column([
                            ft.Row([
                                ft.Text(f"Zamówienie #{o['id']}", size=16, weight=ft.FontWeight.BOLD),
                                ft.Text(f"{o['total_price']:.2f} zł", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Text(f"Status: {o['status'].upper()}", color=status_color, weight=ft.FontWeight.BOLD),
                            ft.Text(f"Data: {o.get('created_at', '')[:19].replace('T', ' ')}", size=12, color=ft.Colors.GREY_600),
                            ft.Text(items_txt, size=13),
                            cancel_btn if cancel_btn else ft.Container()
                        ], spacing=6)
                    )
                )
                controls.append(card)

        return ft.Column(controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # --- WIDOK ADMINA (/admin) ---
    async def build_admin_view() -> ft.Column:
        skeleton = create_shimmer_skeleton()
        container = ft.Column([ft.Text("Panel Administratora", size=24, weight=ft.FontWeight.BOLD), skeleton])
        page.update()

        users_res = await api_client.admin_get_users()
        logs_res = await api_client.admin_get_logs()

        controls = [ft.Text("Panel Administratora & Zero Trust Audit", size=24, weight=ft.FontWeight.BOLD)]

        # Sekcja Użytkowników
        controls.append(ft.Text("Zarządzanie Rola / Użytkownicy (Odszyfrowane dane z DB):", size=18, weight=ft.FontWeight.BOLD))
        for u in users_res.get("users", []):
            role_dd = ft.Dropdown(
                value=u["role"], width=130,
                options=[ft.dropdown.Option(r) for r in ["rootadmin", "admin", "teacher", "student", "user"]]
            )
            upd_btn = ft.ElevatedButton("Zmień rolę")
            async def make_role_h(uid, r_dd):
                async def h(e):
                    r = await api_client.admin_update_user_role(uid, r_dd.value)
                    page.snack_bar = ft.SnackBar(ft.Text(r.get("message", "Zmieniono rolę")), bgcolor=ft.Colors.GREEN_600 if r.get("status") == "success" else ft.Colors.RED_400)
                    page.snack_bar.open = True
                    page.update()
                return h
            upd_btn.on_click = await make_role_h(u["id"], role_dd)

            card = ft.Card(content=ft.Container(padding=10, content=ft.Row([
                ft.Column([
                    ft.Text(f"ID: {u['id']} - {u['name']} {u['last_name']}", weight=ft.FontWeight.BOLD),
                    ft.Text(f"E-mail: {u['email']} | Aktywny: {u['is_active']}", size=12, color=ft.Colors.GREY_600)
                ], expand=True),
                role_dd,
                upd_btn
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)))
            controls.append(card)

        # Sekcja Dodawania Dania
        controls.append(ft.Divider())
        controls.append(ft.Text("Szybkie dodawanie dania do menu:", size=18, weight=ft.FontWeight.BOLD))
        item_name = ft.TextField(label="Nazwa dania", width=200)
        item_price = ft.TextField(label="Cena (zł)", width=100, value="15.00")
        item_stock = ft.TextField(label="Ilość porcji", width=100, value="50")
        add_item_btn = ft.ElevatedButton("Dodaj danie", icon=ft.Icons.ADD)

        async def handle_add_item(e):
            r = await api_client.admin_add_item(1, item_name.value, float(item_price.value or 0), int(item_stock.value or 0), "Danie dodane z panelu admina")
            page.snack_bar = ft.SnackBar(ft.Text(r.get("message", "Dodano danie")), bgcolor=ft.Colors.GREEN_600 if r.get("status") == "success" else ft.Colors.RED_400)
            page.snack_bar.open = True
            page.update()

        add_item_btn.on_click = handle_add_item
        controls.append(ft.Row([item_name, item_price, item_stock, add_item_btn], spacing=10))

        # Sekcja Logów
        controls.append(ft.Divider())
        controls.append(ft.Text("Ostatnie Logi Bezpieczeństwa (DB Logs Table):", size=18, weight=ft.FontWeight.BOLD))
        for l in logs_res.get("logs", [])[:15]:
            controls.append(ft.Text(f"[{l.get('created_at', '')[:19]}] [{l['level'].upper()}] IP: {l.get('ip_address', 'N/A')} -> {l['message']}", size=11, font_family="monospace"))

        return ft.Column(controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # --- ROUTE CHANGE HANDLER ---
    async def on_route_change(e: ft.RouteChangeEvent):
        page.controls.clear()
        route = e.route

        # Sprawdź auth guard
        if not await check_auth_guard(route):
            return

        nav = create_nav_bar()
        page.add(nav)

        if route == "/login":
            page.add(build_login_view())
        elif route == "/register":
            page.add(build_register_view())
        elif route == "/menu":
            menu_view = await build_menu_view()
            page.add(menu_view)
        elif route == "/cart":
            cart_view = await build_cart_view()
            page.add(cart_view)
        elif route == "/orders":
            orders_view = await build_orders_view()
            page.add(orders_view)
        elif route == "/admin":
            if app_state["role"] in ["admin", "rootadmin"]:
                admin_view = await build_admin_view()
                page.add(admin_view)
            else:
                page.add(ft.Text("Brak uprawnień do panelu administratora.", color=ft.Colors.RED_400, size=18))
        else:
            page.go("/login" if not app_state["role"] else "/menu")

        # Aktualizacja na koniec operacji (zgodnie z Instruction #3)
        page.update()

    page.on_route_change = on_route_change
    page.go("/login")

if __name__ == "__main__":
    ft.app(target=main)
