import os
import json
from log.log_generator import create_log
def get_data(key:str):
    with open("venv/config/conf.json","r",encoding="utf-8") as file:
        data = json.load(file)
        search = data[key]
        return search
    
def put_data(key:str,value:str):
    with open("venv/config/conf.json","w",encoding="utf-8") as file:
        data = {
            key:value
        }
        json.dump(data,file,indent=4)
        create_log(level="info",message=f"W konfiguracjii dodano wpis {key}:{value}")

def put_key(key:str,value:bytes):
    path = "venv/config/conf.json"
    if os.path.exists(path):
        try:
              with open(path, "r", encoding="utf-8") as file:
                   data = json.load(file)  
        except json.JSONDecodeError:
               data = {}  
    else:
         data = {}
    if key in data:
        create_log(level="warning",message=f"{key} Taki klucz jusz instnieje!")
    else:
        data_value = value.decode('utf-8')
        data[key] = data_value

        with open(path,"w",encoding='utf-8') as file:
            json.dump(data,file,indent=4,ensure_ascii=False)
            create_log(level="info",message="Stworzono master key!")
