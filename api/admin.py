from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import redirect
from django.db.models import Avg, Count
from .models import (
    Restaurant, RestaurantImage, MenuItem, MenuCategory, Booking, 
    RestaurantFeature, RestaurantFeatureRelation,
    RatingCategory, RestaurantRating, RestaurantAnalytics
)


class RestaurantFeatureInline(admin.TabularInline):
    model = RestaurantFeatureRelation
    extra = 5
    verbose_name = 'Особенность'
    verbose_name_plural = 'Особенности'
    autocomplete_fields = ['feature']


class RestaurantImageInline(admin.TabularInline):
    model = RestaurantImage
    extra = 5
    fields = ('image_preview', 'image', 'order')
    readonly_fields = ('image_preview',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 80px; border-radius: 8px;"/>', obj.image.url)
        return format_html('<span style="color: #999;">📷 Нет фото</span>')
    image_preview.short_description = 'Превью'


class MenuCategoryInline(admin.TabularInline):
    model = MenuCategory
    extra = 0
    fields = ('image_preview', 'name', 'icon', 'order', 'is_active', 'items_count')
    readonly_fields = ('image_preview', 'items_count')
    show_change_link = True
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 50px; width: auto; border-radius: 8px; object-fit: cover; border: 1px solid #ddd;"/>', 
                obj.image.url
            )
        return format_html('<span style="color: #999;">📷 Нет фото</span>')
    image_preview.short_description = 'Фото'
    
    def items_count(self, obj):
        count = obj.menu_items.count()
        return format_html('<span style="color: #e67e22; font-weight: bold;">{} блюд</span>', count)
    items_count.short_description = 'Блюд в категории'


class MenuItemInline(admin.TabularInline):
    model = MenuItem
    extra = 0
    fields = ('image_preview', 'name', 'category', 'price', 'is_recommended', 'order')
    readonly_fields = ('image_preview',)
    show_change_link = True
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 55px; width: auto; border-radius: 8px; object-fit: cover; border: 1px solid #ddd;"/>', 
                obj.image.url
            )
        return format_html('<span style="color: #999;">📷 Нет фото</span>')
    image_preview.short_description = 'Фото'


class RestaurantRatingInline(admin.TabularInline):
    model = RestaurantRating
    extra = 0
    fields = ('category', 'score', 'comment', 'created_at', 'session_key')
    readonly_fields = ('created_at', 'session_key')
    can_delete = True
    show_change_link = True
    verbose_name = 'Оценка'
    verbose_name_plural = 'Оценки'


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('name', 'region', 'establishment_type', 'cuisine_type', 'price_level', 'rating', 'total_ratings', 'views_count', 'logo_preview', 'telegram_status', 'gold_badge', 'orders_status', 'bookings_status', 'published_status', 'menu_status')
    list_filter = ('region', 'establishment_type', 'cuisine_type', 'price_level', 'show_on_map', 'send_booking_notifications', 'is_gold', 'is_accepting_orders', 'is_accepting_bookings', 'is_published', 'is_menu_published')
    search_fields = ('name', 'address', 'phone', 'telegram_chat_id')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [RestaurantImageInline, RestaurantFeatureInline, RestaurantRatingInline]
    change_form_template = "admin/api/restaurant_change_form.html"
    
    fieldsets = (
        ('Основная информация', {
            'fields': (('name', 'slug'), ('logo', 'description'), ('region', 'establishment_type'), ('cuisine_type', 'price_level'))
        }),
        ('Контакты', {
            'fields': ('address', 'phone', 'email'),
        }),
        ('Часы работы', {
            'fields': ('working_hours',),
        }),
        ('Локация на карте', {
            'fields': (('latitude', 'longitude'), 'show_on_map'),
            'classes': ('wide',),
        }),
        ('Дополнительные кухни', {
            'fields': ('additional_cuisines',),
            'classes': ('wide',),
            'description': 'Укажите через запятую: Японская, Китайская, Европейская'
        }),
        ('Социальные сети', {
            'fields': (('instagram', 'telegram'), ('facebook', 'website')),
            'classes': ('wide',),
        }),
        ('Telegram уведомления', {
            'fields': (('telegram_chat_id', 'telegram_bot_token'), ('send_booking_notifications', 'send_review_notifications')),
            'classes': ('wide',),
            'description': 'Настройте отправку уведомлений в Telegram. Chat ID можно получить у @userinfobot'
        }),
        ('Управление рестораном', {
            'fields': (('is_accepting_orders', 'is_accepting_bookings'), ('is_gold', 'is_published'), 'is_menu_published'),
            'classes': ('wide',),
            'description': 'Настройте доступные функции для ресторана (заказы, бронирования, Gold статус, видимость)'
        }),
    )
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/menu/', self.admin_site.admin_view(self.menu_management_view), name='restaurant_menu_management'),
        ]
        return custom_urls + urls
    
    def menu_management_view(self, request, object_id):
        from django.shortcuts import render, get_object_or_404
        from .models import Restaurant as RestaurantModel
        
        restaurant = get_object_or_404(RestaurantModel, id=object_id)
        categories = MenuCategory.objects.filter(restaurant=restaurant).order_by('order')
        
        context = {
            'restaurant': restaurant,
            'categories': categories,
            'opts': self.model._meta,
            'original': restaurant,
            'has_change_permission': self.has_change_permission(request),
        }
        
        return render(request, 'admin/api/menu_management.html', context)
    
    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 40px; width: auto; border-radius: 50%; border: 1px solid #e67e22;"/>', 
                obj.logo.url
            )
        return '-'
    logo_preview.short_description = 'Логотип'
    
    def telegram_status(self, obj):
        if obj.telegram_chat_id:
            return format_html(
                '<span style="color: #27ae60;">✅ {}</span>',
                obj.telegram_chat_id[:15] + '...' if len(obj.telegram_chat_id) > 15 else obj.telegram_chat_id
            )
        return format_html('<span style="color: #e74c3c;">❌ Не настроен</span>')
    telegram_status.short_description = 'Telegram'
    
    def gold_badge(self, obj):
        if obj.is_gold:
            return format_html('<span style="background: #f39c1220; color: #f39c12; padding: 4px 10px; border-radius: 20px; font-weight: bold;">⭐ GOLD</span>')
        return format_html('<span style="color: #999;">—</span>')
    gold_badge.short_description = 'Gold статус'
    
    def orders_status(self, obj):
        if obj.is_accepting_orders:
            return format_html('<span style="background: #2ecc7120; color: #2ecc71; padding: 4px 10px; border-radius: 20px;">✅ Принимает</span>')
        return format_html('<span style="background: #e74c3c20; color: #e74c3c; padding: 4px 10px; border-radius: 20px;">❌ Не принимает</span>')
    orders_status.short_description = 'Заказы'
    
    def bookings_status(self, obj):
        if obj.is_accepting_bookings:
            return format_html('<span style="background: #2ecc7120; color: #2ecc71; padding: 4px 10px; border-radius: 20px;">✅ Принимает</span>')
        return format_html('<span style="background: #e74c3c20; color: #e74c3c; padding: 4px 10px; border-radius: 20px;">❌ Не принимает</span>')
    bookings_status.short_description = 'Бронирования'
    
    def published_status(self, obj):
        if obj.is_published:
            return format_html('<span style="background: #2ecc7120; color: #2ecc71; padding: 4px 10px; border-radius: 20px;">✅ Опубликован</span>')
        return format_html('<span style="background: #e74c3c20; color: #e74c3c; padding: 4px 10px; border-radius: 20px;">❌ Скрыт</span>')
    published_status.short_description = 'Статус на сайте'
    
    def menu_status(self, obj):
        if obj.is_menu_published:
            return format_html('<span style="background: #2ecc7120; color: #2ecc71; padding: 4px 10px; border-radius: 20px;">✅ Меню активно</span>')
        return format_html('<span style="background: #e74c3c20; color: #e74c3c; padding: 4px 10px; border-radius: 20px;">❌ Меню скрыто</span>')
    menu_status.short_description = 'Меню'
    
    def total_ratings(self, obj):
        count = obj.ratings.count()
        if count > 0:
            return format_html('<span style="color: #e67e22; font-weight: bold;">{} ★</span>', count)
        return '0'
    total_ratings.short_description = 'Оценок'
    
    def views_count(self, obj):
        analytics = getattr(obj, 'analytics', None)
        if analytics and analytics.views_count > 0:
            return format_html('<span style="color: #3498db;">👁️ {}</span>', analytics.views_count)
        return '0'
    views_count.short_description = 'Просмотров'


@admin.register(MenuCategory)
class MenuCategoryAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'name', 'restaurant_link', 'icon', 'order', 'is_active_badge', 'items_count')
    list_filter = ('is_active', 'restaurant')
    search_fields = ('name', 'restaurant__name')
    list_editable = ('order',)
    list_select_related = ('restaurant',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': (('restaurant', 'name'), ('icon', 'order'), ('image',), 'is_active')
        }),
        ('Переводы', {
            'fields': (('name_uz', 'name_ru', 'name_en'),),
            'classes': ('wide',),
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 45px; width: auto; border-radius: 8px; object-fit: cover; border: 1px solid #ddd;"/>', 
                obj.image.url
            )
        return format_html('<span style="color: #999;">📷 Нет фото</span>')
    image_preview.short_description = 'Фото'
    
    def restaurant_link(self, obj):
        url = reverse('admin:api_restaurant_change', args=[obj.restaurant.id])
        return format_html('<a href="{}" style="color: #e67e22; font-weight: bold;">{}</a>', url, obj.restaurant.name)
    restaurant_link.short_description = 'Ресторан'
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #2ecc71;">✅ Активна</span>')
        return format_html('<span style="color: #e74c3c;">❌ Неактивна</span>')
    is_active_badge.short_description = 'Статус'
    
    def items_count(self, obj):
        count = obj.menu_items.count()
        return format_html('<span style="color: #e67e22; font-weight: bold;">{} блюд</span>', count)
    items_count.short_description = 'Блюд'


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('image_preview', 'name', 'restaurant_link', 'category_link', 'price_display', 'is_recommended_badge', 'order')
    list_filter = ('restaurant', 'category', 'is_recommended')
    search_fields = ('name', 'restaurant__name')
    list_editable = ('order',)
    list_select_related = ('restaurant', 'category')
    
    fieldsets = (
        ('Основная информация', {
            'fields': (('restaurant', 'category'), 'name', 'description')
        }),
        ('Цена и фото', {
            'fields': (('price', 'is_recommended'), ('image',)),
            'classes': ('wide',),
        }),
        ('Сортировка', {
            'fields': ('order',),
        }),
    )
    
    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 45px; width: auto; border-radius: 8px; object-fit: cover; border: 1px solid #ddd;"/>', 
                obj.image.url
            )
        return format_html('<span style="color: #999;">📷 Нет фото</span>')
    image_preview.short_description = 'Фото'
    
    def restaurant_link(self, obj):
        url = reverse('admin:api_restaurant_change', args=[obj.restaurant.id])
        return format_html('<a href="{}" style="color: #e67e22;">{}</a>', url, obj.restaurant.name[:30])
    restaurant_link.short_description = 'Ресторан'
    
    def category_link(self, obj):
        if obj.category:
            url = reverse('admin:api_menucategory_change', args=[obj.category.id])
            return format_html('<a href="{}" style="color: #3498db;">{}</a>', url, obj.category.name)
        return format_html('<span style="color: #999;">Без категории</span>')
    category_link.short_description = 'Категория'
    
    def price_display(self, obj):
        price_str = f"{int(obj.price):,}".replace(',', ' ')
        return format_html(
            '<span style="background: #e67e2220; color: #e67e22; padding: 2px 10px; border-radius: 20px; font-weight: bold;">💰 {}</span>',
            price_str
        )
    price_display.short_description = 'Цена (сум)'
    
    def is_recommended_badge(self, obj):
        if obj.is_recommended:
            return format_html('<span style="color: #f39c12;">⭐ Да</span>')
        return format_html('<span style="color: #999;">—</span>')
    is_recommended_badge.short_description = 'Рекомендуемое'


@admin.register(RestaurantImage)
class RestaurantImageAdmin(admin.ModelAdmin):
    list_display = ('restaurant', 'image_preview', 'order', 'created_at')
    list_filter = ('restaurant',)
    list_editable = ('order',)
    
    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px; border-radius: 6px;"/>', obj.image.url)
        return '-'
    image_preview.short_description = 'Фото'


@admin.register(RestaurantFeature)
class RestaurantFeatureAdmin(admin.ModelAdmin):
    list_display = ('label', 'value')
    list_filter = ('value',)
    search_fields = ('label',)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_number', 'customer_name', 'customer_phone', 'restaurant_link', 'date', 'time', 'guests', 'status_badge')
    list_filter = ('status', 'date', 'restaurant')
    search_fields = ('booking_number', 'customer_name', 'customer_phone')
    readonly_fields = ('booking_number', 'created_at')
    
    fieldsets = (
        ('Информация о бронировании', {
            'fields': (('booking_number', 'restaurant'), 'status')
        }),
        ('Данные клиента', {
            'fields': (('customer_name', 'customer_phone'), 'customer_email')
        }),
        ('Детали брони', {
            'fields': (('date', 'time'), 'guests', 'comment')
        }),
    )
    
    def restaurant_link(self, obj):
        url = reverse('admin:api_restaurant_change', args=[obj.restaurant.id])
        return format_html('<a href="{}" style="color: #e67e22;">{}</a>', url, obj.restaurant.name)
    restaurant_link.short_description = 'Ресторан'
    
    def status_badge(self, obj):
        colors = {
            'pending': ('#f39c12', '⏳ Ожидает'),
            'confirmed': ('#2ecc71', '✅ Подтверждено'),
            'cancelled': ('#e74c3c', '❌ Отменено'),
            'completed': ('#3498db', '📌 Завершено')
        }
        color, label = colors.get(obj.status, ('#95a5a6', obj.status))
        return format_html(
            '<span style="background: {}20; color: {}; padding: 4px 10px; border-radius: 20px; font-size: 12px;">{}</span>',
            color, color, label
        )
    status_badge.short_description = 'Статус'
    
    actions = ['confirm_bookings', 'cancel_bookings']
    
    def confirm_bookings(self, request, queryset):
        updated = queryset.update(status='confirmed')
        self.message_user(request, f'✅ {updated} бронирований подтверждено.')
    confirm_bookings.short_description = '✅ Подтвердить'
    
    def cancel_bookings(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'❌ {updated} бронирований отменено.')
    cancel_bookings.short_description = '❌ Отменить'


@admin.register(RatingCategory)
class RatingCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon', 'weight', 'is_active_badge', 'order')
    list_filter = ('is_active',)
    search_fields = ('name', 'slug')
    list_editable = ('weight', 'order')
    prepopulated_fields = {'slug': ('name',)}
    
    def is_active_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color: #2ecc71;">✅ Активна</span>')
        return format_html('<span style="color: #e74c3c;">❌ Неактивна</span>')
    is_active_badge.short_description = 'Статус'


@admin.register(RestaurantRating)
class RestaurantRatingAdmin(admin.ModelAdmin):
    list_display = ('id', 'restaurant_link', 'category', 'score_stars', 'comment_preview', 'created_at')
    list_filter = ('category', 'score', 'created_at', 'restaurant')
    search_fields = ('comment', 'restaurant__name', 'session_key', 'ip_address')
    readonly_fields = ('created_at', 'updated_at', 'session_key', 'ip_address', 'user_agent')
    
    fieldsets = (
        ('Ресторан и категория', {
            'fields': (('restaurant', 'category'),)
        }),
        ('Оценка и отзыв', {
            'fields': ('score', 'comment')
        }),
        ('Техническая информация', {
            'fields': ('session_key', 'ip_address', 'user_agent', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def restaurant_link(self, obj):
        if obj.restaurant:
            url = reverse('admin:api_restaurant_change', args=[obj.restaurant.id])
            return format_html('<a href="{}" style="font-weight: bold; color: #e67e22;">{}</a>', url, obj.restaurant.name)
        return '-'
    restaurant_link.short_description = 'Ресторан'
    
    def score_stars(self, obj):
        stars = '⭐' * obj.score + '☆' * (5 - obj.score)
        return format_html('<span title="{} из 5">{}</span>', obj.score, stars)
    score_stars.short_description = 'Оценка'
    
    def comment_preview(self, obj):
        if obj.comment:
            preview = obj.comment[:80] + '...' if len(obj.comment) > 80 else obj.comment
            return format_html('<span style="color: #aaa; font-style: italic;">"{}"</span>', preview)
        return '-'
    comment_preview.short_description = 'Отзыв'


@admin.register(RestaurantAnalytics)
class RestaurantAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('restaurant_link', 'overall_rating_display', 'total_ratings', 'unique_raters', 'views_count')
    list_filter = ('overall_rating',)
    search_fields = ('restaurant__name',)
    readonly_fields = ('last_updated',)
    
    fieldsets = (
        ('Ресторан', {
            'fields': ('restaurant',)
        }),
        ('Рейтинги', {
            'fields': (('overall_rating', 'food_avg'), ('service_avg', 'atmosphere_avg'))
        }),
        ('Статистика', {
            'fields': (('total_ratings', 'unique_raters'), 'views_count')
        }),
        ('Системная информация', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )
    
    def restaurant_link(self, obj):
        if obj.restaurant:
            url = reverse('admin:api_restaurant_change', args=[obj.restaurant.id])
            return format_html('<a href="{}" style="font-weight: bold; color: #e67e22;">{}</a>', url, obj.restaurant.name)
        return '-'
    restaurant_link.short_description = 'Ресторан'
    
    def overall_rating_display(self, obj):
        color = '#f39c12' if obj.overall_rating >= 4 else '#e67e22' if obj.overall_rating >= 3 else '#95a5a6'
        return format_html(
            '<span style="background: {}20; color: {}; padding: 4px 10px; border-radius: 20px; font-weight: bold;">⭐ {:.1f}</span>',
            color, color, obj.overall_rating
        )
    overall_rating_display.short_description = 'Рейтинг'