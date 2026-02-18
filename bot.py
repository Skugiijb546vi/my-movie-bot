import os, requests, firebase_admin, json
from firebase_admin import credentials, db

if not firebase_admin._apps:
    # لێرەدا کلیلە نهێنییەکە لە گیتھەب دەخوێنینەوە
    decoded_key = json.loads(os.environ.get('FIREBASE_KEY'))
    cred = credentials.Certificate(decoded_key)
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'لینکەکەت_لێرە_دابنێ' 
    })

TMDB_API_KEY = "کلیلی_تۆ_لێرە_دابنێ"

def sync():
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
    movies = requests.get(url).json().get('results', [])
    for m in movies:
        m_id = str(m['id'])
        ref = db.reference(f'/subtitled_movies/{m_id}')
        if ref.get() is None:
            ref.set({
                "id": m['id'], "title": m['title'], "description": m['overview'],
                "poster": f"https://image.tmdb.org/t/p/w500{m['poster_path']}",
                "url": f"https://vidsrc.me/embed/movie?tmdb={m_id}",
                "type": "movie", "subtitleEnglish": f"https://sub.wyzie.ru/search?id={m_id}&format=srt&encoding=utf-8"
            })
            print(f"Added: {m['title']}")
sync()
