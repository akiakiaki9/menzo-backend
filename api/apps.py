from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
    
    def ready(self):
        import os
        # Проверяем, что это основной процесс, а не авто-перезагрузчик
        if os.environ.get('RUN_MAIN', None) == 'true':
            return
        
        # Автоматическое создание суперпользователя
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        try:
            if not User.objects.filter(username='superadmin').exists():
                User.objects.create_superuser(
                    username='superadmin',
                    email='tillayevakbarshoh@gmail.com',
                    password='Admin123456'
                )
                print("✅ Superuser created automatically!")
            else:
                print("ℹ️ Superuser already exists")
        except Exception as e:
            print(f"⚠️ Error creating superuser: {e}")