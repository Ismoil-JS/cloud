from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views as core_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.HomeView.as_view(), name='home'),
    path('projects/', include('core.urls')),
    path('register/', core_views.RegisterView.as_view(), name='register'),
    path('health/', core_views.health_check, name='health-check'),
    path('', include('django.contrib.auth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
