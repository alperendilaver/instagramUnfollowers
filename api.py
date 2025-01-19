from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from instagram_private_api import Client, ClientError

app = FastAPI()

class LoginData(BaseModel):
    username: str
    password: str
    target_username: str  # Hedef kullanıcının kullanıcı adı

def get_all_followers(api, user_id):
    followers = []
    rank_token = api.generate_uuid()
    next_max_id = ''

    while next_max_id is not None:
        response = api.user_followers(user_id, rank_token=rank_token, max_id=next_max_id)
        followers.extend([f['username'] for f in response['users']])
        next_max_id = response.get('next_max_id')

    return set(followers)

def get_all_followees(api, user_id):
    followees = []
    rank_token = api.generate_uuid()
    next_max_id = ''

    while next_max_id is not None:
        response = api.user_following(user_id, rank_token=rank_token, max_id=next_max_id)
        followees.extend([f['username'] for f in response['users']])
        next_max_id = response.get('next_max_id')

    return set(followees)

def get_profile(api, username):
    user_id = api.username_info(username)['user']['pk']
    followers = get_all_followers(api, user_id)
    followees = get_all_followees(api, user_id)
    return followers, followees

@app.post("/unfollowers/")
async def get_unfollowers(login_data: LoginData):
    try:
        api = Client(login_data.username, login_data.password)
        followers, followees = get_profile(api, login_data.target_username)
        unfollowers = followees - followers
        return {"unfollowers": list(unfollowers)}
    except ClientError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")