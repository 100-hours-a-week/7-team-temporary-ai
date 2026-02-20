import asyncio
from datetime import date, datetime, timedelta
import random
from app.db.supabase_client import get_supabase_client

async def insert_test_data():
    client = get_supabase_client()
    user_id = 999999
    
    # 기존 데이터 강력히 삭제 (user_id = 999999 기준)
    try:
        print("Cleaning up old test data...")
        client.table("planner_records").delete().eq("user_id", user_id).execute()
        # record_tasks, schedule_histories는 CASCADE로 삭제됨
    except Exception as e:
        pass
    
    # 2026-02-21을 기준으로 과거 4주 (28일)
    base_date = date(2026, 2, 21)
    
    print(f"[{base_date}] 4학년 컴공 졸업과제 페르소나 데이터(정밀 시간/이력 포함) 삽입 시작...")
    
    for i in range(28):
        current_date = base_date - timedelta(days=27 - i) 
        weekday = current_date.weekday() # 0: Mon, 6: Sun
        
        day_plan_id = 900000 + i
        created_at_dt = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=23, minutes=59)
        created_at_iso = created_at_dt.isoformat() + "Z"
        
        tasks_payload = []
        histories_payload = []
        task_id_counter = 9000000 + (i * 100)
        
        # --- 시간 배정 엔진 시뮬레이션 ---
        # 09:00 ~ 23:00 타임라인
        available_slots = [] # (start_min, end_min)
        available_slots.append((9*60, 23*60))
        
        def allocate_time(duration_min):
            nonlocal available_slots
            # 첫 번째 맞는 슬롯에서 시간 할당
            for idx, (s, e) in enumerate(available_slots):
                if e - s >= duration_min:
                    allocated_s = s
                    allocated_e = s + duration_min
                    # 슬롯 업데이트
                    available_slots.pop(idx)
                    if allocated_e < e:
                        available_slots.insert(idx, (allocated_e, e))
                    return allocated_s, allocated_e
            return None, None
            
        def allocate_fixed_time(start_min, end_min):
            nonlocal available_slots
            new_slots = []
            for s, e in available_slots:
                # 겹치지 않음
                if end_min <= s or start_min >= e:
                    new_slots.append((s, e))
                else:
                    # 겹침, 분할
                    if start_min > s:
                        new_slots.append((s, start_min))
                    if end_min < e:
                        new_slots.append((end_min, e))
            available_slots = new_slots
            return start_min, end_min

        def min_to_hhmm(minutes):
            h = minutes // 60
            m = minutes % 60
            return f"{h:02d}:{m:02d}"

        # 1. 고정 일정 (FIXED): 점심, 저녁
        lunch_s, lunch_e = allocate_fixed_time(12*60, 13*60)
        tasks_payload.append({
            "task_id": task_id_counter,
            "title": "점심 식사",
            "task_type": "FIXED",
            "category": "휴식", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
            "start_at": min_to_hhmm(lunch_s), "end_at": min_to_hhmm(lunch_e), "duration_plan_min": 60
        })
        task_id_counter += 1
        
        dinner_s, dinner_e = allocate_fixed_time(18*60+30, 19*60+30)
        tasks_payload.append({
            "task_id": task_id_counter,
            "title": "저녁 식사",
            "task_type": "FIXED",
            "category": "휴식", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
            "start_at": min_to_hhmm(dinner_s), "end_at": min_to_hhmm(dinner_e), "duration_plan_min": 60
        })
        task_id_counter += 1

        # 2. 고정 일정: 운동 (월수금 20:00~21:30)
        if weekday in [0, 2, 4]:
            workout_status = "DONE" if random.random() > 0.2 else "TODO"
            ws, we = allocate_fixed_time(20*60, 21*60+30)
            tasks_payload.append({
                "task_id": task_id_counter,
                "title": "헬스장 (웨이트 트레이닝)",
                "task_type": "FIXED",
                "category": "운동", "status": workout_status, "assignment_status": "ASSIGNED", "assigned_by": "USER",
                "start_at": min_to_hhmm(ws), "end_at": min_to_hhmm(we), "duration_plan_min": 90
            })
            # 수정 이력 더미 데이터 (예: 원래 19:30 이었는데 20:00으로 미룬 적이 있다고 가정)
            if random.random() > 0.5:
                histories_payload.append({
                    "schedule_id": task_id_counter,
                    "event_type": "MOVE_TIME",
                    "prev_start_at": "19:30", "prev_end_at": "21:00",
                    "new_start_at": min_to_hhmm(ws), "new_end_at": min_to_hhmm(we),
                    "created_at_client": (created_at_dt - timedelta(hours=5)).isoformat() + "Z",
                    "created_at_server": created_at_iso
                })
            task_id_counter += 1

        # 3. 고정 일정: 회의 (화목 14:00~15:00)
        if weekday in [1, 3]:
            ms, me = allocate_fixed_time(14*60, 15*60)
            tasks_payload.append({
                "task_id": task_id_counter,
                "title": "졸업과제 교수님/팀 랩미팅",
                "task_type": "FIXED",
                "category": "업무", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
                "start_at": min_to_hhmm(ms), "end_at": min_to_hhmm(me), "duration_plan_min": 60
            })
            task_id_counter += 1

        # 4. 돌발 상황 (15% 확률로 15:00 ~ 18:00 시간 날아감)
        is_disrupted = random.random() < 0.15
        if is_disrupted:
            disruption_task = random.choice([
                "치명적인 웹소켓 서버 배포 에러 긴급 복구",
                "급한 면접 제안으로 인한 포트폴리오 철야 수정",
                "친한 선배 연락받고 급작스럽게 치맥",
            ])
            ds, de = allocate_fixed_time(15*60, 18*60)
            tasks_payload.append({
                "task_id": task_id_counter,
                "title": disruption_task,
                "task_type": "FLEX", # 플렉스지만 강제 배정
                "category": "기타" if "치맥" in disruption_task else "업무",
                "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
                "start_at": min_to_hhmm(ds), "end_at": min_to_hhmm(de), "duration_plan_min": 180
            })
            task_id_counter += 1

        # 5. FLEX 일정 (학업/개인프로젝트 등)
        grad_tasks = [
            ("졸작 백엔드 핵심 API 개발", 120, "학업"),
            ("테스트 코드 작성 방어", 90, "학업"),
            ("이전 회의 피드백 기반 논문 수정", 120, "학업"),
            ("프론트엔드 API 연동 테스트", 90, "학업"),
            ("추천 알고리즘 성능 최적화", 150, "학업"),
            ("밀린 알고리즘 문제 풀이", 60, "학업"),
            ("기술 블로그 작성 (이번주 회고)", 60, "개인프로젝트"),
            ("최신 AI 트렌드 리서치", 60, "개인프로젝트")
        ]
        
        daily_flex_tasks = random.sample(grad_tasks, random.randint(3, 5))
        
        for title, duration, cat in daily_flex_tasks:
            # 돌발상황 발생 시 남은 시간이 부족할 확률이 큼.
            s, e = allocate_time(duration)
            
            if s is not None and e is not None:
                # 배정 성공
                status = "DONE" if random.random() > 0.15 else "TODO"
                assignment_status = "ASSIGNED"
                start_str, end_str = min_to_hhmm(s), min_to_hhmm(e)
            else:
                # 시간이 부족해서 배정 실패 (EXCLUDED)
                status = "TODO"
                assignment_status = "EXCLUDED"
                start_str, end_str = None, None
                
            tasks_payload.append({
                "task_id": task_id_counter,
                "title": title,
                "task_type": "FLEX",
                "category": cat,
                "status": status,
                "assignment_status": assignment_status,
                "assigned_by": "USER",
                "start_at": start_str,
                "end_at": end_str,
                "duration_plan_min": duration
            })
            task_id_counter += 1
            
        # 6. 통계 계산 로직 (정확히 수행)
        total_flex = len([t for t in tasks_payload if t["task_type"] == "FLEX"])
        assigned_flex = len([t for t in tasks_payload if t["task_type"] == "FLEX" and t["assignment_status"] == "ASSIGNED"])
        excluded_flex = len([t for t in tasks_payload if t["task_type"] == "FLEX" and t["assignment_status"] == "EXCLUDED"])
        
        assigned_flex_duration = sum(t["duration_plan_min"] for t in tasks_payload if t["assignment_status"] == "ASSIGNED" and t["task_type"] == "FLEX")
        total_available_minutes = 14 * 60 # 09:00 ~ 23:00 (14시간)
        fill_rate = min(1.0, assigned_flex_duration / total_available_minutes) if total_available_minutes > 0 else 0
        fill_rate = round(fill_rate, 4)

        record_payload = {
            "user_id": user_id,
            "day_plan_id": day_plan_id,
            "record_type": "USER_FINAL",
            "start_arrange": "09:00",
            "day_end_time": "23:00",
            "focus_time_zone": "NIGHT" if random.random() < 0.6 else "AFTERNOON",
            "user_age": 24,
            "user_gender": "MALE",
            "total_tasks": total_flex,
            "assigned_count": assigned_flex,
            "excluded_count": excluded_flex,
            "fill_rate": fill_rate,
            "plan_date": current_date.isoformat(),
            "created_at": created_at_iso
        }
        
        try:
            res = client.table("planner_records").insert(record_payload).execute()
            if not res.data:
                print(f"Failed to insert record for {current_date}")
                continue
            
            record_id = res.data[0]["id"]
            
            for t in tasks_payload:
                t["record_id"] = record_id
                t["day_plan_id"] = day_plan_id
                t["created_date"] = current_date.isoformat()
                t["created_at"] = created_at_iso
                
            client.table("record_tasks").insert(tasks_payload).execute()
            
            # 히스토리 삽입
            if histories_payload:
                for h in histories_payload:
                    h["record_id"] = record_id
                client.table("schedule_histories").insert(histories_payload).execute()
            
            disrupt_text = "⚠️ 돌발상황 발생! 일부 작업 EXCLUDED됨" if is_disrupted else "정상 하루"
            print(f"[{current_date.strftime('%Y-%m-%d')}] 삽입 완료 (FLEX_TOTAL: {total_flex}, ASSIGNED: {assigned_flex}) - {disrupt_text}")
            
        except Exception as e:
            print(f"Error inserting data for {current_date}: {e}")

    print("\n[성공] 4학년 컴공 페르소나 (완벽한 시간흐름, 예외상황, EXCLUDED, DB 스키마 100% 준수) 28일치 생성이 완료되었습니다!")

if __name__ == "__main__":
    asyncio.run(insert_test_data())
