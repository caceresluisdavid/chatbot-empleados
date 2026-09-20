import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px

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
    
    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        try:
            st.image("logo.png", use_container_width=True)
        except:
            st.info("Sube tu archivo 'logo.png' a GitHub para que aparezca aquí.")

    st.markdown("<h2 style='text-align: center; color: #1E88E5;'>Asistente de Datos 2.0 🤖</h2>", unsafe_allow_html=True)
    
    if st.button("Cerrar Sesión"):
        st.session_state["password_correct"] = False
        st.rerun()

    # 3. CONFIGURACIÓN GEMINI
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-3.6-flash')

    # 4. CARGAR DATOS Y FORMATEAR
    @st.cache_data
    def cargar_datos():
        url = "https://docs.google.com/spreadsheets/d/1oiv8fN5SjlToafR0uhk37FG3uWRxfH2pcxnUMyaWO2E/export?format=csv&gid=0"
        df = pd.read_csv(url) 
        
        # Formatear ID a 4 dígitos
        col_id = df.columns[0]
        df[col_id] = pd.to_numeric(df[col_id], errors='coerce').fillna(0).astype(int)
        df[col_id] = df[col_id].apply(lambda x: f"{x:04d}")
        
        # Limpieza a prueba de balas para Coordenadas
        def limpiar_coord(val, prefijo):
            # Si está vacío, lo ignoramos
            if pd.isna(val): 
                return None
            
            # Lo pasamos a texto y le quitamos puntos y comas
            s = str(val).replace('.', '').replace(',', '').strip()
            if s == '' or s.lower() == 'nan': 
                return None
                
            # Si es de Corrientes, rearmamos el decimal en su lugar correcto
            if s.startswith(prefijo):
                try:
                    return float(s[:3] + '.' + s[3:])
                except:
                    return None
            
            # Si ya venía bien, lo devolvemos como número
            try:
                return float(s)
            except:
                return None

        # Aplicamos la limpieza solo si existen las columnas lat y lon
        if 'lat' in df.columns and 'lon' in df.columns:
            # Latitud en Paso de los Libres empieza con -29...
            df['lat'] = df['lat'].apply(lambda x: limpiar_coord(x, '-29'))
            # Longitud en Paso de los Libres empieza con -57...
            df['lon'] = df['lon'].apply(lambda x: limpiar_coord(x, '-57'))
            
        return df

    try:
        df = cargar_datos()
        with st.expander("Ver primeros datos (Nota: Los IDs ya tienen formato 4 dígitos)"):
            st.dataframe(df.head())
    except Exception as e:
        st.error(f"Error al cargar la hoja: {e}")
        st.stop()

    # 5. HISTORIAL MULTIMEDIA DEL CHAT
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

    # 6. EL AGENTE PROGRAMADOR
    pregunta = st.chat_input("Ej: ¿Cuántos tienen sobrepeso? o Grafica encuestados por barrio")

    if pregunta:
        st.session_state.mensajes.append({"role": "user", "texto": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)
        
        with st.chat_message("assistant"):
            respuesta_placeholder = st.empty()
            respuesta_placeholder.markdown("Traduciendo a Python y calculando... ⏳")
            
            historial_text = "\n".join([f"{m['role']}: {m.get('texto', 'Gráfico/Mapa generado')}" for m in st.session_state.mensajes[-5:]])
            
            prompt = f"""
            Eres un Agente de Análisis de Datos experto en Python, Pandas y Plotly. 
            El usuario te hará una pregunta sobre un DataFrame llamado `df`.
            
            REGLAS ESTRICTAS DE RESPUESTA:
            1. Escribe ÚNICAMENTE el código Python válido. CERO texto de relleno. NADA de etiquetas "```python", solo el código crudo.
            2. El código debe ejecutarse desde cero usando el DataFrame `df`.
            3. Guarda la respuesta en texto amigable dentro de una variable llamada `respuesta_final`.
            4. GRÁFICOS (Barras, Tortas, etc): Créalos usando Plotly Express (`px`) y guarda la figura en `grafico_final`. ¡PROHIBIDO USAR PLOTLY PARA MAPAS!
            5. MAPAS: Si pide un mapa de ubicaciones, NO USES PLOTLY. Tu única tarea es filtrar el DataFrame para eliminar los registros vacíos usando `.dropna(subset=['lat', 'lon'])` y guardar el DataFrame resultante en la variable `mapa_final`.
            
            DICCIONARIO DE DATOS Y COLUMNAS:
            Columnas en 'df': {", ".join(df.columns.tolist())}
            - Columna 1 (ID): Es un String de 4 dígitos (ej: '0001').
            - La tabla proviene de un relevamiento social. Contiene datos de viviendas, salud, ingresos e infraestructura. Deduce el significado por sus nombres.
            
            HISTORIAL DE LA CONVERSACIÓN:
            {historial_text}
            
            Pregunta actual: {pregunta}
            """
            
            try:
                respuesta_gemini = model.generate_content(prompt)
                codigo = respuesta_gemini.text.strip()
                
                if codigo.startswith("```python"): codigo = codigo[9:]
                if codigo.startswith("```"): codigo = codigo[3:]
                if codigo.endswith("```"): codigo = codigo[:-3]
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
                respuesta_placeholder.error(f"Se produjo un error al ejecutar el código. Intenta preguntar de otra manera. \nDetalle técnico: {e}")
