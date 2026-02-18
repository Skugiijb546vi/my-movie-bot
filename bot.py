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

# فەنکشنی وەرگێڕان
def translate_srt_to_kurdish(srt_content):
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
                translated_text = translator.translate(text_to_translate)
                translated_srt += f"{index}\n{timestamp}\n{translated_text}\n\n"
            except Exception as e:
                translated_srt += f"{index}\n{timestamp}\n{text_to_translate}\n\n"
                time.sleep(1)
        else:
            translated_srt += block + "\n\n"
    return translated_srt

def translate_existing_movies():
    # دەچێتە ناو فایەربەیسەکەی خۆت نەک TMDB
    movies_ref = db.reference('/subtitled_movies')
    all_movies = movies_ref.get()
    
    if not all_movies:
        print("هیچ فیلمێک لە فایەربەیس نەدۆزرایەوە.")
        return

    processed = 0
    for m_id, movie_data in all_movies.items():
        # پشکنین دەکات بزانێت ئایا ئەم فیلمە ژێرنووسی کوردی بۆ کراوە؟
        sub_ref = db.reference(f'/kurdish_subtitles/{m_id}')
        
        if sub_ref.get() is None:
            title = movie_data.get('title', 'Unknown')
            print(f"🎬 خەریکی پەیداکردنی ژێرنووس بۆ فیلمی: {title}")
            
            # هێنانی ژێرنووسە ئینگلیزییەکە بەپێی ئایدی فیلمەکە
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
