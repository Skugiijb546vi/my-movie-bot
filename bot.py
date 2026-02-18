import os
import requests
import firebase_admin
import json
from firebase_admin import credentials, db

# 1. ڕێکخستنی فایەربەیس
if not firebase_admin._apps:
    # لێرەدا کلیلە نهێنییەکە (JSON) لە GitHub Secrets دەخوێندرێتەوە
    try:
        firebase_key_raw = os.environ.get('FIREBASE_KEY')
        if firebase_key_raw:
            decoded_key = json.loads(firebase_key_raw)
            cred = credentials.Certificate(decoded_key)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://sarko-43d61-default-rtdb.firebaseio.com'
            })
    except Exception as e:
        print(f"Error initializing Firebase: {e}")

# 2. کلیلی TMDB (ئەوەی خۆت دامناوە)
TMDB_API_KEY = "7ff77f551b7a1db3b68d9a5a991e7cd5"

def sync():
    # هێنانی فیلمە باوەکان (Popular)
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
    
    try:
        response = requests.get(url)
        movies = response.json().get('results', [])
        
        for m in movies:
            m_id = str(m['id'])
            # پشکنین لە ناو نۆدی subtitled_movies
            ref = db.reference(f'/subtitled_movies/{m_id}')
            
            if ref.get() is None:
                # ئامادەکردنی زانیارییەکان ڕێک بەپێی مۆدێلەکەت
                movie_data = {
                    "id": m['id'],
                    "title": m['title'],
                    "description": m['overview'],
                    "poster": f"https://image.tmdb.org/t/p/w500{m['poster_path']}",
                    "cover": f"https://image.tmdb.org/t/p/original{m.get('backdrop_path', '')}",
                    "imdb": m['vote_average'],
                    "year": int(m['release_date'][:4]) if m.get('release_date') else 0,
                    "url": f"https://vidsrc.me/embed/movie?tmdb={m_id}",
                    "type": "movie",
                    "isDubbed": False,
                    "subtitleEnglish": f"https://sub.wyzie.ru/search?id={m_id}&format=srt&encoding=utf-8"
                }
                ref.set(movie_data)
                print(f"✅ فیلمی نوێ زیاد کرا: {m['title']}")
            else:
                print(f"ℹ️ فیلمی ({m['title']}) پێشتر هەیە.")
                
    except Exception as e:
        print(f"Error during sync: {e}")

if __name__ == "__main__":
    sync()
