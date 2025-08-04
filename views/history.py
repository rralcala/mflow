from typing import Any, List

from flask_login import current_user

from models.history import History


def nw_history(assets) -> List[List[Any]]:
    history = History.query.filter_by(user_id=current_user.id).all()
    items = len(history)
    report = []
    if items > 13:
        items = 13
    if items > 2:
        result = [element.to_dict() for element in history]
        pval = result[len(result) - items]["value"]
        result = result[-(items - 1) :]

        for element in result:
            change = element["value"] - pval - element["fixed"]
            report.append(
                [element["date"][:7], element["value"], element["fixed"], change]
            )
            pval = element["value"]

    return report
