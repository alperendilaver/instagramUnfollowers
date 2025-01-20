from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from instagram_private_api import Client, ClientError
import os
import json
import base64

app = FastAPI()

class UnfollowersRequest(BaseModel):
    username: str
    password: str
    target_username: str

def load_session_from_env():
    """Ortam değişkeninden oturum bilgilerini yükler."""
    session_json = os.getenv("INSTAGRAM_SESSION")
    if not session_json:
        raise Exception("No session data found in environment variables")
    session_data = json.loads(session_json)
    for key, value in session_data.items():
        if isinstance(value, str):
            try:
                session_data[key] = base64.b64decode(value.encode("utf-8"))
            except (ValueError, TypeError):
                pass
    return session_data

def save_session_to_env(api):
    """Yeni oturum bilgilerini ortam değişkenine kaydeder."""
    settings = api.settings
    for key, value in settings.items():
        if isinstance(value, bytes):
            settings[key] = base64.b64encode(value).decode("utf-8")
    os.environ["INSTAGRAM_SESSION"] = json.dumps(settings)

def recreate_session(username, password):
    """Oturum bilgileri geçersiz olduğunda yeni bir oturum oluştur."""
    try:
        api = Client(username, password)
        save_session_to_env(api)
        return api.settings
    except Exception as e:
        raise Exception(f"Failed to recreate session: {e}")

def get_all_followers(api, user_id):
    """Kullanıcının tüm takipçilerini alır."""
    followers = []
    rank_token = api.generate_uuid()
    next_max_id = None
    while next_max_id is not None or next_max_id == "":
        response = api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)
        print("Followers Response:", response)  # Hangi verilerin döndüğünü kontrol edin
        followers.extend([f["username"] for f in response["users"]])
        next_max_id = response.get("next_max_id", None)
    return set(followers)

def get_all_followees(api, user_id):
    """Kullanıcının tüm takip ettiklerini alır."""
    followees = []
    rank_token = api.generate_uuid()
    next_max_id = None
    while next_max_id is not None or next_max_id == "":
        response = api.user_following(user_id, rank_token=rank_token, max_id=next_max_id)
        print("Followees Response:", response)  # Hangi verilerin döndüğünü kontrol edin
        followees.extend([f["username"] for f in response["users"]])
        next_max_id = response.get("next_max_id", None)
    return set(followees)

@app.post("/unfollowers/")
async def get_unfollowers(data: UnfollowersRequest):
    try:
        # Oturum bilgilerini yükle veya yeniden oluştur
        try:
            session_data = load_session_from_env()
        except Exception:
            session_data = recreate_session(data.username, data.password)

        # Instagram API'yi başlat
        api = Client(data.username, None, settings=session_data)

        # Hedef kullanıcının takipçi ve takip edilen bilgilerini al
        user_id = api.username_info(data.target_username)["user"]["pk"]
        followers = get_all_followers(api, user_id)
        followees = get_all_followees(api, user_id)

        # Unfollowers hesapla
        unfollowers = followees - followers
        print("Followers:", followers)
        print("Followees:", followees)
        print("Unfollowers:", unfollowers)
        return {"unfollowers": list(unfollowers)}

    except ClientError as e:
        raise HTTPException(status_code=400, detail=f"Instagram API Error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
