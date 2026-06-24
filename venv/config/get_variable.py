import json
from pathlib import Path

# 1. Pobiera ścieżkę do folderu, w którym znajduje się TEN plik (np. /twój_projekt/config)
CURRENT_DIR = Path(__file__).resolve().parent

# 2. Tworzy absolutną ścieżkę do pliku conf.json w tym samym folderze
CONFIG_PATH = CURRENT_DIR / "conf.json"

# 3. Bezpieczne wczytanie danych
with open(CONFIG_PATH, "r", encoding="utf-8") as file:
    data = json.load(file)
    db_url = data["DATABASE_URL"]

# Wyświetli poprawny url niezależnie od tego, skąd uruchomisz projekt
print(db_url)
