from itertools import product
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
    session,
    make_response,
    send_file,
)
import pandas as pd
import os
import re
import requests
from datetime import datetime
from urllib.parse import urlparse
import concurrent.futures
import random
import pdfkit
import io
import json
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from scraper import get_lowest_price, get_amazon_price, get_flipkart_price

# -----------------------------
# PATHS & GLOBAL CONFIG
# -----------------------------
DB_PATH = os.path.join("laptop_dataset.db")  # main laptops DB path

app = Flask(__name__)
app.secret_key = "super_admin_secret_qualitron_123"

# -----------------------------
# DEFAULT BRAND IMAGES
# -----------------------------
default_brand_images = {
    "HP": "https://m.media-amazon.com/images/I/71gE7D4x3-L._SL1500_.jpg",
    "Dell": "https://m.media-amazon.com/images/I/61gGtqfZFlL._SL1500_.jpg",
    "Acer": "https://m.media-amazon.com/images/I/71CZcP2FRoL._SL1500_.jpg",
    "Asus": "https://m.media-amazon.com/images/I/71S8U9VzLTL._SL1500_.jpg",
    "Lenovo": "https://m.media-amazon.com/images/I/71eXNIDUGjL._SL1500_.jpg",
    "MSI": "https://m.media-amazon.com/images/I/71tH6wz5jUL._SL1500_.jpg",
    "Apple": "https://m.media-amazon.com/images/I/61L1ItFgFHL._SL1500_.jpg",
    "Microsoft": "https://m.media-amazon.com/images/I/71y4JtEdWYL._SL1500_.jpg",
}


# -----------------------------
# ORDERS DB INITIALIZATION
# -----------------------------
conn = sqlite3.connect("orders.db")
cur = conn.cursor()
cur.execute(
    """
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    product_info TEXT NOT NULL,
    invoice_id TEXT NOT NULL UNIQUE,
    invoice_pdf_path TEXT NOT NULL,
    order_date TEXT DEFAULT CURRENT_TIMESTAMP
);
"""
)
conn.commit()
conn.close()
print("orders.db created successfully")

# -----------------------------
# RULE-BASED PRICE PREDICTION
# -----------------------------
def predict_price_rule_based(brand, ram, storage, cpu):
    price = 0

    brand_prices = {
        "HP": 20000,
        "Dell": 22000,
        "Lenovo": 18000,
        "Asus": 21000,
        "Acer": 17000,
        "MSI": 25000,
        "Apple": 60000,
        "Microsoft": 50000
    }
    price += brand_prices.get(brand, 15000)

    ram_prices = {4: 0, 8: 3000, 16: 6000, 32: 10000}
    price += ram_prices.get(ram, 0)

    storage_prices = {256: 4000, 512: 7000, 1024: 12000}
    price += storage_prices.get(storage, 3000)

    cpu_prices = {
        "i3": 0,
        "i5": 8000,
        "i7": 15000,
        "Ryzen 3": 0,
        "Ryzen 5": 7000,
        "Ryzen 7": 14000
    }
    price += cpu_prices.get(cpu, 5000)

    return price

def init_contact_db():
    conn = sqlite3.connect("contact.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS contact_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

# Initialize DB at app startup
init_contact_db()


# -----------------------------
# HELPER: URL VALIDATION (OPTIONAL)
# -----------------------------
def validate_image_url(url):
    """Validate if a URL points to a valid image"""
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False

        response = requests.head(url, timeout=5)
        content_type = response.headers.get("content-type", "")
        return "image" in content_type.lower()
    except:
        return False


def validate_urls_parallel(urls):
    """Validate multiple URLs in parallel"""
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        results = executor.map(validate_image_url, urls)
        return list(results)


# -----------------------------
# MAIN DATASET LOADER
# -----------------------------
def load_dataset():
    """
    Always loads the latest laptop data from SQLite,
    cleans it, adds IDs and image_url, and renames columns
    to match templates.
    """
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM laptops", conn)
    conn.close()

    # Round numeric columns if present
    for col in ["Price_Rs", "Weight", "Inches", "CPU_freq"]:
        if col in df.columns:
            df[col] = df[col].round(2)

    # Add ID column (sequential)
    df["ID"] = range(1, len(df) + 1)

    # Image URL handling
    if "image_url" in df.columns:
        df.loc[df["image_url"] == "", "image_url"] = df.loc[
            df["image_url"] == "", "Company"
        ].map(default_brand_images)
    else:
        # No Image_URL column → use brand defaults
        df["image_url"] = df["Company"].map(default_brand_images)

    # Rename columns for consistency with templates
    df = df.rename(
        columns={
            "Price_Rs": "Price",
            "Company": "Brand",
            "Ram": "RAM_Size",
            "PrimaryStorage": "Storage_Capacity",
            "Inches": "Screen_Size",
            "CPU_freq": "Processor_Speed",
            "CPU_model": "Processor_Model",
            "CPU_company": "Processor_Brand",
        }
    )

    return df


# -----------------------------
# FLASK APP & ROUTES
# -----------------------------
@app.route("/monitors")
def monitors():
    """Monitors page - shows external monitor recommendations"""
    return render_template("monitors.html")


@app.route("/")
def home():
    categories = [
        {
            "name": "Laptops",
            "desc": "Gaming | Office | Students",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTjeQkkw7u63MYY8Z3HSh_pHA-XQafHvMDB7Q&s",
            "href": "/products?category=laptops",
        },
        {
            "name": "Antivirus Software",
            "desc": "Kaspersky | Norton | McAfee",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTPCAefBFCP6jr0eh5wJS-8kFJfm_lKDQ2Xjg&s",
            "href": "/antivirus",
        },
        {
            "name": "External Monitors",
            "desc": "4K UHD | Gaming | Portable",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQj3ZGbfqSapoW_U2JamvoboHM12G_Jqn0u4w&s",
            "href": "/monitors",
        },
        {
            "name": "Accessories",
            "desc": "Chargers | Cables | Covers",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRxbSLQWufLFI5o8SlDrCPivQudiX82dl3gAqdrpFtZlVI-PnLPPkdOegMfKGreEjojGss&usqp=CAU",
            "href": "/accessories",
        },
    ]
    return render_template("index.html", categories=categories)


@app.route("/gaming_laptop")
def gaming_laptop():
    return render_template("gaming_laptop.html")


# -----------------------------
# PRODUCTS LIST PAGE
# -----------------------------
# Helper function for parallel processing
def process_laptop_price(l):
    b = l.get("Brand")
    r = int(l.get("RAM_Size", 8))
    s = int(l.get("Storage_Capacity", 256))
    cpu = l.get("Processor_Model") or l.get("Processor_Brand")

    predicted = predict_price_rule_based(b, r, s, cpu)
    
    # Fetch real-time prices from Amazon and Flipkart
    amazon_url = l.get("amazon_link")
    flipkart_url = l.get("flipkart_link")
    
    price_data = get_lowest_price(amazon_url, flipkart_url, predicted)
    
    # Use the lowest price for display
    l["Price"] = price_data["lowest_price"]
    l["price_source"] = price_data["price_source"]
    l["amazon_price"] = price_data["amazon_price"]
    l["flipkart_price"] = price_data["flipkart_price"]
    return l

@app.route("/products")
def products():
    df = load_dataset()

    brand = request.args.get("brand", "")
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    ram = request.args.get("ram", type=int)
    storage = request.args.get("storage", type=int)

    filtered_df = df.copy()

    if brand and brand != "all":
        filtered_df = filtered_df[filtered_df["Brand"] == brand]
    if min_price:
        filtered_df = filtered_df[filtered_df["Price"] >= min_price]
    if max_price:
        filtered_df = filtered_df[filtered_df["Price"] <= max_price]
    if ram:
        filtered_df = filtered_df[filtered_df["RAM_Size"] == ram]
    if storage:
        filtered_df = filtered_df[filtered_df["Storage_Capacity"] == storage]

    # STEP 1 — Convert to dict first
    laptops_raw = filtered_df.to_dict("records")

    # STEP 2 — Apply predicted price (FAST)
    # We no longer fetch real-time prices here to avoid blocking
    for l in laptops_raw:
        b = l.get("Brand")
        r = int(l.get("RAM_Size", 8))
        s = int(l.get("Storage_Capacity", 256))
        cpu = l.get("Processor_Model") or l.get("Processor_Brand")
        
        # Set base price as the display price initially
        predicted = predict_price_rule_based(b, r, s, cpu)
        l["Price"] = predicted
        l["predicted_price"] = predicted
        l["price_source"] = "predicted"
        
    laptops = laptops_raw


    # STEP 3 — Sort AFTER prediction
    sort_by = request.args.get("sort", "price_asc")
    if sort_by == "price_asc":
        laptops = sorted(laptops, key=lambda x: x["Price"])
    elif sort_by == "price_desc":
        laptops = sorted(laptops, key=lambda x: x["Price"], reverse=True)

    # STEP 4 — Render page
    brands = df["Brand"].unique().tolist()
    ram_options = df["RAM_Size"].unique().tolist()
    storage_options = df["Storage_Capacity"].unique().tolist()

    return render_template(
        "products.html",
        laptops=laptops,
        brands=brands,
        ram_options=ram_options,
        storage_options=storage_options,
        current_brand=brand,
        current_ram=ram,
        current_storage=storage,
        sort_by=sort_by,
    )



# -----------------------------
# PRODUCT DETAIL PAGE
# -----------------------------
@app.route("/product/<int:product_id>")
def product_detail(product_id):
    df = load_dataset()
    laptop_df = df[df["ID"] == product_id]

    if laptop_df.empty:
        return "Product not found", 404

    laptop = laptop_df.iloc[0].to_dict()   # <-- FIRST we create laptop dict

    # Calculate predicted price
    brand = laptop.get("Brand")
    ram = int(laptop.get("RAM_Size", 8))
    storage = int(laptop.get("Storage_Capacity", 256))
    cpu = laptop.get("Processor_Model") or laptop.get("Processor_Brand")

    predicted_price = predict_price_rule_based(brand, ram, storage, cpu)
    
    # Fetch real-time prices from Amazon and Flipkart
    # amazon_url = laptop.get("amazon_link")
    # flipkart_url = laptop.get("flipkart_link")
    
    # price_data = get_lowest_price(amazon_url, flipkart_url, predicted_price)
    
    # Update laptop dict with all price information
    laptop["Price"] = predicted_price # Start with predicted
    laptop["predicted_price"] = predicted_price
    laptop["amazon_price"] = None # Load via API
    laptop["flipkart_price"] = None # Load via API
    laptop["price_source"] = "predicted"

    return render_template("product_detail.html", laptop=laptop)


# -----------------------------
# PDF / INVOICE DOWNLOAD
# -----------------------------
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib import colors
from reportlab.lib.units import mm


@app.route("/invoice/download")
def download_invoice():
    order_items = session.get("last_order", [])
    if not order_items:
        return redirect("/cart")

    buffer = io.BytesIO()
    pdf = rl_canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40

    # Title
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(40, y, "INVOICE")
    y -= 30

    # Invoice ID & Date
    pdf.setFont("Helvetica", 11)
    pdf.drawString(
        40, y, f"Invoice ID: QLS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    y -= 15
    pdf.drawString(40, y, f"Date: {datetime.now().strftime('%d %B %Y')}")
    y -= 30

    # Shop info
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(40, y, "Qualitron Laptop Store")
    y -= 15
    pdf.setFont("Helvetica", 11)
    pdf.drawString(40, y, "Bengaluru, Karnataka, India")
    y -= 15
    pdf.drawString(40, y, "Phone: 9980307550")
    y -= 15
    pdf.drawString(40, y, "Email: support@qualitron.com")
    y -= 30

    # Table header
    pdf.setLineWidth(0.8)
    pdf.line(40, y, width - 40, y)
    y -= 18

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(40, y, "Product")
    pdf.drawString(220, y, "Qty")
    pdf.drawString(270, y, "Base Price")
    pdf.drawString(350, y, "GST %")
    pdf.drawString(410, y, "GST Amt")
    pdf.drawString(480, y, "Total")
    y -= 15

    pdf.line(40, y, width - 40, y)
    y -= 15

    # Items
    pdf.setFont("Helvetica", 11)
    grand_total = 0

    for item in order_items:
        price = item["price"] * item["quantity"]
        gst_percent = 18
        gst_amount = round(price * gst_percent / 100)
        total_amount = price + gst_amount
        grand_total += total_amount

        pdf.drawString(40, y, item["name"])
        pdf.drawString(220, y, str(item["quantity"]))
        pdf.drawString(270, y, f"₹{price:,.2f}")
        pdf.drawString(350, y, f"{gst_percent}%")
        pdf.drawString(410, y, f"₹{gst_amount:,.2f}")
        pdf.drawString(480, y, f"₹{total_amount:,.2f}")

        y -= 18
        if y < 120:
            pdf.showPage()
            y = height - 40

    # Grand Total box
    y -= 25
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(350, y, f"Grand Total: ₹{grand_total:,.2f}")

    pdf.save()
    buffer.seek(0)

    response = make_response(buffer.getvalue())
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = "attachment; filename=Invoice.pdf"
    return response


# -----------------------------
# ABOUT PAGE (STATS & CHART DATA)
# -----------------------------
import sqlite3
import requests
import importlib
import re

# Try dynamic import of BeautifulSoup to avoid static linter errors when bs4 isn't installed
try:
    bs4 = importlib.import_module("bs4")
    BeautifulSoup = bs4.BeautifulSoup  # type: ignore
except Exception:
    # bs4 not available — provide a minimal fallback to extract price tokens containing '₹'
    class _FakeTag:
        def __init__(self, text):
            self.text = text

    class BeautifulSoup:
        def __init__(self, text, parser):
            self._text = text

        def find(self, *args, **kwargs):
            # naive search for first occurrence of '₹' followed by digits/commas/decimals
            m = re.search(r'₹\s*[\d,]+(?:\.\d+)?', self._text)
            if m:
                return _FakeTag(m.group(0))
            return None

from flask import render_template
# reuse the 'app' object created earlier in the file

# ---- PRICE FETCH FUNCTION ----
def fetch_market_price(model_name):
    try:
        url = f"https://www.google.com/search?q={model_name.replace(' ', '+')}+laptop+price"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers)
        soup = BeautifulSoup(res.text, "html.parser")

        price_text = soup.find("span", text=lambda t: t and "₹" in t)
        if price_text:
            clean = price_text.text.replace("₹", "").replace(",", "")
            return float(clean)
    except:
        pass

    return None


# ---- ABOUT ROUTE ----
@app.route("/about")
def about():
    conn = sqlite3.connect("laptop_dataset.db")
    c = conn.cursor()

    # Count laptops
    c.execute("SELECT COUNT(*) FROM laptops")
    total_laptops = c.fetchone()[0]

    # Count brands
    c.execute("SELECT COUNT(DISTINCT Company) FROM laptops")
    num_brands = c.fetchone()[0]

    # Avg price
    c.execute("SELECT AVG(Price_Rs) FROM laptops")
    avg_price = c.fetchone()[0] or 0

    # Availability (dummy as no stock column)
    available_laptops = total_laptops

    # Brand distribution
    c.execute("SELECT Company, COUNT(*) FROM laptops GROUP BY Company")
    brand_data = c.fetchall()
    brand_labels = [b[0] for b in brand_data]
    brand_counts = [b[1] for b in brand_data]

    # Trending laptops (dummy)
    trending_labels = brand_labels[:5]
    trending_counts = brand_counts[:5]

    # Price range distribution
    c.execute("SELECT Price_Rs FROM laptops")
    prices = [p[0] for p in c.fetchall()]

    price_ranges = ["0-30K", "30K-50K", "50K-70K", "70K-100K", "100K+"]
    r_counts = [0,0,0,0,0]

    for p in prices:
        if p <= 30000: r_counts[0] += 1
        elif p <= 50000: r_counts[1] += 1
        elif p <= 70000: r_counts[2] += 1
        elif p <= 100000: r_counts[3] += 1
        else: r_counts[4] += 1

    # ---- MARKET PRICE COMPARISON ----
    c.execute("SELECT Product FROM laptops LIMIT 10")
    models = [m[0] for m in c.fetchall()]

    current_prices = []
    past_prices = []
    future_prices = []

    for m in models:
        price_now = fetch_market_price(m)
        if price_now is None:
            price_now = 50000  # fallback

        current_prices.append(price_now)
        past_prices.append(price_now * 1.20)   # past +20%
        future_prices.append(price_now * 0.85) # future -15%

    stats = {
        "total_laptops": total_laptops,
        "num_brands": num_brands,
        "avg_price": avg_price,
        "available_laptops": available_laptops,

        "brand_labels": brand_labels,
        "brand_counts": brand_counts,

        "trending_labels": trending_labels,
        "trending_counts": trending_counts,

        "price_range_labels": price_ranges,
        "price_range_counts": r_counts,

        "model_labels": models,
        "past_prices": past_prices,
        "current_prices": current_prices,
        "future_prices": future_prices
    }

    return render_template("about.html", stats=stats)



# -----------------------------
# CONTACT PAGE
# -----------------------------
@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        subject = request.form["subject"]
        message = request.form["message"]

        conn = sqlite3.connect("contact.db")
        c = conn.cursor()
        c.execute("""
            INSERT INTO contact_messages (name, email, subject, message)
            VALUES (?, ?, ?, ?)
        """, (name, email, subject, message))
        conn.commit()
        conn.close()

        flash("Your message has been sent successfully!")
        return redirect("/contact")

    return render_template("contact.html")



# -----------------------------
# WARRANTY PAGE
# -----------------------------
@app.route("/warranty", methods=["GET", "POST"])
def warranty_page():
    warranty_result = None

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        company = request.form.get("company", "").strip()
        product = request.form.get("product", "").strip()

        if not phone or not company or not product:
            flash("Please fill all fields", "danger")
            return render_template("warranty.html", warranty_result=None)

        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute(
            """
            SELECT warranty_status FROM laptops
            WHERE Company = ? AND Product = ?
        """,
            (company, product),
        )

        row = cur.fetchone()
        con.close()

        if row:
            warranty_result = row[0]
        else:
            flash("No warranty details found for this product.", "danger")

    return render_template("warranty.html", warranty_result=warranty_result)


# -----------------------------
# ACCESSORIES
# -----------------------------
@app.route("/accessories")
def accessories():
    return render_template("accessories.html")


# -----------------------------
# ANTIVIRUS DATA & ROUTES
# -----------------------------
antivirus_list = [
    {
        "id": 1,
        "name": "Kaspersky Total Security",
        "price": 799,
        "validity": "1 Year - 1 Device",
        "features": ["Real-time protection", "Anti-phishing", "Parental controls"],
        "url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcS9ilBrZ40fE0mwtP6YboP41IZ6bnBqmGUBvA&s",
    },
    {
        "id": 2,
        "name": "Quick Heal Total Security",
        "price": 699,
        "validity": "1 Year - 1 Device",
        "features": ["Ransomware protection", "Web security", "Performance optimizer"],
        "url": "https://images-eu.ssl-images-amazon.com/images/I/71U8ZqX6hPL._AC_UL210_SR210,210_.jpg",
    },
    {
        "id": 3,
        "name": "McAfee Antivirus Plus",
        "price": 899,
        "validity": "1 Year - 3 Devices",
        "features": ["VPN included", "Password manager", "Multi-device support"],
        "url": "https://5.imimg.com/data5/SELLER/Default/2023/3/296418100/LS/QN/QW/9971803/norton-360-deluxe-software-500x500.png",
    },
    {
        "id": 4,
        "name": "Norton 360 Deluxe",
        "price": 999,
        "validity": "1 Year - 5 Devices",
        "features": ["Cloud backup", "Smart firewall", "Dark web monitoring"],
        "url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSTlDA1GACboNR0X8c3iMtT_Lxm0N_4vO_Etir2Vvdcdq-ed8ihPNESMR-NWBEBN7ZexO8&usqp=CAU",
    },
]


@app.route("/antivirus")
def antivirus():
    return render_template("antivirus.html", antiviruses=antivirus_list)


@app.route("/buy-antivirus/<int:av_id>")
def buy_antivirus(av_id):
    antivirus = next((av for av in antivirus_list if av["id"] == av_id), None)
    if antivirus:
        return render_template("buy_antivirus.html", antivirus=antivirus)
    return "Antivirus not found", 404


# -----------------------------
# API: LAPTOPS JSON
# -----------------------------
@app.route("/api/laptops")
def api_laptops():
    df = load_dataset()
    return jsonify(df.to_dict("records"))


# -----------------------------
# API: REAL-TIME PRICE CHECK
# -----------------------------
@app.route("/api/get_price/<int:product_id>")
def get_price_api(product_id):
    """
    API endpoint to fetch price for a specific product.
    Uses cached prices from database for fast response.
    Only fetches fresh prices if cache is stale (>1 hour old) or missing.
    """
    from datetime import datetime, timedelta
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Fetch laptop data with cached prices
    cursor.execute("""
        SELECT Company, Product, Ram, PrimaryStorage, CPU_model, CPU_company,
               amazon_link, flipkart_link, 
               amazon_price_cached, flipkart_price_cached, last_price_update
        FROM laptops 
        WHERE rowid = ?
    """, (product_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return jsonify({"error": "Product not found"}), 404
    
    (brand, product_name, ram, storage, cpu_model, cpu_company,
     amazon_url, flipkart_url, 
     amazon_cached, flipkart_cached, last_update) = row
    
    # Calculate predicted price
    cpu = cpu_model or cpu_company
    predicted_price = predict_price_rule_based(brand, int(ram or 8), int(storage or 256), cpu)
    
    # Check if cached prices are fresh (less than 1 hour old)
    cache_is_fresh = False
    if last_update:
        try:
            last_update_dt = datetime.fromisoformat(last_update)
            cache_age = datetime.now() - last_update_dt
            cache_is_fresh = cache_age < timedelta(hours=1)
        except:
            pass
    
    # Use cached prices if fresh, otherwise fetch in real-time
    if cache_is_fresh and (amazon_cached or flipkart_cached):
        amazon_price = amazon_cached
        flipkart_price = flipkart_cached
    else:
        # Cache is stale or empty - fetch real-time prices
        print(f"Fetching real-time prices for product {product_id}...")
        amazon_price = get_amazon_price(amazon_url) if amazon_url else None
        flipkart_price = get_flipkart_price(flipkart_url) if flipkart_url else None
        
        # Update cache in database
        if amazon_price or flipkart_price:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            current_time = datetime.now().isoformat()
            cursor.execute("""
                UPDATE laptops 
                SET amazon_price_cached = ?,
                    flipkart_price_cached = ?,
                    last_price_update = ?
                WHERE rowid = ?
            """, (amazon_price, flipkart_price, current_time, product_id))
            conn.commit()
            conn.close()
            print(f"✓ Cached prices updated for product {product_id}")
    
    # Determine lowest price - ONLY compare Amazon and Flipkart (exclude predicted)
    marketplace_prices = []
    if amazon_price:
        marketplace_prices.append(('amazon', amazon_price))
    if flipkart_price:
        marketplace_prices.append(('flipkart', flipkart_price))
    
    # Use marketplace lowest price if available, otherwise fallback to predicted
    if marketplace_prices:
        price_source, lowest_price = min(marketplace_prices, key=lambda x: x[1])
    else:
        lowest_price = predicted_price
        price_source = 'predicted'
    
    response_data = {
        'amazon_price': amazon_price,
        'flipkart_price': flipkart_price,
        'lowest_price': lowest_price,
        'price_source': price_source,
        'amazon_link': amazon_url,
        'flipkart_link': flipkart_url,
        'cached': cache_is_fresh
    }
    
    print(f"📊 API Response for product {product_id}:")
    print(f"   Amazon: ₹{amazon_price if amazon_price else 'N/A'}")
    print(f"   Flipkart: ₹{flipkart_price if flipkart_price else 'N/A'}")
    print(f"   Lowest: ₹{lowest_price} (source: {price_source})")
    
    return jsonify(response_data)


# -----------------------------
# CATEGORY PAGES
# -----------------------------
@app.route("/students_laptops")
def students_laptops():
    return render_template("students_laptops.html")


@app.route("/office_laptops")
def office_laptops():
    return render_template("office_laptops.html")


@app.route("/cheap_laptops")
def cheap_laptops():
    return render_template("cheap_laptops.html")


@app.route("/shop")
def shop():
    categories = [
        {
            "name": "Laptops",
            "desc": "Gaming | Office | Students",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTjeQkkw7u63MYY8Z3HSh_pHA-XQafHvMDB7Q&s",
            "href": "/products?category=laptops",
        },
        {
            "name": "Antivirus Software",
            "desc": "Kaspersky | Norton | McAfee",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTPCAefBFCP6jr0eh5wJS-8kFJfm_lKDQ2Xjg&s",
            "href": "/antivirus",
        },
        {
            "name": "External Monitors",
            "desc": "4K UHD | Gaming | Portable",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQj3ZGbfqSapoW_U2JamvoboHM12G_Jqn0u4w&s",
            "href": "/monitors",
        },
        {
            "name": "Accessories",
            "desc": "Chargers | Cables | Covers",
            "img": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRxbSLQWufLFI5o8SlDrCPivQudiX82dl3gAqdrpFtZlVI-PnLPPkdOegMfKGreEjojGss&usqp=CAU",
            "href": "/accessories",
        },
    ]
    return render_template("shop.html", categories=categories)


# -----------------------------
# CART & CHECKOUT (LAPTOPS)
# -----------------------------
def initialize_cart():
    if "cart" not in session:
        session["cart"] = []
        session["total_items"] = 0
        session["total_price"] = 0


@app.route("/cart")
def cart_page():
    return render_template(
        "cart.html",
        cart=session.get("cart", []),
        total_items=session.get("total_items", 0),
        total_price=session.get("total_price", 0),
    )


@app.route("/checkout", methods=["GET"])
def checkout_cart():
    cart = session.get("cart", [])
    total_price = session.get("total_price", 0)
    return render_template("checkout_cart.html", cart=cart, total_price=total_price)


@app.route("/place-order", methods=["POST"])
def place_order():
    cart = session.get("cart", [])
    if not cart:
        return redirect("/cart")

    customer_name = request.form.get("name")
    phone = request.form.get("phone")
    payment_method = request.form.get("payment")

    invoice_id = f"QLT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    session["last_order"] = cart
    session["customer_name"] = customer_name
    session["phone"] = phone
    session["payment_method"] = payment_method
    session["invoice_id"] = invoice_id

    # Generate invoice PDF
    pdf_buffer = io.BytesIO()
    pdf = rl_canvas.Canvas(pdf_buffer, pagesize=A4)
    y = 800

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(50, y, "INVOICE")
    y -= 30

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Invoice ID: {invoice_id}")
    y -= 15
    pdf.drawString(50, y, f"Customer Name: {customer_name}")
    y -= 15
    pdf.drawString(50, y, f"Phone: {phone}")
    y -= 20

    pdf.drawString(50, y, "Products:")
    y -= 15

    grand_total = 0
    for item in cart:
        amount = item["price"] * item["quantity"]
        pdf.drawString(60, y, f"{item['name']} x {item['quantity']}  =  ₹{amount}")
        grand_total += amount
        y -= 18

    y -= 10
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, y, f"Grand Total: ₹{grand_total}")

    pdf.save()
    pdf_buffer.seek(0)

    if not os.path.exists("invoices"):
        os.makedirs("invoices")

    pdf_filename = f"{invoice_id}.pdf"
    pdf_path = os.path.join("invoices", pdf_filename)
    with open(pdf_path, "wb") as f:
        f.write(pdf_buffer.getvalue())

    # Store Order in orders.db
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orders (customer_name, phone, payment_method, product_info, invoice_id, invoice_pdf_path)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (customer_name, phone, payment_method, json.dumps(cart), invoice_id, pdf_path),
    )
    conn.commit()
    conn.close()

    # Clear cart
    session["cart"] = []
    session["total_items"] = 0
    session["total_price"] = 0
    session.modified = True

    return render_template("order_success_cart.html", invoice_id=invoice_id)


@app.route("/invoice")
def invoice():
    order_items = session.get("last_order", [])
    if not order_items:
        return redirect("/cart")

    customer_name = session.get("customer_name")
    phone = session.get("phone")
    payment_method = session.get("payment_method")

    invoice_id = f"QLS-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    invoice_date = datetime.now().strftime("%d %B %Y")

    pdf_folder = "invoice_pdfs"
    os.makedirs(pdf_folder, exist_ok=True)
    pdf_path = f"{pdf_folder}/{invoice_id}.pdf"

    buffer = io.BytesIO()
    pdf = rl_canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(40, y, "INVOICE")
    y -= 30

    pdf.setFont("Helvetica", 12)
    pdf.drawString(40, y, f"Invoice ID: {invoice_id}")
    y -= 18
    pdf.drawString(40, y, f"Date: {invoice_date}")
    y -= 30

    grand_total = 0
    for item in order_items:
        amount = item["price"] * item["quantity"]
        gst = round(amount * 0.18)
        total = amount + gst
        grand_total += total

        pdf.drawString(40, y, f"{item['name']} (x{item['quantity']}) — ₹{total}")
        y -= 20

    pdf.drawString(40, y - 20, f"Grand Total: ₹{grand_total}")
    pdf.save()

    with open(pdf_path, "wb") as f:
        f.write(buffer.getvalue())

    product_info = str(order_items)
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orders (customer_name, phone, payment_method, product_info, invoice_id, invoice_pdf_path)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (customer_name, phone, payment_method, product_info, invoice_id, pdf_path),
    )
    conn.commit()
    conn.close()

    return render_template(
        "invoice.html",
        order_items=order_items,
        grand_total=grand_total,
        invoice_id=invoice_id,
    )


@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    initialize_cart()

    product_id = request.form.get("id")
    name = request.form.get("name")
    price = float(str(request.form.get("price")).replace(",", ""))
    image = request.form.get("image")

    for item in session["cart"]:
        if item["id"] == product_id:
            item["quantity"] += 1
            break
    else:
        session["cart"].append(
            {
                "id": product_id,
                "name": name,
                "price": price,
                "image": image,
                "quantity": 1,
            }
        )

    session["total_items"] = sum(i["quantity"] for i in session["cart"])
    session["total_price"] = sum(i["price"] * i["quantity"] for i in session["cart"])
    session.modified = True

    flash("Item added to cart")
    return redirect(request.referrer)


@app.route("/remove-item", methods=["POST"])
def remove_item():
    product_id = request.form.get("product_id")
    session["cart"] = [item for item in session["cart"] if item["id"] != product_id]

    session["total_items"] = sum(i["quantity"] for i in session["cart"])
    session["total_price"] = sum(i["price"] * i["quantity"] for i in session["cart"])
    session.modified = True

    return redirect(url_for("cart_page"))


@app.route("/update-quantity", methods=["POST"])
def update_quantity():
    product_id = request.form.get("product_id")
    quantity = int(request.form.get("quantity"))

    for item in session["cart"]:
        if item["id"] == product_id:
            item["quantity"] = quantity
            break

    session["total_items"] = sum(i["quantity"] for i in session["cart"])
    session["total_price"] = sum(i["price"] * i["quantity"] for i in session["cart"])
    session.modified = True

    return redirect(url_for("cart_page"))


@app.route("/buy-now", methods=["POST"])
def buy_now():
    initialize_cart()

    product_id = request.form.get("id")
    name = request.form.get("name")
    price = float(str(request.form.get("price")).replace(",", ""))
    image = request.form.get("image")

    for item in session["cart"]:
        if item["id"] == product_id:
            item["quantity"] += 1
            break
    else:
        session["cart"].append(
            {
                "id": product_id,
                "name": name,
                "price": price,
                "image": image,
                "quantity": 1,
            }
        )

    session["total_items"] = sum(i["quantity"] for i in session["cart"])
    session["total_price"] = sum(i["price"] * i["quantity"] for i in session["cart"])
    session.modified = True

    return redirect(url_for("cart_page"))


# -----------------------------
# RATINGS (IN-MEMORY)
# -----------------------------
ratings = {}  # { laptop_id: [ratings...] }


@app.route("/rate/<id>", methods=["POST"])
def rate_laptop(id):
    rating = int(request.form["rating"])
    if id not in ratings:
        ratings[id] = []
    ratings[id].append(rating)
    return redirect(request.referrer)


# -----------------------------
# SIMPLE RECOMMENDER (if used)
# -----------------------------
def recommend_laptops(selected_ids):
    df = load_dataset()
    laptops = df.to_dict("records")

    if not selected_ids:
        return random.sample(laptops, min(3, len(laptops)))

    selected = [l for l in laptops if str(l["ID"]) in selected_ids]
    if not selected:
        return random.sample(laptops, min(3, len(laptops)))

    base = selected[0]

    recs = []
    for l in laptops:
        if str(l["ID"]) in selected_ids:
            continue
        same_cpu = ("Processor_Model" in l and "Processor_Model" in base and
                    l["Processor_Model"] == base["Processor_Model"])
        same_ram = ("RAM_Size" in l and "RAM_Size" in base and
                    l["RAM_Size"] == base["RAM_Size"])
        close_price = abs(float(l["Price"]) - float(base["Price"])) <= 20000
        if same_cpu or same_ram or close_price:
            recs.append(l)

    if not recs:
        recs = [l for l in laptops if str(l["ID"]) not in selected_ids]

    return random.sample(recs, min(3, len(recs)))


# -----------------------------
# CHATBOT
# -----------------------------
@app.route("/chatbot", methods=["POST"])
def chatbot():
    user_msg = request.json.get("message", "").lower()

    responses = {
        "hi": "Hello! 👋 How can I assist you today?",
        "hello": "Hello! 😊 What laptop details would you like to know?",
        "dell": "💼 Dell laptops are highly reliable for office and business use. • Inspiron – budget and everyday tasks • XPS – premium performance and build quality.",
        "hp": "💛 HP laptops offer solid reliability and good customer support. • Pavilion – budget & students • Omen – gaming and high performance.",
        "lenovo": "🟥 Lenovo provides the best value-for-money laptops. • IdeaPad – students & daily use • Legion – high-end gaming and performance.",
        "asus": "🟦 Asus is excellent for performance and gaming. • VivoBook – everyday & office • TUF/ROG – gaming with strong thermals.",
        "acer": "🟨 Acer offers powerful performance at affordable pricing. • Aspire – budget segment • Predator – gaming laptops.",
        "gaming laptop": "🎮 For gaming, consider: Ryzen 7 / Core i7 | 16GB RAM | RTX 3050 / 3060 GPU | 144Hz display. These specs provide smooth performance in modern games.",
        "student laptop": "🎓 For students: Ryzen 5 / Core i5 | 8GB RAM | 512GB SSD | good battery backup. Lightweight models are recommended for portability.",
        "under 30000": "💰 Top laptops under ₹30,000 — Lenovo V14 | HP 15s | Acer Aspire 3. Ideal for basic office and student needs.",
        "under 40000": "💰 Best laptops under ₹40,000 — Lenovo IdeaPad Slim 3 | HP 15s | Acer Aspire 5. Good for students & office users.",
        "under 50000": "💰 Recommended under ₹50,000 — Dell Inspiron 15 3000 | Lenovo IdeaPad 3 | Acer Aspire 5. Balanced performance and value.",
        "under 60000": "💰 Best picks under ₹60,000 — Asus VivoBook Pro | HP Victus | Lenovo IdeaPad Gaming. Suitable for entry-level gaming and editing.",
        "under 70000": "💰 Best under ₹70,000 — Lenovo Legion 5 | Asus TUF F15 | HP Victus 16. Great for gaming and heavy work.",
        "under 80000": "💰 Top laptops under ₹80,000 — Dell G15 | Asus ROG Strix | Lenovo Legion 5. Powerful gaming and graphics performance.",
        "under 100000": "💰 Best under ₹1,00,000 — MacBook Air M1 | Dell XPS 13 | Asus ROG Zephyrus. Premium build and high performance.",
        "battery": "🔋 For long battery life, choose Intel U-series / Ryzen U-series processors and 50–70Wh battery capacity.",
        "heating": "🔥 Laptop heating can be reduced by ensuring proper ventilation, using it on hard surfaces and cleaning air vents regularly.",
        "slow": "⚡ To speed up a slow laptop: upgrade to SSD, add more RAM, remove startup apps, and perform regular updates.",
        "warranty": "🛡 Warranty can be checked using the laptop's serial number on the brand's official support website.",
        "clean": "🧼 Clean your laptop screen with a microfiber cloth and use compressed air to remove dust from the keyboard and vents.",
        "bye": "Thank you for chatting with us! 👋 Have a great day ahead!",
        "thank you": "You're welcome! 😊 Happy to assist you anytime.",
    }

    for key in responses:
        if key in user_msg:
            return jsonify({"reply": responses[key]})

    return jsonify(
        {
            "reply": "I'm here to help 😊 Ask about brands, gaming laptops, student laptops, budget laptops, battery, or warranty."
        }
    )


# -----------------------------
# ANTIVIRUS CHECKOUT
# -----------------------------
@app.route("/checkout/<int:id>", methods=["POST"])
def checkout(id):
    antivirus = next((a for a in antivirus_list if a["id"] == id), None)

    customer_name = request.form["name"]
    email = request.form["email"]
    phone = request.form["phone"]
    payment_method = request.form["payment"]

    session["order"] = {
        "name": customer_name,
        "email": email,
        "phone": phone,
        "payment_method": payment_method,
    }

    upi_id = "9980307550-2@axl"  # change to your UPI
    return render_template("checkout.html", antivirus=antivirus, upi_id=upi_id)


@app.route("/order_success/<int:id>", methods=["POST"])
def order_success(id):
    antivirus = next((a for a in antivirus_list if a["id"] == id), None)
    
    # Populate session for invoice generation
    if antivirus:
        session["last_order"] = [{
            "name": antivirus["name"],
            "price": antivirus["price"],
            "quantity": 1,
            "id": antivirus["id"]
        }]
        
        # Get customer details from the order session set in checkout
        order_details = session.get("order", {})
        session["customer_name"] = order_details.get("name", "Customer")
        session["phone"] = order_details.get("phone", "")
        session["payment_method"] = order_details.get("payment_method", "")
        
    return render_template("order_success.html", antivirus=antivirus)


# -----------------------------
# CART COUNT IN NAVBAR
# -----------------------------
@app.context_processor
def cart_total_processor():
    cart = session.get("cart", [])
    cart_count = sum(item["quantity"] for item in cart)
    return dict(cart_count=cart_count)


# -----------------------------
# ADMIN CONFIG
# -----------------------------
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "sachin@2005"

# Face recognition storage (in production, use a secure database)
FACE_DATA_FILE = "admin_face_data.json"

# Helper function to calculate Euclidean distance
def euclidean_distance(descriptor1, descriptor2):
    """Calculate Euclidean distance between two face descriptors."""
    import numpy as np
    arr1 = np.array(descriptor1)
    arr2 = np.array(descriptor2)
    return np.linalg.norm(arr1 - arr2)


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session["admin"] = True
            flash("Login successful!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("admin_login.html")


@app.route("/admin/face/register", methods=["GET", "POST"])
def admin_face_register():
    """Face registration page - MULTI-ADMIN support (adds faces, doesn't replace)"""
    # Check how many faces are already registered
    total_registered = 0
    if os.path.exists(FACE_DATA_FILE):
        try:
            with open(FACE_DATA_FILE, 'r') as f:
                face_data = json.load(f)
            total_registered = len(face_data.get("registered_faces", []))
        except:
            total_registered = 0
    
    if request.method == "POST":
        # Verify BOTH username and password before allowing registration
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        
        # Strict authentication - both must match
        if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
            flash("Invalid credentials. Both username and password are required.", "danger")
            return render_template("admin_face_register.html", 
                                 show_auth=True, 
                                 total_registered=total_registered)
        
        # Credentials correct, show face capture interface
        return render_template("admin_face_register.html", 
                             show_auth=False, 
                             authenticated=True,
                             total_registered=total_registered)
    
    # GET request - check if already authenticated via session
    if session.get("admin"):
        # Admin logged in, allow registration
        return render_template("admin_face_register.html", 
                             show_auth=False, 
                             authenticated=True,
                             total_registered=total_registered)
    
    # Not authenticated, show credential prompt
    return render_template("admin_face_register.html", 
                         show_auth=True,
                         total_registered=total_registered)


@app.route("/api/save_face", methods=["POST"])
def save_face():
    """API endpoint to save admin face descriptors - MULTI-ADMIN SUPPORT"""
    try:
        data = request.get_json()
        descriptors = data.get("descriptors", [])
        
        if not descriptors or len(descriptors) < 5:
            return jsonify({
                "success": False,
                "message": "Insufficient face data. Please capture at least 5 images for maximum security."
            })
        
        # Load existing face data or create new structure
        if os.path.exists(FACE_DATA_FILE):
            with open(FACE_DATA_FILE, 'r') as f:
                face_data = json.load(f)
            registered_faces = face_data.get("registered_faces", [])
        else:
            registered_faces = []
        
        # Create new face profile with unique ID
        new_face_profile = {
            "id": f"admin_{len(registered_faces) + 1}",
            "descriptors": descriptors,
            "registered_at": datetime.now().isoformat(),
            "total_samples": len(descriptors),
            "status": "active"
        }
        
        # ADD to the list (not replace)
        registered_faces.append(new_face_profile)
        
        # Save updated list
        face_data = {
            "registered_faces": registered_faces,
            "total_admins": len(registered_faces),
            "last_updated": datetime.now().isoformat()
        }
        
        with open(FACE_DATA_FILE, 'w') as f:
            json.dump(face_data, f, indent=2)
        
        print(f"✓ New admin face registered successfully")
        print(f"   Profile ID: {new_face_profile['id']}")
        print(f"   Total Registered Admins: {len(registered_faces)}")
        print(f"   Samples: {len(descriptors)}")
        
        return jsonify({
            "success": True,
            "message": f"Face profile registered successfully! Total admins: {len(registered_faces)}",
            "profile_id": new_face_profile['id'],
            "total_admins": len(registered_faces)
        })
    
    except Exception as e:
        print(f"Error saving face data: {e}")
        return jsonify({
            "success": False,
            "message": f"Error saving face data: {str(e)}"
        })


@app.route("/api/verify_face", methods=["POST"])
def verify_face():
    """API endpoint to verify admin face - MULTI-ADMIN SUPPORT"""
    try:
        data = request.get_json()
        descriptor = data.get("descriptor", [])
        
        if not descriptor:
            print("⚠ Face verification failed: No face data provided")
            return jsonify({
                "success": False,
                "message": "No face data provided."
            })
        
        # Load stored face data
        if not os.path.exists(FACE_DATA_FILE):
            print("⚠ Face verification failed: No face profiles registered")
            return jsonify({
                "success": False,
                "message": "No admin faces registered. Please register your face first or use password login."
            })
        
        with open(FACE_DATA_FILE, 'r') as f:
            face_data = json.load(f)
        
        registered_faces = face_data.get("registered_faces", [])
        
        if not registered_faces:
            print("⚠ Face verification failed: No face profiles found")
            return jsonify({
                "success": False,
                "message": "No admin faces registered. Please register first."
            })
        
        # Check against ALL registered admin faces
        print(f"🔍 Face verification attempt - Checking against {len(registered_faces)} registered admin(s)")
        
        best_match = None
        best_min_distance = float('inf')
        
        # Try to match with each registered admin
        for admin_profile in registered_faces:
            if admin_profile.get("status") != "active":
                continue  # Skip inactive profiles
            
            stored_descriptors = admin_profile.get("descriptors", [])
            if not stored_descriptors:
                continue
            
            # Calculate distances to this admin's samples
            distances = []
            for stored_descriptor in stored_descriptors:
                distance = euclidean_distance(descriptor, stored_descriptor)
                distances.append(distance)
            
            # Get stats for this admin
            min_distance = min(distances)
            avg_distance = sum(distances) / len(distances)
            close_matches = sum(1 for d in distances if d < 0.4)
            
            print(f"   Admin {admin_profile['id']}:")
            print(f"     Min: {min_distance:.4f}, Avg: {avg_distance:.4f}, Matches: {close_matches}/{len(distances)}")
            
            # Check if this admin matches
            strict_threshold = 0.4
            avg_threshold = 0.5
            
            if min_distance < strict_threshold and avg_distance < avg_threshold and close_matches >= 2:
                # Found a match!
                if min_distance < best_min_distance:
                    best_match = admin_profile
                    best_min_distance = min_distance
        
        # Check if we found a match
        if best_match:
            # Face matched with one of the admins!
            session["admin"] = True
            print(f"✓ Face verification SUCCESS")
            print(f"   Matched Admin: {best_match['id']}")
            print(f"   Registered: {best_match['registered_at']}")
            print(f"   Min Distance: {best_min_distance:.4f}")
            return jsonify({
                "success": True,
                "message": f"Welcome, Admin! Access granted.",
                "redirect": url_for("admin_dashboard"),
                "admin_id": best_match['id']
            })
        else:
            # No match found with any admin
            print(f"✗ Face verification FAILED - No match with any registered admin")
            print(f"   Checked {len(registered_faces)} admin profile(s)")
            
            return jsonify({
                "success": False,
                "message": "Face not recognized. This face is not registered as admin."
            })
    
    except Exception as e:
        print(f"❌ Error verifying face: {e}")
        return jsonify({
            "success": False,
            "message": f"Verification error: {str(e)}"
        })


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    flash("Logged out successfully", "info")
    return redirect(url_for("admin_login"))


@app.route("/admin/dashboard")
def admin_dashboard():
    # Laptops count
    conn = sqlite3.connect("laptop_dataset.db")  # your laptop DB
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM laptops")
    laptop_count = c.fetchone()[0]
    conn.close()

    # Orders count
    conn = sqlite3.connect("orders.db")  # If you have orders DB
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM orders")
    order_count = c.fetchone()[0]
    conn.close()

    # Contact Messages count
    conn = sqlite3.connect("contact.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM contact_messages")
    contact_count = c.fetchone()[0]
    conn.close()

    return render_template("admin_dashboard.html",
                           laptop_count=laptop_count,
                           order_count=order_count,
                           contact_count=contact_count)


# -----------------------------
# ADMIN LAPTOP CRUD
# -----------------------------
@app.route("/admin/laptops")
def admin_laptops():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT rowid, Company, Product, Price_Rs, warranty_status FROM laptops"
    )
    laptops = cur.fetchall()
    conn.close()

    return render_template("admin_laptops.html", laptops=laptops)


@app.route("/admin/laptops/add", methods=["GET", "POST"])
def admin_add_laptop():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        company = request.form["company"]
        product = request.form["product"]
        price = request.form["price"]
        image = request.form["image"]  # currently unused in DB
        warranty = request.form["warranty"]
        amazon_link = request.form.get("amazon_link", "")
        flipkart_link = request.form.get("flipkart_link", "")

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO laptops (Company, Product, Price_Rs, warranty_status, amazon_link, flipkart_link) VALUES (?, ?, ?, ?, ?, ?)",
            (company, product, price, warranty, amazon_link, flipkart_link),
        )
        conn.commit()
        conn.close()

        flash("Laptop added successfully!", "success")
        return redirect(url_for("admin_laptops"))

    return render_template("admin_add_laptop.html")


@app.route("/admin/laptops/edit/<int:id>", methods=["GET", "POST"])
def admin_edit_laptop(id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    if request.method == "POST":
        company = request.form["company"]
        product = request.form["product"]
        price = request.form["price"]
        image = request.form["image"]  # currently unused
        warranty = request.form["warranty"]
        amazon_link = request.form.get("amazon_link", "")
        flipkart_link = request.form.get("flipkart_link", "")

        cur.execute(
            """
            UPDATE laptops SET Company=?, Product=?, Price_Rs=?, warranty_status=?, amazon_link=?, flipkart_link=? WHERE rowid=?
        """,
            (company, product, price, warranty, amazon_link, flipkart_link, id),
        )
        conn.commit()
        conn.close()

        flash("Laptop updated successfully!", "success")
        return redirect(url_for("admin_laptops"))

    cur.execute(
        "SELECT Company, Product, Price_Rs, warranty_status, amazon_link, flipkart_link FROM laptops WHERE rowid=?",
        (id,),
    )
    laptop = cur.fetchone()
    conn.close()

    return render_template("admin_edit_laptop.html", laptop=laptop, id=id)


@app.route("/admin/laptops/delete/<int:id>")
def admin_delete_laptop(id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM laptops WHERE rowid=?", (id,))
    conn.commit()
    conn.close()

    flash("Laptop deleted successfully!", "success")
    return redirect(url_for("admin_laptops"))


# -----------------------------
# ADMIN ORDERS MANAGEMENT
# -----------------------------
@app.route("/admin/orders")
def admin_orders():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("orders.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders ORDER BY id DESC")
    orders = cur.fetchall()
    conn.close()

    return render_template("admin_orders.html", orders=orders)


@app.route("/admin/orders/invoice/<int:id>")
def admin_order_invoice(id):
    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()
    cur.execute("SELECT invoice_pdf_path FROM orders WHERE id=?", (id,))
    row = cur.fetchone()
    conn.close()

    if row and os.path.exists(row[0]):
        return send_file(row[0], as_attachment=True)
    else:
        return "Invoice not found", 404


@app.route("/admin/orders/delete/<int:id>")
def admin_order_delete(id):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))

    conn = sqlite3.connect("orders.db")
    cur = conn.cursor()
    cur.execute("SELECT invoice_pdf_path FROM orders WHERE id=?", (id,))
    row = cur.fetchone()

    if row and os.path.exists(row[0]):
        os.remove(row[0])

    cur.execute("DELETE FROM orders WHERE id=?", (id,))
    conn.commit()
    conn.close()

    flash("Order deleted successfully!", "info")
    return redirect(url_for("admin_orders"))

@app.route("/admin/contact_messages")
def admin_contact_messages():
    conn = sqlite3.connect("contact.db")
    c = conn.cursor()
    c.execute("SELECT id, name, email, subject, message, created_at FROM contact_messages ORDER BY created_at DESC")
    messages = c.fetchall()
    conn.close()

    return render_template("admin_contact_messages.html", messages=messages)


@app.route("/admin/delete_message/<int:msg_id>", methods=["POST"])
def delete_message(msg_id):
    conn = sqlite3.connect("contact.db")
    c = conn.cursor()
    c.execute("DELETE FROM contact_messages WHERE id = ?", (msg_id,))
    conn.commit()
    conn.close()

    flash("Message deleted successfully!")
    return redirect("/admin/contact_messages")

@app.route("/admin/message/<int:msg_id>")
def admin_view_message(msg_id):
    conn = sqlite3.connect("contact.db")
    c = conn.cursor()
    c.execute("SELECT id, name, email, subject, message, created_at FROM contact_messages WHERE id = ?", (msg_id,))
    msg = c.fetchone()
    conn.close()

    return render_template("admin_view_message.html", msg=msg)

@app.route("/admin/reply_message/<int:msg_id>", methods=["POST"])
def reply_message(msg_id):
    reply_text = request.form["reply_text"]

    # Fetch user email
    conn = sqlite3.connect("contact.db")
    c = conn.cursor()
    c.execute("SELECT email, subject FROM contact_messages WHERE id = ?", (msg_id,))
    user_email, subject = c.fetchone()
    conn.close()

    # -------- YOUR EMAIL SETTINGS ----------
    sender_email = "yourgmail@gmail.com"
    sender_password = "your_app_password"  # Not normal password!
    # ----------------------------------------

    # Build email
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = user_email
    msg["Subject"] = f"Re: {subject}"

    msg.attach(MIMEText(reply_text, "plain"))

    # Send email
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, user_email, msg.as_string()) 
        server.quit()

        flash("Reply sent successfully!")
    except Exception as e:
        flash(f"Error sending reply: {e}")

    return redirect(f"/admin/message/{msg_id}")

# -----------------------------
# MAIN ENTRY
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
