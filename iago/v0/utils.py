import json
import unicodedata


def clean_str(s: str):
    """ custom string cleaner, returns normalized unicode with spaces trimmed

        Args:
            string(str)

        Returns:
            string(str): normalized unicode string with spaces trimmed
    """
    return unicodedata.normalize('NFC', str(s.strip()))


def words_in(s: str):
    """ counts space seperated words in string

    Args:
        s (str): string to count words of

    Returns:
        int: number of words in s split my spaces
    """
    return len(s.split(' '))


def isValidJSON(s: str):
    """ returns false if s is not a valid JSON string, else returns s as a json object

    Args:
        s (str): string to check

    Returns:
        False if s is not a valid JSON string, else returns s as a json object
    """
    try:
        json.loads(s)
        return True
    except ValueError:
        return False
