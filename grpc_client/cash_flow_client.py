from datetime import datetime, timezone
import logging

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

import proto.cash_flow_pb2 as pb
import proto.cash_flow_pb2_grpc as pb_grpc


def fetch_timeline(end_dt: datetime | None = None, host: str = "localhost", port: int = 50051):
    """Fetch timeline from gRPC server and return list of (country, timeline) where
    timeline is list of (datetime, (amount, currency))."""
    channel = grpc.insecure_channel(f"{host}:{port}")
    stub = pb_grpc.CashFlowServiceStub(channel)

    req = pb.GenerateTimelineRequest()
    if end_dt is not None:
        ts = Timestamp()
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        ts.FromDatetime(end_dt)
        req.end.CopyFrom(ts)

    resp = stub.GenerateTimeline(req)
    results = []
    for ct in resp.timelines:
        timeline = []
        for p in ct.payments:
            dt = p.date.ToDatetime()
            timeline.append((dt, (p.amount, p.currency)))
        results.append((ct.country, timeline))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from datetime import timedelta

    print(fetch_timeline(datetime.now() + timedelta(days=365)))
