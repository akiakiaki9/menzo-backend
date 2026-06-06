from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from api import views

router = DefaultRouter()
router.register(r'restaurants', views.RestaurantViewSet)
router.register(r'bookings', views.BookingViewSet)
router.register(r'ratings', views.RatingViewSet, basename='rating')
router.register(r'cart', views.CartViewSet, basename='cart')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/orders/create/', views.OrderAPIView.as_view(), name='order-create'),  # Добавить эту строку
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)