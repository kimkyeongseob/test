import streamlit as st

st.title("Hello World!")
st.write("Streamlit 앱에 오신 것을 환영합니다!")

name = st.text_input("이름을 입력하세요:")
if name:
    st.write(f"안녕하세요, {name}님!")
