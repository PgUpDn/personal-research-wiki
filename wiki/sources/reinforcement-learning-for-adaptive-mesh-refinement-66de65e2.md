---
title: "Reinforcement Learning for Adaptive Mesh Refinement"
aliases:
  - "Reinforcement Learning for Adaptive Mesh Refinement"
  - "yang2023reinforcement"
note_type: "source"
schema_version: "research-wiki-pdf-v1"
source_id: "yang2023reinforcement"
citation_key: "yang2023reinforcement"
source_kind: "raw_pdf"
source_status: "compiled"
year: 2023
lead_author: "Jiachen Yang"
authors:
  - "Jiachen Yang"
  - "Tarik Dzani"
  - "Brenden Petersen"
  - "Jun Kudo"
  - "Ketan Mittal"
  - "Vladimir Tomov"
  - "Jean-Sylvain Camier"
  - "Tuo Zhao"
  - "Hongyuan Zha"
  - "Tzanio Kolev"
  - "Robert Anderson"
  - "Daniel Faissol"
sources:
  - "raw/Yang et al. - 2023 - Reinforcement Learning for Adaptive Mesh Refinement.pdf"
concepts:
  - "[[Partial Differential Equations]]"
  - "[[Reinforcement Learning]]"
domains: []
themes:
  - "geometry and irregular domains"
section_index:
  - "1 INTRODUCTION"
  - "2 RELATED WORK"
  - "3 BACKGROUND AND FORMULATION"
  - "3.1 Finite Element Method"
  - "3.2 AMR as a Markov Decision Process"
  - "6.4 Choice of Architecture"
  - "7 LIMITATIONS"
  - "8 CONCLUSION"
  - "Acknowledgements"
  - "References"
tags:
  - "research/source"
  - "source/raw-pdf"
  - "transcription/vision"
  - "year/2023"
related:
  - "[[Partial Differential Equations]]"
  - "[[Reinforcement Learning]]"
cache_path: "_meta/converted_sources/Yang et al. - 2023 - Reinforcement Learning for Adaptive Mesh Refinement.md"
page_image_dir: "_meta/source_page_images/yang-et-al-2023-reinforcement-learning-for-adaptive-mesh-refinement-614586d6"
page_count: 18
last_compiled: 2026-04-14
---

# Reinforcement Learning for Adaptive Mesh Refinement

> This source page is maintained by the wiki compiler so the vault can summarize, link, and query `raw/Yang et al. - 2023 - Reinforcement Learning for Adaptive Mesh Refinement.pdf` without modifying the raw source.

## Citation & Files

- Citation: Jiachen Yang et al. · (2023) · `yang2023reinforcement`
- Authors: Jiachen Yang et al.
- Identifiers: raw_pdf / compiled
- Source: `raw/Yang et al. - 2023 - Reinforcement Learning for Adaptive Mesh Refinement.pdf`
- Assets: cache `_meta/converted_sources/Yang et al. - 2023 - Reinforcement Learning for Adaptive Mesh Refinement.md` · 18 pages `_meta/source_page_images/yang-et-al-2023-reinforcement-learning-for-adaptive-mesh-refinement-614586d6`

<details>
<summary>Full author list</summary>

- Jiachen Yang
- Tarik Dzani
- Brenden Petersen
- Jun Kudo
- Ketan Mittal
- Vladimir Tomov
- Jean-Sylvain Camier
- Tuo Zhao
- Hongyuan Zha
- Tzanio Kolev
- Robert Anderson
- Daniel Faissol
</details>

## TL;DR

Finite element simulations of physical systems governed by partial differential equations (PDE) crucially depend on adaptive mesh refinement (AMR) to allocate computational budget to regions where higher resolution is...

## Abstract

Finite element simulations of physical systems governed by partial differential equations (PDE) crucially depend on adaptive mesh refinement (AMR) to allocate computational budget to regions where higher resolution is required. Existing scalable AMR methods make heuristic refinement decisions based on instantaneous error estimation and thus do not aim for long-term optimality over an entire simulation. We propose a novel formulation of AMR as a Markov decision process and apply deep reinforcement learning (RL) to train refinement *policies* directly from simulation.

## Key Concepts

- [[Partial Differential Equations]]
- [[Reinforcement Learning]]

## Research Signals

- Themes: geometry and irregular domains
- Keywords: refinement, mesh, llnl, reinforcement, adaptive, equations

## Reading Map

- 1 INTRODUCTION
- 2 RELATED WORK
- 3 BACKGROUND AND FORMULATION
- 3.1 Finite Element Method
- 3.2 AMR as a Markov Decision Process
- 6.4 Choice of Architecture
- 7 LIMITATIONS
- 8 CONCLUSION
- Acknowledgements
- References

## Provenance

- Last compiled: 2026-04-14
- Schema version: `research-wiki-pdf-v1`

