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
CLIENT_SECRET = "JcMp7ntF3Rx32ZYTRjyaYUWfmp0EU3co"
BASE_URL = "https://sky-aurora-staff.onrender.com"

ADMIN_SECRET_KEY = "sky_aurora_admin_secret_key_1234"
DATA_FILE = "sky_aurora_admin_data.json"
DEFAULT_ADMINS = ["1534184089144266872", "843621337066504225"]

# GitHub 영구 저장 환경변수
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

        /* 🚨 커스텀 삭제 경고 모달 */
        #custom-confirm-modal {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0, 0, 0, 0.85); backdrop-filter: blur(12px);
            z-index: 999999; display: none; justify-content: center; align-items: center;
        }
        .modal-box {
            background: rgba(10, 15, 30, 0.95); border: 1px solid #ef4444; border-radius: 18px;
            padding: 28px; width: 90%; max-width: 420px; text-align: center; box-shadow: 0 0 30px rgba(239, 68, 68, 0.3);
            animation: modalPop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
        }
        @keyframes modalPop { from { transform: scale(0.8); opacity: 0; } to { transform: scale(1); opacity: 1; } }

        /* 🚀 인트로 로딩 화면 스타일 */
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
        .intro-ring.expand {
            transform: scale(1.3); border-width: 4px; border-color: #00ffaa;
            box-shadow: 0 0 25px #00ffaa, inset 0 0 15px #00ffaa; opacity: 1;
        }
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

        .login-box { padding: 50px 24px; text-align: center; margin: auto; max-width: 400px; width: 90%; background: rgba(13, 20, 38, 0.85); border: 1px solid rgba(0, 255, 170, 0.25); border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.6); }
        .discord-btn { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 14px; background: #5865F2; color: white; text-decoration: none; border-radius: 12px; font-family: 'Pretendard', sans-serif; font-weight: bold; font-size: 15px; border: none; cursor: pointer; transition: all 0.2s; }
        .discord-btn:hover { background: #4752C4; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(88, 101, 242, 0.5); }

        .dashboard { display: flex; flex: 1; overflow: hidden; }
        
        .sidebar { width: 300px; background: rgba(0, 0, 0, 0.4); border-right: 1px solid rgba(255, 255, 255, 0.08); padding: 20px 14px; overflow-y: auto; }
        .sidebar-category-title { font-size: 12px; color: #00ffaa; letter-spacing: 1px; margin: 16px 0 8px 8px; text-transform: uppercase; font-family: 'Pretendard'; font-weight: bold; }
        
        /* ⭕ 기존 회전 링(Glow Ring) 강조 스타일 복원 */
        .aurora-btn-wrapper { position: relative; margin-bottom: 10px; border-radius: 12px; padding: 2px; transition: all 0.3s ease; }
        .aurora-btn-wrapper.active {
            background: linear-gradient(135deg, #00ffaa, #00f2fe);
            box-shadow: 0 0 20px rgba(0, 255, 170, 0.6), inset 0 0 10px rgba(0, 242, 254, 0.5);
        }
        .item-btn { position: relative; z-index: 1; width: 100%; text-align: left; padding: 12px 14px; background: rgba(10, 16, 32, 0.95); border: none; color: #8a99ad; border-radius: 10px; cursor: pointer; font-size: 13px; font-family: 'Pretendard', sans-serif; font-weight: 600; display: flex; justify-content: space-between; align-items: center; transition: all 0.2s ease; }
        .aurora-btn-wrapper.active .item-btn { color: #ffffff; background: rgba(6, 24, 38, 0.98); font-weight: bold; }
        .pin-badge { font-size: 11px; margin-right: 4px; }

        .main-content { flex: 1; padding: 28px; overflow-y: auto; position: relative; }
        .content-card { background: rgba(5, 8, 17, 0.7); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        
        .doc-title { font-size: 20px; margin-bottom: 16px; color: #ffffff; border-bottom: 1px solid rgba(255, 255, 255, 0.1); padding-bottom: 12px; display: flex; align-items: center; gap: 10px; }
        .doc-title::before { content: ''; display: inline-block; width: 4px; height: 20px; background: #00ffaa; border-radius: 2px; }
        .doc-body { font-family: 'Pretendard', sans-serif; font-weight: 500; font-size: 15px; line-height: 1.85; color: #cbd5e1; white-space: pre-wrap; background: rgba(0, 0, 0, 0.3); padding: 20px; border-radius: 14px; border: 1px solid rgba(255, 255, 255, 0.05); }

        input, textarea, select { width: 100%; background: rgba(3, 5, 9, 0.8); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.12); padding: 12px 14px; border-radius: 10px; margin-bottom: 12px; outline: none; font-family: 'Pretendard', sans-serif; }
        input:focus, textarea:focus, select:focus { border-color: #00ffaa; box-shadow: 0 0 12px rgba(0, 255, 170, 0.3); }
        .btn-ui { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; border: none; padding: 10px 18px; border-radius: 10px; font-weight: 700; cursor: pointer; font-family: 'Pretendard', sans-serif; transition: all 0.2s ease; }
        .btn-ui:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4); }
        .btn-danger { background: linear-gradient(135deg, #ef4444, #b91c1c); }
        .btn-secondary { background: linear-gradient(135deg, #475569, #334155); }

        ul.data-list { list-style: none; padding: 0; }
        ul.data-list li { background: rgba(10, 16, 32, 0.7); padding: 12px 14px; margin-bottom: 8px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.05); display: flex; justify-content: space-between; align-items: center; font-family: 'Pretendard', sans-serif; font-size: 14px; }

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
        document.addEventListener('contextmenu', e => e.preventDefault());
        document.addEventListener('selectstart', e => e.preventDefault());
        document.addEventListener('dragstart', e => e.preventDefault());

        let lastSecurityViolationLogTime = 0;
        function sendSecurityViolationLog(details) {
            const now = Date.now();
            if (now - lastSecurityViolationLogTime < 2000) return; // 2초 디바운싱
            lastSecurityViolationLogTime = now;

            fetch('/api/security_log', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ action_detail: details })
            });
        }

        function triggerSecurityLock(actionName) { 
            const overlay = document.getElementById('security-overlay'); 
            if (overlay) overlay.style.display = 'flex'; 
            if (actionName) sendSecurityViolationLog(actionName);
        }

        function releaseSecurityLock() { 
            const overlay = document.getElementById('security-overlay'); 
            if (overlay) overlay.style.display = 'none'; 
        }

        /* 🚨 실시간 보안 감지 및 어드민 로그 기록 */
        document.addEventListener('keydown', function(e) {
            if (e.key === 'PrintScreen') { triggerSecurityLock('화면 캡처 시도 (PrintScreen)'); }
            if (e.key === 'F12') { triggerSecurityLock('개발자 도구 열기 시도 (F12)'); }
            
            const k = e.key.toLowerCase();
            if ((e.ctrlKey || e.metaKey) && ['c', 'v', 'u', 's', 'p', 'a', 'i', 'j'].includes(k)) { 
                triggerSecurityLock(`단축키 무단 조작 시도 (Ctrl/Cmd + ${k.toUpperCase()})`); 
            }
        }, true);

        document.addEventListener('keyup', function(e) { 
            if (!e.shiftKey && !e.metaKey && !e.ctrlKey && !e.altKey) { releaseSecurityLock(); } 
        });
        window.addEventListener('blur', function() { triggerSecurityLock('화면 이탈 / 캡처 프로그램 감지'); }); 
        window.addEventListener('focus', releaseSecurityLock);
        document.addEventListener('visibilitychange', function() { 
            if (document.hidden) triggerSecurityLock('탭 전환 / 무단 화면 감시'); else releaseSecurityLock(); 
        });

        function login() {
            const redirectUri = encodeURIComponent(window.location.origin + '/callback');
            location.href = `https://discord.com/oauth2/authorize?client_id=__CLIENT_ID__&response_type=code&redirect_uri=${redirectUri}&scope=identify`;
        }
    </script>
</head>
<body>
    <div id="security-overlay">
        <div class="alert-icon">⚠️</div>
        <div class="alert-main-text">보안 경고: 무단 캡처 및 복사 감지됨</div>
        <div class="alert-sub-text">해당 조작 시도가 관리자 로그에 즉시 기록되었습니다.</div>
    </div>

    <!-- 🚨 커스텀 삭제 확인 모달 -->
    <div id="custom-confirm-modal">
        <div class="modal-box">
            <div style="font-size:40px; margin-bottom:10px;">⚠️</div>
            <h3 style="color:#ef4444; font-size:18px; margin-bottom:12px;">매뉴얼 삭제 경고</h3>
            <p id="modal-delete-text" style="font-size:14px; color:#cbd5e1; font-family:'Pretendard'; margin-bottom:20px; line-height:1.5;"></p>
            <div style="display:flex; gap:10px; justify-content:center;">
                <button onclick="confirmExecuteDelete()" class="btn-ui btn-danger" style="flex:1;">삭제 진행</button>
                <button onclick="closeConfirmModal()" class="btn-ui btn-secondary" style="flex:1;">취소</button>
            </div>
        </div>
    </div>

    <!-- 🚀 인트로 로딩 커스텀 레이어 -->
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
                디스코드 계정으로 통합 로그인
            </button>
        </div>

        <div id="main-dashboard" class="dashboard" style="display:none;">
            <div class="sidebar">
                <div id="manual-sidebar-categorized"></div>

                <div id="admin-menu-section" style="display:none; margin-top:20px; border-top:1px solid rgba(255,255,255,0.1); padding-top:10px;">
                    <div class="sidebar-category-title" style="color:#38bdf8;">Admin Controls</div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-m-manage">
                        <button class="item-btn" onclick="switchAdminTab('m-manage')">⚙️ 매뉴얼 생성 및 수정</button>
                    </div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-permissions">
                        <button class="item-btn" onclick="switchAdminTab('permissions')">🛡️ 권한 제어 센터</button>
                    </div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-logs">
                        <button class="item-btn" onclick="switchAdminTab('logs')">📜 실시간 보안/접속 로그</button>
                    </div>
                </div>
            </div>

            <div class="main-content">
                <div id="view-manual" class="tab-enter" style="display:block;">
                    <div id="doc-title" class="doc-title">매뉴얼 선택 중...</div>
                    <div id="doc-body" class="doc-body"></div>
                </div>

                <div id="view-admin-m-manage" class="tab-enter" style="display:none;">
                    <div class="doc-title">매뉴얼 제작 및 선택 수정</div>
                    <div class="content-card">
                        <div style="margin-bottom:16px;">
                            <label style="font-family:'Pretendard'; font-size:13px; color:#00ffaa; display:block; margin-bottom:6px;">✏️ 수정할 매뉴얼 선택 (신규 작성 시 '신규 작성' 선택):</label>
                            <select id="m-select-target" onchange="onAdminSelectManualToEdit()" style="margin-bottom:0;">
                                <option value="NEW">➕ [신규] 새 매뉴얼 작성하기</option>
                            </select>
                        </div>
                        <hr style="border:0; border-top:1px solid rgba(255,255,255,0.1); margin:16px 0;">
                        <div style="display:flex; gap:10px; margin-bottom:4px;">
                            <input type="text" id="m-edit-category" placeholder="주제(카테고리) 예: 운항 지침, 공통 매뉴얼" style="flex:2;">
                            <label style="display:flex; align-items:center; gap:6px; font-family:'Pretendard'; font-size:13px; color:#00ffaa; cursor:pointer; padding-bottom:12px;">
                                <input type="checkbox" id="m-edit-pinned" style="width:auto; margin:0;"> 📌 상단 고정
                            </label>
                        </div>
                        <input type="text" id="m-edit-title" placeholder="매뉴얼 제목을 입력하세요">
                        <textarea id="m-edit-content" style="height:220px;" placeholder="매뉴얼 상세 내용을 입력하세요"></textarea>
                        <div style="display:flex; gap:10px;">
                            <button onclick="saveManualData()" class="btn-ui" style="flex:1;">💾 저장 / 업데이트</button>
                            <button onclick="openConfirmModal()" class="btn-ui btn-danger" style="width:110px;">🗑️ 매뉴얼 삭제</button>
                        </div>
                    </div>
                </div>

                <div id="view-admin-permissions" class="tab-enter" style="display:none;">
                    <div class="doc-title">스태프 접근 권한 관리</div>
                    <div class="content-card" style="margin-bottom:20px;">
                        <div style="display:flex; gap:10px;">
                            <input type="text" id="perm-target-id" placeholder="대상 디스코드 유저 ID 입력" style="margin:0;">
                            <button onclick="updatePermission('whitelist', 'add')" class="btn-ui">화이트리스트 추가</button>
                            <button onclick="updatePermission('blacklist', 'add')" class="btn-ui btn-danger">블랙리스트 차단</button>
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
                    <div class="doc-title">실시간 활동 및 보안 로그</div>
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

        async function syncSystemState() {
            try {
                const res = await fetch('/api/state');
                if (res.status === 403) { alert("권한이 거부되었거나 변경되었습니다."); location.reload(); return; }
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

        /* ⏱️ 로딩 완료 후 3초 동안 문구 고정 및 부드러운 이행 */
        function runCustomIntro(nickname, username, avatarUrl, onComplete) {
            const introOverlay = document.getElementById('intro-overlay');
            const introProgress = document.getElementById('intro-progress');
            const introRing = document.getElementById('intro-ring');
            const introAvatar = document.getElementById('intro-avatar-img');
            const introWelcome = document.getElementById('intro-welcome');

            introAvatar.src = avatarUrl;
            introOverlay.style.display = 'flex';

            const totalDuration = (Math.random() * (2000 - 300) + 300); // 0.3~2초 로딩
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
                    introWelcome.innerText = `${nickname}(${username}) 님 환영합니다.`;
                    introWelcome.classList.add('show');

                    // 요청사항: 3초 고정 대기 후 부드럽게 화면 전환
                    setTimeout(() => {
                        introOverlay.style.opacity = '0';
                        setTimeout(() => {
                            introOverlay.style.display = 'none';
                            onComplete();
                        }, 800);
                    }, 3000);
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
            populateAdminManualSelect();
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
                }, 200);
            } else {
                targetTab.style.display = 'block';
                targetTab.classList.add('tab-enter');
                currentActiveTabId = targetTabId;
            }
        }

        function selectManualItem(idx) {
            selectedManualIndex = idx;
            document.querySelectorAll('.admin-nav').forEach(el => el.classList.remove('active'));
            transitionToTab('view-manual');
            renderCategorizedSidebar();
        }

        function switchAdminTab(tabName) {
            document.querySelectorAll('.admin-nav').forEach(el => el.classList.remove('active'));
            const navEl = document.getElementById(`nav-${tabName}`);
            if (navEl) navEl.classList.add('active');
            transitionToTab(`view-admin-${tabName}`);
        }

        function populateAdminManualSelect() {
            const selectEl = document.getElementById('m-select-target');
            if (!selectEl) return;

            selectEl.innerHTML = '<option value="NEW">➕ [신규] 새 매뉴얼 작성하기</option>';
            appState.manuals.forEach((m, idx) => {
                const opt = document.createElement('option');
                opt.value = idx;
                opt.innerText = `[${m.category || '일반'}] ${m.pinned ? '📌 ' : ''}${m.title}`;
                selectEl.appendChild(opt);
            });
        }

        function onAdminSelectManualToEdit() {
            const val = document.getElementById('m-select-target').value;
            if (val === 'NEW') {
                document.getElementById('m-edit-category').value = '';
                document.getElementById('m-edit-pinned').checked = false;
                document.getElementById('m-edit-title').value = '';
                document.getElementById('m-edit-content').value = '';
            } else {
                const idx = parseInt(val, 10);
                const target = appState.manuals[idx];
                if (target) {
                    document.getElementById('m-edit-category').value = target.category || '';
                    document.getElementById('m-edit-pinned').checked = !!target.pinned;
                    document.getElementById('m-edit-title').value = target.title || '';
                    document.getElementById('m-edit-content').value = target.content || '';
                }
            }
        }

        function renderAdminViews() {
            if (appState.role !== 'admin') return;

            document.getElementById('perm-wl-list').innerHTML = appState.user_whitelist.map(id => `
                <li><span>${id}</span><button onclick="updatePermission('whitelist', 'remove', '${id}')" class="btn-ui btn-danger" style="padding:3px 8px; font-size:12px;">삭제</button></li>
            `).join('');
            
            document.getElementById('perm-bl-list').innerHTML = appState.user_blacklist.map(id => `
                <li><span>${id}</span><button onclick="updatePermission('blacklist', 'remove', '${id}')" class="btn-ui btn-secondary" style="padding:3px 8px; font-size:12px;">해제</button></li>
            `).join('');

            document.getElementById('admin-log-box').innerHTML = appState.logs.map(l => `
                <div style="padding:3px 0; border-bottom:1px solid rgba(255,255,255,0.03); color:${l.includes('보안 경고') ? '#ef4444' : (l.includes('[어드민]') ? '#38bdf8' : '#00ffaa')};">${l}</div>
            `).join('');
        }

        async function saveManualData() {
            const selectVal = document.getElementById('m-select-target').value;
            const category = document.getElementById('m-edit-category').value.trim() || '공통 매뉴얼';
            const pinned = document.getElementById('m-edit-pinned').checked;
            const title = document.getElementById('m-edit-title').value.trim();
            const content = document.getElementById('m-edit-content').value.trim();
            if(!title) return alert('제목을 입력해주세요.');

            let updatedManuals = [...appState.manuals];
            const manualObj = { category, pinned, title, content };

            if (selectVal === 'NEW') {
                updatedManuals.push(manualObj);
            } else {
                const editIdx = parseInt(selectVal, 10);
                updatedManuals[editIdx] = manualObj;
            }

            await sendAdminAction({ action: 'save_manual', manuals: updatedManuals, title });
            document.getElementById('m-select-target').value = 'NEW';
            onAdminSelectManualToEdit();
        }

        /* 🚨 커스텀 삭제 확인 모달 제어 */
        function openConfirmModal() {
            const selectVal = document.getElementById('m-select-target').value;
            if (selectVal === 'NEW') return alert('삭제할 매뉴얼을 상단 드롭다운에서 선택해 주세요.');

            const idx = parseInt(selectVal, 10);
            const target = appState.manuals[idx];
            
            document.getElementById('modal-delete-text').innerText = `'${target.title}' 매뉴얼을 정말 삭제하시겠습니까?\n이 작업은 즉시 적용되며 저장소에 기록됩니다.`;
            document.getElementById('custom-confirm-modal').style.display = 'flex';
        }

        function closeConfirmModal() {
            document.getElementById('custom-confirm-modal').style.display = 'none';
        }

        async function confirmExecuteDelete() {
            closeConfirmModal();
            const selectVal = document.getElementById('m-select-target').value;
            const idx = parseInt(selectVal, 10);
            
            let updatedManuals = appState.manuals.filter((_, i) => i !== idx);
            await sendAdminAction({ action: 'delete_manual', manuals: updatedManuals, title: appState.manuals[idx]?.title });
            
            selectedManualIndex = 0;
            document.getElementById('m-select-target').value = 'NEW';
            onAdminSelectManualToEdit();
        }

        async function updatePermission(type, act, targetId = null) {
            const id = targetId || document.getElementById('perm-target-id').value.trim();
            if (!id) return alert('디스코드 유저 ID를 입력하세요.');

            let wl = [...appState.user_whitelist];
            let bl = [...appState.user_blacklist];

            if (type === 'whitelist') {
                if (act === 'add' && !wl.includes(id)) wl.push(id);
                if (act === 'remove') wl = wl.filter(i => i !== id);
            } else {
                if (act === 'add' && !bl.includes(id)) bl.push(id);
                if (act === 'remove') bl = bl.filter(i => i !== id);
            }

            await sendAdminAction({ action: `${act}_${type}`, user_whitelist: wl, user_blacklist: bl, target_id: id });
            document.getElementById('perm-target-id').value = '';
        }

        async function sendAdminAction(payload) {
            const res = await fetch('/api/admin_update', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            if (res.ok) syncSystemState();
        }

        syncSystemState();
        setInterval(syncSystemState, 3000);
    </script>
</body>
</html>
"""

@app.route('/')
def main_page():
    return MAIN_HTML_TEMPLATE.replace('__CLIENT_ID__', CLIENT_ID)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "인증 코드 오류가 발생했습니다.", 400

    redirect_uri = f"{BASE_URL}/callback"
    token_data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }
    res = requests.post('https://discord.com/api/v10/oauth2/token', data=token_data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
    
    if res.status_code == 200:
        access_token = res.json().get('access_token')
        user_res = requests.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'})
        if user_res.status_code == 200:
            user_info = user_res.json()
            user_id = str(user_info.get('id'))
            data = load_data()

            if user_id in data.get('user_blacklist', []):
                return "<h2 style='color:#ef4444; text-align:center; margin-top:100px;'>접근 차단: 블랙리스트 계정입니다.</h2>", 403

            if user_id in data.get('admin_whitelist', []):
                session['user'] = user_info
                session['role'] = 'admin'
                add_log(data, "어드민", user_info.get('username'), f"시스템 로그인 성공 (어드민 권한)")
            else:
                if data.get('user_whitelist') and user_id not in data.get('user_whitelist'):
                    return f"<h2 style='color:#ef4444; text-align:center; margin-top:100px;'>접근 거부: 화이트리스트에 등록되지 않았습니다. (ID: {user_id})</h2>", 403
                
                session['user'] = user_info
                session['role'] = 'staff'
                add_log(data, "스태프", user_info.get('username'), f"스태프 시스템 접속")

            save_data(data)
            return redirect('/')

    return "Discord 인증에 실패했습니다.", 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/api/state')
def get_system_state():
    user = session.get('user')
    role = session.get('role')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    data = load_data()
    user_id = str(user.get('id'))

    if role != 'admin':
        if user_id in data.get('user_blacklist', []):
            session.clear()
            return jsonify({"status": "forbidden"}), 403
        if data.get('user_whitelist') and user_id not in data.get('user_whitelist'):
            session.clear()
            return jsonify({"status": "forbidden"}), 403

    response_payload = {
        "status": "authenticated",
        "user": user,
        "role": role,
        "manuals": data.get("manuals", [])
    }

    if role == 'admin':
        response_payload["user_whitelist"] = data.get("user_whitelist", [])
        response_payload["user_blacklist"] = data.get("user_blacklist", [])
        response_payload["logs"] = data.get("logs", [])

    return jsonify(response_payload)

@app.route('/api/security_log', methods=['POST'])
def handle_security_log():
    user = session.get('user')
    if not user:
        return jsonify({"status": "unauthorized"}), 401
    
    req = request.get_json()
    action_detail = req.get('action_detail', '보안 규정 위반 행위')
    
    data = load_data()
    add_log(data, "보안 경고", user.get('username'), f"🚨 {action_detail}")
    save_data(data)
    
    return jsonify({"status": "logged"})

@app.route('/api/admin_update', methods=['POST'])
def handle_admin_update():
    if session.get('role') != 'admin':
        return jsonify({"status": "unauthorized"}), 401

    user = session.get('user')
    data = load_data()
    req = request.get_json()
    action = req.get('action')

    if 'manuals' in req: data['manuals'] = req['manuals']
    if 'user_whitelist' in req: data['user_whitelist'] = req['user_whitelist']
    if 'user_blacklist' in req: data['user_blacklist'] = req['user_blacklist']

    if action == 'save_manual': add_log(data, "어드민", user.get('username'), f"매뉴얼 저장 ({req.get('title')})")
    elif action == 'delete_manual': add_log(data, "어드민", user.get('username'), f"매뉴얼 삭제 ({req.get('title')})")
    elif action == 'add_whitelist': add_log(data, "어드민", user.get('username'), f"화이트리스트 추가 ({req.get('target_id')})")
    elif action == 'add_blacklist': add_log(data, "어드민", user.get('username'), f"블랙리스트 등록 ({req.get('target_id')})")
    elif action == 'remove_whitelist': add_log(data, "어드민", user.get('username'), f"화이트리스트 삭제 ({req.get('target_id')})")
    elif action == 'remove_blacklist': add_log(data, "어드민", user.get('username'), f"블랙리스트 해제 ({req.get('target_id')})")

    save_data(data)
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
