"""Formularios para gestión de usuarios desde el panel administrativo.

Solo administradores/staff deben tener acceso a estos formularios.
Validan username, email, contraseña y grupo.
"""
import re

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.core.validators import validar_nombre_operativo


User = get_user_model()

PATRON_USERNAME = re.compile(r'^[a-zA-Z0-9_.-]{3,30}$')


class UserCreateForm(forms.ModelForm):
    """Formulario para crear un usuario desde el panel administrativo."""

    password1 = forms.CharField(
        label='Contraseña',
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
            'placeholder': 'Mínimo 8 caracteres',
        }),
        help_text='Mínimo 8 caracteres. No puede ser demasiado común.',
    )
    password2 = forms.CharField(
        label='Confirmar contraseña',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
    )
    grupo = forms.ModelChoiceField(
        label='Grupo',
        queryset=Group.objects.all().order_by('name'),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Define los permisos del usuario dentro de la plataforma.',
    )
    enviar_email = forms.BooleanField(
        label='Enviar correo de bienvenida',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text='El usuario recibirá un correo con sus credenciales e instrucciones.',
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'username',
                'placeholder': 'Ej.: jperez',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'autocomplete': 'email',
                'placeholder': 'correo@dominio.com',
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'given-name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'autocomplete': 'family-name',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'username': 'Nombre de usuario',
            'email': 'Correo electrónico',
            'first_name': 'Nombre',
            'last_name': 'Apellido',
            'is_active': 'Cuenta activa',
        }

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not PATRON_USERNAME.match(username):
            raise ValidationError(
                'El nombre de usuario debe tener entre 3 y 30 caracteres y '
                'solo puede contener letras, números, puntos, guiones y '
                'guiones bajos.'
            )
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Ya existe un usuario con ese nombre.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise ValidationError('El correo electrónico es obligatorio.')
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Ya existe un usuario con ese correo.')
        return email

    def clean_first_name(self):
        nombre = (self.cleaned_data.get('first_name') or '').strip()
        if nombre:
            validar_nombre_operativo(nombre, etiqueta='El nombre')
        return nombre

    def clean_last_name(self):
        apellido = (self.cleaned_data.get('last_name') or '').strip()
        if apellido:
            validar_nombre_operativo(apellido, etiqueta='El apellido')
        return apellido

    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            try:
                validate_password(password)
            except ValidationError as e:
                raise ValidationError(e.messages)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Las contraseñas no coinciden.')
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_active = self.cleaned_data.get('is_active', True)
        if commit:
            user.save()
            grupo = self.cleaned_data.get('grupo')
            if grupo:
                user.groups.set([grupo])
        return user


class UserUpdateForm(forms.ModelForm):
    """Formulario para editar un usuario existente.

    No permite cambiar la contraseña. Para eso se usa el flujo separado.
    """

    grupo = forms.ModelChoiceField(
        label='Grupo',
        queryset=Group.objects.all().order_by('name'),
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text='Define los permisos del usuario dentro de la plataforma.',
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 150}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            grupos = self.instance.groups.all()
            if grupos.exists():
                self.initial['grupo'] = grupos.first().pk

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not PATRON_USERNAME.match(username):
            raise ValidationError(
                'El nombre de usuario debe tener entre 3 y 30 caracteres y '
                'solo puede contener letras, números, puntos, guiones y '
                'guiones bajos.'
            )
        qs = User.objects.filter(username__iexact=username)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ya existe un usuario con ese nombre.')
        return username

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise ValidationError('El correo electrónico es obligatorio.')
        qs = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError('Ya existe un usuario con ese correo.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            grupo = self.cleaned_data.get('grupo')
            if grupo:
                user.groups.set([grupo])
        return user
