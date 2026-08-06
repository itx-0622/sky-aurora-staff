import os
import json
import base64
import datetime
import random
from flask import Flask, request, render_template_string, redirect, session, jsonify
import requests
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = os.urandom(24)

# ==========================================
# ⚙️ 설정 및 환경 변수
# ==========================================
CLIENT_ID = "1534184089144266872"
CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "ZfLY_vs2lo_LQVtd89ZB64jHe3dviRNm")
BASE_URL = "https://sky-aurora-staff.onrender.com"

ADMIN_SECRET_KEY = "sky_aurora_admin_secret_key_1234"
DATA_FILE = "sky_aurora_admin_data.json"
DEFAULT_ADMINS = ["1534184089144266872", "843621337066504225"]

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")

# --------------------------------------------------
# 📁 데이터 불러오기 및 영구 저장 로직
# --------------------------------------------------
def load_data():
    if GITHUB_TOKEN and GITHUB_REPO:
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
            headers = {"Authorization": f"token {GITHUB_TOKEN}"}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                content = res.json()["content"]
                decoded_data = base64.b64decode(content).decode('utf-8')
                data = json.loads(decoded_data)
                for admin_id in DEFAULT_ADMINS:
                    if admin_id not in data.get("admin_whitelist", []):
                        data.setdefault("admin_whitelist", []).append(admin_id)
                return data
        except Exception as e:
            print(f"[GitHub Sync Load Error] {e}")

    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for admin_id in DEFAULT_ADMINS:
                    if admin_id not in data.get("admin_whitelist", []):
                        data.setdefault("admin_whitelist", []).append(admin_id)
                return data
        except Exception:
            pass

    return {
        "admin_whitelist": DEFAULT_ADMINS,
        "user_whitelist": [],
        "user_blacklist": [],
        "manuals": [
            {
                "id": 1,
                "category": "보안 지침",
                "pinned": True,
                "title": "01. 기본 보안 규칙",
                "content": "본 매뉴얼 시스템에 포함된 모든 정보는 외부 유출이 엄격히 금지됩니다.\n\n1. 본 시스템 화면 캡처 및 무단 촬영 금지\n2. 계정 타인 공유 금지\n3. 접속 IP 및 접근 기록 실시간 로깅 중"
            }
        ],
        "logs": []
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if GITHUB_TOKEN and GITHUB_REPO:
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
            headers = {"Authorization": f"token {GITHUB_TOKEN}"}
            get_res = requests.get(url, headers=headers, timeout=5)
            sha = get_res.json().get("sha") if get_res.status_code == 200 else None
            
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
            encoded_content = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            
            payload = {
                "message": f"Auto-sync manual data [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]",
                "content": encoded_content
            }
            if sha:
                payload["sha"] = sha
                
            requests.put(url, headers=headers, json=payload, timeout=5)
        except Exception as e:
            print(f"[GitHub Sync Save Error] {e}")

def add_log(data, category, user_name, action, device_type="PC"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{now}] [{category}] [{device_type}] {user_name}: {action}"
    if "logs" not in data:
        data["logs"] = []
    data["logs"].insert(0, log_entry)

# --------------------------------------------------
# 🎨 프론트엔드 UI/UX
# --------------------------------------------------
MAIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, shrink-to-fit=no">
    <title>SKY AURORA STAFF MANUAL</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css">
    <style>
        @font-face {
            font-family: 'GmarketSansBold';
            src: url('https://fastly.jsdelivr.net/gh/projectnoonnu/noonfonts_2001@1.1/GmarketSansBold.woff') format('woff');
            font-weight: normal; font-style: normal;
        }
        * {
            box-sizing: border-box; margin: 0; padding: 0;
            -webkit-user-select: none !important; -moz-user-select: none !important; -ms-user-select: none !important; user-select: none !important;
            -webkit-touch-callout: none !important; -webkit-tap-highlight-color: transparent;
        }
        body {
            font-family: 'GmarketSansBold', 'Pretendard', sans-serif;
            background: #030509; color: #ffffff; overflow: hidden; height: 100vh; width: 100vw;
            display: flex; justify-content: center; align-items: center;
        }

        #security-overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: #000000;
            z-index: 99999999; display: none; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px;
        }
        .alert-icon { font-size: 80px; color: #ff2d55; margin-bottom: 20px; animation: pulse 1.2s infinite ease-in-out; }
        .alert-main-text { font-size: 24px; font-weight: bold; color: #ff2d55; margin-bottom: 12px; }
        .alert-sub-text { font-size: 14px; color: #a0aec0; font-family: 'Pretendard', sans-serif; }
        @keyframes pulse { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.15); opacity: 0.7; } 100% { transform: scale(1); opacity: 1; } }

        /* 커스텀 오로라 라이트 알림 토스트 UI */
        #custom-notification {
            position: fixed; top: 25px; right: 25px; z-index: 999999; display: flex; align-items: center; gap: 12px;
            padding: 14px 22px; background: rgba(8, 15, 30, 0.95); border: 1px solid #00ffaa;
            border-radius: 14px; box-shadow: 0 0 20px rgba(0, 255, 170, 0.4);
            transform: translateX(150%); transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            font-family: 'Pretendard', sans-serif; font-size: 14px; font-weight: 600;
        }
        #custom-notification.show { transform: translateX(0); }

        #intro-overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: #030509; z-index: 99999; display: flex; flex-direction: column;
            justify-content: center; align-items: center; opacity: 1; transition: opacity 0.8s ease;
        }
        .intro-circle-container {
            position: relative; width: 140px; height: 140px; display: flex;
            justify-content: center; align-items: center; margin-bottom: 24px;
        }
        .intro-ring {
            position: absolute; width: 100%; height: 100%; border-radius: 50%;
            border: 2px solid transparent; border-top-color: #00ffaa; border-right-color: #00f2fe;
            animation: spinRing 1s linear infinite; opacity: 0.5; transition: all 0.5s ease;
        }
        
        /* 펄스 확장 및 동적 생성 오로라 링 스타일 */
        .intro-circle-container.pulse-active {
            animation: containerPulse 1.6s ease-in-out infinite alternate;
        }
        @keyframes containerPulse {
            0% { transform: scale(0.95); }
            100% { transform: scale(1.25); }
        }

        .extra-aurora-ring {
            position: absolute; border-radius: 50%; border: 1.5px solid rgba(0, 255, 170, 0.6);
            box-shadow: 0 0 15px rgba(0, 255, 170, 0.3); pointer-events: none;
            animation: extraRingSpin 2s linear infinite;
        }
        @keyframes extraRingSpin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

        @keyframes spinRing { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .intro-avatar {
            width: 100px; height: 100px; border-radius: 50%; object-fit: cover;
            opacity: 0; transform: scale(0.6); transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
            border: 2px solid #00ffaa; box-shadow: 0 0 20px rgba(0,255,170,0.5); z-index: 2;
        }
        .intro-avatar.show { opacity: 1; transform: scale(1); }
        .intro-progress-text { font-size: 28px; color: #00ffaa; font-family: 'GmarketSansBold'; letter-spacing: 1px; }
        .intro-welcome-text { font-size: 18px; color: #ffffff; font-family: 'Pretendard'; font-weight: 600; margin-top: 16px; opacity: 0; transition: opacity 0.5s ease; text-align: center; padding: 0 20px; }
        .intro-welcome-text.show { opacity: 1; }

        #bg-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 1; }

        .container {
            position: relative; z-index: 2; width: 94%; max-width: 1280px; height: 90vh;
            background: rgba(8, 12, 24, 0.85); backdrop-filter: blur(25px); border: 1px solid rgba(0, 255, 200, 0.25);
            border-radius: 24px; box-shadow: 0 0 60px rgba(0, 255, 170, 0.12);
            display: flex; flex-direction: column; overflow: hidden; animation: containerAppear 0.8s ease;
        }
        @keyframes containerAppear { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

        header { padding: 16px 24px; background: rgba(5, 8, 18, 0.95); border-bottom: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between; align-items: center; }
        header h1 { font-size: 18px; font-weight: bold; background: linear-gradient(90deg, #00f2fe, #00ffaa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .header-controls { display: flex; align-items: center; gap: 12px; }
        .badge-admin { background: rgba(255, 45, 85, 0.2); border: 1px solid #ff2d55; color: #ff2d55; font-size: 11px; padding: 3px 8px; border-radius: 6px; font-family: 'Pretendard'; }
        .badge-staff { background: rgba(0, 255, 170, 0.2); border: 1px solid #00ffaa; color: #00ffaa; font-size: 11px; padding: 3px 8px; border-radius: 6px; font-family: 'Pretendard'; }
        .avatar-img { width: 34px; height: 34px; border-radius: 50%; border: 2px solid #00ffaa; }
        .logout-btn { font-family: 'Pretendard', sans-serif; color: #8a99ad; text-decoration: none; font-size: 12px; padding: 5px 12px; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; }
        .logout-btn:hover { color: #fff; border-color: #00ffaa; background: rgba(0, 255, 170, 0.1); }

        .login-box { padding: 50px 24px; text-align: center; margin: auto; max-width: 400px; width: 90%; background: rgba(13, 20, 38, 0.85); border: 1px solid rgba(0, 255, 170, 0.25); border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.6); }
        .discord-btn { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 14px; background: #5865F2; color: white; text-decoration: none; border-radius: 12px; font-family: 'Pretendard', sans-serif; font-weight: bold; font-size: 15px; border: none; cursor: pointer; transition: all 0.2s; }
        .discord-btn:hover { background: #4752C4; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(88, 101, 242, 0.5); }

        .dashboard { display: flex; flex: 1; overflow: hidden; }
        
        .sidebar { width: 300px; background: rgba(0, 0, 0, 0.4); border-right: 1px solid rgba(255, 255, 255, 0.08); padding: 20px 14px; overflow-y: auto; }
        .sidebar-category-title { font-size: 12px; color: #00ffaa; letter-spacing: 1px; margin: 16px 0 8px 8px; text-transform: uppercase; font-family: 'Pretendard'; font-weight: bold; }
        
        .aurora-btn-wrapper { position: relative; margin-bottom: 8px; border-radius: 12px; overflow: hidden; padding: 2px; background: rgba(255, 255, 255, 0.03); transition: all 0.25s ease; }
        .aurora-btn-wrapper.active { background: linear-gradient(90deg, #00ffaa, #00f2fe); box-shadow: 0 0 15px rgba(0, 255, 170, 0.4); }
        .item-btn { position: relative; z-index: 1; width: 100%; text-align: left; padding: 12px 14px; background: rgba(10, 16, 32, 0.95); border: none; color: #8a99ad; border-radius: 10px; cursor: pointer; font-size: 13px; font-family: 'Pretendard', sans-serif; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
        .aurora-btn-wrapper.active .item-btn { color: #ffffff; background: rgba(6, 24, 38, 0.95); font-weight: bold; }
        .pin-badge { font-size: 11px; margin-right: 4px; }

        .main-content { flex: 1; padding: 28px; overflow-y: auto; position: relative; }
        .content-card { background: rgba(5, 8, 17, 0.7); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); position: relative; }
        
        .doc-title { font-size: 20px; margin-bottom: 16px; color: #ffffff; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 12px; display: flex; align-items: center; gap: 10px; }
        .doc-title::before { content: ''; display: inline-block; width: 4px; height: 20px; background: #00ffaa; border-radius: 2px; }
        .doc-body { font-family: 'Pretendard', sans-serif; font-weight: 500; font-size: 15px; line-height: 1.85; color: #cbd5e1; white-space: pre-wrap; background: rgba(0, 0, 0, 0.3); padding: 20px; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.05); }

        input, textarea, select { width: 100%; background: rgba(3, 5, 9, 0.8); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.12); padding: 12px 14px; border-radius: 10px; margin-bottom: 12px; outline: none; font-family: 'Pretendard', sans-serif; }
        input:focus, textarea:focus, select:focus { border-color: #38bdf8; box-shadow: 0 0 12px rgba(56, 189, 248, 0.3); }
        .btn-ui { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; border: none; padding: 10px 18px; border-radius: 10px; font-weight: 700; cursor: pointer; font-family: 'Pretendard', sans-serif; transition: all 0.2s ease; }
        .btn-ui:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4); }
        .btn-danger { background: linear-gradient(135deg, #ef4444, #b91c1c); }
        .btn-secondary { background: linear-gradient(135deg, #475569, #334155); }

        ul.data-list { list-style: none; padding: 0; }
        ul.data-list li { background: rgba(10, 16, 32, 0.7); padding: 12px 14px; margin-bottom: 8px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.05); display: flex; justify-content: space-between; align-items: center; font-family: 'Pretendard', sans-serif; font-size: 14px; }

        /* 디스코드 태그 추천 팝업 UI */
        .mention-dropdown {
            position: absolute; top: 75px; left: 24px; right: 24px; z-index: 1000;
            background: rgba(15, 23, 42, 0.98); border: 1px solid #00ffaa; border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.8); display: none; max-height: 180px; overflow-y: auto;
        }
        .mention-item {
            display: flex; align-items: center; gap: 12px; padding: 10px 14px; cursor: pointer; transition: background 0.2s;
        }
        .mention-item:hover { background: rgba(0, 255, 170, 0.15); }
        .mention-avatar { width: 28px; height: 28px; border-radius: 50%; border: 1px solid #00ffaa; }

        /* 선택된 유저 프로필 태그 카운터 카드 */
        .user-profile-tag {
            display: flex; align-items: center; gap: 12px; background: rgba(0, 255, 170, 0.1);
            border: 1px solid rgba(0, 255, 170, 0.4); padding: 10px 14px; border-radius: 12px; margin-bottom: 12px;
        }
        .user-profile-tag img { width: 36px; height: 36px; border-radius: 50%; border: 1.5px solid #00ffaa; }

        .tab-enter { animation: manualEnter 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        .tab-leave { animation: manualLeave 0.25s cubic-bezier(0.7, 0, 0.84, 0) forwards; }
        @keyframes manualEnter { 0% { opacity: 0; transform: translateY(20px) scale(0.98); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
        @keyframes manualLeave { 0% { opacity: 1; transform: translateY(0) scale(1); } 100% { opacity: 0; transform: translateY(-15px) scale(0.98); } }

        @media (max-width: 768px) {
            .container { width: 100%; height: 100vh; border-radius: 0; border: none; }
            .dashboard { flex-direction: column; }
            .sidebar { width: 100%; height: 210px; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.1); padding: 12px; }
            .main-content { padding: 16px; }
            header { padding: 12px 16px; }
            header h1 { font-size: 15px; }
            .doc-title { font-size: 17px; }
            .doc-body { font-size: 14px; padding: 14px; }
        }
    </style>
    <script>
        function getDeviceType() {
            const ua = navigator.userAgent;
            if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) return "Mobile (Tablet)";
            if (/Mobile|iP(hone|od)|Android|BlackBerry|IEMobile|Kindle|Silk-Accelerated|(hpw|web)OS|Opera M(obi|ini)/i.test(ua)) return "Mobile";
            return "PC";
        }

        function notifyLog(actionName) {
            fetch('/api/log/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ action: actionName, device: getDeviceType() })
            }).catch(e => {});
        }

        document.addEventListener('contextmenu', e => e.preventDefault());
        document.addEventListener('selectstart', e => e.preventDefault());
        document.addEventListener('dragstart', e => e.preventDefault());

        function triggerSecurityLock() { const overlay = document.getElementById('security-overlay'); if (overlay) overlay.style.display = 'flex'; }
        function releaseSecurityLock() { const overlay = document.getElementById('security-overlay'); if (overlay) overlay.style.display = 'none'; }

        // 감지 및 캡처 감지 개선 (Ctrl+C, Ctrl+V, Win+Shift+S, PrintScreen 대응)
        document.addEventListener('keydown', function(e) {
            if (e.key === 'PrintScreen' || e.key === 'F12') { 
                triggerSecurityLock();
                notifyLog("화면 캡처 감지 (PrintScreen)");
            }
            if (e.shiftKey && (e.key === 'S' || e.key === 's') && (e.metaKey || e.key === 'Meta')) {
                triggerSecurityLock();
                notifyLog("캡처 도구 감지 (Win+Shift+S)");
            }
            const k = e.key.toLowerCase();
            if (e.ctrlKey || e.metaKey) {
                if (k === 'c') notifyLog("복사 감지 (Ctrl+C)");
                if (k === 'v') notifyLog("붙여넣기 감지 (Ctrl+V)");
                if (['c', 'v', 'u', 's', 'p', 'a', 'i', 'j'].includes(k)) { triggerSecurityLock(); }
            }
        }, true);

        document.addEventListener('keyup', function(e) { if (!e.shiftKey && !e.metaKey && !e.ctrlKey && !e.altKey) { releaseSecurityLock(); } });
        window.addEventListener('blur', triggerSecurityLock); window.addEventListener('focus', releaseSecurityLock);
        document.addEventListener('visibilitychange', function() { if (document.hidden) triggerSecurityLock(); else releaseSecurityLock(); });

        function showNotification(msg) {
            const toast = document.getElementById('custom-notification');
            const text = document.getElementById('custom-notification-text');
            if (toast && text) {
                text.innerText = msg;
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 3000);
            }
        }

        function login() {
            const redirectUri = encodeURIComponent("https://sky-aurora-staff.onrender.com/callback");
            location.href = `https://discord.com/oauth2/authorize?client_id={{ client_id }}&response_type=code&redirect_uri=${redirectUri}&scope=identify`;
        }
    </script>
</head>
<body>
    <div id="security-overlay">
        <div class="alert-icon">⚠️</div>
        <div class="alert-main-text">보안 경고: 무단 캡처 금지</div>
        <div class="alert-sub-text">시스템 정보의 무단 촬영 및 복제 시도는 금지되어 있습니다.</div>
    </div>

    <!-- 자체 시스템 라이트 커스텀 알림 모달 -->
    <div id="custom-notification">
        <span style="font-size:18px;">🌌</span>
        <span id="custom-notification-text">알림 메세지</span>
    </div>

    <div id="intro-overlay" style="display:none;">
        <div id="intro-container" class="intro-circle-container">
            <div id="intro-ring" class="intro-ring"></div>
            <img id="intro-avatar-img" class="intro-avatar" src="" alt="User Avatar">
        </div>
        <div id="intro-progress" class="intro-progress-text">0%</div>
        <div id="intro-welcome" class="intro-welcome-text"></div>
    </div>

    <canvas id="bg-canvas"></canvas>

    <div class="container">
        <header>
            <h1>SKY AURORA STAFF SYSTEM</h1>
            <div id="user-header-info" class="header-controls" style="display:none;">
                <span id="user-role-badge" class="badge-staff">STAFF</span>
                <img id="user-avatar" src="" alt="Avatar" class="avatar-img" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                <span id="user-name" style="font-size: 13px; color: #00ffaa; font-family: 'Pretendard'; font-weight:600;"></span>
                <a href="/logout" class="logout-btn">로그아웃</a>
            </div>
        </header>

        <div id="login-box" class="login-box">
            <h2 style="font-size: 18px; color: #e2e8f0; margin-bottom: 24px; font-family: 'GmarketSansBold';">🔒 스태프 시스템 인증</h2>
            <button onclick="login()" class="discord-btn">
                디스코드 계정으로 통합 로그인
            </button>
        </div>

        <div id="main-dashboard" class="dashboard" style="display:none;">
            <div class="sidebar">
                <div id="manual-sidebar-categorized"></div>

                <div id="admin-menu-section" style="display:none; margin-top:20px; border-top:1px solid rgba(255,255,255,0.1); padding-top:10px;">
                    <div class="sidebar-category-title" style="color:#38bdf8;">Admin Controls</div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-m-manage">
                        <button class="item-btn" onclick="switchAdminTab('m-manage')">📖 매뉴얼 등록/관리</button>
                    </div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-permissions">
                        <button class="item-btn" onclick="switchAdminTab('permissions')">🛡️ 권한 제어 센터</button>
                    </div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-logs">
                        <button class="item-btn" onclick="switchAdminTab('logs')">📜 실시간 접속 로그</button>
                    </div>
                </div>
            </div>

            <div class="main-content">
                <div id="view-manual" class="tab-enter" style="display:block;">
                    <div id="doc-title" class="doc-title">매뉴얼 선택 중...</div>
                    <div id="doc-body" class="doc-body"></div>
                </div>

                <div id="view-admin-m-manage" class="tab-enter" style="display:none;">
                    <div class="doc-title">매뉴얼 신규 등록 및 작성</div>
                    <div class="content-card">
                        <!-- 매뉴얼 선택 수정 드롭다운 추가 -->
                        <div style="margin-bottom:12px;">
                            <label style="font-size:12px; color:#00ffaa; font-family:'Pretendard'; font-weight:bold; display:block; margin-bottom:4px;">수정할 매뉴얼 선택</label>
                            <select id="m-select-edit" onchange="onManualSelectToEdit(this.value)">
                                <option value="-1">-- 새 매뉴얼 작성 --</option>
                            </select>
                        </div>
                        <div style="display:flex; gap:10px; margin-bottom:4px;">
                            <input type="text" id="m-edit-category" placeholder="주제(카테고리) 예: 운항 지침, 공통 매뉴얼" style="flex:2;">
                            <label style="display:flex; align-items:center; gap:6px; font-family:'Pretendard'; font-size:13px; color:#00ffaa; cursor:pointer; padding-bottom:12px;">
                                <input type="checkbox" id="m-edit-pinned" style="width:auto; margin:0;"> 📌 상단 고정
                            </label>
                        </div>
                        <input type="text" id="m-edit-title" placeholder="매뉴얼 제목을 입력하세요">
                        <textarea id="m-edit-content" style="height:220px;" placeholder="매뉴얼 상세 내용을 입력하세요"></textarea>
                        
                        <div style="display:flex; gap:10px;">
                            <button onclick="saveManualData()" class="btn-ui" style="flex:1;">💾 매뉴얼 저장/수정</button>
                            <button onclick="saveDraftManual()" class="btn-ui btn-secondary" style="width:120px;">📝 임시저장</button>
                            <button onclick="deleteManualData()" class="btn-ui btn-danger" style="width:90px;">🗑️ 삭제</button>
                            <button onclick="resetManualForm()" class="btn-ui btn-secondary" style="width:90px;">새로작성</button>
                        </div>
                    </div>
                </div>

                <div id="view-admin-permissions" class="tab-enter" style="display:none;">
                    <div class="doc-title">스태프 접근 권한 관리</div>
                    <div class="content-card" style="margin-bottom:20px;">
                        <div style="position:relative;">
                            <input type="text" id="perm-target-id" placeholder="대상 디스코드 ID 또는 @사용자이름 입력" style="margin-bottom:8px;" oninput="onUserIdInput(this.value)">
                            
                            <!-- @태그 자동완성 드롭다운 -->
                            <div id="mention-dropdown" class="mention-dropdown"></div>

                            <!-- 선택된 유저 프로필 카드 영역 -->
                            <div id="selected-user-card" style="display:none;" class="user-profile-tag">
                                <img id="sel-card-img" src="" alt="">
                                <div>
                                    <div id="sel-card-name" style="font-weight:bold; font-size:14px; color:#00ffaa;"></div>
                                    <div id="sel-card-id" style="font-size:11px; color:#8a99ad; font-family:monospace;"></div>
                                </div>
                            </div>

                            <div style="display:flex; align-items:center; justify-content:space-between; margin-top:8px;">
                                <label style="display:flex; align-items:center; gap:6px; font-family:'Pretendard'; font-size:13px; color:#38bdf8; cursor:pointer;">
                                    <input type="checkbox" id="perm-is-admin" style="width:auto; margin:0;"> 👑 어드민 권한도 함께 부여
                                </label>
                                <div style="display:flex; gap:10px;">
                                    <button onclick="updatePermission('whitelist', 'add')" class="btn-ui">화이트리스트 추가</button>
                                    <button onclick="updatePermission('blacklist', 'add')" class="btn-ui btn-danger">블랙리스트 차단</button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                        <div class="content-card">
                            <h3 style="color:#4ade80; margin-bottom:12px; font-size:15px;">화이트리스트 목록</h3>
                            <ul id="perm-wl-list" class="data-list"></ul>
                        </div>
                        <div class="content-card">
                            <h3 style="color:#f87171; margin-bottom:12px; font-size:15px;">블랙리스트 목록</h3>
                            <ul id="perm-bl-list" class="data-list"></ul>
                        </div>
                    </div>
                </div>

                <div id="view-admin-logs" class="tab-enter" style="display:none;">
                    <div class="doc-title">실시간 활동 로그</div>
                    <div class="content-card">
                        <div id="admin-log-box" style="background:rgba(3, 5, 9, 0.9); padding:16px; border-radius:12px; font-family:monospace; font-size:12px; height:450px; overflow-y:auto; border:1px solid rgba(255,255,255,0.05);"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const canvas = document.getElementById('bg-canvas');
        const ctx = canvas.getContext('2d');
        function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
        window.addEventListener('resize', resize); resize();
        const stars = Array.from({ length: 120 }, () => ({ x: Math.random() * canvas.width, y: Math.random() * canvas.height, size: Math.random() * 2, alpha: Math.random(), speed: Math.random() * 0.012 + 0.005 }));
        let tick = 0;
        function drawRibbonAurora(yOffset, waveHeight, color1, color2, speedMult) {
            ctx.save(); ctx.beginPath();
            const startY = yOffset + Math.sin(tick * speedMult) * 20; ctx.moveTo(0, startY);
            for (let x = 0; x <= canvas.width; x += 30) {
                const y = yOffset + Math.sin(x * 0.0025 + tick * speedMult) * waveHeight;
                ctx.lineTo(x, y);
            }
            ctx.lineTo(canvas.width, startY + 200); ctx.lineTo(0, startY + 200); ctx.closePath();
            const grad = ctx.createLinearGradient(0, yOffset - 50, canvas.width, yOffset + 200);
            grad.addColorStop(0, color1); grad.addColorStop(1, color2);
            ctx.fillStyle = grad; ctx.filter = 'blur(25px)'; ctx.fill(); ctx.restore();
        }
        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            stars.forEach(s => { s.alpha += s.speed; if (s.alpha > 1 || s.alpha < 0) s.speed = -s.speed; ctx.fillStyle = `rgba(255, 255, 255, ${Math.abs(s.alpha)})`; ctx.beginPath(); ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2); ctx.fill(); });
            tick += 0.015;
            drawRibbonAurora(canvas.height * 0.05, 65, 'rgba(0, 255, 170, 0.3)', 'rgba(0, 150, 255, 0.03)', 0.8);
            drawRibbonAurora(canvas.height * 0.12, 85, 'rgba(0, 180, 255, 0.2)', 'rgba(140, 0, 255, 0.03)', 1.1);
            requestAnimationFrame(animate);
        }
        animate();

        let appState = { user: null, role: null, manuals: [], user_whitelist: [], user_blacklist: [], logs: [] };
        let selectedManualIndex = 0;
        let currentActiveTabId = 'view-manual';
        let hasIntroRun = false;
        let selectedMentionUser = null;

        async function syncSystemState() {
            try {
                const res = await fetch('/api/state');
                if (res.status === 403) { showNotification("권한이 없거나 차단된 계정입니다."); location.reload(); return; }
                if (res.ok) {
                    const data = await res.json();
                    if (data.status === 'unauthorized') return;

                    appState = data;
                    document.getElementById('login-box').style.display = 'none';

                    const avatarUrl = data.user.avatar 
                        ? `https://cdn.discordapp.com/avatars/${data.user.id}/${data.user.avatar}.png` 
                        : 'https://cdn.discordapp.com/embed/avatars/0.png';

                    if (!hasIntroRun) {
                        hasIntroRun = true;
                        runCustomIntro(data.user.global_name || data.user.username, data.user.username, avatarUrl, () => {
                            showMainDashboard(data, avatarUrl);
                        });
                    } else {
                        showMainDashboard(data, avatarUrl);
                    }
                }
            } catch(e) { console.error("Sync error:", e); }
        }

        // 인트로 애니메이션 (랜덤 3~5초 / 오로라 링 다중 생성 연출)
        function runCustomIntro(nickname, username, avatarUrl, onComplete) {
            const introOverlay = document.getElementById('intro-overlay');
            const introContainer = document.getElementById('intro-container');
            const introProgress = document.getElementById('intro-progress');
            const introRing = document.getElementById('intro-ring');
            const introAvatar = document.getElementById('intro-avatar-img');
            const introWelcome = document.getElementById('intro-welcome');

            introAvatar.src = avatarUrl;
            introOverlay.style.display = 'flex';

            // 3초에서 5초 사이의 랜덤 로딩 타임 지정
            const totalDuration = Math.random() * (5000 - 3000) + 3000;
            const startTime = performance.now();

            function updateLoading(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(Math.floor((elapsed / totalDuration) * 100), 100);
                introProgress.innerText = `${progress}%`;

                if (progress < 100) {
                    requestAnimationFrame(updateLoading);
                } else {
                    introProgress.style.display = 'none';
                    introAvatar.classList.add('show');
                    
                    // 커지는 애니메이션 펄스 활성화
                    introContainer.classList.add('pulse-active');

                    // 커졌을 때 동적으로 여러 보조 링 생성
                    const createdRings = [];
                    for (let i = 1; i <= 3; i++) {
                        const extraRing = document.createElement('div');
                        extraRing.className = 'extra-aurora-ring';
                        extraRing.style.width = `${140 + i * 28}px`;
                        extraRing.style.height = `${140 + i * 28}px`;
                        extraRing.style.animationDuration = `${1.5 + i * 0.5}s`;
                        introContainer.appendChild(extraRing);
                        createdRings.push(extraRing);
                    }

                    introWelcome.innerText = `${nickname}(${username}) 님 환영합니다.`;
                    introWelcome.classList.add('show');

                    setTimeout(() => {
                        // 작아질 때 보조 링 제거 및 축소
                        introContainer.classList.remove('pulse-active');
                        createdRings.forEach(r => r.remove());

                        introOverlay.style.opacity = '0';
                        setTimeout(() => {
                            introOverlay.style.display = 'none';
                            onComplete();
                        }, 800);
                    }, 1800);
                }
            }
            requestAnimationFrame(updateLoading);
        }

        function showMainDashboard(data, avatarUrl) {
            document.getElementById('main-dashboard').style.display = 'flex';
            document.getElementById('user-header-info').style.display = 'flex';

            document.getElementById('user-avatar').src = avatarUrl;
            document.getElementById('user-name').innerText = `${data.user.global_name || data.user.username}`;

            const roleBadge = document.getElementById('user-role-badge');
            if (data.role === 'admin') {
                roleBadge.innerText = 'ADMIN';
                roleBadge.className = 'badge-admin';
                document.getElementById('admin-menu-section').style.display = 'block';
            } else {
                roleBadge.innerText = 'STAFF';
                roleBadge.className = 'badge-staff';
                document.getElementById('admin-menu-section').style.display = 'none';
            }

            renderCategorizedSidebar();
            renderAdminViews();
            loadDraftManual();
        }

        function renderCategorizedSidebar() {
            const container = document.getElementById('manual-sidebar-categorized');
            container.innerHTML = '';

            const editSelect = document.getElementById('m-select-edit');
            if (editSelect) editSelect.innerHTML = '<option value="-1">-- 새 매뉴얼 작성 --</option>';

            const sortedManuals = [...appState.manuals].map((m, originalIdx) => ({ ...m, originalIdx }));
            sortedManuals.sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));

            const categories = {};
            sortedManuals.forEach(item => {
                const cat = item.category || '공통 매뉴얼';
                if (!categories[cat]) categories[cat] = [];
                categories[cat].push(item);
            });

            for (const [catName, items] of Object.entries(categories)) {
                const catTitle = document.createElement('div');
                catTitle.className = 'sidebar-category-title';
                catTitle.innerText = `📂 ${catName}`;
                container.appendChild(catTitle);

                items.forEach(m => {
                    const wrapper = document.createElement('div');
                    wrapper.className = `aurora-btn-wrapper ${m.originalIdx === selectedManualIndex ? 'active' : ''}`;
                    wrapper.innerHTML = `
                        <button class="item-btn" onclick="selectManualItem(${m.originalIdx})">
                            <span>${m.pinned ? '<span class="pin-badge">📌</span>' : ''}${m.title}</span>
                        </button>
                    `;
                    container.appendChild(wrapper);

                    if (editSelect) {
                        const opt = document.createElement('option');
                        opt.value = m.originalIdx;
                        opt.innerText = `[${catName}] ${m.title}`;
                        editSelect.appendChild(opt);
                    }
                });
            }

            if (appState.manuals.length > 0) {
                const current = appState.manuals[selectedManualIndex] || appState.manuals[0];
                document.getElementById('doc-title').innerText = `${current.pinned ? '📌 ' : ''}${current.title}`;
                document.getElementById('doc-body').innerText = current.content;
            }
        }

        function selectManualItem(idx) {
            selectedManualIndex = idx;
            renderCategorizedSidebar();
            transitionToTab('view-manual');
            
            if (appState.role === 'admin') {
                const current = appState.manuals[idx];
                if (current) {
                    document.getElementById('m-select-edit').value = idx;
                    document.getElementById('m-edit-category').value = current.category || '';
                    document.getElementById('m-edit-pinned').checked = !!current.pinned;
                    document.getElementById('m-edit-title').value = current.title || '';
                    document.getElementById('m-edit-content').value = current.content || '';
                }
            }
        }

        function onManualSelectToEdit(val) {
            const idx = parseInt(val);
            if (idx === -1) {
                resetManualForm();
            } else {
                selectManualItem(idx);
            }
        }

        function transitionToTab(targetTabId) {
            if (currentActiveTabId === targetTabId) return;

            const currentTab = document.getElementById(currentActiveTabId);
            const targetTab = document.getElementById(targetTabId);

            if (currentTab) {
                currentTab.classList.remove('tab-enter');
                currentTab.classList.add('tab-leave');
                setTimeout(() => {
                    currentTab.style.display = 'none';
                    currentTab.classList.remove('tab-leave');
                    
                    targetTab.style.display = 'block';
                    targetTab.classList.add('tab-enter');
                    currentActiveTabId = targetTabId;
                }, 250);
            } else {
                targetTab.style.display = 'block';
                targetTab.classList.add('tab-enter');
                currentActiveTabId = targetTabId;
            }
        }

        function switchAdminTab(tabName) {
            document.querySelectorAll('.admin-nav').forEach(el => el.classList.remove('active'));
            const navEl = document.getElementById(`nav-${tabName}`);
            if (navEl) navEl.classList.add('active');
            
            transitionToTab(`view-admin-${tabName}`);
        }

        function renderAdminViews() {
            if (appState.role !== 'admin') return;

            const wlList = document.getElementById('perm-wl-list');
            wlList.innerHTML = appState.user_whitelist.map(id => `
                <li>
                    <span>${id}</span>
                    <button class="btn-ui btn-danger" style="padding:4px 8px; font-size:11px;" onclick="updatePermission('whitelist', 'remove', '${id}')">제거</button>
                </li>
            `).join('');

            const blList = document.getElementById('perm-bl-list');
            blList.innerHTML = appState.user_blacklist.map(id => `
                <li>
                    <span>${id}</span>
                    <button class="btn-ui btn-secondary" style="padding:4px 8px; font-size:11px;" onclick="updatePermission('blacklist', 'remove', '${id}')">해제</button>
                </li>
            `).join('');

            const logBox = document.getElementById('admin-log-box');
            logBox.innerHTML = appState.logs.map(log => `<div style="margin-bottom:6px; border-bottom:1px dashed rgba(255,255,255,0.05); padding-bottom:4px;">${log}</div>`).join('');
        }

        // 디스코드 유저 @태그 입력 처리
        function onUserIdInput(val) {
            const dropdown = document.getElementById('mention-dropdown');
            if (val.startsWith('@')) {
                const query = val.substring(1).toLowerCase();
                const sampleUsers = [
                    { id: "1534184089144266872", username: "sky_aurora_admin", nickname: "스카이 오로라 봇", avatar: "https://cdn.discordapp.com/embed/avatars/0.png" },
                    { id: "843621337066504225", username: "staff_manager", nickname: "총괄 관리자", avatar: "https://cdn.discordapp.com/embed/avatars/1.png" },
                    { id: appState.user.id, username: appState.user.username, nickname: appState.user.global_name || appState.user.username, avatar: `https://cdn.discordapp.com/avatars/${appState.user.id}/${appState.user.avatar}.png` }
                ];

                const filtered = sampleUsers.filter(u => u.username.toLowerCase().includes(query) || u.nickname.toLowerCase().includes(query));
                if (filtered.length > 0) {
                    dropdown.innerHTML = filtered.map(u => `
                        <div class="mention-item" onclick="selectMentionUser('${u.id}', '${u.nickname}', '${u.username}', '${u.avatar}')">
                            <img src="${u.avatar}" class="mention-avatar">
                            <div>
                                <div style="font-size:13px; font-weight:bold; color:#fff;">${u.nickname}</div>
                                <div style="font-size:11px; color:#8a99ad;">@${u.username} (${u.id})</div>
                            </div>
                        </div>
                    `).join('');
                    dropdown.style.display = 'block';
                } else {
                    dropdown.style.display = 'none';
                }
            } else {
                dropdown.style.display = 'none';
            }
        }

        function selectMentionUser(id, nickname, username, avatar) {
            selectedMentionUser = { id, nickname, username, avatar };
            document.getElementById('perm-target-id').value = id;
            document.getElementById('mention-dropdown').style.display = 'none';

            const card = document.getElementById('selected-user-card');
            document.getElementById('sel-card-img').src = avatar;
            document.getElementById('sel-card-name').innerText = `${nickname} (@${username})`;
            document.getElementById('sel-card-id').innerText = `ID: ${id}`;
            card.style.display = 'flex';
        }

        async function saveManualData() {
            const category = document.getElementById('m-edit-category').value.trim();
            const pinned = document.getElementById('m-edit-pinned').checked;
            const title = document.getElementById('m-edit-title').value.trim();
            const content = document.getElementById('m-edit-content').value.trim();

            if (!title || !content) return showNotification("제목과 내용을 입력해주세요.");

            const res = await fetch('/api/admin/manual', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: selectedManualIndex, category, pinned, title, content })
            });

            if (res.ok) {
                showNotification("매뉴얼이 성공적으로 저장되었습니다.");
                localStorage.removeItem('sky_manual_draft');
                syncSystemState();
            }
        }

        function saveDraftManual() {
            const draft = {
                category: document.getElementById('m-edit-category').value,
                pinned: document.getElementById('m-edit-pinned').checked,
                title: document.getElementById('m-edit-title').value,
                content: document.getElementById('m-edit-content').value
            };
            localStorage.setItem('sky_manual_draft', JSON.stringify(draft));
            showNotification("매뉴얼 임시저장이 완료되었습니다.");
        }

        function loadDraftManual() {
            const draftStr = localStorage.getItem('sky_manual_draft');
            if (draftStr) {
                try {
                    const draft = JSON.parse(draftStr);
                    if (draft.title || draft.content) {
                        document.getElementById('m-edit-category').value = draft.category || '';
                        document.getElementById('m-edit-pinned').checked = !!draft.pinned;
                        document.getElementById('m-edit-title').value = draft.title || '';
                        document.getElementById('m-edit-content').value = draft.content || '';
                        showNotification("임시 보관된 매뉴얼을 불러왔습니다.");
                    }
                } catch(e) {}
            }
        }

        async function deleteManualData() {
            if (!confirm("정말 이 매뉴얼을 삭제하시겠습니까?")) return;

            const res = await fetch('/api/admin/manual/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: selectedManualIndex })
            });

            if (res.ok) {
                showNotification("매뉴얼이 삭제되었습니다.");
                selectedManualIndex = 0;
                resetManualForm();
                syncSystemState();
            }
        }

        function resetManualForm() {
            selectedManualIndex = appState.manuals.length;
            document.getElementById('m-select-edit').value = -1;
            document.getElementById('m-edit-category').value = '';
            document.getElementById('m-edit-pinned').checked = false;
            document.getElementById('m-edit-title').value = '';
            document.getElementById('m-edit-content').value = '';
        }

        async function updatePermission(target, action, explicitId = null) {
            const userId = explicitId || document.getElementById('perm-target-id').value.trim();
            const isAdmin = document.getElementById('perm-is-admin').checked;

            if (!userId) return showNotification("디스코드 유저 ID를 입력해주세요.");

            const res = await fetch('/api/admin/permission', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target, action, user_id: userId, is_admin: isAdmin })
            });

            if (res.ok) {
                showNotification(`권한 변경 완료: ${target} (${action})`);
                if (!explicitId) {
                    document.getElementById('perm-target-id').value = '';
                    document.getElementById('selected-user-card').style.display = 'none';
                }
                syncSystemState();
            }
        }

        window.onload = syncSystemState;
    </script>
</body>
</html>
"""

# --------------------------------------------------
# 🛣️ Flask 라우트 정의 (백엔드 상호작용 강화)
# --------------------------------------------------
@app.route("/")
def index():
    return render_template_string(MAIN_HTML_TEMPLATE, client_id=CLIENT_ID)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return redirect("/")

    redirect_uri = f"{BASE_URL}/callback"
    
    token_res = requests.post("https://discord.com/api/oauth2/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})

    if token_res.status_code != 200:
        return redirect("/")

    access_token = token_res.json().get("access_token")
    user_res = requests.get("https://discord.com/api/users/@me", headers={
        "Authorization": f"Bearer {access_token}"
    })

    if user_res.status_code == 200:
        session["user"] = user_res.json()
        
        data = load_data()
        user_id = str(session["user"]["id"])
        user_name = session["user"].get("global_name") or session["user"].get("username")
        
        add_log(data, "인증", user_name, f"시스템 로그인 성공 (ID: {user_id})")
        save_data(data)

    return redirect("/")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/api/state")
def get_state():
    user = session.get("user")
    if not user:
        return jsonify({"status": "unauthorized"}), 200

    data = load_data()
    user_id = str(user.get("id"))

    if user_id in data.get("user_blacklist", []):
        session.clear()
        return jsonify({"error": "blacklisted"}), 403

    role = "guest"
    if user_id in data.get("admin_whitelist", DEFAULT_ADMINS):
        role = "admin"
    elif user_id in data.get("user_whitelist", []):
        role = "staff"
    else:
        session.clear()
        return jsonify({"error": "not_authorized"}), 403

    return jsonify({
        "user": user,
        "role": role,
        "manuals": data.get("manuals", []),
        "user_whitelist": data.get("user_whitelist", []) if role == "admin" else [],
        "user_blacklist": data.get("user_blacklist", []) if role == "admin" else [],
        "logs": data.get("logs", []) if role == "admin" else []
    })

@app.route("/api/log/action", methods=["POST"])
def log_action():
    user = session.get("user")
    if not user:
        return jsonify({"status": "ignored"}), 200

    data = load_data()
    req_data = request.json or {}
    action = req_data.get("action", "알 수 없는 행동")
    device = req_data.get("device", "PC")
    user_name = user.get("global_name") or user.get("username")

    add_log(data, "보안 감지", user_name, action, device_type=device)
    save_data(data)
    return jsonify({"status": "logged"})

@app.route("/api/admin/manual", methods=["POST"])
def admin_manual():
    user = session.get("user")
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    data = load_data()
    if str(user.get("id")) not in data.get("admin_whitelist", DEFAULT_ADMINS):
        return jsonify({"error": "forbidden"}), 403

    req_data = request.json or {}
    idx = req_data.get("index")
    category = req_data.get("category", "공통 매뉴얼")
    pinned = req_data.get("pinned", False)
    title = req_data.get("title")
    content = req_data.get("content")

    user_name = user.get("global_name") or user.get("username")
    manual_item = {
        "id": int(datetime.datetime.now().timestamp()),
        "category": category,
        "pinned": pinned,
        "title": title,
        "content": content
    }

    if idx is not None and 0 <= idx < len(data["manuals"]):
        data["manuals"][idx] = manual_item
        add_log(data, "매뉴얼 수정", user_name, f"매뉴얼 '{title}' 수정 완료")
    else:
        data["manuals"].append(manual_item)
        add_log(data, "매뉴얼 등록", user_name, f"새 매뉴얼 '{title}' 등록 완료")

    save_data(data)
    return jsonify({"status": "success"})

@app.route("/api/admin/manual/delete", methods=["POST"])
def admin_manual_delete():
    user = session.get("user")
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    data = load_data()
    if str(user.get("id")) not in data.get("admin_whitelist", DEFAULT_ADMINS):
        return jsonify({"error": "forbidden"}), 403

    idx = request.json.get("index")
    if idx is not None and 0 <= idx < len(data["manuals"]):
        deleted = data["manuals"].pop(idx)
        user_name = user.get("global_name") or user.get("username")
        add_log(data, "매뉴얼 삭제", user_name, f"매뉴얼 '{deleted.get('title')}' 삭제 완료")
        save_data(data)

    return jsonify({"status": "success"})

@app.route("/api/admin/permission", methods=["POST"])
def admin_permission():
    user = session.get("user")
    if not user:
        return jsonify({"error": "unauthorized"}), 401

    data = load_data()
    if str(user.get("id")) not in data.get("admin_whitelist", DEFAULT_ADMINS):
        return jsonify({"error": "forbidden"}), 403

    target = request.json.get("target")
    action = request.json.get("action")
    target_id = str(request.json.get("user_id"))
    is_admin = request.json.get("is_admin", False)

    user_name = user.get("global_name") or user.get("username")

    if target == "whitelist":
        if action == "add":
            if "user_whitelist" not in data: data["user_whitelist"] = []
            if target_id not in data["user_whitelist"]:
                data["user_whitelist"].append(target_id)
            
            # 블랙리스트에서 제거
            if "user_blacklist" in data and target_id in data["user_blacklist"]:
                data["user_blacklist"].remove(target_id)

            # 옵션으로 어드민 권한 부여
            if is_admin:
                if "admin_whitelist" not in data: data["admin_whitelist"] = []
                if target_id not in data["admin_whitelist"]:
                    data["admin_whitelist"].append(target_id)
                add_log(data, "권한 변경", user_name, f"ID {target_id} -> 화이트리스트 및 어드민 승격 추가")
            else:
                add_log(data, "권한 변경", user_name, f"ID {target_id} -> 화이트리스트 추가")

        elif action == "remove":
            if "user_whitelist" in data and target_id in data["user_whitelist"]:
                data["user_whitelist"].remove(target_id)
            add_log(data, "권한 변경", user_name, f"ID {target_id} -> 화이트리스트 제거")

    elif target == "blacklist":
        if action == "add":
            if "user_blacklist" not in data: data["user_blacklist"] = []
            if target_id not in data["user_blacklist"]:
                data["user_blacklist"].append(target_id)

            # 블랙리스트 등록 시 화이트리스트 및 어드민에서 유저 ID 자동 삭제
            if "user_whitelist" in data and target_id in data["user_whitelist"]:
                data["user_whitelist"].remove(target_id)
            if "admin_whitelist" in data and target_id in data["admin_whitelist"] and target_id not in DEFAULT_ADMINS:
                data["admin_whitelist"].remove(target_id)

            add_log(data, "권한 변경", user_name, f"ID {target_id} -> 블랙리스트 등록 (화이트리스트 자동 제거)")

        elif action == "remove":
            if "user_blacklist" in data and target_id in data["user_blacklist"]:
                data["user_blacklist"].remove(target_id)
            add_log(data, "권한 변경", user_name, f"ID {target_id} -> 블랙리스트 차단 해제")

    save_data(data)
    return jsonify({"status": "success"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
