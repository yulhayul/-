import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import time
import pandas as pd

# =====================================================================
# 1. UI 기본 설정
# =====================================================================
st.set_page_config(page_title="반도체 8대 공정 시뮬레이터", layout="wide")

st.title("반도체 8대 공정 시뮬레이터 팹(FAB) 🚀")
st.write("사이드바에서 파라미터를 조절하여 수율(Yield) 99% 달성에 도전해 보세요! 파라미터가 권장 범위를 벗어나면 수율이 깎이고 불량이 발생합니다.")

# =====================================================================
# 2. [코드 최적화] 공정별 임계값(Threshold) 및 페널티 규칙 사전 정의
# =====================================================================
# limit: 불량 판정 기준값 / dir: over(초과시 불량), under(미달시 불량) / weight: 한계 돌파 시 수율 차감 가중치
PROCESS_SPECS = {
    1: {'key': 'ttv', 'limit': 1.8, 'dir': 'over', 'name': '1. 웨이퍼 제조', 'cause_fmt': "평탄도(TTV) {val}µm 과다", 'effect': "표면 굴곡으로 인한 포토 공정 초점 불량", 'defect': 'Defocus', 'weight': 15.0},
    2: {'key': 'oxi_temp', 'limit': 1050, 'dir': 'over', 'name': '2. 산화 공정', 'cause_fmt': "챔버 온도 {val}℃ 과열", 'effect': "웨이퍼 중앙부 산화막 두께 팽창", 'defect': 'Center', 'weight': 0.15},
    3: {'key': 'dose', 'limit': 25, 'dir': 'under', 'name': '3. 포토 공정', 'cause_fmt': "노광량 {val}mJ/cm² 부족", 'effect': "샷 노이즈(Shot noise) 발생 및 회로 단선", 'defect': 'Random', 'weight': 2.0},
    4: {'key': 'rf_power', 'limit': 500, 'dir': 'over', 'name': '4. 식각 공정', 'cause_fmt': "RF 파워 {val}W 과다", 'effect': "플라즈마 가장자리 쏠림 (링 결함)", 'defect': 'Ring', 'weight': 0.08},
    5: {'key': 'gas_flow', 'limit': 70, 'dir': 'over', 'name': '5. 박막 증착', 'cause_fmt': "가스 유량 {val}sccm 과다", 'effect': "가스 미확산으로 인한 도넛 형태 박막 뭉침", 'defect': 'Donut', 'weight': 0.8},
    6: {'key': 'pressure', 'limit': 4.5, 'dir': 'over', 'name': '6. 연마 공정 (CMP)', 'cause_fmt': "패드 누름 압력 {val}psi 과다", 'effect': "웨이퍼 표면 마이크로 스크래치 발생", 'defect': 'Scratch', 'weight': 8.0},
    7: {'key': 'probe_force', 'limit': 3.0, 'dir': 'over', 'name': '7. EDS 검사', 'cause_fmt': "프로브 핀 하중 {val}g 초과", 'effect': "패드 물리적 파임 및 접촉 불량", 'defect': 'ProbeMark', 'weight': 12.0},
    8: {'key': 'dicing_spd', 'limit': 65, 'dir': 'over', 'name': '8. 패키징', 'cause_fmt': "톱날 속도 {val}mm/s 과속", 'effect': "다이(Die) 가장자리 실리콘 깨짐(Chipping)", 'defect': 'EdgeChipping', 'weight': 1.2},
}

# =====================================================================
# 3. 공정별 웨이퍼 엔진 
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
# 4. 사이드바 파라미터 설정
# =====================================================================
st.sidebar.header("🎛️ 공정 파라미터 설정")

current_vals = {
    'ttv': st.sidebar.slider("1. 웨이퍼 평탄도 (TTV, µm)", 0.5, 3.0, 2.0, step=0.1),
    'oxi_temp': st.sidebar.slider("2. 산화 챔버 온도 (℃)", 800, 1200, 1000, step=10),
    'dose': st.sidebar.slider("3. 노광량 Dose (mJ/cm²)", 10, 60, 30, step=2),
    'rf_power': st.sidebar.slider("4. 식각 RF 파워 (W)", 200, 800, 400, step=10),
    'gas_flow': st.sidebar.slider("5. 증착 가스 유량 (sccm)", 20, 100, 50, step=5),
    'pressure': st.sidebar.slider("6. CMP 연마 압력 (psi)", 1.0, 8.0, 3.0, step=0.5),
    'probe_force': st.sidebar.slider("7. 테스트 프로브 하중 (g)", 1.0, 5.0, 2.0, step=0.2),
    'dicing_spd': st.sidebar.slider("8. 패키징 톱날 속도 (mm/s)", 30, 90, 50, step=5)
}

run_btn = st.sidebar.button("▶️ 시뮬레이션 시작", type="primary")

# =====================================================================
# 5. 시각화 및 실행 로직
# =====================================================================
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📡 실시간 Wafer 상태")
    progress_bar = st.empty() # UX 개선: 상태 진행률 바
    status_text = st.empty()
    wafer_placeholder = st.empty()

with col2:
    st.subheader("📊 생산 수율 및 불량 분석")
    yield_metric = st.empty() # 게이미피케이션: 실시간 수율 점수
    rca_placeholder = st.empty()

if run_btn:
    cumulative_defects = np.zeros((size, size))
    rca_report = []
    
    # 초기 수율 100%에서 시작
    current_yield = 100.0 
    yield_metric.metric("예상 최종 수율", f"{current_yield:.1f}%")
    
    my_bar = progress_bar.progress(0)
    
    # 8대 공정 연속 실행 (약 3~4초 소요)
    for step in range(1, 9):
        spec = PROCESS_SPECS[step]
        val = current_vals[spec['key']]
        
        is_defect = False
        penalty = 0.0
        
        # 임계값 초과/미달에 따른 수율 차감 로직 계산
        if spec['dir'] == 'over' and val > spec['limit']:
            is_defect = True
            penalty = (val - spec['limit']) * spec['weight']
        elif spec['dir'] == 'under' and val < spec['limit']:
            is_defect = True
            penalty = (spec['limit'] - val) * spec['weight']
            
        if is_defect:
            # 수율 깎임 반영
            current_yield = max(0.0, current_yield - penalty)
            cumulative_defects += get_defect_pattern(spec['defect'])
            
            # RCA 리포트 데이터 축적
            rca_report.append({
                "공정 단계": spec['name'], 
                "원인 (설정 오류)": spec['cause_fmt'].format(val=val), 
                "결과 (발생 결함)": spec['effect']
            })
            
        # UI 업데이트: 진행률, 텍스트, 수율 갱신
        my_bar.progress(step / 8.0)
        status_text.info(f"▶ 진행 중: {spec['name']} ... (현재 수율: {current_yield:.1f}%)")
        yield_metric.metric("예상 최종 수율", f"{current_yield:.1f}%", delta=f"-{penalty:.1f}%" if is_defect else "정상", delta_color="inverse")
            
        current_wafer = get_base_wafer(step) + cumulative_defects
        current_wafer[~wafer_mask] = np.nan
        
        # Matplotlib 최신 버전(3.7+) 호환 방식 적용
        fig, ax = plt.subplots(figsize=(5, 5), facecolor='black')
        ax.set_facecolor('black')
        cmap_name = 'bone' if np.max(cumulative_defects) == 0 else 'turbo'
        
        try:
            cmap_obj = plt.get_cmap(cmap_name).copy()
            cmap_obj.set_bad(color='black')
        except AttributeError:
            cmap_obj = plt.get_cmap(cmap_name).with_extremes(bad='black')
            
        ax.imshow(current_wafer, cmap=cmap_obj, interpolation='none', vmin=-0.2, vmax=1.5)
        ax.axis('off')
        
        wafer_placeholder.pyplot(fig)
        plt.close(fig)
        time.sleep(0.4) 

    # 시퀀스 완료 후 UI 정리
    status_text.success("전체 공정 시뮬레이션 완료!")
    my_bar.empty()

    # 결과 및 RCA 리포트 출력
    with rca_placeholder.container():
        if len(rca_report) > 0:
            st.error(f"🚨 **수율 저하 발생 (최종 수율: {current_yield:.1f}%)**")
            
            # DataFrame으로 변환하여 표 형태로 표시
            df_rca = pd.DataFrame(rca_report)
            st.table(df_rca)
            
            # 현장감 강화: CSV 다운로드 기능 (utf-8-sig로 인코딩하여 한글 깨짐 방지)
            csv_data = df_rca.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 RCA 분석 리포트 다운로드 (CSV 엑셀 파일)",
                data=csv_data,
                file_name="FAB_RCA_Report.csv",
                mime="text/csv",
                type="primary"
            )
        else:
            st.success("✅ **결함 없음 (Golden Yield 100%)**")
            st.write("모든 공정이 완벽하게 제어되었습니다. 생산된 칩은 스마트폰 및 TV 조립 라인으로 정상 출하됩니다.")
            st.balloons() # 만점 달성 시 축하 이펙트
