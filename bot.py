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

TMDB_API_KEY = "7ff77f551b7a1db3b68d9a5a991e7cd5"

# فەنکشنی وەرگێڕانی ئۆتۆماتیکی فایلی SRT بۆ کوردی (سۆرانی)
def translate_srt_to_kurdish(srt_content):
    # ckb واتە سۆرانی (Central Kurdish)
    translator = GoogleTranslator(source='en', target='ckb') 
    blocks = srt_content.strip().split('\n\n')
    translated_srt = ""
    
    print(f"⏳ دەستکرا بە وەرگێڕانی {len(blocks)} دێڕ بۆ کوردی...")
    
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            index = lines[0]
            timestamp = lines[1]
            text_to_translate = "\n".join(lines[2:])
            
            try:
                # وەرگێڕانی دەقەکە
                translated_text = translator.translate(text_to_translate)
                translated_srt += f"{index}\n{timestamp}\n{translated_text}\n\n"
            except Exception as e:
                # ئەگەر کێشەیەک هەبوو، با بە ئینگلیزییەکە بمێنێتەوە تا فیلمەکە تێک نەچێت
                translated_srt += f"{index}\n{timestamp}\n{text_to_translate}\n\n"
                time.sleep(1) # پشوودان بۆ ئەوەی گووگڵ بلۆکمان نەکات
        else:
            translated_srt += block + "\n\n"
            
    return translated_srt

def sync_movies():
    url = f"https://api.themoviedb.org/3/movie/popular?api_key={TMDB_API_KEY}&language=en-US&page=1"
    
    try:
        response = requests.get(url)
        movies = response.json().get('results', [])
        
        movies_processed_this_run = 0 # ڕێگریکردن لە بلۆکبوونی گیتھەب
        
        for m in movies:
            m_id = str(m['id'])
            ref = db.reference(f'/subtitled_movies/{m_id}')
            
            if ref.get() is None:
                title = m['title']
                print(f"🎬 فیلمی نوێ دۆزرایەوە: {title}")
                
                # 1. هێنانی ژێرنووسە ئینگلیزییەکە
                eng_sub_url = f"https://sub.wyzie.ru/search?id={m_id}&format=srt&encoding=utf-8"
                eng_sub_response = requests.get(eng_sub_url)
                
                kurdish_subtitle_text = ""
                if eng_sub_response.status_code == 200 and len(eng_sub_response.text) > 100:
                    # 2. ناردنی بۆ وەرگێڕان ئەگەر ژێرنووس هەبوو
                    kurdish_subtitle_text = translate_srt_to_kurdish(eng_sub_response.text)
                    
                    # 3. خەزنکردنی ژێرنووسە کوردییەکە لە فایەربەیس (لە نۆدێکی تایبەت تا قورس نەبێت)
                    sub_ref = db.reference(f'/kurdish_subtitles/{m_id}')
                    sub_ref.set({"srt_content": kurdish_subtitle_text})
                    print(f"✅ ژێرنووسی کوردی بۆ {title} دروستکرا و خەزنکرا!")
                else:
                    print(f"⚠️ ژێرنووسی ئینگلیزی بۆ {title} نەدۆزرایەوە.")

                # 4. ئامادەکردنی زانیارییەکان ڕێک بەپێی مۆدێلەکەت
                movie_data = {
                    "id": m['id'],
                    "title": title,
                    "description": m['overview'],
                    "poster": f"https://image.tmdb.org/t/p/w500{m['poster_path']}",
                    "cover": f"https://image.tmdb.org/t/p/original{m.get('backdrop_path', '')}",
                    "imdb": m['vote_average'],
                    "year": int(m['release_date'][:4]) if m.get('release_date') else 0,
                    "url": f"https://vidsrc.me/embed/movie?tmdb={m_id}", # ئەمە دواتر دەگۆڕین بۆ Extractor
                    "type": "movie",
                    "isDubbed": False,
                    "hasKurdishSub": True if kurdish_subtitle_text else False # نیشانەیەک بۆ ئەپەکەت کە کوردی هەیە
                }
                ref.set(movie_data)
                
                # زۆر گرنگ: تەنها ٢ فیلم لە هەر کارپێکردنێکدا وەردەگێڕێت تا گووگڵ بلۆکمان نەکات!
                movies_processed_this_run += 1
                if movies_processed_this_run >= 2:
                    print("🛑 وەرگێڕانی ٢ فیلم تەواو بوو. پشوودان بۆ جاری داهاتوو تا گووگڵ ترانسلەیت بلۆکمان نەکات.")
                    break
            else:
                pass # فیلمەکە پێشتر هەیە
                
    except Exception as e:
        print(f"Error during sync: {e}")

if __name__ == "__main__":
    print("🚀 مەکینەی وەرگێڕان دەستی پێکرد...")
    sync_movies()
    print("✨ کارەکان تەواو بوون!")
