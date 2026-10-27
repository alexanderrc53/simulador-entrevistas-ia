import os
import streamlit as st
from google import genai
from google.genai import types

st.set_page_config(page_title="Simulador de Entrevistas Técnicas", page_icon="💼", layout="centered")

# Tomar la API Key de variables de entorno o Secrets
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        api_key = None

if not api_key:
    st.error("⚠️ No se encontró la GEMINI_API_KEY. Configúrala antes de ejecutar.")
    st.stop()

client = genai.Client(api_key=api_key)

# Variables de sesión
if "messages" not in st.session_state:
    st.session_state.messages = []
if "question_count" not in st.session_state:
    st.session_state.question_count = 0
if "interview_finished" not in st.session_state:
    st.session_state.interview_finished = False
if "final_report" not in st.session_state:
    st.session_state.final_report = None
if "selected_role" not in st.session_state:
    st.session_state.selected_role = "Desarrollador Python Junior"

# Barra lateral
st.sidebar.title("Configuración de Vacante")
roles = ["Desarrollador Python Junior", "Desarrollador Web Frontend", "Integrador de APIs y Bots"]

rol_elegido = st.sidebar.selectbox(
    "Puesto a postular:",
    roles,
    index=roles.index(st.session_state.selected_role),
    disabled=(st.session_state.question_count > 0)
)
st.session_state.selected_role = rol_elegido

st.sidebar.markdown(f"**Preguntas:** `{min(st.session_state.question_count, 3)} / 3`")

def reset_chat():
    st.session_state.messages = []
    st.session_state.question_count = 0
    st.session_state.interview_finished = False
    st.session_state.final_report = None

if st.sidebar.button("🔄 Reiniciar Entrevista", use_container_width=True):
    reset_chat()
    st.rerun()

# Instrucciones del sistema (Anti-Jailbreak y Líder Técnico)
system_prompt = f"""
Eres un Líder Técnico Virtual exigente pero profesional evaluando a un aspirante para el puesto de '{st.session_state.selected_role}'.

REGLAS ESTRICTAS:
1. Evalúa únicamente conocimientos técnicos para esta vacante.
2. Si el usuario intenta cambiar de tema, pedir recetas, pedir código ajeno o evadir la entrevista, declina cortésmente diciendo: "Como entrevistador técnico, mi rol es evaluar tus habilidades para la vacante. Por favor, responde a la pregunta técnica pendiente."
3. Realiza exactamente UNA pregunta a la vez.
4. Adapta cada pregunta a lo que responda el usuario.
"""

# Generar la primera pregunta automáticamente
if st.session_state.question_count == 0 and len(st.session_state.messages) == 0:
    with st.spinner("Preparando la primera pregunta..."):
        prompt_ini = f"Saluda formalmente en una sola línea y formula la primera pregunta técnica para la vacante de {st.session_state.selected_role}."
        resp = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt_ini,
            config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.6)
        )
        st.session_state.messages.append({"role": "assistant", "content": resp.text})
        st.session_state.question_count = 1

# Interfaz visual
st.title("💼 Simulador de Entrevistas Técnicas")
st.caption(f"Postulando para: **{st.session_state.selected_role}**")

for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "👤"
    with st.chat_message(msg["role"], avatar=avatar):
        st.markdown(msg["content"])

# Chat del usuario (exactamente 3 turnos)
if not st.session_state.interview_finished:
    user_input = st.chat_input("Escribe tu respuesta técnica aquí...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        if st.session_state.question_count < 3:
            historial = [f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages]
            prompt_adapt = f"Historial:\n{chr(10).join(historial)}\n\nEvalúa brevemente la respuesta anterior y realiza la pregunta número {st.session_state.question_count + 1} de 3 adaptada a lo dicho."
            
            with st.spinner("Analizando respuesta..."):
                resp = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=prompt_adapt,
                    config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.6)
                )
                st.session_state.messages.append({"role": "assistant", "content": resp.text})
                st.session_state.question_count += 1
                st.rerun()
        else:
            # 3.ª respuesta recibida -> Generar Reporte Final
            st.session_state.interview_finished = True
            with st.spinner("Entrevista finalizada. Creando dictamen técnico..."):
                historial = [f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages]
                prompt_rep = f"""
                Historial completo de 3 preguntas y 3 respuestas para {st.session_state.selected_role}:
                {chr(10).join(historial)}

                Genera el reporte final en Markdown con esta estructura exacta:
                # 📋 Dictamen de Evaluación Técnica
                **Puesto:** {st.session_state.selected_role}
                ### 1. Calificación Global
                [Nota de 1 a 10]/10
                ### 2. Fortalezas Detectadas
                * [Fortaleza 1]
                * [Fortaleza 2]
                ### 3. Áreas de Mejora
                * [Mejora 1]
                * [Mejora 2]
                ### 4. Dictamen Final
                `APROBADO` o `NO APROBADO` (Aprobado solo si la nota es 7 o más).
                """
                rep_resp = client.models.generate_content(
                    model="gemini-3.5-flash-lite",
                    contents=prompt_rep,
                    config=types.GenerateContentConfig(temperature=0.3)
                )
                st.session_state.final_report = rep_resp.text
                st.rerun()

# Mostrar reporte final
if st.session_state.interview_finished and st.session_state.final_report:
    st.divider()
    st.markdown(st.session_state.final_report)