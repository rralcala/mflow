from flask import redirect, url_for
from flask_admin import AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("login"))


class AnalyticsView(BaseView):
    @expose("/")
    def index(self):
        return self.render("analytics_index.html")

    def is_accessible(self):
        return current_user.is_authenticated


class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated


class RecurrentModelView(SecureModelView):
    column_display_pk = True
    form_columns = (
        "identifier",
        "parent_asset_id",
        "country",
        "amount",
        "currency",
        "recurrence",
        "start",
        "end",
        "flow_class",
        "rate",
    )
