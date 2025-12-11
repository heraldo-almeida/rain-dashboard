# company_branding.py

# """
# Centralized configuration for company branding (logos, names, colors).
# Update the paths below to point to your real logo image files in the repo.
# """

# # Relative paths from the repository root. Example:
# # put your images in:  assets/logo_primary.png  and  assets/logo_secondary.png
# PRIMARY_LOGO_PATH = "rain.png"     # main company logo
# SECONDARY_LOGO_PATH = "99-food-logo.png" # partner / product logo

# # Optional: textual brand elements you might want to reuse
# COMPANY_NAME = "99 Food"
# PRODUCT_NAME = "Rainfall Insights"
# TAGLINE = "Brazilian Precipitation Analytics"


import streamlit as st
import base64

# ---------------------------------------------------------
# COMPANY BRANDING ASSETS
# ---------------------------------------------------------

# Background image (URL or local file – both supported)
BACKGROUND_IMAGE = "https://images.unsplash.com/photo-1504384308090-c894fdcc538d"

# # Two company logos (replace with your actual paths)
# LOGO_PRIMARY = "https://upload.wikimedia.org/wikipedia/commons/a/ab/Logo_TV_2015.png"
# LOGO_SECONDARY = "https://upload.wikimedia.org/wikipedia/commons/thumb/8/89/HD_transparent_picture.png/600px-HD_transparent_picture.png"

LOGO_PRIMARY = "rain.png"     # main company logo
LOGO_SECONDARY = "99-food-logo.png" # partner / product logo

# ---------------------------------------------------------
# BACKGROUND INJECTION FUNCTION
# ---------------------------------------------------------

def apply_background(image_path: str, opacity: float = 0.35):
    """
    Adds a background image with transparency to the Streamlit dashboard.
    Works with local paths or URLs.

    opacity: 0.0 (fully transparent) to 1.0 (opaque)
    """

    if image_path.startswith("http"):
        # Background from URL
        st.markdown(
            f"""
            <style>
            .stApp {{
                background: linear-gradient(
                    rgba(0, 0, 0, {opacity}),
                    rgba(0, 0, 0, {opacity})
                ), url("{image_path}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    else:
        # Background from local file
        with open(image_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        st.markdown(
            f"""
            <style>
            .stApp {{
                background: linear-gradient(
                    rgba(0, 0, 0, {opacity}),
                    rgba(0, 0, 0, {opacity})
                ), url("data:image/png;base64,{encoded}");
                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )

