import os, requests, firebase_admin, json, time
from firebase_admin import credentials, db

if not firebase_admin._apps:
    try:
        fb_key = os.environ.get('FIREBASE_KEY')
        cred = credentials.Certificate(json.loads(fb_key))
        firebase_admin.initialize_app(cred, {'databaseURL': 'https://sarko-43d61-default-rtdb.firebaseio.com'})
    except: pass

TMDB_API_KEY = "7ff77f551b7a1db3b68d9a5a991e7cd5"

def process_item(item, is_tv=False):
    tmdb_id = str(item['id'])
    path = 'series' if is_tv else 'subtitled_movies'
    ref = db.reference(f'/{path}/{tmdb_id}')
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
        print(f"✅ زیادکرا: {data['title']}")

def run():
    status_ref = db.reference('/crawler_status')
    status = status_ref.get() or {}
    m_p = status.get('movie_page', 1)
    t_p = status.get('tv_page', 1)

    for p in range(m_p, m_p + 5):
        try:
            res = requests.get(f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&page={p}").json().get('results', [])
            for i in res: process_item(i, False)
            m_p = p
        except: break

    for p in range(t_p, t_p + 5):
        try:
            res = requests.get(f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_API_KEY}&page={p}").json().get('results', [])
            for i in res: process_item(i, True)
            t_p = p
        except: break

    status_ref.set({'movie_page': m_p + 1, 'tv_page': t_p + 1})

if __name__ == "__main__":
    # ئەم خولە وادەکات بۆتەکە نزیکەی 1 سەعات بەبەردەوام ئیش بکات
    for i in range(60): 
        print(f"🔄 خولی Crawler ژمارە {i+1}...")
        run()
        time.sleep(5) 
