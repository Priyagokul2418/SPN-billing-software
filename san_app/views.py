from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import User,Customer,Product,Device,Order,Transaction,ScanLog
from .serializers import UserSerializer,CustomerSerializer,ProductSerializer,DeviceSerializer,OrderSerializer,TransactionSerializer,LoginSerializer,ChangePasswordSerializer,ForgotPasswordSerializer,ResetPasswordSerializer,OrderReceiptSerializer,OrderHistorySerializer,DeviceLoginSerializer, DeviceSerializer,ScanLogSerializer
from django.conf import settings
from django.shortcuts import render
from django.db.models import Sum, Q,Count
from datetime import date, timedelta
from django.utils.dateparse import parse_date

from decimal import Decimal
from django.db import transaction as db_transaction



from reportlab.pdfbase import pdfmetrics
# from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from io import BytesIO
from django.db import transaction
from django.http import HttpResponse

from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from django.utils.timezone import now

from django.utils import timezone
from datetime import timedelta
from .utils import generate_qr_code  

from .utils import send_otp_via_email
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from rest_framework.test import APIRequestFactory

import os
import datetime
import qrcode

font_path = os.path.join(settings.BASE_DIR, "fonts", "DejaVuSans.ttf")



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
        otp = send_otp_via_email(user.username)

       
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

    
        user.password = new_password
        user.otp = None
        user.otp_created_at = None
        user.save()

        return Response({"message": "Password reset successfully"}, status=status.HTTP_200_OK)


# ------------------------------customer API view-------------------------------------------
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

            # ✅ Order latest first
            customers = customers.order_by("-created_at")

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
    











#  -------------------------product API view-------------------------------------------------------------
class ProductAPIView(APIView):


    # def get(self, request, pk=None):
    #     if pk:
    #         product = get_object_or_404(Product, pk=pk)
    #         serializer = ProductSerializer(product)
    #         return Response(serializer.data)

    #     products = Product.objects.all().order_by("-id")

    #     # --- Filter by product_name and get its categories ---
    #     product_name = request.query_params.get('product')
    #     if product_name:
    #         # Filter products whose name contains the given string (case-insensitive)
    #         filtered_products = products.filter(product_name__icontains=product_name)

    #         # Get unique categories for these products
    #         categories = filtered_products.values_list('category', flat=True).distinct()
    #         return Response({
    #             "product_name": product_name,
    #             "categories": list(categories)
    #         })

    #     # --- Optional: filter by category only ---
    #     category = request.query_params.get('category')
    #     if category:
    #         products = products.filter(category=category)

    #     serializer = ProductSerializer(products, many=True)
    #     return Response(serializer.data)



    def get(self, request, pk=None):
        if pk:
            product = get_object_or_404(Product, pk=pk)
            serializer = ProductSerializer(product)
            return Response(serializer.data)

        products = Product.objects.all().order_by("-id")

        # --- If query param 'productnames' is given, return distinct product names only ---
        productnames = request.query_params.get('productnames')
        if productnames is not None:
            distinct_names = products.values_list('product_name', flat=True).distinct().order_by('product_name')
            return Response({
                "product_names": list(distinct_names)
            })

        # --- If specific product name + category given => return full details ---
        product_name = request.query_params.get('product')
        category = request.query_params.get('category')
        if product_name and category:
            products = products.filter(product_name__iexact=product_name, category__iexact=category)
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data)

        # --- If only product name is given => return its categories ---
        if product_name:
            filtered_products = products.filter(product_name__iexact=product_name)
            categories = filtered_products.values_list('category', flat=True).distinct()
            return Response({
                "product_name": product_name,
                "categories": list(categories)
            })

        # --- Optional: filter by category only ---
        if category:
            products = products.filter(category=category)

        # --- Return full product details ---
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
    









# --------------------------Device API view--------------------------------------
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


# -----------------------Device Login view-----------------------

class DeviceLoginView(APIView):
    def post(self, request):
        serializer = DeviceLoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data["username"]
            password = serializer.validated_data["password"]
            device_id = serializer.validated_data.get("device_id")
            id_verify = serializer.validated_data.get("id_verify", False)

            if isinstance(id_verify, str):
                id_verify = id_verify.lower() == "true"

            try:
                device = Device.objects.get(username=username)
            except Device.DoesNotExist:
                return Response({"error": "Invalid username"}, status=status.HTTP_400_BAD_REQUEST)

            if device.password != password:
                return Response({"error": "Invalid password"}, status=status.HTTP_400_BAD_REQUEST)

            if id_verify: 
                if not device_id or device.device_id != device_id:
                    return Response({"error": "Invalid device ID"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({
                "message": "Login successful",
                "device": DeviceSerializer(device).data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Register only the stable Tamil font once (no variable fonts)
# font_path = r"C:\projects\SAN_project\san_app\fonts\Noto_Sans_Tamil\static\NotoSansTamil-Regular.ttf"
# pdfmetrics.registerFont(TTFont("NotoSansTamil", font_path))

# # Register DejaVuSans (if you want it, otherwise remove)
# dejavu_path = os.path.join(os.path.dirname(font_path), "..", "DejaVuSans.ttf")
# if os.path.exists(dejavu_path):
#     pdfmetrics.registerFont(TTFont("DejaVuSans", dejavu_path))

# class ReceiptPDFView(APIView):
#     def get(self, request, order_id, *args, **kwargs):
#         order = Order.objects.get(order_id=order_id)
#         qr_content = generate_qr_code(order, request)

#         response = HttpResponse(content_type="application/pdf")
#         response["Content-Disposition"] = f'inline; filename="order_{order.order_id}.pdf"'

#         buffer = BytesIO()
#         RECEIPT_WIDTH, RECEIPT_HEIGHT = 226, 400
#         p = canvas.Canvas(buffer, pagesize=(RECEIPT_WIDTH, RECEIPT_HEIGHT))

#         width, height = RECEIPT_WIDTH, RECEIPT_HEIGHT
#         y = height - 30

#         # Draw Tamil headers with font explicitly set
#         p.setFont("NotoSansTamil", 12)
#         p.drawCentredString(width / 2, y, "கேட் பாஸ்")  # Gate Pass in Tamil
#         y -= 20

#         p.setFont("NotoSansTamil", 10)
#         p.drawCentredString(width / 2, y, "வாடிக்கையாளர் ரசீது")  # Customer Receipt
#         y -= 30

#         p.setFont("NotoSansTamil", 8)

#         def line(label, value):
#             nonlocal y
#             p.setFont("NotoSansTamil", 8)  # Always set Tamil font before drawing
#             p.drawString(20, y, f"{label}:")
#             p.drawRightString(width - 20, y, str(value))
#             y -= 12

#         # Draw order details lines
#         line("கட்டண வகை", order.payment_method)
#         line("வாடிக்கையாளர் பெயர்", order.customer.name)
#         line("நகரம்", order.customer.city if hasattr(order.customer, "city") else "-")
#         line("பொருள்", order.product.product_name)
#         line("வகை", order.category)
#         line("அளவு", order.quantity or order.unit)
#         line("மொத்தம்", f"₹{order.total_amount}")
#         line("செலுத்தியது", f"₹{order.paid_amount}")
#         line("நிலுவை", f"₹{order.pending_amount}")
#         line("கட்டண நிலை", order.payment_status)
#         line("ஆபரேட்டர்", order.created_by.username if order.created_by else "Admin")

#         if order.qr_code:
#             p.drawInlineImage(order.qr_code.path, width / 2 - 40, y - 100, 80, 80)
#             y -= 110

#         # Set Tamil font before final string
#         p.setFont("NotoSansTamil", 8)
#         p.drawString(20, y, "மேலாளர் கையொப்பம்")  # Manager Sign

#         p.showPage()
#         p.save()
#         pdf = buffer.getvalue()
#         buffer.close()
#         response.write(pdf)

#         return response



# class ReceiptPDFView(APIView):
#     def get(self, request, order_id, *args, **kwargs):
#         order = Order.objects.get(order_id=order_id)
#         qr_content = generate_qr_code(order, request)

#         response = HttpResponse(content_type="application/pdf")
#         response["Content-Disposition"] = f'inline; filename="order_{order.order_id}.pdf"'

#         buffer = BytesIO()
#         RECEIPT_WIDTH, RECEIPT_HEIGHT = 226, 400
#         p = canvas.Canvas(buffer, pagesize=(RECEIPT_WIDTH, RECEIPT_HEIGHT))

#         width, height = RECEIPT_WIDTH, RECEIPT_HEIGHT
#         y = height - 30

#         # Draw English headers
#         p.setFont("Helvetica-Bold", 12)
#         p.drawCentredString(width / 2, y, "GATE PASS")
#         y -= 20

#         p.setFont("Helvetica", 10)
#         p.drawCentredString(width / 2, y, "CUSTOMER RECEIPT")
#         y -= 30

#         p.setFont("Helvetica", 8)

#         def line(label, value):
#             nonlocal y
#             p.setFont("Helvetica", 8)
#             p.drawString(20, y, f"{label}:")
#             p.drawRightString(width - 20, y, str(value))
#             y -= 12

#         # Draw order details lines in English
#         line("Payment Method", order.payment_method)
#         line("Customer Name", order.customer.name)
#         line("City", order.customer.city if hasattr(order.customer, "city") else "-")
#         line("Product", order.product.product_name)
#         line("Category", order.category)
#         line("Quantity/Unit", order.quantity or order.unit)
#         line("Total", f"{order.total_amount}")
#         line("Paid", f"{order.paid_amount}")
#         line("Pending", f"{order.pending_amount}")
#         line("Payment Status", order.payment_status)
#         line("Operator", order.created_by.username if order.created_by else "Admin")

#         if order.qr_code:
#             p.drawInlineImage(order.qr_code.path, width / 2 - 40, y - 100, 80, 80)
#             y -= 110

#         p.setFont("Helvetica", 8)
#         p.drawString(20, y, "Manager Sign")

#         p.showPage()
#         p.save()
#         pdf = buffer.getvalue()
#         buffer.close()
#         response.write(pdf)

#         return response




# class ReceiptPDFView(APIView):

#     def get(self, request, order_id, *args, **kwargs):
#         # 🔹 Fetch order instance
#         order = Order.objects.get(order_id=order_id)

#         # 🔹 Generate QR (this will also save to order.qr_code field)
#         qr_content = generate_qr_code(order, request)

#         # 🔹 Start PDF response
#         response = HttpResponse(content_type="application/pdf")
#         response["Content-Disposition"] = f'inline; filename="order_{order.order_id}.pdf"'

#         buffer = BytesIO()

#         # ✅ Receipt size instead of A4 (80mm width, ~200mm height)
#         RECEIPT_WIDTH = 226   # ~80mm
#         RECEIPT_HEIGHT = 400  # you can adjust if content bigger
#         p = canvas.Canvas(buffer, pagesize=(RECEIPT_WIDTH, RECEIPT_HEIGHT))

#         width, height = (RECEIPT_WIDTH, RECEIPT_HEIGHT)
#         y = height - 30  # top margin

#         # Title
#         p.setFont("DejaVuSans", 12)
#         p.drawCentredString(width/2, y, "Gate Pass")
#         y -= 20
#         p.setFont("DejaVuSans", 10)
#         p.drawCentredString(width/2, y, "Customer Receipt")

#         y -= 30
#         p.setFont("DejaVuSans", 8)

#         # Print order details
#         def line(label, value):
#             nonlocal y
#             p.drawString(20, y, f"{label}:")
#             p.drawRightString(width - 20, y, str(value))
#             y -= 12

#         line("Payment Type", order.payment_method)
#         line("Customer Name", order.customer.name)
#         line("City", order.customer.city if hasattr(order.customer, "city") else "-")
#         line("Product", order.product.product_name)
#         line("Category", order.category)
#         line("Quantity", order.quantity or order.unit)
#         line("Amount", f"₹{order.total_amount}")
#         line("Paid", f"₹{order.paid_amount}")
#         line("Pending", f"₹{order.pending_amount}")
#         line("Payment Status", order.payment_status)
#         line("Operator", order.created_by.username if order.created_by else "Admin")

#         # 🔹 Insert QR code image saved in model
#         if order.qr_code:
#             p.drawInlineImage(order.qr_code.path, width/2 - 40, y-100, 80, 80)
#             y -= 110

#         # Footer
#         p.drawString(20, y, "Manager Sign")

#         p.showPage()
#         p.save()
#         pdf = buffer.getvalue()
#         buffer.close()
#         response.write(pdf)
#         return response

from django.core.serializers.json import DjangoJSONEncoder

class OrderAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            order = get_object_or_404(Order, pk=pk)
            serializer = OrderSerializer(order)
        else:
            # ✅ Latest orders first by created_at
            orders = Order.objects.all().order_by("-created_at")
            serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    def post(self, request):
        serializer = OrderSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()

            # ✅ Generate QR Code
            qr_content = generate_qr_code(order, request)
            qr_url = request.build_absolute_uri(order.qr_code.url) if hasattr(order, "qr_code") else None

            # ✅ Call ReceiptDataView internally (JSON response)
            factory = APIRequestFactory()
            pdf_request = factory.get(f"/api/receipt/{order.order_id}/")
            pdf_request.user = request.user
            view = ReceiptDataView.as_view()
            pdf_response = view(pdf_request, order_id=order.order_id)

            # ✅ Save JSON as file (not real PDF)
            receipt_path = os.path.join(settings.MEDIA_ROOT, 'receipts', f'order_{order.order_id}.json')
            os.makedirs(os.path.dirname(receipt_path), exist_ok=True)
           
            with open(receipt_path, 'w', encoding="utf-8") as f:
                import json
                json.dump(pdf_response.data, f, indent=4, ensure_ascii=False, cls=DjangoJSONEncoder)

            receipt_url = request.build_absolute_uri(
                os.path.join(settings.MEDIA_URL, 'receipts', f'order_{order.order_id}.json')
            )

            return Response({
                "order": OrderSerializer(order).data,
                "qr_url": qr_url,
                "receipt_url": receipt_url,
                "encoded_api_url": qr_content
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        order = get_object_or_404(Order, pk=pk)
        serializer = OrderSerializer(order, data=request.data, partial=True, context={'request': request})

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            order = serializer.save()

            # Update related transaction
            transaction_obj = Transaction.objects.filter(order=order).first()
            if transaction_obj:
                transaction_obj.total_amount = (order.total_amount or 0) - (order.discount or 0)
                transaction_obj.paid = order.paid_amount or 0
                transaction_obj.pending = order.pending_amount or 0
                transaction_obj.payment_status = getattr(order, 'payment_status', '')
                transaction_obj.save()

            receipt_path = None
            receipt_url = None

            # Check order status safely
            order_status = getattr(order, 'order_status', '')  # use the actual model field
            if order_status.lower() == "delivered":
                qr_path = generate_qr_code(order)

                # Call ReceiptPDFView internally
                factory = APIRequestFactory()
                pdf_request = factory.get(f"/api/receipt/{order.order_id}/")
                pdf_request.user = request.user
                view = ReceiptDataView.as_view()
                pdf_response = view(pdf_request, order_id=order.order_id)

                receipt_dir = os.path.join(settings.MEDIA_ROOT, 'receipts')
                os.makedirs(receipt_dir, exist_ok=True)

                receipt_path = os.path.join(receipt_dir, f'order_{order.order_id}.pdf')
                with open(receipt_path, 'wb') as f:
                    f.write(pdf_response.content)

                receipt_url = request.build_absolute_uri(
                    os.path.join(settings.MEDIA_URL, 'receipts', f'order_{order.order_id}.pdf')
                )

        return Response({
            "order": serializer.data,
            "receipt_path": receipt_path,
            "receipt_url": receipt_url
        }, status=status.HTTP_200_OK)
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
import datetime

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
            transactions = transactions.filter(paid_at__date__range=[start, end])

        # Monthly filter
        elif filter_type == "month":
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            transactions = transactions.filter(paid_at__date__range=[start, end])

        # Yearly filter
        elif filter_type == "year":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
            transactions = transactions.filter(paid_at__date__range=[start, end])

        # Specific date filter
        if specific_date:
            date_obj = parse_date(specific_date)
            if date_obj:
                transactions = transactions.filter(paid_at__date=date_obj)

        # Range filter
        if start_date and end_date:
            start_obj = parse_date(start_date)
            end_obj = parse_date(end_date)
            if start_obj and end_obj:
                transactions = transactions.filter(paid_at__date__range=[start_obj, end_obj])

        # ✅ Order by latest first
        transactions = transactions.order_by("-paid_at")

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
    

class CustomerOrderHistoryAPIView(APIView):
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({"message": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

                # Get query params
        # Get query params
        filter_type = request.query_params.get("filter_type", None)  # e.g., filter_type=date
        date_value = request.query_params.get("date", None)
        start_date = request.query_params.get("start_date", None)
        end_date = request.query_params.get("end_date", None)
        timeline = request.query_params.get("timeline", None)

        # Base queryset
        orders = Order.objects.filter(customer=customer).order_by("-created_at")

        # Filter by created_at for a specific date
        if filter_type == "date" and date_value:
            orders = orders.filter(created_at__date=date_value)

        # Filter by created_at date range
        if start_date and end_date:
            orders = orders.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

        # Filter by timeline
        today = date.today()
        if timeline == "today":
            orders = orders.filter(created_at__date=today)
        elif timeline == "week":
            start_week = today - timedelta(days=today.weekday())
            orders = orders.filter(created_at__date__gte=start_week)
        elif timeline == "month":
            start_month = today.replace(day=1)
            orders = orders.filter(created_at__date__gte=start_month)
        elif timeline == "year":
            start_year = today.replace(month=1, day=1)
            orders = orders.filter(created_at__date__gte=start_year)

        # Aggregates
        totals = orders.aggregate(
            total_amount=Sum("final_amount") or 0,
            total_paid=Sum("paid_amount") or 0,
        )

        total_amount = totals.get("total_amount") or 0
        total_paid = totals.get("total_paid") or 0
        total_pending = total_amount - total_paid

        # Prepare response
        response_data = {
            "customer": customer.name,
            "total_orders": orders.count(),
            "total_amount": total_amount,
            "total_paid": total_paid,
            "total_pending": total_pending,
            "orders": OrderSerializer(orders, many=True).data
        }

        return Response(response_data, status=status.HTTP_200_OK)




class CustomerTransactionHistoryAPIView(APIView):
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        transactions = Transaction.objects.filter(customer=customer)

        # Optional date filters
        filter_type = request.query_params.get("filter")  # week/month/year
        specific_date = request.query_params.get("date")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        today = now().date()

        if filter_type == "week":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            transactions = transactions.filter(paid_at__date__range=[start, end])

        elif filter_type == "month":
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            transactions = transactions.filter(paid_at__date__range=[start, end])

        elif filter_type == "year":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
            transactions = transactions.filter(paid_at__date__range=[start, end])

        if specific_date:
            date_obj = parse_date(specific_date)
            if date_obj:
                transactions = transactions.filter(paid_at__date=date_obj)

        if start_date and end_date:
            start_obj = parse_date(start_date)
            end_obj = parse_date(end_date)
            if start_obj and end_obj:
                transactions = transactions.filter(paid_at__date__range=[start_obj, end_obj])

        # Order by newest first
        transactions = transactions.order_by("-paid_at")

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

# ---------------- Orders -------------------
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
 # We'll create a serializer



class PayNowAPIView(APIView):
    def post(self, request, customer_id):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({"message": "Customer not found"}, status=404)

        pay_amount = request.data.get("pay_amount")
        payment_method = request.data.get("payment_method", "Cash")

        if not pay_amount:
            return Response({"message": "Payment amount is required"}, status=400)

        try:
            pay_amount = Decimal(pay_amount)
        except:
            return Response({"message": "Invalid payment amount"}, status=400)

        if pay_amount <= 0:
            return Response({"message": "Payment amount must be greater than zero"}, status=400)

        with db_transaction.atomic():
            # Get all unpaid orders for the customer, ordered by created_at
            orders = Order.objects.filter(customer=customer).exclude(payment_status="Paid").order_by("created_at")

            remaining_pay = pay_amount

            for order in orders:
                if remaining_pay <= 0:
                    break

                # Calculate how much can be paid for this order
                final_amount = order.final_amount  # Already includes pass_amount and discount
                pending_amount = order.pending_amount
                existing_paid = order.paid_amount

                if remaining_pay >= pending_amount:
                    # Full payment for this order
                    order.paid_amount = existing_paid + pending_amount
                    order.pending_amount = Decimal("0.00")
                    order.payment_status = "Paid"
                    paid_for_order = pending_amount
                    remaining_pay -= pending_amount
                else:
                    # Partial payment
                    order.paid_amount = existing_paid + remaining_pay
                    order.pending_amount = final_amount - order.paid_amount
                    order.payment_status = "Pending"
                    paid_for_order = remaining_pay
                    remaining_pay = Decimal("0.00")

                order.paid_amount = order.paid_amount.quantize(Decimal("0.01"))
                order.pending_amount = order.pending_amount.quantize(Decimal("0.01"))
                order.save()

                # Create/update Transaction (your serializer logic handles this)
                Transaction.objects.update_or_create(
                    order=order,
                    defaults={
                        "customer": customer,
                        "total_amount": order.final_amount,
                        "paid_amount": paid_for_order.quantize(Decimal("0.01")),
                        "pending_amount": order.pending_amount,
                        "payment_method": payment_method,
                        "updated_at": timezone.now(),
                    },
                )

            # Compute remaining pending for all orders
            total_remaining_pending = sum(
                o.pending_amount for o in Order.objects.filter(customer=customer)
            ).quantize(Decimal("0.01"))

        return Response({
            "message": "Payment processed successfully",
            "customer_id": customer.id,
            "paid_amount": str(pay_amount - remaining_pay),
            "remaining_pending": str(total_remaining_pending)
        }, status=200)

class ScanLogAPIView(APIView):
    """
    API to handle ScanLog
    Supports GET, POST, PUT, DELETE
    """

    def get(self, request, pk=None):
        if pk:
            scan = get_object_or_404(ScanLog, pk=pk)
            serializer = ScanLogSerializer(scan)
        else:
            scans = ScanLog.objects.all()
            serializer = ScanLogSerializer(scans, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ScanLogSerializer(data=request.data)
        if serializer.is_valid():
            scan = serializer.save()

            # Optionally, update delivery status in Order if needed
            if scan.order and scan.order.delivery_status != "Delivered":
                scan.order.delivery_status = "Delivered"
                scan.order.save()

            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        scan = get_object_or_404(ScanLog, pk=pk)
        serializer = ScanLogSerializer(scan, data=request.data, partial=True)
        if serializer.is_valid():
            scan = serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        scan = get_object_or_404(ScanLog, pk=pk)
        scan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)





from django.http import HttpResponse
from reportlab.pdfgen import canvas
from io import BytesIO
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Order
from .serializers import OrderSerializer  # We'll create a serializer

from decimal import Decimal

class ReceiptDataView(APIView):
    def get(self, request, order_id, *args, **kwargs):
        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        from decimal import Decimal

        final_amount = Decimal(order.final_amount or 0)  # already includes pass_amount
        paid_amount = Decimal(order.paid_amount or 0)
        pending_amount = final_amount - paid_amount

        if pending_amount <= 0:
            payment_status = "Paid"
            pending_amount = Decimal("0.00")
        elif paid_amount == 0:
            payment_status = "Unpaid"
        else:
            payment_status = "Pending"

        data = {
            "order_id": order.order_id,
            "payment_method": order.payment_method,
            "customer_name": order.customer.name,
            "city": getattr(order.customer, "city", "-"),
            "product_name": order.product.product_name,
            "category": order.category,
            "quantity": order.quantity or order.unit,
            "final_amount": str(final_amount.quantize(Decimal("0.01"))),
            "paid_amount": str(paid_amount.quantize(Decimal("0.01"))),
            "pending_amount": str(pending_amount.quantize(Decimal("0.01"))),
            "payment_status": payment_status,
            "operator": "SPN",
            "qr_code_url": request.build_absolute_uri(order.qr_code.url) if order.qr_code else None,
        }

        return Response(data, status=status.HTTP_200_OK)


from datetime import datetime, timedelta
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Order, Transaction


from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Order, Transaction
from datetime import datetime, timedelta
from decimal import Decimal
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.response import Response


class ReportAPIView(APIView):

    def get(self, request):
        # --- Filter params ---
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        specific_date = request.GET.get('date')
        period = request.GET.get('period')
        category = request.GET.get('category')
        product_name = request.GET.get('product')

        # --- Base QuerySets ---
        orders = Order.objects.all()
        today = datetime.today().date()

        # --- Date filters ---
        if specific_date:
            orders = orders.filter(created_at__date=specific_date)

        if start_date and end_date:
            orders = orders.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)

        if period:
            if period.lower() == 'weekly':
                week_ago = today - timedelta(days=7)
                orders = orders.filter(created_at__date__gte=week_ago)
            elif period.lower() == 'monthly':
                orders = orders.filter(created_at__month=today.month, created_at__year=today.year)
            elif period.lower() == 'yearly':
                orders = orders.filter(created_at__year=today.year)

        # --- Product / Category filters ---
        if product_name:
            orders = orders.filter(product__product_name=product_name)
        if category:
            orders = orders.filter(product__category=category)

        # --- Product Summary ---
        product_summary = (
            orders.values('product__category', 'product__product_name')
                  .annotate(
                      total_quantity=Sum('quantity'),
                      total_pass_no=Sum('pass_no')
                  )
        )

        # --- Order Summary ---
        order_summary = {
            'total_orders': orders.count(),
            'delivered': orders.filter(delivery_status='Delivered').count(),
            'exported': orders.filter(delivery_status='Exported').count(),
        }

        # --- Transaction Summary (sum unique orders) ---
        total_amount_sum = Decimal("0.00")
        paid_amount_sum = Decimal("0.00")
        pending_amount_sum = Decimal("0.00")

        for o in orders.distinct():
            order_final = Decimal(o.final_amount or 0)
            pass_amount = Decimal(o.pass_amount or 0)
            final_total = order_final + pass_amount
            total_amount_sum += final_total
            paid_amount_sum += Decimal(o.paid_amount or 0)
            pending_amount_sum += Decimal(o.pending_amount or 0)

        transaction_summary = {
            'total_amount': str(total_amount_sum.quantize(Decimal("0.01"))),
            'paid_amount': str(paid_amount_sum.quantize(Decimal("0.01"))),
            'pending_amount': str(pending_amount_sum.quantize(Decimal("0.01"))),
        }

        # --- Response ---
        response = {
            'product_summary': list(product_summary),
            'order_summary': order_summary,
            'transaction_summary': transaction_summary,
        }

        return Response(response)



# --------------------------------------------
# Orders Report
# -------------------------------------
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
            transactions = transactions.filter(
                created_at__month=today.month,
                created_at__year=today.year
            )

        # Custom date range
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                transactions = transactions.filter(created_at__date__range=[start, end])
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Aggregations in one go
        aggregates = transactions.aggregate(
            total_amount=Sum("order__final_amount"),
            paid_amount=Sum("paid_amount"),
        )

        total_amount = aggregates["total_amount"] or 0
        paid_amount = aggregates["paid_amount"] or 0
        pending_amount = total_amount - paid_amount
        # Transaction history
        serializer = TransactionSerializer(transactions, many=True)

        data = {
            "summary": {
                "total_amount": total_amount,
                "paid_amount": paid_amount,
                "pending_amount": pending_amount,
            },
            "filters": {
                "timeline": timeline,
                "start_date": start_date,
                "end_date": end_date,
            },
            "transactions": serializer.data,
        }
        return Response(data, status=status.HTTP_200_OK)

class RecentOrdersAPIView(APIView):
    def get(self, request):
        limit = int(request.query_params.get("limit", 10))  # default 5 orders
        recent_orders = Order.objects.order_by("-created_at")[:limit]
        serializer = OrderSerializer(recent_orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




def scan_auto(request):
    order_id = request.GET.get("order_id")
    order = get_object_or_404(Order, order_id=order_id)

    # Just render the mobile-friendly page
    return render(request, "scan_success.html", {"order": order})




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



class DashboardAPIView(APIView):
    def get(self, request):
        return Response({
            "total_customers": Customer.objects.count(),
            "total_orders": Order.objects.count(),
            # "pending_deliveries": Order.objects.filter(delivery_status="Pending").count(),
            # "completed_orders": Order.objects.filter(delivery_status="Delivered").count(),
            "exported_orders": Order.objects.filter(delivery_status="Exported").count(),  
            "delivered_orders": Order.objects.filter(delivery_status="Delivered").count(),  
        })
