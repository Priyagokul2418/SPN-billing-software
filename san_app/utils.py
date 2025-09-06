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


def generate_receipt_pdf(order):
    """Generate PDF receipt for an order in Tamil"""
    # Create receipts directory if not exists
    receipts_dir = os.path.join(settings.MEDIA_ROOT, 'receipts')
    os.makedirs(receipts_dir, exist_ok=True)
    
    # PDF file path
    file_path = os.path.join(receipts_dir, f'order_{order.order_id}.pdf')
    
    # Create PDF canvas
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    
    # ===== RECEIPT HEADER =====
    # Shop name (Tamil)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width/2, height-20*mm, "கேட் பாஸ் மரக்கடை")
    c.setFont("Helvetica", 12)
    c.drawCentredString(width/2, height-28*mm, "வாடிக்கையாளர் ரசீது")
    
    # ===== CUSTOMER DETAILS =====
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20*mm, height-45*mm, "வாடிக்கையாளர் விவரங்கள்:")
    c.setFont("Helvetica", 11)
    
    y_position = height-55*mm
    details = [
        f"பெயர்: {order.customer.name}",
        f"முகவரி: {order.delivery_address}",
        f"தொலைபேசி: {order.contact_no}",
        f"ஆர்டர் எண்: {order.order_id}",
        f"தேதி: {order.created_at.strftime('%d-%m-%Y %H:%M')}"
    ]
    
    for detail in details:
        c.drawString(25*mm, y_position, detail)
        y_position -= 8*mm
    
    # ===== ORDER DETAILS =====
    y_position -= 5*mm  # Add some space
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20*mm, y_position, "ஆர்டர் விவரங்கள்:")
    y_position -= 10*mm
    
    # Product details
    c.setFont("Helvetica", 11)
    c.drawString(25*mm, y_position, f"பொருள்: {order.product}")
    y_position -= 8*mm
    c.drawString(25*mm, y_position, f"வகை: {order.category}")
    y_position -= 8*mm
    
    # Quantity/Unit with calculation
    if order.measurement_type == 'Quantity':
        item_line = f"அளவு: {order.quantity} x ₹{order.product.price} = ₹{order.quantity * order.product.price}"
    else:
        item_line = f"அளவு: {order.unit} x ₹{order.product.price} = ₹{float(order.unit) * float(order.product.price)}"
    
    c.drawString(25*mm, y_position, item_line)
    y_position -= 15*mm
    
    # ===== PAYMENT DETAILS =====
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20*mm, y_position, "கட்டண விவரங்கள்:")
    y_position -= 10*mm
    
    c.setFont("Helvetica", 11)
    payment_details = [
        f"மொத்த தொகை: ₹{order.total_amount}",
        f"தள்ளுபடி: ₹{order.discount}" if order.discount > 0 else None,
        f"செலுத்திய தொகை: ₹{order.paid_amount}",
        f"நிலுவை தொகை: ₹{order.pending_amount}",
        f"கட்டண முறை: {order.get_payment_method_display()}"
    ]
    
    for detail in payment_details:
        if detail:  # Skip None values (like when no discount)
            c.drawString(25*mm, y_position, detail)
            y_position -= 8*mm
    
    # ===== QR CODE =====
    if order.qr_code:
        try:
            qr_path = order.qr_code.path
            if os.path.exists(qr_path):
                # Position QR code at bottom right
                qr_size = 35*mm
                qr_x = width - 20*mm - qr_size
                qr_y = 20*mm
                c.drawImage(qr_path, qr_x, qr_y, qr_size, qr_size)
                
                # Add text below QR code
                c.setFont("Helvetica", 8)
                c.drawCentredString(width - 20*mm - qr_size/2, 15*mm, "ஸ்கேன் செய்யவும்")
        except:
            pass
    
    # ===== FOOTER =====
    c.setFont("Helvetica-Oblique", 9)
    c.drawCentredString(width/2, 10*mm, "நன்றி! மீண்டும் வருக!")
    
    # Save PDF
    c.showPage()
    c.save()
    
    return file_path




def generate_receipt_pdf(order):
    file_path = f"media/receipts/order_{order.order_id}.pdf"
    doc = SimpleDocTemplate(file_path, pagesize=(80*mm, 200*mm))
    styles = getSampleStyleSheet()
    styles["Normal"].fontName = "TamilFont"

    elements = []

    # Header
    elements.append(Paragraph("<b>வரிசிமனசாமியைச் சேமிப்பு பண்ணை</b>", styles["Normal"]))
    elements.append(Paragraph("ஆசிரமம், ஒண்ணாமலை - 627859", styles["Normal"]))
    elements.append(Spacer(1, 10))

    # Customer Info
    customer_table = Table([
        ["வாடிக்கையாளர் பெயர்:", order.customer.name],
        ["முகவரி:", order.delivery_address],
        ["தொலைபேசி:", order.customer.mobile],
    ], colWidths=[80, 200])
    customer_table.setStyle(TableStyle([
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("FONTNAME", (0,0), (-1,-1), "TamilFont"),
    ]))
    elements.append(customer_table)
    elements.append(Spacer(1, 10))

    # Item Info
    item_table = Table([
        ["பொருள்", "அளவு", "விலை"],
        [order.product.product_name, order.quantity or order.unit, f"₹{order.total_amount}"]
    ])
    item_table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("FONTNAME", (0,0), (-1,-1), "TamilFont"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
    ]))
    elements.append(item_table)

    # Save PDF
    doc.build(elements)
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
        qr_content = f"http://10.205.166.96:8000/scan_auto/?order_id={order_instance.order_id}"

    # ✅ Debug print
    print("🔍 QR CONTENT:", qr_content)

    qr = qrcode.make(qr_content)

    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)

    filename = f"order_{order_instance.order_id}.png"
    order_instance.qr_code.save(filename, File(buffer), save=True)

    return qr_content

