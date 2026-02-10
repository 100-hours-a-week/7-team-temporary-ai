# 개인화 데이터 DB 적재 구현 가이드

이 문서는 백엔드 서버가 **AI 데이터베이스에 사용자 플래너 데이터를 적재하는 전체 과정**을 **순서대로** 상세히 설명합니다.

백엔드 개발자는 아래의 **Step 1 ~ Step 4** 흐름을 그대로 구현하면 됩니다.

---

## **[Step 0] 데이터 준비**
적재를 시작하기 전에, 백엔드는 특정 사용자의 **완료된 하루 플래너**와 관련된 모든 데이터를 메모리에 로드해야 합니다.

*   **준비 데이터**:
    1.  `User` 정보 (나이, 성별, 몰입 시간대 등)
    2.  `Schedule` 목록 (해당 날짜의 모든 플래너 일정)
    3.  `ScheduleHistory` 목록 (해당 일정들에 대한 수정 이력)

> **주의**: 적재 대상은 **사용자가 최종 수정한 데이터(USER_FINAL)** 여야 합니다. (AI가 제안만 했던 데이터는 적재하지 않음)

---

## **[Step 1] `planner_records` 데이터 생성 및 적재**

가장 먼저 각 날짜별 플래너의 **요약 정보(Header)**를 생성하고 저장해야 합니다. 이 과정에서 **`record_id` (PK)** 를 생성하는 것이 핵심입니다.

### 1-1. 데이터 준비
- `user_id`: 사용자 ID
- `day_plan_id`: 사용자 플래너 ID
- `record_type`: 'USER_FINAL' (고정)
- `start_arrange`: 사용자 플래너 시작 시간 (HH:MM 형태)
- `day_end_time`: 사용자 플래너 종료 시간 (HH:MM 형태)
- `focus_time_zone`: 사용자 플래너 몰입 시간대 (MORNING / AFTERNOON / EVENING / NIGHT)
- `user_age`: 사용자 나이
- `user_gender`: 사용자 성별 (MALE / FEMALE)  
- `created_at`: 생성 시간 (ISO 8601) (`NOW()` SQL문으로 처리)

### 1-2. 통계 데이터 계산
`Schedule` 목록을 순회하며 다음 값을 계산합니다. (메모리상에서 계산)
*   **`total_tasks`**: `type="FLEX"`인 작업의 개수
*   **`assigned_count`**: `assignmentStatus="ASSIGNED"`인 작업의 개수
*   **`excluded_count`**: `assignmentStatus="EXCLUDED"`인 작업의 개수
*   **`fill_rate` (가동률)**:
    *   `총 가용 시간(분)` = `00:00` ~ `Users.dayEndTime`까지의 분
    *   `총 작업 시간(분)` = `ASSIGNED`된 작업들의 (`endAt` - `startAt`) 합계
    *   `fill_rate` = `총 작업 시간` / `총 가용 시간` (소수점 4자리 반올림)

### 1-3. DB Insert & ID 반환 (RETURNING id)
계산된 데이터를 `planner_records` 테이블에 INSERT하고, **생성된 PK(`id`)를 반환**받습니다.

```sql
INSERT INTO planner_records (
    user_id, day_plan_id, record_type, start_arrange, day_end_time,
    focus_time_zone, user_age, user_gender,
    total_tasks, assigned_count, excluded_count, fill_rate, created_at
) VALUES (
    101, 505, 'USER_FINAL', '09:00', '23:00',
    'MORNING', 25, 'MALE',
    5, 4, 1, 0.45, NOW()
)
RETURNING id;
```

- **결과**: `id` = **1001** (예시)  
    - ※ 이 **1001** 값을 변수(`record_id`)에 저장해두세요. 다음 단계에서 필수적으로 사용됩니다.

### 1-4. (심화) 다수 데이터 일괄 적재 (Bulk Insert)
여러 날짜의 플래너 데이터를 한 번에 적재해야 할 경우, `VALUES`에 여러 행을 나열하여 **Bulk Insert**를 수행할 수 있습니다.

```sql
INSERT INTO planner_records (...)
VALUES 
    (101, 505, ...),  -- 첫 번째 플래너
    (101, 506, ...)   -- 두 번째 플래너
RETURNING id;
```

> **⚠️ [중요] ID 매핑 주의사항**
> *   `RETURNING id`는 **입력된 순서(VALUES절의 순서)** 그대로 ID 리스트를 반환합니다.
> *   예: `[PlanA, PlanB]` 순서로 입력했다면, 반환된 ID도 `[IdA, IdB]` 순서입니다.
> *   애플리케이션에서는 이 순서를 보장하여 **반환된 ID를 각 원본 데이터와 정확히 매핑**해야 합니다. (Step 2에서 올바른 외래키 연결을 위해 필수)

---

## **[Step 2] `record_tasks` 데이터 매핑 및 적재**

이제 각 플래너의 개별 일정(Detail)을 저장합니다. **Step 1에서 얻은 `record_id` (1001)** 를 외래키로 사용합니다.

### 2-1. 데이터 매핑
보유한 `Schedule` 리스트를 반복문으로 순회하며 DB 행(Row) 데이터를 생성합니다.

*   **`record_id`**: **1001** (Step 1의 결과값)
*   `task_id`: `Schedule.taskId`
*   `day_plan_id`: `Schedule.dayPlanId`
*   `title`: `Schedule.title`
*   `status`: `Schedule.status` (TODO / DONE)
*   `parent_schedule_id`: `Schedule.parentScheduleId`
*   `task_type`: `Schedule.type` (FIXED / FLEX)
*   `assigned_by`: `Schedule.assignedBy` (USER / AI)
*   `assignment_status`: `Schedule.assignmentStatus` (ASSIGNED / NOT_ASSIGNED / EXCLUDED)
*   `start_at` / `end_at`: "HH:MM" 또는 NULL 허용
*   `created_at`: 생성 시간 (ISO 8601) (`NOW()` SQL문으로 처리)

### 2-2. Bulk Insert (일괄 저장)
대량의 데이터를 효율적으로 저장하기 위해 Bulk Insert를 권장합니다.

```sql
INSERT INTO record_tasks (
    record_id, task_id, day_plan_id, title, status, parent_schedule_id, task_type, assigned_by, assignment_status, start_at, end_at, created_at
) VALUES
    (1001, 10, 505, '영어 공부', 'DONE', 100, 'FIXED', 'USER', 'ASSIGNED', '09:00', '10:00', NOW()),
    (1001, 11, 505, '운동', ...),
    (1022, 54, 124, ...);
```

---

## **[Step 3] `schedule_histories` 데이터 매핑 및 적재**

마지막으로, 사용자의 수정 이력을 저장합니다. 마찬가지로 **Step 1의 `record_id` (1001)** 를 사용합니다.

### 3-1. 데이터 매핑
보유한 `ScheduleHistory` 리스트를 순회합니다.

*   **`record_id`**: **1001** (Step 1의 결과값)
*   `schedule_id`: `ScheduleHistory.scheduleId`
*   `event_type`: `ScheduleHistory.eventType` (ASSIGN_TIME / MOVE_TIME / CHANGE_DURATION)
*   `prev_start_at`, `prev_end_at`: 변경 전 시간
*   `new_start_at`, `new_end_at`: 변경 후 시간
*   `created_at_client`: `ScheduleHistory.createdAt` (사용자 행위 시각) (이것은 플래너 수정 시간대를 정렬하기 위해서 필요함)
*   `created_at_server`: 생성 시간 (ISO 8601) (`NOW()` SQL문으로 처리)

### 3-2. Bulk Insert (일괄 저장)
이력이 없다면 이 단계는 생략합니다.

```sql
INSERT INTO schedule_histories (
    record_id, schedule_id, event_type, prev_start_at, prev_end_at, new_start_at, new_end_at, created_at_client, created_at_server
) VALUES
    (1001, 10, 'MOVE_TIME', '13:00', '14:00', '14:00', '15:00', '2026-01-10T19:10:40.456789', NOW()),
    (1001, 10, 'CHANGE_DURATION', '14:00', '15:00', '14:00', '16:00', '2026-01-22T19:18:05.987654', NOW());
```

---

## **[Step 4] 트랜잭션 커밋 (완료)**

위 모든 과정(Step 1 ~ Step 3)이 에러 없이 완료되면 트랜잭션을 **Commit** 하여 저장을 확정합니다.
만약 중간에 에러가 발생하면 전체를 **Rollback** 해야 데이터 정합성이 유지됩니다.
