class ImproperArgumentError(ValueError):
    """
    ImproperArgumentError class.

    An Error class that handles the passing of arguments of improper type
    to class methods.

    Args:
    ----
        ValueError (Error): The ValueError class that ImproperArgumentError
                            extends.

    """

    def __init__(self, message: str):
        """
        ImproperArgumentError constructor.

        Initialize an ImproperArgumentError object by setting the fields
        to the arguments passed to the constructor.

        Args:
        ----
            message (str): The error message displayed to the user, based
                           on the argument input type.

        """
        self.message = message
