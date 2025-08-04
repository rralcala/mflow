from typing import Any, Dict


class DataSource:
    def __init__(self, source_type, filename, mtime: float, user_id: str):
        self.source_type = source_type
        self.mtime = mtime
        self.name = filename
        self.settings = None
        self.user_id = user_id

    def get_table(self, worksheet: str):
        return self._get_table(self.name, worksheet, self.user_id)

    def get_dict(self, worksheet: str):
        return self._get_dict(self.name, worksheet, self.user_id)

    def get_sheet_settings(self) -> Dict[str, Any]:
        if not self.settings:
            self.settings = self._get_sheet_settings(self.name, self.user_id)
        return self.settings

    def _get_table(self, sheet: str, worksheet: str, user_id: str):
        raise NotImplementedError

    def _get_dict(self, sheet: str, worksheet: str, user_id: str):
        raise NotImplementedError

    def _get_sheet_settings(self, sheet: str, user_id: str) -> Dict[str, Any]:
        raise NotImplementedError
