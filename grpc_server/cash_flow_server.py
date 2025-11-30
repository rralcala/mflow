import logging
import os
import sys
from concurrent import futures
from datetime import datetime, timedelta, timezone

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

import proto.cash_flow_pb2 as pb
import proto.cash_flow_pb2_grpc as pb_grpc
from reports.cash_flow import generate_timeline
from reports.list_assets import list_assets


class CashFlowServicer(pb_grpc.CashFlowServiceServicer):
    def GenerateTimeline(self, request, context):
        # Convert request end timestamp to datetime, or default to one year from now
        if request.HasField("end") and (
            request.end.seconds != 0 or request.end.nanos != 0
        ):
            end_dt = request.end.ToDatetime()
        else:
            end_dt = datetime.now() + timedelta(days=365)

        resp = pb.GenerateTimelineResponse()
        for country, tl in generate_timeline(end_dt):
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
        return resp

    def ListAssets(self, request, context):
        # Call the local list_assets and map results to protobuf response
        currency_summary, returns, breakdown = list_assets(
            request.print_pos, request.print_neg
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
