import streamlit as st
import pandas as pd
import google.generativeai as genai
import plotly.express as px

# 1. CONTROL DE ACCESO GENERAL
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

    # 2. DISEÑO Y LOGO
    st.set_page_config(page_title="Asistente de Registros 2.0", page_icon="🏢")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        try:
            st.image("logo.png", use_container_width=True)
        except Exception:
            st.info("Sube tu archivo 'logo.png' a GitHub para que aparezca aquí.")

    st.markdown("<h2 style='text-align: center; color: #1E88E5;'>Asistente de Datos 2.0 🤖</h2>", unsafe_allow_html=True)

    # 3. CONTROL DE DATOS SENSIBLES EN BARRA LATERAL
    if "admin_desbloqueado" not in st.session_state:
        st.session_state["admin_desbloqueado"] = False

    with st.sidebar:
        st.markdown("### 🔐 Privacidad de Datos")
        if not st.session_state["admin_desbloqueado"]:
            clave_admin = st.text_input("Clave para ver DNI / Nombres:", type="password")
            if st.button("Desbloquear Datos Sensibles"):
                if clave_admin == st.secrets.get("CLAVE_ADMIN", "AdminCora2026"):
                    st.session_state["admin_desbloqueado"] = True
                    st.success("✅ Datos sensibles desbloqueados.")
                    st.rerun()
                else:
                    st.error("Clave incorrecta.")
        else:
            st.success("🔓 Modo Administrador Activo (DNI, nombres y apellidos visibles)")
            if st.button("Ocultar Datos Sensibles"):
                st.session_state["admin_desbloqueado"] = False
                st.rerun()
                
        st.divider()
        if st.button("Cerrar Sesión"):
            st.session_state["password_correct"] = False
            st.session_state["admin_desbloqueado"] = False
            st.rerun()

    # 4. CONFIGURACIÓN GEMINI
    @st.cache_resource
    def inicializar_modelo():
        API_KEY = st.secrets["GEMINI_API_KEY"]
        genai.configure(api_key=API_KEY)
        return genai.GenerativeModel(
            'gemini-3.6-flash',
            generation_config={"temperature": 0.0}
        )

    model = inicializar_modelo()

    # 5. CARGAR LA BASE DE DATOS COMPLETA (db_empleados)
    @st.cache_data
    def cargar_datos_completos():
        url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTI1_HYlETtMdr7XvihhbC1prkNq9nvE9cARLPLP41wQJ0XwN-rDcLpJMeJ8GDcxfwmcFtuQgiq23K_/pub?gid=0&single=true&output=csv"
        df = pd.read_csv(url) 
        
        # Formatear ID a 4 dígitos
        col_id = df.columns[0]
        df[col_id] = pd.to_numeric(df[col_id], errors='coerce').fillna(0).astype(int)
        df[col_id] = df[col_id].apply(lambda x: f"{x:04d}")
        
        # Limpieza de Coordenadas
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
        df_raw = cargar_datos_completos()
    except Exception as e:
        st.error(f"Error al cargar la hoja: {e}")
        st.stop()

    # Filtro de protección según el estado de la sesión
    columnas_sensibles = ['dni', 'apellido', 'nombres']
    if st.session_state["admin_desbloqueado"]:
        df = df_raw.copy()
    else:
        # Se remueven las columnas de identidad si no es admin
        cols_a_borrar = [c for c in columnas_sensibles if c in df_raw.columns]
        df = df_raw.drop(columns=cols_a_borrar)

    with st.expander("Ver primeros datos (Vista actual en memoria)"):
        st.dataframe(df.head())

    # 6. HISTORIAL VISUAL DEL CHAT (AVATAR ILUSTRADO DE LA CHICA RUBIA)
    AVATAR_USER = "https://api.dicebear.com/7.x/avataaars/png?seed=Luna&skinColor=f8d25c&hairColor=ffd15c&top=longHairStraightStrand"
    AVATAR_BOT = "assistant"

    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []

    for msg in st.session_state.mensajes:
        avatar_icono = AVATAR_USER if msg["role"] == "user" else AVATAR_BOT
        with st.chat_message(msg["role"], avatar=avatar_icono):
            if "texto" in msg and msg["texto"]:
                st.markdown(msg["texto"])
            if "grafico" in msg and msg["grafico"] is not None:
                st.plotly_chart(msg["grafico"])
            if "mapa" in msg and msg["mapa"] is not None:
                st.map(msg["mapa"])

    # 7. AGENTE PROGRAMADOR
    pregunta = st.chat_input("Haceme un gráfico de torta con el nivel de estudios")

    if pregunta:
        # Interceptar preguntas sobre datos sensibles si no está autorizado
        palabras_sensibles = ["dni", "documento", "apellido", "nombre"]
        pregunta_lower = pregunta.lower()
        requiere_sensibles = any(p in pregunta_lower for p in palabras_sensibles)

        if requiere_sensibles and not st.session_state["admin_desbloqueado"]:
            st.session_state.mensajes.append({"role": "user", "texto": pregunta})
            with st.chat_message("user", avatar=AVATAR_USER):
                st.markdown(pregunta)
            
            with st.chat_message("assistant", avatar=AVATAR_BOT):
                msg_bloqueo = "🔒 **Acceso Denegado:** Esta consulta solicita datos protegidos (DNI, nombres o apellidos). Para consultarlos debes ingresar la clave especial en el menú lateral."
                st.warning(msg_bloqueo)
                st.session_state.mensajes.append({
                    "role": "assistant",
                    "texto": msg_bloqueo,
                    "grafico": None,
                    "mapa": None
                })
        else:
            st.session_state.mensajes.append({"role": "user", "texto": pregunta})
            with st.chat_message("user", avatar=AVATAR_USER):
                st.markdown(pregunta)
            
            with st.chat_message("assistant", avatar=AVATAR_BOT):
                with st.spinner("Analizando datos y procesando respuesta... ⏳"):
                    columnas_disponibles = ", ".join(df.columns.tolist())
                    
                    prompt = f"""
Genera código Python para responder una consulta sobre un DataFrame cargado en memoria llamado `df`.

REGLAS OBLIGATORIAS:
1. Responde ÚNICAMENTE con el bloque de código Python ejecutable. CERO texto de introducción o cierre. CERO bloques markdown como ```python.
2. Guarda la conclusión o respuesta numérica en texto amigable dentro de la variable `respuesta_final`.
3. Si la pregunta pide gráficos (barras, tortas, distribución), usa Plotly Express (`px`) y guárdalo en `grafico_final`.
4. Si la pregunta pide ver en mapa o ubicaciones: NO USES PLOTLY. Haz: `mapa_final = df.dropna(subset=['lat', 'lon'])` (con filtros aplicados si corresponde).

COLUMNAS DISPONIBLES EN 'df':
{columnas_disponibles}

CONSULTA:
{pregunta}
"""
                    codigo = None
                    try:
                        respuesta_gemini = model.generate_content(prompt)
                        if hasattr(respuesta_gemini, "text") and respuesta_gemini.text:
                            codigo = respuesta_gemini.text.strip()
                        else:
                            st.error("La API no devolvió una respuesta válida.")
                    except Exception as e:
                        st.error(f"Error al conectar con la API de Gemini: {e}")

                    if codigo:
                        if codigo.startswith("```python"):
                            codigo = codigo[9:]
                        if codigo.startswith("```"):
                            codigo = codigo[3:]
                        if codigo.endswith("```"):
                            codigo = codigo[:-3]
                        codigo = codigo.strip()

                        local_vars = {"df": df, "px": px, "pd": pd}
                        
                        try:
                            exec(codigo, globals(), local_vars)
                            
                            texto = local_vars.get("respuesta_final", "✅ Análisis procesado correctamente.")
                            grafico = local_vars.get("grafico_final", None)
                            mapa = local_vars.get("mapa_final", None)
                            
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

                        except Exception as err_exec:
                            st.error(f"Error al ejecutar el cálculo: {err_exec}")
                            with st.expander("Ver código ejecutado"):
                                st.code(codigo, language="python")
