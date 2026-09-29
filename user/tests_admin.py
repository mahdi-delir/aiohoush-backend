from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase, override_settings
from django.urls import reverse

from .admin_forms import UserAdminCreationForm

User = get_user_model()


class UserAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.root = User.objects.create_user('09120000001', 'Test-only-password!7', is_staff=True, is_superuser=True)
        cls.student = User.objects.create_user('09120000002')
        cls.staff = User.objects.create_user('09120000003', is_staff=True)

    def setUp(self):
        self.client.force_login(self.root)

    def test_admin_pages_render(self):
        for url in (reverse('admin:user_user_changelist'), reverse('admin:user_user_add'), reverse('admin:user_user_change', args=[self.student.pk]), reverse('admin:auth_user_password_change', args=[self.student.pk])):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_staff_cannot_access_admin(self):
        self.client.force_login(self.staff)
        for name in ('admin:index', 'admin:user_user_changelist', 'admin:user_user_add'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_inactive_superuser_cannot_access(self):
        self.root.is_active = False
        self.root.save(update_fields=['is_active'])
        self.assertEqual(self.client.get(reverse('admin:user_user_changelist')).status_code, 302)

    def test_normalized_mobile_and_unusable_password(self):
        response = self.client.post(reverse('admin:user_user_add'), {'mobile': '+۹۸۹۱۲۳۴۵۶۷۸۹', 'usable_password': 'false', '_save': '1'})
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(mobile='09123456789')
        self.assertFalse(user.has_usable_password())
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)

    def test_duplicate_normalized_mobile(self):
        form = UserAdminCreationForm(data={'mobile': '+989120000002', 'usable_password': 'false'})
        self.assertFalse(form.is_valid())
        self.assertIn('mobile', form.errors)

    def test_invalid_mobile(self):
        form = UserAdminCreationForm(data={'mobile': '123', 'usable_password': 'false'})
        self.assertFalse(form.is_valid())
        self.assertIn('mobile', form.errors)

    def test_password_hashing(self):
        password = 'Test-only-new-password!8'
        form = UserAdminCreationForm(data={'mobile': '09123456789', 'usable_password': 'true', 'password1': password, 'password2': password})
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertNotEqual(user.password, password)
        self.assertTrue(user.check_password(password))

    @override_settings(AUTH_PASSWORD_VALIDATORS=[{'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'}])
    def test_password_validation(self):
        for first, second in [('short', 'short'), ('Strong-test-password!1', 'Different-password!2'), ('', '')]:
            with self.subTest(first=first):
                form = UserAdminCreationForm(data={'mobile': '09123456789', 'usable_password': 'true', 'password1': first, 'password2': second})
                self.assertFalse(form.is_valid())

    def test_edit_permissions_and_preserve_password(self):
        group = Group.objects.create(name='Test mentor')
        permission = Permission.objects.get(content_type__app_label='user', content_type__model='user', codename='change_user')
        old_password = self.student.password
        response = self.client.post(reverse('admin:user_user_change', args=[self.student.pk]), {
            'mobile': self.student.mobile, 'first_name': 'تست', 'is_active': 'on',
            'groups': [group.pk], 'user_permissions': [permission.pk],
            'denied_permissions': [permission.pk], '_save': '1',
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(pk=self.student.pk)
        self.assertEqual(user.password, old_password)
        self.assertEqual(user.first_name, 'تست')
        self.assertIsNone(user.email)
        self.assertIsNone(user.national_id)
        self.assertTrue(user.groups.filter(pk=group.pk).exists())
        self.assertTrue(user.user_permissions.filter(pk=permission.pk).exists())
        self.assertTrue(user.denied_permissions.filter(pk=permission.pk).exists())
        self.assertFalse(user.has_perm('user.change_user'))
