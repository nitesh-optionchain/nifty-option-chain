import streamlit as st
import streamlit.components.v1 as components

# 📊 1. Multi-page Navigation ke andar sub-page configuration layout lock karna
# (Dhyan rahe: st.set_page_config hamesha page ki pehli line ke aas-pass hona chahiye)
st.set_page_config(layout="wide")

# 🏛️ 2. UI Header Setup
st.subheader("📊 Live Multi-Asset Analytical Chart Terminal")
st.markdown("---")

# 🔄 3. Integrating your high-performance HTML5 canvas chart via live URL
# Isse aapka advance chart bina Streamlit ko heavy kiye alag sandbox thread me makkhan chalega
components.html(
    '<iframe src="https://nitesh-optionchain.github.io/advance-chart/" width="100%" height="780" style="border:none; background-color: #131722;"></iframe>',
    height=800
)
