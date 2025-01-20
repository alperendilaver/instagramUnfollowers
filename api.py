import os
import base64
from fastapi import FastAPI, HTTPException
import instaloader

app = FastAPI()

def get_instagram_follow_data(base64_session: str, username: str):
    """
    Instagram takipçi ve takip edilen verilerini alır.
    base64 olarak gelen session verisini çözerek geçici bir dosya oluşturur.
    """
    try:
        # Base64 formatındaki session verisini çöz
        session_data = base64.b64decode(base64_session)
        temp_session_file = "/tmp/instaloader_session"

        # Geçici session dosyasını oluştur
        with open(temp_session_file, "wb") as f:
            f.write(session_data)

        # Instaloader ile session yükle
        instagram = instaloader.Instaloader()
        instagram.load_session_from_file(temp_session_file)
        profile = instaloader.Profile.from_username(instagram.context, username)

        followers = [f.username for f in profile.get_followers()]
        followees = [f.username for f in profile.get_followees()]

        return followers, followees
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hata: {str(e)}")
    finally:
        # Geçici dosyayı sil
        if os.path.exists(temp_session_file):
            os.remove(temp_session_file)

@app.get("/unfollowers")
def get_unfollowers(username: str):
    """
    Geri takip etmeyen kullanıcıları döner.
    Session bilgisi environment değişkeninden alınır.
    """
    # Environment'den session bilgisi al
    base64_session = os.getenv("INSTAGRAM_SESSION")
    if not base64_session:
        raise HTTPException(status_code=500, detail="Session bilgisi bulunamadı.")

    # Takipçi ve takip edilenleri al
    followers, followees = get_instagram_follow_data(base64_session, username)

    # Geri takip etmeyen kullanıcıları hesapla
    unfollowers = [user for user in followees if user not in followers]
    return {"unfollowers": unfollowers}
