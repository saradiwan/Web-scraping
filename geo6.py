# land_image_enhancer_classic_only.py
import streamlit as st
from PIL import Image, ImageEnhance, ImageFilter
import io
import os
import numpy as np
import cv2
from streamlit_image_comparison import image_comparison

st.set_page_config(page_title="Land Image Enhancer", layout="wide")

st.title("🌍 Land Image Enhancer")
st.write("Upload a land/satellite image to enhance resolution (classic upscale), adjust sharpness/contrast, crop/zoom and download results.")

# ---------------------------
# UI controls
# ---------------------------
# File uploader
uploaded_file = st.file_uploader("Upload Land Image", type=["png", "jpg", "jpeg", "jfif", "webp", "bmp", "tiff"])

def pil_to_bytes(img):
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

if uploaded_file:
    try:
        orig = Image.open(uploaded_file).convert("RGB")
    except Exception:
        st.error("❌ Unsupported or corrupted image file.")
        st.stop()

    # Sidebar controls
    with st.sidebar.expander("⚙️ Enhancement Controls", expanded=True):
        scale_classic = st.slider("Upscale Factor", 1, 6, 2)
        sharpness = st.slider("Sharpness", 0.5, 3.0, 1.5, 0.1)
        contrast = st.slider("Contrast", 0.5, 3.0, 1.3, 0.1)
        brightness = st.slider("Brightness", 0.5, 2.0, 1.1, 0.1)

    # ---------- ENHANCEMENT PIPELINE ----------
    enhanced = orig.resize(
        (orig.width * scale_classic, orig.height * scale_classic),
        Image.Resampling.LANCZOS
    )
    enhanced = enhanced.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    enhanced = ImageEnhance.Sharpness(enhanced).enhance(sharpness)
    enhanced = ImageEnhance.Contrast(enhanced).enhance(contrast)
    enhanced = ImageEnhance.Brightness(enhanced).enhance(brightness)

    # ---------- RESPONSIVE BEFORE/AFTER ----------
    st.subheader("🔍 Before vs After")
    display_mode = st.radio("Display mode:", ["Auto", "Desktop (swipe)", "Mobile (side-by-side)"], horizontal=True)

    # Resize images for comparison to avoid disappearing/fade issues
    max_width = 1024
    ratio = min(max_width / orig.width, 1.0)
    orig_resized = orig.resize((int(orig.width * ratio), int(orig.height * ratio)))
    enhanced_resized = enhanced.resize((int(enhanced.width * ratio), int(enhanced.height * ratio)))

    if display_mode == "Desktop (swipe)":
        try:
            image_comparison(
                img1=Image.open(pil_to_bytes(orig_resized)),
                img2=Image.open(pil_to_bytes(enhanced_resized)),
                label1=f"Original ({orig.width}x{orig.height})",
                label2=f"Enhanced ({enhanced.width}x{enhanced.height})",
                width=700
            )
        except Exception:
            # fallback side-by-side
            c1, c2 = st.columns(2)
            with c1:
                st.image(orig, caption=f"Original ({orig.width}x{orig.height})", use_container_width=True)
            with c2:
                st.image(enhanced, caption=f"Enhanced ({enhanced.width}x{enhanced.height})", use_container_width=True)
    elif display_mode == "Mobile (side-by-side)":
        c1, c2 = st.columns(2)
        with c1:
            st.image(orig, caption=f"Original ({orig.width}x{orig.height})", use_container_width=True)
        with c2:
            st.image(enhanced, caption=f"Enhanced ({enhanced.width}x{enhanced.height})", use_container_width=True)
    else:
        # Auto-detect based on user agent
        try:
            if st.experimental_user_agent and "Mobile" in st.experimental_user_agent:
                c1, c2 = st.columns(2)
                with c1:
                    st.image(orig, caption=f"Original ({orig.width}x{orig.height})", use_container_width=True)
                with c2:
                    st.image(enhanced, caption=f"Enhanced ({enhanced.width}x{enhanced.height})", use_container_width=True)
            else:
                image_comparison(
                    img1=Image.open(pil_to_bytes(orig_resized)),
                    img2=Image.open(pil_to_bytes(enhanced_resized)),
                    label1=f"Original ({orig.width}x{orig.height})",
                    label2=f"Enhanced ({enhanced.width}x{enhanced.height})",
                    width=700
                )
        except Exception:
            c1, c2 = st.columns(2)
            with c1:
                st.image(orig, caption=f"Original ({orig.width}x{orig.height})", use_container_width=True)
            with c2:
                st.image(enhanced, caption=f"Enhanced ({enhanced.width}x{enhanced.height})", use_container_width=True)

    # ---------- CROP-TO-ZOOM ----------
    st.markdown("---")
    st.subheader("🖼️ Crop to Zoom")
    st.write("Select a crop area (x1,y1,x2,y2) in the original image coordinates to zoom in on the enhanced image.")
    col1, col2 = st.columns(2)
    x1 = col1.number_input("x1", min_value=0, max_value=orig.width, value=0)
    y1 = col2.number_input("y1", min_value=0, max_value=orig.height, value=0)
    col3, col4 = st.columns(2)
    x2 = col3.number_input("x2", min_value=0, max_value=orig.width, value=orig.width)
    y2 = col4.number_input("y2", min_value=0, max_value=orig.height, value=orig.height)

    if st.button("🔎 Crop & Zoom", use_container_width=True):
        try:
            scale_factor = scale_classic
            left = int(x1 * scale_factor)
            upper = int(y1 * scale_factor)
            right = int(x2 * scale_factor)
            lower = int(y2 * scale_factor)
            cropped = enhanced.crop((left, upper, right, lower))
            st.image(
                cropped.resize((min(900, cropped.width), min(900, cropped.height)), Image.Resampling.LANCZOS),
                caption="Zoomed crop (enhanced)", use_container_width=True
            )
        except Exception as e:
            st.error("⚠️ Invalid crop area selected or processing error: " + str(e))

    # ---------- DOWNLOAD ----------
    st.markdown("---")
    buf = io.BytesIO()
    enhanced.save(buf, format="PNG")
    st.download_button(
        "📥 Download Enhanced Image",
        data=buf.getvalue(),
        file_name="enhanced_land.png",
        mime="image/png",
        use_container_width=True
    )
