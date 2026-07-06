"""
==========================================================
FRONTEND - SISTEMA EXPERTO DE MANTENIMIENTO INDUSTRIAL
(Dashboard interactivo con Streamlit)
==========================================================
Este archivo es el "front" de tu sistema experto difuso.
Usa la MISMA lógica de mantenimiento_experto_difuso.py, pero
en vez de imprimir resultados en la terminal, los muestra en
una pantalla interactiva con sliders.

CÓMO EJECUTARLO (en la terminal de VS Code):
    pip install streamlit plotly scikit-fuzzy numpy matplotlib
    streamlit run app_mantenimiento.py

Se abrirá automáticamente en tu navegador (normalmente en
http://localhost:8501). Cierra la terminal para detenerlo.
==========================================================
"""

import numpy as np
import streamlit as st
import plotly.graph_objects as go

import skfuzzy as fuzz
from skfuzzy import control as ctrl

# ----------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ----------------------------------------------------------
st.set_page_config(
    page_title="Sistema Experto de Mantenimiento",
    page_icon="🛠️",
    layout="wide",
)

# ----------------------------------------------------------
# 1. MOTOR DIFUSO (idéntico al backend, cacheado para que no
#    se reconstruya en cada movimiento del slider)
# ----------------------------------------------------------
@st.cache_resource
def construir_sistema():
    horas_uso = ctrl.Antecedent(np.arange(0, 501, 1), "horas_uso")
    temperatura = ctrl.Antecedent(np.arange(20, 121, 1), "temperatura")
    vibracion = ctrl.Antecedent(np.arange(0, 11, 0.1), "vibracion")
    urgencia = ctrl.Consequent(np.arange(0, 101, 1), "urgencia")

    horas_uso["baja"] = fuzz.trimf(horas_uso.universe, [0, 0, 150])
    horas_uso["media"] = fuzz.trimf(horas_uso.universe, [80, 220, 350])
    horas_uso["alta"] = fuzz.trimf(horas_uso.universe, [250, 500, 500])

    temperatura["normal"] = fuzz.trimf(temperatura.universe, [20, 20, 65])
    temperatura["elevada"] = fuzz.trimf(temperatura.universe, [55, 75, 95])
    temperatura["critica"] = fuzz.trimf(temperatura.universe, [85, 120, 120])

    vibracion["baja"] = fuzz.trimf(vibracion.universe, [0, 0, 3])
    vibracion["moderada"] = fuzz.trimf(vibracion.universe, [2, 4.5, 7])
    vibracion["alta"] = fuzz.trimf(vibracion.universe, [5.5, 10, 10])

    urgencia["sin_accion"] = fuzz.trimf(urgencia.universe, [0, 0, 25])
    urgencia["monitorear"] = fuzz.trimf(urgencia.universe, [15, 35, 55])
    urgencia["programar"] = fuzz.trimf(urgencia.universe, [45, 65, 85])
    urgencia["urgente"] = fuzz.trimf(urgencia.universe, [70, 100, 100])

    reglas = [
        ctrl.Rule(horas_uso["baja"] & temperatura["normal"] & vibracion["baja"], urgencia["sin_accion"]),
        ctrl.Rule(horas_uso["baja"] & temperatura["normal"] & vibracion["moderada"], urgencia["monitorear"]),
        ctrl.Rule(horas_uso["media"] & temperatura["normal"] & vibracion["baja"], urgencia["monitorear"]),
        ctrl.Rule(horas_uso["media"] & temperatura["elevada"], urgencia["programar"]),
        ctrl.Rule(horas_uso["media"] & vibracion["moderada"], urgencia["programar"]),
        ctrl.Rule(horas_uso["alta"] & temperatura["normal"] & vibracion["baja"], urgencia["programar"]),
        ctrl.Rule(horas_uso["alta"] & (temperatura["elevada"] | vibracion["moderada"]), urgencia["urgente"]),
        ctrl.Rule(temperatura["critica"], urgencia["urgente"]),
        ctrl.Rule(vibracion["alta"], urgencia["urgente"]),
        ctrl.Rule(horas_uso["baja"] & temperatura["normal"] & vibracion["alta"], urgencia["urgente"]),
    ]
    return ctrl.ControlSystem(reglas)


sistema_control = construir_sistema()


def evaluar_maquina(h, t, v):
    """Misma lógica de 2 capas del backend: reglas duras + fuzzy."""
    if t >= 110:
        return 100, "URGENTE - DETENER MÁQUINA", (
            f"Temperatura de {t}°C supera el límite crítico de seguridad. "
            "Regla dura: detener la máquina de inmediato, sin importar los demás sensores."
        )
    if v >= 9.5:
        return 100, "URGENTE - DETENER MÁQUINA", (
            f"Vibración de {v} mm/s indica posible falla mecánica grave inminente. "
            "Regla dura: detener la máquina de inmediato."
        )

    sim = ctrl.ControlSystemSimulation(sistema_control)
    sim.input["horas_uso"] = np.clip(h, 0, 500)
    sim.input["temperatura"] = np.clip(t, 20, 120)
    sim.input["vibracion"] = np.clip(v, 0, 10)
    try:
    sim.compute()
    score = sim.output["urgencia"]
    except:
    return 0, "SIN ACCIÓN", "Combinación fuera de las reglas del sistema."

    if score < 25:
        etiqueta = "SIN ACCIÓN"
    elif score < 50:
        etiqueta = "MONITOREAR"
    elif score < 75:
        etiqueta = "PROGRAMAR MANTENIMIENTO"
    else:
        etiqueta = "URGENTE - PRIORITARIO"

    texto = (
        f"Con {h}h de uso, {t}°C y {v} mm/s de vibración, el sistema difuso "
        f"calcula una urgencia de {score:.1f}/100 → {etiqueta}."
    )
    return score, etiqueta, texto


COLORES = {
    "SIN ACCIÓN": "#2ecc71",
    "MONITOREAR": "#f1c40f",
    "PROGRAMAR MANTENIMIENTO": "#e67e22",
    "URGENTE - PRIORITARIO": "#e74c3c",
    "URGENTE - DETENER MÁQUINA": "#c0392b",
}

# ----------------------------------------------------------
# 2. ENCABEZADO
# ----------------------------------------------------------
st.title("🛠️ Sistema Experto de Mantenimiento Industrial")
st.caption("Recomendación con lógica difusa (fuzzy logic) + reglas duras de seguridad")

col_izq, col_der = st.columns([1, 1.4])

# ----------------------------------------------------------
# 3. PANEL DE CONTROLES (izquierda)
# ----------------------------------------------------------
with col_izq:
    st.subheader("Sensores de la máquina")

    h = st.slider("Horas de uso desde el último mantenimiento", 0, 500, 200, step=5)
    t = st.slider("Temperatura de operación (°C)", 20, 120, 70, step=1)
    v = st.slider("Vibración (mm/s)", 0.0, 10.0, 3.5, step=0.1)

    st.divider()
    st.markdown("**Casos rápidos de ejemplo:**")
    ejemplo = st.selectbox(
        "Cargar un caso predefinido",
        [
            "— Elegir —",
            "Máquina recién revisada",
            "Uso moderado",
            "Mucho uso y algo caliente",
            "Vibración alarmante",
            "Sobrecalentada",
        ],
    )
    presets = {
        "Máquina recién revisada": (20, 45, 1.2),
        "Uso moderado": (200, 68, 3.5),
        "Mucho uso y algo caliente": (420, 78, 4.8),
        "Vibración alarmante": (100, 50, 9.8),
        "Sobrecalentada": (300, 115, 5.0),
    }
    if ejemplo in presets:
        h, t, v = presets[ejemplo]
        st.info(f"Caso cargado: {h}h · {t}°C · {v} mm/s (ajusta los sliders arriba si quieres modificarlo)")

# ----------------------------------------------------------
# 4. RESULTADO (derecha)
# ----------------------------------------------------------
score, etiqueta, texto = evaluar_maquina(h, t, v)
color = COLORES.get(etiqueta, "#3498db")

with col_der:
    st.subheader("Diagnóstico del sistema experto")

    st.markdown(
        f"""
        <div style="padding: 1.2rem; border-radius: 12px; background-color:{color}22;
                    border: 2px solid {color};">
            <span style="font-size: 1.4rem; font-weight: 700; color:{color};">
                {etiqueta}
            </span>
            <br>
            <span style="font-size: 2.6rem; font-weight: 800; color:{color};">
                {score:.0f}/100
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.progress(min(int(score), 100))
    st.write(texto)

st.divider()

# ----------------------------------------------------------
# 5. SUPERFICIE DE DECISIÓN 3D INTERACTIVA
# ----------------------------------------------------------
st.subheader("Superficie de decisión (temperatura × vibración)")
st.caption(f"Calculada con horas de uso fijas en {h}h — gírala con el mouse")

temp_range = np.linspace(20, 120, 30)
vib_range = np.linspace(0, 10, 30)
Tg, Vg = np.meshgrid(temp_range, vib_range)
Z = np.zeros_like(Tg)
for i in range(Tg.shape[0]):
    for j in range(Tg.shape[1]):
        s, _, _ = evaluar_maquina(h, Tg[i, j], Vg[i, j])
        Z[i, j] = s

fig = go.Figure(data=[go.Surface(x=temp_range, y=vib_range, z=Z, colorscale="Turbo")])
fig.update_layout(
    scene=dict(
        xaxis_title="Temperatura (°C)",
        yaxis_title="Vibración (mm/s)",
        zaxis_title="Urgencia",
    ),
    height=500,
    margin=dict(l=0, r=0, t=10, b=0),
)
st.plotly_chart(fig, use_container_width=True)

st.caption(
    "Sistema experto híbrido: reglas duras de seguridad + inferencia difusa (scikit-fuzzy). "
    "Proyecto académico — Industrias Ariova."
)
