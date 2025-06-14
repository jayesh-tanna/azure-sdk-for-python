# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

from datetime import datetime, timedelta
from typing import Any, cast, Dict, Optional, Union

from ._generated._utils.serialization import Serializer

_ERROR_TOO_MANY_FILE_PERMISSIONS = 'file_permission and file_permission_key should not be set at the same time'
_FILE_PERMISSION_TOO_LONG = 'Size of file_permission is too large. file_permission should be <=8KB, else' \
                            'please use file_permission_key'


def _get_file_permission(file_permission, file_permission_key, default_permission):
    # if file_permission and file_permission_key are both empty, then use the default_permission
    # value as file permission, file_permission size should be <= 8KB, else file permission_key should be used
    if file_permission and len(str(file_permission).encode('utf-8')) > 8 * 1024:
        raise ValueError(_FILE_PERMISSION_TOO_LONG)

    if not file_permission:
        if not file_permission_key:
            return default_permission
        return None

    if not file_permission_key:
        return file_permission

    raise ValueError(_ERROR_TOO_MANY_FILE_PERMISSIONS)


def _parse_datetime_from_str(string_datetime):
    if not string_datetime:
        return None
    dt, _, us = string_datetime.partition(".")
    dt = datetime.strptime(dt, "%Y-%m-%dT%H:%M:%S")
    us = int(us[:-2])  # microseconds
    datetime_obj = dt + timedelta(microseconds=us)
    return datetime_obj


def _datetime_to_str(datetime_obj):
    if not datetime_obj:
        return None
    if isinstance(datetime_obj, str):
        return datetime_obj
    return Serializer.serialize_iso(datetime_obj)[:-1].ljust(27, "0") + "Z"


def _parse_snapshot(
    snapshot: Optional[Union[str, Dict[str, Any]]] = None,
    path_snapshot: Optional[str] = None
) -> Optional[str]:
    if hasattr(snapshot, 'snapshot'):
        return snapshot.snapshot  # type: ignore
    if isinstance(snapshot, Dict):
        return cast(str, snapshot['snapshot'])
    return snapshot or path_snapshot
