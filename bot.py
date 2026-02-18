import os
import requests
import firebase_admin
import json
from firebase_admin import credentials, db

# 1. ڕێکخستنی فایەربەیس
if not firebase_admin._apps:
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

TMDB_API_KEY = "7ff77f551b7a1db3b68d9a5a991e7cd5"

def sync_content(media_type):
    # media_type دەبێت 'movie' یان 'tv' بێت
    node_name = "subtitled_movies" if media_type == "movie" else "series"
    
    # لێرەدا دەتوانیت ژمارەی لاپەڕەکان زیاد بکەیت (بۆ نموونە لە 1 بۆ 10)
    for page in range(1, 11): 
        url = f"https://api.themoviedb.org/3/{media_type}/popular?api_key={TMDB_API_KEY}&language=en-US&page={page}"
        
        try:
            response = requests.get(url)
            results = response.json().get('results', [])
            
            for item in results:
                m_id = str(item['id'])
                # پشکنین بۆ ئەوەی داتای دووبارە نەیەت
                ref = db.reference(f'/{node_name}/{m_id}')
                
                if ref.get() is None:
                    # ئامادەکردنی داتا بۆ فیلم یان زنجیرە
                    is_movie = (media_type == "movie")
                    title = item.get('title') if is_movie else item.get('name')
                    date_key = 'release_date' if is_movie else 'first_air_date'
                    
                    content_data = {
                        "id": item['id'],
                        "title": title,
                        "description": item.get('overview', ''),
                        "poster": f"https://image.tmdb.org/t/p/w500{item.get('poster_path', '')}",
                        "cover": f"https://image.tmdb.org/t/p/original{item.get('backdrop_path', '')}",
                        "imdb": item.get('vote_average', 0.0),
                        "year": int(item.get(date_key, "0000")[:4]) if item.get(date_key) else 0,
                        "url": f"https://vidsrc.me/embed/{media_type}?tmdb={m_id}",
                        "type": media_type,
                        "isDubbed": False,
                        "subtitleEnglish": f"https://sub.wyzie.ru/search?id={m_id}&format=srt&encoding=utf-8"
                    }
                    
                    ref.set(content_data)
                    print(f"✅ {media_type} نوێ زیاد کرا: {title}")
                else:
                    print(f"ℹ️ {title} پێشتر لە ناو {node_name} هەیە.")
                    
        except Exception as e:
            print(f"Error during {media_type} sync on page {page}: {e}")

if __name__ == "__main__":
    print("🚀 دەست دەکرێت بە هێنانی فیلمەکان...")
    sync_content("movie")
    print("🚀 دەست دەکرێت بە هێنانی زنجیرەکان...")
    sync_content("tv")
    print("✨ هەموو کارەکان تەواو بوون!")
