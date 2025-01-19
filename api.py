from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from instagram_private_api import Client, ClientError
import os
import json

app = FastAPI()

class UnfollowersRequest(BaseModel):
    username: str
    target_username: str

# Ortam değişkeninden oturum bilgilerini yükle
def load_session_from_env():
    session_json = os.getenv("INSTAGRAM_SESSION")
    if not session_json:
        raise Exception("No session data found in environment variables")
    return json.loads(session_json)

# Kullanıcının tüm takipçilerini al
def get_all_followers(api, user_id):
    followers = []
    rank_token = api.generate_uuid()
    next_max_id = ""
    while next_max_id is not None:
        response = api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)
        followers.extend([f["username"] for f in response["users"]])
        next_max_id = response.get("next_max_id")
    return set(followers)

# Kullanıcının tüm takip ettiklerini al
def get_all_followees(api, user_id):
    followees = []
    rank_token = api.generate_uuid()
    next_max_id = ""
    while next_max_id is not None:
        response = api.user_following(user_id, rank_token=rank_token, max_id=next_max_id)
        followees.extend([f["username"] for f in response["users"]])
        next_max_id = response.get("next_max_id")
    return set(followees)

@app.post("/unfollowers/")
async def get_unfollowers(data: UnfollowersRequest):
    try:
        # Ortam değişkeninden oturum bilgilerini al
        session_data = load_session_from_env()

        # Instagram API'yi oturum bilgileriyle başlat
        api = Client(data.username, None, settings=session_data)

        # Hedef kullanıcının takipçi ve takip edilen bilgilerini al
        user_id = api.username_info(data.target_username)["user"]["pk"]
        followers = get_all_followers(api, user_id)
        followees = get_all_followees(api, user_id)

        # Unfollowers hesapla
        unfollowers = followees - followers
        return {"unfollowers": list(unfollowers)}

    except ClientError as e:
        raise HTTPException(status_code=400, detail=f"Instagram API Error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
