---
title: "Multiple Physics Pretraining for Spatiotemporal Surrogate Models"
aliases:
  - "Multiple Physics Pretraining for Spatiotemporal Surrogate Models"
  - "mccab2024multiple"
note_type: "source"
schema_version: "research-wiki-pdf-v1"
source_id: "mccab2024multiple"
citation_key: "mccab2024multiple"
source_kind: "raw_pdf"
source_status: "compiled"
year: 2024
lead_author: "Michael McCab"
authors:
  - "Michael McCab"
  - "Bruno Régaldo-Saint Blancar"
  - "Liam Parker"
  - "Ruben Ohan"
  - "Miles Cranmer"
  - "Alberto Bietti"
  - "Michael Eickenberg"
  - "Siavash Golkar"
  - "Geraud Krawezik"
  - "Francois Lanuss"
  - "Mariel Pette"
  - "Tiberiu Tesileanu"
  - "Kyunghyun Cho"
  - "Shirley Ho"
  - "The Polymathic AI Collaboration"
  - "Université Paris-Saclay"
  - "Université Paris Cité"
sources:
  - "raw/McCabe et al. - 2024 - Multiple Physics Pretraining for Physical Surrogate Models.pdf"
concepts:
  - "[[Surrogate Models]]"
  - "[[Foundation Models]]"
  - "[[Transformers]]"
  - "[[Benchmarks and Evaluation]]"
  - "[[Pretraining and Transfer Learning]]"
domains:
  - "computational fluid dynamics"
themes:
  - "benchmarking and data curation"
  - "scaling and transfer"
section_index:
  - "Multiple Physics Pretraining for Spatiotemporal Surrogate Models"
  - "1 Introduction"
  - "2 Background"
  - "3 Related Work"
  - "4 Scalable Multiple Physics Pretraining"
  - "4.1 Compositionality and Pretraining"
  - "5.1 Pretraining Representations"
  - "5.2 Transfer to Low-data Domains"
  - "5.3 Inflation to 3D"
  - "6 Conclusion"
tags:
  - "research/source"
  - "source/raw-pdf"
  - "transcription/mixed"
  - "year/2024"
related:
  - "[[Surrogate Models]]"
  - "[[Foundation Models]]"
  - "[[Transformers]]"
  - "[[Benchmarks and Evaluation]]"
  - "[[Pretraining and Transfer Learning]]"
cache_path: "_meta/converted_sources/McCabe et al. - 2024 - Multiple Physics Pretraining for Physical Surrogate Models.md"
page_image_dir: "_meta/source_page_images/mccabe-et-al-2024-multiple-physics-pretraining-for-physical-surrogate-mo-53c2a2f8"
page_count: 35
last_compiled: 2026-04-14
---

# Multiple Physics Pretraining for Spatiotemporal Surrogate Models

> This source page is maintained by the wiki compiler so the vault can summarize, link, and query `raw/McCabe et al. - 2024 - Multiple Physics Pretraining for Physical Surrogate Models.pdf` without modifying the raw source.

## Citation & Files

- Citation: Michael McCab et al. · (2024) · `mccab2024multiple`
- Authors: Michael McCab et al.
- Identifiers: raw_pdf / compiled
- Source: `raw/McCabe et al. - 2024 - Multiple Physics Pretraining for Physical Surrogate Models.pdf`
- Assets: cache `_meta/converted_sources/McCabe et al. - 2024 - Multiple Physics Pretraining for Physical Surrogate Models.md` · 35 pages `_meta/source_page_images/mccabe-et-al-2024-multiple-physics-pretraining-for-physical-surrogate-mo-53c2a2f8`

<details>
<summary>Full author list</summary>

- Michael McCab
- Bruno Régaldo-Saint Blancar
- Liam Parker
- Ruben Ohan
- Miles Cranmer
- Alberto Bietti
- Michael Eickenberg
- Siavash Golkar
- Geraud Krawezik
- Francois Lanuss
- Mariel Pette
- Tiberiu Tesileanu
- Kyunghyun Cho
- Shirley Ho
- The Polymathic AI Collaboration
- Université Paris-Saclay
- Université Paris Cité
</details>

## TL;DR

We introduce multiple physics pretraining (MPP), an autoregressive task-agnostic pretraining approach for physical surrogate modeling of spatiotemporal systems with transformers. In MPP, rather than training one model...

## Abstract

We introduce multiple physics pretraining (MPP), an autoregressive task-agnostic pretraining approach for physical surrogate modeling of spatiotemporal systems with transformers. In MPP, rather than training one model on a specific physical system, we train a backbone model to predict the dynamics of multiple heterogeneous physical systems simultaneously in order to learn features that are broadly useful across systems and facilitate transfer. In order to learn effectively in this setting, we introduce a shared embedding and normalization strategy that projects the fields of multiple systems into a shared embedding space.

## Key Concepts

- [[Surrogate Models]]
- [[Foundation Models]]
- [[Transformers]]
- [[Benchmarks and Evaluation]]
- [[Pretraining and Transfer Learning]]

## Research Signals

- Domains: computational fluid dynamics
- Themes: benchmarking and data curation, scaling and transfer
- Keywords: multiple, pretraining, physical, that, finetuning, spatiotemporal

## Reading Map

- Multiple Physics Pretraining for Spatiotemporal Surrogate Models
- 1 Introduction
- 2 Background
- 3 Related Work
- 4 Scalable Multiple Physics Pretraining
- 4.1 Compositionality and Pretraining
- 5.1 Pretraining Representations
- 5.2 Transfer to Low-data Domains
- 5.3 Inflation to 3D
- 6 Conclusion

## Provenance

- Last compiled: 2026-04-14
- Schema version: `research-wiki-pdf-v1`

