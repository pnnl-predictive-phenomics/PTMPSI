# vim: set expandtab shiftwidth=4 softtabstop=4:

# === UCSF ChimeraX Copyright ===
# Copyright 2016 Regents of the University of California.
# All rights reserved.  This software provided pursuant to a
# license agreement containing restrictions on its disclosure,
# duplication and use.  For details see:
# http://www.rbvi.ucsf.edu/chimerax/docs/licensing.html
# This notice must be embedded in or attached to all copies,
# including partial copies, of the software or any revisions
# or derivations thereof.
# === UCSF ChimeraX Copyright ===

defaults = {
    "library": "CysPTM",
}

from  chimerax.core.settings import Settings
from copy import deepcopy

class _RotamersSettings(Settings):
	EXPLICIT_SAVE = deepcopy(defaults)

_settings = None
def get_settings(session):
    global _settings
    if _settings is None:
        _settings = _RotamersSettings(session, "PTM")
    return _settings
