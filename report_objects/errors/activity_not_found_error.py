class ActivityNotFoundError(BaseException):
    """
    ActivityNotFoundError class.

    An Error class that handles the presence of Activities not defined in the Activities
    Table.

    Args:
    ----
        BaseException (Exception): The BaseException class that ActivityNotFoundError
                                   extends.

    """

    def __init__(self, message: str):
        """
        ActivityNotFoundError constructor.

        Initialize an ActivityNotFoundError object by setting the fields
        to the arguments passed to the constructor.

        Args:
        ----
            message (str): The error message displayed to the user, based
                           on the argument input type.

        """
        self.message = message
