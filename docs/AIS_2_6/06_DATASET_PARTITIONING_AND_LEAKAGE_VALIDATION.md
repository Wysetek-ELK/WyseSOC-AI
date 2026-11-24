# 06 — Dataset Partitioning and Leakage Validation Report

## Executive Summary

This report establishes the cluster-aware dataset partitioning protocol for Verdictum AI. To prevent data leakage and over-optimistic evaluation metrics, all 20 historical incidents have been partitioned into Partitions A, B, and C with mathematical cluster integrity.

---

## 1. Partitioning Structure

| Partition | Name | Target Size | Purpose | Assigned Clusters | Independent Incidents | Total Incidents |
|---|---|---|---|---|---|---|
| **Partition A** | Development & Calibration | 8 | Algorithm development, prompt engineering, and policy compilation calibration | **Cluster 1** (5 incidents) | 3 incidents | **8** |
| **Partition B** | Held-Out Evaluation | 7 | Independent, blind evaluation of empirical accuracy and selective coverage | **Cluster 2** (2 incidents) | 5 incidents | **7** |
| **Partition C** | Ambiguous & Stress Testing | 5 | Stress testing of abstention safety, context truncation, and missing evidence | **Cluster 3** (3 incidents) | 2 incidents | **5** |

---

## 2. Cluster Integrity Guarantee

A common failure mode in LLM SOC evaluation is splitting duplicate or clustered alerts across train and test sets, allowing the model to memorize hostnames or file paths.

### 2.1 Cluster Partition Assignments
1. **Cluster 1** (`132438483`, `132439932`, `132441815`, `132461358`, `132461368`):
   - All 5 members reside **strictly in Partition A**.
   - Zero members in Partition B or C.
2. **Cluster 2** (`132501348`, `132527297`):
   - Both members reside **strictly in Partition B**.
   - Zero members in Partition A or C.
3. **Cluster 3** (`132599145`, `132599146`, `132599330`):
   - All 3 members reside **strictly in Partition C**.
   - Zero members in Partition A or B.

**Mathematical Contamination Check**: $\text{Cluster Contamination Rate} = 0.0\%$.
