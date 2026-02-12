import streamlit as st
import pandas as pd

import db


st.set_page_config(page_title="Inventaire Pharmacie", layout="wide")


@st.cache_resource
def _conn():
    conn = db.get_conn()
    db.init_db(conn)
    return conn


conn = _conn()

st.title("Inventaire pharmacie (MVP)")

st.markdown("---")
st.subheader("Ajouter un produit")

with st.form("add_product", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Nom du produit")
    with col2:
        quantity = st.text_input("Quantité (ex: boîte, flacon, ampoule…)")
    submitted = st.form_submit_button("Ajouter")

    if submitted:
        if not name.strip() or not quantity.strip():
            st.error("Le nom et la quantité sont obligatoires.")
        else:
            try:
                db.add_product(conn, name=name, quantity=quantity)
                st.success("Produit ajouté.")
                st.rerun()
            except Exception as e:
                st.error(f"Impossible d’ajouter le produit : {e}")

st.markdown("---")
st.subheader("Enregistrer une sortie")

products = db.list_products(conn)
if not products:
    st.info("Ajoute d’abord des produits ci-dessus.")
else:
    product_by_label = {
        f"{p['name']} ({p['quantity']})": int(p["id"]) for p in products
    }

    with st.form("add_out", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            prod_label = st.selectbox("Produit", list(product_by_label.keys()))
        with col2:
            qty = st.number_input("Quantité à sortir", min_value=0.0, value=1.0, step=1.0)
        submitted = st.form_submit_button("Enregistrer la sortie")

        if submitted:
            if qty <= 0:
                st.error("La quantité doit être > 0.")
            else:
                pid = product_by_label[prod_label]
                db.add_movement(conn, product_id=pid, mvt_type="OUT", quantity=qty)
                # Mettre à jour la quantité du produit avec le reste (quantité - total sorties)
                cur = conn.execute(
                    "SELECT CAST(quantity AS REAL) - COALESCE(SUM(CASE WHEN type = 'OUT' THEN quantity ELSE 0 END), 0) AS reste FROM products LEFT JOIN movements ON products.id = movements.product_id WHERE products.id = ?",
                    (pid,)
                )
                row = cur.fetchone()
                reste = row["reste"] if row else 0
                conn.execute(
                    "UPDATE products SET quantity = ? WHERE id = ?",
                    (str(reste), pid)
                )
                conn.commit()
                st.success("Sortie enregistrée et quantité mise à jour.")
                st.rerun()

st.markdown("---")
st.subheader("Inventaire (reste disponible)")

rows = db.get_inventory(conn)
if not rows:
    st.info("Aucun produit.")
else:
    df = pd.DataFrame([dict(r) for r in rows])
    df = df.rename(
        columns={
            "name": "Produit",
            "quantity": "Quantité",
            "total_out": "Total sorties",
            "remaining": "Reste",
        }
    )

    st.dataframe(
        df[["Produit", "Quantité", "Total sorties", "Reste"]],
        use_container_width=True,
        hide_index=True,
    )
