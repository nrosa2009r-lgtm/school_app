# pyright: reportUnusedCoroutine=false
import flet as ft
from ui.http_actions import api_client

async def main(page: ft.Page):
    page.title = "Shool-app"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window.width = 450
    page.window.height = 700
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # Definicja komponentów interfejsu logowania
    email_field = ft.TextField(label="E-mail", width=320, prefix_icon=ft.Icons.EMAIL)
    password_field = ft.TextField(label="Hasło", width=320, password=True, can_reveal_password=True, prefix_icon=ft.Icons.LOCK)
    error_message = ft.Text(value="", color=ft.Colors.RED_400, size=14)
    login_button = ft.ElevatedButton(content="Zaloguj się", width=150, disabled=True)

    async def theme_change(e):
        if e.control.value:
            page.theme_mode = ft.ThemeMode.DARK
            
        else:
            page.theme_mode = ft.ThemeMode.LIGHT
            
        page.update()

    theme_switch = ft.Switch(
        value=False,
        on_change=theme_change
    )

    # Funkcja sprawdzająca poprawność wypełnienia formularza
    async def validate_fields(e):
        if email_field.value.strip() and password_field.value.strip():
            login_button.disabled = False
        else:
            login_button.disabled = True
        page.update()

    # Rejestracja walidatora na bieżąco podczas wpisywania tekstu
    email_field.on_change = validate_fields
    password_field.on_change = validate_fields

    # Obsługa procesu logowania
    async def handle_login(e):
        # 1. Blokujemy natychmiast przycisk przed ponownym kliknięciem i czyścimy błędy
        login_button.disabled = True
        error_message.value = ""
        page.update()
        
        try:
            # 2. Wysyłamy zapytanie do API
            response = await api_client.login(email=email_field.value, password=password_field.value)
            
            if response.get("status") == "success":
                error_message.value = "Zalogowano pomyślnie!"
                error_message.color = ft.Colors.GREEN_400
                # Miejsce na ewentualne przekierowanie: page.go("/dashboard")
            else:
                error_message.value = response.get("message", "Niepoprawny e-mail lub hasło.")
                error_message.color = ft.Colors.RED_400
                # Odblokowujemy przycisk wyłącznie w przypadku błędu, by użytkownik mógł spróbować ponownie
                login_button.disabled = False
        except Exception:
            error_message.value = "Błąd połączenia z serwerem."
            error_message.color = ft.Colors.RED_400
            login_button.disabled = False
        
        page.update()

    # Przypisanie funkcji do przycisku logowania
    login_button.on_click = handle_login


    




    main_window = ft.Column([
        error_message,
        email_field,
        password_field,
        login_button
    ],
    alignment=ft.MainAxisAlignment.CENTER,
    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    expand=True
        )


    # Dodanie elementów do widoku strony
    page.add(
        ft.Stack(
            controls=[
                main_window,


                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.SUNNY, size=16),
                        theme_switch,
                        ft.Icon(ft.Icons.DARK_MODE, size=16)
                    ],
                    alignment=ft.MainAxisAlignment.END,
                    top=30,
                    right=5
                )
            ],
            expand=True
        )
    )

# Uruchomienie aplikacji
if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)
