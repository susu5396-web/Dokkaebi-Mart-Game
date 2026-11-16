"""계산대 검사 안내와 한 판 종료 결과."""
from catalog import PRODUCTS
from market_art import box, VIEW_W
from settings import ACQUISITION_TARGET

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
    art.text('게임 성공!' if success else '게임 실패 / 시간 초과', VIEW_W / 2, 265, 48, center=True)
    if success:
        art.draw('ui/reward_banknotes', (VIEW_W / 2 - 100, 310, 200, 130), trim=True)
        art.text(f'보수 {market.reward:,}원 받았습니다', VIEW_W / 2, 479, 34, center=True)
        art.text(f'인수 자금 {market.session.funds:,} / {ACQUISITION_TARGET:,}원',
                 VIEW_W / 2, 530, 27, center=True)
        note = ('목표 달성! 이제 우리 마트입니다.' if market.session.acquired else
                '2단계가 열렸습니다!' if market.stage == 1 else '다음 장보기도 도전해 보세요!')
        art.text(note, VIEW_W / 2, 579, 27, center=True)
    else:
        art.text('제한 시간 안에 장보기를 마치지 못했어요.', VIEW_W / 2, 407, 30, center=True)
        art.text('이번 보수는 0원입니다. 다시 도전해 보세요!', VIEW_W / 2, 477, 27, center=True)
    box(RESULT_BUTTON, (60, 111, 184))
    label = '인수 완료 보기' if success and market.session.acquired else '로비로 돌아가기'
    art.text(label + '  [Enter]', VIEW_W / 2, 681, 28, (255, 255, 255), True)
