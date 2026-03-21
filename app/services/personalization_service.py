import time
import logging
from datetime import timedelta
from collections import defaultdict

from app.models.personalization import (
    PersonalizationIngestRequest,
    PersonalizationIngestResponse,
    DraftFinalComparison,
    ComparisonResult,
    WeightSignals,
)
from app.models.planner.weights import WeightParams
from app.db.repositories.personalization_repository import PersonalizationRepository
from app.services.planner.utils.time_utils import hhmm_to_minutes, get_timezone

logger = logging.getLogger(__name__)


class PersonalizationService:
    def __init__(self):
        self.repository = PersonalizationRepository()

    async def process_ingest_request(
        self, request: PersonalizationIngestRequest
    ) -> PersonalizationIngestResponse:
        start_time = time.time()

        results = []
        for user_id in request.user_ids:
            try:
                result = await self._process_user(user_id, request.target_date)
                results.append(result)
            except Exception as e:
                logger.error(f"[Personalization] user_id={user_id} error: {e}")
                results.append({"user_id": user_id, "status": "error", "message": str(e)})

        updated_count = sum(1 for r in results if r.get("status") == "updated")
        skipped_count = sum(1 for r in results if r.get("status") == "skipped")
        error_count = sum(1 for r in results if r.get("status") == "error")

        process_time = time.time() - start_time

        return PersonalizationIngestResponse(
            success=error_count == 0,
            process_time=process_time,
            user_ids=request.user_ids,
            message=f"updated={updated_count}, skipped={skipped_count}, errors={error_count}",
        )

    async def _process_user(self, user_id: int, target_date) -> dict:
        """한 사용자의 주간 데이터를 분석하여 가중치를 업데이트한다."""
        start_date = target_date - timedelta(days=7)

        # 1. AI_DRAFT + USER_FINAL 쌍 조회
        records = await self.repository.fetch_draft_final_pairs(
            user_id, start_date, target_date
        )
        if not records:
            return {"user_id": user_id, "status": "skipped", "message": "No draft-final pairs found"}

        # day_plan_id별로 AI_DRAFT, USER_FINAL 분리
        pairs = self._group_record_pairs(records)
        if not pairs:
            return {"user_id": user_id, "status": "skipped", "message": "No complete pairs"}

        # 2. 모든 record_id의 태스크 조회
        all_record_ids = []
        for ai_rec, user_rec in pairs:
            all_record_ids.extend([ai_rec["id"], user_rec["id"]])

        tasks = await self.repository.fetch_record_tasks(all_record_ids)
        tasks_by_record = defaultdict(list)
        for t in tasks:
            tasks_by_record[t["record_id"]].append(t)

        # 3. 비교 결과 생성
        comparisons = []
        for ai_rec, user_rec in pairs:
            comparison = self._build_comparison(
                ai_rec, user_rec,
                tasks_by_record[ai_rec["id"]],
                tasks_by_record[user_rec["id"]],
                user_id,
            )
            if comparison and comparison.task_comparisons:
                comparisons.append(comparison)

        if not comparisons:
            return {"user_id": user_id, "status": "skipped", "message": "No tasks to compare"}

        # 4. 현재 가중치 로드
        weight_data = await self.repository.fetch_current_weights(user_id)
        if weight_data:
            current_weights = WeightParams(**weight_data["weights"])
            current_version = weight_data["version"]
        else:
            current_weights = WeightParams()
            current_version = 0

        # 5. 주간 신호 누적 추출
        aggregated_signals = self._aggregate_weekly_signals(comparisons, current_weights)

        # 6. EMA 적용 + 클리핑
        new_weights = self._apply_ema_update(current_weights, aggregated_signals)

        # 7. 저장
        new_version = current_version + 1
        await self.repository.save_weights(
            user_id, new_weights.model_dump(), new_version
        )

        logger.info(f"[Personalization] user_id={user_id} weights updated v{current_version}->v{new_version}")
        return {
            "user_id": user_id,
            "status": "updated",
            "old_version": current_version,
            "new_version": new_version,
        }

    def _group_record_pairs(self, records: list[dict]) -> list[tuple[dict, dict]]:
        """day_plan_id별로 (AI_DRAFT, USER_FINAL) 쌍을 만든다.
        같은 day_plan_id에 AI_DRAFT가 여러 개면 최신 것을 사용."""
        by_day = defaultdict(dict)
        for r in records:
            day_id = r["day_plan_id"]
            rtype = r["record_type"]
            # 같은 타입이 여러 개면 최신 것(created_at DESC)을 사용
            if rtype not in by_day[day_id] or r["created_at"] > by_day[day_id][rtype]["created_at"]:
                by_day[day_id][rtype] = r

        pairs = []
        for day_id, type_map in by_day.items():
            if "AI_DRAFT" in type_map and "USER_FINAL" in type_map:
                pairs.append((type_map["AI_DRAFT"], type_map["USER_FINAL"]))
        return pairs

    def _build_comparison(
        self,
        ai_rec: dict,
        user_rec: dict,
        ai_tasks: list[dict],
        user_tasks: list[dict],
        user_id: int,
    ) -> ComparisonResult | None:
        """AI_DRAFT와 USER_FINAL의 태스크를 task_id로 매칭하여 비교 결과를 생성."""
        ai_task_map = {t["task_id"]: t for t in ai_tasks}
        user_task_map = {t["task_id"]: t for t in user_tasks}

        # 양쪽 모두에 존재하는 task_id만 비교
        common_ids = set(ai_task_map.keys()) & set(user_task_map.keys())
        if not common_ids:
            return None

        task_comparisons = []
        for tid in common_ids:
            ai = ai_task_map[tid]
            user = user_task_map[tid]
            task_comparisons.append(DraftFinalComparison(
                task_id=tid,
                category=ai.get("category"),
                focus_level=ai.get("focus_level"),
                is_urgent=ai.get("is_urgent"),
                ai_assignment_status=ai["assignment_status"],
                ai_start_at=ai.get("start_at"),
                ai_end_at=ai.get("end_at"),
                ai_importance_score=float(ai["importance_score"]) if ai.get("importance_score") is not None else None,
                user_assignment_status=user["assignment_status"],
                user_start_at=user.get("start_at"),
                user_end_at=user.get("end_at"),
            ))

        return ComparisonResult(
            user_id=user_id,
            day_plan_id=ai_rec["day_plan_id"],
            ai_fill_rate=float(ai_rec.get("fill_rate") or 0),
            user_fill_rate=float(user_rec.get("fill_rate") or 0),
            focus_time_zone=ai_rec.get("focus_time_zone", "MORNING"),
            task_comparisons=task_comparisons,
        )

    def _aggregate_weekly_signals(
        self, comparisons: list[ComparisonResult], current_weights: WeightParams
    ) -> WeightSignals:
        """여러 일별 ComparisonResult에서 신호를 추출하고, 태스크 수 기준 가중 평균."""
        daily_signals = []
        for comp in comparisons:
            sig = self._compute_signals(comp, current_weights)
            if sig.n_tasks_compared > 0:
                daily_signals.append(sig)

        if not daily_signals:
            return self._neutral_signals(current_weights)

        # 태스크 수 기준 가중 평균
        total_tasks = sum(s.n_tasks_compared for s in daily_signals)
        if total_tasks == 0:
            return self._neutral_signals(current_weights)

        agg = WeightSignals()
        agg.n_tasks_compared = total_tasks

        for sig in daily_signals:
            w = sig.n_tasks_compared / total_tasks
            agg.s_focus += sig.s_focus * w
            agg.s_urgent += sig.s_urgent * w
            agg.s_alpha_duration += sig.s_alpha_duration * w
            agg.s_included += sig.s_included * w
            agg.s_excluded += sig.s_excluded * w
            agg.s_overflow += sig.s_overflow * w
            agg.s_focus_align += sig.s_focus_align * w
            agg.s_fatigue_risk += sig.s_fatigue_risk * w

            for cat, val in sig.s_category.items():
                agg.s_category[cat] = agg.s_category.get(cat, 0) + val * w

        return agg

    def _neutral_signals(self, weights: WeightParams) -> WeightSignals:
        """변화 없는 중립 신호 (현재 가중치 유지)."""
        return WeightSignals(
            s_focus=weights.w_focus,
            s_urgent=weights.w_urgent,
            s_category=dict(weights.w_category),
            s_alpha_duration=weights.alpha_duration,
            s_included=weights.w_included,
            s_excluded=weights.w_excluded,
            s_overflow=weights.w_overflow,
            s_focus_align=weights.w_focus_align,
            s_fatigue_risk=weights.w_fatigue_risk,
            n_tasks_compared=0,
        )

    def _compute_signals(
        self, comparison: ComparisonResult, current_weights: WeightParams
    ) -> WeightSignals:
        """하루치 ComparisonResult에서 각 가중치의 목표 신호를 추출."""
        tasks = comparison.task_comparisons
        n_total = len(tasks)
        signals = WeightSignals(n_tasks_compared=n_total)

        if n_total == 0:
            return signals

        # --- Signal A: 포함/제외 불일치 ---
        ai_assigned_user_excluded = [
            t for t in tasks
            if t.ai_assignment_status == "ASSIGNED" and t.user_assignment_status == "EXCLUDED"
        ]
        ai_excluded_user_assigned = [
            t for t in tasks
            if t.ai_assignment_status == "EXCLUDED" and t.user_assignment_status == "ASSIGNED"
        ]

        over_inclusion_rate = len(ai_assigned_user_excluded) / n_total
        under_inclusion_rate = len(ai_excluded_user_assigned) / n_total

        signals.s_included = current_weights.w_included * (1.0 - over_inclusion_rate + under_inclusion_rate)
        signals.s_excluded = current_weights.w_excluded * (1.0 + over_inclusion_rate - under_inclusion_rate)

        # --- Signal B: 시간대 이동 (Focus Alignment) ---
        focus_tz = comparison.focus_time_zone
        moved_into_focus = 0
        moved_out_of_focus = 0

        for t in tasks:
            if t.ai_start_at and t.user_start_at and t.ai_start_at != t.user_start_at:
                ai_tz = _get_timezone_from_hhmm(t.ai_start_at)
                user_tz = _get_timezone_from_hhmm(t.user_start_at)
                if user_tz == focus_tz and ai_tz != focus_tz:
                    moved_into_focus += 1
                elif ai_tz == focus_tz and user_tz != focus_tz:
                    moved_out_of_focus += 1

        focus_shift = (moved_into_focus - moved_out_of_focus) / n_total
        signals.s_focus_align = current_weights.w_focus_align * (1.0 + focus_shift)

        # --- Signal C: 시간 변경 (Duration) ---
        duration_deltas = []
        for t in tasks:
            if t.ai_start_at and t.ai_end_at and t.user_start_at and t.user_end_at:
                ai_dur = _duration_minutes(t.ai_start_at, t.ai_end_at)
                user_dur = _duration_minutes(t.user_start_at, t.user_end_at)
                if ai_dur > 0:
                    duration_deltas.append((user_dur - ai_dur) / ai_dur)

        if duration_deltas:
            avg_dur_delta = sum(duration_deltas) / len(duration_deltas)
            signals.s_alpha_duration = current_weights.alpha_duration * (1.0 + avg_dur_delta * 0.5)
        else:
            signals.s_alpha_duration = current_weights.alpha_duration

        # --- Signal D: 채우기율 차이 (Overflow / Fatigue) ---
        fill_delta = comparison.user_fill_rate - comparison.ai_fill_rate
        signals.s_overflow = current_weights.w_overflow * (1.0 - fill_delta)
        signals.s_fatigue_risk = current_weights.w_fatigue_risk * (1.0 - fill_delta * 0.3)

        # --- Signal E: 카테고리 선호 ---
        cat_kept: dict[str, int] = {}
        cat_total: dict[str, int] = {}

        for t in tasks:
            cat = t.category or "기타"
            if t.ai_assignment_status == "ASSIGNED":
                cat_total[cat] = cat_total.get(cat, 0) + 1
                if t.user_assignment_status == "ASSIGNED":
                    cat_kept[cat] = cat_kept.get(cat, 0) + 1

        for cat, total in cat_total.items():
            kept = cat_kept.get(cat, 0)
            ratio = kept / total
            old_val = current_weights.w_category.get(cat, 1.0)
            signals.s_category[cat] = old_val * (0.5 + ratio)  # 0.5x ~ 1.5x

        # --- Signal F: w_focus (focus_level 기반) ---
        kept_focus_sum = 0
        removed_focus_sum = 0
        kept_count = 0
        removed_count = 0
        for t in tasks:
            fl = t.focus_level or 5
            if t.ai_assignment_status == "ASSIGNED" and t.user_assignment_status == "EXCLUDED":
                removed_focus_sum += fl
                removed_count += 1
            elif t.user_assignment_status == "ASSIGNED":
                kept_focus_sum += fl
                kept_count += 1

        if kept_count > 0 and removed_count > 0:
            avg_kept = kept_focus_sum / kept_count
            avg_removed = removed_focus_sum / removed_count
            focus_signal = (avg_kept - avg_removed) / 10.0
            signals.s_focus = current_weights.w_focus * (1.0 + focus_signal)
        else:
            signals.s_focus = current_weights.w_focus

        # --- Signal G: w_urgent (긴급 태스크 유지율) ---
        urgent_kept = sum(1 for t in tasks if t.is_urgent and t.user_assignment_status == "ASSIGNED")
        urgent_removed = sum(
            1 for t in tasks
            if t.is_urgent and t.user_assignment_status == "EXCLUDED" and t.ai_assignment_status == "ASSIGNED"
        )
        urgent_total = urgent_kept + urgent_removed
        if urgent_total > 0:
            urgent_keep_rate = urgent_kept / urgent_total
            signals.s_urgent = current_weights.w_urgent * (0.5 + urgent_keep_rate)
        else:
            signals.s_urgent = current_weights.w_urgent

        return signals

    def _apply_ema_update(
        self, current: WeightParams, signals: WeightSignals
    ) -> WeightParams:
        """EMA 스무딩 + 클리핑으로 새 가중치를 계산."""
        decay = current.ema_decay

        def ema(old: float, new_signal: float) -> float:
            return decay * old + (1 - decay) * new_signal

        def clip(val: float) -> float:
            return max(current.clip_min, min(current.clip_max, val))

        # 카테고리 가중치 업데이트
        new_category = dict(current.w_category)
        for cat, signal_val in signals.s_category.items():
            old_val = current.w_category.get(cat, 1.0)
            new_category[cat] = clip(ema(old_val, signal_val))

        return WeightParams(
            w_focus=clip(ema(current.w_focus, signals.s_focus)),
            w_urgent=clip(ema(current.w_urgent, signals.s_urgent)),
            w_category=new_category,
            alpha_duration=clip(ema(current.alpha_duration, signals.s_alpha_duration)),
            beta_load=current.beta_load,
            w_included=clip(ema(current.w_included, signals.s_included)),
            w_excluded=clip(ema(current.w_excluded, signals.s_excluded)),
            w_overflow=clip(ema(current.w_overflow, signals.s_overflow)),
            w_focus_align=clip(ema(current.w_focus_align, signals.s_focus_align)),
            w_fatigue_risk=clip(ema(current.w_fatigue_risk, signals.s_fatigue_risk)),
            # 아직 미사용 파라미터들은 그대로 보존
            w_carry_task=current.w_carry_task,
            w_carry_group=current.w_carry_group,
            w_reject_penalty=current.w_reject_penalty,
            w_switch=current.w_switch,
            w_instruction=current.w_instruction,
            instruction_cap=current.instruction_cap,
            clip_min=current.clip_min,
            clip_max=current.clip_max,
            ema_decay=current.ema_decay,
        )


# --- 헬퍼 함수 ---

def _get_timezone_from_hhmm(time_str: str) -> str:
    """HH:MM 문자열을 timezone으로 변환."""
    return get_timezone(hhmm_to_minutes(time_str))


def _duration_minutes(start: str, end: str) -> int:
    """HH:MM 두 개로 duration(분) 계산."""
    return hhmm_to_minutes(end) - hhmm_to_minutes(start)
