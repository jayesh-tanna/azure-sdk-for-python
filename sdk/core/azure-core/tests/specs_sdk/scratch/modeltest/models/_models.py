# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# Code generated by Microsoft (R) Python Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is regenerated.
# --------------------------------------------------------------------------
# pylint: disable=useless-super-delegation

from typing import Any, Mapping, TYPE_CHECKING, overload

from .._utils.model_base import Model as _Model, rest_field

if TYPE_CHECKING:
    from .. import models as _models


class ClientNamedPropertyModel(_Model):
    """Model with a property that has a client name.

    :ivar prop_client_name: Required.
    :vartype prop_client_name: str
    """

    prop_client_name: str = rest_field(
        name="propClientName", visibility=["read", "create", "update", "delete", "query"]
    )
    """Required."""

    @overload
    def __init__(
        self,
        *,
        prop_client_name: str,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class FlattenModel(_Model):
    """Model with one level of flattening.

    :ivar name: Required.
    :vartype name: str
    :ivar properties: Required.
    :vartype properties: ~modeltest.models.PropertiesModel
    """

    name: str = rest_field(visibility=["read", "create", "update", "delete", "query"])
    """Required."""
    properties: "_models.PropertiesModel" = rest_field(visibility=["read", "create", "update", "delete", "query"])
    """Required."""

    __flattened_items = ["description", "age"]

    @overload
    def __init__(
        self,
        *,
        name: str,
        properties: "_models.PropertiesModel",
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        _flattened_input = {k: kwargs.pop(k) for k in kwargs.keys() & self.__flattened_items}
        super().__init__(*args, **kwargs)
        for k, v in _flattened_input.items():
            setattr(self, k, v)

    def __getattr__(self, name: str) -> Any:
        if name in self.__flattened_items:
            if self.properties is None:
                return None
            return getattr(self.properties, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def __setattr__(self, key: str, value: Any) -> None:
        if key in self.__flattened_items:
            if self.properties is None:
                self.properties = self._attr_to_rest_field["properties"]._class_type()
            setattr(self.properties, key, value)
        else:
            super().__setattr__(key, value)


class PropertiesModel(_Model):
    """Properties model.

    :ivar description: Required.
    :vartype description: str
    :ivar age: Required.
    :vartype age: int
    """

    description: str = rest_field(visibility=["read", "create", "update", "delete", "query"])
    """Required."""
    age: int = rest_field(visibility=["read", "create", "update", "delete", "query"])
    """Required."""

    @overload
    def __init__(
        self,
        *,
        description: str,
        age: int,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class ReadonlyModel(_Model):
    """Model with a readonly property.

    :ivar id: Required.
    :vartype id: int
    """

    id: int = rest_field(visibility=["read"])
    """Required."""


class Scratch(_Model):
    """A scratch model for testing purposes.

    :ivar prop: A string property. Required.
    :vartype prop: str
    """

    prop: str = rest_field(visibility=["read", "create", "update", "delete", "query"])
    """A string property. Required."""

    @overload
    def __init__(
        self,
        *,
        prop: str,
    ) -> None: ...

    @overload
    def __init__(self, mapping: Mapping[str, Any]) -> None:
        """
        :param mapping: raw JSON to initialize the model.
        :type mapping: Mapping[str, Any]
        """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
