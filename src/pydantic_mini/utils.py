import typing
import logging
import inspect
from dataclasses import MISSING

logger = logging.getLogger(__name__)


def get_function_call_args(
    func, params: typing.Union[typing.Dict[str, typing.Any], object]
) -> typing.Dict[str, typing.Any]:
    """
    Extracts the arguments for a function call from the provided parameters.

    Args:
        func: The function for which arguments are to be extracted.
        params: A dictionary of parameters containing
                the necessary arguments for the function.

    Returns:
        A dictionary where the keys are the function argument names
        and the values are the corresponding argument values.
    """
    params_dict = {}
    try:
        sig = inspect.signature(func)
        for param in sig.parameters.values():
            if param.name != "self":
                value = (
                    params.get(param.name, param.default)
                    if isinstance(params, dict)
                    else getattr(params, param.name, param.default)
                )
                if value is not MISSING and value is not inspect.Parameter.empty:
                    params_dict[param.name] = value
                else:
                    params_dict[param.name] = None
    except (ValueError, KeyError) as e:
        logger.warning(f"Parsing {func} for call parameters failed {str(e)}")

    for key in ["args", "kwargs"]:
        if key in params_dict and params_dict[key] is None:
            params_dict.pop(key, None)
    return params_dict


def init_class(
    klass: typing.Type, params: typing.Union[typing.Dict[str, typing.Any], object]
):
    kwargs = get_function_call_args(klass.__init__, params)
    excluded_kwargs = {key: params[key] for key in params if key not in kwargs}
    instance = klass(**kwargs)
    if excluded_kwargs:
        instance.__dict__.update(excluded_kwargs)
    return instance
