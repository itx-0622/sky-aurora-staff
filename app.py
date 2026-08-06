import os
import json
import base64
import random
import requests
from flask import Flask, redirect, url_for, session, request, jsonify, render_template_string

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Environment Variables
DISCORD_CLIENT_SECRET = os.environ.get("DISCORD_CLIENT_SECRET", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "") # Format: "username/repo"
DATA_FILE = "sky_aurora_admin_data.json"

# Discord OAuth2 Config
DISCORD_CLIENT_ID = "1336971557418827788" # Application ID
REDIRECT_URI = "https://sky-aurora-staff.onrender.com/callback"

# Global In-Memory Data Store
DATA_STORE = {
    "admin_whitelist": [
        "1534184089144266872",
        "843621337066504225"
    ],
    "user_whitelist": [
        "1336971557418827788"
    ],
    "user_blacklist": [],
    "manuals": [],
    "logs": []
}

def load_data_from_github():
    global DATA_STORE
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("[GitHub Sync] GITHUB_TOKEN or GITHUB_REPO not set. Using local in-memory store.")
        return
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            content = response.json().get("content", "")
            decoded_bytes = base64.b64decode(content)
            DATA_STORE = json.loads(decoded_bytes.decode('utf-8'))
            print("[GitHub Sync] Data initialized successfully from GitHub repo.")
        else:
            print(f"[GitHub Sync] File not found or failed to fetch (Status {response.status_code}). Using default store.")
    except Exception as e:
        print(f"[GitHub Sync Failed] Error loading data: {e}")

def save_data_to_github(commit_message="Auto-sync manual data"):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{DATA_FILE}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    sha = None
    try:
        get_res = requests.get(url, headers=headers)
        if get_res.status_code == 200:
            sha = get_res.json().get("sha")
    except Exception as e:
        print(f"[GitHub Sync Warning] Failed to check existing file sha: {e}")
        
    json_str = json.dumps(DATA_STORE, indent=2, ensure_ascii=False)
    encoded_content = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": f"{commit_message} [{request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)}]",
        "content": encoded_content
    }
    if sha:
        payload["sha"] = sha
        
    try:
        put_res = requests.put(url, headers=headers, json=payload)
        if put_res.status_code in [200, 201]:
            print("[GitHub Sync] Data successfully saved to GitHub.")
        else:
            print(f"[GitHub Sync Error] Failed to save (Status {put_res.status_code}): {put_res.text}")
    except Exception as e:
        print(f"[GitHub Sync Failed] Error saving data: {e}")

# Load initial data from GitHub
load_data_from_github()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sky Aurora Staff Portal</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.5/font/bootstrap-icons.css">
    <style>
        :root {
            --aurora-bg: #0b0f19;
            --aurora-card: rgba(22, 28, 45, 0.75);
            --aurora-border: rgba(99, 102, 241, 0.25);
            --aurora-primary: #6366f1;
            --aurora-accent: #a855f7;
            --aurora-cyan: #06b6d4;
        }

        body {
            background-color: var(--aurora-bg);
            color: #f3f4f6;
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif;
            min-height: 100vh;
            overflow-x: hidden;
            position: relative;
        }

        /* 오로라 라이트 애니메이션 배경 */
        .aurora-bg-glow {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: -1;
            overflow: hidden;
            pointer-events: none;
        }

        .aurora-blob {
            position: absolute;
            filter: blur(80px);
            opacity: 0.35;
            border-radius: 50%;
            animation: floatAurora 18s infinite alternate ease-in-out;
        }

        .blob-1 { top: -10%; left: -10%; width: 50vw; height: 50vw; background: radial-gradient(circle, #6366f1, #a855f7); }
        .blob-2 { bottom: -20%; right: -10%; width: 60vw; height: 60vw; background: radial-gradient(circle, #06b6d4, #3b82f6); animation-delay: -5s; }
        .blob-3 { top: 40%; left: 30%; width: 40vw; height: 40vw; background: radial-gradient(circle, #ec4899, #8b5cf6); animation-delay: -10s; }

        @keyframes floatAurora {
            0% { transform: translate(0, 0) scale(1) rotate(0deg); }
            50% { transform: translate(50px, 40px) scale(1.1) rotate(180deg); }
            100% { transform: translate(-30px, 80px) scale(0.95) rotate(360deg); }
        }

        .glass-card {
            background: var(--aurora-card);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--aurora-border);
            border-radius: 16px;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        .nav-tabs .nav-link {
            color: #9ca3af;
            border: none;
            border-bottom: 2px solid transparent;
            padding: 12px 20px;
            font-weight: 500;
        }

        .nav-tabs .nav-link.active {
            color: #ffffff;
            background: transparent;
            border-bottom: 2px solid var(--aurora-primary);
        }

        /* 인트로 오버레이 및 프로필 링 애니메이션 */
        #intro-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: #070a12;
            z-index: 9999;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            transition: opacity 0.8s ease, visibility 0.8s;
        }

        .profile-ring-container {
            position: relative;
            width: 140px;
            height: 140px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .profile-avatar-img {
            width: 100px;
            height: 100px;
            border-radius: 50%;
            z-index: 2;
            object-fit: cover;
            border: 2px solid var(--aurora-cyan);
            box-shadow: 0 0 20px rgba(6, 182, 212, 0.5);
        }

        /* 프로필 링 커졌다 작아지는 효과 및 파동 링 */
        .ring-pulse {
            position: absolute;
            top: 0;
            left: 0;
            width: 140px;
            height: 140px;
            border-radius: 50%;
            border: 2px solid var(--aurora-primary);
            animation: ringExpandShrink 2.5s infinite ease-in-out;
            z-index: 1;
        }

        .ripple-ring {
            position: absolute;
            border-radius: 50%;
            border: 1.5px solid var(--aurora-accent);
            opacity: 0;
            animation: rippleExpand 2.5s infinite ease-out;
        }

        .ripple-1 { animation-delay: 0s; }
        .ripple-2 { animation-delay: 0.6s; }
        .ripple-3 { animation-delay: 1.2s; }

        @keyframes ringExpandShrink {
            0%, 100% { transform: scale(0.85); opacity: 0.5; border-color: var(--aurora-cyan); }
            50% { transform: scale(1.25); opacity: 1; border-color: var(--aurora-accent); box-shadow: 0 0 25px var(--aurora-accent); }
        }

        @keyframes rippleExpand {
            0% { width: 100px; height: 100px; opacity: 0.8; }
            100% { width: 220px; height: 220px; opacity: 0; }
        }

        /* 태그 자동완성 Dropdown */
        .autocomplete-suggestions {
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: #111827;
            border: 1px solid var(--aurora-border);
            border-radius: 8px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
        }

        .suggestion-item {
            padding: 8px 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .suggestion-item:hover {
            background: rgba(99, 102, 241, 0.2);
        }

        /* Custom Modal Notification */
        .custom-alert-modal {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            min-width: 300px;
            border-radius: 12px;
            background: rgba(17, 24, 39, 0.95);
            border: 1px solid var(--aurora-primary);
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
        }
    </style>
</head>
<body>

    <!-- 오로라 백그라운드 -->
    <div class="aurora-bg-glow">
        <div class="aurora-blob blob-1"></div>
        <div class="aurora-blob blob-2"></div>
        <div class="aurora-blob blob-3"></div>
    </div>

    <!-- 인트로 오버레이 -->
    <div id="intro-overlay">
        <div class="profile-ring-container mb-4">
            <div class="ring-pulse"></div>
            <div class="ripple-ring ripple-1"></div>
            <div class="ripple-ring ripple-2"></div>
            <div class="ripple-ring ripple-3"></div>
            {% if session.get('user') %}
                <img src="https://cdn.discordapp.com/avatars/{{ session['user']['id'] }}/{{ session['user']['avatar'] }}.png" class="profile-avatar-img" alt="Profile">
            {% else %}
                <img src="https://cdn.discordapp.com/embed/avatars/0.png" class="profile-avatar-img" alt="Guest">
            {% endif %}
        </div>
        <h4 id="intro-text" class="text-light fw-bold">시스템 접속 준비 중...</h4>
        <p class="text-muted small">Sky Aurora Staff Management Protocol</p>
    </div>

    <!-- 커스텀 알림 모달 컨테이너 -->
    <div id="alert-container"></div>

    <div class="container py-4">
        <!-- 상단 헤더 -->
        <header class="d-flex justify-content-between align-items-center mb-4 glass-card p-3">
            <div class="d-flex align-items-center gap-3">
                <i class="bi bi-airplane-engines-fill text-primary fs-3"></i>
                <h3 class="m-0 fw-bold bg-gradient text-white">Sky Aurora Staff Portal</h3>
            </div>
            <div>
                {% if session.get('user') %}
                    <div class="d-flex align-items-center gap-3">
                        <img src="https://cdn.discordapp.com/avatars/{{ session['user']['id'] }}/{{ session['user']['avatar'] }}.png" width="36" height="36" class="rounded-circle border border-primary" alt="avatar">
                        <div>
                            <span class="fw-bold d-block fs-6">{{ session['user']['username'] }}</span>
                            <span class="badge bg-primary-subtle text-primary border border-primary-subtle fs-7">
                                {% if session['user']['id'] in admin_whitelist %}Admin{% else %}Staff{% endif %}
                            </span>
                        </div>
                        <a href="/logout" class="btn btn-outline-danger btn-sm ms-2"><i class="bi bi-box-arrow-right"></i></a>
                    </div>
                {% else %}
                    <a href="/login" class="btn btn-primary"><i class="bi bi-discord me-2"></i>Discord 로그인</a>
                {% endif %}
            </div>
        </header>

        {% if session.get('user') %}
        <!-- 네비게이션 탭 -->
        <ul class="nav nav-tabs mb-4 border-secondary" id="portalTabs" role="tablist">
            <li class="nav-item">
                <button class="nav-link active" id="manual-tab" data-bs-toggle="tab" data-bs-target="#manual-sec" type="button"><i class="bi bi-journal-text me-2"></i>매뉴얼 관리</button>
            </li>
            {% if session['user']['id'] in admin_whitelist %}
            <li class="nav-item">
                <button class="nav-link" id="staff-tab" data-bs-toggle="tab" data-bs-target="#staff-sec" type="button"><i class="bi bi-people-fill me-2"></i>직원/권한 관리</button>
            </li>
            <li class="nav-item">
                <button class="nav-link" id="log-tab" data-bs-toggle="tab" data-bs-target="#log-sec" type="button"><i class="bi bi-shield-lock-fill me-2"></i>시스템 보안 로그</button>
            </li>
            {% endif %}
        </ul>

        <div class="tab-content" id="portalTabsContent">
            <!-- 매뉴얼 관리 탭 -->
            <div class="tab-pane fade show active" id="manual-sec" role="tabpanel">
                <div class="row g-4">
                    <div class="col-lg-5">
                        <div class="glass-card p-4">
                            <h5 class="fw-bold mb-3 text-info"><i class="bi bi-pencil-square me-2"></i>매뉴얼 작성 및 수정</h5>
                            
                            <!-- 매뉴얼 선택 드롭다운 (수정 모드 지원) -->
                            <div class="mb-3">
                                <label class="form-label text-muted small">수정할 매뉴얼 선택</label>
                                <select class="form-select bg-dark text-light border-secondary" id="select-manual-to-edit" onchange="loadSelectedManual()">
                                    <option value="">-- 새로 작성하기 --</option>
                                    {% for m in manuals %}
                                        <option value="{{ m.id }}">[{{ m.category }}] {{ m.title }}</option>
                                    {% endfor %}
                                </select>
                            </div>

                            <input type="hidden" id="manual-id-val" value="">

                            <div class="mb-3">
                                <label class="form-label text-muted small">카테고리</label>
                                <input type="text" id="manual-category" class="form-control bg-dark text-light border-secondary" placeholder="예: 운항, 지상지원, 보안">
                            </div>
                            <div class="mb-3">
                                <label class="form-label text-muted small">제목</label>
                                <input type="text" id="manual-title" class="form-control bg-dark text-light border-secondary" placeholder="매뉴얼 제목 입력">
                            </div>
                            <div class="mb-3">
                                <label class="form-label text-muted small">내용</label>
                                <textarea id="manual-content" class="form-control bg-dark text-light border-secondary" rows="6" placeholder="세부 지침을 작성하세요..."></textarea>
                            </div>
                            <div class="form-check mb-3">
                                <input class="form-check-input" type="checkbox" id="manual-pinned">
                                <label class="form-check-label text-muted small" for="manual-pinned">상단 고정 지정</label>
                            </div>
                            <div class="d-flex gap-2">
                                <button class="btn btn-primary flex-grow-1" onclick="submitManual()"><i class="bi bi-check-lg me-1"></i>저장하기</button>
                                <button class="btn btn-outline-warning" onclick="saveDraft()"><i class="bi bi-bookmark-plus me-1"></i>임시저장</button>
                                <button class="btn btn-outline-info" onclick="loadDraft()"><i class="bi bi-arrow-counterclockwise me-1"></i>임시불러오기</button>
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-7">
                        <div class="glass-card p-4">
                            <h5 class="fw-bold mb-3"><i class="bi bi-journal-bookmark me-2"></i>등록된 매뉴얼 목록</h5>
                            <div class="accordion" id="manualAccordion">
                                {% for m in manuals %}
                                <div class="accordion-item bg-dark border-secondary text-light mb-2 rounded overflow-hidden">
                                    <h2 class="accordion-header">
                                        <button class="accordion-button collapsed bg-dark text-light" type="button" data-bs-toggle="collapse" data-bs-target="#collapse{{ m.id }}">
                                            {% if m.pinned %}<span class="badge bg-warning text-dark me-2">고정</span>{% endif %}
                                            <span class="badge bg-secondary me-2">{{ m.category }}</span>
                                            <strong>{{ m.title }}</strong>
                                        </button>
                                    </h2>
                                    <div id="collapse{{ m.id }}" class="accordion-collapse collapse" data-bs-parent="#manualAccordion">
                                        <div class="accordion-body border-top border-secondary">
                                            <p style="white-space: pre-wrap;">{{ m.content }}</p>
                                            {% if session['user']['id'] in admin_whitelist %}
                                            <div class="text-end">
                                                <button class="btn btn-danger btn-sm" onclick="deleteManual({{ m.id }})"><i class="bi bi-trash"></i> 삭제</button>
                                            </div>
                                            {% endif %}
                                        </div>
                                    </div>
                                </div>
                                {% endfor %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {% if session['user']['id'] in admin_whitelist %}
            <!-- 직원 및 권한 관리 탭 -->
            <div class="tab-pane fade" id="staff-sec" role="tabpanel">
                <div class="row g-4">
                    <div class="col-lg-6">
                        <div class="glass-card p-4">
                            <h5 class="fw-bold mb-3 text-success"><i class="bi bi-person-check me-2"></i>화이트리스트 등록 (직원 추가)</h5>
                            
                            <div class="mb-3 position-relative">
                                <label class="form-label text-muted small">디스코드 사용자 검색 / ID 입력 ('@' 입력 가능)</label>
                                <input type="text" id="target-wl-id" class="form-control bg-dark text-light border-secondary" placeholder="@사용자이름 또는 디스코드 ID" oninput="handleUserSearch(this)">
                                <div id="wl-autocomplete" class="autocomplete-suggestions d-none"></div>
                            </div>

                            <!-- 선택된 사용자 프로필 미리보기 카드 -->
                            <div id="user-profile-preview" class="d-none card bg-dark border-info p-3 mb-3">
                                <div class="d-flex align-items-center gap-3">
                                    <img id="preview-avatar" src="" class="rounded-circle" width="48" height="48" alt="avatar">
                                    <div>
                                        <h6 id="preview-name" class="m-0 fw-bold text-info"></h6>
                                        <small id="preview-id" class="text-muted"></small>
                                    </div>
                                </div>
                            </div>

                            <div class="form-check mb-3">
                                <input class="form-check-input" type="checkbox" id="grant-admin-option">
                                <label class="form-check-label text-warning small fw-bold" for="grant-admin-option">
                                    <i class="bi bi-shield-lock me-1"></i>어드민(Admin) 권한으로 함께 등록
                                </label>
                            </div>

                            <button class="btn btn-success w-100" onclick="addWhitelist()"><i class="bi bi-plus-circle me-1"></i>화이트리스트 추가</button>
                        </div>
                    </div>

                    <div class="col-lg-6">
                        <div class="glass-card p-4">
                            <h5 class="fw-bold mb-3 text-danger"><i class="bi bi-person-slash me-2"></i>블랙리스트 등록</h5>
                            <div class="mb-3">
                                <label class="form-label text-muted small">디스코드 ID</label>
                                <input type="text" id="target-bl-id" class="form-control bg-dark text-light border-secondary" placeholder="블랙리스트 등록 대상 ID">
                            </div>
                            <p class="text-muted small">* 블랙리스트 등록 시 해당 대상은 화이트리스트 및 어드민 권한에서 즉시 자동 삭제 처리됩니다.</p>
                            <button class="btn btn-danger w-100" onclick="addBlacklist()"><i class="bi bi-slash-circle me-1"></i>블랙리스트 추가</button>
                        </div>
                    </div>

                    <div class="col-12">
                        <div class="glass-card p-4">
                            <h5 class="fw-bold mb-3"><i class="bi bi-list-stars me-2"></i>등록 현황</h5>
                            <div class="row">
                                <div class="col-md-4">
                                    <h6>Admin Whitelist</h6>
                                    <ul class="list-group bg-dark">
                                        {% for aid in admin_whitelist %}
                                            <li class="list-group-item bg-dark text-light border-secondary d-flex justify-content-between align-items-center">
                                                {{ aid }}
                                            </li>
                                        {% endfor %}
                                    </ul>
                                </div>
                                <div class="col-md-4">
                                    <h6>Staff Whitelist</h6>
                                    <ul class="list-group bg-dark">
                                        {% for wid in user_whitelist %}
                                            <li class="list-group-item bg-dark text-light border-secondary d-flex justify-content-between align-items-center">
                                                {{ wid }}
                                                <button class="btn btn-sm btn-outline-danger" onclick="removeWhitelist('{{ wid }}')">삭제</button>
                                            </li>
                                        {% endfor %}
                                    </ul>
                                </div>
                                <div class="col-md-4">
                                    <h6>Blacklist</h6>
                                    <ul class="list-group bg-dark">
                                        {% for bid in user_blacklist %}
                                            <li class="list-group-item bg-dark text-light border-secondary d-flex justify-content-between align-items-center">
                                                {{ bid }}
                                                <button class="btn btn-sm btn-outline-secondary" onclick="removeBlacklist('{{ bid }}')">해제</button>
                                            </li>
                                        {% endfor %}
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 시스템 보안 로그 탭 -->
            <div class="tab-pane fade" id="log-sec" role="tabpanel">
                <div class="glass-card p-4">
                    <h5 class="fw-bold mb-3 text-warning"><i class="bi bi-terminal me-2"></i>실시간 보안 및 조작 로그</h5>
                    <div class="bg-dark p-3 rounded border border-secondary font-monospace" style="max-height: 400px; overflow-y: auto;" id="log-container">
                        {% for log in logs %}
                            <div class="text-light fs-7 mb-1">{{ log }}</div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            {% endif %}
        </div>
        {% else %}
        <div class="text-center py-5 glass-card my-5">
            <i class="bi bi-shield-lock text-primary display-1"></i>
            <h2 class="mt-3 fw-bold">인증이 필요합니다</h2>
            <p class="text-muted">Sky Aurora 직원 포탈을 이용하시려면 디스코드 계정으로 로그인해 주세요.</p>
            <a href="/login" class="btn btn-primary btn-lg mt-3"><i class="bi bi-discord me-2"></i>Discord 계정으로 로그인</a>
        </div>
        {% endif %}
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // 랜덤 3~5초 인트로 타이머 및 애니메이션 제어
        document.addEventListener("DOMContentLoaded", function() {
            const introOverlay = document.getElementById("intro-overlay");
            const introText = document.getElementById("intro-text");
            
            const randomDelay = Math.floor(Math.random() * 2000) + 3000; // 3000ms ~ 5000ms
            
            setTimeout(() => {
                introText.innerText = "환영합니다!";
                introText.classList.add("text-cyan");
                
                setTimeout(() => {
                    introOverlay.style.opacity = "0";
                    setTimeout(() => {
                        introOverlay.style.visibility = "hidden";
                    }, 800);
                }, 800);
            }, randomDelay);
        });

        // 커스텀 사이트 모달 알림
        function showCustomAlert(message, type = 'info') {
            const container = document.getElementById('alert-container');
            const alertDiv = document.createElement('div');
            alertDiv.className = `custom-alert-modal p-3 text-light alert-${type} fade show`;
            alertDiv.innerHTML = `
                <div class="d-flex justify-content-between align-items-center">
                    <div><i class="bi bi-bell-fill me-2 text-info"></i>${message}</div>
                    <button type="button" class="btn-close btn-close-white ms-2" onclick="this.parentElement.parentElement.remove()"></button>
                </div>
            `;
            container.appendChild(alertDiv);
            setTimeout(() => { alertDiv.remove(); }, 4000);
        }

        // 보안 감지 (Ctrl+C, Ctrl+V, Win+Shift+S / PrintScreen, 접속 기기 정보)
        const getDeviceType = () => {
            const ua = navigator.userAgent;
            return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(ua) ? "Mobile" : "Desktop (PC)";
        };

        document.addEventListener('keydown', function(e) {
            const device = getDeviceType();
            
            // 복사 / 붙여넣기 감지
            if ((e.ctrlKey || e.metaKey) && (e.key === 'c' || e.key === 'v')) {
                const action = e.key === 'c' ? '복사 (Ctrl+C)' : '붙여넣기 (Ctrl+V)';
                sendLog(`[보안 감지] [${device}] 사용자가 클립보드 ${action}를 수행함`);
            }

            // Windows + Shift + S 또는 PrintScreen 캡처 감지
            if (e.key === 'PrintScreen' || (e.shiftKey && e.metaKey && e.key === 'S') || (e.shiftKey && e.winKey && e.key === 'S')) {
                sendLog(`[보안 경고] [${device}] 화면 캡처 시도 감지됨 (Win+Shift+S / PrintScreen)`);
                showCustomAlert("화면 캡처 동작이 감지되어 보안 로그에 기록되었습니다.", "danger");
            }
        });

        function sendLog(logMessage) {
            fetch('/api/log', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ message: logMessage })
            });
        }

        // 매뉴얼 임시저장 / 불러오기 기능
        function saveDraft() {
            const draft = {
                category: document.getElementById('manual-category').value,
                title: document.getElementById('manual-title').value,
                content: document.getElementById('manual-content').value,
                pinned: document.getElementById('manual-pinned').checked
            };
            localStorage.setItem('manual_draft', JSON.stringify(draft));
            showCustomAlert("작성 중인 매뉴얼이 브라우저에 임시저장되었습니다.", "success");
        }

        function loadDraft() {
            const draftStr = localStorage.getItem('manual_draft');
            if (!draftStr) {
                showCustomAlert("임시저장된 데이터가 없습니다.", "warning");
                return;
            }
            const draft = JSON.parse(draftStr);
            document.getElementById('manual-category').value = draft.category || '';
            document.getElementById('manual-title').value = draft.title || '';
            document.getElementById('manual-content').value = draft.content || '';
            document.getElementById('manual-pinned').checked = draft.pinned || false;
            showCustomAlert("임시저장된 내용을 성공적으로 불러왔습니다.", "info");
        }

        // 선택 매뉴얼 수정 로드
        function loadSelectedManual() {
            const selectedId = document.getElementById('select-manual-to-edit').value;
            if (!selectedId) {
                document.getElementById('manual-id-val').value = "";
                document.getElementById('manual-category').value = "";
                document.getElementById('manual-title').value = "";
                document.getElementById('manual-content').value = "";
                document.getElementById('manual-pinned').checked = false;
                return;
            }

            fetch('/api/manuals/' + selectedId)
                .then(res => res.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('manual-id-val').value = data.manual.id;
                        document.getElementById('manual-category').value = data.manual.category;
                        document.getElementById('manual-title').value = data.manual.title;
                        document.getElementById('manual-content').value = data.manual.content;
                        document.getElementById('manual-pinned').checked = data.manual.pinned;
                        showCustomAlert("매뉴얼 데이터를 불러왔습니다. 수정 후 저장하세요.", "info");
                    }
                });
        }

        function submitManual() {
            const id = document.getElementById('manual-id-val').value;
            const category = document.getElementById('manual-category').value;
            const title = document.getElementById('manual-title').value;
            const content = document.getElementById('manual-content').value;
            const pinned = document.getElementById('manual-pinned').checked;

            if (!title || !content) {
                showCustomAlert("제목과 내용을 입력해 주세요.", "warning");
                return;
            }

            fetch('/api/manuals', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ id: id, category: category, title: title, content: content, pinned: pinned })
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    localStorage.removeItem('manual_draft');
                    location.reload();
                }
            });
        }

        function deleteManual(id) {
            if (confirm("정말 이 매뉴얼을 삭제하시겠습니까?")) {
                fetch('/api/manuals/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id: id })
                }).then(res => res.json()).then(data => { if (data.success) location.reload(); });
            }
        }

        // 사용자 태그 자동완성 검색 (@기능)
        const mockUsers = [
            { id: "1534184089144266872", username: "SkyAurora_Admin", nickname: "총괄 관리자", avatar: "https://cdn.discordapp.com/embed/avatars/1.png" },
            { id: "1336971557418827788", username: "Staff_Member1", nickname: "지상팀 팀장", avatar: "https://cdn.discordapp.com/embed/avatars/2.png" },
            { id: "843621337066504225", username: "Pilot_Captain", nickname: "운항 기장", avatar: "https://cdn.discordapp.com/embed/avatars/3.png" }
        ];

        function handleUserSearch(input) {
            const val = input.value;
            const autocomplete = document.getElementById('wl-autocomplete');
            
            if (val.startsWith('@') || val.length > 0) {
                const query = val.replace('@', '').toLowerCase();
                const filtered = mockUsers.filter(u => u.username.toLowerCase().includes(query) || u.nickname.toLowerCase().includes(query) || u.id.includes(query));
                
                if (filtered.length > 0) {
                    autocomplete.innerHTML = filtered.map(u => `
                        <div class="suggestion-item" onclick="selectUser('${u.id}', '${u.username}', '${u.nickname}', '${u.avatar}')">
                            <img src="${u.avatar}" width="24" height="24" class="rounded-circle">
                            <div>
                                <strong>${u.nickname}</strong> <small class="text-muted">(@${u.username})</small>
                            </div>
                        </div>
                    `).join('');
                    autocomplete.classList.remove('d-none');
                } else {
                    autocomplete.classList.add('d-none');
                }
            } else {
                autocomplete.classList.add('d-none');
            }
        }

        function selectUser(id, username, nickname, avatar) {
            document.getElementById('target-wl-id').value = id;
            document.getElementById('wl-autocomplete').classList.add('d-none');

            // 프로필 미리보기
            document.getElementById('preview-avatar').src = avatar;
            document.getElementById('preview-name').innerText = `${nickname} (@${username})`;
            document.getElementById('preview-id').innerText = `ID: ${id}`;
            document.getElementById('user-profile-preview').classList.remove('d-none');
        }

        function addWhitelist() {
            const targetId = document.getElementById('target-wl-id').value;
            const grantAdmin = document.getElementById('grant-admin-option').checked;

            if (!targetId) {
                showCustomAlert("대상 디스코드 ID를 입력해 주세요.", "warning");
                return;
            }

            fetch('/api/whitelist/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ target_id: targetId, is_admin: grantAdmin })
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    showCustomAlert("화이트리스트에 성공적으로 등록되었습니다.", "success");
                    setTimeout(() => location.reload(), 1000);
                }
            });
        }

        function addBlacklist() {
            const targetId = document.getElementById('target-bl-id').value;
            if (!targetId) {
                showCustomAlert("블랙리스트 대상 ID를 입력해 주세요.", "warning");
                return;
            }

            fetch('/api/blacklist/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ target_id: targetId })
            }).then(res => res.json()).then(data => {
                if (data.success) {
                    showCustomAlert("블랙리스트에 등록되었으며, 기존 권한에서 차단/제거되었습니다.", "danger");
                    setTimeout(() => location.reload(), 1000);
                }
            });
        }

        function removeWhitelist(id) {
            fetch('/api/whitelist/remove', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ target_id: id })
            }).then(res => res.json()).then(data => { if (data.success) location.reload(); });
        }

        function removeBlacklist(id) {
            fetch('/api/blacklist/remove', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ target_id: id })
            }).then(res => res.json()).then(data => { if (data.success) location.reload(); });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(
        HTML_TEMPLATE,
        session=session,
        admin_whitelist=DATA_STORE["admin_whitelist"],
        user_whitelist=DATA_STORE["user_whitelist"],
        user_blacklist=DATA_STORE["user_blacklist"],
        manuals=sorted(DATA_STORE["manuals"], key=lambda x: x.get('pinned', False), reverse=True),
        logs=DATA_STORE["logs"]
    )

@app.route('/login')
def login():
    discord_auth_url = f"https://discord.com/api/oauth2/authorize?client_id={DISCORD_CLIENT_ID}&redirect_uri={REDIRECT_URI}&response_type=code&scope=identify"
    return redirect(discord_auth_url)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index'))
    
    data = {
        'client_id': DISCORD_CLIENT_ID,
        'client_secret': DISCORD_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    token_res = requests.post('https://discord.com/api/oauth2/token', data=data, headers=headers)
    token_json = token_res.json()
    access_token = token_json.get('access_token')
    
    if not access_token:
        return "Discord Authentication Failed.", 400
        
    user_res = requests.get('https://discord.com/api/users/@me', headers={'Authorization': f'Bearer {access_token}'})
    user_data = user_res.json()
    
    user_id = user_data.get('id')
    
    # Check Blacklist
    if user_id in DATA_STORE["user_blacklist"]:
        return "접속이 거부되었습니다 (Blacklisted User).", 403
        
    session['user'] = user_data
    
    # Log User Login
    log_msg = f"[{user_data.get('username')}] 사탕이: 시스템에 성공적으로 로그인함 (ID: {user_id})"
    DATA_STORE["logs"].insert(0, log_msg)
    save_data_to_github("User Login Log Update")
    
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

# API: 매뉴얼 단건 조회 (수정용)
@app.route('/api/manuals/<int:manual_id>', methods=['GET'])
def get_manual(manual_id):
    manual = next((m for m in DATA_STORE["manuals"] if m["id"] == manual_id), None)
    if manual:
        return jsonify({"success": True, "manual": manual})
    return jsonify({"success": False, "message": "Not Found"}), 404

# API: 매뉴얼 추가/수정
@app.route('/api/manuals', methods=['POST'])
def save_manual():
    if 'user' not in session:
        return jsonify({"success": False}), 403
    
    req = request.json
    m_id = req.get('id')
    category = req.get('category', '일반')
    title = req.get('title')
    content = req.get('content')
    pinned = req.get('pinned', False)
    
    if m_id:
        # Edit existing
        for m in DATA_STORE["manuals"]:
            if m["id"] == int(m_id):
                m["category"] = category
                m["title"] = title
                m["content"] = content
                m["pinned"] = pinned
                break
        log_msg = f"[매뉴얼 수정] {session['user']['username']}: 매뉴얼 '{title}' 수정 완료"
    else:
        # Create new
        new_id = random.randint(10000000, 99999999)
        DATA_STORE["manuals"].append({
            "id": new_id,
            "category": category,
            "title": title,
            "content": content,
            "pinned": pinned
        })
        log_msg = f"[매뉴얼 등록] {session['user']['username']}: 새 매뉴얼 '{title}' 등록 완료"

    DATA_STORE["logs"].insert(0, log_msg)
    save_data_to_github("Manual Created/Updated")
    return jsonify({"success": True})

@app.route('/api/manuals/delete', methods=['POST'])
def delete_manual():
    if 'user' not in session or session['user']['id'] not in DATA_STORE["admin_whitelist"]:
        return jsonify({"success": False}), 403
    
    m_id = request.json.get('id')
    DATA_STORE["manuals"] = [m for m in DATA_STORE["manuals"] if m["id"] != int(m_id)]
    
    log_msg = f"[매뉴얼 삭제] Admin({session['user']['username']}): 매뉴얼 (ID: {m_id}) 삭제"
    DATA_STORE["logs"].insert(0, log_msg)
    save_data_to_github("Manual Deleted")
    return jsonify({"success": True})

# API: 화이트리스트 추가 (어드민 옵션 포함)
@app.route('/api/whitelist/add', methods=['POST'])
def add_whitelist():
    if 'user' not in session or session['user']['id'] not in DATA_STORE["admin_whitelist"]:
        return jsonify({"success": False}), 403
    
    target_id = request.json.get('target_id')
    is_admin = request.json.get('is_admin', False)
    
    if target_id not in DATA_STORE["user_whitelist"]:
        DATA_STORE["user_whitelist"].append(target_id)
        
    if is_admin and target_id not in DATA_STORE["admin_whitelist"]:
        DATA_STORE["admin_whitelist"].append(target_id)
        
    log_msg = f"[권한 변경] {session['user']['username']}: ID {target_id} -> whitelist 추가 (Admin 옵션: {is_admin})"
    DATA_STORE["logs"].insert(0, log_msg)
    save_data_to_github("Whitelist Added")
    return jsonify({"success": True})

# API: 블랙리스트 추가 (기존 화이트/어드민 리스트 자동 제거)
@app.route('/api/blacklist/add', methods=['POST'])
def add_blacklist():
    if 'user' not in session or session['user']['id'] not in DATA_STORE["admin_whitelist"]:
        return jsonify({"success": False}), 403
    
    target_id = request.json.get('target_id')
    
    if target_id not in DATA_STORE["user_blacklist"]:
        DATA_STORE["user_blacklist"].append(target_id)
        
    # 기존 화이트리스트 및 어드민 리스트에서 완전 삭제 처리
    if target_id in DATA_STORE["user_whitelist"]:
        DATA_STORE["user_whitelist"].remove(target_id)
    if target_id in DATA_STORE["admin_whitelist"]:
        DATA_STORE["admin_whitelist"].remove(target_id)
        
    log_msg = f"[차단 등록] {session['user']['username']}: ID {target_id} -> 블랙리스트 등록 (기존 권한 전부 박탈)"
    DATA_STORE["logs"].insert(0, log_msg)
    save_data_to_github("Blacklist Added")
    return jsonify({"success": True})

@app.route('/api/whitelist/remove', methods=['POST'])
def remove_whitelist():
    if 'user' not in session or session['user']['id'] not in DATA_STORE["admin_whitelist"]:
        return jsonify({"success": False}), 403
    
    target_id = request.json.get('target_id')
    if target_id in DATA_STORE["user_whitelist"]:
        DATA_STORE["user_whitelist"].remove(target_id)
        
    save_data_to_github("Whitelist Removed")
    return jsonify({"success": True})

@app.route('/api/blacklist/remove', methods=['POST'])
def remove_blacklist():
    if 'user' not in session or session['user']['id'] not in DATA_STORE["admin_whitelist"]:
        return jsonify({"success": False}), 403
    
    target_id = request.json.get('target_id')
    if target_id in DATA_STORE["user_blacklist"]:
        DATA_STORE["user_blacklist"].remove(target_id)
        
    save_data_to_github("Blacklist Removed")
    return jsonify({"success": True})

# API: 실시간 클라이언트 로그 전송
@app.route('/api/log', methods=['POST'])
def client_log():
    log_msg = request.json.get('message')
    if log_msg:
        DATA_STORE["logs"].insert(0, log_msg)
        save_data_to_github("Security Client Log Entry")
    return jsonify({"success": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
