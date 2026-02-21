import asyncio
from datetime import date, datetime, timedelta
import random
from app.db.supabase_client import get_supabase_client

async def insert_test_data():
    client = get_supabase_client()
    user_id = 777777  # 세 번째 유저 (회계사 준비생)
    
    # 기존 데이터 강력히 삭제 (user_id = 777777 기준)
    try:
        print("Cleaning up old test data...")
        client.table("planner_records").delete().eq("user_id", user_id).execute()
    except Exception as e:
        pass
    
    # 2026-02-21을 기준으로 과거 4주 (28일)
    base_date = date(2026, 2, 21)
    
    print(f"[{base_date}] 회계사 준비생(하루종일 공부) 페르소나 데이터 삽입 시작...")
    
    for i in range(28):
        current_date = base_date - timedelta(days=27 - i) 
        
        day_plan_id = 700000 + i
        created_at_dt = datetime.combine(current_date, datetime.min.time()) + timedelta(hours=23, minutes=59)
        created_at_iso = created_at_dt.isoformat() + "Z"
        
        tasks_payload = []
        histories_payload = []
        task_id_counter = 7000000 + (i * 100)
        
        # --- 시간 배정 엔진 시뮬레이션 ---
        # 매일 07:00 ~ 23:30 (휴일 없음)
        available_slots = [(7*60, 23*60+30)]
        
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

        # 1. 고정 일정 (FIXED): 기상/아침, 점심, 저녁 (운동 없음)
        bs, be = allocate_fixed_time(7*60, 8*60)
        tasks_payload.append({
            "task_id": task_id_counter, "title": "기상 및 아침 식사", "task_type": "FIXED",
            "category": "휴식", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
            "start_at": min_to_hhmm(bs), "end_at": min_to_hhmm(be), "duration_plan_min": 60
        })
        task_id_counter += 1
        
        ls, le = allocate_fixed_time(12*60, 13*60)
        tasks_payload.append({
            "task_id": task_id_counter, "title": "점심 식사 및 휴식", "task_type": "FIXED",
            "category": "휴식", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
            "start_at": min_to_hhmm(ls), "end_at": min_to_hhmm(le), "duration_plan_min": 60
        })
        task_id_counter += 1

        ds, de = allocate_fixed_time(18*60, 19*60)
        tasks_payload.append({
            "task_id": task_id_counter, "title": "저녁 식사", "task_type": "FIXED",
            "category": "휴식", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
            "start_at": min_to_hhmm(ds), "end_at": min_to_hhmm(de), "duration_plan_min": 60
        })
        task_id_counter += 1

        # 2. 돌발 상황 (고시생의 아주 가끔 있는 멘탈 붕괴나 경조사, 아픔: 5% 확률)
        is_disrupted = random.random() < 0.05
        
        if is_disrupted:
            disruption_task = random.choice([
                ("독몸살 감기로 인한 병원 진료 및 수액", 240),
                ("슬럼프(번아웃) 와서 하루종일 침대에서 유튜브", 300),
                ("가족 필수 경조사 참석", 360)
            ])
            # 돌발상황은 점심 직후에 주로 발생한다고 가정
            ds_slot, de_slot = allocate_fixed_time(13*60, 13*60 + disruption_task[1])
            tasks_payload.append({
                "task_id": task_id_counter, "title": disruption_task[0], "task_type": "FLEX", 
                "category": "기타", "status": "DONE", "assignment_status": "ASSIGNED", "assigned_by": "USER",
                "start_at": min_to_hhmm(ds_slot), "end_at": min_to_hhmm(de_slot), "duration_plan_min": disruption_task[1]
            })
            task_id_counter += 1

        # 3. FLEX 일정 (오로지 공부)
        study_tasks = [
            ("재무회계 인강 3강 수강", 180, "학업"),
            ("원가관리회계 연습서 풀이", 150, "학업"),
            ("세법 객관식 100문제 풀고 오답정리", 240, "학업"),
            ("재무관리 기출문제 모의고사", 120, "학업"),
            ("회계감사 기준서 통암기", 150, "학업"),
            ("경제학 미시/거시 복습", 180, "학업"),
            ("상법 조문 백지 복습", 120, "학업"),
            ("세무회계 종합문제 풀이", 210, "학업")
        ]
        
        # 고독하게 하루에 3~4개의 굵직한 과목 교차 수강 (순공 시간 10시간~12시간 목표)
        daily_flex_tasks = random.sample(study_tasks, random.randint(3, 4))
        
        for title, duration, cat in daily_flex_tasks:
            s, e = allocate_time(duration)
            
            if s is not None and e is not None:
                # 합격에 대한 굳은 의지로 대부분 완수함. 하지만 번아웃일때는 실패
                status = "TODO" if is_disrupted else ("DONE" if random.random() > 0.1 else "TODO")
                assignment_status = "ASSIGNED"
                start_str, end_str = min_to_hhmm(s), min_to_hhmm(e)
            else:
                # 시간이 부족해서 배정 실패 (너무 무리하게 계획을 세운 경우)
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
            
        # 4. 통계 계산 로직
        total_flex = len([t for t in tasks_payload if t["task_type"] == "FLEX"])
        assigned_flex = len([t for t in tasks_payload if t["task_type"] == "FLEX" and t["assignment_status"] == "ASSIGNED"])
        excluded_flex = total_flex - assigned_flex
        
        assigned_flex_duration = sum(t["duration_plan_min"] for t in tasks_payload if t["assignment_status"] == "ASSIGNED" and t["task_type"] == "FLEX")
        total_available_minutes = 16.5 * 60 # 07:00 ~ 23:30 (16.5시간)
        fill_rate = min(1.0, assigned_flex_duration / total_available_minutes) if total_available_minutes > 0 else 0
        fill_rate = round(fill_rate, 4)

        record_payload = {
            "user_id": user_id,
            "day_plan_id": day_plan_id,
            "record_type": "USER_FINAL",
            "start_arrange": "07:00",
            "day_end_time": "23:30",
            "focus_time_zone": "MORNING" if random.random() < 0.5 else "AFTERNOON",
            "user_age": 27,             # 고시 준비생 나이
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
            
            if histories_payload:
                for h in histories_payload:
                    h["record_id"] = record_id
                client.table("schedule_histories").insert(histories_payload).execute()
            
            disrupt_text = "🚨 집중력 붕괴/변수 발생!" if is_disrupted else "🔥 순공 10시간 달성!"
            print(f"[{current_date.strftime('%Y-%m-%d')}] 삽입 완료 (공부 과목수: {total_flex}) - {disrupt_text}")
            
        except Exception as e:
            print(f"Error inserting data for {current_date}: {e}")

    print("\n[성공] 회계사 준비생(하루종일 공부만 하는 고시생) 페르소나 데이터 DB 삽입 완료!")

if __name__ == "__main__":
    asyncio.run(insert_test_data())
