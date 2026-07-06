# pyright: reportUnusedCoroutine=false
import flet as ft
from ui.http_actions import api_client

async def main(page: ft.Page):
    page.title = "Shool-app"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 450
    page.window.height = 700

    # Definicja komponentów interfejsu logowania
    email_field = ft.TextField(label="E-mail", width=320, prefix_icon=ft.Icons.EMAIL)
    password_field = ft.TextField(label="Hasło", width=320, password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK)
    error_message = ft.Text(value="", color=ft.Colors.RED_400, size=14)
    login_button = ft.Button(content=ft.Text("Zaloguj się"), width=150, disabled=True)

    # Funkcja sprawdzająca poprawność wypełnienia formularza
    async def validate_fields(e):
        if email_field.value.strip() != "" and password_field.value.strip() != "":
            login_button.disabled = False
        else:
            login_button.disabled = True
        page.update()  # USUNIĘTO AWAIT (Metoda synchroniczna)

    # Rejestracja walidatora na bieżąco podczas wpisywania tekstu
    email_field.on_change = validate_fields
    password_field.on_change = validate_fields

    # Obsługa procesu logowania
    async def handle_login(e):
        error_message.value = ""
        login_button.disabled = True
        page.update()  # USUNIĘTO AWAIT
        
        response = await api_client.login(email=email_field.value, password=password_field.value)
        
        if response.get("status") == "success":
            email_field.value = ""
            password_field.value = ""
            page.push_route("/dashboard")  # USUNIĘTO AWAIT
        else:
            error_message.value = response.get("detail", "Niepoprawny e-mail lub hasło.")
            login_button.disabled = False
            page.update()  # USUNIĘTO AWAIT

    # Obsługa procesu wylogowania
    async def handle_logout(e):
        await api_client.logout()
        page.push_route("/login")  # USUNIĘTO AWAIT

    # Powiązanie przycisku z funkcją logowania
    login_button.on_click = handle_login

    # Zarządzanie ścieżkami (routing) aplikacji
    async def route_change(route):
        page.views.clear()
        
        # 1. WIDOK LOGOWANIA
        if page.route == "/login" or page.route == "/":
            page.views.append(
                ft.View(
                    route="/login",
                    controls=[
                        ft.AppBar(title=ft.Text("Logowanie")),
                        ft.Column(
                            [
                                ft.Icon(ft.Icons.RESTAURANT_MENU, size=60, color=ft.Colors.BLUE_400),
                                ft.Text("Aplikacja Cateringowa", size=24, weight=ft.FontWeight.BOLD),
                                ft.Container(height=20),
                                email_field,
                                password_field,
                                error_message,
                                ft.Container(height=10),
                                login_button,
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            expand=True
                        )
                    ]
                )
            )
            
        # 2. WIDOK PANELU GŁÓWNEGO (DASHBOARD)
        elif page.route == "/dashboard":
            profile = await api_client.get_profile()
            
            # Weryfikacja sesji użytkownika
            if "detail" in profile or profile.get("status") == "error":
                page.push_route("/login")  # USUNIĘTO AWAIT
                return
                
            user_data = profile.get("user_data", {})
            user_role = user_data.get("role", "Brak roli")
            
            page.views.append(
                ft.View(
                    route="/dashboard",
                    controls=[
                        ft.AppBar(
                            title=ft.Text("Panel Główny"),
                            bgcolor=ft.Colors.ON_SURFACE_VARIANT,
                            actions=[
                                ft.IconButton(ft.Icons.LOGOUT, on_click=handle_logout, tooltip="Wyloguj się")
                            ]
                        ),
                        ft.Column(
                            [
                                ft.Text("Pomyślnie zalogowano!", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_400),
                                ft.Text(f"Zalogowano jako: {user_role}", size=16),
                                ft.Container(height=30),
                                ft.Button(content=ft.Text("Przejdź do zamówień"), on_click=lambda _: page.push_route("/orders")),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            expand=True
                        )
                    ]
                )
            )
        page.update()  # USUNIĘTO AWAIT

    # Rejestracja mechanizmu routingu
    page.on_route_change = route_change
    
    # Ręczne wywołanie lokalnego managera widoków (funkcja jest async def, więc tu zostawiamy await!)
    await route_change(page.route)
    page.push_route("/login")  # USUNIĘTO AWAIT

if __name__ == "__main__":
    ft.run(main)
