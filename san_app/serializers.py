from rest_framework import serializers
from .models import User, Customer, Product, Device, Order, Transaction

# -------------------- User Serializer --------------------
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'username', 'password']
        extra_kwargs = {'password': {'write_only': True}}



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

# -------------------- Order Serializer --------------------
# serializers.py
from rest_framework import serializers
from .models import Order, Customer, Transaction

class OrderSerializer(serializers.ModelSerializer):
    # For response (read-only)
    product_name = serializers.CharField(source='product.name', read_only=True)
    # customer_name_display = serializers.CharField(source='customer.name', read_only=True)

    # For request (write-only)
    customer_name = serializers.CharField(write_only=True, required=False)   # for new customer
    contact_no = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Order
        fields = [
            'order_id', 'customer', 'customer_name',  
            'contact_no', 'product', 'product_name', 'category', 
            'measurement_type', 'quantity', 'unit', 
            'delivery_address', 'total_amount', 'discount', 'paid_amount',
            'pending_amount', 'payment_status', 'delivery_status', 'payment_method',
            'exported_at', 'delivered_at', 'delivered_by',
            'created_by', 'updated_by', 'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'customer': {'read_only': True},  
            'total_amount': {'read_only': True},
            'pending_amount': {'read_only': True},
        }

    def create(self, validated_data):
        user = self.context['request'].user if 'request' in self.context else None

        # 🔹 Customer creation/check by mobile
        name = validated_data.pop("customer_name", None)
        mobile = validated_data.pop("contact_no", None)

        customer, created = Customer.objects.get_or_create(
            mobile=mobile,
            defaults={"name": name or "Unknown"}
        )
        validated_data["customer"] = customer

        # 🔹 Calculate total amount
        product = validated_data['product']
        measurement_type = validated_data['measurement_type']
        quantity = validated_data.get('quantity') or 0
        unit = validated_data.get('unit') or 0

        if measurement_type == 'Quantity':
            validated_data['total_amount'] = product.price * quantity
        elif measurement_type == 'Unit':
            validated_data['total_amount'] = float(product.price) * float(unit)
        else:
            validated_data['total_amount'] = product.price

        # 🔹 Calculate pending amount
        discount = validated_data.get('discount') or 0
        paid_amount = validated_data.get('paid_amount') or 0
        validated_data['pending_amount'] = validated_data['total_amount'] - discount - paid_amount

        # 🔹 Set default statuses if not provided
        validated_data.setdefault('payment_status', 'Unpaid')
        validated_data.setdefault('delivery_status', 'Exported')

        # 🔹 Create Order
        order = super().create(validated_data)

        # 🔹 Automatically create Transaction
        Transaction.objects.create(
            customer=order.customer,
            order=order,
            total_amount=order.total_amount - discount,
            paid_amount=order.paid_amount,
            pending_amount=order.pending_amount,
            payment_method=order.payment_method,
            # created_by=user,
            # updated_by=user
        )

        return order

    def update(self, instance, validated_data):
        product = validated_data.get('product', instance.product)
        measurement_type = validated_data.get('measurement_type', instance.measurement_type)
        quantity = validated_data.get('quantity', instance.quantity)
        unit = validated_data.get('unit', instance.unit)

        # 🔹 Recalculate total_amount
        if measurement_type == 'Quantity':
            validated_data['total_amount'] = product.price * quantity
        elif measurement_type == 'Unit':
            validated_data['total_amount'] = float(product.price) * float(unit)
        else:
            validated_data['total_amount'] = product.price

        # 🔹 Recalculate pending_amount
        discount = validated_data.get('discount', instance.discount)
        paid_amount = validated_data.get('paid_amount', instance.paid_amount)
        validated_data['pending_amount'] = validated_data['total_amount'] - discount - paid_amount

        return super().update(instance, validated_data)

    def validate(self, data):
        quantity = data.get('quantity')
        unit = data.get('unit')

        # Ensure either quantity or unit is provided (not both, not none)
        if not quantity and not unit:
            raise serializers.ValidationError("Either quantity or unit must be provided.")
        if quantity is not None and unit is not None:
            raise serializers.ValidationError("You cannot provide both Quantity and Unit together.")

        # Total amount and discount cannot be negative
        if data.get('total_amount', 0) < 0 or data.get('discount', 0) < 0:
            raise serializers.ValidationError("Amounts cannot be negative.")

        # Validate payment status
        payment_choices = [choice[0] for choice in Order.PAYMENT_STATUS_CHOICES]
        if data.get('payment_status') and data['payment_status'] not in payment_choices:
            raise serializers.ValidationError({"payment_status": "Invalid payment status."})

        # Validate delivery status
        delivery_choices = [choice[0] for choice in Order.delivery_status_choices]
        if data.get('delivery_status') and data['delivery_status'] not in delivery_choices:
            raise serializers.ValidationError({"delivery_status": "Invalid delivery status."})

        return data


# -------------------- Transaction Serializer --------------------
class TransactionSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    updated_by_name = serializers.CharField(source='updated_by.name', read_only=True)
    
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    order_payment_status = serializers.CharField(source='order.payment_status', read_only=True)

    class Meta:
        model = Transaction
        fields = '__all__'





class OrderHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ['order_id', 'category', 'measurement_type',
                  'quantity', 'unit', 'total_amount', 'discount',
                  'paid_amount', 'pending_amount', 'payment_status',
                  'delivery_status', 'created_at', 'delivered_at',]
        



class ReportSerializer(serializers.Serializer):
    total_orders = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_quantity = serializers.IntegerField()