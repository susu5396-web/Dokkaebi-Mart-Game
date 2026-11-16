"""실행 중에만 보관하는 상태. 미리보기는 보상이나 해금을 발생시키지 않는다."""
from dataclasses import dataclass
from settings import STAGE_REWARDS, ACQUISITION_TARGET


@dataclass
class Session:
    nickname: str = ""
    selected_stage: int | None = None
    stage2_unlocked: bool = False

    funds: int = 0

    @property
    def acquired(self):
        return self.funds >= ACQUISITION_TARGET

    def complete_stage(self, stage):
        reward = STAGE_REWARDS[stage]
        self.funds += reward
        if stage == 1:
            self.stage2_unlocked = True
        return reward

    def reset(self):
        self.funds = 0
        self.nickname = ""
        self.selected_stage = None
        self.stage2_unlocked = False

    def choose_stage(self, stage):
        if stage == 2 and not self.stage2_unlocked:
            return False
        if stage not in (1, 2):
            return False
        self.selected_stage = stage
        return True

    def return_to_lobby(self):
        self.selected_stage = None
