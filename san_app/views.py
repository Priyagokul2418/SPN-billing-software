from decimal import Decimal
import os
from io import BytesIO
from datetime import datetime, date, time, timedelta

from django.conf import settings
from django.db import transaction
from django.db import transaction as db_transaction
from django.db.models import Sum, Q, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate
from django.http import HttpResponse, FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.timezone import now, make_aware, get_current_timezone

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

import qrcode

from .models import (
    User,
    Customer,
    Product,
    Device,
    Order,
    Transaction,
    ScanLog,
    ScanReport,
)

from .serializers import (
    UserSerializer,
    CustomerSerializer,
    ProductSerializer,
    DeviceSerializer,
    OrderSerializer,
    TransactionSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    ForgotPasswordSerializer,
    ResetPasswordSerializer,
    OrderHistorySerializer,
    DeviceLoginSerializer,
    ScanLogSerializer,
    ScanReportSerializer,
)

from .utils import (
    generate_qr_code,
    send_otp_via_email,
    generate_order_pdf,
)



font_path = os.path.join(settings.BASE_DIR, "fonts", "DejaVuSans.ttf")

 
def to_dec(value):
    try:
        return Decimal(value or 0)
    except:
        return Decimal('0.00')
 


# ============================================================
# UserAPIView
# ============================================================

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
    
# ============================================================
# LoginAPIView
# ============================================================

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

# ============================================================
# changepasswordAPI
# ============================================================

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


# ============================================================
# Forgotpassword
# ============================================================

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
    

# ============================================================
# Reset Password
# ============================================================

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



# ============================================================
# customerAPI
# ============================================================

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
            mobile = request.query_params.get("mobile")  
    
            if name:
                customers = customers.filter(name__icontains=name)
            if email:
                customers = customers.filter(email__icontains=email)
            if mobile:
                customers = customers.filter(mobile__icontains=mobile)  
    
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




# ============================================================
# Product API
# ============================================================

class ProductAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            product = get_object_or_404(Product, pk=pk)
            serializer = ProductSerializer(product)
            return Response(serializer.data)
        products = Product.objects.all().order_by("-id")
        category = request.query_params.get("category")
        product_name = request.query_params.get("product_names")

   
        if category is not None and category == "":
            distinct_categories = products.values_list("category", flat=True).distinct().order_by("category")
            return Response({"categories": list(distinct_categories)})

       
        if category and not product_name:
            filtered = products.filter(category__iexact=category)
            distinct_products = filtered.values_list("product_name", flat=True).distinct().order_by("product_name")
            return Response({
                "category": category,
                "product_names": list(distinct_products)
            })

        
        if category and product_name:
            filtered = products.filter(
                category__iexact=category,
                product_name__iexact=product_name
            )
            serializer = ProductSerializer(filtered, many=True)
            return Response(serializer.data)

        # 4️ Default → return all products
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


# ============================================================
# Device API
# ============================================================


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



# ============================================================
# Device Login
# ============================================================


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


class DeviceScanHistoryAPIView(APIView):

    def get(self, request, device_id=None):
        """
        Device ID basis scan history
        """
        if device_id:
            device = get_object_or_404(Device, device_id=device_id)
            scans = ScanLog.objects.filter(device=device).order_by('-scanned_at')
            serializer = ScanLogSerializer(scans, many=True)
            return Response({
                "device_id": device.device_id,
                "device_name": device.name,
                "scan_history": serializer.data
            }, status=status.HTTP_200_OK)
        else:
            
            scans = ScanLog.objects.all().order_by('-scanned_at')
            serializer = ScanLogSerializer(scans, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

# ============================================================
# ScanLog API
# ============================================================

class ScanLogAPIView(APIView):


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
            order = serializer.validated_data.get("order")

            if order and order.delivery_status == "Delivered":
                return Response(
                    {"error": "இந்த ஆர்டர் ஏற்கனவே 'Delivered' ஆனது, மீண்டும் Scan செய்ய முடியாது."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if order and order.delivery_status == "Cancelled":
                return Response(
                    {"error": "இந்த ஆர்டர் Cancel செய்யப்பட்டதால் Scan செய்ய முடியாது."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            scan = serializer.save()
            if scan.order and scan.order.delivery_status != "Delivered":
                scan.order.delivery_status = "Delivered"
                scan.order.save(update_fields=["delivery_status"])

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

class ScanOrderAPIView(APIView):
    def get(self, request):
        order_id = request.GET.get("order_id")
        print(" Scan API called with order_id:", order_id)

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

      
class ScanReportAPIView(APIView):


    def get(self, request, device_id=None):
        if device_id:
            report, created = ScanReport.objects.get_or_create(device_id=device_id)
            report.update_report()  
            serializer = ScanReportSerializer(report)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            for report in ScanReport.objects.all():
                report.update_report()
            reports = ScanReport.objects.all()
            serializer = ScanReportSerializer(reports, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


def scan_auto(request):
    order_id = request.GET.get("order_id")
    order = get_object_or_404(Order, order_id=order_id)
    return render(request, "scan_success.html", {"order": order})


class AllDeviceScanReportsAPIView(APIView):


    def get(self, request):
        device_id = request.query_params.get('device_id')
        timeline = request.query_params.get('timeline')
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')

        logs = ScanLog.objects.all()

        if device_id:
            logs = logs.filter(device_id=device_id)

        now = timezone.now()
        if timeline == 'today':
            logs = logs.filter(scanned_at__date=now.date())
        elif timeline == 'week':
            logs = logs.filter(scanned_at__gte=now - timedelta(days=7))
        elif timeline == 'month':
            logs = logs.filter(scanned_at__gte=now - timedelta(days=30))

        if from_date:
            try:
                from_dt = datetime.strptime(from_date, '%Y-%m-%d')
                logs = logs.filter(scanned_at__date__gte=from_dt.date())
            except ValueError:
                pass

        if to_date:
            try:
                to_dt = datetime.strptime(to_date, '%Y-%m-%d')
                logs = logs.filter(scanned_at__date__lte=to_dt.date())
            except ValueError:
                pass

        reports = []
        for d_id in logs.values_list('device_id', flat=True).distinct():
            device_logs = logs.filter(device_id=d_id).order_by('-scanned_at')
            report, _ = ScanReport.objects.get_or_create(device_id=d_id)
            report.total_scans = device_logs.count()
            report.last_scanned_at = device_logs.first().scanned_at if device_logs.exists() else None
            report.save()
            reports.append(report)

        serializer = ScanReportSerializer(reports, many=True)
        return Response(serializer.data)


# ============================================================
# Gatepass API
# ============================================================

dejavu_path = os.path.join(os.path.dirname(font_path), "..", "DejaVuSans.ttf")
if os.path.exists(dejavu_path):
    pdfmetrics.registerFont(TTFont("DejaVuSans", dejavu_path))



class ReceiptPDFView(APIView):
    def get(self, request, order_id, *args, **kwargs):
        order = Order.objects.get(order_id=order_id)
        qr_content = generate_qr_code(order, request)

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'inline; filename="order_{order.order_id}.pdf"'

        buffer = BytesIO()
        RECEIPT_WIDTH, RECEIPT_HEIGHT = 226, 400
        p = canvas.Canvas(buffer, pagesize=(RECEIPT_WIDTH, RECEIPT_HEIGHT))

        width, height = RECEIPT_WIDTH, RECEIPT_HEIGHT
        y = height - 30
        p.setFont("Helvetica-Bold", 12)
        p.drawCentredString(width / 2, y, "GATE PASS")
        y -= 20

        p.setFont("Helvetica", 10)
        p.drawCentredString(width / 2, y, "CUSTOMER RECEIPT")
        y -= 30

        p.setFont("Helvetica", 8)

        def line(label, value):
            nonlocal y
            p.setFont("Helvetica", 8)
            p.drawString(20, y, f"{label}:")
            p.drawRightString(width - 20, y, str(value))
            y -= 12

        line("Payment Method", order.payment_method)
        line("Customer Name", order.customer.name)
        line("City", order.customer.city if hasattr(order.customer, "city") else "-")
        line("Product", order.product.product_name)
        line("Category", order.product.category)
        line("Quantity/Unit", order.quantity or order.unit)
        line("Total", f"{order.total_amount}")
        line("Paid", f"{order.paid_amount}")
        line("Pending", f"{order.pending_amount}")
        line("Payment Status", order.payment_status)
        line("Operator", order.created_by.username if order.created_by else "Admin")

        if order.qr_code:
            p.drawInlineImage(order.qr_code.path, width / 2 - 40, y - 100, 80, 80)
            y -= 110

        p.setFont("Helvetica", 8)
        p.drawString(20, y, "Manager Sign")

        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)

        return response


# ============================================================
# Paynow API
# ============================================================

class PayNowAPIView(APIView):
    def post(self, request, customer_id):
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return Response({"message": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        pay_amount = Decimal(request.data.get("pay_amount", 0))
        payment_method = request.data.get("payment_method", "Cash")

        if pay_amount <= 0:
            return Response({"message": "Invalid pay amount"}, status=status.HTTP_400_BAD_REQUEST)

        orders = Order.objects.filter(customer=customer, pending_amount__gt=0).order_by("order_id")

        if not orders.exists():
            customer.available_balance = (customer.available_balance or Decimal("0.00")) + pay_amount
            customer.save(update_fields=["available_balance"])
            transaction = Transaction.objects.create(
                customer=customer,
                paid_amount=pay_amount,
                pending_amount=Decimal("0.00"),
                transaction_type="Pending Clearance",
                payment_method=payment_method,
            )
            total_paid = Transaction.objects.filter(customer=customer).aggregate(
                total=Sum('paid_amount')
            )['total'] or Decimal('0.00')

            return Response({
                "message": "Payment added to available balance",
                "customer_id": customer.id,
                "paid_amount": float(pay_amount),
                "total_paid_amount": float(total_paid),
                "payment_method": payment_method,
                "orders_cleared": [],
                "remaining_pending_total": 0.0,
                "available_balance": float(customer.available_balance),
                "transaction_id": transaction.id,
            }, status=status.HTTP_200_OK)

        with db_transaction.atomic():
            remaining_payment = pay_amount
            orders_cleared = []
            total_pending_after = Decimal("0.00")

            for order in orders:
                if remaining_payment <= 0:
                    total_pending_after += order.pending_amount
                    orders_cleared.append({
                        "order_id": order.order_id,
                        "cleared_amount": 0,
                        "remaining_pending": float(order.pending_amount)
                    })
                    continue

                if remaining_payment >= order.pending_amount:
                    cleared = order.pending_amount
                    order.paid_amount += cleared
                    remaining_payment -= cleared
                    order.pending_amount = Decimal("0.00")
                else:
                    cleared = remaining_payment
                    order.paid_amount += cleared
                    order.pending_amount -= cleared
                    remaining_payment = Decimal("0.00")

                order.save(update_fields=["pending_amount", "paid_amount"])

                orders_cleared.append({
                    "order_id": order.order_id,
                    "cleared_amount": float(cleared),
                    "remaining_pending": float(order.pending_amount)
                })

                total_pending_after += order.pending_amount

            customer.available_balance = (customer.available_balance or Decimal("0.00")) + remaining_payment
            customer.save(update_fields=["available_balance"])

            transaction = Transaction.objects.create(
                customer=customer,
                paid_amount=pay_amount,
                pending_amount=total_pending_after,
                transaction_type="Pending Clearance",
                payment_method=payment_method,
            )
            total_paid = Transaction.objects.filter(customer=customer).aggregate(
                total=Sum('paid_amount')
            )['total'] or Decimal('0.00')

        return Response({
            "message": "Payment processed successfully",
            "customer_id": customer.id,
            "paid_amount": float(pay_amount),
            "total_paid_amount": float(total_paid),  
            "payment_method": payment_method,
            "orders_cleared": orders_cleared,
            "remaining_pending_total": float(total_pending_after),
            "available_balance": float(customer.available_balance),
            "transaction_id": transaction.id,
        }, status=status.HTTP_200_OK)



# ============================================================
# Order API
# ============================================================


class OrderAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            order = get_object_or_404(Order, pk=pk)
            serializer = OrderSerializer(order)
        else:
            orders = Order.objects.all().order_by("-exported_at")
            serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        serializer = OrderSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            order = serializer.save()
            qr_content = generate_qr_code(order, request)  
            qr_url = request.build_absolute_uri(order.qr_code.url) if hasattr(order, "qr_code") else None
            factory = APIRequestFactory()
            pdf_request = factory.get(f"/api/receipt/{order.order_id}/")   
            pdf_request.user = request.user  
            view = ReceiptPDFView.as_view()
            pdf_response = view(pdf_request, order_id=order.order_id)

            # Save PDF to media
            receipt_path = os.path.join(settings.MEDIA_ROOT, 'receipts', f'order_{order.order_id}.pdf')
            os.makedirs(os.path.dirname(receipt_path), exist_ok=True)
            with open(receipt_path, 'wb') as f:
                f.write(pdf_response.content)

            receipt_url = request.build_absolute_uri(
                os.path.join(settings.MEDIA_URL, 'receipts', f'order_{order.order_id}.pdf')
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
            transaction_obj = Transaction.objects.filter(order=order).first()
            if transaction_obj:
                transaction_obj.total_amount = (order.total_amount or 0) - (order.discount or 0)
                transaction_obj.paid = order.paid_amount or 0
                transaction_obj.pending = order.pending_amount or 0
                transaction_obj.payment_status = getattr(order, 'payment_status', '')
                transaction_obj.save()

            receipt_path = None
            receipt_url = None

            order_status = getattr(order, 'order_status', '')  
            if order_status.lower() == "delivered":
                qr_path = generate_qr_code(order)
                factory = APIRequestFactory()
                pdf_request = factory.get(f"/api/receipt/{order.order_id}/")
                pdf_request.user = request.user
                view = ReceiptPDFView.as_view()
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
    



class RefundAPIView(APIView):
    def post(self, request, order_id):
        # --- Get order ---
        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        # --- Check delivery status ---
        if order.delivery_status != "Cancelled":
            return Response(
                {"error": "Refund allowed only if order is Cancelled"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Get refund amount ---
        refund_amount = request.data.get("refund_amount")
        if not refund_amount:
            return Response({"error": "Refund amount is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            refund_amount = Decimal(refund_amount)
        except:
            return Response({"error": "Invalid refund amount"}, status=status.HTTP_400_BAD_REQUEST)

        # --- Snapshot values before refund ---
        final_amount = order.paid_amount 
        already_refunded = order.refunded_amount
        pending_before_refund = final_amount - already_refunded  

        # --- Check refundable limit ---
        if refund_amount > pending_before_refund:
            return Response(
                {"error": f"Refund cannot exceed pending refundable {pending_before_refund}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # --- Process refund (update order refunded_amount, refunded_at) ---
        order.refunded_amount += refund_amount
        order.refunded_at = timezone.now()
        order.save()

        # --- Create Refund Transaction ---
        Transaction.objects.create(
            customer=order.customer,
            order=order,
            total_amount=final_amount,
            paid_amount=refund_amount,
            pending_amount=final_amount - order.refunded_amount,
            payment_method=request.data.get("payment_method", "Refund"),
            transaction_type="REFUND"
        )

        # --- Build Response ---
        return Response({
            "order_id": order.order_id,
            "final_amount": str(final_amount),                 
            "paid_amount": str(refund_amount),                 
            "pending_amount": str(final_amount - order.refunded_amount),  
            "total_refunded": str(order.refunded_amount),
            "refunded_at": order.refunded_at,
            "refund_status": (
                "Partially Refunded" 
                if order.refunded_amount < final_amount 
                else "Fully Refunded"
            )
        }, status=status.HTTP_200_OK)



class RecentOrdersAPIView(APIView):
    def get(self, request):
        limit = int(request.query_params.get("limit", 10))
        recent_orders = Order.objects.order_by("-exported_at")[:limit]
        serializer = OrderSerializer(recent_orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

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




class OrderReceiptDownloadView(APIView):
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
    

 
# ============================================================
# Transaction API
# ============================================================

  
class TransactionAPIView(APIView):

    def get(self, request, pk=None):
        if pk:
            transaction = get_object_or_404(Transaction, pk=pk)
            serializer = TransactionSerializer(transaction)
            return Response(serializer.data, status=status.HTTP_200_OK)

        transactions = Transaction.objects.all()
        orders = Order.objects.all()

        filter_type = request.query_params.get("filter", "today")
        specific_date = request.query_params.get("date")      
        start_date = request.query_params.get("start_date")   
        end_date = request.query_params.get("end_date")       
        payment_method = request.query_params.get("payment_method")  
        customer_name = request.query_params.get("customer_name")
        
        tz = get_current_timezone()
        today = now().astimezone(tz).date()

        if customer_name:
            transactions = transactions.filter(
                Q(customer__name__icontains=customer_name) |
                Q(customer__email__icontains=customer_name)
            )
            orders = orders.filter(
                Q(customer__name__icontains=customer_name) |
                Q(customer__email__icontains=customer_name)
            )

        if filter_type == "today" or not filter_type:
            start_dt = make_aware(datetime.combine(today, time.min), tz)
            end_dt = make_aware(datetime.combine(today, time.max), tz)
            transactions = transactions.filter(paid_at__range=[start_dt, end_dt])
            orders = orders.filter(exported_at__range=[start_dt, end_dt])

        elif filter_type == "week":
            start = today - timedelta(days=today.weekday())  
            end = start + timedelta(days=6)                 
            start_dt = make_aware(datetime.combine(start, time.min), tz)
            end_dt = make_aware(datetime.combine(end, time.max), tz)
            transactions = transactions.filter(paid_at__range=[start_dt, end_dt])
            orders = orders.filter(exported_at__range=[start_dt, end_dt])

        elif filter_type == "month":
            start = today.replace(day=1)
            if start.month == 12:
                end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            start_dt = make_aware(datetime.combine(start, time.min), tz)
            end_dt = make_aware(datetime.combine(end, time.max), tz)
            transactions = transactions.filter(paid_at__range=[start_dt, end_dt])
            orders = orders.filter(exported_at__range=[start_dt, end_dt])

        elif filter_type == "year":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
            start_dt = make_aware(datetime.combine(start, time.min), tz)
            end_dt = make_aware(datetime.combine(end, time.max), tz)
            transactions = transactions.filter(paid_at__range=[start_dt, end_dt])
            orders = orders.filter(exported_at__range=[start_dt, end_dt])

        if specific_date:
            date_obj = parse_date(specific_date)
            if date_obj:
                start_dt = make_aware(datetime.combine(date_obj, time.min), tz)
                end_dt = make_aware(datetime.combine(date_obj, time.max), tz)
                transactions = transactions.filter(paid_at__range=[start_dt, end_dt])
                orders = orders.filter(exported_at__range=[start_dt, end_dt])

        if start_date and end_date:
            start_obj = parse_date(start_date)
            end_obj = parse_date(end_date)
            if start_obj and end_obj:
                start_dt = make_aware(datetime.combine(start_obj, time.min), tz)
                end_dt = make_aware(datetime.combine(end_obj, time.max), tz)
                transactions = transactions.filter(paid_at__range=[start_dt, end_dt])
                orders = orders.filter(exported_at__range=[start_dt, end_dt])

        if payment_method:
            transactions = transactions.filter(payment_method=payment_method)

        transactions = transactions.order_by("-paid_at")
        orders = orders.order_by("-exported_at")

        total_orders_final_amount = Decimal('0.00')
        total_orders_paid_amount = Decimal('0.00')
        total_orders_pending_amount = Decimal('0.00')
        total_orders_count = orders.count()

        for order in orders:
            total_orders_final_amount += to_dec(order.final_amount)
            total_orders_paid_amount += to_dec(order.paid_amount)
            total_orders_pending_amount += to_dec(order.pending_amount)

        total_transactions_paid = Decimal('0.00')
        total_transactions_count = transactions.count()

        transaction_list = []
        for transaction in transactions:
            serializer = TransactionSerializer(transaction)
            transaction_data = serializer.data
            transaction_list.append(transaction_data)
            total_transactions_paid += to_dec(transaction.paid_amount)

        response_data = {
            "summary": {
                "total_orders": total_orders_count,
                "total_orders_final_amount": str(total_orders_final_amount.quantize(Decimal('0.01'))),
                "total_orders_paid_amount": str(total_orders_paid_amount.quantize(Decimal('0.01'))),
                "total_orders_pending_amount": str(total_orders_pending_amount.quantize(Decimal('0.01'))),
                "total_transactions": total_transactions_count,
                "total_transactions_paid": str(total_transactions_paid.quantize(Decimal('0.01'))),
                "total_final_amount": str(total_orders_final_amount.quantize(Decimal('0.01'))),
                "total_paid_amount": str(total_orders_paid_amount.quantize(Decimal('0.01'))),
                "total_pending_amount": str(total_orders_pending_amount.quantize(Decimal('0.01')))
            },
            "transactions": transaction_list
        }

        return Response(response_data, status=status.HTTP_200_OK)

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
    


# ============================================================
# Reports Page  API
# ============================================================


class ReportAPIView(APIView):

    def get(self, request):
        start_date = request.query_params.get('start_date') 
        end_date = request.query_params.get('end_date')      
        specific_date = request.query_params.get('date')     
        period = request.query_params.get('period')      
        category = request.query_params.get('category')
        product_name = request.query_params.get('product_name')

        tz = get_current_timezone()
        orders = Order.objects.all()
        transactions = Transaction.objects.all()

        # Date filtering
        if specific_date:
            try:
                date_obj = datetime.strptime(specific_date, "%Y-%m-%d").date()
                start_dt = make_aware(datetime.combine(date_obj, time.min), tz)
                end_dt = make_aware(datetime.combine(date_obj, time.max), tz)
                orders = orders.filter(exported_at__range=[start_dt, end_dt])
                transactions = transactions.filter(paid_at__range=[start_dt, end_dt])
            except ValueError:
                pass

        if start_date and end_date:
            try:
                start_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                start_dt = make_aware(datetime.combine(start_obj, time.min), tz)
                end_dt = make_aware(datetime.combine(end_obj, time.max), tz)
                orders = orders.filter(exported_at__range=[start_dt, end_dt])
                transactions = transactions.filter(paid_at__range=[start_dt, end_dt])
            except ValueError:
                pass

        # Period filtering
        today = now().astimezone(tz).date()
        if period:
            if period.lower() == 'weekly':
                start = today - timedelta(days=today.weekday())
                end = start + timedelta(days=6)
            elif period.lower() == 'monthly':
                start = today.replace(day=1)
                if start.month == 12:
                    end = start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
                else:
                    end = start.replace(month=start.month + 1, day=1) - timedelta(days=1)
            elif period.lower() == 'yearly':
                start = today.replace(month=1, day=1)
                end = today.replace(month=12, day=31)
            else:
                start = end = None

            if start and end:
                start_dt = make_aware(datetime.combine(start, time.min), tz)
                end_dt = make_aware(datetime.combine(end, time.max), tz)
                orders = orders.filter(exported_at__range=[start_dt, end_dt])
                transactions = transactions.filter(paid_at__range=[start_dt, end_dt])

        # PRODUCT FILTERING
        if product_name:
            orders = orders.filter(product__product_name__iexact=product_name)
        if category:
            orders = orders.filter(product__category__iexact=category)

        order_ids = orders.values_list('order_id', flat=True)
        filtered_transactions = transactions.filter(order__order_id__in=order_ids)

        print(f"Total orders found: {orders.count()}")
        print(f"Total transactions found: {filtered_transactions.count()}")
        for order in orders:
            print(f"Order {order.order_id}: paid_amount={order.paid_amount}, final_amount={order.final_amount}")
        for transaction in filtered_transactions:
            print(f"Transaction for Order {transaction.order.order_id}: paid_amount={transaction.paid_amount}")


        product_summary = (
            orders.values('product__category', 'product__product_name')
                  .annotate(
                      total_quantity=Sum('quantity'),
                      total_units=Sum('unit'),
                      total_pass_no=Sum('pass_no'),
                      total_final_amount=Sum('final_amount'),
                      total_paid_amount=Sum('paid_amount'),
                      total_pending_amount=Sum('pending_amount')
                  )
        )
        product_summary_with_paid = []
        total_filtered_final_amount = Decimal('0.00')
        total_filtered_paid_from_orders = Decimal('0.00')
        total_filtered_paid_from_transactions = Decimal('0.00')
        total_filtered_pending_amount = Decimal('0.00')

        for product in product_summary:
            product_orders = orders.filter(
                product__category=product['product__category'],
                product__product_name=product['product__product_name']
            )
            
            product_order_ids = product_orders.values_list('order_id', flat=True)
            product_transactions = filtered_transactions.filter(order__order_id__in=product_order_ids)
            
            total_paid_from_transactions = product_transactions.aggregate(
                total_paid=Sum('paid_amount')
            )['total_paid'] or Decimal('0.00')
            
            total_paid_from_orders = product_orders.aggregate(
                total_paid=Sum('paid_amount')
            )['total_paid'] or Decimal('0.00')
            
            actual_paid_amount = max(total_paid_from_orders, total_paid_from_transactions)
            product_final_amount = product['total_final_amount'] or Decimal('0.00')
            product_pending_amount = product['total_pending_amount'] or Decimal('0.00')
            
            total_filtered_final_amount += product_final_amount
            total_filtered_paid_from_orders += total_paid_from_orders
            total_filtered_paid_from_transactions += total_paid_from_transactions
            total_filtered_pending_amount += product_pending_amount
            
            product_summary_with_paid.append({
                'product_category': product['product__category'],
                'product_name': product['product__product_name'],
                'total_quantity': product['total_quantity'],
                'total_units': product['total_units'],
                'total_pass_no': product['total_pass_no'],
                'total_final_amount': float(product_final_amount),
                'total_paid_amount': float(actual_paid_amount), 
                'total_paid_from_orders': float(total_paid_from_orders),  
                'total_paid_from_transactions': float(total_paid_from_transactions), 
                'total_pending_amount': float(product_pending_amount)
            })

        order_summary = {
            'total_orders': orders.count(),
            'delivered': orders.filter(delivery_status='Delivered').count(),
            'exported': orders.filter(delivery_status='Exported').count(),
        }
        accurate_paid_amount = total_filtered_paid_from_orders
        transaction_summary = {
            'total_amount': float(total_filtered_final_amount),
            'paid_amount': float(accurate_paid_amount),  
            'pending_amount': float(total_filtered_pending_amount),
        }

        return Response({
            'product_summary': product_summary_with_paid,
            'order_summary': order_summary,
            'transaction_summary': transaction_summary,
            'debug_info': {
                'total_orders_found': orders.count(),
                'total_transactions_found': filtered_transactions.count(),
                'total_paid_from_orders': float(total_filtered_paid_from_orders),
                'total_paid_from_transactions': float(total_filtered_paid_from_transactions),
            },
            'filters_applied': {
                'product_name': product_name,
                'category': category,
                'start_date': start_date,
                'end_date': end_date,
                'specific_date': specific_date,
                'period': period
            }
        }, status=200)




# ============================================================
# customer order history
# ============================================================


class CustomerOrderHistoryAPIView(APIView):
    def get(self, request, customer_id):
        # --- Get customer ---
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({"message": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        # --- Get query params ---
        filter_type = request.query_params.get("filter_type", None)
        date_value = request.query_params.get("date", None)
        start_date = request.query_params.get("start_date", None)
        end_date = request.query_params.get("end_date", None)
        timeline = request.query_params.get("timeline", None)

        # --- Base queryset ---
        orders = Order.objects.filter(customer=customer).order_by("-exported_at")
        transactions = Transaction.objects.filter(customer=customer)

        # --- Apply date filters ---
        today = date.today()
        if filter_type == "date" and date_value:
            try:
                date_obj = datetime.strptime(date_value, "%Y-%m-%d").date()
                orders = orders.filter(exported_at__date=date_obj)
                transactions = transactions.filter(paid_at__date=date_obj)
            except ValueError:
                return Response({"message": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        if start_date and end_date:
            try:
                start_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                orders = orders.filter(exported_at__date__range=[start_obj, end_obj])
                transactions = transactions.filter(paid_at__date__range=[start_obj, end_obj])
            except ValueError:
                return Response({"message": "Invalid start_date or end_date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        if timeline:
            timeline = timeline.lower()
            if timeline == "today":
                orders = orders.filter(exported_at__date=today)
                transactions = transactions.filter(paid_at__date=today)
            elif timeline == "week":
                start_week = today - timedelta(days=today.weekday())
                orders = orders.filter(exported_at__date__gte=start_week)
                transactions = transactions.filter(paid_at__date__gte=start_week)
            elif timeline == "month":
                start_month = today.replace(day=1)
                orders = orders.filter(exported_at__date__gte=start_month)
                transactions = transactions.filter(paid_at__date__gte=start_month)
            elif timeline == "year":
                start_year = today.replace(month=1, day=1)
                orders = orders.filter(exported_at__date__gte=start_year)
                transactions = transactions.filter(paid_at__date__gte=start_year)

        # --- Adjust order pending amounts based on final_amount ---
        for order in orders:
            pending_clearance_paid = sum(
                [Decimal(t.paid_amount or 0) for t in transactions if t.order_id == order.order_id and t.transaction_type == "Pending Clearance"]
            )
            order.pending_amount = Decimal(order.final_amount or 0) - Decimal(order.paid_amount or 0) - pending_clearance_paid
            if order.pending_amount < 0:
                order.pending_amount = Decimal("0.00")

        # --- Calculate totals based on final_amount ---
        total_amount = sum([Decimal(o.final_amount or 0) for o in orders])
        total_paid_orders = sum([Decimal(o.paid_amount or 0) for o in orders])
        total_pending_clearance = sum([Decimal(t.paid_amount or 0) for t in transactions if t.order is None])
        total_paid = total_paid_orders + total_pending_clearance
        total_pending = total_amount - total_paid
        if total_pending < 0:
            total_pending = Decimal("0.00")

        # --- Prepare response ---
        response_data = {
            "customer": customer.name,
            "total_orders": orders.count(),
            "total_amount": float(total_amount),
            "total_paid": float(total_paid),
            "total_pending": float(total_pending),
            "orders": OrderSerializer(orders, many=True).data
        }

        return Response(response_data, status=status.HTTP_200_OK)



# ============================================================
# customer Transaction history
# ============================================================


class CustomerTransactionHistoryAPIView(APIView):
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        orders = Order.objects.filter(customer=customer)
        transactions = Transaction.objects.filter(customer=customer).order_by("-paid_at")

        
        filter_type = request.query_params.get("filter") 
        specific_date = request.query_params.get("date")
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")

        today = now().date()

     
        if filter_type == "week":
            start = today - timedelta(days=today.weekday())
            end = start + timedelta(days=6)
            orders = orders.filter(exported_at__date__range=[start, end])
            transactions = transactions.filter(paid_at__date__range=[start, end])
        elif filter_type == "month":
            start = today.replace(day=1)
            end = (start.replace(month=start.month + 1, day=1) - timedelta(days=1)) if start.month < 12 else start.replace(year=start.year + 1, month=1, day=1) - timedelta(days=1)
            orders = orders.filter(exported_at__date__range=[start, end])
            transactions = transactions.filter(paid_at__date__range=[start, end])
        elif filter_type == "year":
            start = today.replace(month=1, day=1)
            end = today.replace(month=12, day=31)
            orders = orders.filter(exported_at__date__range=[start, end])
            transactions = transactions.filter(paid_at__date__range=[start, end])

        if specific_date:
            date_obj = parse_date(specific_date)
            if date_obj:
                orders = orders.filter(exported_at__date=date_obj)
                transactions = transactions.filter(paid_at__date=date_obj)

        if start_date and end_date:
            start_obj = parse_date(start_date)
            end_obj = parse_date(end_date)
            if start_obj and end_obj:
                orders = orders.filter(exported_at__date__range=[start_obj, end_obj])
                transactions = transactions.filter(paid_at__date__range=[start_obj, end_obj])

        for order in orders:
            pending_clearance_paid = sum(
                Decimal(t.paid_amount or 0)
                for t in transactions
                if t.order_id == order.order_id and t.transaction_type == "Pending Clearance"
            )
            order.pending_amount = Decimal(order.final_amount or 0) - Decimal(order.paid_amount or 0) - pending_clearance_paid
            if order.pending_amount < 0:
                order.pending_amount = Decimal("0.00")

        
        gross_total = sum([Decimal(o.final_amount or 0) for o in orders])

        
        total_refunds = sum([
            Decimal(t.paid_amount or 0)
            for t in transactions
            if t.transaction_type in ("REFUND", "Refund")
        ])

        
        total_amount = gross_total - total_refunds
        if total_amount < 0:
            total_amount = Decimal("0.00")

       
        total_payments = sum([
            Decimal(t.paid_amount or 0)
            for t in transactions
            if not (t.transaction_type in ("REFUND", "Refund") or t.payment_method == "Available Balance")
        ])
        
       
        total_paid = total_payments - total_refunds
        if total_paid < 0:
            total_paid = Decimal("0.00")

        total_pending = total_amount - total_paid
        if total_pending < 0:
            total_pending = Decimal("0.00")

        serializer = TransactionSerializer(transactions, many=True)

        # --- Response ---
        return Response({
            "customer": customer.name,
            "total_orders": orders.count(),
            "total_amount": float(total_amount),
            "total_paid": float(total_paid),
            "total_pending": float(total_pending),
            "available_balance": float(customer.available_balance),
            "transaction_history": serializer.data
        }, status=status.HTTP_200_OK)
        
      
# ============================================================
# customer Report
# ============================================================

  
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


# ============================================================
# customer report download 
# ============================================================


class CustomerReportDownloadAPIView(APIView):
    def get(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        orders = Order.objects.filter(customer=customer)
        transactions = Transaction.objects.filter(customer=customer)
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
            qty_or_unit = str(o.quantity) if o.measurement_type == 'Quantity' else str(o.unit)
            total_amount += float(o.total_amount)
            total_paid += float(o.paid_amount)
            total_pending += float(o.pending_amount)
            status = f"Delivery: {o.delivery_status}\nPayment: {o.payment_status}"

            order_data.append([
                f"{o.order_id} ({o.exported_at.strftime('%d-%m-%y')})",
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



    
    
# --------------------------------------------
# Orders Report
# -------------------------------------
class OrdersReportView(APIView):
    def get(self, request):
        orders = Order.objects.all()

        # Filters
        product_name = request.query_params.get("product")
        category = request.query_params.get("category")
        delivery_status = request.query_params.get("status") 
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
            orders = orders.filter(exported_at__date=today)
        elif timeline == "week":
            start_week = today - timedelta(days=today.weekday())
            orders = orders.filter(exported_at__date__gte=start_week)
        elif timeline == "month":
            orders = orders.filter(exported_at__month=today.month, exported_at__year=today.year)

        # Custom date range
        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                orders = orders.filter(exported_at__date__range=[start, end])
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

        if start_date and end_date:
            try:
                start = datetime.strptime(start_date, "%Y-%m-%d").date()
                end = datetime.strptime(end_date, "%Y-%m-%d").date()
                transactions = transactions.filter(created_at__date__range=[start, end])
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD"}, status=status.HTTP_400_BAD_REQUEST)

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



class ReceiptDataView(APIView):
    def get(self, request, order_id, *args, **kwargs):
        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        from decimal import Decimal

        final_amount = Decimal(order.final_amount or 0) 
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
            "category": order.product.category,
            "quantity": order.quantity or order.unit,
            "final_amount": str(final_amount.quantize(Decimal("0.01"))),
            "paid_amount": str(paid_amount.quantize(Decimal("0.01"))),
            "pending_amount": str(pending_amount.quantize(Decimal("0.01"))),
            "payment_status": payment_status,
            "operator": "SPN",
            "qr_code_url": request.build_absolute_uri(order.qr_code.url) if order.qr_code else None,
        }

        return Response(data, status=status.HTTP_200_OK)






# ============================================================
#  ORDER INVOICE PDF
# ============================================================

class OrderPDFDownloadAPIView(APIView):
    def get(self, request, order_id):
        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)

        serializer = OrderSerializer(order)
        pdf_bytes = generate_order_pdf(serializer.data)

        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="order_{order_id}.pdf"'
        return response


# ============================================================
# CUSTOMER ORDER REPORT PDF
# ============================================================
class CustomerOrderReportDownloadAPIView(APIView):
    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return HttpResponse("Customer not found", status=404)

        # --- Filter orders ---
        orders = Order.objects.filter(customer=customer).order_by("-exported_at")

        today = date.today()
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        timeline = (request.query_params.get("timeline") or "").lower()

        # --- Apply date filters ---
        if start_date and end_date:
            try:
                start_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                orders = orders.filter(exported_at__date__range=[start_obj, end_obj])
            except ValueError:
                return HttpResponse("Invalid start_date or end_date format", status=400)

        if timeline in ["today", "week", "month", "year"]:
            if timeline == "today":
                orders = orders.filter(exported_at__date=today)
            elif timeline == "week":
                start_week = today - timedelta(days=today.weekday())
                orders = orders.filter(exported_at__date__gte=start_week)
            elif timeline == "month":
                start_month = today.replace(day=1)
                orders = orders.filter(exported_at__date__gte=start_month)
            elif timeline == "year":
                start_year = today.replace(month=1, day=1)
                orders = orders.filter(exported_at__date__gte=start_year)

        # --- Helper functions ---
        def payment_status(order):
            paid, final = Decimal(order.paid_amount or 0), Decimal(order.final_amount or 0)
            if paid == 0:
                return "Unpaid"
            elif paid < final:
                return "Pending"
            return "Paid"

        def delivery_status(order):
            return order.delivery_status or "Pending"

        # --- Build PDF ---
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()

        elements.append(Paragraph("<b>Customer Order Report</b>", styles["Title"]))
        elements.append(Spacer(1, 10))

        # --- Customer Info Table ---
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
        customer_table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
        elements.append(customer_table)
        elements.append(Spacer(1, 20))

        elements.append(Paragraph(f"<b>Total Orders:</b> {orders.count()}", styles["Normal"]))
        elements.append(Spacer(1, 10))

        # --- Orders Table ---
        table_data = [["Order ID", "Product Name", "Qty/Unit", "Final Amount", "Paid", "Pending", "Status"]]
        total_final = total_paid = total_pending = Decimal("0.00")

        for order in orders:
            final_amt = Decimal(order.final_amount or 0)
            paid_amt = Decimal(order.paid_amount or 0)
            pending_amt = max(final_amt - paid_amt, Decimal("0.00"))

            order_id_cell = Paragraph(
                f"<b>{order.order_id}</b><br/>"
                f"Exported: {order.exported_at.strftime('%d-%m-%Y %I:%M %p') if order.exported_at else '-'}<br/>"
                f"Delivered: {order.delivered_at.strftime('%d-%m-%Y %I:%M %p') if order.delivered_at else '-'}",
                styles["Normal"]
            )

            status_text = f"Payment: {payment_status(order)}<br/>Delivery: {delivery_status(order)}"
            status_cell = Paragraph(status_text, styles["Normal"])

            table_data.append([
                order_id_cell,
                order.product.product_name if order.product else "-",
                f"{order.unit or order.quantity or '0.00'}",
                f"{final_amt:.2f}",
                f"{paid_amt:.2f}",
                f"{pending_amt:.2f}",
                status_cell,
            ])

            total_final += final_amt
            total_paid += paid_amt
            total_pending += pending_amt

        # --- Totals Row ---
        table_data.append([
            Paragraph("<b>Totals</b>", styles["Normal"]),
            "", "", f"{total_final:.2f}", f"{total_paid:.2f}", f"{total_pending:.2f}", ""
        ])

        table = Table(table_data, repeatRows=1, colWidths=[70, 110, 60, 70, 70, 70, 110])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(table)

        doc.build(elements)
        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="customer_{customer.id}_order_report.pdf"'
        response.write(pdf)
        return response



class CustomerTransactionReportDownloadAPIView(APIView):
  

    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return HttpResponse("Customer not found", status=404)

       
        transactions = Transaction.objects.filter(customer=customer).order_by("-paid_at")

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        center_style = ParagraphStyle(name="center", alignment=1)

        elements.append(Paragraph(f"Customer Transaction History - {customer.name}", styles["Title"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"Total Transactions: {transactions.count()}", styles["Normal"]))
        elements.append(Spacer(1, 12))

        table_data = [["Order ID", "Transaction Type", "Final Amount", "Paid/Refund Amount", "Pending Amount", "Paid At", "Payment Status"]]

        balance_additions = {}
        
        for t in transactions:
            if not t.order:
                continue

            order_id = t.order.order_id
            transaction_type = t.transaction_type or "order_payment"
            final_amount = f"{Decimal(t.total_amount or 0):.2f}"
            
          
            if t.paid_at:
                if settings.USE_TZ:
                    local_paid_at = timezone.localtime(t.paid_at)
                    paid_at = local_paid_at.strftime("%d-%m-%Y %I:%M %p")
                else:
                    paid_at = t.paid_at.strftime("%d-%m-%Y %I:%M %p")
            else:
                paid_at = "-"
                
            pending_amount = f"{Decimal(t.pending_amount or 0):.2f}"

          
            if transaction_type == "REFUND":
                paid_amount = Paragraph(f"<font color='red'>-{Decimal(t.paid_amount or 0):.2f}</font>", center_style)
                status = "Fully Refunded" if Decimal(t.pending_amount or 0) == 0 else "Partially Refunded"
                
                table_data.append([
                    order_id,
                    "REFUND",
                    final_amount,
                    paid_amount,
                    pending_amount,
                    paid_at, 
                    status
                ])
                
            elif transaction_type == "balance_addition":
                balance_amount = Decimal(t.paid_amount or 0)
                balance_additions[order_id] = balance_additions.get(order_id, Decimal('0.00')) + balance_amount
                
                paid_amount = Paragraph(f"<font color='green'>+{balance_amount:.2f}</font>", center_style)
                
                table_data.append([
                    order_id,
                    "BALANCE ADDITION",
                    "-",
                    paid_amount,
                    "-",
                    paid_at,  
                    "Added to Balance"
                ])
                
            elif transaction_type == "pending_clearance":
                paid_amount = f"{Decimal(t.paid_amount or 0):.2f}"
                status = "Paid" if Decimal(t.pending_amount or 0) == 0 else "Pending"
                
                table_data.append([
                    order_id,
                    "PENDING CLEARANCE",
                    final_amount,
                    paid_amount,
                    pending_amount,
                    paid_at,  
                    status
                ])
                
            else:  
                paid_amount = f"{Decimal(t.paid_amount or 0):.2f}"
                status = "Paid" if Decimal(t.pending_amount or 0) == 0 else "Pending"
                
                table_data.append([
                    order_id,
                    "ORDER PAYMENT",
                    final_amount,
                    paid_amount,
                    pending_amount,
                    paid_at,  
                    status
                ])

        table = Table(table_data, repeatRows=1, colWidths=[60, 100, 70, 100, 70, 100, 70])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 20))
       
        
        total_payments = sum(Decimal(t.paid_amount or 0) for t in transactions if t.transaction_type not in ["REFUND", "balance_addition"])
        total_refunds = sum(Decimal(t.paid_amount or 0) for t in transactions if t.transaction_type == "REFUND")
        

        doc.build(elements)

        pdf = buffer.getvalue()
        buffer.close()

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="customer_{customer.id}_transaction_history.pdf"'
        response.write(pdf)
        return response
        
        
        
 