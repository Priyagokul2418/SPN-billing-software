from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import User,Customer,Product,Device,Order,Transaction
from .serializers import UserSerializer,CustomerSerializer,ProductSerializer,DeviceSerializer,OrderSerializer,TransactionSerializer,LoginSerializer,ChangePasswordSerializer,ForgotPasswordSerializer,ResetPasswordSerializer
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from .models import Order
from django.utils import timezone
from datetime import timedelta
from .utils import generate_qr_code  
import qrcode
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils.dateparse import parse_date
from reportlab.lib.units import inch



class UserAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            user = get_object_or_404(User, pk=pk)
            serializer = UserSerializer(user)
        else:
            users = User.objects.all()
            serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']

        try:
            user = User.objects.get(username=username)
            if user.password != password:  # plain text password check
                return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # If you want, you can return a token here for authentication
        return Response({
            "id": user.id,
            "name": user.name,
            "username": user.username
        })


class ChangePasswordView(APIView):
    

    def post(self, request, user_id):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(id=user_id)
            if user.password != old_password:
                return Response({"error": "Old password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)
            user.password = new_password
            user.save()
            return Response({"message": "Password changed successfully"})
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

from .utils import send_otp_via_email

class ForgotPasswordView(APIView):
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        otp = user.generate_otp()

        # 🔥 Send OTP via email
        otp = send_otp_via_email(user.username)   # username is email

        # save OTP to user model
        user.otp = otp
        user.otp_created_at = timezone.now()
        user.save()

        return Response({"message": "OTP sent successfully to your email"})
    

class ResetPasswordView(APIView):
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = serializer.validated_data['username']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        if user.otp != otp:
            return Response({"error": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)

        if timezone.now() > user.otp_created_at + timedelta(minutes=10):
            return Response({"error": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Store password as plain text
        user.password = new_password
        user.otp = None
        user.otp_created_at = None
        user.save()

        return Response({"message": "Password reset successfully"}, status=status.HTTP_200_OK)



class CustomerAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            customer = get_object_or_404(Customer, pk=pk)
            serializer = CustomerSerializer(customer)
        else:
            customers = Customer.objects.all()

            # Normal filters
            name = request.query_params.get("name")
            email = request.query_params.get("email")
            phone = request.query_params.get("phone")

            if name:
                customers = customers.filter(name__icontains=name)
            if email:
                customers = customers.filter(email__icontains=email)
            if phone:
                customers = customers.filter(phone__icontains=phone)

            # Date filters
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")

            if start_date:
                start_date = parse_date(start_date)
                if start_date:
                    customers = customers.filter(created_at__date__gte=start_date)

            if end_date:
                end_date = parse_date(end_date)
                if end_date:
                    customers = customers.filter(created_at__date__lte=end_date)

            serializer = CustomerSerializer(customers, many=True)

        return Response(serializer.data)

    def post(self, request):
        serializer = CustomerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        serializer = CustomerSerializer(customer, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        customer.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class ProductAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            product = get_object_or_404(Product, pk=pk)
            serializer = ProductSerializer(product)
        else:
            products = Product.objects.all()
            serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)  

class DeviceAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            device = get_object_or_404(Device, pk=pk)
            serializer = DeviceSerializer(device)
        else:
            devices = Device.objects.all()
            serializer = DeviceSerializer(devices, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = DeviceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        serializer = DeviceSerializer(device, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        device.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    



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


class OrderAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            order = get_object_or_404(Order, pk=pk)
            serializer = OrderSerializer(order)
        else:
            orders = Order.objects.all()
            serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    def post(self, request):
            serializer = OrderSerializer(data=request.data, context={'request': request})
            if serializer.is_valid():
                order = serializer.save()

                # ✅ Generate QR Code
                qr = qrcode.make(f"Order ID: {order.order_id}, Amount: {order.total_amount}")
                qr_filename = f"order_{order.order_id}.png"
                qr_path = os.path.join(settings.MEDIA_ROOT, 'qrcodes', qr_filename)

                # ensure dir exists
                os.makedirs(os.path.dirname(qr_path), exist_ok=True)
                qr.save(qr_path)

                # save path in model if ImageField exists
                if hasattr(order, "qr_code"):
                    order.qr_code.name = f"qrcodes/{qr_filename}"
                    order.save()

                # ✅ Generate Receipt PDF (from utils.py)
                receipt_path = generate_receipt_pdf(order)

                # ✅ Build URLs
                qr_url = request.build_absolute_uri(order.qr_code.url) if hasattr(order, "qr_code") else None
                receipt_url = request.build_absolute_uri(
                    os.path.join(settings.MEDIA_URL, 'receipts', f'order_{order.order_id}.pdf')
                )

                return Response({
                    "order": OrderSerializer(order).data,
                    "qr_url": qr_url,
                    "receipt_url": receipt_url
                }, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderSerializer(order, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()

            # ✅ Update transaction
            transaction = Transaction.objects.filter(order=order).first()
            if transaction:
                discount = order.discount
                transaction.total_amount = order.total_amount - discount
                transaction.paid = order.paid_amount
                transaction.pending = order.pending_amount
                transaction.payment_status = order.payment_status
                transaction.save()

            receipt_path, receipt_url = None, None

            # ✅ Generate QR + Receipt only if order is completed after update
            if order.status.lower() == "completed":
                qr_path = generate_qr_code(order)
                receipt_path = generate_receipt_pdf(order, qr_path)

                receipt_url = request.build_absolute_uri(
                    os.path.join(settings.MEDIA_URL, 'receipts', f'order_{order.order_id}.pdf')
                )

            return Response({
                "order": OrderSerializer(order).data,
                "receipt_path": receipt_path,
                "receipt_url": receipt_url
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        Transaction.objects.filter(order=order).delete()
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class OrderReceiptDownloadView(APIView):
    """View to download order receipt as PDF"""
    def get(self, request, order_id):
        # Get order or return 404
        order = get_object_or_404(Order, order_id=order_id)
        
        # Generate PDF
        pdf_path = generate_receipt_pdf(order)
        
        # Return PDF as download response
        with open(pdf_path, 'rb') as pdf_file:
            response = HttpResponse(pdf_file.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename=GatePass_Receipt_{order.order_id}.pdf'
            return response
    
class TransactionAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            transaction = get_object_or_404(Transaction, pk=pk)
            serializer = TransactionSerializer(transaction)
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Base queryset
        transactions = Transaction.objects.all()

        # ---- Filters ----
        filter_type = request.query_params.get("filter")   # week/month/year
        specific_date = request.query_params.get("date")   # YYYY-MM-DD
        start_date = request.query_params.get("start_date")  # YYYY-MM-DD
        end_date = request.query_params.get("end_date")      # YYYY-MM-DD

        today = now().date()

        # Weekly filter
        if filter_type == "week":
            start = today - timedelta(days=today.weekday())  # Monday
            end = start + timedelta(days=6)                  # Sunday
            transactions = transactions.filter(created_at__date__range=[start, end])

        # Monthly filter
        elif filter_type == "month":
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            transactions = transactions.filter(created_at__date__range=[start, end])

        # Yearly filter
        elif filter_type == "year":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
            transactions = transactions.filter(created_at__date__range=[start, end])

        # Specific date filter
        if specific_date:
            date_obj = parse_date(specific_date)
            if date_obj:
                transactions = transactions.filter(created_at__date=date_obj)

        # Range filter
        if start_date and end_date:
            start_obj = parse_date(start_date)
            end_obj = parse_date(end_date)
            if start_obj and end_obj:
                transactions = transactions.filter(created_at__date__range=[start_obj, end_obj])

        # Serialize
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = TransactionSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            transaction = serializer.save()
            return Response(TransactionSerializer(transaction).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        serializer = TransactionSerializer(transaction, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            transaction = serializer.save()
            return Response(TransactionSerializer(transaction).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        transaction = get_object_or_404(Transaction, pk=pk)
        transaction.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

from .serializers import OrderHistorySerializer


class CustomerOrderHistoryAPIView(APIView):
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({"message": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        orders = Order.objects.filter(customer=customer).order_by("-created_at")
        serializer = OrderHistorySerializer(orders, many=True)
        return Response({
            "customer_id": customer.id,
            "customer_name": customer.name,
            "mobile": customer.mobile,
            "email": customer.email,
            "order_history": serializer.data
        }, status=status.HTTP_200_OK)



class CustomerTransactionHistoryAPIView(APIView):
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        transactions = Transaction.objects.filter(customer=customer).order_by("-created_at")
        serializer = TransactionSerializer(transactions, many=True)
        return Response({
            "customer": customer.name,
            "transaction_history": serializer.data
        }, status=status.HTTP_200_OK)

class CustomerReportAPIView(APIView):
    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)

        # serialize customer
        customer_data = CustomerSerializer(customer).data

        # get orders & transactions
        orders = Order.objects.filter(customer=customer)
        transactions = Transaction.objects.filter(customer=customer)

        orders_data = OrderSerializer(orders, many=True).data
        transactions_data = TransactionSerializer(transactions, many=True).data

        response_data = {
            "customer": customer_data,
            "orders": orders_data,
            "transactions": transactions_data
        }

        return Response(response_data)


import csv
from django.http import HttpResponse
import csv
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

class CustomerReportDownloadAPIView(APIView):
    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        orders = Order.objects.filter(customer=customer)
        transactions = Transaction.objects.filter(customer=customer)

        # PDF response
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="customer_{pk}_report.pdf"'

        doc = SimpleDocTemplate(response, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()

        # Title
        elements.append(Paragraph(f"Customer Report - {customer.name}", styles['Title']))
        elements.append(Spacer(1, 12))

        # ---------------- Customer Details ----------------
        elements.append(Paragraph("Customer Details", styles['Heading2']))
        customer_data = [
            ["ID", customer.id],
            ["Name", customer.name],
            ["Age", customer.age],
            ["Mobile", customer.mobile],
            ["Gender", customer.gender],
            ["Email", customer.email],
            ["Address", customer.address],
            ["City", customer.city],
            ["Business Name", customer.Business_name],
            ["Customer Type", customer.customer_type],
            ["Pincode", customer.pincode],
            ["Credit Limit", str(customer.credit_limit)],
            ["Created At", customer.created_at.strftime("%Y-%m-%d %H:%M:%S") if customer.created_at else ""],
        ]
        customer_table = Table(customer_data, hAlign="LEFT")
        customer_table.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.5, colors.grey)]))
        elements.append(customer_table)
        elements.append(Spacer(1, 20))

# ---------------- Orders ----------------
        elements.append(Paragraph("Order History", styles['Heading2']))

        order_data = [[
            "Order ID (Date)", "Product", "Quantity/Unit",
            "Total Amount", "Paid Amount", "Pending", "Status"
        ]]

        total_orders = orders.count()
        total_amount = 0
        total_paid = 0
        total_pending = 0

        for o in orders:
            # Quantity / Unit
            qty_or_unit = str(o.quantity) if o.measurement_type == 'Quantity' else str(o.unit)

            # Accumulate totals
            total_amount += float(o.total_amount)
            total_paid += float(o.paid_amount)
            total_pending += float(o.pending_amount)

            # Status: Delivery + Payment
            status = f"Delivery: {o.delivery_status}\nPayment: {o.payment_status}"

            order_data.append([
                f"{o.order_id} ({o.created_at.strftime('%d-%m-%y')})",
                str(o.product),
                qty_or_unit,
                f"{o.total_amount:.2f}",
                f"{o.paid_amount:.2f}",
                f"{o.pending_amount:.2f}",
                status
            ])

        order_table = Table(order_data, repeatRows=1, hAlign="LEFT")
        order_table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.5, colors.black),
            ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
        ]))
        elements.append(order_table)
        elements.append(Spacer(1, 12))

        # ---------------- Orders Summary ----------------
        summary_data = [
            ["Total Orders:", f"{total_orders}"],
            ["Total Amount:", f"{total_amount:.2f}"],
            ["Paid Amount:", f"{total_paid:.2f}"],
            ["Pending Amount:", f"{total_pending:.2f}"]
        ]

        summary_table = Table(summary_data, colWidths=[2*inch, 1*inch], hAlign="RIGHT")
        summary_table.setStyle(TableStyle([
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ALIGN", (0,0), (-1,-1), "RIGHT"),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
                   # Build PDF
        try:
            doc.build(elements)
        except Exception as e:
            return Response({"error": f"Failed to generate PDF: {str(e)}"}, status=500)

        return response




# views.py
from django.db.models import Sum, Q
from rest_framework.views import APIView
from rest_framework.response import Response
from datetime import date, timedelta
from .models import Order, Transaction

class ReportAPIView(APIView):
    def get(self, request):
        orders = Order.objects.all()
        transactions = Transaction.objects.all()

        # --- Filters ---
        product_name = request.query_params.get("product_name")
        category = request.query_params.get("category")
        delivery_status = request.query_params.get("delivery_status")
        timeline = request.query_params.get("timeline")   # today, week, month
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # filter by product name
        if product_name:
            orders = orders.filter(product__name__icontains=product_name)

        # filter by category
        if category:
            orders = orders.filter(product__category__icontains=category)

        # filter by delivery status
        if delivery_status:
            orders = orders.filter(delivery_status=delivery_status)

        # timeline filter
        today = date.today()
        if timeline == "today":
            orders = orders.filter(order_date=today)
        elif timeline == "week":
            start_week = today - timedelta(days=today.weekday())
            orders = orders.filter(order_date__gte=start_week)
        elif timeline == "month":
            orders = orders.filter(order_date__month=today.month, order_date__year=today.year)

        # custom date range
        if start_date and end_date:
            orders = orders.filter(order_date__range=[start_date, end_date])

        # --- Aggregations ---
        total_orders = orders.count()
        total_amount = orders.aggregate(total=Sum("total_amount"))["total"] or 0
        paid_amount = transactions.filter(order__in=orders).aggregate(paid=Sum("amount_paid"))["paid"] or 0
        pending_amount = total_amount - paid_amount
        total_quantity = orders.aggregate(qty=Sum("quantity"))["qty"] or 0

        data = {
            "total_orders": total_orders,
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "pending_amount": pending_amount,
            "total_quantity": total_quantity,
        }

        return Response(data)



from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Sum, Count
from datetime import datetime, timedelta, date
from .models import Order, Transaction

# -------------------------------
# Orders Report
# -------------------------------
class OrdersReportView(APIView):
    def get(self, request):
        orders = Order.objects.all()

        # Filters
        product_name = request.query_params.get("product")
        category = request.query_params.get("category")
        delivery_status = request.query_params.get("status")  # renamed
        timeline = request.query_params.get("timeline")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        # Filter by product name
        if product_name:
            orders = orders.filter(product__product_name__icontains=product_name)
        # Filter by category
        if category:
            orders = orders.filter(product__category__icontains=category)
        # Filter by delivery status
        if delivery_status:
            orders = orders.filter(delivery_status__iexact=delivery_status)

        # Timeline filter
        today = date.today()
        if timeline == "today":
            orders = orders.filter(created_at__date=today)
        elif timeline == "week":
            start_week = today - timedelta(days=today.weekday())
            orders = orders.filter(created_at__date__gte=start_week)
        elif timeline == "month":
            orders = orders.filter(created_at__month=today.month, created_at__year=today.year)

        # Custom date range
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                orders = orders.filter(created_at__date__range=[start, end])
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        # Aggregations
        total_orders = orders.count()
        delivered_orders = orders.filter(delivery_status="Delivered").count()
        pending_orders = orders.filter(delivery_status="Pending").count()
        cancelled_orders = orders.filter(delivery_status="Cancelled").count()
        total_quantity = orders.aggregate(total_qty=Sum("quantity"))["total_qty"] or 0

        data = {
            "total_orders": total_orders,
            "delivered_orders": delivered_orders,
            "pending_orders": pending_orders,
            "cancelled_orders": cancelled_orders,
            "total_quantity": total_quantity,
            "filters": {
                "product_name": product_name,
                "category": category,
                "status": delivery_status,
                "timeline": timeline,
                "start_date": start_date,
                "end_date": end_date
            }
        }
        
        return Response(data, status=status.HTTP_200_OK)


# -------------------------------
# Transactions Report
# -------------------------------
class TransactionsReportView(APIView):
    def get(self, request):
        transactions = Transaction.objects.all()

        # Timeline filter
        timeline = request.query_params.get("timeline")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        today = date.today()
        if timeline == "today":
            transactions = transactions.filter(created_at__date=today)
        elif timeline == "week":
            start_week = today - timedelta(days=today.weekday())
            transactions = transactions.filter(created_at__date__gte=start_week)
        elif timeline == "month":
            transactions = transactions.filter(created_at__month=today.month, created_at__year=today.year)

        # Custom date range
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                transactions = transactions.filter(created_at__date__range=[start, end])
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

        # Aggregations
        total_amount = transactions.aggregate(total=Sum("total_amount"))["total"] or 0
        paid_amount = transactions.aggregate(paid=Sum("paid_amount"))["paid"] or 0
        pending_amount = total_amount - paid_amount

        data = {
            "total_amount": total_amount,
            "paid_amount": paid_amount,
            "pending_amount": pending_amount,
            "filters": {
                "timeline": timeline,
                "start_date": start_date,
                "end_date": end_date
            }
        }
        return Response(data, status=status.HTTP_200_OK)


class RecentOrdersAPIView(APIView):
    def get(self, request):
        limit = int(request.query_params.get("limit", 20))  # default 5 orders
        recent_orders = Order.objects.order_by("-created_at")[:limit]
        serializer = OrderSerializer(recent_orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



# # views.py
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from django.shortcuts import get_object_or_404
# from .models import Order, ScanLog

# class QRScanAPIView(APIView):
#     """
#     QR scan endpoint: marks delivered, logs scan, returns full order details
#     """
#     def get(self, request, order_id):
#         device_info = request.META.get("HTTP_USER_AGENT", "Unknown")
#         ip_address = request.META.get("REMOTE_ADDR", "")
#         location = "Unknown"

#         # Try to get location via IP API
#         try:
#             import requests
#             res = requests.get(f"http://ip-api.com/json/{ip_address}").json()
#             if res.get("status") == "success":
#                 location = f"{res.get('city')}, {res.get('regionName')}, {res.get('country')}"
#         except:
#             pass

#         order = get_object_or_404(Order, order_id=order_id)

#         # ✅ Update delivery status
#         order.delivery_status = "Delivered"
#         order.delivered_at = now()
#         order.save(update_fields=["delivery_status", "delivered_at"])

#         # ✅ Save Scan Log
#         ScanLog.objects.create(
#             order=order,
#             device_id=device_info,
#             location=location
#         )

#         serializer = OrderSerializer(order)
#         return Response(serializer.data)

# from django.http import JsonResponse
# from django.utils.timezone import now
# import requests


# @api_view(['GET'])
# def scan_order(request):
#     order_id = request.GET.get('order_id')
#     order = get_object_or_404(Order, id=order_id)

#     # Order status update
#     order.status = "Delivered"
#     order.save()

#     # Response
#     return Response({
#         "message": "Order delivered successfully",
#         "order_id": order.id,
#         "customer": order.customer.name,
#         "amount": order.total_amount,
#         "status": order.status
#     })


from io import BytesIO
from django.core.files import File
import qrcode
from django.shortcuts import render, get_object_or_404
from django.utils.timezone import now
from .models import Order

def scan_auto(request):
    order_id = request.GET.get("order_id")
    order = get_object_or_404(Order, order_id=order_id)

    # Just render the mobile-friendly page
    return render(request, "scan_success.html", {"order": order})


from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from .models import Order
from .serializers import OrderSerializer

class ScanOrderAPIView(APIView):
    def get(self, request):
        order_id = request.GET.get("order_id")
        print("✅ Scan API called with order_id:", order_id)

        order = get_object_or_404(Order, order_id=order_id)

        if order.delivery_status != "Delivered":
            order.delivery_status = "Delivered"
            order.delivered_at = now()
            order.save(update_fields=["delivery_status", "delivered_at"])

        serializer = OrderSerializer(order)
        return Response({
            "scanned_url": request.build_absolute_uri(),
            "order": serializer.data
        })
