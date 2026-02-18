import os
import requests
import firebase_admin
import json
from firebase_admin import credentials, db

# 1. ڕێکخستنی فایەربەیس
if not firebase_admin._apps:
    try:
        fb_key = os.environ.get('FIREBASE_KEY')
        cred = credentials.Certificate(json.loads(fb_key))
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://sarko-43d61-default-rtdb.firebaseio.com'
        })
    except Exception as e:
        print(f"Firebase Error: {e}", flush=True)

TMDB_API_KEY = "7ff77f551b7a1db3b68d9a5a991e7cd5"

def process_item(item, is_tv=False):
    tmdb_id = str(item['id'])
    # دیاریکردنی ڕێڕەوی خەزنکردن بەپێی داواکاری تۆ
    path = 'series' if is_tv else 'subtitled_movies'
    ref = db.reference(f'/{path}/{tmdb_id}')
    
    # ئەگەر فیلمەکە یان زنجیرەکە پێشتر بوونی نەبوو، زیادی بکە
    if ref.get() is None:
        data = {
            "id": item['id'],
            "title": item.get('title' if not is_tv else 'name'),
            "poster": f"https://image.tmdb.org/t/p/w500{item['poster_path']}",
            "year": item.get('release_date' if not is_tv else 'first_air_date', '0000')[:4],
            "hasKurdishSub": False,
            "url": f"https://vidsrc.me/embed/movie?tmdb={tmdb_id}" if not is_tv else f"https://vidsrc.me/embed/tv?tmdb={tmdb_id}",
            "type": "tv" if is_tv else "movie"
        }
        ref.set(data)
        print(f"✅ نێردرا بۆ /{path}: {data['title']}", flush=True)

def run():
    status_ref = db.reference('/crawler_status')
    status = status_ref.get() or {}
    
    # خوێندنەوەی لاپەڕەکان بە شێوەیەکی سەلامەت بۆ ئەوەی KeyError نەدات
    m_p = status.get('movie_page', 1)
    t_p = status.get('tv_page', 1)

    print(f"🚀 دەستکرا بە پشکنینی لاپەڕەی {m_p} بۆ فیلم و {t_p} بۆ زنجیرە...", flush=True)

    # هێنانی 5 لاپەڕە فیلم
    for p in range(m_p, m_p + 5):
        try:
            url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&page={p}&sort_by=popularity.desc"
            res = requests.get(url).json().get('results', [])
            for i in res:
                process_item(i, is_tv=False)
            m_p = p
        except: pass

    # هێنانی 5 لاپەڕە زنجیرە
    for p in range(t_p, t_p + 5):
        try:
            url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_API_KEY}&page={p}&sort_by=popularity.desc"
            res = requests.get(url).json().get('results', [])
            for i in res:
                process_item(i, is_tv=True)
            t_p = p
        except: pass

    # نوێکردنەوەی دۆخی لاپەڕەکان لە فایەربەیس
    status_ref.set({
        'movie_page': m_p + 1,
        'tv_page': t_p + 1
    })

if __name__ == "__main__":
    run()
