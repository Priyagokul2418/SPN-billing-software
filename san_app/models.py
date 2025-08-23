from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, ValidationError
import random
from datetime import timedelta
from django.utils import timezone
import qrcode
import qrcode
from io import BytesIO
from django.core.files import File


class User(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    username = models.EmailField(unique=True)
    password = models.CharField(max_length=255) 
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)   


    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(null=True, blank=True) 
    otp_verified_at = models.DateTimeField(null=True, blank=True)


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
    created_by = models.ForeignKey(User, related_name='customers_created', on_delete=models.SET_NULL, null=True, blank=True)
    updated_by = models.ForeignKey(User, related_name='customers_updated', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)   

    def __str__(self):
        return self.name


class Product(models.Model):
    # PRODUCT_CHOICES = [
    #     ('Bricks', 'செங்கல்'),
    #     ('Sand', 'மண் / மணல்'),
    #     ('Stone', 'கல்'),
    #     ('Gravel', 'சிறுகல்'),
    #     ('Cement', 'சிமெண்டு'),
    # ]


    MEASUREMENT_CHOICES = [
        ('Quantity', 'Quantity'),
        ('Unit', 'Unit'),
    ]

    id = models.AutoField(primary_key=True)
    product_name = models.CharField(max_length=50)   
    category = models.CharField(max_length=100) 
    measurement_type = models.CharField(max_length=20, choices=MEASUREMENT_CHOICES)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    product_code = models.CharField(max_length=20, unique=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    created_by = models.ForeignKey('User', related_name='products_created', on_delete=models.SET_NULL, null=True, blank=True)
    updated_by = models.ForeignKey('User', related_name='products_updated', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)   

    
    def save(self, *args, **kwargs):
        if not self.product_code:  
            # Category short form (first 3 letters)
            cat_prefix = self.category[:3].upper()

            # Product short form (first 3 letters of product_name)
            prod_prefix = self.product_name[:3].upper()

            # Check if this product already exists in same category
            existing = Product.objects.filter(
                category__iexact=self.category,
                product_name__iexact=self.product_name
            ).first()

            if existing:  
                # Use same code as existing product
                self.product_code = existing.product_code
            else:
                # Count how many unique product names in this category
                unique_names = (
                    Product.objects.filter(category__iexact=self.category)
                    .values_list("product_name", flat=True).distinct()
                )
                count = len(unique_names) + 1
                self.product_code = f"{cat_prefix}-{prod_prefix}{count}"

        super().save(*args, **kwargs)


    
    
    def clean(self):
        """Ensure category belongs to selected product."""
        valid_varieties = [v[0] for v in self.PRODUCT_VARIETIES.get(self.product, [])]
        if self.category not in valid_varieties:
            raise ValidationError({"category": f"{self.product} does not have variety {self.category}"})

    def __str__(self):
       return f"{self.product_name} - {self.category} ({self.measurement_type})"




# Device model
class Device(models.Model):
    device_id = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=255)
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
        ('Partially Paid', 'Partially Paid'),
]
    
    MEASUREMENT_CHOICES = [
    ('Quantity', 'Quantity'),  
    ('Unit', 'Unit'),         
]
    
    delivery_status_choices = [
    ('Pending', 'Pending'),
    ('Exported', 'Exported'),
    ('Delivered', 'Delivered')
]    
    

    PAYMENT_METHOD_CHOICES = [
        ('UPI', 'UPI'),
        ('Cash', 'Cash'),
        ('Bank', 'Bank Transfer'),
        ('Card', 'Card'),
    ]
    order_id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    category = models.CharField(max_length=255)
    measurement_type = models.CharField(max_length=20, choices=MEASUREMENT_CHOICES)
    quantity = models.PositiveIntegerField(null=True, blank=True)
    unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    contact_no = models.CharField(max_length=20)
    delivery_address = models.TextField()
    qr_code = models.ImageField(upload_to='qrcodes/', null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pending_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash')
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="Unpaid"
    )
    delivery_status = models.CharField(max_length=10, choices=delivery_status_choices, default='Pending')
    exported_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    delivered_by = models.CharField(max_length=255, null=True, blank=True) 
    
    created_by = models.ForeignKey(User, related_name='orders_created', on_delete=models.SET_NULL, null=True, blank=True)
    updated_by = models.ForeignKey(User, related_name='orders_updated', on_delete=models.SET_NULL, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True) 



    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save to get the order_id

        if not self.qr_code:
            # ✅ THIS is the only correct content
            qr_content = f"http://192.168.1.25:8000/scan_auto/?order_id={self.order_id}"
            print("✅ QR Content to encode:", qr_content)  # Debug

            qr = qrcode.make(qr_content)

            buffer = BytesIO()
            qr.save(buffer, format="PNG")
            filename = f"order_{self.order_id}.png"
            self.qr_code.save(filename, File(buffer), save=False)

            super().save(update_fields=["qr_code"])

    def __str__(self):
        return f"Order {self.id} - {self.customer.name}"
    



class ScanLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="scans")
    device_id = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    scanned_at = models.DateTimeField(auto_now_add=True)

# Transaction model
class Transaction(models.Model):
    PAYMENT_METHOD_CHOICES = Order.PAYMENT_METHOD_CHOICES
    id = models.AutoField(primary_key=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions", null=True, blank=True)
    reference = models.CharField(max_length=20, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2)
    pending_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, default='Cash')  
    created_by = models.ForeignKey(User, related_name='transactions_created', on_delete=models.SET_NULL, null=True, blank=True)
    updated_by = models.ForeignKey(User, related_name='transactions_updated', on_delete=models.SET_NULL, null=True, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)  
    updated_at = models.DateTimeField(auto_now=True)   


    def __str__(self):
        return f"Transaction {self.id} - {self.customer.name}"