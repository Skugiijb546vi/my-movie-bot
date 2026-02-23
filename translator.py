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
