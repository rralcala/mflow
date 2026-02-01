from typing import Any, Dict


class DataSource:
    def __init__(self, source_type, filename, mtime: float):
        self.source_type = source_type
        self.mtime = mtime
        self.name = filename
        self.settings = None

    def get_table(self, worksheet: str):
        return self._get_table(self.name, worksheet)

    def get_dict(self, worksheet: str):
        return self._get_dict(self.name, worksheet)

    def get_sheet_settings(self) -> Dict[str, Any]:
        if not self.settings:
            self.settings = self._get_sheet_settings(self.name)
        return self.settings

    def _get_table(self, sheet: str, worksheet: str):
        raise NotImplementedError

    def _get_dict(self, sheet: str, worksheet: str):
        raise NotImplementedError

    def _get_sheet_settings(self, sheet: str) -> Dict[str, Any]:
        raise NotImplementedError
