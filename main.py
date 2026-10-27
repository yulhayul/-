import streamlit as st
import time
import random

# =====================================================================
# 1. HMI Terminal 기본 설정 및 CSS (산업용 기계 느낌 극대화)
# =====================================================================
st.set_page_config(page_title="OSAT & App Integration Terminal", layout="wide")

st.markdown("""
<style>
    /* 배경 및 폰트 설정 (다크 테마, 모노스페이스) */
    .stApp { background-color: #0e1117; color: #00ff00; font-family: 'Courier New', monospace; }
    
    /* 터미널 로그창 스타일 */
    .terminal-box {
        background-color: #000000;
        border: 2px solid #333;
        border-radius: 5px;
        padding: 15px;
        height: 350px;
        overflow-y: auto;
        color: #00ff00;
        font-family: 'Courier New', Courier, monospace;
        font-size: 14px;
        line-height: 1.5;
        box-shadow: inset 0 0 10px #000;
    }
    
    /* 하드웨어 제어 버튼 스타일 */
    .stButton>button {
        width: 100%;
        border-radius: 2px;
        border: 1px solid #555;
        font-weight: bold;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    h1, h2, h3 { color: #00ff00 !important; }
    hr { border-color: #333; }
</style>
""", unsafe_allow_html=True)

# =====================================================================
# 2. 기계 상태(State) 관리 (Interlock 구현)
# =====================================================================
if 'sys_power' not in st.session_state: st.session_state.sys_power = False
if 'wafer_loaded' not in st.session_state: st.session_state.wafer_loaded = False
if 'logs' not in st.session_state: st.session_state.logs = ["[SYSTEM] OSAT Terminal Boot Sequence Initiated... OK"]

def add_log(msg):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {msg}")

# =====================================================================
# 3. UI 레이아웃 구성
# =====================================================================
st.markdown("## 🏭 [SYS-04] POST-FAB & APPLICATION ASSEMBLY HMI")
st.markdown("---")

col_hw, col_recipe, col_terminal = st.columns([1, 1, 1.8])

# ---------------------------------------------------------------------
# [패널 1] 하드웨어 제어부 (기계 스위치 조작)
# ---------------------------------------------------------------------
with col_hw:
    st.markdown("### 🎛️ HARDWARE CTRL")
    
    # MAIN POWER
    power_btn_text = "🔴 TURN POWER OFF" if st.session_state.sys_power else "🟢 TURN POWER ON"
    if st.button(power_btn_text):
        st.session_state.sys_power = not st.session_state.sys_power
        add_log(f"MAIN POWER {'ON' if st.session_state.sys_power else 'OFF'}")
        st.rerun()

    # WAFER LOAD
    load_btn_text = "⏏️ UNLOAD WAFER" if st.session_state.wafer_loaded else "📥 LOAD FABRICATED WAFER"
    if st.button(load_btn_text):
        if not st.session_state.sys_power:
            st.error("🚨 INTERLOCK ERROR: Main Power is OFF.")
            add_log("ERR: Load failed. System unpowered.")
        else:
            st.session_state.wafer_loaded = not st.session_state.wafer_loaded
            add_log(f"Wafer Cassette {'Unloaded' if not st.session_state.wafer_loaded else 'Loaded & Aligned'}.")
        st.rerun()

    st.markdown("---")
    st.markdown("#### ⚙️ SENSOR STATUS")
    st.write(f"🔌 POWER: `{'ONLINE' if st.session_state.sys_power else 'OFFLINE'}`")
    st.write(f"💿 WAFER: `{'CHAMBER IN' if st.session_state.wafer_loaded else 'EMPTY'}`")
    st.write(f"🌡️ TEMP : `{'24.5 °C' if st.session_state.sys_power else 'N/A'}`")

# ---------------------------------------------------------------------
# [패널 2] 후공정 레시피 조작부
# ---------------------------------------------------------------------
with col_recipe:
    st.markdown("### 📋 RECIPE SETUP")
    
    pkg_type = st.radio("Packaging Technique", ["Wire Bonding (Legacy)", "Flip Chip (Advanced)", "TSV (3D Stacking)"])
    
    target_app = st.selectbox("Target Application (최종 제품)", [
        "📱 Smartphone (Mobile AP)", 
        "📺 Smart TV (Display Driver IC)", 
        "🚗 Automotive (MCU)"
    ])
    
    dicing_speed = st.slider("Dicing Blade RPM", 20000, 60000, 40000, step=5000)
    
    st.markdown("<br>", unsafe_allow_html=True)
    run_btn = st.button("▶️ EXECUTE SEQUENCE", type="primary")

# ---------------------------------------------------------------------
# [패널 3] 실시간 터미널 출력 및 기계 구동 시뮬레이션
# ---------------------------------------------------------------------
with col_terminal:
    st.markdown("### 🖥️ SYSTEM CONSOLE")
    
    # 터미널 창을 위한 empty 컨테이너
    terminal_placeholder = st.empty()
    
    def render_terminal():
        log_html = "<br>".join(st.session_state.logs[-15:]) # 최근 15줄만 표시
        terminal_placeholder.markdown(f"<div class='terminal-box'>{log_html}</div>", unsafe_allow_html=True)
    
    render_terminal()

# =====================================================================
# 4. 기계 구동 로직 (Run Sequence)
# =====================================================================
if run_btn:
    if not st.session_state.sys_power:
        st.error("🚨 INTERLOCK ERROR: 전원을 먼저 켜십시오.")
    elif not st.session_state.wafer_loaded:
        st.error("🚨 INTERLOCK ERROR: 웨이퍼를 로딩하십시오.")
    else:
        # 터미널 로그 실시간 업데이트 시뮬레이션
        st.session_state.logs = ["[SYSTEM] Executing Back-end & Assembly Sequence..."]
        render_terminal()
        
        sequence_steps = [
            ("Initiating Dicing Saw...", 1.0),
            (f"Blade RPM stabilized at {dicing_speed}.", 0.5),
            ("Cutting wafer into individual dies... [||||||    ]", 1.5),
            ("Die sorting & Visual Inspection completed.", 0.8),
            (f"Starting Die Attach using {pkg_type} method...", 1.2),
            ("Connecting I/O terminals (Bonding)...", 1.5),
            ("Applying Epoxy Molding Compound (EMC)...", 1.0),
            ("Curing package in oven (175°C)...", 1.5),
            ("Final Package Test (Electrical & Thermal)... PASS.", 1.0),
            ("=======================================", 0.5),
            (f"Routing packaged chips to {target_app} assembly line...", 1.5),
            ("Mounting chip onto Main PCB...", 1.0),
            ("System integration & Final QA Check... OK.", 1.0)
        ]
        
        for msg, delay in sequence_steps:
            time.sleep(delay)
            add_log(msg)
            render_terminal()
            
        add_log("✅ SEQUENCE COMPLETE. PRODUCT READY FOR SHIPMENT.")
        render_terminal()
        
        st.success(f"성공적으로 패키징이 완료되어 **{target_app}** 메인보드에 탑재되었습니다!")
