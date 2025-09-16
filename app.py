import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import uuid  # ✅ Para IDs únicos

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
        return f"${num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"${num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"${num/1_000:.1f}K"
    else:
        return f"${num}"

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

# ----------------------------
# LOGIN / REGISTRO
# ----------------------------
if "user" not in st.session_state:
    tabs = st.tabs(["🔑 Iniciar sesión", "🆕 Registrarse"])

    with tabs[0]:
        email = st.text_input("Correo", key="login_email_input")
        password = st.text_input("Contraseña", type="password", key="login_pass_input")
        if st.button("Entrar", key="login_button"):
            user = login(email, password)
            if "error" in user:
                st.error(user["error"]["message"])
            else:
                st.session_state["user"] = {"uid": user["localId"], "email": user["email"]}
                st.success(f"Sesión iniciada: {user['email']}")
                st.rerun()

    with tabs[1]:
        new_email = st.text_input("Correo nuevo", key="signup_email_input")
        new_pass = st.text_input("Contraseña nueva", type="password", key="signup_pass_input")
        if st.button("Crear cuenta", key="signup_button"):
            user = signup(new_email, new_pass)
            if "error" in user:
                st.error(user["error"]["message"])
            else:
                st.success(f"Cuenta creada: {new_email}. Ahora puedes iniciar sesión.")

else:
    st.success(f"✅ Bienvenido {st.session_state['user']['email']}")
    uid = st.session_state["user"]["uid"]
    perfiles = list_profiles(uid)

    # ============================
    # PESTAÑAS PRINCIPALES
    # ============================
    pestañas = st.tabs([
        "👤 Gestión de Perfiles",
        "📦 Inventario",
        "🗑️ 🔄 Borrar / Mover Brainrots",
        "🚪 Cerrar Sesión"
    ])

    # ----------------------------
    # TAB 1: GESTIÓN DE PERFILES
    # ----------------------------
    with pestañas[0]:
        st.subheader("👤 Gestión de Perfiles")
        perfil_actual = None

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
    # TAB 2: INVENTARIO
    # ----------------------------
    with pestañas[1]:
        if "perfil_actual" not in locals() or not perfil_actual or perfil_actual == "(ninguno)":
            st.warning("Selecciona un perfil en la pestaña de gestión de perfiles.")
        else:
            brainrots, cuentas = load_data(uid, perfil_actual)

            st.subheader(f"📦 Inventario — Perfil: {perfil_actual}")

            BRAINROTS = {
                "Graipuss Medussi": 150000,
                "Job Job Job Sahur": 8293023,
                "Trenozostruzo Turbo 3000": 225000,
                "Blackhole Goat": 420000,
                "La Vaca Saturno Saturnina": 300000,
                "Bominitos": 550000,
                "Sammyni Spiderini": 290000
            }

            COLORES = {
                "-": 0,
                "Gold": 1.25,
                "Rainbow": 10,
                "Galaxy": 7,
                "Candy": 4,
                "Diamond": 17
            }

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

            personaje = st.selectbox(
                "Selecciona un Brainrot",
                ["(ninguno)"] + [f"{k} — {format_num(v)}" for k, v in BRAINROTS.items()]
            )

            color = st.selectbox("Color", list(COLORES.keys()))
            mutaciones = st.multiselect("Mutaciones", list(MUTACIONES.keys()), max_selections=5)
            cuenta_sel = st.text_input("Cuenta", "(ninguna)")

            if st.button("Agregar") and personaje != "(ninguno)":
                nombre = personaje.split(" — ")[0]
                base = BRAINROTS[nombre]

                multiplicador = 1.0
                if color != "-":
                    multiplicador += COLORES[color]
                for m in mutaciones:
                    multiplicador += MUTACIONES[m]

                total = base * multiplicador

                brainrots.append({
                    "id": str(uuid.uuid4()),
                    "Brainrot": nombre,
                    "Color": color,
                    "Mutaciones": mutaciones,
                    "Cuenta": cuenta_sel,
                    "Total": total
                })
                save_data(uid, perfil_actual, brainrots, cuentas)
                st.success(f"Brainrot '{nombre}' agregado con total {format_num(total)}.")
                st.rerun()

            if brainrots:
                df = pd.DataFrame(brainrots)
                df["Total"] = df["Total"].apply(format_num)
                df = df.drop(columns=["id"], errors="ignore")
                st.dataframe(df.reset_index(drop=True).style.hide(axis="index"), use_container_width=True)

    # ----------------------------
    # TAB 3: BORRAR / MOVER
    # ----------------------------
    with pestañas[2]:
        if "perfil_actual" not in locals() or not perfil_actual or perfil_actual == "(ninguno)":
            st.warning("Selecciona un perfil en la pestaña de gestión de perfiles.")
        else:
            brainrots, cuentas = load_data(uid, perfil_actual)

            st.markdown("### 🗑️ 🔄 Borrar / Mover Brainrots")

            def brainrot_label(b):
                parts = [f"{b['Brainrot']}", f"Cuenta: {b['Cuenta']}", f"Total: {format_num(b['Total'])}"]
                if b.get("Color") and b["Color"] != "-":
                    parts.append(f"Color: {b['Color']}")
                if b.get("Mutaciones"):
                    parts.append(f"Mutaciones: {', '.join(b['Mutaciones'])}")
                return " | ".join(parts), b["id"]

            opciones_brainrots = ["(ninguno)"] + [brainrot_label(b)[0] for b in brainrots]
            ids_map = {brainrot_label(b)[0]: brainrot_label(b)[1] for b in brainrots}

            to_delete = st.selectbox("Selecciona un Brainrot para borrar", opciones_brainrots)
            if st.button("🗑️ Borrar Brainrot") and to_delete != "(ninguno)":
                brainrot_id = ids_map[to_delete]
                brainrots = [b for b in brainrots if b["id"] != brainrot_id]
                save_data(uid, perfil_actual, brainrots, cuentas)
                st.success("Brainrot borrado.")
                st.rerun()

            mover = st.selectbox("Selecciona un Brainrot para mover", opciones_brainrots)
            nueva_cuenta_sel = st.text_input("Mover a cuenta", "(ninguna)")
            if st.button("🔄 Mover Brainrot") and mover != "(ninguno)" and nueva_cuenta_sel != "(ninguna)":
                brainrot_id = ids_map[mover]
                for b in brainrots:
                    if b["id"] == brainrot_id:
                        b["Cuenta"] = nueva_cuenta_sel
                save_data(uid, perfil_actual, brainrots, cuentas)
                st.success(f"Brainrot movido a cuenta '{nueva_cuenta_sel}'.")
                st.rerun()

    # ----------------------------
    # TAB 4: CERRAR SESIÓN
    # ----------------------------
    with pestañas[3]:
        if st.button("🚪 Cerrar sesión"):
            del st.session_state["user"]
            st.rerun()



















































