from abc import ABCMeta
from typing import Tuple

import sidekick as sk


class ModelMeta(ABCMeta):
    """
    Metaclass for model classes.
    """

    DATA_ALIASES: dict
    _meta: "Meta"

    def __init__(cls, name, bases, ns):
        meta = ns.pop("Meta", None)
        super().__init__(name, bases, ns)
        meta_kwargs = meta_arguments(bases, meta)
        cls._meta = Meta(cls, **meta_kwargs)


class Meta:
    """
    Meta information about model.

    Attributes:
        params:
            Information about parameters, subclass of :cls:`ParamsInfo`
    """

    cls: ModelMeta
    params: "ParamsInfo"

    def __init__(self, cls, **kwargs):
        self.cls = cls
        self.explicit_kwargs = kwargs
        self.params = ParamsInfo(self)
        for k, v in kwargs.items():
            if "__" in k:
                ns, _, tail = k.partition("__")
                setattr(getattr(self, ns), tail, v)
            else:
                setattr(self, k, v)

    @sk.lazy
    def component_index(self):
        cls = self.cls
        if hasattr(cls, "DATA_COLUMNS"):
            items = zip(cls.DATA_COLUMNS, cls.DATA_COLUMNS)
        else:
            items = cls.DATA_ALIASES.items()

        idx_map = {}
        for i, (k, v) in enumerate(items):
            idx_map[k] = idx_map[v] = i
        return idx_map

    @sk.lazy
    def data_columns(self):
        cls = self.cls
        try:
            return tuple(getattr(cls, "DATA_COLUMNS"))
        except AttributeError:
            return tuple(cls.DATA_ALIASES.values())

    @sk.lazy
    def params__primary(self) -> Tuple[str]:
        return frozenset(k for k, v in self._params() if not v.is_derived)

    @sk.lazy
    def params__alternative(self):
        return frozenset(k for k, v in self._params() if v.is_derived)

    @sk.lazy
    def params__all(self):
        return self.params__primary | self.params__alternative

    def _params(self):
        cls = self.cls
        for k in dir(cls):
            v = getattr(cls, k, None)
            if hasattr(v, "__get__") and getattr(v, "is_param", False):
                yield k, v


class SubNamespaceView:
    """
    View a sub-set of the target object namespace.
    """

    __slots__ = ("_obj", "_prefix")

    def __init__(self, obj, prefix):
        cls = type(self)
        cls._obj.__set__(self, obj)
        cls._prefix.__set__(self, prefix)

    def __setattr__(self, attr, value):
        try:
            setattr(self._obj, self._prefix + attr, value)
        except AttributeError:
            raise AttributeError(attr)

    def __getattr__(self, attr):
        try:
            return getattr(self._obj, self._prefix + attr)
        except AttributeError:
            raise AttributeError(attr)


class ParamsInfo(SubNamespaceView):
    """
    Object that holds information about parameters.
    """

    __slots__ = ()

    def __init__(self, obj):
        super().__init__(obj, "params__")

    def is_static(self, param: str, model: "Model"):
        return True


def meta_arguments(bases, meta_declaration):
    """
    Extract keyword arguments to pass to a Meta declaration.
    """

    kwargs = {}
    for base in reversed(bases):
        if isinstance(base, ModelMeta):
            meta: Meta = base._meta
            kwargs.update(meta.explicit_kwargs)
    if meta_declaration is not None:
        ns = vars(meta_declaration)
        kwargs.update({k: v for k, v in ns if not k.startswith("_")})
    return kwargs
