import os
import requests
import firebase_admin
import json
import time
from firebase_admin import credentials, db
from deep_translator import GoogleTranslator

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

# 2. کلیلەکان
TMDB_API_KEY = "7ff77f551b7a1db3b68d9a5a991e7cd5"
OS_API_KEY = "sVvb2q0PHBMPy474EVjbwDuqWiqLFLIp" # کلیلەکەی تۆ لێرە دانراوە

def translate_srt_to_kurdish(srt_content):
    translator = GoogleTranslator(source='en', target='ckb') 
    blocks = srt_content.strip().split('\n\n')
    translated_srt = ""
    
    print(f"⏳ خەریکی وەرگێڕانی دێڕەکانە...")
    
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            index = lines[0]
            timestamp = lines[1]
            text_to_translate = "\n".join(lines[2:])
            try:
                translated_text = translator.translate(text_to_translate)
                translated_srt += f"{index}\n{timestamp}\n{translated_text}\n\n"
            except Exception as e:
                translated_srt += f"{index}\n{timestamp}\n{text_to_translate}\n\n"
            time.sleep(0.5) # پشووی بچووک تا گووگڵ بلۆکمان نەکات
        else:
            translated_srt += block + "\n\n"
            
    return translated_srt

def get_opensubtitles_srt(tmdb_id):
    if not OS_API_KEY:
        print("❌ کێشە: کلیلی OS_API_KEY دانەنراوە!")
        return None
        
    headers = {
        'Api-Key': OS_API_KEY,
        'User-Agent': 'KurdishMovieBot v1.0'
    }
    
    search_url = f"https://api.opensubtitles.com/api/v1/subtitles?tmdb_id={tmdb_id}&languages=en"
    try:
        res = requests.get(search_url, headers=headers)
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data:
                file_id = data[0]['attributes']['files'][0]['file_id']
                dl_res = requests.post("https://api.opensubtitles.com/api/v1/download", headers=headers, json={"file_id": file_id})
                if dl_res.status_code == 200:
                    download_link = dl_res.json().get('link')
                    return requests.get(download_link).text
    except Exception as e:
        print(f"Error fetching from OpenSubtitles: {e}")
    return None

def translate_existing_movies():
    movies_ref = db.reference('/subtitled_movies')
    all_movies = movies_ref.get()
    
    if not all_movies: return

    processed = 0
    for m_id, movie_data in all_movies.items():
        sub_ref = db.reference(f'/kurdish_subtitles/{m_id}')
        
        if sub_ref.get() is None:
            title = movie_data.get('title', 'Unknown')
            print(f"🎬 گەڕان بۆ ژێرنووسی: {title}")
            
            eng_srt = get_opensubtitles_srt(m_id)
            
            if eng_srt and len(eng_srt) > 500:
                kurdish_text = translate_srt_to_kurdish(eng_srt)
                sub_ref.set({"srt_content": kurdish_text})
                movies_ref.child(m_id).update({"hasKurdishSub": True})
                print(f"✅ وەرگێڕان تەواو بوو بۆ: {title}")
            else:
                print(f"⚠️ ژێرنووسی ئینگلیزی نەدۆزرایەوە بۆ: {title}")
            
            processed += 1
            if processed >= 2:
                print("🛑 وەرگێڕانی ٢ فیلم تەواو بوو. پشوودان...")
                break

if __name__ == "__main__":
    translate_existing_movies()
