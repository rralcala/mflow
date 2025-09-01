from typing import Dict, List
import json

import redis


class Transactions:
    r = redis.Redis(host="127.0.0.1", port=6379, db=0)

    def __init__(self):
        pass

    def get(self, account: str, year: str, month: str) -> List[Dict]:
        contents = self.r.lrange(f"{account}-{year}-{month}", 0, -1)
        ret = []
        for v in contents:
            ret.append(json.loads(v))
        return ret

    def set(self, account: str, year: str, month: str, data: Dict):
        contents = json.dumps(data)
        self.r.rpush(f"{account}-{year}-{month}", contents)
