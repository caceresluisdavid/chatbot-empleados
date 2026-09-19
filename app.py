import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. DISEÑO DE LA PÁGINA
st.set_page_config(page_title="Chatbot de Base de Datos", page_icon="📊")

st.markdown("<h2 style='text-align: center; color: #1E88E5;'>Asistente Virtual de Registros 🤖</h2>", unsafe_allow_html=True)
st.write("Hazme cualquier consulta sobre la base de datos.")

# 2. CONFIGURACIÓN DE GEMINI
# Llama a la clave secreta que configuraremos en Streamlit
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# 3. CONECTAR TU PLANILLA
@st.cache_data
def cargar_datos():
    # Tu enlace convertido a formato de descarga CSV (gid=0 es la primera pestaña)
    url = "https://docs.google.com/spreadsheets/d/1oiv8fN5SjlToafR0uhk37FG3uWRxfH2pcxnUMyaWO2E/export?format=csv&gid=0"
    return pd.read_csv(url)

try:
    df = cargar_datos()
    with st.expander("Ver datos cargados"):
        st.dataframe(df.head())
except Exception as e:
    st.error("Error al cargar la hoja. Asegúrate de que está pública.")

# 4. MEMORIA DEL CHAT
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. CAJA DE TEXTO PARA PREGUNTAR
pregunta = st.chat_input("Ej: ¿Cuántas personas hay en la lista? o ¿Quién es el director?")

if pregunta and 'df' in locals():
    # Mostrar la pregunta
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)
    
    # Transformar la tabla a texto para que la IA la lea
    datos_texto = df.to_csv(index=False)
    
    prompt = f"""
    Eres un asistente de análisis de datos. Responde la siguiente pregunta basándote ÚNICAMENTE en estos datos:
    
    {datos_texto}
    
    Pregunta: {pregunta}
    """
    
    # Generar respuesta
    with st.chat_message("assistant"):
        respuesta_placeholder = st.empty()
        respuesta_placeholder.markdown("Analizando datos... ⏳")
        try:
            respuesta = model.generate_content(prompt)
            respuesta_placeholder.markdown(respuesta.text)
            st.session_state.mensajes.append({"role": "assistant", "content": respuesta.text})
        except Exception as e:
            respuesta_placeholder.error(f"Error al consultar a Gemini: {e}")
