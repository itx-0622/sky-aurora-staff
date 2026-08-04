import os
import requests
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'sky_aurora_secret_key_9988'

VALID_AUTH_CODE = "1234"
ACCESS_LOGS = []

MANUALS = [
    {
        "id": 1,
        "title": "01. 기본 보안 지침",
        "content": "본 매뉴얼 시스템에 포함된 모든 정보는 외부 유출이 엄격히 금지됩니다.\n\n1. 본 시스템의 화면을 캡처하거나 촬영하는 행위를 금지합니다.\n2. 인증 계정 및 코드는 타인에게 공유할 수 없습니다.\n3. 시스템 이용 시 접속 IP 및 접근 위치가 실시간 기록됩니다."
    },
    {
        "id": 2,
        "title": "02. 스태프 업무 수칙",
        "content": "SKY AURORA 스태프 업무 수행 시 아래 수칙을 준수해야 합니다.\n\n- 모든 변경 사항은 관리자 승인 후 반영되어야 합니다.\n- 시스템 장애 및 이상 접근 감지 시 즉시 보고를 진행합니다.\n- 공지사항을 정기적으로 확인하고 업데이트 내역을 숙지하세요."
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
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
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
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
            user-select: none;
            -webkit-touch-callout: none; /* 모바일 길게 누르기 메뉴 차단 */
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
            transition: filter 0.15s ease, opacity 0.15s ease;
        }

        /* 🔒 보안 가림막 (캡처 / 창 이탈 / 모바일 전환 시 적용) */
        body.security-blur {
            filter: blur(50px) grayscale(100%);
            opacity: 0.05;
        }

        #bg-canvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 1;
        }

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
        }

        header {
            padding: 22px 30px;
            background: rgba(8, 14, 28, 0.85);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        header h1 {
            font-size: 22px;
            font-weight: bold;
            letter-spacing: 1px;
            background: linear-gradient(90deg, #00f2fe, #4facfe, #00ffaa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        header .logout-btn {
            font-family: 'Pretendard', sans-serif;
            color: #8a99ad;
            text-decoration: none;
            font-size: 13px;
            padding: 6px 14px;
            border: 1px solid rgba(255,255,255,0.15);
            border-radius: 6px;
            transition: 0.3s;
        }
        header .logout-btn:hover {
            color: #fff;
            border-color: #00ffaa;
        }

        .login-box {
            padding: 50px 30px;
            text-align: center;
            margin: auto;
            max-width: 400px;
            width: 100%;
        }
        .login-box input[type="password"] {
            font-family: 'Pretendard', sans-serif;
            width: 100%;
            padding: 12px 16px;
            margin-top: 20px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
            border-radius: 8px;
            color: #fff;
            font-size: 16px;
            outline: none;
            text-align: center;
        }
        .login-box input[type="password"]:focus {
            border-color: #00ffaa;
            box-shadow: 0 0 10px rgba(0, 255, 170, 0.3);
        }

        .dashboard {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        .sidebar {
            width: 310px;
            background: rgba(0, 0, 0, 0.25);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
            padding: 24px 14px;
            overflow-y: auto;
        }
        .sidebar h2 {
            font-size: 13px;
            color: #7f8c8d;
            letter-spacing: 1px;
            margin-bottom: 18px;
            padding-left: 8px;
        }

        /* ✨ 오로라 버튼 스타일 ✨ */
        .aurora-btn-wrapper {
            position: relative;
            margin-bottom: 12px;
            border-radius: 12px;
            overflow: hidden;
            padding: 2px;
            background: rgba(255, 255, 255, 0.05);
            transition: transform 0.2s ease, box-shadow 0.3s ease;
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
            animation: rotateAurora 3.5s linear infinite;
            opacity: 0;
            transition: opacity 0.3s ease;
        }

        .aurora-btn-wrapper:hover::before {
            opacity: 1;
        }
        .aurora-btn-wrapper:hover {
            transform: translateY(-2px);
            box-shadow: 0 0 18px rgba(255, 0, 128, 0.35);
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
            animation: rotateAurora 2.5s linear infinite !important;
        }
        .aurora-btn-wrapper.active {
            box-shadow: 0 0 22px rgba(0, 255, 170, 0.45);
        }

        .item-btn {
            position: relative;
            z-index: 1;
            width: 100%;
            text-align: left;
            padding: 14px 18px;
            background: rgba(12, 18, 36, 0.95);
            border: none;
            color: #8a99ad;
            border-radius: 10px;
            cursor: pointer;
            font-size: 15px;
            transition: color 0.2s, background 0.2s;
            display: block;
        }

        .aurora-btn-wrapper:hover .item-btn {
            color: #ff77c6;
        }
        .aurora-btn-wrapper.active .item-btn {
            color: #00ffaa;
            font-weight: bold;
            background: rgba(8, 28, 42, 0.95);
        }

        @keyframes rotateAurora {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .main-content {
            flex: 1;
            padding: 35px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
        }
        .doc-title {
            font-size: 24px;
            margin-bottom: 22px;
            color: #ffffff;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
            padding-bottom: 14px;
            letter-spacing: 0.5px;
        }
        .doc-body {
            font-family: 'Pretendard', sans-serif;
            font-weight: 500;
            font-size: 16px;
            line-height: 1.85;
            color: #e2e8f0;
            white-space: pre-wrap;
            flex: 1;
        }
    </style>
    <script>
        // 우클릭 및 스마트폰 긴 터치 방지
        document.addEventListener('contextmenu', e => e.preventDefault());
        document.addEventListener('touchstart', function(e) {
            if (e.touches.length > 1) e.preventDefault(); // 다중 터치 캡처 시도 차단
        }, { passive: false });

        // PC 캡처 키 및 Win+Shift+S 감지 시 강제 블러
        document.addEventListener('keydown', function(e) {
            // Windows 키, Shift 키, PrintScreen 또는 캡처 관련 조합키 입력 시 화면 가림
            if (e.key === 'PrintScreen' || e.key === 'Meta' || e.key === 'OS' || (e.shiftKey && e.key === 'S')) {
                document.body.classList.add('security-blur');
                navigator.clipboard.writeText('');
                setTimeout(() => {
                    document.body.classList.remove('security-blur');
                }, 2000);
            }

            if (e.key === 'F12' || (e.ctrlKey && ['c', 'u', 's', 'a', 'p'].includes(e.key.toLowerCase()))) {
                e.preventDefault();
                alert('보안 정책상 복사, 인쇄 및 개발자 도구 사용이 금지되어 있습니다.');
            }
        });

        // 모바일/PC 포커스 이탈, 화면 전환, 최근 앱 진입 시 무조건 암전/블러 처리
        function enableBlur() {
            document.body.classList.add('security-blur');
        }
        function disableBlur() {
            document.body.classList.remove('security-blur');
        }

        window.addEventListener('blur', enableBlur);
        window.addEventListener('focus', disableBlur);
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                enableBlur();
            } else {
                disableBlur();
            }
        });

        function selectManual(btnElement) {
            document.querySelectorAll('.aurora-btn-wrapper').forEach(w => w.classList.remove('active'));
            const wrapper = btnElement.closest('.aurora-btn-wrapper');
            if (wrapper) wrapper.classList.add('active');
            
            const title = btnElement.getAttribute('data-title');
            const content = btnElement.getAttribute('data-content');
            
            document.getElementById('doc-title').innerText = title;
            document.getElementById('doc-body').innerText = content;
        }
    </script>
</head>
<body>
    <canvas id="bg-canvas"></canvas>

    <div class="container">
        <header>
            <h1>SKY AURORA STAFF 매뉴얼</h1>
            {% if authenticated %}
                <a href="/logout" class="logout-btn">로그아웃</a>
            {% endif %}
        </header>

        {% if not authenticated %}
            <div class="login-box">
                <h2 style="font-size: 19px; color: #e2e8f0;">🔒 스태프 인증</h2>
                <p style="font-size: 13px; color: #8a99ad; margin-top: 8px; font-family: 'Pretendard';">인가된 접근 코드를 입력해 주세요.</p>
                {% if error %}
                    <div class="alert-error" style="color:#ff5555; margin-top:10px;">{{ error }}</div>
                {% endif %}
                <form method="POST" action="/login">
                    <input type="password" name="auth_code" placeholder="인증코드 입력" required autocomplete="off">
                    <div class="aurora-btn-wrapper active" style="margin-top: 18px;">
                        <button type="submit" class="item-btn" style="text-align: center; font-family: 'GmarketSansBold'; font-size: 16px;">인증하기</button>
                    </div>
                </form>
            </div>
        {% else %}
            <div class="dashboard">
                <div class="sidebar">
                    <h2>MANUAL LIST</h2>
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
                    <div id="doc-title" class="doc-title">{{ manuals[0].title if manuals else '매뉴얼이 없습니다.' }}</div>
                    <div id="doc-body" class="doc-body">{{ manuals[0].content if manuals else '' }}</div>
                </div>
            </div>
        {% endif %}
    </div>

    <!-- 배경 애니메이션 -->
    <script>
        const canvas = document.getElementById('bg-canvas');
        const ctx = canvas.getContext('2d');

        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        window.addEventListener('resize', resize);
        resize();

        const stars = Array.from({ length: 140 }, () => ({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            size: Math.random() * 1.8,
            alpha: Math.random(),
            speed: Math.random() * 0.01 + 0.005
        }));

        let tick = 0;

        function drawRibbonAurora(yOffset, waveHeight, color1, color2, speedMult) {
            ctx.save();
            ctx.beginPath();
            
            const startY = yOffset + Math.sin(tick * speedMult) * 20;
            ctx.moveTo(0, startY);

            for (let x = 0; x <= canvas.width; x += 30) {
                const y = yOffset + 
                          Math.sin(x * 0.002 + tick * speedMult) * waveHeight + 
                          Math.cos(x * 0.001 + tick * 0.5) * (waveHeight * 0.5);
                ctx.lineTo(x, y);
            }

            ctx.lineTo(canvas.width, startY + 180);
            ctx.lineTo(0, startY + 180);
            ctx.closePath();

            const grad = ctx.createLinearGradient(0, yOffset - 50, canvas.width, yOffset + 200);
            grad.addColorStop(0, color1);
            grad.addColorStop(1, color2);

            ctx.fillStyle = grad;
            ctx.filter = 'blur(20px)';
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

            tick += 0.012;

            drawRibbonAurora(
                canvas.height * 0.08, 
                60, 
                'rgba(0, 255, 170, 0.35)', 
                'rgba(0, 150, 255, 0.05)', 
                0.8
            );

            drawRibbonAurora(
                canvas.height * 0.12, 
                80, 
                'rgba(0, 180, 255, 0.25)', 
                'rgba(140, 0, 255, 0.02)', 
                1.2
            );

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
    return render_template_string(
        HTML_TEMPLATE, 
        authenticated=is_auth, 
        manuals=MANUALS
    )

@app.route('/login', methods=['POST'])
def login():
    entered_code = request.form.get('auth_code')
    
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip and ',' in user_ip:
        user_ip = user_ip.split(',')[0].strip()
        
    location_info = get_location_from_ip(user_ip)
    now_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    ACCESS_LOGS.insert(0, {
        "ip": user_ip,
        "location": location_info,
        "time": now_time
    })

    if entered_code == VALID_AUTH_CODE:
        session['authenticated'] = True
        return redirect(url_for('index'))
    else:
        return render_template_string(
            HTML_TEMPLATE, 
            authenticated=False, 
            error="❌ 인증코드가 올바르지 않습니다.",
            manuals=MANUALS
        )

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('index'))

if __name__ == '__main__':
    # host='0.0.0.0'으로 변경하여 로컬 네트워크(동일 Wi-Fi) 접속 허용
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
