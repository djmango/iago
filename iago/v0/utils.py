import json
import unicodedata

def clean_str(s: str):
    """ custom string cleaner, returns normalized unicode with spaces trimmed

        Args:
            string(str)

        Returns:
            string(str): normalized unicode string with spaces trimmed
    """

    # u = unicodedata.normalize('NFC', str(string.replace('\n', '').strip()))
    u = unicodedata.normalize('NFC', str(s.strip()))
    return u

def isValidJSON(s: str):
    """ returns false if s is not a valid JSON string, else returns s as a json object

    Args:
        s (str): string to check

    Returns:
        False if s is not a valid JSON string, else returns s as a json object
    """
    try: 
        return True
    except ValueError:
        return False
