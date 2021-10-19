"""
permission utils and classes for iago views
"""

from django.contrib.auth.models import Group
from rest_framework import permissions

## auth checks

# https://stackoverflow.com/questions/19372553/django-rest-framework-check-user-is-in-group
# https://www.django-rest-framework.org/api-guide/permissions/#custom-permissions
# https://www.django-rest-framework.org/tutorial/4-authentication-and-permissions/
def is_in_group(user, group_name):
    """
    Takes a user and a group name, and returns `True` if the user is in that group.
    """
    try:
        return Group.objects.get(name=group_name).user_set.filter(id=user.id).exists()
    except Group.DoesNotExist:
        return None

class HasGroupPermission(permissions.BasePermission):
    """
    Check if user is in any of the allowed groups
    """

    def has_permission(self, request, view):
        # Get a mapping of methods -> required group.
        allowed_groups_mapping = getattr(view, "allowed_groups", {})

        # Determine the required groups for this particular request method.
        allowed_groups = allowed_groups_mapping.get(request.method, [])

        # Return True if the user has any of the required groups or is staff.
        return any([is_in_group(request.user, group_name) if group_name != "__all__" else True for group_name in allowed_groups]) or (request.user and request.user.is_superuser)
