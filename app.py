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
# ⚙️ Discord OAuth2 & 통합 환경 설정
# ==========================================
CLIENT_ID = "1534184089144266872"
CLIENT_SECRET = "JcMp7ntF3Rx32ZYTRjyaYUWfmp0EU3co"
BASE_URL = "https://sky-aurora-admin.onrender.com"

ADMIN_SECRET_KEY = "sky_aurora_admin_secret_key_1234"
DATA_FILE = "sky_aurora_admin_data.json"
DEFAULT_ADMINS = ["1534184089144266872", "843621337066504225"]

# --------------------------------------------------
# 📁 데이터 관리 및 로그 함수
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
# 1️⃣ 어드민 관제 사이트 HTML (소스코드 1번 기반)
# --------------------------------------------------
ADMIN_COMMON_HEAD = """
<style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { box-sizing: border-box; transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1); font-family: 'Pretendard', sans-serif; }
    body { background: #050811; color: #f1f5f9; margin: 0; padding: 0; min-height: 100vh; overflow-x: hidden; position: relative; }
    #bg-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 0; pointer-events: none; }
    .content-wrapper { position: relative; z-index: 1; }
    @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px) scale(0.98); } to { opacity: 1; transform: translateY(0) scale(1); } }
    @keyframes glowPulse { 0% { box-shadow: 0 0 15px rgba(56, 189, 248, 0.2); } 50% { box-shadow: 0 0 35px rgba(168, 85, 247, 0.5); } 100% { box-shadow: 0 0 15px rgba(56, 189, 248, 0.2); } }
    .animated-element { animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
    .glass-card { background: rgba(15, 23, 42, 0.65); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 16px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .glass-card:hover { border-color: rgba(56, 189, 248, 0.4); }
    button { background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; border: none; padding: 10px 20px; border-radius: 10px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3); }
    button:hover { transform: translateY(-1px); animation: glowPulse 1.5s infinite; }
    .btn-danger { background: linear-gradient(135deg, #ef4444, #b91c1c); box-shadow: 0 4px 14px rgba(239, 68, 68, 0.3); }
    .btn-secondary { background: linear-gradient(135deg, #475569, #334155); }
    input, textarea { width: 100%; background: rgba(5, 8, 17, 0.8); color: white; border: 1px solid rgba(255, 255, 255, 0.1); padding: 12px 16px; border-radius: 10px; margin-bottom: 12px; outline: none; }
    input:focus, textarea:focus { border-color: #38bdf8; box-shadow: 0 0 15px rgba(56, 189, 248, 0.25); }
    ul { list-style: none; padding: 0; margin: 0; }
    li { background: rgba(5, 8, 17, 0.6); padding: 12px 16px; margin-bottom: 10px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.05); display: flex; justify-content: space-between; align-items: center; }
    li:hover { background: rgba(30, 41, 59, 0.8); border-color: rgba(56, 189, 248, 0.3); }
    .aurora-loader-container { position: relative; width: 140px; height: 140px; margin: 0 auto 20px auto; display: flex; justify-content: center; align-items: center; }
    .aurora-ring { position: absolute; width: 100%; height: 100%; border-radius: 50%; background: conic-gradient(from 0deg, #38bdf8, #a855f7, #10b981, #38bdf8); mask: radial-gradient(transparent 58%, black 59%); -webkit-mask: radial-gradient(transparent 58%, black 59%); animation: spinAurora 1.8s linear infinite; filter: drop-shadow(0 0 12px rgba(56, 189, 248, 0.6)); }
    .aurora-avatar { width: 100px; height: 100px; border-radius: 50%; object-fit: cover; z-index: 2; border: 2px solid rgba(255, 255, 255, 0.2); }
    @keyframes spinAurora { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
</style>
<canvas id="bg-canvas"></canvas>
<script>
    const canvas = document.getElementById('bg-canvas');
    const ctx = canvas.getContext('2d');
    let width, height, stars = [], auroraTime = 0;
    function resize() { width = canvas.width = window.innerWidth; height = canvas.height = window.innerHeight; initStars(); }
    function initStars() { stars = []; for(let i = 0; i < 150; i++) { stars.push({ x: Math.random() * width, y: Math.random() * height, size: Math.random() * 1.5, alpha: Math.random(), speed: 0.005 + Math.random() * 0.015 }); } }
    function drawAurora() {
        auroraTime += 0.008; ctx.clearRect(0, 0, width, height);
        stars.forEach(s => { s.alpha += s.speed; if (s.alpha > 1 || s.alpha < 0) s.speed = -s.speed; ctx.fillStyle = `rgba(255, 255, 255, ${Math.abs(s.alpha)})`; ctx.beginPath(); ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2); ctx.fill(); });
        const grad1 = ctx.createLinearGradient(0, 0, width, height);
        grad1.addColorStop(0, `rgba(56, 189, 248, ${0.12 + Math.sin(auroraTime) * 0.05})`);
        grad1.addColorStop(0.5, `rgba(168, 85, 247, ${0.15 + Math.cos(auroraTime * 0.8) * 0.05})`);
        grad1.addColorStop(1, `rgba(10, 185, 129, ${0.1 + Math.sin(auroraTime * 1.2) * 0.04})`);
        ctx.fillStyle = grad1; ctx.beginPath(); ctx.moveTo(0, height * 0.3);
        for(let x = 0; x <= width; x += 50) { const y = height * 0.3 + Math.sin(x * 0.003 + auroraTime) * 80 + Math.cos(x * 0.001 + auroraTime * 1.5) * 40; ctx.lineTo(x, y); }
        ctx.lineTo(width, height); ctx.lineTo(0, height); ctx.closePath(); ctx.fill();
        requestAnimationFrame(drawAurora);
    }
    window.addEventListener('resize', resize); resize(); drawAurora();
</script>
"""

@app.route('/')
def admin_page():
    html = """
    <!DOCTYPE html>
    <html lang="ko">
    <head><meta charset="UTF-8"><title>SKY AURORA ADMIN SYSTEM</title>__COMMON_HEAD__</head>
    <body>
        <div class="content-wrapper">
            <div id="login-box" style="display:flex; justify-content:center; align-items:center; height:100vh;">
                <div class="glass-card animated-element" style="text-align:center; width:380px;">
                    <h1 style="color:#38bdf8; font-size:28px; margin-bottom:8px;">SKY AURORA</h1>
                    <p style="color:#94a3b8; margin-bottom:28px; font-size:14px;">통합 어드민 관제 시스템</p>
                    <button onclick="login('admin')" style="width:100%; padding:14px; font-size:15px;">🔑 Discord 어드민 로그인</button>
                </div>
            </div>

            <div id="welcome-box" style="display:none; justify-content:center; align-items:center; height:100vh;">
                <div class="glass-card animated-element" style="text-align:center; width:400px; padding:36px;">
                    <div class="aurora-loader-container">
                        <div class="aurora-ring"></div>
                        <img id="welcome-avatar" class="aurora-avatar" src="" alt="Profile">
                    </div>
                    <div id="welcome-percent" style="color:#38bdf8; font-size:24px; font-weight:800; margin-bottom:12px;">0%</div>
                    <h2 id="welcome-msg" style="color:#f1f5f9; font-size:20px; margin:0 0 8px 0; font-weight:700;">사용자 인증 중...</h2>
                    <p id="welcome-sub" style="color:#94a3b8; font-size:13px; margin:0;">보안 액세스 권한을 확인하고 있습니다.</p>
                </div>
            </div>

            <div id="admin-box" style="display:none; height:100vh;">
                <div style="width:280px; background:rgba(5, 8, 17, 0.85); border-right:1px solid rgba(255,255,255,0.08); padding:28px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <h2 style="color:#38bdf8; font-size:22px; margin-bottom:28px;">SKY AURORA</h2>
                        <div class="nav-btn" onclick="switchTab('manuals')" style="padding:14px; cursor:pointer; color:#94a3b8; font-weight:600; border-radius:10px;">📖 매뉴얼 작성/관리</div>
                        <div class="nav-btn" onclick="switchTab('permissions')" style="padding:14px; cursor:pointer; color:#94a3b8; font-weight:600; border-radius:10px;">🛡️ 권한 제어 센터</div>
                        <div class="nav-btn" onclick="switchTab('logs')" style="padding:14px; cursor:pointer; color:#94a3b8; font-weight:600; border-radius:10px;">📜 실시간 로그</div>
                    </div>
                    <div>
                        <div id="sidebar-profile" class="glass-card" style="padding:14px; margin-bottom:14px; display:flex; align-items:center; gap:12px; background:rgba(15, 23, 42, 0.8);">
                            <img id="sidebar-avatar" src="" style="width:42px; height:42px; border-radius:50%; border:1px solid #38bdf8;">
                            <div style="overflow:hidden;">
                                <div id="sidebar-username" style="color:#f1f5f9; font-weight:700; font-size:14px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"></div>
                                <div id="sidebar-userid" style="color:#94a3b8; font-size:11px;"></div>
                            </div>
                        </div>
                        <button onclick="logout()" class="btn-danger" style="width:100%;">로그아웃</button>
                    </div>
                </div>

                <div style="flex:1; padding:36px; overflow-y:auto;">
                    <div id="tab-manuals" class="tab-content animated-element">
                        <div style="display:grid; grid-template-columns:1fr 1.8fr; gap:28px;">
                            <div class="glass-card">
                                <h3 style="color:#38bdf8; margin-top:0;">매뉴얼 목록</h3>
                                <ul id="manual-list"></ul>
                            </div>
                            <div class="glass-card">
                                <h3 style="color:#38bdf8; margin-top:0;">매뉴얼 작성 및 수정</h3>
                                <input type="text" id="m-title" placeholder="매뉴얼 제목을 입력하세요">
                                <textarea id="m-content" style="height:260px;" placeholder="매뉴얼 상세 내용을 입력하세요"></textarea>
                                <div style="display:flex; gap:10px;">
                                    <button onclick="saveManual()" style="flex:1;">💾 매뉴얼 저장/수정</button>
                                    <button onclick="deleteManual()" class="btn-danger" style="width:100px;">🗑️ 삭제</button>
                                    <button onclick="resetForm()" class="btn-secondary" style="width:100px;">새로작성</button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div id="tab-permissions" class="tab-content animated-element" style="display:none;">
                        <div class="glass-card" style="margin-bottom:28px;">
                            <h3 style="color:#38bdf8; margin-top:0;">일반 매뉴얼 사이트 차단 / 허용 설정</h3>
                            <div style="display:flex; gap:12px;">
                                <input type="text" id="target-id" placeholder="대상 디스코드 유저 ID 입력" style="margin:0;">
                                <button onclick="addPermission('whitelist')">화이트리스트 추가</button>
                                <button onclick="addPermission('blacklist')" class="btn-danger">블랙리스트 등록</button>
                            </div>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:28px;">
                            <div class="glass-card">
                                <h3 style="color:#4ade80; margin-top:0;">일반 사이트 화이트리스트</h3>
                                <ul id="wl-list"></ul>
                            </div>
                            <div class="glass-card">
                                <h3 style="color:#f87171; margin-top:0;">일반 사이트 블랙리스트</h3>
                                <ul id="bl-list"></ul>
                            </div>
                        </div>
                    </div>

                    <div id="tab-logs" class="tab-content animated-element" style="display:none;">
                        <div class="glass-card">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                                <h3 style="color:#38bdf8; margin:0;">실시간 접속 및 활동 로그</h3>
                                <div style="display:flex; gap:8px;">
                                    <button onclick="filterLogs('ALL')" class="btn-secondary" style="padding:6px 12px; font-size:12px;">전체</button>
                                    <button onclick="filterLogs('어드민')" class="btn-secondary" style="padding:6px 12px; font-size:12px; color:#38bdf8;">어드민 로그</button>
                                    <button onclick="filterLogs('스태프 매뉴얼')" class="btn-secondary" style="padding:6px 12px; font-size:12px; color:#4ade80;">스태프 로그</button>
                                </div>
                            </div>
                            <div id="log-list" style="background:rgba(5, 8, 17, 0.9); padding:18px; border-radius:12px; font-family:monospace; font-size:13px; height:460px; overflow-y:auto; border:1px solid rgba(255,255,255,0.05);"></div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let currentData = { user_whitelist: [], user_blacklist: [], manuals: [], logs: [] };
            let selectedManualIndex = -1;
            let currentLogFilter = 'ALL';
            let isLoadedOnce = false;

            function login(target) {
                const redirectUri = encodeURIComponent(window.location.origin + '/callback?target=' + target);
                location.href = `https://discord.com/oauth2/authorize?client_id=__CLIENT_ID__&response_type=code&redirect_uri=${redirectUri}&scope=identify`;
            }

            function logout() { location.href = '/logout'; }

            function switchTab(name) {
                document.querySelectorAll('.tab-content').forEach(e => e.style.display = 'none');
                document.getElementById(`tab-${name}`).style.display = 'block';
            }

            function triggerAuroraLoading(user, callback) {
                document.getElementById('login-box').style.display = 'none';
                document.getElementById('welcome-box').style.display = 'flex';

                const avatarUrl = user.avatar 
                    ? `https://cdn.discordapp.com/avatars/${user.id}/${user.avatar}.png?size=128`
                    : 'https://cdn.discordapp.com/embed/avatars/0.png';
                
                document.getElementById('welcome-avatar').src = avatarUrl;
                
                let percent = 0;
                const interval = setInterval(() => {
                    percent += 2;
                    document.getElementById('welcome-percent').innerText = `${percent}%`;

                    if (percent >= 100) {
                        clearInterval(interval);
                        document.getElementById('welcome-msg').innerText = `${user.username}님 환영합니다!`;
                        document.getElementById('welcome-sub').innerText = `ID: ${user.id} | 어드민 인증 완료`;
                        
                        setTimeout(() => {
                            document.getElementById('welcome-box').style.display = 'none';
                            document.getElementById('admin-box').style.display = 'flex';
                            if(callback) callback();
                        }, 1200);
                    }
                }, 20);
            }

            async function syncData() {
                try {
                    const res = await fetch('/api/data');
                    if (res.ok) {
                        const data = await res.json();
                        if (data.user) {
                            currentData = data;
                            if (!isLoadedOnce) {
                                isLoadedOnce = true;
                                const avatarUrl = data.user.avatar 
                                    ? `https://cdn.discordapp.com/avatars/${data.user.id}/${data.user.avatar}.png?size=128`
                                    : 'https://cdn.discordapp.com/embed/avatars/0.png';
                                
                                document.getElementById('sidebar-avatar').src = avatarUrl;
                                document.getElementById('sidebar-username').innerText = data.user.username;
                                document.getElementById('sidebar-userid').innerText = `ID: ${data.user.id}`;
                                
                                triggerAuroraLoading(data.user, () => {
                                    render();
                                });
                            } else {
                                render();
                            }
                        }
                    }
                } catch (e) { console.error("Sync error:", e); }
            }

            function render() {
                const ml = document.getElementById('manual-list');
                ml.innerHTML = currentData.manuals.map((m, i) => `
                    <li onclick="selectManual(${i})" style="cursor:pointer; ${selectedManualIndex === i ? 'border-color:#38bdf8; background:rgba(56, 189, 248, 0.15);' : ''}">
                        <span>${m.title}</span>
                    </li>
                `).join('');

                document.getElementById('wl-list').innerHTML = currentData.user_whitelist.map(id => `<li><span>${id}</span><button onclick="removePermission('whitelist', '${id}')" class="btn-danger" style="padding:4px 8px; font-size:12px;">삭제</button></li>`).join('');
                document.getElementById('bl-list').innerHTML = currentData.user_blacklist.map(id => `<li><span>${id}</span><button onclick="removePermission('blacklist', '${id}')" style="padding:4px 8px; font-size:12px;">해제</button></li>`).join('');

                renderLogs(currentLogFilter);
            }

            function renderLogs(filter) {
                currentLogFilter = filter;
                const logBox = document.getElementById('log-list');
                let logs = currentData.logs;
                if (filter !== 'ALL') {
                    logs = logs.filter(l => l.includes(`[${filter}]`));
                }
                logBox.innerHTML = logs.map(l => {
                    let color = '#38bdf8';
                    if (l.includes('[스태프 매뉴얼]')) color = '#4ade80';
                    return `<div style="padding:4px 0; border-bottom:1px solid rgba(255,255,255,0.03); color:${color};">${l}</div>`;
                }).join('');
            }

            function filterLogs(type) { renderLogs(type); }

            function selectManual(idx) {
                selectedManualIndex = idx;
                document.getElementById('m-title').value = currentData.manuals[idx].title;
                document.getElementById('m-content').value = currentData.manuals[idx].content;
                render();
            }

            function resetForm() {
                selectedManualIndex = -1;
                document.getElementById('m-title').value = '';
                document.getElementById('m-content').value = '';
                render();
            }

            async function saveManual() {
                const title = document.getElementById('m-title').value.trim();
                const content = document.getElementById('m-content').value.trim();
                if (!title) return alert('제목을 입력해주세요.');

                if (selectedManualIndex >= 0) {
                    currentData.manuals[selectedManualIndex] = { title, content };
                } else {
                    currentData.manuals.push({ title, content });
                }

                await updateData({ action: 'save_manual', manuals: currentData.manuals, title });
                resetForm();
            }

            async function deleteManual() {
                if (selectedManualIndex < 0) return alert('삭제할 매뉴얼을 선택하세요.');
                if (confirm('이 매뉴얼을 삭제하시겠습니까?')) {
                    const deletedTitle = currentData.manuals[selectedManualIndex].title;
                    currentData.manuals.splice(selectedManualIndex, 1);
                    await updateData({ action: 'delete_manual', manuals: currentData.manuals, title: deletedTitle });
                    resetForm();
                }
            }

            async function addPermission(type) {
                const id = document.getElementById('target-id').value.trim();
                if (!id) return alert('ID를 입력하세요.');
                if (type === 'whitelist') currentData.user_whitelist.push(id);
                else currentData.user_blacklist.push(id);
                await updateData({ action: `add_${type}`, user_whitelist: currentData.user_whitelist, user_blacklist: currentData.user_blacklist, target_id: id });
                document.getElementById('target-id').value = '';
            }

            async function removePermission(type, id) {
                if (type === 'whitelist') currentData.user_whitelist = currentData.user_whitelist.filter(i => i !== id);
                else currentData.user_blacklist = currentData.user_blacklist.filter(i => i !== id);
                await updateData({ action: `remove_${type}`, user_whitelist: currentData.user_whitelist, user_blacklist: currentData.user_blacklist, target_id: id });
            }

            async function updateData(payload) {
                const res = await fetch('/api/data', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
                const json = await res.json();
                currentData = json.data;
                render();
            }

            syncData();
            setInterval(syncData, 2000);
        </script>
    </body>
    </html>
    """
    return html.replace('__COMMON_HEAD__', ADMIN_COMMON_HEAD).replace('__CLIENT_ID__', CLIENT_ID)

# --------------------------------------------------
# 2️⃣ 스태프 매뉴얼 사이트 HTML (소스코드 2번 디자인 + 보안 시스템)
# --------------------------------------------------
STAFF_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, shrink-to-fit=no">
    <title>SKY AURORA STAFF 매뉴얼</title>
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
        .alert-main-text { font-size: 26px; font-weight: bold; color: #ff2d55; letter-spacing: -0.5px; margin-bottom: 12px; font-family: 'GmarketSansBold', sans-serif; text-shadow: 0 0 20px rgba(255, 45, 85, 0.6); }
        .alert-sub-text { font-size: 15px; color: #a0aec0; font-family: 'Pretendard', sans-serif; line-height: 1.6; }
        @keyframes pulse { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.15); opacity: 0.7; } 100% { transform: scale(1); opacity: 1; } }
        #bg-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 1; }
        .container {
            position: relative; z-index: 2; width: 92%; max-width: 1100px; height: 88vh;
            background: rgba(8, 12, 24, 0.8); backdrop-filter: blur(25px); border: 1px solid rgba(0, 255, 200, 0.25);
            border-radius: 24px; box-shadow: 0 0 60px rgba(0, 255, 170, 0.12), inset 0 0 30px rgba(0, 255, 170, 0.03);
            display: flex; flex-direction: column; overflow: hidden; animation: containerAppear 0.9s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes containerAppear { 0% { opacity: 0; transform: translateY(30px) scale(0.95); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
        header { padding: 18px 28px; background: rgba(5, 8, 18, 0.9); border-bottom: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between; align-items: center; }
        header h1 { font-size: 20px; font-weight: bold; letter-spacing: 1px; background: linear-gradient(90deg, #00f2fe, #4facfe, #00ffaa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; animation: glowText 3s infinite alternate; }
        @keyframes glowText { 0% { filter: drop-shadow(0 0 2px rgba(0, 242, 254, 0.2)); } 100% { filter: drop-shadow(0 0 12px rgba(0, 255, 170, 0.7)); } }
        header .user-info { display: flex; align-items: center; gap: 12px; }
        .avatar-img { width: 36px; height: 36px; border-radius: 50%; border: 2px solid #00ffaa; object-fit: cover; box-shadow: 0 0 10px rgba(0, 255, 170, 0.4); }
        header .logout-btn { font-family: 'Pretendard', sans-serif; color: #8a99ad; text-decoration: none; font-size: 12px; padding: 6px 14px; border: 1px solid rgba(255,255,255,0.15); border-radius: 8px; transition: all 0.3s ease; }
        header .logout-btn:hover { color: #fff; border-color: #00ffaa; box-shadow: 0 0 12px rgba(0, 255, 170, 0.3); background: rgba(0, 255, 170, 0.1); }
        .login-box { padding: 50px 28px; text-align: center; margin: auto; max-width: 380px; width: 100%; background: rgba(13, 20, 38, 0.75); border: 1px solid rgba(0, 255, 170, 0.2); border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.6), 0 0 25px rgba(0, 255, 170, 0.1); animation: fadeIn 0.6s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(15px); } to { opacity: 1; transform: translateY(0); } }
        .discord-btn { display: flex; align-items: center; justify-content: center; gap: 12px; width: 100%; padding: 15px; background: #5865F2; color: white; text-decoration: none; border-radius: 12px; font-family: 'Pretendard', sans-serif; font-weight: bold; font-size: 15px; transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1); box-shadow: 0 4px 15px rgba(88, 101, 242, 0.4); cursor: pointer; border: none; }
        .discord-btn:hover { background: #4752C4; transform: translateY(-3px) scale(1.02); box-shadow: 0 8px 25px rgba(88, 101, 242, 0.7); }
        .dashboard { display: flex; flex: 1; overflow: hidden; }
        .sidebar { width: 280px; background: rgba(0, 0, 0, 0.35); border-right: 1px solid rgba(255, 255, 255, 0.08); padding: 24px 14px; overflow-y: auto; }
        .sidebar h2 { font-size: 11px; color: #00ffaa; letter-spacing: 1.5px; margin-bottom: 20px; padding-left: 8px; text-transform: uppercase; }
        .aurora-btn-wrapper { position: relative; margin-bottom: 12px; border-radius: 14px; overflow: hidden; padding: 2px; background: rgba(255, 255, 255, 0.03); transition: transform 0.25s ease, box-shadow 0.3s ease; }
        .aurora-btn-wrapper::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: conic-gradient(from 0deg, transparent 0%, #ff007f 25%, #7928ca 50%, #ff0080 75%, transparent 100%); animation: rotateAurora 4s linear infinite; opacity: 0; transition: opacity 0.3s ease; }
        .aurora-btn-wrapper:hover::before { opacity: 1; }
        .aurora-btn-wrapper:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(255, 0, 128, 0.3); }
        .aurora-btn-wrapper.active::before { opacity: 1; background: conic-gradient(from 0deg, transparent 0%, #00ffaa 25%, #00d2ff 50%, #0051ff 75%, #00ffaa 100%) !important; animation: rotateAurora 2s linear infinite !important; }
        .aurora-btn-wrapper.active { box-shadow: 0 0 25px rgba(0, 255, 170, 0.4); }
        .item-btn { position: relative; z-index: 1; width: 100%; text-align: left; padding: 14px 18px; background: rgba(10, 16, 32, 0.95); border: none; color: #8a99ad; border-radius: 12px; cursor: pointer; font-size: 14px; transition: color 0.2s, background 0.2s; display: block; }
        .aurora-btn-wrapper:hover .item-btn { color: #ff77c6; }
        .aurora-btn-wrapper.active .item-btn { color: #00ffaa; font-weight: bold; background: rgba(6, 24, 38, 0.95); }
        @keyframes rotateAurora { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        .main-content { flex: 1; padding: 40px; overflow-y: auto; display: flex; flex-direction: column; position: relative; }
        .doc-wrapper { display: flex; flex-direction: column; flex: 1; transition: opacity 0.3s ease, transform 0.3s ease; }
        .doc-wrapper.manual-enter { animation: manualEnter 0.45s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        .doc-wrapper.manual-exit { animation: manualExit 0.3s cubic-bezier(0.7, 0, 0.84, 0) forwards; }
        @keyframes manualEnter { 0% { opacity: 0; transform: translateY(35px) scale(0.98); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
        @keyframes manualExit { 0% { opacity: 1; transform: translateY(0) scale(1); } 100% { opacity: 0; transform: translateY(35px) scale(0.98); } }
        .doc-title { font-size: 24px; margin-bottom: 24px; color: #ffffff; border-bottom: 1px solid rgba(255, 255, 255, 0.12); padding-bottom: 16px; letter-spacing: 0.5px; display: flex; align-items: center; gap: 10px; }
        .doc-title::before { content: ''; display: inline-block; width: 4px; height: 22px; background: #00ffaa; border-radius: 2px; box-shadow: 0 0 10px #00ffaa; }
        .doc-body { font-family: 'Pretendard', sans-serif; font-weight: 500; font-size: 15px; line-height: 1.9; color: #cbd5e1; white-space: pre-wrap; flex: 1; background: rgba(0, 0, 0, 0.2); padding: 24px; border-radius: 16px; border: 1px solid rgba(255, 255, 255, 0.05); }
    </style>
    <script>
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

        let isTransitioning = false;
        function selectManual(btnElement) {
            if (isTransitioning) return;
            const targetWrapper = btnElement.closest('.aurora-btn-wrapper');
            if (targetWrapper.classList.contains('active')) return;
            isTransitioning = true;
            document.querySelectorAll('.aurora-btn-wrapper').forEach(w => w.classList.remove('active'));
            targetWrapper.classList.add('active');

            const title = btnElement.getAttribute('data-title');
            const content = btnElement.getAttribute('data-content');

            const docWrapper = document.getElementById('doc-wrapper');
            const titleEl = document.getElementById('doc-title');
            const bodyEl = document.getElementById('doc-body');

            docWrapper.classList.remove('manual-enter');
            docWrapper.classList.add('manual-exit');

            setTimeout(() => {
                titleEl.innerText = title;
                bodyEl.innerText = content;
                docWrapper.classList.remove('manual-exit');
                docWrapper.classList.add('manual-enter');
                setTimeout(() => { isTransitioning = false; }, 450);
            }, 300);
        }

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
            <h1>SKY AURORA STAFF 매뉴얼</h1>
            <div id="user-header-info" class="user-info" style="display:none;">
                <img id="user-avatar" src="" alt="Avatar" class="avatar-img" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                <span id="user-name" style="font-size: 13px; color: #00ffaa; font-family: 'Pretendard';"></span>
                <a href="/logout" class="logout-btn">로그아웃</a>
            </div>
        </header>

        <div id="login-box" class="login-box">
            <h2 style="font-size: 18px; color: #e2e8f0; margin-bottom: 24px; font-family: 'GmarketSansBold';">🔒 스태프 인증</h2>
            <button onclick="login('user')" class="discord-btn">
                <svg width="22" height="17" viewBox="0 0 127.14 96.36" fill="currentColor">
                    <path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1,105.25,105.25,0,0,0,32.19-16.14c2.64-27.38-4.51-51.11-18.91-72.15ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,45.91,53.87,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,45.91,96.1,53,91.08,65.69,84.69,65.69Z"/>
                </svg>
                Discord 계정으로 로그인
            </button>
        </div>

        <div id="staff-dashboard" class="dashboard" style="display:none;">
            <div class="sidebar">
                <h2>Manual List</h2>
                <div id="sidebar-list"></div>
            </div>
            <div class="main-content">
                <div id="doc-wrapper" class="doc-wrapper manual-enter">
                    <div id="doc-title" class="doc-title">매뉴얼 불러오는 중...</div>
                    <div id="doc-body" class="doc-body"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
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

        async function syncUserData() {
            try {
                const res = await fetch('/api/user_data');
                if (res.status === 403) {
                    alert("권한이 변경되었거나 차단되어 접속할 수 없습니다.");
                    location.reload();
                    return;
                }
                if (res.ok) {
                    const data = await res.json();
                    document.getElementById('login-box').style.display = 'none';
                    document.getElementById('staff-dashboard').style.display = 'flex';
                    document.getElementById('user-header-info').style.display = 'flex';

                    if(data.user) {
                        const avatarUrl = data.user.avatar ? `https://cdn.discordapp.com/avatars/${data.user.id}/${data.user.avatar}.png` : 'https://cdn.discordapp.com/embed/avatars/0.png';
                        document.getElementById('user-avatar').src = avatarUrl;
                        document.getElementById('user-name').innerText = data.user.username;
                    }

                    const sidebarList = document.getElementById('sidebar-list');
                    if (data.manuals && data.manuals.length > 0) {
                        sidebarList.innerHTML = data.manuals.map((m, idx) => `
                            <div class="aurora-btn-wrapper ${idx === 0 ? 'active' : ''}">
                                <button class="item-btn" data-title="${m.title}" data-content="${m.content}" onclick="selectManual(this)">
                                    ${m.title}
                                </button>
                            </div>
                        `).join('');

                        document.getElementById('doc-title').innerText = data.manuals[0].title;
                        document.getElementById('doc-body').innerText = data.manuals[0].content;
                    } else {
                        document.getElementById('doc-title').innerText = "등록된 매뉴얼이 없습니다.";
                        document.getElementById('doc-body').innerText = "";
                    }
                }
            } catch (e) { console.error("Sync error:", e); }
        }

        syncUserData();
        setInterval(syncUserData, 2000);
    </script>
</body>
</html>
"""

@app.route('/user')
def user_page():
    return STAFF_HTML_TEMPLATE.replace('__CLIENT_ID__', CLIENT_ID)

# --------------------------------------------------
# 🔑 OAuth2 Callback 및 라우팅 처리
# --------------------------------------------------
@app.route('/callback')
def callback():
    code = request.args.get('code')
    target = request.args.get('target', 'admin')
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
                    return f"<h2 style='color:#ef4444; text-align:center; margin-top:100px;'>접근 거부: 어드민 권한이 없습니다. (ID: {user_id})</h2>", 403
                session['admin_user'] = user_info
                add_log(data, "어드민", user_info.get('username'), f"어드민 사이트 접속 성공 (ID: {user_id})")
                save_data(data)
                return redirect('/')

            else:
                if user_id in data.get('user_blacklist', []):
                    return "<h2 style='color:#ef4444; text-align:center; margin-top:100px;'>접근 차단: 블랙리스트 계정입니다.</h2>", 403

                if data.get('user_whitelist') and user_id not in data.get('user_whitelist'):
                    return "<h2 style='color:#ef4444; text-align:center; margin-top:100px;'>접근 거부: 화이트리스트 지정 유저만 접속 가능합니다.</h2>", 403

                session['site_user'] = user_info
                add_log(data, "스태프 매뉴얼", user_info.get('username'), f"스태프 매뉴얼 사이트 접속 (ID: {user_id})")
                save_data(data)
                return redirect('/user')

    return "로그인 인증 실패", 400

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# --------------------------------------------------
# 🛠️ API 라우트 (어드민 / 스태프 / 외부 PyQt 앱 연동)
# --------------------------------------------------
@app.route('/api/data', methods=['GET', 'POST'])
def handle_admin_data():
    data = load_data()
    user = session.get('admin_user')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    if request.method == 'POST':
        req = request.get_json()
        action = req.get('action')
        if 'manuals' in req: data['manuals'] = req['manuals']
        if 'user_whitelist' in req: data['user_whitelist'] = req['user_whitelist']
        if 'user_blacklist' in req: data['user_blacklist'] = req['user_blacklist']

        if action == 'save_manual': add_log(data, "어드민", user.get('username'), f"매뉴얼 저장/수정 ({req.get('title')})")
        elif action == 'delete_manual': add_log(data, "어드민", user.get('username'), f"매뉴얼 삭제 ({req.get('title')})")
        elif action == 'add_whitelist': add_log(data, "어드민", user.get('username'), f"스태프 화이트 추가 ({req.get('target_id')})")
        elif action == 'add_blacklist': add_log(data, "어드민", user.get('username'), f"스태프 블랙 추가 ({req.get('target_id')})")
        elif action == 'remove_whitelist': add_log(data, "어드민", user.get('username'), f"스태프 화이트 삭제 ({req.get('target_id')})")
        elif action == 'remove_blacklist': add_log(data, "어드민", user.get('username'), f"스태프 블랙 해제 ({req.get('target_id')})")

        save_data(data)
        return jsonify({"status": "ok", "data": data})

    return jsonify({"user": user, "user_whitelist": data.get("user_whitelist", []), "user_blacklist": data.get("user_blacklist", []), "manuals": data.get("manuals", []), "logs": data.get("logs", [])})

@app.route('/api/user_data')
def handle_user_data():
    user = session.get('site_user')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    user_id = str(user.get('id'))
    data = load_data()

    if user_id in data.get('user_blacklist', []):
        session.pop('site_user', None)
        return jsonify({"status": "forbidden", "message": "blacklisted"}), 403

    if data.get('user_whitelist') and user_id not in data.get('user_whitelist'):
        session.pop('site_user', None)
        return jsonify({"status": "forbidden", "message": "not_whitelisted"}), 403

    return jsonify({"user": user, "manuals": data.get("manuals", [])})

# PyQt6 외부 애플리케이션용 API
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
        new_manual = {
            "id": new_id,
            "title": req_data.get("title", ""),
            "content": req_data.get("content", "")
        }
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
