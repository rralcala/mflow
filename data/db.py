from typing import Dict, List
import json
import logging
import redis
import sys

BALANCE_HISTORY_KEY = "balance-history"


class Transactions:
    r = redis.Redis(host="127.0.0.1", port=6379, db=0)

    def __init__(self):
        try:
            self.r.ping()
        except Exception as e:
            logging.exception("Redis not available.")
            sys.exit(1)

    def get(self, account: str, year: str, month: str) -> List[Dict]:
        contents = self.r.lrange(f"{account}-{year}-{month}", 0, -1)
        ret = []
        for v in contents:
            ret.append(json.loads(v))
        return ret

    def set(self, account: str, year: str, month: str, data: Dict):
        contents = json.dumps(data)
        self.r.rpush(f"{account}-{year}-{month}", contents)

    def set_balance_history(self, year: str, month: str, amount: float):
        contents = json.loads(self.r.lrange(BALANCE_HISTORY_KEY, -1, -1))
        if len(contents) == 1:
            if "month" in contents and "year" in contents:
                if contents["month"] == month and contents["year"] == year:
                    self.r.rpop()
            else:
                self.r.rpop(BALANCE_HISTORY_KEY)
        self.r.rpush(
            BALANCE_HISTORY_KEY,
            json.dumps({"year": year, "month": month, "amount": amount}),
        )

    def get_balance_history(self):
        contents = self.r.lrange(BALANCE_HISTORY_KEY, 0, -1)
        ret = []
        for v in contents:
            row = json.loads(v)
            ret.append((f"{row['month']}-{row['year']}", float(row["amount"])))
        return ret

    def ping(self):
        print(self.r.ping())
