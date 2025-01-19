import os
import json
from instagram_private_api import Client, ClientError
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class UnfollowersRequest(BaseModel):
    username: str
    target_username: str

# Ortam değişkeninden oturum bilgisini yükle
def load_session_from_env():
    session_json = os.getenv("INSTAGRAM_SESSION")
    if not session_json:
        raise Exception("No session data found in environment variables")
    return json.loads(session_json)

@app.post("/unfollowers/")
async def get_unfollowers(data: UnfollowersRequest):
    try:
        # Ortam değişkeninden oturum bilgilerini al
        session_data = load_session_from_env()
        
        # Instagram API'yi oturum bilgileriyle başlat
        api = Client(data.username, None, settings=session_data)
        
        # Hedef kullanıcının takipçi ve takip edilen bilgilerini alın
        user_id = api.username_info(data.target_username)["user"]["pk"]
        followers = api.user_followers(user_id)["users"]
        followees = api.user_following(user_id)["users"]

        # Unfollowers hesapla
        unfollowers = set(f["username"] for f in followees) - set(f["username"] for f in followers)
        return {"unfollowers": list(unfollowers)}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=f"Instagram API Error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
