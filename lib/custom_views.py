from flask import redirect, request, url_for
from flask_admin import AdminIndexView, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user


class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated

    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for("auth.login"))


class AnalyticsView(BaseView):
    @expose("/")
    def index(self):
        prefix = request.headers.get("X-Forwarded-Prefix", "") + "/"
        return self.render("analytics_index.html", prefix=prefix)

    def is_accessible(self):
        return current_user.is_authenticated


class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated
