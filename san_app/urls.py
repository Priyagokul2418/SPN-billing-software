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
    RefundAPIView,
    ScanOrderAPIView,
    DeviceLoginView,
    ReportAPIView,
    DashboardAPIView,
    ScanLogAPIView,
    PayNowAPIView,
    ReceiptDataView,
    DeviceScanHistoryAPIView,
    scan_auto,
    OrderPDFDownloadAPIView,
    CustomerOrderReportDownloadAPIView,
    CustomerTransactionReportDownloadAPIView,ScanReportAPIView,
)

from .views import AllDeviceScanReportsAPIView

urlpatterns = [
    # User URLs
    path('users/', UserAPIView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserAPIView.as_view(), name='user-detail'),
   
    # Login URLs
    path('login/', LoginView.as_view(), name='login'),
    path('change-password/<int:user_id>/', ChangePasswordView.as_view(), name='change-password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),

     # dashboard URL
    path("dashboard/", DashboardAPIView.as_view(), name="dashboard"),


    # Customer URLs
    path('customers/', CustomerAPIView.as_view(), name='customer-list'),
    path('customers/<int:pk>/', CustomerAPIView.as_view(), name='customer-detail'),
    path("customers/<int:pk>/report/", CustomerReportAPIView.as_view(), name="customer-report"),
    path("customers/<int:pk>/report/download/", CustomerReportDownloadAPIView.as_view(), name="customer-report-download"),
    path("customers/<int:customer_id>/order-history/", CustomerOrderHistoryAPIView.as_view(), name="customer-order-history"),
    path("customer/<int:customer_id>/transactions/", CustomerTransactionHistoryAPIView.as_view(), name="customer-transaction-history"),
    path('customers/<int:customer_id>/order_report/download/', CustomerOrderReportDownloadAPIView.as_view(), name='customer-report-download'),
    path('customers/<int:customer_id>/transaction-history/download/',CustomerTransactionReportDownloadAPIView.as_view(),name='customer-transaction-history-pdf'),
    path("customers/<int:customer_id>/paynow/", PayNowAPIView.as_view(), name="customer-paynow"),
  
 


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
    path("orders/recent/", RecentOrdersAPIView.as_view(), name="recent-orders"),
    path('orders/<int:order_id>/receipt-data/', ReceiptDataView.as_view(), name='receipt-data'),
    path('orders/<int:order_id>/download/', OrderPDFDownloadAPIView.as_view(), name='order-pdf-download'),\
    path('refund/<str:order_id>/', RefundAPIView.as_view(), name='order-refund'),



    path('scanlogs/', ScanLogAPIView.as_view(), name='scanlog-list'),
    path('scanlogs/<int:pk>/', ScanLogAPIView.as_view(), name='scanlog-detail'),
    path('scan-report/<str:device_id>/', ScanReportAPIView.as_view(), name='scan-report'),
    path('scan-reports/', AllDeviceScanReportsAPIView.as_view(), name='all-scan-reports'),
    path('device-scans/', DeviceScanHistoryAPIView.as_view(), name='all-device-scans'),
    path("scan_auto/", scan_auto, name="scan-auto"),

    # Transaction URLs
    path('transactions/', TransactionAPIView.as_view(), name='transaction-list'),
    path('transactions/<int:pk>/', TransactionAPIView.as_view(), name='transaction-detail'),
    

    #Reports URLS
    path('reports/', ReportAPIView.as_view(), name='full-report'),
    path("reports/orders/", OrdersReportView.as_view(), name="orders-report"),
    path("reports/transactions/", TransactionsReportView.as_view(), name="transactions-report"),



  

 
  
    
]

