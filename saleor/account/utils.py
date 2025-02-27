import os
import random

from django.conf import settings
from django.contrib.admin.views.decorators import (
    staff_member_required as _staff_member_required,
)
from django.core.files import File

from ..checkout import AddressType
from ..core.utils import create_thumbnails
from ..extensions.manager import get_extensions_manager
from .models import User

AVATARS_PATH = os.path.join(
    settings.PROJECT_ROOT, "saleor", "static", "images", "avatars"
)


def store_user_address(user, address, address_type):
    """Add address to user address book and set as default one."""
    address = get_extensions_manager().change_user_address(address, address_type, user)
    address_data = address.as_data()

    address = user.addresses.filter(**address_data).first()
    if address is None:
        address = user.addresses.create(**address_data)

    if address_type == AddressType.BILLING:
        if not user.default_billing_address:
            set_user_default_billing_address(user, address)
    elif address_type == AddressType.SHIPPING:
        if not user.default_shipping_address:
            set_user_default_shipping_address(user, address)


def set_user_default_billing_address(user, address):
    user.default_billing_address = address
    user.save(update_fields=["default_billing_address"])


def set_user_default_shipping_address(user, address):
    user.default_shipping_address = address
    user.save(update_fields=["default_shipping_address"])


def change_user_default_address(user, address, address_type):
    address = get_extensions_manager().change_user_address(address, address_type, user)
    if address_type == AddressType.BILLING:
        if user.default_billing_address:
            user.addresses.add(user.default_billing_address)
        set_user_default_billing_address(user, address)
    elif address_type == AddressType.SHIPPING:
        if user.default_shipping_address:
            user.addresses.add(user.default_shipping_address)
        set_user_default_shipping_address(user, address)


def get_user_first_name(user):
    """Return a user's first name from their default belling address.

    Return nothing if none where found.
    """
    if user.first_name:
        return user.first_name
    if user.default_billing_address:
        return user.default_billing_address.first_name
    return None


def get_user_last_name(user):
    """Return a user's last name from their default belling address.

    Return nothing if none where found.
    """
    if user.last_name:
        return user.last_name
    if user.default_billing_address:
        return user.default_billing_address.last_name
    return None


def create_superuser(credentials):

    user, created = User.objects.get_or_create(
        email=credentials["email"],
        defaults={"is_active": True, "is_staff": True, "is_superuser": True},
    )
    if created:
        user.avatar = get_random_avatar()
        user.set_password(credentials["password"])
        user.save()
        create_thumbnails(
            pk=user.pk, model=User, size_set="user_avatars", image_attr="avatar"
        )
        msg = "Superuser - %(email)s/%(password)s" % credentials
    else:
        msg = "Superuser already exists - %(email)s" % credentials
    return msg


def get_random_avatar():
    """Return random avatar picked from a pool of static avatars."""
    avatar_name = random.choice(os.listdir(AVATARS_PATH))
    avatar_path = os.path.join(AVATARS_PATH, avatar_name)
    return File(open(avatar_path, "rb"), name=avatar_name)


def remove_staff_member(staff):
    """Remove staff member account only if it has no orders placed.

    Otherwise, switches is_staff status to False.
    """
    if staff.orders.exists():
        staff.is_staff = False
        staff.user_permissions.clear()
        staff.save()
    else:
        staff.delete()


def staff_member_required(f):
    return _staff_member_required(f, login_url="account:login")
