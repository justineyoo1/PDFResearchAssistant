class ColumnSubsetError(KeyError):
    """
    ColumnSubsetError class.

    An Error class that handles the attempting to subset a dataframe by column(s)
    that are not present.

    Args:
    ----
        KeyError (Error): The KeyError class that ColumnSubsetError extends.

    """

    def __init__(self, message: str):
        """
        ColumnSubsetError constructor.

        Initialize an ColumnSubsetError object by setting the fields
        to the arguments passed to the constructor.

        Args:
        ----
            message (str): The error message displayed to the user, based
                           on the argument input type.

        """
        self.message = message
