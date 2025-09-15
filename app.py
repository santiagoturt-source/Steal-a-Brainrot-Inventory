import streamlit as st
import pandas as pd
import requests
import firebase_admin
from firebase_admin import credentials, firestore

# ================================
# CONFIGURACIÓN FIREBASE
# ================================
FIREBASE_KEY = "firebase_key.json"  # tu clave privada descargada
WEB_API_KEY = "TU_FIREBASE_WEB_API_KEY"  # ⚠️ reemplaza con tu API Key de Firebase

if not firebase_admin._apps:
    cred = credentials.Certificate(FIREBASE_KEY)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ================================
# FUNCIONES AUTENTICACIÓN
# ================================
def signup_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    res = requests.post(url, json=payload)
    return res.json()

def login_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    res = requests.post(url, json=payload)
    return res.json()

# ================================
# FUNCIONES DE PERFILES
# ================================
def list_profiles(uid):
    col = db.collection("perfiles").document(uid).collection("data").stream()
    return [doc.id for doc in col]

def save_profile(uid, name):
    ref = db.collection("perfiles").document(uid).collection("data").document(name)
    ref.set({"rows": []})  # por ahora un inventario vacío

def delete_profile(uid, name):
    db.collection("perfiles").document(uid).collection("data").document(name).delete()

# ================================
# INTERFAZ
# ================================
if "user" not in st.session_state:
    st.session_state["user"] = None

st.title("📒 Inventario — Paso 1: Usuarios + Perfiles")

# ---------- LOGIN / REGISTRO ----------
if not st.session_state["user"]:
    tab1, tab2 = st.tabs(["🔑 Iniciar sesión", "🆕 Registrarse"])

    with tab1:
        email = st.text_input("Correo", key="login_email")
        password = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Entrar"):
            res = login_user(email, password)
            if "error" in res:
                st.error(res["error"]["message"])
            else:
                st.session_state["user"] = {"email": email, "uid": res["localId"]}
                st.success("Sesión iniciada")
                st.rerun()

    with tab2:
        email = st.text_input("Correo nuevo", key="signup_email")
        password = st.text_input("Contraseña nueva", type="password", key="signup_pass")
        if st.button("Crear cuenta"):
            res = signup_user(email, password)
            if "error" in res:
                st.error(res["error"]["message"])
            else:
                st.success("Cuenta creada. Ahora inicia sesión en la pestaña anterior.")

# ---------- PÁGINA PRINCIPAL (LOGUEADO) ----------
else:
    user = st.session_state["user"]
    st.sidebar.success(f"Conectado como {user['email']}")

    st.subheader("👤 Gestión de perfiles")

    perfiles = list_profiles(user["uid"])
    if perfiles:
        perfil_actual = st.selectbox("Selecciona un perfil", perfiles)
    else:
        st.info("No tienes perfiles aún.")

    nuevo = st.text_input("Nombre de perfil nuevo")
    if st.button("Crear perfil"):
        if nuevo:
            save_profile(user["uid"], nuevo)
            st.success(f"Perfil {nuevo} creado")
            st.rerun()
        else:
            st.warning("Escribe un nombre para el perfil.")

    if perfiles:
        if st.button("Borrar perfil seleccionado"):
            delete_profile(user["uid"], perfil_actual)
            st.warning(f"Perfil {perfil_actual} borrado")
            st.rerun()

    if st.button("Cerrar sesión"):
        st.session_state["user"] = None
        st.rerun()


