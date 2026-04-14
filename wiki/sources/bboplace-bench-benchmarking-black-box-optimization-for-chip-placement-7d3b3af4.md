---
title: "BBOPlace-Bench Benchmarking Black-Box Optimization for Chip Placement"
aliases:
  - "BBOPlace-Bench Benchmarking Black-Box Optimization for Chip Placement"
  - "xue2025bboplace"
note_type: "source"
schema_version: "research-wiki-pdf-v1"
source_id: "xue2025bboplace"
citation_key: "xue2025bboplace"
source_kind: "raw_pdf"
source_status: "compiled"
year: 2025
lead_author: "Ke Xue∗"
authors:
  - "Ke Xue∗"
  - "Ruo-Tong Chen∗"
  - "Rong-Xi Tan∗"
  - "Xi Lin"
  - "Yunqi Shi"
  - "Siyuan Xu"
  - "Mingxuan Yuan"
  - "Chao Qian"
  - "Senior Member"
sources:
  - "raw/Xue et al. - 2025 - BBOPlace-Bench Benchmarking Black-Box Optimization for Chip Placement.pdf"
concepts:
  - "[[Benchmarks and Evaluation]]"
  - "[[Semiconductor Design]]"
  - "[[Inverse Design]]"
domains:
  - "semiconductor systems"
themes:
  - "benchmarking and data curation"
  - "inverse design and optimization"
section_index:
  - "1 import argparse"
  - "2 import numpy as np"
  - "3 from src.evaluator import Evaluator"
  - "5 # Set parameters"
  - "6 parser = argparse.ArgumentParser()"
  - "7 parser.add_argument(\"--benchmark\", type=str, default"
  - "8 parser.add_argument(\"--eval_gp_hpwl\", action=\""
  - "9 parser.add_argument(\"--placer\", type=str, choices=[\""
  - "10 parser.add_argument(\"--sigma\", type=float, default"
  - "11 parser.add_argument(\"--pop_size\", type=int, default"
tags:
  - "research/source"
  - "source/raw-pdf"
  - "transcription/mixed"
  - "year/2025"
related:
  - "[[Benchmarks and Evaluation]]"
  - "[[Semiconductor Design]]"
  - "[[Inverse Design]]"
cache_path: "_meta/converted_sources/Xue et al. - 2025 - BBOPlace-Bench Benchmarking Black-Box Optimization for Chip Placement.md"
page_image_dir: "_meta/source_page_images/xue-et-al-2025-bboplace-bench-benchmarking-black-box-optimization-for-ch-84633df8"
page_count: 17
last_compiled: 2026-04-14
---

# BBOPlace-Bench Benchmarking Black-Box Optimization for Chip Placement

> This source page is maintained by the wiki compiler so the vault can summarize, link, and query `raw/Xue et al. - 2025 - BBOPlace-Bench Benchmarking Black-Box Optimization for Chip Placement.pdf` without modifying the raw source.

## Citation & Files

- Citation: Ke Xue∗ et al. · (2025) · `xue2025bboplace`
- Authors: Ke Xue∗ et al.
- Identifiers: raw_pdf / compiled
- Source: `raw/Xue et al. - 2025 - BBOPlace-Bench Benchmarking Black-Box Optimization for Chip Placement.pdf`
- Assets: cache `_meta/converted_sources/Xue et al. - 2025 - BBOPlace-Bench Benchmarking Black-Box Optimization for Chip Placement.md` · 17 pages `_meta/source_page_images/xue-et-al-2025-bboplace-bench-benchmarking-black-box-optimization-for-ch-84633df8`

<details>
<summary>Full author list</summary>

- Ke Xue∗
- Ruo-Tong Chen∗
- Rong-Xi Tan∗
- Xi Lin
- Yunqi Shi
- Siyuan Xu
- Mingxuan Yuan
- Chao Qian
- Senior Member
</details>

## TL;DR

—Chip placement is a vital stage in modern chip design as it has a substantial impact on the subsequent processes and the overall quality of the final chip. The use of black- box optimization (BBO) for chip placement...

## Abstract

—Chip placement is a vital stage in modern chip design as it has a substantial impact on the subsequent processes and the overall quality of the final chip. The use of black- box optimization (BBO) for chip placement has a history of several decades. However, early efforts were limited by immature problem formulations and inefficient algorithm designs, leading to suboptimal efficiency, quality, and scalability, compared to the more prevalent analytical methods.

## Key Concepts

- [[Benchmarks and Evaluation]]
- [[Semiconductor Design]]
- [[Inverse Design]]

## Research Signals

- Domains: semiconductor systems
- Themes: benchmarking and data curation, inverse design and optimization
- Keywords: chip, placement, problem, algorithms, bboplace-bench, optimization

## Reading Map

- 1 import argparse
- 2 import numpy as np
- 3 from src.evaluator import Evaluator
- 5 # Set parameters
- 6 parser = argparse.ArgumentParser()
- 7 parser.add_argument("--benchmark", type=str, default
- 8 parser.add_argument("--eval_gp_hpwl", action="
- 9 parser.add_argument("--placer", type=str, choices=["
- 10 parser.add_argument("--sigma", type=float, default
- 11 parser.add_argument("--pop_size", type=int, default

## Provenance

- Last compiled: 2026-04-14
- Schema version: `research-wiki-pdf-v1`

