import hmac
import hashlib
import base64

WEB_ID = "a3b9d8b1-7cca-4545-bebb-f6dbdbaae57d"
WEB_KEY = "j5gMezmY2HFbt68g"
SECRET = "BZ6RrWZ7scAAXSnRgJJ7ht2YSFJx6tgHeFmmjRBzTwwfathAN5cXCZhg8f8WkBa9"


def get_signature(timestamp):
    fullsec = timestamp + WEB_ID + WEB_KEY
    
    msg = fullsec.encode('utf-8')
    secret = SECRET.encode('utf-8')

    hashed = hmac.new(secret, msg, hashlib.sha256).digest()
    encoded_string = base64.b64encode(hashed)

    return encoded_string.decode('utf-8')
