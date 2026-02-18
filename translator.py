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

OS_API_KEY = "sVvb2q0PHBMPy474EVjbwDuqWiqLFLIp"

def translate_batch_safe(texts):
    """وەرگێڕانی گروپێک دەق بە شێوەیەکی سەلامەت"""
    if not texts: return []
    translator = GoogleTranslator(source='en', target='ckb')
    combined = " [X] ".join(texts)
    try:
        res = translator.translate(combined)
        translated_list = res.split("[X]")
        if len(translated_list) != len(texts):
            return [translator.translate(t) for t in texts]
        return [t.strip() for t in translated_list]
    except Exception as e:
        print(f"⚠️ ئیرۆر لە وەرگێڕان: {e}")
        return texts

def translate_srt_now(srt_content):
    blocks = srt_content.strip().split('\n\n')
    final_srt = ""
    batch_texts, batch_meta = [], []
    
    print(f"🚀 دەستکرا بە وەرگێڕانی {len(blocks)} دێڕ...", flush=True)
    
    for i, block in enumerate(blocks):
        lines = block.split('\n')
        if len(lines) >= 3:
            batch_meta.append((lines[0], lines[1]))
            batch_texts.append("\n".join(lines[2:]))
            
            if len(batch_texts) >= 30:
                translated = translate_batch_safe(batch_texts)
                for j in range(min(len(translated), len(batch_meta))):
                    final_srt += f"{batch_meta[j][0]}\n{batch_meta[j][1]}\n{translated[j]}\n\n"
                batch_texts, batch_meta = [], []
                print(f"⚡ {i} دێڕ وەرگێڕدرا...", flush=True)
                time.sleep(0.5)

    if batch_texts:
        translated = translate_batch_safe(batch_texts)
        for j in range(min(len(translated), len(batch_meta))):
            final_srt += f"{batch_meta[j][0]}\n{batch_meta[j][1]}\n{translated[j]}\n\n"
            
    return final_srt

def get_opensubtitles_srt(tmdb_id):
    headers = {'Api-Key': OS_API_KEY, 'User-Agent': 'KurdishMovieBot v2.0'}
    try:
        res = requests.get(f"https://api.opensubtitles.com/api/v1/subtitles?tmdb_id={tmdb_id}&languages=en", headers=headers)
        if res.status_code == 200:
            data = res.json().get('data', [])
            if data:
                file_id = data[0]['attributes']['files'][0]['file_id']
                dl = requests.post("https://api.opensubtitles.com/api/v1/download", headers=headers, json={"file_id": file_id})
                link = dl.json().get('link')
                if link:
                    return requests.get(link).text
    except: pass
    return None

def start_worker():
    # پشکنینی نۆدی فیلمەکان (subtitled_movies) و زنجیرەکان (series)
    for path in ['/subtitled_movies', '/series']:
        ref = db.reference(path)
        items = ref.get()
        if not items: continue

        for m_id, data in items.items():
            if data.get('hasKurdishSub') == False:
                title = data.get('title', 'Unknown')
                print(f"🎬 خەریکی وەرگێڕانی: {title}", flush=True)
                
                srt = get_opensubtitles_srt(m_id)
                if srt and len(srt) > 500:
                    k_srt = translate_srt_now(srt)
                    db.reference(f'/kurdish_subtitles/{m_id}').set({"srt_content": k_srt})
                    ref.child(m_id).update({"hasKurdishSub": True})
                    print(f"✅ تەواو بوو: {title}", flush=True)
                    return True # یەک فیلم تەواو بوو
                else:
                    ref.child(m_id).update({"hasKurdishSub": "not_found"})
    return False # هیچ فیلمێک نەبوو بۆ وەرگێڕان

if __name__ == "__main__":
    print("🤖 بۆتی وەرگێڕی بێوەستان (Loop Mode) چالاک بوو...")
    # بۆ ماوەی 100 خول بەردەوام دەبێت
    for i in range(100):
        print(f"⏳ خولی وەرگێڕانی ژمارە {i+1} دەستی پێکرد...")
        found = start_worker()
        if not found:
            print("😴 فیلمی نوێ نییە بۆ وەرگێڕان، 30 چرکە پشوو...")
            time.sleep(30)
        else:
            time.sleep(2) # پشوو لە نێوان فیلمەکان
