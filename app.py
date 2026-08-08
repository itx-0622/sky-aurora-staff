import base64
import datetime
import json
import math
import os
import random
import sys
from datetime import datetime as dt
from flask import Flask, jsonify, redirect, render_template_string, request, session
import pygame
import requests
from werkzeug.middleware.proxy_fix import ProxyFix

# ==========================================
# 1. Flask 웹 애플리케이션 및 설정
# ==========================================
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.secret_key = os.urandom(24)

CLIENT_ID = "1534184089144266872"
CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "ZfLY_vs2lo_LQVtd89ZB64jHe3dviRNm")
BASE_URL = "https://sky-aurora-staff.onrender.com"

ADMIN_SECRET_KEY = "sky_aurora_admin_secret_key_1234"
DATA_FILE = "sky_aurora_admin_data.json"
DEFAULT_ADMINS = ["1534184089144266872", "843621337066504225"]

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# --------------------------------------------------
# 데이터 불러오기 및 저장 로직
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
        "user_profiles": {},
        "quiz_config": {
            "difficulty": "medium",
            "count": 3
        },
        "manuals": [
            {
                "id": 1,
                "category": "보안 지침",
                "pinned": True,
                "title": "01. 기본 보안 규칙",
                "content": "<h2 style='color:#00ffaa;'>기본 보안 가이드라인</h2><p>본 매뉴얼 시스템에 포함된 모든 정보는 외부 유출이 엄격히 금지됩니다.</p><hr/><p><mark style='background-color:#fef08a; color:#000; padding:2px 6px; border-radius:4px;'>📌 필수 유의사항</mark></p><p>1. 화면 캡처 금지<br/>2. 계정 공유 금지<br/>3. 실시간 접속 기록 로깅 중</p><p>참고 영상: https://www.youtube.com/watch?v=dQw4w9WgXcQ</p>"
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
            
            now_kst = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime('%Y-%m-%d %H:%M:%S')
            payload = {
                "message": f"Auto-sync manual data [{now_kst} KST]",
                "content": encoded_content
            }
            if sha:
                payload["sha"] = sha
                
            requests.put(url, headers=headers, json=payload, timeout=5)
        except Exception as e:
            print(f"[GitHub Sync Save Error] {e}")

def add_log(data, category, user_name, action, device_type="PC"):
    now_kst = (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{now_kst} KST] [{category}] [{device_type}] {user_name}: {action}"
    if "logs" not in data:
        data["logs"] = []
    data["logs"].insert(0, log_entry)

# --------------------------------------------------
# HTML 템플릿
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
        
        :root {
            --bg-body: #030509;
            --container-bg: rgba(8, 12, 24, 0.85);
            --container-border: rgba(0, 255, 200, 0.25);
            --text-main: #ffffff;
            --text-sub: #cbd5e1;
            --header-bg: rgba(5, 8, 18, 0.95);
            --sidebar-bg: rgba(0, 0, 0, 0.4);
            --card-bg: rgba(5, 8, 17, 0.7);
            --input-bg: rgba(3, 5, 9, 0.8);
            --btn-item-bg: rgba(10, 16, 32, 0.95);
            --intro-bg: #030509;
            --intro-border: #00ffaa;
            --intro-text: #ffffff;
        }

        body.day-theme {
            --bg-body: #e0f2fe;
            --container-bg: rgba(255, 255, 255, 0.85);
            --container-border: rgba(56, 189, 248, 0.4);
            --text-main: #0f172a;
            --text-sub: #334155;
            --header-bg: rgba(241, 245, 249, 0.95);
            --sidebar-bg: rgba(255, 255, 255, 0.5);
            --card-bg: rgba(255, 255, 255, 0.75);
            --input-bg: rgba(255, 255, 255, 0.9);
            --btn-item-bg: rgba(241, 245, 249, 0.95);
            --intro-bg: #f0f9ff;
            --intro-border: #0284c7;
            --intro-text: #0f172a;
        }

        body {
            font-family: 'GmarketSansBold', 'Pretendard', sans-serif;
            background: var(--bg-body); color: var(--text-main); overflow: hidden; height: 100vh; width: 100vw;
            display: flex; justify-content: center; align-items: center; transition: background 0.5s ease, color 0.5s ease;
        }

        #security-overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: #000000;
            z-index: 99999999; display: none; flex-direction: column; justify-content: center; align-items: center; text-align: center; padding: 20px;
        }
        .alert-icon { font-size: 80px; color: #ff2d55; margin-bottom: 20px; animation: pulse 1.2s infinite ease-in-out; }
        .alert-main-text { font-size: 24px; font-weight: bold; color: #ff2d55; margin-bottom: 12px; }
        .alert-sub-text { font-size: 14px; color: #a0aec0; font-family: 'Pretendard', sans-serif; }
        @keyframes pulse { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.15); opacity: 0.7; } 100% { transform: scale(1); opacity: 1; } }

        #custom-notification {
            position: fixed; top: 25px; right: 25px; z-index: 999999; display: flex; align-items: center; gap: 12px;
            padding: 14px 22px; background: rgba(8, 15, 30, 0.95); border: 1px solid #00ffaa;
            border-radius: 14px; box-shadow: 0 0 20px rgba(0, 255, 170, 0.4); color: #fff;
            transform: translateX(150%); transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            font-family: 'Pretendard', sans-serif; font-size: 14px; font-weight: 600;
        }
        #custom-notification.show { transform: translateX(0); }

        #intro-overlay {
            position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
            background: var(--intro-bg); z-index: 99999; display: flex; flex-direction: column;
            justify-content: center; align-items: center; opacity: 1; transition: opacity 0.8s ease, background 0.5s ease;
        }
        
        .intro-circle-container {
            position: relative; width: 120px; height: 120px; display: flex;
            justify-content: center; align-items: center; margin-bottom: 24px;
        }
        .intro-aura-glow {
            position: absolute; width: 100%; height: 100%; border-radius: 50%;
            background: radial-gradient(circle, rgba(0,255,170,0.6) 0%, rgba(0,242,254,0.2) 60%, transparent 100%);
            animation: auraPulse 2s ease-in-out infinite alternate; filter: blur(10px);
        }
        @keyframes auraPulse { 0% { transform: scale(0.85); opacity: 0.4; } 100% { transform: scale(1.35); opacity: 0.9; } }

        .intro-avatar {
            width: 100px; height: 100px; border-radius: 50%; object-fit: cover;
            opacity: 0; transform: scale(0.6); transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
            border: 2px solid var(--intro-border); box-shadow: 0 0 25px rgba(0,255,170,0.6); z-index: 2;
        }
        .intro-avatar.show { opacity: 1; transform: scale(1); }
        .intro-progress-text { font-size: 28px; color: var(--intro-border); font-family: 'GmarketSansBold'; letter-spacing: 1px; }
        .intro-welcome-text { font-size: 18px; color: var(--intro-text); font-family: 'Pretendard'; font-weight: 600; margin-top: 16px; opacity: 0; transition: opacity 0.5s ease; text-align: center; padding: 0 20px; }
        .intro-welcome-text.show { opacity: 1; }

        #bg-canvas { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; z-index: 1; }

        .container {
            position: relative; z-index: 2; width: 94%; max-width: 1280px; height: 90vh;
            background: var(--container-bg); backdrop-filter: blur(25px); border: 1px solid var(--container-border);
            border-radius: 24px; box-shadow: 0 0 60px rgba(0, 255, 170, 0.12);
            display: flex; flex-direction: column; overflow: hidden; animation: containerAppear 0.8s ease;
            transition: background 0.5s ease, border-color 0.5s ease;
        }
        @keyframes containerAppear { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }

        header { padding: 16px 24px; background: var(--header-bg); border-bottom: 1px solid rgba(125, 125, 125, 0.2); display: flex; justify-content: space-between; align-items: center; transition: background 0.5s ease; }
        header h1 { font-size: 18px; font-weight: bold; background: linear-gradient(90deg, #00f2fe, #00ffaa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        
        .header-controls { display: flex; align-items: center; gap: 12px; }
        .theme-toggle-btn {
            background: rgba(255, 255, 255, 0.15); border: 1px solid rgba(255, 255, 255, 0.3);
            color: var(--text-main); font-family: 'Pretendard'; font-size: 12px; font-weight: bold;
            padding: 6px 14px; border-radius: 20px; cursor: pointer; transition: all 0.3s;
            display: flex; align-items: center; gap: 6px; backdrop-filter: blur(5px);
        }
        body.day-theme .theme-toggle-btn { background: rgba(0, 0, 0, 0.08); border-color: rgba(0, 0, 0, 0.2); }
        .theme-toggle-btn:hover { transform: scale(1.05); }

        .badge-admin { background: rgba(255, 45, 85, 0.2); border: 1px solid #ff2d55; color: #ff2d55; font-size: 11px; padding: 3px 8px; border-radius: 6px; font-family: 'Pretendard'; }
        .badge-staff { background: rgba(0, 255, 170, 0.2); border: 1px solid #00ffaa; color: #00ffaa; font-size: 11px; padding: 3px 8px; border-radius: 6px; font-family: 'Pretendard'; }
        .avatar-img { width: 34px; height: 34px; border-radius: 50%; border: 2px solid #00ffaa; }
        .logout-btn { font-family: 'Pretendard', sans-serif; color: var(--text-sub); text-decoration: none; font-size: 12px; padding: 5px 12px; border: 1px solid rgba(125,125,125,0.3); border-radius: 8px; }
        .logout-btn:hover { color: var(--text-main); border-color: #00ffaa; background: rgba(0, 255, 170, 0.1); }

        .login-box { padding: 50px 24px; text-align: center; margin: auto; max-width: 400px; width: 90%; background: var(--card-bg); border: 1px solid var(--container-border); border-radius: 20px; box-shadow: 0 15px 35px rgba(0,0,0,0.3); }
        .discord-btn { display: flex; align-items: center; justify-content: center; gap: 10px; width: 100%; padding: 14px; background: #5865F2; color: white; text-decoration: none; border-radius: 12px; font-family: 'Pretendard', sans-serif; font-weight: bold; font-size: 15px; border: none; cursor: pointer; transition: all 0.2s; }
        .discord-btn:hover { background: #4752C4; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(88, 101, 242, 0.5); }

        .dashboard { display: flex; flex: 1; overflow: hidden; }
        
        .sidebar { width: 300px; background: var(--sidebar-bg); border-right: 1px solid rgba(125, 125, 125, 0.2); padding: 20px 14px; overflow-y: auto; transition: background 0.5s ease; }
        .sidebar-category-title { font-size: 12px; color: #00ffaa; letter-spacing: 1px; margin: 16px 0 8px 8px; text-transform: uppercase; font-family: 'Pretendard'; font-weight: bold; }
        body.day-theme .sidebar-category-title { color: #0284c7; }
        
        .aurora-btn-wrapper { position: relative; margin-bottom: 8px; border-radius: 12px; overflow: hidden; padding: 2px; background: rgba(125, 125, 125, 0.05); transition: all 0.25s ease; }
        .aurora-btn-wrapper.active { background: linear-gradient(90deg, #00ffaa, #00f2fe); box-shadow: 0 0 15px rgba(0, 255, 170, 0.4); }
        .item-btn { position: relative; z-index: 1; width: 100%; text-align: left; padding: 12px 14px; background: var(--btn-item-bg); border: none; color: var(--text-sub); border-radius: 10px; cursor: pointer; font-size: 13px; font-family: 'Pretendard', sans-serif; font-weight: 600; display: flex; justify-content: space-between; align-items: center; }
        .aurora-btn-wrapper.active .item-btn { color: var(--text-main); font-weight: bold; }
        .pin-badge { font-size: 11px; margin-right: 4px; }

        .main-content { flex: 1; padding: 28px; overflow-y: auto; position: relative; scroll-behavior: smooth; }
        .content-card { background: var(--card-bg); backdrop-filter: blur(16px); border: 1px solid rgba(125, 125, 125, 0.15); border-radius: 18px; padding: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); position: relative; margin-bottom: 20px; transition: background 0.5s ease; }
        
        .doc-title { font-size: 20px; margin-bottom: 16px; color: var(--text-main); border-bottom: 1px solid rgba(125, 125, 125, 0.2); padding-bottom: 12px; display: flex; align-items: center; justify-content: space-between; }
        .doc-title-text { display: flex; align-items: center; gap: 10px; }
        .doc-title-text::before { content: ''; display: inline-block; width: 4px; height: 20px; background: #00ffaa; border-radius: 2px; }
        .doc-body { font-family: 'Pretendard', sans-serif; font-weight: 500; font-size: 15px; line-height: 1.85; color: var(--text-sub); background: rgba(0, 0, 0, 0.15); padding: 20px; border-radius: 14px; border: 1px solid rgba(125, 125, 125, 0.1); }

        .video-embed-box { margin: 15px 0; position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 12px; border: 1px solid rgba(0, 255, 170, 0.3); box-shadow: 0 8px 20px rgba(0,0,0,0.4); }
        .video-embed-box iframe { position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0; }

        input, textarea, select { width: 100%; background: var(--input-bg); color: var(--text-main); border: 1px solid rgba(125, 125, 125, 0.3); padding: 12px 14px; border-radius: 10px; margin-bottom: 12px; outline: none; font-family: 'Pretendard', sans-serif; }
        input:focus, textarea:focus, select:focus { border-color: #38bdf8; box-shadow: 0 0 12px rgba(56, 189, 248, 0.3); }

        .btn-ui {
            position: relative; background: linear-gradient(135deg, #2563eb, #1d4ed8); color: white; border: none;
            padding: 10px 18px; border-radius: 10px; font-weight: 700; cursor: pointer; font-family: 'Pretendard', sans-serif;
            transition: all 0.25s ease; outline: none; overflow: hidden;
        }
        .btn-ui::after {
            content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
            background: radial-gradient(circle, rgba(0, 255, 170, 0.3) 0%, transparent 70%);
            opacity: 0; transition: opacity 0.3s ease; pointer-events: none;
        }
        .btn-ui:hover { transform: translateY(-2px); box-shadow: 0 0 15px rgba(0, 255, 170, 0.5), 0 0 30px rgba(0, 242, 254, 0.3); }
        .btn-ui:hover::after { opacity: 1; }
        .btn-danger { background: linear-gradient(135deg, #ef4444, #b91c1c); }
        .btn-danger:hover { box-shadow: 0 0 15px rgba(255, 45, 85, 0.6); }
        .btn-secondary { background: linear-gradient(135deg, #475569, #334155); }

        .editor-toolbar { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; background: rgba(0,0,0,0.2); padding: 8px; border-radius: 10px; }
        .editor-toolbar button { padding: 6px 10px; font-size: 12px; background: var(--btn-item-bg); color: var(--text-main); border: 1px solid rgba(125,125,125,0.3); border-radius: 6px; cursor: pointer; font-family: 'Pretendard'; }
        .editor-toolbar button:hover { border-color: #00ffaa; color: #00ffaa; }

        .speech-bubble-pop {
            position: absolute; background: #00ffaa; color: #030509; padding: 10px 16px; border-radius: 12px;
            font-size: 13px; font-weight: bold; font-family: 'Pretendard'; z-index: 1000; box-shadow: 0 10px 25px rgba(0,0,0,0.4);
            animation: popIn 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        .speech-bubble-pop::after {
            content: ''; position: absolute; bottom: -8px; left: 20px; border-width: 8px 8px 0; border-style: solid; border-color: #00ffaa transparent; display: block; width: 0;
        }
        @keyframes popIn { from { transform: scale(0.5); opacity: 0; } to { transform: scale(1); opacity: 1; } }

        .key-display { display: flex; gap: 10px; align-items: center; justify-content: center; padding: 20px; background: rgba(0,0,0,0.3); border-radius: 12px; margin-top: 10px; }
        .key-cap { background: #334155; color: #fff; padding: 10px 16px; border-radius: 8px; border-bottom: 4px solid #1e293b; font-family: monospace; font-size: 18px; font-weight: bold; }
        .key-cap.active { background: #00ffaa; color: #000; border-bottom-color: #00cc88; transform: translateY(2px); }

        ul.data-list { list-style: none; padding: 0; }
        ul.data-list li { background: var(--btn-item-bg); padding: 14px; margin-bottom: 10px; border-radius: 12px; border: 1px solid rgba(125, 125, 125, 0.2); display: flex; justify-content: space-between; align-items: center; font-family: 'Pretendard', sans-serif; font-size: 14px; }

        .user-card-info { display: flex; align-items: center; gap: 12px; }
        .user-card-avatar { width: 40px; height: 40px; border-radius: 50%; border: 1px solid #00ffaa; object-fit: cover; }
        .user-card-names { display: flex; flex-direction: column; }
        .user-card-nick { font-weight: bold; color: var(--text-main); font-size: 14px; }
        .user-card-sub { font-size: 12px; color: #00ffaa; display: flex; align-items: center; gap: 6px; }
        body.day-theme .user-card-sub { color: #0284c7; }
        .eye-btn { cursor: pointer; background: transparent; border: none; color: var(--text-sub); font-size: 13px; margin-left: 4px; }
        .eye-btn:hover { color: #00ffaa; }

        .mention-dropdown {
            position: absolute; top: 45px; left: 0; right: 0; z-index: 1000;
            background: var(--card-bg); border: 1px solid #00ffaa; border-radius: 12px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5); display: none; max-height: 180px; overflow-y: auto;
        }
        .mention-item { display: flex; align-items: center; gap: 12px; padding: 10px 14px; cursor: pointer; transition: background 0.2s; }
        .mention-item:hover { background: rgba(0, 255, 170, 0.15); }

        .tab-enter { animation: manualEnter 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
        .tab-leave { animation: manualLeave 0.25s cubic-bezier(0.7, 0, 0.84, 0) forwards; }
        @keyframes manualEnter { 0% { opacity: 0; transform: translateY(20px) scale(0.98); } 100% { opacity: 1; transform: translateY(0) scale(1); } }
        @keyframes manualLeave { 0% { opacity: 1; transform: translateY(0) scale(1); } 100% { opacity: 0; transform: translateY(-15px) scale(0.98); } }

        @media (max-width: 768px) {
            .container { width: 100%; height: 100vh; border-radius: 0; border: none; }
            .dashboard { flex-direction: column; }
            .sidebar { width: 100%; height: 210px; border-right: none; border-bottom: 1px solid rgba(125,125,125,0.2); padding: 12px; }
            .main-content { padding: 16px; }
            header { padding: 12px 16px; }
            header h1 { font-size: 15px; }
            .doc-title { font-size: 17px; }
            .doc-body { font-size: 14px; padding: 14px; }
        }
    </style>
    <script>
        function getDeviceType() {
            const ua = navigator.userAgent;
            if (/(tablet|ipad|playbook|silk)|(android(?!.*mobi))/i.test(ua)) return "Mobile (Tablet)";
            if (/Mobile|iP(hone|od)|Android|BlackBerry|IEMobile|Kindle|Silk-Accelerated|(hpw|web)OS|Opera M(obi|ini)/i.test(ua)) return "Mobile";
            return "PC";
        }

        function notifyLog(actionName) {
            fetch('/api/log/action', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ action: actionName, device: getDeviceType() })
            }).catch(e => {});
        }

        document.addEventListener('contextmenu', e => e.preventDefault());
        document.addEventListener('selectstart', e => e.preventDefault());
        document.addEventListener('dragstart', e => e.preventDefault());

        function triggerSecurityLock() { const overlay = document.getElementById('security-overlay'); if (overlay) overlay.style.display = 'flex'; }
        function releaseSecurityLock() { const overlay = document.getElementById('security-overlay'); if (overlay) overlay.style.display = 'none'; }

        document.addEventListener('keydown', function(e) {
            if (e.key === 'PrintScreen' || e.key === 'F12') { triggerSecurityLock(); notifyLog("화면 캡처 감지 (PrintScreen)"); }
            if (e.shiftKey && (e.key === 'S' || e.key === 's') && (e.metaKey || e.key === 'Meta')) { triggerSecurityLock(); notifyLog("캡처 도구 감지 (Win+Shift+S)"); }
            const k = e.key.toLowerCase();
            if (e.ctrlKey || e.metaKey) {
                if (k === 'c') notifyLog("복사 감지 (Ctrl+C)");
                if (k === 'v') notifyLog("붙여넣기 감지 (Ctrl+V)");
                if (['c', 'v', 'u', 's', 'p', 'a', 'i', 'j'].includes(k)) { triggerSecurityLock(); }
            }
            
            const keyCap = document.getElementById('active-key-cap');
            if(keyCap) {
                keyCap.innerText = e.key.toUpperCase();
                keyCap.classList.add('active');
                setTimeout(() => keyCap.classList.remove('active'), 300);
            }
        }, true);

        document.addEventListener('keyup', function(e) { if (!e.shiftKey && !e.metaKey && !e.ctrlKey && !e.altKey) { releaseSecurityLock(); } });
        window.addEventListener('blur', triggerSecurityLock); window.addEventListener('focus', releaseSecurityLock);
        document.addEventListener('visibilitychange', function() { if (document.hidden) triggerSecurityLock(); else releaseSecurityLock(); });

        function showNotification(msg) {
            const toast = document.getElementById('custom-notification');
            const text = document.getElementById('custom-notification-text');
            if (toast && text) {
                text.innerText = msg;
                toast.classList.add('show');
                setTimeout(() => toast.classList.remove('show'), 3000);
            }
        }

        function login() {
            const redirectUri = encodeURIComponent("https://sky-aurora-staff.onrender.com/callback");
            location.href = `https://discord.com/oauth2/authorize?client_id={{ client_id }}&response_type=code&redirect_uri=${redirectUri}&scope=identify`;
        }
    </script>
</head>
<body>
    <div id="security-overlay">
        <div class="alert-icon">⚠️</div>
        <div class="alert-main-text">보안 경고: 무단 캡처 금지</div>
        <div class="alert-sub-text">시스템 정보의 무단 촬영 및 복제 시도는 금지되어 있습니다.</div>
    </div>

    <div id="custom-notification">
        <span style="font-size:18px;">🌌</span>
        <span id="custom-notification-text">알림 메세지</span>
    </div>

    <div id="intro-overlay" style="display:none;">
        <div id="intro-container" class="intro-circle-container">
            <div class="intro-aura-glow"></div>
            <img id="intro-avatar-img" class="intro-avatar" src="" alt="User Avatar">
        </div>
        <div id="intro-progress" class="intro-progress-text">0%</div>
        <div id="intro-welcome" class="intro-welcome-text"></div>
    </div>

    <canvas id="bg-canvas"></canvas>

    <div class="container">
        <header>
            <h1>SKY AURORA STAFF SYSTEM</h1>
            <div class="header-controls">
                <button id="themeToggleBtn" class="theme-toggle-btn" onclick="toggleThemeMode()">
                    <span id="themeBtnIcon">☀️</span> <span id="themeBtnText">데이 모드</span>
                </button>
                <div id="user-header-info" style="display:none; align-items:center; gap:12px;">
                    <span id="user-role-badge" class="badge-staff">STAFF</span>
                    <img id="user-avatar" src="" alt="Avatar" class="avatar-img" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                    <span id="user-name" style="font-size: 13px; color: #00ffaa; font-family: 'Pretendard'; font-weight:600;"></span>
                    <a href="/logout" class="logout-btn">로그아웃</a>
                </div>
            </div>
        </header>

        <div id="login-box" class="login-box">
            <h2 style="font-size: 18px; margin-bottom: 24px; font-family: 'GmarketSansBold';">🔒 스태프 시스템 인증</h2>
            <button onclick="login()" class="discord-btn">
                디스코드 계정으로 통합 로그인
            </button>
        </div>

        <div id="main-dashboard" class="dashboard" style="display:none;">
            <div class="sidebar">
                <div id="manual-sidebar-categorized"></div>

                <div class="aurora-btn-wrapper" style="margin-top:15px;">
                    <button class="item-btn" onclick="transitionToTab('view-quiz')">🧩 AI 매뉴얼 퀴즈</button>
                </div>

                <div id="admin-menu-section" style="display:none; margin-top:20px; border-top:1px solid rgba(125,125,125,0.2); padding-top:10px;">
                    <div class="sidebar-category-title" style="color:#38bdf8;">Admin Controls</div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-m-manage">
                        <button class="item-btn" onclick="switchAdminTab('m-manage')">📖 매뉴얼 등록/관리</button>
                    </div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-permissions">
                        <button class="item-btn" onclick="switchAdminTab('permissions')">🛡️ 권한 제어 센터</button>
                    </div>
                    <div class="aurora-btn-wrapper admin-nav" id="nav-logs">
                        <button class="item-btn" onclick="switchAdminTab('logs')">📜 실시간 접속 로그</button>
                    </div>
                </div>
            </div>

            <div class="main-content" id="main-content-area">
                <div id="view-manual" class="tab-enter" style="display:block;">
                    <div class="doc-title">
                        <div id="doc-title" class="doc-title-text">매뉴얼 선택 중...</div>
                        <label style="font-size:12px; font-family:'Pretendard'; color:var(--text-sub); display:flex; align-items:center; gap:6px; cursor:pointer;">
                            <input type="checkbox" id="embed-preview-toggle" onchange="toggleEmbedPreview(this.checked)" checked style="width:auto; margin:0;">
                            🎥 링크 미리보기 켜기
                        </label>
                    </div>
                    <div id="doc-body" class="doc-body"></div>
                </div>

                <!-- AI 퀴즈 탭 -->
                <div id="view-quiz" class="tab-enter" style="display:none;">
                    <div class="doc-title"><div class="doc-title-text">AI 매뉴얼 이해도 테스트</div></div>
                    <div class="content-card">
                        <div id="quiz-admin-config" style="display:none; margin-bottom:20px; background:rgba(56,189,248,0.1); padding:14px; border-radius:12px; border:1px solid #38bdf8;">
                            <h4 style="color:#38bdf8; margin-bottom:8px;">⚙️ [어드민] 퀴즈 설정</h4>
                            <div style="display:flex; gap:10px;">
                                <select id="quiz-difficulty" style="margin:0;">
                                    <option value="easy">난이도: 쉬움</option>
                                    <option value="medium" selected>난이도: 보통</option>
                                    <option value="hard">난이도: 어려움</option>
                                </select>
                                <input type="number" id="quiz-count" value="3" min="1" max="10" placeholder="문제 수" style="margin:0; width:100px;">
                                <button onclick="saveQuizConfig()" class="btn-ui" style="flex-shrink:0;">설정 저장</button>
                            </div>
                        </div>

                        <button onclick="generateQuiz()" class="btn-ui" style="width:100%; margin-bottom:20px;">🤖 현재 매뉴얼 기반 AI 문제 생성하기</button>
                        <div id="quiz-container"></div>
                    </div>
                </div>

                <div id="view-admin-m-manage" class="tab-enter" style="display:none;">
                    <div class="doc-title"><div class="doc-title-text">매뉴얼 신규 등록 및 작성</div></div>
                    <div class="content-card" id="manual-edit-card">
                        <div style="margin-bottom:12px;">
                            <label style="font-size:12px; color:#00ffaa; font-family:'Pretendard'; font-weight:bold; display:block; margin-bottom:4px;">수정할 매뉴얼 선택</label>
                            <select id="m-select-edit" onchange="onManualSelectToEdit(this.value)">
                                <option value="-1">-- 새 매뉴얼 작성 --</option>
                            </select>
                        </div>

                        <!-- 서식 확장 도구 모음 -->
                        <div class="editor-toolbar">
                            <button onclick="insertTag('<img>', '이미지 URL', 'https://via.placeholder.com/400x200')">📷 이미지 추가</button>
                            <button onclick="insertYoutubeEmbed()">▶️ 유튜브 링크 삽입</button>
                            <button onclick="insertTag('<mark>', '형광펜 텍스트', '강조할 내용', '</mark>')">🖍️ 형광펜</button>
                            <button onclick="insertTag('<span style=\\'color:#ff2d55;\\'>', '색상 텍스트', '빨간색 글자', '</span>')">🎨 글자 색상</button>
                            <button onclick="insertTag('<span style=\\'font-size:20px; font-weight:bold;\\'>', '큰 글자', '큰 글씨', '</span>')">🔍 글자 크기</button>
                            <button onclick="insertTag('<hr/>')">➖ 구분선</button>
                            <button onclick="insertTag('<fieldset style=\\'border:1px solid #00ffaa; padding:10px; border-radius:8px;\\'><legend style=\\'color:#00ffaa;\\'>도형 타이틀</legend>', '박스 내 내용', '도형 상자 안의 설명', '</fieldset>')">🔲 도형 박스</button>
                            <button onclick="insertInteractiveBubble()">💬 상호작용 말풍선</button>
                        </div>

                        <div style="display:flex; gap:10px; margin-bottom:4px;">
                            <input type="text" id="m-edit-category" placeholder="주제(카테고리) 예: 운항 지침, 공통 매뉴얼" style="flex:2;">
                            <label style="display:flex; align-items:center; gap:6px; font-family:'Pretendard'; font-size:13px; color:#00ffaa; cursor:pointer; padding-bottom:12px;">
                                <input type="checkbox" id="m-edit-pinned" style="width:auto; margin:0;"> 📌 상단 고정
                            </label>
                        </div>
                        <input type="text" id="m-edit-title" placeholder="매뉴얼 제목을 입력하세요">
                        <textarea id="m-edit-content" style="height:220px;" placeholder="매뉴얼 상세 내용을 입력하세요 (HTML 서식 및 유튜브 URL 지원)"></textarea>
                        
                        <div style="display:flex; gap:10px;">
                            <button onclick="saveManualData()" class="btn-ui" style="flex:1;">💾 매뉴얼 저장/수정</button>
                            <button onclick="saveDraftManual()" class="btn-ui btn-secondary" style="width:120px;">📝 임시저장</button>
                            <button onclick="deleteManualData()" class="btn-ui btn-danger" style="width:90px;">🗑️ 삭제</button>
                            <button onclick="resetManualForm()" class="btn-ui btn-secondary" style="width:90px;">새로작성</button>
                        </div>
                    </div>
                </div>

                <div id="view-admin-permissions" class="tab-enter" style="display:none;">
                    <div class="doc-title"><div class="doc-title-text">스태프 접근 권한 관리</div></div>
                    
                    <div class="content-card" style="margin-bottom:20px;">
                        <div style="position:relative;">
                            <div style="display:flex; gap:10px; margin-bottom:8px;">
                                <input type="text" id="perm-target-id" placeholder="대상 디스코드 ID 또는 @사용자이름 입력" style="margin-bottom:0;" oninput="onUserIdInput(this.value)">
                                <button onclick="searchAndDisplayUser()" class="btn-ui btn-secondary" style="width:100px; flex-shrink:0;">👤 조회</button>
                            </div>
                            <div id="mention-dropdown" class="mention-dropdown"></div>

                            <div id="searched-user-card" style="display:none; background:rgba(0, 255, 170, 0.05); border:1px solid #00ffaa; padding:12px; border-radius:12px; margin-bottom:12px;">
                                <div class="user-card-info">
                                    <img id="sc-avatar" src="" class="user-card-avatar" alt="Avatar">
                                    <div class="user-card-names">
                                        <div id="sc-nick" class="user-card-nick">사용자 이름</div>
                                        <div class="user-card-sub">
                                            ID: <span id="sc-id-masked">**************</span>
                                            <button class="eye-btn" onclick="toggleIdVisibility('sc-id-masked', 'sc-id-full')">👁️</button>
                                            <span id="sc-id-full" style="display:none;"></span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div style="display:flex; align-items:center; justify-content:space-between; margin-top:8px;">
                                <label style="display:flex; align-items:center; gap:6px; font-family:'Pretendard'; font-size:13px; color:#38bdf8; cursor:pointer;">
                                    <input type="checkbox" id="perm-is-admin" style="width:auto; margin:0;"> 👑 어드민 권한 부여
                                </label>
                                <div style="display:flex; gap:10px;">
                                    <button onclick="updatePermission('whitelist', 'add')" class="btn-ui">화이트리스트 추가</button>
                                    <button onclick="updatePermission('blacklist', 'add')" class="btn-ui btn-danger">블랙리스트 차단</button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="content-card" style="margin-bottom:20px;">
                        <h3 style="font-size:14px; color:#00ffaa; margin-bottom:10px;">⚡ 선택 유저 일괄 제어</h3>
                        <div style="display:flex; gap:10px; flex-wrap:wrap;">
                            <button onclick="batchAction('admin_upgrade')" class="btn-ui">👑 선택 어드민 승격</button>
                            <button onclick="batchAction('admin_demote')" class="btn-ui btn-secondary">👑 어드민 권한 취소</button>
                            <button onclick="batchAction('blacklist')" class="btn-ui btn-danger">🚫 선택 블랙리스트 차단</button>
                            <button onclick="batchAction('remove')" class="btn-ui btn-secondary">🗑️ 목록에서 일괄 제거</button>
                        </div>
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:16px;">
                        <div class="content-card">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                                <h3 style="color:#4ade80; font-size:15px;">화이트리스트 목록</h3>
                                <label style="font-size:12px; font-family:'Pretendard'; color:var(--text-sub); cursor:pointer;">
                                    <input type="checkbox" onclick="toggleSelectAll('wl-check', this.checked)" style="width:auto;"> 전체 선택
                                </label>
                            </div>
                            <ul id="perm-wl-list" class="data-list"></ul>
                        </div>
                        <div class="content-card">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                                <h3 style="color:#f87171; font-size:15px;">블랙리스트 목록</h3>
                                <label style="font-size:12px; font-family:'Pretendard'; color:var(--text-sub); cursor:pointer;">
                                    <input type="checkbox" onclick="toggleSelectAll('bl-check', this.checked)" style="width:auto;"> 전체 선택
                                </label>
                            </div>
                            <ul id="perm-bl-list" class="data-list"></ul>
                        </div>
                    </div>
                </div>

                <div id="view-admin-logs" class="tab-enter" style="display:none;">
                    <div class="doc-title"><div class="doc-title-text">실시간 활동 로그</div></div>
                    <div class="content-card">
                        <div id="admin-log-box" style="background:var(--input-bg); padding:16px; border-radius:12px; font-family:monospace; font-size:12px; height:450px; overflow-y:auto; border:1px solid rgba(125,125,125,0.2);"></div>
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

        let savedTheme = localStorage.getItem('sky_theme_mode');
        let currentMode;

        if (savedTheme) {
            currentMode = savedTheme;
        } else {
            const currentHour = new Date().getHours();
            currentMode = (currentHour >= 6 && currentHour < 18) ? 'day' : 'night';
        }

        let progress = currentMode === 'day' ? 1.0 : 0.0;
        let targetProgress = progress;
        let isSetting = currentMode === 'night';

        applyThemeUI(currentMode);

        function toggleThemeMode() {
            if (targetProgress === 0) {
                targetProgress = 1.0;
                currentMode = 'day';
                isSetting = false;
            } else {
                targetProgress = 0.0;
                currentMode = 'night';
                isSetting = true;
            }
            localStorage.setItem('sky_theme_mode', currentMode);
            applyThemeUI(currentMode);
        }

        function applyThemeUI(mode) {
            const btnIcon = document.getElementById('themeBtnIcon');
            const btnText = document.getElementById('themeBtnText');
            if (mode === 'day') {
                document.body.classList.add('day-theme');
                btnIcon.innerText = '🌙';
                btnText.innerText = '밤 모드';
            } else {
                document.body.classList.remove('day-theme');
                btnIcon.innerText = '☀️';
                btnText.innerText = '데이 모드';
            }
        }

        function hexToRgb(hex) {
            const bigint = parseInt(hex.replace('#', ''), 16);
            return [(bigint >> 16) & 255, (bigint >> 8) & 255, bigint & 255];
        }

        function interpolateColor(hex1, hex2, t) {
            const c1 = hexToRgb(hex1);
            const c2 = hexToRgb(hex2);
            const r = Math.round(c1[0] + (c2[0] - c1[0]) * t);
            const g = Math.round(c1[1] + (c2[1] - c1[1]) * t);
            const b = Math.round(c1[2] + (c2[2] - c1[2]) * t);
            return `rgb(${r}, ${g}, ${b})`;
        }

        const stars = Array.from({ length: 120 }, () => ({
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            size: Math.random() * 2,
            alpha: Math.random(),
            speed: Math.random() * 0.012 + 0.005
        }));

        let tick = 0;

        function drawSunRays(sunX, sunY, opacity, sunsetGlow) {
            if (opacity <= 0) return;
            ctx.save();
            ctx.translate(sunX, sunY);
            
            const rayLength = Math.max(canvas.width, canvas.height) * 1.5;
            const baseAngles = [Math.PI/3.5, Math.PI/2.5, Math.PI/1.8, Math.PI/1.2]; 
            const widths = [0.18, 0.08, 0.22, 0.12];

            for (let i = 0; i < baseAngles.length; i++) {
                const angle = baseAngles[i] + Math.sin(tick * 0.15 + i) * 0.08;
                const width = widths[i] + Math.cos(tick * 0.1 + i) * 0.04;

                ctx.beginPath();
                ctx.moveTo(0, 0);
                ctx.arc(0, 0, rayLength, angle - width, angle + width);
                ctx.closePath();
                
                const rayGrad = ctx.createRadialGradient(0, 0, 10, 0, 0, rayLength);
                
                const r = 255;
                const g = 250 - sunsetGlow * 80;
                const b = 224 - sunsetGlow * 150;
                
                rayGrad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${0.4 * opacity})`);
                rayGrad.addColorStop(1, `rgba(255, 255, 255, 0)`);
                
                ctx.globalCompositeOperation = 'screen';
                ctx.fillStyle = rayGrad;
                ctx.fill();
            }
            ctx.restore();
        }

        function drawRibbonAurora(yOffset, waveHeight, color1, color2, speedMult, opacity) {
            if (opacity <= 0) return;
            ctx.save();
            ctx.globalAlpha = opacity;
            ctx.beginPath();
            const startY = yOffset + Math.sin(tick * speedMult) * 20;
            ctx.moveTo(0, startY);
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
            progress += (targetProgress - progress) * 0.02;

            const sunsetOpacity = Math.max(0, 1 - Math.abs(progress - 0.5) * 2.2);

            const skyTop = interpolateColor('#030509', '#38bdf8', progress);
            const skyBottom = interpolateColor('#0a1020', '#bae6fd', progress);
            
            const bgGrad = ctx.createLinearGradient(0, 0, 0, canvas.height);
            bgGrad.addColorStop(0, skyTop);
            bgGrad.addColorStop(1, skyBottom);
            ctx.fillStyle = bgGrad;
            ctx.fillRect(0, 0, canvas.width, canvas.height);

            if (sunsetOpacity > 0.01) {
                const sunsetLayer = ctx.createLinearGradient(0, 0, 0, canvas.height);
                sunsetLayer.addColorStop(0, `rgba(255, 100, 50, ${sunsetOpacity * 0.4})`);
                sunsetLayer.addColorStop(0.5, `rgba(255, 130, 0, ${sunsetOpacity * 0.6})`);
                sunsetLayer.addColorStop(1, `rgba(255, 180, 80, ${sunsetOpacity * 0.8})`);
                
                ctx.save();
                ctx.globalCompositeOperation = 'color-dodge';
                ctx.fillStyle = sunsetLayer;
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                ctx.restore();
            }

            tick += 0.015;

            if (progress < 0.8) {
                const starAlphaMult = 1 - progress;
                stars.forEach(s => {
                    s.alpha += s.speed;
                    if (s.alpha > 1 || s.alpha < 0) s.speed = -s.speed;
                    ctx.fillStyle = `rgba(255, 255, 255, ${Math.abs(s.alpha) * starAlphaMult})`;
                    ctx.beginPath();
                    ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2);
                    ctx.fill();
                });
            }

            const auroraOpacity = 1 - progress;
            drawRibbonAurora(canvas.height * 0.05, 65, 'rgba(0, 255, 170, 0.35)', 'rgba(0, 150, 255, 0.03)', 0.8, auroraOpacity);
            drawRibbonAurora(canvas.height * 0.12, 85, 'rgba(0, 180, 255, 0.25)', 'rgba(140, 0, 255, 0.03)', 1.1, auroraOpacity);

            if (progress > 0.01) {
                let sunX;
                if (!isSetting) {
                    sunX = canvas.width * 0.1 + progress * (canvas.width * 0.4); 
                } else {
                    sunX = canvas.width * 0.9 - progress * (canvas.width * 0.4);
                }
                
                const sunY = canvas.height * 1.1 - Math.sin(progress * Math.PI / 2) * (canvas.height * 0.85);

                const r = 255;
                const g = 245 - sunsetOpacity * 100;
                const b = 180 - sunsetOpacity * 180;

                const glowGrad = ctx.createRadialGradient(sunX, sunY, 10, sunX, sunY, 350);
                glowGrad.addColorStop(0, `rgba(${r}, ${g}, ${Math.max(0, b)}, ${0.8 * progress})`);
                glowGrad.addColorStop(0.5, `rgba(${r}, ${g - 30}, ${Math.max(0, b - 50)}, ${0.4 * progress})`);
                glowGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');
                
                ctx.fillStyle = glowGrad;
                ctx.beginPath();
                ctx.arc(sunX, sunY, 350, 0, Math.PI * 2);
                ctx.fill();

                drawSunRays(sunX, sunY, progress, sunsetOpacity);

                ctx.beginPath();
                ctx.arc(sunX, sunY, 40, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(255, 253, ${235 - sunsetOpacity * 100}, ${Math.min(1, progress * 1.2)})`;
                ctx.shadowColor = `rgba(${r}, ${g}, ${Math.max(0, b)}, 0.8)`;
                ctx.shadowBlur = 40 + sunsetOpacity * 20;
                ctx.fill();
                ctx.shadowBlur = 0;
            }

            requestAnimationFrame(animate);
        }
        animate();

        let appState = { user: null, role: null, manuals: [], user_whitelist: [], user_blacklist: [], admin_whitelist: [], user_profiles: {}, logs: [], quiz_config: {difficulty:'medium', count:3} };
        let selectedManualIndex = 0;
        let currentActiveTabId = 'view-manual';
        let hasIntroRun = false;

        let embedPreviewEnabled = localStorage.getItem('sky_embed_preview') !== 'false';

        function toggleEmbedPreview(enabled) {
            embedPreviewEnabled = enabled;
            localStorage.setItem('sky_embed_preview', enabled);
            renderCategorizedSidebar();
        }

        function processYoutubeEmbeds(content, enablePreview) {
            if (!content) return '';
            
            const ytRegex = /(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})(?:[^\s<]*)?/g;

            if (enablePreview) {
                return content.replace(ytRegex, function(match, videoId) {
                    return `<div class="video-embed-box">
                        <iframe src="https://www.youtube.com/embed/${videoId}" allowfullscreen></iframe>
                    </div>`;
                });
            } else {
                return content.replace(ytRegex, function(match, videoId) {
                    const fullUrl = match.startsWith('http') ? match : `https://${match}`;
                    return `<a href="${fullUrl}" target="_blank" style="color:#00ffaa; text-decoration:underline;">🔗 유튜브 동영상 보기 (${fullUrl})</a>`;
                });
            }
        }

        async function syncSystemState() {
            try {
                const res = await fetch('/api/state');
                if (res.status === 403) { showNotification("권한이 없거나 차단된 계정입니다."); location.reload(); return; }
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

        function runCustomIntro(nickname, username, avatarUrl, onComplete) {
            const introOverlay = document.getElementById('intro-overlay');
            const introProgress = document.getElementById('intro-progress');
            const introAvatar = document.getElementById('intro-avatar-img');
            const introWelcome = document.getElementById('intro-welcome');

            introAvatar.src = avatarUrl;
            introOverlay.style.display = 'flex';

            const totalDuration = 2000;
            const startTime = performance.now();

            function updateLoading(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(Math.floor((elapsed / totalDuration) * 100), 100);
                introProgress.innerText = `${progress}%`;

                if (progress < 100) {
                    requestAnimationFrame(updateLoading);
                } else {
                    introProgress.style.display = 'none';
                    introAvatar.classList.add('show');
                    
                    introWelcome.innerText = `${nickname}(${username}) 님 환영합니다.`;
                    introWelcome.classList.add('show');

                    setTimeout(() => {
                        introOverlay.style.opacity = '0';
                        setTimeout(() => {
                            introOverlay.style.display = 'none';
                            onComplete();
                        }, 800);
                    }, 1200);
                }
            }
            requestAnimationFrame(updateLoading);
        }

        function showMainDashboard(data, avatarUrl) {
            document.getElementById('main-dashboard').style.display = 'flex';
            document.getElementById('user-header-info').style.display = 'flex';

            document.getElementById('user-avatar').src = avatarUrl;
            document.getElementById('user-name').innerText = `${data.user.global_name || data.user.username}`;

            const embedToggle = document.getElementById('embed-preview-toggle');
            if (embedToggle) embedToggle.checked = embedPreviewEnabled;

            const roleBadge = document.getElementById('user-role-badge');
            if (data.role === 'admin') {
                roleBadge.innerText = 'ADMIN';
                roleBadge.className = 'badge-admin';
                document.getElementById('admin-menu-section').style.display = 'block';
                document.getElementById('quiz-admin-config').style.display = 'block';
                
                if (data.quiz_config) {
                    document.getElementById('quiz-difficulty').value = data.quiz_config.difficulty || 'medium';
                    document.getElementById('quiz-count').value = data.quiz_config.count || 3;
                }
            } else {
                roleBadge.innerText = 'STAFF';
                roleBadge.className = 'badge-staff';
                document.getElementById('admin-menu-section').style.display = 'none';
                document.getElementById('quiz-admin-config').style.display = 'none';
            }

            renderCategorizedSidebar();
            renderAdminViews();
        }

        function renderCategorizedSidebar() {
            const container = document.getElementById('manual-sidebar-categorized');
            container.innerHTML = '';

            const editSelect = document.getElementById('m-select-edit');
            if (editSelect) editSelect.innerHTML = '<option value="-1">-- 새 매뉴얼 작성 --</option>';

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

                    if (editSelect) {
                        const opt = document.createElement('option');
                        opt.value = m.originalIdx;
                        opt.innerText = `[${catName}] ${m.title}`;
                        editSelect.appendChild(opt);
                    }
                });
            }

            if (appState.manuals.length > 0) {
                const current = appState.manuals[selectedManualIndex] || appState.manuals[0];
                document.getElementById('doc-title').innerText = `${current.pinned ? '📌 ' : ''}${current.title}`;
                
                const processedContent = processYoutubeEmbeds(current.content, embedPreviewEnabled);
                document.getElementById('doc-body').innerHTML = processedContent;
            }
        }

        function selectManualItem(idx) {
            selectedManualIndex = idx;
            renderCategorizedSidebar();
            transitionToTab('view-manual');
            
            if (appState.role === 'admin') {
                const current = appState.manuals[idx];
                if (current) {
                    document.getElementById('m-select-edit').value = idx;
                    document.getElementById('m-edit-category').value = current.category || '';
                    document.getElementById('m-edit-pinned').checked = !!current.pinned;
                    document.getElementById('m-edit-title').value = current.title || '';
                    document.getElementById('m-edit-content').value = current.content || '';
                }
            }
        }

        function insertTag(openTag, placeholder = "", defaultText = "", closeTag = "") {
            const textarea = document.getElementById('m-edit-content');
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            const selectedText = textarea.value.substring(start, end) || defaultText;
            
            let inserted = "";
            if (openTag === '<img>') {
                const url = prompt("이미지 URL을 입력하세요:", defaultText);
                if (url) inserted = `<img src="${url}" style="max-width:100%; border-radius:10px; margin:10px 0;"/>`;
            } else {
                inserted = `${openTag}${selectedText}${closeTag}`;
            }

            textarea.value = textarea.value.substring(0, start) + inserted + textarea.value.substring(end);
            textarea.focus();
        }

        function insertYoutubeEmbed() {
            const url = prompt("유튜브 동영상 링크(URL)를 입력하세요:", "https://www.youtube.com/watch?v=dQw4w9WgXcQ");
            if (url) {
                const textarea = document.getElementById('m-edit-content');
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                textarea.value = textarea.value.substring(0, start) + `\n${url.trim()}\n` + textarea.value.substring(end);
                textarea.focus();
            }
        }

        function insertInteractiveBubble() {
            const msg = prompt("말풍선에 표시할 메시지를 입력하세요:", "이 버튼을 클릭하여 실행되었습니다!");
            if(!msg) return;
            const btnText = prompt("버튼 텍스트를 입력하세요:", "상호작용 테스트");
            
            const htmlSnippet = `
<div style="margin:15px 0; position:relative; display:inline-block;">
    <button class="btn-ui" onclick="showBubblePop(this, '${msg}')">${btnText || '상호작용 테스트'}</button>
</div>
<div class="key-display">
    <span>실제 키보드를 눌러보세요:</span>
    <div id="active-key-cap" class="key-cap">KEY</div>
</div>
`;
            insertTag(htmlSnippet);
        }

        function showBubblePop(btnEl, text) {
            const existing = document.getElementById('active-speech-pop');
            if (existing) existing.remove();

            const pop = document.createElement('div');
            pop.id = 'active-speech-pop';
            pop.className = 'speech-bubble-pop';
            pop.innerText = text;

            const rect = btnEl.getBoundingClientRect();
            pop.style.top = (rect.top - 45) + 'px';
            pop.style.left = rect.left + 'px';

            document.body.appendChild(pop);
            setTimeout(() => { if (pop) pop.remove(); }, 3000);
        }

        function onManualSelectToEdit(val) {
            const idx = parseInt(val);
            if (idx === -1) {
                resetManualForm();
            } else {
                selectedManualIndex = idx;
                const current = appState.manuals[idx];
                if (current) {
                    document.getElementById('m-edit-category').value = current.category || '';
                    document.getElementById('m-edit-pinned').checked = !!current.pinned;
                    document.getElementById('m-edit-title').value = current.title || '';
                    document.getElementById('m-edit-content').value = current.content || '';
                }
            }
            const editCard = document.getElementById('manual-edit-card');
            if (editCard) editCard.scrollIntoView({ behavior: 'smooth' });
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
                }, 250);
            } else {
                targetTab.style.display = 'block';
                targetTab.classList.add('tab-enter');
                currentActiveTabId = targetTabId;
            }
        }

        function switchAdminTab(tabName) {
            document.querySelectorAll('.admin-nav').forEach(el => el.classList.remove('active'));
            const navEl = document.getElementById(`nav-${tabName}`);
            if (navEl) navEl.classList.add('active');
            
            transitionToTab(`view-admin-${tabName}`);
        }

        async function generateQuiz() {
            const container = document.getElementById('quiz-container');
            container.innerHTML = '<div style="text-align:center; padding:20px; color:#00ffaa;">🤖 AI가 매뉴얼을 분석하여 퀴즈를 생성하고 있습니다...</div>';

            const res = await fetch('/api/quiz/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ manual_index: selectedManualIndex })
            });

            if (res.ok) {
                const data = await res.json();
                renderQuiz(data.questions);
            } else {
                container.innerHTML = '<div style="color:#ff2d55; padding:10px;">퀴즈 생성에 실패했습니다. (OpenAI API 키 설정 확인 필요)</div>';
            }
        }

        function renderQuiz(questions) {
            const container = document.getElementById('quiz-container');
            if (!questions || questions.length === 0) {
                container.innerHTML = '<div>생성된 문제가 없습니다.</div>';
                return;
            }

            container.innerHTML = questions.map((q, qIdx) => `
                <div style="background:rgba(0,0,0,0.2); padding:16px; border-radius:12px; margin-bottom:16px; border:1px solid rgba(125,125,125,0.2);">
                    <div style="font-weight:bold; margin-bottom:10px; color:var(--text-main);">Q${qIdx+1}. ${q.question}</div>
                    <div>
                        ${q.options.map((opt, oIdx) => `
                            <label style="display:block; padding:8px 12px; background:var(--btn-item-bg); margin-bottom:6px; border-radius:8px; cursor:pointer;">
                                <input type="radio" name="q_${qIdx}" value="${oIdx}" style="width:auto; margin-right:8px;"> ${opt}
                            </label>
                        `).join('')}
                    </div>
                    <button class="btn-ui btn-secondary" style="margin-top:8px; padding:4px 10px; font-size:12px;" onclick="checkAnswer(${qIdx}, ${q.answer_index}, '${q.explanation}')">정답 확인</button>
                    <div id="quiz-result-${qIdx}" style="margin-top:8px; font-size:13px;"></div>
                </div>
            `).join('');
        }

        function checkAnswer(qIdx, correctIdx, explanation) {
            const selected = document.querySelector(`input[name="q_${qIdx}"]:checked`);
            const resDiv = document.getElementById(`quiz-result-${qIdx}`);
            if (!selected) return showNotification("답을 선택해주세요!");

            if (parseInt(selected.value) === correctIdx) {
                resDiv.innerHTML = `<span style="color:#4ade80; font-weight:bold;">⭕ 정답입니다!</span><br/><span style="color:var(--text-sub);">${explanation}</span>`;
            } else {
                resDiv.innerHTML = `<span style="color:#f87171; font-weight:bold;">❌ 오답입니다.</span><br/><span style="color:var(--text-sub);">${explanation}</span>`;
            }
        }

        async function saveQuizConfig() {
            const difficulty = document.getElementById('quiz-difficulty').value;
            const count = parseInt(document.getElementById('quiz-count').value);

            const res = await fetch('/api/admin/quiz_config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ difficulty, count })
            });

            if (res.ok) {
                showNotification("퀴즈 설정이 저장되었습니다.");
                syncSystemState();
            }
        }

        function maskId(idStr) {
            if (!idStr || idStr.length < 6) return idStr;
            return idStr.substring(0, 4) + '*'.repeat(idStr.length - 4);
        }

        function toggleIdVisibility(maskedElemId, fullElemId) {
            const masked = document.getElementById(maskedElemId);
            const full = document.getElementById(fullElemId);
            if (masked && full) {
                if (full.style.display === 'none') {
                    full.style.display = 'inline';
                    masked.style.display = 'none';
                } else {
                    full.style.display = 'none';
                    masked.style.display = 'inline';
                }
            }
        }

        function renderAdminViews() {
            if (appState.role !== 'admin') return;

            const adminSet = new Set(appState.admin_whitelist || []);
            const profiles = appState.user_profiles || {};

            const wlList = document.getElementById('perm-wl-list');
            wlList.innerHTML = appState.user_whitelist.map(id => {
                const prof = profiles[id] || { username: 'Discord User', global_name: '스태프', avatar_url: 'https://cdn.discordapp.com/embed/avatars/0.png' };
                return `
                <li>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <input type="checkbox" class="wl-check" value="${id}" style="width:auto; margin:0;">
                        <img src="${prof.avatar_url}" class="user-card-avatar" alt="Avatar" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                        <div class="user-card-names">
                            <div class="user-card-nick">${prof.global_name || prof.username} ${adminSet.has(id) ? '<span style="color:#38bdf8; font-size:11px;">[👑 어드민]</span>' : ''}</div>
                            <div class="user-card-sub">
                                <span id="wl-m-${id}">${maskId(id)}</span>
                                <span id="wl-f-${id}" style="display:none;">${id}</span>
                                <button class="eye-btn" onclick="toggleIdVisibility('wl-m-${id}', 'wl-f-${id}')">👁️</button>
                            </div>
                        </div>
                    </div>
                    <button class="btn-ui btn-danger" style="padding:4px 8px; font-size:11px;" onclick="updatePermission('whitelist', 'remove', '${id}')">제거</button>
                </li>
            `}).join('');

            const blList = document.getElementById('perm-bl-list');
            blList.innerHTML = appState.user_blacklist.map(id => {
                const prof = profiles[id] || { username: 'Discord User', global_name: '차단 유저', avatar_url: 'https://cdn.discordapp.com/embed/avatars/0.png' };
                return `
                <li>
                    <div style="display:flex; align-items:center; gap:10px;">
                        <input type="checkbox" class="bl-check" value="${id}" style="width:auto; margin:0;">
                        <img src="${prof.avatar_url}" class="user-card-avatar" alt="Avatar" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                        <div class="user-card-names">
                            <div class="user-card-nick">${prof.global_name || prof.username}</div>
                            <div class="user-card-sub">
                                <span id="bl-m-${id}">${maskId(id)}</span>
                                <span id="bl-f-${id}" style="display:none;">${id}</span>
                                <button class="eye-btn" onclick="toggleIdVisibility('bl-m-${id}', 'bl-f-${id}')">👁️</button>
                            </div>
                        </div>
                    </div>
                    <button class="btn-ui btn-secondary" style="padding:4px 8px; font-size:11px;" onclick="updatePermission('blacklist', 'remove', '${id}')">해제</button>
                </li>
            `}).join('');

            const logBox = document.getElementById('admin-log-box');
            logBox.innerHTML = appState.logs.map(log => `<div style="margin-bottom:6px; border-bottom:1px dashed rgba(125,125,125,0.2); padding-bottom:4px;">${log}</div>`).join('');
        }

        async function searchAndDisplayUser() {
            const targetId = document.getElementById('perm-target-id').value.trim();
            if (!targetId) return showNotification("조회할 디스코드 ID를 입력해주세요.");

            const res = await fetch(`/api/admin/user_info/${targetId}`);
            if (res.ok) {
                const data = await res.json();
                document.getElementById('sc-avatar').src = data.avatar_url;
                document.getElementById('sc-nick').innerText = `${data.global_name} (@${data.username})`;
                document.getElementById('sc-id-masked').innerText = maskId(data.id);
                document.getElementById('sc-id-full').innerText = data.id;
                document.getElementById('searched-user-card').style.display = 'block';
                showNotification("사용자 정보를 성공적으로 불러왔습니다.");
            } else {
                showNotification("해당 ID의 사용자를 찾을 수 없습니다.");
            }
        }

        function toggleSelectAll(className, isChecked) {
            document.querySelectorAll('.' + className).forEach(cb => cb.checked = isChecked);
        }

        async function batchAction(actionType) {
            const checkedWL = Array.from(document.querySelectorAll('.wl-check:checked')).map(cb => cb.value);
            const checkedBL = Array.from(document.querySelectorAll('.bl-check:checked')).map(cb => cb.value);
            const selectedIds = [...new Set([...checkedWL, ...checkedBL])];

            if (selectedIds.length === 0) return showNotification("선택된 사용자가 없습니다.");

            const res = await fetch('/api/admin/permission/batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user_ids: selectedIds, action: actionType })
            });

            if (res.ok) {
                showNotification(`선택한 ${selectedIds.length}명에 대해 처리 완료되었습니다.`);
                syncSystemState();
            }
        }

        function onUserIdInput(val) {
            const dropdown = document.getElementById('mention-dropdown');
            if (val.startsWith('@')) {
                const query = val.substring(1).toLowerCase();
                
                const allScanUsers = [];
                if (appState.user) {
                    allScanUsers.push({ id: appState.user.id, name: appState.user.global_name || appState.user.username });
                }
                (appState.user_whitelist || []).forEach(id => {
                    const prof = (appState.user_profiles || {})[id];
                    allScanUsers.push({ id, name: prof ? (prof.global_name || prof.username) : `스태프 (${id})` });
                });

                const filtered = allScanUsers.filter(u => u.name.toLowerCase().includes(query) || u.id.includes(query));

                if (filtered.length > 0) {
                    dropdown.innerHTML = filtered.map(u => `
                        <div class="mention-item" onclick="selectMentionUser('${u.id}')">
                            <span style="font-size:16px;">👤</span>
                            <div>
                                <div style="font-size:13px; font-weight:bold; color:var(--text-main);">${u.name}</div>
                                <div style="font-size:11px; color:var(--text-sub);">ID: ${maskId(u.id)}</div>
                            </div>
                        </div>
                    `).join('');
                    dropdown.style.display = 'block';
                } else {
                    dropdown.style.display = 'none';
                }
            } else {
                dropdown.style.display = 'none';
            }
        }

        function selectMentionUser(id) {
            document.getElementById('perm-target-id').value = id;
            document.getElementById('mention-dropdown').style.display = 'none';
            searchAndDisplayUser();
        }

        async function saveManualData() {
            const category = document.getElementById('m-edit-category').value.trim();
            const pinned = document.getElementById('m-edit-pinned').checked;
            const title = document.getElementById('m-edit-title').value.trim();
            const content = document.getElementById('m-edit-content').value.trim();

            if (!title || !content) return showNotification("제목과 내용을 입력해주세요.");

            const res = await fetch('/api/admin/manual', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: selectedManualIndex, category, pinned, title, content })
            });

            if (res.ok) {
                showNotification("매뉴얼이 저장되었습니다.");
                syncSystemState();
            }
        }

        function saveDraftManual() {
            const draft = {
                category: document.getElementById('m-edit-category').value,
                pinned: document.getElementById('m-edit-pinned').checked,
                title: document.getElementById('m-edit-title').value,
                content: document.getElementById('m-edit-content').value
            };
            localStorage.setItem('sky_manual_draft', JSON.stringify(draft));
            showNotification("매뉴얼 임시저장 완료");
        }

        async function deleteManualData() {
            if (!confirm("정말 이 매뉴얼을 삭제하시겠습니까?")) return;

            const res = await fetch('/api/admin/manual/delete', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ index: selectedManualIndex })
            });

            if (res.ok) {
                showNotification("매뉴얼이 삭제되었습니다.");
                selectedManualIndex = 0;
                resetManualForm();
                syncSystemState();
            }
        }

        function resetManualForm() {
            selectedManualIndex = appState.manuals.length;
            document.getElementById('m-select-edit').value = -1;
            document.getElementById('m-edit-category').value = '';
            document.getElementById('m-edit-pinned').checked = false;
            document.getElementById('m-edit-title').value = '';
            document.getElementById('m-edit-content').value = '';
        }

        async function updatePermission(target, action, explicitId = null) {
            const userId = explicitId || document.getElementById('perm-target-id').value.trim();
            const isAdmin = document.getElementById('perm-is-admin') ? document.getElementById('perm-is-admin').checked : false;

            if (!userId) return showNotification("대상 디스코드 ID를 입력해주세요.");

            const res = await fetch('/api/admin/permission', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target, action, user_id: userId, is_admin: isAdmin })
            });

            if (res.ok) {
                showNotification("권한 설정이 업데이트되었습니다.");
                if (!explicitId) document.getElementById('perm-target-id').value = '';
                syncSystemState();
            }
        }

        syncSystemState();
    </script>
</body>
</html>
"""

# --------------------------------------------------
# Flask 라우트 정의
# --------------------------------------------------
@app.route('/')
def index():
    return render_template_string(MAIN_HTML_TEMPLATE, client_id=CLIENT_ID)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect('/')

    token_url = "https://discord.com/api/oauth2/token"
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': f"{BASE_URL}/callback"
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    res = requests.post(token_url, data=data, headers=headers)
    
    if res.status_code == 200:
        token_data = res.json()
        access_token = token_data.get('access_token')

        user_res = requests.get("https://discord.com/api/users/@me", headers={'Authorization': f'Bearer {access_token}'})
        if user_res.status_code == 200:
            user_info = user_res.json()
            session['user'] = user_info
            
            db = load_data()
            user_id = user_info['id']
            avatar_hash = user_info.get('avatar')
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png" if avatar_hash else "https://cdn.discordapp.com/embed/avatars/0.png"
            
            db.setdefault("user_profiles", {})[user_id] = {
                "id": user_id,
                "username": user_info.get("username"),
                "global_name": user_info.get("global_name") or user_info.get("username"),
                "avatar_url": avatar_url
            }
            
            user_name = user_info.get('global_name') or user_info.get('username')
            add_log(db, "인증", user_name, f"디스코드 로그인 완료 (ID: {user_id})")
            save_data(db)

    return redirect('/')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')

@app.route('/api/state')
def get_state():
    user = session.get('user')
    if not user:
        return jsonify({"status": "unauthorized"})

    db = load_data()
    user_id = user['id']

    if user_id in db.get("user_blacklist", []):
        session.pop('user', None)
        return jsonify({"status": "forbidden", "message": "Blacklisted"}), 403

    role = "guest"
    if user_id in db.get("admin_whitelist", []):
        role = "admin"
    elif user_id in db.get("user_whitelist", []):
        role = "staff"

    return jsonify({
        "status": "success",
        "user": user,
        "role": role,
        "manuals": db.get("manuals", []),
        "user_whitelist": db.get("user_whitelist", []),
        "user_blacklist": db.get("user_blacklist", []),
        "admin_whitelist": db.get("admin_whitelist", []),
        "user_profiles": db.get("user_profiles", {}),
        "logs": db.get("logs", [])[:50],
        "quiz_config": db.get("quiz_config", {"difficulty": "medium", "count": 3})
    })

@app.route('/api/log/action', methods=['POST'])
def log_action():
    user = session.get('user')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    req_data = request.json or {}
    action = req_data.get('action', '알 수 없는 작업')
    device = req_data.get('device', 'PC')

    db = load_data()
    user_name = user.get('global_name') or user.get('username')
    add_log(db, "보안감시", user_name, action, device)
    save_data(db)

    return jsonify({"status": "success"})

@app.route('/api/admin/manual', methods=['POST'])
def save_manual():
    user = session.get('user')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    db = load_data()
    if user['id'] not in db.get("admin_whitelist", []):
        return jsonify({"status": "forbidden"}), 403

    req = request.json
    index = req.get('index', -1)
    category = req.get('category', '공통 매뉴얼')
    pinned = req.get('pinned', False)
    title = req.get('title')
    content = req.get('content')

    manuals = db.get("manuals", [])
    
    if 0 <= index < len(manuals):
        manuals[index] = {
            "id": manuals[index].get("id", len(manuals) + 1),
            "category": category,
            "pinned": pinned,
            "title": title,
            "content": content
        }
        action_msg = f"매뉴얼 수정 [{title}]"
    else:
        new_id = max([m.get("id", 0) for m in manuals], default=0) + 1
        manuals.append({
            "id": new_id,
            "category": category,
            "pinned": pinned,
            "title": title,
            "content": content
        })
        action_msg = f"새 매뉴얼 등록 [{title}]"

    db["manuals"] = manuals
    user_name = user.get('global_name') or user.get('username')
    add_log(db, "매뉴얼", user_name, action_msg)
    save_data(db)

    return jsonify({"status": "success"})

@app.route('/api/admin/manual/delete', methods=['POST'])
def delete_manual():
    user = session.get('user')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    db = load_data()
    if user['id'] not in db.get("admin_whitelist", []):
        return jsonify({"status": "forbidden"}), 403

    index = request.json.get('index', -1)
    manuals = db.get("manuals", [])

    if 0 <= index < len(manuals):
        deleted = manuals.pop(index)
        db["manuals"] = manuals
        user_name = user.get('global_name') or user.get('username')
        add_log(db, "매뉴얼", user_name, f"매뉴얼 삭제 [{deleted.get('title')}]")
        save_data(db)
        return jsonify({"status": "success"})

    return jsonify({"status": "invalid_index"}), 400

@app.route('/api/admin/permission', methods=['POST'])
def update_permission():
    user = session.get('user')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    db = load_data()
    if user['id'] not in db.get("admin_whitelist", []):
        return jsonify({"status": "forbidden"}), 403

    req = request.json
    target = req.get('target')
    action = req.get('action')
    target_user_id = str(req.get('user_id')).strip()
    is_admin = req.get('is_admin', False)

    wl = db.get("user_whitelist", [])
    bl = db.get("user_blacklist", [])
    al = db.get("admin_whitelist", [])

    if target == 'whitelist':
        if action == 'add':
            if target_user_id not in wl:
                wl.append(target_user_id)
            if target_user_id in bl:
                bl.remove(target_user_id)
            if is_admin and target_user_id not in al:
                al.append(target_user_id)
            elif not is_admin and target_user_id in al and target_user_id not in DEFAULT_ADMINS:
                al.remove(target_user_id)
        elif action == 'remove':
            if target_user_id in wl:
                wl.remove(target_user_id)
            if target_user_id in al and target_user_id not in DEFAULT_ADMINS:
                al.remove(target_user_id)

    elif target == 'blacklist':
        if action == 'add':
            if target_user_id not in bl:
                bl.append(target_user_id)
            if target_user_id in wl:
                wl.remove(target_user_id)
            if target_user_id in al and target_user_id not in DEFAULT_ADMINS:
                al.remove(target_user_id)
        elif action == 'remove':
            if target_user_id in bl:
                bl.remove(target_user_id)

    db["user_whitelist"] = wl
    db["user_blacklist"] = bl
    db["admin_whitelist"] = al

    user_name = user.get('global_name') or user.get('username')
    add_log(db, "권한변경", user_name, f"권한 업데이트 -> 대상 ID: {target_user_id} ({target}:{action})")
    save_data(db)

    return jsonify({"status": "success"})

@app.route('/api/admin/permission/batch', methods=['POST'])
def batch_permission():
    user = session.get('user')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    db = load_data()
    if user['id'] not in db.get("admin_whitelist", []):
        return jsonify({"status": "forbidden"}), 403

    req = request.json
    user_ids = req.get('user_ids', [])
    action = req.get('action')

    wl = db.get("user_whitelist", [])
    bl = db.get("user_blacklist", [])
    al = db.get("admin_whitelist", [])

    for uid in user_ids:
        uid = str(uid).strip()
        if action == 'admin_upgrade':
            if uid not in al:
                al.append(uid)
            if uid not in wl:
                wl.append(uid)
            if uid in bl:
                bl.remove(uid)
        elif action == 'admin_demote':
            if uid in al and uid not in DEFAULT_ADMINS:
                al.remove(uid)
        elif action == 'blacklist':
            if uid not in bl:
                bl.append(uid)
            if uid in wl:
                wl.remove(uid)
            if uid in al and uid not in DEFAULT_ADMINS:
                al.remove(uid)
        elif action == 'remove':
            if uid in wl:
                wl.remove(uid)
            if uid in bl:
                bl.remove(uid)
            if uid in al and uid not in DEFAULT_ADMINS:
                al.remove(uid)

    db["user_whitelist"] = wl
    db["user_blacklist"] = bl
    db["admin_whitelist"] = al

    user_name = user.get('global_name') or user.get('username')
    add_log(db, "권한변경", user_name, f"일괄 권한 변경 실행 ({action}) -> {len(user_ids)}명 대상")
    save_data(db)

    return jsonify({"status": "success"})

@app.route('/api/admin/user_info/<user_id>')
def get_user_info(user_id):
    user = session.get('user')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    db = load_data()
    if user['id'] not in db.get("admin_whitelist", []):
        return jsonify({"status": "forbidden"}), 403

    profiles = db.get("user_profiles", {})
    if user_id in profiles:
        return jsonify(profiles[user_id])

    bot_token = os.environ.get("DISCORD_BOT_TOKEN")
    if bot_token:
        headers = {"Authorization": f"Bot {bot_token}"}
        res = requests.get(f"https://discord.com/api/v10/users/{user_id}", headers=headers)
        if res.status_code == 200:
            u = res.json()
            avatar_hash = u.get("avatar")
            avatar_url = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png" if avatar_hash else "https://cdn.discordapp.com/embed/avatars/0.png"
            prof = {
                "id": user_id,
                "username": u.get("username"),
                "global_name": u.get("global_name") or u.get("username"),
                "avatar_url": avatar_url
            }
            profiles[user_id] = prof
            db["user_profiles"] = profiles
            save_data(db)
            return jsonify(prof)

    return jsonify({
        "id": user_id,
        "username": "Unknown User",
        "global_name": "미확인 유저",
        "avatar_url": "https://cdn.discordapp.com/embed/avatars/0.png"
    })

@app.route('/api/admin/quiz_config', methods=['POST'])
def set_quiz_config():
    user = session.get('user')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    db = load_data()
    if user['id'] not in db.get("admin_whitelist", []):
        return jsonify({"status": "forbidden"}), 403

    req = request.json
    db["quiz_config"] = {
        "difficulty": req.get("difficulty", "medium"),
        "count": int(req.get("count", 3))
    }
    save_data(db)
    return jsonify({"status": "success"})

@app.route('/api/quiz/generate', methods=['POST'])
def generate_quiz_api():
    user = session.get('user')
    if not user:
        return jsonify({"status": "unauthorized"}), 401

    db = load_data()
    req = request.json
    idx = req.get("manual_index", 0)
    manuals = db.get("manuals", [])

    if not (0 <= idx < len(manuals)):
        return jsonify({"status": "invalid_manual"}), 400

    target_manual = manuals[idx]
    config = db.get("quiz_config", {"difficulty": "medium", "count": 3})

    if not OPENAI_API_KEY:
        return jsonify({"status": "no_openai_key"}), 500

    prompt = f"""
다음 매뉴얼 내용을 기반으로 이해도 점검 퀴즈 {config['count']}문제를 생성해 주세요.
난이도: {config['difficulty']}

[매뉴얼 내용]
제목: {target_manual.get('title')}
내용: {target_manual.get('content')}

응답은 반드시 아래 형식의 JSON 배열 객체로만 출력하세요. 다른 텍스트는 포함하지 마세요.
[
  {{
    "question": "문제 내용",
    "options": ["보기1", "보기2", "보기3", "보기4"],
    "answer_index": 0,
    "explanation": "해설 내용"
  }}
]
"""
    try:
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        res = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            result_text = res.json()['choices'][0]['message']['content'].strip()
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            questions = json.loads(result_text)
            return jsonify({"status": "success", "questions": questions})
        else:
            return jsonify({"status": "openai_error", "details": res.text}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ==========================================
# 2. Pygame 인터랙티브 보드 그래픽 클래스
# ==========================================
class FlipTile:
    def __init__(self, x, y, w, h, font):
        self.rect = pygame.Rect(x, y, w, h)
        self.current_char = ""
        self.target_char = ""
        self.flip_progress = 1.0
        self.font = font

    def set_char(self, char):
        if self.target_char != char:
            self.target_char = char
            self.flip_progress = 0.0

    def update(self):
        if self.flip_progress < 1.0:
            self.flip_progress += 0.25
            if self.flip_progress >= 0.5 and self.current_char != self.target_char:
                self.current_char = self.target_char
            if self.flip_progress >= 1.0:
                self.flip_progress = 1.0

    def draw(self, surface):
        pygame.draw.rect(surface, (20, 22, 28), self.rect, border_radius=4)
        pygame.draw.rect(surface, (45, 50, 60), self.rect, 1, border_radius=4)

        cy = self.rect.centery
        pygame.draw.line(surface, (10, 10, 12), (self.rect.left, cy), (self.rect.right, cy), 1)

        if self.current_char:
            txt = self.font.render(self.current_char, True, (240, 240, 240))
            txt_rect = txt.get_rect(center=self.rect.center)
            surface.blit(txt, txt_rect)


class ToggleSwitch:
    def __init__(self, x, y, width=64, height=32):
        self.rect = pygame.Rect(x, y, width, height)
        self.is_night = True
        self.handle_x = x + width - height / 2
        self.target_x = self.handle_x
        self.radius = (height - 6) // 2

    def toggle(self):
        self.is_night = not self.is_night
        if self.is_night:
            self.target_x = self.rect.x + self.rect.width - self.rect.height / 2
        else:
            self.target_x = self.rect.x + self.rect.height / 2

    def update(self):
        self.handle_x += (self.target_x - self.handle_x) * 0.3

    def draw(self, surface):
        bg_color = (35, 40, 55) if self.is_night else (180, 210, 240)
        handle_color = (240, 240, 250) if self.is_night else (255, 190, 40)

        pygame.draw.rect(surface, bg_color, self.rect, border_radius=16)
        pygame.draw.rect(surface, (80, 90, 110), self.rect, 2, border_radius=16)
        pygame.draw.circle(
            surface,
            handle_color,
            (int(self.handle_x), self.rect.centery),
            self.radius
        )


class Star:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.x = random.randint(0, width)
        self.y = random.randint(0, int(height * 0.65))
        self.base_brightness = random.randint(100, 255)
        self.brightness = self.base_brightness
        self.twinkle_speed = random.uniform(0.03, 0.09)
        self.phase = random.uniform(0, math.pi * 2)

    def update(self):
        self.phase += self.twinkle_speed
        self.brightness = int(130 + 125 * math.sin(self.phase) * (self.base_brightness / 255))


class ShootingStar:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.reset()

    def reset(self):
        self.x = random.randint(0, self.width)
        self.y = random.randint(-40, int(self.height * 0.3))
        self.length = random.randint(70, 130)
        self.speed = random.uniform(10, 18)
        self.angle = math.radians(random.uniform(35, 50))
        self.active = False
        self.alpha = 255

    def spawn(self):
        if not self.active and random.random() < 0.07:
            self.reset()
            self.active = True

    def update(self):
        if self.active:
            self.x += math.cos(self.angle) * self.speed
            self.y += math.sin(self.angle) * self.speed
            self.alpha -= 5
            if self.alpha <= 0 or self.x > self.width or self.y > self.height * 0.7:
                self.active = False

    def draw(self, surface):
        if self.active:
            end_x = self.x - math.cos(self.angle) * self.length
            end_y = self.y - math.sin(self.angle) * self.length

            s = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.line(s, (255, 255, 200, max(0, self.alpha)), (self.x, self.y), (end_x, end_y), 2)
            pygame.draw.circle(s, (255, 255, 255, max(0, self.alpha)), (int(self.x), int(self.y)), 3)
            surface.blit(s, (0, 0))


# ==========================================
# 3. Pygame 루프 실행 함수
# ==========================================
def run_pygame():
    pygame.init()
    pygame.font.init()

    WIDTH, HEIGHT = 1000, 750
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Interactive Board")
    clock = pygame.time.Clock()

    FONT_FLIP = pygame.font.SysFont("arial", 20, bold=True)

    stars = [Star(WIDTH, HEIGHT) for _ in range(85)]
    shooting_star = ShootingStar(WIDTH, HEIGHT)
    toggle = ToggleSwitch(WIDTH - 90, 20)

    time_tiles = [FlipTile(30 + i * 26, HEIGHT - 55, 22, 34, FONT_FLIP) for i in range(19)]

    aurora_time = 0.0
    running = True

    while running:
        dt = clock.tick(60) / 1000.0
        aurora_time += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if toggle.rect.collidepoint(event.pos):
                    toggle.toggle()

        toggle.update()
        is_night = toggle.is_night

        if is_night:
            screen.fill((10, 12, 22))

            aurora_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for i in range(3):
                points = []
                base_y = 90 + i * 35
                for x in range(0, WIDTH + 20, 20):
                    y = (
                        base_y
                        + math.sin(x * 0.007 + aurora_time * 2.8 + i) * 40
                        + math.cos(x * 0.014 - aurora_time * 2.0) * 25
                    )
                    points.append((x, y))
                points.append((WIDTH, HEIGHT * 0.6))
                points.append((0, HEIGHT * 0.6))

                color = (0, 255, 150, 40) if i % 2 == 0 else (130, 70, 255, 30)
                pygame.draw.polygon(aurora_surface, color, points)
            screen.blit(aurora_surface, (0, 0))

            for star in stars:
                star.update()
                pygame.draw.circle(
                    screen,
                    (star.brightness, star.brightness, star.brightness),
                    (star.x, star.y),
                    2 if star.brightness > 200 else 1
                )

            for i in range(len(stars)):
                for j in range(i + 1, len(stars)):
                    dx = stars[i].x - stars[j].x
                    dy = stars[i].y - stars[j].y
                    dist = math.hypot(dx, dy)
                    if dist < 65 and stars[i].brightness > 160 and stars[j].brightness > 160:
                        alpha = int((1 - dist / 65) * 85)
                        line_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                        pygame.draw.line(
                            line_surf,
                            (180, 220, 255, alpha),
                            (stars[i].x, stars[i].y),
                            (stars[j].x, stars[j].y),
                            1
                        )
                        screen.blit(line_surf, (0, 0))

            shooting_star.spawn()
            shooting_star.update()
            shooting_star.draw(screen)

        else:
            screen.fill((215, 232, 248))
            pygame.draw.circle(screen, (255, 215, 80), (140, 90), 45)

        board_rect = pygame.Rect(30, 65, WIDTH - 60, HEIGHT - 140)
        pygame.draw.rect(
            screen,
            (18, 22, 32, 210) if is_night else (255, 255, 255, 230),
            board_rect,
            border_radius=10
        )
        pygame.draw.rect(
            screen,
            (55, 65, 85) if is_night else (190, 200, 215),
            board_rect,
            2,
            border_radius=10
        )

        toggle.draw(screen)

        now = dt.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        for idx, char in enumerate(time_str):
            if idx < len(time_tiles):
                time_tiles[idx].set_char(char)
                time_tiles[idx].update()
                time_tiles[idx].draw(screen)

        pygame.display.flip()

    pygame.quit()


# ==========================================
# 4. 프로그램 엔트리 포인트
# ==========================================
if __name__ == "__main__":
    # 환경변수 PYGAME_RUN이 "1"로 설정되어 있으면 Pygame 창을 실행하고,
    # 기본 상태(웹 서버 모드)에서는 Flask 앱을 실행합니다.
    if os.environ.get("PYGAME_RUN") == "1":
        run_pygame()
    else:
        port = int(os.environ.get("PORT", 5000))
        app.run(host="0.0.0.0", port=port, debug=False)
