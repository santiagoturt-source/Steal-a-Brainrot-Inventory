import streamlit as st
import pandas as pd
from io import BytesIO
import os, re, json

# =========================
# "Base de datos" en código (ejemplo)
# =========================
PERSONAJES = [
    {"nombre": "Noobini Pizzanini",       "rareza": "Common",       "precio": 1},
    {"nombre": "Job Job Job Sahur",       "rareza": "Secret",       "precio": 700_000},
    {"nombre": "Blackhole Goat",          "rareza": "Secret",       "precio": 220_000},
    {"nombre": "Graipuss Medussi",        "rareza": "Secret",       "precio": 1_000_000},
    {"nombre": "Trenozostruzo Turbo 3000", "rareza": "Brainrot God", "precio": 150_000},
]

COLORES = [
    {"nombre": "—",       "mult": 0.0},
    {"nombre": "Gold",    "mult": 1.25},
    {"nombre": "Diamond",   "mult": 1.5},
    {"nombre": "Bloodrot",   "mult": 2},
    {"nombre": "Candy",   "mult": 4.0},
    {"nombre": "Rainbow", "mult": 10.0},
    {"nombre": "Galaxy",  "mult": 7.0},
]

MUTACIONES = [
    {"nombre": "4th of July Fireworks",  "mult": 6.0},
    {"nombre": "Lightning",              "mult": 6.0},
    {"nombre": "Bombardiro",             "mult": 4.0},
    {"nombre": "Taco",                   "mult": 3.0},
    {"nombre": "Matteo Hat",             "mult": 4.5},
    {"nombre": "UFO",                    "mult": 3.0},
    {"nombre": "Glitch",                 "mult": 5.0},
    {"nombre": "Nyan Cat",               "mult": 6.0},
]

if "PERSONAJES" not in globals(): PERSONAJES = []
if "COLORES" not in globals(): COLORES = []
if "MUTACIONES" not in globals(): MUTACIONES = []

COLUMNS = ["Cuenta","Personaje","Rareza","PrecioBase","Color","Mutaciones","Total"]
PERSONAJE_OPTS = [p.get("nombre") for p in PERSONAJES]
COLOR_OPTS     = [c.get("nombre") for c in COLORES]
MUT_OPTS       = [m.get("nombre") for m in MUTACIONES]

# =========================
# Utilidades
# =========================
def personaje_info(nombre: str):
    return next((p for p in PERSONAJES if p.get("nombre") == nombre), None)

def color_mult(nombre: str) -> float:
    c = next((c for c in COLORES if c.get("nombre") == nombre), None)
    return float(c.get("mult", 0)) if c else 0.0

def mut_mult(nombre: str) -> float:
    m = next((m for m in MUTACIONES if m.get("nombre") == nombre), None)
    return float(m.get("mult", 0)) if m else 0.0

def calc_total(precio_base: float, color_name: str, muts: list[str]) -> float:
    mults = [color_mult(color_name)] + [mut_mult(n) for n in (muts or []) if n]
    aportes = sum(precio_base * float(m) for m in mults if m)
    return float(aportes) if aportes > 0 else float(precio_base)

def fmt_number(n):
    try:
        n = float(n)
    except:
        return "-"
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1_000_000_000: return f"{sign}{n/1_000_000_000:.1f}B"
    if n >= 1_000_000:     return f"{sign}{n/1_000_000:.1f}M"
    if n >= 1_000:         return f"{sign}{n/1_000:.1f}K"
    return f"{sign}{n:,.0f}"

def export_excel(df):
    out = BytesIO()
    df.to_excel(out, index=False, engine="openpyxl")
    return out.getvalue()

def empty_df():
    df = pd.DataFrame(columns=COLUMNS)
    df["PrecioBase"] = df["PrecioBase"].astype("float64")
    df["Total"]      = df["Total"].astype("float64")
    return df

def ensure_schema(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in COLUMNS:
        if c not in df.columns: df[c] = None
    df["PrecioBase"] = pd.to_numeric(df["PrecioBase"], errors="coerce").fillna(0.0)
    df["Total"]      = pd.to_numeric(df["Total"], errors="coerce").fillna(0.0)
    return df[COLUMNS]

def recalc_row(row: pd.Series) -> pd.Series:
    info = personaje_info(str(row["Personaje"]))
    if info:
        row["Rareza"] = info.get("rareza", "")
        row["PrecioBase"] = float(info.get("precio", 0.0))
    else:
        row["Rareza"], row["PrecioBase"] = "", 0.0
    muts = [x.strip() for x in str(row.get("Mutaciones","")).split(",") if x.strip()]
    row["Total"] = calc_total(row["PrecioBase"], str(row.get("Color","—")), muts)
    return row

def recalc_df(df: pd.DataFrame) -> pd.DataFrame:
    return df.apply(recalc_row, axis=1)

# =========================
# Persistencia perfiles + cuentas
# =========================
DATA_DIR     = "perfiles"
PROFILE_KEY  = "profile"
DF_KEY       = "df"
ACCOUNTS_KEY = "accounts"

os.makedirs(DATA_DIR, exist_ok=True)

def _filename_from_display(name: str) -> str:
    name = name.strip()
    safe = re.sub(r"[^\w\s\-.]", "", name, flags=re.UNICODE)
    safe = re.sub(r"\s+", "_", safe)
    if not safe: safe = "Default"
    return f"{safe}.csv"

def _display_from_filename(fname: str) -> str:
    base = re.sub(r"\.csv$", "", fname, flags=re.IGNORECASE)
    return base.replace("_", " ")

def _accfile_from_display(name: str) -> str:
    base = re.sub(r"\.csv$", "", _filename_from_display(name), flags=re.IGNORECASE)
    return os.path.join(DATA_DIR, f"{base}.accounts.json")

def list_profiles():
    files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".csv")]
    displays = sorted((_display_from_filename(f) for f in files), key=lambda s: s.casefold())
    if not displays:
        save_profile("Default", empty_df())
        save_accounts("Default", default_accounts())
        return ["Default"]
    return displays

def _path_for(name_display: str) -> str:
    return os.path.join(DATA_DIR, _filename_from_display(name_display))

def load_profile(name_display: str) -> pd.DataFrame:
    path = _path_for(name_display)
    if os.path.exists(path):
        try:
            return ensure_schema(pd.read_csv(path))
        except Exception:
            return empty_df()
    df = empty_df()
    df.to_csv(path, index=False)
    return df

def save_profile(name_display: str, df: pd.DataFrame):
    ensure_schema(df).to_csv(_path_for(name_display), index=False)

def delete_profile(name_display: str):
    path = _path_for(name_display)
    if os.path.exists(path): os.remove(path)
    accp = _accfile_from_display(name_display)
    if os.path.exists(accp): os.remove(accp)

def default_accounts():
    return ["Cuenta 1", "Cuenta 2", "Cuenta 3", "Cuenta 4"]

def load_accounts(name_display: str) -> list[str]:
    accp = _accfile_from_display(name_display)
    if os.path.exists(accp):
        try:
            with open(accp, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list): return data
        except Exception:
            pass
    save_accounts(name_display, default_accounts())
    return default_accounts()

def save_accounts(name_display: str, accounts: list[str]):
    accp = _accfile_from_display(name_display)
    clean = [a.strip() for a in accounts if isinstance(a, str) and a.strip()]
    seen, dedup = set(), []
    for a in clean:
        cf = a.casefold()
        if cf in seen: continue
        seen.add(cf); dedup.append(a)
    if not dedup: dedup = default_accounts()
    with open(accp, "w", encoding="utf-8") as f:
        json.dump(dedup, f, ensure_ascii=False, indent=2)

# =========================
# Inicialización segura
# =========================
if PROFILE_KEY not in st.session_state:
    st.session_state[PROFILE_KEY] = "Default"
if DF_KEY not in st.session_state:
    st.session_state[DF_KEY] = load_profile(st.session_state[PROFILE_KEY])
if ACCOUNTS_KEY not in st.session_state:
    st.session_state[ACCOUNTS_KEY] = load_accounts(st.session_state[PROFILE_KEY])

# =========================
# APP
# =========================
st.set_page_config(page_title="Inventario con Perfiles", layout="wide")
st.title("📒 Inventario de Personajes")

# ---------- Sidebar ----------
st.sidebar.header("👤 Perfil")
profiles = list_profiles()
cur = st.session_state[PROFILE_KEY]
idx = 0 if cur not in profiles else profiles.index(cur)
sel = st.sidebar.selectbox("Selecciona un perfil", profiles, index=idx)
if sel != cur:
    st.session_state[PROFILE_KEY] = sel
    st.session_state[DF_KEY] = load_profile(sel)
    st.session_state[ACCOUNTS_KEY] = load_accounts(sel)
    st.rerun()

st.sidebar.text_input("Crear perfil nuevo", key="__new_profile_name__")
if st.sidebar.button("Crear"):
    new_name = st.session_state["__new_profile_name__"].strip()
    if new_name and new_name not in profiles:
        save_profile(new_name, empty_df())
        save_accounts(new_name, default_accounts())
        st.session_state[PROFILE_KEY] = new_name
        st.session_state[DF_KEY] = load_profile(new_name)
        st.session_state[ACCOUNTS_KEY] = load_accounts(new_name)
        st.rerun()

c1, c2 = st.sidebar.columns(2)
if c1.button("Guardar"):
    save_profile(st.session_state[PROFILE_KEY], st.session_state[DF_KEY])
    save_accounts(st.session_state[PROFILE_KEY], st.session_state[ACCOUNTS_KEY])
if c2.button("Borrar perfil"):
    if st.session_state[PROFILE_KEY].lower() != "default":
        delete_profile(st.session_state[PROFILE_KEY])
        st.session_state[PROFILE_KEY] = "Default"
        st.session_state[DF_KEY] = load_profile("Default")
        st.session_state[ACCOUNTS_KEY] = load_accounts("Default")
        st.rerun()

st.sidebar.divider()
st.sidebar.subheader("💼 Cuentas en este perfil")
for i, acc in enumerate(st.session_state[ACCOUNTS_KEY]):
    colA, colB = st.sidebar.columns([3,1])
    colA.write(acc)
    if colB.button("❌", key=f"del_acc_{i}"):
        accs = st.session_state[ACCOUNTS_KEY]
        removed = accs.pop(i)
        st.session_state[ACCOUNTS_KEY] = accs
        save_accounts(st.session_state[PROFILE_KEY], accs)
        df = st.session_state[DF_KEY]
        if not accs: accs = default_accounts()
        if "Cuenta" in df.columns:
            df.loc[df["Cuenta"] == removed, "Cuenta"] = accs[0]
        st.session_state[DF_KEY] = df
        save_profile(st.session_state[PROFILE_KEY], df)
        st.rerun()

st.sidebar.text_input("Nueva cuenta", key="__new_acc__")
if st.sidebar.button("Agregar cuenta"):
    new_acc = st.session_state["__new_acc__"].strip()
    if new_acc and new_acc not in st.session_state[ACCOUNTS_KEY]:
        st.session_state[ACCOUNTS_KEY].append(new_acc)
        save_accounts(st.session_state[PROFILE_KEY], st.session_state[ACCOUNTS_KEY])
        st.rerun()

# ---------- Alta ----------
st.divider()
with st.form("alta"):
    cuentas = st.session_state[ACCOUNTS_KEY]
    c1, c2, c3 = st.columns([1,2,1])
    cuenta = c1.selectbox("Cuenta", cuentas, index=0)
    personaje = c2.selectbox("Personaje", PERSONAJE_OPTS or ["(define PERSONAJES)"])
    color = c3.selectbox("Color", COLOR_OPTS or ["(define COLORES)"])
    mut_sel = st.multiselect("Mutaciones", MUT_OPTS)

    if st.form_submit_button("Agregar"):
        base = personaje_info(personaje)
        precio = float(base.get("precio", 0.0)) if base else 0.0
        nueva = {
            "Cuenta": cuenta,
            "Personaje": personaje,
            "Rareza": base.get("rareza", "") if base else "",
            "PrecioBase": precio,
            "Color": color,
            "Mutaciones": ", ".join(mut_sel or []),
            "Total": calc_total(precio, color, mut_sel or []),
        }
        st.session_state[DF_KEY] = ensure_schema(
            pd.concat([st.session_state[DF_KEY], pd.DataFrame([nueva])], ignore_index=True)
        )
        save_profile(st.session_state[PROFILE_KEY], st.session_state[DF_KEY])
        st.success(f"✅ Agregado: {personaje} ({fmt_number(nueva['Total'])})")

# ---------- Vista con botones de borrar ----------
# ---------- Vista con botones de borrar ----------
st.divider()
st.subheader(f"📊 Vista — Perfil: {st.session_state[PROFILE_KEY]}")

df_view = ensure_schema(st.session_state[DF_KEY]).copy()
if not df_view.empty:
    df_view["PrecioBaseFmt"] = df_view["PrecioBase"].apply(fmt_number)
    df_view["TotalFmt"] = df_view["Total"].apply(fmt_number)

    # Selector de orden
    orden = st.selectbox(
        "Ordenar por:",
        ["Total (mayor a menor)", "Total (menor a mayor)", "Cuenta (A-Z)", "Cuenta (Z-A)"],
        index=0
    )

    if orden == "Total (mayor a menor)":
        df_view = df_view.sort_values(by="Total", ascending=False)
    elif orden == "Total (menor a mayor)":
        df_view = df_view.sort_values(by="Total", ascending=True)
    elif orden == "Cuenta (A-Z)":
        df_view = df_view.sort_values(by="Cuenta", ascending=True)
    elif orden == "Cuenta (Z-A)":
        df_view = df_view.sort_values(by="Cuenta", ascending=False)

    # Render expanders
    for i, row in df_view.iterrows():
        partes = [row["Cuenta"], row["Personaje"]]

        if row["Color"] and str(row["Color"]).strip() != "—":
            partes.append(str(row["Color"]))

        if row["Mutaciones"] and str(row["Mutaciones"]).strip():
            partes.append(str(row["Mutaciones"]))

        partes.append(fmt_number(row["Total"]))
        header = " — ".join(partes)

        with st.expander(header):
            st.write(f"**Cuenta:** {row['Cuenta']}")
            st.write(f"**Rareza:** {row['Rareza']}")
            st.write(f"**Color:** {row['Color'] or '—'}")
            st.write(f"**Mutaciones:** {row['Mutaciones'] or '—'}")
            st.write(f"**Precio base:** {fmt_number(row['PrecioBase'])}")
            st.write(f"**Total:** {fmt_number(row['Total'])}")

            if st.button(f"🗑️ Borrar este personaje", key=f"del_{i}"):
                st.session_state["__delete_idx__"] = i

    # Confirmación de borrado
    if "__delete_idx__" in st.session_state:
        idx = st.session_state["__delete_idx__"]
        if 0 <= idx < len(df_view):
            row = df_view.iloc[idx]
            st.warning(
                f"¿Seguro que quieres borrar **{row['Personaje']}** "
                f"con color **{row['Color']}** y mutaciones **{row['Mutaciones'] or '—'}**?"
            )
            colC1, colC2 = st.columns(2)
            if colC1.button("✅ Sí, borrar", key="confirm_delete"):
                df_new = df_view.drop(idx).reset_index(drop=True)
                st.session_state[DF_KEY] = df_new
                save_profile(st.session_state[PROFILE_KEY], df_new)
                del st.session_state["__delete_idx__"]
                st.success("Registro borrado.")
                st.rerun()
            if colC2.button("❌ Cancelar", key="cancel_delete"):
                del st.session_state["__delete_idx__"]
                st.info("Cancelado.")

    # Exportación
    st.download_button(
        "⬇️ Exportar CSV",
        data=st.session_state[DF_KEY].to_csv(index=False).encode("utf-8"),
        file_name=f"{re.sub(r'\\s+','_',st.session_state[PROFILE_KEY])}.csv",
        mime="text/csv",
    )
    st.download_button(
        "⬇️ Exportar Excel",
        data=export_excel(st.session_state[DF_KEY]),
        file_name=f"{re.sub(r'\\s+','_',st.session_state[PROFILE_KEY])}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
else:

    st.info("Inventario vacío. Usa el formulario para agregar registros.")

