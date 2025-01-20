from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from instagram_private_api import Client, ClientError
import os
import json
import base64
import asyncio
import redis

# FastAPI uygulaması başlat
app = FastAPI()

# Redis önbelleği yapılandır
cache = redis.StrictRedis(host='localhost', port=6379, db=0)

# İstek modeli tanımla
class UnfollowersRequest(BaseModel):
    username: str
    password: str
    target_username: str

# Oturum bilgilerini ortam değişkeninden yükleme
def load_session_from_env():
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

# Yeni oturum bilgilerini ortam değişkenine kaydetme
def save_session_to_env(api):
    settings = api.settings
    for key, value in settings.items():
        if isinstance(value, bytes):
            settings[key] = base64.b64encode(value).decode("utf-8")
    os.environ["INSTAGRAM_SESSION"] = json.dumps(settings)

# Oturumu yeniden oluşturma
def recreate_session(username, password):
    try:
        api = Client(username, password)
        save_session_to_env(api)
        return api.settings
    except Exception as e:
        raise Exception(f"Failed to recreate session: {e}")

# Kullanıcının tüm takipçilerini alma
def get_all_followers(api, user_id):
    followers = set()
    rank_token = api.generate_uuid()
    next_max_id = None
    while next_max_id != "":
        response = api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)
        followers.update([f["username"] for f in response["users"]])
        next_max_id = response.get("next_max_id", None)
    return followers

# Kullanıcının tüm takip ettiklerini alma
def get_all_followees(api, user_id):
    followees = set()
    rank_token = api.generate_uuid()
    next_max_id = None
    while next_max_id != "":
        response = api.user_following(user_id, rank_token=rank_token, max_id=next_max_id)
        followees.update([f["username"] for f in response["users"]])
        next_max_id = response.get("next_max_id", None)
    return followees

# Redis önbelleğini kullanarak takipçileri alma
def cache_followers(api, user_id):
    followers_key = f"followers:{user_id}"
    if cache.exists(followers_key):
        return json.loads(cache.get(followers_key))
    followers = get_all_followers(api, user_id)
    cache.setex(followers_key, 3600, json.dumps(list(followers)))  # 1 saat önbellek
    return followers

# Redis önbelleğini kullanarak takip edilenleri alma
def cache_followees(api, user_id):
    followees_key = f"followees:{user_id}"
    if cache.exists(followees_key):
        return json.loads(cache.get(followees_key))
    followees = get_all_followees(api, user_id)
    cache.setex(followees_key, 3600, json.dumps(list(followees)))  # 1 saat önbellek
    return followees

# Asenkron takipçi ve takip edilen veri çekimi
async def fetch_followers(api, user_id):
    return await asyncio.to_thread(cache_followers, api, user_id)

async def fetch_followees(api, user_id):
    return await asyncio.to_thread(cache_followees, api, user_id)

# Unfollowers API endpoint
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

        # Asenkron takipçi ve takip edilen verilerini çek
        user_id = api.username_info(data.target_username)["user"]["pk"]
        followers, followees = await asyncio.gather(
            fetch_followers(api, user_id),
            fetch_followees(api, user_id)
        )

        # Takipleşenleri hesapla
        mutual_followers = set(followees) & set(followers)

        # Unfollowers hesapla
        unfollowers = set(followees) - mutual_followers

        return {"unfollowers": list(unfollowers)}

    except ClientError as e:
        raise HTTPException(status_code=400, detail=f"Instagram API Error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
