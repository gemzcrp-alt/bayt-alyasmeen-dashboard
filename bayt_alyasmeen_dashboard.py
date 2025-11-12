# -*- coding: utf-8 -*-
"""
bayt_alyasmeen_dashboard.py
المرحلة 2/3 — لوحة تحكم (Dashboard) لتطبيق بيت الياسمين
ميزات:
- Dashboard (إحصائيات يومية / شهرية / كلي)
- صفحة الطلبات (فتح سابقاً موجود) + صفحة التقارير
- حفظ الفواتير في مجلد invoices/
- RTL: محاذاة إلى اليمين حيث أمكن (Tkinter محدود في RTL لكن قمنا بضبط المحاذاة)
- يعتمد على نفس قاعدة البيانات store.sqlite3
"""

import os
import shutil
import sqlite3
from datetime import datetime, date
from tkinter import *
from tkinter import ttk, filedialog, messagebox
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from PIL import Image, ImageTk

# ---------- إعداد المسارات ----------
APP_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(APP_DIR, "store.sqlite3")
IMAGES_DIR = os.path.join(APP_DIR, "images_perfumes")
INVOICES_DIR = os.path.join(APP_DIR, "invoices")
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(INVOICES_DIR, exist_ok=True)

# ---------- اتصال بقاعدة البيانات ----------
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ---------- دوال مساعدة ----------
def copy_image(src_path):
    try:
        base = os.path.basename(src_path)
        dst = os.path.join(IMAGES_DIR, f"{int(datetime.now().timestamp())}_{base}")
        shutil.copy(src_path, dst)
        return dst
    except Exception as e:
        print("copy_image error:", e)
        return ""

def create_invoice_pdf(sale_row, logo_path=None):
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fname = f"فاتورة_{sale_row['customer_name']}_{stamp}.pdf"
    path = os.path.join(INVOICES_DIR, fname)
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawRightString(w-40, h - 60, "بيت الياسمين للعطور")
    c.setFont("Helvetica", 10)
    c.drawRightString(w-40, h - 80, f"التاريخ: {sale_row['sold_at']}")
    # Customer
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(w-40, h - 110, "بيانات المستلم:")
    c.setFont("Helvetica", 10)
    c.drawRightString(w-40, h - 125, f"الاسم: {sale_row['customer_name']}")
    c.drawRightString(w-40, h - 140, f"الهاتف: {sale_row['customer_phone']}")
    c.drawRightString(w-40, h - 155, f"العنوان: {sale_row['customer_address']}")
    # Product details (left-aligned box)
    top = h - 200
    c.setFont("Helvetica-Bold", 12)
    c.drawString(40, top, "تفاصيل المنتج:")
    c.setFont("Helvetica", 10)
    c.drawString(40, top - 20, f"المنتج: {sale_row['product_name']}")
    c.drawString(40, top - 35, f"الكمية: {sale_row['quantity']}")
    c.drawString(40, top - 50, f"سعر الوحدة (بيع): {sale_row['unit_sell']:.2f}")
    c.drawString(40, top - 65, f"إجمالي البيع: {sale_row['total']:.2f}")
    c.drawString(40, top - 80, f"تكلفة الإجمالي: {sale_row['cost_total']:.2f}")
    c.drawString(40, top - 95, f"صافي الربح: {sale_row['net_profit']:.2f}")
    # Product image (on right)
    try:
        if sale_row.get("image_path") and os.path.exists(sale_row["image_path"]):
            c.drawImage(sale_row["image_path"], w-220, top-10, width=180, height=180, preserveAspectRatio=True)
    except Exception:
        pass
    # Footer
    c.setFont("Helvetica", 10)
    c.drawString(40, 60, "شكراً لتعاملكم مع بيت الياسمين للعطور")
    c.save()
    return path

def export_sales_to_excel(output_path):
    wb = Workbook()
    ws = wb.active
    ws.title = "المبيعات"
    headers = ["التاريخ","المنتج","الكمية","سعر الوحدة","اجمالي البيع","تكلفة الاجمالي","صافي الربح","اسم العميل","هاتف","العنوان"]
    ws.append(headers)
    cur.execute("SELECT sold_at, product_name, quantity, unit_sell, total, cost_total, net_profit, customer_name, customer_phone, customer_address FROM sales ORDER BY id DESC")
    for row in cur.fetchall():
        ws.append(row)
    wb.save(output_path)
    return output_path

# ---------- الواجهة (Tkinter) ----------
class DashboardApp:
    def __init__(self, root):
        self.root = root
        root.title("بيت الياسمين للعطور — لوحة التحكم")
        root.geometry("1150x760")
        root.configure(bg="white")

        # top bar
        top = Frame(root, bg="white")
        top.pack(fill=X, padx=12, pady=8)
        self.logo_img = None
        self.logo_path = None
        self.title_lbl = Label(top, text="🏷 بيت الياسمين للعطور", font=("Arial", 18, "bold"), bg="white", anchor="e")
        self.title_lbl.pack(side=RIGHT)
        Button(top, text="رفع شعار", command=self.upload_logo).pack(side=RIGHT, padx=8)
        Button(top, text="لوحة التحكم", command=self.show_dashboard).pack(side=LEFT, padx=6)
        Button(top, text="الطلبات", command=self.show_orders).pack(side=LEFT, padx=6)
        Button(top, text="التقارير", command=self.show_reports).pack(side=LEFT, padx=6)

        # main container
        self.container = Frame(root, bg="white")
        self.container.pack(fill=BOTH, expand=True, padx=12, pady=8)

        # initialize pages
        self.dashboard_page = None
        self.orders_page = None
        self.reports_page = None

        self.show_dashboard()

    def upload_logo(self):
        p = filedialog.askopenfilename(filetypes=[("Image files","*.png;*.jpg;*.jpeg;*.bmp")])
        if not p: return
        dst = copy_image(p)
        self.logo_path = dst
        try:
            im = Image.open(dst); im.thumbnail((80,80)); self.logo_img = ImageTk.PhotoImage(im)
            self.title_lbl.config(image=self.logo_img, text="")
        except:
            pass

    # ---------- لوحة التحكم (Dashboard) ----------
    def show_dashboard(self):
        self.clear_container()
        frame = Frame(self.container, bg="white")
        frame.pack(fill=BOTH, expand=True)

        # compute stats
        today = date.today().isoformat()
        month_start = date.today().replace(day=1).isoformat()
        cur.execute("SELECT COUNT(*), IFNULL(SUM(total),0), IFNULL(SUM(net_profit),0) FROM sales")
        total_ops, total_revenue, total_profit = cur.fetchone()
        cur.execute("SELECT COUNT(*), IFNULL(SUM(total),0), IFNULL(SUM(net_profit),0) FROM sales WHERE date(sold_at)=?", (today,))
        today_ops, today_revenue, today_profit = cur.fetchone()
        cur.execute("SELECT COUNT(*), IFNULL(SUM(total),0), IFNULL(SUM(net_profit),0) FROM sales WHERE date(sold_at)>=?", (month_start,))
        month_ops, month_revenue, month_profit = cur.fetchone()

        # header
        Label(frame, text="لوحة التحكم", font=("Arial", 16, "bold"), bg="white").pack(anchor="e")

        stats_frame = Frame(frame, bg="white")
        stats_frame.pack(fill=X, pady=8)

        def stat_card(parent, title, value, subtitle=""):
            card = Frame(parent, bg="#FAFAFA", bd=1, relief=RIDGE, padx=12, pady=8)
            Label(card, text=title, font=("Arial", 11, "bold"), bg="#FAFAFA", anchor="e").pack(anchor="e")
            Label(card, text=value, font=("Arial", 14, "bold"), bg="#FAFAFA", fg="green", anchor="e").pack(anchor="e")
            if subtitle:
                Label(card, text=subtitle, font=("Arial", 9), bg="#FAFAFA", anchor="e").pack(anchor="e")
            return card

        # create 3 columns for Today / Month / Total
        left = Frame(stats_frame, bg="white")
        left.pack(side=RIGHT, expand=True, fill=BOTH, padx=6)
        mid = Frame(stats_frame, bg="white")
        mid.pack(side=RIGHT, expand=True, fill=BOTH, padx=6)
        right = Frame(stats_frame, bg="white")
        right.pack(side=RIGHT, expand=True, fill=BOTH, padx=6)

        # Today
        stat_card(left, "اليوم", "", "").pack(fill=BOTH, padx=6, pady=4)
        stat_card(left, "عدد الطلبات اليوم", today_ops, "").pack(fill=BOTH, padx=6, pady=4)
        stat_card(left, "إجمالي الإيراد اليوم", f"{today_revenue:.2f} جنيه", "").pack(fill=BOTH, padx=6, pady=4)
        stat_card(left, "صافي الربح اليوم", f"{today_profit:.2f} جنيه", "").pack(fill=BOTH, padx=6, pady=4)

        # Month
        stat_card(mid, "هذا الشهر", "", "").pack(fill=BOTH, padx=6, pady=4)
        stat_card(mid, "عدد الطلبات هذا الشهر", month_ops, "").pack(fill=BOTH, padx=6, pady=4)
        stat_card(mid, "إجمالي الإيراد الشهر", f"{month_revenue:.2f} جنيه", "").pack(fill=BOTH, padx=6, pady=4)
        stat_card(mid, "صافي الربح الشهر", f"{month_profit:.2f} جنيه", "").pack(fill=BOTH, padx=6, pady=4)

        # Total
        stat_card(right, "الإجمالي الكلي", "", "").pack(fill=BOTH, padx=6, pady=4)
        stat_card(right, "عدد الطلبات الكلي", total_ops, "").pack(fill=BOTH, padx=6, pady=4)
        stat_card(right, "إجمالي الإيراد الكلي", f"{total_revenue:.2f} جنيه", "").pack(fill=BOTH, padx=6, pady=4)
        stat_card(right, "صافي الربح الكلي", f"{total_profit:.2f} جنيه", "").pack(fill=BOTH, padx=6, pady=4)

        # quick actions
        actions = Frame(frame, bg="white")
        actions.pack(fill=X, pady=8)
        Button(actions, text="إضافة منتج جديد", command=self.open_add_product).pack(side=RIGHT, padx=6)
        Button(actions, text="تصدير مبيعات إلى Excel", command=self.export_sales).pack(side=RIGHT, padx=6)

        self.dashboard_page = frame

    def export_sales(self):
        p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files","*.xlsx")])
        if not p: return
        try:
            export_sales_to_excel(p)
            messagebox.showinfo("تم", f"تم التصدير إلى {p}")
        except Exception as e:
            messagebox.showerror("خطأ", str(e))

    # ---------- Orders page (عرض الطلبات) ----------
    def show_orders(self):
        self.clear_container()
        frame = Frame(self.container, bg="white")
        frame.pack(fill=BOTH, expand=True)
        Label(frame, text="قائمة الطلبات", font=("Arial", 16, "bold"), bg="white").pack(anchor="e", padx=6, pady=(2,6))

        # table of orders
        cols = ("التاريخ","المنتج","الكمية","سعر الوحدة","إجمالي","صافي الربح","العميل","هاتف")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=18)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor=CENTER, width=120)
        tree.pack(fill=BOTH, expand=True, padx=12, pady=8)
        scrollbar = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)

        def load_orders():
            for i in tree.get_children():
                tree.delete(i)
            cur.execute("SELECT id,sold_at,product_name,quantity,unit_sell,total,net_profit,customer_name,customer_phone FROM sales ORDER BY id DESC")
            for r in cur.fetchall():
                tree.insert("", "end", iid=r[0], values=(r[1], r[2], r[3], f"{r[4]:.2f}", f"{r[5]:.2f}", f"{r[6]:.2f}", r[7], r[8]))
        load_orders()

        # right-click menu
        menu = Menu(self.root, tearoff=0)
        def edit_order():
            sel = tree.selection()
            if not sel: return
            oid = int(sel[0])
            self.open_edit_sale(oid, refresh_fn=load_orders)
        def delete_order():
            sel = tree.selection()
            if not sel: return
            oid = int(sel[0])
            if messagebox.askyesno("تأكيد","هل تريد حذف هذه العملية؟"):
                cur.execute("SELECT product_id, quantity FROM sales WHERE id=?", (oid,))
                row = cur.fetchone()
                if row:
                    pid, q = row
                    cur.execute("UPDATE products SET qty = qty + ? WHERE id=?", (q, pid))
                cur.execute("DELETE FROM sales WHERE id=?", (oid,))
                conn.commit()
                load_orders()
                messagebox.showinfo("تم","تم حذف العملية")
        menu.add_command(label="تعديل", command=edit_order)
        menu.add_command(label="حذف", command=delete_order)
        def on_right(event):
            iid = tree.identify_row(event.y)
            if iid:
                tree.selection_set(iid)
                menu.post(event.x_root, event.y_root)
        tree.bind("<Button-3>", on_right)

        self.orders_page = frame

    # ---------- Reports page ----------
    def show_reports(self):
        self.clear_container()
        frame = Frame(self.container, bg="white")
        frame.pack(fill=BOTH, expand=True)
        Label(frame, text="تقارير متقدمة", font=("Arial", 16, "bold"), bg="white").pack(anchor="e", padx=6, pady=(2,6))

        # quick stats (reuse dashboard numbers)
        cur.execute("SELECT COUNT(*), IFNULL(SUM(total),0), IFNULL(SUM(net_profit),0) FROM sales")
        total_ops, total_revenue, total_profit = cur.fetchone()
        stats = Frame(frame, bg="white")
        stats.pack(fill=X, padx=12, pady=6)
        Label(stats, text=f"عدد الطلبات: {total_ops}", bg="white").pack(side=RIGHT, padx=8)
        Label(stats, text=f"إجمالي الإيراد: {total_revenue:.2f} جنيه", bg="white").pack(side=RIGHT, padx=8)
        Label(stats, text=f"صافي الربح: {total_profit:.2f} جنيه", bg="white").pack(side=RIGHT, padx=8)

        # filter & search
        f = Frame(frame, bg="white")
        f.pack(fill=X, padx=12, pady=6)
        Label(f, text="بحث (منتج/عميل):", bg="white").pack(side=RIGHT, padx=6)
        search_var = StringVar()
        Entry(f, textvariable=search_var, width=30).pack(side=RIGHT, padx=6)
        Label(f, text="من تاريخ (YYYY-MM-DD):", bg="white").pack(side=RIGHT, padx=6)
        from_var = StringVar(); Entry(f, textvariable=from_var, width=12).pack(side=RIGHT, padx=6)
        Label(f, text="إلى تاريخ (YYYY-MM-DD):", bg="white").pack(side=RIGHT, padx=6)
        to_var = StringVar(); Entry(f, textvariable=to_var, width=12).pack(side=RIGHT, padx=6)

        # result table
        cols = ("التاريخ","المنتج","الكمية","سعر الوحدة","اجمالي","تكلفة","صافي الربح","عميل","هاتف")
        tree = ttk.Treeview(frame, columns=cols, show="headings", height=14)
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor=CENTER, width=110)
        tree.pack(fill=BOTH, expand=True, padx=12, pady=8)
        scrollbar = ttk.Scrollbar(frame, orient=VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=RIGHT, fill=Y)

        def load_table():
            for i in tree.get_children():
                tree.delete(i)
            q = search_var.get().strip().lower()
            f_from = from_var.get().strip()
            f_to = to_var.get().strip()
            sql = "SELECT sold_at,product_name,quantity,unit_sell,total,cost_total,net_profit,customer_name,customer_phone FROM sales WHERE 1=1"
            params = []
            if q:
                sql += " AND (LOWER(product_name) LIKE ? OR LOWER(customer_name) LIKE ?)"
                params += [f"%{q}%", f"%{q}%"]
            if f_from:
                sql += " AND date(sold_at) >= date(?)"
                params.append(f_from)
            if f_to:
                sql += " AND date(sold_at) <= date(?)"
                params.append(f_to)
            sql += " ORDER BY id DESC"
            cur.execute(sql, params)
            for row in cur.fetchall():
                tree.insert("", "end", values=row)
        load_table()

        # export button
        def export_action():
            p = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel files","*.xlsx")])
            if not p: return
            try:
                export_sales_to_excel(p)
                messagebox.showinfo("تم", f"تم التصدير إلى {p}")
            except Exception as e:
                messagebox.showerror("خطأ", str(e))
        Button(frame, text="تصدير إلى Excel", command=export_action).pack(pady=6)

        self.reports_page = frame

    # ---------- تعديل عملية بيع (تفتح من orders) ----------
    def open_edit_sale(self, sale_id, refresh_fn=None):
        cur.execute("SELECT id,sold_at,product_id,product_name,quantity,unit_sell,unit_cost,total,cost_total,net_profit,customer_name,customer_phone,customer_address FROM sales WHERE id=?", (sale_id,))
        r = cur.fetchone()
        if not r:
            messagebox.showerror("خطأ","العملية غير موجودة")
            return
        win = Toplevel(self.root)
        win.title("تعديل عملية البيع")
        win.geometry("480x520")
        win.configure(bg="white")
        Label(win, text="تعديل بيانات البيع", bg="white", font=("Arial",12,"bold")).pack(pady=8)
        Label(win, text="اسم العميل:", bg="white").pack(anchor="e", padx=12)
        name_e = Entry(win); name_e.insert(0, r[10]); name_e.pack(fill=X, padx=12)
        Label(win, text="هاتف العميل:", bg="white").pack(anchor="e", padx=12)
        phone_e = Entry(win); phone_e.insert(0, r[11]); phone_e.pack(fill=X, padx=12)
        Label(win, text="العنوان:", bg="white").pack(anchor="e", padx=12)
        addr_e = Entry(win); addr_e.insert(0, r[12]); addr_e.pack(fill=X, padx=12)
        Label(win, text="الكمية:", bg="white").pack(anchor="e", padx=12)
        qty_e = Entry(win); qty_e.insert(0, str(r[4])); qty_e.pack(fill=X, padx=12)
        Label(win, text="سعر البيع للوحدة:", bg="white").pack(anchor="e", padx=12)
        unit_sell_e = Entry(win); unit_sell_e.insert(0, str(r[5])); unit_sell_e.pack(fill=X, padx=12)

        def save_edit():
            try:
                new_name = name_e.get().strip()
                new_phone = phone_e.get().strip()
                new_addr = addr_e.get().strip()
                new_qty = int(qty_e.get())
                new_unit_sell = float(unit_sell_e.get())
            except:
                messagebox.showwarning("قيمة خاطئة","تأكد من المدخلات")
                return
            cur.execute("SELECT unit_cost, product_id, quantity FROM sales WHERE id=?", (sale_id,))
            row = cur.fetchone()
            if not row:
                messagebox.showerror("خطأ","المعلومة مفقودة")
                return
            unit_cost, prod_id, old_qty = float(row[0]), int(row[1]), int(row[2])
            # adjust product qty
            diff = new_qty - old_qty
            cur.execute("UPDATE products SET qty = qty - ? WHERE id=?", (diff, prod_id))
            new_total = new_unit_sell * new_qty
            new_cost_total = unit_cost * new_qty
            new_profit = new_total - new_cost_total
            cur.execute("""UPDATE sales SET customer_name=?, customer_phone=?, customer_address=?, quantity=?, unit_sell=?, total=?, cost_total=?, net_profit=? WHERE id=?""",
                        (new_name, new_phone, new_addr, new_qty, new_unit_sell, new_total, new_cost_total, new_profit, sale_id))
            conn.commit()
            messagebox.showinfo("تم","تم حفظ التعديلات")
            win.destroy()
            if refresh_fn:
                refresh_fn()

        Button(win, text="حفظ التعديل", command=save_edit).pack(pady=12)

    # ---------- فتح إضافة منتج (مستخدم في dashboard) ----------
    def open_add_product(self):
        # reuse product add window similar to previous implementation
        win = Toplevel(self.root)
        win.title("إضافة منتج جديد")
        win.geometry("420x520")
        win.configure(bg="white")
        Label(win, text="اسم المنتج:", bg="white").pack(anchor="e", padx=12, pady=(8,0))
        name_e = Entry(win); name_e.pack(fill=X, padx=12)
        Label(win, text="الوصف:", bg="white").pack(anchor="e", padx=12, pady=(8,0))
        desc_e = Entry(win); desc_e.pack(fill=X, padx=12)
        Label(win, text="الكمية:", bg="white").pack(anchor="e", padx=12, pady=(8,0))
        qty_e = Entry(win); qty_e.pack(fill=X, padx=12)
        Label(win, text="سعر الشراء:", bg="white").pack(anchor="e", padx=12, pady=(8,0))
        cost_e = Entry(win); cost_e.pack(fill=X, padx=12)
        Label(win, text="سعر البيع:", bg="white").pack(anchor="e", padx=12, pady=(8,0))
        sell_e = Entry(win); sell_e.pack(fill=X, padx=12)
        img_path_var = StringVar(value="")
        img_lbl = Label(win, text="لم يتم اختيار صورة", bg="white")
        img_lbl.pack(padx=12, pady=8)
        def choose_img():
            p = filedialog.askopenfilename(filetypes=[("Image files","*.png;*.jpg;*.jpeg;*.bmp")])
            if p:
                dst = copy_image(p)
                img_path_var.set(dst)
                img_lbl.config(text=os.path.basename(dst))
        Button(win, text="اختيار صورة", command=choose_img).pack(padx=12)
        def save():
            name = name_e.get().strip()
            desc = desc_e.get().strip()
            try:
                qty = int(qty_e.get() or 0)
                cost = float(cost_e.get() or 0)
                sell = float(sell_e.get() or 0)
            except:
                messagebox.showwarning("قيمة خاطئة","تأكد من المدخلات الرقمية")
                return
            img = img_path_var.get()
            cur.execute("INSERT INTO products (name,description,qty,cost_price,sell_price,image_path) VALUES (?,?,?,?,?,?)",
                        (name, desc, qty, cost, sell, img))
            conn.commit()
            messagebox.showinfo("تم","تمت إضافة المنتج")
            win.destroy()
            self.show_dashboard()
        Button(win, text="حفظ المنتج", command=save).pack(pady=10)

    # ---------- utilities ----------
    def clear_container(self):
        for w in self.container.winfo_children():
            w.destroy()

# ---------- تشغيل ----------
if __name__ == "__main__":
    root = Tk()
    app = DashboardApp(root)
    root.mainloop()
