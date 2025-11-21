class MosMetroError(Exception):
    """Base exception for mosmetro."""
    pass

class NetworkError(MosMetroError):
    """General network error."""
    pass

class NetworkTimeoutError(NetworkError):
    """Network timeout."""
    pass

class AuthError(MosMetroError):
    """Authentication failed."""
    pass

class CaptchaRequiredError(AuthError):
    """Captcha is required."""
    pass

class DeviceNotRegisteredError(AuthError):
    """Device is not registered."""
    pass
