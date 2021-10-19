import unicodedata

def clean_str(string=str()):
    """ custom string cleaner, returns normalized unicode with spaces trimmed

        Args:
            string(str)

        Returns:
            string(str): normalized unicode string with spaces trimmed
    """

    # u = unicodedata.normalize('NFC', str(string.replace('\n', '').strip()))
    u = unicodedata.normalize('NFC', str(string.strip()))
    return u