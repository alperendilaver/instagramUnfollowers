from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from instagram_private_api import Client, ClientError
import json
import os
import base64
import pickle

app = FastAPI()

# Giriş için kullanılan veri modeli
class LoginData(BaseModel):
    username: str
    password: str

# Unfollowers için kullanılan veri modeli
class UnfollowersRequest(BaseModel):
    username: str
    target_username: str

# Oturum bilgilerini base64 ile encode ederek kaydet
def save_session_to_file(api, session_file="session.json"):
    settings = api.settings
    for key, value in settings.items():
        if isinstance(value, bytes):
            settings[key] = base64.b64encode(value).decode("utf-8")
    with open(session_file, "w") as file:
        json.dump(settings, file)

# Oturum bilgilerini dosyadan yükle
def load_session_from_file(session_file="session.json"):
    if not os.path.exists(session_file):
        raise FileNotFoundError("Session file not found.")
    with open(session_file, "r") as file:
        settings = json.load(file)
    for key, value in settings.items():
        if isinstance(value, str):
            try:
                settings[key] = base64.b64decode(value.encode("utf-8"))
            except (ValueError, TypeError):
                pass
    return settings

# Giriş endpoint'i
@app.post("/login/")
async def login_and_save_session(login_data: LoginData):
    try:
        # Instagram'a giriş yap
        api = Client(login_data.username, login_data.password)

        # Oturum bilgilerini kaydet
        save_session_to_file(api)

        return {"message": "Login successful, session saved to session.json"}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=f"Login failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")

# Unfollowers endpoint'i
@app.post("/unfollowers/")
async def get_unfollowers(data: UnfollowersRequest):
    try:
        # Oturum bilgilerini dosyadan yükle
        session_settings = load_session_from_file()

        # Instagram API'yi oturum bilgileriyle başlat
        api = Client(data.username, None, settings=session_settings)

        # Hedef kullanıcının takipçi ve takip edilen bilgilerini al
        user_id = api.username_info(data.target_username)["user"]["pk"]
        followers = api.user_followers(user_id)["users"]
        followees = api.user_following(user_id)["users"]

        # Unfollowers hesapla
        unfollowers = set(f["username"] for f in followees) - set(f["username"] for f in followers)
        return {"unfollowers": list(unfollowers)}
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail="Session file not found. Please log in first.")
    except ClientError as e:
        raise HTTPException(status_code=400, detail=f"Instagram API Error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {e}")
