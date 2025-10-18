# utils.py
import qrcode
from io import BytesIO
from django.core.files import File
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.utils import ImageReader
import qrcode
import io
from datetime import datetime
from django.http import HttpResponse
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# import os 
# font_path = os.path.join(os.path.dirname(__file__), 'fonts', 'NotoSansTamil-Regular.ttf')
# pdfmetrics.registerFont(TTFont('NotoTamil', font_path))

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from django.conf import settings
import os

# Correct path with the subfolder and exact filename
font_path = os.path.join(settings.BASE_DIR, 'san_app', 'fonts', 'Noto_Sans_Tamil')

# Debug: print the path
print(f"Font path: {font_path}")
print(f"File exists: {os.path.exists(font_path)}")

if not os.path.exists(font_path):
    raise FileNotFoundError(f"Tamil font not found at: {font_path}. Please check the file path.")

# Register the font
try:
    pdfmetrics.registerFont(TTFont('NotoTamil', font_path))
    print("Tamil font registered successfully!")
except Exception as e:
    print(f"Error registering font: {e}")
    # You might want to use a fallback font here


import random
from django.core.mail import send_mail
from django.conf import settings

def send_otp_via_email(email):
    otp = random.randint(100000, 999999)  # 6-digit OTP
    subject = "உங்கள் OTP குறியீடு"
    message = f"உங்கள் OTP: {otp}. தயவு செய்து இதை 5 நிமிடங்களில் உள்ளீடு செய்யவும்."
    
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,  # from email
        [email],                   # to email
        fail_silently=False,
    )
    return otp
import os
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ---------- Register Tamil font ----------
# Use exact path to TTF
FONT_PATH = os.path.join(
    settings.BASE_DIR,  # C:\projects\SAN_project
    "san_app", "fonts", "Noto_Sans_Tamil", "static", "NotoSansTamil-Regular.ttf"
)

if not os.path.exists(FONT_PATH):
    raise FileNotFoundError(f"Tamil font not found at: {FONT_PATH}")

# Register font with ReportLab
pdfmetrics.registerFont(TTFont("TamilFont", FONT_PATH))
print("Tamil font registered successfully!")

def get_attr(obj, key, default=""):
    """
    Safe getter: works for model instances or dicts (nested keys allowed, e.g. 'customer.name').
    """
    if isinstance(obj, dict):
        try:
            parts = key.split(".")
            val = obj
            for p in parts:
                val = val[p]
            return val
        except (KeyError, TypeError):
            return default
    else:
        parts = key.split(".")
        val = obj
        try:
            for p in parts:
                val = getattr(val, p)
            return val
        except AttributeError:
            return default


def generate_receipt_pdf(order):
    """
    Generate PDF receipt for an order in Tamil.
    Works with model instance or DRF serializer dict.
    Returns PDF file path.
    """
    # Create receipts directory
    receipts_dir = os.path.join(settings.MEDIA_ROOT, "receipts")
    os.makedirs(receipts_dir, exist_ok=True)

    # Get order_id safely
    order_id = get_attr(order, "order_id", "unknown")
    file_path = os.path.join(receipts_dir, f"order_{order_id}.pdf")

    # Create PDF
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    y = height - 20 * mm

    # HEADER
    c.setFont("TamilFont", 16)
    c.drawCentredString(width / 2, y, "கேட் பாஸ் மரக்கடை")
    y -= 10 * mm
    c.setFont("TamilFont", 12)
    c.drawCentredString(width / 2, y, "வாடிக்கையாளர் ரசீது")
    y -= 15 * mm

    # CUSTOMER DETAILS
    c.setFont("TamilFont", 12)
    c.drawString(20 * mm, y, "வாடிக்கையாளர் விவரங்கள்:")
    y -= 8 * mm
    c.setFont("TamilFont", 11)

    customer_name = get_attr(order, "customer.name", "")
    customer_mobile = get_attr(order, "customer.mobile", "")
    delivery_address = get_attr(order, "delivery_address", "")
    created_at = get_attr(order, "created_at", "")
    if hasattr(created_at, "strftime"):
        created_at = created_at.strftime("%d-%m-%Y %H:%M")

    for label, value in [
        ("பெயர்", customer_name),
        ("மொபைல்", customer_mobile),
        ("முகவரி", delivery_address),
        ("ஆர்டர் எண்", order_id),
        ("தேதி", created_at),
    ]:
        c.drawString(25 * mm, y, f"{label}: {value}")
        y -= 7 * mm

    # ORDER DETAILS
    y -= 5 * mm
    c.setFont("TamilFont", 12)
    c.drawString(20 * mm, y, "ஆர்டர் விவரங்கள்:")
    y -= 10 * mm
    c.setFont("TamilFont", 11)

    product_name = get_attr(order, "product.product_name", "")
    category = get_attr(order, "category", "")
    measurement_type = get_attr(order, "measurement_type", "Quantity")
    quantity = get_attr(order, "quantity", 0)
    unit = get_attr(order, "unit", 0)
    price = get_attr(order, "product.price", 0)

    if measurement_type == "Quantity":
        item_line = f"பொருள்: {product_name} | வகை: {category} | அளவு: {quantity} x ₹{price} = ₹{quantity * price}"
    else:
        item_line = f"பொருள்: {product_name} | வகை: {category} | அளவு: {unit} x ₹{price} = ₹{unit * price}"

    c.drawString(25 * mm, y, item_line)
    y -= 12 * mm

    # PAYMENT DETAILS
    c.setFont("TamilFont", 12)
    c.drawString(20 * mm, y, "கட்டண விவரங்கள்:")
    y -= 8 * mm
    c.setFont("TamilFont", 11)

    discount = get_attr(order, "discount", 0)
    paid_amount = get_attr(order, "paid_amount", 0)
    total_amount = get_attr(order, "total_amount", 0)
    pending_amount = get_attr(order, "pending_amount", 0)
    payment_method_func = get_attr(order, "get_payment_method_display", lambda: "")
    payment_method = payment_method_func() if callable(payment_method_func) else payment_method_func

    for label, value in [
        ("மொத்த தொகை", total_amount),
        ("தள்ளுபடி", discount) if discount else None,
        ("செலுத்திய தொகை", paid_amount),
        ("நிலுவை தொகை", pending_amount),
        ("கட்டண முறை", payment_method),
    ]:
        if label:
            c.drawString(25 * mm, y, f"{label}: {value}")
            y -= 7 * mm

    # FOOTER
    y -= 10 * mm
    c.setFont("TamilFont", 10)
    c.drawCentredString(width / 2, 15 * mm, "நன்றி! மீண்டும் வருக!")

    c.showPage()
    c.save()

    return file_path

# def generate_qr_code(order_instance, request=None):
#     if request:
#         qr_content = request.build_absolute_uri(
#             f"/scan_auto/?order_id={order_instance.order_id}"
#         )
#     else:
#         qr_content = f"http://127.0.0.1:8000/scan_auto/?order_id={order_instance.order_id}"

#     qr = qrcode.make(qr_content)
#     buffer = BytesIO()
#     qr.save(buffer, format="PNG")
#     buffer.seek(0)

#     filename = f"order_{order_instance.order_id}.png"
#     order_instance.qr_code.save(filename, File(buffer), save=True)
#     print("🔍 QR CONTENT:", qr_content)


#     return qr_content



def generate_qr_code(order_instance, request=None):
    if request:
        qr_content = request.build_absolute_uri(
            f"/scan_auto/?order_id={order_instance.order_id}"
        )
    else:
        qr_content = f"https://http://192.168.1.34:8000/scan_auto/?order_id={order_instance.order_id}"

    # ✅ Debug print
    print("🔍 QR CONTENT:", qr_content)

    qr = qrcode.make(qr_content)

    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    filename = f"order_{order_instance.order_id}.png"
    order_instance.qr_code.save(filename, File(buffer), save=True)

    return qr_content


# from decimal import Decimal
# from .models import TransactionLog

# def create_transaction_log(customer, amount_received, orders_cleared=None, excess_amount=Decimal("0.00")):
#     orders_cleared = orders_cleared or []
#     note = f"Paid ₹{amount_received}. Orders cleared: {orders_cleared}. Excess balance added: ₹{excess_amount}."
    
#     TransactionLog.objects.create(
#         customer=customer,
#         amount_received=Decimal(amount_received),
#         orders_cleared=orders_cleared,
#         excess_amount=Decimal(excess_amount),
#         note=note
#     )

from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime



def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0
    

from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from datetime import datetime

from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime

def safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

def generate_order_pdf(order_data: dict) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50

    # ---------- Title ----------
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, y, f"Order Receipt - #{order_data.get('order_id', '')}")
    y -= 40

    # ---------- Customer Information ----------
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Customer Information")
    y -= 25
    c.setFont("Helvetica", 12)

    customer_name = order_data.get('customer_name_display') or order_data.get('customer')
    if customer_name:
        c.drawString(50, y, f"Name: {customer_name}")
        y -= 20

    mobile_no = order_data.get('customer_mobile') or order_data.get('contact_no')
    if mobile_no:
        c.drawString(50, y, f"Mobile: {mobile_no}")
        y -= 20

    delivery_address = order_data.get('delivery_address')
    if delivery_address:
        c.drawString(50, y, f"Delivery Address: {delivery_address}")
        y -= 20

    y -= 10

    # ---------- Product & Order Information ----------
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Product & Order Information")
    y -= 25
    c.setFont("Helvetica", 12)

    product_name = order_data.get('product_name')
    if product_name:
        c.drawString(50, y, f"Product Name: {product_name}")
        y -= 20

    category = order_data.get('category')
    if category:
        c.drawString(50, y, f"Category: {category}")
        y -= 20

    quantity = safe_float(order_data.get('quantity'))
    unit = safe_float(order_data.get('unit'))

    if quantity != 0:
        c.drawString(50, y, f"Quantity: {quantity:.2f}")
        y -= 20

    if unit != 0:
        c.drawString(50, y, f"Unit: {unit:.2f}")
        y -= 20
    total_amount = safe_float(order_data.get('total_amount'))
    pass_amount = safe_float(order_data.get('pass_amount'))
    discount = safe_float(order_data.get('discount'))
    final_amount = safe_float(order_data.get('final_amount'))

    c.drawString(50, y, f"Total Amount: {total_amount:.2f}")
    y -= 20
    c.drawString(50, y, f"Pass Amount: {pass_amount:.2f}")
    y -= 20
    c.drawString(50, y, f"Discount: {discount:.2f}")
    y -= 20
    c.drawString(50, y, f"Final Amount: {final_amount:.2f}")
    y -= 20

    # ---------- Payment Information ----------
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Payment Information")
    y -= 25
    c.setFont("Helvetica", 12)

    paid_amount = safe_float(order_data.get('paid_amount'))
    pending_amount = safe_float(order_data.get('pending_amount'))
    payment_method = order_data.get('payment_method', '')
    paid_at = order_data.get('paid_at', '')

    c.drawString(50, y, f"Paid Amount: {paid_amount:.2f}")
    y -= 20
    c.drawString(50, y, f"Pending Amount: {pending_amount:.2f}")
    y -= 20
    if payment_method:
        c.drawString(50, y, f"Payment Method: {payment_method}")
        y -= 20
    if paid_at:
        try:
            dt = datetime.strptime(paid_at, "%Y-%m-%d %H:%M:%S")
            paid_at_str = dt.strftime("%d-%m-%Y %I:%M %p")
        except:
            paid_at_str = paid_at
        c.drawString(50, y, f"Paid At: {paid_at_str}")
        y -= 20

    y -= 10

    # ---------- Delivery Information ----------
    delivery_status = order_data.get('delivery_status', '').lower()
    if delivery_status == 'delivered':
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "Delivery Information")
        y -= 25
        c.setFont("Helvetica", 12)

        delivered_at = order_data.get('delivered_at')
        if delivered_at:
            try:
                dt = datetime.strptime(delivered_at, "%Y-%m-%d %H:%M:%S")
                delivered_at_str = dt.strftime("%d-%m-%Y %I:%M %p")
            except:
                delivered_at_str = delivered_at
            c.drawString(50, y, f"Delivered At: {delivered_at_str}")
            y -= 20

        if delivery_address:
            c.drawString(50, y, f"Delivery Address: {delivery_address}")
            y -= 20

    # ---------- Exported / Generated At ----------
    c.setFont("Helvetica", 10)
    c.drawString(50, 30, f"Exported At: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}")

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.read()



# -----------------------------------tamil invoice------------------
import os
from django.http import HttpResponse, Http404
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .models import Order  # import your Order model

import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Correct path to the font
FONT_PATH = os.path.join(
    os.path.dirname(__file__),  # this is san_app
    "fonts", "Noto_Sans_Tamil", "static", "NotoSansTamil-Regular.ttf"
)

# Register the font
pdfmetrics.registerFont(TTFont("NotoTamil", FONT_PATH))
def order_receipt_pdf(request, order_id):
    try:
        order = Order.objects.select_related("customer", "product").get(pk=order_id)
    except Order.DoesNotExist:
        raise Http404("Order not found")

    # Response setup
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f"attachment; filename=OrderReceipt_{order.order_id}.pdf"

    # PDF builder
    doc = SimpleDocTemplate(response)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Tamil", fontName="NotoTamil", fontSize=12))

    story = []

    # ===== Title =====
    story.append(Paragraph(f"ஆர்டர் ரசீது - #{order.order_id}", styles["Tamil"]))
    story.append(Spacer(1, 12))

    # ===== Customer Info =====
    story.append(Paragraph("வாடிக்கையாளர் தகவல்", styles["Tamil"]))
    story.append(Paragraph(f"பெயர்: {order.customer.name if order.customer else ''}", styles["Tamil"]))
    story.append(Paragraph(f"மொபைல்: {order.customer.mobile if order.customer else ''}", styles["Tamil"]))
    story.append(Paragraph(f"முகவரி: {order.delivery_address or ''}", styles["Tamil"]))
    story.append(Spacer(1, 12))

    # ===== Product Info =====
    story.append(Paragraph("பொருள் & ஆர்டர் விவரம்", styles["Tamil"]))
    story.append(Paragraph(f"பொருள் பெயர்: {order.product.product_name if order.product else ''}", styles["Tamil"]))
    story.append(Paragraph(f"வகை: {order.category}", styles["Tamil"]))
    story.append(Paragraph(f"அளவீட்டு வகை: {order.measurement_type}", styles["Tamil"]))
    story.append(Paragraph(f"அளவு: {order.quantity or '0'}", styles["Tamil"]))
    story.append(Paragraph(f"அலகு: {order.unit or '0'}", styles["Tamil"]))
    story.append(Paragraph(f"மொத்த தொகை: ₹{order.total_amount}", styles["Tamil"]))
    story.append(Paragraph(f"தள்ளுபடி: ₹{order.discount}", styles["Tamil"]))
    story.append(Paragraph(f"இறுதி தொகை: ₹{order.final_amount}", styles["Tamil"]))
    story.append(Paragraph(f"செலுத்திய தொகை: ₹{order.paid_amount}", styles["Tamil"]))
    story.append(Paragraph(f"நிலுவை தொகை: ₹{order.pending_amount}", styles["Tamil"]))
    story.append(Paragraph(f"கட்டணம் நிலை: {order.payment_status}", styles["Tamil"]))
    story.append(Spacer(1, 12))

    # ===== Pass Info =====
    story.append(Paragraph("பாஸ் விவரம்", styles["Tamil"]))
    story.append(Paragraph(f"பாஸ் எண்: {order.pass_no or ''}", styles["Tamil"]))
    story.append(Paragraph(f"ஒரு பாஸ் விலை: ₹{order.amount_per_pass or '0.00'}", styles["Tamil"]))
    story.append(Paragraph(f"பாஸ் தொகை: ₹{order.pass_amount or '0.00'}", styles["Tamil"]))

    # Build PDF
    doc.build(story)
    return response
