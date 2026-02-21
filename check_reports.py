import asyncio
import os
from app.db.supabase_client import get_supabase_client

async def check_generated_reports():
    client = get_supabase_client()
    user_ids = [999999, 888888, 777777]
    
    print("Checking weekly_reports table for generated reports...")
    
    try:
        response = client.table("weekly_reports").select("*").in_("user_id", user_ids).execute()
        
        if not response.data:
            print("No reports found yet. The background task might still be running.")
            return

        print(f"Found {len(response.data)} reports!\n")
        
        for record in response.data:
            print("="*60)
            print(f"USER ID: {record['user_id']} | REPORT_ID: {record['report_id']}")
            print(f"BASE DATE: {record['base_date']}")
            print("-" * 60)
            print("CONTENT PREVIEW (First 500 chars):")
            print(record['content'][:500] + "..." if len(record['content']) > 500 else record['content'])
            print("="*60 + "\n")
            
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    asyncio.run(check_generated_reports())
