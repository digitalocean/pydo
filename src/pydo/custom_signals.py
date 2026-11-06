"""Deprecated ``agent_id`` alias for Signals path parameters."""

import inspect
import warnings

_ID_PARAMS = ("environment_id", "agent_id")
_ALIAS_WARNING = "agent_id is deprecated; use environment_id"


def _id_parameter(func):
    names = [name for name in inspect.signature(func).parameters if name in _ID_PARAMS]
    if len(names) != 1:
        raise TypeError(
            "%s must accept exactly one of environment_id or agent_id"
            % func.__qualname__
        )
    return names[0]


def _positional_index(func, id_name):
    index = 0
    for name, param in inspect.signature(func).parameters.items():
        if name == "self":
            continue
        if param.kind not in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            return -1
        if name == id_name:
            return index
        index += 1
    return -1


def _prepare_environment_call(func, args, kwargs):
    id_name = _id_parameter(func)
    kwargs = dict(kwargs)
    has_agent = "agent_id" in kwargs
    has_environment = "environment_id" in kwargs
    agent_id = kwargs.pop("agent_id", None)
    environment_id = kwargs.pop("environment_id", None)
    pos_index = _positional_index(func, id_name)
    has_positional = pos_index >= 0 and len(args) > pos_index
    supplied = []
    if has_positional:
        supplied.append(args[pos_index])
    if has_environment:
        supplied.append(environment_id)
    if has_agent:
        supplied.append(agent_id)
    if any(value != supplied[0] for value in supplied[1:]):
        raise ValueError("agent_id and environment_id must be equal when both are set")
    if not has_positional and supplied:
        kwargs[id_name] = supplied[0]
    return args, kwargs, has_agent


def with_agent_id_alias(func):
    """Accept ``agent_id=`` as a deprecated alias of the generated id parameter.

    The generated parameter may be named ``environment_id`` (current spec) or
    ``agent_id`` (clients generated before the rename). ``agent_id=`` is
    forwarded under whichever of those names ``func`` accepts. Passing both
    with different values raises ``ValueError``.
    """

    def _apply(args, kwargs):
        args, kwargs, used_alias = _prepare_environment_call(func, args, kwargs)
        if used_alias:
            warnings.warn(_ALIAS_WARNING, DeprecationWarning, stacklevel=3)
        return args, kwargs

    if inspect.iscoroutinefunction(func):

        async def wrapper(self, *args, **kwargs):
            args, kwargs = _apply(args, kwargs)
            return await func(self, *args, **kwargs)

    else:

        def wrapper(self, *args, **kwargs):
            args, kwargs = _apply(args, kwargs)
            return func(self, *args, **kwargs)

    wrapper.__name__ = func.__name__
    wrapper.__qualname__ = func.__qualname__
    wrapper.__doc__ = func.__doc__
    return wrapper
