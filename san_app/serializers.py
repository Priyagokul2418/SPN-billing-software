from rest_framework import serializers
from .models import User, Customer, Product, Device, Order, Transaction,ScanLog,ScanReport
from decimal import Decimal, InvalidOperation 
from django.utils import timezone
from django.db.models import Sum
from django.db import models
from decimal import Decimal


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


# -------------------- Customer Serializer ------------------
class CustomerSerializer(serializers.ModelSerializer):
    total_pending_amount = serializers.SerializerMethodField()
    
    
    class Meta:
        model = Customer
        fields = '__all__'
    def get_total_pending_amount(self, obj):
        if not obj:
            return "0.00"
        total_pending = (
            Order.objects.filter(customer=obj)
            .aggregate(total=Sum("pending_amount"))["total"] or Decimal("0.00")
        )
        return str(total_pending.quantize(Decimal("0.01")))

# -------------------- Product Serializer ------------------
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



def to_dec(v):
    if v is None:
        return Decimal('0.00')
    if isinstance(v, Decimal):
        return v
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0.00')
        
        
class OrderSerializer(serializers.ModelSerializer):
    # Response-only computed fields (override any stale DB values)
    total_amount = serializers.SerializerMethodField()
    final_amount = serializers.SerializerMethodField()
    pending_amount = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    customer_total_pending = serializers.SerializerMethodField()

    customer_available_balance = serializers.SerializerMethodField()
    refund_amount = serializers.SerializerMethodField()
    refund_status = serializers.SerializerMethodField()
    refund_method = serializers.SerializerMethodField()
    customer_mobile = serializers.CharField(source="customer.mobile", read_only=True)  # 
    # ---------- Response read-only ----------
    product_name = serializers.CharField(source="product.product_name", read_only=True)
    category = serializers.CharField(source='product.category', read_only=True)
    customer_name_display = serializers.CharField(source="customer.name", read_only=True)
    customer_total_pending = serializers.SerializerMethodField()

    customer_available_balance = serializers.SerializerMethodField()
    credit_limit_alert = serializers.SerializerMethodField()

    
    # For response (read-only)
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    customer_name_display = serializers.CharField(source='customer.name', read_only=True)
    

    # For request (write-only)
    customer_name = serializers.CharField(write_only=True, required=False)
    contact_no = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = Order
        ordering = ["-exported_at"] 
        fields = [
            'order_id', 'customer', 'customer_name', 'customer_name_display','customer_mobile', 
            'contact_no', 'product', 'product_name', 'category','order_status',
            'measurement_type', 'quantity', 'unit','refund_method','refund_amount','refund_status','ton',
            'delivery_address', 'total_amount', 'discount', 'final_amount',
            'paid_amount', 'pending_amount', 'payment_status', 'delivery_status', 'payment_method',
            'exported_at', 'delivered_at', 'delivered_by',
            'pass_no', 'amount_per_pass', 'pass_amount',  "customer_available_balance",'customer_total_pending', 
            'created_by', 'updated_by', 'exported_at', 'updated_at','credit_limit_alert'
        ]
        extra_kwargs = {
            'customer': {'read_only': True},
        }

    # ---------- Response computations ----------
    def get_customer_available_balance(self, obj):
        if obj.customer and hasattr(obj.customer, "available_balance"):
            return str(obj.customer.available_balance.quantize(Decimal("0.01")))
        return "0.00"
    
    def get_customer_total_pending(self, obj):
        if not obj.customer:
            return "0.00"
        total_pending = (
            Order.objects.filter(customer=obj.customer)
            .aggregate(total=Sum("pending_amount"))["total"] or Decimal("0.00")
        )
        return str(total_pending.quantize(Decimal("0.01")))
    
    def get_credit_limit_alert(self, obj):
         return getattr(obj, 'credit_limit_alert', None)
    
    def get_total_amount(self, obj):
        price = to_dec(getattr(obj.product, 'price', 0))
        mtype = getattr(obj, 'measurement_type', None)
        qty = to_dec(getattr(obj, 'quantity', 0) or 0)
        unit = to_dec(getattr(obj, 'unit', 0) or 0)
        ton = to_dec(getattr(obj, 'ton', 0) or 0)

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
        
    def get_refund_amount(self, obj):
        refunded = to_dec(getattr(obj, 'refunded_amount', 0))
        return str(refunded.quantize(Decimal('0.01')))

    def get_pending_amount(self, obj):
        final = to_dec(self.get_final_amount(obj))
        paid = to_dec(getattr(obj, 'paid_amount', 0) or 0)
        pending = final - paid
        if pending < Decimal("0.00"):
            pending = Decimal("0.00")
        return str(pending.quantize(Decimal('0.01')))

    def get_payment_status(self, obj):
        final = to_dec(self.get_final_amount(obj))
        paid = to_dec(getattr(obj, 'paid_amount', 0) or 0)
        if paid == Decimal('0.00'):
            return "Unpaid"
        elif paid < final:
            return "Pending"
        else:
            return "Paid"
    
    def refund(self, refund_amount):
        if not self.instance:
            raise serializers.ValidationError("Order instance required to process refund.")

        try:
            refund_amount = Decimal(refund_amount)
        except (InvalidOperation, TypeError):
            raise serializers.ValidationError("Invalid refund amount.")

        self.instance.process_refund(refund_amount)
        return self.instance
    
    
    def get_refund_status(self, obj):
        paid = to_dec(obj.paid_amount)
        refunded = to_dec(obj.refunded_amount)

        if refunded == Decimal("0.00"):
            return "Not Refunded"
        elif refunded < paid:
            return "Partially Refunded"
        elif refunded == paid:
            return "Refunded"
        return "Not Refunded"
        

    def get_refund_method(self, obj):
        return getattr(obj, "refund_method", None)
        


# ---------- Validation to check available balance ----------

    def validate(self, attrs):
        mobile = attrs.get('contact_no')
        paid_amount_input = to_dec(attrs.get('paid_amount', 0))

        if mobile:
            try:
                customer = Customer.objects.get(mobile=mobile)
                available_balance = to_dec(customer.available_balance)
                credit_limit = to_dec(getattr(customer, 'credit_limit', 0))
                product = attrs.get('product')
                mtype = attrs.get('measurement_type')
                qty = to_dec(attrs.get('quantity', 0) or 0)
                unit = to_dec(attrs.get('unit', 0) or 0)
                ton = to_dec(attrs.get('ton', 0) or 0)
                price = to_dec(product.price) if product else Decimal('0.00')

                if mtype == 'Quantity':
                  total = price * qty
                elif mtype == 'Unit':
                  total = price * unit
                elif mtype == 'Ton':
                  total = price * ton
                else:
                  total = price

                discount = to_dec(attrs.get('discount', 0))
                pass_no = to_dec(attrs.get('pass_no', 0))
                amount_per_pass = to_dec(attrs.get('amount_per_pass', 0))
                pass_amount = pass_no * amount_per_pass
                final_amount = (total + pass_amount) - discount

            
                pending_orders = Order.objects.filter(
                    customer=customer, 
                    pending_amount__gt=0
                ).aggregate(total_pending=models.Sum('pending_amount'))
                current_total_pending = to_dec(pending_orders.get('total_pending') or 0)

         
                if credit_limit > 0 and current_total_pending > credit_limit:
                    excess_amount = current_total_pending - credit_limit
                    self.context['credit_limit_alert'] = {
                        'customer': customer.name,
                        'current_pending': str(current_total_pending.quantize(Decimal('0.01'))),
                        'credit_limit': str(credit_limit.quantize(Decimal('0.01'))),
                        'excess_amount': str(excess_amount.quantize(Decimal('0.01'))),
                        'message': (
                            f" Credit limit reached! Customer '{customer.name}' has ₹{current_total_pending} pending, "
                            f"which exceeds the credit limit of ₹{credit_limit} by ₹{excess_amount}. "
                            f"Please clear dues or confirm before placing new orders."
                        )
                    }

           
                if paid_amount_input == Decimal('0.00') and available_balance < final_amount:
                    remaining_needed = final_amount - available_balance
                    self.context['balance_info'] = {
                        'available_balance': str(available_balance.quantize(Decimal('0.01'))),
                        'order_amount': str(final_amount.quantize(Decimal('0.01'))),
                        'remaining_needed': str(remaining_needed.quantize(Decimal('0.01'))),
                        'message': (
                            f"Available balance ₹{available_balance} is less than order amount ₹{final_amount}. "
                            f"Remaining ₹{remaining_needed} will be set as pending."
                        )
                    }

            except Customer.DoesNotExist:
                pass

        return attrs
                    
            
    def create(self, validated_data):
        print("DEBUG: Starting create method")
        print(f"DEBUG: validated_data type: {type(validated_data)}")
        print(f"DEBUG: validated_data keys: {list(validated_data.keys())}")
        
        try:
            name = validated_data.pop("customer_name", None)
            mobile = validated_data.pop("contact_no", None)
            customer, _ = Customer.objects.get_or_create(
                mobile=mobile, defaults={"name": name or "Unknown"}
            )
            validated_data["customer"] = customer
    
            # Calculate order amounts
            product = validated_data['product']
            mtype = validated_data['measurement_type']
            qty = to_dec(validated_data.get('quantity') or 0)
            unit = to_dec(validated_data.get('unit') or 0)
            ton = to_dec(validated_data.get('ton') or 0) 
            price = to_dec(product.price)
    
            if mtype == 'Quantity':
                total = price * qty
            elif mtype == 'Unit':
                total = price * unit
            elif mtype == 'Ton':
                total = price * ton
            else:
                total = price
    
            discount = to_dec(validated_data.get('discount') or 0)
            cash_paid_by_customer = to_dec(validated_data.get('paid_amount') or 0) 
    
            pass_no = to_dec(validated_data.get('pass_no') or 0)
            amount_per_pass = to_dec(validated_data.get('amount_per_pass') or 0)
            pass_amount = pass_no * amount_per_pass
    
            final_amount = (total + pass_amount) - discount
            available_balance = to_dec(customer.available_balance)
    
            print(f" CUSTOMER PAID: ₹{cash_paid_by_customer}, FINAL AMOUNT: ₹{final_amount}, AVAILABLE BALANCE: ₹{available_balance}")
    
            amount_used_from_balance = Decimal('0.00')
            total_paid_for_order = cash_paid_by_customer
            pending_amount_for_order = final_amount - cash_paid_by_customer
    
            # 1. AUTO USE BALANCE IF NEEDED
            if pending_amount_for_order > Decimal('0.00') and available_balance > Decimal('0.00'):
                balance_to_use = min(available_balance, pending_amount_for_order)
                amount_used_from_balance = balance_to_use
                total_paid_for_order += balance_to_use
                pending_amount_for_order -= balance_to_use
                customer.available_balance = available_balance - balance_to_use
                customer.save(update_fields=['available_balance'])
                print(f"AUTO BALANCE USE: ₹{balance_to_use} from available balance")
    
            # 2. EXCESS PAYMENT HANDLING
            excess_amount = Decimal('0.00')
            if cash_paid_by_customer > final_amount:
                excess_amount = cash_paid_by_customer - final_amount
                print(f"EXCESS DETECTED: ₹{excess_amount}")
    
                # Clear pending orders with excess (SILENT)
                pending_orders = Order.objects.filter(
                    customer=customer, 
                    pending_amount__gt=0
                ).exclude(order_id=getattr(validated_data.get('order_id'), 'order_id', None)).order_by('exported_at')
                
                if pending_orders.exists():
                    remaining_excess = excess_amount
                    for order in pending_orders:
                        if remaining_excess <= 0:
                            break
                            
                        current_pending = to_dec(order.pending_amount)
                        amount_to_clear = min(current_pending, remaining_excess)
                        
                        # Update pending order (SILENT)
                        order.paid_amount = to_dec(order.paid_amount) + amount_to_clear
                        order.pending_amount = current_pending - amount_to_clear
                        order.save(update_fields=['paid_amount', 'pending_amount'])
                        
                        remaining_excess -= amount_to_clear
                        print(f"CLEARED PENDING: ₹{amount_to_clear} from order {order.order_id}")
                    
                    # Add remaining excess to balance (SILENT)
                    if remaining_excess > 0:
                        customer.available_balance = to_dec(customer.available_balance) + remaining_excess
                        customer.save(update_fields=['available_balance'])
                        print(f"ADDED TO BALANCE: ₹{remaining_excess}")
                else:
                    # No pending orders, add all excess to balance (SILENT)
                    customer.available_balance = to_dec(customer.available_balance) + excess_amount
                    customer.save(update_fields=['available_balance'])
                    print(f"ADDED TO BALANCE: ₹{excess_amount}")
    
                # Adjust current order amounts
                total_paid_for_order = final_amount
                pending_amount_for_order = Decimal('0.00')
    
            # Ensure pending amount is not negative
            if pending_amount_for_order < Decimal('0.00'):
                pending_amount_for_order = Decimal('0.00')
    
            # Set order data
            validated_data['total_amount'] = total.quantize(Decimal('0.01'))
            validated_data['pass_amount'] = pass_amount.quantize(Decimal('0.01'))
            validated_data['final_amount'] = final_amount.quantize(Decimal('0.01'))
            validated_data['pending_amount'] = pending_amount_for_order.quantize(Decimal('0.01'))
            validated_data['paid_amount'] = total_paid_for_order.quantize(Decimal('0.01'))  # TOTAL PAID (CASH + BALANCE)
            validated_data.setdefault('delivery_status', 'Exported')
            validated_data.setdefault('payment_method', 'Cash')
    
            # Create the order
            try:
                order = Order.objects.create(
                    customer=validated_data['customer'],
                    product=validated_data['product'],
                    measurement_type=validated_data['measurement_type'],
                    quantity=validated_data.get('quantity'),
                    unit=validated_data.get('unit'),
                    ton=validated_data.get('ton'),
                    total_amount=validated_data['total_amount'],
                    final_amount=validated_data['final_amount'],
                    paid_amount=validated_data['paid_amount'],  # TOTAL PAID
                    pending_amount=validated_data['pending_amount'],
                    discount=validated_data.get('discount', Decimal('0.00')),
                    pass_no=validated_data.get('pass_no', 0),
                    amount_per_pass=validated_data.get('amount_per_pass', Decimal('0.00')),
                    pass_amount=validated_data['pass_amount'],
                    delivery_status=validated_data.get('delivery_status', 'Exported'),
                    payment_method=validated_data.get('payment_method', 'Cash'),
                    order_status='Booked'
                )
            except Exception as e:
                print(f"DEBUG: Order creation failed: {e}")
                order = super().create(validated_data)
    
            # ========== ONLY ONE TRANSACTION - SHOW ACTUAL CASH PAID ==========
            Transaction.objects.create(
                customer=order.customer,
                order=order,
                total_amount=order.final_amount,
                paid_amount=cash_paid_by_customer,  
                pending_amount=order.pending_amount,
                payment_method=validated_data.get('payment_method', 'Cash'),
                transaction_type="order_payment", 
                reference=f"Order {order.order_id}",
                paid_at=timezone.now(),
            )
    
            print(f"TRANSACTION CREATED: Customer paid ₹{cash_paid_by_customer} in cash")
            print(f"ORDER SUMMARY: Total Paid ₹{total_paid_for_order} (Cash: ₹{cash_paid_by_customer} + Balance: ₹{amount_used_from_balance}), Pending: ₹{pending_amount_for_order}")
            print(f"CUSTOMER BALANCE: ₹{customer.available_balance}")
            if hasattr(self, 'context'):
                if 'credit_limit_alert' in self.context:
                    order.credit_limit_alert = self.context['credit_limit_alert']
                if 'balance_info' in self.context:
                    order.balance_info = self.context['balance_info']
    
            print(f"FINAL RESULT: Customer balance: {customer.available_balance}, Order paid: {order.paid_amount}, Order pending: {order.pending_amount}")
    
            return order
    
        except Exception as e:
            print(f"DEBUG: Create method failed completely: {e}")
            import traceback
            print(f"DEBUG: Full traceback: {traceback.format_exc()}")
            raise
    
    def update(self, instance, validated_data):
        # Store old values for comparison
        old_paid_amount = to_dec(instance.paid_amount)
        old_final_amount = to_dec(instance.final_amount)
        old_customer = instance.customer
        
        name = validated_data.pop("customer_name", None)
        mobile = validated_data.pop("contact_no", None)
        
        if mobile:
            customer, _ = Customer.objects.get_or_create(
                mobile=mobile, defaults={"name": name or "Unknown"}
            )
            validated_data["customer"] = customer
        else:
            customer = instance.customer
        
        product = validated_data.get('product', instance.product)
        mtype = validated_data.get('measurement_type', instance.measurement_type)
        qty = to_dec(validated_data.get('quantity') or instance.quantity or 0)
        unit = to_dec(validated_data.get('unit') or instance.unit or 0)
        ton = to_dec(validated_data.get('ton') or instance.ton or 0)
        price = to_dec(product.price)
    
        if mtype == 'Quantity':
            total = price * qty
        elif mtype == 'Unit':
            total = price * unit
        elif mtype == 'Ton':
            total = price * ton
        else:
            total = price
    
        discount = to_dec(validated_data.get('discount') or instance.discount or 0)
        cash_paid_by_customer = to_dec(validated_data.get('paid_amount') or instance.paid_amount or 0)  # ACTUAL CASH PAID
    
        pass_no = to_dec(validated_data.get('pass_no') or instance.pass_no or 0)
        amount_per_pass = to_dec(validated_data.get('amount_per_pass') or instance.amount_per_pass or 0)
        pass_amount = pass_no * amount_per_pass
    
        final_amount = (total + pass_amount) - discount
        available_balance = to_dec(customer.available_balance)
    
        print(f" UPDATE DEBUG: OLD Paid: ₹{old_paid_amount}, NEW Cash: ₹{cash_paid_by_customer}, Final: ₹{final_amount}, Balance: ₹{available_balance}")
    
        if old_customer == customer:
            old_balance_used = max(Decimal('0.00'), old_final_amount - old_paid_amount)
            if old_balance_used > Decimal('0.00'):
                customer.available_balance = to_dec(customer.available_balance) + old_balance_used
                customer.save(update_fields=['available_balance'])
                print(f" REVERTED OLD BALANCE: ₹{old_balance_used}")
    
        amount_used_from_balance = Decimal('0.00')
        total_paid_for_order = cash_paid_by_customer
        pending_amount_for_order = final_amount - cash_paid_by_customer
    
        # 1. AUTO USE BALANCE IF NEEDED
        if pending_amount_for_order > Decimal('0.00') and available_balance > Decimal('0.00'):
            balance_to_use = min(available_balance, pending_amount_for_order)
            amount_used_from_balance = balance_to_use
            total_paid_for_order += balance_to_use
            pending_amount_for_order -= balance_to_use
    
            customer.available_balance = available_balance - balance_to_use
            customer.save(update_fields=['available_balance'])
            print(f" AUTO BALANCE USE: ₹{balance_to_use} from available balance")
    
        # 2. EXCESS PAYMENT HANDLING
        excess_amount = Decimal('0.00')
        if cash_paid_by_customer > final_amount:
            excess_amount = cash_paid_by_customer - final_amount
            print(f" EXCESS DETECTED: ₹{excess_amount}")
            pending_orders = Order.objects.filter(
                customer=customer, 
                pending_amount__gt=0
            ).exclude(order_id=instance.order_id).order_by('exported_at')
            
            if pending_orders.exists():
                remaining_excess = excess_amount
                for order in pending_orders:
                    if remaining_excess <= 0:
                        break
                        
                    current_pending = to_dec(order.pending_amount)
                    amount_to_clear = min(current_pending, remaining_excess)
                    order.paid_amount = to_dec(order.paid_amount) + amount_to_clear
                    order.pending_amount = current_pending - amount_to_clear
                    order.save(update_fields=['paid_amount', 'pending_amount'])
                    remaining_excess -= amount_to_clear
                    print(f" CLEARED PENDING: ₹{amount_to_clear} from order {order.order_id}")
                
        
                if remaining_excess > 0:
                    customer.available_balance = to_dec(customer.available_balance) + remaining_excess
                    customer.save(update_fields=['available_balance'])
                    print(f" ADDED TO BALANCE: ₹{remaining_excess}")
            else:
                customer.available_balance = to_dec(customer.available_balance) + excess_amount
                customer.save(update_fields=['available_balance'])
                print(f" ADDED TO BALANCE: ₹{excess_amount}")

            total_paid_for_order = final_amount
            pending_amount_for_order = Decimal('0.00')

        if pending_amount_for_order < Decimal('0.00'):
            pending_amount_for_order = Decimal('0.00')
    
        validated_data['total_amount'] = total.quantize(Decimal('0.01'))
        validated_data['pass_amount'] = pass_amount.quantize(Decimal('0.01'))
        validated_data['final_amount'] = final_amount.quantize(Decimal('0.01'))
        validated_data['pending_amount'] = pending_amount_for_order.quantize(Decimal('0.01'))
        validated_data['paid_amount'] = total_paid_for_order.quantize(Decimal('0.01'))
        
        delivery_status = validated_data.get("delivery_status", instance.delivery_status)
    
        if delivery_status == "Cancelled":
            validated_data['order_status'] = "Cancelled"
    
        if delivery_status == "Delivered" and instance.delivery_status == "Delivered":
            validated_data['delivered_at'] = timezone.now()
    
        print(f" UPDATE FINAL DEBUG: Total paid: {total_paid_for_order} (Cash: {cash_paid_by_customer} + Balance: {amount_used_from_balance}), pending: {pending_amount_for_order}")
    
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
    
        # ========== TRANSACTION HANDLING ==========
        Transaction.objects.filter(order=instance).delete()
        
        # ========== ONLY ONE TRANSACTION - SHOW ACTUAL CASH PAID ==========
        Transaction.objects.create(
            customer=instance.customer,
            order=instance,
            total_amount=instance.final_amount,
            paid_amount=cash_paid_by_customer,  
            pending_amount=instance.pending_amount,
            payment_method=validated_data.get('payment_method', instance.payment_method),
            transaction_type="order_payment",
            reference=f"Order {instance.order_id} (Updated)",
            paid_at=timezone.now(),
        )
        print(f"TRANSACTION UPDATED: Customer paid ₹{cash_paid_by_customer} in cash")
    
        print(f" ORDER SUMMARY: Total Paid ₹{total_paid_for_order} (Cash: ₹{cash_paid_by_customer} + Balance: ₹{amount_used_from_balance}), Pending: ₹{pending_amount_for_order}")
        print(f" CUSTOMER BALANCE: ₹{customer.available_balance}")
    
        return instance

        
# -------------------- Transaction Serializer -----------------------
class TransactionSerializer(serializers.ModelSerializer):
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    paid_amount = serializers.SerializerMethodField() 

    class Meta:
        model = Transaction
        fields = [
            "id",
            "customer_name",
            "reference",
            "paid_amount",
            "pending_amount",
            "payment_method",
            "transaction_type",
            "paid_at",
            "updated_at",
            "customer",
            "order",
            "created_by",
            "updated_by",
        ]

    def get_paid_amount(self, obj):
        amount = Decimal(obj.paid_amount or 0)
        if obj.transaction_type == "REFUND":
            return str(-amount.quantize(Decimal("0.01")))
        return str(amount.quantize(Decimal("0.01")))



class OrderHistorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Order
        fields = ['order_id', 'category', 'measurement_type',
                  'quantity', 'unit', 'total_amount', 'discount',
                  'paid_amount', 'pending_amount', 'payment_status',
                  'delivery_status', 'exported_at', 'delivered_at',]
        



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
    payment_method = serializers.CharField()   



class ScanReportSerializer(serializers.ModelSerializer):
    scan_history = serializers.SerializerMethodField()

    class Meta:
        model = ScanReport
        fields = ['device_id', 'total_scans', 'last_scanned_at', 'scan_history']

    def get_scan_history(self, obj):
        from .models import ScanLog
        logs = ScanLog.objects.filter(device_id=obj.device_id).order_by('-scanned_at')
        return [
            {
                "order_id": log.order.order_id,
                "location": log.location,
                "delivery_address": log.delivery_address,
                "scanned_at": log.scanned_at,
            }
            for log in logs
        ]


