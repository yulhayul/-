import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import time

# =====================================================================
# 1. 터미널 및 UI 기본 설정 (한국어 HMI 테마)
# =====================================================================
st.set_page_config(
    page_title="FAB 공정 제어 HMI 시뮬레이터",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0e1117; font-family: 'Malgun Gothic', sans-serif; }
    
    /* 터미널 로그창 스타일 */
    .terminal-box {
        background-color: #000000;
        border: 2px solid #333;
        border-radius: 5px;
        padding: 15px;
        height: 400px;
        overflow-y: auto;
        color: #00ff00;
        font-family: 'Courier New', monospace;
        font-size: 15px;
        line-height: 1.6;
        box-shadow: inset 0 0 10px #000;
    }
    
    h1, h2, h3 { color: #00ff00 !important; }
    .st-emotion-cache-1v0mbdj > img { border-radius: 50%; border: 2px solid #555; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. 공정별 웨이퍼 상태 및 결함 생성 엔진
# =====================================================================
size = 300
x, y = np.meshgrid(np.linspace(-1, 1, size), np.linspace(-1, 1, size))
R = np.sqrt(x**2 + y**2)
theta = np.arctan2(y, x)
notch = (R > 0.96) & (np.abs(theta + np.pi/2) < 0.05)
wafer_mask = (R <= 1.0) & ~notch

def get_base_wafer(step):
    """각 공정 단계(step)별로 웨이퍼의 정상적인 외형 변화를 수학적으로 렌더링"""
    base = np.zeros((size, size))
    
    if step >= 1: # 웨이퍼 제조 (기본 실리콘)
        base += 0.5 
    if step >= 2: # 산화 공정 (산화막 생성으로 인한 톤 변화)
        base += gaussian_filter(np.random.rand(size, size), sigma=20) * 0.1 - 0.1
    if step >= 3: # 포토 공정 (미세 격자 패턴 생성)
        grid = (np.abs(x * 30) % 1 < 0.1) | (np.abs(y * 30) % 1 < 0.1)
        base = np.where(grid, base + 0.2, base)
    if step >= 4: # 식각 공정 (패턴의 깊이감이 생김)
        grid_deep = (np.abs(x * 30) % 1 < 0.2) | (np.abs(y * 30) % 1 < 0.2)
        base = np.where(grid_deep, base - 0.1, base)
    if step >= 5: # 박막 증착 (금속성 광택 느낌 추가)
        base += 0.2 
    if step >= 6: # CMP 연마 (표면이 부드러워짐)
        base = gaussian_filter(base, sigma=0.5)
    if step >= 7: # EDS 테스트 (프로브 핀 접촉 자국)
        dots = (np.abs(x * 30) % 1 < 0.05) & (np.abs(y * 30) % 1 < 0.05)
        base = np.where(dots, 1.0, base)
    if step >= 8: # 패키징 (다이싱 쏘로 칩 분리)
        cut_lines = (np.abs(x * 30) % 1 < 0.03) | (np.abs(y * 30) % 1 < 0.03)
        base = np.where(cut_lines, 0.0, base) # 선을 까맣게 자름
        
    return base

def get_defect_pattern(defect_type):
    """설정값이 어긋났을 때 누적될 특정 불량 패턴 반환"""
    defect = np.zeros((size, size))
    if defect_type == "Defocus": # 평탄도 불량 파도 패턴
        defect = np.sin(x*15) * np.cos(y*15) * 0.3
    elif defect_type == "Center": # 튜브 온도 중앙 집중
        defect = np.exp(-(R**2) / 0.1) * 0.7
    elif defect_type == "Random": # EUV 샷 노이즈
        defect = (np.random.rand(size, size) > 0.98).astype(float) * 0.8
    elif defect_type == "Ring": # ICP 플라즈마 쏠림
        defect = np.exp(-((R - 0.9)**2) / 0.005) * 0.9
    elif defect_type == "Donut": # 가스 유량 퍼짐 불량
        defect = np.exp(-((R - 0.5)**2) / 0.02) * 0.6
    elif defect_type == "Scratch": # CMP 하드패드 긁힘
        dist = np.abs(x - y) / np.sqrt(2)
        defect = np.exp(-(dist**2) / 0.0001) * 0.8 * np.random.choice([0,1], (size,size), p=[0.2, 0.8])
    elif defect_type == "ProbeMark": # 핀 하중 과다 파임
        defect = (np.cos(x * 60)**2 * np.cos(y * 60)**2 > 0.8).astype(float) * 0.8
    elif defect_type == "EdgeChipping": # 톱날 깨짐
        defect = (R > 0.94).astype(float) * (np.random.rand(size, size) > 0.6).astype(float) * 1.0
    return defect

# =====================================================================
# 3. 메인 인터페이스 및 기계 상태 (Session State)
# =====================================================================
if 'sys_power' not in st.session_state: st.session_state.sys_power = False
if 'vac_pump' not in st.session_state: st.session_state.vac_pump = False

st.markdown("## 🏭 [SYS-01] 반도체 8대 공정 통합 제어 패널 (HMI)")
st.markdown("왼쪽 제어판에서 전원을 켜고 파라미터를 설정한 뒤, 시뮬레이션을 가동하여 웨이퍼의 실시간 변화를 관찰하십시오.")
st.divider()

col_hw, col_visual, col_log = st.columns([1, 1.2, 1.2])

# ---------------------------------------------------------------------
# [패널 1] 하드웨어 제어 및 파라미터 조작부 (사이드바 대체)
# ---------------------------------------------------------------------
with col_hw:
    st.markdown("### 🔌 기계 전원 제어")
    pwr_btn = "🔴 주 전원 차단 (POWER OFF)" if st.session_state.sys_power else "🟢 주 전원 가동 (POWER ON)"
    if st.button(pwr_btn, use_container_width=True):
        st.session_state.sys_power = not st.session_state.sys_power
        st.rerun()
        
    vac_btn = "🔴 진공 펌프 정지 (PUMP OFF)" if st.session_state.vac_pump else "🟢 진공 펌프 가동 (PUMP ON)"
    if st.button(vac_btn, use_container_width=True):
        st.session_state.vac_pump = not st.session_state.vac_pump
        st.rerun()

    st.markdown("---")
    st.markdown("### 🎛️ 8대 공정 파라미터 설정")
    
    if not (st.session_state.sys_power and st.session_state.vac_pump):
        st.error("⚠️ 인터락(Interlock) 발동: 주 전원과 진공 펌프를 모두 가동해야 공정 레시피를 수정할 수 있습니다.")
        params = None
    else:
        # 8가지 핵심 공정 파라미터를 아코디언 메뉴로 설계
        params = {}
        with st.expander("1. 웨이퍼 제조 (Wafer Mfg)"):
            params['ttv'] = st.slider("웨이퍼 평탄도 (TTV, µm)", 0.5, 3.0, 1.0, step=0.1)
        with st.expander("2. 산화 공정 (Oxidation)"):
            params['oxi_eq'] = st.selectbox("산화 설비", ["Furnace (대용량 배치형)", "RTP (급속열처리)"])
            params['oxi_temp'] = st.slider("챔버 온도 (℃)", 800, 1200, 1000, step=10)
        with st.expander("3. 포토 공정 (Photo)"):
            params['photo_eq'] = st.selectbox("노광 설비", ["ASML EUV (극자외선)", "ArF Immersion (액침)"])
            params['dose'] = st.slider("노광량 Dose (mJ/cm²)", 10, 60, 30, step=2)
        with st.expander("4. 식각 공정 (Etch)"):
            params['etch_eq'] = st.selectbox("플라즈마 소스", ["ICP (유도결합형)", "CCP (용량결합형)"])
            params['rf_power'] = st.slider("RF 플라즈마 파워 (W)", 200, 800, 400, step=10)
        with st.expander("5. 박막 증착 (Deposition)"):
            params['gas_flow'] = st.slider("반응 가스 유량 (sccm)", 20, 100, 50, step=5)
        with st.expander("6. 연마 공정 (CMP)"):
            params['pressure'] = st.slider("패드 누름 압력 (psi)", 1.0, 8.0, 3.0, step=0.5)
        with st.expander("7. EDS 검사 (Wafer Test)"):
            params['probe_force'] = st.slider("프로브 핀 하중 (g)", 1.0, 5.0, 2.0, step=0.2)
        with st.expander("8. 패키징 (Dicing)"):
            params['dicing_spd'] = st.slider("블레이드 절단 속도 (mm/s)", 30, 90, 50, step=5)

        run_btn = st.button("▶️ 전체 공정 연속 실행 (RUN)", type="primary", use_container_width=True)

# ---------------------------------------------------------------------
# [패널 2 & 3] 실시간 웨이퍼 시각화 & 터미널 로그
# ---------------------------------------------------------------------
with col_visual:
    st.markdown("### 📡 실시간 인라인 계측 (Wafer Map)")
    wafer_placeholder = st.empty() # 애니메이션을 위한 빈 컨테이너

with col_log:
    st.markdown("### 🖥️ FDC 터미널 로그")
    terminal_placeholder = st.empty()

# 초기 화면 렌더링 (빈 상태)
if 'logs' not in st.session_state: 
    st.session_state.logs = ["[SYSTEM] HMI 인터페이스 부팅 완료. 시스템 대기 중..."]
    
def render_terminal():
    log_html = "<br>".join(st.session_state.logs[-18:])
    terminal_placeholder.markdown(f"<div class='terminal-box'>{log_html}</div>", unsafe_allow_html=True)

render_terminal()
wafer_placeholder.info("전원을 켜고 공정을 실행하면 웨이퍼의 변화가 실시간으로 표시됩니다.")

# =====================================================================
# 4. 시퀀스 실행 로직 (애니메이션 및 결함 판정)
# =====================================================================
if params is not None and run_btn:
    st.session_state.logs = ["[SYSTEM] 8대 공정 자동화 시퀀스 가동을 시작합니다..."]
    
    # 컬러맵 정의 (공정 진행에 따라 색상이 바뀜)
    step_cmaps = ['bone', 'bone', 'ocean', 'viridis', 'magma', 'copper', 'gray', 'gray', 'bone']
    
    # 누적 결함 맵
    cumulative_defects = np.zeros((size, size))
    
    for step in range(1, 9):
        # 1. 단계별 로그 작성 및 결함 체크
        defect_this_step = None
        
        if step == 1:
            st.session_state.logs.append("▶ [STEP 1] 웨이퍼(Wafer) 잉곳 절단 및 폴리싱 진행 중...")
            if params['ttv'] > 1.8:
                defect_this_step = "Defocus"
                st.session_state.logs.append(f"<span style='color:red;'>[경고] 평탄도(TTV) {params['ttv']}µm 과다. 웨이퍼 표면 굴곡 발생.</span>")
                
        elif step == 2:
            st.session_state.logs.append(f"▶ [STEP 2] 산화(Oxidation) 공정 시작. 설비: {params['oxi_eq']}")
            if "Furnace" in params['oxi_eq'] and params['oxi_temp'] > 1050:
                defect_this_step = "Center"
                st.session_state.logs.append(f"<span style='color:red;'>[경고] Furnace 챔버 온도 {params['oxi_temp']}℃ 과열. 중앙부 산화막 두께 변형.</span>")
                
        elif step == 3:
            st.session_state.logs.append(f"▶ [STEP 3] 포토(Photo) 노광 공정 시작. 설비: {params['photo_eq']}")
            if "EUV" in params['photo_eq'] and params['dose'] < 25:
                defect_this_step = "Random"
                st.session_state.logs.append(f"<span style='color:red;'>[경고] EUV Dose {params['dose']} 부족. 샷 노이즈(Shot Noise)로 패턴 끊어짐.</span>")
                
        elif step == 4:
            st.session_state.logs.append(f"▶ [STEP 4] 식각(Etch) 공정 시작. 설비: {params['etch_eq']}")
            if "ICP" in params['etch_eq'] and params['rf_power'] > 500:
                defect_this_step = "Ring"
                st.session_state.logs.append(f"<span style='color:red;'>[경고] ICP RF 파워 {params['rf_power']}W 과다. 엣지(Edge) 플라즈마 집중.</span>")
                
        elif step == 5:
            st.session_state.logs.append(f"▶ [STEP 5] 박막(Deposition) 증착 시작. 가스 주입 중...")
            if params['gas_flow'] > 70:
                defect_this_step = "Donut"
                st.session_state.logs.append(f"<span style='color:red;'>[경고] 반응 가스 유량 {params['gas_flow']}sccm 과다. 도넛 형태 박막 뭉침.</span>")
                
        elif step == 6:
            st.session_state.logs.append(f"▶ [STEP 6] CMP 연마 공정 시작. 패드 압력 인가 중...")
            if params['pressure'] > 4.5:
                defect_this_step = "Scratch"
                st.session_state.logs.append(f"<span style='color:red;'>[경고] 연마 압력 {params['pressure']}psi 과다. 마이크로 스크래치(Scratch) 발생.</span>")
                
        elif step == 7:
            st.session_state.logs.append(f"▶ [STEP 7] EDS 전기적 특성 검사 진행 중...")
            if params['probe_force'] > 3.0:
                defect_this_step = "ProbeMark"
                st.session_state.logs.append(f"<span style='color:red;'>[경고] 프로브 핀 하중 {params['probe_force']}g 초과. 패드 물리적 손상.</span>")
                
        elif step == 8:
            st.session_state.logs.append(f"▶ [STEP 8] 패키징(Packaging) 다이싱 절단 진행 중...")
            if params['dicing_spd'] > 65:
                defect_this_step = "EdgeChipping"
                st.session_state.logs.append(f"<span style='color:red;'>[경고] 톱날 속도 {params['dicing_spd']}mm/s 과속. 칩 가장자리 깨짐(Chipping) 발생.</span>")
        
        render_terminal()
        
        # 2. 웨이퍼 시각화 업데이트
        if defect_this_step:
            cumulative_defects += get_defect_pattern(defect_this_step)
            
        current_wafer = get_base_wafer(step) + cumulative_defects
        current_wafer[~wafer_mask] = np.nan
        
        fig, ax = plt.subplots(figsize=(6, 6), facecolor='black')
        ax.set_facecolor('black')
        
        # 공정 진행에 따라 컬러맵 변경 (결함은 빨간색으로 오버레이 되도록 turbo 사용)
        cmap = plt.cm.get_cmap(step_cmaps[step]) if np.max(cumulative_defects) == 0 else plt.cm.turbo
        cmap.set_bad(color='black')
        
        ax.imshow(current_wafer, cmap=cmap, interpolation='none', vmin=-0.2, vmax=1.5)
        
        # HMI 스캔 라인 이펙트
        ax.axhline(y=150, color='lime', linewidth=1, alpha=0.3, linestyle='--')
        ax.axvline(x=150, color='lime', linewidth=1, alpha=0.3, linestyle='--')
        ax.axis('off')
        
        # 스트림릿 컨테이너에 플롯 덮어쓰기 (애니메이션 효과)
        wafer_placeholder.pyplot(fig)
        plt.close(fig) # 메모리 누수 방지
        
        # 시각적 변화를 느낄 수 있도록 1.5초 대기
        time.sleep(1.5)

    # 전체 완료 로그
    if np.max(cumulative_defects) == 0:
        st.session_state.logs.append("<span style='color:#00ff00;'>[SYSTEM] ✅ 전 공정 완벽 수행 (Golden Yield). 스마트폰 AP 실장 준비 완료.</span>")
    else:
        st.session_state.logs.append("<span style='color:red;'>[SYSTEM] 🚨 수율 저하 감지. 누적된 결함으로 인해 최종 칩 테스트 불합격 가능성이 높습니다.</span>")
    render_terminal()
