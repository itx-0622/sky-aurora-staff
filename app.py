import React, { useState, useEffect } from 'react';

// ==========================================
// 오로라 테마 색상 팔레트 정의
// ==========================================
const AURORA_PALETTES = [
  'linear-gradient(135deg, #7F00FF, #E100FF, #00F2FE)', // 퍼플-핑크-시안
  'linear-gradient(135deg, #00c6ff, #0072ff, #2AFADF)', // 북극광 블루
  'linear-gradient(135deg, #43e97b, #38f9d7, #0575E6)', // 에메랄드 그린
  'linear-gradient(135deg, #fa709a, #fee140, #96e6a1)', // 황혼 파스텔
  'linear-gradient(135deg, #667eea, #764ba2, #6B8DD6)', // 미드나잇 바이올렛
];

export default function SkyAuroraStaffManual() {
  // ==========================================
  // 상태 관리 (State Management)
  // ==========================================
  const [user, setUser] = useState({
    id: 'user_staff_01',
    name: 'StaffUser',
    role: 'ADMIN', // 'ADMIN' | 'USER'
    isWhitelisted: true,
    isBlacklisted: false,
  });

  const [adminInput, setAdminInput] = useState('');
  const [currentAurora, setCurrentAurora] = useState(AURORA_PALETTES[0]);
  const [logs, setLogs] = useState([]);

  // 매뉴얼 데이터 목록 상태
  const [manuals, setManuals] = useState([
    {
      id: 1,
      category: '운항 지침',
      title: '비행 지침 및 기본 운항 표준',
      content: '지상 및 운항 중 준수해야 할 기본 절차입니다.',
      pinned: true,
    },
    {
      id: 2,
      category: '공통 매뉴얼',
      title: '스태프 공통 근무 수칙',
      content: '모든 스태프가 숙지해야 하는 서비스 및 소통 지침입니다.',
      pinned: false,
    },
  ]);

  // 매뉴얼 작성 및 수정 폼 상태
  const [editManual, setEditManual] = useState({
    id: null,
    category: '',
    title: '',
    content: '',
    pinned: false,
  });

  // ==========================================
  // 라이프사이클 및 보안 검증 (Effects)
  // ==========================================
  useEffect(() => {
    // 1. 블랙리스트 검증 - 차단 유저 접근 금지
    if (user.isBlacklisted) {
      alert('[접속 거부] 블랙리스트 처리된 사용자입니다.');
      return;
    }

    // 2. 화이트리스트 검증 - 미등록 유저 접근 금지
    if (!user.isWhitelisted) {
      alert('[접속 거부] 화이트리스트에 등록되어 있지 않습니다.');
      return;
    }

    // 3. 접속할 때마다 오로라 색상 무작위 할당
    const randomIndex = Math.floor(Math.random() * AURORA_PALETTES.length);
    setCurrentAurora(AURORA_PALETTES[randomIndex]);
  }, [user]);

  // ==========================================
  // 핸들러 함수 (Event Handlers)
  // ==========================================
  
  // 시스템 로그 기록 함수
  const addLog = (logMessage) => {
    const timeString = new Date().toLocaleTimeString();
    const newLogItem = {
      id: Date.now(),
      text: logMessage,
      time: timeString,
    };
    setLogs((prevLogs) => [newLogItem, ...prevLogs]);
  };

  // 어드민 직접 등록 핸들러 (ID 또는 @이름)
  const handleAssignAdmin = () => {
    if (!adminInput.trim()) {
      alert('디스코드 ID 또는 @이름을 입력해 주세요.');
      return;
    }

    const trimmedValue = adminInput.trim();

    if (trimmedValue.startsWith('@')) {
      const targetUsername = trimmedValue.substring(1);
      addLog(`[어드민 권한 부여] 유저 닉네임 검색 요청: @${targetUsername}`);
      alert(`'@${targetUsername}' 유저를 검색하여 어드민 권한을 부여했습니다.`);
    } else {
      addLog(`[어드민 권한 부여] 디스코드 고유 ID 직접 등록: ${trimmedValue}`);
      alert(`ID [${trimmedValue}] 사용자에게 어드민 권한을 부여했습니다.`);
    }

    setAdminInput('');
  };

  // 매뉴얼 카드에서 수정 버튼 클릭 시 핸들러
  const handleSelectEditManual = (manualItem) => {
    setEditManual({
      id: manualItem.id,
      category: manualItem.category,
      title: manualItem.title,
      content: manualItem.content,
      pinned: manualItem.pinned,
    });

    // 수정 폼 위치로 스무스 스크롤 이동
    const editorSection = document.getElementById('manual-editor-section');
    if (editorSection) {
      editorSection.scrollIntoView({ behavior: 'smooth' });
    }
  };

  // 폼 초기화 핸들러
  const handleResetForm = () => {
    setEditManual({
      id: null,
      category: '',
      title: '',
      content: '',
      pinned: false,
    });
  };

  // 매뉴얼 저장 및 수정 완료 핸들러
  const handleSaveManual = () => {
    if (!editManual.title.trim() || !editManual.content.trim()) {
      alert('매뉴얼 제목과 내용을 모두 입력해 주세요.');
      return;
    }

    if (editManual.id !== null) {
      // 기존 매뉴얼 수정 로직
      setManuals((prevList) =>
        prevList.map((item) =>
          item.id === editManual.id ? { ...editManual } : item
        )
      );
      addLog(`[매뉴얼 수정] '${editManual.title}' 매뉴얼 정보 업데이트 완료`);
      alert('매뉴얼 수정이 완료되었습니다.');
    } else {
      // 신규 매뉴얼 생성 로직
      const newManualData = {
        ...editManual,
        id: Date.now(),
      };
      setManuals((prevList) => [newManualData, ...prevList]);
      addLog(`[매뉴얼 신규 작성] '${editManual.title}' 새 매뉴얼 추가 완료`);
      alert('새 매뉴얼이 성공적으로 등록되었습니다.');
    }

    handleResetForm();
  };

  // ==========================================
  // 렌더링 (UI Layout)
  // ==========================================
  return (
    <div style={containerStyle}>
      {/* 1. 최상단 헤더 영역 */}
      <header style={headerBarStyle}>
        <h1 style={headerTitleStyle}>Sky Aurora Staff Manual</h1>
        <span style={headerSubTitleStyle}>
          Control & Documentation Management System
        </span>
      </header>

      {/* 2. 접속자 환영 및 오로라 링 애니메이션 카운터 */}
      <div style={welcomeCardStyle}>
        <div
          style={{
            ...auroraRingStyle,
            background: currentAurora,
          }}
        />
        <div style={welcomeTextStyle}>
          <h2 style={{ margin: '0px', fontSize: '20px', fontWeight: '600' }}>
            반갑습니다, {user.name}님
          </h2>
          <p
            style={{
              margin: '4px 0px 0px 0px',
              color: '#94a3b8',
              fontSize: '13px',
            }}
          >
            접속 권한 계급:{' '}
            <span
              style={{
                color: user.role === 'ADMIN' ? '#38bdf8' : '#facc15',
                fontWeight: 'bold',
              }}
            >
              {user.role}
            </span>
          </p>
        </div>
      </div>

      {/* 3. 어드민 전용 - 어드민 승급 및 권한 등록 폼 */}
      {user.role === 'ADMIN' && (
        <section style={cardSectionStyle}>
          <h3 style={sectionTitleStyle}>⚙️ 어드민 승급 및 권한 부여</h3>
          <p
            style={{
              color: '#94a3b8',
              fontSize: '13px',
              marginTop: '0px',
              marginBottom: '12px',
            }}
          >
            디스코드 고유 ID(숫자)를 직접 입력하거나 <strong>@유저이름</strong>
            을 입력하여 어드민 권한을 부여합니다.
          </p>
          <div style={{ display: 'flex', gap: '8px', width: '100%' }}>
            <input
              type="text"
              placeholder="예: 123456789012345678 또는 @유저이름"
              value={adminInput}
              onChange={(e) => setAdminInput(e.target.value)}
              style={inputFieldStyle}
            />
            <button style={btnSuccessStyle} onClick={handleAssignAdmin}>
              어드민 등록
            </button>
          </div>
        </section>
      )}

      {/* 4. 등록된 매뉴얼 리스트 영역 */}
      <section style={{ marginTop: '28px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '12px',
          }}
        >
          <h3 style={{ margin: '0px', fontSize: '18px', fontWeight: '600' }}>
            📖 매뉴얼 목록
          </h3>
          <button style={btnSecondaryStyle} onClick={handleResetForm}>
            + 새 매뉴얼 작성
          </button>
        </div>

        <div style={{ display: 'grid', gap: '12px', width: '100%' }}>
          {manuals.map((manualItem) => (
            <div key={manualItem.id} style={manualCardStyle}>
              <div style={{ flex: 1, marginRight: '16px' }}>
                <div
                  style={{
                    display: 'flex',
                    gap: '6px',
                    marginBottom: '6px',
                    alignItems: 'center',
                  }}
                >
                  {manualItem.category && (
                    <span style={badgeStyle}>{manualItem.category}</span>
                  )}
                  {manualItem.pinned && (
                    <span style={pinBadgeStyle}>📌 상단 고정</span>
                  )}
                </div>
                <h4
                  style={{
                    margin: '0px 0px 6px 0px',
                    fontSize: '16px',
                    fontWeight: '600',
                  }}
                >
                  {manualItem.title}
                </h4>
                <p
                  style={{
                    margin: '0px',
                    color: '#94a3b8',
                    fontSize: '13px',
                    lineHeight: '1.4',
                  }}
                >
                  {manualItem.content}
                </p>
              </div>
              <button
                style={btnSecondaryStyle}
                onClick={() => handleSelectEditManual(manualItem)}
              >
                ✏️ 수정
              </button>
            </div>
          ))}
        </div>
      </section>

      {/* 5. 매뉴얼 에디터 폼 영역 (수정 시 이 위치로 스크롤) */}
      <section
        id="manual-editor-section"
        style={{ ...cardSectionStyle, marginTop: '28px' }}
      >
        <h3 style={sectionTitleStyle}>
          {editManual.id !== null ? '✏️ 매뉴얼 수정' : '📝 새 매뉴얼 작성'}
        </h3>

        <div style={{ display: 'grid', gap: '10px', width: '100%' }}>
          <div style={{ display: 'flex', gap: '8px', width: '100%' }}>
            <input
              type="text"
              placeholder="주제(카테고리) 예: 운항 지침, 공통 매뉴얼"
              value={editManual.category}
              onChange={(e) =>
                setEditManual({ ...editManual, category: e.target.value })
              }
              style={{ ...inputFieldStyle, flex: 1 }}
            />
            <label style={checkboxLabelStyle}>
              <input
                type="checkbox"
                checked={editManual.pinned}
                onChange={(e) =>
                  setEditManual({ ...editManual, pinned: e.target.checked })
                }
                style={{ cursor: 'pointer' }}
              />
              📌 상단 고정
            </label>
          </div>

          <input
            type="text"
            placeholder="매뉴얼 제목을 입력하세요"
            value={editManual.title}
            onChange={(e) =>
              setEditManual({ ...editManual, title: e.target.value })
            }
            style={inputFieldStyle}
          />

          <textarea
            placeholder="매뉴얼 상세 내용을 입력하세요"
            value={editManual.content}
            onChange={(e) =>
              setEditManual({ ...editManual, content: e.target.value })
            }
            style={{
              ...inputFieldStyle,
              height: '120px',
              resize: 'vertical',
              fontFamily: 'inherit',
            }}
          />

          <div
            style={{
              display: 'flex',
              gap: '8px',
              justifyContent: 'flex-end',
              marginTop: '4px',
            }}
          >
            {editManual.id !== null && (
              <button style={btnSecondaryStyle} onClick={handleResetForm}>
                취소
              </button>
            )}
            <button style={btnPrimaryStyle} onClick={handleSaveManual}>
              {editManual.id !== null ? '수정사항 저장' : '새 매뉴얼 등록'}
            </button>
          </div>
        </div>
      </section>

      {/* 6. 처리 로그 확인 창 */}
      {logs.length > 0 && (
        <section
          style={{
            ...cardSectionStyle,
            marginTop: '28px',
            backgroundColor: '#090d16',
            borderColor: '#1e293b',
          }}
        >
          <h4
            style={{
              margin: '0px 0px 8px 0px',
              color: '#64748b',
              fontSize: '13px',
              fontWeight: '500',
            }}
          >
            📋 실시간 처리 로그
          </h4>
          <div
            style={{
              fontSize: '12px',
              fontFamily: 'monospace',
              color: '#38bdf8',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
            }}
          >
            {logs.map((logItem) => (
              <div key={logItem.id}>
                [{logItem.time}] {logItem.text}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* CSS 키프레임 애니메이션 */}
      <style>{`
        @keyframes auroraPulse {
          0% {
            transform: scale(1);
            box-shadow: 0 0 8px rgba(255, 255, 255, 0.2);
          }
          50% {
            transform: scale(1.2);
            box-shadow: 0 0 24px rgba(255, 255, 255, 0.6);
          }
          100% {
            transform: scale(1);
            box-shadow: 0 0 8px rgba(255, 255, 255, 0.2);
          }
        }
      `}</style>
    </div>
  );
}

// ==========================================
// 상세 개별 인라인 스타일 객체 (Detailed Styles)
// ==========================================
const containerStyle = {
  backgroundColor: '#0f172a',
  color: '#f8fafc',
  minHeight: '100vh',
  paddingTop: '24px',
  paddingBottom: '24px',
  paddingLeft: '24px',
  paddingRight: '24px',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  maxWidth: '900px',
  marginLeft: 'auto',
  marginRight: 'auto',
  boxSizing: 'border-box',
};

const headerBarStyle = {
  borderBottomWidth: '1px',
  borderBottomStyle: 'solid',
  borderBottomColor: '#334155',
  paddingBottom: '12px',
  marginBottom: '20px',
};

const headerTitleStyle = {
  marginTop: '0px',
  marginBottom: '0px',
  fontSize: '24px',
  color: '#38bdf8',
  fontWeight: 'bold',
};

const headerSubTitleStyle = {
  fontSize: '12px',
  color: '#64748b',
};

const welcomeCardStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '16px',
  paddingTop: '16px',
  paddingBottom: '16px',
  paddingLeft: '20px',
  paddingRight: '20px',
  backgroundColor: '#1e293b',
  borderRadius: '12px',
  borderWidth: '1px',
  borderStyle: 'solid',
  borderColor: '#334155',
};

const auroraRingStyle = {
  width: '40px',
  height: '40px',
  borderRadius: '50%',
  animation: 'auroraPulse 3s infinite ease-in-out',
  flexShrink: 0,
};

const welcomeTextStyle = {
  display: 'flex',
  flexDirection: 'column',
};

const cardSectionStyle = {
  backgroundColor: '#1e293b',
  paddingTop: '20px',
  paddingBottom: '20px',
  paddingLeft: '20px',
  paddingRight: '20px',
  borderRadius: '12px',
  borderWidth: '1px',
  borderStyle: 'solid',
  borderColor: '#334155',
};

const sectionTitleStyle = {
  marginTop: '0px',
  marginBottom: '12px',
  fontSize: '16px',
  fontWeight: '600',
};

const manualCardStyle = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  paddingTop: '16px',
  paddingBottom: '16px',
  paddingLeft: '16px',
  paddingRight: '16px',
  backgroundColor: '#1e293b',
  borderRadius: '10px',
  borderWidth: '1px',
  borderStyle: 'solid',
  borderColor: '#334155',
};

const badgeStyle = {
  backgroundColor: '#0284c7',
  fontSize: '11px',
  paddingTop: '2px',
  paddingBottom: '2px',
  paddingLeft: '6px',
  paddingRight: '6px',
  borderRadius: '4px',
  color: '#ffffff',
  fontWeight: '500',
};

const pinBadgeStyle = {
  backgroundColor: '#dc2626',
  fontSize: '11px',
  paddingTop: '2px',
  paddingBottom: '2px',
  paddingLeft: '6px',
  paddingRight: '6px',
  borderRadius: '4px',
  color: '#ffffff',
  fontWeight: '500',
};

const inputFieldStyle = {
  paddingTop: '10px',
  paddingBottom: '10px',
  paddingLeft: '12px',
  paddingRight: '12px',
  backgroundColor: '#0f172a',
  borderWidth: '1px',
  borderStyle: 'solid',
  borderColor: '#334155',
  color: '#ffffff',
  borderRadius: '6px',
  fontSize: '14px',
  boxSizing: 'border-box',
  outline: 'none',
  width: '100%',
};

const checkboxLabelStyle = {
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  backgroundColor: '#0f172a',
  borderWidth: '1px',
  borderStyle: 'solid',
  borderColor: '#334155',
  paddingLeft: '12px',
  paddingRight: '12px',
  borderRadius: '6px',
  fontSize: '13px',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
};

const btnPrimaryStyle = {
  backgroundColor: '#0284c7',
  color: '#ffffff',
  border: 'none',
  paddingTop: '10px',
  paddingBottom: '10px',
  paddingLeft: '18px',
  paddingRight: '18px',
  borderRadius: '6px',
  cursor: 'pointer',
  fontWeight: 'bold',
  fontSize: '14px',
};

const btnSecondaryStyle = {
  backgroundColor: '#334155',
  color: '#ffffff',
  border: 'none',
  paddingTop: '8px',
  paddingBottom: '8px',
  paddingLeft: '14px',
  paddingRight: '14px',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '13px',
};

const btnSuccessStyle = {
  backgroundColor: '#16a34a',
  color: '#ffffff',
  border: 'none',
  paddingTop: '10px',
  paddingBottom: '10px',
  paddingLeft: '18px',
  paddingRight: '18px',
  borderRadius: '6px',
  cursor: 'pointer',
  whiteSpace: 'nowrap',
  fontWeight: 'bold',
  fontSize: '14px',
};
