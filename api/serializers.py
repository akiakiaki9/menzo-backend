from django.db.models import Avg
from rest_framework import serializers
from .models import (
    Restaurant, RestaurantImage, MenuItem, MenuCategory, Booking, 
    RestaurantFeature, RestaurantFeatureRelation,
    RatingCategory, RestaurantRating, RestaurantAnalytics,
    Cart, CartItem
)

class RestaurantImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = RestaurantImage
        fields = ('id', 'image', 'image_url', 'order')
    
    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class MenuCategorySerializer(serializers.ModelSerializer):
    items_count = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuCategory
        fields = ('id', 'name', 'name_uz', 'name_ru', 'name_en', 'icon', 'image', 'image_url', 'order', 'is_active', 'items_count')
    
    def get_items_count(self, obj):
        return obj.menu_items.count()
    
    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    category_image_url = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MenuItem
        fields = ('id', 'name', 'description', 'price', 'image', 'image_url', 'is_recommended', 'order', 'category', 'category_name', 'category_icon', 'category_image_url')
    
    def get_image_url(self, obj):
        if obj.image:
            return obj.image.url
        return None
    
    def get_category_image_url(self, obj):
        if obj.category and obj.category.image:
            return obj.category.image.url
        return None


class RestaurantFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestaurantFeature
        fields = ('id', 'value', 'label')


class RatingCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RatingCategory
        fields = ('id', 'name', 'slug', 'icon', 'weight')


class RestaurantRatingSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)
    
    class Meta:
        model = RestaurantRating
        fields = ('id', 'category', 'category_name', 'category_icon', 'customer_name', 'score', 'comment', 'created_at')


class RestaurantAnalyticsSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    
    class Meta:
        model = RestaurantAnalytics
        fields = '__all__'


class RestaurantSerializer(serializers.ModelSerializer):
    images = RestaurantImageSerializer(many=True, read_only=True)
    menu_items = MenuItemSerializer(many=True, read_only=True)
    menu_categories = MenuCategorySerializer(many=True, read_only=True)
    features = serializers.SerializerMethodField()
    cuisines_list = serializers.SerializerMethodField()
    establishment_type_label = serializers.CharField(source='get_establishment_type_display', read_only=True)
    cuisine_type_label = serializers.CharField(source='get_cuisine_type_display', read_only=True)
    region_label = serializers.CharField(source='get_region_display', read_only=True)
    logo_url = serializers.SerializerMethodField()
    
    # НОВЫЕ ПОЛЯ ДЛЯ УПРАВЛЕНИЯ
    is_accepting_orders = serializers.BooleanField(read_only=True)
    is_accepting_bookings = serializers.BooleanField(read_only=True)
    is_gold = serializers.BooleanField(read_only=True)
    
    # НОВЫЕ ПОЛЯ ДЛЯ ВИДИМОСТИ
    is_published = serializers.BooleanField(read_only=True)
    is_menu_published = serializers.BooleanField(read_only=True)
    
    analytics = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    rating_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = Restaurant
        fields = '__all__'
    
    def get_logo_url(self, obj):
        if obj.logo:
            return obj.logo.url
        return None
    
    def get_features(self, obj):
        relations = obj.feature_relations.select_related('feature').all()
        return [{'id': rel.feature.id, 'value': rel.feature.value, 'label': rel.feature.label} for rel in relations]
    
    def get_cuisines_list(self, obj):
        return obj.get_cuisines_list()
    
    def get_rating(self, obj):
        stats = self._get_ratings_from_analytics(obj)
        if stats['overall'] > 0:
            return stats['overall']
        return self._calculate_ratings(obj)['overall']
    
    def get_analytics(self, obj):
        analytics = getattr(obj, 'analytics', None)
        if analytics and analytics.total_ratings and any((analytics.food_avg, analytics.service_avg, analytics.atmosphere_avg, analytics.overall_rating)):
            return RestaurantAnalyticsSerializer(analytics).data
        stats = self._calculate_ratings(obj)
        return {
            'id': None,
            'restaurant_name': obj.name,
            'total_ratings': stats['total'],
            'unique_raters': obj.ratings.values('session_key').distinct().count(),
            'food_avg': stats['food'],
            'service_avg': stats['service'],
            'atmosphere_avg': stats['atmosphere'],
            'overall_rating': stats['overall'],
            'views_count': getattr(getattr(obj, 'analytics', None), 'views_count', 0),
            'last_updated': getattr(getattr(obj, 'analytics', None), 'last_updated', None),
            'restaurant': obj.id
        }
    
    def get_rating_stats(self, obj):
        stats = self._get_ratings_from_analytics(obj)
        if stats['total'] > 0 and stats['overall'] > 0:
            return stats
        return self._calculate_ratings(obj)
    
    def _get_ratings_from_analytics(self, obj):
        analytics = getattr(obj, 'analytics', None)
        if not analytics:
            return {'overall': 0, 'food': 0, 'service': 0, 'atmosphere': 0, 'total': 0}
        return {
            'overall': round(analytics.overall_rating, 1),
            'food': round(analytics.food_avg, 1),
            'service': round(analytics.service_avg, 1),
            'atmosphere': round(analytics.atmosphere_avg, 1),
            'total': analytics.total_ratings
        }
    
    def _calculate_ratings(self, obj):
        ratings = obj.ratings.all()
        if not ratings.exists():
            return {'overall': 0, 'food': 0, 'service': 0, 'atmosphere': 0, 'total': 0}

        food_avg = ratings.filter(category__slug='food').aggregate(Avg('score'))['score__avg'] or 0
        service_avg = ratings.filter(category__slug='service').aggregate(Avg('score'))['score__avg'] or 0
        atmosphere_avg = ratings.filter(category__slug='atmosphere').aggregate(Avg('score'))['score__avg'] or 0
        total = ratings.count()
        overall = ratings.aggregate(Avg('score'))['score__avg'] or 0

        return {
            'overall': round(overall, 1),
            'food': round(food_avg, 1),
            'service': round(service_avg, 1),
            'atmosphere': round(atmosphere_avg, 1),
            'total': total
        }


class BookingSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    restaurant_telegram_chat_id = serializers.CharField(source='restaurant.telegram_chat_id', read_only=True)
    
    class Meta:
        model = Booking
        fields = '__all__'
        read_only_fields = ('booking_number', 'created_at')
    
    def validate_customer_phone(self, value):
        if not value or len(value) < 9:
            raise serializers.ValidationError("Введите корректный номер телефона")
        return value
    
    def validate_customer_name(self, value):
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Введите корректное имя (минимум 2 символа)")
        return value.strip()
    
    def validate_guests(self, value):
        if value < 1:
            raise serializers.ValidationError("Количество гостей должно быть не менее 1")
        if value > 50:
            raise serializers.ValidationError("Максимальное количество гостей - 50")
        return value
    

class CartItemSerializer(serializers.ModelSerializer):
    menu_item_name = serializers.CharField(source='menu_item.name', read_only=True)
    menu_item_price = serializers.DecimalField(source='menu_item.price', read_only=True, max_digits=10, decimal_places=0)
    menu_item_image = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    
    class Meta:
        model = CartItem
        fields = ('id', 'menu_item', 'menu_item_name', 'menu_item_price', 'menu_item_image', 'quantity', 'total')
    
    def get_menu_item_image(self, obj):
        if obj.menu_item.image:
            return obj.menu_item.image.url
        return None
    
    def get_total(self, obj):
        return obj.get_total()


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    
    class Meta:
        model = Cart
        fields = ('id', 'restaurant', 'restaurant_name', 'items', 'total', 'created_at', 'updated_at')
    
    def get_total(self, obj):
        return obj.get_total()