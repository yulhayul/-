import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

# =====================================================================
# 1. 페이지 기본 설정
# =====================================================================
st.set_page_config(
    page_title="반도체 8대 공정 전면 시뮬레이터",
    page_icon="🏭",
    layout="wide"
)

# =====================================================================
# 2. 정교한 웨이퍼 맵 생성 함수 (8대 공정 불량 패턴 모델링)
# =====================================================================
@st.cache_data
def generate_realistic_wafer(error_type="Normal"):
    size = 200
    x = np.linspace(-1, 1, size)
    y = np.linspace(-1, 1, size)
    X, Y = np.meshgrid(x, y)
    R = np.sqrt(X**2 + Y**2)
    wafer_mask = R <= 1.0 
    
    # 기본 베이스 노이즈 (정상 상태의 미세한 산포)
    wafer_map = gaussian_filter(np.random.rand(size, size), sigma=8) * 0.3 
    
    # 8가지 오류 패턴 렌더링
    if error_type == "Defocus": # 웨이퍼 평탄도 불량 (Photo 초점 나감)
        defect = np.sin(X*10) * np.cos(Y*10) * 0.5 + 0.5
        wafer_map += gaussian_filter(defect, sigma=5) * 0.8
        
    elif error_type == "Center": # 산화 공정 온도 불균일
        defect = np.exp(-(R**2) / 0.1) * 0.8
        wafer_map += defect
        
    elif error_type == "Random": # 포토 공정 Dose 불량 (산발적 파티클/CD불량)
        particles = (np.random.rand(size, size) > 0.99).astype(float) * 0.9
        wafer_map += gaussian_filter(particles, sigma=1.5)
        
    elif error_type == "Ring": # 식각 공정 플라즈마 쏠림
        defect = np.exp(-((R - 0.9)**2) / 0.01) * 0.9
        defect *= (1 + gaussian_filter(np.random.rand(size, size), sigma=2) * 0.4)
        wafer_map += defect
        
    elif error_type == "Donut": # 박막 공정 가스 흐름 불량
        defect = np.exp(-((R - 0.5)**2) / 0.03) * 0.75
        wafer_map += defect
        
    elif error_type == "Scratch": # 금속 배선/CMP 압력 불량
        dist_from_line = np.abs(X - Y) / np.sqrt(2)
        defect = np.exp(-(dist_from_line**2) / 0.0002) * 0.9
        defect *= np.random.choice([0, 1], size=(size, size), p=[0.2, 0.8])
        wafer_map += gaussian_filter(defect, sigma=1)
        
    elif error_type == "ProbeMark": # EDS 테스트 프로브 핀 압력 과다
        # 바둑판 모양의 주기적인 점 패턴
        grid_x = np.cos(X * 40)**2
        grid_y = np.cos(Y * 40)**2
        defect = (grid_x * grid_y > 0.9).astype(float) * 0.9
        wafer_map += gaussian_filter(defect, sigma=0.5)
        
    elif error_type == "EdgeChipping": # 패키징 다이싱 톱날 속도 불량
        # 가장자리가 깨진 듯한 불규칙한 패턴
        edge_noise = np.random.rand(size, size)
        defect = (R > 0.95).astype(float) * (edge_noise > 0.7).astype(float) * 1.5
        wafer_map += defect

    # 마스크 및 값 스케일링
    wafer_map[~wafer_mask] = np.nan
    wafer_map = np.clip(wafer_map, 0, 1)
    
    return wafer_map

# =====================================================================
# 3. 메인 앱 실행 함수
# =====================================================================
def main():
    try:
        st.title("🏭 반도체 8대 공정 통합 시뮬레이터 & 트러블슈팅 가이드")
        st.markdown("""
        8대 공정의 핵심 파라미터를 직접 조작해 보세요. 최적 마진(Process Window)을 벗어나면 
        가상 팹(Virtual Fab)에서 즉각적으로 수율 저하 패턴을 감지하고 **해결 가이드라인**을 제시합니다.
        """)
        
        st.divider()

        # --- [사이드바] 8대 공정 파라미터 셋업 ---
        st.sidebar.header("⚙️ 8대 공정 파라미터 제어판")
        
        with st.sidebar.expander("1. 웨이퍼 제조 (Wafer Mfg)", expanded=True):
            ttv = st.slider("평탄도 TTV (µm)", 0.5, 3.0, 1.0, step=0.1, help="타겟: 1.0µm 이하")
            
        with st.sidebar.expander("2. 산화 공정 (Oxidation)"):
            oxi_temp = st.slider("Chamber Temp (℃)", 800, 1200, 1000, step=10, help="타겟: 1000℃")
            
        with st.sidebar.expander("3. 포토 공정 (Photo)"):
            photo_dose = st.slider("Exposure Dose (mJ/cm²)", 10, 50, 30, step=1, help="타겟: 30mJ/cm²")
            
        with st.sidebar.expander("4. 식각 공정 (Etch)"):
            etch_power = st.slider("RF Power (W)", 100, 500, 300, step=10, help="타겟: 300W")
            
        with st.sidebar.expander("5. 박막 공정 (Deposition)"):
            dep_gas = st.slider("Gas Flow Rate (sccm)", 10, 100, 50, step=5, help="타겟: 50sccm")
            
        with st.sidebar.expander("6. 금속 배선 (Metallization)"):
            metal_press = st.slider("Sputtering Pressure (mTorr)", 1.0, 10.0, 5.0, step=0.5, help="타겟: 5.0mTorr")
            
        with st.sidebar.expander("7. EDS (테스트)"):
            probe_force = st.slider("Probe Contact Force (g)", 1.0, 5.0, 2.0, step=0.1, help="타겟: 2.0g")
            
        with st.sidebar.expander("8. 패키징 (Packaging)"):
            dicing_speed = st.slider("Dicing Blade Speed (mm/s)", 20, 80, 50, step=5, help="타겟: 50mm/s")

        simulate_btn = st.sidebar.button("🔬 8대 공정 시뮬레이션 실행", type="primary", use_container_width=True)

        # --- [메인 화면] 로직 판단 및 시각화 ---
        if simulate_btn:
            with st.spinner("AI가 8대 공정 데이터를 취합하여 수율을 분석 중입니다..."):
                
                # 오류 감지 로직 (공정 순서대로 가장 먼저 마진을 이탈한 치명적 불량을 캐치)
                error_type = "Normal"
                
                if ttv > 1.8:
                    error_type, fault_proc = "Defocus", "1. 웨이퍼 제조 공정"
                    cause = f"웨이퍼 평탄도(TTV)가 {ttv}µm로 기준치(1.5) 초과. 표면이 굴곡져 포토 공정 시 초점(Focus)이 맞지 않습니다."
                    guide = "1) 래핑(Lapping) 및 폴리싱(Polishing) 설비의 정반 평탄도를 재측정하세요.\n2) 연마재(Slurry) 공급량을 늘리고 압력을 재조정하세요."
                
                elif oxi_temp < 920 or oxi_temp > 1080:
                    error_type, fault_proc = "Center", "2. 산화 (Oxidation) 공정"
                    cause = f"온도가 {oxi_temp}℃로 타겟(1000℃) 이탈. 챔버 내외곽 온도 차이로 중앙부 산화막 두께가 변형되었습니다."
                    guide = "1) 챔버 히터(Heater)의 Zone별(Center/Edge) 온도 캘리브레이션을 수행하세요.\n2) 챔버 도어의 열 손실(Leak) 여부를 점검하세요."
                    
                elif photo_dose < 22 or photo_dose > 38:
                    error_type, fault_proc = "Random", "3. 포토 (Photo) 공정"
                    cause = f"노광량(Dose)이 {photo_dose}mJ/cm²로 불안정. 회로 선폭(CD)이 균일하지 않아 산발적인 패턴 무너짐이 발생합니다."
                    guide = "1) 노광기 광원(Light Source)의 램프 수명 및 출력을 점검하세요.\n2) 포토레지스트(PR) 코팅 두께의 균일도를 계측기로 재확인하세요."
                    
                elif etch_power < 240 or etch_power > 360:
                    error_type, fault_proc = "Ring", "4. 식각 (Etch) 공정"
                    cause = f"RF Power가 {etch_power}W로 타겟(300W) 이탈. 플라즈마 밀도가 웨이퍼 가장자리에 쏠려 엣지 과식각이 발생했습니다."
                    guide = "1) RF 매칭 네트워크(Matching Network) 상태를 점검하세요.\n2) 웨이퍼 테두리를 보호하는 Focus Ring의 마모 상태를 확인하고 교체하세요."
                    
                elif dep_gas < 35 or dep_gas > 65:
                    error_type, fault_proc = "Donut", "5. 박막 (Deposition) 공정"
                    cause = f"가스 유량(Flow)이 {dep_gas}sccm으로 타겟(50sccm) 이탈. 반응 가스가 도넛 형태로 불균일하게 확산되었습니다."
                    guide = "1) 샤워헤드(Showerhead)의 홀(Hole) 막힘이나 오염을 점검하세요.\n2) MFC(질량 유량 제어기)의 영점(Zero Point) 조정을 실시하세요."
                    
                elif metal_press > 7.0:
                    error_type, fault_proc = "Scratch", "6. 금속 배선 (Metallization)"
                    cause = f"Sputtering 압력이 {metal_press}mTorr로 과다. 증착 중 튀어오른 파티클이나 스트레스로 인해 물리적 스크래치(Void/Short)가 발생했습니다."
                    guide = "1) 아르곤(Ar) 가스 밸브 및 진공 펌프 압력 제어기를 점검하세요.\n2) 타겟(Target) 물질의 노후화 및 이물질 부착 여부를 확인하세요."
                    
                elif probe_force > 3.0:
                    error_type, fault_proc = "ProbeMark", "7. EDS 공정 (Wafer Test)"
                    cause = f"프로브 핀 접촉 하중이 {probe_force}g로 타겟(2.0g) 초과. 핀이 패드(Pad)를 과도하게 눌러 바둑판 형태의 파임 불량이 발생했습니다."
                    guide = "1) 프로버(Prober) 장비의 Z축 오버드라이브(Overdrive) 값을 낮추세요.\n2) 프로브 카드(Probe Card) 핀의 정렬 상태 및 팁 마모를 현미경으로 검사하세요."
                    
                elif dicing_speed > 65:
                    error_type, fault_proc = "EdgeChipping", "8. 패키징 (Dicing) 공정"
                    cause = f"다이싱 톱날 속도가 {dicing_speed}mm/s로 너무 빠름. 웨이퍼 절단 중 충격으로 칩 가장자리(Edge)가 깨져나갔습니다."
                    guide = "1) 블레이드(Blade)의 이송 속도를 낮추고 냉각수(DI Water) 분사량을 늘리세요.\n2) 다이싱 테이프의 접착력 및 블레이드 마모도를 점검하세요."
                    
                else:
                    error_type, fault_proc = "Normal", "전체 공정 정상"
                    cause = "8대 공정의 모든 파라미터가 최적 마진(Process Window) 내에서 안정적으로 제어되고 있습니다."
                    guide = "현재의 황금 레시피(Golden Recipe)를 유지하며 양산을 진행하세요. OEE(설비 종합 효율)가 우수합니다."

                # --- 화면 출력부 ---
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
                    
                with col2:
                    st.subheader("🤖 FDC 트러블슈팅 리포트")
                    
                    if error_type == "Normal":
                        st.success("🟢 **Yield Status: 최상급 (Golden Yield)**")
                    else:
                        st.error(f"🔴 **Yield Status: 수율 경고 ({error_type} 패턴 감지)**")
                        
                    st.markdown("---")
                    st.markdown(f"#### 📍 문제 발생 노드: **{fault_proc}**")
                    st.markdown(f"**🔍 Root Cause (근본 원인):**\n{cause}")
                    
                    st.markdown("#### 🛠️ 현장 엔지니어 조치 가이드라인")
                    # 가이드라인을 보기 좋게 박스 형태로 출력
                    st.info(guide)

        else:
            st.info("👈 왼쪽 사이드바에서 8대 공정 파라미터를 자유롭게 조작한 뒤 **'시뮬레이션 실행'** 버튼을 클릭하세요.")

    except Exception as e:
        st.error("🚨 화면 구성 중 오류가 발생했습니다.")
        st.markdown("**[디버깅 가이드]** `requirements.txt`에 `matplotlib`과 `scipy`가 있는지 확인하세요.")
        st.write(f"상세 로그: {e}")

if __name__ == "__main__":
    main()
