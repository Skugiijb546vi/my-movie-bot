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
OS_API_KEY = os.environ.get('OS_API_KEY') # کلیلی OpenSubtitles

# 3. وەرگێڕانی زیرەک بە شێوازی پاکەت (Batch)
def translate_srt_to_kurdish(srt_content):
    translator = GoogleTranslator(source='en', target='ckb') 
    blocks = srt_content.strip().split('\n\n')
    
    metadata = []
    texts = []
    
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            metadata.append((lines[0], lines[1]))
            texts.append("\n".join(lines[2:]))
            
    print(f"⏳ خەریکی وەرگێڕانی {len(texts)} دێڕە بە شێوازی خێرا...")
    
    translated_texts = []
    batch_size = 25 # هەموو 25 دێڕێک بەیەکەوە وەردەگێڕێت
    separator = " \n\n "
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        combined = separator.join(batch)
        
        try:
            if len(combined) > 4500: # ئەگەر زۆر درێژ بوو
                for t in batch:
                    translated_texts.append(translator.translate(t))
            else:
                res = translator.translate(combined)
                chunks = res.split(separator)
                if len(chunks) == len(batch):
                    translated_texts.extend(chunks)
                else:
                    for t in batch:
                        translated_texts.append(translator.translate(t))
        except Exception as e:
            translated_texts.extend(batch) # ئەگەر کێشەیەک هەبوو، ئینگلیزییەکە دادەنێتەوە
        
        time.sleep(1) # پشوویەکی بچووک تا گووگڵ بلۆکمان نەکات
        
    final_srt = ""
    for i in range(len(translated_texts)):
        if i < len(metadata):
            idx, ts = metadata[i]
            final_srt += f"{idx}\n{ts}\n{translated_texts[i].strip()}\n\n"
            
    return final_srt

# 4. هێنانی فایلی ئۆرجیناڵ لە OpenSubtitles
def get_opensubtitles_srt(tmdb_id):
    if not OS_API_KEY:
        print("❌ کێشە: کلیلی OS_API_KEY دانەنراوە لە Secrets!")
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
                # داواکردنی لینکی داگرتن
                dl_res = requests.post("https://api.opensubtitles.com/api/v1/download", headers=headers, json={"file_id": file_id})
                if dl_res.status_code == 200:
                    download_link = dl_res.json().get('link')
                    srt_text = requests.get(download_link).text
                    return srt_text
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
            print(f"🎬 گەڕان لە OpenSubtitles بۆ: {title}")
            
            eng_srt = get_opensubtitles_srt(m_id)
            
            if eng_srt and len(eng_srt) > 500: # دڵنیابوونەوە کە فایلی ڕاستەقینەیە
                kurdish_text = translate_srt_to_kurdish(eng_srt)
                sub_ref.set({"srt_content": kurdish_text})
                movies_ref.child(m_id).update({"hasKurdishSub": True})
                print(f"✅ وەرگێڕان تەواو بوو بۆ: {title}")
            else:
                print(f"⚠️ ژێرنووسی ئینگلیزی نەدۆزرایەوە بۆ: {title}")
            
            processed += 1
            if processed >= 2: # تەنها 2 فیلم تا بلۆک نەبین
                print("🛑 وەرگێڕانی ٢ فیلم تەواو بوو. پشوودان بۆ ٥ خولەکی تر...")
                break

if __name__ == "__main__":
    translate_existing_movies()
            eng_sub_url = f"https://sub.wyzie.ru/search?id={m_id}&format=srt&encoding=utf-8"
            
            try:
                eng_sub_response = requests.get(eng_sub_url)
                if eng_sub_response.status_code == 200 and len(eng_sub_response.text) > 100:
                    
                    # وەرگێڕان بۆ کوردی
                    kurdish_text = translate_srt_to_kurdish(eng_sub_response.text)
                    
                    # خەزنکردنی لە فایەربەیس
                    sub_ref.set({"srt_content": kurdish_text})
                    
                    # گۆڕینی نیشانەی فیلمەکە بۆ ئەوەی ئەپەکەت بزانێت کوردی هەیە
                    movies_ref.child(m_id).update({"hasKurdishSub": True})
                    print(f"✅ وەرگێڕان تەواو بوو بۆ فیلمی: {title}")
                else:
                    print(f"⚠️ ژێرنووسی ئینگلیزی نەدۆزرایەوە بۆ: {title}")
            except Exception as e:
                print(f"Error fetching subtitle for {title}: {e}")
            
            # زۆر گرنگ: تەنها ٢ فیلم لە هەر کارپێکردنێکدا تا بلۆک نەبین
            processed += 1
            if processed >= 2:
                print("🛑 وەرگێڕانی ٢ فیلم تەواو بوو. پشوودان بۆ ٥ خولەکی تر...")
                break

if __name__ == "__main__":
    print("🚀 مەکینەی وەرگێڕانی فیلمەکانی ناو فایەربەیس دەستی پێکرد...")
    translate_existing_movies()
    print("✨ کارەکان تەواو بوون!")
