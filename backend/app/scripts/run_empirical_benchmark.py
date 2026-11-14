"""
CLI runner for the Verdictum AI Empirical Benchmark Harness.
Usage:
    python backend/app/scripts/run_empirical_benchmark.py --mode offline
    python backend/app/scripts/run_empirical_benchmark.py --mode live --endpoint http://<SERVER_2_IP>:8000/v1
"""

import argparse
import asyncio
import os
import sys
import json
from datetime import datetime, timezone

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.services.empirical_benchmark_harness import EmpiricalBenchmarkHarness


async def main():
    parser = argparse.ArgumentParser(description="Verdictum AI Empirical Benchmark Harness")
    parser.add_argument("--mode", choices=["offline", "live"], default="offline", help="Evaluation mode (offline simulation vs live local LLM)")
    parser.add_argument("--zip-path", default=None, help="Path to FortiSIEM incident zip archive (defaults to fixtures/Incident json.zip)")
    parser.add_argument("--endpoint", default=None, help="Base URL for live OpenAI-compatible LLM endpoint (e.g. http://192.168.1.100:8000/v1)")
    parser.add_argument("--output-dir", default="docs/LLM_EMPIRICAL_READINESS", help="Directory where reports are saved")
    args = parser.parse_args()

    print(f"=== Verdictum AI Empirical Benchmark Runner ===")
    print(f"Mode: {args.mode}")
    print(f"Zip Path: {args.zip_path or 'fixtures/Incident json.zip'}")
    if args.mode == "live":
        print(f"Model Endpoint: {args.endpoint}")
    print(f"Output Directory: {args.output_dir}")
    print("-----------------------------------------------")

    report = await EmpiricalBenchmarkHarness.run_benchmark(
        source="fixtures",
        zip_path=args.zip_path,
        mode=args.mode,
        model_endpoint=args.endpoint,
    )

    md_content = EmpiricalBenchmarkHarness.generate_markdown_report(report)

    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Save Markdown report
    md_filename = "OFFLINE_TEST_RESULTS.md" if args.mode == "offline" else f"LIVE_GPU_BENCHMARK_{report.report_id}.md"
    md_path = os.path.join(args.output_dir, md_filename)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"\n[+] Saved Markdown Report to: {md_path}")

    # Save JSON report
    json_path = os.path.join(args.output_dir, f"benchmark_{report.report_id}.json")
    # Custom serializer for dataclasses
    def _to_serializable(obj):
        if hasattr(obj, "__dict__"):
            return {k: _to_serializable(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, list):
            return [_to_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: _to_serializable(v) for k, v in obj.items()}
        return obj

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(_to_serializable(report), f, indent=2)
    print(f"[+] Saved JSON Artifact to: {json_path}")

    # Print summary
    m = report.overall_metrics
    print("\n--- BENCHMARK SUMMARY ---")
    print(f"Total Incidents Evaluated: {m.total_incidents}")
    print(f"Verified Ground Truth:     {m.verified_ground_truth_count}")
    print(f"Decisive Decisions:        {m.decisive_decisions_count} ({m.coverage_rate:.1%})")
    print(f"Abstentions:               {m.total_abstained} ({m.abstention_rate:.1%})")
    print(f"Confusion Matrix:          TP={m.tp}, TN={m.tn}, FP={m.fp}, FN={m.fn}")
    print(f"TP Recall / Precision:     {m.tp_recall:.1%} / {m.tp_precision:.1%}" if (m.tp_recall and m.tp_precision) else "TP Recall / Precision: N/A")
    print(f"FP Recall / Precision:     {m.fp_recall:.1%} / {m.fp_precision:.1%}" if (m.fp_recall and m.fp_precision) else "FP Recall / Precision: N/A")
    print(f"Unsafe FP Rate (Safety):   {m.unsafe_fp_rate:.1%} ({m.unsafe_fp_count}/{m.verified_tp_count})")
    print(f"Data Leakage Detected:     {m.leakage_detected_count}")
    print("===============================================")


if __name__ == "__main__":
    asyncio.run(main())

