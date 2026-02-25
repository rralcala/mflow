from flask_admin.contrib.sqla import ModelView

class RecurrentModelView(ModelView):
    column_display_pk = True
    form_columns = ('identifier', 'parent_asset_id', 'country', 'amount', 'currency', 'recurrence', 'start', 'end', 'flow_class', 'rate')
