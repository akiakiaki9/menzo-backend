from django.db import models
import json

class Restaurant(models.Model):
    # Типы заведений
    TYPE_CHOICES = [
        ('restaurant', 'Ресторан'),
        ('cafe', 'Кафе'),
        ('fastfood', 'Фастфуд'),
        ('restobar', 'Рестобар'),
        ('coffeehouse', 'Кофейня'),
        ('teahouse', 'Чайхана'),
        ('bakery', 'Пекарня / Кондитерская'),
        ('canteen', 'Столовая'),
    ]
    
    # Типы кухонь
    CUISINE_TYPE_CHOICES = [
        ('uzbek', 'Узбекская'),
        ('european', 'Европейская'),
        ('italian', 'Итальянская'),
        ('turkish', 'Турецкая'),
        ('caucasian', 'Кавказская'),
        ('asian', 'Азиатская'),
        ('japanese', 'Японская (суши)'),
        ('fastfood', 'Бургеры / Фастфуд'),
    ]
    
    PRICE_CHOICES = [
        ('$', 'Эконом (до 50,000 сум)'),
        ('$$', 'Средний (50,000 - 150,000 сум)'),
        ('$$$', 'Высокий (150,000 - 300,000 сум)'),
        ('$$$$', 'Премиум (от 300,000 сум)'),
    ]
    
    # Города и регионы Узбекистана
    REGION_CHOICES = [
        ('tashkent', 'Ташкент'),
        ('tashkent_region', 'Ташкентская область'),
        ('samarkand', 'Самарканд'),
        ('bukhara', 'Бухара'),
        ('khiva', 'Хива'),
        ('fergana', 'Фергана'),
        ('andijan', 'Андижан'),
        ('namangan', 'Наманган'),
        ('kokand', 'Коканд'),
        ('nukus', 'Нукус'),
        ('termiz', 'Термез'),
        ('qarshi', 'Карши'),
        ('navoi', 'Навои'),
        ('jizzakh', 'Джизак'),
        ('gulistan', 'Гулистан'),
        ('urgench', 'Ургенч'),
        ('other', 'Другой город'),
    ]
    
    # Основные поля
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('URL', unique=True)
    description = models.TextField('Описание', blank=True)
    address = models.CharField('Адрес', max_length=300)
    region = models.CharField('Город/Область', max_length=30, choices=REGION_CHOICES, default='tashkent', db_index=True)
    phone = models.CharField('Телефон', max_length=50)
    email = models.EmailField('Email', blank=True)
    
    # Тип заведения
    establishment_type = models.CharField('Тип заведения', max_length=20, choices=TYPE_CHOICES, default='restaurant')
    
    # Кухня
    cuisine_type = models.CharField('Тип кухни', max_length=20, choices=CUISINE_TYPE_CHOICES, default='uzbek')
    cuisine = models.CharField('Основная кухня (текст)', max_length=50, blank=True)
    
    price_level = models.CharField('Уровень цен', max_length=5, choices=PRICE_CHOICES, default='$$')
    rating = models.FloatField('Рейтинг', default=0)
    working_hours = models.CharField('Часы работы', max_length=200, default='11:00 - 23:00')
    
    # Координаты для карты
    latitude = models.DecimalField('Широта', max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField('Долгота', max_digits=10, decimal_places=7, null=True, blank=True)
    show_on_map = models.BooleanField('Показывать на карте', default=True)
    
    # Дополнительные кухни
    additional_cuisines = models.CharField('Дополнительные кухни', max_length=200, blank=True)
    
    # Соц сети
    instagram = models.URLField('Instagram', blank=True)
    telegram = models.URLField('Telegram', blank=True)
    facebook = models.URLField('Facebook', blank=True)
    website = models.URLField('Сайт', blank=True)
    
    # ========== НОВОЕ ПОЛЕ: ЛОГОТИП РЕСТОРАНА ==========
    logo = models.ImageField(
        'Логотип ресторана',
        upload_to='restaurants/logos/',
        blank=True,
        null=True,
        help_text='Загрузите логотип ресторана (круглая иконка)'
    )
    
    # ========== НОВЫЕ ПОЛЯ ДЛЯ TELEGRAM ==========
    telegram_chat_id = models.CharField(
        'Telegram Chat ID для уведомлений',
        max_length=100,
        blank=True,
        null=True,
        help_text='ID чата в Telegram для отправки уведомлений о бронированиях и отзывах'
    )
    telegram_bot_token = models.CharField(
        'Токен Telegram бота',
        max_length=255,
        blank=True,
        null=True,
        help_text='Если оставить пустым, будет использоваться основной токен бота'
    )
    send_booking_notifications = models.BooleanField(
        'Отправлять уведомления о бронированиях',
        default=True
    )
    send_review_notifications = models.BooleanField(
        'Отправлять уведомления об отзывах',
        default=True
    )
    
    # ========== НОВЫЕ ПОЛЯ ДЛЯ УПРАВЛЕНИЯ РЕСТОРАНОМ ==========
    is_accepting_orders = models.BooleanField(
        'Принимает заказы',
        default=False,
        help_text='Вкл/Выкл приём заказов через сайт'
    )
    is_accepting_bookings = models.BooleanField(
        'Принимает бронирования',
        default=False,
        help_text='Вкл/Выкл приём бронирований через сайт'
    )
    is_gold = models.BooleanField(
        'Gold ресторан',
        default=False,
        help_text='Премиум статус ресторана (Gold тариф)'
    )
    
    # ========== НОВЫЕ ПОЛЯ ДЛЯ ВИДИМОСТИ ==========
    is_published = models.BooleanField(
        'Опубликован на сайте',
        default=True,
        help_text='Отображать ресторан на сайте. Если снять галочку, ресторан будет скрыт'
    )
    is_menu_published = models.BooleanField(
        'Меню опубликовано',
        default=True,
        help_text='Отображать меню ресторана. Если снять галочку, страница меню будет недоступна'
    )
    
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        verbose_name = 'Ресторан'
        verbose_name_plural = 'Рестораны'
        ordering = ['-rating']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.cuisine:
            self.cuisine = self.get_cuisine_type_display()
        super().save(*args, **kwargs)
    
    def get_cuisines_list(self):
        cuisines = [self.get_cuisine_type_display()]
        if self.additional_cuisines:
            cuisines.extend([c.strip() for c in self.additional_cuisines.split(',')])
        return cuisines
    
    def get_region_display_ru(self):
        region_dict = dict(self.REGION_CHOICES)
        return region_dict.get(self.region, self.region)


class RestaurantFeature(models.Model):
    FEATURE_CHOICES = [
        ('family', 'Семейный'),
        ('romantic', 'Для свиданий'),
        ('friends', 'С друзьями'),
        ('business_lunch', 'Бизнес-ланч'),
        ('kids_friendly', 'С детьми'),
        ('terrace', 'Терраса'),
        ('live_music', 'Живая музыка'),
        ('hookah', 'Кальян'),
        ('karaoke', 'Караоке'),
        ('wifi', 'Wi-Fi'),
        ('parking', 'Парковка'),
        ('air_conditioning', 'Кондиционер'),
        ('delivery', 'Доставка'),
        ('takeaway', 'Самовывоз'),
        ('online_booking', 'Онлайн-бронирование'),
        ('open_now', 'Открыто сейчас'),
    ]
    
    value = models.CharField('Код', max_length=30, unique=True, choices=FEATURE_CHOICES)
    label = models.CharField('Название', max_length=50)
    
    class Meta:
        verbose_name = 'Особенность'
        verbose_name_plural = 'Особенности'
        ordering = ['label']
    
    def __str__(self):
        return self.label


class RestaurantFeatureRelation(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='feature_relations')
    feature = models.ForeignKey(RestaurantFeature, on_delete=models.CASCADE, related_name='restaurant_relations')
    
    class Meta:
        unique_together = ('restaurant', 'feature')
        verbose_name = 'Особенность ресторана'
        verbose_name_plural = 'Особенности ресторанов'
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.feature.label}"


class RestaurantImage(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField('Фото', upload_to='restaurants/')
    order = models.IntegerField('Порядок', default=0)
    created_at = models.DateTimeField('Загружено', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Фото ресторана'
        verbose_name_plural = 'Фото ресторана'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.restaurant.name} - Фото {self.order}"


# ========== НОВАЯ МОДЕЛЬ: КАТЕГОРИИ МЕНЮ ==========
class MenuCategory(models.Model):
    """Категория для группировки блюд в меню"""
    restaurant = models.ForeignKey(
        Restaurant, 
        on_delete=models.CASCADE, 
        related_name='menu_categories'
    )
    name = models.CharField('Название категории', max_length=100)
    name_uz = models.CharField('Название (Узбекский)', max_length=100, blank=True)
    name_ru = models.CharField('Название (Русский)', max_length=100, blank=True)
    name_en = models.CharField('Название (Английский)', max_length=100, blank=True)
    icon = models.CharField('Иконка (emoji)', max_length=10, blank=True, default='🍽️')
    image = models.ImageField(
        'Фото категории', 
        upload_to='menu/categories/', 
        blank=True, 
        null=True,
        help_text='Загрузите фото для категории (будет отображаться в меню)'
    )
    order = models.PositiveIntegerField('Порядок отображения', default=0)
    is_active = models.BooleanField('Активна', default=True)
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Категория меню'
        verbose_name_plural = 'Категории меню'
        ordering = ['order', 'name']
        unique_together = ('restaurant', 'name')
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.name}"
    
    def get_translated_name(self, lang='ru'):
        """Возвращает название на нужном языке"""
        if lang == 'uz' and self.name_uz:
            return self.name_uz
        if lang == 'en' and self.name_en:
            return self.name_en
        return self.name


class MenuItem(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='menu_items')
    category = models.ForeignKey(
        MenuCategory, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='menu_items',
        verbose_name='Категория'
    )
    name = models.CharField('Название блюда', max_length=200)
    description = models.TextField('Описание', blank=True)
    price = models.DecimalField('Цена (сум)', max_digits=10, decimal_places=0)
    image = models.ImageField('Фото блюда', upload_to='menu/items/', blank=True, null=True)
    is_recommended = models.BooleanField('Рекомендуемое', default=False)
    order = models.IntegerField('Порядок', default=0)
    created_at = models.DateTimeField('Создано', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Блюдо'
        verbose_name_plural = 'Меню'
        ordering = ['category__order', 'order', 'name']
    
    def __str__(self):
        return f"{self.name} - {self.price} сум"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('confirmed', 'Подтверждено'),
        ('cancelled', 'Отменено'),
        ('completed', 'Завершено'),
    ]
    
    booking_number = models.CharField('Номер брони', max_length=50, unique=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='bookings')
    customer_name = models.CharField('Имя', max_length=200)
    customer_phone = models.CharField('Телефон', max_length=50)
    customer_email = models.EmailField('Email', blank=True)
    date = models.DateField('Дата')
    time = models.TimeField('Время')
    guests = models.IntegerField('Количество гостей')
    comment = models.TextField('Комментарий', blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    
    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.booking_number} - {self.customer_name}"
    
    def save(self, *args, **kwargs):
        if not self.booking_number:
            import random
            from datetime import datetime
            date_str = datetime.now().strftime('%Y%m%d')
            random_num = random.randint(1000, 9999)
            self.booking_number = f"BK-{date_str}-{random_num}"
        super().save(*args, **kwargs)


# ========== МОДЕЛИ ДЛЯ ОЦЕНОК ==========

class RatingCategory(models.Model):
    name = models.CharField('Название', max_length=50)
    slug = models.SlugField('URL', unique=True)
    icon = models.CharField('Иконка', max_length=10, default='⭐')
    weight = models.FloatField('Вес в общем рейтинге', default=1.0)
    is_active = models.BooleanField('Активна', default=True)
    order = models.IntegerField('Порядок', default=0)
    
    class Meta:
        verbose_name = 'Категория оценки'
        verbose_name_plural = 'Категории оценок'
        ordering = ['order']
    
    def __str__(self):
        return self.name


class RestaurantRating(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='ratings')
    category = models.ForeignKey(RatingCategory, on_delete=models.CASCADE, related_name='ratings')
    
    # НОВОЕ ПОЛЕ
    customer_name = models.CharField('Имя пользователя', max_length=100, blank=True, default='Аноним')
    
    session_key = models.CharField('Ключ сессии', max_length=100, db_index=True)
    ip_address = models.GenericIPAddressField('IP адрес', null=True, blank=True)
    user_agent = models.TextField('User Agent', blank=True)
    
    score = models.IntegerField('Оценка', choices=[(1,1),(2,2),(3,3),(4,4),(5,5)])
    comment = models.TextField('Отзыв', blank=True)
    
    is_verified = models.BooleanField('Подтвержден', default=False)
    is_moderated = models.BooleanField('Промодерирован', default=False)
    
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    
    class Meta:
        unique_together = ('restaurant', 'category', 'session_key')
        verbose_name = 'Оценка ресторана'
        verbose_name_plural = 'Оценки ресторанов'
    
    def __str__(self):
        return f"{self.restaurant.name} - {self.category.name}: {self.score}★"


class RestaurantAnalytics(models.Model):
    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE, related_name='analytics')
    
    total_ratings = models.IntegerField('Всего оценок', default=0)
    unique_raters = models.IntegerField('Уникальных оценивших', default=0)
    
    food_avg = models.FloatField('Средняя оценка еды', default=0)
    service_avg = models.FloatField('Средняя оценка обслуживания', default=0)
    atmosphere_avg = models.FloatField('Средняя оценка атмосферы', default=0)
    
    overall_rating = models.FloatField('Общий рейтинг', default=0)
    views_count = models.IntegerField('Просмотров', default=0)
    
    last_updated = models.DateTimeField('Последнее обновление', auto_now=True)
    
    class Meta:
        verbose_name = 'Аналитика ресторана'
        verbose_name_plural = 'Аналитика ресторанов'
    
    def __str__(self):
        return f"{self.restaurant.name} - Рейтинг: {self.overall_rating}"


class Cart(models.Model):
    """Корзина заказов по IP"""
    session_key = models.CharField('Ключ сессии (IP)', max_length=100, db_index=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='carts')
    created_at = models.DateTimeField('Создана', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлена', auto_now=True)
    
    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
        unique_together = ('session_key', 'restaurant')
    
    def __str__(self):
        return f"Корзина {self.session_key[:15]} - {self.restaurant.name}"
    
    def get_total(self):
        return sum(item.get_total() for item in self.items.all())


class CartItem(models.Model):
    """Товар в корзине"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField('Количество', default=1)
    
    class Meta:
        verbose_name = 'Товар в корзине'
        verbose_name_plural = 'Товары в корзине'
        unique_together = ('cart', 'menu_item')
    
    def __str__(self):
        return f"{self.menu_item.name} x{self.quantity}"
    
    def get_total(self):
        return self.menu_item.price * self.quantity