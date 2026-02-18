class RateLimitError(Exception):
    def __init__(self) -> None:
        super().__init__("Please wait before requesting another verification code")
