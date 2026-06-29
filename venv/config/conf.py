import os
import json
from log.log_generator import create_log

#Geting parameters from config file
def get_data(key:str):
    with open("venv/config/conf.json","r",encoding="utf-8") as file:
        data = json.load(file)
        
        return data.get(key)
    

#Inserting data into config file
def put_data(key: str, value: str):
    file_path = "venv/config/conf.json"
    data = {}
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        
        pass

    data[key] = value

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)

    create_log(level="info", message=f"W konfiguracji dodano wpis {key}:{value}")#Inserting key into config file
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
