import re

import jsonpickle
import math
from django.core.mail import send_mail
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.views import View
from django_redis import get_redis_connection
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer,SignatureExpired

# Create your views here.
from goods.models import GoodsSKU
from netshop.settings import SECRET_KEY, EMAIL_FROM
from order.models import OrderInfo, OrderGoods
from user.models import User, Address
from celery_tasks.tasks import send_register_active_email

class RegisterView(View):
    '''
    注册
    '''
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        # 接收数据
        user_name=request.POST.get('user_name','')
        pwd=request.POST.get('pwd','')
        cpwd=request.POST.get('cpwd','')
        to_email=request.POST.get('email','')
        allow=request.POST.get('allow','')
        # 校验数据
        # if not all([user_name,pwd,to_email]):
        #     return render(request,'register.html',{'errmsg':'数据不完整'})
        # if cpwd !=pwd:
        #     return render(request, 'register.html', {'errmsg': '两次密码不一致'})
        # if allow != 'on':
        #     return render(request, 'register.html', {'errmsg': '请确定是否同意协议'})
        try:
            user = User.objects.create(username=user_name, password=pwd, email=to_email)
            print(user)
        except User.DoesNotExist:
            return redirect('/user/register/')
        # 发送激活邮件，包含激活链接 http://localhost:8000/user/active/XXX

        # 激活链接中需要包含用户的身份信息，并且要把身份信息进行加密处理
        serializer=Serializer(SECRET_KEY,3600)
        info={'user_id':user.id}
        token=serializer.dumps(info)
        token=token.decode('utf-8')

        # 发送邮件需要设置SMTP服务器
        '''
        subject="欢迎光临良实速运" #欢迎信息
        message=""   #邮件正文
        from_email=EMAIL_FROM    #发件人
        receiver=[to_email]   #收件人
        html_message='<h1>%s,欢迎登陆</h1>请点击一下链接进行账户激活<a href="http://localhost:8000/user/active/%s">http://localhost:8000/user/active/%s</a>'%(user_name,token,token)
        send_mail(subject, message, from_email, receiver,html_message=html_message)
        '''
        send_register_active_email.delay(to_email, user_name, token)

        return redirect('/user/login/')


class ActiveView(View):
    '''
    邮件激活
    '''
    def get(self,request,token_id):
        # token_id=request.GET.get('token_id')
        # print(token_id)
        # return HttpResponse('1')
        serializer = Serializer(SECRET_KEY, 3600)
        try:
            info=serializer.loads(token_id)
            user_id=info['user_id']
            # print(user_id)
            user=User.objects.get(id=user_id)
            user.is_active=1
            user.save()
            return redirect('/user/login')
        except SignatureExpired as e:
            return HttpResponse('激活链接过期')


class LoginView(View):
    def get(self,request):
        if 'username' in request.COOKIES and 'password' in request.COOKIES:
            username=request.COOKIES.get('username')
            password=request.COOKIES.get('password')
            checked='checked'
        else:
            username=''
            password=''
            checked=''
        return render(request,'login.html',{'username':username,'password':password,'checked':checked})
    def post(self,request):
        # 接收数据
        username=request.POST.get('username')
        pwd=request.POST.get('pwd')
        remember=request.POST.get('remember','')

        if not all([username,pwd]):
            return render(request,'login.html',{'errmsg':'数据不完整'})
        # 查询数据
        try:
            user=User.objects.get(username=username,password=pwd)
        except User.DoesNotExist:
            return render(request,'login.html',{'errmsg':'账号不存在'})

        print(user)
        # 确认激活状态
        if user.is_active==False:
            return render(request,'login.html',{'errmsg':'账号未激活'})

        # 存储session
        request.session['user']=jsonpickle.dumps(user)
        res = redirect('/index/')

        if remember=='on':
            res.set_cookie('username',username,max_age=7200)
            res.set_cookie('password',pwd,max_age=7200)
        else:
            res.delete_cookie('username')
            res.delete_cookie('password')
        return res



class CodeUser(View):
    '''用户名验证'''
    def get(self,request):
        username=request.GET.get('username')
        user=User.objects.filter(username=username)
        flag=False
        passwd=''
        if user:
            flag=True
            for u in user:
                passwd=u.password
        return JsonResponse({'flag':flag,'passwd':passwd})


class CodeEmail(View):
    '''邮箱验证'''
    def get(self, request):
        email = request.GET.get('email')


class UserInfo(View):
    '''用户中心-个人信息'''
    def get(self,request):
        page = 'user'
        if 'user' not in request.session:
            return redirect('/user/login/')
        user=jsonpickle.loads(request.session.get('user'))
        try:
            address=Address.objects.get(user=user,is_default=True)
        except Address.DoesNotExist:
            return render(request,'user_center_info.html',{'errmsg':'无此记录'})
        '''历史浏览记录'''
        con=get_redis_connection('default')  #连接数据库
        history_key='history_%d'%user.id  #设置数据格式
        skus_id=con.lrange(history_key,0,4)
        goods_list=[]
        for id in skus_id:
            goods=GoodsSKU.objects.get(id=id)
            goods_list.append(goods)
        context={
            'page':page,
            'address': address,
            'goods_list':goods_list
        }


        return render(request,'user_center_info.html',context)


class UserOrder(View):
    def get(self,request,num):
        '''用户中心-全部订单'''
        if 'user' not in request.session:
            return redirect('/user/login/')
        user=jsonpickle.loads(request.session.get('user'))
        # 所有订单
        orders=OrderInfo.objects.filter(user=user)
        print('orders',orders)
        # 遍历订单
        for order in orders:
            # 所有订单商品
            order_skus=OrderGoods.objects.filter(order=order)
            # 遍历订单商品
            for order_sku in order_skus:
                amount=order_sku.price * order_sku.count
                order_sku.amount=amount
            order.order_skus=order_skus
            order.status_name=OrderInfo.ORDER_STATUS[order.order_status]
            # 分页
        page_orders = Paginator(orders, 1)
        num = int(num)

        try:
            page_list = page_orders.page(num)
        except PageNotAnInteger:
            page_list = page_orders.page(1)
        except EmptyPage:
            page_list = page_orders.page(page_orders.num_pages)

        begin = (num - int(math.ceil(4.0 / 2)))
        if begin < 1:
            begin = 1

        end = begin + 3
        if end > page_orders.num_pages:
            end = page_orders.num_pages
        if end <= 4:
            begin = 1
        else:
            begin = end - 3
        page_num = range(begin, end + 1)

            # 组织上下文
        context = {
            'page_list': page_list,
            'num': num,
            'page_num': page_num,
            'page': orders,
        }

        return render(request, 'user_center_order.html',context)



class UserAddress(View):
    def get(self,request):
        '''用户中心-收货地址'''
        page = 'address'
        if 'user' not in request.session:
            return redirect('/user/login/')
        user=jsonpickle.loads(request.session.get('user'))
        try:
            address=Address.objects.get(user=user,is_default=True)
        except Address.DoesNotExist:
            return render(request,'user_center_site.html')
        print(address)
        context={
            'page':page,
            'address':address
        }
        return render(request,'user_center_site.html',context)
    def post(self,request):
        # 接收数据
        receiver=request.POST.get('receiver')
        zip_code=request.POST.get('zip_code')
        phone=request.POST.get('phone')
        addr=request.POST.get('addr')
        # 校验数据
        if not all([receiver,zip_code,phone,addr]):
            return render(request,'user_center_site.html',{'errmsg':'数据不完整'})
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$',phone):
            return render(request,'user_center_site.html',{'errmsg':'手机号格式错误'})
        user=''
        if 'user' in request.session:
            user=jsonpickle.loads(request.session.get('user'))
        # 判断 is_default的值
        try:
            address = Address.objects.get(user=user,is_default=True)
        except Address.DoesNotExist:
            address = None
        # 添加地址
        # 如果用户已存在默认收货地址，添加的地址不作为默认收货地址，否则作为默认收货地址
        if address:
            is_default = False
        else:
            # 不存在默认收货地址
            is_default = True
        try:
            Address.objects.create(receiver=receiver,zip_code=zip_code,phone=phone,addr=addr,user=user,is_default=is_default)
        except Address.DoesNotExist:
            return render(request,'user_center_site.html',{'errmsg':'添加失败'})
        return redirect('/user/address/')

class LoginOut(View):
    '''退出登录'''
    def get(self,request):
        # del request.session['user']
        request.session.flush()

        resp = redirect('/user/login/')
        resp.delete_cookie('username')
        resp.delete_cookie('password')

        return resp
