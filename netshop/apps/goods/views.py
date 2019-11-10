from django.core.cache import cache
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, redirect
from django.views import View
from django_redis import get_redis_connection
from goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, GoodsSKU, GoodsImage
import jsonpickle
import math

# Create your views here.
from order.models import OrderGoods


class IndexView(View):
    def get(self, request):

        context = cache.get('index_page_data')

        if context is None:

            # 展示分类
            types = GoodsType.objects.all()

            # 首页轮播图
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            # 首页促销
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            for type in types:
                # 图片产品
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1)
                # 文字产品
                title_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0)
                # 动态添加文字商品与图片商品
                type.image_banners = image_banners
                type.title_banners = title_banners

            # 组织上下文
            context = {
                'types': types,
                'goods_banners': goods_banners,
                'promotion_banners': promotion_banners
            }
            # 设置缓存
            cache.set('index_page_data', context, 3600)

        # 获取购物车数量
        cart_count = 0
        if 'user' in request.session:
            user = jsonpickle.loads(request.session.get('user'))
            con = get_redis_connection('default')  # 连接redis
            cart_key = 'cart_%d' % user.id  # 设置数据格式
            cart_count = con.hlen(cart_key)

        context.update(cart_count=cart_count)

        return render(request, 'index.html', context)


class DetailView(View):
    '''商品详情'''

    def get(self, request):
        # 获取goods_id
        goods_id = request.GET.get('goods_id')

        # 查询对应商品
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect('/index/')

        # 获取分类信息
        types = GoodsType.objects.all()

        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=sku.type).exclude(id=goods_id).order_by('-create_time')[:2]

        # 获取同一SPU下的商品
        same_sku_spu = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 获取同一商品的其他图片
        other_img = GoodsImage.objects.filter(sku=sku)

        # 获取评论信息
        sku_comment = OrderGoods.objects.filter(sku=sku).exclude(comment='').order_by('-create_time')

        cart_count = 0
        if 'user' in request.session:
            user = jsonpickle.loads(request.session.get('user'))
            # 获取购物车数量
            con = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = con.hlen(cart_key)

            # 存储用户历史浏览记录
            history_key = 'history_%d' % user.id
            # 去重
            con.lrem(history_key, 0, goods_id)
            # 从左到右插入数据
            con.lpush(history_key, goods_id)
            # 显示数量
            con.ltrim(history_key, 0, 4)

        context = {
            'sku': sku,
            'types': types,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'same_sku_spu': same_sku_spu,
            'other_img': other_img,
            'sku_comment':sku_comment,
        }

        return render(request, 'detail.html', context)


class ListView(View):
    '''列表'''

    def get(self, request, type_id):

        # 获取当前种类信息
        type = GoodsType.objects.get(id=type_id)

        # 获取所有种类信息
        types = GoodsType.objects.all()

        # 获取sort
        sort = request.GET.get('sort')

        if sort == 'price':
            skus = GoodsSKU.objects.filter(type=type).order_by('-price')
        elif sort == 'hot':
            skus = GoodsSKU.objects.filter(type=type).order_by('-sales')
        else:
            sort = 'default'
            skus = GoodsSKU.objects.filter(type=type).order_by('id')

        # 获取新品信息
        new_skus = GoodsSKU.objects.filter(type=type).order_by('-create_time')[:2]

        # 分页器
        page_skus = Paginator(skus, 2)

        num = request.GET.get('num', 1)
        num = int(num)

        try:
            page_list = page_skus.page(num)
        except PageNotAnInteger:
            page_list = page_skus.page(1)
        except EmptyPage:
            page_list = page_skus.page(page_skus.num_pages)

        begin = (num - int(math.ceil(4.0 / 2)))
        if begin < 1:
            begin = 1

        end = begin + 3
        if end > page_skus.num_pages:
            end = page_skus.num_pages

        if end <= 4:
            begin = 1
        else:
            begin = end - 3

        page_num = range(begin, end + 1)

        # 获取购物车数量
        cart_count = 0
        if 'user' in request.session:
            user = jsonpickle.loads(request.session.get('user'))
            con = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = con.hlen(cart_key)

        # 组织上下文
        context = {
            'type': type,
            'types': types,
            'sort': sort,
            'skus': page_list,
            'new_skus': new_skus,
            'page_num': page_num,
            'num': num,
            'cart_count': cart_count,
        }

        return render(request, 'list.html', context)






















