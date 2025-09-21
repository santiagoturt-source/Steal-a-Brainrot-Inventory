import streamlit as st
import requests
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import uuid
import time
import os, json

TOKEN_FILE = "session_token.json"

RARITY_BADGE_STYLE = """
<style>
.rarity-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.15rem 0.8rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.85rem;
    letter-spacing: 0.02em;
    min-width: 8ch;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
}
.rarity-badge.rarity-común {
    background-color: #2ecc71;
    color: #0e331c;
}
.rarity-badge.rarity-raro {
    background-color: #3498db;
    color: #0e2332;
}
.rarity-badge.rarity-épico {
    background-color: #9b59b6;
    color: #f5f0f8;
}
.rarity-badge.rarity-legendario {
    background-color: #f1c40f;
    color: #3d3203;
}
.rarity-badge.rarity-mítico {
    background-color: #e74c3c;
    color: #fff4f2;
}
.rarity-badge.rarity-brainrot-god {
    background-image: linear-gradient(135deg, red, blue);
    color: #ffffff;
    text-shadow: 0 0 4px rgba(255, 255, 255, 0.35);
}
.rarity-badge.rarity-secreto {
    background-color: #000000;
    color: #f5f5f5;
}
.rarity-badge.rarity-og {
    background-image: linear-gradient(135deg, #000000, #f0b12b);
    color: #ffffff;
    text-shadow: 0 0 4px rgba(0, 0, 0, 0.45);
    box-shadow: inset 0 0 0 1px rgba(255, 217, 0, 0.35);
}
.brainrot-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.75rem;
}
.brainrot-table th {
    text-align: left;
    padding: 0.55rem 0.75rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.18);
    font-weight: 600;
    font-size: 0.9rem;
}
.brainrot-table td {
    padding: 0.5rem 0.75rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    font-size: 0.9rem;
}
.brainrot-table tr:last-child td {
    border-bottom: none;
}
</style>
"""


COLOR_BADGE_STYLE = """
<style>
.color-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.15rem 0.8rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.85rem;
    letter-spacing: 0.02em;
    min-width: 8ch;
    box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.08);
}
.color-badge.color-ninguno {
    background-color: rgba(255, 255, 255, 0.08);
    color: #f5f5f5;
}
.color-badge.color-dorado {
    background: linear-gradient(135deg, #f1c40f, #f7dc6f);
    color: #3d2f02;
}
.color-badge.color-diamante {
    background: linear-gradient(135deg, #74d4ff, #a5f1e9);
    color: #06333d;
}
.color-badge.color-luna-roja {
    background: linear-gradient(135deg, #8e1c24, #e74c3c);
    color: #fff5f4;
}
.color-badge.color-candy {
    background: linear-gradient(135deg, #ff7eb9, #ff65a3);
    color: #3e1025;
}
.color-badge.color-lava {
    background: linear-gradient(135deg, #f05053, #f26d3d);
    color: #3d0c02;
}
.color-badge.color-galaxy {
    background: radial-gradient(circle at top left, #6d5dfc, #320d6d);
    color: #f2e9ff;
}
.color-badge.color-rainbow {
    background-image: linear-gradient(135deg, #ff0000, #ffff00, #00ff00, #0000ff, #4b0082, #ee82ee);
    color: #ffffff;
    text-shadow: 0 0 4px rgba(0, 0, 0, 0.35);
}
</style>
"""


def ensure_rarity_styles():
    """Injecta los estilos de las insignias de rareza para la tabla HTML."""
    st.markdown(RARITY_BADGE_STYLE, unsafe_allow_html=True)


def ensure_color_styles():
    """Injecta los estilos de las insignias de color para la tabla HTML."""
    st.markdown(COLOR_BADGE_STYLE, unsafe_allow_html=True)


def rarity_badge_html(rarity: str) -> str:
    """Devuelve una insignia HTML para la rareza indicada."""
    if not rarity:
        return ""
    slug = rarity.lower().replace(" ", "-")
    return f"<span class='rarity-badge rarity-{slug}'>{rarity}</span>"


COLOR_BADGE_CLASS_MAP = {
    "-": "color-ninguno",
    "🟡 Dorado": "color-dorado",
    "💎 Diamante": "color-diamante",
    "🩸 Luna Roja": "color-luna-roja",
    "🍬 Candy": "color-candy",
    "🌋 Lava": "color-lava",
    "🌌 Galaxy": "color-galaxy",
    "🌈 Rainbow": "color-rainbow",
}


def color_badge_html(color: str) -> str:
    """Devuelve una insignia HTML para el color indicado."""
    if not color:
        color = "-"
    css_class = COLOR_BADGE_CLASS_MAP.get(color, "color-ninguno")
    return f"<span class='color-badge {css_class}'>{color}</span>"

def apply_theme():
    st.markdown(THEME_STYLE_TEMPLATE.format(**DEFAULT_THEME), unsafe_allow_html=True)



def _write_token_file(data):
    try:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except OSError as exc:
        st.warning(f"No se pudo guardar la sesión localmente: {exc}")


def save_session_token(uid, email, id_token=None, refresh_token=None):
    """Guarda la sesión en memoria y en disco para persistir entre recargas."""
    user_data = {
        "uid": uid,
        "email": email,
        "id_token": id_token,
        "refresh_token": refresh_token,
    }
    st.session_state["user"] = user_data
    _write_token_file(user_data)


def load_session_token():
    """Carga la sesión existente desde memoria o desde archivo."""
    if "user" in st.session_state:
        return True

    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            st.session_state["user"] = data
            return True
        except (OSError, json.JSONDecodeError) as exc:
            st.warning(f"No se pudo cargar la sesión previa: {exc}")
    return False


def clear_session_token():
    """Elimina la sesión activa tanto en memoria como en disco."""
    st.session_state.pop("user", None)
    if os.path.exists(TOKEN_FILE):
        try:
            os.remove(TOKEN_FILE)
        except OSError as exc:
            st.warning(f"No se pudo eliminar el archivo de sesión: {exc}")
# ============================
# CONFIGURACIÓN FIREBASE
# ============================

if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["FIREBASE_KEY"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()
WEB_API_KEY = st.secrets["firebase"]["api_key"]

# ============================
# FUNCIONES AUXILIARES
# ============================

from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

def format_num(num):
    num = Decimal(str(num))  # precisión exacta
    if num >= 1_000_000_000:
        # Billones → TRUNCADO
        val = (num / Decimal("1000000000")).quantize(Decimal("0.1"), rounding=ROUND_DOWN)
        return f"${val}B/s"
    elif num >= 1_000_000:
        # Millones → TRUNCADO
        val = (num / Decimal("1000000")).quantize(Decimal("0.1"), rounding=ROUND_DOWN)
        return f"${val}M/s"
    elif num >= 1_000:
        # Miles → REDONDEADO
        val = (num / Decimal("1000")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        return f"${val}K/s"
    else:
        return f"${num}/s"

def calcular_total(base, color_mult, mutaciones_mults):
    """Cálculo con la fórmula exacta de Excel"""
    total = base
    total += base * max(color_mult - 1, 0)
    for m in mutaciones_mults:
        total += base * max(m - 1, 0)
    return total


def confirm_deletion(state_key, message):
    """Muestra un mensaje de confirmación antes de borrar y devuelve el valor almacenado si se confirma."""
    st.warning(message)
    col_confirm, col_cancel = st.columns(2)
    confirmed_value = None
    with col_confirm:
        if st.button("✅ Confirmar", key=f"{state_key}_confirm"):
            confirmed_value = st.session_state.pop(state_key, None)
            return confirmed_value
    with col_cancel:
        if st.button("❌ Cancelar", key=f"{state_key}_cancel"):
            st.session_state.pop(state_key, None)
    return confirmed_value

# ============================
# FUNCIONES DE AUTENTICACIÓN
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
# FUNCIONES DE PERFILES
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
# INTERFAZ STREAMLIT
# ============================

st.title("📒 Inventario de Brainrots")

# ============================
# 🖥️ INTERFAZ LOGIN / SIGNUP
# ============================

if not load_session_token():
    tabs = st.tabs(["🔑 Iniciar sesión", "🆕 Registrarse"])

    with tabs[0]:
        email = st.text_input("Correo", key="login_email_input")
        password = st.text_input("Contraseña", type="password", key="login_pass_input")
        if st.button("Entrar", key="login_button"):
            user = login(email, password)
            if "error" in user:
                st.error(user["error"]["message"])
            else:
                save_session_token(
                    user.get("localId"),
                    user.get("email"),
                    user.get("idToken"),
                    user.get("refreshToken"),
                )
                st.success(f"✅ Sesión iniciada: {user['email']}")
                st.rerun()

    with tabs[1]:
        new_email = st.text_input("Correo nuevo", key="signup_email_input")
        new_pass = st.text_input("Contraseña nueva", type="password", key="signup_pass_input", placeholder="Mínimo 6 caracteres")
        if st.button("Crear cuenta", key="signup_button"):
            user = signup(new_email, new_pass)
            if "error" in user:
                st.error(user["error"]["message"])
            else:
                st.success(f"✅ Cuenta creada: {new_email}. Ahora puedes iniciar sesión.")

else:
    st.success(f"✅ Bienvenido {st.session_state['user']['email']}")


    # ============================
    # PESTAÑAS PRINCIPALES
    # ============================
    pestañas = st.tabs(["👤 Perfiles", "📦 Inventario", "⚙️ Opciones"])

    # ============================
    # 👤 GESTIÓN DE PERFILES
    # ============================
    with pestañas[0]:
        with st.container(border=True):
            st.subheader("👤 Gestión de Perfiles")
            
            perfil_actual = None
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
                    st.session_state["confirm_delete_profile"] = perfil_actual

                if "confirm_delete_profile" in st.session_state:
                    perfil_to_delete = st.session_state["confirm_delete_profile"]
                    confirmed = confirm_deletion(
                        "confirm_delete_profile",
                        f"⚠️ ¿Seguro que deseas borrar el perfil '{perfil_to_delete}'? Esta acción no se puede deshacer.",
                    )
                    if confirmed:
                        delete_profile(uid, perfil_to_delete)
                        st.success(f"Perfil '{perfil_to_delete}' borrado.")
                        st.rerun()

    # ============================
    # INVENTARIO DE BRAINROTS
    # ============================
    with pestañas[1]:
         if "user" in st.session_state and st.session_state["user"]:
            if perfil_actual and perfil_actual != "(ninguno)":
                brainrots, cuentas = load_data(uid, perfil_actual)

                st.subheader(f"📦 Inventario — Perfil: {perfil_actual}")

                    # ----------------------------
                    # Gestión de cuentas
                    # ----------------------------
                with st.container(border=True):
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
                            st.session_state["confirm_delete_account"] = cuenta_borrar

                        if "confirm_delete_account" in st.session_state:
                            cuenta_to_delete = st.session_state["confirm_delete_account"]
                            confirmed_account = confirm_deletion(
                                "confirm_delete_account",
                                f"⚠️ ¿Seguro que deseas borrar la cuenta '{cuenta_to_delete}'? Los brainrots asociados quedarán sin cuenta.",
                            )
                            if confirmed_account:
                                cuentas = [c for c in cuentas if c != confirmed_account]
                                for b in brainrots:
                                    if b["Cuenta"] == confirmed_account:
                                        b["Cuenta"] = "(ninguna)"
                                save_data(uid, perfil_actual, brainrots, cuentas)
                                st.success(f"Cuenta '{confirmed_account}' borrada.")
                                st.rerun()

                    # ----------------------------
                    # Agregar Brainrot
                    # ----------------------------
                with st.container(border=True):
                    st.markdown("### ➕ Agregar Brainrot")

                    
                    BRAINROT_BASES = {
                        "Noobini Pizzanini": 1,
    "Lirilì Larilà": 3,
    "Tim Cheese": 5,
    "Fluriflura": 7,
    "Talpa Di Fero": 9,
    "Svinina Bombardino": 10,
    "Raccooni Jandelini": 12,
    "Pipi Kiwi": 13,
    "Pipi Corni": 14,
    "Trippi Troppi": 15,
    "Gangster Footera": 30,
    "Bandito Bobritto": 35,
    "Boneca Ambalabu": 40,
    "Cacto Hipopotamo": 50,
    "Ta Ta Ta Ta Sahur": 55,
    "Tric-Trac-Baraboom": 65,
    "Pipi Avocado": 70,
    "Cappuccino Assassino": 75,
    "Bandito Axolito": 90,
    "Brr Brr Patapim": 100,
    "Avocadini Antilopini": 115,
    "Bambini Crostini": 120,
    "Trulimero Trulicina": 125,
    "Malame Amarele": 140,
    "Bananita Dolphinita": 150,
    "Perochello Lemonchello": 160,
    "Brri Brri Bicus Dicus Bombicus": 175,
    "Burbaloni Loliloli": 200,
    "Ti Ti Ti Sahur": 225,
    "Avocadini Guffo": 225,
    "Mangolini Parrocini": 235,
    "Salamino Penguino": 250,
    "Penguino Cocosino": 300,
    "Chimpanzini Bananini": 300,
    "Tirilikalika Tirilikalako": 450,
    "Ballerina Cappuccina": 500,
    "Chef Crabracadabra": 600,
    "Lionel Cactuseli": 650,
    "Glorbo Fruttodrillo": 750,
    "Quivioli Ameleonni": 900,
    "Blueberrinni Octopusini": 1000,
    "Caramello Filtrello": 1000,
    "Pipi Potato": 1100,
    "Strawberelli Flamingelli": 1100,
    "Cocosini Mama": 1200,
    "Pandaccini Bananini": 1200,
    "Pi Pi Watermelon": 1300,
    "Signore Carapace": 1300,
    "Sigma Boy": 1300,
    "Frigo Camelo": 1400,
    "Sigma Girl": 1800,
    "Orangutini Ananassini": 2000,
    "Rhino Toasterino": 2100,
    "Bombardiro Crocodilo": 2500,
    "Bruto Gialutto": 3000,
    "Spioniro Golubiro": 3500,
    "Bombombini Gusini": 5000,
    "Zibra Zubra Zibralini": 6000,
    "Tigrilini Watermelini": 6500,
    "Avocadorilla": 7000,
    "Cavallo Virtuoso": 7500,
    "Gorillo Subwoofero": 7700,
    "Gorillo Watermelondrillo": 8000,
    "Tob Tobi Tobi": 8500,
    "Lerulerulerule": 8700,
    "Ganganzelli Trulala": 9000,
    "Te Te Te Sahur": 9500,
    "Rhino Helicopterino": 11000,
    "Tracoducotulu Delapeladustuz": 12000,
    "Los Noobinis": 12500,
    "Carloo": 13500,
    "Carrotini Brainini": 15000,
    "Elefanto Frigo": 14000,
    "Cocofanto Elefanto": 17500,
    "Antonio": 18500,
    "Girafa Celestre": 20000,
    "Gattatino Nyanino": 35000,
    "Chihuanini Taconini": 45000,
    "Tralalero Tralala": 50000,
    "Matteo": 50000,
    "Los Crocodillitos": 55000,
    "Tigroligre Frutonni": 60000,
    "Espresso Signora": 70000,
    "Uncilto Samito": 75000,
    "Tipi Topi Taco": 75000,
    "Odin Din Din Dun": 75000,
    "Alessio": 85000,
    "Tukanno Bananno": 100000,
    "Orcalero Orcala": 100000,
    "Tralalita Tralala": 100000,
    "Extinct Ballerina": 125000,
    "Urubini Flamenguini": 150000,
    "Capi Taco": 155000,
    "Gattito Tacoto": 160000,
    "Trenostruzzo Turbo 3000": 150000,
    "Trippi Troppi Troppa Trippa": 175000,
    "Las Cappuchinas": 185000,
    "Ballerino Lololo": 200000,
    "Bulbito Bandito Traktorito": 205000,
    "Los Bombinitos": 220000,
    "Los Tungtungtungcitos": 210000,
    "Pakrahmatmamat": 215000,
    "Piccione Macchina": 225000,
    "Brr es Teh Patipum": 225000,
    "Bombardini Tortini": 225000,
    "Tractoro Dinosauro": 230000,
    "Los Orcalitos": 235000,
    "Crabbo Limonetta": 235000,
    "Orcalita Orcala": 240000,
    "Cacasito Satalito": 240000,
    "Tartaruga Cisterna": 250000,
    "Los Tipi Tacos": 260000,
    "Dug dug dug": 255000,
    "Piccionetta Machina": 270000,
    "Mastodontico Telepiedone": 275000,
    "Anpali Babel": 280000,
    "Belula Beluga": 290000,
    "Bisonte Giuppitere": 300000,
    "Los Matteos": 300000,
    "Karkerkar Kurkur": 300000,
    "La Vacca Saturno Saturnita": 300000,
    "Trenostruzzo Turbo 4000": 310000,
    "Torrtuginni Dragonfrutini": 350000,
    "Sammyini Spyderini": 325000,
    "Dul Dul Dul": 375000,
    "Blackhole Goat": 400000,
    "Chachechi": 400000,
    "Agarrini La Palini": 425000,
    "Fragola La La La": 450000,
    "Extinct Tralalero": 450000,
    "La Cucaracha": 475000,
    "Los Tralaleritos": 500000,
    "La Karkerkar Combinasion": 600000,
    "Los Spyderinis": 550000,
    "Guerriro Digitale": 550000,
    "Las Tralaleritas": 650000,
    "Job Job Job Sahur": 700000,
    "Las Vaquitas Saturnitas": 750000,
    "Graipuss Medussi": 1000000,
    "Nooo My Hotspot": 1500000,
    "To to to Sahur": 2200000,
    "La Sahur Combinasion": 2000000,
    "Pot Hotspot": 2500000,
    "Quesadilla Crocodila": 3000000,
    "La Extinct Grande": 3250000,
    "Chicleteira Bicicleteira": 3500000,
    "Los Nooo My Hotspotsitos": 5500000,
    "Los Chicleteiras": 7000000,
    "67": 7500000,
    "La Grande Combinasion": 10000000,
    "Mariachi Corazoni": 12500000,
    "Los Combinasionas": 15000000,
    "Nuclearo Dinossauro": 15000000,
    "Tacorita Bicicleta": 16500000,
    "Las Sis": 17500000,
    "Los Hotspotsitos": 20000000,
    "Celularcini Viciosini": 22500000,
    "Los Bros": 24000000,
    "Tralaledon": 27500000,
    "Esok Sekolah": 30000000,
    "Los Tacoritas": 32000000,
    "Ketupat Kepat": 35000000,
    "Tictac Sahur": 37500000,
    "La Supreme Combinasion": 40000000,
    "Ketchuru and Musturu": 42500000,
    "Garama and Madundung": 50000000,
    "Spaghetti Tualetti": 60000000,
    "Dragon Cannelloni": 100000000,
    "Strawberry Elephant": 300000000,
}
    

                    BRAINROT_RARITIES = {
                        "Noobini Pizzanini": "Común",
                        "Lirilì Larilà": "Común",
                        "Tim Cheese": "Común",
                        "Fluriflura": "Común",
                        "Talpa Di Fero": "Común",
                        "Svinina Bombardino": "Común",
                        "Raccooni Jandelini": "Común",
                        "Pipi Kiwi": "Común",
                        "Pipi Corni": "Común",
                        "Trippi Troppi": "Raro",
                        "Gangster Footera": "Raro",
                        "Bandito Bobritto": "Raro",
                        "Boneca Ambalabu": "Raro",
                        "Cacto Hipopotamo": "Raro",
                        "Ta Ta Ta Ta Sahur": "Raro",
                        "Tric-Trac-Baraboom": "Raro",
                        "Pipi Avocado": "Raro",
                        "Cappuccino Assassino": "Épico",
                        "Bandito Axolito": "Épico",
                        "Brr Brr Patapim": "Épico",
                        "Avocadini Antilopini": "Épico",
                        "Bambini Crostini": "Épico",
                        "Trulimero Trulicina": "Épico",
                        "Malame Amarele": "Épico",
                        "Bananita Dolphinita": "Épico",
                        "Perochello Lemonchello": "Épico",
                        "Brri Brri Bicus Dicus Bombicus": "Épico",
                        "Burbaloni Loliloli": "Legendario",
                        "Ti Ti Ti Sahur": "Épico",
                        "Avocadini Guffo": "Épico",
                        "Mangolini Parrocini": "Épico",
                        "Salamino Penguino": "Épico",
                        "Penguino Cocosino": "Épico",
                        "Chimpanzini Bananini": "Legendario",
                        "Tirilikalika Tirilikalako": "Legendario",
                        "Ballerina Cappuccina": "Legendario",
                        "Chef Crabracadabra": "Legendario",
                        "Lionel Cactuseli": "Legendario",
                        "Glorbo Fruttodrillo": "Legendario",
                        "Quivioli Ameleonni": "Legendario",
                        "Blueberrinni Octopusini": "Legendario",
                        "Caramello Filtrello": "Legendario",
                        "Pipi Potato": "Legendario",
                        "Strawberelli Flamingelli": "Legendario",
                        "Cocosini Mama": "Legendario",
                        "Pandaccini Bananini": "Legendario",
                        "Pi Pi Watermelon": "Legendario",
                        "Signore Carapace": "Legendario",
                        "Sigma Boy": "Legendario",
                        "Frigo Camelo": "Mítico",
                        "Sigma Girl": "Mítico",
                        "Orangutini Ananassini": "Mítico",
                        "Rhino Toasterino": "Mítico",
                        "Bombardiro Crocodilo": "Mítico",
                        "Bruto Gialutto": "Mítico",
                        "Spioniro Golubiro": "Mítico",
                        "Bombombini Gusini": "Mítico",
                        "Zibra Zubra Zibralini": "Mítico",
                        "Tigrilini Watermelini": "Mítico",
                        "Avocadorilla": "Mítico",
                        "Cavallo Virtuoso": "Mítico",
                        "Gorillo Subwoofero": "Mítico",
                        "Gorillo Watermelondrillo": "Mítico",
                        "Tob Tobi Tobi": "Mítico",
                        "Lerulerulerule": "Mítico",
                        "Ganganzelli Trulala": "Mítico",
                        "Te Te Te Sahur": "Mítico",
                        "Rhino Helicopterino": "Mítico",
                        "Tracoducotulu Delapeladustuz": "Mítico",
                        "Los Noobinis": "Mítico",
                        "Carloo": "Mítico",
                        "Carrotini Brainini": "Mítico",
                        "Elefanto Frigo": "Mítico",
                        "Cocofanto Elefanto": "Brainrot God",
                        "Antonio": "Brainrot God",
                        "Girafa Celestre": "Brainrot God",
                        "Gattatino Nyanino": "Brainrot God",
                        "Chihuanini Taconini": "Brainrot God",
                        "Tralalero Tralala": "Brainrot God",
                        "Matteo": "Brainrot God",
                        "Los Crocodillitos": "Brainrot God",
                        "Tigroligre Frutonni": "Brainrot God",
                        "Espresso Signora": "Brainrot God",
                        "Uncilto Samito": "Brainrot God",
                        "Tipi Topi Taco": "Brainrot God",
                        "Odin Din Din Dun": "Brainrot God",
                        "Alessio": "Brainrot God",
                        "Tukanno Bananno": "Brainrot God",
                        "Orcalero Orcala": "Brainrot God",
                        "Tralalita Tralala": "Brainrot God",
                        "Extinct Ballerina": "Brainrot God",
                        "Urubini Flamenguini": "Brainrot God",
                        "Capi Taco": "Brainrot God",
                        "Gattito Tacoto": "Brainrot God",
                        "Trenostruzzo Turbo 3000": "Brainrot God",
                        "Trippi Troppi Troppa Trippa": "Brainrot God",
                        "Las Cappuchinas": "Brainrot God",
                        "Ballerino Lololo": "Brainrot God",
                        "Bulbito Bandito Traktorito": "Brainrot God",
                        "Los Bombinitos": "Brainrot God",
                        "Los Tungtungtungcitos": "Brainrot God",
                        "Pakrahmatmamat": "Brainrot God",
                        "Piccione Macchina": "Brainrot God",
                        "Brr es Teh Patipum": "Brainrot God",
                        "Bombardini Tortini": "Brainrot God",
                        "Tractoro Dinosauro": "Brainrot God",
                        "Los Orcalitos": "Brainrot God",
                        "Crabbo Limonetta": "Brainrot God",
                        "Orcalita Orcala": "Brainrot God",
                        "Cacasito Satalito": "Brainrot God",
                        "Tartaruga Cisterna": "Brainrot God",
                        "Los Tipi Tacos": "Brainrot God",
                        "Dug dug dug": "Brainrot God",
                        "Piccionetta Machina": "Brainrot God",
                        "Mastodontico Telepiedone": "Brainrot God",
                        "Anpali Babel": "Brainrot God",
                        "Belula Beluga": "Brainrot God",
                        "Bisonte Giuppitere": "Secreto",
                        "Los Matteos": "Secreto",
                        "Karkerkar Kurkur": "Secreto",
                        "La Vacca Saturno Saturnita": "Secreto",
                        "Trenostruzzo Turbo 4000": "Secreto",
                        "Torrtuginni Dragonfrutini": "Secreto",
                        "Sammyini Spyderini": "Secreto",
                        "Dul Dul Dul": "Secreto",
                        "Blackhole Goat": "Secreto",
                        "Chachechi": "Secreto",
                        "Agarrini La Palini": "Secreto",
                        "Fragola La La La": "Secreto",
                        "Extinct Tralalero": "Secreto",
                        "La Cucaracha": "Secreto",
                        "Los Tralaleritos": "Secreto",
                        "La Karkerkar Combinasion": "Secreto",
                        "Los Spyderinis": "Secreto",
                        "Guerriro Digitale": "Secreto",
                        "Las Tralaleritas": "Secreto",
                        "Job Job Job Sahur": "Secreto",
                        "Las Vaquitas Saturnitas": "Secreto",
                        "Graipuss Medussi": "Secreto",
                        "Nooo My Hotspot": "Secreto",
                        "To to to Sahur": "Secreto",
                        "La Sahur Combinasion": "Secreto",
                        "Pot Hotspot": "Secreto",
                        "Quesadilla Crocodila": "Secreto",
                        "La Extinct Grande": "Secreto",
                        "Chicleteira Bicicleteira": "Secreto",
                        "Los Nooo My Hotspotsitos": "Secreto",
                        "Los Chicleteiras": "Secreto",
                        "67": "Secreto",
                        "La Grande Combinasion": "Secreto",
                        "Mariachi Corazoni": "Secreto",
                        "Los Combinasionas": "Secreto",
                        "Nuclearo Dinossauro": "Secreto",
                        "Tacorita Bicicleta": "Secreto",
                        "Las Sis": "Secreto",
                        "Los Hotspotsitos": "Secreto",
                        "Celularcini Viciosini": "Secreto",
                        "Los Bros": "Secreto",
                        "Tralaledon": "Secreto",
                        "Esok Sekolah": "Secreto",
                        "Los Tacoritas": "Secreto",
                        "Ketupat Kepat": "Secreto",
                        "Tictac Sahur": "Secreto",
                        "La Supreme Combinasion": "Secreto",
                        "Ketchuru and Musturu": "Secreto",
                        "Garama and Madundung": "Secreto",
                        "Spaghetti Tualetti": "Secreto",
                        "Dragon Cannelloni": "Secreto",
                        "Strawberry Elephant": "OG",
                    }

                    BRAINROTS = {
                        nombre: {
                            "income": base,
                            "quality": BRAINROT_RARITIES.get(nombre, "Común"),
                        }
                        for nombre, base in BRAINROT_BASES.items()
                    }

                    faltantes_calidad = False
                    for brainrot in brainrots:
                        if "Calidad" not in brainrot:
                            info = BRAINROTS.get(brainrot.get("Brainrot"))
                            brainrot["Calidad"] = info["quality"] if info else "Común"
                            faltantes_calidad = True

                    if faltantes_calidad:
                        save_data(uid, perfil_actual, brainrots, cuentas)
                        

                    COLORES = {
    "-": 0,
    "🟡 Dorado": 1.25,
    "💎 Diamante": 1.5,
    "🩸 Luna Roja": 2,
    "🍬 Candy": 4,
    "🌋 Lava": 6,
    "🌌 Galaxy": 7,
    "🌈 Rainbow": 10
}

                    MUTACIONES = {
    "🌧️ Lluvia": 1.5,
    "❄️ Nieve": 2,
    "🌮 Taco": 3,
    "🛸 Alien": 3,
    "✨ Lluvia de Estrellas": 3.5,
    "🦈 Aleta": 4,
    "🪐 Galáctico": 4,
    "🍬 Chicle": 4,
    "💣 Bombardiro": 4,
    "🔟 10B": 4,
    "☠️ Extinto": 4,
    "🎩 Sombrero (Matteo)": 4.5,
    "🕷️ Araña (Spyderini)": 4.5,
    "🥁 Ataque Tung Tung": 5,
    "🦀 Cangrejo": 5,
    "🌐 Glitch": 5,
    "🎶 Concierto": 5,
    "🌯🤠 Sombrero Mexico": 5,
    "🇧🇷 Brasil": 5,
    "🚲🍭 Chicletera": 6,
    "🔥 Fuego": 6,
    "🐱 Nyan Cat": 6,
    "🎆 4 de Julio": 6,
    "⚡🐲 Dragón Rayo": 6,
    "🍓 Fresa": 8,
}

                    personaje = st.selectbox(
                        "Selecciona un Brainrot",
                        ["(ninguno)"]
                        + [
                            f"{nombre} — {format_num(data['income'])}"
                            for nombre, data in BRAINROTS.items()
                        ]
                    )

                    color = st.selectbox("Color", list(COLORES.keys()))
                    mutaciones = st.multiselect("Mutaciones", list(MUTACIONES.keys()))
                    cuenta_sel = st.selectbox("Cuenta", ["(ninguna)"] + cuentas)

                    total_preview = None
                    nombre_seleccionado = None
                    datos_brainrot = None
                    if personaje != "(ninguno)":
                        nombre_seleccionado = personaje.split(" — ")[0]
                        datos_brainrot = BRAINROTS[nombre_seleccionado]
                        base = datos_brainrot["income"]
                        total_preview = calcular_total(
                            base,
                            COLORES[color],
                            [MUTACIONES[m] for m in mutaciones],
                        )
                        st.info(f"Total: {format_num(total_preview)}")
                    else:
                        st.info("Selecciona un Brainrot para ver la vista previa del total.")

                    if st.button("Agregar") and nombre_seleccionado:
                        brainrots.append({
                            "id": str(uuid.uuid4()),  # ID invisible
                            "Brainrot": nombre_seleccionado,
                            "Calidad": datos_brainrot["quality"],
                            "Color": color,
                            "Mutaciones": mutaciones,
                            "Cuenta": cuenta_sel,
                            "Total": total_preview
                        })
                        save_data(uid, perfil_actual, brainrots, cuentas)
                        st.success(
                            f"Brainrot '{nombre_seleccionado}' [{datos_brainrot['quality']}] agregado con total {format_num(total_preview)}."
                        )
                        st.rerun()

                    if brainrots:
                        df = pd.DataFrame(brainrots)
                        
                        if "orden" not in st.session_state:
                            st.session_state["orden"] = "Total ↓"
                            
                        orden = st.selectbox(
                            "Ordenar por",
                            ["Total ↓", "Total ↑", "Cuenta", "Brainrot", "Cuenta + Total ↓"],
                            key="orden"
                        )
                        
                        if "cuenta_filtro" not in st.session_state:
                            st.session_state["cuenta_filtro"] = "Todas"
                            
                        cuentas_filtro = ["Todas"] + sorted(df["Cuenta"].unique().tolist())
                        cuenta_filtro = st.selectbox(
                            "Filtrar por Cuenta",
                            cuentas_filtro,
                            key="cuenta_filtro"
                        )

                        if st.session_state["cuenta_filtro"] != "Todas":
                            df = df[df["Cuenta"] == st.session_state["cuenta_filtro"]]
                            
                        if st.session_state["orden"] == "Total ↓":
                            df = df.sort_values(by="Total", ascending=False)
                        elif st.session_state["orden"] == "Total ↑":
                            df = df.sort_values(by="Total", ascending=True)
                        elif st.session_state["orden"] == "Cuenta":
                            df = df.sort_values(by="Cuenta")
                        elif st.session_state["orden"] == "Brainrot":
                            df = df.sort_values(by="Brainrot")
                        elif st.session_state["orden"] == "Cuenta + Total ↓":
                            df = df.sort_values(by=["Cuenta", "Total"], ascending=[True, False])
                            
                        df["Total"] = df["Total"].apply(format_num)
                        df = df.drop(columns=["id"], errors="ignore")
                        if "Calidad" not in df.columns:
                            df["Calidad"] = df["Brainrot"].map(
                                lambda nombre: BRAINROTS.get(nombre, {}).get("quality", "Common")
                            )

                        df["Mutaciones"] = df["Mutaciones"].apply(
                            lambda mut: ", ".join(mut) if isinstance(mut, list) else mut
                        )

                        columnas = ["Brainrot", "Calidad", "Cuenta", "Total", "Color", "Mutaciones"]
                        df = df[[col for col in columnas if col in df.columns]]

                        if df.empty:
                            st.info("No hay brainrots para mostrar con los filtros seleccionados.")
                        else:
                            ensure_rarity_styles()
                            ensure_color_styles()

                            df_display = df.copy()
                            df_display["Calidad"] = df_display["Calidad"].apply(rarity_badge_html)
                            df_display["Mutaciones"] = df_display["Mutaciones"].apply(
                                lambda valor: valor if valor else "-"
                            )
                            df_display["Cuenta"] = df_display["Cuenta"].apply(
                                lambda valor: valor if valor else "-"
                            )
                            if "Color" in df_display:
                                df_display["Color"] = df_display["Color"].apply(color_badge_html)

                        st.markdown(
                                df_display.to_html(
                                    escape=False,
                                    index=False,
                                    classes="brainrot-table"
                                ),
                                unsafe_allow_html=True,
                            )



                        # ----------------------------
                        # Borrar / Mover Brainrots
                        # ----------------------------
                        with st.container(border=True):
                            st.markdown("### 🗑️ 🔄 Borrar / Mover Brainrots")

                            def brainrot_label(b):
                                parts = [
                                    f"{b['Brainrot']}",
                                    f"Cuenta: {b['Cuenta']}",
                                    f"Total: {format_num(b['Total'])}"
                                ]
                                if b.get("Calidad"):
                                    parts.append(f"Calidad: {b['Calidad']}")
                                if b.get("Color") and b["Color"] != "-":
                                    parts.append(f"Color: {b['Color']}")
                                if b.get("Mutaciones"):
                                    parts.append(f"Mutaciones: {', '.join(b['Mutaciones'])}")
                                return " | ".join(parts), b["id"]

                            opciones_brainrots = ["(ninguno)"] + [brainrot_label(b)[0] for b in brainrots]
                            ids_map = {brainrot_label(b)[0]: brainrot_label(b)[1] for b in brainrots}

                            # Borrar
                            to_delete = st.selectbox("Selecciona un Brainrot para borrar", opciones_brainrots)
                            if st.button("🗑️ Borrar Brainrot") and to_delete != "(ninguno)":
                                brainrot_id = ids_map[to_delete]
                                brainrots = [b for b in brainrots if b["id"] != brainrot_id]
                                save_data(uid, perfil_actual, brainrots, cuentas)
                                st.success("Brainrot borrado.")
                                st.rerun()

                            # Mover
                            mover = st.selectbox("Selecciona un Brainrot para mover", opciones_brainrots)
                            nueva_cuenta_sel = st.selectbox("Mover a cuenta", ["(ninguna)"] + cuentas)
                            if st.button("🔄 Mover Brainrot") and mover != "(ninguno)" and nueva_cuenta_sel != "(ninguna)":
                                brainrot_id = ids_map[mover]
                                for b in brainrots:
                                    if b["id"] == brainrot_id:
                                        b["Cuenta"] = nueva_cuenta_sel
                                save_data(uid, perfil_actual, brainrots, cuentas)
                                st.success(f"Brainrot movido a cuenta '{nueva_cuenta_sel}'.")
                                st.rerun()
            else:
                st.info("Debes seleccionar un perfil para ver tu inventario")
                                
    with pestañas[2]:
        with st.container(border=True):
            st.subheader("⚙️ Opciones")

            if "user" in st.session_state and st.session_state["user"]:
                if st.button("🚪 Cerrar sesión", key="logout_button"):
                    clear_session_token()
                    st.session_state.pop("user", None)
                    st.success("✅ Sesión cerrada correctamente.")
                    st.rerun()

st.divider()
st.markdown(
    """
    <div style='text-align: left;'>
        <a href="https://www.roblox.com/es/games/109983668079237/Steal-a-Brainrot" target="_blank" rel="noopener noreferrer">
            🎮 Jugar Steal a Brainrot en Roblox
        </a>
    </div>
    """,
    unsafe_allow_html=True,
)








































































































































































































