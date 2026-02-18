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

def process_item_smart(item, is_tv=False):
    tmdb_id = str(item['id'])
    # گۆڕینی ناوی نۆدەکان بەپێی داواکاری تۆ
    path = 'series' if is_tv else 'subtitled_movies'
    ref = db.reference(f'/{path}/{tmdb_id}')
    
    # ئەگەر فیلم یان زنجیرەکە پێشتر نەبوو
    if ref.get() is None:
        data = {
            "id": item['id'],
            "title": item.get('title' if not is_tv else 'name'),
            "poster": f"https://image.tmdb.org/t/p/w500{item['poster_path']}",
            "year": item.get('release_date' if not is_tv else 'first_air_date', '0000')[:4],
            "hasKurdishSub": False,
            "type": "tv" if is_tv else "movie"
        }

        # ئەگەر زنجیرە بوو، هەموو وەرز و ئەڵقەکان ڕێکدەخەین
        if is_tv:
            print(f"📡 خەریکی هێنانی ئەڵقەکانی زنجیرەی: {data['title']}", flush=True)
            try:
                tv_url = f"https://api.themoviedb.org/3/tv/{tmdb_id}?api_key={TMDB_API_KEY}"
                tv_detail = requests.get(tv_url).json()
                
                seasons = {}
                for s in tv_detail.get('seasons', []):
                    s_num = s['season_number']
                    if s_num == 0: continue # وەرزی تایبەت لادەبەین
                    
                    episodes = {}
                    for e in range(1, s['episode_count'] + 1):
                        episodes[f"ep_{e}"] = {
                            "ep_num": e,
                            "url": f"https://vidsrc.me/embed/tv?tmdb={tmdb_id}&sea={s_num}&epi={e}",
                            "hasKurdishSub": False
                        }
                    seasons[f"season_{s_num}"] = episodes
                data["seasons"] = seasons
            except Exception as e:
                print(f"Error fetching TV details: {e}")
        else:
            # ئەگەر فیلم بوو، تەنها یەک لینکی هەیە
            data["url"] = f"https://vidsrc.me/embed/movie?tmdb={tmdb_id}"

        ref.set(data)
        print(f"✅ {data['title']} بە سەرکەوتوویی نێردرا بۆ /{path}", flush=True)

def run():
    status_ref = db.reference('/crawler_status')
    status = status_ref.get() or {"m": 1, "t": 1}
    
    # پشکنینی 5 لاپەڕە فیلم
    print(f"🚀 پشکنینی فیلمەکان لە لاپەڕەی {status['m']}...")
    for p in range(status['m'], status['m'] + 5):
        m_url = f"https://api.themoviedb.org/3/discover/movie?api_key={TMDB_API_KEY}&page={p}&sort_by=popularity.desc"
        m_list = requests.get(m_url).json().get('results', [])
        for i in m_list: process_item_smart(i, is_tv=False)
        status['m'] = p

    # پشکنینی 5 لاپەڕە زنجیرە
    print(f"🚀 پشکنینی زنجیرەکان لە لاپەڕەی {status['t']}...")
    for p in range(status['t'], status['t'] + 5):
        t_url = f"https://api.themoviedb.org/3/discover/tv?api_key={TMDB_API_KEY}&page={p}&sort_by=popularity.desc"
        t_list = requests.get(t_url).json().get('results', [])
        for i in t_list: process_item_smart(i, is_tv=True)
        status['t'] = p

    # خەزنکردنی لاپەڕەی کۆتایی
    status_ref.set(status)

if __name__ == "__main__":
    run()
