import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import time

# =====================================================================
# 1. UI 기본 설정 (깔끔한 기본 스타일로 복귀)
# =====================================================================
st.set_page_config(page_title="반도체 8대 공정 시뮬레이터", layout="wide")

st.title("반도체 8대 공정 시뮬레이터 팹(FAB)")
st.write("왼쪽 사이드바에서 각 공정의 파라미터를 조절한 뒤, 시뮬레이션을 실행하여 불량 발생 여부를 확인하세요.")

# =====================================================================
# 2. 공정별 웨이퍼 엔진 (속도 최적화)
# =====================================================================
size = 250
x, y = np.meshgrid(np.linspace(-1, 1, size), np.linspace(-1, 1, size))
R = np.sqrt(x**2 + y**2)
theta = np.arctan2(y, x)
wafer_mask = (R <= 1.0) & ~((R > 0.96) & (np.abs(theta + np.pi/2) < 0.05))

def get_base_wafer(step):
    base = np.zeros((size, size))
    if step >= 1: base += 0.5 
    if step >= 2: base += gaussian_filter(np.random.rand(size, size), sigma=10) * 0.1 - 0.1
    if step >= 3: base = np.where((np.abs(x * 20) % 1 < 0.1) | (np.abs(y * 20) % 1 < 0.1), base + 0.2, base)
    if step >= 4: base = np.where((np.abs(x * 20) % 1 < 0.2) | (np.abs(y * 20) % 1 < 0.2), base - 0.1, base)
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
# 3. 사이드바 파라미터 설정
# =====================================================================
st.sidebar.header("🎛️ 공정 파라미터 설정")

ttv = st.sidebar.slider("1. 웨이퍼 평탄도 (TTV, µm)", 0.5, 3.0, 2.0, step=0.1)
oxi_temp = st.sidebar.slider("2. 산화 챔버 온도 (℃)", 800, 1200, 1000, step=10)
dose = st.sidebar.slider("3. 노광량 Dose (mJ/cm²)", 10, 60, 30, step=2)
rf_power = st.sidebar.slider("4. 식각 RF 파워 (W)", 200, 800, 400, step=10)
gas_flow = st.sidebar.slider("5. 증착 가스 유량 (sccm)", 20, 100, 50, step=5)
pressure = st.sidebar.slider("6. CMP 연마 압력 (psi)", 1.0, 8.0, 3.0, step=0.5)
probe_force = st.sidebar.slider("7. 테스트 프로브 하중 (g)", 1.0, 5.0, 2.0, step=0.2)
dicing_spd = st.sidebar.slider("8. 패키징 톱날 속도 (mm/s)", 30, 90, 50, step=5)

run_btn = st.sidebar.button("▶️ 시뮬레이션 시작", type="primary")

# =====================================================================
# 4. 시각화 및 실행 로직
# =====================================================================
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📡 실시간 Wafer 상태")
    wafer_placeholder = st.empty()
    status_text = st.empty()

with col2:
    st.subheader("📋 불량 원인 분석 (RCA)")
    rca_placeholder = st.empty()

if run_btn:
    cumulative_defects = np.zeros((size, size))
    rca_report = []
    
    # 8대 공정 연속 실행 (약 3~4초 소요)
    for step in range(1, 9):
        defect_this_step = None
        step_name = ""
        
        if step == 1:
            step_name = "1. 웨이퍼 제조"
            if ttv > 1.8:
                defect_this_step = "Defocus"
                rca_report.append({"step": step_name, "cause": f"평탄도(TTV) {ttv}µm 과다", "effect": "표면 굴곡으로 인한 포토 공정 초점 불량 유발"})
        elif step == 2:
            step_name = "2. 산화 공정"
            if oxi_temp > 1050:
                defect_this_step = "Center"
                rca_report.append({"step": step_name, "cause": f"챔버 온도 {oxi_temp}℃ 과열", "effect": "웨이퍼 중앙부 산화막 두께 팽창"})
        elif step == 3:
            step_name = "3. 포토 공정"
            if dose < 25:
                defect_this_step = "Random"
                rca_report.append({"step": step_name, "cause": f"노광량 {dose}mJ/cm² 부족", "effect": "샷 노이즈(Shot Noise) 발생 및 회로 단선"})
        elif step == 4:
            step_name = "4. 식각 공정"
            if rf_power > 500:
                defect_this_step = "Ring"
                rca_report.append({"step": step_name, "cause": f"RF 파워 {rf_power}W 과다", "effect": "플라즈마가 가장자리로 쏠림 (링 결함)"})
        elif step == 5:
            step_name = "5. 박막 증착"
            if gas_flow > 70:
                defect_this_step = "Donut"
                rca_report.append({"step": step_name, "cause": f"가스 유량 {gas_flow}sccm 과다", "effect": "가스 미확산으로 인한 도넛 형태 박막 뭉침"})
        elif step == 6:
            step_name = "6. 연마 공정 (CMP)"
            if pressure > 4.5:
                defect_this_step = "Scratch"
                rca_report.append({"step": step_name, "cause": f"패드 누름 압력 {pressure}psi 과다", "effect": "웨이퍼 표면 마이크로 스크래치 발생"})
        elif step == 7:
            step_name = "7. EDS 검사"
            if probe_force > 3.0:
                defect_this_step = "ProbeMark"
                rca_report.append({"step": step_name, "cause": f"프로브 핀 하중 {probe_force}g 초과", "effect": "패드 물리적 파임 및 접촉 불량"})
        elif step == 8:
            step_name = "8. 패키징"
            if dicing_spd > 65:
                defect_this_step = "EdgeChipping"
                rca_report.append({"step": step_name, "cause": f"톱날 속도 {dicing_spd}mm/s 과속", "effect": "다이(Die) 가장자리 실리콘 깨짐(Chipping)"})
        
        status_text.info(f"▶ 진행 중: {step_name}")
        
        # 결함 누적
        if defect_this_step:
            cumulative_defects += get_defect_pattern(defect_this_step)
            
        current_wafer = get_base_wafer(step) + cumulative_defects
        current_wafer[~wafer_mask] = np.nan
        
        # ---------------------------------------------------------
        # 에러 수정 부분: Matplotlib 최신 버전(3.7+) 호환 방식 적용
        # ---------------------------------------------------------
        fig, ax = plt.subplots(figsize=(5, 5), facecolor='black')
        ax.set_facecolor('black')
        
        cmap_name = 'bone' if np.max(cumulative_defects) == 0 else 'turbo'
        
        # 최신 Matplotlib을 위한 안전한 colormap 설정
        try:
            cmap_obj = plt.get_cmap(cmap_name).copy()
            cmap_obj.set_bad(color='black')
        except AttributeError:
            # copy()를 지원하지 않는 최신 버전의 경우 with_extremes 사용
            cmap_obj = plt.get_cmap(cmap_name).with_extremes(bad='black')
            
        ax.imshow(current_wafer, cmap=cmap_obj, interpolation='none', vmin=-0.2, vmax=1.5)
        ax.axis('off')
        
        wafer_placeholder.pyplot(fig)
        plt.close(fig)
        
        time.sleep(0.4) # 각 과정 0.4초 소요 (총 약 3초)

    status_text.empty()

    # 결과 및 RCA 리포트 출력
    with rca_placeholder.container():
        if len(rca_report) > 0:
            st.error("🚨 **수율 저하 감지: 결함이 발생했습니다.**")
            for issue in rca_report:
                st.markdown(f"""
                - **문제 발생 공정:** `{issue['step']}`
                - **설정 오류 (원인):** {issue['cause']}
                - **발생한 결함 (결과):** {issue['effect']}
                """)
        else:
            st.success("✅ **결함 없음 (Golden Yield)**")
            st.write("모든 공정이 완벽하게 제어되었습니다. 생산된 칩은 스마트폰 및 TV 조립 라인으로 정상 출하됩니다.")
