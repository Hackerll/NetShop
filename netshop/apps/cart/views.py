import jsonpickle
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django_redis import get_redis_connection

from goods.models import GoodsSKU


# Create your views here.


class CartAdd(View):
    '''加入购物车'''

    def post(self, request):
        # 判断是否登录
        if 'user' not in request.session:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        user = jsonpickle.loads(request.session.get('user'))

        # 获取参数
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '信息不完整'})

        # 验证数字格式
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '数目出错'})

        # 验证是否有当前商品
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 获取已经存在的商品数目
        con = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        cart_count = con.hget(cart_key, sku_id)

        # 累计商品数量
        if cart_count:
            count += int(cart_count)
        # 判断库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '库存不足'})
        # 添加信息
        con.hset(cart_key, sku_id, count)
        # 获取购物车中商品数量
        total_count = con.hlen(cart_key)

        return JsonResponse({'res': 5, 'message': '添加成功', 'total_count': total_count})


class CartInfo(View):
    '''购物车详情'''

    def get(self, request):
        # 判断用户是否登录
        if 'user' not in request.session:
            return redirect('/user/login/')
        user = jsonpickle.loads(request.session.get('user'))

        # 获取数据库中所有键值对
        con = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        cart_dict = con.hgetall(cart_key)

        skus = []
        total_count = 0
        total_price = 0
        for sku_id, count in cart_dict.items():
            # 获取所有商品
            sku = GoodsSKU.objects.get(id=sku_id)
            # 处理商品数目格式
            count = int(count)
            # 计算商品小计
            amount = count * sku.price
            # 动态添加count对象
            sku.count = count
            # 动态添加amount对象
            sku.amount = amount

            skus.append(sku)
            # 商品总数量
            total_count += count
            # 商品总价格
            total_price += amount
        # 组织上下文
        context = {
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
        }

        return render(request, 'cart.html', context)


class CartUpdate(View):
    '''购物车添加功能'''

    def post(self, request):
        if 'user' not in request.session:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        user = jsonpickle.loads(request.session.get('user'))

        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '信息不完整'})

        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '数目异常'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '无此商品'})

        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '库存不足'})

        con = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        con.hset(cart_key, sku_id, count)

        return JsonResponse({'res': 5, 'message': '添加成功'})


class CartDelete(View):
    '''购物车-删除'''

    def post(self, request):
        if 'user' not in request.session:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        user = jsonpickle.loads(request.session.get('user'))

        # 接受数据
        sku_id = request.POST.get('sku_id')

        # 校验数据
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的商品ID'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '无此商品'})

        con = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        con.hdel(cart_key, sku_id)

        return JsonResponse({'res': 3, 'errmsg': '删除成功'})

















