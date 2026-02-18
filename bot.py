import os
import requests
import firebase_admin
import json
from firebase_admin import credentials, db

# 1. Firebase Setup
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
        print(f"Error: {e}", flush=True)

TMDB_API_KEY = "7ff77f551b7a1db3b68d9a5a991e7cd5"

def process_item_fast(item, is_tv=False):
    m_id = str(item['id'])
    type_path = 'tv_series' if is_tv else 'subtitled_movies'
    ref = db.reference(f'/{type_path}/{m_id}')
    
    # ئەگەر فیلمەکە پێشتر نەبوو، یەکسەر زانیارییەکانی دابنێ
    if ref.get() is None:
        print(f"✅ خێرا زیادکرا: {item.get('title' if not is_tv else 'name')}", flush=True)
        data = {
            "id": item['id'],
            "title": item.get('title' if not is_tv else 'name'),
            "poster": f"https://image.tmdb.org/t/p/w500{item['poster_path']}",
            "year": item.get('release_date' if not is_tv else 'first_air_date', '0000')[:4],
            "hasKurdishSub": False, # هێشتا وەرگێڕانی بۆ نەکراوە
            "url": f"https://vidsrc.me/embed/movie?tmdb={m_id}" if not is_tv else f"https://vidsrc.me/embed/tv?tmdb={m_id}",
            "type": "tv" if is_tv else "movie"
        }
        ref.set(data)

def run_fast_crawler():
    # دەستپێکردن بە هێنانی 10 لاپەڕە بەیەکەوە (200 فیلم و زنجیرە لە هەر 3 خولەکێکدا!)
    status_ref = db.reference('/crawler_status')
    status = status_ref.get() or {"movie_page": 1, "tv_page": 1}
    
    m_page = status['movie_page']
    t_page = status['tv_page']

    print(f"🚀 پڕکردنەوەی خێرا دەستی پێکرد لە لاپەڕەی: {m_page}", flush=True)

    # هێنانی فیلمەکان (5 لاپەڕە = 100 فیلم)
    for p in range(m_page, m_page + 5):
        url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&page={p}&sort_by=popularity.desc"
        res = requests.get(url).json().get('results', [])
        for item in res: process_item_fast(item, is_tv=False)
        m_page = p

    # هێنانی زنجیرەکان (5 لاپەڕە = 100 زنجیرە)
    for p in range(t_page, t_page + 5):
        url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_API_KEY}&page={p}&sort_by=popularity.desc"
        res = requests.get(url).json().get('results', [])
        for item in res: process_item_fast(item, is_tv=True)
        t_page = p

    # خەزنکردنی شوێنی وەستان
    status_ref.set({"movie_page": m_page + 1, "tv_page": t_page + 1})

if __name__ == "__main__":
    run_fast_crawler()
