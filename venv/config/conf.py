import json

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