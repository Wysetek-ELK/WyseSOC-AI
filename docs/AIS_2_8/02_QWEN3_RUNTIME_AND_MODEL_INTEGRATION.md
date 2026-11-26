# 02 — Qwen3-14B-AWQ Runtime & Model Integration

## 1. Model Baseline & Runtime Configuration

- **Model ID:** `Qwen/Qwen3-14B-AWQ` (AWQ INT4, FP16 runtime precision)
- **Context Window:** `8192` tokens (`768` completion reserve, `7424` target input budget)
- **Timeout:** `180.0s` default (`LOCAL_LLM_TIMEOUT`), `temperature=0.0`, `top_p=1.0`, `enable_thinking=false`
- **vLLM Serve Configuration:** `--max-model-len 8192 --gpu-memory-utilization 0.90 --max-num-seqs 1 --max-num-batched-tokens 2048 --enable-chunked-prefill --default-chat-template-kwargs '{"enable_thinking": false}'`

## 2. Implemented Changes

1. Replaced hardcoded `Qwen/Qwen2.5-7B-Instruct-AWQ` defaults across `config.py`, `llm_config_service.py`, `openai_compatible.py`, `ais27_benchmark_runner.py`, `empirical_benchmark_harness.py`, `ais_evaluation_service.py`, `rule_learning_service.py`, `verdict_pipeline.py`, and frontend config UIs.
2. Added `chat_template_kwargs: {"enable_thinking": false}` injection for Qwen3 inference in `OpenAICompatibleProvider` and `AIS27BenchmarkRunner`, plus defensive `<think>...</think>` stripping during JSON extraction without modifying `raw_model_response`.
3. Extended `/api/llm/test-connection` with explicit `endpoint_reachable`, `runtime_healthy`, `configured_model_available`, `model_mismatch`, and `runtime_status_detail` checks (tested via HTTP mock in `test_ais_2_8_intelligence.py`).
4. Post-deploy check on `http://172.26.41.240/api/health` verified `local_llm.model_name = "Qwen/Qwen3-14B-AWQ"` and `current_s2_health = "ONLINE"`.
