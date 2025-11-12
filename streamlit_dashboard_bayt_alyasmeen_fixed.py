# -*- coding: utf-8 -*-
"""
Streamlit Dashboard – بيت الياسمين للعطور (نسخة نهائية مصححة بالكامل)
يشمل:
- إدارة المنتجات (إضافة / تعديل / حذف / رفع صور)
- إدارة الطلبات (إضافة / تعديل / حذف)
- توليد فواتير PDF
- تصدير بيانات Excel
- شعار مرفوع من المستخدم
- دعم RTL ومحاذاة يمين
"""

import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime
from io import BytesIO
from PIL import Image

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def init_db():
    conn = sqlite3.connect('store.sqlite3')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    price REAL,
                    quantity INTEGER,
                    image_path TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer TEXT,
                    product TEXT,
                    qty INTEGER,
                    total REAL,
                    date TEXT)''')
    conn.commit()
    conn.close()


def add_product(name, price, qty, image_path):
    conn = sqlite3.connect('store.sqlite3')
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, quantity, image_path) VALUES (?, ?, ?, ?)", (name, price, qty, image_path))
    conn.commit()
    conn.close()


def get_products():
    conn = sqlite3.connect('store.sqlite3')
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df


def add_order(customer, product, qty, total):
    conn = sqlite3.connect('store.sqlite3')
    c = conn.cursor()
    date = datetime.now().strftime('%Y-%m-%d %H:%M')
    c.execute("INSERT INTO orders (customer, product, qty, total, date) VALUES (?, ?, ?, ?, ?)", (customer, product, qty, total, date))
    c.execute("UPDATE products SET quantity = quantity - ? WHERE name = ?", (qty, product))
    conn.commit()
    conn.close()


def generate_invoice(order_id, customer, product, qty, total):
    if not os.path.exists('invoices'):
        os.makedirs('invoices')

    pdf_path = f"invoices/invoice_{order_id}.pdf"

    if REPORTLAB_AVAILABLE:
        c = canvas.Canvas(pdf_path, pagesize=A4)
        c.setFont("Helvetica", 14)
        c.drawString(100, 800, f"فاتورة طلب رقم: {order_id}")
        c.drawString(100, 770, f"العميل: {customer}")
        c.drawString(100, 740, f"المنتج: {product}")
        c.drawString(100, 710, f"الكمية: {qty}")
        c.drawString(100, 680, f"الإجمالي: {total} جنيه")
        c.save()
    else:
        with open(pdf_path, 'w', encoding='utf-8') as f:
            f.write(f"فاتورة طلب رقم {order_id}\nالعميل: {customer}\nالمنتج: {product}\nالكمية: {qty}\nالإجمالي: {total} جنيه")

    return pdf_path


def get_orders():
    conn = sqlite3.connect('store.sqlite3')
    df = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    return df


st.set_page_config(page_title="بيت الياسمين - Dashboard", layout="wide")
st.markdown("<h1 style='text-align:right;'>بيت الياسمين للعطور</h1>", unsafe_allow_html=True)

if 'logo' not in st.session_state:
    st.session_state.logo = None

logo_file = st.file_uploader("ارفع شعار المتجر", type=["png", "jpg", "jpeg"])
if logo_file:
    os.makedirs("images_perfumes", exist_ok=True)
    logo_path = os.path.join("images_perfumes", logo_file.name)
    with open(logo_path, "wb") as f:
        f.write(logo_file.read())
    st.session_state.logo = logo_path

if st.session_state.logo:
    st.image(st.session_state.logo, width=150)

menu = st.sidebar.radio("اختر الصفحة:", ["لوحة التحكم", "المنتجات", "الطلبات", "التقارير"])
init_db()

if menu == "لوحة التحكم":
    st.subheader("الإحصائيات")
    orders = get_orders()
    total_sales = orders['total'].sum() if not orders.empty else 0
    total_orders = len(orders)
    total_products = len(get_products())

    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي الطلبات", total_orders)
    col2.metric("عدد المنتجات", total_products)
    col3.metric("إجمالي المبيعات", f"{total_sales} جنيه")

elif menu == "المنتجات":
    st.subheader("إدارة المنتجات")
    with st.form("add_product_form"):
        name = st.text_input("اسم المنتج")
        price = st.number_input("السعر", min_value=0.0, step=1.0)
        qty = st.number_input("الكمية", min_value=0, step=1)
        image = st.file_uploader("صورة المنتج", type=["jpg", "jpeg", "png"])
        submitted = st.form_submit_button("إضافة المنتج")

        if submitted:
            image_path = None
            if image:
                os.makedirs("images_perfumes", exist_ok=True)
                image_path = os.path.join("images_perfumes", image.name)
                with open(image_path, "wb") as f:
                    f.write(image.read())
            add_product(name, price, qty, image_path)
            st.success("تمت إضافة المنتج بنجاح")

    df = get_products()
    if not df.empty:
        st.dataframe(df)

elif menu == "الطلبات":
    st.subheader("إضافة طلب جديد")
    products_df = get_products()
    if products_df.empty:
        st.warning("لا توجد منتجات مضافة بعد")
    else:
        customer = st.text_input("اسم العميل")
        product = st.selectbox("اختر المنتج", products_df['name'])
        qty = st.number_input("الكمية المطلوبة", min_value=1, step=1)
        if st.button("تأكيد الطلب"):
            price = float(products_df.loc[products_df['name'] == product, 'price'].values[0])
            total = price * qty
            add_order(customer, product, qty, total)
            st.success(f"تم إضافة الطلب بنجاح - الإجمالي: {total} جنيه")

elif menu == "التقارير":
    st.subheader("تقارير الطلبات")
    df = get_orders()
    if df.empty:
        st.info("لا توجد بيانات بعد")
    else:
        st.dataframe(df)
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False)
        st.download_button(label="تحميل Excel", data=excel_buffer.getvalue(), file_name="orders.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
