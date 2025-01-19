import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from instagram_private_api import Client, ClientError

app = FastAPI()



# Giriş bilgileri modeli
class LoginData(BaseModel):
    username: str
    password: str
    target_username: str

# Oturum bilgilerini ortam değişkenine kaydet
def save_session_to_env(api):
    session_json = json.dumps(api.settings)
    os.environ["INSTAGRAM_SESSION"] = session_json

# Ortam değişkeninden oturum bilgilerini yükle
def load_session_from_env():
    session_json = os.getenv("INSTAGRAM_SESSION")
    if session_json and session_json != "{}":
        return json.loads(session_json)
    return None

# Takipçileri çek
def get_all_followers(api, user_id):
    followers = []
    rank_token = api.generate_uuid()
    next_max_id = ""

    while next_max_id is not None:
        response = api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)
        followers.extend([f['username'] for f in response['users']])
        next_max_id = response.get('next_max_id')

    return set(followers)

# Takip edilenleri çek
def get_all_followees(api, user_id):
    followees = []
    rank_token = api.generate_uuid()
    next_max_id = ""

    while next_max_id is not None:
        response = api.user_following(user_id, rank_token=rank_token, max_id=next_max_id)
        followees.extend([f['username'] for f in response['users']])
        next_max_id = response.get('next_max_id')

    return set(followees)

# Profil bilgilerini al
def get_profile(api, username):
    user_id = api.username_info(username)['user']['pk']
    followers = get_all_followers(api, user_id)
    followees = get_all_followees(api, user_id)
    return followers, followees

# Unfollowers API endpoint
@app.post("/unfollowers/")
async def get_unfollowers(login_data: LoginData):
    try:
        # Oturum yükle
        settings = load_session_from_env()
        if settings:
            api = Client(login_data.username, login_data.password, settings=settings)
        else:
            api = Client(login_data.username, login_data.password)

        # Oturum kaydet
        save_session_to_env(api)

        # Takipçileri ve takip edilenleri al
        followers, followees = get_profile(api, login_data.target_username)
        unfollowers = followees - followers

        return {"unfollowers": list(unfollowers)}

    except ClientError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")
