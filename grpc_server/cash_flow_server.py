import logging
import os
import sys
import time
from concurrent import futures
from datetime import datetime, timedelta, timezone
from pathlib import Path

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

import grpc
from google.protobuf.timestamp_pb2 import Timestamp
from mflow_shared_rralcala.data.asset_store import load_assets
from mflow_shared_rralcala.data.coinbase import get_accounts

import proto.cash_flow_pb2 as pb
import proto.cash_flow_pb2_grpc as pb_grpc
from asset_classes.fetcher import fetch_assets
from asset_classes.instrument import Instrument
from lib.config import (
    BASE_PATH,
    COINBASE_API_KEY,
    COINBASE_API_SECRET,
    COINBASE_PORTFOLIO_ID,
)
from reports.cash_flow import generate_timeline
from reports.list_assets import list_assets


class CashFlowServicer(pb_grpc.CashFlowServiceServicer):
    def __init__(self):
        super().__init__()
        self.key_path = Path("./key.json")
        self.load_assets()

    def load_assets(self):
        self.assets = load_assets(fetch_assets, BASE_PATH, self.key_path)
        for position in get_accounts(
            COINBASE_API_KEY, COINBASE_API_SECRET, COINBASE_PORTFOLIO_ID
        ):
            if position["asset"] == "USDC":
                qty = float(position["total_balance_crypto"])
                rate = 0.045
                account = Instrument(
                    location="Coinbase",
                    symbol="USDC",
                    price=1.0,
                    factor=1.0,
                    qty=qty,
                    estimated_dividend=qty * rate / 12,
                    rate=rate,
                    dividend="0 0 1 * *",
                    currency="USD",
                    acquisition_date=datetime(2025, 9, 24),
                    acquisition_price=1.0,
                    liquid=True,
                )
                self.assets["USD"].append(account)
            if position["asset"] == "SOL":
                qty = float(position["total_balance_crypto"])
                rate = 0.0424
                account = Instrument(
                    location="Coinbase",
                    symbol="SOLUSD",
                    price=float(position["total_balance_fiat"]) / qty,
                    factor=1.0,
                    qty=qty,
                    estimated_dividend=qty * rate / 12,
                    rate=rate,
                    dividend="0 0 1 * *",
                    currency="USD",
                    acquisition_date=datetime(2025, 9, 24),
                    acquisition_price=float(position["cost_basis"]["value"]) / qty,
                    liquid=False,
                )
                self.assets["USD"].append(account)

    def ClearCache(self, request, context):
        self.assets = self.load_assets()
        return pb.BoolResponse(success=True)

    def GenerateTimeline(self, request, context):
        start_time = time.perf_counter()
        # Convert request end timestamp to datetime, or default to one year from now
        if request.HasField("end") and (
            request.end.seconds != 0 or request.end.nanos != 0
        ):
            end_dt = request.end.ToDatetime()
        else:
            end_dt = datetime.now() + timedelta(days=365)

        resp = pb.GenerateTimelineResponse()
        for country, tl in generate_timeline(self.assets, end_dt):
            ct = pb.CountryTimeline(country=country)
            for entry in tl:
                # entry is (datetime, (amount, currency))
                d, (amount, currency) = entry
                ts = Timestamp()
                dt = datetime(d.year, d.month, d.day)
                if dt.tzinfo is None:
                    dt_aware = dt.replace(tzinfo=timezone.utc)
                else:
                    dt_aware = dt.astimezone(timezone.utc)
                ts.FromDatetime(dt_aware)
                payment = pb.Payment(date=ts, amount=amount, currency=currency)
                ct.payments.append(payment)
            resp.timelines.append(ct)
        logging.info(
            f"GenerateTimeline processed in {time.perf_counter() - start_time:.4f} seconds"
        )

        return resp

    def ListAssets(self, request, context):
        start_time = time.perf_counter()
        # Call the local list_assets and map results to protobuf response
        currency_summary, returns, breakdown = list_assets(
            self.assets, request.print_pos, request.print_neg
        )

        resp = pb.ListAssetsResponse()

        for cur, pval, nval in currency_summary:
            resp.currency_summary.add(
                currency=cur, positive_value=pval, negative_value=nval
            )

        for item in returns:
            # item: [current_value, current_return, identifier]
            cv, cr, ident = item
            resp.return_history.add(
                current_value=cv, current_return=cr, identifier=ident
            )

        # breakdown may use key 'postives' (typo in source) or 'positives'
        positives = breakdown.get("positives") or breakdown.get("postives") or []
        negatives = breakdown.get("negatives") or []

        for ident, formatted in positives:
            resp.positives.add(identifier=ident, formatted=formatted)

        for ident, formatted in negatives:
            resp.negatives.add(identifier=ident, formatted=formatted)
        logging.info(
            f"ListAssets processed in {time.perf_counter() - start_time:.4f} seconds"
        )
        return resp


def serve(port: int = 50051):
    logging.basicConfig(level=logging.INFO)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    pb_grpc.add_CashFlowServiceServicer_to_server(CashFlowServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    logging.info(f"CashFlow gRPC server started on 0.0.0.0:{port}")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logging.info("Shutting down server...")
        server.stop(0)


if __name__ == "__main__":
    serve()
