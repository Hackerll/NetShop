from django.urls import path
from .import views

urlpatterns = [
    path('register/',views.RegisterView.as_view()), # 注册
    path('active/<token_id>',views.ActiveView.as_view()), # 邮件激活
    path('login/',views.LoginView.as_view()), # 登录
    path('login_out/',views.LoginOut.as_view()), # 退出登录
    path('',views.UserInfo.as_view()), # 用户中心-主页
    path('order/<num>',views.UserOrder.as_view()), # 用户中心-订单
    path('address/',views.UserAddress.as_view()), # 用户中心-地址
    path('code_user/',views.CodeUser.as_view()), # 用户名验证
    path('code_email/',views.CodeEmail.as_view()), # 邮箱验证
]