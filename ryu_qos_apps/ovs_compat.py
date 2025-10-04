"""Compatibility helpers for python-ovs API changes.

This module provides a tiny shim that restores the legacy
``ovs.db.idl._uuid_to_row`` helper that older versions of Ryu expect.
Recent releases of python-ovs removed this function, which causes
``ryu.lib.ovs.vsctl`` to fail when it attempts to translate UUID values
returned from OVSDB.  When that happens the QoS REST application raises
``ValueError('ovsdb addr is not available.')`` while processing
``/v1.0/conf/switches/<dpid>/ovsdb_addr`` requests.

The helper below recreates the missing function by keeping a weak
registry of ``ovs.db.idl.Idl`` instances.  The recreated function looks
up referenced rows in the registered IDL objects, mimicking the
behaviour that older python-ovs releases exposed.  The shim is applied
only when the new python-ovs package is detected (i.e. when
``_uuid_to_row`` no longer exists), so environments that still ship the
legacy helper remain unaffected.
"""

from __future__ import annotations

import logging
import weakref
from typing import Callable, Iterable


LOG = logging.getLogger(__name__)


_IDL_WEAKREFS: "weakref.WeakSet[object]" = weakref.WeakSet()
_IDL_STRONGREFS: list[object] = []
_PATCHED = False


def _register_idl_instance(idl_obj: object) -> None:
    """Store the IDL instance in the weak registry."""

    try:
        _IDL_WEAKREFS.add(idl_obj)
    except TypeError:
        # Some IDL implementations might not be weak-referenceable.
        _IDL_STRONGREFS.append(idl_obj)


def _iter_idl_instances() -> Iterable[object]:
    for idl in list(_IDL_WEAKREFS):
        yield idl
    for idl in list(_IDL_STRONGREFS):
        yield idl


def _build_uuid_to_row(ovs_idl_module) -> Callable[[object, object], object]:
    Row = getattr(ovs_idl_module, "Row", None)

    def _uuid_to_row(value: object, base: object) -> object:
        # Preserve legacy behaviour for already-resolved rows.
        if Row is not None and isinstance(value, Row):
            return value

        ref_table = getattr(base, "ref_table", None)
        if not ref_table:
            return value

        table_name = getattr(ref_table, "name", None)
        if not table_name:
            return value

        for idl in _iter_idl_instances():
            tables = getattr(idl, "tables", None)
            if not tables:
                continue
            table = tables.get(table_name) if hasattr(tables, "get") else None
            if table is None:
                continue
            rows = getattr(table, "rows", None)
            if not rows:
                continue
            row = rows.get(value) if hasattr(rows, "get") else None
            if row is not None:
                return row
        return None

    return _uuid_to_row


def ensure_ovs_idl_compatibility() -> None:
    """Patch python-ovs so older Ryu helpers continue to work."""

    global _PATCHED

    if _PATCHED:
        return

    try:
        from ovs.db import idl as ovs_idl
    except ImportError:
        LOG.debug("python-ovs is not installed; skipping compatibility shim")
        _PATCHED = True
        return

    if hasattr(ovs_idl, "_uuid_to_row"):
        _PATCHED = True
        return

    if getattr(ovs_idl.Idl, "__qos_compat_wrapped__", False):
        _PATCHED = True
        return

    original_init = ovs_idl.Idl.__init__

    def wrapped_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        _register_idl_instance(self)

    ovs_idl.Idl.__init__ = wrapped_init
    setattr(ovs_idl.Idl, "__qos_compat_wrapped__", True)
    ovs_idl._uuid_to_row = _build_uuid_to_row(ovs_idl)

    LOG.info("Installed python-ovs compatibility shim for _uuid_to_row")
    _PATCHED = True

