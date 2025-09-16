import streamlit as st
import pandas as pd
import json
import firebase_admin
from firebase_admin import credentials, firestore
import pyrebase

# ---- CONFIGURACIÓN ----
st.set_page_config(page_title="Inventario con Usuarios + Perfiles", layout="wide")

# ---- CSS ----
st.markdown("""
    <style>
        .card {
            background-color: #1e1e1e;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            border: 1px solid #444;
        }
        .card h3 {
            color: #a970ff;
            margin-bottom: 15px;
        }
    </style>
""", unsafe_allow_html=True)

# ---- FIREBASE ----
if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["FIREBASE_KEY"]))
    firebase_admin.initialize_app(cred)
db = firestore.client()

firebase_config = {
    "apiKey": st.secrets["firebase"]["api_key"],
    "authDomain": st.secrets["firebase"]["auth_domain"],
    "projectId": st.secrets["firebase"]["project_id"],
    "storageBucket": st.secrets["firebase"]["storage_bucket"],
    "messagingSenderId": st.secrets["firebase"]["messaging_sender_id"],
    "appId": st.secrets["firebase"]["app_id"],
}
firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# ---- LOGIN ----
with st.container():
    st.markdown("<div class='card'><h3>🔑 Iniciar sesión / Registro</h3>", unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Iniciar sesión", "Registrarse"])
    with tab_login:
        email = st.text_input("Correo", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Entrar"):
            try:
                user = auth.sign_in_with_email_and_password(email, password)
                st.session_state["user"] = user
                st.success("Sesión iniciada correctamente")
            except Exception:
                st.error("Error al iniciar sesión")

    with tab_register:
        email_new = st.text_input("Correo nuevo", key="reg_email")
        password_new = st.text_input("Contraseña nueva", type="password", key="reg_pass")
        if st.button("Crear cuenta"):
            try:
                user = auth.create_user_with_email_and_password(email_new, password_new)
                st.success("Cuenta creada correctamente")
            except Exception:
                st.error("Error al crear cuenta")

    st.markdown("</div>", unsafe_allow_html=True)

if "user" not in st.session_state:
    st.warning("Debes iniciar sesión para ver tus perfiles.")
    st.stop()

user = st.session_state["user"]
uid = user["localId"]

# ---- FUNCIONES ----
def list_profiles(uid):
    col = db.collection("perfiles").document(uid).collection("data").stream()
    return [doc.id for doc in col]

def get_profile_data(uid, perfil):
    return db.collection("perfiles").document(uid).collection("data").document(perfil).get().to_dict()

def save_profile_data(uid, perfil, data):
    db.collection("perfiles").document(uid).collection("data").document(perfil).set(data)

# ---- PERFILES ----
with st.container():
    st.markdown("<div class='card'><h3>👤 Gestión de Perfiles</h3>", unsafe_allow_html=True)
    perfiles = list_profiles(uid)
    perfil_actual = st.selectbox("Selecciona un perfil", ["(ninguno)"] + perfiles)
    nuevo_perfil = st.text_input("Nombre de nuevo perfil")
    if st.button("➕ Crear perfil"):
        if nuevo_perfil:
            save_profile_data(uid, nuevo_perfil, {"brainrots": [], "cuentas": []})
            st.success(f"Perfil '{nuevo_perfil}' creado.")
            st.rerun()
    if perfil_actual != "(ninguno)" and st.button(f"🗑️ Borrar perfil '{perfil_actual}'"):
        db.collection("perfiles").document(uid).collection("data").document(perfil_actual).delete()
        st.success(f"Perfil '{perfil_actual}' borrado.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

if perfil_actual == "(ninguno)":
    st.stop()

perfil_data = get_profile_data(uid, perfil_actual)
if perfil_data is None:
    perfil_data = {"brainrots": [], "cuentas": []}

# ---- CUENTAS ----
with st.container():
    st.markdown("<div class='card'><h3>🏷️ Gestión de Cuentas</h3>", unsafe_allow_html=True)
    nueva_cuenta = st.text_input("Nombre de nueva cuenta")
    if st.button("➕ Agregar cuenta"):
        if nueva_cuenta and nueva_cuenta not in perfil_data["cuentas"]:
            perfil_data["cuentas"].append(nueva_cuenta)
            save_profile_data(uid, perfil_actual, perfil_data)
            st.success(f"Cuenta '{nueva_cuenta}' añadida.")
            st.rerun()

    cuenta_borrar = st.selectbox("Selecciona una cuenta para borrar", ["(ninguna)"] + perfil_data["cuentas"])
    if st.button("🗑️ Borrar cuenta"):
        if cuenta_borrar != "(ninguna)":
            perfil_data["cuentas"].remove(cuenta_borrar)
            save_profile_data(uid, perfil_actual, perfil_data)
            st.warning(f"Cuenta '{cuenta_borrar}' eliminada.")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ---- AGREGAR BRAINROT ----
with st.container():
    st.markdown("<div class='card'><h3>➕ Agregar Brainrot</h3>", unsafe_allow_html=True)
    nombre = st.text_input("Nombre del Brainrot")
    color = st.selectbox("Color", ["-", "Gold", "Rainbow"])
    mutaciones = st.multiselect("Mutaciones", ["Taco", "Matteo Hat", "Glow", "Shadow"])
    cuenta = st.selectbox("Cuenta", ["(ninguna)"] + perfil_data["cuentas"])
    valor_base = st.number_input("Valor base", min_value=0, step=1000)

    if st.button("Agregar Brainrot"):
        brainrot = {"nombre": nombre, "color": color, "mutaciones": mutaciones, "cuenta": cuenta, "total": valor_base}
        perfil_data["brainrots"].append(brainrot)
        save_profile_data(uid, perfil_actual, perfil_data)
        st.success(f"Brainrot '{nombre}' agregado.")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ---- TABLA ----
with st.container():
    st.markdown("<div class='card'><h3>📊 Inventario de Brainrots</h3>", unsafe_allow_html=True)
    brainrots = perfil_data.get("brainrots", [])
    if brainrots:
        df = pd.DataFrame(brainrots)
        df["mutaciones"] = df["mutaciones"].apply(lambda x: ", ".join(x) if x else "-")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No hay Brainrots aún.")
    st.markdown("</div>", unsafe_allow_html=True)

# ---- BORRAR / MOVER ----
with st.container():
    st.markdown("<div class='card'><h3>🗑️➡️ Borrar / Mover Brainrots</h3>", unsafe_allow_html=True)

    opciones = ["(ninguno)"] + [
        f"{b['nombre']} | Total: {b['total']} | Cuenta: {b['cuenta']} | Color: {b['color']} | Mutaciones: {', '.join(b['mutaciones']) if b['mutaciones'] else '-'}"
        for b in brainrots
    ]

    borrar = st.selectbox("Selecciona un Brainrot para borrar", opciones, key="borrar_br")
    if st.button("🗑️ Borrar Brainrot"):
        if borrar != "(ninguno)":
            idx = opciones.index(borrar) - 1
            eliminado = perfil_data["brainrots"].pop(idx)
            save_profile_data(uid, perfil_actual, perfil_data)
            st.warning(f"Brainrot '{eliminado['nombre']}' eliminado.")
            st.rerun()

    mover = st.selectbox("Selecciona un Brainrot para mover", opciones, key="mover_br")
    mover_a = st.selectbox("Mover a cuenta", ["(ninguna)"] + perfil_data["cuentas"])
    if st.button("➡️ Mover Brainrot"):
        if mover != "(ninguno)" and mover_a != "(ninguna)":
            idx = opciones.index(mover) - 1
            perfil_data["brainrots"][idx]["cuenta"] = mover_a
            save_profile_data(uid, perfil_actual, perfil_data)
            st.success(f"Brainrot '{perfil_data['brainrots'][idx]['nombre']}' movido a cuenta {mover_a}.")
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)






















