# app.py
# -------------------------------------------------------------
# Real‑Time AHP Site Suitability (Satellite + OSM + Manual)
# Author: ChatGPT for Sara's friend (Geography)
# Run:  streamlit run app.py
# -------------------------------------------------------------

import math
import json
import time
from datetime import date, timedelta
from typing import Dict, Any, Tuple, Optional, List

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
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': "🌍 Real-Time AHP Site Suitability\nBuilt with Python + Streamlit"
    }
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
        # expects values in 0..1
        total = 0.0
        for crit in self.criteria:
            for sub in self.sub_criteria[crit]:
                v = float(site_values.get(sub, 0))
                total += v * self.sub_weights_global[crit][sub]
        # normalize by theoretical max (all ones)
        max_sum = 0.0
        for crit in self.criteria:
            for sub in self.sub_criteria[crit]:
                max_sum += 1.0 * self.sub_weights_global[crit][sub]
        return total / max_sum if max_sum else 0.0

# ------------------------------
# Fetchers (External APIs)
# ------------------------------
# 1) NASA POWER: ALLSKY_SFC_SW_DWN (kWh/m^2/day) – Global Horizontal Irradiance

@st.cache_data(show_spinner=True)
def get_nasa_power(lat: float, lon: float, days: int = 30) -> Optional[float]:
    try:
        end = date.today()
        start = end - timedelta(days=days)
        params = {
            "latitude": lat,
            "longitude": lon,
            "parameters": "ALLSKY_SFC_SW_DWN",
            "community": "RE",
            "format": "JSON",
            "start": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
        }
        url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        data = cached_get(url, params=params)
        series = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
        vals = list(series.values())
        vals = [v for v in vals if v is not None]
        return float(np.mean(vals)) if vals else None
    except Exception:
        return None

# 2) OpenTopoData SRTM90m elevation -> derive slope by sampling 3x3 window (~100m offsets)
@st.cache_data(show_spinner=True)
def get_slope_deg(lat: float, lon: float) -> Optional[float]:
    # sample grid ~ 0.001 deg (~100 m at equator)
    try:
        offsets = [-0.001, 0.0, 0.001]
        pts = [(lat+dy, lon+dx) for dy in offsets for dx in offsets]
        locs = "|".join([f"{p[0]},{p[1]}" for p in pts])
        url = "https://api.opentopodata.org/v1/srtm90m"
        data = cached_get(url, params={"locations": locs})
        elev = np.array([r.get("elevation") for r in data.get("results", [])]).reshape(3,3)
        if elev.size != 9 or np.any(pd.isna(elev)):
            return None
        # gradient using central differences
        # dx ~ east-west, dy ~ north-south
        dz_dx = (elev[1,2] - elev[1,0]) / (2 * 111000 * math.cos(math.radians(lat)))  # m per meter
        dz_dy = (elev[2,1] - elev[0,1]) / (2 * 111000)
        slope_rad = math.atan(math.sqrt(dz_dx**2 + dz_dy**2))
        return math.degrees(slope_rad)
    except Exception:
        return None

# 3) Overpass API helpers (OSM)
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

OSM_QUERIES = {
    "roads": "way[highway]",
    "power": "(way[power=line]; node[power=substation]; way[power=substation];)",
    "water": "(way[natural=water]; way[waterway=river]; relation[waterway=river];)",
    "protected": "(relation[boundary=protected_area]; way[leisure=nature_reserve]; relation[leisure=nature_reserve];)",
    "demand": "(node[place=city]; node[place=town]; node[place=village];)"
}

@st.cache_data(show_spinner=True)
def overpass_nearest_distance_km(lat: float, lon: float, key: str, radius_km: float = 20.0, max_radius_km: float = 60.0) -> Optional[float]:
    if key not in OSM_QUERIES:
        return None
    rad = radius_km
    while rad <= max_radius_km:
        bbox = f"{lat-rad/111.0},{lon-rad/111.0},{lat+rad/111.0},{lon+rad/111.0}"
        q = f"[out:json][timeout:25];({OSM_QUERIES[key]}(bbox:{bbox}););out center 200;"
        try:
            data = requests.post(OVERPASS_URL, data={"data": q}, timeout=30)
            data.raise_for_status()
            js = data.json()
            if not js.get("elements"):
                rad *= 1.7
                continue
            dmin = None
            for el in js["elements"]:
                if "lat" in el and "lon" in el:
                    d = haversine_km(lat, lon, el["lat"], el["lon"]) 
                elif "center" in el:
                    d = haversine_km(lat, lon, el["center"]["lat"], el["center"]["lon"])
                else:
                    continue
                dmin = d if (dmin is None or d < dmin) else dmin
            return dmin
        except Exception:
            return None
    return None

# 4) Land use (simple): query landuse tag around point and return most common category within small radius
@st.cache_data(show_spinner=True)
def get_landuse(lat: float, lon: float, radius_km: float = 2.0) -> Optional[str]:
    bbox = f"{lat-radius_km/111.0},{lon-radius_km/111.0},{lat+radius_km/111.0},{lon+radius_km/111.0}"
    q = """
    [out:json][timeout:25];
    (
      way[landuse](bbox:__BBOX__);
      relation[landuse](bbox:__BBOX__);
    );
    out tags center 150;
    """.replace("__BBOX__", bbox)
    try:
        data = requests.post(OVERPASS_URL, data={"data": q}, timeout=30)
        data.raise_for_status()
        js = data.json()
        tags = [el.get("tags", {}).get("landuse") for el in js.get("elements", []) if el.get("tags", {}).get("landuse")]
        if not tags:
            return None
        # return most frequent
        vals, counts = np.unique(tags, return_counts=True)
        return vals[np.argmax(counts)]
    except Exception:
        return None

# ------------------------------
# Normalization helpers (0..1)
# ------------------------------
# For benefit criteria (higher is better): min-max with cap

def norm_benefit(x: Optional[float], min_v: float, max_v: float) -> float:
    if x is None:
        return 0.0
    if max_v == min_v:
        return 0.0
    return float(np.clip((x - min_v) / (max_v - min_v), 0.0, 1.0))

# For cost/distance criteria (lower is better): 1 - min-max with cap

def norm_cost(x: Optional[float], min_v: float, max_v: float) -> float:
    if x is None:
        return 0.0
    if max_v == min_v:
        return 0.0
    z = float(np.clip((x - min_v) / (max_v - min_v), 0.0, 1.0))
    return 1.0 - z

# Land use simple scores (editable in UI)
DEFAULT_LANDUSE_SCORES = {
    "farmland": 0.8,
    "industrial": 0.2,
    "residential": 0.3,
    "forest": 0.2,
    "meadow": 0.6,
    "grass": 0.6,
    "brownfield": 0.7,
    "greenfield": 0.9,
    "commercial": 0.3,
    "retail": 0.3,
}

# ------------------------------
# Streamlit UI
# ------------------------------
# st.set_page_config(
#     page_title="Real-Time AHP Site Suitability",
#     page_icon="🌍",
#     layout="wide",
#     initial_sidebar_state="expanded",
#     menu_items={
#         'Get Help': None,
#         'Report a bug': None,
#         'About': "🌍 Real-Time AHP Site Suitability\nBuilt with Python + Streamlit"
#     }
# )

st.title("🌍 Real‑Time AHP Site Suitability")
st.caption("Enter a location, fetch live layers (Solar, Slope, OSM proximity), adjust AHP weights, and see suitability in real time.")

with st.sidebar:
    st.header("AHP Weights")
    st.write("Adjust main criteria weights (must sum ≈ 1.0)")
    ahp = AHPModel()
    col1, col2, col3 = st.columns(3)
    with col1:
        wT = st.number_input("Technical", min_value=0.0, max_value=1.0, value=ahp.main_weights['Technical'], step=0.01)
    with col2:
        wE = st.number_input("Environmental", min_value=0.0, max_value=1.0, value=ahp.main_weights['Environmental'], step=0.01)
    with col3:
        wS = st.number_input("Social", min_value=0.0, max_value=1.0, value=ahp.main_weights['Social'], step=0.01)
    total_main = wT + wE + wS
    if total_main == 0:
        total_main = 1.0
    ahp.set_main_weight('Technical', wT/total_main)
    ahp.set_main_weight('Environmental', wE/total_main)
    ahp.set_main_weight('Social', wS/total_main)

    st.divider()
    st.write("Local sub‑criteria weights (each group sums ≈ 1.0)")
    for crit in ahp.criteria:
        st.markdown(f"**{crit}**")
        subs = ahp.sub_criteria[crit]
        cols = st.columns(len(subs))
        vals = []
        for i, sub in enumerate(subs):
            default = ahp.sub_weights_local[crit][sub]
            vals.append(cols[i].number_input(sub, min_value=0.0, max_value=1.0, value=float(default), step=0.01))
        s = sum(vals) if sum(vals) > 0 else 1.0
        for sub, v in zip(subs, vals):
            ahp.set_local_weight(crit, sub, v/s)

    st.divider()
    st.subheader("Normalization Caps")
    ghi_min = st.number_input("Solar Radiation min (kWh/m²/day)", 0.0, 10.0, 3.0, 0.1)
    ghi_max = st.number_input("Solar Radiation max (kWh/m²/day)", 0.0, 10.0, 7.0, 0.1)

    slope_min = st.number_input("Slope min (deg)", 0.0, 90.0, 0.0, 0.5)
    slope_max = st.number_input("Slope max (deg) [flatter better]", 0.0, 90.0, 15.0, 0.5)

    dist_cap = st.number_input("Distance cap for proximity (km)", 1.0, 200.0, 30.0, 1.0)

    st.divider()
    st.subheader("Land Use Scoring (editable)")
    lu_scores = DEFAULT_LANDUSE_SCORES.copy()
    for k in list(lu_scores.keys()):
        lu_scores[k] = st.slider(f"{k}", 0.0, 1.0, float(lu_scores[k]), 0.05)
    custom_lu = st.text_input("Add custom landuse:score (comma‑sep, e.g. quarry:0.2, orchard:0.7)")
    if custom_lu:
        parts = [p.strip() for p in custom_lu.split(',') if ':' in p]
        for p in parts:
            k, v = p.split(':', 1)
            try:
                lu_scores[k.strip()] = float(v)
            except Exception:
                pass

# Main layout
colL, colR = st.columns([1,1])
with colL:
    st.subheader("1) Location Input")
    lat = st.number_input("Latitude", -89.9, 89.9, 22.7196, 0.0001)
    lon = st.number_input("Longitude", -179.9, 179.9, 75.8577, 0.0001)
    st.write("Tip: paste coordinates of any point you want to assess.")
    do_fetch = st.button("Fetch Live Layers")

    st.subheader("2) Raw Layer Values")
    if do_fetch:
        with st.spinner("Fetching layers..."):
            ghi = get_nasa_power(lat, lon)
            slope = get_slope_deg(lat, lon)
            d_road = overpass_nearest_distance_km(lat, lon, "roads")
            d_power = overpass_nearest_distance_km(lat, lon, "power")
            d_water = overpass_nearest_distance_km(lat, lon, "water")
            d_prot = overpass_nearest_distance_km(lat, lon, "protected")
            d_dem = overpass_nearest_distance_km(lat, lon, "demand")
            landuse = get_landuse(lat, lon)

            raw = {
                "Latitude": lat,
                "Longitude": lon,
                "Solar Radiation kWh/m²/day": ghi,
                "Slope deg": slope,
                "Nearest Road km": d_road,
                "Nearest Power Grid km": d_power,
                "Nearest Water km": d_water,
                "Nearest Protected Area km": d_prot,
                "Nearest Demand Center km": d_dem,
                "Land Use (OSM)": landuse,
            }
            st.table(pd.DataFrame([raw]))
            st.session_state["raw_layers"] = raw

    raw_layers = st.session_state.get("raw_layers")

    st.subheader("3) Enter/Override Manual Values (optional)")
    st.caption("If an auto value is missing or you prefer manual, enter 0..1 normalized values below. Leave blank to use auto.")
    manual = {}
    # Manual entries for sub‑criteria (0..1)
    for crit in ahp.criteria:
        st.markdown(f"**{crit}**")
        for sub in ahp.sub_criteria[crit]:
            manual[sub] = st.text_input(f"Manual {sub} (0..1)", key=f"manual_{sub}")

with colR:
    st.subheader("4) Normalization & Scoring")
    auto_norm = {}
    # Compute auto normalized values from raw_layers
    if raw_layers:
        # Technical
        auto_norm['Solar Radiation'] = norm_benefit(raw_layers.get('Solar Radiation kWh/m²/day'), ghi_min, ghi_max)
        auto_norm['Slope'] = norm_cost(raw_layers.get('Slope deg'), slope_min, slope_max)
        auto_norm['Proximity to Grid'] = norm_cost(raw_layers.get('Nearest Power Grid km'), 0.0, float(dist_cap))
        # Environmental
        lu_tag = raw_layers.get('Land Use (OSM)')
        auto_norm['Land Use'] = float(lu_scores.get(lu_tag, 0.5)) if lu_tag else 0.5
        auto_norm['Distance from Protected Areas'] = norm_cost(raw_layers.get('Nearest Protected Area km'), 0.0, float(dist_cap))
        auto_norm['Water Body Buffer'] = norm_cost(raw_layers.get('Nearest Water km'), 0.0, float(dist_cap))
        # Social
        auto_norm['Distance from Roads'] = norm_cost(raw_layers.get('Nearest Road km'), 0.0, float(dist_cap))
        auto_norm['Proximity to Demand Centers'] = norm_cost(raw_layers.get('Nearest Demand Center km'), 0.0, float(dist_cap))
        # Population Density left manual
        auto_norm['Population Density'] = None

    # Merge manual overrides (0..1) if provided
    site_values: Dict[str, float] = {}
    for crit in ahp.criteria:
        for sub in ahp.sub_criteria[crit]:
            mval = manual.get(sub)
            if mval is not None and mval.strip() != "":
                try:
                    site_values[sub] = float(mval)
                except Exception:
                    site_values[sub] = 0.0
            else:
                v = auto_norm.get(sub)
                site_values[sub] = float(v) if (v is not None) else 0.0

    if site_values:
        df_vals = pd.DataFrame([{**site_values}])
        st.markdown("**Normalized (0..1) sub‑criteria values**")
        st.table(df_vals)

        score = ahp.score(site_values)
        st.markdown("### Final Suitability Score")
        st.progress(min(max(score, 0.0), 1.0), text=f"Score: {score:.3f}")

        if score >= 0.8:
            rec = "Highly Suitable"
        elif score >= 0.6:
            rec = "Moderately Suitable"
        elif score >= 0.4:
            rec = "Marginally Suitable"
        else:
            rec = "Not Suitable"
        st.success(f"Recommendation: {rec}")

        # Show weights tables
        st.markdown("### Weights")
        st.write("**Main criteria**")
        st.table(pd.DataFrame([ahp.main_weights]))
        st.write("**Sub‑criteria (Local)**")
        st.table(pd.DataFrame(ahp.sub_weights_local))
        # Global weights as flat table
        gw_rows = []
        for crit in ahp.criteria:
            for sub in ahp.sub_criteria[crit]:
                gw_rows.append({"Criterion": crit, "Sub‑criterion": sub, "Global Weight": ahp.global_weight(crit, sub)})
        st.table(pd.DataFrame(gw_rows))

    # Map (optional)
    st.subheader("5) Map Preview (nearest features)")
    if folium and raw_layers:
        m = folium.Map(location=[lat, lon], zoom_start=11)
        folium.Marker([lat, lon], popup="Site").add_to(m)
        # draw approximate circles for distances
        def draw_circle(d_km, color, label):
            if d_km is None:
                return
            folium.Circle([lat, lon], radius=d_km*1000, color=color, fill=False, tooltip=f"~{label}: {d_km:.1f} km").add_to(m)
        draw_circle(raw_layers.get('Nearest Road km'), 'blue', 'road')
        draw_circle(raw_layers.get('Nearest Power Grid km'), 'green', 'grid')
        draw_circle(raw_layers.get('Nearest Water km'), 'cyan', 'water')
        draw_circle(raw_layers.get('Nearest Protected Area km'), 'red', 'protected')
        draw_circle(raw_layers.get('Nearest Demand Center km'), 'purple', 'demand center')
        st_folium(m, height=450)
    else:
        if not folium:
            st.info("Install folium + streamlit-folium for map: pip install folium streamlit-folium")

st.divider()
st.markdown(
"""
**How this works**
1. Enter latitude/longitude and click **Fetch Live Layers**.
2. The app calls:
   - **NASA POWER** for recent solar radiation (GHI).
   - **OpenTopoData SRTM90m** to derive **slope**.
   - **OpenStreetMap Overpass** to find nearest **roads, power grid, water, protected areas, demand centers**.
   - **OSM landuse** tag near the point.
3. Values are normalized to 0–1 using the caps you set.
4. AHP weights (main + local) are applied to compute the final suitability score and recommendation.
5. You may override any sub‑criterion manually (0–1) for full control.

**Notes**
- If an API is busy/unavailable, that value will show as missing; you can enter it manually.
- Distances are approximated to nearest features found in the search radius.
- Population density & Land cost are not auto‑fetched; enter them manually as normalized values.

**Install**
```bash
pip install streamlit requests numpy pandas folium streamlit-folium
```
Run:
```bash
streamlit run app.py
```
"""
)
