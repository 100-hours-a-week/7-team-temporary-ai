import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import types

from app.services.embedding_service import sync_task_embeddings


@pytest.fixture
def mock_supabase():
    with patch("app.services.embedding_service.get_supabase_client") as mock:
        yield mock


@pytest.fixture
def mock_gemini():
    with patch("app.services.embedding_service.get_gemini_client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_sync_task_embeddings_no_records(mock_supabase, mock_gemini):
    # Mock planner_records query to return empty data
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client
    
    # Mock the execute() chain for planner_records
    mock_response = MagicMock()
    mock_response.data = []
    mock_client.table().select().eq().gte().lte().execute.return_value = mock_response

    await sync_task_embeddings()

    # The record_tasks table should not be queried
    mock_client.table().select().in_().eq().is_().execute.assert_not_called()


@pytest.mark.asyncio
async def test_sync_task_embeddings_no_tasks(mock_supabase, mock_gemini):
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client
    
    # Mock planner_records to return 1 record
    mock_record_response = MagicMock()
    mock_record_response.data = [{"id": 1}]
    mock_client.table().select().eq().gte().lte().execute.return_value = mock_record_response
    
    # Mock record_tasks query to return empty data
    mock_task_response = MagicMock()
    mock_task_response.data = []
    
    # The chain: table("record_tasks").select().in_().eq().is_().execute()
    mock_client.table("record_tasks").select().in_().eq().is_().execute.return_value = mock_task_response

    await sync_task_embeddings()
    
    # Vector update should not be called
    mock_client.table().update().eq().execute.assert_not_called()


@pytest.mark.asyncio
async def test_sync_task_embeddings_success(mock_supabase, mock_gemini):
    mock_client = MagicMock()
    mock_supabase.return_value = mock_client
    
    # 1. Mock planner_records
    mock_record_response = MagicMock()
    mock_record_response.data = [{"id": 100}]
    mock_client.table().select().eq().gte().lte().execute.return_value = mock_record_response
    
    # 2. Mock record_tasks return
    mock_task_response = MagicMock()
    mock_task_response.data = [
        {"id": 1001, "title": "Implement embedding schedule"},
        {"id": 1002, "title": "Write unit tests"}
    ]
    mock_client.table("record_tasks").select().in_().eq().is_().execute.return_value = mock_task_response
    
    # 3. Mock Gemini Client
    mock_gemini_instance = MagicMock()
    mock_gemini.return_value = mock_gemini_instance
    
    # Mock embed_content response
    mock_embed_result = MagicMock()
    mock_embedding1 = MagicMock()
    mock_embedding1.values = [0.1, 0.2, 0.3]
    mock_embed_result.embeddings = [mock_embedding1]
    
    mock_gemini_instance.client.models.embed_content.return_value = mock_embed_result
    
    # 4. Mock the Update table chain
    mock_update_chain = MagicMock()
    mock_client.table("record_tasks").update.return_value = mock_update_chain
    mock_update_chain.eq.return_value = mock_update_chain

    # Mock asyncio.sleep so the test runs fast without waiting
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await sync_task_embeddings()

    # Gemini client should be called twice (for the two tasks)
    assert mock_gemini_instance.client.models.embed_content.call_count == 2
    
    # DB update should be called twice
    assert mock_client.table("record_tasks").update.call_count == 2
    
    # Verify the specific update arguments for the first call
    mock_client.table("record_tasks").update.assert_any_call({"combined_embedding_text": [0.1, 0.2, 0.3]})
    mock_update_chain.eq.assert_any_call("id", 1001)
    mock_update_chain.eq.assert_any_call("id", 1002)
    assert mock_update_chain.execute.call_count == 2
