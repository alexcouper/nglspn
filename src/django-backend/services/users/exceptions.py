class UserNotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("User not found")


class RateLimitError(Exception):
    def __init__(self) -> None:
        super().__init__("Please wait before requesting another verification code")


class EmailAlreadyRegisteredError(Exception):
    def __init__(self) -> None:
        super().__init__("Email already registered")


class KennitalaAlreadyRegisteredError(Exception):
    def __init__(self) -> None:
        super().__init__("Kennitala already registered")


class CodeExhaustedError(Exception):
    def __init__(self) -> None:
        super().__init__("Too many failed attempts. Please request a new code.")
