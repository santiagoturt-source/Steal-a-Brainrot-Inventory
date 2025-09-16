import streamlit as st
import pandas as pd
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore

# ============================
# Ajustes de página y estilos
# ============================
st.set_page_config(page_title="Inventario con Usuarios + Perfiles", layout="wide")

st.markdown("""
<style>
.card {
  background: #1e1e1e;
  border: 1px solid #3a3a3a;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
}
.card h3 { margin-top: 0; color: #b69cff; }
.badge { padding: 2px 8px; border-radius: 999px; background:#2a2a2a; border:1px solid #444; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# ============================
# Firebase (admin + REST auth)
# ============================
# secrets esperados:
# st.secrets["FIREBASE_KEY"]       -> JSON del service account (string o dict)
# st.secrets["firebase"]["api_key"] -> API key de Firebase (web)

def _load_service_account():
    key = st.secrets["FIREBASE_KEY"]
    if isinstance(key, str):
        return json.loads(key)
    return dict(key)

if not firebase_admin._apps:
    cred = credentials.Certificate(_load_service_account())
    firebase_admin.initialize_app(cred)
db = firestore.client()

WEB_API_KEY = st.secrets["firebase"]["api_key"]

def fb_signup(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()

def fb_login(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()

# ============================
# Utilidades
# ============================
def format_num(num: float) -> str:
    try:
        n = float(num)
    except Exception:
        return str(num)
    if n >= 1_000_000_000:
        return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return f"{int(n):,}".replace(",", ".")

def list_profiles(uid: str):
    col = db.collection("perfiles").document(uid).collection("data").stream()
    return [doc.id for doc in col]

def load_profile(uid: str, perfil: str):
    doc = db.collection("perfiles").document(uid).collection("data").document(perfil).get()
    if doc.exists:
        data = doc.to_dict()
        return data.get("brainrots", []), data.get("cuentas", [])
    return [], []

def save_profile(uid: str, perfil: str, brainrots, cuentas):
    db.collection("perfiles").document(uid).collection("data").document(perfil).set({
        "brainrots": brainrots,
        "cuentas": cuentas
    })

def create_profile(uid: str, nombre: str):
    save_profile(uid, nombre, [], [])

def delete_profile(uid: str, nombre: str):
    db.collection("perfiles").document(uid).collection("data").document(nombre).delete()

# ============================
# Catálogos (valores y multip.)
# ============================
BRAINROTS_BASE = {
    "Graipuss Medussi": 150000,
    "Job Job Job Sahur": 8293023,
    "Trenozostruzo Turbo 3000": 225000,
    "Blackhole Goat": 420000,
    "La Vaca Saturno Saturnina": 300000,
}

COLORES_MULT = {
    "-": 0,
    "Gold": 1.25,
    "Rainbow": 10,
    "Galaxy": 7,
    "Candy": 4,
    "Diamond": 17,
}

MUTACIONES_MULT = {
    "Taco": 3,
    "Matteo Hat": 4.5,
    "UFO": 3,
    "Concert / Disco": 5,
    "Bubblegum": 4,
    "Fire (Solar Flare)": 6,
    "Glitch": 5,
    "Crab Rave": 5,
    "Nyan Cat": 6,
    "Lightning": 6,
}

def calc_total(base: int, color: str, mutaciones: list[str]) -> float:
    total = base
    if color in COLORES_MULT and color != "-":
        total += base * COLORES_MULT[color]
    for m in mutaciones or []:
        if m in MUTACIONES_MULT:
            total += base * MUTACIONES_MULT[m]
    return total

# ============================
# Login / Registro
# ============================
with st.container():
    st.markdown("<div class='card'><h3>🔑 Iniciar sesión / Registrarse</h3>", unsafe_allow_html=True)
    tab_login, tab_signup = st.tabs(["Iniciar sesión", "Registrarse"])

    with tab_login:
        lemail = st.text_input("Correo", key="login_email")
        lpass = st.text_input("Contraseña", type="password", key="login_pass")
        if st.button("Entrar"):
            if not lemail or not lpass:
                st.error("Ingresa correo y contraseña.")
            else:
                res = fb_login(lemail, lpass)
                if "error" in res:
                    st.error(res["error"]["message"])
                else:
                    st.session_state["user"] = {"uid": res["localId"], "email": res["email"]}
                    st.success(f"Sesión iniciada: {res['email']}")
                    st.rerun()

    with tab_signup:
        semail = st.text_input("Correo nuevo", key="signup_email")
        spass = st.text_input("Contraseña nueva", type="password", key="signup_pass")
        if st.button("Crear cuenta"):
            if not semail or not spass:
                st.error("Ingresa correo y contraseña.")
            else:
                res = fb_signup(semail, spass)
                if "error" in res:
                    st.error(res["error"]["message"])
                else:
                    st.success("Cuenta creada. Ahora inicia sesión.")
    st.markdown("</div>", unsafe_allow_html=True)

if "user" not in st.session_state:
    st.stop()

uid = st.session_state["user"]["uid"]

# ============================
# Gestión de perfiles
# ============================
with st.container():
    st.markdown("<div class='card'><h3>👤 Gestión de Perfiles</h3>", unsafe_allow_html=True)
    perfiles = list_profiles(uid)
    perfil_actual = st.selectbox("Selecciona un perfil", ["(ninguno)"] + perfiles, key="perfil_sel")

    nuevo_perfil = st.text_input("Nombre de nuevo perfil", key="perfil_nuevo")
    colp1, colp2 = st.columns(2)
    with colp1:
        if st.button("➕ Crear perfil"):
            if nuevo_perfil:
                create_profile(uid, nuevo_perfil)
                st.success(f"Perfil '{nuevo_perfil}' creado.")
                st.rerun()
    with colp2:
        if perfil_actual != "(ninguno)" and st.button(f"🗑️ Borrar perfil '{perfil_actual}'"):
            delete_profile(uid, perfil_actual)
            st.success(f"Perfil '{perfil_actual}' borrado.")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

if perfil_actual == "(ninguno)":
    st.stop()

brainrots, cuentas = load_profile(uid, perfil_actual)

# ============================
# Gestión de cuentas
# ============================
with st.container():
    st.markdown("<div class='card'><h3>🏷️ Gestión de Cuentas</h3>", unsafe_allow_html=True)
    nueva_cuenta = st.text_input("Nombre de nueva cuenta", key="nueva_cuenta")
    colc1, colc2 = st.columns(2)
    with colc1:
        if st.button("➕ Agregar cuenta"):
            if nueva_cuenta and nueva_cuenta not in cuentas:
                cuentas.append(nueva_cuenta)
                save_profile(uid, perfil_actual, brainrots, cuentas)
                st.success(f"Cuenta '{nueva_cuenta}' añadida.")
                st.rerun()
    with colc2:
        cuenta_borrar = st.selectbox("Selecciona una cuenta para borrar", ["(ninguna)"] + cuentas, key="cuenta_borrar")
        if st.button("🗑️ Borrar cuenta"):
            if cuenta_borrar != "(ninguna)":
                cuentas = [c for c in cuentas if c != cuenta_borrar]
                # reetiquetar brainrots que tenían esa cuenta
                for b in brainrots:
                    if b.get("cuenta") == cuenta_borrar:
                        b["cuenta"] = "(ninguna)"
                save_profile(uid, perfil_actual, brainrots, cuentas)
                st.warning(f"Cuenta '{cuenta_borrar}' borrada.")
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ============================
# Agregar Brainrot
# ============================
with st.container():
    st.markdown("<div class='card'><h3>➕ Agregar Brainrot</h3>", unsafe_allow_html=True)

    br_opt = ["(ninguno)"] + [f"{k} — {format_num(v)}" for k, v in BRAINROTS_BASE.items()]
    br_sel = st.selectbox("Selecciona un Brainrot", br_opt, key="br_sel")

    color_sel = st.selectbox("Color", list(COLORES_MULT.keys()), key="color_sel")
    muts_sel = st.multiselect("Mutaciones (máx 5)", list(MUTACIONES_MULT.keys()), max_selections=5, key="muts_sel")
    cuenta_sel = st.selectbox("Cuenta", ["(ninguna)"] + cuentas, key="cuenta_sel")

    if st.button("Agregar"):
        if br_sel == "(ninguno)":
            st.error("Selecciona un brainrot.")
        else:
            nombre = br_sel.split(" — ")[0]
            base = BRAINROTS_BASE[nombre]
            total = calc_total(base, color_sel, muts_sel)
            brainrots.append({
                "personaje": nombre,
                "color": color_sel,
                "mutaciones": muts_sel,
                "cuenta": cuenta_sel,
                "total": total
            })
            save_profile(uid, perfil_actual, brainrots, cuentas)
            st.success(f"{nombre} agregado. Total: {format_num(total)}")
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ============================
# Tabla (Inventario)
# ============================
with st.container():
    st.markdown("<div class='card'><h3>📊 Inventario de Brainrots</h3>", unsafe_allow_html=True)

    if brainrots:
        df = pd.DataFrame(brainrots)
        # orden
        orden = st.selectbox("Ordenar por", ["Total ↓", "Total ↑", "Cuenta", "Personaje"], key="orden_tabla")
        if orden == "Total ↓":
            df = df.sort_values(by="total", ascending=False)
        elif orden == "Total ↑":
            df = df.sort_values(by="total", ascending=True)
        elif orden == "Cuenta":
            df = df.sort_values(by="cuenta", na_position="last")
        elif orden == "Personaje":
            df = df.sort_values(by="personaje")

        # mostrar totales formateados
        df_show = df.copy()
        df_show["total"] = df_show["total"].apply(format_num)
        # mutaciones como badges: solo para visual (texto)
        df_show["mutaciones"] = df_show["mutaciones"].apply(lambda xs: ", ".join(xs) if xs else "-")

        st.dataframe(df_show.reset_index(drop=True), use_container_width=True)
    else:
        st.info("No hay brainrots en este perfil.")
























