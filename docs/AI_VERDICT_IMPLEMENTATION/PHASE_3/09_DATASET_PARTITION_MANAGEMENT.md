# 09. DATASET PARTITION MANAGEMENT

**Document Identifier:** `AV-P3-DOC-09`  
**Requirement Mapping:** `P3-REQ-07` (Dataset Partitioning & Leakage Prevention)  
**Implementation Modules:** `app/services/calibration_evaluation_service.py`, `app/schemas/calibration.py`  

---

## 1. Zero-Leakage 4-Way Dataset Partitioning

To enable rigorous machine learning evaluation and prompt optimization without circular overfitting or test-set leakage, `CalibrationEvaluationService.assign_dataset_partition` partitions incidents into 4 strictly isolated subsets:

| Partition | Allocation | Intended Purpose |
| :--- | :--- | :--- |
| **TRAIN** | 50% (Buckets 00–49) | Training data for few-shot learning and supervised fine-tuning. |
| **TUNING** | 20% (Buckets 50–69) | Prompt engineering, guideline synthesis, and Studio iteration. |
| **CALIBRATION** | 15% (Buckets 70–84) | Platt scaling / Isotonic regression parameter fitting. |
| **LOCKED_TEST** | 15% (Buckets 85–99) | Final, inviolable benchmark evaluation; never exposed during tuning. |

---

## 2. Deterministic Hash-Modulo Algorithm

Partition assignment is computed using a deterministic SHA-256 hash of the stable incident ID:

$$\text{bucket} = \text{hex\_to\_int}(\text{SHA256}(\text{incident\_id})[:8]) \pmod{100}$$

### Mathematical Properties:
- **Stateless & Deterministic:** Any system component can compute the partition independently without maintaining state or database locks.
- **Stable Across Replays:** Re-evaluating or re-ingesting an incident produces the identical partition assignment.
- **Zero Leakage:** Test cases can never bleed into training or tuning sets.

