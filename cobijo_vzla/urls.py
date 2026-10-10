from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from apps.core.auth_views import PasswordChangeViewAudited, PasswordResetRequestView, PasswordResetCompleteView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', include('apps.mapa.urls_health')),
    path('', include('apps.publico.urls')),
    path('panel/', include('apps.mapa.urls')),
    path('api/', include('apps.mapa.urls_api')),
    path('api/emergencias/', include('apps.emergencias.urls')),
    path('api/core/', include('apps.core.urls')),
    path('api/publico/', include('apps.publico.urls_api')),
    path('api/reportes/', include('apps.reportes.urls_api')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path(
        'accounts/password-change/',
        PasswordChangeViewAudited.as_view(
            template_name='registration/password_change_form.html',
            success_url='/accounts/password-change/done/',
        ),
        name='password_change',
    ),
    path(
        'accounts/password-change/done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='registration/password_change_done.html'
        ),
        name='password_change_done',
    ),
    path(
        'accounts/password-reset/',
        PasswordResetRequestView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url='/accounts/password-reset/done/',
        ),
        name='password_reset',
    ),
    path(
        'accounts/password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html'
        ),
        name='password_reset_done',
    ),
    path(
        'accounts/password-reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url='/accounts/password-reset/complete/',
        ),
        name='password_reset_confirm',
    ),
    path(
        'accounts/password-reset/complete/',
        PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html'
        ),
        name='password_reset_complete',
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
