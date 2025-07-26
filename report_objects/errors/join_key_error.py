class JoinKeyError(KeyError):
    """
    JoinKeyError class.

    An Error class that handles the attempting to join two or more dataframes on keys that are
    not present in each dataframe to be joined.

    Args:
    ----
        KeyError (Error): The KeyError class that JoinKeyError extends.

    """

    def __init__(self, message: str):
        """
        JoinKeyError constructor.

        Initialize an JoinKeyError object by setting the fields to the arguments passed to the
        constructor.

        Args:
        ----
            message (str): The error message displayed to the user, based
                           on the argument input type.

        """
        self.message = message
