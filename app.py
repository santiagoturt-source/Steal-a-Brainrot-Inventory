import streamlit as st
import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd

# ============================
# 🔐 CONFIGURACIÓN FIREBASE
# ============================

if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["FIREBASE_KEY"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()
WEB_API_KEY = st.secrets["firebase"]["api_key"]

# ============================
# 🔐 FUNCIONES DE AUTENTICACIÓN
# ============================

def signup(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, data=payload).json()

def login(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, data=payload).json()

# ============================
# 📦 FUNCIONES DE PERFILES Y BRAINROTS
# ============================

def list_profiles(uid):
    col = db.collection("perfiles").document(uid).collection("data").stream()
    return [doc.id for doc in col]

def create_profile(uid, name):
    db.collection("perfiles").document(uid).collection("data").document(name).set({"brainrots": []})

def delete_profile(uid, name):
    db.collection("perfiles").document(uid).collection("data").document(name).delete()

def load_brainrots(uid, perfil):
    doc = db.collection("perfiles").document(uid).collection("data").document(perfil).get()
    return doc.to_dict().get("brainrots", []) if doc.exists else []

def save_brainrots(uid, perfil, brainrots):
    db.collection("perfiles").document(uid).collection("data").document(perfil).update({"brainrots": brainrots})

# ============================
# 📊 DATOS DE REFERENCIA
# ============================

BRAINROTS = {
    "Job Job Job Sahur": 700000,
    "Graipuss Medussi": 1000000,
    "Trenozostruzo Turbo 3000": 150000
}

COLORES = {
    "-": 1,
    "Gold": 1.25,
    "Galaxy": 7,
    "Rainbow": 10
}

MUTACIONES = {
    "Taco": 3,
    "Bubblegum": 4,
    "Matteo Hat": 4.5,
    "4th of July Fireworks": 6,
    "Glitch": 5
}

# ============================
# 🎨 INTERFAZ STREAMLIT
# ============================

st.title("🧠 Inventario de Brainrots — Cuentas como Etiquetas")

# Tabs de login/registro
tabs = st.tabs(["🔑 Iniciar sesión", "🆕 Registrarse"])

# ----------------------------
# TAB LOGIN
# ----------------------------
with tabs[0]:
    email = st.text_input("Correo", key="login_email")
    password = st.text_input("Contraseña", type="password", key="login_pass")

    if st.button("Entrar"):
        user = login(email, password)
        if "error" in user:
            st.error(user["error"]["message"])
        else:
            st.session_state["user"] = {"uid": user["localId"], "email": user["email"]}
            st.success(f"Sesión iniciada: {user['email']}")

# ----------------------------
# TAB REGISTRO
# ----------------------------
with tabs[1]:
    new_email = st.text_input("Correo nuevo", key="signup_email")
    new_pass = st.text_input("Contraseña nueva", type="password", key="signup_pass")

    if st.button("Crear cuenta"):
        user = signup(new_email, new_pass)
        if "error" in user:
            st.error(user["error"]["message"])
        else:
            st.success(f"Cuenta creada: {new_email}. Ahora puedes iniciar sesión.")

# ----------------------------
# GESTIÓN DE PERFILES Y BRAINROTS
# ----------------------------
st.subheader("👤 Gestión de Perfiles")

perfil_actual = None

if "user" in st.session_state and st.session_state["user"]:
    uid = st.session_state["user"]["uid"]
    perfiles = list_profiles(uid)

    if perfiles:
        perfil_actual = st.selectbox("Selecciona un perfil", ["(ninguno)"] + perfiles)
    else:
        st.info("No tienes perfiles creados todavía.")

    nuevo_perfil = st.text_input("Nombre de nuevo perfil")
    if st.button("➕ Crear perfil"):
        if nuevo_perfil:
            create_profile(uid, nuevo_perfil)
            st.success(f"Perfil '{nuevo_perfil}' creado.")
            st.rerun()

    if perfil_actual and perfil_actual != "(ninguno)":
        if st.button(f"🗑️ Borrar perfil '{perfil_actual}'"):
            delete_profile(uid, perfil_actual)
            st.success(f"Perfil '{perfil_actual}' borrado.")
            st.rerun()

        # ----------------------------
        # BRAINROTS EN EL PERFIL
        # ----------------------------
        st.subheader(f"🧠 Brainrots en perfil {perfil_actual}")

        brainrots = load_brainrots(uid, perfil_actual)

        # Formulario para añadir Brainrot
        with st.form("add_brainrot"):
            personaje = st.selectbox("Brainrot", list(BRAINROTS.keys()))
            color = st.selectbox("Color", list(COLORES.keys()))
            mutaciones = st.multiselect("Mutaciones", list(MUTACIONES.keys()))
            cuenta = st.text_input("Etiqueta de cuenta (ej: Cuenta A)")
            submitted = st.form_submit_button("Agregar")

            if submitted:
                base = BRAINROTS[personaje]
                total = base * COLORES[color] if color in COLORES else base
                for m in mutaciones:
                    total += base * MUTACIONES[m]

                nuevo = {
                    "personaje": personaje,
                    "color": color,
                    "mutaciones": mutaciones,
                    "cuenta": cuenta,
                    "total": total
                }
                brainrots.append(nuevo)
                save_brainrots(uid, perfil_actual, brainrots)
                st.success(f"{personaje} agregado en {cuenta} con total {total:,}")
                st.rerun()

        # Mostrar y administrar Brainrots
        if brainrots:
            df = pd.DataFrame(brainrots)

            orden = st.selectbox("Ordenar por", ["Total ↓", "Total ↑", "Cuenta", "Personaje"])
            if orden == "Total ↓":
                df = df.sort_values(by="total", ascending=False)
            elif orden == "Total ↑":
                df = df.sort_values(by="total", ascending=True)
            elif orden == "Cuenta":
                df = df.sort_values(by="cuenta")
            elif orden == "Personaje":
                df = df.sort_values(by="personaje")

            st.dataframe(df, use_container_width=True)

            # Borrar Brainrot
            to_delete = st.selectbox("Selecciona un Brainrot para borrar", ["(ninguno)"] + [f"{b['personaje']} ({b['cuenta']})" for b in brainrots])
            if st.button("🗑️ Borrar Brainrot") and to_delete != "(ninguno)":
                personaje_sel = to_delete.split(" (")[0]
                brainrots = [b for b in brainrots if b["personaje"] != personaje_sel]
                save_brainrots(uid, perfil_actual, brainrots)
                st.success(f"Brainrot '{to_delete}' borrado.")
                st.rerun()

            # Mover Brainrot a otra cuenta
            mover = st.selectbox("Selecciona un Brainrot para mover", ["(ninguno)"] + [f"{b['personaje']} ({b['cuenta']})" for b in brainrots])
            nueva_cuenta = st.text_input("Nueva etiqueta de cuenta")
            if st.button("🔄 Mover Brainrot") and mover != "(ninguno)" and nueva_cuenta:
                personaje_sel = mover.split(" (")[0]
                for b in brainrots:
                    if b["personaje"] == personaje_sel:
                        b["cuenta"] = nueva_cuenta
                save_brainrots(uid, perfil_actual, brainrots)
                st.success(f"Brainrot '{personaje_sel}' movido a cuenta '{nueva_cuenta}'.")
                st.rerun()

else:
    st.warning("Debes iniciar sesión para ver tus perfiles y brainrots.")














