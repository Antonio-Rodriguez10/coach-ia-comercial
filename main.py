import os
import streamlit as st
import pandas as pd
from datetime import datetime
from openai import OpenAI

SYSTEM_PROMPT = """# System Prompt — Analista de Llamadas Comerciales (Venta Consultiva, Escuela de Negocios)

## Identidad y rol
Eres un **Director Comercial** de una **escuela de negocios**. Tu función es **analizar llamadas comerciales** (transcripciones) para evaluar la calidad del speech, la ejecución del embudo de venta y la personalización de la conversación.

## Contexto y fuente de verdad
Dispones de un **Documento de Referencia** (adjunto en esta conversación) que contiene:
- El **embudo de venta** y/o
- Las **fases del speech** (estructura ideal de la llamada)

Ese documento es la **fuente de verdad**. Debes basar el análisis **exclusivamente** en ese documento para:
- Definir las fases
- Determinar qué cumple o no cumple
- Evaluar desviaciones y redundancias

Si el documento no está disponible en el contexto actual, indícalo explícitamente y limita el análisis a observaciones generales sin inventar fases.

## Objetivo del análisis
1. Realizar un **análisis por fases** (según el Documento de Referencia), de todas las llamadas para hacer una valoración global, indicando:
   - Qué fases aparecen
   - Cuáles faltan
   - Dónde se ejecutan bien o mal
   - Evidencias (frases o fragmentos breves de la transcripción) para justificar

2. Generar **dos gráficas** en el resultado final:
   - **Gráfica 1: Cumplimiento de fases** en la llamada (cobertura).
   - **Gráfica 2: Redundancias por fase**, detectando repeticiones innecesarias:
     - Muletillas repetidas
     - La misma explicación reiterada sin aportar valor
     - Preguntas duplicadas que no avanzan

3. Evaluar si la llamada refleja una **venta emocional y centrada en el alumno**, evitando un discurso “de catálogo”.

4. Verificar que la llamada está **personalizada**:
   - No debe sonar como un speech “enlatado”
   - Debe adaptarse al contexto del lead
   - Debe responder a lo que el lead expresa (escucha activa)

## Principios de evaluación (venta consultiva)
- El alumno y su contexto están en el centro: objetivos, miedos, motivaciones, limitaciones de tiempo/dinero, situación profesional.
- Prioriza la **detección de necesidades** y el **match** del programa con objetivos.
- El asesor debe evitar conversaciones demasiado “iguales” entre leads: se valora la adaptación.
- Se penaliza:
  - Monólogos extensos sin validar comprensión
  - Saltar fases críticas (por ejemplo, no investigar necesidades)
  - Presionar sin construir valor
  - Repetición excesiva de muletillas o argumentos

## Cómo debes analizar (método)
### 1) Preparación
- Lee la transcripción completa.
- Identifica interlocutores (Asesor/Lead).
- Segmenta la llamada en bloques temáticos.

### 2) Mapeo a fases (según Documento de Referencia)
- Asigna cada bloque a una fase del speech.
- Si un bloque parece pertenecer a varias fases, asigna la fase dominante y anota la ambigüedad.

### 3) Métrica de cobertura por fases (para Gráfica 1)
Para cada fase, estima cobertura usando al menos dos señales:
- Presencia/ausencia (sí/no)
- Intensidad (baja/media/alta) o porcentaje aproximado por turnos (intervenciones)

### 4) Detección de redundancias (para Gráfica 2)
Para cada fase:
- Detecta muletillas repetidas (palabras o expresiones recurrentes).
- Detecta repetición de la misma idea sin aportar información nueva (paráfrasis redundante).
- Marca severidad:
  - 0 = ninguna
  - 1 = leve
  - 2 = moderada
  - 3 = alta

No penalices repeticiones cuando:
- El lead pide aclaración
- Se resume para confirmar comprensión
- Se reformula para adaptarse a una objeción real

### 5) Evaluación de personalización y enfoque emocional
Analiza si el asesor:
- Usa el lenguaje del lead (objetivos, contexto, situación)
- Conecta beneficios con “dolor/objetivo” del lead
- Hace preguntas abiertas y escucha
- Valida emociones/limitaciones (“entiendo”, “tiene sentido”, “si estás con poco tiempo…”)
- Evita sonar como un guion idéntico para todos

## Formato de salida (obligatorio)
Entrega SIEMPRE el resultado en **texto**, y además incluye **dos gráficas** en formato Markdown (ASCII).

### Estructura exacta de respuesta
1. **Resumen ejecutivo (5–8 líneas)**
   - Diagnóstico general
   - 3 aciertos clave
   - 3 mejoras prioritarias

2. **Gráfica 1 — Cumplimiento de fases**
   - Usa barras ASCII por fase (0–100) o niveles (0–10).
   - Ejemplo de barra: `██████░░░░` (10 niveles)
   - Incluye una leyenda.

3. **Gráfica 2 — Redundancias por fase**
   - Mismo formato de barras, pero midiendo redundancia (0–3 o 0–10).
   - Incluye leyenda de severidad.

4. **Análisis por fases (según Documento de Referencia)**
   Para cada fase:
   - Objetivo de la fase (según documento)
   - Evidencias encontradas (fragmentos breves)
   - Qué se hizo bien
   - Qué falta o qué se puede mejorar
   - Señales de personalización (sí/no + ejemplo)
   - Redundancias detectadas (muletillas/ideas repetidas + impacto)

5. **Observaciones de venta emocional y centrada en el alumno**
   - Qué elementos emocionales se trabajaron
   - Qué oportunidades se perdieron
   - Qué frases alternativas podrían ayudar (máximo 5, muy concretas)

6. **Plan de mejora accionable**
   - 5 acciones concretas (tipo checklist) para la próxima llamada
   - 2 “stop doing” (cosas que debe dejar de hacer)
   - 2 “keep doing” (cosas que debe mantener)

## Reglas de estilo
- Idioma: español.
- Tono: profesional, claro, directo y constructivo.
- Evita generalidades: cada conclusión debe tener evidencia o justificación.
- No inventes datos, ni fases, ni contenido del Documento de Referencia.
- No uses emojis.
- No hagas el análisis “por intuición” si faltan documento o transcripción: indícalo y limita el alcance.

## Entradas esperadas del usuario
El usuario te proporcionará:
- La transcripción de la llamada (texto).
- El Documento de Referencia (embudo/fases del speech) si no está ya adjunto en el contexto.
- Opcional: nombre del programa y objetivo de la llamada (cualificación, cierre, seguimiento).
"""

REFERENCE_DOC_TEXT = """Presentación:
- Hola, pregunto por yyy
- Qué tal yyy, soy xxx, te llamo de IEBS, escuela de negocios.
- Te llamo porque nos habías pedido información de nnn, es correcto?
- Genial, tienes unos minutos para verlo?
Notas: Presentación clara y breve, preguntando si el lead tiene unos minutos para poder atendernos.

Investigación:
- Antes de nada, quiero ver el motivo de querer hacer este programa nnn, para ver si es el adecuado para tus objetivos. Cuéntame que esperas conseguir, tu perfil actual, trayectoria, etc.
Notas: Descubrir qué necesita el lead, qué espera conseguir y su perfil actual. Detección de necesidades y miedos. Preguntas abiertas. Importante la escucha activa.

Match objetivo con programa:
- Perfecto, el programa encaja por (dar motivos)
- Vamos a ver otro programa que creo que encaja mejor con tus objetivos.
Notas: Validar el encaje con objetivos. Visualizar qué aportará, cómo mejorará su día a día y futuro profesional. Dar ejemplos concretos. Cubrir necesidad/dolor.

Pregunta de control:
- ¿Como lo ves? ¿Encaja? ¿Dudas?
Notas: Controlar si el lead considera adecuado el programa y si tiene dudas sobre temario/objetivos/resultados.

Metodología de aprendizaje:
- Nuestra metodología se basa en proyectos progresivos e incrementales, diseñados para que adquieras las competencias técnicas más demandadas del sector.
- Cada mes, te enfrentarás a una nueva asignatura y un proyecto desafrafo que completarás de principio a fin. Estos proyectos se convertirán en tu portafolio profesional.
- Cada asignatura se desarrolla a lo largo de un mes, con tres semanas de preparación, tres sprints semanales iterativos, que te van preparando de forma exponencial, asegurando que estés listo para resolver el proyecto mensual la cuarta semana.
- Vídeos concisos de 10-15 minutos, con transcripciones y buscador integrado.
- Profesores profesionales activos: crean contenido y dan feedback continuo durante el proyecto. Resolución de dudas por email o chat interno con compromiso de respuesta en 24h.
- Además del profesor, contarás con un learning coach (seguimiento y soporte campus).
- Director del programa: guía en global project.
- Grupos de hasta 40 alumnos (entorno heterogéneo y multicultural).
- Tutorías con profesores y compañeros, grabadas para quienes no asistan en vivo.
Notas: No es obligatorio seguir palabra por palabra, pero sí explicar de forma clara cómo funciona, destacando aspectos clave.

Pregunta de control (metodología):
- ¿Encaja? ¿Podrás dedicarle el tiempo necesario? ¿Es lo que buscabas?
Notas: Preguntas más cerradas para confirmar encaje, tiempo disponible y dudas.

Precio:
- Ver precio del programa, si aplica una beca, formas de pago.

Pregunta de control (precio):
- ¿Es asumible? ¿Cómo afrontas la inversión? ¿Particular o empresa? ¿Te ayudan con el pago? ¿Contado o en cuotas?

Proceso de admisión:
- Explicar el proceso de admisión: solicitud, entrevista personal y que es un proceso para conseguir un grupo reducido. Proponer rellenar la solicitud ahora o en una llamada posterior.

Cierre:
- Buscar compromiso de siguiente contacto con llamada de seguimiento.
- Usar preguntas de doble alternativa: ¿Te viene bien hablar mañana o pasado mañana? ¿Por la mañana o por la tarde?

Pregunta de control final:
- ¿Queda alguna duda?

Despedida:
- Despedida cordial y agradable.
"""


def call_openai(system_prompt: str, reference_doc_text: str, transcripts_payload: str) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return "Error: No se ha encontrado la clave OPENAI_API_KEY. Por favor configúrala en los Secrets de Replit."

    client = OpenAI(api_key=api_key)

    # Ayuda a que el modelo entienda que el documento de referencia está incluido aquí
    user_content = f"""
A continuación incluyo el Documento de Referencia (FUENTE DE VERDAD) y las Transcripciones.
Debes basar el análisis EXCLUSIVAMENTE en el Documento de Referencia incluido aquí.

### Documento de Referencia (Fuente de verdad):
{reference_doc_text}

### Transcripciones (con metadatos):
{transcripts_payload}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content


def get_transcripts(comercial: str, fecha_inicio, fecha_fin):
    folder = "transcripts"
    if not os.path.exists(folder):
        return []

    files = os.listdir(folder)
    matched = []

    for filename in files:
        if not filename.endswith(".txt"):
            continue

        parts = filename.split("_")
        if len(parts) < 3:
            continue

        file_comercial = parts[0]
        file_fecha_str = parts[1]

        try:
            file_fecha = datetime.strptime(file_fecha_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        if comercial != "Todos" and comercial != file_comercial:
            continue

        if not (fecha_inicio <= file_fecha <= fecha_fin):
            continue

        filepath = os.path.join(folder, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        matched.append(
            {
                "Comercial": file_comercial,
                "Fecha": file_fecha_str,
                "Archivo": filename,
                "Contenido": content,
            }
        )

    return matched


def main():
    st.set_page_config(page_title="Coach IA Comercial — Análisis Automático", layout="wide")

    # CSS simple para look SaaS
    st.markdown(
        """
<style>
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1200px; }

.app-header {
  display:flex; align-items:center; gap:16px;
  padding: 18px 22px;
  border-radius: 16px;
  background: linear-gradient(90deg, rgba(37,99,235,0.16), rgba(37,99,235,0.03));
  border: 1px solid rgba(37,99,235,0.25);
  margin-bottom: 18px;
}
.app-icon {
  width: 42px; height: 42px; border-radius: 12px;
  background: #2563EB;
  display:flex; align-items:center; justify-content:center;
  color: white; font-weight: 800; font-size: 18px;
}
.app-title { font-size: 30px; font-weight: 800; margin: 0; color:#0F172A; }
.app-subtitle { margin-top: 4px; font-size: 14px; color: rgba(15,23,42,0.72); font-weight: 500; }

.card {
  background: #FFFFFF;
  border-radius: 16px;
  border: 1px solid rgba(2,6,23,0.08);
  padding: 16px 18px;
  box-shadow: 0 8px 20px rgba(2,6,23,0.06);
  margin-bottom: 18px;
}
.card-title { font-weight: 800; color:#0F172A; margin-bottom: 6px; }
.card-hint { color: rgba(15,23,42,0.65); font-size: 14px; margin-bottom: 10px; }

div.stButton > button {
  border-radius: 12px !important;
  padding: 0.65rem 1.15rem !important;
  font-weight: 700 !important;
}
</style>
""",
        unsafe_allow_html=True,
    )

    # Fecha en español
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    hoy = datetime.now()
    fecha_hoy = f"{dias[hoy.weekday()]}, {hoy.day} de {meses[hoy.month - 1]} de {hoy.year}"

    if "status" not in st.session_state:
        st.session_state.status = "Estado: listo"

    # Header visual
    st.markdown(
        f"""
<div class="app-header">
  <div class="app-icon">AI</div>
  <div>
    <div class="app-title">Coach IA Comercial</div>
    <div class="app-subtitle">Análisis Automático · {fecha_hoy} · {st.session_state.status}</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    # Tarjeta filtros
    st.markdown(
        """
<div class="card">
  <div class="card-title">Parámetros de Análisis</div>
  <div class="card-hint">Configura los filtros para generar el reporte comercial.</div>
""",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        comercial = st.selectbox("Comercial", options=["Todos", "Gemma", "Alejandro"])
    with col2:
        fecha_inicio = st.date_input("Fecha inicio")
    with col3:
        fecha_fin = st.date_input("Fecha fin")

    run_clicked = st.button("Generar análisis", type="primary")

    st.markdown("</div>", unsafe_allow_html=True)  # cierre card filtros

    if run_clicked:
        st.session_state.status = "Estado: procesando..."

        transcripts = get_transcripts(comercial, fecha_inicio, fecha_fin)

        if not transcripts:
            st.warning("No hay transcripciones que coincidan con los filtros.")
            st.session_state.status = "Estado: listo"
            st.stop()

        payload_parts = []
        for t in transcripts:
            payload_parts.append(
                f"Comercial: {t['Comercial']}\n"
                f"Fecha: {t['Fecha']}\n"
                f"Archivo: {t['Archivo']}\n"
                f"Transcripción:\n{t['Contenido']}\n"
                f"{'-' * 40}"
            )
        transcripts_payload = "\n".join(payload_parts)

        if "OPENAI_API_KEY" not in os.environ:
            st.error("Error: Falta la OPENAI_API_KEY. Configúrala en los Secrets de Replit.")
            st.stop()

        with st.spinner("Analizando con OpenAI..."):
            response_text = call_openai(SYSTEM_PROMPT, REFERENCE_DOC_TEXT, transcripts_payload)

        st.session_state.status = "Estado: análisis completado"

        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Resultados del Análisis")

        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        kpi1.metric("Nº archivos analizados", len(transcripts))
        kpi2.metric("Nº transcripciones", len(transcripts))
        kpi3.metric("Comercial", comercial)
        kpi4.metric("Rango", f"{fecha_inicio.strftime('%Y-%m-%d')} a {fecha_fin.strftime('%Y-%m-%d')}")
        kpi5.metric("Estado", "Completado")

        df = pd.DataFrame(
            [{"Comercial": t["Comercial"], "Fecha": t["Fecha"], "Archivo": t["Archivo"]} for t in transcripts]
        )
        st.dataframe(df, hide_index=True)

        st.subheader("Respuesta del agente")
        st.markdown(response_text)

        st.markdown("</div>", unsafe_allow_html=True)  # cierre card resultados


if __name__ == "__main__":
    main()