import os
import json
import base64
import datetime
from flask import Flask, request, render_template_string, redirect, session, jsonify, url_for
import requests
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

# Reverse Proxy 환경 대응
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

# ==========================================
# ⚙️ 쿠키 및 세션 보안 설정 (무한 로그인 방지)
# ==========================================
app.secret_key = os.environ.get("SECRET_KEY", "sky_aurora_super_secret_key_2026")
app.config['SESSION_COOKIE_NAME'] = 'sky_aurora_session'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = False  # HTTP/HTTPS 환경 유연 대응
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=7)

# ==========================================
# ⚙️ 설정 및 환경 변수 (보안을 위해 환경 변수 처리)
# ==========================================
CLIENT_ID = "1534184089144266872"
CLIENT_SECRET = "ZfLY_vs2lo_LQVtd89ZB64jHe3dviRNm"
BOT_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "")

DATA_FILE = "sky_aurora_admin_data.json"
DEFAULT_ADMINS = ["1534184089144266872", "843621337066504225"]

# 깃허브 토큰과 레포지토리는 환경 변수에서 안전하게 불러옵니다.
# (배포 환경이나 로컬 환경 변수에 GITHUB_TOKEN을 설정해주세요)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = "itx-0622/sky-aurora-staff"

# --------------------------------------------------
# 📁 데이터 저장/불러오기
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
            "manuals": [
                {
                    "id": 1,
                    "category": "보안 지침",
                    "pinned": True,
                    "title": "01. 기본 보안 규칙",
                    "content": "본 매뉴얼 시스템에 포함된 모든 정보는 외부 유출이 엄격히 금지됩니다."
                }
            ],
            "logs": []
        }

    for admin_id in DEFAULT_ADMINS:
        if str(admin_id) not in [str(a) for a in data.get("admin_whitelist", [])]:
            data.setdefault("admin_whitelist", []).append(str(admin_id))

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
                "message": f"Auto-sync data [{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]",
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
# 🎨 프론트엔드 UI/UX
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

        .dashboard { display: flex; flex: 1; overflow: hidden; }
        .sidebar { width: 300px; background: rgba(0, 0, 0, 0.4); border-right: 1px solid rgba(255, 255, 255, 0.08); padding: 20px 14px; overflow-y: auto; }
        .sidebar-category-title { font-size: 12px; color: #00ffaa; letter-spacing: 1px; margin: 16px 0 8px 8px; text-transform: uppercase; font-family: 'Pretendard'; font-weight: bold; }
        
        .aurora-btn-wrapper { position: relative; margin-bottom: 8px; border-radius: 12px; overflow: hidden; padding: 2px; background: rgba(255, 255, 255, 0.03); transition: all 0.25s ease; }
        .aurora-btn-wrapper.active { background: linear-gradient(90deg, #00ffaa, #00f2fe); box-shadow: 0 0 15px rgba(0, 255, 170, 0.4); }
        .item-btn { position: relative; z-index: 1; width: 100%; text-align: left; padding: 12px 14px; background: rgba(10, 16, 32, 0.95); border: none; color: #8a99ad; border-radius: 10px; cursor: pointer; font-size: 13px; font-family: 'Pretendard', sans-serif; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
        .aurora-btn-wrapper.active .item-btn { color: #ffffff; background: rgba(6, 24, 38, 0.95); font-weight: bold; }

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
        @keyframes manualEnter { 0% { opacity: 0; transform: translateY(20px) scale(0.98); } 100% { opacity: 1; transform: translateY(0) scale(1); } }

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

        <div id="main-dashboard" class="dashboard" style="display:none;">
            <div class="sidebar">
                <div id="manual-sidebar-categorized"></div>

                <div id="admin-menu-section" style="display:none; margin-top:20px; border-top:1px solid rgba(255,255,255,0.1); padding-top:10px;">
                    <div class="sidebar-category-title" style="color:#38bdf8;">Admin Controls</div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-m-manage">
                        <button class="item-btn" onclick="switchAdminTab('m-manage')">📖 매뉴얼 등록/수정</button>
                    </div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-permissions">
                        <button class="item-btn" onclick="switchAdminTab('permissions')">🛡️ 어드민 권한 관리</button>
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
                            <button onclick="deleteManualData()" class="btn-ui btn-danger" style="width:110px;">🗑️ 삭제</button>
                            <button onclick="resetManualForm()" class="btn-ui btn-secondary" style="width:110px;">새 매뉴얼</button>
                        </div>
                    </div>
                </div>

                <div id="view-admin-permissions" class="tab-enter" style="display:none;">
                    <div class="doc-title">어드민 권한 업그레이드 및 관리</div>
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
                            <button onclick="applyAdminUpgrade()" class="btn-ui" style="flex:1;">⚡ 해당 사용자 어드민(ADMIN)으로 업그레이드</button>
                        </div>
                    </div>

                    <div class="content-card">
                        <h3 style="color:#ff2d55; margin-bottom:12px; font-size:15px;">🛡️ 현재 등록된 어드민 명단</h3>
                        <ul id="perm-admin-list" class="data-list"></ul>
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

        let appState = { user: null, role: null, manuals: [], admin_whitelist: [], logs: [] };
        let selectedManualIndex = 0;
        let currentActiveTabId = 'view-manual';
        let hasIntroRun = false;
        let searchedTargetUser = null;

        async function syncSystemState() {
            try {
                const res = await fetch(`${window.location.origin}/api/state`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.status === 'unauthorized') {
                        document.getElementById('login-box').style.display = 'block';
                        document.getElementById('main-dashboard').style.display = 'none';
                        return;
                    }

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

        function runCustomIntro(nickname, username, avatarUrl, onComplete) {
            const introOverlay = document.getElementById('intro-overlay');
            const introProgress = document.getElementById('intro-progress');
            const introRing = document.getElementById('intro-ring');
            const introAvatar = document.getElementById('intro-avatar-img');
            const introWelcome = document.getElementById('intro-welcome');

            introAvatar.src = avatarUrl;
            introOverlay.style.display = 'flex';

            const totalDuration = (Math.random() * (1600 - 500) + 500);
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
                    }, 800);
                }
            }
            requestAnimationFrame(updateLoading);
        }

        function showMainDashboard(data, avatarUrl) {
            document.getElementById('main-dashboard').style.display = 'flex';
            document.getElementById('user-header-info').style.display = 'flex';
            document.getElementById('user-avatar').src = avatarUrl;
            document.getElementById('user-name').innerText = data.user.global_name || data.user.username;

            const badge = document.getElementById('user-role-badge');
            if (data.role === 'admin') {
                badge.innerText = 'ADMIN';
                badge.className = 'badge-admin';
                document.getElementById('admin-menu-section').style.display = 'block';
            } else {
                badge.innerText = 'STAFF';
                badge.className = 'badge-staff';
                document.getElementById('admin-menu-section').style.display = 'none';
            }

            renderSidebarManuals();
            renderManualContent();
            renderPermissionsLists();
            renderAdminLogs();
        }

        function renderSidebarManuals() {
            const container = document.getElementById('manual-sidebar-categorized');
            container.innerHTML = '';

            const categories = {};
            appState.manuals.forEach((m, idx) => {
                const cat = m.category || '공통 매뉴얼';
                if (!categories[cat]) categories[cat] = [];
                categories[cat].push({ ...m, index: idx });
            });

            for (const [catName, items] of Object.entries(categories)) {
                const catTitle = document.createElement('div');
                catTitle.className = 'sidebar-category-title';
                catTitle.innerText = catName;
                container.appendChild(catTitle);

                items.sort((a, b) => (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0));

                items.forEach(item => {
                    const wrapper = document.createElement('div');
                    wrapper.className = `aurora-btn-wrapper ${item.index === selectedManualIndex ? 'active' : ''}`;

                    const btn = document.createElement('button');
                    btn.className = 'item-btn';
                    btn.innerHTML = `<span>${item.pinned ? '📌 ' : ''}${item.title}</span>`;
                    btn.onclick = () => {
                        selectedManualIndex = item.index;
                        renderSidebarManuals();
                        switchTab('view-manual');
                        renderManualContent();
                    };

                    wrapper.appendChild(btn);
                    container.appendChild(wrapper);
                });
            }
        }

        function renderManualContent() {
            const manual = appState.manuals[selectedManualIndex];
            if (manual) {
                document.getElementById('doc-title').innerText = manual.title;
                document.getElementById('doc-body').innerText = manual.content;

                document.getElementById('m-edit-category').value = manual.category || '';
                document.getElementById('m-edit-title').value = manual.title || '';
                document.getElementById('m-edit-content').value = manual.content || '';
                document.getElementById('m-edit-pinned').checked = !!manual.pinned;
            } else {
                document.getElementById('doc-title').innerText = '매뉴얼이 없습니다.';
                document.getElementById('doc-body').innerText = '등록된 매뉴얼 항목이 존재하지 않습니다.';
            }
        }

        function renderPermissionsLists() {
            const adminUl = document.getElementById('perm-admin-list');
            adminUl.innerHTML = '';

            appState.admin_whitelist.forEach(id => {
                const li = document.createElement('li');
                li.innerHTML = `<span>어드민 ID: ${id}</span>
                                <button onclick="removeAdmin('${id}')" class="btn-ui btn-danger" style="padding:4px 8px; font-size:11px;">권한 회수</button>`;
                adminUl.appendChild(li);
            });
        }

        function renderAdminLogs() {
            const logBox = document.getElementById('admin-log-box');
            logBox.innerHTML = appState.logs.map(log => `<div>${log}</div>`).join('');
        }

        function switchTab(tabId) {
            if (currentActiveTabId === tabId) return;
            const currentEl = document.getElementById(currentActiveTabId);
            const targetEl = document.getElementById(tabId);

            document.querySelectorAll('.aurora-btn-wrapper').forEach(el => el.classList.remove('active'));

            if (currentEl) {
                currentEl.style.display = 'none';
                targetEl.style.display = 'block';
                currentActiveTabId = tabId;
            }
        }

        function switchAdminTab(adminType) {
            const navWrapper = document.getElementById(`nav-${adminType}`);
            switchTab(`view-admin-${adminType}`);
            if (navWrapper) navWrapper.classList.add('active');
        }

        async function saveManualData() {
            const category = document.getElementById('m-edit-category').value.trim();
            const title = document.getElementById('m-edit-title').value.trim();
            const content = document.getElementById('m-edit-content').value.trim();
            const pinned = document.getElementById('m-edit-pinned').checked;

            if (!title || !content) { alert('제목과 내용을 입력해주세요.'); return; }

            const res = await fetch(`${window.location.origin}/api/manual/save`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: selectedManualIndex, category, title, content, pinned })
            });

            if (res.ok) {
                alert('매뉴얼이 저장되었습니다.');
                syncSystemState();
            } else { alert('저장에 실패했습니다.'); }
        }

        async function deleteManualData() {
            if (!confirm('정말 삭제하시겠습니까?')) return;
            const res = await fetch(`${window.location.origin}/api/manual/delete`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: selectedManualIndex })
            });

            if (res.ok) {
                alert('매뉴얼이 삭제되었습니다.');
                selectedManualIndex = 0;
                syncSystemState();
            } else { alert('삭제에 실패했습니다.'); }
        }

        function resetManualForm() {
            selectedManualIndex = appState.manuals.length;
            document.getElementById('m-edit-category').value = '';
            document.getElementById('m-edit-title').value = '';
            document.getElementById('m-edit-content').value = '';
            document.getElementById('m-edit-pinned').checked = false;
        }

        async function searchUser() {
            const query = document.getElementById('perm-search-input').value.trim();
            if (!query) { alert('검색할 디스코드 ID 또는 사용자명을 입력하세요.'); return; }

            try {
                const res = await fetch(`${window.location.origin}/api/user/lookup`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ query })
                });

                if (res.ok) {
                    const user = await res.json();
                    searchedTargetUser = user;
                    document.getElementById('preview-global-name').innerText = user.global_name || user.username;
                    document.getElementById('preview-username').innerText = `@${user.username}`;
                    document.getElementById('preview-id').innerText = `ID: ${user.id}`;
                    document.getElementById('preview-avatar').src = user.avatar 
                        ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png` 
                        : 'https://cdn.discordapp.com/embed/avatars/0.png';
                    document.getElementById('user-search-result').style.display = 'flex';
                } else {
                    alert('사용자를 찾을 수 없습니다.');
                    document.getElementById('user-search-result').style.display = 'none';
                    searchedTargetUser = null;
                }
            } catch(e) { alert('조회 중 오류가 발생했습니다.'); }
        }

        async function applyAdminUpgrade() {
            const query = document.getElementById('perm-search-input').value.trim();
            const targetId = searchedTargetUser ? searchedTargetUser.id : query;

            if (!targetId) { alert('유효한 디스코드 ID를 입력하세요.'); return; }

            const res = await fetch(`${window.location.origin}/api/permission/upgrade`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_id: String(targetId) })
            });

            if (res.ok) {
                alert('성공적으로 어드민 권한으로 업그레이드되었습니다.');
                syncSystemState();
            } else {
                alert('어드민 업그레이드에 실패했습니다.');
            }
        }

        async function removeAdmin(targetId) {
            if (!confirm(`사용자(${targetId})의 어드민 권한을 회수하시겠습니까?`)) return;

            const res = await fetch(`${window.location.origin}/api/permission/remove-admin`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target_id: String(targetId) })
            });

            if (res.ok) {
                syncSystemState();
            } else { alert('권한 회수에 실패했습니다.'); }
        }

        window.onload = syncSystemState;
    </script>
</body>
</html>
"""

# ==========================================
# 🔌 백엔드 API 컨트롤러
# ==========================================

@app.route('/')
def index():
    return render_template_string(MAIN_HTML_TEMPLATE, CLIENT_ID=CLIENT_ID)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))

    redirect_uri = url_for('callback', _external=True)
    token_url = 'https://discord.com/api/oauth2/token'
    
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        res = requests.post(token_url, data=data, headers=headers, timeout=5)
        res_data = res.json()
        access_token = res_data.get('access_token')

        if access_token:
            user_res = requests.get('https://discord.com/api/users/@me', headers={'Authorization': f'Bearer {access_token}'}, timeout=5)
            user_data = user_res.json()

            if 'id' in user_data:
                session['user'] = user_data
                session.permanent = True
                session.modified = True

                db = load_data()
                user_name = user_data.get('global_name') or user_data.get('username')
                add_log(db, "AUTH", user_name, "시스템 로그인 완료")
                save_data(db)

    except Exception as e:
        print(f"[Auth Error] {e}")

    return redirect('/')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/state', methods=['GET'], strict_slashes=False)
def api_state():
    user = session.get('user')
    if not user:
        return jsonify({'status': 'unauthorized'}), 200

    db = load_data()
    user_id = str(user['id'])

    is_admin = user_id in [str(a) for a in db.get('admin_whitelist', [])]
    role = 'admin' if is_admin else 'staff'

    return jsonify({
        'status': 'success',
        'user': user,
        'role': role,
        'manuals': db.get('manuals', []),
        'admin_whitelist': db.get('admin_whitelist', []),
        'logs': db.get('logs', []) if is_admin else []
    })

@app.route('/api/user/lookup', methods=['POST'], strict_slashes=False)
def api_user_lookup():
    user = session.get('user')
    if not user: return jsonify({'error': 'Unauthorized'}), 401

    req_data = request.get_json() or {}
    query = str(req_data.get('query', '')).strip().lstrip('@')

    if not query: return jsonify({'error': 'Query required'}), 400

    if query.isdigit():
        if BOT_TOKEN:
            try:
                res = requests.get(f"https://discord.com/api/v10/users/{query}", headers={"Authorization": f"Bot {BOT_TOKEN}"}, timeout=5)
                if res.status_code == 200:
                    return jsonify(res.json())
            except Exception: pass
        return jsonify({"id": query, "username": f"User_{query}", "global_name": f"사용자 ({query})", "avatar": None})

    return jsonify({'error': 'User not found'}), 404

@app.route('/api/manual/save', methods=['POST'], strict_slashes=False)
def api_manual_save():
    user = session.get('user')
    if not user: return jsonify({'error': 'Unauthorized'}), 401

    db = load_data()
    if str(user['id']) not in [str(a) for a in db.get('admin_whitelist', [])]:
        return jsonify({'error': 'Forbidden'}), 403

    req_data = request.get_json() or {}
    index = req_data.get('index')
    category = req_data.get('category', '공통 매뉴얼')
    title = req_data.get('title')
    content = req_data.get('content')
    pinned = req_data.get('pinned', False)

    manuals = db.get('manuals', [])
    manual_entry = {
        'id': len(manuals) + 1 if index >= len(manuals) else manuals[index].get('id', index + 1),
        'category': category,
        'title': title,
        'content': content,
        'pinned': pinned
    }

    if index is not None and 0 <= index < len(manuals):
        manuals[index] = manual_entry
    else:
        manuals.append(manual_entry)

    db['manuals'] = manuals
    user_name = user.get('global_name') or user.get('username')
    add_log(db, "MANUAL", user_name, f"매뉴얼 저장/수정 ('{title}')")
    save_data(db)

    return jsonify({'status': 'success'})

@app.route('/api/manual/delete', methods=['POST'], strict_slashes=False)
def api_manual_delete():
    user = session.get('user')
    if not user: return jsonify({'error': 'Unauthorized'}), 401

    db = load_data()
    if str(user['id']) not in [str(a) for a in db.get('admin_whitelist', [])]:
        return jsonify({'error': 'Forbidden'}), 403

    req_data = request.get_json() or {}
    index = req_data.get('index')
    manuals = db.get('manuals', [])

    if index is not None and 0 <= index < len(manuals):
        deleted = manuals.pop(index)
        db['manuals'] = manuals
        user_name = user.get('global_name') or user.get('username')
        add_log(db, "MANUAL", user_name, f"매뉴얼 삭제 ('{deleted.get('title')}')")
        save_data(db)
        return jsonify({'status': 'success'})

    return jsonify({'error': 'Invalid index'}), 400

@app.route('/api/permission/upgrade', methods=['POST'], strict_slashes=False)
def api_permission_upgrade():
    user = session.get('user')
    if not user: return jsonify({'error': 'Unauthorized'}), 401

    db = load_data()
    if str(user['id']) not in [str(a) for a in db.get('admin_whitelist', [])]:
        return jsonify({'error': 'Forbidden'}), 403

    req_data = request.get_json() or {}
    target_id = str(req_data.get('target_id', '')).strip()

    if not target_id: return jsonify({'error': 'Target ID required'}), 400

    user_name = user.get('global_name') or user.get('username')
    db['admin_whitelist'] = [str(x) for x in db.get('admin_whitelist', [])]

    if target_id not in db['admin_whitelist']:
        db['admin_whitelist'].append(target_id)
        add_log(db, "PERMISSION", user_name, f"어드민 권한 업그레이드 (ID: {target_id})")

    save_data(db)
    return jsonify({'status': 'success'})

@app.route('/api/permission/remove-admin', methods=['POST'], strict_slashes=False)
def api_permission_remove_admin():
    user = session.get('user')
    if not user: return jsonify({'error': 'Unauthorized'}), 401

    db = load_data()
    if str(user['id']) not in [str(a) for a in db.get('admin_whitelist', [])]:
        return jsonify({'error': 'Forbidden'}), 403

    req_data = request.get_json() or {}
    target_id = str(req_data.get('target_id', '')).strip()

    if not target_id: return jsonify({'error': 'Target ID required'}), 400

    user_name = user.get('global_name') or user.get('username')
    db['admin_whitelist'] = [str(x) for x in db.get('admin_whitelist', [])]

    if target_id in db['admin_whitelist'] and target_id not in DEFAULT_ADMINS:
        db['admin_whitelist'].remove(target_id)
        add_log(db, "PERMISSION", user_name, f"어드민 권한 회수 (ID: {target_id})")
        save_data(db)
        return jsonify({'status': 'success'})

    return jsonify({'error': 'Cannot remove default admin or user not in list'}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
