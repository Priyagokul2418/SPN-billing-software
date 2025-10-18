from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, ValidationError
import random
from decimal import Decimal,InvalidOperation
from datetime import timedelta
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files import File



def to_dec(v):
    if v is None:
        return Decimal('0.00')
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0.00')
    

class User(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    mobile_no = models.CharField(max_length=10)
    username = models.EmailField(unique=True)
    password = models.CharField(max_length=255) 
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)   


    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True) 
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)


    def __str__(self):
        return self.name
    
    def generate_otp(self):
        self.otp = str(random.randint(100000, 999999))
        self.otp_created_at = timezone.now()
        self.save()
        return self.otp
   


# Customer model
class Customer(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(null=True)
    mobile = models.CharField(max_length=10 ,validators=[RegexValidator(r'^\d{10}$', 'Enter a valid 10-digit mobile number')],unique=True)
    gender = models.CharField(max_length=50, default="male")
    email = models.EmailField(unique=True,null=True)
    address = models.TextField(null=True)
    city = models.TextField(null=True)
    Business_name = models.CharField(max_length=255,null=True)
    customer_type= models.CharField(max_length=255,null=True)
    pincode = models.CharField(max_length=6,validators=[RegexValidator(r'^\d{6}$', 'Enter a valid 6-digit pincode')], null=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2,null=True)
    available_balance = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal("0.00")
    )    
    created_by = models.ForeignKey(User, related_name='customers_created', on_delete=models.SET_NULL, null=True, blank=True)
    updated_by = models.ForeignKey(User, related_name='customers_updated', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)   
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Product(models.Model):


    MEASUREMENT_CHOICES = [
        ('Quantity', 'Quantity'),
        ('Unit', 'Unit'),
        ('Ton', 'Ton'), 
    ]

    id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=50)   
    category = models.CharField(max_length=100) 
    measurement_type = models.CharField(max_length=20, choices=MEASUREMENT_CHOICES)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ton = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_code = models.CharField(max_length=20, unique=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    created_by = models.ForeignKey('User', related_name='products_created', on_delete=models.SET_NULL, null=True, blank=True)
    updated_by = models.ForeignKey('User', related_name='products_updated', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True) 
    is_active = models.BooleanField(default=True)  

    
    def save(self, *args, **kwargs):
        if not self.product_code:  
            cat_prefix = self.category[:3].upper()
            prod_prefix = self.product_name[:3].upper()
            existing = Product.objects.filter(
                category__iexact=self.category,
                product_name__iexact=self.product_name
            ).first()

            if existing:  
                self.product_code = existing.product_code
            else:
                unique_names = (
                    Product.objects.filter(category__iexact=self.category)
                    .values_list("product_name", flat=True).distinct()
                )
                count = len(unique_names) + 1
                self.product_code = f"{cat_prefix}-{prod_prefix}{count}"

        super().save(*args, **kwargs)

    def clean(self):

        valid_varieties = [v[0] for v in self.PRODUCT_VARIETIES.get(self.product, [])]
        if self.category not in valid_varieties:
            raise ValidationError({"category": f"{self.product} does not have variety {self.category}"})

    def __str__(self):
       return f"{self.product_name} - {self.category} ({self.measurement_type})"




# Device model
class Device(models.Model):
    device_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    device_state=models.CharField(max_length=255)
    id_verify = models.BooleanField(default=True)
    location = models.CharField(max_length=255)
   
    username = models.CharField(max_length=100, unique=True)
    password = models.CharField(max_length=255) 

    created_by = models.ForeignKey(User, related_name='devices_created', on_delete=models.SET_NULL, null=True, blank=True)
    updated_by = models.ForeignKey(User, related_name='devices_updated', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)   


    def __str__(self):
        return self.device_id


# Order model
class Order(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('Paid', 'Paid'),
        ('Unpaid', 'Unpaid'),
        ('Pending', 'Pending'),
        ("Refunded", "Refunded"),
        ("Partially Refunded", "Partially Refunded"),
]
    
    MEASUREMENT_CHOICES = [
    ('Quantity', 'Quantity'),  
    ('Unit', 'Unit'),
    ('Ton', 'Ton'), 
]
    
    delivery_status_choices = [
        ('Cancelled', 'Cancelled'),
        ('Exported', 'Exported'),
        ('Delivered', 'Delivered')
    ]   
    
    Order_status_choices = [
        ('Cancelled', 'Cancelled'),
        ('Booked', 'Booked'),
    ]   
    


    PAYMENT_METHOD_CHOICES = [
        ('UPI', 'UPI'),
        ('Cash', 'Cash'),
        ('Bank', 'Bank Transfer'),
        ('Card', 'Card'),
        ('Available Balance', 'Available Balance'),
    ]
    order_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    category = models.CharField(max_length=255)
    measurement_type = models.CharField(max_length=20, choices=MEASUREMENT_CHOICES)
    quantity = models.PositiveIntegerField(null=True, blank=True)   
    unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    ton = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    contact_no = models.CharField(max_length=12,null=True,blank=True)
    delivery_address = models.TextField(null=True)
    qr_code = models.ImageField(upload_to='qrcodes/', null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pending_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    refunded_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    refunded_at = models.DateTimeField(null=True, blank=True)
    refund_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="Unpaid"
    )
    delivery_status = models.CharField(max_length=10, choices=delivery_status_choices, default='Exported')
    order_status = models.CharField(max_length=10, choices=Order_status_choices, default='Booked')
    exported_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    pass_no = models.IntegerField(null=True)
    amount_per_pass = models.DecimalField(max_digits=10, decimal_places=2,null=True)
    pass_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0,null=True)
    delivered_by = models.CharField(max_length=255, null=True, blank=True) 
    
    created_by = models.ForeignKey(User, related_name='orders_created', on_delete=models.SET_NULL, null=True, blank=True)
    updated_by = models.ForeignKey(User, related_name='orders_updated', on_delete=models.SET_NULL, null=True, blank=True)

    # created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True) 

    

    def process_refund(self, refund_amount: Decimal):
    
        if self . delivery_status!= "Cancelled":
            raise ValueError("Refund allowed only if order is Cancelled")

        if refund_amount <= 0:
            raise ValueError("Refund amount must be greater than 0")

        if self.refunded_amount + refund_amount > self.paid_amount:
            raise ValueError("Refund amount cannot exceed paid amount")

        # Update refunded details
        self.refunded_amount += refund_amount
        self.refunded_at = timezone.now()

        # Update payment status
        if self.refunded_amount == self.paid_amount:
            self.payment_status = "Refunded"
        elif self.refunded_amount < self.paid_amount:
            self.payment_status = "Partially Refunded"

        self.save()
    
    def get_refund_status(self, obj):
        paid = to_dec(obj.paid_amount)
        refunded = to_dec(obj.refunded_amount)

        if refunded == Decimal("0.00"):
            return "Not Refunded"
        elif refunded < paid:
            return "Partially Refunded"
        elif refunded == paid:
            return "Fully Refunded"
        return "Not Refunded"
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding 
        
    
        if self.delivery_status == "Delivered":
            if not self.delivered_at:
                self.delivered_at = timezone.now()

        if self.order_status == "Cancelled" and self.delivery_status == "Delivered":
            raise ValueError("Delivered order cannot be cancelled.")

        if self.order_status == "Cancelled":
            self.delivery_status = "Cancelled"

        if self.pass_no and self.amount_per_pass:
            self.pass_amount = self.pass_no * self.amount_per_pass
        else:
            self.pass_amount = 0

        if is_new:
            if self.paid_amount > self.final_amount:
                extra_amount = self.paid_amount - self.final_amount
                self.pending_amount = 0
             
                if self.customer:  
                    self.customer.available_balance += extra_amount
                    self.customer.save(update_fields=["available_balance"])
        else:
            
            if self.paid_amount > self.final_amount:
                self.pending_amount = 0
            else:
                self.pending_amount = self.final_amount - self.paid_amount

        super().save(*args, **kwargs)

        # QR code generation (don’t deduct balance here)
        if not self.qr_code:
            base_url = "https://vallibricks.com/scan_auto/"
            qr_content = f"{base_url}?order_id={self.order_id}&amount={self.total_amount}"
            qr = qrcode.make(qr_content)

            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            filename = f"order_{self.order_id}.png"
            self.qr_code.save(filename, File(buffer), save=False)
            super().save(update_fields=["qr_code"])
   
   
    def delete(self, *args, **kwargs):
        print(f"Deleting order {self.order_id} and its related transactions")
        self.transactions.all().delete()
        self.scans.all().delete()
        super().delete(*args, **kwargs)

    def _deduct_available_balance(self):
        """Helper to deduct available balance safely"""
        if self.customer.available_balance < self.final_amount:
            raise ValueError(" Insufficient available balance. Please recharge to continue.")

        self.customer.available_balance -= self.final_amount
        self.customer.save(update_fields=["available_balance"])

        self.paid_amount = self.final_amount
        self.payment_status = "Paid"
        self.pending_amount = 0


    def __str__(self):
        return f"Order {self.id} - {self.customer.name}"
    



class ScanLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="scans")
    device_id = models.CharField(max_length=255)
    location = models.CharField(max_length=255,null=True)
    delivery_address = models.CharField(max_length=255,null=True)
    scanned_at = models.DateTimeField(auto_now_add=True)
    @property
    def name(self):
        return self.device.name if self.device else None
    

# Transaction model
class Transaction(models.Model):
    PAYMENT_METHOD_CHOICES = Order.PAYMENT_METHOD_CHOICES
    id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions", null=True, blank=True)
    reference = models.CharField(max_length=20, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2,null=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    pending_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash')  
    transaction_type = models.CharField(
        max_length=50,
        choices=(('order_payment', 'Order Payment'), ('pending_clearance', 'Pending Clearance'))
    )
    created_by = models.ForeignKey(User, related_name='transactions_created', on_delete=models.SET_NULL, null=True, blank=True)
    updated_by = models.ForeignKey(User, related_name='transactions_updated', on_delete=models.SET_NULL, null=True, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)   


    def __str__(self):
        return f"Transaction {self.id} - {self.customer.name}"
        

class ScanReport(models.Model):
    device_id = models.CharField(max_length=255)
    total_scans = models.PositiveIntegerField(default=0)
    last_scanned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Scan Report"
        verbose_name_plural = "Scan Reports"

    def __str__(self):
        return f"Report for Device {self.device_id}"

    def update_report(self):
        """Recalculate total scans and last scan time from ScanLog."""
        logs = ScanLog.objects.filter(device_id=self.device_id)
        self.total_scans = logs.count()
        last = logs.order_by('-scanned_at').first()
        self.last_scanned_at = last.scanned_at if last else None
        self.save()

    

