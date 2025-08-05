from custard_app.models.phonenumber import PhoneNumber
from custard_app.models.company import Company
from django.core.exceptions import ValidationError
from phonenumber_field.phonenumber import to_python

class CompanyPhoneService:
    """
    Service for managing phone numbers associated with a company.
    """

    def add_phone_number(self, company_id: str, phone_number: str, sid: str, account_sid: str, voice_url: str = None) -> PhoneNumber:
        """
        Add a new phone number to a company.

        Args:
            company_id (str): UUID of the company.
            phone_number (str): Phone number in E.164 format.
            sid (str): Twilio/Plivo SID for the phone number.
            account_sid (str): Twilio/Plivo account SID.
            voice_url (str, optional): URL for voice webhook. Defaults to None.

        Returns:
            PhoneNumber: The created phone number object.

        Raises:
            ValidationError: If the phone number is invalid or already exists.
        """
        # Validate the phone number format
        parsed_phone = to_python(phone_number)
        if not parsed_phone or not parsed_phone.is_valid():
            raise ValidationError("Invalid phone number format. Use E.164 format (e.g., +1234567890).")

        # Check if the phone number already exists
        if PhoneNumber.objects.filter(phone_number=phone_number).exists():
            raise ValidationError("Phone number already exists.")

        # Get the company
        company = Company.objects.get(id=company_id)

        # Create the phone number
        phone = PhoneNumber.objects.create(
            company=company,
            phone_number=phone_number,
            sid=sid,
            account_sid=account_sid,
            voice_url=voice_url,
        )

        return phone

    def update_phone_number(self, phone_number_id: str, **kwargs) -> PhoneNumber:
        """
        Update an existing phone number.

        Args:
            phone_number_id (str): UUID of the phone number to update.
            **kwargs: Fields to update (e.g., `phone_number`, `sid`, `account_sid`, `voice_url`).

        Returns:
            PhoneNumber: The updated phone number object.

        Raises:
            ValidationError: If the phone number is invalid or conflicts with an existing one.
        """
        phone = PhoneNumber.objects.get(id=phone_number_id)

        if "phone_number" in kwargs:
            parsed_phone = to_python(kwargs["phone_number"])
            if not parsed_phone or not parsed_phone.is_valid():
                raise ValidationError("Invalid phone number format. Use E.164 format (e.g., +1234567890).")

            # Check if the new phone number conflicts with an existing one
            if PhoneNumber.objects.filter(phone_number=kwargs["phone_number"]).exclude(id=phone_number_id).exists():
                raise ValidationError("Phone number already exists.")

        for field, value in kwargs.items():
            setattr(phone, field, value)

        phone.save()
        return phone

    def delete_phone_number(self, phone_number_id: str) -> None:
        """
        Delete a phone number.

        Args:
            phone_number_id (str): UUID of the phone number to delete.
        """
        PhoneNumber.objects.filter(id=phone_number_id).delete()

    def get_phone_numbers_by_company(self, company_id: str) -> list[PhoneNumber]:
        """
        Get all phone numbers associated with a company.

        Args:
            company_id (str): UUID of the company.

        Returns:
            list[PhoneNumber]: List of phone number objects.
        """
        return PhoneNumber.objects.filter(company_id=company_id).all()