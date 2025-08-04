from typing import Callable

from flask_admin.base import BaseView, expose
from flask_login import current_user
from markupsafe import Markup

from data.asset_store import get_asset_store
from lib.config import Config
from lib.user_config import UserStore


class CustomReportView(BaseView):
    def __init__(
        self,
        report: Callable | None = None,
        name: str | None = None,
        category: str | None = None,
        endpoint: str | None = None,
        url: str | None = None,
        static_folder: str | None = None,
        static_url_path: str | None = None,
        menu_class_name: str | None = None,
        menu_icon_type: str | None = None,
        menu_icon_value: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            category=category,
            endpoint=endpoint,
            url=url,
            static_folder=static_folder,
            static_url_path=static_url_path,
            menu_class_name=menu_class_name,
            menu_icon_type=menu_icon_type,
            menu_icon_value=menu_icon_value,
        )
        self.report = report

    @expose("/")
    def index(self):

        assets = get_asset_store(UserStore.get_user_config(current_user.id))
        report_data = {"contents": Markup(self.report(assets))}

        return self.render("custom_report.html", report_data=report_data)

    def is_accessible(self):
        return current_user.is_authenticated
