"""
개인화 학습 로직 시나리오 테스트.
DB 없이 순수 로직만 검증 (signal 추출, EMA 업데이트, 클리핑).
"""
import pytest
from app.services.personalization_service import PersonalizationService
from app.models.personalization import (
    DraftFinalComparison,
    ComparisonResult,
    WeightSignals,
)
from app.models.planner.weights import WeightParams


@pytest.fixture
def service():
    """DB 연결 없이 서비스 로직만 테스트하기 위한 fixture."""
    svc = PersonalizationService.__new__(PersonalizationService)
    return svc


# ============================================================
# 시나리오 1: AI가 ASSIGNED 했는데 사용자가 EXCLUDED한 경우
#   → w_included 감소, w_excluded 증가
# ============================================================
class TestSignalInclusionExclusion:
    def test_user_removes_ai_tasks(self, service):
        """사용자가 AI 추천 태스크 3개 중 2개를 제거 → w_included 감소"""
        comparison = ComparisonResult(
            user_id=1, day_plan_id=100,
            ai_fill_rate=0.8, user_fill_rate=0.4,
            focus_time_zone="MORNING",
            task_comparisons=[
                DraftFinalComparison(
                    task_id=1, category="학업", focus_level=7, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="09:00", ai_end_at="10:00",
                    user_assignment_status="EXCLUDED", user_start_at=None, user_end_at=None,
                ),
                DraftFinalComparison(
                    task_id=2, category="업무", focus_level=5, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="10:00", ai_end_at="11:00",
                    user_assignment_status="EXCLUDED", user_start_at=None, user_end_at=None,
                ),
                DraftFinalComparison(
                    task_id=3, category="운동", focus_level=3, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="14:00", ai_end_at="15:00",
                    user_assignment_status="ASSIGNED", user_start_at="14:00", user_end_at="15:00",
                ),
            ],
        )
        weights = WeightParams()
        signals = service._compute_signals(comparison, weights)

        # over_inclusion_rate = 2/3 ≈ 0.667
        # s_included = 1.0 * (1.0 - 0.667) = 0.333
        assert signals.s_included < weights.w_included
        # s_excluded = 1.2 * (1.0 + 0.667) = 2.0
        assert signals.s_excluded > weights.w_excluded

    def test_user_adds_ai_excluded_tasks(self, service):
        """사용자가 AI가 제외한 태스크를 포함 → w_included 증가"""
        comparison = ComparisonResult(
            user_id=1, day_plan_id=100,
            ai_fill_rate=0.4, user_fill_rate=0.7,
            focus_time_zone="MORNING",
            task_comparisons=[
                DraftFinalComparison(
                    task_id=1, category="학업", focus_level=7, is_urgent=False,
                    ai_assignment_status="EXCLUDED",
                    user_assignment_status="ASSIGNED", user_start_at="09:00", user_end_at="10:00",
                ),
                DraftFinalComparison(
                    task_id=2, category="업무", focus_level=5, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="10:00", ai_end_at="11:00",
                    user_assignment_status="ASSIGNED", user_start_at="10:00", user_end_at="11:00",
                ),
            ],
        )
        weights = WeightParams()
        signals = service._compute_signals(comparison, weights)

        # under_inclusion_rate = 1/2 = 0.5
        # s_included = 1.0 * (1.0 + 0.5) = 1.5
        assert signals.s_included > weights.w_included


# ============================================================
# 시나리오 2: 사용자가 focus timezone으로 태스크를 이동
#   → w_focus_align 증가
# ============================================================
class TestSignalFocusAlignment:
    def test_move_into_focus_timezone(self, service):
        """태스크를 AFTERNOON → MORNING(focus)으로 이동 → w_focus_align 증가"""
        comparison = ComparisonResult(
            user_id=1, day_plan_id=100,
            ai_fill_rate=0.6, user_fill_rate=0.6,
            focus_time_zone="MORNING",
            task_comparisons=[
                DraftFinalComparison(
                    task_id=1, category="학업", focus_level=8, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="14:00", ai_end_at="15:00",
                    user_assignment_status="ASSIGNED", user_start_at="09:00", user_end_at="10:00",
                ),
                DraftFinalComparison(
                    task_id=2, category="업무", focus_level=5, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="10:00", ai_end_at="11:00",
                    user_assignment_status="ASSIGNED", user_start_at="10:00", user_end_at="11:00",
                ),
            ],
        )
        weights = WeightParams()
        signals = service._compute_signals(comparison, weights)

        # 1 task moved into focus, 0 moved out
        # focus_shift = 1/2 = 0.5
        assert signals.s_focus_align > weights.w_focus_align


# ============================================================
# 시나리오 3: 사용자가 태스크 시간을 줄임
#   → alpha_duration 감소
# ============================================================
class TestSignalDuration:
    def test_user_shortens_duration(self, service):
        """사용자가 태스크 시간을 60분 → 30분으로 줄임"""
        comparison = ComparisonResult(
            user_id=1, day_plan_id=100,
            ai_fill_rate=0.6, user_fill_rate=0.4,
            focus_time_zone="MORNING",
            task_comparisons=[
                DraftFinalComparison(
                    task_id=1, category="학업", focus_level=5, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="09:00", ai_end_at="10:00",
                    user_assignment_status="ASSIGNED", user_start_at="09:00", user_end_at="09:30",
                ),
            ],
        )
        weights = WeightParams()
        signals = service._compute_signals(comparison, weights)

        # delta = (30-60)/60 = -0.5 → signal = 0.05 * (1 + (-0.5)*0.5) = 0.0375
        assert signals.s_alpha_duration < weights.alpha_duration

    def test_user_lengthens_duration(self, service):
        """사용자가 태스크 시간을 60분 → 90분으로 늘림"""
        comparison = ComparisonResult(
            user_id=1, day_plan_id=100,
            ai_fill_rate=0.6, user_fill_rate=0.8,
            focus_time_zone="MORNING",
            task_comparisons=[
                DraftFinalComparison(
                    task_id=1, category="학업", focus_level=5, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="09:00", ai_end_at="10:00",
                    user_assignment_status="ASSIGNED", user_start_at="09:00", user_end_at="10:30",
                ),
            ],
        )
        weights = WeightParams()
        signals = service._compute_signals(comparison, weights)

        assert signals.s_alpha_duration > weights.alpha_duration


# ============================================================
# 시나리오 4: 카테고리 선호도
#   → 유지된 카테고리의 w_category 증가, 제거된 카테고리 감소
# ============================================================
class TestSignalCategory:
    def test_category_preference(self, service):
        """학업 태스크 2개 중 2개 유지, 운동 2개 중 0개 유지"""
        comparison = ComparisonResult(
            user_id=1, day_plan_id=100,
            ai_fill_rate=0.6, user_fill_rate=0.4,
            focus_time_zone="MORNING",
            task_comparisons=[
                DraftFinalComparison(
                    task_id=1, category="학업", focus_level=7, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="09:00", ai_end_at="10:00",
                    user_assignment_status="ASSIGNED", user_start_at="09:00", user_end_at="10:00",
                ),
                DraftFinalComparison(
                    task_id=2, category="학업", focus_level=6, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="10:00", ai_end_at="11:00",
                    user_assignment_status="ASSIGNED", user_start_at="10:00", user_end_at="11:00",
                ),
                DraftFinalComparison(
                    task_id=3, category="운동", focus_level=3, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="14:00", ai_end_at="15:00",
                    user_assignment_status="EXCLUDED", user_start_at=None, user_end_at=None,
                ),
                DraftFinalComparison(
                    task_id=4, category="운동", focus_level=2, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="15:00", ai_end_at="16:00",
                    user_assignment_status="EXCLUDED", user_start_at=None, user_end_at=None,
                ),
            ],
        )
        weights = WeightParams()
        signals = service._compute_signals(comparison, weights)

        # 학업: kept=2, total=2, ratio=1.0 → signal = 3.0 * (0.5+1.0) = 4.5
        assert signals.s_category["학업"] > weights.w_category["학업"]
        # 운동: kept=0, total=2, ratio=0.0 → signal = 1.5 * (0.5+0.0) = 0.75
        assert signals.s_category["운동"] < weights.w_category["운동"]


# ============================================================
# 시나리오 5: EMA 업데이트 + 클리핑 검증
# ============================================================
class TestEMAUpdate:
    def test_ema_blends_old_and_new(self, service):
        """EMA가 기존 70% + 신호 30%로 블렌딩되는지 검증"""
        weights = WeightParams()  # w_included=1.0, ema_decay=0.7
        signals = WeightSignals(
            s_focus=weights.w_focus,
            s_urgent=weights.w_urgent,
            s_alpha_duration=weights.alpha_duration,
            s_included=2.0,  # 신호: 2.0 (증가 방향)
            s_excluded=weights.w_excluded,
            s_overflow=weights.w_overflow,
            s_focus_align=weights.w_focus_align,
            s_fatigue_risk=weights.w_fatigue_risk,
            s_category=dict(weights.w_category),
            n_tasks_compared=10,
        )
        new_weights = service._apply_ema_update(weights, signals)

        # EMA: 0.7 * 1.0 + 0.3 * 2.0 = 1.3
        assert abs(new_weights.w_included - 1.3) < 0.01

    def test_clip_prevents_extreme_values(self, service):
        """클리핑이 극단값을 방지하는지 검증"""
        weights = WeightParams()  # clip_min=0.1, clip_max=5.0
        signals = WeightSignals(
            s_focus=weights.w_focus,
            s_urgent=100.0,  # 극단적으로 높은 신호
            s_alpha_duration=0.0,  # 극단적으로 낮은 신호
            s_included=weights.w_included,
            s_excluded=weights.w_excluded,
            s_overflow=weights.w_overflow,
            s_focus_align=weights.w_focus_align,
            s_fatigue_risk=weights.w_fatigue_risk,
            s_category=dict(weights.w_category),
            n_tasks_compared=10,
        )
        new_weights = service._apply_ema_update(weights, signals)

        # w_urgent: EMA(5.0, 100.0) = 0.7*5 + 0.3*100 = 33.5 → clipped to 5.0
        assert new_weights.w_urgent == 5.0
        # alpha_duration: EMA(0.05, 0.0) = 0.035 → clipped to 0.1
        assert new_weights.alpha_duration == 0.1

    def test_unchanged_params_preserved(self, service):
        """미사용 파라미터들이 그대로 보존되는지 검증"""
        weights = WeightParams()
        signals = WeightSignals(
            s_focus=2.0, s_urgent=3.0,
            s_alpha_duration=0.1,
            s_included=1.5, s_excluded=1.0,
            s_overflow=1.5, s_focus_align=1.0,
            s_fatigue_risk=0.3,
            s_category={"학업": 2.0},
            n_tasks_compared=5,
        )
        new_weights = service._apply_ema_update(weights, signals)

        # 미사용 파라미터 그대로 보존
        assert new_weights.w_carry_task == weights.w_carry_task
        assert new_weights.w_carry_group == weights.w_carry_group
        assert new_weights.w_switch == weights.w_switch
        assert new_weights.ema_decay == weights.ema_decay
        assert new_weights.clip_min == weights.clip_min
        assert new_weights.clip_max == weights.clip_max


# ============================================================
# 시나리오 6: 주간 누적 (여러 일의 신호 가중 평균)
# ============================================================
class TestWeeklyAggregation:
    def test_weighted_average_by_task_count(self, service):
        """태스크 수 기반 가중 평균이 올바르게 동작하는지 검증"""
        weights = WeightParams()

        # Day 1: 2 tasks, w_included 신호 = 0.5
        comp1 = ComparisonResult(
            user_id=1, day_plan_id=100,
            ai_fill_rate=0.6, user_fill_rate=0.6,
            focus_time_zone="MORNING",
            task_comparisons=[
                DraftFinalComparison(
                    task_id=1, category="학업", focus_level=5, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="09:00", ai_end_at="10:00",
                    user_assignment_status="ASSIGNED", user_start_at="09:00", user_end_at="10:00",
                ),
                DraftFinalComparison(
                    task_id=2, category="학업", focus_level=5, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="10:00", ai_end_at="11:00",
                    user_assignment_status="ASSIGNED", user_start_at="10:00", user_end_at="11:00",
                ),
            ],
        )
        # Day 2: 1 task, 사용자가 제거
        comp2 = ComparisonResult(
            user_id=1, day_plan_id=101,
            ai_fill_rate=0.5, user_fill_rate=0.2,
            focus_time_zone="MORNING",
            task_comparisons=[
                DraftFinalComparison(
                    task_id=3, category="운동", focus_level=3, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="14:00", ai_end_at="15:00",
                    user_assignment_status="EXCLUDED", user_start_at=None, user_end_at=None,
                ),
            ],
        )

        aggregated = service._aggregate_weekly_signals([comp1, comp2], weights)

        # total_tasks = 3, day1 weight = 2/3, day2 weight = 1/3
        assert aggregated.n_tasks_compared == 3
        # s_included는 day1(변화없음)과 day2(감소)의 가중 평균
        # day1: over=0, under=0 → s_included = 1.0
        # day2: over=1/1, under=0 → s_included = 1.0 * (1.0 - 1.0) = 0.0
        # weighted avg = 1.0*(2/3) + 0.0*(1/3) ≈ 0.667
        assert aggregated.s_included < weights.w_included


# ============================================================
# 시나리오 7: 긴급 태스크 유지율
# ============================================================
class TestSignalUrgent:
    def test_urgent_tasks_all_kept(self, service):
        """긴급 태스크를 모두 유지 → w_urgent 유지/증가"""
        comparison = ComparisonResult(
            user_id=1, day_plan_id=100,
            ai_fill_rate=0.6, user_fill_rate=0.6,
            focus_time_zone="MORNING",
            task_comparisons=[
                DraftFinalComparison(
                    task_id=1, category="업무", focus_level=9, is_urgent=True,
                    ai_assignment_status="ASSIGNED", ai_start_at="09:00", ai_end_at="10:00",
                    user_assignment_status="ASSIGNED", user_start_at="09:00", user_end_at="10:00",
                ),
                DraftFinalComparison(
                    task_id=2, category="학업", focus_level=5, is_urgent=False,
                    ai_assignment_status="ASSIGNED", ai_start_at="10:00", ai_end_at="11:00",
                    user_assignment_status="ASSIGNED", user_start_at="10:00", user_end_at="11:00",
                ),
            ],
        )
        weights = WeightParams()
        signals = service._compute_signals(comparison, weights)

        # urgent_keep_rate = 1/1 = 1.0 → signal = 5.0 * (0.5 + 1.0) = 7.5
        assert signals.s_urgent >= weights.w_urgent

    def test_urgent_tasks_removed(self, service):
        """긴급 태스크를 제거 → w_urgent 감소"""
        comparison = ComparisonResult(
            user_id=1, day_plan_id=100,
            ai_fill_rate=0.6, user_fill_rate=0.3,
            focus_time_zone="MORNING",
            task_comparisons=[
                DraftFinalComparison(
                    task_id=1, category="업무", focus_level=9, is_urgent=True,
                    ai_assignment_status="ASSIGNED", ai_start_at="09:00", ai_end_at="10:00",
                    user_assignment_status="EXCLUDED", user_start_at=None, user_end_at=None,
                ),
            ],
        )
        weights = WeightParams()
        signals = service._compute_signals(comparison, weights)

        # urgent_keep_rate = 0/1 = 0.0 → signal = 5.0 * 0.5 = 2.5
        assert signals.s_urgent < weights.w_urgent


# ============================================================
# 시나리오 8: 데이터 없음 → 중립 신호 (가중치 변화 없음)
# ============================================================
class TestNeutralSignals:
    def test_no_tasks_returns_neutral(self, service):
        """태스크가 0개면 중립 신호 반환"""
        comparison = ComparisonResult(
            user_id=1, day_plan_id=100,
            ai_fill_rate=0.0, user_fill_rate=0.0,
            focus_time_zone="MORNING",
            task_comparisons=[],
        )
        weights = WeightParams()
        signals = service._compute_signals(comparison, weights)

        assert signals.n_tasks_compared == 0

    def test_neutral_signals_preserve_weights(self, service):
        """중립 신호로 EMA 적용 시 가중치 변화 없음"""
        weights = WeightParams()
        neutral = service._neutral_signals(weights)
        new_weights = service._apply_ema_update(weights, neutral)

        assert abs(new_weights.w_focus - weights.w_focus) < 0.001
        assert abs(new_weights.w_urgent - weights.w_urgent) < 0.001
        assert abs(new_weights.w_included - weights.w_included) < 0.001
