import os
import requests
import sqlite3
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'sky_aurora_secret_key_9988'

# ==========================================
# ⚙️ 최초 소유자(Owner) 디스코드 ID 설정
# ==========================================
OWNER_DISCORD_ID = "843621337066504225"  # <- 요청하신 사용자 ID 적용 완료!

DISCORD_CLIENT_ID = "1534184089144266872"
DISCORD_CLIENT_SECRET = "ekHMzJEF519uQiAn94PuOPxER-51IH5s"
DISCORD_REDIRECT_URI = "https://sky-aurora-staff.onrender.com/callback"

DISCORD_AUTH_URL = (
    f"https://discord.com/api/oauth2/authorize"
    f"?client_id={DISCORD_CLIENT_ID}"
    f"&redirect_uri={DISCORD_REDIRECT_URI}"
    f"&response_type=code"
    f"&scope=identify%20email"
)

DB_FILE = 'data.db'

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 매뉴얼 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS manuals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')
    # 접속 로그 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            discord_id TEXT,
            username TEXT,
            ip_address TEXT,
            device_info TEXT,
            access_time TEXT
        )
    ''')
    # 관리자 목록 테이블
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            discord_id TEXT PRIMARY KEY,
            memo TEXT,
            created_at TEXT
        )
    ''')
    
    # 기본 매뉴얼 생성 (최초 1회)
    c.execute("SELECT COUNT(*) FROM manuals")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO manuals (title, content) VALUES (?, ?)", 
                  ("01. 기본 보안 지침", "본 매뉴얼 시스템에 포함된 모든 정보는 외부 유출이 엄격히 금지됩니다.\n\n1. 본 시스템의 화면을 캡처하거나 촬영하는 행위를 금지합니다.\n2. 인증 계정 및 코드는 타인에게 공유할 수 없습니다.\n3. 시스템 이용 시 접속 IP 및 접근 위치가 실시간 기록됩니다."))
        c.execute("INSERT INTO manuals (title, content) VALUES (?, ?)", 
                  ("02. 스태프 업무 수칙", "SKY AURORA 스태프 업무 수행 시 아래 수칙을 준수해야 합니다.\n\n- 모든 변경 사항은 관리자 승인 후 반영되어야 합니다.\n- 시스템 장애 및 이상 접근 감지 시 즉시 보고를 진행합니다.\n- 공지사항을 정기적으로 확인하고 업데이트 내역을 숙지하세요."))
        conn.commit()
    conn.close()

init_db()

def is_admin_id(discord_id):
    """소유자이거나 DB에 등록된 관리자인지 체크"""
    discord_id = str(discord_id)
    if discord_id == OWNER_DISCORD_ID:
        return True
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT discord_id FROM admins WHERE discord_id=?", (discord_id,))
    row = c.fetchone()
    conn.close()
    return row is not None

def log_access(discord_id, username):
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip and ',' in user_ip:
        user_ip = user_ip.split(',')[0].strip()
        
    device_info = request.headers.get('User-Agent', 'Unknown Device')
    now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO logs (discord_id, username, ip_address, device_info, access_time)
        VALUES (?, ?, ?, ?, ?)
    ''', (discord_id, username, user_ip, device_info, now_time))
    conn.commit()
    conn.close()

def get_manuals():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, title, content FROM manuals ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "content": r[2]} for r in rows]

def verify_admin_token(request_obj):
    """토큰 기반 관리자 권한 확인"""
    auth_header = request_obj.headers.get('Authorization')
    if not auth_header or not auth_header.startswith("Bearer "):
        return False, None
    
    token = auth_header.split(" ")[1]
    res = requests.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {token}'})
    if res.status_code != 200:
        return False, None
    
    user_info = res.json()
    discord_id = str(user_info.get('id'))
    if is_admin_id(discord_id):
        return True, user_info
    return False, None

# --- 웹 페이지 UI HTML ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>SKY AURORA STAFF 매뉴얼</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css">
    <style>
        @font-face {
            font-family: 'GmarketSansBold';
            src: url('https://fastly.jsdelivr.net/gh/projectnoonnu/noonfonts_2001@1.1/GmarketSansBold.woff') format('woff');
            font-weight: normal; font-style: normal;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; user-select: none; }
        body { font-family: 'GmarketSansBold', 'Pretendard', sans-serif; background: #060913; color: #ffffff; overflow: hidden; height: 100vh; display: flex; justify-content: center; align-items: center; }
        #bg-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 1; }
        .container { position: relative; z-index: 2; width: 90%; max-width: 1100px; height: 85vh; background: rgba(12, 18, 36, 0.75); backdrop-filter: blur(16px); border: 1px solid rgba(0, 255, 200, 0.3); border-radius: 20px; box-shadow: 0 0 50px rgba(0, 255, 170, 0.2); display: flex; flex-direction: column; overflow: hidden; }
        header { padding: 22px 30px; background: rgba(8, 14, 28, 0.85); border-bottom: 1px solid rgba(255, 255, 255, 0.1); display: flex; justify-content: space-between; align-items: center; }
        header h1 { font-size: 22px; font-weight: bold; background: linear-gradient(90deg, #00f2fe, #4facfe, #00ffaa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .user-info { display: flex; align-items: center; gap: 12px; }
        .logout-btn { color: #8a99ad; text-decoration: none; font-size: 13px; padding: 6px 14px; border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; }
        .login-box { padding: 40px 30px; text-align: center; margin: auto; max-width: 400px; width: 100%; }
        .discord-btn { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 14px; background: #5865F2; color: white; text-decoration: none; border-radius: 8px; font-family: 'Pretendard'; font-weight: bold; font-size: 15px; }
        .dashboard { display: flex; flex: 1; overflow: hidden; }
        .sidebar { width: 310px; background: rgba(0, 0, 0, 0.25); border-right: 1px solid rgba(255, 255, 255, 0.08); padding: 24px 14px; overflow-y: auto; }
        .item-btn { width: 100%; text-align: left; padding: 14px 18px; background: rgba(12, 18, 36, 0.95); border: none; color: #8a99ad; border-radius: 10px; cursor: pointer; font-size: 15px; margin-bottom: 8px; }
        .main-content { flex: 1; padding: 35px; overflow-y: auto; display: flex; flex-direction: column; }
        .doc-title { font-size: 24px; margin-bottom: 22px; color: #ffffff; border-bottom: 1px solid rgba(255, 255, 255, 0.12); padding-bottom: 14px; }
        .doc-body { font-family: 'Pretendard'; font-size: 16px; line-height: 1.85; color: #e2e8f0; white-space: pre-wrap; flex: 1; }
    </style>
</head>
<body>
    <canvas id="bg-canvas"></canvas>
    <div class="container">
        <header>
            <h1>SKY AURORA STAFF 매뉴얼</h1>
            {% if authenticated %}
                <div class="user-info">
                    <span style="font-size: 13px; color: #00ffaa;">👤 {{ username }}</span>
                    <a href="/logout" class="logout-btn">로그아웃</a>
                </div>
            {% endif %}
        </header>
        {% if not authenticated %}
            <div class="login-box">
                <h2 style="font-size: 19px; color: #e2e8f0; margin-bottom: 20px;">🔒 스태프 디스코드 인증</h2>
                <a href="/login/discord" class="discord-btn">Discord 계정으로 로그인</a>
            </div>
        {% else %}
            <div class="dashboard">
                <div class="sidebar">
                    <h2 style="font-size: 13px; color: #7f8c8d; margin-bottom: 18px;">MANUAL LIST</h2>
                    {% for item in manuals %}
                        <button class="item-btn" onclick="document.getElementById('doc-title').innerText='{{ item.title }}'; document.getElementById('doc-body').innerText='{{ item.content }}';">{{ item.title }}</button>
                    {% endfor %}
                </div>
                <div class="main-content">
                    <div id="doc-title" class="doc-title">{{ manuals[0].title if manuals else '매뉴얼이 없습니다.' }}</div>
                    <div id="doc-body" class="doc-body">{{ manuals[0].content if manuals else '' }}</div>
                </div>
            </div>
        {% endif %}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, authenticated=session.get('authenticated', False), username=session.get('username', '스태프'), manuals=get_manuals())

@app.route('/login/discord')
def login_discord():
    return redirect(DISCORD_AUTH_URL)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code: return redirect(url_for('index'))
    data = {'client_id': DISCORD_CLIENT_ID, 'client_secret': DISCORD_CLIENT_SECRET, 'grant_type': 'authorization_code', 'code': code, 'redirect_uri': DISCORD_REDIRECT_URI}
    token_res = requests.post('https://discord.com/api/v10/oauth2/token', data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'}).json()
    access_token = token_res.get('access_token')
    if not access_token: return redirect(url_for('index'))
    
    user_data = requests.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}).json()
    
    log_access(user_data.get('id'), user_data.get('username'))
    session['authenticated'] = True
    session['username'] = user_data.get('global_name') or user_data.get('username')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ==========================================
# 🛠️ 관리자 앱 통신 API
# ==========================================
@app.route('/api/admin/logs', methods=['GET'])
def api_get_logs():
    is_admin, _ = verify_admin_token(request)
    if not is_admin:
        return jsonify({"error": "Unauthorized"}), 403
        
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, discord_id, username, ip_address, device_info, access_time FROM logs ORDER BY id DESC LIMIT 100")
    logs = [{"id": r[0], "discord_id": r[1], "username": r[2], "ip_address": r[3], "device_info": r[4], "access_time": r[5]} for r in c.fetchall()]
    conn.close()
    return jsonify(logs)

@app.route('/api/admin/manuals', methods=['POST'])
def api_update_manuals():
    is_admin, _ = verify_admin_token(request)
    if not is_admin:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM manuals")
    for item in data:
        c.execute("INSERT INTO manuals (title, content) VALUES (?, ?)", (item['title'], item['content']))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# --- 👥 관리자 목록 조회 API ---
@app.route('/api/admin/users', methods=['GET'])
def api_get_admins():
    is_admin, _ = verify_admin_token(request)
    if not is_admin:
        return jsonify({"error": "Unauthorized"}), 403
        
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT discord_id, memo, created_at FROM admins ORDER BY created_at DESC")
    admins = [{"discord_id": r[0], "memo": r[1], "created_at": r[2]} for r in c.fetchall()]
    conn.close()
    return jsonify(admins)

# --- ➕ 관리자 추가 API ---
@app.route('/api/admin/users/add', methods=['POST'])
def api_add_admin():
    is_admin, _ = verify_admin_token(request)
    if not is_admin:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    discord_id = str(data.get('discord_id', '')).strip()
    memo = data.get('memo', '')
    now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not discord_id:
        return jsonify({"error": "디스코드 ID가 필요합니다."}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO admins (discord_id, memo, created_at) VALUES (?, ?, ?)", (discord_id, memo, now_time))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

# --- ❌ 관리자 삭제 API ---
@app.route('/api/admin/users/delete', methods=['POST'])
def api_delete_admin():
    is_admin, _ = verify_admin_token(request)
    if not is_admin:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    discord_id = str(data.get('discord_id', '')).strip()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM admins WHERE discord_id=?", (discord_id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
