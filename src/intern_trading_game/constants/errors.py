"""Error codes and messages used in the trading system."""


class ErrorCodes:
    """Error codes for API responses."""

    CANCEL_FAILED = "CANCEL_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    INVALID_ORDER_TYPE = "INVALID_ORDER_TYPE"
    MISSING_PRICE = "MISSING_PRICE"
    INVALID_SIDE = "INVALID_SIDE"


class ErrorMessages:
    """Error messages for user responses."""

    ORDER_NOT_FOUND = "Order not found"

    @staticmethod
    def format_cancel_failed(reason: str) -> str:
        """Format cancel failure message."""
        return f"Cancel failed: {reason}"
