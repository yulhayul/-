import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
import time
import pandas as pd
import random
from datetime import datetime

# =====================================================================
# 1. UI 기본 설정 및 Session State 초기화
# =====================================================================
st.set_page_config(page_title="FAB 공정 & 수율 분석 시스템", layout="wide")

st.title("반도체 8대 공정 & 수율(Yield) 분석 시스템 🏭")
st.write("실제 팹(FAB)의 데이터를 모사합니다. 파라미터를 조절하거나 랜덤 시나리오를 발생시켜 불량 원인과 재무적 손실을 분석하세요.")

if 'spc_history' not in st.session_state:
    st.session_state.spc_history = []

# =====================================================================
# 2. [가이드 & 랜덤 시나리오] 기능 구현
# =====================================================================
def set_random_scenario():
    """랜덤한 파라미터 값으로 세션 스테이트를 덮어씌워 무작위 불량 시나리오 생성"""
    st.session_state.ttv = round(random.uniform(0.5, 3.0), 1)
    st.session_state.oxi_temp = random.randint(800, 1200)
    st.session_state.dose = random.randint(10, 60)
    st.session_state.rf_power = random.randint(200, 800)
    st.session_state.gas_flow = random.randint(20, 100)
    st.session_state.pressure = round(random.uniform(1.0, 8.0), 1)
    st.session_state.probe_force = round(random.uniform(1.0, 5.0), 1)
    st.session_state.dicing_spd = random.randint(30, 90)

# =====================================================================
# 3. 공정별 임계값 및 페널티 룰 (리포트용 단위 및 기준 텍스트 추가)
# =====================================================================
PROCESS_SPECS = {
    1: {'key': 'ttv', 'limit': 1.8, 'dir': 'over', 'unit': 'µm', 'target': '1.8 이하', 'name': '1. 웨이퍼 제조', 'cause': "평탄도(TTV) 과다", 'effect': "표면 굴곡 -> 포토 초점 불량", 'defect': 'Defocus', 'weight': 15.0},
    2: {'key': 'oxi_temp', 'limit': 1050, 'dir': 'over', 'unit': '℃', 'target': '1050 이하', 'name': '2. 산화 공정', 'cause': "챔버 온도 과열", 'effect': "산화막 두께 팽창", 'defect': 'Center', 'weight': 0.15},
    3: {'key': 'dose', 'limit': 25, 'dir': 'under', 'unit': 'mJ/cm²', 'target': '25 이상', 'name': '3. 포토 공정', 'cause': "노광량 부족", 'effect': "샷 노이즈 -> 회로 단선", 'defect': 'Random', 'weight': 2.0},
    4: {'key': 'rf_power', 'limit': 500, 'dir': 'over', 'unit': 'W', 'target': '500 이하', 'name': '4. 식각 공정', 'cause': "RF 파워 과다", 'effect': "플라즈마 가장자리 쏠림 (Ring)", 'defect': 'Ring', 'weight': 0.08},
    5: {'key': 'gas_flow', 'limit': 70, 'dir': 'over', 'unit': 'sccm', 'target': '70 이하', 'name': '5. 박막 증착', 'cause': "가스 유량 과다", 'effect': "가스 미확산 (Donut 뭉침)", 'defect': 'Donut', 'weight': 0.8},
    6: {'key': 'pressure', 'limit': 4.5, 'dir': 'over', 'unit': 'psi', 'target': '4.5 이하', 'name': '6. 연마 (CMP)', 'cause': "패드 압력 과다", 'effect': "마이크로 스크래치 발생", 'defect': 'Scratch', 'weight': 8.0},
    7: {'key': 'probe_force', 'limit': 3.0, 'dir': 'over', 'unit': 'g', 'target': '3.0 이하', 'name': '7. EDS 검사', 'cause': "프로브 하중 초과", 'effect': "패드 물리적 파임", 'defect': 'ProbeMark', 'weight': 12.0},
    8: {'key': 'dicing_spd', 'limit': 65, 'dir': 'over', 'unit': 'mm/s', 'target': '65 이하', 'name': '8. 패키징', 'cause': "다이싱 톱날 속도 과속", 'effect': "실리콘 엣지 깨짐(Chipping)", 'defect': 'EdgeChipping', 'weight': 1.2},
}

# =====================================================================
# 4. 사이드바 UI (파라미터 & 툴팁)
# =====================================================================
st.sidebar.header("🎛️ 공정 파라미터 제어")
st.sidebar.button("🎲 랜덤 불량 시나리오 생성", on_click=set_random_scenario, type="secondary", use_container_width=True)
st.sidebar.divider()

current_vals = {
    'ttv': st.sidebar.slider("1. 웨이퍼 평탄도 (TTV, µm)", 0.5, 3.0, key='ttv', value=2.0, step=0.1, help="권장 타겟: 1.8 µm 이하 (초과 시 초점 불량)"),
    'oxi_temp': st.sidebar.slider("2. 산화 챔버 온도 (℃)", 800, 1200, key='oxi_temp', value=1000, step=10, help="권장 타겟: 1050 ℃ 이하 (초과 시 산화막 팽창)"),
    'dose': st.sidebar.slider("3. 노광량 Dose (mJ/cm²)", 10, 60, key='dose', value=30, step=2, help="권장 타겟: 25 mJ/cm² 이상 (미달 시 회로 단선)"),
    'rf_power': st.sidebar.slider("4. 식각 RF 파워 (W)", 200, 800, key='rf_power', value=400, step=10, help="권장 타겟: 500 W 이하 (초과 시 플라즈마 쏠림)"),
    'gas_flow': st.sidebar.slider("5. 증착 가스 유량 (sccm)", 20, 100, key='gas_flow', value=50, step=5, help="권장 타겟: 70 sccm 이하 (초과 시 박막 뭉침)"),
    'pressure': st.sidebar.slider("6. CMP 연마 압력 (psi)", 1.0, 8.0, key='pressure', value=3.0, step=0.5, help="권장 타겟: 4.5 psi 이하 (초과 시 스크래치)"),
    'probe_force': st.sidebar.slider("7. 테스트 프로브 하중 (g)", 1.0, 5.0, key='probe_force', value=2.0, step=0.2, help="권장 타겟: 3.0 g 이하 (초과 시 패드 파손)"),
    'dicing_spd': st.sidebar.slider("8. 패키징 톱날 속도 (mm/s)", 30, 90, key='dicing_spd', value=50, step=5, help="권장 타겟: 65 mm/s 이하 (초과 시 칩 깨짐)")
}

run_btn = st.sidebar.button("▶️ 생산 시뮬레이션 시작", type="primary", use_container_width=True)

# =====================================================================
# 5. 물리 엔진 (웨이퍼 및 결함 렌더링)
# =====================================================================
size = 250
x, y = np.meshgrid(np.linspace(-1, 1, size), np.linspace(-1, 1, size))
R = np.sqrt(x**2 + y**2)
wafer_mask = (R <= 1.0) & ~((R > 0.96) & (np.abs(np.arctan2(y, x) + np.pi/2) < 0.05))

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
# 6. 메인 UI 레이아웃
# =====================================================================
col_dash1, col_dash2, col_dash3 = st.columns(3)
m_yield = col_dash1.empty()
m_dies = col_dash2.empty()
m_loss = col_dash3.empty()

progress_bar = st.empty()
status_text = st.empty()

col_visual, col_spc = st.columns([1.2, 1])
with col_visual:
    st.subheader("📡 Wafer & Die Map 시각화")
    wafer_placeholder = st.empty()
with col_spc:
    st.subheader("📉 SPC 공정 능력 트렌드 (최근 기록)")
    spc_placeholder = st.empty()

if len(st.session_state.spc_history) > 0:
    spc_placeholder.line_chart(pd.DataFrame({"Yield (%)": st.session_state.spc_history}), height=300)

rca_placeholder = st.empty()

# =====================================================================
# 7. 시뮬레이션 및 데이터 시각화 실행
# =====================================================================
if run_btn:
    cumulative_defects = np.zeros((size, size))
    rca_report = []
    current_yield_pct = 100.0
    
    m_yield.metric("예상 공정 수율", "100.0%")
    m_dies.metric("생산 칩(Die) 현황", "분석 중...")
    m_loss.metric("재무적 손실 비용", "계산 중...")
    
    # 1) 공정 시각화 루프
    for step in range(1, 9):
        spec = PROCESS_SPECS[step]
        val = current_vals[spec['key']]
        is_defect = False
        
        if spec['dir'] == 'over' and val > spec['limit']: is_defect = True
        elif spec['dir'] == 'under' and val < spec['limit']: is_defect = True
            
        if is_defect:
            cumulative_defects += get_defect_pattern(spec['defect'])
            # 엑셀 다운로드를 고려하여 리포트 구조를 명확히 세분화
            rca_report.append({
                "공정명": spec['name'], 
                "권장 기준값": f"{spec['target']} {spec['unit']}",
                "나의 설정값": f"{val} {spec['unit']}",
                "발생 결함": spec['effect'],
                "상세 원인": spec['cause']
            })
            current_yield_pct -= spec['weight']
            
        progress_bar.progress(step / 8.0)
        status_text.info(f"▶ 진행 중: {spec['name']}... (표면 스캔)")
        
        current_wafer = get_base_wafer(step) + cumulative_defects
        current_wafer[~wafer_mask] = np.nan
        
        fig, ax = plt.subplots(figsize=(6, 5), facecolor='black')
        ax.set_facecolor('black')
        cmap_name = 'bone' if np.max(cumulative_defects) == 0 else 'turbo'
        try:
            cmap_obj = plt.get_cmap(cmap_name).copy()
            cmap_obj.set_bad(color='black')
        except AttributeError:
            cmap_obj = plt.get_cmap(cmap_name).with_extremes(bad='black')
            
        ax.imshow(current_wafer, cmap=cmap_obj, interpolation='none', vmin=-0.2, vmax=1.5, extent=[-1,1,-1,1])
        ax.axis('off')
        wafer_placeholder.pyplot(fig)
        plt.close(fig)
        time.sleep(0.4)
        
    status_text.success("표면 스캔 완료. 칩(Die) 단위 수율 및 재무 손실 계산 중...")
    progress_bar.empty()

    # 2) Die Map 및 비즈니스 임팩트 계산
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5), facecolor='black')
    
    ax1.set_facecolor('black')
    ax1.imshow(current_wafer, cmap=cmap_obj, interpolation='none', vmin=-0.2, vmax=1.5, extent=[-1,1,-1,1])
    ax1.axis('off')
    ax1.set_title("Physical Wafer Surface", color='white')
    
    ax2.set_facecolor('black')
    ax2.plot(np.cos(np.linspace(0, 2*np.pi, 100)), np.sin(np.linspace(0, 2*np.pi, 100)), color='gray', linewidth=2)
    
    grid_size = 22
    die_step = 2.0 / grid_size
    total_dies = 0
    fail_dies = 0
    
    for i in range(grid_size):
        for j in range(grid_size):
            x_min, y_min = -1.0 + j * die_step, -1.0 + i * die_step
            cx, cy = x_min + die_step/2, y_min + die_step/2
            
            if np.sqrt(cx**2 + cy**2) <= 0.95:
                total_dies += 1
                px_min, px_max = int((x_min+1)/2*size), int((x_min+die_step+1)/2*size)
                py_min, py_max = int((y_min+1)/2*size), int((y_min+die_step+1)/2*size)
                defect_area = cumulative_defects[py_min:py_max, px_min:px_max]
                
                if np.max(defect_area) > 0.05:
                    fail_dies += 1
                    color = '#ff3333'
                else:
                    color = '#33cc33'
                    
                import matplotlib.patches as patches
                rect = patches.Rectangle((x_min, y_min), die_step, die_step, linewidth=0.5, edgecolor='black', facecolor=color, alpha=0.8)
                ax2.add_patch(rect)
                
    ax2.set_xlim(-1.1, 1.1)
    ax2.set_ylim(-1.1, 1.1)
    ax2.axis('off')
    ax2.set_title("Pass/Fail Die Map", color='white')
    
    wafer_placeholder.pyplot(fig)
    plt.close(fig)

    # 3) 대시보드 지표 및 통계 업데이트
    good_dies = total_dies - fail_dies
    final_yield = (good_dies / total_dies * 100) if total_dies > 0 else 0
    DIE_PRICE = 50000
    total_revenue = total_dies * DIE_PRICE
    financial_loss = fail_dies * DIE_PRICE

    st.session_state.spc_history.append(final_yield)
    spc_placeholder.line_chart(pd.DataFrame({"Yield (%)": st.session_state.spc_history}), height=300)

    m_yield.metric("최종 확정 수율 (Die Yield)", f"{final_yield:.1f}%", delta=f"-{(100-final_yield):.1f}%" if final_yield < 100 else "Golden!", delta_color="inverse")
    m_dies.metric("생산 칩(Die) 현황", f"{good_dies}개 Pass", delta=f"{fail_dies}개 Fail", delta_color="inverse")
    m_loss.metric("재무적 손실 비용", f"-{financial_loss:,} 원", help=f"칩 단가 {DIE_PRICE:,}원 기준")
    
    status_text.empty()

    # 4) 불량 분석 (RCA) 리포트 다운로드
    with rca_placeholder.container():
        st.divider()
        if len(rca_report) > 0:
            st.error(f"🚨 **수율 저하 감지: {fail_dies}개의 칩이 폐기 처리되었습니다.**")
            df_rca = pd.DataFrame(rca_report)
            st.table(df_rca)
            
            # 리포트 다운로드 파일명에 타임스탬프 추가 (파일 덮어쓰기 방지)
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_data = df_rca.to_csv(index=False).encode('utf-8-sig')
            
            st.download_button(
                label="📥 RCA 원인 분석 리포트 다운로드 (CSV 엑셀)", 
                data=csv_data, 
                file_name=f"FAB_RCA_Report_{current_time}.csv", 
                mime="text/csv", 
                type="primary"
            )
        else:
            st.success(f"✅ **결함 없음 (Golden Yield 100%)** - 총 잠재 매출: {total_revenue:,} 원 확보!")
            st.balloons()
