import re
from django.forms import ValidationError


def agent_name_validator(name):
    if not re.search(r"^[a-zA-Z0-9- ]{1,100}$", name):
        raise ValidationError(
            "Agent Name must be alphanumeric and less than 100 characters"
        )
    return name