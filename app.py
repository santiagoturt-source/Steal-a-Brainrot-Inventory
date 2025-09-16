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
# 📊 FUNCIONES AUXILIARES
# ============================

def format_num(num):
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return str(num)

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
    db.collection("perfiles").document(uid).collection("data").document(name).set({
        "brainrots": [],
        "cuentas": []
    })

def delete_profile(uid, name):
    db.collection("perfiles").document(uid).collection("data").document(name).delete()

def load_data(uid, perfil):
    doc = db.collection("perfiles").document(uid).collection("data").document(perfil).get()
    if doc.exists:
        data = doc.to_dict()
        return data.get("brainrots", []), data.get("cuentas", [])
    return [], []

def save_data(uid, perfil, brainrots, cuentas):
    db.collection("perfiles").document(uid).collection("data").document(perfil).set({
        "brainrots": brainrots,
        "cuentas": cuentas
    })

# ============================
# 🎨 INTERFAZ STREAMLIT
# ============================

st.title("📒 Inventario con Usuarios + Perfiles + Brainrots")

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
            st.rerun()

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

    # ============================
    # 📦 INVENTARIO DE BRAINROTS
    # ============================
    if perfil_actual and perfil_actual != "(ninguno)":
        brainrots, cuentas = load_data(uid, perfil_actual)

        st.subheader(f"📦 Inventario — Perfil: {perfil_actual}")

        # ----------------------------
        # Gestión de cuentas
        # ----------------------------
        st.markdown("### 🏷️ Gestión de cuentas")
        nueva_cuenta = st.text_input("Nombre de nueva cuenta")
        if st.button("➕ Agregar cuenta"):
            if nueva_cuenta and nueva_cuenta not in cuentas:
                cuentas.append(nueva_cuenta)
                save_data(uid, perfil_actual, brainrots, cuentas)
                st.success(f"Cuenta '{nueva_cuenta}' añadida.")
                st.rerun()

        if cuentas:
            cuenta_borrar = st.selectbox("Selecciona una cuenta para borrar", ["(ninguna)"] + cuentas)
            if st.button("🗑️ Borrar cuenta") and cuenta_borrar != "(ninguna)":
                cuentas = [c for c in cuentas if c != cuenta_borrar]
                for b in brainrots:
                    if b["cuenta"] == cuenta_borrar:
                        b["cuenta"] = "(ninguna)"
                save_data(uid, perfil_actual, brainrots, cuentas)
                st.success(f"Cuenta '{cuenta_borrar}' borrada.")
                st.rerun()

        # ----------------------------
        # Agregar Brainrot
        # ----------------------------
        st.markdown("### ➕ Agregar Brainrot")
        personaje = st.text_input("Nombre del Brainrot")
        color = st.text_input("Color", value="-")
        mutaciones = st.text_area("Mutaciones (separadas por coma)")
        cuenta_sel = st.selectbox("Cuenta", ["(ninguna)"] + cuentas)
        total = st.number_input("Valor base", min_value=0, step=1000)

        if st.button("Agregar"):
            brainrots.append({
                "personaje": personaje,
                "color": color,
                "mutaciones": [m.strip() for m in mutaciones.split(",") if m.strip()],
                "cuenta": cuenta_sel,
                "total": total
            })
            save_data(uid, perfil_actual, brainrots, cuentas)
            st.success(f"Brainrot '{personaje}' agregado.")
            st.rerun()

        # ----------------------------
        # Mostrar tabla
        # ----------------------------
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

            df["total"] = df["total"].apply(format_num)
            st.dataframe(df.reset_index(drop=True), use_container_width=True)

            # ----------------------------
            # Opciones de borrar/mover
            # ----------------------------
            def brainrot_label(b):
                parts = [b["personaje"]]
                if b.get("cuenta") and b["cuenta"] != "(ninguna)":
                    parts.append(f"[{b['cuenta']}]")
                if b.get("color") and b["color"] != "-":
                    parts.append(f"Color: {b['color']}")
                if b.get("mutaciones"):
                    parts.append(f"Mutaciones: {', '.join(b['mutaciones'])}")
                parts.append(f"Total: {format_num(b['total'])}")
                return " | ".join(parts)

            opciones_brainrots = ["(ninguno)"] + [brainrot_label(b) for b in brainrots]

            # Borrar
            to_delete = st.selectbox("Selecciona un Brainrot para borrar", opciones_brainrots)
            if st.button("🗑️ Borrar Brainrot") and to_delete != "(ninguno)":
                personaje_sel = to_delete.split(" | ")[0]
                brainrots = [b for b in brainrots if b["personaje"] != personaje_sel]
                save_data(uid, perfil_actual, brainrots, cuentas)
                st.success(f"Brainrot '{to_delete}' borrado.")
                st.rerun()

            # Mover
            mover = st.selectbox("Selecciona un Brainrot para mover", opciones_brainrots)
            nueva_cuenta_sel = st.selectbox("Mover a cuenta", ["(ninguna)"] + cuentas)
            if st.button("🔄 Mover Brainrot") and mover != "(ninguno)" and nueva_cuenta_sel != "(ninguna)":
                personaje_sel = mover.split(" | ")[0]
                for b in brainrots:
                    if b["personaje"] == personaje_sel:
                        b["cuenta"] = nueva_cuenta_sel
                save_data(uid, perfil_actual, brainrots, cuentas)
                st.success(f"Brainrot '{personaje_sel}' movido a cuenta '{nueva_cuenta_sel}'.")
                st.rerun()

else:
    st.warning("Debes iniciar sesión para ver tus perfiles.")
















