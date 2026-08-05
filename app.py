import os
import json
import datetime
from flask import Flask, request, render_template_string, redirect, session, jsonify
import requests
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = os.urandom(24)

# ==========================================
# ⚙️ Discord OAuth2 & 환경 설정
# ==========================================
CLIENT_ID = "1534184089144266872"
CLIENT_SECRET = "JcMp7ntF3Rx32ZYTRjyaYUWfmp0EU3co"
BASE_URL = "https://sky-aurora-admin.onrender.com"

ADMIN_SECRET_KEY = "sky_aurora_admin_secret_key_1234"
DATA_FILE = "sky_aurora_admin_data.json"
DEFAULT_ADMINS = ["1534184089144266872", "843621337066504225"]

# --------------------------------------------------
# 📁 데이터 관리 및 보안 로깅
# --------------------------------------------------
def load_data():
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
                "title": "01. 기본 보안 지침",
                "content": "본 매뉴얼 시스템에 포함된 모든 정보는 외부 유출이 엄격히 금지됩니다.\n\n1. 본 시스템의 화면을 캡처하거나 촬영하는 행위를 금지합니다.\n2. 인증 계정은 타인에게 공유할 수 없습니다.\n3. 시스템 이용 시 접속 IP 및 접근 위치가 실시간 기록됩니다."
            },
            {
                "id": 2,
                "title": "02. 스태프 업무 수칙",
                "content": "SKY AURORA 스태프 업무 수행 시 아래 수칙을 준수해야 합니다.\n\n- 모든 변경 사항은 관리자 승인 후 반영되어야 합니다.\n- 시스템 장애 및 이상 접근 감지 시 즉시 보고를 진행합니다.\n- 공지사항을 정기적으로 확인하고 업데이트 내역을 숙지하세요."
            }
        ],
        "logs": []
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_log(data, category, user_name, action):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{now}] [{category}] {user_name}: {action}"
    if "logs" not in data:
        data["logs"] = []
    data["logs"].insert(0, log_entry)

def check_admin_auth():
    auth_key = request.headers.get('X-Admin-Key')
    return auth_key == ADMIN_SECRET_KEY

# --------------------------------------------------
# 🎨 메인 프론트엔드 HTML (매뉴얼 인터페이스 중심 + 어드민 통합)
# --------------------------------------------------
MAIN_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, shrink-to-fit=no">
    <title>SKY AURORA STAFF MANUAL & CONTROL SYSTEM</title>
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

        /* 🛡️ 강력 보안 오버레이 */
        #security-overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: #000000;
            z-index: 99999999; display: none; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px;
        }
        .alert-icon { font-size: 80px; color: #ff2d55; margin-bottom: 20px; animation: pulse 1.2s infinite ease-in-out; }
        .alert-main-text { font-size: 26px; font-weight: bold; color: #ff2d55; letter-spacing: -0.5px; margin-bottom: 12px; font-family: 'GmarketSansBold', sans-serif; text-shadow: 0 0 20px rgba(255, 45, 85, 0.6); }
        .alert-sub-text { font-size: 15px; color: #a0aec0; font-family: 'Pretendard', sans-serif; line-height: 1.6; }
        @keyframes pulse { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.15); opacity: 0.7; } 100% { transform: scale(1); opacity: 1; } }

        /* 🌌 배경 애니메이션 Canvas */
        #bg-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 1; }

        /* 🖼️ 메인 컨테이너 (매뉴얼 디자인 체계) */
        .container {
            position: relative; z-index: 2; width: 94%; max-width: 1250px; height: 90vh;
            background: rgba(8, 12, 24, 0.82); backdrop-filter: blur(25px); border: 1px solid rgba(0, 255, 200, 0.25);
            border-radius: 24px; box-shadow: 0 0 60px rgba(0, 255, 170, 0.12), inset 0 0 30px rgba(0, 255, 170, 0.03);
            display: flex; flex-direction: column; overflow: hidden; animation: containerAppear 0.9s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes containerAppear { 0% { opacity: 0; transform: translateY(30px) scale(0.95); } 100% { opacity: 1; transform: translateY(0) scale(1); } }

        /* 🔝 헤더 영역 */
        header { padding: 18px 28px; background: rgba(5, 8, 18, 0.92); border-bottom: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between; align-items: center; }
        header h1 { font-size: 20px; font-weight: bold; letter-spacing: 1px; background: linear-gradient(90deg, #00f2fe, #4facfe, #00ffaa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: glowText 3s infinite alternate; }
        @keyframes glowText { 0% { filter: drop-shadow(0 0 2px rgba(0, 242, 254, 0.2)); } 100% { filter: drop-shadow(0 0 12px rgba(0, 255, 170, 0.7)); } }
        
        .header-controls { display: flex; align-items: center; gap: 14px; }
        .badge-admin { background: rgba(255, 45, 85, 0.2); border: 1px solid #ff2d55; color: #ff2d55; font-size: 11px; padding: 3px 8px; border-radius: 6px; font-family: 'Pretendard'; }
        .badge-staff { background: rgba(0, 255, 170, 0.2); border: 1px solid #00ffaa; color: #00ffaa; font-size: 11px; padding: 3px 8px; border-radius: 6px; font-family: 'Pretendard'; }
        .avatar-img { width: 36px; height: 36px; border-radius: 50%; border: 2px solid #00ffaa; object-fit: cover; box-shadow: 0 0 10px rgba(0, 255, 170, 0.4); }
        .logout-btn { font-family: 'Pretendard', sans-serif; color: #8a99ad; text-decoration: none; font-size: 12px; padding: 6px 14px; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; transition: all 0.3s ease; }
        .logout-btn:hover { color: #fff; border-color: #00ffaa; box-shadow: 0 0 12px rgba(0, 255, 170, 0.3); background: rgba(0, 255, 170, 0.1); }

        /* 🔐 로그인 카드 영역 */
        .login-box { padding: 50px 28px; text-align: center; margin: auto; max-width: 420px; width: 100%; background: rgba(13, 20, 38, 0.8); border: 1px solid rgba(0, 255, 170, 0.2); border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.6), 0 0 25px rgba(0, 255, 170, 0.1); animation: fadeIn 0.6s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
        .discord-btn { display: flex; align-items: center; justify-content: center; gap: 12px; width: 100%; padding: 15px; background: #5865F2; color: white; text-decoration: none; border-radius: 12px; font-family: 'Pretendard', sans-serif; font-weight: bold; font-size: 15px; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: 0 4px 15px rgba(88, 101, 242, 0.4); cursor: pointer; border: none; margin-bottom: 12px; }
        .discord-btn:hover { background: #4752C4; transform: translateY(-2px); box-shadow: 0 8px 25px rgba(88, 101, 242, 0.7); }
        .admin-login-btn { background: linear-gradient(135deg, #1e293b, #0f172a); border: 1px solid rgba(255,255,255,0.15); color: #cbd5e1; }
        .admin-login-btn:hover { border-color: #38bdf8; color: #38bdf8; box-shadow: 0 4px 15px rgba(56, 189, 248, 0.3); }

        /* 🖥️ 대시보드 구조 (좌측 사이드바 + 우측 메인 영역) */
        .dashboard { display: flex; flex: 1; overflow: hidden; }
        .sidebar { width: 280px; background: rgba(0, 0, 0, 0.4); border-right: 1px solid rgba(255, 255, 255, 0.08); padding: 24px 14px; overflow-y: auto; display: flex; flex-direction: column; justify-content: space-between; }
        .sidebar-section-title { font-size: 11px; color: #00ffaa; letter-spacing: 1.5px; margin: 18px 0 10px 8px; text-transform: uppercase; }
        .sidebar-section-title:first-child { margin-top: 0; }

        /* 🌈 매뉴얼 사이트 스타일의 오로라 버튼 프레임워크 */
        .aurora-btn-wrapper { position: relative; margin-bottom: 10px; border-radius: 14px; overflow: hidden; padding: 2px; background: rgba(255, 255, 255, 0.03); transition: transform 0.25s ease, box-shadow 0.3s ease; }
        .aurora-btn-wrapper::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: conic-gradient(from 0deg, transparent 0%, #ff007f 25%, #7928ca 50%, #ff0080 75%, transparent 100%); animation: rotateAurora 4s linear infinite; opacity: 0; transition: opacity 0.3s ease; }
        .aurora-btn-wrapper:hover::before { opacity: 1; }
        .aurora-btn-wrapper:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(255, 0, 128, 0.3); }
        .aurora-btn-wrapper.active::before { opacity: 1; background: conic-gradient(from 0deg, transparent 0%, #00ffaa 25%, #00d2ff 50%, #0051ff 75%, #00ffaa 100%) !important; animation: rotateAurora 2s linear infinite !important; }
        .aurora-btn-wrapper.active { box-shadow: 0 0 25px rgba(0, 255, 170, 0.4); }
        .aurora-btn-wrapper.admin-nav.active::before { background: conic-gradient(from 0deg, transparent 0%, #ff2d55 25%, #ff007f 50%, #38bdf8 75%, #ff2d55 100%) !important; }
        
        .item-btn { position: relative; z-index: 1; width: 100%; text-align: left; padding: 14px 18px; background: rgba(10, 16, 32, 0.95); border: none; color: #8a99ad; border-radius: 12px; cursor: pointer; font-size: 14px; transition: color 0.2s, background 0.2s; display: block; font-family: 'Pretendard', sans-serif; font-weight: 600; }
        .aurora-btn-wrapper:hover .item-btn { color: #ff77c6; }
        .aurora-btn-wrapper.active .item-btn { color: #00ffaa; font-weight: bold; background: rgba(6, 24, 38, 0.95); }
        .aurora-btn-wrapper.admin-nav.active .item-btn { color: #38bdf8; }
        @keyframes rotateAurora { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

        /* 📄 우측 메인 콘텐츠 영역 */
        .main-content { flex: 1; padding: 36px; overflow-y: auto; display: flex; flex-direction: column; position: relative; }
        .content-card { background: rgba(5, 8, 17, 0.65); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 18px; padding: 28px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        
        .doc-title { font-size: 22px; margin-bottom: 20px; color: #ffffff; border-bottom: 1px solid rgba(255, 255, 255, 0.12); padding-bottom: 16px; letter-spacing: 0.5px; display: flex; align-items: center; gap: 10px; }
        .doc-title::before { content: ''; display: inline-block; width: 4px; height: 22px; background: #00ffaa; border-radius: 2px; box-shadow: 0 0 10px #00ffaa; }
        .doc-title.admin-title::before { background: #38bdf8; box-shadow: 0 0 10px #38bdf8; }
        .doc-body { font-family: 'Pretendard', sans-serif; font-weight: 500; font-size: 15px; line-height: 1.9; color: #cbd5e1; white-space: pre-wrap; flex: 1; background: rgba(0, 0, 0, 0.25); padding: 24px; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.05); }

        /* 🛠️ 어드민 컨트롤 폼 폼 UI */
        input, textarea { width: 100%; background: rgba(3, 5, 9, 0.8); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.12); padding: 12px 16px; border-radius: 10px; margin-bottom: 12px; outline: none; font-family: 'Pretendard', sans-serif; }
        input:focus, textarea:focus { border-color: #38bdf8; box-shadow: 0 0 15px rgba(56, 189, 248, 0.3); }
        .btn-ui { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; border: none; padding: 10px 20px; border-radius: 10px; font-weight: 700; cursor: pointer; font-family: 'Pretendard', sans-serif; transition: all 0.2s ease; }
        .btn-ui:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(37, 99, 235, 0.4); }
        .btn-danger { background: linear-gradient(135deg, #ef4444, #b91c1c); }
        .btn-danger:hover { box-shadow: 0 4px 15px rgba(239, 68, 68, 0.4); }
        .btn-secondary { background: linear-gradient(135deg, #475569, #334155); }

        ul.data-list { list-style: none; padding: 0; margin: 0; }
        ul.data-list li { background: rgba(10, 16, 32, 0.7); padding: 12px 16px; margin-bottom: 8px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.05); display: flex; justify-content: space-between; align-items: center; font-family: 'Pretendard', sans-serif; font-size: 14px; }
        
        .animated-tab { animation: manualEnter 0.45s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        @keyframes manualEnter { 0% { opacity: 0; transform: translateY(25px) scale(0.98); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
    </style>
    <script>
        // 🔒 개발자 도구 / 우클릭 / 드래그 / 단축키 차단 (보안 강화)
        document.addEventListener('contextmenu', e => e.preventDefault());
        document.addEventListener('selectstart', e => e.preventDefault());
        document.addEventListener('dragstart', e => e.preventDefault());

        function triggerSecurityLock() {
            const overlay = document.getElementById('security-overlay');
            if (overlay) overlay.style.display = 'flex';
        }

        function releaseSecurityLock() {
            const overlay = document.getElementById('security-overlay');
            if (overlay) overlay.style.display = 'none';
        }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Shift' || e.key === 'Meta' || e.key === 'Alt' || e.key === 'Control' || e.key === 'PrintScreen' || e.key === 'F12') {
                triggerSecurityLock();
            }
            const k = e.key.toLowerCase();
            if ((e.ctrlKey && ['c', 'v', 'u', 's', 'p', 'a', 'i', 'j'].includes(k)) || (e.metaKey && ['c', 'v', 'u', 's', 'p', 'a', 'i', 'j'].includes(k))) {
                triggerSecurityLock();
            }
        }, true);

        document.addEventListener('keyup', function(e) {
            if (!e.shiftKey && !e.metaKey && !e.ctrlKey && !e.altKey) { releaseSecurityLock(); }
        });

        window.addEventListener('blur', triggerSecurityLock);
        window.addEventListener('focus', releaseSecurityLock);
        document.addEventListener('visibilitychange', function() { if (document.hidden) triggerSecurityLock(); else releaseSecurityLock(); });
        window.addEventListener('pagehide', triggerSecurityLock);
        document.addEventListener('mouseleave', function(e) { if (e.clientY <= 0) triggerSecurityLock(); });

        function login(target) {
            const redirectUri = encodeURIComponent(window.location.origin + '/callback?target=' + target);
            location.href = `https://discord.com/oauth2/authorize?client_id=__CLIENT_ID__&response_type=code&redirect_uri=${redirectUri}&scope=identify`;
        }
    </script>
</head>
<body>
    <div id="security-overlay">
        <div class="alert-icon">⚠️</div>
        <div class="alert-main-text">보안 경고: 무단 캡처 및 복제 금지</div>
        <div class="alert-sub-text">
            본 시스템의 정보 무단 캡처, 복사, 개발자 도구 활용 시도는 엄격히 금지되어 있습니다.<br>
            접근 시도 및 접속 IP 정보가 보안 기록에 실시간 저장됩니다.
        </div>
    </div>

    <canvas id="bg-canvas"></canvas>

    <div class="container">
        <header>
            <h1>SKY AURORA STAFF MANUAL</h1>
            <div id="user-header-info" class="header-controls" style="display:none;">
                <span id="user-role-badge" class="badge-staff">STAFF</span>
                <img id="user-avatar" src="" alt="Avatar" class="avatar-img" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                <span id="user-name" style="font-size: 13px; color: #00ffaa; font-family: 'Pretendard';"></span>
                <a href="/logout" class="logout-btn">로그아웃</a>
            </div>
        </header>

        <!-- 1️⃣ 로그인 선택 화면 -->
        <div id="login-box" class="login-box">
            <h2 style="font-size: 18px; color: #e2e8f0; margin-bottom: 24px; font-family: 'GmarketSansBold';">🔒 시스템 접근 인증</h2>
            <button onclick="login('user')" class="discord-btn">
                <svg width="22" height="17" viewBox="0 0 127.14 96.36" fill="currentColor">
                    <path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1,105.25,105.25,0,0,0,32.19-16.14c2.64-27.38-4.51-51.11-18.91-72.15ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,45.91,53.87,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,45.91,96.1,53,91.08,65.69,84.69,65.69Z"/>
                </svg>
                스태프 매뉴얼 접속
            </button>
            <button onclick="login('admin')" class="discord-btn admin-login-btn">
                🔑 어드민 관제 시스템 접속
            </button>
        </div>

        <!-- 2️⃣ 매뉴얼 & 어드민 관제 통합 대시보드 -->
        <div id="main-dashboard" class="dashboard" style="display:none;">
            <div class="sidebar">
                <div>
                    <div class="sidebar-section-title">Manual Navigation</div>
                    <div id="manual-sidebar-list"></div>

                    <div id="admin-menu-section" style="display:none; margin-top:20px;">
                        <div class="sidebar-section-title" style="color:#38bdf8;">Admin Control Center</div>
                        <div class="aurora-btn-wrapper admin-nav" id="nav-m-manage">
                            <button class="item-btn" onclick="switchAdminTab('m-manage')">📖 매뉴얼 작성/관리</button>
                        </div>
                        <div class="aurora-btn-wrapper admin-nav" id="nav-permissions">
                            <button class="item-btn" onclick="switchAdminTab('permissions')">🛡️ 권한 제어 센터</button>
                        </div>
                        <div class="aurora-btn-wrapper admin-nav" id="nav-logs">
                            <button class="item-btn" onclick="switchAdminTab('logs')">📜 실시간 접속 로그</button>
                        </div>
                    </div>
                </div>
            </div>

            <div class="main-content">
                <!-- 📖 스태프 매뉴얼 뷰어 -->
                <div id="view-manual" class="animated-tab" style="display:block;">
                    <div id="doc-title" class="doc-title">매뉴얼 불러오는 중...</div>
                    <div id="doc-body" class="doc-body"></div>
                </div>

                <!-- 🛠️ 어드민: 매뉴얼 편집 -->
                <div id="view-admin-m-manage" class="animated-tab" style="display:none;">
                    <div class="doc-title admin-title">매뉴얼 데이터 편집 및 추가</div>
                    <div class="content-card">
                        <input type="text" id="m-edit-title" placeholder="매뉴얼 제목을 입력하세요">
                        <textarea id="m-edit-content" style="height:260px;" placeholder="매뉴얼 상세 내용을 입력하세요"></textarea>
                        <div style="display:flex; gap:10px;">
                            <button onclick="saveManualData()" class="btn-ui" style="flex:1;">💾 매뉴얼 저장/수정</button>
                            <button onclick="deleteManualData()" class="btn-ui btn-danger" style="width:110px;">🗑️ 삭제</button>
                            <button onclick="resetManualForm()" class="btn-ui btn-secondary" style="width:110px;">새로작성</button>
                        </div>
                    </div>
                </div>

                <!-- 🛡️ 어드민: 권한 제어 센터 -->
                <div id="view-admin-permissions" class="animated-tab" style="display:none;">
                    <div class="doc-title admin-title">스태프 접속 권한 제어</div>
                    <div class="content-card" style="margin-bottom:24px;">
                        <div style="display:flex; gap:12px;">
                            <input type="text" id="perm-target-id" placeholder="대상 디스코드 유저 ID 입력" style="margin:0;">
                            <button onclick="updatePermission('whitelist', 'add')" class="btn-ui">화이트리스트 추가</button>
                            <button onclick="updatePermission('blacklist', 'add')" class="btn-ui btn-danger">블랙리스트 등록</button>
                        </div>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">
                        <div class="content-card">
                            <h3 style="color:#4ade80; margin-bottom:14px; font-size:16px;">화이트리스트 목록</h3>
                            <ul id="perm-wl-list" class="data-list"></ul>
                        </div>
                        <div class="content-card">
                            <h3 style="color:#f87171; margin-bottom:14px; font-size:16px;">블랙리스트 목록</h3>
                            <ul id="perm-bl-list" class="data-list"></ul>
                        </div>
                    </div>
                </div>

                <!-- 📜 어드민: 실시간 로그 -->
                <div id="view-admin-logs" class="animated-tab" style="display:none;">
                    <div class="doc-title admin-title">실시간 보안 및 활동 로그</div>
                    <div class="content-card">
                        <div id="admin-log-box" style="background:rgba(3, 5, 9, 0.9); padding:18px; border-radius:12px; font-family:monospace; font-size:13px; height:480px; overflow-y:auto; border:1px solid rgba(255,255,255,0.05);"></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 🌌 오로라 백그라운드 애니메이션 구현 (매뉴얼 인터페이스 차용)
        const canvas = document.getElementById('bg-canvas');
        const ctx = canvas.getContext('2d');
        function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
        window.addEventListener('resize', resize); resize();
        const stars = Array.from({ length: 160 }, () => ({ x: Math.random() * canvas.width, y: Math.random() * canvas.height, size: Math.random() * 2, alpha: Math.random(), speed: Math.random() * 0.012 + 0.005 }));
        let tick = 0;
        function drawRibbonAurora(yOffset, waveHeight, color1, color2, speedMult) {
            ctx.save(); ctx.beginPath();
            const startY = yOffset + Math.sin(tick * speedMult) * 25; ctx.moveTo(0, startY);
            for (let x = 0; x <= canvas.width; x += 25) {
                const y = yOffset + Math.sin(x * 0.0025 + tick * speedMult) * waveHeight + Math.cos(x * 0.0012 + tick * 0.6) * (waveHeight * 0.6);
                ctx.lineTo(x, y);
            }
            ctx.lineTo(canvas.width, startY + 240); ctx.lineTo(0, startY + 240); ctx.closePath();
            const grad = ctx.createLinearGradient(0, yOffset - 50, canvas.width, yOffset + 250);
            grad.addColorStop(0, color1); grad.addColorStop(1, color2);
            ctx.fillStyle = grad; ctx.filter = 'blur(28px)'; ctx.fill(); ctx.restore();
        }
        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            stars.forEach(s => { s.alpha += s.speed; if (s.alpha > 1 || s.alpha < 0) s.speed = -s.speed; ctx.fillStyle = `rgba(255, 255, 255, ${Math.abs(s.alpha)})`; ctx.beginPath(); ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2); ctx.fill(); });
            tick += 0.015;
            drawRibbonAurora(canvas.height * 0.05, 75, 'rgba(0, 255, 170, 0.35)', 'rgba(0, 150, 255, 0.04)', 0.8);
            drawRibbonAurora(canvas.height * 0.09, 95, 'rgba(0, 180, 255, 0.25)', 'rgba(140, 0, 255, 0.03)', 1.2);
            drawRibbonAurora(canvas.height * 0.15, 60, 'rgba(255, 0, 128, 0.15)', 'rgba(0, 255, 170, 0.02)', 0.5);
            requestAnimationFrame(animate);
        }
        animate();

        // 🔄 데이터 및 상태 관리
        let appState = { user: null, role: null, manuals: [], user_whitelist: [], user_blacklist: [], logs: [] };
        let selectedManualIndex = 0;

        async function syncSystemState() {
            try {
                const res = await fetch('/api/state');
                if (res.status === 403) {
                    alert("권한이 차단되었거나 변경되었습니다.");
                    location.reload();
                    return;
                }
                if (res.ok) {
                    const data = await res.json();
                    if (data.status === 'unauthorized') return;

                    appState = data;
                    document.getElementById('login-box').style.display = 'none';
                    document.getElementById('main-dashboard').style.display = 'flex';
                    document.getElementById('user-header-info').style.display = 'flex';

                    // 프로필 설정
                    const avatarUrl = data.user.avatar 
                        ? `https://cdn.discordapp.com/avatars/${data.user.id}/${data.user.avatar}.png` 
                        : 'https://cdn.discordapp.com/embed/avatars/0.png';
                    document.getElementById('user-avatar').src = avatarUrl;
                    document.getElementById('user-name').innerText = data.user.username;

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

                    renderManualSidebar();
                    renderAdminViews();
                }
            } catch(e) { console.error("Sync error:", e); }
        }

        function renderManualSidebar() {
            const listEl = document.getElementById('manual-sidebar-list');
            listEl.innerHTML = appState.manuals.map((m, idx) => `
                <div class="aurora-btn-wrapper ${idx === selectedManualIndex ? 'active' : ''}">
                    <button class="item-btn" onclick="selectManualItem(${idx})">${m.title}</button>
                </div>
            `).join('');

            if (appState.manuals.length > 0) {
                const current = appState.manuals[selectedManualIndex] || appState.manuals[0];
                document.getElementById('doc-title').innerText = current.title;
                document.getElementById('doc-body').innerText = current.content;
            }
        }

        function selectManualItem(idx) {
            selectedManualIndex = idx;
            hideAllTabs();
            document.getElementById('view-manual').style.display = 'block';
            document.querySelectorAll('.admin-nav').forEach(el => el.classList.remove('active'));
            renderManualSidebar();
        }

        function switchAdminTab(tabName) {
            hideAllTabs();
            document.querySelectorAll('.admin-nav').forEach(el => el.classList.remove('active'));
            document.getElementById(`nav-${tabName}`).classList.add('active');
            document.getElementById(`view-admin-${tabName}`).style.display = 'block';
        }

        function hideAllTabs() {
            document.getElementById('view-manual').style.display = 'none';
            document.getElementById('view-admin-m-manage').style.display = 'none';
            document.getElementById('view-admin-permissions').style.display = 'none';
            document.getElementById('view-admin-logs').style.display = 'none';
        }

        function renderAdminViews() {
            if (appState.role !== 'admin') return;

            // 1. 권한 목록
            document.getElementById('perm-wl-list').innerHTML = appState.user_whitelist.map(id => `
                <li><span>${id}</span><button onclick="updatePermission('whitelist', 'remove', '${id}')" class="btn-ui btn-danger" style="padding:4px 8px; font-size:12px;">삭제</button></li>
            `).join('');
            
            document.getElementById('perm-bl-list').innerHTML = appState.user_blacklist.map(id => `
                <li><span>${id}</span><button onclick="updatePermission('blacklist', 'remove', '${id}')" class="btn-ui btn-secondary" style="padding:4px 8px; font-size:12px;">해제</button></li>
            `).join('');

            // 2. 로그 목록
            document.getElementById('admin-log-box').innerHTML = appState.logs.map(l => `
                <div style="padding:4px 0; border-bottom:1px solid rgba(255,255,255,0.03); color:${l.includes('[어드민]') ? '#38bdf8' : '#00ffaa'};">${l}</div>
            `).join('');
        }

        // 어드민 제어 핸들러
        async function saveManualData() {
            const title = document.getElementById('m-edit-title').value.trim();
            const content = document.getElementById('m-edit-content').value.trim();
            if(!title) return alert('제목을 입력하세요.');

            let updatedManuals = [...appState.manuals];
            if (selectedManualIndex < updatedManuals.length) {
                updatedManuals[selectedManualIndex] = { title, content };
            } else {
                updatedManuals.push({ title, content });
            }

            await sendAdminAction({ action: 'save_manual', manuals: updatedManuals, title });
            resetManualForm();
        }

        async function deleteManualData() {
            if (confirm('선택된 매뉴얼을 삭제하시겠습니까?')) {
                let updatedManuals = appState.manuals.filter((_, idx) => idx !== selectedManualIndex);
                await sendAdminAction({ action: 'delete_manual', manuals: updatedManuals, title: appState.manuals[selectedManualIndex]?.title });
                selectedManualIndex = 0;
                resetManualForm();
            }
        }

        function resetManualForm() {
            selectedManualIndex = appState.manuals.length;
            document.getElementById('m-edit-title').value = '';
            document.getElementById('m-edit-content').value = '';
        }

        async function updatePermission(type, act, targetId = null) {
            const id = targetId || document.getElementById('perm-target-id').value.trim();
            if (!id) return alert('유저 ID를 입력하세요.');

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
        setInterval(syncSystemState, 2000);
    </script>
</body>
</html>
"""

@app.route('/')
def main_page():
    return MAIN_HTML_TEMPLATE.replace('__CLIENT_ID__', CLIENT_ID)

# --------------------------------------------------
# 🔑 Discord OAuth2 통합 처리
# --------------------------------------------------
@app.route('/callback')
def callback():
    code = request.args.get('code')
    target = request.args.get('target', 'user')
    if not code:
        return "인증 오류가 발생했습니다.", 400

    redirect_uri = f"{BASE_URL}/callback?target={target}"
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

            if target == 'admin':
                if user_id not in data.get('admin_whitelist', []):
                    return f"<h2 style='color:#ef4444; text-align:center; margin-top:100px; font-family:sans-serif;'>접근 거부: 어드민 권한이 필요합니다. (ID: {user_id})</h2>", 403
                session['user'] = user_info
                session['role'] = 'admin'
                add_log(data, "어드민", user_info.get('username'), f"어드민 시스템 로그인 성공 (ID: {user_id})")
                save_data(data)
                return redirect('/')

            else:
                if user_id in data.get('user_blacklist', []):
                    return "<h2 style='color:#ef4444; text-align:center; margin-top:100px; font-family:sans-serif;'>접근 차단: 블랙리스트 대상 계정입니다.</h2>", 403

                if data.get('user_whitelist') and user_id not in data.get('user_whitelist'):
                    return "<h2 style='color:#ef4444; text-align:center; margin-top:100px; font-family:sans-serif;'>접근 거부: 화이트리스트 등록 유저만 이용 가능합니다.</h2>", 403

                session['user'] = user_info
                session['role'] = 'staff'
                add_log(data, "스태프 매뉴얼", user_info.get('username'), f"스태프 매뉴얼 접속 (ID: {user_id})")
                save_data(data)
                return redirect('/')

    return "Discord 인증에 실패했습니다.", 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --------------------------------------------------
# 🛠️ 데이터 연동 API (웹 + PyQt 시스템)
# --------------------------------------------------
@app.route('/api/state')
def get_system_state():
    user = session.get('user')
    role = session.get('role')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    data = load_data()
    user_id = str(user.get('id'))

    # 스태프 권한 체크
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

    if action == 'save_manual': add_log(data, "어드민", user.get('username'), f"매뉴얼 저장/수정 ({req.get('title')})")
    elif action == 'delete_manual': add_log(data, "어드민", user.get('username'), f"매뉴얼 삭제 ({req.get('title')})")
    elif action == 'add_whitelist': add_log(data, "어드민", user.get('username'), f"스태프 화이트리스트 추가 ({req.get('target_id')})")
    elif action == 'add_blacklist': add_log(data, "어드민", user.get('username'), f"스태프 블랙리스트 추가 ({req.get('target_id')})")
    elif action == 'remove_whitelist': add_log(data, "어드민", user.get('username'), f"스태프 화이트리스트 삭제 ({req.get('target_id')})")
    elif action == 'remove_blacklist': add_log(data, "어드민", user.get('username'), f"스태프 블랙리스트 해제 ({req.get('target_id')})")

    save_data(data)
    return jsonify({"status": "ok"})

# 외부 PyQt 애플리케이션 지원 REST API
@app.route('/api/admin/manuals', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_admin_manuals():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = load_data()
    if request.method == 'GET':
        return jsonify(data.get("manuals", []))

    elif request.method == 'POST':
        req_data = request.json
        new_id = max([m.get('id', 0) for m in data.get("manuals", [])], default=0) + 1
        new_manual = { "id": new_id, "title": req_data.get("title", ""), "content": req_data.get("content", "") }
        data["manuals"].append(new_manual)
        add_log(data, "외부 API", "ADMIN_APP", f"매뉴얼 추가 ({new_manual['title']})")
        save_data(data)
        return jsonify({"status": "success", "manual": new_manual})

    elif request.method == 'PUT':
        req_data = request.json
        target_id = req_data.get("id")
        for m in data.get("manuals", []):
            if m.get('id') == target_id:
                m['title'] = req_data.get("title", m['title'])
                m['content'] = req_data.get("content", m['content'])
                add_log(data, "외부 API", "ADMIN_APP", f"매뉴얼 수정 ({m['title']})")
                save_data(data)
                return jsonify({"status": "success", "manual": m})
        return jsonify({"error": "Not found"}), 404

    elif request.method == 'DELETE':
        manual_id = request.args.get('id', type=int)
        data["manuals"] = [m for m in data.get("manuals", []) if m.get('id') != manual_id]
        add_log(data, "외부 API", "ADMIN_APP", f"매뉴얼 삭제 (ID: {manual_id})")
        save_data(data)
        return jsonify({"status": "success"})

@app.route('/api/admin/blacklist', methods=['GET', 'POST', 'DELETE'])
def api_admin_blacklist():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401

    data = load_data()
    if request.method == 'GET':
        return jsonify(data.get("user_blacklist", []))

    elif request.method == 'POST':
        discord_id = str(request.json.get('discord_id', '')).strip()
        if discord_id and discord_id not in data.get("user_blacklist", []):
            data.setdefault("user_blacklist", []).append(discord_id)
            add_log(data, "외부 API", "ADMIN_APP", f"블랙리스트 등록 ({discord_id})")
            save_data(data)
        return jsonify({"status": "success", "blacklist": data.get("user_blacklist", [])})

    elif request.method == 'DELETE':
        discord_id = str(request.args.get('discord_id', '')).strip()
        if discord_id in data.get("user_blacklist", []):
            data["user_blacklist"].remove(discord_id)
            add_log(data, "외부 API", "ADMIN_APP", f"블랙리스트 해제 ({discord_id})")
            save_data(data)
        return jsonify({"status": "success", "blacklist": data.get("user_blacklist", [])})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
