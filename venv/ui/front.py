import flet as ft
from ui.http_actions import api_client

async def main(page: ft.Page):
    page.title = "Shool-app"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 450
    page.window.height = 700

    page.update()

















ft.app(target=main)