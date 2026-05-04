import os
import requests
import argparse
import time
from flask import Flask, jsonify, render_template
from dotenv import load_dotenv

# ==========================================
# 1. KONFIGURASI ENVIRONMENT & STATE
# ==========================================
load_dotenv()
app = Flask(__name__)

APP_ENV = os.getenv('APP_ENV', 'development')
EXTERNAL_API_URL = os.getenv('EXTERNAL_API_URL', 'https://www.googleapis.com/books/v1/volumes')
API_KEY = os.getenv('EXTERNAL_API_KEY', '')

# In-Memory State (Data sementara)
recent_searches = ["bumi manusia", "clean code", "filosofi teras"]
system_stats = {
    "total_api_requests": 0,
    "start_time": time.time(),
    "active_users": 15 
}

# ==========================================
# 2. FUNGSI LOGIKA BACKEND (API EXTERNAL)
# ==========================================
def fetch_book_metadata(query):
    # maxResults menjadi 6 agar menampilkan banyak buku
    params = {'q': query, 'maxResults': 6}
    if API_KEY: params['key'] = API_KEY
        
    try:
        response = requests.get(EXTERNAL_API_URL, params=params)
        system_stats["total_api_requests"] += 1
        
        if response.status_code == 200:
            data = response.json()
            if 'items' in data and len(data['items']) > 0:
                results = []
                
                # Looping semua buku yang ditemukan
                for item in data['items']:
                    book_info = item.get('volumeInfo', {})
                    results.append({
                        "title": book_info.get('title', 'Tidak diketahui'),
                        "authors": book_info.get('authors', ['Penulis tidak diketahui']),
                        "publisher": book_info.get('publisher', 'Penerbit tidak diketahui'),
                        "published_date": book_info.get('publishedDate', 'Tahun tidak diketahui'),
                        "page_count": book_info.get('pageCount', 0),
                        "description": book_info.get('description', 'Tidak ada sinopsis tersedia untuk buku ini.'),
                        "thumbnail": book_info.get('imageLinks', {}).get('thumbnail', '')
                    })
                
                # Tambah ke riwayat pencarian
                query_lower = query.lower()
                if query_lower in recent_searches:
                    recent_searches.remove(query_lower)
                recent_searches.insert(0, query_lower)
                if len(recent_searches) > 6: 
                    recent_searches.pop()
                
                return results # Kembalikan array/list dari banyak buku
            return {"error": "Buku tidak ditemukan di database Google Books."}
        else:
            return {"error": f"Gagal terhubung ke API. Status: {response.status_code}"}
    except Exception as e:
        return {"error": f"Kesalahan jaringan: {str(e)}"}

# ==========================================
# 3. ROUTING WEB SERVER
# ==========================================
@app.route('/')
def index():
    return render_template('index.html', env=APP_ENV)

@app.route('/api/book/<query>')
def get_book_info(query):
    data = fetch_book_metadata(query)
    return jsonify({
        "environment": APP_ENV,
        "search_query": query,
        "result": data
    })

@app.route('/api/stats')
def get_system_stats():
    # Menambahkan endpoint yang dicari oleh file HTML (agar tidak 404 lagi)
    return jsonify({
        "total_requests": system_stats["total_api_requests"],
        "active_users": system_stats["active_users"],
        "recent_searches": recent_searches
    })

# ==========================================
# 4. CLI SERVER
# ==========================================
def run_cli():
    parser = argparse.ArgumentParser(description="CLI Tool - Library SaaS")
    parser.add_argument('action', choices=['runserver', 'fetch'])
    parser.add_argument('--query', default='bumi manusia')
    
    args = parser.parse_args()

    if args.action == 'fetch':
        print(f"\n[LibraryBook] Eksekusi CLI ({APP_ENV} env) -> Kata kunci: '{args.query}'\n")
        data = fetch_book_metadata(args.query)
        print("=== Hasil Data dari Google Books API ===")
        # Karena data sekarang list, kita potong print-nya agar tidak kepanjangan di terminal
        if isinstance(data, list):
            print(f"Ditemukan {len(data)} buku. Menampilkan detail buku pertama:")
            print(data[0])
        else:
            print(data)
        print("========================================\n")
    elif args.action == 'runserver':
        print(f"[*] Menjalankan Server di environment: {APP_ENV.upper()}")
        is_debug = (APP_ENV == 'development')
        app.run(host='0.0.0.0', port=5000, debug=is_debug)

if __name__ == '__main__':
    run_cli()