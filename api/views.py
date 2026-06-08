from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.decorators import throttle_classes
from django.conf import settings
from django.db.models import Q, Count, Avg
from django.utils import timezone
from .models import (
    Restaurant, Booking, RestaurantFeature, MenuCategory,
    RatingCategory, RestaurantRating, RestaurantAnalytics,
    Cart, CartItem, MenuItem
)
from .serializers import (
    RestaurantSerializer, BookingSerializer, MenuCategorySerializer,
    RatingCategorySerializer, RestaurantRatingSerializer,
    RestaurantAnalyticsSerializer, CartSerializer, CartItemSerializer
)
from .throttles import FormRateThrottle
import requests
import hashlib
import uuid
import pytz
from math import radians, sin, cos, sqrt, atan2
from datetime import timedelta

# Часовой пояс Ташкента
TA_SHKENT_TZ = pytz.timezone('Asia/Tashkent')


class RestaurantViewSet(viewsets.ModelViewSet):
    queryset = Restaurant.objects.filter(is_published=True)  # Только опубликованные рестораны
    serializer_class = RestaurantSerializer
    lookup_field = 'slug'
    
    def get_queryset(self):
        # Базовый queryset - только опубликованные
        queryset = Restaurant.objects.filter(is_published=True)
        
        cuisine = self.request.query_params.get('cuisine', None)
        price = self.request.query_params.get('price', None)
        establishment_type = self.request.query_params.get('type', None)
        region = self.request.query_params.get('region', None)
        search = self.request.query_params.get('search', None)
        
        if cuisine and cuisine != 'Все' and cuisine != 'all':
            queryset = queryset.filter(
                Q(cuisine_type=cuisine) | Q(additional_cuisines__icontains=cuisine)
            )
        if price and price != 'Все' and price != 'all':
            queryset = queryset.filter(price_level=price)
        if establishment_type and establishment_type != 'Все' and establishment_type != 'all':
            queryset = queryset.filter(establishment_type=establishment_type)
        if region and region != 'Все' and region != 'all':
            queryset = queryset.filter(region=region)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(cuisine_type__icontains=search) |
                Q(additional_cuisines__icontains=search)
            )
        
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        analytics, created = RestaurantAnalytics.objects.get_or_create(restaurant=instance)
        analytics.views_count += 1
        analytics.save()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def filters(self, request):
        # Используем только опубликованные рестораны для фильтров
        restaurants = Restaurant.objects.filter(is_published=True)
        
        establishment_types = restaurants.values_list('establishment_type', flat=True).distinct()
        type_options = []
        for et in establishment_types:
            if et:
                type_options.append({
                    'value': et,
                    'label': dict(Restaurant.TYPE_CHOICES).get(et, et)
                })
        
        cuisine_options = []
        all_cuisines = set()
        
        for cuisine in restaurants.values_list('cuisine_type', flat=True).distinct():
            if cuisine:
                all_cuisines.add(cuisine)
        
        for additional in restaurants.values_list('additional_cuisines', flat=True):
            if additional:
                for c in additional.split(','):
                    c = c.strip()
                    if c:
                        all_cuisines.add(c)
        
        for cuisine in sorted(all_cuisines):
            cuisine_options.append({
                'value': cuisine.lower().replace(' ', '_'),
                'label': cuisine
            })
        
        price_options = []
        price_labels = {
            '$': 'Эконом (до 50,000 сум)',
            '$$': 'Средний (50,000 - 150,000 сум)',
            '$$$': 'Высокий (150,000 - 300,000 сум)',
            '$$$$': 'Премиум (от 300,000 сум)'
        }
        for price in restaurants.values_list('price_level', flat=True).distinct():
            if price:
                price_options.append({
                    'value': price,
                    'label': price_labels.get(price, price)
                })
        
        feature_options = []
        features = RestaurantFeature.objects.all()
        for feature in features:
            feature_options.append({
                'value': feature.value,
                'label': feature.label
            })
        
        return Response({
            'types': type_options,
            'cuisines': cuisine_options,
            'prices': price_options,
            'features': feature_options
        })
    
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        try:
            lat = float(request.query_params.get('lat', 0))
            lng = float(request.query_params.get('lng', 0))
            radius = float(request.query_params.get('radius', 5))
            
            if lat == 0 or lng == 0:
                return Response({'error': 'Укажите координаты lat и lng'}, status=400)
            
            # Только опубликованные рестораны
            restaurants = self.get_queryset().filter(
                latitude__isnull=False,
                longitude__isnull=False,
                show_on_map=True
            )
            
            nearby_restaurants = []
            R = 6371
            
            for restaurant in restaurants:
                lat1 = radians(lat)
                lon1 = radians(lng)
                lat2 = radians(float(restaurant.latitude))
                lon2 = radians(float(restaurant.longitude))
                
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * atan2(sqrt(a), sqrt(1-a))
                distance = R * c
                
                if distance <= radius:
                    nearby_restaurants.append({
                        'id': restaurant.id,
                        'name': restaurant.name,
                        'slug': restaurant.slug,
                        'address': restaurant.address,
                        'cuisine': restaurant.cuisine_type,
                        'price_level': restaurant.price_level,
                        'rating': restaurant.rating,
                        'distance': round(distance, 2),
                        'latitude': float(restaurant.latitude),
                        'longitude': float(restaurant.longitude),
                        'image': restaurant.images.first().image.url if restaurant.images.exists() else None
                    })
            
            nearby_restaurants.sort(key=lambda x: x['distance'])
            return Response(nearby_restaurants)
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['get'])
    def top_restaurants(self, request):
        sort_by = request.query_params.get('sort', 'rating')
        limit = int(request.query_params.get('limit', 10))
        establishment_type = request.query_params.get('type', None)
        
        # Только опубликованные рестораны
        restaurants = Restaurant.objects.filter(is_published=True).prefetch_related('images', 'analytics')
        
        if establishment_type:
            restaurants = restaurants.filter(establishment_type=establishment_type)
        
        if sort_by == 'rating':
            restaurants = sorted(restaurants, key=lambda x: x.rating, reverse=True)
        elif sort_by == 'popular':
            restaurants = sorted(restaurants, key=lambda x: x.analytics.total_ratings if hasattr(x, 'analytics') else 0, reverse=True)
        elif sort_by == 'trending':
            week_ago = timezone.now() - timedelta(days=7)
            restaurants = sorted(restaurants, key=lambda x: x.ratings.filter(created_at__gte=week_ago).count(), reverse=True)
        
        restaurants = restaurants[:limit]
        
        result = []
        for r in restaurants:
            result.append({
                'id': r.id,
                'name': r.name,
                'slug': r.slug,
                'rating': r.rating,
                'overall_rating': r.analytics.overall_rating if hasattr(r, 'analytics') else r.rating,
                'price_level': r.price_level,
                'cuisine_type': r.cuisine_type,
                'cuisine_type_label': r.get_cuisine_type_display(),
                'region': r.region,
                'region_label': r.get_region_display(),
                'image': r.images.first().image.url if r.images.exists() else None,
                'total_ratings': r.analytics.total_ratings if hasattr(r, 'analytics') else 0
            })
        
        return Response(result)
    
    @action(detail=True, methods=['get'])
    def menu_categories(self, request, slug=None):
        restaurant = self.get_object()
        categories = restaurant.menu_categories.filter(is_active=True)
        serializer = MenuCategorySerializer(categories, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def good_reviews(self, request, slug=None):
        """Получить только хорошие отзывы (оценка 4 и 5)"""
        restaurant = self.get_object()
        
        good_reviews = RestaurantRating.objects.filter(
            restaurant=restaurant,
            score__gte=4,
            comment__isnull=False,
            comment__gt=''
        ).select_related('category').order_by('-created_at')
        
        grouped_reviews = {}
        for review in good_reviews:
            key = f"{review.session_key}_{review.comment}_{review.customer_name}_{review.created_at.date()}"
            if key not in grouped_reviews:
                grouped_reviews[key] = {
                    'customer_name': review.customer_name,
                    'comment': review.comment,
                    'created_at': review.created_at,
                    'ratings': []
                }
            grouped_reviews[key]['ratings'].append({
                'category_name': review.category.name,
                'category_icon': review.category.icon,
                'score': review.score
            })
        
        result = []
        for item in grouped_reviews.values():
            avg_score = sum(r['score'] for r in item['ratings']) / len(item['ratings'])
            result.append({
                'customer_name': item['customer_name'],
                'comment': item['comment'],
                'created_at': item['created_at'],
                'avg_score': round(avg_score, 1),
                'ratings': item['ratings']
            })
        
        return Response(result[:10])
    
    # ========== НОВЫЕ ЭНДПОИНТЫ ДЛЯ GOLD И РЕКОМЕНДАЦИЙ ==========
    
    @action(detail=False, methods=['get'])
    def recommended(self, request):
        """Получить рекомендованные рестораны (только Gold и топ по рейтингу)"""
        limit = int(request.query_params.get('limit', 6))
    
        # Получаем Gold рестораны (только опубликованные)
        gold_restaurants = Restaurant.objects.filter(is_gold=True, is_published=True).prefetch_related('images', 'analytics')
        gold_list = list(gold_restaurants[:limit])
    
        # Если Gold ресторанов меньше limit, добираем топом по рейтингу
        if len(gold_list) < limit:
            remaining = limit - len(gold_list)
            # Исключаем уже добавленные Gold
            gold_ids = [r.id for r in gold_list]
            non_gold_top = list(Restaurant.objects.filter(is_gold=False, is_published=True).exclude(id__in=gold_ids).order_by('-rating')[:remaining])
            gold_list.extend(non_gold_top)
    
        serializer = self.get_serializer(gold_list, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def top_rated(self, request):
        """Получить ресторан с самым высоким рейтингом (только опубликованный)"""
        top_restaurant = Restaurant.objects.filter(is_published=True).order_by('-rating').first()
        if top_restaurant:
            serializer = self.get_serializer(top_restaurant)
            return Response(serializer.data)
        return Response({'error': 'Нет ресторанов'}, status=404)
    
    @action(detail=False, methods=['get'])
    def cities(self, request):
        """Получить список городов, в которых есть рестораны (только опубликованные)"""
        cities_with_count = []
    
        # Группируем рестораны по городам (только опубликованные)
        for region_code, region_name in Restaurant.REGION_CHOICES:
            count = Restaurant.objects.filter(region=region_code, is_published=True).count()
            if count > 0:
                cities_with_count.append({
                    'region': region_code,
                    'name': region_name,
                    'count': count
                })
    
        return Response(cities_with_count)


class RatingViewSet(viewsets.ViewSet):
    """API для работы с оценками"""
    
    def get_session_key(self, request):
        ip = request.META.get('REMOTE_ADDR', '')
        ua = request.META.get('HTTP_USER_AGENT', '')
        key_string = f"{ip}_{ua}"
        return hashlib.md5(key_string.encode()).hexdigest()[:32]
    
    def get_or_create_rating(self, restaurant_id, category_id, session_key, customer_name, ip, ua, score, comment):
        """Получить существующую оценку или создать новую"""
        existing = RestaurantRating.objects.filter(
            restaurant_id=restaurant_id,
            category_id=category_id,
            session_key=session_key
        ).first()
        
        if existing:
            # Обновляем существующую оценку
            existing.score = score
            existing.comment = comment
            existing.customer_name = customer_name
            existing.updated_at = timezone.now()
            existing.save()
            return existing
        else:
            # Создаём новую оценку
            return RestaurantRating.objects.create(
                restaurant_id=restaurant_id,
                category_id=category_id,
                session_key=session_key,
                customer_name=customer_name,
                ip_address=ip,
                user_agent=ua[:500],
                score=score,
                comment=comment
            )
    
    def update_restaurant_analytics(self, restaurant_id):
        analytics, created = RestaurantAnalytics.objects.get_or_create(restaurant_id=restaurant_id)
        
        food_ratings = RestaurantRating.objects.filter(
            restaurant_id=restaurant_id,
            category__slug='food'
        )
        service_ratings = RestaurantRating.objects.filter(
            restaurant_id=restaurant_id,
            category__slug='service'
        )
        atmosphere_ratings = RestaurantRating.objects.filter(
            restaurant_id=restaurant_id,
            category__slug='atmosphere'
        )
        
        analytics.food_avg = food_ratings.aggregate(Avg('score'))['score__avg'] or 0
        analytics.service_avg = service_ratings.aggregate(Avg('score'))['score__avg'] or 0
        analytics.atmosphere_avg = atmosphere_ratings.aggregate(Avg('score'))['score__avg'] or 0
        
        analytics.total_ratings = RestaurantRating.objects.filter(restaurant_id=restaurant_id).count()
        analytics.unique_raters = RestaurantRating.objects.filter(
            restaurant_id=restaurant_id
        ).values('session_key').distinct().count()
        
        food_weight = 1.5
        service_weight = 1.2
        atmosphere_weight = 1.0
        total_weight = food_weight + service_weight + atmosphere_weight
        
        analytics.overall_rating = (
            (analytics.food_avg * food_weight) +
            (analytics.service_avg * service_weight) +
            (analytics.atmosphere_avg * atmosphere_weight)
        ) / total_weight
        
        analytics.save()
        
        restaurant = Restaurant.objects.get(id=restaurant_id)
        restaurant.rating = round(analytics.overall_rating, 1)
        restaurant.save()
    
    def send_telegram_review_to_restaurant(self, restaurant, ratings_data, customer_name, comment, is_update=False):
        """Отправляет уведомление о новом или обновлённом отзыве"""
        try:
            if not restaurant.send_review_notifications:
                return
            
            bot_token = restaurant.telegram_bot_token or settings.TELEGRAM_BOT_TOKEN
            chat_id = restaurant.telegram_chat_id or settings.TELEGRAM_CHAT_ID
            
            if not bot_token or not chat_id:
                return
            
            tashkent_now = timezone.now().astimezone(TA_SHKENT_TZ)
            
            ratings_text = ""
            for cat in ratings_data:
                icon_map = {
                    'Еда': '🍜',
                    'Обслуживание': '🤵',
                    'Атмосфера': '🕯️'
                }
                icon = icon_map.get(cat['name'], '⭐')
                ratings_text += f"\n{icon} {cat['name']}: {'⭐' * cat['score']} {cat['score']}/5"
            
            action_text = "ОБНОВЛЁН ОТЗЫВ" if is_update else "НОВЫЙ ОТЗЫВ"
            
            message = f"""
📝 {action_text} 📝
━━━━━━━━━━━━━━━━━━━━━

🏠 Ресторан: {restaurant.name}
👤 Гость: {customer_name or 'Аноним'}

⭐ ОЦЕНКИ:{ratings_text}

💬 КОММЕНТАРИЙ:
{comment[:300] if comment else 'Без комментария'}

━━━━━━━━━━━━━━━━━━━━━
🕐 {tashkent_now.strftime('%d.%m.%Y %H:%M:%S')}
📱 tavsia.uz
"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(url, json={'chat_id': chat_id, 'text': message}, timeout=5)
            print(f"✅ Уведомление об отзыве отправлено в {restaurant.name}")
            
        except Exception as e:
            print(f"❌ Ошибка отправки в Telegram: {e}")
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        categories = RatingCategory.objects.filter(is_active=True)
        serializer = RatingCategorySerializer(categories, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def user_rating(self, request, pk=None):
        session_key = self.get_session_key(request)
        
        ratings = RestaurantRating.objects.filter(
            restaurant_id=pk,
            session_key=session_key
        ).values_list('category_id', 'score', 'customer_name', 'comment')
        
        result = {}
        for r in ratings:
            result[str(r[0])] = r[1]
        
        if ratings:
            result['customer_name'] = ratings[0][2]
            result['comment'] = ratings[0][3]
        
        return Response(result)
    
    @action(detail=True, methods=['post'], throttle_classes=[FormRateThrottle])
    def rate(self, request, pk=None):
        session_key = self.get_session_key(request)
        
        ratings_data = request.data.get('ratings', [])
        comment = request.data.get('comment', '')
        customer_name = request.data.get('customer_name', '').strip()
        
        if not ratings_data:
            return Response({'error': 'Укажите оценки'}, status=400)
        
        if not customer_name:
            customer_name = 'Аноним'
        
        ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
        
        # Сохраняем или обновляем оценки
        saved_ratings = []
        is_update = False
        
        for r in ratings_data:
            rating = self.get_or_create_rating(
                restaurant_id=pk,
                category_id=r['category_id'],
                session_key=session_key,
                customer_name=customer_name,
                ip=ip_address,
                ua=user_agent,
                score=r['score'],
                comment=comment
            )
            saved_ratings.append(rating)
            # Если оценка существовала и была обновлена
            if rating.updated_at != rating.created_at:
                is_update = True
        
        # Обновляем аналитику ресторана
        self.update_restaurant_analytics(pk)
        
        # Отправляем уведомление в Telegram
        restaurant = Restaurant.objects.get(id=pk)
        
        ratings_for_telegram = []
        for r in saved_ratings:
            ratings_for_telegram.append({
                'name': r.category.name,
                'score': r.score
            })
        
        self.send_telegram_review_to_restaurant(restaurant, ratings_for_telegram, customer_name, comment, is_update)
        
        return Response({'success': True, 'message': 'Спасибо за оценку!'})


class BookingViewSet(viewsets.ModelViewSet):
    throttle_classes = [FormRateThrottle]
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    
    def create(self, request, *args, **kwargs):
        print("=" * 50)
        print("📝 Получены данные от фронтенда:")
        print(request.data)
        print("=" * 50)
        
        restaurant_id = request.data.get('restaurant')
        if not restaurant_id:
            return Response({'restaurant': ['Не указан ресторан']}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
        except Restaurant.DoesNotExist:
            return Response({'restaurant': ['Ресторан не найден']}, status=status.HTTP_404_NOT_FOUND)
        
        # ========== НОВАЯ ПРОВЕРКА ==========
        if not restaurant.is_accepting_bookings:
            return Response({
                'error': 'Ресторан временно не принимает бронирования',
                'code': 'bookings_disabled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        booking_data = {
            'restaurant': restaurant.id,
            'customer_name': request.data.get('customer_name', '').strip(),
            'customer_phone': request.data.get('customer_phone', '').strip(),
            'customer_email': request.data.get('customer_email', '').strip(),
            'date': request.data.get('date'),
            'time': request.data.get('time'),
            'guests': request.data.get('guests', 2),
            'comment': request.data.get('comment', '').strip()
        }
        
        serializer = self.get_serializer(data=booking_data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        booking = serializer.save()
        
        self.send_telegram_notification_to_restaurant(booking)
        
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def send_telegram_notification_to_restaurant(self, booking):
        try:
            restaurant = booking.restaurant
            if not restaurant.send_booking_notifications:
                return
            
            bot_token = restaurant.telegram_bot_token or settings.TELEGRAM_BOT_TOKEN
            chat_id = restaurant.telegram_chat_id or settings.TELEGRAM_CHAT_ID
            
            if not bot_token or not chat_id:
                return
            
            tashkent_now = timezone.now().astimezone(TA_SHKENT_TZ)
            
            message = f"""
🆕 НОВОЕ БРОНИРОВАНИЕ 🆕
━━━━━━━━━━━━━━━━━━━━━

🔢 Номер: {booking.booking_number}
🏠 Ресторан: {booking.restaurant.name}
👤 Имя: {booking.customer_name}
📱 Телефон: {booking.customer_phone}
📅 Дата: {booking.date}
⏰ Время: {booking.time}
👥 Гостей: {booking.guests}
💭 Пожелания: {booking.comment or 'нет'}

━━━━━━━━━━━━━━━━━━━━━
🕐 {tashkent_now.strftime('%d.%m.%Y %H:%M:%S')}
📱 tavsia.uz
"""
            
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(url, json={'chat_id': chat_id, 'text': message}, timeout=5)
            
        except Exception as e:
            print(f"❌ Ошибка отправки в Telegram: {e}")


class CartViewSet(viewsets.ViewSet):
    """API для работы с корзиной"""
    
    def get_session_key(self, request):
        ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', ''))
        ua = request.META.get('HTTP_USER_AGENT', '')[:50]
        key_string = f"{ip}_{ua}"
        if not key_string or key_string == '_':
            key_string = str(uuid.uuid4())
        return hashlib.md5(key_string.encode()).hexdigest()[:32]
    
    @action(detail=False, methods=['get'])
    def my_cart(self, request):
        try:
            session_key = self.get_session_key(request)
            print(f"🔑 Session key для корзины: {session_key}")
            
            carts = Cart.objects.filter(session_key=session_key).prefetch_related('items__menu_item')
            result = []
            for cart in carts:
                serializer = CartSerializer(cart)
                result.append(serializer.data)
            
            return Response(result)
        except Exception as e:
            print(f"❌ Ошибка в my_cart: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=True, methods=['post'])
    def add_item(self, request, pk=None):
        try:
            print(f"📝 Добавление товара в ресторан {pk}")
            print(f"📝 Данные запроса: {request.data}")
            
            session_key = self.get_session_key(request)
            print(f"🔑 Session key: {session_key}")
            
            menu_item_id = request.data.get('menu_item_id')
            quantity = int(request.data.get('quantity', 1))
            
            if not menu_item_id:
                return Response({'error': 'Не указан товар'}, status=400)
            
            try:
                menu_item = MenuItem.objects.get(id=menu_item_id, restaurant_id=pk)
                print(f"✅ Товар найден: {menu_item.name}")
            except MenuItem.DoesNotExist:
                return Response({'error': 'Товар не найден'}, status=404)
            
            cart, created = Cart.objects.get_or_create(
                session_key=session_key,
                restaurant_id=pk
            )
            print(f"📦 Корзина: {'создана' if created else 'существующая'}")
            
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                menu_item=menu_item,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
                print(f"🔄 Обновлено количество: {cart_item.quantity}")
            else:
                print(f"➕ Добавлен новый товар")
            
            serializer = CartSerializer(cart)
            return Response(serializer.data)
            
        except Exception as e:
            print(f"❌ Ошибка в add_item: {e}")
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)
    
    @action(detail=True, methods=['post'])
    def remove_item(self, request, pk=None):
        try:
            session_key = self.get_session_key(request)
            menu_item_id = request.data.get('menu_item_id')
            
            if not menu_item_id:
                return Response({'error': 'Не указан товар'}, status=400)
            
            cart = Cart.objects.get(session_key=session_key, restaurant_id=pk)
            cart_item = CartItem.objects.get(cart=cart, menu_item_id=menu_item_id)
            cart_item.delete()
            
            serializer = CartSerializer(cart)
            return Response(serializer.data)
            
        except Cart.DoesNotExist:
            return Response({'error': 'Корзина не найдена'}, status=404)
        except CartItem.DoesNotExist:
            return Response({'error': 'Товар не найден в корзине'}, status=404)
        except Exception as e:
            print(f"❌ Ошибка в remove_item: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=True, methods=['post'])
    def update_quantity(self, request, pk=None):
        try:
            session_key = self.get_session_key(request)
            menu_item_id = request.data.get('menu_item_id')
            quantity = int(request.data.get('quantity', 1))
            
            if not menu_item_id:
                return Response({'error': 'Не указан товар'}, status=400)
            
            if quantity <= 0:
                return self.remove_item(request, pk)
            
            cart = Cart.objects.get(session_key=session_key, restaurant_id=pk)
            cart_item = CartItem.objects.get(cart=cart, menu_item_id=menu_item_id)
            cart_item.quantity = quantity
            cart_item.save()
            
            serializer = CartSerializer(cart)
            return Response(serializer.data)
            
        except Cart.DoesNotExist:
            return Response({'error': 'Корзина не найдена'}, status=404)
        except CartItem.DoesNotExist:
            return Response({'error': 'Товар не найден в корзине'}, status=404)
        except Exception as e:
            print(f"❌ Ошибка в update_quantity: {e}")
            return Response({'error': str(e)}, status=500)
    
    @action(detail=True, methods=['delete'])
    def clear(self, request, pk=None):
        try:
            session_key = self.get_session_key(request)
            
            cart = Cart.objects.get(session_key=session_key, restaurant_id=pk)
            cart.items.all().delete()
            cart.delete()
            return Response({'success': True, 'message': 'Корзина очищена'})
            
        except Cart.DoesNotExist:
            return Response({'success': True, 'message': 'Корзина уже пуста'})
        except Exception as e:
            print(f"❌ Ошибка в clear: {e}")
            return Response({'error': str(e)}, status=500)


class OrderAPIView(APIView):
    throttle_classes = [FormRateThrottle]
    """API для оформления заказа"""
    
    def post(self, request):
        data = request.data
        restaurant_id = data.get('restaurant_id')
        customer_name = data.get('customer_name')
        customer_phone = data.get('customer_phone')
        comment = data.get('comment', '')
        items = data.get('items', [])
        total = data.get('total', 0)
        
        try:
            restaurant = Restaurant.objects.get(id=restaurant_id)
        except Restaurant.DoesNotExist:
            return Response({'error': 'Ресторан не найден'}, status=404)
        
        # ========== НОВАЯ ПРОВЕРКА ==========
        if not restaurant.is_accepting_orders:
            return Response({
                'error': 'Ресторан временно не принимает заказы',
                'code': 'orders_disabled'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        items_text = ""
        for item in items:
            items_text += f"\n   • {item['name']} x{item['quantity']} = {item['total']:,} сум"
        
        tashkent_now = timezone.now().astimezone(TA_SHKENT_TZ)
        
        message = f"""
🛍️ НОВЫЙ ЗАКАЗ 🛍️
━━━━━━━━━━━━━━━━━━━━━

🏠 Ресторан: {restaurant.name}
👤 Заказчик: {customer_name}
📱 Телефон: {customer_phone}

📋 СОСТАВ ЗАКАЗА:
{items_text}

💰 ИТОГО: {total:,} сум

💭 КОММЕНТАРИЙ:
{comment if comment else 'Нет'}

━━━━━━━━━━━━━━━━━━━━━
🕐 {tashkent_now.strftime('%d.%m.%Y %H:%M:%S')}
📱 tavsia.uz
"""
        
        bot_token = restaurant.telegram_bot_token or settings.TELEGRAM_BOT_TOKEN
        chat_id = restaurant.telegram_chat_id or settings.TELEGRAM_CHAT_ID
        
        if bot_token and chat_id:
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            requests.post(url, json={'chat_id': chat_id, 'text': message}, timeout=5)
        
        return Response({'success': True, 'message': 'Заказ отправлен'})