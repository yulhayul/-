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
