# Batch Processor Enhancement Plan

## Overview
Enhance the EE Toolbox ingestion pipeline to handle 1,000+ items reliably with progress tracking, error handling, resumability, rate limiting, controlled concurrency, and reporting.

## Architecture

### New Files
1. **`pipeline/batch_processor.py`** — Core batch processing engine with all 6 features
2. **`pipeline/run_batch.py`** — CLI runner with argparse
3. **`pipeline/test_batch_processor.py`** — Integration test demonstrating all features

### State Files (created at runtime)
- **`pipeline/progress.json`** — Real-time progress (JSON, updated every item)
- **`pipeline/batch_state.json`** — Resumability state (tracks processed item IDs)
- **`pipeline/batch_report.json`** — Final summary report after completion

## Detailed Design

### 1. BatchProcessor Class

```python
class BatchProcessor:
    def __init__(self, config: BatchConfig):
        ...
    
    def process_batch(self, items: list[dict], resume: bool = False) -> BatchReport:
        """Main entry point. Processes items with all features enabled."""
        ...
```

#### BatchConfig (dataclass):
- `batch_id`: str — unique identifier for this batch run (default: timestamp-based)
- `max_retries`: int = 3
- `retry_base_delay`: float = 2.0 (seconds, for exponential backoff)
- `llm_delay`: float = 1.0 (seconds between LLM calls)
- `embedding_delay`: float = 0.2 (seconds between embedding calls)
- `llm_concurrency`: int = 1 (sequential by default, max 3)
- `embedding_concurrency`: int = 5 (can batch/parallelize)
- `model`: str = DEFAULT_MODEL
- `mock_mode`: bool = False (skip actual LLM/embedding calls)
- `state_dir`: str = "pipeline/" (where to write state files)
- `progress_file`: str = "pipeline/progress.json"
- `state_file`: str = "pipeline/batch_state.json"

### 2. Progress Tracking
- Write `progress.json` after every item completes
- Format:
```json
{
  "batch_id": "batch-20260526-143000",
  "status": "running",
  "started_at": "2026-05-26T14:30:00",
  "updated_at": "2026-05-26T14:35:23",
  "total": 1000,
  "processed": 150,
  "stored": 120,
  "skipped": 20,
  "failed": 10,
  "percent_complete": 15.0,
  "avg_latency_ms": 32000,
  "estimated_remaining_seconds": 850,
  "current_item": "Title of item being processed",
  "items_per_minute": 1.8
}
```

### 3. Error Handling with Retry
- Wrap each stage (classify, extract, embed, store) with retry logic
- Exponential backoff: delay * 2^attempt (2s, 4s, 8s for 3 retries)
- Catch specific exceptions:
  - subprocess.TimeoutExpired → retry
  - JSON parse error → retry (LLM may give better output)
  - openai.RateLimitError → retry with longer backoff
  - psycopg2 connection errors → retry
- Track retry counts per item and per stage in the report

### 4. Resumability
- `batch_state.json` tracks:
  - `processed_ids`: set of cgspace_ids already processed
  - `results`: dict mapping cgspace_id → status
- On resume: load state, skip items whose cgspace_id is in processed_ids
- Each item's result is flushed to state immediately after processing
- Use `_derive_cgspace_id()` from ingest.py to compute the ID

### 5. Rate Limiting
- Simple token-bucket approach: track last LLM call time, sleep if needed
- `llm_delay` between Claude CLI calls (default 1s)
- `embedding_delay` between OpenAI calls (default 0.2s)
- Configurable via CLI flags

### 6. Concurrent Processing
- Use `concurrent.futures.ThreadPoolExecutor` for embeddings
- LLM calls: sequential or limited concurrency (1-3 workers)
- Pipeline stages for each item remain sequential (classify → extract → embed → store)
- But multiple items can be processed in parallel with limited workers
- Thread-safe progress/state file writes using a lock

### 7. Mock Mode
- When `mock_mode=True`:
  - Skip classify_relevance() → return random relevant/irrelevant with synthetic confidence
  - Skip extract_metadata() → return synthetic extraction dict
  - Skip embed_tool_fields() → return None (no embedding)
  - Still exercise: progress tracking, state management, resumability, reporting
  - Add small random delay (0.01-0.05s) to simulate processing time
- This allows testing infrastructure at 1K scale without API costs

### 8. Batch Report
```json
{
  "batch_id": "batch-20260526-143000",
  "started_at": "...",
  "completed_at": "...",
  "elapsed_seconds": 1234.5,
  "total_items": 1000,
  "stored": 800,
  "skipped_irrelevant": 150,
  "failed": 50,
  "success_rate": 0.95,
  "avg_latency_ms": {
    "classify": 15000,
    "extract": 18000,
    "embed": 500,
    "store": 50,
    "total": 33550
  },
  "retry_stats": {
    "total_retries": 12,
    "retries_by_stage": {"classify": 5, "extract": 4, "embed": 2, "store": 1}
  },
  "failure_reasons": {
    "Classification timeout": 3,
    "Extraction JSON parse error": 2,
    ...
  },
  "taxonomy_distribution": {
    "pillars": {"Policy and Regulatory": 300, ...},
    "domains": {"Agri-food Systems": 500, ...},
    "types": {"Framework": 200, ...},
    "stages": {"Established and field-tested": 400, ...}
  }
}
```

### 9. CLI Runner (`run_batch.py`)

```
python -m pipeline.run_batch \
  --input items.json \
  --batch-size 100 \
  --concurrency 2 \
  --llm-delay 1.5 \
  --max-retries 3 \
  --resume \
  --mock \
  --state-dir pipeline/ \
  --model claude-sonnet-4-20250514
```

Arguments:
- `--input FILE` — JSON file with items to process
- `--batch-size N` — process first N items (default: all)
- `--concurrency N` — LLM worker threads (default: 1, max: 5)
- `--llm-delay SECS` — delay between LLM calls (default: 1.0)
- `--embedding-delay SECS` — delay between embedding calls (default: 0.2)
- `--max-retries N` — max retries per stage (default: 3)
- `--resume` — resume from previous state
- `--mock` — use mock mode (no actual API calls)
- `--state-dir DIR` — directory for state/progress files
- `--model MODEL` — LLM model to use
- `--generate N` — generate N synthetic items instead of reading from file

### 10. Test Data Generation
- Generate 1,000 realistic CG Space items
- Reuse patterns from `bulk_load.py`'s `generate_additional_items()`
- Include realistic variation in:
  - Titles (agricultural research topics)
  - Abstracts (2-3 sentences)
  - Doc types (Framework, Method, Tool, Guide, Report, etc.)
  - Authors (CGIAR center names + researcher names)
  - Dates (2015-2024)
  - URLs (cgspace.cgiar.org patterns)
- Mix of ~70% relevant and ~30% irrelevant items

### 11. Integration Test Plan
1. Generate 1,000 synthetic items → save to `pipeline/test_data/synthetic_1k.json`
2. Run 25 items through FULL pipeline (real LLM calls) to verify retry/progress works
3. Run remaining 975 items through MOCK mode to verify infrastructure
4. During mock run: kill and resume to demonstrate resumability
5. Verify final report shows correct counts
6. Verify progress.json was updating in real-time
7. Verify batch_state.json enables correct resume
