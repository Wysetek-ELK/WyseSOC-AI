# Report 15: Capacity Planning — 10,000 Incidents per Day (P4-REQ-06)

## 1. Workload Modeling & Throughput Calculations

A production tier handling **10,000 incidents per day** equates to the following mathematical demand:

- **Average Daily Rate:** $\frac{10,000}{86,400\text{ s}} \approx 0.116\text{ incidents/second}$ (~7 incidents/minute).
- **Peak Hour Burst (5x Peak-to-Average Ratio):**
  $$\text{Peak Rate} \approx 0.116 \times 5 = 0.58\text{ incidents/second} \approx 35\text{ incidents/minute}$$
- **Extreme Burst Event (DDoS / Outbreak):** Up to 2-3 incidents/second over short 5-minute intervals.

---

## 2. Server 2 GPU Inference Throughput Analysis

### Inference Latency Profile (Qwen2.5-7B-Instruct-AWQ on NVIDIA T4):
- **Prompt Token Budget (Phase 3):** Fixed at ~900 tokens maximum context.
- **Completion Output:** Structured JSON response (~150 tokens).
- **Time To First Token (TTFT):** ~350 ms.
- **Inter-Token Latency:** ~25 ms/token.
- **Total Single-Request Latency:**
  $$\text{Latency} \approx 350\text{ ms} + (150 \times 25\text{ ms}) \approx 4,100\text{ ms} \approx 4.1\text{ seconds}$$

### Sustained Daily GPU Capacity:
With 4 concurrent execution slots managed by `GPUWorkloadManager`:
$$\text{Max Daily Throughput} = \frac{86,400\text{ seconds}}{4.1\text{ seconds/request}} \times 4\text{ concurrent slots} \approx 84,292\text{ incidents/day}$$

At 10,000 incidents per day, Server 2 operates at approximately **11.8% average daily GPU duty cycle**, leaving substantial headroom for traffic spikes, background simulation replays, and batch prompt evaluations.

---

## 3. Server 1 System Resource Sizing

### A. Database Storage Projections (10,000 Incidents/Day):
- **Incident + Events Record Size:** ~4 KB average (normalized JSON + metadata).
- **Daily Raw Incident Ingestion:** $10,000 \times 4\text{ KB} \approx 40\text{ MB/day}$.
- **Token Usage + Audit Log Entries:** ~1 KB per evaluation $\approx 10\text{ MB/day}$.
- **Annual Storage Demand:** $\approx 50\text{ MB/day} \times 365 \approx 18.25\text{ GB/year}$.
- **Hardware Requirement:** A standard 100 GB NVMe volume on Server 1 provides over 4 years of uncompressed historical incident retention before archival pruning is needed.

### B. Redis Broker Sizing:
- Task payload in Redis list: ~500 bytes.
- Peak queue backlog of 1,000 tasks: ~500 KB RAM.
- Negligible memory footprint (< 50 MB allocated to Redis).

### C. Network Bandwidth:
- Traffic between Server 1 and Server 2 per inference: ~5 KB request + ~1 KB response $\approx 6\text{ KB}$.
- Daily internal traffic: $10,000 \times 6\text{ KB} \approx 60\text{ MB/day}$.
- Well within standard 1 Gbps / 10 Gbps cloud private networks.

