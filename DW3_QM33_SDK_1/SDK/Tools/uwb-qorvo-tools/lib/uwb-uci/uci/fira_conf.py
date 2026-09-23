# SPDX-FileCopyrightText: Copyright (c) 2024 Qorvo US, Inc.
# SPDX-License-Identifier: LicenseRef-QORVO-2

__all__ = ["Config", "config_params"]

from .utils import DynIntEnum
from .fira_enums import DeviceState


class Config(DynIntEnum):
    State = 0x0


Config.defs = [
    (Config.State, 1),
]

config_params = {
    # Enum Value,               parameter type, Read Only, description)
    Config.State: (DeviceState, 1, "get Device State."),
}
