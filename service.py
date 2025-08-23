from flask import Flask, make_response
from io import BytesIO

from matplotlib.figure import Figure
from reports.list_assets import list_assets as r_list_assets, check_history as r_check_history
from reports.cash_flow import cash_flow as r_cash_flow

app = Flask(__name__)


@app.route("/list-assets")
def list_assets():
    return r_list_assets(print_pos=True, print_neg=True)


@app.route("/cash-flow")
def cash_flow():
    x, y, t = r_cash_flow()
    response = []
    for i, xval in enumerate(x):
        response.append((xval, y[i], t[i]))
    return response

@app.route("/check-history-chart")
def check_history_chart():
    asset_data = r_list_assets(False, False)
    tpval = 0.0
    tnval = 0.0
    for _, pval, nval in asset_data["currency_summary"]:
        tpval += pval
        tnval += nval
    x, y = r_check_history(tpval, tnval)
    buffer = BytesIO()

    fig = Figure()
    ax = fig.subplots()
    ax.plot(x, y)
    ax.set_xlabel("Month")
    ax.set_xticklabels(x, rotation=90)
    ax.hlines(y=0, xmin=x[0], xmax=x[-1], colors="red", linestyles="dashed")
    
    ax.set_ylabel("Dollar Savings")
    ax.set_title(f"Asset Value Change History {(tpval + tnval):,.0f}")
    fig.savefig(buffer, format="jpeg", dpi=150)

    response = make_response(buffer.getvalue())
    response.headers.set("Content-Type", "image/jpeg")
    return response


@app.route("/cash-flow-chart")
def cash_flow_chart():
    buffer = BytesIO()
    x, y, _ = r_cash_flow()
    fig = Figure()
    ax = fig.subplots()
    ax.plot(x, y)
    ax.set_xticklabels(x, rotation=90)
    ax.hlines(y=0, xmin=x[0], xmax=x[-1], colors="red", linestyles="dashed")
    ax.set_xlabel("Month")
    ax.set_ylabel("Dollar Balance")
    ax.set_title("Cash Flow Over Time")
    fig.savefig(buffer, format="jpeg", dpi=150)

    response = make_response(buffer.getvalue())
    response.headers.set("Content-Type", "image/jpeg")
    return response


app.run(debug=True)
