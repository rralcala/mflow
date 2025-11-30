import logging
from concurrent import futures
from datetime import datetime, timedelta, timezone
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, "..")
sys.path.insert(0, project_root)

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from reports.cash_flow import generate_timeline
import proto.cash_flow_pb2 as pb
import proto.cash_flow_pb2_grpc as pb_grpc


class CashFlowServicer(pb_grpc.CashFlowServiceServicer):
    def GenerateTimeline(self, request, context):
        # Convert request end timestamp to datetime, or default to one year from now
        if request.HasField("end") and (request.end.seconds != 0 or request.end.nanos != 0):
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
