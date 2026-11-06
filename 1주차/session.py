"""실행 중에만 보관하는 상태. 미리보기는 보상이나 해금을 발생시키지 않는다."""
from dataclasses import dataclass


@dataclass
class Session:
    nickname: str = ""
    selected_stage: int | None = None
    stage2_unlocked: bool = False

    def reset(self):
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
