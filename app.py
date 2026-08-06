import os
import json
import random
import time
from datetime import datetime
from flask import Flask, request, redirect, session, url_for, render_template_string, jsonify
import requests

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ---------------------------------------------------------------------------
# Environment Variables & GitHub Sync
# ---------------------------------------------------------------------------
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "") # e.g. "itx-0622/sky-aurora-data"

GITHUB_FILE_PATH = "sky_aurora_admin_data.json"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{GITHUB_FILE_PATH}" if GITHUB_REPO else ""

# ---------------------------------------------------------------------------
# Data Persistence Functions
# ---------------------------------------------------------------------------
def get_default_data():
    return {
        "admin_whitelist": ["1534184089144266872", "843621337066504225"],
        "user_whitelist": ["1336971557418827788"],
        "user_blacklist": [],
        "manuals": [],
        "drafts": {}, # { user_id: { "title": ..., "category": ..., "content": ... } }
        "logs": []
    }

def load_data():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return get_default_data()
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        res = requests.get(GITHUB_API_URL, headers=headers, timeout=5)
        if res.status_code == 200:
            content = res.json().get("content", "")
            import base64
            decoded = base64.b64decode(content).decode('utf-8')
            data = json.loads(decoded)
            if "drafts" not in data:
                data["drafts"] = {}
            return data
    except Exception as e:
        print(f"[GitHub Load Error] {e}")
    return get_default_data()

def save_data(data):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Get current sha
    sha = None
    try:
        get_res = requests.get(GITHUB_API_URL, headers=headers, timeout=5)
        if get_res.status_code == 200:
            sha = get_res.json().get("sha")
    except Exception as e:
        print(f"[GitHub SHA Fetch Error] {e}")

    import base64
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    encoded_content = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

    payload = {
        "message": f"Auto-sync admin data [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha

    try:
        put_res = requests.put(GITHUB_API_URL, headers=headers, json=payload, timeout=5)
        return put_res.status_code in [200, 201]
    except Exception as e:
        print(f"[GitHub Save Error] {e}")
        return False

def add_log(data, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data["logs"].insert(0, f"[{timestamp}] {message}")
    if len(data["logs"]) > 100:
        data["logs"] = data["logs"][:100]

# ---------------------------------------------------------------------------
# HTML Template
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sky Aurora Staff System</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0b0f19;
            --aurora-1: #00ffa3;
            --aurora-2: #00b8ff;
            --aurora-3: #7b2cbf;
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.12);
        }

        body {
            background-color: var(--bg-dark);
            color: #ffffff;
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }

        /* 오로라 배경 애니메이션 */
        .aurora-bg {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            z-index: -1;
            background: radial-gradient(circle at 20% 20%, rgba(0, 255, 163, 0.15), transparent 40%),
                        radial-gradient(circle at 80% 80%, rgba(0, 184, 255, 0.15), transparent 40%),
                        radial-gradient(circle at 50% 50%, rgba(123, 44, 191, 0.15), transparent 50%);
            filter: blur(60px);
            animation: auroraMove 12s infinite alternate ease-in-out;
        }

        @keyframes auroraMove {
            0% { transform: scale(1) rotate(0deg); }
            50% { transform: scale(1.2) rotate(5deg); }
            100% { transform: scale(1) rotate(-5deg); }
        }

        /* 인트로 오버레이 */
        #intro-overlay {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: #05070d;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            transition: opacity 0.8s ease, visibility 0.8s ease;
        }

        /* 프로필 링 애니메이션 */
        .avatar-container {
            position: relative;
            width: 120px;
            height: 120px;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .avatar-img {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            z-index: 2;
            border: 3px solid var(--aurora-1);
            box-shadow: 0 0 20px rgba(0,255,163,0.5);
            animation: avatarPulse 2s infinite ease-in-out;
        }

        @keyframes avatarPulse {
            0%, 100% { transform: scale(1); }
            50% { transform: scale(1.15); }
        }

        .ring {
            position: absolute;
            border-radius: 50%;
            border: 2px solid transparent;
            border-top-color: var(--aurora-1);
            border-bottom-color: var(--aurora-2);
            animation: spinRing 2s linear infinite;
            opacity: 0;
            transition: opacity 0.3s;
        }

        .avatar-container.expanding .ring {
            opacity: 1;
        }

        .ring-1 { width: 120px; height: 120px; animation-duration: 2s; }
        .ring-2 { width: 140px; height: 140px; animation-duration: 3s; animation-direction: reverse; }
        .ring-3 { width: 160px; height: 160px; animation-duration: 1.5s; }

        @keyframes spinRing {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* 글래스모피즘 카드 */
        .glass-card {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
            margin-bottom: 24px;
        }

        /* 커스텀 자체 알림 */
        .custom-alert {
            position: fixed;
            top: 20px; right: 20px;
            z-index: 10000;
            min-width: 300px;
            background: rgba(15, 23, 42, 0.95);
            border-left: 4px solid var(--aurora-1);
            color: white;
            padding: 16px 20px;
            border-radius: 8px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            display: none;
            animation: slideIn 0.3s forwards;
        }

        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }

        /* 디코 유저 자동완성 팝업 */
        .mention-dropdown {
            position: absolute;
            background: #1e293b;
            border: 1px solid var(--glass-border);
            border-radius: 8px;
            max-height: 200px;
            overflow-y: auto;
            width: 100%;
            z-index: 1000;
            display: none;
        }

        .mention-item {
            padding: 10px 14px;
            display: flex;
            align-items: center;
            gap: 12px;
            cursor: pointer;
            transition: background 0.2s;
        }

        .mention-item:hover {
            background: rgba(255, 255, 255, 0.1);
        }

        .mention-avatar {
            width: 32px; height: 32px; border-radius: 50%;
        }

        .btn-aurora {
            background: linear-gradient(135deg, var(--aurora-1), var(--aurora-2));
            color: #000;
            font-weight: 600;
            border: none;
            transition: all 0.3s;
        }

        .btn-aurora:hover {
            opacity: 0.9;
            box-shadow: 0 0 15px rgba(0,255,163,0.4);
        }
    </style>
</head>
<body>

<div class="aurora-bg"></div>

<!-- 커스텀 메세지 알림 -->
<div id="customAlert" class="custom-alert">
    <div class="d-flex align-items-center justify-content-between">
        <span id="alertMsg">알림 메시지</span>
        <button type="button" class="btn-close btn-close-white ms-3" onclick="closeCustomAlert()"></button>
    </div>
</div>

<!-- 인트로 오버레이 -->
{% if user %}
<div id="intro-overlay">
    <div class="avatar-container mb-4" id="introAvatar">
        <div class="ring ring-1"></div>
        <div class="ring ring-2"></div>
        <div class="ring ring-3"></div>
        <img src="{{ user.avatar }}" class="avatar-img" alt="Profile">
    </div>
    <h3 id="introStatus" class="fw-bold text-light">오로라 시스템에 접속 중...</h3>
    <p id="welcomeMsg" class="text-info mt-2" style="display:none; font-size: 1.2rem;">
        ✨ {{ user.username }}님 환영합니다!
    </p>
</div>
{% endif %}

<div class="container py-4">
    <!-- 헤더 -->
    <div class="glass-card d-flex justify-content-between align-items-center">
        <div>
            <h2 class="fw-bold m-0"><i class="fa-solid fa-plane-departure text-info me-2"></i>Sky Aurora Staff</h2>
        </div>
        <div>
            {% if user %}
                <span class="me-3"><img src="{{ user.avatar }}" width="30" class="rounded-circle me-1"> <strong>{{ user.username }}</strong></span>
                <a href="/logout" class="btn btn-outline-danger btn-sm"><i class="fa-solid fa-right-from-bracket"></i> 로그아웃</a>
            {% else %}
                <a href="/login" class="btn btn-aurora btn-sm"><i class="fa-brands fa-discord me-1"></i> 디스코드 로그인</a>
            {% endif %}
        </div>
    </div>

    {% if user %}
    <div class="row">
        <!-- 매뉴얼 관리 섹션 -->
        <div class="col-md-7">
            <div class="glass-card">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h4 class="fw-bold m-0"><i class="fa-solid fa-book me-2"></i>매뉴얼 관리</h4>
                    {% if is_admin %}
                    <div>
                        <button class="btn btn-sm btn-outline-warning me-2" onclick="saveDraft()"><i class="fa-solid fa-floppy-disk"></i> 임시 저장</button>
                        <button class="btn btn-sm btn-aurora" onclick="resetForm()"><i class="fa-solid fa-plus"></i> 새로 작성</button>
                    </div>
                    {% endif %}
                </div>

                {% if is_admin %}
                <form id="manualForm" action="/save_manual" method="POST" class="mb-4">
                    <input type="hidden" id="manual_id" name="manual_id" value="">
                    <div class="mb-2">
                        <select id="select_manual" class="form-select bg-dark text-light border-secondary" onchange="loadManualToEdit(this.value)">
                            <option value="">-- 수정할 매뉴얼 선택 (신규 작성 시 선택 해제) --</option>
                            {% for m in data.manuals %}
                            <option value="{{ m.id }}">{{ m.title }} [{{ m.category }}]</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="row g-2 mb-2">
                        <div class="col-md-4">
                            <input type="text" id="manual_category" name="category" class="form-control bg-dark text-light border-secondary" placeholder="카테고리" required>
                        </div>
                        <div class="col-md-8">
                            <input type="text" id="manual_title" name="title" class="form-control bg-dark text-light border-secondary" placeholder="제목" required>
                        </div>
                    </div>
                    <div class="mb-2">
                        <textarea id="manual_content" name="content" class="form-control bg-dark text-light border-secondary" rows="4" placeholder="매뉴얼 내용을 입력하세요..." required></textarea>
                    </div>
                    <button type="submit" class="btn btn-aurora w-100">매뉴얼 저장 및 게시</button>
                </form>
                {% endif %}

                <!-- 매뉴얼 목록 -->
                <div class="accordion" id="manualAccordion">
                    {% for m in data.manuals %}
                    <div class="accordion-item bg-dark text-light border-secondary mb-2">
                        <h2 class="accordion-header">
                            <button class="accordion-button collapsed bg-dark text-light" type="button" data-bs-toggle="collapse" data-bs-target="#m{{ m.id }}">
                                <span class="badge bg-info me-2">{{ m.category }}</span> <strong>{{ m.title }}</strong>
                            </button>
                        </h2>
                        <div id="m{{ m.id }}" class="accordion-collapse collapse">
                            <div class="accordion-body">
                                <p style="white-space: pre-wrap;">{{ m.content }}</p>
                                {% if is_admin %}
                                <div class="text-end">
                                    <button class="btn btn-sm btn-outline-info" onclick="loadManualToEdit('{{ m.id }}')">수정</button>
                                    <a href="/delete_manual/{{ m.id }}" class="btn btn-sm btn-outline-danger" onclick="return confirm('삭제하시겠습니까?')">삭제</a>
                                </div>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- 직원 권한 관리 섹션 (어드민전용) -->
        <div class="col-md-5">
            {% if is_admin %}
            <div class="glass-card">
                <h4 class="fw-bold mb-3"><i class="fa-solid fa-users-gear me-2"></i>직원 권한 관리</h4>
                
                <form action="/update_user_role" method="POST" class="mb-4">
                    <div class="position-relative mb-2">
                        <label class="form-label text-muted small">디스코드 ID / 멘션(@유저명)</label>
                        <input type="text" id="discord_id_input" name="user_id" class="form-control bg-dark text-light border-secondary" placeholder="@사용자이름 또는 ID 입력" autocomplete="off" required>
                        
                        <!-- 멘션 자동완성 드롭다운 -->
                        <div id="mentionDropdown" class="mention-dropdown"></div>
                    </div>

                    <div class="form-check form-switch mb-3">
                        <input class="form-check-input" type="checkbox" id="grant_admin" name="grant_admin" value="true">
                        <label class="form-check-label" for="grant_admin">어드민 권한 부여 (화이트리스트 추가 시)</label>
                    </div>

                    <div class="d-flex gap-2">
                        <button type="submit" name="action" value="whitelist" class="btn btn-aurora flex-fill"><i class="fa-solid fa-user-check me-1"></i> 화이트리스트 등록</button>
                        <button type="submit" name="action" value="blacklist" class="btn btn-danger flex-fill"><i class="fa-solid fa-user-slash me-1"></i> 블랙리스트 등록</button>
                    </div>
                </form>

                <hr class="border-secondary">

                <h6 class="fw-bold mt-3">관리자 (Admin)</h6>
                <ul class="list-group list-group-flush mb-3">
                    {% for uid in data.admin_whitelist %}
                    <li class="list-group-bg bg-transparent text-light list-group-item d-flex justify-content-between align-items-center border-secondary px-0">
                        <code>{{ uid }}</code>
                        <span class="badge bg-warning text-dark">Admin</span>
                    </li>
                    {% endfor %}
                </ul>

                <h6 class="fw-bold">화이트리스트 (Whitelist)</h6>
                <ul class="list-group list-group-flush mb-3">
                    {% for uid in data.user_whitelist %}
                    <li class="list-group-bg bg-transparent text-light list-group-item d-flex justify-content-between align-items-center border-secondary px-0">
                        <code>{{ uid }}</code>
                        <a href="/remove_user/whitelist/{{ uid }}" class="btn btn-sm btn-outline-danger">제거</a>
                    </li>
                    {% endfor %}
                </ul>

                <h6 class="fw-bold">블랙리스트 (Blacklist)</h6>
                <ul class="list-group list-group-flush">
                    {% for uid in data.user_blacklist %}
                    <li class="list-group-bg bg-transparent text-light list-group-item d-flex justify-content-between align-items-center border-secondary px-0">
                        <code>{{ uid }}</code>
                        <a href="/remove_user/blacklist/{{ uid }}" class="btn btn-sm btn-outline-secondary">제거</a>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            {% endif %}

            <!-- 시스템 로그 섹션 -->
            <div class="glass-card">
                <h5 class="fw-bold mb-3"><i class="fa-solid fa-list-check me-2"></i>시스템 활동 로그</h5>
                <div style="max-height: 250px; overflow-y: auto; font-size: 0.85rem;" class="bg-dark p-2 rounded border border-secondary">
                    {% for log in data.logs %}
                    <div class="text-muted border-bottom border-secondary py-1">{{ log }}</div>
                    {% endfor %}
                </div>
            </div>
        </div>
    </div>
    {% else %}
    <div class="text-center py-5 glass-card">
        <h3>스태프 관제 시스템에 접속하려면 로그인하세요.</h3>
        <p class="text-muted">디스코드 계정 인증을 통해 권한이 부여된 사용자만 접근할 수 있습니다.</p>
        <a href="/login" class="btn btn-aurora btn-lg mt-2"><i class="fa-brands fa-discord me-2"></i> Discord로 로그인</a>
    </div>
    {% endif %}
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    const manualsData = {{ data.manuals | tojson }};
    const currentUserId = "{{ user.id if user else '' }}";

    // 1. 커스텀 자체 알림 함수
    function showAlert(msg) {
        const alertBox = document.getElementById('customAlert');
        document.getElementById('alertMsg').innerText = msg;
        alertBox.style.display = 'block';
        setTimeout(() => { closeCustomAlert(); }, 4000);
    }
    function closeCustomAlert() {
        document.getElementById('customAlert').style.display = 'none';
    }

    // 2. 인트로 로딩 및 펄스 링 애니메이션
    {% if user %}
    window.addEventListener('DOMContentLoaded', () => {
        const overlay = document.getElementById('intro-overlay');
        const avatarContainer = document.getElementById('introAvatar');
        const statusText = document.getElementById('introStatus');
        const welcomeMsg = document.getElementById('welcomeMsg');

        // 3초 ~ 5초 랜덤 로딩
        const randomTime = Math.floor(Math.random() * 2000) + 3000;

        setTimeout(() => {
            statusText.style.display = 'none';
            welcomeMsg.style.display = 'block';
            avatarContainer.classList.add('expanding'); // 링 생성 및 확장

            setTimeout(() => {
                avatarContainer.classList.remove('expanding'); // 링 제거
                overlay.style.opacity = '0';
                setTimeout(() => { overlay.style.visibility = 'hidden'; }, 800);
            }, 1200);
        }, randomTime);
    });
    {% endif %}

    // 3. 매뉴얼 선택 수정 및 임시 저장
    function loadManualToEdit(id) {
        if (!id) { resetForm(); return; }
        const item = manualsData.find(m => m.id == id);
        if (item) {
            document.getElementById('manual_id').value = item.id;
            document.getElementById('manual_category').value = item.category;
            document.getElementById('manual_title').value = item.title;
            document.getElementById('manual_content').value = item.content;
            document.getElementById('select_manual').value = item.id;
            showAlert('수정할 매뉴얼을 불러왔습니다.');
        }
    }

    function resetForm() {
        document.getElementById('manual_id').value = '';
        document.getElementById('manual_category').value = '';
        document.getElementById('manual_title').value = '';
        document.getElementById('manual_content').value = '';
        document.getElementById('select_manual').value = '';
    }

    function saveDraft() {
        const draft = {
            category: document.getElementById('manual_category').value,
            title: document.getElementById('manual_title').value,
            content: document.getElementById('manual_content').value
        };
        fetch('/save_draft', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(draft)
        }).then(res => res.json()).then(data => {
            if(data.success) showAlert('임시 저장이 완료되었습니다.');
        });
    }

    // 4. 복사/붙여넣기 및 캡처 감지 보안 로그
    function sendSecurityLog(actionType) {
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        const deviceType = isMobile ? "Mobile" : "Desktop";
        fetch('/log_event', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ action: actionType, device: deviceType })
        });
    }

    document.addEventListener('copy', () => sendSecurityLog('복사 (Ctrl+C) 감지'));
    document.addEventListener('paste', () => sendSecurityLog('붙여넣기 (Ctrl+V) 감지'));
    document.addEventListener('keydown', (e) => {
        // Win + Shift + S 또는 PrintScreen 감지
        if ((e.key === 'S' || e.key === 's') && e.shiftKey && (e.metaKey || e.osKey)) {
            sendSecurityLog('화면 캡처 시도 (Win+Shift+S)');
        } else if (e.key === 'PrintScreen') {
            sendSecurityLog('화면 캡처 시도 (PrintScreen)');
        }
    });

    // 5. @멘션 디스코드 자동완성
    const idInput = document.getElementById('discord_id_input');
    const dropdown = document.getElementById('mentionDropdown');

    if (idInput) {
        idInput.addEventListener('input', (e) => {
            const val = e.target.value;
            if (val.startsWith('@')) {
                const query = val.substring(1);
                fetch(`/search_discord_user?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(users => {
                        dropdown.innerHTML = '';
                        if (users.length > 0) {
                            dropdown.style.display = 'block';
                            users.forEach(u => {
                                const div = document.createElement('div');
                                div.className = 'mention-item';
                                div.innerHTML = `
                                    <img src="${u.avatar}" class="mention-avatar">
                                    <div>
                                        <div class="fw-bold">${u.username} <small class="text-muted">(${u.global_name})</small></div>
                                        <div class="text-muted small">ID: ${u.id}</div>
                                    </div>
                                `;
                                div.onclick = () => {
                                    idInput.value = u.id;
                                    dropdown.style.display = 'none';
                                };
                                dropdown.appendChild(div);
                            });
                        } else {
                            dropdown.style.display = 'none';
                        }
                    });
            } else {
                dropdown.style.display = 'none';
            }
        });
    }
</script>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# Flask Routes
# ---------------------------------------------------------------------------
@app.route('/')
def index():
    data = load_data()
    user = session.get('user')
    is_admin = False
    
    if user:
        user_id = str(user['id'])
        if user_id in data.get('admin_whitelist', []):
            is_admin = True
            
    return render_template_string(HTML_TEMPLATE, data=data, user=user, is_admin=is_admin)

@app.route('/login')
def login():
    # Discord OAuth2 Redirect
    redirect_uri = url_for('callback', _external=True)
    client_id = "1346387062407696414"
    discord_url = f"https://discord.com/oauth2/authorize?client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope=identify"
    return redirect(discord_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect('/')
    
    redirect_uri = url_for('callback', _external=True)
    data = {
        'client_id': '1346387062407696414',
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': redirect_uri
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    r = requests.post('https://discord.com/api/v10/oauth2/token', data=data, headers=headers)
    token_json = r.json()
    
    access_token = token_json.get('access_token')
    if not access_token:
        return redirect('/')

    # Fetch User Profile
    user_res = requests.get('https://discord.com/api/v10/users/@me', headers={'Authorization': f'Bearer {access_token}'}).json()
    
    avatar_id = user_res.get('avatar')
    user_id = user_res.get('id')
    avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_id}.png" if avatar_id else "https://cdn.discordapp.com/embed/avatars/0.png"
    
    session['user'] = {
        'id': user_id,
        'username': user_res.get('username'),
        'avatar': avatar_url
    }

    # Logging Device & Login
    data_store = load_data()
    user_agent = request.headers.get('User-Agent', '')
    is_mobile = any(device in user_agent for device in ['iPhone', 'iPad', 'Android', 'Mobile'])
    device_str = "Mobile" if is_mobile else "Desktop"
    
    add_log(data_store, f"[인증] {user_res.get('username')}: 접속 성공 (ID: {user_id}, 기기: {device_str})")
    save_data(data_store)

    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/save_manual', methods=['POST'])
def save_manual():
    user = session.get('user')
    data_store = load_data()
    if not user or str(user['id']) not in data_store.get('admin_whitelist', []):
        return redirect('/')

    manual_id = request.form.get('manual_id')
    category = request.form.get('category')
    title = request.form.get('title')
    content = request.form.get('content')

    if manual_id: # 수정
        for m in data_store['manuals']:
            if str(m['id']) == str(manual_id):
                m['category'] = category
                m['title'] = title
                m['content'] = content
                break
        add_log(data_store, f"[매뉴얼 수정] {user['username']}: '{title}' 수정됨")
    else: # 신규 추가
        new_item = {
            "id": int(time.time()),
            "category": category,
            "title": title,
            "content": content
        }
        data_store['manuals'].insert(0, new_item)
        add_log(data_store, f"[매뉴얼 추가] {user['username']}: '{title}' 등록됨")

    save_data(data_store)
    return redirect('/')

@app.route('/delete_manual/<int:m_id>')
def delete_manual(m_id):
    user = session.get('user')
    data_store = load_data()
    if not user or str(user['id']) not in data_store.get('admin_whitelist', []):
        return redirect('/')

    data_store['manuals'] = [m for m in data_store['manuals'] if m['id'] != m_id]
    add_log(data_store, f"[매뉴얼 삭제] {user['username']}: ID {m_id} 매뉴얼 삭제됨")
    save_data(data_store)
    return redirect('/')

@app.route('/save_draft', methods=['POST'])
def save_draft():
    user = session.get('user')
    if not user:
        return jsonify({"success": False})
    
    req_data = request.json
    data_store = load_data()
    data_store['drafts'][str(user['id'])] = req_data
    save_data(data_store)
    return jsonify({"success": True})

@app.route('/update_user_role', methods=['POST'])
def update_user_role():
    user = session.get('user')
    data_store = load_data()
    if not user or str(user['id']) not in data_store.get('admin_whitelist', []):
        return redirect('/')

    target_id = request.form.get('user_id', '').strip()
    action = request.form.get('action')
    grant_admin = request.form.get('grant_admin') == 'true'

    if not target_id:
        return redirect('/')

    if action == 'whitelist':
        # 블랙리스트에 있으면 제거
        if target_id in data_store['user_blacklist']:
            data_store['user_blacklist'].remove(target_id)
        
        if target_id not in data_store['user_whitelist']:
            data_store['user_whitelist'].append(target_id)
            
        if grant_admin and target_id not in data_store['admin_whitelist']:
            data_store['admin_whitelist'].append(target_id)
            add_log(data_store, f"[권한 변경] {user['username']}: ID {target_id} -> 관리자(Admin) 및 화이트리스트 등록")
        else:
            add_log(data_store, f"[권한 변경] {user['username']}: ID {target_id} -> 화이트리스트 등록")

    elif action == 'blacklist':
        # 화이트리스트 및 어드민에서 자동 제거
        if target_id in data_store['user_whitelist']:
            data_store['user_whitelist'].remove(target_id)
        if target_id in data_store['admin_whitelist']:
            data_store['admin_whitelist'].remove(target_id)
        
        if target_id not in data_store['user_blacklist']:
            data_store['user_blacklist'].append(target_id)
            
        add_log(data_store, f"[권한 변경] {user['username']}: ID {target_id} -> 블랙리스트 등록 (화이트/어드민 자동 제거)")

    save_data(data_store)
    return redirect('/')

@app.route('/remove_user/<role_type>/<uid>')
def remove_user(role_type, uid):
    user = session.get('user')
    data_store = load_data()
    if not user or str(user['id']) not in data_store.get('admin_whitelist', []):
        return redirect('/')

    if role_type == 'whitelist' and uid in data_store['user_whitelist']:
        data_store['user_whitelist'].remove(uid)
    elif role_type == 'blacklist' and uid in data_store['user_blacklist']:
        data_store['user_blacklist'].remove(uid)

    add_log(data_store, f"[권한 제거] {user['username']}: ID {uid} ({role_type}) 제거됨")
    save_data(data_store)
    return redirect('/')

@app.route('/log_event', methods=['POST'])
def log_event():
    user = session.get('user')
    data = request.json
    data_store = load_data()
    username = user['username'] if user else "비로그인 유저"
    add_log(data_store, f"[보안 로그] {username}: {data.get('action')} (기기: {data.get('device')})")
    save_data(data_store)
    return jsonify({"status": "ok"})

@app.route('/search_discord_user')
def search_discord_user():
    # 검색어 쿼리 mock 또는 백엔드 예시 처리
    query = request.args.get('q', '')
    # 유저 시뮬레이션 데이터반환
    results = [
        {"id": "1336971557418827788", "username": query or "user_sample", "global_name": "스태프 사용자", "avatar": "https://cdn.discordapp.com/embed/avatars/0.png"}
    ]
    return jsonify(results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
