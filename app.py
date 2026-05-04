import os
import requests
import argparse
from flask import Flask, jsonify, render_template_string
from dotenv import load_dotenv

# 1. Load konfigurasi dari file .env
# Membedakan environment staging/development dan production
load_dotenv()

app = Flask(__name__)

# Konfigurasi Environment dan API
APP_ENV = os.getenv('APP_ENV', 'development')
EXTERNAL_API_URL = os.getenv('EXTERNAL_API_URL', 'https://www.googleapis.com/books/v1/volumes')
API_KEY = os.getenv('EXTERNAL_API_KEY', '')

# 2. FUNGSI INTEGRASI REST API (Menggunakan Google Books API)
def fetch_book_metadata(query):
    """
    Fungsi untuk mengambil data metadata buku dari API eksternal.
    """
    # Menyusun parameter pencarian
    params = {
        'q': query,
        'maxResults': 1  # Ambil 1 hasil paling relevan untuk contoh
    }
    
    # Tambahkan API Key jika diset di .env
    if API_KEY:
        params['key'] = API_KEY
        
    try:
        response = requests.get(EXTERNAL_API_URL, params=params)
        
        if response.status_code == 200:
            data = response.json()
            # Cek apakah buku ditemukan
            if 'items' in data and len(data['items']) > 0:
                book_info = data['items'][0]['volumeInfo']
                return {
                    "title": book_info.get('title', 'Tidak diketahui'),
                    "authors": book_info.get('authors', ['Tidak diketahui']),
                    "publisher": book_info.get('publisher', 'Tidak diketahui'),
                    "published_date": book_info.get('publishedDate', 'Tidak diketahui'),
                    "page_count": book_info.get('pageCount', 0),
                    "description": book_info.get('description', 'Tidak ada deskripsi.')
                }
            return {"error": "Buku tidak ditemukan."}
        else:
            return {"error": f"Gagal mengambil data buku. Status API: {response.status_code}"}
    except Exception as e:
        return {"error": f"Terjadi kesalahan koneksi jaringan: {str(e)}"}

# 3. ROUTING WEB SERVER (Untuk Landing Page SaaS & Endpoint Lokal)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Library Book</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 text-gray-800 flex flex-col min-h-screen">
    <!-- Navbar -->
    <nav class="bg-white shadow-md p-4 flex justify-between items-center">
        <div class="text-2xl font-bold text-blue-600">📚 Library</div>
        <div class="text-sm font-semibold bg-orange-100 text-orange-600 px-3 py-1 rounded-full shadow-sm">
            Status Server: {{ env | upper }}
        </div>
    </nav>

    <!-- Main Content -->
    <main class="flex-grow container mx-auto px-4 py-12 max-w-5xl">
        <div class="text-center mb-12">
            <h1 class="text-4xl md:text-5xl font-extrabold text-gray-900 mb-6">Automasi Metadata Buku Perpustakaan Anda</h1>
            <p class="text-lg text-gray-600 max-w-2xl mx-auto">Solusi SaaS terbaik untuk perpustakaan dan toko buku. Dapatkan metadata lengkap seperti penulis, penerbit, dan sinopsis hanya dengan satu klik.</p>
        </div>

        <!-- Search Feature (Uji Coba API) -->
        <div class="bg-white p-8 rounded-2xl shadow-lg border border-gray-100 mb-16">
            <h2 class="text-2xl font-bold mb-4">Coba Fitur Tarik Data (Live API)</h2>
            <div class="flex flex-col sm:flex-row gap-3">
                <input type="text" id="searchInput" placeholder="Masukkan judul buku (Contoh: Laskar Pelangi)..." class="flex-grow p-4 bg-gray-50 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500">
                <button onclick="searchBook()" class="bg-blue-600 text-white px-8 py-4 rounded-xl hover:bg-blue-700 transition font-bold shadow-md">Cari Buku</button>
            </div>
            
            <div id="loading" class="hidden mt-6 text-center text-blue-600 font-semibold animate-pulse">Memproses permintaan ke server...</div>
            
            <div id="resultContainer" class="hidden mt-8 p-6 bg-blue-50 border border-blue-100 rounded-xl">
                <h3 id="resTitle" class="text-2xl font-bold text-gray-800 mb-4"></h3>
                <div class="grid md:grid-cols-2 gap-4">
                    <p class="text-gray-700"><strong>Penulis:</strong> <span id="resAuthors" class="text-gray-900"></span></p>
                    <p class="text-gray-700"><strong>Penerbit:</strong> <span id="resPublisher" class="text-gray-900"></span></p>
                    <p class="text-gray-700"><strong>Tahun Rilis:</strong> <span id="resDate" class="text-gray-900"></span></p>
                    <p class="text-gray-700"><strong>Jumlah Halaman:</strong> <span id="resPages" class="text-gray-900"></span> hal</p>
                </div>
                <div class="mt-4 pt-4 border-t border-blue-200">
                    <p class="text-gray-700 text-sm leading-relaxed" id="resDesc"></p>
                </div>
            </div>
            <div id="errorContainer" class="hidden mt-6 p-4 bg-red-50 text-red-700 border border-red-200 rounded-xl font-medium"></div>
        </div>

        
    </main>
    <!-- Logic untuk mengambil data dari Backend Flask kita -->
    <script>
        async function searchBook() {
            const query = document.getElementById('searchInput').value;
            if (!query) return; // Cegah pencarian kosong
            
            // Atur tampilan UI loading
            const btn = document.querySelector('button');
            btn.disabled = true;
            btn.classList.add('opacity-50');
            document.getElementById('loading').classList.remove('hidden');
            document.getElementById('resultContainer').classList.add('hidden');
            document.getElementById('errorContainer').classList.add('hidden');

            try {
                // Memanggil endpoint API lokal kita yang sudah terhubung ke Google Books
                const response = await fetch(`/api/book/${encodeURIComponent(query)}`);
                const data = await response.json();
                
                document.getElementById('loading').classList.add('hidden');
                btn.disabled = false;
                btn.classList.remove('opacity-50');

                if (data.result.error) {
                    document.getElementById('errorContainer').innerText = data.result.error;
                    document.getElementById('errorContainer').classList.remove('hidden');
                } else {
                    // Tampilkan data ke HTML
                    document.getElementById('resTitle').innerText = data.result.title;
                    document.getElementById('resAuthors').innerText = data.result.authors.join(', ');
                    document.getElementById('resPublisher').innerText = data.result.publisher;
                    document.getElementById('resDate').innerText = data.result.published_date;
                    document.getElementById('resPages').innerText = data.result.page_count;
                    document.getElementById('resDesc').innerText = data.result.description || 'Tidak ada sinopsis.';
                    document.getElementById('resultContainer').classList.remove('hidden');
                }
            } catch (err) {
                document.getElementById('loading').classList.add('hidden');
                btn.disabled = false;
                btn.classList.remove('opacity-50');
                document.getElementById('errorContainer').innerText = 'Terjadi kesalahan jaringan saat menghubungi server lokal.';
                document.getElementById('errorContainer').classList.remove('hidden');
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, env=APP_ENV)

@app.route('/api/book/<query>')
def get_book_info(query):
    # Endpoint lokal untuk layanan SaaS kita yang membungkus API eksternal
    data = fetch_book_metadata(query)
    return jsonify({
        "service": "Library Auto-Metadata",
        "environment": APP_ENV,
        "search_query": query,
        "result": data
    })

# 4. CLI (Command Line Interface) UNTUK ADMINISTRATOR SERVER
def run_cli():
    """
    Fungsi CLI untuk testing pengambilan data via terminal server.
    Sangat berguna untuk sysadmin memastikan API berjalan sebelum deploy.
    """
    parser = argparse.ArgumentParser(description="CLI Tool - Library SaaS")
    parser.add_argument('action', choices=['runserver', 'fetch'], help="Aksi: 'runserver' (jalankan web) atau 'fetch' (tarik data via CLI)")
    parser.add_argument('--query', help="Judul buku atau ISBN yang ingin dicari", default='bumi manusia')
    
    args = parser.parse_args()

    if args.action == 'fetch':
        print(f"\n[Library] Mengambil Metadata Buku via CLI ({APP_ENV} env)")
        print(f"Mencari kata kunci: '{args.query}'...\n")
        
        data = fetch_book_metadata(args.query)
        
        print("=== Hasil Data dari Google Books API ===")
        if "error" in data:
            print(f"Error: {data['error']}")
        else:
            print(f"Judul     : {data.get('title')}")
            print(f"Penulis   : {', '.join(data.get('authors', []))}")
            print(f"Penerbit  : {data.get('publisher')}")
            print(f"Tahun     : {data.get('published_date')}")
            print(f"Halaman   : {data.get('page_count')} hal")
            print(f"Sinopsis  : {data.get('description')[:150]}...") # Potong sinopsis agar rapi di terminal
        print("========================================\n")
        
    elif args.action == 'runserver':
        print(f"=== Menjalankan Library Web Server di {APP_ENV} environment ===")
        is_debug = (APP_ENV == 'development')
        app.run(host='0.0.0.0', port=5000, debug=is_debug)

if __name__ == '__main__':
    run_cli()