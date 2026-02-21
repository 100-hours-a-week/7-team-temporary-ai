import asyncio
from datetime import date, datetime, timedelta
import random
from app.db.supabase_client import get_supabase_client

async def insert_test_data():
    client = get_supabase_client()
    user_id = 888888  # 두 번째 유저 (사회초년생 쇼핑몰 풀스택 직장인)
    
    # 기존 데이터 강력히 삭제 (user_id = 888888 기준)
    try:
        print("Cleaning up old test data...")
        client.table("planner_records").delete().eq("user_id", user_id).execute()
    except Exception as e:
        pass
    
    # 2026-02-21을 기준으로 과거 4주 (28일)
    base_date = date(2026, 2, 21)
    
    print(f"[{base_date}] 사회초년생(쇼핑몰 풀스택 개발자) 페르소나 데이터 삽입 시작...")
    
    for i in range(28):
        current_date = base_date - timedelta(days=27 - i) 
        weekday = current_date.weekday() # 0: Mon, 6: Sun
        is_weekend = weekday >= 5
        
        day_plan_id = 800000 + i
        created_at_dt = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=23, minutes=59)
        created_at_iso = created_at_dt.isoformat() + "Z"
        
        tasks_payload = []
        histories_payload = []
        task_id_counter = 8000000 + (i * 100)
        
        # --- 시간 배정 엔진 시뮬레이션 ---
        # 평일: 07:00 ~ 23:30, 주말: 10:00 ~ 24:00
        available_slots = [] 
        if is_weekend:
            available_slots.append((10*60, 24*60))
        else:
            available_slots.append((7*60, 23*60+30))
        
        def allocate_time(duration_min):
            nonlocal available_slots
            for idx, (s, e) in enumerate(available_slots):
                if e - s >= duration_min:
                    allocated_s = s
                    allocated_e = s + duration_min
                    available_slots.pop(idx)
                    if allocated_e < e:
                        available_slots.insert(idx, (allocated_e, e))
                    return allocated_s, allocated_e
            return None, None
            
        def allocate_fixed_time(start_min, end_min):
            nonlocal available_slots
            new_slots = []
            for s, e in available_slots:
                if end_min <= s or start_min >= e:
                    new_slots.append((s, e))
                else:
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

        # 1. 고정 일정 (FIXED): 평일 출퇴근, 중식, 데일리 스크럼
        if not is_weekend:
            # 출근 (08:00~09:00)
            c1_s, c1_e = allocate_fixed_time(8*60, 9*60)
            tasks_payload.append({
                "task_id": task_id_counter, "title": "출근", "task_type": "FIXED",
                "category": "기타", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
                "start_at": min_to_hhmm(c1_s), "end_at": min_to_hhmm(c1_e), "duration_plan_min": 60
            })
            task_id_counter += 1
            
            # 데일리 스크럼 (10:00~10:30)
            ds, de = allocate_fixed_time(10*60, 10*60+30)
            tasks_payload.append({
                "task_id": task_id_counter, "title": "개발팀 데일리 스크럼", "task_type": "FIXED",
                "category": "업무", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
                "start_at": min_to_hhmm(ds), "end_at": min_to_hhmm(de), "duration_plan_min": 30
            })
            task_id_counter += 1
            
            # 주간 회의 (월요일 14:00~15:30)
            if weekday == 0:
                ws, we = allocate_fixed_time(14*60, 15*60+30)
                tasks_payload.append({
                    "task_id": task_id_counter, "title": "전사 주간 회의", "task_type": "FIXED",
                    "category": "업무", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
                    "start_at": min_to_hhmm(ws), "end_at": min_to_hhmm(we), "duration_plan_min": 90
                })
                task_id_counter += 1

            # 점심 (12:30~13:30)
            ls, le = allocate_fixed_time(12*60+30, 13*60+30)
            tasks_payload.append({
                "task_id": task_id_counter, "title": "점심 식사 및 산책", "task_type": "FIXED",
                "category": "휴식", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
                "start_at": min_to_hhmm(ls), "end_at": min_to_hhmm(le), "duration_plan_min": 60
            })
            task_id_counter += 1
            
            # 퇴근 (18:30~19:30) - 야근이 없으면 기본 퇴근
            c2_s, c2_e = allocate_fixed_time(18*60+30, 19*60+30)
            tasks_payload.append({
                "task_id": task_id_counter, "title": "퇴근", "task_type": "FIXED",
                "category": "기타", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
                "start_at": min_to_hhmm(c2_s), "end_at": min_to_hhmm(c2_e), "duration_plan_min": 60
            })
            task_id_counter += 1
        else:
            # 주말 늦은 점심
            ls, le = allocate_fixed_time(13*60, 14*60)
            tasks_payload.append({
                "task_id": task_id_counter, "title": "주말 늦은 점심", "task_type": "FIXED",
                "category": "휴식", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
                "start_at": min_to_hhmm(ls), "end_at": min_to_hhmm(le), "duration_plan_min": 60
            })
            task_id_counter += 1

        # 4. 돌발 상황 (쇼핑몰 운영의 특수성: 20% 확률로 서버 장애, 긴급 패치 등 발생)
        # 평일에 주로 발생
        is_disrupted = (random.random() < 0.25) if not is_weekend else (random.random() < 0.05)
        
        if is_disrupted:
            if not is_weekend:
                disruption_task = random.choice([
                    ("결제 서버 연동 오류 긴급 디버깅", 180),
                    ("상품 상세 페이지 렌더링 깨짐 긴급 핫픽스", 120),
                    ("DB 슬로우 쿼리 발생으로 긴급 인덱스 튜닝", 150),
                    ("대표님의 갑작스러운 기능 추가 요청 (야근)", 180)
                ])
                ds, de = allocate_fixed_time(15*60, 15*60 + disruption_task[1])
                tasks_payload.append({
                    "task_id": task_id_counter, "title": disruption_task[0], "task_type": "FLEX", 
                    "category": "업무", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
                    "start_at": min_to_hhmm(ds), "end_at": min_to_hhmm(de), "duration_plan_min": disruption_task[1]
                })
                task_id_counter += 1
            else:
                ds, de = allocate_fixed_time(15*60, 18*60)
                tasks_payload.append({
                    "task_id": task_id_counter, "title": "갑작스러운 주말 출근 및 서버 모니터링", "task_type": "FIXED", 
                    "category": "업무", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
                    "start_at": min_to_hhmm(ds), "end_at": min_to_hhmm(de), "duration_plan_min": 180
                })
                task_id_counter += 1

        # 5. FLEX 일정 (풀스택 개발/루틴)
        if not is_weekend:
            work_tasks = [
                ("쇼핑몰 어드민 대시보드 UI/UX 작업", 120, "업무"),
                ("신규 결제 PG사 연동 백엔드 로직 작성", 150, "업무"),
                ("Legacy 코드 리팩토링 및 타입스크립트 전환", 90, "업무"),
                ("사용자 리뷰 API 속도 개선", 120, "업무"),
                ("회원가입/로그인 플로우 프론트 연동", 120, "업무"),
                ("사내 개발 스터디 (Next.js 14)", 60, "학업"),
                ("인프콘 영상 시청", 60, "학업")
            ]
            daily_flex_tasks = random.sample(work_tasks, random.randint(3, 4))
        else:
            # 주말 유동 일정
            weekend_tasks = [
                ("밀린 집안일 및 방 청소", 90, "기타"),
                ("사이드 프로젝트 (자기계발 앱) 프론트 뷰 짜기", 150, "개인프로젝트"),
                ("대학 동기들과 성수동 카페 탐방", 180, "휴식"),
                ("늦잠 자고 유튜브 숏츠 감상", 120, "휴식"),
                ("자취방 근처 코인세탁소", 60, "기타")
            ]
            daily_flex_tasks = random.sample(weekend_tasks, random.randint(2, 4))
        
        for title, duration, cat in daily_flex_tasks:
            s, e = allocate_time(duration)
            
            if s is not None and e is not None:
                # 업무 강도나 퇴근 후 지침으로 인해 할당되어도 못할 때가 있음
                status = "DONE" if random.random() > 0.15 else "TODO"
                assignment_status = "ASSIGNED"
                start_str, end_str = min_to_hhmm(s), min_to_hhmm(e)
            else:
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
            
        # 6. 통계 계산 로직
        total_flex = len([t for t in tasks_payload if t["task_type"] == "FLEX"])
        assigned_flex = len([t for t in tasks_payload if t["task_type"] == "FLEX" and t["assignment_status"] == "ASSIGNED"])
        excluded_flex = len([t for t in tasks_payload if t["task_type"] == "FLEX" and t["assignment_status"] == "EXCLUDED"])
        
        assigned_flex_duration = sum(t["duration_plan_min"] for t in tasks_payload if t["assignment_status"] == "ASSIGNED" and t["task_type"] == "FLEX")
        total_available_minutes = 16.5 * 60 if not is_weekend else 14 * 60
        fill_rate = min(1.0, assigned_flex_duration / total_available_minutes) if total_available_minutes > 0 else 0
        fill_rate = round(fill_rate, 4)

        record_payload = {
            "user_id": user_id,
            "day_plan_id": day_plan_id,
            "record_type": "USER_FINAL",
            "start_arrange": "07:00" if not is_weekend else "10:00",
            "day_end_time": "23:30" if not is_weekend else "24:00",
            "focus_time_zone": "AFTERNOON" if not is_weekend else "EVENING",
            "user_age": 26,             # 사회초년생 나이
            "user_gender": "FEMALE",    # 다양한 인구통계 테스트
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
            
            if histories_payload:
                for h in histories_payload:
                    h["record_id"] = record_id
                client.table("schedule_histories").insert(histories_payload).execute()
            
            disrupt_text = "⚠️ 긴급 장애/야근 발생!" if is_disrupted else "무난한 하루"
            weekend_txt = " (주말)" if is_weekend else " (평일)"
            print(f"[{current_date.strftime('%Y-%m-%d')}]{weekend_txt} 삽입 완료 (FLEX_TOTAL: {total_flex}) - {disrupt_text}")
            
        except Exception as e:
            print(f"Error inserting data for {current_date}: {e}")

    print("\n[성공] 사회초년생(쇼핑몰 풀스택 개발자) 페르소나 데이터 재생성 및 DB 삽입 완료!")

if __name__ == "__main__":
    asyncio.run(insert_test_data())
