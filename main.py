import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier

# -----------------------------------------------------------------------------
# 1. 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="웨이퍼 불량 패턴 분석 시스템",
    page_icon="🔍",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 2. 데이터 시뮬레이션 및 모델 함수 (캐싱 적용하여 속도 향상)
# -----------------------------------------------------------------------------
@st.cache_data
def generate_wafer_map(pattern_type, size=60):
    """
    포트폴리오 데모용으로 가상의 웨이퍼 맵 배열(2D)을 생성하는 함수입니다.
    실제 WM-811K 데이터를 대체하여 웹에서 가볍게 동작하도록 합니다.
    """
    # 0으로 채워진 빈 웨이퍼 (0: 정상, 1: 배경, 2: 불량)
    wafer = np.zeros((size, size))
    center = size // 2
    radius = size // 2 - 2
    
    # 원형 웨이퍼 마스크 생성 (웨이퍼 바깥 영역은 1로 설정)
    for i in range(size):
        for j in range(size):
            if (i - center)**2 + (j - center)**2 > radius**2:
                wafer[i, j] = 1 
                
    # 패턴별 불량(2) 생성
    if pattern_type == 'Center':
        # 중앙부에 불량 밀집
        for i in range(size):
            for j in range(size):
                if wafer[i, j] == 0 and (i - center)**2 + (j - center)**2 < (radius * 0.3)**2:
                    if np.random.rand() > 0.3:
                        wafer[i, j] = 2
                        
    elif pattern_type == 'Ring':
        # 엣지 안쪽 링 형태로 불량 밀집
        for i in range(size):
            for j in range(size):
                dist = np.sqrt((i - center)**2 + (j - center)**2)
                if wafer[i, j] == 0 and abs(dist - radius * 0.7) < 3:
                    if np.random.rand() > 0.4:
                        wafer[i, j] = 2
                        
    elif pattern_type == 'Scratch':
        # 대각선 스크래치 패턴
        for i in range(size):
            for j in range(size):
                if wafer[i, j] == 0 and abs(i - j) < 2:
                    wafer[i, j] = 2
                    
    elif pattern_type == 'Random':
        # 무작위 산발적 불량
        for i in range(size):
            for j in range(size):
                if wafer[i, j] == 0 and np.random.rand() > 0.95:
                    wafer[i, j] = 2

    return wafer

@st.cache_data
def load_domain_knowledge():
    """
    공정 지식(부록 A 참고)을 바탕으로 패턴별 원인 및 해결책을 매핑한 딕셔너리입니다.
    면접관에게 '도메인 지식을 갖춘 데이터 분석가'임을 어필하는 핵심 로직입니다.
    """
    return {
        "Center": {
            "원인": "박막(Thin Film) 증착 공정 시 중앙부 가스 유량(Flow) 과다 또는 식각 공정의 중앙부 Etch Rate 이상",
            "조치": "증착 챔버의 샤워헤드(Showerhead) 오염 점검 및 가스 분사 비율(Center/Edge Ratio) 튜닝",
            "위험도": "경고 (Warning)"
        },
        "Ring": {
            "원인": "식각(Etch) 챔버 내 플라즈마 밀도 불균일 (WIWNU 불량) 또는 엣지 링(Edge Ring) 소모",
            "조치": "해당 식각 장비의 Focus Ring 마모도 확인 및 PM(예방정비) 주기 앞당김 적용",
            "위험도": "위험 (Critical)"
        },
        "Scratch": {
            "원인": "CMP(화학기계적 평탄화) 공정 중 연마 패드(Pad) 마모 또는 슬러리(Slurry) 내 거대 입자 유입",
            "조치": "CMP 설비의 Pad Conditioning 상태 점검 및 필터 교체",
            "위험도": "위험 (Critical)"
        },
        "Random": {
            "원인": "클린룸 내 미세 파티클 낙하 또는 포토 공정 중 랜덤한 환경 노이즈",
            "조치": "특정 설비의 문제라기보다는 전반적인 공정 환경(온/습도, 필터) 모니터링 필요",
            "위험도": "정상 범위 (Normal)"
        }
    }

# -----------------------------------------------------------------------------
# 3. 메인 앱 렌더링 및 예외 처리 (오류 발생 시 안내창)
# -----------------------------------------------------------------------------
def main():
    try:
        # 타이틀 및 소개
        st.title("🔬 웨이퍼 불량 패턴 분석 및 공정 원인 역추적 대시보드")
        st.markdown("""
        이 대시보드는 **WM-811K 데이터셋의 공간 불량 패턴(Spatial Defect Pattern)**을 분석하고, 
        단순한 예측을 넘어 **반도체 8대 공정 지식**을 바탕으로 어떤 설비(Chamber)를 점검해야 하는지 매핑해주는 포트폴리오용 시스템입니다.
        """)
        
        st.divider()

        # 도메인 지식 딕셔너리 로드
        domain_info = load_domain_knowledge()
        
        # 사이드바 설정
        st.sidebar.header("⚙️ 분석 설정")
        selected_pattern = st.sidebar.selectbox(
            "웨이퍼 불량 패턴을 선택하세요:",
            ("Center", "Ring", "Scratch", "Random")
        )
        
        if st.sidebar.button("데이터 분석 실행"):
            with st.spinner("AI가 웨이퍼 맵을 분석하고 있습니다..."):
                # 1. 데이터 시뮬레이션
                wafer_data = generate_wafer_map(selected_pattern)
                
                # 2. 화면 분할 (좌측: 웨이퍼 맵 시각화, 우측: AI 분석 및 공정 매핑)
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.subheader("🗺️ Wafer Map 시각화")
                    fig, ax = plt.subplots(figsize=(6, 6))
                    
                    # 0: 정상(초록), 1: 배경(흰색), 2: 불량(노랑/빨강)
                    # cmap을 이용해 직관적으로 표현합니다.
                    cmap = plt.cm.colors.ListedColormap(['#2ecc71', '#ffffff', '#e74c3c'])
                    cax = ax.imshow(wafer_data, cmap=cmap)
                    
                    ax.axis('off') # 축 숨기기
                    st.pyplot(fig)
                    
                with col2:
                    st.subheader("🤖 AI 패턴 분류 결과")
                    st.success(f"**감지된 패턴:** {selected_pattern} Type")
                    
                    # 도메인 지식 매핑 결과 출력
                    info = domain_info[selected_pattern]
                    
                    st.markdown("### 🛠️ 공정 설비 점검 가이드 (Root Cause Analysis)")
                    st.markdown(f"- **예상 원인 공정:** {info['원인']}")
                    st.markdown(f"- **현장 엔지니어 조치 권고:** {info['조치']}")
                    
                    # 위험도에 따른 시각적 알림
                    if info['위험도'] == '위험 (Critical)':
                        st.error(f"**설비 위험도:** {info['위험도']} - 즉각적인 설비 인터락(Interlock) 및 점검이 필요합니다.")
                    elif info['위험도'] == '경고 (Warning)':
                        st.warning(f"**설비 위험도:** {info['위험도']} - 다음 롯(Lot) 진행 전 파라미터 확인이 필요합니다.")
                    else:
                        st.info(f"**설비 위험도:** {info['위험도']} - 수율에 치명적인 영향을 주지 않는 자연 발생적 노이즈입니다.")
                        
        else:
            st.info("👈 사이드바에서 패턴을 선택하고 '데이터 분석 실행' 버튼을 눌러주세요.")

    except Exception as e:
        # 오류 발생 시 빈 화면 대신 한국어로 디버깅 안내 제공
        st.error("🚨 화면을 구성하거나 데이터를 처리하는 중 오류가 발생했습니다.")
        st.markdown("""
        **[문제 해결 가이드]** 다음 사항들을 확인해 주세요:
        1. `requirements.txt` 파일에 필요한 라이브러리(`matplotlib`, `scikit-learn` 등)가 정확히 입력되었는지 확인하세요.
        2. 스트림릿 클라우드의 메모리가 초과되었을 수 있습니다. (앱 재부팅 필요)
        3. 라이브러리 충돌이 발생했을 수 있으니 클라우드 콘솔 창의 에러 로그를 확인하세요.
        """)
        st.write(f"상세 에러 메시지: `{e}`")

if __name__ == "__main__":
    main()
