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

st.title("📒 Inventario de Brainrots")

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
                    if b["Cuenta"] == cuenta_borrar:
                        b["Cuenta"] = "(ninguna)"
                save_data(uid, perfil_actual, brainrots, cuentas)
                st.success(f"Cuenta '{cuenta_borrar}' borrada.")
                st.rerun()

        # ----------------------------
        # Agregar Brainrot
        # ----------------------------
        st.markdown("### ➕ Agregar Brainrot")

        # Lista fija de Brainrots con valores base
        BRAINROTS = {
            "Graipuss Medussi": 150000,
            "Job Job Job Sahur": 8293023,
            "Trenozostruzo Turbo 3000": 225000,
            "Blackhole Goat": 420000,
            "La Vaca Saturno Saturnina": 300000
        }

        # Colores con multiplicadores
        COLORES = {
            "-": 0,
            "Gold": 1.25,
            "Rainbow": 10,
            "Galaxy": 7,
            "Candy": 4,
            "Diamond": 17
        }

        # Mutaciones con multiplicadores
        MUTACIONES = {
            "Taco": 3,
            "Matteo Hat": 4.5,
            "UFO": 3,
            "Concert / Disco": 5,
            "Bubblegum": 4,
            "Fire (Solar Flare)": 6,
            "Glitch": 5,
            "Crab Rave": 5,
            "Nyan Cat": 6,
            "Lightning": 6
        }

        # Selección del Brainrot
        personaje = st.selectbox(
            "Selecciona un Brainrot",
            ["(ninguno)"] + [f"{k} — {format_num(v)}" for k, v in BRAINROTS.items()]
        )

        color = st.selectbox("Color", list(COLORES.keys()))
        mutaciones = st.multiselect("Mutaciones", list(MUTACIONES.keys()), max_selections=5)
        cuenta_sel = st.selectbox("Cuenta", ["(ninguna)"] + cuentas)

        if st.button("Agregar") and personaje != "(ninguno)":
            # Extraer nombre limpio y valor base
            nombre = personaje.split(" — ")[0]
            base = BRAINROTS[nombre]

            # Calcular total
            total = base
            if color != "-":
                total += base * COLORES[color]
            for m in mutaciones:
                total += base * MUTACIONES[m]

            brainrots.append({
                "Brainrot": nombre,
                "Color": color,
                "Mutaciones": mutaciones,
                "Cuenta": cuenta_sel,
                "Total": total
            })
            save_data(uid, perfil_actual, brainrots, cuentas)
            st.success(f"Brainrot '{nombre}' agregado con total {format_num(total)}.")
            st.rerun()

        # ----------------------------
        # Mostrar tabla
        # ----------------------------
        # ----------------------------
# Mostrar tabla y gestionar Brainrots
# ----------------------------
# ----------------------------
# Mostrar tabla y gestionar Brainrots
# ----------------------------
if brainrots:
    # Normalizar claves antiguas
    for b in brainrots:
        if "personaje" in b:
            b["Brainrot"] = b.pop("personaje")
        if "nombre" in b:
            b["Brainrot"] = b.pop("nombre")
        if "color" in b:
            b["Color"] = b.pop("color")
        if "mutaciones" in b:
            b["Mutaciones"] = b.pop("mutaciones")
        if "cuenta" in b:
            b["Cuenta"] = b.pop("cuenta")
        if "total" in b:
            b["Total"] = b.pop("total")

    df = pd.DataFrame(brainrots)

    # Ordenamiento
    orden = st.selectbox("Ordenar por", ["Total ↓", "Total ↑", "Cuenta", "Brainrot"])
    if orden == "Total ↓":
        df = df.sort_values(by="Total", ascending=False)
    elif orden == "Total ↑":
        df = df.sort_values(by="Total", ascending=True)
    elif orden == "Cuenta":
        df = df.sort_values(by="Cuenta")
    elif orden == "Brainrot":
        df = df.sort_values(by="Brainrot")

    # Mostrar tabla limpia
    df_vista = df.copy()
    df_vista["Total"] = df_vista["Total"].apply(format_num)
    st.markdown("### 📊 Inventario de Brainrots")
    st.dataframe(df_vista[["Brainrot", "Cuenta", "Total", "Color", "Mutaciones"]].reset_index(drop=True), use_container_width=True)

    # ----------------------------
# Borrar / Mover Brainrots
# ----------------------------
st.markdown("### 🗑️🔄 Borrar / Mover Brainrots")

opciones_brainrots = ["(ninguno)"] + [brainrot_label(b) for b in brainrots]

# Borrar
to_delete = st.selectbox("Selecciona un Brainrot para borrar", opciones_brainrots)
if st.button("🗑️ Borrar Brainrot") and to_delete != "(ninguno)":
    personaje_sel = to_delete.split(" | ")[0]
    brainrots = [b for b in brainrots if b.get("Brainrot", "???") != personaje_sel]
    save_data(uid, perfil_actual, brainrots, cuentas)
    st.success(f"Brainrot '{personaje_sel}' borrado.")
    st.rerun()

# Mover
mover = st.selectbox("Selecciona un Brainrot para mover", opciones_brainrots)
nueva_cuenta_sel = st.selectbox("Mover a cuenta", ["(ninguna)"] + cuentas)
if st.button("🔄 Mover Brainrot") and mover != "(ninguno)" and nueva_cuenta_sel != "(ninguna)":
    personaje_sel = mover.split(" | ")[0]
    for b in brainrots:
        if b.get("Brainrot", "???") == personaje_sel:
            b["Cuenta"] = nueva_cuenta_sel
    save_data(uid, perfil_actual, brainrots, cuentas)
    st.success(f"Brainrot '{personaje_sel}' movido a cuenta '{nueva_cuenta_sel}'.")
    st.rerun()



























