import os
import requests
import argparse
import time
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv
import google.generativeai as genai

# ==========================================
# 1. KONFIGURASI ENVIRONMENT & STATE
# ==========================================
load_dotenv()
app = Flask(__name__)

APP_ENV = os.getenv('APP_ENV', 'development')
EXTERNAL_API_URL = os.getenv('EXTERNAL_API_URL', 'https://www.googleapis.com/books/v1/volumes')
OPENLIBRARY_API_URL = os.getenv('OPENLIBRARY_API_URL', 'https://openlibrary.org/search.json')
API_KEY = os.getenv('EXTERNAL_API_KEY', '')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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
        # Menambahkan timeout 10 detik agar tidak lag berkepanjangan
        response = requests.get(EXTERNAL_API_URL, params=params, timeout=10)
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
            return fetch_from_openlibrary(query)
        else:
            # Fallback ke OpenLibrary jika Google error (misal 429 Too Many Requests)
            return fetch_from_openlibrary(query)
    except Exception as e:
        # Fallback jika timeout atau gagal koneksi ke Google
        return fetch_from_openlibrary(query)

def fetch_from_openlibrary(query):
    try:
        url = OPENLIBRARY_API_URL
        params = {'q': query, 'limit': 6}
        response = requests.get(url, params=params, timeout=10)
        system_stats["total_api_requests"] += 1
        
        if response.status_code == 200:
            data = response.json()
            if 'docs' in data and len(data['docs']) > 0:
                results = []
                for item in data['docs'][:6]:
                    cover_id = item.get('cover_i')
                    if cover_id:
                        thumbnail = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
                    elif item.get('isbn') and len(item['isbn']) > 0:
                        isbn = item['isbn'][0]
                        thumbnail = f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg"
                    else:
                        thumbnail = ""
                    
                    authors = item.get('author_name', ['Penulis tidak diketahui'])
                    publishers = item.get('publisher', ['Penerbit tidak diketahui'])
                    
                    results.append({
                        "title": item.get('title', 'Tidak diketahui'),
                        "authors": authors,
                        "publisher": publishers[0] if publishers else 'Penerbit tidak diketahui',
                        "published_date": str(item.get('first_publish_year', 'Tahun tidak diketahui')),
                        "page_count": item.get('number_of_pages_median', 0),
                        "description": "Tidak ada sinopsis tersedia dari sumber ini. (Data dari OpenLibrary)",
                        "thumbnail": thumbnail
                    })
                
                query_lower = query.lower()
                if query_lower in recent_searches:
                    recent_searches.remove(query_lower)
                recent_searches.insert(0, query_lower)
                if len(recent_searches) > 6: 
                    recent_searches.pop()
                
                return results
            return {"error": "Buku tidak ditemukan di database manapun (Google & OpenLibrary)."}
        else:
            return {"error": f"Semua API gangguan. Status OpenLibrary: {response.status_code}"}
    except Exception as e:
        return {"error": f"Kesalahan jaringan total saat mencoba fallback: {str(e)}"}

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

@app.route('/api/chat', methods=['POST'])
def chat_assistant():
    try:
        data = request.get_json()
        messages = data.get('messages', [])
        
        if not messages:
            return jsonify({"error": "Pesan tidak boleh kosong."}), 400
            
        system_instruction = "Anda adalah Pustakawan LibraryBook, asisten literatur yang berdedikasi, cerdas, dan ramah. Jangan pernah menyebut diri Anda sebagai Gemini, AI, LLM, atau program komputer. Bertindaklah seperti manusia staf perpustakaan yang nyata. Tugas utama Anda adalah memberikan rekomendasi buku, menjelaskan isi buku, dan membantu pengguna mengeksplorasi dunia literatur. Berikan respons yang ringkas, elegan, dan menggunakan bahasa Indonesia yang baik."
        
        # Inisialisasi model
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction)
        
        # Konversi format histori chat
        history = []
        for msg in messages[:-1]:
            role = "user" if msg['role'] == "user" else "model"
            history.append({"role": role, "parts": [msg['content']]})
            
        chat = model.start_chat(history=history)
        
        # Kirim pesan terbaru
        user_message = messages[-1]['content']
        response = chat.send_message(user_message)
        
        return jsonify({"reply": response.text})
            
    except Exception as e:
        return jsonify({"error": f"Terjadi kesalahan pada Gemini API: {str(e)}"}), 500

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