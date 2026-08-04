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
OWNER_DISCORD_ID = "843621337066504225"

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
    c.execute('''
        CREATE TABLE IF NOT EXISTS manuals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL
        )
    ''')
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            discord_id TEXT PRIMARY KEY,
            memo TEXT,
            created_at TEXT
        )
    ''')
    
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
        
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-user-select: none !important;
            user-select: none !important;
            -webkit-touch-callout: none !important;
        }

        body {
            font-family: 'GmarketSansBold', 'Pretendard', sans-serif;
            background: #060913;
            color: #ffffff;
            overflow: hidden;
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        
        #bg-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 1; pointer-events: none; }
        
        .container {
            position: relative;
            z-index: 2;
            width: 90%;
            max-width: 1100px;
            height: 85vh;
            background: rgba(12, 18, 36, 0.75);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(0, 255, 200, 0.3);
            border-radius: 20px;
            box-shadow: 0 0 50px rgba(0, 255, 170, 0.2);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            transition: all 0.5s ease;
        }
        
        .container.theme-blue { border-color: rgba(0, 242, 254, 0.5); box-shadow: 0 0 50px rgba(0, 242, 254, 0.25); }
        .container.theme-ruby { border-color: rgba(255, 45, 85, 0.5); box-shadow: 0 0 50px rgba(255, 45, 85, 0.25); }
        
        header { padding: 22px 30px; background: rgba(8, 14, 28, 0.85); border-bottom: 1px solid rgba(255, 255, 255, 0.1); display: flex; justify-content: space-between; align-items: center; }
        header h1 { font-size: 22px; font-weight: bold; background: linear-gradient(90deg, #00f2fe, #4facfe, #00ffaa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .user-info { display: flex; align-items: center; gap: 12px; }
        .logout-btn { color: #8a99ad; text-decoration: none; font-size: 13px; padding: 6px 14px; border: 1px solid rgba(255,255,255,0.15); border-radius: 6px; transition: 0.3s; }
        .logout-btn:hover { background: rgba(255, 255, 255, 0.1); color: #fff; }
        
        .login-box { padding: 40px 30px; text-align: center; margin: auto; max-width: 400px; width: 100%; }
        .discord-btn { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 14px; background: #5865F2; color: white; text-decoration: none; border-radius: 8px; font-family: 'Pretendard'; font-weight: bold; font-size: 15px; }
        
        .dashboard { display: flex; flex: 1; overflow: hidden; }
        .sidebar { width: 310px; background: rgba(0, 0, 0, 0.25); border-right: 1px solid rgba(255, 255, 255, 0.08); padding: 24px 14px; overflow-y: auto; }
        
        /* 💡 요청하신 이미지 참고한 네온 포인트 상단 바 테두리 버튼 스타일 */
        .item-btn {
            position: relative;
            width: 100%;
            text-align: left;
            padding: 16px 18px;
            background: rgba(12, 18, 36, 0.95);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: #8a99ad;
            border-radius: 12px;
            cursor: pointer;
            font-size: 15px;
            margin-bottom: 12px;
            overflow: hidden;
            transition: all 0.3s ease;
        }

        /* 버튼 상단 네온 포인트 라인 (기본 숨김) */
        .item-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: 0%;
            height: 3px;
            transition: width 0.3s ease;
        }

        /* 🔵 푸른색 테마 버튼 선택 */
        .item-btn.active-blue {
            color: #00ffaa;
            border-color: rgba(0, 255, 170, 0.5);
            box-shadow: 0 0 15px rgba(0, 255, 170, 0.25);
            font-weight: bold;
        }
        .item-btn.active-blue::before {
            width: 70%;
            background: linear-gradient(90deg, #00f2fe, #00ffaa);
            box-shadow: 0 0 10px #00ffaa;
        }

        /* 🔴 루비색 테마 버튼 선택 */
        .item-btn.active-ruby {
            color: #ff4d6d;
            border-color: rgba(255, 45, 85, 0.5);
            box-shadow: 0 0 15px rgba(255, 45, 85, 0.3);
            font-weight: bold;
        }
        .item-btn.active-ruby::before {
            width: 70%;
            background: linear-gradient(90deg, #ff2d55, #ff4d6d);
            box-shadow: 0 0 10px #ff2d55;
        }

        .main-content { flex: 1; padding: 35px; overflow-y: auto; display: flex; flex-direction: column; }
        .doc-title { font-size: 24px; margin-bottom: 22px; color: #ffffff; border-bottom: 1px solid rgba(255, 255, 255, 0.12); padding-bottom: 14px; transition: opacity 0.3s ease, transform 0.3s ease; }
        .doc-body { font-family: 'Pretendard'; font-size: 16px; line-height: 1.85; color: #e2e8f0; white-space: pre-wrap; flex: 1; transition: opacity 0.3s ease, transform 0.3s ease; }
        
        .fade-out { opacity: 0; transform: translateY(8px); }
        .fade-in { opacity: 1; transform: translateY(0); }

        /* 🔒 강력한 캡처 방지 보안 오버레이 (최근 앱 보기 및 이탈 시 작동) */
        #security-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: #060913;
            z-index: 999999;
            display: none;
            justify-content: center;
            align-items: center;
            color: #ff2d55;
            font-size: 22px;
            font-weight: bold;
            letter-spacing: -1px;
        }

        /* 본문 캡처 방지를 위한 보안 워터마크/캔버스 레이어 */
        #content-shield {
            position: relative;
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div id="security-overlay">🔒 보안 정책으로 인해 화면이 보호됩니다.</div>
    <canvas id="bg-canvas"></canvas>
    
    <div class="container theme-blue" id="main-container">
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
                        {% if loop.index % 2 == 1 %}
                            <button class="item-btn active-blue" onclick="selectManual(this, 'blue', '{{ item.title }}', `{{ item.content }}`)">{{ item.title }}</button>
                        {% else %}
                            <button class="item-btn" onclick="selectManual(this, 'ruby', '{{ item.title }}', `{{ item.content }}`)">{{ item.title }}</button>
                        {% endif %}
                    {% endfor %}
                </div>
                <div class="main-content" id="content-shield">
                    <div id="doc-title" class="doc-title">{{ manuals[0].title if manuals else '매뉴얼이 없습니다.' }}</div>
                    <div id="doc-body" class="doc-body">{{ manuals[0].content if manuals else '' }}</div>
                </div>
            </div>
        {% endif %}
    </div>

    <script>
        // --- 🌌 울렁이는 푸른색 & 루비 오로라 배경 애니메이션 ---
        const canvas = document.getElementById('bg-canvas');
        const ctx = canvas.getContext('2d');
        
        let width, height;
        let mouseX = -1000, mouseY = -1000;
        let targetMouseX = -1000, targetMouseY = -1000;
        
        function resize() {
            width = canvas.width = window.innerWidth;
            height = canvas.height = window.innerHeight;
        }
        window.addEventListener('resize', resize);
        resize();

        window.addEventListener('mousemove', (e) => {
            targetMouseX = e.clientX;
            targetMouseY = e.clientY;
        });

        const stars = [];
        for (let i = 0; i < 140; i++) {
            stars.push({
                x: Math.random() * window.innerWidth,
                y: Math.random() * window.innerHeight,
                size: Math.random() * 1.8 + 0.5,
                alpha: Math.random(),
                speed: Math.random() * 0.012 + 0.004
            });
        }

        let time = 0;

        function drawBackground() {
            ctx.clearRect(0, 0, width, height);
            time += 0.01;
            
            for (let star of stars) {
                star.alpha += star.speed;
                if (star.alpha > 1 || star.alpha < 0) star.speed = -star.speed;
                ctx.fillStyle = `rgba(255, 255, 255, ${Math.abs(star.alpha)})`;
                ctx.beginPath();
                ctx.arc(star.x, star.y, star.size, 0, Math.PI * 2);
                ctx.fill();
            }

            // 울렁이는 푸른색 오로라
            const blueA = ctx.createRadialGradient(
                width * 0.3 + Math.sin(time) * 150, 
                height * 0.3 + Math.cos(time * 0.7) * 100, 
                60, width * 0.3, height * 0.3, width * 0.6
            );
            blueA.addColorStop(0, 'rgba(0, 242, 254, 0.28)');
            blueA.addColorStop(0.5, 'rgba(0, 150, 255, 0.12)');
            blueA.addColorStop(1, 'rgba(6, 9, 19, 0)');
            ctx.fillStyle = blueA;
            ctx.fillRect(0, 0, width, height);

            // 울렁이는 루비 붉은색 오로라 (배경 양쪽 공존)
            const rubyA = ctx.createRadialGradient(
                width * 0.7 + Math.cos(time * 0.8) * 160, 
                height * 0.7 + Math.sin(time * 0.9) * 110, 
                80, width * 0.7, height * 0.7, width * 0.65
            );
            rubyA.addColorStop(0, 'rgba(255, 45, 85, 0.25)');
            rubyA.addColorStop(0.5, 'rgba(225, 29, 72, 0.1)');
            rubyA.addColorStop(1, 'rgba(6, 9, 19, 0)');
            ctx.fillStyle = rubyA;
            ctx.fillRect(0, 0, width, height);

            // 마우스 커서 루비 붉은색 오로라 추적
            mouseX += (targetMouseX - mouseX) * 0.08;
            mouseY += (targetMouseY - mouseY) * 0.08;

            if (mouseX > 0 && mouseY > 0) {
                const rubyCursor = ctx.createRadialGradient(mouseX, mouseY, 10, mouseX, mouseY, 300);
                rubyCursor.addColorStop(0, 'rgba(255, 45, 85, 0.4)');
                rubyCursor.addColorStop(0.5, 'rgba(225, 29, 72, 0.18)');
                rubyCursor.addColorStop(1, 'rgba(6, 9, 19, 0)');
                ctx.fillStyle = rubyCursor;
                ctx.fillRect(0, 0, width, height);
            }

            requestAnimationFrame(drawBackground);
        }
        drawBackground();

        // --- 📑 매뉴얼 클릭 시 색상 및 전환 애니메이션 ---
        function selectManual(btn, themeColor, title, content) {
            document.querySelectorAll('.item-btn').forEach(b => {
                b.classList.remove('active-blue', 'active-ruby');
            });

            const mainContainer = document.getElementById('main-container');

            if (themeColor === 'ruby') {
                btn.classList.add('active-ruby');
                mainContainer.className = 'container theme-ruby';
            } else {
                btn.classList.add('active-blue');
                mainContainer.className = 'container theme-blue';
            }

            const titleElem = document.getElementById('doc-title');
            const bodyElem = document.getElementById('doc-body');

            titleElem.classList.add('fade-out');
            bodyElem.classList.add('fade-out');

            setTimeout(() => {
                titleElem.innerText = title;
                bodyElem.innerText = content;

                titleElem.classList.remove('fade-out');
                bodyElem.classList.remove('fade-out');
                titleElem.classList.add('fade-in');
                bodyElem.classList.add('fade-in');
            }, 200);
        }

        // ==========================================
        // 🔒 강력한 캡처 방지 및 최근 앱 숨김(꼼수 차단)
        // ==========================================
        const overlay = document.getElementById('security-overlay');

        document.addEventListener('contextmenu', e => e.preventDefault());
        document.addEventListener('selectstart', e => e.preventDefault());
        document.addEventListener('dragstart', e => e.preventDefault());

        document.addEventListener('keydown', (e) => {
            if (
                e.key === 'PrintScreen' ||
                e.keyCode === 44 ||
                e.keyCode === 123 ||
                (e.ctrlKey && e.shiftKey && (e.key === 'I' || e.key === 'J' || e.key === 'C')) ||
                (e.ctrlKey && (e.key === 's' || e.key === 'S' || e.key === 'p' || e.key === 'P' || e.key === 'u' || e.key === 'U'))
            ) {
                e.preventDefault();
                alert('🔒 보안 정책에 의해 캡처 및 단축키가 금지되어 있습니다.');
            }
        });

        function hideScreen() { overlay.style.display = 'flex'; }
        function showScreen() { overlay.style.display = 'none'; }

        window.addEventListener('blur', hideScreen);
        window.addEventListener('focus', showScreen);
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) hideScreen();
            else showScreen();
        });
    </script>
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
# 🛠️ 관리자 API
# ==========================================
@app.route('/api/admin/logs', methods=['GET'])
def api_get_logs():
    is_admin, _ = verify_admin_token(request)
    if not is_admin: return jsonify({"error": "Unauthorized"}), 403
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, discord_id, username, ip_address, device_info, access_time FROM logs ORDER BY id DESC LIMIT 100")
    logs = [{"id": r[0], "discord_id": r[1], "username": r[2], "ip_address": r[3], "device_info": r[4], "access_time": r[5]} for r in c.fetchall()]
    conn.close()
    return jsonify(logs)

@app.route('/api/admin/manuals', methods=['POST'])
def api_update_manuals():
    is_admin, _ = verify_admin_token(request)
    if not is_admin: return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM manuals")
    for item in data:
        c.execute("INSERT INTO manuals (title, content) VALUES (?, ?)", (item['title'], item['content']))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/admin/users', methods=['GET'])
def api_get_admins():
    is_admin, _ = verify_admin_token(request)
    if not is_admin: return jsonify({"error": "Unauthorized"}), 403
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT discord_id, memo, created_at FROM admins ORDER BY created_at DESC")
    admins = [{"discord_id": r[0], "memo": r[1], "created_at": r[2]} for r in c.fetchall()]
    conn.close()
    return jsonify(admins)

@app.route('/api/admin/users/add', methods=['POST'])
def api_add_admin():
    is_admin, _ = verify_admin_token(request)
    if not is_admin: return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    discord_id = str(data.get('discord_id', '')).strip()
    memo = data.get('memo', '')
    now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if not discord_id: return jsonify({"error": "디스코드 ID가 필요합니다."}), 400

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO admins (discord_id, memo, created_at) VALUES (?, ?, ?)", (discord_id, memo, now_time))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/admin/users/delete', methods=['POST'])
def api_delete_admin():
    is_admin, _ = verify_admin_token(request)
    if not is_admin: return jsonify({"error": "Unauthorized"}), 403
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
