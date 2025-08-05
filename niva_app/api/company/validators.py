from rest_framework.exceptions import ValidationError
import re


def location_name_validator(name):
    if not re.search(r"^[a-zA-Z0-9- ]{1,150}$", name):
        raise ValidationError(
            "Location Name must be alphanumeric and less than 150 characters"
        )
    return name