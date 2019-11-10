from django.urls import path
from order import views

urlpatterns = [
    path('place/',views.OrderPlace.as_view()), # 订单页
    path('commit/',views.OrderCommit.as_view()), # 订单添加
    path('pay/',views.OrderPay.as_view()), # 订单支付
    path('check/',views.OrderCheck.as_view()), # 支付结果
    path('comment/<order_id>',views.OrderComment.as_view()), # 支付结果
]