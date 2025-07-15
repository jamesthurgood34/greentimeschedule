"""Custom exceptions for the Green Time Schedule API."""

class GreenScheduleException(Exception):
    """Base exception class for the Green Time Schedule API."""
    pass


class CarbonAPIUnavailableError(GreenScheduleException):
    """Raised when the Carbon Intensity API is unavailable."""
    def __init__(self, message="Carbon Intensity API is currently unavailable"):
        self.message = message
        super().__init__(self.message)


class CarbonAPIResponseError(GreenScheduleException):
    """Raised when there is an error in the Carbon Intensity API response."""
    def __init__(self, message="Error in Carbon Intensity API response", status_code=None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class InvalidScheduleRequestError(GreenScheduleException):
    """Raised when the job scheduling request is invalid."""
    def __init__(self, message="Invalid job scheduling request"):
        self.message = message
        super().__init__(self.message)


class NoViableTimeSlotError(GreenScheduleException):
    """Raised when no viable time slot can be found for the job."""
    def __init__(self, message="No viable time slot found for the job"):
        self.message = message
        super().__init__(self.message)


class CacheError(GreenScheduleException):
    """Raised when there is an error with the cache."""
    def __init__(self, message="Error with the cache"):
        self.message = message
        super().__init__(self.message)