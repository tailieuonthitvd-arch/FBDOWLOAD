from flask import Flask, render_template_string, request, Response, stream_with_context, url_for
import yt_dlp
import requests
import re
import unidecode
from urllib.parse import quote_plus 
import os
import tempfile
import subprocess 

app = Flask(__name__)

# ==========================================
# GIAO DIỆN MỚI (V9 - GIỮ NGUYÊN)
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi" class="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PVQ Downloader - Tự Động Ghép Video 1080p</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: { sans: ['Be Vietnam Pro', 'sans-serif'] },
                    colors: {
                        slate: { 850: '#151e2e', 900: '#0f172a', 950: '#020617' },
                        primary: { 500: '#3b82f6', 600: '#2563eb', 700: '#1d4ed8' }
                    }
                }
            }
        }
    </script>

    <style>
        .bg-grid-pattern {
            background-color: transparent;
            background-image: radial-gradient(rgba(99, 102, 241, 0.1) 1px, transparent 1px);
            background-size: 30px 30px;
        }
        .dark .bg-grid-pattern {
            background-image: radial-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px);
        }
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        .dark ::-webkit-scrollbar-thumb { background: #334155; }
        ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }
        .loader {
            border: 3px solid rgba(255,255,255,0.2); border-top: 3px solid #fff;
            border-radius: 50%; width: 20px; height: 20px;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

        /* Hiệu ứng chờ khi ghép file */
        .loading-overlay {
            position: fixed; top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.8); z-index: 9999;
            display: none; 
            flex-direction: column; align-items: center; justify-content: center;
            color: white;
        }
        .loading-overlay.active { display: flex; }
        .loading-box {
            background: #1e293b; padding: 2rem; border-radius: 1rem;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            max-width: 400px; text-align: center;
        }

        /* Thêm hiệu ứng hover cho khối tính năng */
        .feature-card:hover {
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.2); /* Bóng đổ mạnh hơn */
            transform: translateY(-5px); /* Nhấc lên 5px */
            background-color: #f0f4f8; /* Tăng độ sáng nhẹ (light mode) */
        }
        .dark .feature-card:hover {
            background-color: #1a2335; /* Tăng độ sáng nhẹ (dark mode) */
        }
        /* Đảm bảo transition mượt mà */
        .feature-card {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
    </style>

    <script>
        function initTheme() {
            if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
        }
        initTheme();

        function toggleTheme() {
            if (document.documentElement.classList.contains('dark')) {
                document.documentElement.classList.remove('dark');
                localStorage.theme = 'light';
            } else {
                document.documentElement.classList.add('dark');
                localStorage.theme = 'dark';
            }
        }

        function handleFormSubmit() {
            const btn = document.getElementById('submit-button');
            const icon = document.getElementById('btn-icon');
            const loader = document.getElementById('btn-loader');
            const text = document.getElementById('btn-text');

            if(document.querySelector('input[name="url"]').value.trim() === "") return false;

            btn.disabled = true;
            btn.classList.add('opacity-75', 'cursor-wait');
            icon.classList.add('hidden');
            loader.classList.remove('hidden');
            text.textContent = 'Đang xử lý...';
            return true;
        }
        
        async function pasteLink() {
            try {
                const text = await navigator.clipboard.readText();
                document.querySelector('input[name="url"]').value = text;
            } catch (err) { alert('Vui lòng dán thủ công (Ctrl+V)'); }
        }

        function showLoadingOverlay(resolution) {
            document.getElementById('loading-text').innerText = `Đang tự động GHÉP file ${resolution}... Quá trình này có thể mất vài phút. Vui lòng không đóng trang.`;
            document.getElementById('loading-overlay').classList.add('active');
            // Disable nút khác để tránh lỗi
            document.querySelectorAll('a').forEach(a => a.style.pointerEvents = 'none');
        }

        function handlePageTrackerSubmit() {
            const trackerUrlInput = document.getElementById('tracker-url');
            if (trackerUrlInput.value.trim() === "") {
                alert("Vui lòng nhập link Trang/Kênh cần theo dõi.");
                return false;
            }
            // Tải lại trang với tham số video_page_url
            window.location.href = "/?video_page_url=" + encodeURIComponent(trackerUrlInput.value.trim());
            return false;
        }
    </script>
</head>
<body class="bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-200 min-h-screen flex flex-col transition-colors duration-300 relative">
    
    <div class="fixed inset-0 bg-grid-pattern pointer-events-none z-0"></div>

    <div id="loading-overlay" class="loading-overlay">
        <div class="loading-box">
            <div class="loader w-12 h-12 mb-4 mx-auto !border-4"></div>
            <h2 class="text-xl font-bold mb-2">Đang xử lý Ghép Video</h2>
            <p id="loading-text" class="text-slate-400 text-sm">Quá trình này có thể mất vài phút. Vui lòng không đóng trang.</p>
        </div>
    </div>

    <header class="sticky top-0 z-50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-lg border-b border-slate-200 dark:border-slate-800 shadow-sm">
        <div class="container mx-auto px-6 h-16 flex justify-between items-center max-w-7xl">
            <a href="/" class="flex items-center gap-3">
                <div class="w-10 h-10 bg-primary-600 rounded-xl flex items-center justify-center text-white shadow-lg shadow-primary-500/30">
                    <i class="fas fa-video text-lg"></i>
                </div>
                <span class="text-xl font-bold tracking-tight text-slate-900 dark:text-white">PVQ<span class="text-primary-600">Downloader</span></span>
            </a>
            
            <button onclick="toggleTheme()" class="w-10 h-10 rounded-full border border-slate-200 dark:border-slate-700 bg-slate-100 dark:bg-slate-800 flex items-center justify-center hover:bg-slate-200 dark:hover:bg-slate-700 transition">
                <i class="fas fa-sun text-yellow-500 dark:hidden"></i>
                <i class="fas fa-moon text-blue-400 hidden dark:block"></i>
            </button>
        </div>
    </header>

    <main class="flex-grow container mx-auto px-6 py-12 relative z-10 max-w-7xl">
        
        <div class="text-center mb-12 max-w-4xl mx-auto">
            <h1 class="text-4xl md:text-5xl font-extrabold text-slate-900 dark:text-white mb-4 tracking-tight">
                Tải Video Facebook <span class="text-primary-600">Tự Động Ghép File</span>
            </h1>
            <p class="text-lg text-slate-600 dark:text-slate-400 mb-6">
                Dán link video Facebook hoặc link Trang/Kênh để xem các video mới nhất.
            </p>

            <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-800 p-2">
                <form method="POST" onsubmit="return handleFormSubmit()" class="flex flex-col md:flex-row gap-2">
                    <div class="relative flex-grow">
                        <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                            <i class="fab fa-facebook text-slate-400 text-xl"></i>
                        </div>
                        <input type="text" name="url" placeholder="Dán link video Facebook vào đây..." required
                            class="w-full h-14 pl-12 pr-4 bg-transparent text-lg text-slate-900 dark:text-white placeholder-slate-400 focus:outline-none rounded-xl">
                        <button type="button" onclick="pasteLink()" class="absolute right-2 top-2 bottom-2 px-3 text-sm font-medium text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition hidden md:block">
                            Dán
                        </button>
                    </div>
                    <button type="submit" id="submit-button" class="h-14 px-8 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-xl shadow-lg shadow-primary-600/30 transition-all flex items-center justify-center gap-2 whitespace-nowrap text-lg">
                        <div id="btn-loader" class="loader hidden"></div>
                        <i id="btn-icon" class="fas fa-search"></i>
                        <span id="btn-text">Lấy Thông Tin Video</span>
                    </button>
                </form>
            </div>
            {% if error %}
            <div class="mt-6 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl flex items-center gap-4">
                <i class="fas fa-times-circle text-red-600 text-xl flex-shrink-0"></i>
                <p class="text-sm text-red-600 dark:text-red-300"><b>Lỗi:</b> {{ error }}</p>
            </div>
            {% endif %}
        </div>

        {% if video_data %}
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-fade-in-up">
            
            <div class="lg:col-span-1 space-y-4">
                <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 overflow-hidden">
                    <div class="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                        <h3 class="font-bold text-lg text-slate-800 dark:text-white flex items-center gap-2">
                            <i class="fas fa-eye text-primary-600"></i> Xem Trước
                        </h3>
                        <span class="text-xs font-semibold px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded text-slate-500">{{ video_data.duration }}</span>
                    </div>
                    <div class="relative w-full aspect-video bg-black">
                        <video controls poster="{{ video_data.thumbnail }}" class="w-full h-full object-contain">
                            <source src="{{ video_data.preview_url }}" type="video/mp4">
                        </video>
                    </div>
                    <div class="p-4">
                        <h2 class="text-md font-bold text-slate-900 dark:text-white leading-snug line-clamp-2">{{ video_data.title }}</h2>
                        <a href="/" class="mt-4 inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 transition w-full">
                            <i class="fas fa-arrow-left mr-2"></i> Tải Video Khác
                        </a>
                    </div>
                </div>
                
                <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 p-4">
                    <h3 class="font-bold text-lg text-slate-900 dark:text-white mb-3 flex items-center gap-2">
                        <i class="fas fa-search-location text-yellow-600"></i> Kiểm Tra Bản Quyền
                    </h3>
                    <div class="grid grid-cols-2 gap-3">
                        <a href="{{ video_data.google_search_url }}" target="_blank" class="flex items-center justify-center gap-2 p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-red-500 hover:text-white transition text-sm font-medium">
                            <i class="fab fa-google"></i> Tiêu đề
                        </a>
                         <a href="{{ video_data.google_image_search_url }}" target="_blank" class="flex items-center justify-center gap-2 p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-blue-500 hover:text-white transition text-sm font-medium">
                            <i class="fas fa-image"></i> Ảnh đại diện
                        </a>
                    </div>
                </div>
            </div>

            <div class="lg:col-span-2 space-y-6">
                
                <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 p-6">
                    <h3 class="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <i class="fas fa-check-circle text-green-600"></i> Tải Nguyên Khối (Có tiếng)
                    </h3>
                    <div class="space-y-3">
                        {% for fmt in video_data.formats %}
                        <a href="{{ url_for('download_proxy', url=fmt.url, filename=video_data.title_slug + '_' + fmt.resolution.split(' ')[0] + '.mp4') }}" 
                           class="group flex items-center justify-between p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-green-500 dark:hover:border-green-500 hover:bg-green-50 dark:hover:bg-green-900/10 transition cursor-pointer relative">
                            <div class="relative flex items-center gap-4">
                                <div class="w-12 h-12 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center text-green-600 font-black text-lg">MP4</div>
                                <div>
                                    <div class="font-bold text-slate-800 dark:text-slate-100 text-lg group-hover:text-green-600 transition">{{ fmt.resolution }}</div>
                                    <div class="text-xs text-slate-500 dark:text-slate-400 font-medium">Video + Audio đã gộp (Xem ngay)</div>
                                </div>
                            </div>
                            <div class="relative w-10 h-10 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-green-500 group-hover:bg-green-600 group-hover:text-white transition">
                                <i class="fas fa-download"></i>
                            </div>
                        </a>
                        {% endfor %}
                    </div>
                </div>
                
                <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 p-6">
                    <h3 class="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <i class="fas fa-magic text-blue-600"></i> Tải & Ghép Tự Động (1080p/4K)
                    </h3>
                    
                    <div class="space-y-3">
                        {% if video_data.video_only_1080p and video_data.audio_only %}
                        <a href="{{ url_for('mux_and_stream', video_url=video_data.video_only_1080p, audio_url=video_data.audio_only, filename=video_data.title_slug + '_1080p_GHÉP.mp4', resolution='1080p') }}" 
                           onclick="showLoadingOverlay('1080p/4K')"
                           class="group flex items-center justify-between p-4 rounded-xl border border-blue-200 dark:border-blue-700 bg-blue-50 dark:bg-blue-900/10 hover:border-blue-500 hover:bg-blue-100 dark:hover:bg-blue-900/20 transition cursor-pointer relative">
                            <div class="relative flex items-center gap-4">
                                <div class="w-12 h-12 rounded-lg bg-blue-600 dark:bg-blue-600 flex items-center justify-center text-white font-black text-lg shadow-md">FHD</div>
                                <div>
                                    <div class="font-bold text-slate-800 dark:text-slate-100 text-lg group-hover:text-blue-600 transition">Video 1080p/4K (Đã Ghép)</div>
                                    <div class="text-xs text-blue-600 dark:text-blue-400 font-medium">Video + Audio gộp tự động. (Sẽ chờ lâu hơn)</div>
                                </div>
                            </div>
                            <div class="relative w-10 h-10 rounded-full bg-blue-100 dark:bg-blue-800 flex items-center justify-center text-blue-500 group-hover:bg-blue-600 group-hover:text-white transition shadow-sm">
                                <i class="fas fa-download"></i>
                            </div>
                        </a>
                        {% endif %}
                    </div>
                    
                    <div class="mt-4 p-3 bg-red-50 dark:bg-red-900/10 rounded-lg text-sm text-red-700 dark:text-red-400 border border-red-200 dark:border-red-900/30">
                        <h4 class="font-bold mb-1"><i class="fas fa-exclamation-circle mr-1"></i> Cảnh báo tốc độ:</h4>
                        <p>Quá trình **Tự động Ghép** yêu cầu tải 2 file lớn và xử lý trên máy chủ. Vui lòng **kiên nhẫn chờ đợi** cho đến khi file tự động tải về trình duyệt. **Không có thanh tiến trình** hiển thị được.</p>
                    </div>
                </div>
            </div>
        </div>
        
        {% endif %}

        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-6xl mx-auto mt-12 opacity-80">
            <div class="feature-card p-6 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm text-center">
                <div class="w-14 h-14 mx-auto bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center text-blue-600 text-2xl mb-4">
                    <i class="fas fa-bolt"></i>
                </div>
                <h3 class="font-bold text-lg text-slate-900 dark:text-white mb-2">Tốc Độ Siêu Tốc</h3>
                <p class="text-sm text-slate-500 dark:text-slate-400">Hệ thống tối ưu hóa luồng dữ liệu, tải về nhanh nhất có thể.</p>
            </div>
            <div class="feature-card p-6 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm text-center">
                <div class="w-14 h-14 mx-auto bg-green-100 dark:bg-green-900/30 rounded-full flex items-center justify-center text-green-600 text-2xl mb-4">
                    <i class="fas fa-lock"></i>
                </div>
                <h3 class="font-bold text-lg text-slate-900 dark:text-white mb-2">An Toàn Tuyệt Đối</h3>
                <p class="text-sm text-slate-500 dark:text-slate-400">Không lưu trữ link, **không lấy thông tin** người dùng.</p>
            </div>
            <div class="feature-card p-6 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm text-center">
                <div class="w-14 h-14 mx-auto bg-purple-100 dark:bg-purple-900/30 rounded-full flex items-center justify-center text-purple-600 text-2xl mb-4">
                    <i class="fas fa-mobile-alt"></i>
                </div>
                <h3 class="font-bold text-lg text-slate-900 dark:text-white mb-2">Hỗ Trợ Đa Nền Tảng</h3>
                <p class="text-sm text-slate-500 dark:text-slate-400">Tương thích hoàn hảo trên PC, Mac, iOS và Android.</p>
            </div>
        </div>

        <div class="mb-12 max-w-4xl mx-auto mt-12">
            <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 p-6">
                <h3 class="text-xl font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                    <i class="fas fa-history text-purple-600"></i> Xem Video Mới Nhất Từ Trang/Kênh
                </h3>
                <form onsubmit="return handlePageTrackerSubmit()" class="flex flex-col md:flex-row gap-2 mb-4">
                    <input type="text" id="tracker-url" placeholder="Dán link Trang Facebook/Kênh YouTube vào đây..."
                        class="w-full h-12 px-4 bg-transparent text-slate-900 dark:text-white placeholder-slate-400 border border-slate-300 dark:border-slate-700 focus:outline-none rounded-lg">
                    <button type="submit" class="h-12 px-6 bg-purple-600 hover:bg-purple-700 text-white font-bold rounded-lg transition-all flex items-center justify-center gap-2 whitespace-nowrap">
                        <i class="fas fa-link"></i> Lấy Danh Sách
                    </button>
                </form>
                
                {% if page_videos %}
                    <h4 class="font-bold text-slate-800 dark:text-white mb-3 mt-4">Video mới từ: {{ page_title }}</h4>
                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-h-96 overflow-y-auto pr-2">
                        {% for item in page_videos %}
                            <div class="flex items-start gap-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg hover:bg-primary-50 dark:hover:bg-slate-800 transition">
                                <img src="{{ item.thumbnail }}" class="w-20 h-14 object-cover rounded-md flex-shrink-0" alt="Thumbnail">
                                <div>
                                    <p class="text-sm font-semibold line-clamp-2 text-slate-900 dark:text-white">{{ item.title }}</p>
                                    <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Đăng: {{ item.upload_date }}</p>
                                    <form method="POST" class="mt-1" onsubmit="return handleFormSubmit()">
                                        <input type="hidden" name="url" value="{{ item.url }}">
                                        <button type="submit" class="text-xs text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1">
                                            <i class="fas fa-arrow-circle-down"></i> Tải ngay
                                        </button>
                                    </form>
                                </div>
                            </div>
                        {% endfor %}
                    </div>
                {% elif page_videos is not none and not page_videos %}
                    <div class="p-3 mt-4 text-center bg-yellow-50 dark:bg-yellow-900/10 rounded-lg text-sm text-yellow-700 dark:text-yellow-400">
                        <i class="fas fa-info-circle mr-1"></i> Không tìm thấy video nào gần đây từ nguồn này.
                    </div>
                {% endif %}
            </div>
        </div>

    </main>

    <footer class="mt-auto border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 py-8">
        <div class="container mx-auto px-6 text-center">
            <p class="text-slate-500 dark:text-slate-400 text-sm mb-2">© 2024 PVQ Downloader. Designed by PhanVanQuang.</p>
        </div>
    </footer>

</body>
</html>
"""

# ==========================================
# BACKEND (LOGIC) - CẬP NHẬT TIMEOUT TRONG download_proxy()
# ==========================================
def format_seconds(seconds):
    if not seconds: return "N/A"
    try:
        seconds = int(seconds)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    except: return "N/A"

def slugify(text):
    if not text: return "video_download"
    text = unidecode.unidecode(text).lower()
    return re.sub(r'[\W_]+', '_', text).strip('_')

def get_facebook_video_info(url):
    ydl_opts_merged = { 'quiet': True, 'no_warnings': True, 'format': 'best' }
    ydl_opts_adaptive = { 
        'quiet': True, 'no_warnings': True, 
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio'
    }

    video_only_1080p_url = None
    audio_only_url = None
    formats_list_merged = []

    try:
        # Lấy file gộp (SD/HD có tiếng)
        with yt_dlp.YoutubeDL(ydl_opts_merged) as ydl:
            info_merged = ydl.extract_info(url, download=False)
            
            formats_map_merged = {} 
            for f in info_merged.get('formats', []):
                if f.get('acodec') == 'none' or 'm3u8' in f.get('protocol', ''): continue
                if f.get('url') and f.get('height') and f.get('ext') == 'mp4':
                    formats_map_merged[f.get('height')] = { 'resolution': f"{f.get('height')}p", 'url': f['url'] }

            formats_list_merged = sorted(list(formats_map_merged.values()), key=lambda x: int(x['resolution'].strip('p')), reverse=True)
            
            if not formats_list_merged and info_merged.get('url'): 
                formats_list_merged.append({'resolution': 'SD (Mặc định)', 'url': info_merged.get('url')})
            
            title = info_merged.get('title', 'facebook_video')
            thumbnail = info_merged.get('thumbnail')
            duration = info_merged.get('duration')
            
            if not formats_list_merged: return {'error': "Không tìm thấy link tải video hợp lệ (hoặc video riêng tư)."}
                 
        # Lấy file riêng (Video Only 1080p+ và Audio Only)
        with yt_dlp.YoutubeDL(ydl_opts_adaptive) as ydl:
            info_adaptive = ydl.extract_info(url, download=False)
            
            video_formats = [f for f in info_adaptive.get('formats', []) if f.get('vcodec') != 'none' and f.get('acodec') == 'none']
            best_video = max(video_formats, key=lambda f: f.get('height', 0), default=None)
            
            if best_video and best_video.get('height') >= 1080:
                video_only_1080p_url = best_video['url']
            
            audio_formats = [f for f in info_adaptive.get('formats', []) if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
            best_audio = max(audio_formats, key=lambda f: f.get('abr', 0), default=None)
            if best_audio:
                audio_only_url = best_audio['url']


        return {
            'title': title, 'title_slug': slugify(title),
            'thumbnail': thumbnail, 'duration': format_seconds(duration),
            'formats': formats_list_merged, 'preview_url': formats_list_merged[-1]['url'],
            'video_only_1080p': video_only_1080p_url, 'audio_only': audio_only_url,
            'google_search_url': f"https://www.google.com/search?q={quote_plus(title)}",
            'google_image_search_url': f"https://www.google.com/searchbyimage?image_url={quote_plus(thumbnail)}"
        }
            
    except yt_dlp.utils.DownloadError:
        return {'error': "Video không tồn tại, ở chế độ Riêng tư, hoặc link không hợp lệ."}
    except Exception as e:
        print(f"Error: {e}")
        return {'error': "Lỗi hệ thống xử lý không xác định."}

def get_page_videos(page_url):
    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'extract_flat': 'in_playlist',
        'force_generic_extractor': True,
        'skip_download': True,
        'playlist_items': '1:10', # Lấy 10 video mới nhất
        'dump_single_json': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(page_url, download=False)

        if info.get('_type') == 'playlist':
            # Lấy thông tin tiêu đề trang/kênh
            page_title = info.get('title', 'Trang/Kênh Video')
            
            # Xử lý danh sách video
            entries = info.get('entries', [])
            
            videos = []
            for entry in entries:
                if entry and entry.get('url') and entry.get('title'):
                    upload_date = entry.get('upload_date', 'N/A')
                    if upload_date and upload_date != 'N/A':
                        upload_date = f"{upload_date[6:8]}/{upload_date[4:6]}/{upload_date[0:4]}"

                    videos.append({
                        'title': entry['title'],
                        'url': entry['url'],
                        'thumbnail': entry.get('thumbnail'),
                        'upload_date': upload_date
                    })
            
            return {'page_title': page_title, 'videos': videos}
        else:
            return {'page_title': 'N/A', 'videos': []} # Không phải playlist (trang/kênh)
            
    except Exception as e:
        print(f"Lỗi khi lấy danh sách video: {e}")
        return {'page_title': 'Lỗi', 'videos': None}

@app.route('/', methods=['GET', 'POST'])
def index():
    video_data = None
    error = None
    page_videos = None
    page_title = None
    
    # 1. Xử lý POST (Tải 1 video)
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            data = get_facebook_video_info(url)
            if 'error' in data: error = data['error']
            else: video_data = data
        else: error = "Vui lòng nhập đường dẫn!"
        
    # 2. Xử lý GET (Xem video mới từ Trang/Kênh)
    video_page_url = request.args.get('video_page_url')
    if video_page_url:
        page_info = get_page_videos(video_page_url)
        page_videos = page_info['videos']
        page_title = page_info['page_title']

    return render_template_string(HTML_TEMPLATE, 
                                  video_data=video_data, 
                                  error=error, 
                                  page_videos=page_videos, 
                                  page_title=page_title)

# Hàm download_proxy - ĐÃ TĂNG TIMEOUT
@app.route('/download_proxy')
def download_proxy():
    video_url = request.args.get('url')
    filename = request.args.get('filename', 'video.mp4')
    if not (filename.endswith('.mp4') or filename.endswith('.m4a')): filename += '.mp4'
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}
        # TĂNG TIMEOUT TỪ 20 LÊN 60 GIÂY
        r = requests.get(video_url, stream=True, headers=headers, timeout=60)
        r.raise_for_status()
        def generate():
            for chunk in r.iter_content(chunk_size=65536):
                if chunk: yield chunk
        content_type = r.headers.get('Content-Type')
        if not content_type: content_type = 'video/mp4' if filename.endswith('.mp4') else 'audio/m4a'
            
        resp = Response(stream_with_context(generate()), content_type=content_type)
        resp.headers['Content-Disposition'] = f"attachment; filename*=utf-8''{quote_plus(filename)}"
        return resp
    except requests.exceptions.Timeout:
        return "Lỗi tải xuống: Quá trình chuyển tiếp dữ liệu bị hết thời gian chờ (timeout). Vui lòng thử lại.", 504
    except Exception as e: 
        print(f"Proxy Download Error: {e}")
        return "Lỗi tải xuống không xác định.", 500

# Hàm mux_and_stream (Giữ nguyên)
@app.route('/mux_and_stream')
def mux_and_stream():
    video_url = request.args.get('video_url')
    audio_url = request.args.get('audio_url')
    filename = request.args.get('filename', 'merged_video.mp4')
    
    if not video_url or not audio_url:
        return "Lỗi: Thiếu URL video hoặc audio.", 400

    temp_dir = tempfile.gettempdir()
    
    video_path = os.path.join(temp_dir, os.urandom(24).hex() + '.mp4')
    audio_path = os.path.join(temp_dir, os.urandom(24).hex() + '.m4a')
    output_path = os.path.join(temp_dir, os.urandom(24).hex() + '_merged.mp4')

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        # 1. Tải Video về file tạm
        print("Bắt đầu tải Video...")
        video_response = requests.get(video_url, stream=True, headers=headers, timeout=300)
        video_response.raise_for_status()
        with open(video_path, 'wb') as f:
            for chunk in video_response.iter_content(chunk_size=8192):
                f.write(chunk)

        # 2. Tải Audio về file tạm
        print("Bắt đầu tải Audio...")
        audio_response = requests.get(audio_url, stream=True, headers=headers, timeout=300)
        audio_response.raise_for_status()
        with open(audio_path, 'wb') as f:
            for chunk in audio_response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        # 3. Sử dụng FFmpeg để ghép (Remuxing)
        print("Bắt đầu ghép file bằng FFmpeg...")
        command = [
            'ffmpeg',
            '-i', video_path,
            '-i', audio_path,
            '-c', 'copy',
            '-y', 
            output_path
        ]
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=600)
        
        if result.returncode != 0:
            print(f"Lỗi FFmpeg: {result.stderr}")
            return f"Lỗi ghép file: FFmpeg thất bại. Lỗi: {result.stderr}", 500
        
        print("Ghép file thành công.")

        # 4. Truyền tải file đã ghép về trình duyệt
        def stream_file():
            with open(output_path, 'rb') as f:
                chunk = f.read(8192)
                while chunk:
                    yield chunk
                    chunk = f.read(8192)
            # 5. Dọn dẹp file tạm sau khi truyền tải
            os.remove(video_path)
            os.remove(audio_path)
            os.remove(output_path)
            print("Đã dọn dẹp file tạm.")

        resp = Response(stream_with_context(stream_file()), content_type='video/mp4')
        resp.headers['Content-Disposition'] = f"attachment; filename*=utf-8''{quote_plus(filename)}"
        return resp

    except FileNotFoundError:
        return "Lỗi: Không tìm thấy lệnh FFmpeg trên máy chủ. Vui lòng cài đặt FFmpeg.", 500
    except requests.exceptions.RequestException as e:
        return f"Lỗi tải file nguồn: {e}", 500
    except subprocess.TimeoutExpired:
        return "Lỗi: Quá trình ghép file đã hết thời gian chờ (Timeout). Thử lại với video ngắn hơn.", 500
    except Exception as e:
        return f"Lỗi hệ thống không xác định: {e}", 500
    finally:
        if os.path.exists(video_path): os.remove(video_path)
        if os.path.exists(audio_path): os.remove(audio_path)
        if os.path.exists(output_path): os.remove(output_path)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
