"""화면과 독립된 한 판의 상품 배치 및 카트 데이터."""
import random
from catalog import PRODUCTS, GROUPS


class MarketState:
    def __init__(self, seed=None):
        rng = random.Random(seed)
        self.layout = []
        for category, groups in enumerate(GROUPS):
            ordered = []
            for group, _, _ in groups:
                ids = [p.id for p in PRODUCTS.values()
                       if p.category == category and p.group == group]
                rng.shuffle(ids)
                ordered.extend(ids)
            self.layout.append([ordered[i:i + 4] for i in range(0, 32, 4)])
        # 스테이지 1: 카테고리마다 1종, 합계 7~8개, 상품별 최대 2개.
        selected = [rng.choice([pid for section in category for pid in section])
                    for category in self.layout]
        self.required = dict.fromkeys(selected, 1)
        for pid in rng.sample(selected, rng.randint(7, 8) - len(selected)):
            self.required[pid] += 1
        self.inventory = {}
        self.remaining = 240.0
        self.outcome = None

    def add(self, pid):
        if self.outcome is None and pid in PRODUCTS:
            self.inventory[pid] = self.inventory.get(pid, 0) + 1

    def discard(self, pid):
        if self.outcome is not None or pid not in self.inventory:
            return
        self.inventory[pid] -= 1
        if self.inventory[pid] == 0:
            del self.inventory[pid]

    def checkout(self):
        if self.outcome is not None:
            return []
        if self.remaining <= 0:
            self.outcome = 'timeout'
            return []
        differences = []
        for pid in dict.fromkeys((*self.required, *self.inventory)):
            delta = self.required.get(pid, 0) - self.inventory.get(pid, 0)
            if delta:
                differences.append((pid, delta))
        if not differences:
            self.outcome = 'success'
        return differences

    def update(self, dt):
        if self.outcome is not None:
            return
        self.remaining = max(0.0, self.remaining - dt)
        if self.remaining == 0:
            self.outcome = 'timeout'
