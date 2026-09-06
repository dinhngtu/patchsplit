from __future__ import annotations

import re
from collections.abc import Iterable

from ..categories import Category, MatchStrength
from ..model import ChangeUnit, Evidence
from .base import ChangeFilter, evidence


class ZsBrandingFilter(ChangeFilter):
    """Classify ZS product identity and release metadata."""

    name = "zs-branding"
    _version_path = re.compile(r"^C/7zVersion(?:Tr)?\.(?:h|rc)$")
    _identity_path = re.compile(r"^(?:CPP/7zip/UI/|C/Util/7zip(?:Install|Uninstall)/)")
    _identity = re.compile(
        r"7-Zip(?:-Zstandard|[^\r\n\"]*\bZS\b)|"
        r"SevenZipZS|k_7zip_GUID_Data2_ZS|23170F69-20BB|"
        r"MY_(?:AUTHOR_NAME|COPYRIGHT(?:_DATE)?|VERSION_(?:NUMBERS|COPYRIGHT_DATE))|"
        r'VALUE\s+"(?:CompanyName|ProductName)"',
        re.IGNORECASE,
    )

    def classify(self, change: ChangeUnit) -> Iterable[Evidence]:
        if self._version_path.search(change.path):
            yield evidence(
                self,
                Category.ZS_BRANDING,
                MatchStrength.EXACT,
                "7-Zip version metadata path",
            )
        elif self._identity_path.search(change.path) and self._identity.search(
            change.searchable_text
        ):
            yield evidence(
                self,
                Category.ZS_BRANDING,
                MatchStrength.STRONG,
                "ZS product identity",
            )
