import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px
import time
from google.api_core.exceptions import ResourceExhausted

# 1. CONTRASEÑA SEGURA
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["CLAVE_ACCESO"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #1E88E5;'>Acceso Restringido 🔒</h2>", unsafe_allow_html=True)
        st.text_input("Ingresa la contraseña:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.markdown("<h2 style='text-align: center; color: #1E88E5;'>Acceso Restringido 🔒</h2>", unsafe_allow_html=True)
        st.text_input("Ingresa la contraseña:", type="password", on_change=password_entered, key="password")
        st.error("😕 Contraseña incorrecta. Inténtalo de nuevo.")
        return False
    else:
        return True

if check_password():
    
    # 2. DISEÑO Y LOGO CENTRADO
    st.set_page_config(page_title="Asistente de Registros 2.0", page_icon="🏢")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.info("Sube tu archivo 'logo.png' a GitHub para que aparezca aquí.")

    st.markdown("<h2 style='text-align: center; color: #1E88E5;'>Asistente de Datos 2.0 🤖</h2>", unsafe_allow_html=True)
    
    if st.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()

    # 3. CONFIGURACIÓN GEMINI CACHEADA
    @st.cache_resource
    def obtener_modelo():
        API_KEY = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel(
            'gemini-3.6-flash',
            generation_config={"temperature": 0.0}
        )

    model = obtener_modelo()

    # 4. CARGAR DATOS Y FORMATEAR
    @st.cache_data
    def cargar_datos():
        url = "https://docs.google.com/spreadsheets/d/1oiv8fN5SjlToafR0uhk37FG3uWRxfH2pcxnUMyaWO2E/export?format=csv&gid=0"
        df = pd.read_csv(url) 
        
        # Formatear ID a 4 dígitos
        col_id = df.columns[0]
        df[col_id] = pd.to_numeric(df[col_id], errors='coerce').fillna(0).astype(int)
        df[col_id] = df[col_id].apply(lambda x: f"{x:04d}")
        
        # Limpieza para Coordenadas
        def limpiar_coord(val, prefijo):
            if pd.isna(val): 
                return None
            s = str(val).replace('.', '').replace(',', '').strip()
            if s == '' or s.lower() == 'nan': 
                return None
            if s.startswith(prefijo):
                try:
                    return float(s[:3] + '.' + s[3:])
                except Exception:
                    return None
            try:
                return float(s)
            except Exception:
                return None

        if 'lat' in df.columns and 'lon' in df.columns:
            df['lat'] = df['lat'].apply(lambda x: limpiar_coord(x, '-29'))
            df['lon'] = df['lon'].apply(lambda x: limpiar_coord(x, '-57'))
            
        return df

    try:
        df = cargar_datos()
        with st.expander("Ver primeros datos (Nota: Los IDs ya tienen formato 4 dígitos)"):
            st.dataframe(df.head())
    except Exception as e:
        st.error(f"Error al cargar la hoja: {e}")
        st.stop()

    # 5. HISTORIAL VISUAL DEL CHAT
    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []

    for msg in st.session_state.mensajes:
        with st.chat_message(msg["role"]):
            if "texto" in msg and msg["texto"]:
                st.markdown(msg["texto"])
            if "grafico" in msg and msg["grafico"] is not None:
                st.plotly_chart(msg["grafico"])
            if "mapa" in msg and msg["mapa"] is not None:
                st.map(msg["mapa"])

    # 6. EL AGENTE PROGRAMADOR (OPTIMIZADO CON REINTENTOS)
    pregunta = st.chat_input("Ej: ¿Cuántos tienen sobrepeso? o Grafica encuestados por barrio")

    if pregunta:
        st.session_state.mensajes.append({"role": "user", "texto": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)
        
        with st.chat_message("assistant"):
            respuesta_placeholder = st.empty()
            respuesta_placeholder.markdown("Traduciendo a Python y calculando... ⏳")
            
            # Prompt reducido al mínimo estricto
            columnas_disponibles = ", ".join(df.columns.tolist())
            prompt = f"""
Genera código Python para responder una consulta sobre un DataFrame `df`.

REGLAS:
1. Responde ÚNICAMENTE con código Python ejecutable, sin explicaciones ni markdown.
2. Guarda el mensaje final en texto en la variable `respuesta_final`.
3. Para gráficos (barras, tortas), usa Plotly Express (`px`) y guárdalo en `grafico_final`.
4. Para mapas: NO USES PLOTLY. Haz `mapa_final = df.dropna(subset=['lat', 'lon'])`.

COLUMNAS EN 'df':
{columnas_disponibles}

CONSULTA:
{pregunta}
"""
            
            codigo = None
            max_reintentos = 3
            
            # Sistema de resiliencia ante el límite de cuota (429)
            for intento in range(max_reintentos):
                try:
                    respuesta_gemini = model.generate_content(prompt)
                    codigo = respuesta_gemini.text.strip()
                    break
                except ResourceExhausted:
                    if intento < max_reintentos - 1:
                        respuesta_placeholder.markdown("⏳ Cuota momentáneamente saturada (límite de 5 consultas/min). Reintentando en 11 segundos...")
                        time.sleep(11)
                    else:
                        respuesta_placeholder.error("Se superó el límite por minuto de la API gratuita. Por favor espera 30 segundos y vuelve a consultar.")
                        st.stop()
                except Exception as e:
                    respuesta_placeholder.error(f"Error de conexión con la API: {e}")
                    st.stop()
            
            if codigo:
                try:
                    # Limpieza de bloques de código
                    if codigo.startswith("```python"):
                        codigo = codigo[9:]
                    if codigo.startswith("```"):
                        codigo = codigo[3:]
                    if codigo.endswith("```"):
                        codigo = codigo[:-3]
                    codigo = codigo.strip()
                    
                    local_vars = {"df": df, "px": px, "pd": pd}
                    exec(codigo, globals(), local_vars)
                    
                    texto = local_vars.get("respuesta_final", "✅ Análisis procesado correctamente.")
                    grafico = local_vars.get("grafico_final", None)
                    mapa = local_vars.get("mapa_final", None)
                    
                    respuesta_placeholder.empty()
                    st.markdown(texto)
                    if grafico is not None:
                        st.plotly_chart(grafico)
                    if mapa is not None:
                        st.map(mapa)
                    
                    st.session_state.mensajes.append({
                        "role": "assistant", 
                        "texto": texto,
                        "grafico": grafico,
                        "mapa": mapa
                    })
                    
                except Exception as e:
                    respuesta_placeholder.error(f"Error al ejecutar el código generado: {e}")
