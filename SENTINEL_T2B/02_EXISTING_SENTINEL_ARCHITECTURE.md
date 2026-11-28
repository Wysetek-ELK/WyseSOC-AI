# 02 — Existing & Updated Sentinel Architecture

## Request–Response Path

```
Frontend Chat UI (frontend/src/app/soc-chatbot/page.tsx)
  └─> Frontend API Client (frontend/src/lib/api.ts :: streamChatMessage / continueChatMessage)
        └─> Next.js Rewrite Proxy (frontend/next.config.ts :: /api/* -> 127.0.0.1:8000, proxyTimeout: 600s)
              └─> Nginx Reverse Proxy (deployment/nginx/ai-verdict.conf :: proxy_read_timeout: 300s, proxy_buffering: off)
                    └─> FastAPI Chat Router (backend/app/api/chat.py)
                          ├─> Auth & Owner Isolation (backend/app/api/deps.py :: get_current_user)
                          ├─> Context-Aware Budget (backend/app/services/sentinel_token_budget.py)
                          │     └─> vLLM /tokenize API or ModelTokenizerService
                          ├─> Concurrency & Circuit Breaker (backend/app/services/gpu_manager.py)
                          ├─> Persistence (backend/app/models/chat.py :: sentinel_conversations / sentinel_messages)
                          └─> vLLM Server 2 (http://13.204.214.64:8000/v1/chat/completions)
                                └─> SSE Stream (stream_options.include_usage=True, 10s keepalive, finish_reason capture)
```

## Key Components Identified
- **Frontend UI**: `frontend/src/app/soc-chatbot/page.tsx`
- **Frontend API Client**: `frontend/src/lib/api.ts`
- **Backend Chat Router**: `backend/app/api/chat.py`
- **Token Budget & Tokenizer**: `backend/app/services/sentinel_token_budget.py`, `backend/app/services/tokenizer_service.py`
- **Persistence Models & Migration**: `backend/app/models/chat.py`, `backend/alembic/versions/019_sentinel_chat_persistence.py`
- **Configuration**: `backend/app/config.py`, `backend/app/services/llm_config_service.py`
