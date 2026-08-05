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
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(24))

# ==========================================
# ⚙️ 설정 및 환경 변수
# ==========================================
CLIENT_ID = os.environ.get("DISCORD_CLIENT_ID", "1534184089144266872")
CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "JcMp7ntF3Rx32ZYTRjyaYUWfmp0EU3co")
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "") # 사용자 조회를 위한 Bot Token (선택사항)

ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "sky_aurora_admin_secret_key_1234")
DATA_FILE = "sky_aurora_admin_data.json"
DEFAULT_ADMINS = ["1534184089144266872", "843621337066504225"]

# GitHub 영구 저장 환경변수
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")

# --------------------------------------------------
# 📁 데이터 불러오기 및 영구 저장 로직
# --------------------------------------------------
def load_data():
    data = None
    if GITHUB_TOKEN and GITHUB_REPO:
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
            headers = {"Authorization": f"token {GITHUB_TOKEN}"}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                content = res.json()["content"]
                decoded_data = base64.b64decode(content).decode('utf-8')
                data = json.loads(decoded_data)
        except Exception as e:
            print(f"[GitHub Sync Load Error] {e}")

    if not data and os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            pass

    if not data:
        data = {
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

    for admin_id in DEFAULT_ADMINS:
        if admin_id not in data.get("admin_whitelist", []):
            data.setdefault("admin_whitelist", []).append(admin_id)

    return data

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

def add_log(data, category, user_name, action):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{now}] [{category}] {user_name}: {action}"
    if "logs" not in data:
        data["logs"] = []
    data["logs"].insert(0, log_entry)

# --------------------------------------------------
# 🎨 프론트엔드 UI/UX HTML
# --------------------------------------------------
MAIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
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
            -webkit-user-select: none !important; user-select: none !important;
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

        #intro-overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: #030509; z-index: 99999; display: flex; flex-direction: column;
            justify-content: center; align-items: center; opacity: 1; transition: opacity 0.8s ease;
        }
        .intro-circle-container { position: relative; width: 140px; height: 140px; display: flex; justify-content: center; align-items: center; margin-bottom: 24px; }
        .intro-ring {
            position: absolute; width: 100%; height: 100%; border-radius: 50%;
            border: 2px solid transparent; border-top-color: #00ffaa; border-right-color: #00f2fe;
            animation: spinRing 1s linear infinite; opacity: 0.5; transition: all 0.5s ease;
        }
        .intro-ring.expand { transform: scale(1.3); border-width: 4px; border-color: #00ffaa; box-shadow: 0 0 25px #00ffaa, inset 0 0 15px #00ffaa; opacity: 1; }
        @keyframes spinRing { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        
        .intro-avatar {
            width: 100px; height: 100px; border-radius: 50%; object-fit: cover;
            opacity: 0; transform: scale(0.6); transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
            border: 2px solid #00ffaa; box-shadow: 0 0 20px rgba(0,255,170,0.5);
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

        .login-box { padding: 50px 24px; text-align: center; margin: auto; max-width: 420px; width: 90%; background: rgba(13, 20, 38, 0.85); border: 1px solid rgba(0, 255, 170, 0.25); border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.6); }
        .discord-btn { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 14px; background: #5865F2; color: white; text-decoration: none; border-radius: 12px; font-family: 'Pretendard', sans-serif; font-weight: bold; font-size: 15px; border: none; cursor: pointer; transition: all 0.2s; }
        .discord-btn:hover { background: #4752C4; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(88, 101, 242, 0.5); }

        .access-denied-card { background: rgba(255, 45, 85, 0.1); border: 1px solid #ff2d55; padding: 30px; border-radius: 16px; text-align: center; }
        .access-denied-title { font-size: 20px; color: #ff2d55; margin-bottom: 10px; font-family: 'GmarketSansBold'; }

        .dashboard { display: flex; flex: 1; overflow: hidden; }
        .sidebar { width: 300px; background: rgba(0, 0, 0, 0.4); border-right: 1px solid rgba(255, 255, 255, 0.08); padding: 20px 14px; overflow-y: auto; }
        .sidebar-category-title { font-size: 12px; color: #00ffaa; letter-spacing: 1px; margin: 16px 0 8px 8px; text-transform: uppercase; font-family: 'Pretendard'; font-weight: bold; }
        
        .aurora-btn-wrapper { position: relative; margin-bottom: 8px; border-radius: 12px; overflow: hidden; padding: 2px; background: rgba(255, 255, 255, 0.03); transition: all 0.25s ease; }
        .aurora-btn-wrapper.active { background: linear-gradient(90deg, #00ffaa, #00f2fe); box-shadow: 0 0 15px rgba(0, 255, 170, 0.4); }
        .item-btn { position: relative; z-index: 1; width: 100%; text-align: left; padding: 12px 14px; background: rgba(10, 16, 32, 0.95); border: none; color: #8a99ad; border-radius: 10px; cursor: pointer; font-size: 13px; font-family: 'Pretendard', sans-serif; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
        .aurora-btn-wrapper.active .item-btn { color: #ffffff; background: rgba(6, 24, 38, 0.95); font-weight: bold; }
        .pin-badge { font-size: 11px; margin-right: 4px; }

        .main-content { flex: 1; padding: 28px; overflow-y: auto; position: relative; }
        .content-card { background: rgba(5, 8, 17, 0.7); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        
        .doc-title { font-size: 20px; margin-bottom: 16px; color: #ffffff; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 12px; display: flex; align-items: center; gap: 10px; }
        .doc-title::before { content: ''; display: inline-block; width: 4px; height: 20px; background: #00ffaa; border-radius: 2px; }
        .doc-body { font-family: 'Pretendard', sans-serif; font-weight: 500; font-size: 15px; line-height: 1.85; color: #cbd5e1; white-space: pre-wrap; background: rgba(0, 0, 0, 0.3); padding: 20px; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.05); }

        input, textarea, select { width: 100%; background: rgba(3, 5, 9, 0.8); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.12); padding: 12px 14px; border-radius: 10px; margin-bottom: 12px; outline: none; font-family: 'Pretendard', sans-serif; }
        input:focus, textarea:focus, select:focus { border-color: #00ffaa; box-shadow: 0 0 12px rgba(0, 255, 170, 0.3); }
        .btn-ui { background: linear-gradient(135deg, #00f2fe, #00ffaa); color: #030509; border: none; padding: 10px 18px; border-radius: 10px; font-weight: 700; cursor: pointer; font-family: 'Pretendard', sans-serif; transition: all 0.2s ease; }
        .btn-ui:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(0, 255, 170, 0.4); }
        .btn-danger { background: linear-gradient(135deg, #ef4444, #b91c1c); color: white; }
        .btn-secondary { background: linear-gradient(135deg, #475569, #334155); color: white; }

        ul.data-list { list-style: none; padding: 0; }
        ul.data-list li { background: rgba(10, 16, 32, 0.7); padding: 12px 14px; margin-bottom: 8px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.05); display: flex; justify-content: space-between; align-items: center; font-family: 'Pretendard', sans-serif; font-size: 14px; }

        .tab-enter { animation: manualEnter 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        .tab-leave { animation: manualLeave 0.25s cubic-bezier(0.7, 0, 0.84, 0) forwards; }
        @keyframes manualEnter { 0% { opacity: 0; transform: translateY(20px) scale(0.98); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
        @keyframes manualLeave { 0% { opacity: 1; transform: translateY(0) scale(1); } 100% { opacity: 0; transform: translateY(-15px) scale(0.98); } }

        .user-preview-card {
            display: flex; align-items: center; gap: 14px; background: rgba(0, 255, 170, 0.05);
            border: 1px solid rgba(0, 255, 170, 0.2); padding: 12px 16px; border-radius: 12px; margin-bottom: 14px;
        }
        .user-preview-avatar { width: 48px; height: 48px; border-radius: 50%; border: 2px solid #00ffaa; }

        @media (max-width: 768px) {
            .container { width: 100%; height: 100vh; border-radius: 0; border: none; }
            .dashboard { flex-direction: column; }
            .sidebar { width: 100%; height: 210px; border-right: none; border-bottom: 1px solid rgba(255,255,255,0.1); padding: 12px; }
            .main-content { padding: 16px; }
            header { padding: 12px 16px; }
            header h1 { font-size: 15px; }
        }
    </style>
    <script>
        document.addEventListener('contextmenu', e => e.preventDefault());
        document.addEventListener('selectstart', e => e.preventDefault());
        document.addEventListener('dragstart', e => e.preventDefault());

        function triggerSecurityLock() { const overlay = document.getElementById('security-overlay'); if (overlay) overlay.style.display = 'flex'; }
        function releaseSecurityLock() { const overlay = document.getElementById('security-overlay'); if (overlay) overlay.style.display = 'none'; }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Shift' || e.key === 'Meta' || e.key === 'Alt' || e.key === 'Control' || e.key === 'PrintScreen' || e.key === 'F12') { triggerSecurityLock(); }
            const k = e.key.toLowerCase();
            if ((e.ctrlKey && ['c', 'v', 'u', 's', 'p', 'a', 'i', 'j'].includes(k)) || (e.metaKey && ['c', 'v', 'u', 's', 'p', 'a', 'i', 'j'].includes(k))) { triggerSecurityLock(); }
        }, true);

        document.addEventListener('keyup', function(e) { if (!e.shiftKey && !e.metaKey && !e.ctrlKey && !e.altKey) { releaseSecurityLock(); } });
        window.addEventListener('blur', triggerSecurityLock); window.addEventListener('focus', releaseSecurityLock);
        document.addEventListener('visibilitychange', function() { if (document.hidden) triggerSecurityLock(); else releaseSecurityLock(); });

        function login() {
            const redirectUri = encodeURIComponent(window.location.origin + '/callback');
            location.href = `https://discord.com/oauth2/authorize?client_id={{ CLIENT_ID }}&response_type=code&redirect_uri=${redirectUri}&scope=identify`;
        }
    </script>
</head>
<body>
    <div id="security-overlay">
        <div class="alert-icon">⚠️</div>
        <div class="alert-main-text">보안 경고: 무단 캡처 금지</div>
        <div class="alert-sub-text">시스템 정보의 무단 촬영 및 복제 시도는 금지되어 있습니다.</div>
    </div>

    <div id="intro-overlay" style="display:none;">
        <div class="intro-circle-container">
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
                디스코드 계정으로 로그인
            </button>
        </div>

        <div id="access-denied-box" class="login-box" style="display:none; border-color:#ff2d55;">
            <div class="alert-icon" style="font-size: 50px;">⚠️</div>
            <h2 id="denied-title" class="access-denied-title">접근 차단됨</h2>
            <p id="denied-desc" style="font-size:14px; color:#cbd5e1; font-family:'Pretendard'; margin-bottom:20px;">화이트리스트에 등록된 인원만 시스템에 접속할 수 있습니다.</p>
            <a href="/logout" class="logout-btn" style="display:inline-block; padding:10px 20px;">다시 시도 / 로그아웃</a>
        </div>

        <div id="main-dashboard" class="dashboard" style="display:none;">
            <div class="sidebar">
                <div id="manual-sidebar-categorized"></div>

                <div id="admin-menu-section" style="display:none; margin-top:20px; border-top:1px solid rgba(255,255,255,0.1); padding-top:10px;">
                    <div class="sidebar-category-title" style="color:#38bdf8;">Admin Controls</div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-m-manage">
                        <button class="item-btn" onclick="switchAdminTab('m-manage')">📖 매뉴얼 등록/수정</button>
                    </div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-permissions">
                        <button class="item-btn" onclick="switchAdminTab('permissions')">🛡️ 권한 수정 및 관리</button>
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
                    <div class="doc-title">매뉴얼 작성 및 수정</div>
                    <div class="content-card">
                        <div style="display:flex; gap:10px; margin-bottom:4px;">
                            <input type="text" id="m-edit-category" placeholder="카테고리 예: 운항 지침, 공통 매뉴얼" style="flex:2;">
                            <label style="display:flex; align-items:center; gap:6px; font-family:'Pretendard'; font-size:13px; color:#00ffaa; cursor:pointer; padding-bottom:12px;">
                                <input type="checkbox" id="m-edit-pinned" style="width:auto; margin:0;"> 📌 상단 고정
                            </label>
                        </div>
                        <input type="text" id="m-edit-title" placeholder="매뉴얼 제목을 입력하세요">
                        <textarea id="m-edit-content" style="height:220px;" placeholder="매뉴얼 상세 내용을 입력하세요"></textarea>
                        <div style="display:flex; gap:10px;">
                            <button onclick="saveManualData()" class="btn-ui" style="flex:1;">💾 선택된 매뉴얼 저장/수정</button>
                            <button onclick="deleteManualData()" class="btn-ui btn-danger" style="width:110px;">🗑️ 매뉴얼 삭제</button>
                            <button onclick="resetManualForm()" class="btn-ui btn-secondary" style="width:110px;">새 매뉴얼</button>
                        </div>
                    </div>
                </div>

                <div id="view-admin-permissions" class="tab-enter" style="display:none;">
                    <div class="doc-title">스태프 및 어드민 권한 수정/관리</div>
                    <div class="content-card" style="margin-bottom:20px;">
                        <div style="display:flex; gap:10px; margin-bottom:12px;">
                            <input type="text" id="perm-search-input" placeholder="조회할 디스코드 ID 또는 @사용자명 입력" style="margin:0; flex:1;">
                            <button onclick="searchUser()" class="btn-ui" style="width:120px;">🔍 사용자 조회</button>
                        </div>

                        <div id="user-search-result" class="user-preview-card" style="display:none;">
                            <img id="preview-avatar" class="user-preview-avatar" src="" alt="Avatar">
                            <div>
                                <div id="preview-global-name" style="font-size:16px; font-weight:bold; color:#00ffaa;">-</div>
                                <div id="preview-username" style="font-size:13px; color:#a0aec0; font-family:'Pretendard';">-</div>
                                <div id="preview-id" style="font-size:11px; color:#64748b; font-family:monospace;">ID: -</div>
                            </div>
                        </div>

                        <div style="display:flex; gap:10px;">
                            <select id="perm-role-select" style="margin:0; flex:1;">
                                <option value="staff">스태프 (STAFF - 일반 접근 권한)</option>
                                <option value="admin">어드민 (ADMIN - 전체 최고 관리 권한)</option>
                            </select>
                            <button onclick="applyPermission('add')" class="btn-ui">화이트리스트 등록</button>
                            <button onclick="applyPermission('blacklist')" class="btn-ui btn-danger">⚠️ 블랙리스트 등록</button>
                        </div>
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                        <div class="content-card">
                            <h3 style="color:#00ffaa; margin-bottom:12px; font-size:15px;">🟢 승인된 사용자 명단 (화이트리스트)</h3>
                            <ul id="perm-wl-list" class="data-list"></ul>
                        </div>
                        <div class="content-card">
                            <h3 style="color:#ff2d55; margin-bottom:12px; font-size:15px;">🔴 차단된 사용자 명단 (블랙리스트)</h3>
                            <ul id="perm-bl-list" class="data-list"></ul>
                        </div>
                    </div>
                </div>

                <div id="view-admin-logs" class="tab-enter" style="display:none;">
                    <div class="doc-title">실시간 활동 및 보안 접속 로그</div>
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

        let appState = { user: null, role: null, manuals: [], user_whitelist: [], user_blacklist: [], admin_whitelist: [], logs: [] };
        let selectedManualIndex = 0;
        let currentActiveTabId = 'view-manual';
        let hasIntroRun = false;
        let searchedTargetUser = null;

        async function syncSystemState() {
            try {
                const res = await fetch('/api/state');
                if (res.status === 403) {
                    const errData = await res.json();
                    document.getElementById('login-box').style.display = 'none';
                    document.getElementById('access-denied-box').style.display = 'block';
                    if (errData.reason === 'blacklisted') {
                        document.getElementById('denied-title').innerText = "⚠️ 접근 차단 (BLACK LIST)";
                        document.getElementById('denied-desc').innerText = "귀하의 계정은 차단되어 접근할 수 없습니다.";
                    }
                    return;
                }
                if (res.ok) {
                    const data = await res.json();
                    if (data.status === 'unauthorized') return;

                    appState = data;
                    document.getElementById('login-box').style.display = 'none';
                    document.getElementById('access-denied-box').style.display = 'none';

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

        function runCustomIntro(nickname, username, avatarUrl, onComplete) {
            const introOverlay = document.getElementById('intro-overlay');
            const introProgress = document.getElementById('intro-progress');
            const introRing = document.getElementById('intro-ring');
            const introAvatar = document.getElementById('intro-avatar-img');
            const introWelcome = document.getElementById('intro-welcome');

            introAvatar.src = avatarUrl;
            introOverlay.style.display = 'flex';

            const totalDuration = (Math.random() * (1800 - 400) + 400);
            const startTime = performance.now();

            function updateLoading(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(Math.floor((elapsed / totalDuration) * 100), 100);
                introProgress.innerText = `${progress}%`;

                if (progress < 100) {
                    requestAnimationFrame(updateLoading);
                } else {
                    introProgress.style.display = 'none';
                    introRing.classList.add('expand');
                    introAvatar.classList.add('show');
                    introWelcome.innerText = `${nickname} (${username}) 님 환영합니다.`;
                    introWelcome.classList.add('show');

                    setTimeout(() => {
                        introOverlay.style.opacity = '0';
                        setTimeout(() => {
                            introOverlay.style.display = 'none';
                            onComplete();
                        }, 800);
                    }, 1000);
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
        }

        function renderCategorizedSidebar() {
            const container = document.getElementById('manual-sidebar-categorized');
            container.innerHTML = '';

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
            transitionToTab('view-manual');
            renderCategorizedSidebar();
            if (appState.role === 'admin') loadManualToForm(idx);
        }

        function transitionToTab(targetTabId) {
            if (currentActiveTabId === targetTabId) return;

            const currentTab = document.getElementById(currentActiveTabId);
            const targetTab = document.getElementById(targetTabId);

            document.querySelectorAll('.admin-nav').forEach(el => el.classList.remove('active'));

            if (targetTabId.startsWith('view-admin-')) {
                const subNav = targetTabId.replace('view-admin-', '');
                const activeNav = document.getElementById(`nav-${subNav}`);
                if (activeNav) activeNav.classList.add('active');
            }

            if (currentTab) {
                currentTab.classList.remove('tab-enter');
                currentTab.classList.add('tab-leave');

                setTimeout(() => {
                    currentTab.style.display = 'none';
                    currentTab.classList.remove('tab-leave');

                    if (targetTab) {
                        targetTab.style.display = 'block';
                        targetTab.classList.add('tab-enter');
                        currentActiveTabId = targetTabId;
                    }
                }, 200);
            }
        }

        function switchAdminTab(tabName) {
            transitionToTab(`view-admin-${tabName}`);
            if (tabName === 'm-manage' && selectedManualIndex >= 0) {
                loadManualToForm(selectedManualIndex);
            }
        }

        function renderAdminViews() {
            if (appState.role !== 'admin') return;

            const wlList = document.getElementById('perm-wl-list');
            const blList = document.getElementById('perm-bl-list');
            wlList.innerHTML = '';
            blList.innerHTML = '';

            (appState.admin_whitelist || []).forEach(id => {
                const li = document.createElement('li');
                li.innerHTML = `<span><b style="color:#ff2d55;">[ADMIN]</b> ${id}</span>`;
                wlList.appendChild(li);
            });

            (appState.user_whitelist || []).forEach(id => {
                const li = document.createElement('li');
                li.innerHTML = `<span><b style="color:#00ffaa;">[STAFF]</b> ${id}</span><button onclick="removeUserPermission('${id}')" class="btn-ui btn-danger" style="padding:4px 8px; font-size:11px;">삭제</button>`;
                wlList.appendChild(li);
            });

            (appState.user_blacklist || []).forEach(id => {
                const li = document.createElement('li');
                li.innerHTML = `<span><b style="color:#ff2d55;">[BLACK]</b> ${id}</span><button onclick="removeUserPermission('${id}')" class="btn-ui btn-secondary" style="padding:4px 8px; font-size:11px;">차단 해제</button>`;
                blList.appendChild(li);
            });

            const logBox = document.getElementById('admin-log-box');
            logBox.innerHTML = (appState.logs || []).map(l => `<div style="margin-bottom:6px; color:#a0aec0;">${l}</div>`).join('');
        }

        async function searchUser() {
            const query = document.getElementById('perm-search-input').value.trim();
            if (!query) { alert('유저 ID 또는 @사용자명을 입력하세요.'); return; }

            const res = await fetch(`/api/admin/user/lookup?query=${encodeURIComponent(query)}`);
            if (res.ok) {
                const data = await res.json();
                searchedTargetUser = data;
                document.getElementById('user-search-result').style.display = 'flex';
                document.getElementById('preview-avatar').src = data.avatar_url;
                document.getElementById('preview-global-name').innerText = data.global_name || data.username;
                document.getElementById('preview-username').innerText = `@${data.username}`;
                document.getElementById('preview-id').innerText = `ID: ${data.id}`;
            } else {
                alert('사용자를 찾을 수 없습니다. 정확한 ID나 디스코드 태그명을 입력해 주세요.');
            }
        }

        async function applyPermission(actionType) {
            const userId = searchedTargetUser ? searchedTargetUser.id : document.getElementById('perm-search-input').value.trim();
            const selectedRole = document.getElementById('perm-role-select').value;

            if (!userId) { alert('대상 사용자를 지정해 주세요.'); return; }

            const res = await fetch('/api/admin/permission/set', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_id: userId, action: actionType, role: selectedRole })
            });

            if (res.ok) {
                alert('권한이 변경되었습니다.');
                await syncSystemState();
            } else {
                alert('권한 적용에 실패하였습니다.');
            }
        }

        async function removeUserPermission(userId) {
            if (!confirm(`${userId} 님의 권한을 삭제/해제하시겠습니까?`)) return;
            const res = await fetch('/api/admin/permission/set', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_id: userId, action: 'remove' })
            });
            if (res.ok) await syncSystemState();
        }

        function loadManualToForm(idx) {
            const m = appState.manuals[idx];
            if (!m) return;
            document.getElementById('m-edit-category').value = m.category || '';
            document.getElementById('m-edit-title').value = m.title || '';
            document.getElementById('m-edit-content').value = m.content || '';
            document.getElementById('m-edit-pinned').checked = !!m.pinned;
        }

        function resetManualForm() {
            selectedManualIndex = -1;
            document.getElementById('m-edit-category').value = '';
            document.getElementById('m-edit-title').value = '';
            document.getElementById('m-edit-content').value = '';
            document.getElementById('m-edit-pinned').checked = false;
        }

        async function saveManualData() {
            const category = document.getElementById('m-edit-category').value.trim();
            const title = document.getElementById('m-edit-title').value.trim();
            const content = document.getElementById('m-edit-content').value;
            const pinned = document.getElementById('m-edit-pinned').checked;

            if (!title || !content) { alert('제목과 내용을 모두 입력해 주세요.'); return; }

            const res = await fetch('/api/admin/manual', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: selectedManualIndex, category, title, content, pinned })
            });

            if (res.ok) {
                alert('매뉴얼이 성공적으로 저장/수정되었습니다.');
                await syncSystemState();
            } else {
                alert('매뉴얼 저장 중 오류가 발생했습니다.');
            }
        }

        async function deleteManualData() {
            if (selectedManualIndex < 0) { alert('삭제할 매뉴얼을 지정해 주세요.'); return; }
            
            if (!confirm('⚠️ 정말로 이 매뉴얼을 완전 삭제하시겠습니까?\n삭제된 매뉴얼 데이터는 복구할 수 없습니다.')) {
                return;
            }

            const res = await fetch('/api/admin/manual/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: selectedManualIndex })
            });

            if (res.ok) {
                alert('매뉴얼이 삭제되었습니다.');
                resetManualForm();
                selectedManualIndex = 0;
                await syncSystemState();
            }
        }

        syncSystemState();
        setInterval(syncSystemState, 15000);
    </script>
</body>
</html>
"""

# --------------------------------------------------
# 🌐 라우트 및 REST API
# --------------------------------------------------
@app.route('/')
def index():
    return render_template_string(MAIN_HTML_TEMPLATE, CLIENT_ID=CLIENT_ID)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect('/')

    redirect_uri = f"{request.scheme}://{request.host}/callback"
    
    token_req = requests.post("https://discord.com/api/oauth2/token", data={
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri
    }, headers={"Content-Type": "application/x-www-form-urlencoded"})

    if token_req.status_code != 200:
        return f"OAuth Token Error: {token_req.text}", 400

    access_token = token_req.json().get("access_token")
    user_req = requests.get("https://discord.com/api/users/@me", headers={
        "Authorization": f"Bearer {access_token}"
    })

    if user_req.status_code != 200:
        return "Failed to fetch user", 400

    user_info = user_req.json()
    session['user'] = user_info

    data = load_data()
    user_id = user_info['id']
    username = user_info.get('global_name') or user_info.get('username')

    # 권한 엄격 판별
    if user_id in data.get("user_blacklist", []):
        add_log(data, "SECURITY", username, "블랙리스트 유저 차단됨")
        save_data(data)
        return redirect('/')

    is_admin = user_id in data.get("admin_whitelist", [])
    is_staff = user_id in data.get("user_whitelist", [])

    if not (is_admin or is_staff):
        add_log(data, "SECURITY", username, "미등록 사용자 접근 시도 거부")
        save_data(data)
        return redirect('/')

    role_str = "ADMIN" if is_admin else "STAFF"
    add_log(data, "AUTH", username, f"시스템 접속 완료 ({role_str})")
    save_data(data)

    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/state')
def get_state():
    user = session.get('user')
    if not user:
        return jsonify({"status": "unauthorized"})

    data = load_data()
    user_id = user['id']

    if user_id in data.get("user_blacklist", []):
        return jsonify({"status": "forbidden", "reason": "blacklisted"}), 403

    is_admin = user_id in data.get("admin_whitelist", [])
    is_staff = user_id in data.get("user_whitelist", [])

    if not (is_admin or is_staff):
        return jsonify({"status": "forbidden", "reason": "not_whitelisted"}), 403

    role = "admin" if is_admin else "staff"

    response_data = {
        "status": "authenticated",
        "user": user,
        "role": role,
        "manuals": data.get("manuals", [])
    }

    if role == "admin":
        response_data["admin_whitelist"] = data.get("admin_whitelist", [])
        response_data["user_whitelist"] = data.get("user_whitelist", [])
        response_data["user_blacklist"] = data.get("user_blacklist", [])
        response_data["logs"] = data.get("logs", [])

    return jsonify(response_data)

@app.route('/api/admin/user/lookup')
def lookup_user():
    user = session.get('user')
    if not user: return jsonify({"error": "Unauthorized"}), 401
    
    data = load_data()
    if user['id'] not in data.get("admin_whitelist", []):
        return jsonify({"error": "Forbidden"}), 403

    query = request.args.get('query', '').replace('@', '').strip()

    # Bot Token이 설정된 경우 디스코드 API로 조회 시도
    if BOT_TOKEN:
        headers = {"Authorization": f"Bot {BOT_TOKEN}"}
        res = requests.get(f"https://discord.com/api/v10/users/{query}", headers=headers)
        if res.status_code == 200:
            u = res.json()
            avatar = f"https://cdn.discordapp.com/avatars/{u['id']}/{u['avatar']}.png" if u.get('avatar') else "https://cdn.discordapp.com/embed/avatars/0.png"
            return jsonify({
                "id": u["id"],
                "username": u["username"],
                "global_name": u.get("global_name", u["username"]),
                "avatar_url": avatar
            })

    # ID 자체로 조회 시 가상 데이터 프레임 반환
    return jsonify({
        "id": query,
        "username": query,
        "global_name": f"사용자 ({query})",
        "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png"
    })

@app.route('/api/admin/permission/set', methods=['POST'])
def set_permission():
    user = session.get('user')
    if not user: return jsonify({"error": "Unauthorized"}), 401

    data = load_data()
    if user['id'] not in data.get("admin_whitelist", []):
        return jsonify({"error": "Forbidden"}), 403

    req = request.get_json()
    target_id = req.get('target_id')
    action = req.get('action') # 'add', 'blacklist', 'remove'
    role = req.get('role', 'staff') # 'staff', 'admin'
    username = user.get('global_name') or user.get('username')

    # 기존 리스트에서 원본 삭제 처리
    if target_id in data.get("user_whitelist", []): data["user_whitelist"].remove(target_id)
    if target_id in data.get("user_blacklist", []): data["user_blacklist"].remove(target_id)
    if target_id in data.get("admin_whitelist", []) and target_id not in DEFAULT_ADMINS:
        data["admin_whitelist"].remove(target_id)

    if action == "add":
        if role == "admin":
            if target_id not in data.get("admin_whitelist", []): data.setdefault("admin_whitelist", []).append(target_id)
            add_log(data, "PERM", username, f"{target_id} 님을 어드민(ADMIN)으로 지정")
        else:
            if target_id not in data.get("user_whitelist", []): data.setdefault("user_whitelist", []).append(target_id)
            add_log(data, "PERM", username, f"{target_id} 님을 스태프(STAFF) 화이트리스트에 등록")

    elif action == "blacklist":
        if target_id not in data.get("user_blacklist", []): data.setdefault("user_blacklist", []).append(target_id)
        add_log(data, "PERM", username, f"{target_id} 님을 블랙리스트(BLACK)로 지정 및 접근 차단")

    elif action == "remove":
        add_log(data, "PERM", username, f"{target_id} 님의 전체 권한 해제")

    save_data(data)
    return jsonify({"success": True})

@app.route('/api/admin/manual', methods=['POST'])
def handle_manual():
    user = session.get('user')
    if not user: return jsonify({"error": "Unauthorized"}), 401

    data = load_data()
    if user['id'] not in data.get("admin_whitelist", []):
        return jsonify({"error": "Forbidden"}), 403

    req = request.get_json()
    idx = req.get('index', -1)
    category = req.get('category', '공통 매뉴얼')
    title = req.get('title')
    content = req.get('content')
    pinned = req.get('pinned', False)

    username = user.get('global_name') or user.get('username')

    if 0 <= idx < len(data['manuals']):
        data['manuals'][idx] = {
            "id": data['manuals'][idx].get("id", idx + 1),
            "category": category,
            "pinned": pinned,
            "title": title,
            "content": content
        }
        add_log(data, "MANUAL", username, f"매뉴얼 수정: {title}")
    else:
        new_id = max([m.get('id', 0) for m in data['manuals']], default=0) + 1
        data['manuals'].append({
            "id": new_id,
            "category": category,
            "pinned": pinned,
            "title": title,
            "content": content
        })
        add_log(data, "MANUAL", username, f"새 매뉴얼 작성: {title}")

    save_data(data)
    return jsonify({"success": True})

@app.route('/api/admin/manual/delete', methods=['POST'])
def delete_manual():
    user = session.get('user')
    if not user: return jsonify({"error": "Unauthorized"}), 401

    data = load_data()
    if user['id'] not in data.get("admin_whitelist", []):
        return jsonify({"error": "Forbidden"}), 403

    req = request.get_json()
    idx = req.get('index', -1)
    username = user.get('global_name') or user.get('username')

    if 0 <= idx < len(data['manuals']):
        removed = data['manuals'].pop(idx)
        add_log(data, "MANUAL", username, f"매뉴얼 삭제: {removed.get('title')}")
        save_data(data)
        return jsonify({"success": True})

    return jsonify({"error": "Invalid index"}), 400

# --------------------------------------------------
# 🚀 서버 구동
# --------------------------------------------------
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
