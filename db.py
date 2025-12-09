from flask import Flask, render_template_string, request, Response, stream_with_context, url_for
import yt_dlp
import requests
import re
import unidecode
from urllib.parse import quote_plus 

app = Flask(__name__)

# ==========================================
# PHẦN GIAO DIỆN (HTML + TAILWIND CSS) ĐÃ ĐƯỢC CHUYỂN SANG BỐ CỤC ĐA CỘT
# ==========================================
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PVQ Downloader - Tải Video Facebook</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
        body { font-family: 'Inter', sans-serif; transition: background-color 0.3s, color 0.3s; }
        
        /* Dark Mode Styles */
        .dark .bg-gradient-to-br { background-image: linear-gradient(to bottom right, #1f2937, #111827); }
        .dark .bg-white { background-color: #374151; color: #f9fafb; }
        .dark .shadow-xl, .dark .shadow-2xl { box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5), 0 4px 6px -2px rgba(0, 0, 0, 0.2); }
        .dark .border-gray-300 { border-color: #4b5563; }
        .dark .text-gray-800 { color: #f9fafb; }
        .dark .text-gray-500, .dark .text-gray-600 { color: #d1d5db; }
        .dark input { background-color: #4b5563; color: #f9fafb; border-color: #4b5563; }
        .dark input:focus { background-color: #374151; }
        .dark .border-t { border-color: #4b5563; }
        .dark .bg-blue-100 { background-color: #366099; color: #bfdbfe; }
        .dark .bg-red-100 { background-color: #493035; color: #fca5a5; }
        
        /* Video Player Styling */
        .video-container { position: relative; width: 100%; padding-bottom: 56.25%; /* 16:9 Aspect Ratio */ height: 0; overflow: hidden; border-radius: 0.5rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1); }
        .video-container video { position: absolute; top: 0; left: 0; width: 100%; height: 100%; }

        .loader {
            border: 4px solid #f3f3f3; border-top: 4px solid #3b82f6; border-radius: 50%;
            width: 24px; height: 24px; animation: spin 1s linear infinite; display: none;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
    <script>
        // JS cho Dark Mode
        if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }

        function toggleDarkMode() {
            if (document.documentElement.classList.contains('dark')) {
                document.documentElement.classList.remove('dark');
                localStorage.theme = 'light';
            } else {
                document.documentElement.classList.add('dark');
                localStorage.theme = 'dark';
            }
        }
        
        function copyTitle() {
            const titleElement = document.getElementById('videoTitle');
            if (titleElement) {
                const titleText = titleElement.innerText || titleElement.textContent;
                navigator.clipboard.writeText(titleText).then(() => {
                    alert('Đã sao chép tiêu đề: "' + titleText + '"');
                }).catch(err => {
                    console.error('Không thể sao chép: ', err);
                    alert('Lỗi: Không thể sao chép tiêu đề. Vui lòng thử thủ công.');
                });
            }
        }
    </script>
</head>
<body class="bg-gradient-to-br from-gray-100 to-blue-50 dark:from-gray-900 dark:to-gray-800 min-h-screen flex flex-col justify-between">

    <div class="w-full bg-white dark:bg-gray-800 shadow-lg py-4 border-b border-gray-200 dark:border-gray-700">
        <div class="container mx-auto px-4 flex justify-between items-center">
            <h1 class="text-3xl font-extrabold text-blue-600 dark:text-blue-400 tracking-tight flex items-center">
                <i class="fab fa-facebook-square text-4xl mr-3"></i>PVQ Downloader
            </h1>
            <div class="flex items-center space-x-4">
                 <button onclick="toggleDarkMode()" class="p-2 rounded-full text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition duration-200" title="Chuyển đổi Chế độ Nền Tối">
                    <i class="fas fa-moon text-xl dark:hidden"></i>
                    <i class="fas fa-sun text-xl hidden dark:inline"></i>
                </button>
                <span class="text-sm text-gray-500 dark:text-gray-400 font-semibold hidden sm:block">Admin: PhanVanQuang</span>
            </div>
        </div>
    </div>
    <div class="container mx-auto px-4 flex-grow flex flex-col justify-center items-center py-10">
        
        <div class="w-full max-w-2xl lg:max-w-4xl text-center mb-10">
            <h2 class="text-4xl font-extrabold text-gray-800 dark:text-white">Công Cụ Tải Video Facebook</h2>
            <p class="text-gray-500 dark:text-gray-400 mt-3">Tải video từ Facebook với chất lượng cao nhất và kiểm tra bản quyền.</p>
        </div>

        <div class="bg-white dark:bg-gray-700 p-8 rounded-2xl shadow-2xl w-full max-w-2xl lg:max-w-4xl transition-all duration-300">
            <h3 class="text-center text-gray-800 dark:text-white text-2xl font-bold mb-6 flex items-center justify-center">
                <i class="fas fa-paste text-blue-600 mr-2"></i> Dán Link Video Facebook
            </h3>
            
            <form method="POST" onsubmit="document.getElementById('loading').style.display='inline-block'">
                <div class="relative">
                    <input type="text" name="url" placeholder="https://www.facebook.com/..." required
                        class="w-full pl-4 pr-12 py-3 border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white rounded-lg focus:outline-none focus:ring-4 focus:ring-blue-500/50 transition shadow-inner">
                    <i class="fas fa-link absolute right-4 top-4 text-gray-400 dark:text-gray-500"></i>
                </div>
                
                <button type="submit" class="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 rounded-lg shadow-xl shadow-blue-500/50 transition duration-200 flex justify-center items-center gap-2">
                    <div id="loading" class="loader"></div>
                    <span>Lấy Link Tải</span>
                </button>
            </form>

            {% if error %}
            <div class="mt-4 p-4 bg-red-100 dark:bg-red-900/50 text-red-700 dark:text-red-300 rounded-lg text-sm font-medium flex items-center border border-red-300 dark:border-red-700">
                <i class="fas fa-exclamation-circle mr-3 text-lg"></i> 
                <div>
                    <span class="font-bold">Lỗi:</span> {{ error }}
                </div>
            </div>
            {% endif %}
        </div>
        {% if video_data %}
        <div class="w-full max-w-2xl lg:max-w-4xl mt-8">
            <div class="p-4 mb-4 bg-green-100 dark:bg-green-900/50 text-green-700 dark:text-green-300 rounded-lg text-md font-semibold flex items-center border border-green-300 dark:border-green-700 shadow-md">
                <i class="fas fa-check-circle mr-3 text-2xl text-green-500"></i> 
                Tìm kiếm thông tin thành công! Sẵn sàng để xem và tải về.
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
                
                <div class="bg-white dark:bg-gray-700 p-6 rounded-2xl shadow-2xl border-t-4 border-blue-500 dark:border-blue-400">
                    <h3 class="font-extrabold text-xl text-gray-800 dark:text-white mb-4 flex items-center">
                        <i class="fas fa-play-circle text-blue-600 mr-2"></i> Xem Trước Video
                    </h3>
                    <div class="video-container">
                        <video controls poster="{{ video_data.thumbnail }}"
                               class="w-full h-full rounded-lg" preload="none">
                            <source src="{{ video_data.preview_url }}" type="video/mp4">
                            Trình duyệt của bạn không hỗ trợ thẻ video.
                        </video>
                    </div>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-3 text-center">Video xem trước thường là chất lượng thấp (360p/480p).</p>
                </div>

                <div class="bg-white dark:bg-gray-700 p-6 rounded-2xl shadow-2xl border-t-4 border-green-500 dark:border-green-400">
                    <h3 class="font-extrabold text-xl text-gray-800 dark:text-white mb-4 flex items-center">
                        <i class="fas fa-info-circle text-green-600 mr-2"></i> Thông tin & Tùy chọn Tải
                    </h3>
                    
                    <div class="flex items-start gap-3 border-b pb-4 mb-4 border-gray-200 dark:border-gray-600">
                        <img src="{{ video_data.thumbnail }}" alt="Thumb" class="w-16 h-16 object-cover rounded-lg shadow-md flex-shrink-0">
                        <div class="flex-1">
                            <div class="flex items-start justify-between">
                                <h4 class="font-bold text-gray-800 dark:text-white text-md line-clamp-2" id="videoTitle">{{ video_data.title }}</h4>
                                <button onclick="copyTitle()" title="Sao chép tiêu đề" 
                                        class="flex-shrink-0 text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-semibold p-1 rounded transition duration-150">
                                    <i class="fas fa-copy mr-1"></i> Sao chép
                                </button>
                            </div>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Thời lượng: **{{ video_data.duration }}**</p>
                        </div>
                    </div>
                    
                    <h4 class="text-md font-bold text-gray-700 dark:text-gray-300 mb-3 uppercase tracking-wider">Chọn Độ Phân Giải:</h4>
                    <div class="space-y-2 max-h-64 overflow-y-auto pr-2">
                        {% for fmt in video_data.formats %}
                        <a href="{{ url_for('download_proxy', url=fmt.url, filename=video_data.title_slug + '_' + fmt.resolution.split(' ')[0] + '.mp4') }}" 
                           class="block w-full text-center py-2 px-4 border-2 border-blue-600 text-blue-600 dark:text-blue-400 dark:border-blue-400 rounded-lg hover:bg-blue-600 hover:text-white dark:hover:bg-blue-600 dark:hover:text-white transition font-bold flex justify-between items-center group shadow-sm hover:shadow-lg">
                            <span><i class="fas fa-video mr-2"></i> **{{ fmt.resolution }}**</span>
                            <span class="text-xs bg-blue-100 text-blue-800 dark:bg-blue-800 dark:text-blue-200 px-3 py-1 rounded-full group-hover:bg-white group-hover:text-blue-600 dark:group-hover:bg-gray-800 dark:group-hover:text-blue-400">Tải ngay <i class="fas fa-download ml-1"></i></span>
                        </a>
                        {% endfor %}
                    </div>
                </div>
            </div>
            
            <div class="w-full mt-6">
                <div class="bg-white dark:bg-gray-700 p-6 rounded-2xl shadow-2xl border-t-4 border-yellow-500 dark:border-yellow-400">
                    <h4 class="text-xl font-extrabold text-gray-700 dark:text-white mb-4 flex items-center">
                        <i class="fas fa-shield-alt text-yellow-600 mr-2"></i> Kiểm Tra Bản Sao / Bản Quyền
                    </h4>
                    
                    <p class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">1. Tìm kiếm bằng Tiêu đề video:</p>
                    <div class="grid grid-cols-3 gap-3 mb-5">
                        <a href="{{ video_data.google_search_url }}" target="_blank"
                           class="flex items-center justify-center p-3 bg-red-500 hover:bg-red-600 text-white font-medium rounded-lg transition shadow-md">
                            <i class="fab fa-google mr-1"></i> Google
                        </a>
                        
                        <a href="{{ video_data.youtube_search_url }}" target="_blank"
                           class="flex items-center justify-center p-3 bg-red-700 hover:bg-red-800 text-white font-medium rounded-lg transition shadow-md">
                            <i class="fab fa-youtube mr-1"></i> YouTube
                        </a>
                        
                        <a href="{{ video_data.tiktok_search_url }}" target="_blank"
                           class="flex items-center justify-center p-3 bg-black hover:bg-gray-800 text-white font-medium rounded-lg transition shadow-md">
                            <i class="fab fa-tiktok mr-1"></i> TikTok
                        </a>
                    </div>

                    <p class="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 border-t border-gray-200 dark:border-gray-600 pt-4">2. Tìm kiếm bằng Hình ảnh (Thumbnail):</p>
                    <a href="{{ video_data.google_image_search_url }}" target="_blank"
                       class="flex items-center justify-center p-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg transition shadow-xl shadow-blue-500/40">
                        <i class="fas fa-image mr-2"></i> Tìm kiếm bằng Hình ảnh trên Google
                    </a>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-2">Dùng ảnh đại diện (thumbnail) để dò tìm các bản sao trên Internet.</p>
                </div>
            </div>
        </div>
        {% endif %}

        <div class="bg-white dark:bg-gray-700 p-6 rounded-2xl shadow-xl w-full max-w-2xl lg:max-w-4xl mt-8">
            <h3 class="text-xl font-bold text-gray-700 dark:text-white mb-4 border-b pb-2 flex items-center">
                <i class="fas fa-info-circle text-blue-600 mr-2"></i> Hướng Dẫn Nhanh
            </h3>
            <ol class="space-y-3 text-left text-gray-700 dark:text-gray-300">
                <li class="flex items-start">
                    <span class="text-xl font-bold text-blue-600 mr-3 flex-shrink-0">1.</span>
                    <div>
                        <span class="font-bold">Lấy Link Video:</span>
                        <p class="text-sm text-gray-600 dark:text-gray-400">Sao chép liên kết của video **công khai** (Public) trên Facebook.</p>
                    </div>
                </li>
                <li class="flex items-start">
                    <span class="text-xl font-bold text-blue-600 mr-3 flex-shrink-0">2.</span>
                    <div>
                        <span class="font-bold">Dán và Xử Lý:</span>
                        <p class="text-sm text-gray-600 dark:text-gray-400">Dán link vào ô trên và nhấn **Lấy Link Tải**.</p>
                    </div>
                </li>
                <li class="flex items-start">
                    <span class="text-xl font-bold text-blue-600 mr-3 flex-shrink-0">3.</span>
                    <div>
                        <span class="font-bold">Tải Về:</span>
                        <p class="text-sm text-gray-600 dark:text-gray-400">Chọn độ phân giải mong muốn và nhấn nút **Tải ngay**.</p>
                    </div>
                </li>
            </ol>
            <p class="text-xs text-red-500 mt-4 pt-4 border-t border-gray-100 dark:border-gray-600"><i class="fas fa-exclamation-triangle mr-1"></i> Lưu ý: Chỉ hoạt động với video công khai. Để tải 1080p, cần có FFmpeg trên máy chủ.</p>
        </div>
    </div>

    <footer class="w-full bg-gray-800 dark:bg-gray-900 text-white py-6 mt-auto border-t border-gray-700">
        <div class="container mx-auto text-center">
            <p class="font-bold text-lg">Phát triển bởi Admin PhanVanQuang</p>
            <p class="text-gray-400 text-sm mt-1">© 2024 PVQ Studio. All rights reserved.</p>
        </div>
    </footer>
    <script>
        function copyTitle() {
            const titleElement = document.getElementById('videoTitle');
            if (titleElement) {
                const titleText = titleElement.innerText || titleElement.textContent;
                navigator.clipboard.writeText(titleText).then(() => {
                    alert('Đã sao chép tiêu đề: "' + titleText + '"');
                }).catch(err => {
                    console.error('Không thể sao chép: ', err);
                    alert('Lỗi: Không thể sao chép tiêu đề. Vui lòng thử thủ công.');
                });
            }
        }
    </script>
    </body>
</html>
"""

# ==========================================
# PHẦN BACKEND (LOGIC) - KHÔNG ĐỔI
# ==========================================

def format_seconds(seconds):
    if not seconds: return "N/A"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{int(h)}:{int(m):02d}:{int(s):02d}"
    return f"{int(m):02d}:{int(s):02d}"

def slugify(text):
    text = unidecode.unidecode(text).lower()
    return re.sub(r'[\W_]+', '_', text)

def get_facebook_video_info(url):
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'bestvideo*+bestaudio/best', 
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats_list = []
            seen_res = set() 
            
            for f in info.get('formats', []):
                if f.get('url') and f.get('height'):
                    if f.get('vcodec') != 'none':
                        resolution = f"{f.get('height')}p"
                        
                        if f.get('ext') and f.get('ext') != 'mp4': 
                            resolution += f" ({f.get('ext')})"
                        
                        if f.get('format_id') == 'best':
                            resolution = f"Best Quality - {resolution}"
                            
                        if resolution not in seen_res:
                            formats_list.append({
                                'resolution': resolution,
                                'url': f['url']
                            })
                            seen_res.add(resolution)
            
            formats_list.sort(key=lambda x: int(x['resolution'].split('p')[0].split(' ')[-1]) if x['resolution'].split('p')[0].split(' ')[-1].isdigit() else 0, reverse=True)


            title = info.get('title', 'facebook_video')
            
            # Lấy URL xem trước (URL chất lượng thấp nhất/đầu tiên)
            preview_url = formats_list[-1]['url'] if formats_list else None 
            
            return {
                'title': title,
                'title_slug': slugify(title),
                'thumbnail': info.get('thumbnail'),
                'duration': format_seconds(info.get('duration')),
                'formats': formats_list,
                'preview_url': preview_url 
            }
    except Exception as e:
        print(f"Lỗi khi xử lý yt-dlp: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index():
    video_data = None
    error = None
    if request.method == 'POST':
        url = request.form.get('url')
        if url:
            data = get_facebook_video_info(url)
            if data and data['formats']:
                video_data = data
                
                # Tạo URL tìm kiếm
                search_query = data['title']
                video_data['google_search_url'] = f"https://www.google.com/search?q={quote_plus(search_query)}"
                video_data['youtube_search_url'] = f"https://www.youtube.com/results?search_query={quote_plus(search_query)}"
                video_data['tiktok_search_url'] = f"https://www.tiktok.com/search?q={quote_plus(search_query)}" 
                
                # Tạo URL tìm kiếm bằng hình ảnh
                thumbnail_url = data['thumbnail']
                video_data['google_image_search_url'] = f"https://www.google.com/searchbyimage?image_url={quote_plus(thumbnail_url)}"

            else:
                error = "Không tìm thấy video hoặc Link riêng tư. Vui lòng đảm bảo video Public và bạn đã cài đặt FFmpeg."
        else:
            error = "Vui lòng nhập đường dẫn!"
    
    return render_template_string(HTML_TEMPLATE, video_data=video_data, error=error)

@app.route('/download_proxy')
def download_proxy():
    video_url = request.args.get('url')
    filename_raw = request.args.get('filename', 'facebook_video.mp4')
    
    if not filename_raw.lower().endswith('.mp4'):
        filename = f"{filename_raw}.mp4"
    else:
        filename = filename_raw
    
    if not video_url:
        return "URL video không hợp lệ", 400

    try:
        r = requests.get(video_url, stream=True, allow_redirects=True)
        r.raise_for_status() 

        def generate():
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk

        response = Response(stream_with_context(generate()), content_type=r.headers.get('content-type', 'video/mp4'))
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        response.headers['Content-Length'] = r.headers.get('Content-Length')
        
        return response

    except requests.exceptions.RequestException as e:
        print(f"Lỗi Proxy Download: {e}")
        return "Không thể kết nối đến nguồn video. Có thể link đã hết hạn hoặc bị chặn.", 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)