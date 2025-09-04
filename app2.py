# app.py
# -------------------------------------------------------------
# Real‑Time AHP Site Suitability (Satellite + OSM + Manual + Map)
# Author: ChatGPT for Sara's friend (Geography)
# Run:  streamlit run app.py
# -------------------------------------------------------------

import math
import json
from datetime import date, timedelta
from typing import Dict, Any, Optional

import numpy as np
import pandas as pd
import requests
import streamlit as st

# Optional map embed (folium)
try:
    import folium
    from streamlit_folium import st_folium
except Exception:
    folium = None
    st_folium = None

st.set_page_config(
    page_title="Real-Time AHP Site Suitability",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ------------------------------
# Utilities
# ------------------------------
EARTH_R = 6371.0088  # km

def haversine_km(lat1, lon1, lat2, lon2):
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlmb/2)**2
    return 2 * EARTH_R * math.atan2(math.sqrt(a), math.sqrt(1-a))

@st.cache_data(show_spinner=False)
def cached_get(url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None, timeout: int = 25):
    r = requests.get(url, params=params, headers=headers, timeout=timeout)
    r.raise_for_status()
    return r.json()

# ------------------------------
# AHP Model
# ------------------------------
class AHPModel:
    def __init__(self):
        self.criteria = ['Technical', 'Environmental', 'Social']
        self.sub_criteria = {
            'Technical': ['Solar Radiation', 'Slope', 'Proximity to Grid', 'Land Cost'],
            'Environmental': ['Land Use', 'Distance from Protected Areas', 'Water Body Buffer'],
            'Social': ['Distance from Roads', 'Proximity to Demand Centers', 'Population Density']
        }
        self.main_weights = {'Technical':0.693, 'Environmental':0.187, 'Social':0.080}
        self.sub_weights_local = {
            'Technical': {'Solar Radiation':0.558, 'Slope':0.262, 'Proximity to Grid':0.130, 'Land Cost':0.050},
            'Environmental': {'Land Use':0.258, 'Distance from Protected Areas':0.637, 'Water Body Buffer':0.105},
            'Social': {'Distance from Roads':0.637, 'Proximity to Demand Centers':0.258, 'Population Density':0.105}
        }
        self.sub_weights_global = self._compute_global()

    def _compute_global(self):
        g = {}
        for crit in self.criteria:
            g[crit] = {sub: self.main_weights[crit]*w for sub, w in self.sub_weights_local[crit].items()}
        return g

    def set_main_weight(self, crit: str, value: float):
        self.main_weights[crit] = value
        self.sub_weights_global = self._compute_global()

    def set_local_weight(self, crit: str, sub: str, value: float):
        self.sub_weights_local[crit][sub] = value
        self.sub_weights_global = self._compute_global()

    def global_weight(self, crit: str, sub: str) -> float:
        return self.sub_weights_global[crit][sub]

    def score(self, site_values: Dict[str, float]) -> float:
        total = 0.0
        for crit in self.criteria:
            for sub in self.sub_criteria[crit]:
                v = float(site_values.get(sub, 0))
                total += v * self.sub_weights_global[crit][sub]
        max_sum = sum(self.sub_weights_global[crit][sub] for crit in self.criteria for sub in self.sub_criteria[crit])
        return total / max_sum if max_sum else 0.0

# ------------------------------
# Normalization helpers
# ------------------------------
def norm_benefit(x: Optional[float], min_v: float, max_v: float) -> float:
    if x is None: return 0.0
    if max_v == min_v: return 0.0
    return float(np.clip((x - min_v) / (max_v - min_v), 0.0, 1.0))

def norm_cost(x: Optional[float], min_v: float, max_v: float) -> float:
    if x is None: return 0.0
    if max_v == min_v: return 0.0
    return 1.0 - float(np.clip((x - min_v) / (max_v - min_v), 0.0, 1.0))

# ------------------------------
# Map helper: color by score
# ------------------------------
def score_to_color(score: float) -> str:
    if score >= 0.8: return 'green'
    if score >= 0.6: return 'yellow'
    if score >= 0.4: return 'orange'
    return 'red'

def score_to_text(score: float) -> str:
    if score >= 0.8: return "Highly Suitable"
    if score >= 0.6: return "Moderately Suitable"
    if score >= 0.4: return "Marginally Suitable"
    return "Not Suitable"

# ------------------------------
# Streamlit UI
# ------------------------------
st.title("🌍 India Solar Site Suitability (AHP)")
st.caption("Enter coordinates or a location, adjust weights, and view suitability visually.")

# Sidebar: AHP weights
with st.sidebar:
    st.header("Adjust AHP Weights")
    ahp = AHPModel()
    wT = st.number_input("Technical Weight", 0.0, 1.0, ahp.main_weights['Technical'], 0.01)
    wE = st.number_input("Environmental Weight", 0.0, 1.0, ahp.main_weights['Environmental'], 0.01)
    wS = st.number_input("Social Weight", 0.0, 1.0, ahp.main_weights['Social'], 0.01)
    total_main = wT + wE + wS
    if total_main == 0: total_main = 1.0
    ahp.set_main_weight('Technical', wT/total_main)
    ahp.set_main_weight('Environmental', wE/total_main)
    ahp.set_main_weight('Social', wS/total_main)

# Main input
st.subheader("1️⃣ Location Input")
lat = st.number_input("Latitude", 6.0, 37.0, 22.7196, 0.0001)
lon = st.number_input("Longitude", 68.0, 97.0, 75.8577, 0.0001)

st.subheader("2️⃣ Normalized Criteria (0–1)")
site_values = {}
site_values['Solar Radiation'] = st.slider("Solar Radiation", 0.0, 1.0, 0.7)
site_values['Slope'] = st.slider("Slope", 0.0, 1.0, 0.8)
site_values['Proximity to Grid'] = st.slider("Proximity to Grid", 0.0, 1.0, 0.6)
site_values['Land Cost'] = st.slider("Land Cost", 0.0, 1.0, 0.5)
site_values['Land Use'] = st.slider("Land Use", 0.0, 1.0, 0.7)
site_values['Distance from Protected Areas'] = st.slider("Distance from Protected Areas", 0.0, 1.0, 0.6)
site_values['Water Body Buffer'] = st.slider("Water Body Buffer", 0.0, 1.0, 0.5)
site_values['Distance from Roads'] = st.slider("Distance from Roads", 0.0, 1.0, 0.7)
site_values['Proximity to Demand Centers'] = st.slider("Proximity to Demand Centers", 0.0, 1.0, 0.6)
site_values['Population Density'] = st.slider("Population Density", 0.0, 1.0, 0.5)

score = ahp.score(site_values)
rec_text = score_to_text(score)
color = score_to_color(score)

st.subheader("3️⃣ Final Suitability Score")
st.progress(min(max(score,0),1), text=f"Score: {score:.3f}")
st.success(f"Recommendation: {rec_text}")

# ------------------------------
# Map
# ------------------------------
st.subheader("4️⃣ Map Visualization")
if folium:
    m = folium.Map(location=[22.0,78.0], zoom_start=5)  # India-centered
    folium.CircleMarker(
        location=[lat, lon],
        radius=15,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.7,
        popup=f"Score: {score:.3f}\nRecommendation: {rec_text}"
    ).add_to(m)
    st_folium(m, height=500)
else:
    st.info("Install folium + streamlit-folium to view the map: pip install folium streamlit-folium")
