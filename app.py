import streamlit as st
import requests
import json
import firebase_admin
from firebase_admin import credentials, firestore

# ============================
# 🔐 CONFIGURACIÓN FIREBASE
# ============================

# Inicializar Firebase Admin con credenciales de service account desde secrets
if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["FIREBASE_KEY"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Clave de API Web de Firebase Auth desde secrets
WEB_API_KEY = st.secrets["firebase"]["api_key"]

# ============================
# 🔐 FUNCIONES DE AUTENTICACIÓN
# ============================

def signup(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    res = requests.post(url, data=payload)
    return res.json()

def login(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    res = requests.post(url, data=payload)
    return res.json()

# ============================
# 📦 FUNCIONES DE PERFILES
# ============================

def list_profiles(uid):
    try:
        col = db.collection("perfiles").document(uid).collection("data").stream()
        return [doc.id for doc in col]
    except Exception as e:
        st.error(f"Error listando perfiles: {e}")
        return []

def create_profile(uid, name):
    db.collection("perfiles").document(uid).collection("data").document(name).set({"inventario": []})

def delete_profile(uid, name):
    db.collection("perfiles").document(uid).collection("data").document(name).delete()

# ============================
# 🎨 INTERFAZ STREAMLIT
# ============================

st.title("📒 Inventario con Usuarios + Perfiles")

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
# GESTIÓN DE PERFILES
# ----------------------------
st.subheader("👤 Gestión de Perfiles")

perfil_actual = None  # siempre inicializado

if "user" in st.session_state and st.session_state["user"]:
    uid = st.session_state["user"]["uid"]
    perfiles = list_profiles(uid)

    if perfiles:
        perfil_actual = st.selectbox("Selecciona un perfil", ["(ninguno)"] + perfiles)
    else:
        st.info("No tienes perfiles creados todavía.")

    # Crear nuevo perfil
    nuevo_perfil = st.text_input("Nombre de nuevo perfil")
    if st.button("➕ Crear perfil"):
        if nuevo_perfil:
            create_profile(uid, nuevo_perfil)
            st.success(f"Perfil '{nuevo_perfil}' creado.")
            st.experimental_rerun()

    # Borrar perfil seleccionado
    if perfil_actual and perfil_actual != "(ninguno)":
        if st.button(f"🗑️ Borrar perfil '{perfil_actual}'"):
            delete_profile(uid, perfil_actual)
            st.success(f"Perfil '{perfil_actual}' borrado.")
            st.experimental_rerun()

else:
    st.warning("Debes iniciar sesión para ver tus perfiles.")









