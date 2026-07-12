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
        self.button = ft.IconButton(
            icon=ft.Icons.LIGHT_MODE,
            on_click=self.toggle_theme,
            tooltip="Przełącz motyw"
        )

    async def toggle_theme(self, e):
        self.is_dark = not self.is_dark
        self.page.theme_mode = ft.ThemeMode.DARK if self.is_dark else ft.ThemeMode.LIGHT
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
        ft.Container(height=60, bgcolor=ft.Colors.GREY_300, border_radius=8, opacity=0.6),
        ft.Container(height=60, bgcolor=ft.Colors.GREY_300, border_radius=8, opacity=0.4),
        ft.Container(height=60, bgcolor=ft.Colors.GREY_300, border_radius=8, opacity=0.3),
    ], spacing=10)


async def main(page: ft.Page):
    page.title = "School Catering Application"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 500
    page.window.height = 800
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.scroll = ft.ScrollMode.AUTO

    theme_manager = ThemeManager(page)

    app_state = {"role": "", "user_id": None, "email": "", "name": "", "cart_count": 0}

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
                cart_res = await api_client.get_cart()
                if cart_res.get("status") == "success":
                    items = cart_res.get("cart", {}).get("items", [])
                    app_state["cart_count"] = sum(i.get("quantity", 1) for i in items)
                return True
            else:
                page.go("/login")
                return False
        return True

    # --- LOGIN ---
    def build_login_view() -> ft.Column:
        email_field = ft.TextField(label="E-mail", width=320, prefix_icon=ft.Icons.EMAIL)
        password_field = ft.TextField(label="Hasło", width=320, password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK)
        error_message = ft.Text(value="", color=ft.Colors.RED_400, size=14)
        login_button = ft.ElevatedButton(content=ft.Text("Zaloguj się"), width=200, disabled=True)

        async def validate_fields(e):
            login_button.disabled = not (email_field.value.strip() and password_field.value.strip())
            page.update()

        email_field.on_change = validate_fields
        password_field.on_change = validate_fields

        async def handle_login(e):
            await trigger_pulse(login_button, page)
            login_button.disabled = True
            error_message.value = ""
            page.update()
            res = await api_client.login(email_field.value, password_field.value)
            if res.get("status") == "success":
                error_message.value = "Zalogowano!"
                error_message.color = ft.Colors.GREEN_400
                page.update()
                await asyncio.sleep(0.3)
                await check_auth_guard("/menu")
                page.go("/menu")
            else:
                error_message.value = res.get("message", "Błąd logowania")
                error_message.color = ft.Colors.RED_400
                login_button.disabled = False
                await trigger_shake(email_field, page)

        login_button.on_click = handle_login
        return ft.Column([
            ft.Text("Logowanie do systemu", size=24, weight=ft.FontWeight.BOLD),
            error_message, email_field, password_field, login_button,
            ft.TextButton("Nie masz konta? Zarejestruj się", on_click=lambda e: page.go("/register"))
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15)

    # --- REGISTER ---
    def build_register_view() -> ft.Column:
        name_field = ft.TextField(label="Imię", width=320, prefix_icon=ft.Icons.PERSON)
        last_name_field = ft.TextField(label="Nazwisko", width=320, prefix_icon=ft.Icons.PERSON_OUTLINE)
        email_field = ft.TextField(label="E-mail", width=320, prefix_icon=ft.Icons.EMAIL)
        password_field = ft.TextField(label="Hasło", width=320, password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK)
        strength_bar = ft.ProgressBar(width=320, value=0, color=ft.Colors.RED_400, bgcolor=ft.Colors.GREY_200)
        strength_text = ft.Text("Siła hasła: min 10 znaków", size=12, color=ft.Colors.GREY_600)
        error_msg = ft.Text("", color=ft.Colors.RED_400, size=14)
        register_btn = ft.ElevatedButton("Zarejestruj się", width=200, disabled=True)

        async def on_field_change(e):
            pwd = password_field.value or ""
            valid, color_name, score = check_password_strength(pwd)
            strength_bar.value = score / 100.0
            color_map = {"red": ft.Colors.RED_400, "orange": ft.Colors.ORANGE_400, "yellow": ft.Colors.YELLOW_600, "green": ft.Colors.GREEN_500}
            strength_bar.color = color_map.get(color_name, ft.Colors.RED_400)
            strength_text.value = "Siła hasła: Silne!" if valid else "Siła hasła: Słabe"
            strength_text.color = ft.Colors.GREEN_600 if valid else ft.Colors.RED_400
            register_btn.disabled = not (valid and name_field.value.strip() and last_name_field.value.strip() and email_field.value.strip())
            page.update()

        for f in [name_field, last_name_field, email_field, password_field]:
            f.on_change = on_field_change

        async def handle_register(e):
            await trigger_pulse(register_btn, page)
            register_btn.disabled = True
            error_msg.value = ""
            page.update()
            res = await api_client.register(name_field.value, last_name_field.value, email_field.value, password_field.value)
            if res.get("status") == "success":
                error_msg.value = "Zarejestrowano! Przejdź do logowania."
                error_msg.color = ft.Colors.GREEN_400
                page.update()
                await asyncio.sleep(1.0)
                page.go("/login")
            else:
                error_msg.value = res.get("message", "Błąd rejestracji")
                error_msg.color = ft.Colors.RED_400
                register_btn.disabled = False

        register_btn.on_click = handle_register
        return ft.Column([
            ft.Text("Rejestracja nowego konta", size=24, weight=ft.FontWeight.BOLD),
            error_msg, name_field, last_name_field, email_field, password_field,
            strength_bar, strength_text, register_btn,
            ft.TextButton("Masz już konto? Zaloguj się", on_click=lambda e: page.go("/login"))
        ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12)

    # --- MENU ---
    async def build_menu_view() -> ft.Column:
        skeleton = create_shimmer_skeleton()
        container = ft.Column([ft.Text("Menu Stołówki", size=24, weight=ft.FontWeight.BOLD), skeleton])
        page.update()

        from datetime import date, timedelta
        today = date.today()
        dates = [(today + timedelta(days=i)).isoformat() for i in range(6)]
        date_dd = ft.Dropdown(label="Data zamówienia", width=200, options=[ft.dropdown.Option(d, d) for d in dates], value=today.isoformat())

        diet_dd = ft.Dropdown(label="Dieta", width=200, options=[
            ft.dropdown.Option("", "Wszystkie"),
            ft.dropdown.Option("wegetariańskie", "Wegetariańskie"),
            ft.dropdown.Option("wegańskie", "Wegańskie"),
            ft.dropdown.Option("bez glutenu", "Bez glutenu")
        ], value="")

        allergen_txt = ft.TextField(label="Wyklucz alergen (np. orzechy)", width=200)

        res = await api_client.get_menu()
        if res.get("status") != "success":
            return ft.Column([ft.Text("Błąd ładowania menu", color=ft.Colors.RED_400)])

        categories = res.get("categories", [])
        cat_controls = [ft.Text("Menu Stołówki Szkolnej", size=24, weight=ft.FontWeight.BOLD),
                        ft.Text("Zamawianie z wyprzedzeniem:", size=14, color=ft.Colors.GREY_600),
                        ft.Row([date_dd, diet_dd, allergen_txt], spacing=10)]

        for cat in categories:
            cat_controls.append(ft.Text(cat["name"], size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_600))
            items = cat.get("items", [])
            if not items:
                cat_controls.append(ft.Text("Brak dań.", italic=True, color=ft.Colors.GREY_500))
            for item in items:
                stock_txt = f"Dostępnych porcji: {item['stock']}" if item['stock'] > 0 else "Wyprzedane"
                stock_color = ft.Colors.GREEN_600 if item['stock'] > 0 else ft.Colors.RED_500

                option_dropdown = ft.Dropdown(
                    label="Dodatki", width=260,
                    options=[ft.dropdown.Option(str(o["id"]), f"{o['option_name']} (+{o['add_to_price']:.2f} zł)") for o in item.get("options", [])]
                ) if item.get("options") else None

                add_btn = ft.ElevatedButton("Dodaj do koszyka", icon=ft.Icons.ADD_SHOPPING_CART, disabled=(item["stock"] <= 0))

                async def make_add_handler(btn, itm_id, opt_dd, dd):
                    async def handler(e):
                        await trigger_pulse(btn, page)
                        opts = [int(opt_dd.value)] if (opt_dd and opt_dd.value) else []
                        r = await api_client.add_to_cart_with_date(itm_id, 1, opts, dd.value)
                        if r.get("status") == "success":
                            app_state["cart_count"] = sum(i.get("quantity", 1) for i in r.get("cart", {}).get("items", []))
                            page.snack_bar = ft.SnackBar(ft.Text(f"Dodano do koszyka!"))
                            page.snack_bar.open = True
                        else:
                            page.snack_bar = ft.SnackBar(ft.Text(f"Błąd: {r.get('message')}"), bgcolor=ft.Colors.RED_400)
                            page.snack_bar.open = True
                        page.update()
                    return handler

                add_btn.on_click = await make_add_handler(add_btn, item["id"], option_dropdown, date_dd)

                card = ft.Card(content=ft.Container(padding=12, content=ft.Column([
                    ft.Row([ft.Text(item["name"], size=16, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{item['price']:.2f} zł", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(item["descryption"] or "", size=13, color=ft.Colors.GREY_700),
                    ft.Text(stock_txt, size=12, weight=ft.FontWeight.BOLD, color=stock_color),
                    option_dropdown if option_dropdown else ft.Container(),
                    add_btn
                ], spacing=8)))
                cat_controls.append(card)
        return ft.Column(cat_controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # --- CART ---
    async def build_cart_view() -> ft.Column:
        skeleton = create_shimmer_skeleton()
        container = ft.Column([ft.Text("Twój Koszyk", size=24, weight=ft.FontWeight.BOLD), skeleton])
        page.update()
        res = await api_client.get_cart()
        if res.get("status") != "success":
            return ft.Column([ft.Text("Błąd ładowania koszyka", color=ft.Colors.RED_400)])
        cart = res.get("cart", {})
        items = cart.get("items", [])
        total_price = cart.get("total_price", 0.0)
        ttl_sec = cart.get("expires_in_seconds", 300)
        controls = [ft.Text("Twój Koszyk", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(f"Czas: ~{ttl_sec // 60}m {ttl_sec % 60}s", size=14, color=ft.Colors.ORANGE_600)]
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
                card = ft.Card(content=ft.Container(padding=10, content=ft.Row([
                    ft.Column([ft.Text(f"{item['quantity']}x {item['name']}", weight=ft.FontWeight.BOLD),
                              ft.Text("Opcje: " + ", ".join(item['option_names']) if item.get('option_names') else "Brak opcji", size=12)], expand=True),
                    ft.Text(f"{item['item_total']:.2f} zł", weight=ft.FontWeight.BOLD), rem_btn
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)))
                controls.append(card)
            controls.append(ft.Divider())
            controls.append(ft.Row([ft.Text("RAZEM:", size=18, weight=ft.FontWeight.BOLD),
                                    ft.Text(f"{total_price:.2f} zł", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_700)],
                                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
            payment_dd = ft.Dropdown(
                label="Metoda płatności", width=200, value="cash",
                options=[
                    ft.dropdown.Option("cash", "💵 Gotówka"),
                    ft.dropdown.Option("card", "💳 Karta"),
                    ft.dropdown.Option("blik", "📱 BLIK"),
                ]
            )
            checkout_btn = ft.ElevatedButton("Finalizuj Zamówienie", icon=ft.Icons.CHECK, bgcolor=ft.Colors.GREEN_600, color=ft.Colors.WHITE)
            clear_btn = ft.OutlinedButton("Wyczyść koszyk", icon=ft.Icons.CANCEL)

            async def handle_checkout(e):
                await trigger_pulse(checkout_btn, page)
                r = await api_client.checkout(payment_method=payment_dd.value)
                if r.get("status") == "success":
                    app_state["cart_count"] = 0
                    page.snack_bar = ft.SnackBar(ft.Text("Zamówienie sfinalizowane!"), bgcolor=ft.Colors.GREEN_600)
                    page.snack_bar.open = True
                    page.go("/orders")
                else:
                    page.snack_bar = ft.SnackBar(ft.Text(f"Błąd: {r.get('message')}"), bgcolor=ft.Colors.RED_400)
                    page.snack_bar.open = True
                    page.update()

            async def handle_clear(e):
                await api_client.clear_cart()
                app_state["cart_count"] = 0
                await page.on_route_change(ft.RouteChangeEvent(route="/cart"))

            checkout_btn.on_click = handle_checkout
            clear_btn.on_click = handle_clear
            controls.append(payment_dd)
            controls.append(ft.Row([clear_btn, checkout_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN))
        return ft.Column(controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # --- ORDERS ---
    async def build_orders_view() -> ft.Column:
        skeleton = create_shimmer_skeleton()
        container = ft.Column([ft.Text("Twoje Zamówienia", size=24, weight=ft.FontWeight.BOLD), skeleton])
        page.update()
        res = await api_client.get_orders()
        if res.get("status") != "success":
            return ft.Column([ft.Text("Błąd ładowania zamówień", color=ft.Colors.RED_400)])
        orders = res.get("orders", [])
        controls = [ft.Text("Historia Zamówień", size=24, weight=ft.FontWeight.BOLD)]

        # Sekcja skanera QR dla personelu
        if app_state["role"] in ["admin", "rootadmin", "teacher"]:
            qr_field = ft.TextField(label="Wklej dane QR", width=300)
            qr_btn = ft.ElevatedButton("Skanuj i zweryfikuj QR")
            qr_result = ft.Text("")

            async def handle_qr_verify(e):
                r = await api_client.verify_order_qr(qr_field.value)
                if r.get("status") == "success":
                    qr_result.value = f"✅ {r.get('message')}"
                    qr_result.color = ft.Colors.GREEN_600
                else:
                    qr_result.value = f"❌ {r.get('message')}"
                    qr_result.color = ft.Colors.RED_400
                page.update()

            qr_btn.on_click = handle_qr_verify
            controls.append(ft.Divider())
            controls.append(ft.Text("🔍 Skaner QR (Personel Stołówki):", size=16, weight=ft.FontWeight.BOLD))
            controls.append(ft.Row([qr_field, qr_btn], spacing=10))
            controls.append(qr_result)
            controls.append(ft.Divider())

        if not orders:
            controls.append(ft.Text("Brak złożonych zamówień.", italic=True))
        else:
            for o in orders:
                status_color = ft.Colors.GREEN_600 if o["status"] == "active" else ft.Colors.RED_400
                cancel_btn = ft.OutlinedButton("Anuluj", icon=ft.Icons.CANCEL) if o["status"] == "active" else None
                qr_img = ft.Image(src="", width=200, height=200, visible=False)
                qr_show_btn = ft.TextButton("Pokaż kod QR")

                async def make_qr_handler(oid, img_control):
                    async def h(e):
                        r = await api_client.get_order_qrcode(oid)
                        if r.get("status") == "success" and r.get("qr_image"):
                            img_control.src = r["qr_image"]
                            img_control.visible = True
                            page.update()
                    return h

                async def make_cancel_handler(oid):
                    async def h(e):
                        r = await api_client.cancel_order(oid)
                        page.snack_bar = ft.SnackBar(ft.Text(r.get("message", "Anulowano")), bgcolor=ft.Colors.GREEN_600 if r.get("status") == "success" else ft.Colors.RED_400)
                        page.snack_bar.open = True
                        await page.on_route_change(ft.RouteChangeEvent(route="/orders"))
                    return h

                qr_show_btn.on_click = await make_qr_handler(o["id"], qr_img)
                if cancel_btn:
                    cancel_btn.on_click = await make_cancel_handler(o["id"])

                items_txt = "\n".join([f"- {i['quantity']}x danie ID {i['menu_item_id']} ({i['price']:.2f} zł)" for i in o.get("items", [])])
                card = ft.Card(content=ft.Container(padding=12, content=ft.Column([
                    ft.Row([ft.Text(f"Zamówienie #{o['id']}", size=16, weight=ft.FontWeight.BOLD),
                            ft.Text(f"{o['total_price']:.2f} zł", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_700)],
                           alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(f"Status: {o['status'].upper()}", color=status_color, weight=ft.FontWeight.BOLD),
                    ft.Text(items_txt, size=13),
                    ft.Row([qr_show_btn, cancel_btn if cancel_btn else ft.Container()]),
                    qr_img
                ], spacing=6)))
                controls.append(card)
        return ft.Column(controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # --- ADMIN ---
    async def build_admin_view() -> ft.Column:
        skeleton = create_shimmer_skeleton()
        container = ft.Column([ft.Text("Panel Administratora", size=24, weight=ft.FontWeight.BOLD), skeleton])
        page.update()
        users_res = await api_client.admin_get_users()
        logs_res = await api_client.admin_get_logs()

        controls = [ft.Text("Panel Administratora & Zero Trust Audit", size=24, weight=ft.FontWeight.BOLD)]

        # Użytkownicy
        controls.append(ft.Text("Zarządzanie Rolami:", size=18, weight=ft.FontWeight.BOLD))
        for u in users_res.get("users", []):
            role_dd = ft.Dropdown(value=u["role"], width=130,
                                  options=[ft.dropdown.Option(r) for r in ["rootadmin", "admin", "teacher", "student", "user"]])
            upd_btn = ft.ElevatedButton("Zmień rolę")
            async def make_role_h(uid, r_dd):
                async def h(e):
                    r = await api_client.admin_update_user_role(uid, r_dd.value)
                    page.snack_bar = ft.SnackBar(ft.Text(r.get("message", "Zmieniono")), bgcolor=ft.Colors.GREEN_600)
                    page.snack_bar.open = True
                    page.update()
                return h
            upd_btn.on_click = await make_role_h(u["id"], role_dd)
            card = ft.Card(content=ft.Container(padding=10, content=ft.Row([
                ft.Column([ft.Text(f"ID: {u['id']} - {u['name']} {u['last_name']}", weight=ft.FontWeight.BOLD),
                          ft.Text(f"E-mail: {u['email']} | Aktywny: {u['is_active']}", size=12)], expand=True),
                role_dd, upd_btn
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)))
            controls.append(card)

        # Dodawanie dania
        controls.append(ft.Divider())
        controls.append(ft.Text("Szybkie dodawanie dania:", size=18, weight=ft.FontWeight.BOLD))
        item_name = ft.TextField(label="Nazwa dania", width=200)
        item_price = ft.TextField(label="Cena (zł)", width=100, value="15.00")
        item_stock = ft.TextField(label="Porcje", width=100, value="50")
        add_item_btn = ft.ElevatedButton("Dodaj danie", icon=ft.Icons.ADD)

        async def handle_add_item(e):
            r = await api_client.admin_add_item(1, item_name.value, float(item_price.value or 0), int(item_stock.value or 0), "Danie dodane z panelu admina")
            page.snack_bar = ft.SnackBar(ft.Text(r.get("message", "Dodano")), bgcolor=ft.Colors.GREEN_600 if r.get("status") == "success" else ft.Colors.RED_400)
            page.snack_bar.open = True
            page.update()

        add_item_btn.on_click = handle_add_item
        controls.append(ft.Row([item_name, item_price, item_stock, add_item_btn], spacing=10))

        # Raport kuchni
        controls.append(ft.Divider())
        controls.append(ft.Text("Raport produkcyjny kuchni:", size=18, weight=ft.FontWeight.BOLD))
        report_btn = ft.ElevatedButton("Pobierz raport")
        report_text = ft.Text("")

        async def handle_report(e):
            r = await api_client.get_kitchen_report()
            if r.get("status") == "success":
                items = r.get("report", [])
                report_text.value = "\n".join([f"• {it['item']}: {it['total_ordered']} porcji" for it in items]) or "Brak danych"
            page.update()

        report_btn.on_click = handle_report
        controls.append(ft.Row([report_btn, report_text]))

        # 2FA setup
        controls.append(ft.Divider())
        controls.append(ft.Text("Konfiguracja 2FA:", size=18, weight=ft.FontWeight.BOLD))
        fa_btn = ft.ElevatedButton("Skonfiguruj 2FA (TOTP)")
        fa_result = ft.Text("")
        fa_code = ft.TextField(label="Kod z aplikacji", width=200)

        async def handle_2fa_setup(e):
            r = await api_client.setup_2fa()
            if r.get("status") == "success":
                fa_result.value = f"URI: {r.get('uri', '')}\nSekret: {r.get('secret', '')}"
            else:
                fa_result.value = f"Błąd: {r.get('message')}"
            page.update()

        fa_btn.on_click = handle_2fa_setup

        verify_fa_btn = ft.ElevatedButton("Zweryfikuj kod")
        async def handle_2fa_verify(e):
            r = await api_client.verify_2fa(fa_code.value)
            page.snack_bar = ft.SnackBar(ft.Text(r.get("message", "")), bgcolor=ft.Colors.GREEN_600 if r.get("status") == "success" else ft.Colors.RED_400)
            page.snack_bar.open = True
            page.update()

        verify_fa_btn.on_click = handle_2fa_verify
        controls.append(fa_btn)
        controls.append(fa_result)
        controls.append(ft.Row([fa_code, verify_fa_btn], spacing=10))

        # Logi
        controls.append(ft.Divider())
        controls.append(ft.Text("Ostatnie Logi:", size=18, weight=ft.FontWeight.BOLD))
        for l in logs_res.get("logs", [])[:10]:
            controls.append(ft.Text(f"[{l.get('created_at', '')[:19]}] [{l['level'].upper()}] {l['message']}", size=11, font_family="monospace"))

        return ft.Column(controls, spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)

    # --- ROUTER ---
    async def on_route_change(e: ft.RouteChangeEvent):
        page.controls.clear()
        route = e.route
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
                page.add(ft.Text("Brak uprawnień.", color=ft.Colors.RED_400, size=18))
        else:
            page.go("/login" if not app_state["role"] else "/menu")
        page.update()

    page.on_route_change = on_route_change
    page.go("/login")


if __name__ == "__main__":
    ft.app(target=main)
