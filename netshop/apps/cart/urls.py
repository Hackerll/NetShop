from django.urls import path
from .import views
urlpatterns = [
    path('add/',views.CartAdd.as_view()), # 加入购物车
    path('info/',views.CartInfo.as_view()), # 购物车详情
    path('update/',views.CartUpdate.as_view()), # 购物车详情-更新（添加/删除/手动输入）
    path('delete/',views.CartDelete.as_view()), # 购物车详情-删除
]