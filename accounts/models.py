from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.translation import gettext_lazy as _


class CustomUserManager(BaseUserManager):
    def create_user(self, username, full_name, password=None, **extra_fields):
        if not username:
            raise ValueError(_('用户必须提供账号'))
        if not full_name:
            raise ValueError(_('用户必须提供姓名'))
        extra_fields.setdefault('is_active', True)
        user = self.model(username=username, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, full_name, password=None, **extra_fields):
        extra_fields.setdefault('is_teacher', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, full_name, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(_('账号'), max_length=150, unique=True)
    full_name = models.CharField(_('姓名'), max_length=150, unique=False)
    date_joined = models.DateTimeField(_('加入日期'), auto_now_add=True)
    is_active = models.BooleanField(_('是否激活'), default=True)
    is_staff = models.BooleanField(_('是否为管理员'), default=False)
    is_teacher = models.BooleanField(_('是否为教师'), default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'  # 设置登录ID字段为账号
    REQUIRED_FIELDS = ['full_name']  # createsuperuser时需要额外提供的字段

    def __str__(self):
        return self.username
