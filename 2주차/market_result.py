"""계산대 검사 안내와 한 판 종료 결과."""
from catalog import PRODUCTS
from market_art import box, VIEW_W
from records import format_time

RESULT_BUTTON = (VIEW_W / 2 - 190, 650, 380, 62)


def draw_result(art, market):
    state = market.state
    if state.outcome is None:
        if market.inspection_time <= 0:
            return
        box((65, 160, VIEW_W - 130, 250), (68, 91, 119))
        box((69, 164, VIEW_W - 138, 242), (255, 248, 230))
        art.text('검사 실패 / 상품과 수량을 다시 확인해 주세요', VIEW_W / 2, 199, 30, center=True)
        missing = sum(max(0, delta) for _, delta in market.differences)
        extra = sum(max(0, -delta) for _, delta in market.differences)
        art.text(f'부족 {missing}개 / 초과/불필요 {extra}개', VIEW_W / 2, 242, 25, center=True)
        for index, (pid, delta) in enumerate(market.differences[:3]):
            detail = f'{delta}개 부족' if delta > 0 else f'{-delta}개 빼기'
            art.text(f'{PRODUCTS[pid].name} : {detail}', VIEW_W / 2, 281 + index * 30,
                     23, center=True, max_width=VIEW_W - 170)
        art.text('시간은 계속 흐릅니다 / 수정 후 계산대로 돌아오거나 E로 재검사',
                 VIEW_W / 2, 382, 21, center=True)
        return
    success = state.outcome == 'success'
    box((95, 200, VIEW_W - 190, 540), (92, 132, 167))
    box((100, 205, VIEW_W - 200, 530), (255, 248, 230))
    art.text(f'스테이지 {market.stage} 완료!' if success else '게임 오버 / 시간 초과', VIEW_W / 2, 265, 48, center=True)
    if success:
        art.text(market.session.nickname, VIEW_W / 2, 344, 30, center=True, max_width=VIEW_W - 240)
        art.text(f'완료 시간  {format_time(state.elapsed_ms)}', VIEW_W / 2, 411, 40, center=True)
        best = market.session.records.best(market.stage, market.session.nickname)
        art.text(f'내 최고 기록  {format_time(best)}', VIEW_W / 2, 475, 29, center=True)
        art.text('최고 기록 달성!' if market.new_record else '더 빠른 기록에 도전해 보세요!',
                 VIEW_W / 2, 525, 28, center=True)
        note = market.session.records.error or ('스테이지 2가 열렸습니다!' if market.stage == 1 else '스테이지별 랭킹에서 기록을 확인하세요!')
        art.text(note, VIEW_W / 2, 579, 23, center=True, max_width=VIEW_W - 240)
    else:
        art.text('제한 시간 안에 장보기를 마치지 못했어요.', VIEW_W / 2, 407, 30, center=True)
        art.text('랭킹에는 완료한 기록만 등록됩니다.', VIEW_W / 2, 477, 27, center=True)
    box(RESULT_BUTTON, (60, 111, 184))
    label = '로비로 돌아가기'
    art.text(label + '  [Enter]', VIEW_W / 2, 681, 28, (255, 255, 255), True)
