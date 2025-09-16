import streamlit as st
import pandas as pd
import requests
import firebase_admin
from firebase_admin import credentials, firestore
import json, re
from io import BytesIO

# ================================
# CONFIGURACIÓN FIREBASE
# ================================
WEB_API_KEY = "FIREBASE_KEY"   # <-- reemplaza con tu apiKey de Firebase Web

if not firebase_admin._apps:
    cred = credentials.Certificate(dict(st.secrets["FIREBASE_KEY"]))
    firebase_admin.initialize_app(cred)
    db = firestore.client()


# ================================
# AUTENTICACIÓN
# ================================
def signup_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()

def login_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={WEB_API_KEY}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    return requests.post(url, json=payload).json()

# ================================
# FIRESTORE - PERFILES
# ================================
def list_profiles(uid):
    col = db.collection("perfiles").document(uid).collection("data").stream()
    return [doc.id for doc in col]

def load_profile(uid, name):
    ref = db.collection("perfiles").document(uid).collection("data").document(name).get()
    if ref.exists:
        data = ref.to_dict().get("rows", [])
        return pd.DataFrame(data)
    return empty_df()

def save_profile(uid, name, df):
    ref = db.collection("perfiles").document(uid).collection("data").document(name)
    ref.set({"rows": df.to_dict(orient="records")})

def delete_profile(uid, name):
    db.collection("perfiles").document(uid).collection("data").document(name).delete()

# ================================
# UTILIDADES INVENTARIO
# ================================
COLUMNS = ["Cuenta","Personaje","Rareza","PrecioBase","Color","Mutaciones","Total"]

def empty_df():
    df = pd.DataFrame(columns=COLUMNS)
    df["PrecioBase"] = df["PrecioBase"].astype("float64")
    df["Total"]      = df["Total"].astype("float64")
    return df

def fmt_number(n):
    try: n = float(n)
    except: return "-"
    if n >= 1_000_000_000: return f"{n/1_000_000_000:.1f}B"
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M"
    if n >= 1_000: return f"{n/1_000:.1f}K"
    return f"{n:,.0f}"

def export_excel(df):
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return out.getvalue()

# ================================
# SESIÓN USUARIO
# ================================
if "user" not in st.session_state:
    st.session_state["user"] = None

st.title("📒 Inventario con Usuarios + Perfiles")

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

# ---------- APLICACIÓN PRINCIPAL ----------
else:
    user = st.session_state["user"]
    st.sidebar.success(f"Conectado como {user['email']}")

    # Selección de perfil
    perfiles = list_profiles(user["uid"])
    perfil_actual = st.sidebar.selectbox("Selecciona perfil", perfiles or ["(ninguno)"])

    # Crear nuevo perfil
    nuevo = st.sidebar.text_input("Nombre de perfil nuevo")
    if st.sidebar.button("Crear perfil"):
        if nuevo:
            save_profile(user["uid"], nuevo, empty_df())
            st.success(f"Perfil {nuevo} creado")
            st.rerun()
        else:
            st.warning("Escribe un nombre para el perfil.")

    # Borrar perfil
    if perfil_actual and perfil_actual != "(ninguno)":
        if st.sidebar.button("Borrar perfil actual"):
            delete_profile(user["uid"], perfil_actual)
            st.warning(f"Perfil {perfil_actual} borrado")
            st.rerun()

    # Cerrar sesión
    if st.sidebar.button("Cerrar sesión"):
        st.session_state["user"] = None
        st.rerun()

    # =======================
    # INVENTARIO
    # =======================
    if perfil_actual and perfil_actual != "(ninguno)":
        st.subheader(f"Perfil: {perfil_actual}")
        df = load_profile(user["uid"], perfil_actual)

        # Ordenar inventario
        orden = st.selectbox("Ordenar por", ["Total ↓", "Total ↑", "Cuenta"])
        if not df.empty:
            if orden == "Total ↓":
                df = df.sort_values("Total", ascending=False)
            elif orden == "Total ↑":
                df = df.sort_values("Total", ascending=True)
            elif orden == "Cuenta":
                df = df.sort_values("Cuenta")

        # Mostrar tabla
        st.dataframe(df)

        # Agregar personaje
        with st.form("agregar"):
            cuenta = st.text_input("Cuenta")
            personaje = st.text_input("Personaje")
            rareza = st.text_input("Rareza")
            precio = st.number_input("Precio base", min_value=0.0)
            color = st.text_input("Color")
            mutaciones = st.text_input("Mutaciones (separadas por coma)")

            if st.form_submit_button("Agregar"):
                total = precio
                # Multiplicadores simples de ejemplo
                if color:
                    total += precio * 2
                if mutaciones:
                    for _ in mutaciones.split(","):
                        total += precio * 3

                nuevo = {
                    "Cuenta": cuenta,
                    "Personaje": personaje,
                    "Rareza": rareza,
                    "PrecioBase": precio,
                    "Color": color,
                    "Mutaciones": mutaciones,
                    "Total": total,
                }
                df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
                save_profile(user["uid"], perfil_actual, df)
                st.success("Agregado")
                st.rerun()

        # Borrar un registro
        if not df.empty:
            idx = st.number_input("Fila a borrar (número)", min_value=0, max_value=len(df)-1, step=1)
            if st.button("Borrar fila seleccionada"):
                fila = df.iloc[idx]
                confirm = st.checkbox(f"¿Seguro que quieres borrar {fila['Personaje']} de {fila['Cuenta']}?")
                if confirm:
                    df = df.drop(idx).reset_index(drop=True)
                    save_profile(user["uid"], perfil_actual, df)
                    st.warning("Registro borrado")
                    st.rerun()

        # Exportar
        st.download_button("⬇️ Exportar CSV", df.to_csv(index=False).encode("utf-8"),
                           file_name=f"{perfil_actual}.csv", mime="text/csv")
        st.download_button("⬇️ Exportar Excel", export_excel(df),
                           file_name=f"{perfil_actual}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")





