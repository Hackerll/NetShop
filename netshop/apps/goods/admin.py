from django.contrib import admin
from django.core.cache import cache
from goods.models import Goods,GoodsSKU,GoodsType,IndexPromotionBanner,IndexTypeGoodsBanner,IndexGoodsBanner,GoodsImage


# Register your models here.

class BaseModelAamin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        # 调用父类增加和更新时的操作
        super().save_model(request, obj, form, change)
        cache.delete('index_page_data')

    def delete_model(self, request, obj):
        # 调用父类删除操作
        super().delete_model(request, obj)
        cache.delete('index_page_data')


admin.site.register(Goods, BaseModelAamin)
admin.site.register(GoodsSKU, BaseModelAamin)
admin.site.register(GoodsType, BaseModelAamin)
admin.site.register(GoodsImage, BaseModelAamin)
admin.site.register(IndexGoodsBanner, BaseModelAamin)
admin.site.register(IndexTypeGoodsBanner, BaseModelAamin)
admin.site.register(IndexPromotionBanner, BaseModelAamin)
