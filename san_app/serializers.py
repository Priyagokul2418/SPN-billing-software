from rest_framework import serializers
from .models import User, Customer, Product, Device, Order, Transaction,ScanLog
from decimal import Decimal, InvalidOperation 
from django.utils import timezone

# -------------------- User Serializer --------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}
    
    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value



class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

class ForgotPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()

class ResetPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()
    otp = serializers.CharField()
    new_password = serializers.CharField()
    confirm_password = serializers.CharField()


# -------------------- Customer Serializer --------------------
class CustomerSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Customer
        fields = '__all__'

# -------------------- Product Serializer --------------------
class ProductSerializer(serializers.ModelSerializer):
  
   
    class Meta:
        model = Product
        fields = '__all__'

# -------------------- Device Serializer --------------------
class DeviceSerializer(serializers.ModelSerializer):
   
   
    class Meta:
        model = Device
        fields = '__all__'


class DeviceLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()
   



class ScanLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScanLog
        fields = "__all__"



# -------------------- Order Serializer --------------------


from decimal import Decimal


def to_dec(v):
    if v is None:
        return Decimal('0.00')
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0.00')

from decimal import Decimal

class OrderSerializer(serializers.ModelSerializer):
    # Response-only computed fields
    # ---------- Computed fields ----------
    total_amount = serializers.SerializerMethodField()
    final_amount = serializers.SerializerMethodField()
    pending_amount = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    alert = serializers.SerializerMethodField()
    refund_status = serializers.SerializerMethodField()
    # ---------- Response read-only ----------
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    customer_name_display = serializers.CharField(source="customer.name", read_only=True)

    # ---------- Request write-only ----------
    customer_name_input = serializers.CharField(write_only=True, required=False)
    customer_name = serializers.CharField(write_only=True, required=False)
    contact_no = serializers.CharField(write_only=True, required=True)


    class Meta:
        model = Order
        fields = [
            'order_id', 'customer', 'customer_name','customer_name_input','customer_name_display',
            'contact_no', 'product', 'product_name', 'category',
            'measurement_type', 'quantity', 'unit',
            'delivery_address', 'total_amount', 'discount', 'final_amount',
            'paid_amount', 'pending_amount', 'payment_status', 'delivery_status', 'payment_method',
            'exported_at', 'delivered_at', 'delivered_by',
            'pass_no', 'amount_per_pass', 'pass_amount',
            'alert', "refund_status", 
            'created_by', 'updated_by', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'customer': {'read_only': True},
        }

    # ---------- Computed fields ----------
    def get_total_amount(self, obj):
        price = to_dec(getattr(obj.product, 'price', 0))
        mtype = getattr(obj, 'measurement_type', None)
        qty = to_dec(getattr(obj, 'quantity', 0) or 0)
        unit = to_dec(getattr(obj, 'unit', 0) or 0)
        if mtype == 'Quantity':
            total = price * qty
        elif mtype == 'Unit':
            total = price * unit
        else:
            total = price
        return str(total.quantize(Decimal('0.01')))

    def get_final_amount(self, obj):
        total = to_dec(self.get_total_amount(obj))
        discount = to_dec(getattr(obj, 'discount', 0) or 0)
        pass_amount = to_dec(getattr(obj, 'pass_amount', 0) or 0)
        final = (total + pass_amount) - discount
        return str(final.quantize(Decimal('0.01')))

    def get_pending_amount(self, obj):
        final = to_dec(self.get_final_amount(obj))
        paid = to_dec(getattr(obj, 'paid_amount', 0) or 0)
        pending = final - paid
        if pending < 0:
            pending = Decimal('0.00')  # ✅ no negatives
        return str(pending.quantize(Decimal('0.01')))
        

    def get_payment_status(self, obj):
        final = to_dec(getattr(obj, "final_amount", 0))
        paid = to_dec(getattr(obj, "paid_amount", 0))

        if paid == Decimal("0.00"):
            return "Unpaid"
        elif paid == final:
            return "Paid"
        elif paid < final:
            return "Pending"
        else:
           
            return "Paid"


    def get_alert(self, obj):
        if not obj.customer:
            return None
        previous_orders = Order.objects.filter(customer=obj.customer).exclude(order_id=obj.order_id)
        if not previous_orders.exists():
            return None
        total_pending = sum(to_dec(o.pending_amount) for o in previous_orders) + to_dec(obj.pending_amount)
        credit_limit = to_dec(getattr(obj.customer, 'credit_limit', 0))
        if total_pending > credit_limit:
            return f"இந்த வாடிக்கையாளருக்கு முன் பாக்கிய தொகை {total_pending} உள்ளது. கடன் வரம்பு {credit_limit}. உறுதிப்படுத்த விரும்புகிறீர்களா?"
        return None
    

    def refund(self, refund_amount):
        """
        Process refund directly from serializer
        """
        if not self.instance:
            raise serializers.ValidationError("Order instance required to process refund.")

        try:
            refund_amount = Decimal(refund_amount)
        except (InvalidOperation, TypeError):
            raise serializers.ValidationError("Invalid refund amount.")

        self.instance.process_refund(refund_amount)
        return self.instance
    

    
    # ---------- Create ----------
    def create(self, validated_data):
        customer_id = self.initial_data.get("customer")
        if customer_id:
            customer = Customer.objects.get(pk=customer_id)
        else:
            name = self.initial_data.get("customer_name")
            mobile = validated_data.pop("contact_no", None)

            # mobile already exists check
            existing_customer = Customer.objects.filter(mobile=mobile).first()
            if existing_customer:
                raise serializers.ValidationError(
                    {"contact_no": f"Customer with mobile {mobile} already exists."}
            
                )

            # if not exists → create
            customer = Customer.objects.create(
                name=name or "Unknown",
                mobile=mobile
            )

        validated_data["customer"] = customer
        validated_data.pop("customer_name", None)   # remove so Order.objects.create won’t explode

        # return super().create(validated_data)

        # compute amounts
        product = validated_data['product']
        mtype = validated_data['measurement_type']
        qty = to_dec(validated_data.get('quantity') or 0)
        unit = to_dec(validated_data.get('unit') or 0)
        price = to_dec(product.price)

        if mtype == 'Quantity':
            total = price * qty
        elif mtype == 'Unit':
            total = price * unit
        else:
            total = price

        discount = to_dec(validated_data.get('discount') or 0)
        paid = to_dec(validated_data.get('paid_amount') or 0)
        pass_no = to_dec(validated_data.get('pass_no') or 0)
        amount_per_pass = to_dec(validated_data.get('amount_per_pass') or 0)
        pass_amount = pass_no * amount_per_pass

        final = (total + pass_amount) - discount
        pending = final - paid
        if pending < 0:
            pending = Decimal("0.00")
        
    
        validated_data['total_amount'] = total.quantize(Decimal('0.01'))
        validated_data['pass_amount'] = pass_amount.quantize(Decimal('0.01'))
        validated_data['final_amount'] = final.quantize(Decimal('0.01'))
        validated_data['pending_amount'] = pending.quantize(Decimal('0.01'))
        validated_data.setdefault('delivery_status', 'Exported')

        order = super().create(validated_data)

        # ✅ create linked transaction
        Transaction.objects.create(
            customer=order.customer,
            order=order,
            total_amount=order.final_amount,
            paid_amount=order.paid_amount,
            pending_amount=order.pending_amount,
            payment_method=order.payment_method,
        )
        return order



    # ---------- Update ----------
    def update(self, instance, validated_data):
        product = validated_data.get('product', instance.product)
        mtype = validated_data.get('measurement_type', instance.measurement_type)
        qty = to_dec(validated_data.get('quantity', instance.quantity) or 0)
        unit = to_dec(validated_data.get('unit', instance.unit) or 0)
        price = to_dec(product.price)

        if mtype == 'Quantity':
            total = price * qty
        elif mtype == 'Unit':
            total = price * unit
        else:
            total = price

        discount = to_dec(validated_data.get('discount', instance.discount))
        pass_no = to_dec(validated_data.get('pass_no', instance.pass_no or 0))
        amount_per_pass = to_dec(validated_data.get('amount_per_pass', instance.amount_per_pass or 0))
        pass_amount = pass_no * amount_per_pass

        final = (total + pass_amount) - discount

        if 'paid_amount' in validated_data:
            paid_amount = to_dec(validated_data['paid_amount'])
        else:
            paid_amount = to_dec(instance.paid_amount)

        pending = final - paid_amount
        if pending < 0:
            pending = Decimal('0.00')

        validated_data['total_amount'] = total.quantize(Decimal('0.01'))
        validated_data['final_amount'] = final.quantize(Decimal('0.01'))
        validated_data['paid_amount'] = paid_amount.quantize(Decimal('0.01'))
        validated_data['pending_amount'] = pending.quantize(Decimal('0.01'))
        validated_data['pass_amount'] = pass_amount.quantize(Decimal('0.01'))

        instance = super().update(instance, validated_data)

        # ✅ Sync transaction on every update
        Transaction.objects.update_or_create(
            order=instance,
            defaults={
                "customer": instance.customer,
                "total_amount": instance.final_amount,
                "paid_amount": instance.paid_amount,
                "pending_amount": instance.pending_amount,
                "payment_method": instance.payment_method,
                "updated_at": timezone.now(),
            },
        )

        return instance

    # ---------- Persist numbers on update ----------
    def update(self, instance, validated_data):
        product = validated_data.get('product', instance.product)
        mtype = validated_data.get('measurement_type', instance.measurement_type)
        qty = to_dec(validated_data.get('quantity', instance.quantity) or 0)
        unit = to_dec(validated_data.get('unit', instance.unit) or 0)
        price = to_dec(product.price)

        # Calculate new total
        if mtype == 'Quantity':
            total = price * qty
        elif mtype == 'Unit':
            total = price * unit
        else:
            total = price

        discount = to_dec(validated_data.get('discount', instance.discount))
        final = total - discount

        # ✅ keep old paid unless explicitly updated
        if 'paid_amount' in validated_data:
            paid_amount = to_dec(validated_data['paid_amount'])
        else:
            paid_amount = to_dec(instance.paid_amount)

        # ✅ recalc pending
        pending = final - paid_amount
        if pending < 0:
            pending = Decimal('0.00')

        validated_data['total_amount'] = total.quantize(Decimal('0.01'))
        validated_data['final_amount'] = final.quantize(Decimal('0.01'))
        validated_data['paid_amount'] = paid_amount.quantize(Decimal('0.01'))
        validated_data['pending_amount'] = pending.quantize(Decimal('0.01'))

        instance = super().update(instance, validated_data)

        # ✅ Sync related Transaction
        Transaction.objects.update_or_create(
            order=instance,
            customer=instance.customer,
            defaults={
                "total_amount": instance.final_amount,
                "paid_amount": instance.paid_amount,
                "pending_amount": max(instance.pending_amount, Decimal("0.00")),
                "payment_method": instance.payment_method,
                "updated_at": timezone.now(),
            },
        )

        return instance
    

    # def validate(self, attrs):
    #     # get paid_amount and final_amount (old or new)
    #     paid = to_dec(attrs.get("paid_amount") or getattr(self.instance, "paid_amount", 0))
        
    #     # final_amount ah compute panna porom create/update logic la, 
    #     # so ippo approximate ah calculate panna vendiyathu
    #     product = attrs.get("product") or getattr(self.instance, "product", None)
    #     mtype = attrs.get("measurement_type") or getattr(self.instance, "measurement_type", None)
    #     qty = to_dec(attrs.get("quantity") or getattr(self.instance, "quantity", 0))
    #     unit = to_dec(attrs.get("unit") or getattr(self.instance, "unit", 0))
    #     price = to_dec(getattr(product, "price", 0))

    #     if mtype == "Quantity":
    #         total = price * qty
    #     elif mtype == "Unit":
    #         total = price * unit
    #     else:
    #         total = price

    #     discount = to_dec(attrs.get("discount") or getattr(self.instance, "discount", 0))
    #     pass_no = to_dec(attrs.get("pass_no") or getattr(self.instance, "pass_no", 0))
    #     amount_per_pass = to_dec(attrs.get("amount_per_pass") or getattr(self.instance, "amount_per_pass", 0))
    #     pass_amount = pass_no * amount_per_pass

    #     final = (total + pass_amount) - discount

    #     # ✅ Validation
    #     if paid > final:
    #         raise serializers.ValidationError(
    #               {"paid_amount": "செலுத்திய தொகை இறுதி தொகையை விட அதிகமாக இருக்க முடியாது."}            )

    #     return attrs




# -------------------- Transaction Serializer -----------------------


class TransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    order_payment_status = serializers.SerializerMethodField()

    # We override these so they ALWAYS come from the related Order
    final_amount = serializers.SerializerMethodField()
    pending_amount = serializers.SerializerMethodField()
    total_amount = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = [
            "id",
            "customer_name",
            "order_payment_status",
            "final_amount",
            "reference",
            "total_amount",
            "paid_amount",
            "pending_amount",
            "payment_method",
            "paid_at",
            "updated_at",
            "customer",
            "order",
            "created_by",
            "updated_by",
        ]

    def _fresh_order(self, obj):
        """Fetch a fresh Order instance from DB to avoid cached/stale values."""
        if not getattr(obj, "order_id", None):
            return None
        try:
            return Order.objects.get(pk=obj.order_id)
        except Order.DoesNotExist:
            return None

    def get_final_amount(self, obj):
        order = self._fresh_order(obj)
        if not order:
            return None
        # order.final_amount from DB + order.pass_amount (both Decimal fields)
        order_final = Decimal(order.final_amount or 0)
        pass_amount = Decimal(order.pass_amount or 0)
        result = order_final + pass_amount
        return str(result.quantize(Decimal("0.01")))

    def get_total_amount(self, obj):
        order = self._fresh_order(obj)
        if not order:
            return None
        total = Decimal(order.total_amount or 0)
        return str(total.quantize(Decimal("0.01")))
    
    def get_pending_amount(self, obj):
        order = self._fresh_order(obj)
        if not order:
            return None

        final = Decimal(self.get_final_amount(obj) or "0")  # recomputed final (order.final_amount + pass_amount)
        paid = Decimal(obj.paid_amount or 0)
        pending = final - paid
        if pending < 0:
            pending = Decimal("0.00")
        return str(pending.quantize(Decimal("0.01")))

    def get_order_payment_status(self, obj):
        final = Decimal(self.get_final_amount(obj) or "0")
        paid = Decimal(obj.paid_amount or 0)
        if paid == Decimal("0.00"):
            return "Unpaid"
        elif paid >= final:
            return "Paid"
        else:
            return "Pending"




class OrderHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ['order_id', 'category', 'measurement_type',
                  'quantity', 'unit', 'total_amount', 'discount',
                  'paid_amount', 'pending_amount', 'payment_status',
                  'delivery_status', 'created_at', 'delivered_at',]
        



class OrderReceiptSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    city = serializers.CharField(source='customer.city', default='-', read_only=True)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    operator = serializers.CharField(source='created_by.username', default='Admin', read_only=True)
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'order_id',
            'payment_method',
            'customer_name',
            'city',
            'product_name',
            'category',
            'quantity',
            'unit',
            'total_amount',
            'paid_amount',
            'pending_amount',
            'payment_status',
            'operator',
            'qr_code_url',
        ]

    def get_qr_code_url(self, obj):
        request = self.context.get('request')
        if obj.qr_code and request:
            return request.build_absolute_uri(obj.qr_code.url)
        return None



class ReportSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_quantity = serializers.IntegerField()