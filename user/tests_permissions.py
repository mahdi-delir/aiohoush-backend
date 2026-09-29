from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings

from .backends import PermissionOverrideBackend


@override_settings(
    AUTHENTICATION_BACKENDS=["user.backends.PermissionOverrideBackend"]
)
class PermissionOverrideTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.User = get_user_model()
        content_type = ContentType.objects.get_for_model(cls.User)
        cls.permission = Permission.objects.create(
            content_type=content_type,
            codename="test_review_submission",
            name="Test review submission",
        )
        cls.extra_permission = Permission.objects.create(
            content_type=content_type,
            codename="test_view_report",
            name="Test view report",
        )
        cls.permission_name = "user.test_review_submission"
        cls.extra_name = "user.test_view_report"
        cls.mentor_group = Group.objects.create(name="Test senior mentor")
        cls.teacher_group = Group.objects.create(name="Test teacher")
        cls.mentor_group.permissions.add(cls.permission)
        cls.teacher_group.permissions.add(cls.permission)
        cls.user = cls.User.objects.create_user(mobile="09121111111")
        cls.user.groups.add(cls.mentor_group, cls.teacher_group)

    def fresh(self):
        return self.User.objects.get(pk=self.user.pk)

    def test_groups_and_direct_grants_are_combined(self):
        self.user.user_permissions.add(self.extra_permission)
        user = self.fresh()
        self.assertTrue(user.has_perms([self.permission_name, self.extra_name]))

    def test_denial_beats_both_groups_and_direct_grant(self):
        self.user.user_permissions.add(self.permission, self.extra_permission)
        self.user.denied_permissions.add(self.permission)
        user = self.fresh()
        self.assertFalse(user.has_perm(self.permission_name))
        self.assertFalse(user.has_perms([self.permission_name, self.extra_name]))
        self.assertTrue(user.has_perm(self.extra_name))
        self.assertNotIn(self.permission_name, user.get_user_permissions())
        self.assertNotIn(self.permission_name, user.get_group_permissions())
        self.assertNotIn(self.permission_name, user.get_all_permissions())

    def test_denial_removal_restores_group_grant_on_fresh_user(self):
        self.user.denied_permissions.add(self.permission)
        self.assertFalse(self.fresh().has_perm(self.permission_name))
        self.user.denied_permissions.remove(self.permission)
        self.assertTrue(self.fresh().has_perm(self.permission_name))

    def test_removing_direct_grant_does_not_remove_group_grant(self):
        self.user.user_permissions.add(self.permission)
        self.user.user_permissions.remove(self.permission)
        self.assertTrue(self.fresh().has_perm(self.permission_name))

    def test_denial_does_not_create_any_grant(self):
        self.user.denied_permissions.add(self.extra_permission)
        self.assertFalse(self.fresh().has_perm(self.extra_name))
        self.user.denied_permissions.remove(self.extra_permission)
        self.assertFalse(self.fresh().has_perm(self.extra_name))

    def test_module_permission_uses_effective_permissions(self):
        self.user.denied_permissions.add(self.permission)
        self.assertFalse(self.fresh().has_module_perms("user"))
        self.user.user_permissions.add(self.extra_permission)
        self.assertTrue(self.fresh().has_module_perms("user"))

    def test_superuser_bypasses_denial_but_inactive_user_does_not(self):
        self.user.denied_permissions.add(self.permission)
        self.User.objects.filter(pk=self.user.pk).update(is_superuser=True)
        self.assertTrue(self.fresh().has_perm(self.permission_name))
        self.User.objects.filter(pk=self.user.pk).update(is_active=False)
        user = self.fresh()
        self.assertFalse(user.has_perm(self.permission_name))
        self.assertEqual(user.get_all_permissions(), set())

    def test_anonymous_and_object_permissions_are_not_granted(self):
        self.assertFalse(AnonymousUser().has_perm(self.permission_name))
        self.assertFalse(self.fresh().has_perm(self.permission_name, obj=self.user))

    def test_backend_with_perm_excludes_denied_user(self):
        backend = PermissionOverrideBackend()
        self.assertIn(self.user, backend.with_perm(self.permission_name))
        self.user.denied_permissions.add(self.permission)
        self.assertNotIn(self.user, backend.with_perm(self.permission_name))
        self.assertNotIn(self.user, backend.with_perm(self.permission))
        self.User.objects.filter(pk=self.user.pk).update(is_superuser=True)
        self.assertIn(self.user, backend.with_perm(self.permission_name))

    def test_repeated_checks_use_instance_cache(self):
        user = self.fresh()
        user.get_all_permissions()
        with self.assertNumQueries(0):
            self.assertTrue(user.has_perm(self.permission_name))
            self.assertTrue(user.has_module_perms("user"))

    async def test_async_denial_and_lists(self):
        await self.user.user_permissions.aadd(self.permission, self.extra_permission)
        await self.user.denied_permissions.aadd(self.permission)
        user = await self.User.objects.aget(pk=self.user.pk)
        self.assertFalse(await user.ahas_perm(self.permission_name))
        self.assertTrue(await user.ahas_perm(self.extra_name))
        self.assertNotIn(self.permission_name, await user.aget_user_permissions())
        self.assertNotIn(self.permission_name, await user.aget_group_permissions())
        self.assertNotIn(self.permission_name, await user.aget_all_permissions())
        self.assertTrue(await user.ahas_module_perms("user"))

    def test_sync_then_async_checks_agree(self):
        self.user.denied_permissions.add(self.permission)
        user = self.fresh()
        self.assertFalse(user.has_perm(self.permission_name))
        self.assertFalse(async_to_sync(user.ahas_perm)(self.permission_name))
