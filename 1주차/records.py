"""닉네임별 스테이지 최고 기록을 로컬 파일에 보관한다."""
import json
from pathlib import Path

SAVE_PATH = Path(__file__).resolve().parents[1] / 'save_data' / 'rankings.json'


def format_time(milliseconds):
    minutes, rest = divmod(milliseconds, 60_000)
    seconds, millis = divmod(rest, 1000)
    return f'{minutes:02d}:{seconds:02d}.{millis // 10:02d}'


class RecordBook:
    def __init__(self, path=SAVE_PATH):
        self.path = Path(path)
        self.error = ''
        self.entries = {1: {}, 2: {}}
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            for stage in self.entries:
                for name, elapsed in data[str(stage)].items():
                    if isinstance(name, str) and name and type(elapsed) is int and elapsed >= 0:
                        self.entries[stage][name] = elapsed
        except FileNotFoundError:
            pass
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            self.error = '기록 파일을 읽지 못했습니다. 원본 파일을 확인해 주세요.'

    def best(self, stage, nickname):
        return self.entries[stage].get(nickname)

    def ranking(self, stage):
        return sorted(self.entries[stage].items(), key=lambda row: (row[1], row[0]))

    def record(self, stage, nickname, milliseconds):
        previous = self.best(stage, nickname)
        improved = previous is None or milliseconds < previous
        if improved:
            self.entries[stage][nickname] = milliseconds
        if self.error:
            return improved
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix('.tmp')
            temporary.write_text(json.dumps(self.entries, ensure_ascii=False, indent=2), encoding='utf-8')
            temporary.replace(self.path)
        except OSError:
            self.error = '기록 저장 실패: 이번 기록은 게임 종료 시 사라질 수 있습니다.'
        return improved
