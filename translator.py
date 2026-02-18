import os
import requests
import firebase_admin
import json
import time
from firebase_admin import credentials, db
from deep_translator import GoogleTranslator

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
        print(f"Error initializing Firebase: {e}", flush=True)

# کلیلەکان - کلیلەکەی خۆتم تێدا داناوەتەوە
OS_API_KEY = "sVvb2q0PHBMPy474EVjbwDuqWiqLFLIp"

def translate_batch_turbo(texts):
    """وەرگێڕانی 50 دێڕ بەیەکەوە بۆ زیادکردنی خێرایی"""
    translator = GoogleTranslator(source='en', target='ckb')
    combined = " ||| ".join(texts)
    try:
        res = translator.translate(combined)
        return [t.strip() for t in res.split("|||")]
    except:
        return texts

def translate_srt_now(srt_content):
    blocks = srt_content.strip().split('\n\n')
    final_srt = ""
    batch_texts, batch_meta = [], []
    
    print(f"🚀 دەستکرا بە وەرگێڕانی {len(blocks)} دێڕ بە خێرایی توربۆ...", flush=True)
    
    for block in blocks:
        lines = block.split('\n')
        if len(lines) >= 3:
            batch_meta.append((lines[0], lines[1]))
            batch_texts.append("\n".join(lines[2:]))
            
            # هەر کاتێک بوو بە 50 دێڕ، بەیەکەوە وەرگێڕانیان بۆ بکە
            if len(batch_texts) >= 50:
                translated = translate_batch_turbo(batch_texts)
                for j in range(len(translated)):
                    final_srt += f"{batch_meta[j][0]}\n{batch_meta[j][1]}\n{translated[j]}\n\n"
                batch_texts, batch_meta = [], []
                print(f"⚡ 50 دێڕ تەواو بوو...", flush=True)

    # بۆ ئەو دێڕانەی کە لە کۆتاییدا ماونەتەوە
    if batch_texts:
        translated = translate_batch_turbo(batch_texts)
        for j in range(len(translated)):
            final_srt += f"{batch_meta[j][0]}\n{batch_meta[j][1]}\n{translated[j]}\n\n"
            
    return final_srt

def get_opensubtitles_srt(tmdb_id):
    headers = {'Api-Key': OS_API_KEY, 'User-Agent': 'KurdishMovieBot v2.0'}
    try:
        # گەڕان بۆ ژێرنووس بەپێی ئایدی TMDB
        res = requests.get(f"https://api.opensubtitles.com/api/v1/subtitles?tmdb_id={tmdb_id}&languages=en", headers=headers)
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data:
                file_id = data[0]['attributes']['files'][0]['file_id']
                dl = requests.post("https://api.opensubtitles.com/api/v1/download", headers=headers, json={"file_id": file_id})
                if dl_res := dl.json().get('link'):
                    return requests.get(dl_res).text
    except Exception as e:
        print(f"Error fetching SRT: {e}", flush=True)
    return None

def start_worker():
    # سەیری فیلمەکان و زنجیرەکان دەکات
    paths = ['/subtitled_movies', '/tv_series']
    
    for path in paths:
        ref = db.reference(path)
        items = ref.get()
        if not items: continue

        for m_id, data in items.items():
            # تەنها ئەو فیلمانە دەگرێت کە هێشتا ژێرنووسی کوردییان بۆ نەکراوە
            if data.get('hasKurdishSub') == False:
                title = data.get('title', 'Unknown')
                print(f"🎬 خەریکی وەرگێڕانی: {title}", flush=True)
                
                srt = get_opensubtitles_srt(m_id)
                if srt and len(srt) > 500:
                    k_srt = translate_srt_now(srt)
                    # خەزنکردنی دەقە کوردییەکە
                    db.reference(f'/kurdish_subtitles/{m_id}').set({"srt_content": k_srt})
                    # نوێکردنەوەی فیلمەکە کە ئێستا کوردی هەیە
                    ref.child(m_id).update({"hasKurdishSub": True})
                    print(f"✅ ژێرنووسی کوردی بۆ {title} ئامادە کرا!", flush=True)
                    time.sleep(1) # پشوویەکی زۆر کورت
                else:
                    print(f"⚠️ ژێرنووس بۆ {title} نەدۆزرایەوە.", flush=True)

if __name__ == "__main__":
    print("🤖 بۆتی وەرگێڕی بێوەستان دەستی پێکرد...", flush=True)
    start_worker()
