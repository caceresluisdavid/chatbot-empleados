# 6. EL AGENTE PROGRAMADOR (ROBUSTO Y CON FEEDBACK VISUAL)
    pregunta = st.chat_input("Ej: ¿Cuántos tienen sobrepeso? o Grafica encuestados por barrio")

    if pregunta:
        # Registrar y mostrar la pregunta del usuario
        st.session_state.mensajes.append({"role": "user", "texto": pregunta})
        with st.chat_message("user"):
            st.markdown(pregunta)
        
        with st.chat_message("assistant"):
            with st.spinner("Analizando datos y calculando respuesta... ⏳"):
                columnas_disponibles = ", ".join(df.columns.tolist())
                
                prompt = f"""
Genera código Python para responder una consulta sobre un DataFrame ya cargado llamado `df`.

REGLAS ESTRICTAS:
1. Responde ÚNICAMENTE con código Python ejecutable, sin explicaciones ni formato markdown (nada de ```python).
2. Guarda el texto del resultado en la variable `respuesta_final` (string amigable).
3. Si la consulta pide un gráfico, usa Plotly Express (`px`) y guárdalo en la variable `grafico_final`.
4. Si la consulta pide ubicar o ver en mapa, NO USES PLOTLY. Haz: `mapa_final = df.dropna(subset=['lat', 'lon'])` (o el filtro correspondiente con lat y lon).

COLUMNAS DISPONIBLES EN 'df':
{columnas_disponibles}

CONSULTA:
{pregunta}
"""
                codigo = None
                
                try:
                    # Llamada directa a Gemini
                    respuesta_gemini = model.generate_content(prompt)
                    if hasattr(respuesta_gemini, "text") and respuesta_gemini.text:
                        codigo = respuesta_gemini.text.strip()
                    else:
                        st.error("El modelo no devolvió una respuesta válida.")
                except Exception as e:
                    st.error(f"Error al conectar con la API de Gemini: {e}")
                    codigo = None

                if codigo:
                    # Limpieza por si el modelo incluye bloques de markdown
                    if codigo.startswith("```python"):
                        codigo = codigo[9:]
                    if codigo.startswith("```"):
                        codigo = codigo[3:]
                    if codigo.endswith("```"):
                        codigo = codigo[:-3]
                    codigo = codigo.strip()

                    local_vars = {"df": df, "px": px, "pd": pd}
                    
                    try:
                        # Ejecución del código generado
                        exec(codigo, globals(), local_vars)
                        
                        texto = local_vars.get("respuesta_final", "✅ Análisis procesado correctamente.")
                        grafico = local_vars.get("grafico_final", None)
                        mapa = local_vars.get("mapa_final", None)
                        
                        # Renderizar resultados
                        st.markdown(texto)
                        if grafico is not None:
                            st.plotly_chart(grafico)
                        if mapa is not None:
                            st.map(mapa)
                        
                        # Guardar en memoria de sesión
                        st.session_state.mensajes.append({
                            "role": "assistant", 
                            "texto": texto,
                            "grafico": grafico,
                            "mapa": mapa
                        })

                    except Exception as err_exec:
                        st.error(f"Error al ejecutar el cálculo: {err_exec}")
                        with st.expander("Ver código que intentó ejecutar"):
                            st.code(codigo, language="python")
