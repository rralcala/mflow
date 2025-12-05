import logging
from datetime import datetime, timezone

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

import proto.cash_flow_pb2 as pb
import proto.cash_flow_pb2_grpc as pb_grpc


def fetch_timeline(
    end_dt: datetime | None = None, host: str = "localhost", port: int = 50051
):
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

def clear_cache(host: str = "localhost", port: int = 50051):
    """Clear cache on gRPC server."""
    channel = grpc.insecure_channel(f"{host}:{port}")
    stub = pb_grpc.CashFlowServiceStub(channel)

    resp = stub.ClearCache(pb.google_dot_protobuf_dot_empty__pb2.Empty())
    return resp

def fetch_list_assets(
    print_pos: bool, print_neg: bool, host: str = "localhost", port: int = 50051
):
    """Fetch list_assets via gRPC and return (currency_summary, returns, breakdown)
    where:
      - currency_summary: list of (currency, positive_value, negative_value)
      - returns: list of (current_value, current_return, identifier)
      - breakdown: dict with keys 'postives' (typo) and 'negatives', each a list of (identifier, formatted)
    """
    channel = grpc.insecure_channel(f"{host}:{port}")
    stub = pb_grpc.CashFlowServiceStub(channel)

    req = pb.ListAssetsRequest(print_pos=print_pos, print_neg=print_neg)
    resp = stub.ListAssets(req)

    currency_summary = []
    for cs in resp.currency_summary:
        currency_summary.append((cs.currency, cs.positive_value, cs.negative_value))

    returns = []
    for rh in resp.return_history:
        returns.append((rh.current_value, rh.current_return, rh.identifier))

    positives = []
    for a in resp.positives:
        positives.append((a.identifier, a.formatted))

    negatives = []
    for a in resp.negatives:
        negatives.append((a.identifier, a.formatted))

    breakdown = {"postives": positives, "negatives": negatives}
    return currency_summary, returns, breakdown


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from datetime import timedelta

    print(fetch_timeline(datetime.now() + timedelta(days=365)))
