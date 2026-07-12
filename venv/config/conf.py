import os
import json

def _get_conf_path() -> str:
    local_path = os.path.join(os.path.dirname(__file__), "conf.json")
    if os.path.exists(local_path):
        return local_path
    root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "venv", "config", "conf.json"))
    if os.path.exists(root_path):
        return root_path
    return local_path

def get_data(key: str):
    file_path = _get_conf_path()
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data.get(key)
    except Exception:
        return None

def put_data(key: str, value: str):
    file_path = _get_conf_path()
    data = {}
    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    data[key] = value
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
    try:
        from log.log_generator import create_log
        create_log(level="info", message=f"W konfiguracji dodano wpis {key}:{value}")
    except Exception:
        pass

def put_key(key: str, value: bytes):
    path = _get_conf_path()
    data = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError:
            data = {}
    if key in data:
        try:
            from log.log_generator import create_log
            create_log(level="warning", message=f"{key} Taki klucz już istnieje!")
        except Exception:
            pass
    else:
        data_value = value.decode('utf-8') if isinstance(value, bytes) else str(value)
        data[key] = data_value
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding='utf-8') as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        try:
            from log.log_generator import create_log
            create_log(level="info", message="Stworzono klucz w konfiguracji!")
        except Exception:
            pass
