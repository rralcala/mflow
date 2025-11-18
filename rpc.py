from concurrent import futures
import logging
import socket
import time
import sys

import grpc

from exp_proto import expense_pb2
from exp_proto import expense_pb2_grpc

PORT = "50051"

class ExpenseService(expense_pb2_grpc.ExpenseService):
    def CreateExpense(self, request, context):
        logging.warning(request)
        request.expense.id = "1"

        return expense_pb2.CreateExpenseResponse(expense=request.expense)


def serve():
    logging.basicConfig(level=logging.DEBUG)
    IPAddr = ""
    try:
        hostname = socket.gethostname()
        IPAddr = socket.gethostbyname(hostname)
    except socket.gaierror:
        logging.error("Could not resolve hostname to IP address.")
        sys.exit(1)
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    expense_pb2_grpc.add_ExpenseServiceServicer_to_server(ExpenseService(), server)
    server.add_insecure_port(IPAddr + ":" + PORT)

    server.start()
    logging.info(f"gRPC server started on port {IPAddr}:{PORT}...")
    try:
        while True:
            time.sleep(86400)  # One day in seconds
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    serve()
