class PropertyError(ValueError):
    def __init__(self, key, msg, suggestions=None):
        if suggestions is None:
            suggestions = list()
        self.key = key
        self.message = msg
        self.suggestions = suggestions

    def __str__(self):
        return "{} - {}".format(self.key, self.message)


def _parse(key, fn_type=(lambda x: x), **kwargs):
    try:
        return fn_type(kwargs[key])
    except (ValueError, TypeError) as e:
        raise PropertyError(key, str(e))


def parse_option(key, fn_type=(lambda x: x), default_value=None, errors=None, **kwargs):
    """
    Attempts to parse an option from the given keyword arguments based on the specified key.

    This function looks for the key in the keyword arguments and applies a transformation function (fn_type) to its value.
    If the key is missing and a default value is provided, the default value is used instead. If the key is missing and no
    default value is provided, a PropertyError is recorded. All encountered PropertyErrors are appended to the provided
    'errors' list, if any.

    Parameters:
    - key (str): The key to look for in the keyword arguments.
    - fn_type (callable, optional): A function to apply to the value of the found key. Defaults to a no-op lambda that returns the value unchanged.
    - default_value (any, optional): The default value to use if the key is not found in the keyword arguments. Defaults to None.
    - errors (list, optional): A list to which any encountered PropertyErrors will be appended. If None, a new list is created. Defaults to None.
    - **kwargs: Additional keyword arguments among which the function will look for the specified key.

    Returns:
    - The value associated with 'key' in the keyword arguments after applying 'fn_type', the default value if the key is missing, or raises a KeyError if the key is missing and no default value is provided.

    Raises:
    - KeyError: If the key is not found in the keyword arguments and no default value is provided.
    - PropertyError: If there is a ValueError or TypeError when applying 'fn_type' to the value associated with 'key'.
    """
    errors = [] if errors is None else errors
    try:
        return _parse(key, fn_type=fn_type, **kwargs)
    except KeyError:
        if default_value is None:
            errors.append(PropertyError(key, "The key is missing and no default value has been set"))
    except PropertyError as pe:
        errors.append(pe)
    return fn_type(default_value)


def hash_dict(**m):
    return hash("".join(str(k) + str(m.get(k)) for k in sorted(m.keys())))
