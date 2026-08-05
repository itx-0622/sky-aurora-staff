import os
import requests
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = 'sky_aurora_secret_key_9988'

ACCESS_LOGS = []

# ==========================================
# ⚙️ 관리자(오너) 디스코드 ID 및 API 보안 키
# ==========================================
OWNER_DISCORD_ID = "843621337066504225"
ADMIN_SECRET_KEY = "sky_aurora_admin_secret_key_1234"

# 블랙리스트 ID 목록 (메모리 저장)
BLACKLIST_IDS = set()

# --------------------------------------------------
# 🔑 디스코드 OAuth2 설정
# --------------------------------------------------
DISCORD_CLIENT_ID = "1534184089144266872"
DISCORD_CLIENT_SECRET = "HRe8MKk_MY81RnMGIVJifNIByYDCq7es"
DISCORD_REDIRECT_URI = "https://sky-aurora-staff.onrender.com/callback"

DISCORD_AUTH_URL = (
    f"https://discord.com/api/oauth2/authorize"
    f"?client_id={DISCORD_CLIENT_ID}"
    f"&redirect_uri={DISCORD_REDIRECT_URI}"
    f"&response_type=code"
    f"&scope=identify%20email"
)

MANUALS = [
    {
        "id": 1,
        "title": "01. 기본 보안 지침",
        "content": "본 매뉴얼 시스템에 포함된 모든 정보는 외부 유출이 엄격히 금지됩니다.\n\n1. 본 시스템의 화면을 캡처하거나 촬영하는 행위를 금지합니다.\n2. 인증 계정은 타인에게 공유할 수 없습니다.\n3. 시스템 이용 시 접속 IP 및 접근 위치가 실시간 기록됩니다."
    },
    {
        "id": 2,
        "title": "02. 스태프 업무 수칙",
        "content": "SKY AURORA 스태프 업무 수행 시 아래 수칙을 준수해야 합니다.\n\n- 모든 변경 사항은 관리자 승인 후 반영되어야 합니다.\n- 시스템 장애 및 이상 접근 감지 시 즉시 보고를 진행합니다.\n- 공지사항을 정기적으로 확인하고 업데이트 내역을 숙지하세요."
    },
    {
        "id": 3,
        "title": "03. 비상 대응 프로토콜",
        "content": "비상 상황 발생 시 아래 절차에 따라 즉시 조치하십시오.\n\n1. 보안 침해 감지 즉시 오너/관리자에게 디스코드 DM 보고\n2. 영향받은 서버 및 접속 세션 즉시 격리\n3. 상세 로그 수집 후 보고서 작성"
    }
]

def get_location_from_ip(ip_address):
    if ip_address in ['127.0.0.1', 'localhost', '::1']:
        return "로컬 접속 (관리자/테스트)"
        
    try:
        url = f"http://ip-api.com/json/{ip_address}"
        res = requests.get(url, timeout=1).json()
        if res.get('status') == 'success':
            country = res.get('country', 'Unknown')
            city = res.get('city', 'Unknown')
            isp = res.get('isp', 'Unknown')
            return f"{country}, {city} ({isp})"
    except Exception:
        pass
    return "위치 정보 확인 불가"

HTML_TEMPLATE = """
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
            font-weight: normal;
            font-style: normal;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            -webkit-user-select: none !important;
            -moz-user-select: none !important;
            -ms-user-select: none !important;
            user-select: none !important;
            -webkit-touch-callout: none !important;
            -webkit-tap-highlight-color: transparent;
        }

        body {
            font-family: 'GmarketSansBold', 'Pretendard', sans-serif;
            background: #030509;
            color: #ffffff;
            overflow: hidden;
            height: 100vh;
            width: 100vw;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        /* 🔒 보안 경고 오버레이 */
        #security-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: #000000;
            z-index: 99999999;
            display: none;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 20px;
        }

        .alert-icon {
            font-size: 80px;
            color: #ff2d55;
            margin-bottom: 20px;
            animation: pulse 1.2s infinite ease-in-out;
        }

        .alert-main-text {
            font-size: 26px;
            font-weight: bold;
            color: #ff2d55;
            letter-spacing: -0.5px;
            margin-bottom: 12px;
            font-family: 'GmarketSansBold', sans-serif;
            text-shadow: 0 0 20px rgba(255, 45, 85, 0.6);
        }

        .alert-sub-text {
            font-size: 15px;
            color: #a0aec0;
            font-family: 'Pretendard', sans-serif;
            line-height: 1.6;
        }

        @keyframes pulse {
            0% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.15); opacity: 0.7; }
            100% { transform: scale(1); opacity: 1; }
        }

        #bg-canvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 1;
        }

        /* 메인 컨테이너 카드 */
        .container {
            position: relative;
            z-index: 2;
            width: 92%;
            max-width: 1100px;
            height: 88vh;
            background: rgba(8, 12, 24, 0.8);
            backdrop-filter: blur(25px);
            border: 1px solid rgba(0, 255, 200, 0.25);
            border-radius: 24px;
            box-shadow: 0 0 60px rgba(0, 255, 170, 0.12), inset 0 0 30px rgba(0, 255, 170, 0.03);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            animation: containerAppear 0.9s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes containerAppear {
            0% { opacity: 0; transform: translateY(30px) scale(0.95); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
        }

        header {
            padding: 18px 28px;
            background: rgba(5, 8, 18, 0.9);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 {
            font-size: 20px;
            font-weight: bold;
            letter-spacing: 1px;
            background: linear-gradient(90deg, #00f2fe, #4facfe, #00ffaa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            animation: glowText 3s infinite alternate;
        }

        @keyframes glowText {
            0% { filter: drop-shadow(0 0 2px rgba(0, 242, 254, 0.2)); }
            100% { filter: drop-shadow(0 0 12px rgba(0, 255, 170, 0.7)); }
        }

        header .user-info {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .avatar-img {
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: 2px solid #00ffaa;
            object-fit: cover;
            box-shadow: 0 0 10px rgba(0, 255, 170, 0.4);
        }

        header .logout-btn {
            font-family: 'Pretendard', sans-serif;
            color: #8a99ad;
            text-decoration: none;
            font-size: 12px;
            padding: 6px 14px;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        header .logout-btn:hover {
            color: #fff;
            border-color: #00ffaa;
            box-shadow: 0 0 12px rgba(0, 255, 170, 0.3);
            background: rgba(0, 255, 170, 0.1);
        }

        /* 로그인 박스 파트 */
        .login-box {
            padding: 50px 28px;
            text-align: center;
            margin: auto;
            max-width: 380px;
            width: 100%;
            background: rgba(13, 20, 38, 0.75);
            border: 1px solid rgba(0, 255, 170, 0.2);
            border-radius: 20px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.6), 0 0 25px rgba(0, 255, 170, 0.1);
            animation: fadeIn 0.6s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(15px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .discord-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
            width: 100%;
            padding: 15px;
            background: #5865F2;
            color: white;
            text-decoration: none;
            border-radius: 12px;
            font-family: 'Pretendard', sans-serif;
            font-weight: bold;
            font-size: 15px;
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            box-shadow: 0 4px 15px rgba(88, 101, 242, 0.4);
        }
        .discord-btn:hover {
            background: #4752C4;
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 8px 25px rgba(88, 101, 242, 0.7);
        }

        /* 대시보드 레이아웃 */
        .dashboard {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        .sidebar {
            width: 280px;
            background: rgba(0, 0, 0, 0.35);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
            padding: 24px 14px;
            overflow-y: auto;
        }
        .sidebar h2 {
            font-size: 11px;
            color: #00ffaa;
            letter-spacing: 1.5px;
            margin-bottom: 20px;
            padding-left: 8px;
            text-transform: uppercase;
        }

        .aurora-btn-wrapper {
            position: relative;
            margin-bottom: 12px;
            border-radius: 14px;
            overflow: hidden;
            padding: 2px;
            background: rgba(255, 255, 255, 0.03);
            transition: transform 0.25s ease, box-shadow 0.3s ease;
        }

        .aurora-btn-wrapper::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: conic-gradient(
                from 0deg,
                transparent 0%,
                #ff007f 25%,
                #7928ca 50%,
                #ff0080 75%,
                transparent 100%
            );
            animation: rotateAurora 4s linear infinite;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .aurora-btn-wrapper:hover::before { opacity: 1; }
        .aurora-btn-wrapper:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(255, 0, 128, 0.3);
        }

        .aurora-btn-wrapper.active::before {
            opacity: 1;
            background: conic-gradient(
                from 0deg,
                transparent 0%,
                #00ffaa 25%,
                #00d2ff 50%,
                #0051ff 75%,
                #00ffaa 100%
            ) !important;
            animation: rotateAurora 2s linear infinite !important;
        }
        .aurora-btn-wrapper.active {
            box-shadow: 0 0 25px rgba(0, 255, 170, 0.4);
        }

        .item-btn {
            position: relative;
            z-index: 1;
            width: 100%;
            text-align: left;
            padding: 14px 18px;
            background: rgba(10, 16, 32, 0.95);
            border: none;
            color: #8a99ad;
            border-radius: 12px;
            cursor: pointer;
            font-size: 14px;
            transition: color 0.2s, background 0.2s;
            display: block;
        }

        .aurora-btn-wrapper:hover .item-btn { color: #ff77c6; }
        .aurora-btn-wrapper.active .item-btn {
            color: #00ffaa;
            font-weight: bold;
            background: rgba(6, 24, 38, 0.95);
        }

        @keyframes rotateAurora {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .main-content {
            flex: 1;
            padding: 40px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            position: relative;
        }

        /* 🎬 매뉴얼 영역 애니메이션 클래스 */
        .doc-wrapper {
            display: flex;
            flex-direction: column;
            flex: 1;
            transition: opacity 0.3s ease, transform 0.3s ease;
        }

        .doc-wrapper.manual-enter {
            animation: manualEnter 0.45s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        .doc-wrapper.manual-exit {
            animation: manualExit 0.3s cubic-bezier(0.7, 0, 0.84, 0) forwards;
        }

        @keyframes manualEnter {
            0% {
                opacity: 0;
                transform: translateY(35px) scale(0.98);
            }
            100% {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        @keyframes manualExit {
            0% {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
            100% {
                opacity: 0;
                transform: translateY(35px) scale(0.98);
            }
        }

        .doc-title {
            font-size: 24px;
            margin-bottom: 24px;
            color: #ffffff;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
            padding-bottom: 16px;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .doc-title::before {
            content: '';
            display: inline-block;
            width: 4px;
            height: 22px;
            background: #00ffaa;
            border-radius: 2px;
            box-shadow: 0 0 10px #00ffaa;
        }

        .doc-body {
            font-family: 'Pretendard', sans-serif;
            font-weight: 500;
            font-size: 15px;
            line-height: 1.9;
            color: #cbd5e1;
            white-space: pre-wrap;
            flex: 1;
            background: rgba(0, 0, 0, 0.2);
            padding: 24px;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.05);
        }

        /* 📱 모바일 반응형 디자인 */
        @media (max-width: 768px) {
            .container {
                width: 95%;
                height: 94vh;
                border-radius: 18px;
            }
            header {
                padding: 14px 18px;
            }
            header h1 {
                font-size: 16px;
            }
            .user-info span {
                display: none;
            }
            .dashboard {
                flex-direction: column;
            }
            .sidebar {
                width: 100%;
                max-height: 160px;
                border-right: none;
                border-bottom: 1px solid rgba(255, 255, 255, 0.08);
                padding: 12px;
            }
            .main-content {
                padding: 20px;
            }
            .doc-title {
                font-size: 18px;
            }
            .doc-body {
                font-size: 14px;
                padding: 16px;
            }
        }
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
            if (
                e.key === 'Shift' || e.key === 'Meta' || e.key === 'Alt' || 
                e.key === 'Control' || e.key === 'PrintScreen' || e.key === 'F12'
            ) {
                triggerSecurityLock();
            }

            const k = e.key.toLowerCase();
            if (
                (e.ctrlKey && ['c', 'v', 'u', 's', 'p', 'a', 'i', 'j'].includes(k)) ||
                (e.metaKey && ['c', 'v', 'u', 's', 'p', 'a', 'i', 'j'].includes(k))
            ) {
                triggerSecurityLock();
            }
        }, true);

        document.addEventListener('keyup', function(e) {
            if (!e.shiftKey && !e.metaKey && !e.ctrlKey && !e.altKey) {
                releaseSecurityLock();
            }
        });

        window.addEventListener('blur', triggerSecurityLock);
        window.addEventListener('focus', releaseSecurityLock);
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                triggerSecurityLock();
            } else {
                releaseSecurityLock();
            }
        });
        window.addEventListener('pagehide', triggerSecurityLock);

        document.addEventListener('mouseleave', function(e) {
            if (e.clientY <= 0) {
                triggerSecurityLock();
            }
        });

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

                setTimeout(() => {
                    isTransitioning = false;
                }, 450);
            }, 300);
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
            {% if authenticated %}
                <div class="user-info">
                    {% if avatar_url %}
                        <img src="{{ avatar_url }}" alt="Avatar" class="avatar-img">
                    {% endif %}
                    <span style="font-size: 13px; color: #00ffaa; font-family: 'Pretendard';">
                        {{ username }}
                    </span>
                    <a href="/logout" class="logout-btn">로그아웃</a>
                </div>
            {% endif %}
        </header>

        {% if not authenticated %}
            <div class="login-box">
                <h2 style="font-size: 18px; color: #e2e8f0; margin-bottom: 24px; font-family: 'GmarketSansBold';">🔒 스태프 인증</h2>
                
                {% if error %}
                    <div style="color:#ff5555; margin-bottom:15px; font-family: 'Pretendard'; font-size:13px; font-weight: bold;">{{ error }}</div>
                {% endif %}

                <a href="/login/discord" class="discord-btn">
                    <svg width="22" height="17" viewBox="0 0 127.14 96.36" fill="currentColor">
                        <path d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1,105.25,105.25,0,0,0,32.19-16.14c2.64-27.38-4.51-51.11-18.91-72.15ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,45.91,53.87,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,45.91,96.1,53,91.08,65.69,84.69,65.69Z"/>
                    </svg>
                    Discord 계정으로 로그인
                </a>
            </div>
        {% else %}
            <div class="dashboard">
                <div class="sidebar">
                    <h2>Manual List</h2>
                    {% for item in manuals %}
                        <div class="aurora-btn-wrapper {% if loop.first %}active{% endif %}">
                            <button id="btn-{{ item.id }}" 
                                    class="item-btn" 
                                    data-title="{{ item.title }}"
                                    data-content="{{ item.content }}"
                                    onclick="selectManual(this)">
                                {{ item.title }}
                            </button>
                        </div>
                    {% endfor %}
                </div>
                <div class="main-content">
                    <div id="doc-wrapper" class="doc-wrapper manual-enter">
                        <div id="doc-title" class="doc-title">{{ manuals[0].title if manuals else '매뉴얼이 없습니다.' }}</div>
                        <div id="doc-body" class="doc-body">{{ manuals[0].content if manuals else '' }}</div>
                    </div>
                </div>
            </div>
        {% endif %}
    </div>

    <script>
        const canvas = document.getElementById('bg-canvas');
        const ctx = canvas.getContext('2d');

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        window.addEventListener('resize', resize);
        resize();

        const stars = Array.from({ length: 160 }, () => ({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            size: Math.random() * 2,
            alpha: Math.random(),
            speed: Math.random() * 0.012 + 0.005
        }));

        let tick = 0;

        function drawRibbonAurora(yOffset, waveHeight, color1, color2, speedMult) {
            ctx.save();
            ctx.beginPath();
            
            const startY = yOffset + Math.sin(tick * speedMult) * 25;
            ctx.moveTo(0, startY);

            for (let x = 0; x <= canvas.width; x += 25) {
                const y = yOffset + 
                          Math.sin(x * 0.0025 + tick * speedMult) * waveHeight + 
                          Math.cos(x * 0.0012 + tick * 0.6) * (waveHeight * 0.6);
                ctx.lineTo(x, y);
            }

            ctx.lineTo(canvas.width, startY + 240);
            ctx.lineTo(0, startY + 240);
            ctx.closePath();

            const grad = ctx.createLinearGradient(0, yOffset - 50, canvas.width, yOffset + 250);
            grad.addColorStop(0, color1);
            grad.addColorStop(1, color2);

            ctx.fillStyle = grad;
            ctx.filter = 'blur(28px)';
            ctx.fill();
            ctx.restore();
        }

        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);

            stars.forEach(s => {
                s.alpha += s.speed;
                if (s.alpha > 1 || s.alpha < 0) s.speed = -s.speed;
                ctx.fillStyle = `rgba(255, 255, 255, ${Math.abs(s.alpha)})`;
                ctx.beginPath();
                ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
                ctx.fill();
            });

            tick += 0.015;

            drawRibbonAurora(canvas.height * 0.05, 75, 'rgba(0, 255, 170, 0.35)', 'rgba(0, 150, 255, 0.04)', 0.8);
            drawRibbonAurora(canvas.height * 0.09, 95, 'rgba(0, 180, 255, 0.25)', 'rgba(140, 0, 255, 0.03)', 1.2);
            drawRibbonAurora(canvas.height * 0.15, 60, 'rgba(255, 0, 128, 0.15)', 'rgba(0, 255, 170, 0.02)', 0.5);

            requestAnimationFrame(animate);
        }
        animate();
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    is_auth = session.get('authenticated', False)
    username = session.get('username', '스태프')
    avatar_url = session.get('avatar_url')
    return render_template_string(
        HTML_TEMPLATE, 
        authenticated=is_auth, 
        username=username,
        avatar_url=avatar_url,
        manuals=MANUALS
    )

@app.route('/login/discord')
def login_discord():
    return redirect(DISCORD_AUTH_URL)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return render_template_string(
            HTML_TEMPLATE, 
            authenticated=False, 
            error="❌ 디스코드 인증에 실패했습니다.",
            manuals=MANUALS
        )

    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': DISCORD_REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    token_res = requests.post('https://discord.com/api/v10/oauth2/token', data=data, headers=headers)
    token_json = token_res.json()

    access_token = token_json.get('access_token')
    if not access_token:
        return render_template_string(
            HTML_TEMPLATE, 
            authenticated=False, 
            error="❌ 토큰 발급에 실패했습니다.",
            manuals=MANUALS
        )

    user_headers = {'Authorization': f'Bearer {access_token}'}
    user_res = requests.get('https://discord.com/api/v10/users/@me', headers=user_headers)
    user_data = user_res.json()

    discord_id = str(user_data.get('id', 'Unknown'))
    
    if discord_id in BLACKLIST_IDS:
        return render_template_string(
            HTML_TEMPLATE, 
            authenticated=False, 
            error="❌ 차단된 사용자 계정입니다.",
            manuals=MANUALS
        )

    username = user_data.get('global_name') or user_data.get('username', 'Unknown')
    avatar_hash = user_data.get('avatar')
    
    avatar_url = None
    if avatar_hash:
        avatar_url = f"https://cdn.discordapp.com/avatars/{discord_id}/{avatar_hash}.png"

    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip and ',' in user_ip:
        user_ip = user_ip.split(',')[0].strip()

    location_info = get_location_from_ip(user_ip)
    now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    ACCESS_LOGS.insert(0, {
        "discord_id": discord_id,
        "user": username,
        "ip": user_ip,
        "location": location_info,
        "time": now_time,
        "type": "Discord OAuth"
    })

    session['authenticated'] = True
    session['discord_id'] = discord_id
    session['username'] = username
    session['avatar_url'] = avatar_url
    
    return redirect(url_for('index'))

@app.route('/admin/logs')
def admin_logs():
    discord_id = session.get('discord_id')
    if discord_id != OWNER_DISCORD_ID:
        return jsonify({"error": "Unauthorized"}), 403
    return jsonify(ACCESS_LOGS)

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    session.pop('discord_id', None)
    session.pop('username', None)
    session.pop('avatar_url', None)
    return redirect(url_for('index'))

# ==================================================
# 🛠️ 관리자 앱 연동 API (PyQt6 앱 전용 경로)
# ==================================================
def check_admin_auth():
    auth_key = request.headers.get('X-Admin-Key')
    return auth_key == ADMIN_SECRET_KEY

@app.route('/api/admin/manuals', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_admin_manuals():
    global MANUALS
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == 'GET':
        return jsonify(MANUALS)

    elif request.method == 'POST':
        data = request.json
        new_id = max([m['id'] for m in MANUALS], default=0) + 1
        new_manual = {
            "id": new_id,
            "title": data.get("title", ""),
            "content": data.get("content", "")
        }
        MANUALS.append(new_manual)
        return jsonify({"status": "success", "manual": new_manual})

    elif request.method == 'PUT':
        data = request.json
        target_id = data.get("id")
        for m in MANUALS:
            if m['id'] == target_id:
                m['title'] = data.get("title", m['title'])
                m['content'] = data.get("content", m['content'])
                return jsonify({"status": "success", "manual": m})
        return jsonify({"error": "Not found"}), 404

    elif request.method == 'DELETE':
        manual_id = request.args.get('id', type=int)
        MANUALS = [m for m in MANUALS if m['id'] != manual_id]
        return jsonify({"status": "success"})

@app.route('/api/admin/blacklist', methods=['GET', 'POST', 'DELETE'])
def api_admin_blacklist():
    if not check_admin_auth():
        return jsonify({"error": "Unauthorized"}), 401

    if request.method == 'GET':
        return jsonify(list(BLACKLIST_IDS))

    elif request.method == 'POST':
        discord_id = str(request.json.get('discord_id', '')).strip()
        if discord_id:
            BLACKLIST_IDS.add(discord_id)
            return jsonify({"status": "success", "blacklist": list(BLACKLIST_IDS)})

    elif request.method == 'DELETE':
        discord_id = str(request.args.get('discord_id', '')).strip()
        BLACKLIST_IDS.discard(discord_id)
        return jsonify({"status": "success", "blacklist": list(BLACKLIST_IDS)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
