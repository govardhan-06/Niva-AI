import random
import re
import enum
import os

def create_6_digit_otp():
    """
    Create a 6 digit OTP

    Returns:
        int: A 6 digit OTP
    """
    return random.randint(100000, 999999)


def create_4_digit_otp():
    """
    Create a 4 digit OTP

    Returns:
        int: A 4 digit OTP
    """
    return random.randint(1000, 9999)

def get_phone_number_with_country_code(phone_number):
    """
    Get phone number with country code

    This function adds the country code to the phone number if it is not already present.

    Args:
        phone_number (str): Phone number

    Returns:
        str: Phone number with country code
    """
    return "+" + phone_number if phone_number[0] != "+" else phone_number

def clean_content(content):
    """
    Clean content by removing extra new lines

    This function removes extra new lines from the content.

    Args:
        content (str): Content to clean

    Returns:
        str: Cleaned content
    """
    return re.sub(r"\n+", "\n", content).strip()

class FileType(enum.Enum):
    """
    Enum for file types

    This enum contains file types that can be used to identify the type of file. Modify this enum to add new file types.

    Attributes:
        - UNKNOWN: Unknown file type
        - PDF: PDF file type
        - CSV: CSV file type
        - IMAGE: Image file type
        - DOCX: DOCX file type
    """

    UNKNOWN = "Unknown"
    PDF = "PDF"
    CSV = "CSV"
    IMAGE = "Image"
    DOCX = "DOCX"


class FileTypeInfo:
    """
    Class to get file type information

    This class contains methods to get file type information.

    Methods:
        - get_file_type: Get file type based on file name
    """

    @staticmethod
    def get_file_type(file_name):
        """
        Get file type based on file name

        Args:
            file_name (str): Name of the file

        Returns:
            FileType: File type
        """
        # Determine file type using file extension
        file_extension = file_name.split(".")[-1].lower()

        if file_extension == "pdf":
            return FileType.PDF
        elif file_extension == "csv":
            return FileType.CSV
        elif file_extension in ["jpg", "jpeg", "png", "gif"]:
            return FileType.IMAGE
        elif file_extension == "docx":
            return FileType.DOCX
        else:
            return FileType.UNKNOWN

def clean_content(content):
    """
    Clean content by removing extra new lines

    This function removes extra new lines from the content.

    Args:
        content (str): Content to clean

    Returns:
        str: Cleaned content
    """
    return re.sub(r"\n+", "\n", content).strip()