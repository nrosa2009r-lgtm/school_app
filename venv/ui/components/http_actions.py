import httpx
from config.conf import get_data
import http.cookiejar

class ApiClientActions:
    def __init__(self, base_url:str = get_data("SERVER_IP")):
        

        cookie_jar = http.cookiejar.CookieJar()

        self.client = httpx.AsyncClient(base_url=base_url,cookies=cookie_jar)

    async def login(self,email:str,password:str) ->dict:
        try:
            response = await self.client.post(
                "/api/login",
                json={"email":email, "password":password}
            )
            return response.json()
        
        except Exception as e:
            return {"status":"error","message":f"Błąd {str(e)}"}
    
    async def get_profile(self) -> dict:
        try:
            response = await self.client.get("/api/me")
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}

    async def logout(self) -> dict:
        try:
            response = await self.client.post("/api/logout")
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"Błąd połączenia: {str(e)}"}
        
    async def close(self):
        await self.client.aclose()


api_client = ApiClientActions()