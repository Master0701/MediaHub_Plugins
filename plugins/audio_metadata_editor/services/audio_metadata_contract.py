from __future__ import annotations

from mediahub_metadata_core import (
    AUDIO_EXTENSIONS,
)
from mediahub_metadata_core import (
    SAFE_WRITE_POLICY as CORE_SAFE_WRITE_POLICY,
)

CONTRACT_ID = "mediahub.audio_metadata.v1"
CONTRACT_VERSION = 1

OPERATIONS = (
    "status",
    "inspect",
    "identify",
    "compare",
    "plan_write",
    "apply_write",
)

SUPPORTED_AUDIO_EXTENSIONS = AUDIO_EXTENSIONS

# Die zentrale MediaHub-Sicherheitsrichtlinie wird bewusst
# ?ber den Audio-Metadata-Contract bereitgestellt. Dadurch
# verwenden alle Audio-/H?rbuch-Schreibpfade dieselben Regeln.
SAFE_WRITE_POLICY = CORE_SAFE_WRITE_POLICY
