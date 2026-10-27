class DuplicateEmailError(ValueError):
    """A user account already exists for the submitted email."""


class InvalidCredentialsError(ValueError):
    """The submitted credentials do not authenticate an active account."""


class SlotUnavailableError(ValueError):
    """The requested slot is missing, inactive, in the past, or occupied."""


class InvalidAppointmentTransitionError(ValueError):
    """The requested appointment status transition is not allowed."""
