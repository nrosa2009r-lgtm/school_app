import httpx
from config.conf import get_data

class ApiClientActions:
    def __init__(self, base_url:str = get_data("SERVER_IP")):
        
        self.client = httpx.AsyncClient(base_url=base_url,cookies=True)

    async def login(self,email:str,password:str) ->dict:
        try:
            response = await self.client.post(
                "/api/login",
                json={"email":email, "password":password}
            )
            return response.json()
        
        except Exception as e:
            return