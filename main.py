import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

# =====================================================================
# 1. 페이지 기본 설정
# =====================================================================
st.set_page_config(
    page_title="반도체 8대 공정 실전 시뮬레이터 (장비 옵션 포함)",
    page_icon="🏭",
    layout="wide"
)

# =====================================================================
# 2. 웨이퍼 맵 생성 함수 (수학적 모델링)
# =====================================================================
@st.cache_data
def generate_realistic_wafer(error_type="Normal"):
    size = 200
    x, y = np.meshgrid(np.linspace(-1, 1, size), np.linspace(-1, 1, size))
    R = np.sqrt(x**2 + y**2)
    wafer_mask = R <= 1.0 
    
    wafer_map = gaussian_filter(np.random.rand(size, size), sigma=8) * 0.3 
    
    if error_type == "Defocus":
        wafer_map += gaussian_filter(np.sin(x*10) * np.cos(y*10) * 0.5 + 0.5, sigma=5) * 0.8
    elif error_type == "Center":
        wafer_map += np.exp(-(R**2) / 0.1) * 0.8
    elif error_type == "Random":
        wafer_map += gaussian_filter((np.random.rand(size, size) > 0.99).astype(float) * 0.9, sigma=1.5)
    elif error_type == "Ring":
        wafer_map += np.exp(-((R - 0.9)**2) / 0.01) * 0.9 * (1 + gaussian_filter(np.random.rand(size, size), sigma=2) * 0.4)
    elif error_type == "Donut":
        wafer_map += np.exp(-((R - 0.5)**2) / 0.03) * 0.75
    elif error_type == "Scratch":
        dist_from_line = np.abs(x - y) / np.sqrt(2)
        wafer_map += gaussian_filter(np.exp(-(dist_from_line**2) / 0.0002) * 0.9 * np.random.choice([0, 1], size=(size, size), p=[0.2, 0.8]), sigma=1)
    elif error_type == "EdgeChipping":
        wafer_map += (R > 0.95).astype(float) * (np.random.rand(size, size) > 0.7).astype(float) * 1.5

    wafer_map[~wafer_mask] = np.nan
    return np.clip(wafer_map, 0, 1)

# 실제 결함 참조용 인터넷 이미지 URL 매핑 (Wikipedia, 연구소 등 공개 이미지 기반)
DEFECT_IMAGES = {
    "Scratch": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d3/Silicon_wafer_with_defects.jpg/320px-Silicon_wafer_with_defects.jpg",
    "EdgeChipping": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Silicon_wafer.jpg/320px-Silicon_wafer.jpg",
    "Random": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Wafer_2_PhG.jpg/320px-Wafer_2_PhG.jpg",
    "Normal": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Siliciumwafer.jpg/320px-Siliciumwafer.jpg"
}

# =====================================================================
# 3. 메인 앱 실행 함수
# =====================================================================
def main():
    st.title("🏭 반도체 장비 및 파라미터 튜닝 시뮬레이터")
    st.markdown("현업에서 사용하는 **핵심 설비(Equipment) 옵션**과 **공정 파라미터**를 직접 조작해 수율을 분석합니다.")
    st.divider()

    # --- [사이드바] 8대 공정 파라미터 및 장비 셋업 ---
    st.sidebar.header("⚙️ 공정 및 장비 셋업")
    
    with st.sidebar.expander("1. 산화 공정 (Oxidation)"):
        oxi_equip = st.selectbox("장비 타입", ["Furnace (배치형)", "RTP (매엽식 초고속 열처리)"])
        oxi_temp = st.slider("Chamber Temp (℃)", 800, 1200, 1000, step=10)
        
    with st.sidebar.expander("2. 포토 공정 (Photo)"):
        photo_equip = st.selectbox("노광 설비", ["ASML EUV (극자외선)", "ArF Immersion (액침)"])
        photo_dose = st.slider("Exposure Dose (mJ/cm²)", 10, 50, 30, step=1)
        
    with st.sidebar.expander("3. 식각 공정 (Etch)"):
        etch_equip = st.selectbox("플라즈마 소스", ["ICP (유도결합형)", "CCP (용량결합형)"])
        etch_power = st.slider("RF Power (W)", 100, 500, 300, step=10)
        
    with st.sidebar.expander("4. 박막 공정 (Deposition)"):
        dep_equip = st.selectbox("증착 방식", ["ALD (원자층 증착)", "PECVD (플라즈마 화학기상증착)"])
        dep_gas = st.slider("Gas Flow Rate (sccm)", 10, 100, 50, step=5)
        
    with st.sidebar.expander("5. 연마 공정 (CMP)"):
        cmp_pad = st.selectbox("연마 패드(Pad) 타입", ["Soft Pad (소프트)", "Hard Pad (하드)"])
        cmp_press = st.slider("Pad Pressure (psi)", 1.0, 5.0, 3.0, step=0.1)

    simulate_btn = st.sidebar.button("🔬 팹(Fab) 가동 및 수율 분석", type="primary", use_container_width=True)

    # --- [메인 화면] 로직 판단 및 시각화 ---
    if simulate_btn:
        with st.spinner("선택된 장비와 파라미터로 시뮬레이션 중입니다..."):
            
            error_type = "Normal"
            fault_proc = "정상"
            
            # 장비 특성을 반영한 오류 감지 로직
            if oxi_temp > 1050 and oxi_equip == "Furnace (배치형)":
                error_type, fault_proc = "Center", "산화 공정 (Furnace)"
                cause = f"배치(Batch)형 튜브 내부 온도가 {oxi_temp}℃로 과열되었습니다. 대량의 웨이퍼 간 열 전달 불균일로 중심부 두께 편차가 발생했습니다."
                guide = "히터 Zone 밸런스를 재조정하거나, 고온 제어에 유리한 RTP(급속열처리) 장비로의 전환을 검토하세요."
                
            elif photo_dose < 25 and photo_equip == "ASML EUV (극자외선)":
                error_type, fault_proc = "Random", "포토 공정 (EUV)"
                cause = f"EUV 설비에서 Dose 량이 {photo_dose}mJ/cm²로 부족하여 'Photon Shot Noise(광자 산포 노이즈)'가 발생, 패턴이 끊겼습니다."
                guide = "EUV 광원(Source)의 출력을 높이거나, 레지스트(PR)의 민감도를 개선한 고감도 약액으로 교체하세요."
                
            elif etch_power > 380 and etch_equip == "ICP (유도결합형)":
                error_type, fault_proc = "Ring", "식각 공정 (ICP Etch)"
                cause = f"고밀도 ICP 플라즈마 환경에서 RF Power가 {etch_power}W로 초과되어 가장자리 플라즈마 쏠림 현상이 발생했습니다."
                guide = "Bias Power를 낮추고, 엣지 링(Edge Ring)의 높이 및 튜닝 상태를 즉시 점검하세요."
                
            elif dep_gas > 60 and dep_equip == "ALD (원자층 증착)":
                error_type, fault_proc = "Donut", "박막 공정 (ALD)"
                cause = f"ALD 공정 중 전구체(Precursor) 가스가 {dep_gas}sccm으로 과다 주입되어 퍼지(Purge)가 제대로 되지 않고 기상 반응이 일어났습니다."
                guide = "가스 분사 밸브(ALD Valve)의 개폐 시간(Time Step)을 줄이고 Ar 퍼지 시간을 늘리세요."
                
            elif cmp_press > 3.8 and cmp_pad == "Hard Pad (하드)":
                error_type, fault_proc = "Scratch", "연마 공정 (CMP)"
                cause = f"Hard Pad 사용 중 압력이 {cmp_press}psi로 과다하여 패드 표면과 웨이퍼 간 미세 스크래치(Micro-scratch)가 대량 발생했습니다."
                guide = "압력을 낮추거나, 연마재(Slurry) 필터를 교체하고 Pad 컨디셔너(Diamond Disk) 마모도를 확인하세요."

            else:
                error_type, fault_proc = "Normal", "전체 공정 정상"
                cause = "선택한 설비와 파라미터 조합이 완벽한 시너지를 내고 있습니다."
                guide = "양산(HVM)에 즉시 적용 가능한 골든 레시피입니다."

            # 결과 출력부
            col1, col2 = st.columns([1.1, 1.3])
            
            with col1:
                st.subheader("🗺️ 계측 스캔 히트맵")
                wafer_data = generate_realistic_wafer(error_type)
                
                fig, ax = plt.subplots(figsize=(6, 6))
                fig.patch.set_facecolor('none')
                ax.set_facecolor('none')
                
                cmap = plt.cm.RdYlGn_r 
                cmap.set_bad(color='white')
                
                ax.imshow(wafer_data, cmap=cmap, interpolation='gaussian')
                circle = plt.Circle((100, 100), 100, color='black', fill=False, linewidth=1.5)
                ax.add_patch(circle)
                ax.axis('off')
                st.pyplot(fig)
                
                # 인터넷 실제 이미지 렌더링
                st.markdown("**(참고) 실제 현장 결함 양상**")
                img_url = DEFECT_IMAGES.get(error_type, DEFECT_IMAGES["Normal"])
                st.image(img_url, use_container_width=True, caption=f"실제 {error_type} 관련 현미경/맵 이미지")
                
            with col2:
                st.subheader("🤖 장비-파라미터 연계 트러블슈팅 리포트")
                
                if error_type == "Normal":
                    st.success("🟢 **수율 상태: 최상급 (Golden Yield)**")
                else:
                    st.error(f"🔴 **수율 상태: 설비/공정 불일치 경고 ({error_type} 패턴)**")
                    
                st.markdown("---")
                st.markdown(f"#### 📍 문제 발생 노드: **{fault_proc}**")
                st.markdown(f"**🔍 Root Cause (근본 원인):**\n{cause}")
                
                st.markdown("#### 🛠️ 설비 엔지니어링 액션 플랜")
                st.info(guide)
    else:
        st.info("👈 장비(EUV, ALD 등)를 먼저 선택하고 파라미터를 조작한 뒤 **'분석 실행'** 버튼을 누르세요.")

if __name__ == "__main__":
    main()
