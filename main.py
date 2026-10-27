import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import time

# =====================================================================
# 1. 페이지 및 UI 기본 설정 (설비 제어판 테마)
# =====================================================================
st.set_page_config(
    page_title="Advanced HMI: Semiconductor Equipment Control",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# 2. 극사실적 웨이퍼 맵 생성기 (계측기 UI 스타일, Notch, Die Grid 포함)
# =====================================================================
@st.cache_data
def generate_metrology_scan(error_type, intensity=1.0):
    size = 300  # 고해상도
    x, y = np.meshgrid(np.linspace(-1, 1, size), np.linspace(-1, 1, size))
    R = np.sqrt(x**2 + y**2)
    theta = np.arctan2(y, x)
    
    # 1. 웨이퍼 외곽선 및 Notch(하단 정렬 홈) 생성
    notch = (R > 0.96) & (np.abs(theta + np.pi/2) < 0.05)
    wafer_mask = (R <= 1.0) & ~notch
    
    # 2. 베이스 노이즈 (장비의 자연적인 산포)
    base_signal = gaussian_filter(np.random.rand(size, size), sigma=10) * 0.2
    
    # 3. 장비/공정별 특화 결함 시그널
    defect_signal = np.zeros((size, size))
    
    if error_type == "SlipLine": # RTP 고속 냉각 시 발생하는 결정 결함
        defect_signal += np.exp(-((x - y)**2)/0.001) * np.random.choice([0, 1], (size,size), p=[0.9, 0.1])
    elif error_type == "Gradient": # Furnace 온도 구배
        defect_signal += np.exp(-(R**2) / 0.15) * 0.8
    elif error_type == "Stochastic": # EUV Photon Shot Noise
        defect_signal += gaussian_filter((np.random.rand(size, size) > 0.95).astype(float), sigma=1) * 0.9
    elif error_type == "Overlay": # ArF 다중 패터닝 정렬 불량
        defect_signal += np.sin(x*30) * np.cos(y*30) * 0.4 + 0.4
    elif error_type == "EdgePlasma": # ICP 플라즈마 쏠림
        defect_signal += np.exp(-((R - 0.9)**2) / 0.005) * (1 + gaussian_filter(np.random.rand(size,size), 3) * 0.5)
    elif error_type == "MicroScratch": # CMP 하드 패드 스크래치
        dist = np.abs(x + y) / np.sqrt(2)
        defect_signal += gaussian_filter(np.exp(-(dist**2) / 0.0001) * np.random.choice([0,1], (size,size), p=[0.1, 0.9]), sigma=0.5)
    elif error_type == "Dishing": # CMP 소프트 패드 평탄도 불량 (중심부 파임)
        defect_signal += (R < 0.3).astype(float) * 0.6
    
    # 결함 강도(Intensity) 조절
    final_signal = base_signal + (defect_signal * intensity)
    
    # 4. 칩(Die) 단위 격자(Grid) 패턴 오버레이 (실제 수율 맵 느낌)
    grid_x = (np.abs(x * 25) % 1 < 0.1)
    grid_y = (np.abs(y * 25) % 1 < 0.1)
    grid_mask = grid_x | grid_y
    final_signal[grid_mask] *= 0.8  # 격자 부분은 약간 어둡게 처리
    
    # 마스크 바깥쪽(웨이퍼 외부)은 NaN 처리하여 투명하게
    final_signal[~wafer_mask] = np.nan
    return np.clip(final_signal, 0, 1)

# =====================================================================
# 3. HMI 메인 컨트롤 로직
# =====================================================================
def main():
    st.markdown("<h2 style='text-align: center; color: #4CAF50;'>🟢 FAB Equipment Control Interface (HMI)</h2>", unsafe_allow_html=True)
    st.markdown("실제 설비를 다루듯 `Main Power`와 `Vacuum`을 켜고, 장비 타입과 파라미터를 조작해 공정을 Run 하세요.")
    st.divider()

    # -----------------------------------------------------------------
    # 설비 제어판 (Control Panel) - 사이드바
    # -----------------------------------------------------------------
    st.sidebar.markdown("### 🔌 System Status")
    col_pwr1, col_pwr2 = st.sidebar.columns(2)
    sys_power = col_pwr1.toggle("Main Power", value=True)
    vac_pump = col_pwr2.toggle("Vacuum Pump", value=True)
    
    if not (sys_power and vac_pump):
        st.sidebar.error("⚠️ SYSTEM INTERLOCK: 장비 전원과 진공 펌프를 켜야 레시피 조작이 가능합니다.")
        st.error("🚨 시스템이 대기 상태입니다. 왼쪽 제어판에서 Main Power와 Vacuum Pump를 가동하십시오.")
        return # 전원이 꺼지면 아래 로직 실행 안함

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎛️ Recipe Setup (장비 및 파라미터)")
    
    # 공정 모듈 선택
    process_module = st.sidebar.selectbox("Process Module (공정 선택)", ["1. Oxidation (산화)", "2. Photo (노광)", "3. Etch (식각)", "4. CMP (연마)"])
    
    # 모듈별 세부 장비 및 파라미터 동적 렌더링
    if process_module == "1. Oxidation (산화)":
        eq_type = st.sidebar.radio("Equipment Type", ["Furnace (대용량 배치형)", "RTP (매엽식 급속열처리)"])
        param_val = st.sidebar.slider("Ramp-up Rate (℃/sec)", 1, 150, 50, help="온도 상승 속도")
        
    elif process_module == "2. Photo (노광)":
        eq_type = st.sidebar.radio("Equipment Type", ["ArF Immersion (액침)", "EUV (극자외선)"])
        param_val = st.sidebar.slider("Exposure Dose (mJ/cm²)", 10, 80, 30, help="빛의 노출량")
        
    elif process_module == "3. Etch (식각)":
        eq_type = st.sidebar.radio("Plasma Source", ["CCP (용량결합형)", "ICP (유도결합형)"])
        param_val = st.sidebar.slider("Source Power (W)", 100, 1000, 500, help="플라즈마 밀도 제어")
        
    elif process_module == "4. CMP (연마)":
        eq_type = st.sidebar.radio("Pad Material", ["Hard Pad (폴리우레탄)", "Soft Pad (다공성 수지)"])
        param_val = st.sidebar.slider("Down Force (psi)", 1.0, 10.0, 4.0, help="웨이퍼 누르는 압력")

    run_btn = st.sidebar.button("▶️ RUN RECIPE (공정 시작)", type="primary", use_container_width=True)

    # -----------------------------------------------------------------
    # 메인 모니터링 화면 (결과 분석부)
    # -----------------------------------------------------------------
    if run_btn:
        # 가상의 장비 가동 프로그레스 바
        progress_bar = st.progress(0)
        status_text = st.empty()
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)
            status_text.text(f"Processing Wafer... {i+1}% (Step: Plasma Ignited / Gas Flowing)")
        status_text.text("Wafer Processing Complete. Metrology Scan Started.")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()

        # 장비 특성에 따른 로직 (결과/현상 도출)
        error_type = "Normal"
        intensity = 0.0
        insight = ""
        
        # 1. Oxidation 로직
        if "Oxidation" in process_module:
            if eq_type == "RTP (매엽식 급속열처리)" and param_val > 100:
                error_type = "SlipLine"
                intensity = param_val / 150.0
                insight = f"RTP 장비는 승온 속도가 빠르지만, 현재 {param_val}℃/sec로 한계 마진을 초과했습니다. 웨이퍼에 급격한 열 스트레스가 가해져 **결정 결함(Slip Line)**이 발생했습니다."
            elif eq_type == "Furnace (대용량 배치형)" and param_val > 20:
                error_type = "Gradient"
                intensity = param_val / 150.0
                insight = f"Furnace 장비는 열용량이 커서 서서히 가열해야 합니다. {param_val}℃/sec의 빠른 승온은 튜브 중앙부와 외곽의 극심한 온도 구배를 만들어 산화막 균일도(Uniformity)가 무너졌습니다."
            else:
                insight = f"{eq_type} 장비의 특성에 맞는 적절한 Ramp-up 속도입니다."
                
        # 2. Photo 로직
        elif "Photo" in process_module:
            if eq_type == "EUV (극자외선)" and param_val < 30:
                error_type = "Stochastic"
                intensity = 1 - (param_val/80.0)
                insight = f"EUV는 파장이 매우 짧고 에너지가 커서 적은 수의 광자(Photon)가 쏴집니다. Dose량이 {param_val}로 너무 낮아 빛이 균일하게 도달하지 못하는 **Photon Shot Noise(확률적 결함)**가 발생하여 패턴이 끊겼습니다."
            elif eq_type == "ArF Immersion (액침)" and param_val > 50:
                error_type = "Overlay"
                intensity = param_val / 80.0
                insight = f"ArF 공정에서 과도한 노광 에너지는 물(물방울)의 온도 변화를 유발하여 빛의 굴절률이 흔들립니다. 이로 인해 다중 패터닝(Multi-patterning) 시 **오버레이(정렬) 불량**이 발생했습니다."
            else:
                insight = f"{eq_type} 광원 특성에 완벽히 부합하는 Dose량입니다."

        # 3. Etch 로직
        elif "Etch" in process_module:
            if eq_type == "ICP (유도결합형)" and param_val > 700:
                error_type = "EdgePlasma"
                intensity = param_val / 1000.0
                insight = f"ICP 장비는 독립적인 고밀도 플라즈마 제어가 장점이나, Source Power가 {param_val}W로 과다하여 안테나 코일 주변(웨이퍼 가장자리)으로 플라즈마가 심하게 집중되는 **WIWNU(웨이퍼 내 불균일도) 불량**이 발생했습니다."
            elif eq_type == "CCP (용량결합형)" and param_val > 800:
                error_type = "Gradient" # 유사한 타격 데미지 시그널로 대체
                intensity = param_val / 1000.0
                insight = f"CCP 장비는 직진성이 좋지만 이온 에너지가 큽니다. Power가 {param_val}W로 높아 웨이퍼 표면에 심각한 **물리적 이온 데미지(Ion Bombardment)**가 가해졌습니다."
            else:
                insight = "플라즈마 밀도와 이온 에너지가 안정적으로 유지되고 있습니다."

        # 4. CMP 로직
        elif "CMP" in process_module:
            if eq_type == "Hard Pad (폴리우레탄)" and param_val > 7.0:
                error_type = "MicroScratch"
                intensity = param_val / 10.0
                insight = f"Hard Pad는 평탄도는 좋으나 딱딱합니다. Down Force가 {param_val}psi로 너무 강해 표면에 심각한 **Micro-Scratch(미세 긁힘)**가 대량 발생했습니다. 수율에 치명적입니다."
            elif eq_type == "Soft Pad (다공성 수지)" and param_val > 6.0:
                error_type = "Dishing"
                intensity = param_val / 10.0
                insight = f"Soft Pad는 스크래치는 안나지만 패드가 푹신합니다. 높은 압력({param_val}psi)으로 누르면 패턴 사이의 빈 공간이 푹 파이는 **Dishing(디싱) 현상**이 발생하여 배선 단선 위험이 커집니다."
            else:
                insight = f"{eq_type}의 물성과 현재 압력이 최적의 조화를 이루고 있습니다."

        # -------------------------------------------------------------
        # UI 출력 (대시보드 형태)
        # -------------------------------------------------------------
        col_img, col_info = st.columns([1, 1.2])
        
        with col_img:
            st.markdown("#### 📡 In-Line Metrology Scan (Yield Map)")
            
            # 장비 제어판 스타일의 플롯 렌더링
            fig, ax = plt.subplots(figsize=(6, 6), facecolor='black')
            ax.set_facecolor('black')
            
            wafer_data = generate_metrology_scan(error_type, intensity=intensity)
            
            # 산업용 열화상 느낌의 컬러맵(turbo, jet, 또는 magma)
            cmap = plt.cm.turbo 
            cmap.set_bad(color='black') # 웨이퍼 밖은 배경색(검정)
            
            ax.imshow(wafer_data, cmap=cmap, interpolation='none') # interpolation='none'으로 격자 느낌 강조
            
            # 스캔 라인 이펙트 (ui 디테일)
            ax.axhline(y=150, color='lime', linewidth=0.5, alpha=0.5, linestyle='--')
            ax.axvline(x=150, color='lime', linewidth=0.5, alpha=0.5, linestyle='--')
            
            ax.axis('off')
            st.pyplot(fig)
            
        with col_info:
            st.markdown("#### 📊 FDC Analysis Report")
            
            # 디지털 계기판 느낌의 Metric 시각화
            m1, m2, m3 = st.columns(3)
            yield_val = 99.8 if error_type == "Normal" else max(10, 100 - (intensity * 100))
            m1.metric("Est. Yield", f"{yield_val:.1f}%", f"{yield_val - 98.0:.1f}%" if yield_val >= 98 else f"{yield_val - 98.0:.1f}%")
            m2.metric("Chamber Vacuum", "1.2e-6 Torr", "Stable")
            m3.metric("Defect Status", "PASS" if error_type == "Normal" else "FAIL", delta_color="inverse")
            
            st.markdown("---")
            
            # 현장 분석 리포트 박스
            if error_type == "Normal":
                st.success(f"**✅ [정상] {eq_type} Golden Recipe 작동 중**")
                st.write("장비의 물리적 특성을 완벽히 이해한 파라미터 세팅입니다.")
            else:
                st.error(f"**🚨 [알람] {eq_type} 한계 마진 이탈 ({error_type})**")
            
            st.markdown("##### 🔬 장비 특성 기반 원인 분석 (Equipment Insight)")
            st.info(insight)
            
            if error_type != "Normal":
                st.markdown("##### 🔧 조치 권고사항")
                st.write("- 파라미터(슬라이더) 값을 낮추어 장비의 물리적 한계점(Process Window) 안으로 진입시키십시오.")
                st.write("- 또는 현재 타겟 수율을 맞추기 위해 다른 특성을 가진 장비(Equipment Type)로 변경 테스트를 진행하십시오.")
                
    else:
        st.info("👈 장비와 공정 조건을 셋업한 후 **'RUN RECIPE'** 버튼을 클릭하여 시뮬레이션을 시작하세요.")

if __name__ == "__main__":
    main()
