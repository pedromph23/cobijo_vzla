from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.publico.urls')),
    path('panel/', include('apps.mapa.urls')),
    path('api/', include('apps.mapa.urls_api')),
    path('api/emergencias/', include('apps.emergencias.urls')),
    path('api/core/', include('apps.core.urls')),
    path('api/publico/', include('apps.publico.urls_api')),
    path('api/reportes/', include('apps.reportes.urls_api')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)