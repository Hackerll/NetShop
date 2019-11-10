import os
os.environ["DJANGO_SETTINGS_MODULE"] = "netshop.settings"
# 放到Celery服务器上时添加的代码
import django
django.setup()

import time
from celery import Celery
from django.core.mail import send_mail
from netshop.settings import EMAIL_FROM

'''1、指定broker（消息中间件）和backend（结果存储）'''
# redis没有密码时
broker = 'redis://192.168.59.88:6379/9'
backend = 'redis://192.168.59.88:6379/8'
# redis有密码时
# backend='redis://:123456@127.0.0.1:6379/9'
# broker='redis://:123456@127.0.0.1:6379/8'

# 创建一个Celery类的实例对象
app = Celery('celery_tasks.tasks',broker=broker,backend=backend)


# 定义任务函数
@app.task()
def send_register_active_email(to_email,user_name,token):
    subject = "欢迎光临良实速运"  # 欢迎信息
    message = ""  # 邮件正文
    from_email = EMAIL_FROM  # 发件人
    receiver = [to_email]  # 收件人
    html_message = '<h1>%s,欢迎登陆</h1>请点击一下链接进行账户激活<a href="http://192.168.59.88:8000/user/active/%s">http://192.168.59.88:8000/user/active/%s</a>' % (
    user_name, token, token)
    send_mail(subject, message, from_email, receiver, html_message=html_message)
