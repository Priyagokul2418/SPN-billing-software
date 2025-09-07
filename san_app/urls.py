from django.urls import path
from .views import (
    UserAPIView,
    LoginView,
    ChangePasswordView,
    CustomerAPIView,
    CustomerReportDownloadAPIView,
    ProductAPIView,
    DeviceAPIView,
    OrderAPIView,
    TransactionAPIView,
    OrderReceiptDownloadView,
    ForgotPasswordView,
    ResetPasswordView,
    # QRScanAPIView,
    CustomerReportAPIView,
    CustomerOrderHistoryAPIView,
    CustomerTransactionHistoryAPIView,
    OrdersReportView, TransactionsReportView,
    RecentOrdersAPIView,
    # ReceiptPDFView,
    ScanOrderAPIView,
    DeviceLoginView,
    ReportAPIView,
    DashboardAPIView,
    ScanLogAPIView,
    PayNowAPIView,
    ReceiptDataView,
    scan_auto
)

urlpatterns = [
    # User URLs
    path('users/', UserAPIView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserAPIView.as_view(), name='user-detail'),
   

    path('login/', LoginView.as_view(), name='login'),
    path('change-password/<int:user_id>/', ChangePasswordView.as_view(), name='change-password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),


    # Customer URLs
    path('customers/', CustomerAPIView.as_view(), name='customer-list'),
    path('customers/<int:pk>/', CustomerAPIView.as_view(), name='customer-detail'),
    path("customers/<int:pk>/report/", CustomerReportAPIView.as_view(), name="customer-report"),
    path("customers/<int:pk>/report/download/", CustomerReportDownloadAPIView.as_view(), name="customer-report-download"),
    # Product URLs
    path('products/', ProductAPIView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductAPIView.as_view(), name='product-detail'),

    # Device URLs
    path('devices/', DeviceAPIView.as_view(), name='device-list'),
    path('devices/<int:pk>/', DeviceAPIView.as_view(), name='device-detail'),
    path("device/login/", DeviceLoginView.as_view(), name="device-login"),

    # Order URLs
    path('orders/', OrderAPIView.as_view(), name='order-list'),
    path('orders/<int:pk>/', OrderAPIView.as_view(), name='order-detail'),
    # path('orders/<int:order_id>/download-receipt/', 
    #       ReceiptPDFView.as_view(), 
    #      name='download-receipt'),
    path("orders/recent/", RecentOrdersAPIView.as_view(), name="recent-orders"),
    path('orders/<int:order_id>/receipt-data/', ReceiptDataView.as_view(), name='receipt-data'),
    # path("receipt/<int:order_id>/", ReceiptPDFView.as_view(), name="receipt-pdf"),


    path('scanlogs/', ScanLogAPIView.as_view(), name='scanlog-list'),
    path('scanlogs/<int:pk>/', ScanLogAPIView.as_view(), name='scanlog-detail'),



    # Transaction URLs
    path('transactions/', TransactionAPIView.as_view(), name='transaction-list'),
    path('transactions/<int:pk>/', TransactionAPIView.as_view(), name='transaction-detail'),

    path("customers/<int:pk>/report/", CustomerReportAPIView.as_view(), name="customer-report"),
    path("customers/<int:customer_id>/order-history/", CustomerOrderHistoryAPIView.as_view(), name="customer-order-history"),
    path("customer/<int:customer_id>/transactions/", CustomerTransactionHistoryAPIView.as_view(), name="customer-transaction-history"),
    
    path("customers/<int:customer_id>/paynow/", PayNowAPIView.as_view(), name="customer-paynow"),

    path('reports/', ReportAPIView.as_view(), name='full-report'),
    path("reports/orders/", OrdersReportView.as_view(), name="orders-report"),
    path("reports/transactions/", TransactionsReportView.as_view(), name="transactions-report"),

    # path('api/scan/<int:order_id>/', QRScanAPIView.as_view(), name='qr-scan'),
     path("api/scan/", ScanOrderAPIView.as_view(), name="scan-order"),

    path("scan_auto/", scan_auto, name="scan-auto"),
    path("api/scan/", ScanOrderAPIView.as_view(), name="scan-order"),

    path("dashboard/", DashboardAPIView.as_view(), name="dashboard"),
    
]

