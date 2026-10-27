import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

# =====================================================================
# 1. 페이지 기본 설정
# =====================================================================
st.set_page_config(
    page_title="8대 공정 파라미터 기반 웨이퍼 시뮬레이터",
    page_icon="🏭",
    layout="wide"
)

# =====================================================================
# 2. 정교한 웨이퍼 맵 생성 함수 (수학적 모델링 & 가우시안 필터 적용)
# =====================================================================
@st.cache_data
def generate_realistic_wafer(error_type="Normal"):
    """
    단순한 점 찍기가 아닌, 실제 장비의 센서(계측기)가 스캔한 것 같은
    연속적인 표면 히트맵(Surface Heatmap)을 수학적으로 생성합니다.
    """
    size = 200 # 해상도 200x200
    x = np.linspace(-1, 1, size)
    y = np.linspace(-1, 1, size)
    X, Y = np.meshgrid(x, y)
    
    # 원점에서부터의 거리 (반지름 1을 기준)
    R = np.sqrt(X**2 + Y**2)
    wafer_mask = R <= 1.0 # 웨이퍼 영역 마스크 (반지름 1 안쪽만 True)
    
    # 1. 정상 상태의 기본 노이즈 (자연스러운 공정 산포 시뮬레이션)
    # 완전한 균일(0)은 현실에 없으므로, 난수를 생성하고 가우시안 블러로 부드럽게 폄
    base_noise = np.random.rand(size, size)
    wafer_map = gaussian_filter(base_noise, sigma=8) * 0.3 
    
    # 2. 오류 타입에 따른 불량 패턴 덧씌우기
    if error_type == "Ring":
        # 엣지(가장자리) 부근(R=0.85~0.95)에 집중된 불량 (식각 플라즈마 문제 등)
        ring_defect = np.exp(-((R - 0.85)**2) / 0.015) * 0.8
        # 노이즈를 섞어 인위적인 느낌을 없앰
        ring_defect *= (1 + gaussian_filter(np.random.rand(size, size), sigma=2) * 0.5)
        wafer_map += ring_defect

    elif error_type == "Center":
        # 중앙부 집중 불량 (증착/산화 공정의 온도 구배 문제 등)
        center_defect = np.exp(-(R**2) / 0.1) * 0.75
        wafer_map += center_defect

    elif error_type == "Scratch":
        # 대각선 방향의 물리적 스크래치 (CMP 연마 패드 문제 등)
        # x = y 선상을 기준으로 거리를 구함
        distance_from_line = np.abs(X - Y - 0.2) / np.sqrt(2)
        scratch_defect = np.exp(-(distance_from_line**2) / 0.0005) * 0.9
        # 스크래치가 중간에 끊기는 듯한 현실적인 느낌 추가
        scratch_defect *= np.random.choice([0, 1], size=(size, size), p=[0.1, 0.9])
        wafer_map += gaussian_filter(scratch_defect, sigma=1)

    elif error_type == "Random":
        # 산발적인 파티클 오염 (포토 공정 노이즈 등)
        particles = np.random.rand(size, size) > 0.995 # 0.5% 확률로 파티클 발생
        particles = particles.astype(float) * 0.9
        wafer_map += gaussian_filter(particles, sigma=2)

    # 3. 마스크 씌우기 (웨이퍼 바깥쪽은 배경색 처리용으로 NaN 할당)
    wafer_map[~wafer_mask] = np.nan
    
    # 값 범위를 0(정상) ~ 1(불량)로 스케일링
    wafer_map = np.clip(wafer_map, 0, 1)
    
    return wafer_map

# =====================================================================
# 3. 메인 앱 실행 함수
# =====================================================================
def main():
    try:
        # 타이틀 및 안내
        st.title("🏭 반도체 8대 공정 파라미터 튜닝 시뮬레이터")
        st.markdown("""
        이 대시보드는 **엔지니어가 직접 주요 공정의 파라미터를 조작**했을 때, 파라미터가 적정 마진(Process Margin)을 
        벗어날 경우 웨이퍼 상에 어떤 기하학적 불량 패턴이 나타나는지 **인과관계**를 분석합니다.
        """)
        
        st.divider()

        # [사이드바] 공정 파라미터 입력부
        st.sidebar.header("⚙️ 8대 공정 파라미터 셋업")
        st.sidebar.caption("각 공정별 타겟(목표) 값을 확인하고 슬라이더를 조작해 보세요.")
        
        # 1. 산화/증착 공정
        st.sidebar.subheader("1. 산화/증착 (Oxidation & CVD)")
        temp = st.sidebar.slider("Chamber Temperature (℃)", 600, 1200, 1000, step=10, 
                               help="적정 타겟: 1000℃. 온도가 너무 높거나 낮으면 웨이퍼 중앙/가장자리 간 온도 구배가 생겨 Center 패턴 유발.")
        
        # 2. 포토 공정
        st.sidebar.subheader("2. 포토 (Photo/Lithography)")
        dose = st.sidebar.slider("노광량 Dose (mJ/cm²)", 10, 50, 30, step=1,
                               help="적정 타겟: 30. 노광량이 불안정하면 CD(선폭) 산포가 커져 Random 패턴의 수율 저하 발생.")
        
        # 3. 식각 공정
        st.sidebar.subheader("3. 식각 (Etching)")
        rf_power = st.sidebar.slider("RF Power (W)", 100, 500, 300, step=10,
                                   help="적정 타겟: 300W. 파워가 너무 높으면 플라즈마가 웨이퍼 가장자리에 쏠려 Ring 패턴 유발.")
        
        # 4. 연마 공정
        st.sidebar.subheader("4. 연마 (CMP)")
        pressure = st.sidebar.slider("Pad Pressure (psi)", 1.0, 5.0, 3.0, step=0.1,
                                   help="적정 타겟: 3.0. 압력이 과도하게 높으면 미세 파티클에 의해 물리적 Scratch 패턴 유발.")

        # 분석 버튼
        simulate_btn = st.sidebar.button("🔬 공정 시뮬레이션 실행", type="primary")

        # [메인 화면] 로직 판단 및 시각화부
        if simulate_btn:
            with st.spinner("가상 팹(Virtual Fab)에서 웨이퍼를 생산 중입니다..."):
                
                # --- 공정 오류 판독 로직 (우선순위 기반) ---
                error_type = "Normal"
                root_cause = ""
                action_plan = ""
                fault_process = ""

                # 1. 식각 공정 오류 체크
                if rf_power > 380 or rf_power < 220:
                    error_type = "Ring"
                    fault_process = "식각 (Etch) 공정"
                    root_cause = f"RF Power가 {rf_power}W로 타겟(300W)을 크게 벗어남. 플라즈마 밀도가 웨이퍼 엣지(가장자리)에 집중되어 균일도(WIWNU)가 무너졌습니다."
                    action_plan = "식각 챔버의 RF Generator 출력을 점검하고, Edge Ring의 마모 상태를 확인하십시오."
                
                # 2. 연마 공정 오류 체크
                elif pressure > 4.2:
                    error_type = "Scratch"
                    fault_process = "연마 (CMP) 공정"
                    root_cause = f"Pad Pressure가 {pressure}psi로 타겟(3.0psi)을 초과함. 과도한 하중으로 인해 연마 패드와 슬러리 응집체 사이에서 긁힘이 발생했습니다."
                    action_plan = "CMP 설비의 압력 제어 센서를 캘리브레이션하고, Slurry 필터 및 Pad 컨디셔닝 상태를 점검하십시오."
                    
                # 3. 증착/산화 공정 오류 체크
                elif temp > 1080 or temp < 920:
                    error_type = "Center"
                    fault_process = "산화/CVD 공정"
                    root_cause = f"Chamber 온도가 {temp}℃로 타겟(1000℃)을 이탈함. 챔버 내 온도 구배(Gradient)가 발생하여 중앙부의 증착 두께가 달라졌습니다."
                    action_plan = "챔버 내 히터(Heater) Zone별 온도 밸런스를 재조정하고 가스 분사 비율(Center/Edge Ratio)을 튜닝하십시오."
                    
                # 4. 포토 공정 오류 체크
                elif dose > 40 or dose < 20:
                    error_type = "Random"
                    fault_process = "포토 (Photo) 공정"
                    root_cause = f"노광량(Dose)이 {dose}mJ/cm²로 타겟 마진을 벗어남. 불완전한 광학 반응으로 인해 산발적인 패턴 무너짐이 발생했습니다."
                    action_plan = "스캐너(Scanner)의 광원 출력을 점검하고, 포토레지스트(PR) 도포 두께 균일도를 확인하십시오."
                
                else:
                    error_type = "Normal"
                    fault_process = "전 공정 (All Processes)"
                    root_cause = "모든 공정 파라미터가 최적 마진(Process Window) 내에 있습니다."
                    action_plan = "현재의 레시피(Recipe)를 유지하며 양산 공정을 지속하십시오."

                # --- 화면 출력부 ---
                col1, col2 = st.columns([1.2, 1])
                
                with col1:
                    st.subheader("🗺️ 계측 스캔 히트맵 (Surface Yield Map)")
                    # 웨이퍼 이미지 시뮬레이션
                    wafer_data = generate_realistic_wafer(error_type)
                    
                    fig, ax = plt.subplots(figsize=(6, 6))
                    fig.patch.set_facecolor('none') # 배경 투명
                    ax.set_facecolor('none')
                    
                    # RdYlGn_r 컬러맵: 초록색(정상/낮은수치) -> 노란색 -> 빨간색(불량/높은수치)
                    cmap = plt.cm.RdYlGn_r 
                    cmap.set_bad(color='white') # NaN 값(웨이퍼 밖)은 흰색 처리
                    
                    cax = ax.imshow(wafer_data, cmap=cmap, interpolation='gaussian')
                    
                    # 윤곽선 그리기 (웨이퍼 테두리)
                    circle = plt.Circle((100, 100), 100, color='black', fill=False, linewidth=1.5)
                    ax.add_patch(circle)
                    
                    ax.axis('off')
                    st.pyplot(fig)
                    
                with col2:
                    st.subheader("🤖 FDC (이상 감지) 분석 결과")
                    
                    if error_type == "Normal":
                        st.success("🟢 **상태: 정상 (Normal Yield)**")
                    else:
                        st.error(f"🔴 **상태: 수율 경보 발생 ({error_type} 패턴 감지)**")
                        
                    st.markdown("---")
                    st.markdown("### 🔍 Root Cause Analysis (원인 추적)")
                    st.markdown(f"**문제 발생 공정:** {fault_process}")
                    st.markdown(f"**상세 원인:** {root_cause}")
                    
                    st.markdown("### 🛠️ 엔지니어 액션 플랜")
                    st.markdown(f"> {action_plan}")

        else:
            st.info("👈 왼쪽 사이드바에서 공정 엔지니어가 되어 파라미터를 조작한 뒤, **'공정 시뮬레이션 실행'** 버튼을 클릭하세요.")

    except Exception as e:
        # 오류 발생 시 한국어로 구체적인 디버깅 안내 제공 (빈 화면 방지)
        st.error("🚨 화면 구성 또는 시뮬레이션 연산 중 오류가 발생했습니다.")
        st.markdown("""
        **[문제 해결 체크리스트]**
        1. **라이브러리 설치 확인:** `requirements.txt`에 `matplotlib`, `scipy`가 모두 포함되어 있는지 확인하세요.
        2. **캐시 문제:** 코드 수정 후 스트림릿 클라우드에 갱신되지 않은 경우일 수 있습니다. 화면 우측 상단의 'Clear cache'를 클릭한 뒤 새로고침 하세요.
        3. **연산 메모리 초과:** 무료 클라우드 환경에서 트래픽이 몰리면 일시적으로 발생할 수 있습니다. 앱을 재부팅(Reboot) 해보세요.
        """)
        st.expander("상세 에러 로그 보기").write(str(e))

if __name__ == "__main__":
    main()
