import os
from datetime import datetime

import jsonpickle
from alipay import AliPay
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View

# Create your views here.
from django_redis import get_redis_connection

from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods
from user.models import Address


class OrderPlace(View):
    '''订单页'''
    def post(self,request):
        # 判断用户是否登录
        if 'user' not in request.session:
            return redirect('/user/login/')
        user = jsonpickle.loads(request.session.get('user'))

        # 获取 sku_ids
        sku_ids = request.POST.getlist('sku_ids')

        # 判断 sku_ids 是否存在
        if not sku_ids:
            return redirect('/cart/info/')

        # 连接 redis
        con = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        skus = []
        total_count = 0
        total_price = 0

        for sku_id in sku_ids:
            # 获取商品信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 获取商品数量
            count = con.hget(cart_key,sku_id)
            # 获取商品小计
            amount = int(count) * sku.price
            # 动态添加商品数量
            sku.count = int(count)
            # 动态添加商品小计
            sku.amount = amount
            # 追加
            skus.append(sku)
            # 获取商品总数量
            total_count += int(count)
            # 获取商品总价格
            total_price += amount
        # 获取商品运费
        transit_price = 10
        # 获取商品实付价格
        total_pay = total_price + transit_price
        # 获取地址信息
        address = Address.objects.filter(user=user)
        # 处理sku_ids的数据类型
        sku_ids = ','.join(sku_ids)

        # 组织上下文
        context = {
            'sku_ids':sku_ids,
            'skus':skus,
            'total_count':total_count,
            'total_prece':total_price,
            'transit_price':transit_price,
            'total_pay':total_pay,
            'address':address
        }

        return render(request,'place_order.html',context)


class OrderCommit(View):
    '''订单添加'''
    def post(self,request):
        # 判断是否登录
        if 'user' not in request.session:
            return JsonResponse({'res':0,'errmsg':'请先登录'})
        user = jsonpickle.loads(request.session.get('user'))
        # 获取数据
        sku_ids = request.POST.get('sku_ids')
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')

        # 数据校验
        if not all([sku_ids,addr_id,pay_method]):
            return JsonResponse({'res': 1, 'errmsg': '信息不完整'})
        # 验证地址
        try:
            address = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '非法地址'})

        # 验证支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 3, 'errmsg': '非法支付方式'})

        # 获取Order_id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)

        # 获取运费
        transit_price = 10

        # 获取总价格与总数量
        total_count = 0
        total_price = 0

        # 添加订单表
        order = OrderInfo.objects.create(order_id=order_id,total_count=total_count,total_price=total_price,transit_price=transit_price,pay_method=pay_method,user=user,addr=address)


        # todo:添加订单商品表
        # 连接redis,获取count值
        con = get_redis_connection('default')
        cart_key = 'cart_%d'%user.id

        sku_ids = sku_ids.split(',') # 1,2 - > [1,2]

        for sku_id in sku_ids:
            # 获取当前商品信息
            try:
                sku = GoodsSKU.objects.get(id=sku_id)
            except GoodsSKU.DoesNotExist:
                return JsonResponse({'res': 4, 'errmsg': '查无此货'})
            # 获取去数量
            count = con.hget(cart_key,sku_id)
            count = int(count)
            # 添加订单商品表
            OrderGoods.objects.create(order=order,count=count,price=sku.price,sku=sku)
            # 更新库存与销量
            sku.stock -= count
            sku.sales += count
            sku.save()
            # 获取商品小计
            amount = sku.price * count
            # 获取商品的总价格与总数量
            total_price += amount
            total_count += count

        # 更新订单表中的总价格与总数量
        order.total_price = total_price
        order.total_count = total_count
        order.save()
        # 订单生成后删除购物车
        con.hdel(cart_key,*sku_ids)

        return JsonResponse({'res': 5, 'message': '订单生成成功'})


class OrderPay(View):
    '''订单支付'''
    def post(self,request):
        # 判断用户是否登录
        if 'user' not in request.session:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        user = jsonpickle.loads(request.session.get('user'))

        # 获取参数
        order_id = request.POST.get('order_id')

        # 校验数据
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单ID'})
        # 查看订单是否存在
        try:
            order = OrderInfo.objects.get(user=user,pay_method=3,order_status=1,order_id=order_id)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单无效'})


        # 使用python.SDK 连接支付宝接口
        # 初始化
            # 业务处理：条用python.sdk条用支付宝的支付接口
            # 初始化
        alipay = AliPay(
            appid="2016093000634740", # APPID 支付宝沙箱
            app_notify_url=None,  # 默认回调url
            # 应用私钥
            app_private_key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),'app_private_key.pem'),
            # 支付宝公钥
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                'alipay_public_key.pem'),
            sign_type='RSA2',  # RSA 或者 RSA2
            debug=True  # 默认False
        )

        # 调用支付宝接口
        # 电脑网站支付，需要跳转到https://openapi.alipay.com/gateway.do? + order_string
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price + order.transit_price  # Decimal
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay), # str 字符串格式
            subject='良实速运',
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )

        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


class OrderCheck(View):
    '''支付结果'''
    def post(self,request):
        # 判断用户是否登录
        if 'user' not in request.session:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        user = jsonpickle.loads(request.session.get('user'))

        # 获取参数
        order_id = request.POST.get('order_id')
        # 校验数据
        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单ID'})
        # 查看订单是否存在
        try:
            order = OrderInfo.objects.get(user=user, pay_method=3, order_status=1, order_id=order_id)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单无效'})

        # 使用python.SDK 连接支付宝接口
        # 初始化
        # 业务处理：条用python.sdk条用支付宝的支付接口
        # 初始化
        alipay = AliPay(
            appid="2016093000634740",  # APPID 支付宝沙箱
            app_notify_url=None,  # 默认回调url
            # 应用私钥
            app_private_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app_private_key.pem'),
            # 支付宝公钥
            alipay_public_key_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                'alipay_public_key.pem'),
            sign_type='RSA2',  # RSA 或者 RSA2
            debug=True  # 默认False
        )

        # 调用支付宝订单查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)

            code = response.get('code')
            trade_status = response.get('trade_status')
            if code == '10000' and trade_status == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_on = response.get('trade_no')
                # 更新订单状态
                order.trade_on = trade_on
                order.order_status = 4  # 待评价
                order.save()
                # 返回结果
                return JsonResponse({'res': 3, 'message': '支付成功'})

            elif code == '40004' or code == '10000' and trade_status == 'WAIT_BUYER_PAY':
                # 业务处理失败，可能一会就能成功
                # 等待买家付款
                import time
                time.sleep(3)
                continue
            else:
                # 支付出错
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})


class OrderComment(View):
    '''商品评论'''
    def get(self,request,order_id):
        if 'user' not in request.session:
            return redirect('/user/login/')

        user = jsonpickle.loads(request.session.get('user'))

        if not order_id:
            return redirect('/user/order/1')

        try:
            order = OrderInfo.objects.get(order_id=order_id,user=user)
        except OrderInfo.DoesNotExist:
            return redirect('/user/order/1')

        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        order_skus = OrderGoods.objects.filter(order_id=order_id)

        for order_sku in order_skus:
            amount = order_sku.price * order_sku.count
            order_sku.amount = amount

        order.order_skus = order_skus

        context = {
            'page':'order',
            'order':order,
        }

        return render(request,'order_comment.html',context)

    def post(self,request,order_id):

        if 'user' not in request.session:
            return redirect('/user/login/')
        user = jsonpickle.loads(request.session.get('user'))

        if not order_id:
            return redirect('/user/order/1')

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect('/user/order/1')
        
        total_count = request.POST.get('total_count')
        total_count = int(total_count)

        for i in range(1,total_count+1):
            # 获取商品sku_id
            sku_id = request.POST.get('sku_%d'%i)
            # 获取评论内容
            content = request.POST.get('content_%d'%i)

            order_goods = OrderGoods.objects.get(sku_id=sku_id,order_id=order_id)
            # 动态更新评论内容
            order_goods.comment = content
            order_goods.save()
        # 动态更新商品状态
        order.order_status = 5
        order.save()

        return redirect('/user/order/1')

















