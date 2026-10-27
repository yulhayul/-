import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import time

# =====================================================================
# 1. HMI 테마 설정 및 CSS (한국어)
# =====================================================================
st.set_page_config(page_title="FAB 공정 제어 HMI", page_icon="🖥️", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; font-family: 'Malgun Gothic', sans-serif; }
    .terminal-box {
        background-color: #050505;
        border: 1px solid #333;
        border-radius: 4px;
        padding: 12px;
        height: 380px;
        overflow-y: auto;
        color: #00ff00;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.5;
        box-shadow: inset 0 0 10px #000;
    }
    h1, h2, h3 { color: #00ff00 !important; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. 공정별 웨이퍼 엔진 (최적화 처리)
# =====================================================================
size = 250 # 렌더링 속도 향상을 위해 해상도 최적화
x, y = np.meshgrid(np.linspace(-1, 1, size), np.linspace(-1, 1, size))
R = np.sqrt(x**2 + y**2)
theta = np.arctan2(y, x)
wafer_mask = (R <= 1.0) & ~((R > 0.96) & (np.abs(theta + np.pi/2) < 0.05))

def get_base_wafer(step):
    base = np.zeros((size, size))
    if step >= 1: base += 0.5 
    if step >= 2: base += gaussian_filter(np.random.rand(size, size), sigma=10) * 0.1 - 0.1
    if step >= 3: 
        base = np.where((np.abs(x * 20) % 1 < 0.1) | (np.abs(y * 20) % 1 < 0.1), base + 0.2, base)
    if step >= 4: 
        base = np.where((np.abs(x * 20) % 1 < 0.2) | (np.abs(y * 20) % 1 < 0.2), base - 0.1, base)
    if step >= 5: base += 0.2 
    if step >= 6: base = gaussian_filter(base, sigma=0.5)
    if step >= 7: base = np.where((np.abs(x * 20) % 1 < 0.05) & (np.abs(y * 20) % 1 < 0.05), 1.0, base)
    if step >= 8: base = np.where((np.abs(x * 20) % 1 < 0.03) | (np.abs(y * 20) % 1 < 0.03), 0.0, base)
    return base

def get_defect_pattern(defect_type):
    if defect_type == "Defocus": return np.sin(x*10) * np.cos(y*10) * 0.3
    if defect_type == "Center": return np.exp(-(R**2) / 0.1) * 0.7
    if defect_type == "Random": return (np.random.rand(size, size) > 0.98).astype(float) * 0.8
    if defect_type == "Ring": return np.exp(-((R - 0.9)**2) / 0.005) * 0.9
    if defect_type == "Donut": return np.exp(-((R - 0.5)**2) / 0.02) * 0.6
    if defect_type == "Scratch": return np.exp(-((x-y)**2 / 0.0002)) * 0.8 * np.random.choice([0,1], (size,size), p=[0.2,0.8])
    if defect_type == "ProbeMark": return (np.cos(x*50)**2 * np.cos(y*50)**2 > 0.8).astype(float) * 0.8
    if defect_type == "EdgeChipping": return (R > 0.94).astype(float) * (np.random.rand(size, size) > 0.6).astype(float) * 1.0
    return np.zeros((size, size))

# =====================================================================
# 3. UI 및 인터페이스 구성
# =====================================================================
if 'sys_power' not in st.session_state: st.session_state.sys_power = False
if 'vac_pump' not in st.session_state: st.session_state.vac_pump = False
if 'logs' not in st.session_state: st.session_state.logs = ["[SYSTEM] 시스템 부팅 완료..."]

st.markdown("## 🏭 [SYS-02] 8대 공정 고속 제어 패널 및 불량 감지 시스템")
st.divider()

col_hw, col_visual, col_log = st.columns([1, 1.2, 1.2])

with col_hw:
    st.markdown("### 🔌 시스템 제어")
    if st.button("🔴 주 전원 OFF" if st.session_state.sys_power else "🟢 주 전원 ON", use_container_width=True):
        st.session_state.sys_power = not st.session_state.sys_power
        st.rerun()
    if st.button("🔴 진공 펌프 OFF" if st.session_state.vac_pump else "🟢 진공 펌프 ON", use_container_width=True):
        st.session_state.vac_pump = not st.session_state.vac_pump
        st.rerun()

    st.markdown("### 🎛️ 공정 파라미터 (레시피)")
    if not (st.session_state.sys_power and st.session_state.vac_pump):
        st.error("⚠️ 주 전원 및 진공 펌프를 가동하십시오.")
        params = None
    else:
        params = {}
        # 아코디언 메뉴 단순화
        with st.expander("1. 웨이퍼 & 2. 산화"):
            params['ttv'] = st.slider("웨이퍼 평탄도 (TTV, µm)", 0.5, 3.0, 2.0, step=0.1)
            params['oxi_temp'] = st.slider("산화 챔버 온도 (℃)", 800, 1200, 1000, step=10)
        with st.expander("3. 포토 & 4. 식각"):
            params['dose'] = st.slider("노광량 Dose (mJ/cm²)", 10, 60, 30, step=2)
            params['rf_power'] = st.slider("식각 RF 파워 (W)", 200, 800, 400, step=10)
        with st.expander("5. 증착 & 6. 연마"):
            params['gas_flow'] = st.slider("증착 가스 유량 (sccm)", 20, 100, 50, step=5)
            params['pressure'] = st.slider("연마(CMP) 압력 (psi)", 1.0, 8.0, 3.0, step=0.5)
        with st.expander("7. 테스트 & 8. 패키징"):
            params['probe_force'] = st.slider("프로브 핀 하중 (g)", 1.0, 5.0, 2.0, step=0.2)
            params['dicing_spd'] = st.slider("다이싱 톱날 속도 (mm/s)", 30, 90, 50, step=5)

        run_btn = st.button("▶️ 고속 시퀀스 실행 (MAX 4s)", type="primary", use_container_width=True)

with col_visual:
    st.markdown("### 📡 실시간 Wafer Map")
    wafer_placeholder = st.empty()
    rca_placeholder = st.empty() # 불량 원인 분석 출력용

with col_log:
    st.markdown("### 🖥️ 장비 터미널 로그")
    terminal_placeholder = st.empty()

def render_terminal():
    terminal_placeholder.markdown(f"<div class='terminal-box'>{'<br>'.join(st.session_state.logs[-18:])}</div>", unsafe_allow_html=True)

render_terminal()

# =====================================================================
# 4. 고속 실행 및 불량 원인 추적 (RCA) 로직
# =====================================================================
if params is not None and run_btn:
    st.session_state.logs = ["[SYSTEM] 고속 8대 공정 자동화 시작..."]
    cumulative_defects = np.zeros((size, size))
    rca_report = [] # 불량 원인 분석 데이터를 담을 리스트
    
    for step in range(1, 9):
        defect_this_step = None
        
        # 단계별 파라미터 검사 및 불량 추적 데이터 수집
        if step == 1 and params['ttv'] > 1.8:
            defect_this_step = "Defocus"
            rca_report.append({"step": "1. 웨이퍼 제조", "cause": f"평탄도(TTV) {params['ttv']}µm 과다", "effect": "표면 굴곡으로 인한 포토 공정 초점 불량 유발"})
        elif step == 2 and params['oxi_temp'] > 1050:
            defect_this_step = "Center"
            rca_report.append({"step": "2. 산화 공정 (Oxidation)", "cause": f"챔버 온도 {params['oxi_temp']}℃ 과열", "effect": "웨이퍼 중앙부 산화막 두께 팽창"})
        elif step == 3 and params['dose'] < 25:
            defect_this_step = "Random"
            rca_report.append({"step": "3. 포토 공정 (Photo)", "cause": f"노광량(Dose) {params['dose']}mJ/cm² 부족", "effect": "샷 노이즈(Shot Noise) 발생 및 회로 단선"})
        elif step == 4 and params['rf_power'] > 500:
            defect_this_step = "Ring"
            rca_report.append({"step": "4. 식각 공정 (Etch)", "cause": f"RF 파워 {params['rf_power']}W 과다", "effect": "플라즈마가 가장자리로 쏠림 (링 결함)"})
        elif step == 5 and params['gas_flow'] > 70:
            defect_this_step = "Donut"
            rca_report.append({"step": "5. 박막 증착 (Deposition)", "cause": f"가스 유량 {params['gas_flow']}sccm 과다", "effect": "가스 미확산으로 인한 도넛 형태 박막 뭉침"})
        elif step == 6 and params['pressure'] > 4.5:
            defect_this_step = "Scratch"
            rca_report.append({"step": "6. 연마 공정 (CMP)", "cause": f"패드 누름 압력 {params['pressure']}psi 과다", "effect": "웨이퍼 표면 마이크로 스크래치 발생"})
        elif step == 7 and params['probe_force'] > 3.0:
            defect_this_step = "ProbeMark"
            rca_report.append({"step": "7. EDS 검사", "cause": f"프로브 핀 하중 {params['probe_force']}g 초과", "effect": "패드 물리적 파임 및 접촉 불량"})
        elif step == 8 and params['dicing_spd'] > 65:
            defect_this_step = "EdgeChipping"
            rca_report.append({"step": "8. 패키징 (Dicing)", "cause": f"톱날 속도 {params['dicing_spd']}mm/s 과속", "effect": "다이(Die) 가장자리 실리콘 깨짐(Chipping)"})
        
        # 터미널 로그 업데이트
        status_color = "red" if defect_this_step else "#00ff00"
        st.session_state.logs.append(f"<span style='color:{status_color};'>▶ [STEP {step}] 공정 완료. (결함 감지: {'YES' if defect_this_step else 'NO'})</span>")
        render_terminal()
        
        # 웨이퍼 시각화 (속도를 위해 time.sleep을 0.4초로 단축)
        if defect_this_step: cumulative_defects += get_defect_pattern(defect_this_step)
        
        current_wafer = get_base_wafer(step) + cumulative_defects
        current_wafer[~wafer_mask] = np.nan
        
        fig, ax = plt.subplots(figsize=(5, 5), facecolor='black')
        ax.set_facecolor('black')
        cmap = 'bone' if np.max(cumulative_defects) == 0 else plt.cm.turbo
        cmap_obj = plt.cm.get_cmap(cmap).copy()
        cmap_obj.set_bad(color='black')
        ax.imshow(current_wafer, cmap=cmap_obj, interpolation='none', vmin=-0.2, vmax=1.5)
        ax.axis('off')
        
        wafer_placeholder.pyplot(fig)
        plt.close(fig)
        
        time.sleep(0.4) # ✅ 각 단계별 실행 시간 0.4초 제한 (총 3.2초 소요)

    # -----------------------------------------------------------------
    # 불량 발생 시 RCA(Root Cause Analysis) 리포트 출력
    # -----------------------------------------------------------------
    if len(rca_report) > 0:
        st.session_state.logs.append("<span style='color:red;'>[SYSTEM] 🚨 최종 수율 불합격. 결함 추적 리포트를 확인하십시오.</span>")
        
        with rca_placeholder.container():
            st.error("🚨 **불량 발생 감지: 결함 원인 분석(RCA) 결과**")
            for issue in rca_report:
                st.markdown(f"""
                - **문제 발생 위치:** `{issue['step']}`
                - **원인 (Cause):** {issue['cause']}
                - **결과 (Effect):** {issue['effect']}
                """)
    else:
        st.session_state.logs.append("<span style='color:#00ff00;'>[SYSTEM] ✅ 결함 없음. 완제품 생산 승인.</span>")
        rca_placeholder.success("✅ **결함 없음 (Golden Yield)**: 모든 공정이 완벽하게 제어되었습니다. 스마트폰 및 TV 패키징 라인으로 이송합니다.")
        
    render_terminal()
