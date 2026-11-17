"""로그인 상태와 닉네임별 영구 기록을 분리해 관리한다."""
from dataclasses import dataclass, field
from records import RecordBook


@dataclass
class Session:
    nickname: str = ""
    selected_stage: int | None = None
    stage2_unlocked: bool = False

    records: RecordBook = field(default_factory=RecordBook)

    def login(self, nickname):
        self.reset()
        self.nickname = nickname
        self.stage2_unlocked = self.records.best(1, nickname) is not None

    def complete_stage(self, stage):
        if stage == 1:
            self.stage2_unlocked = True

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
