---
title: "GeoTransolver: Learning Physics on Irregular Domains using Multi-scale Geometry Aware Physics Attention Transformer"
aliases:
  - "GeoTransolver: Learning Physics on Irregular Domains using Multi-scale Geometry Aware Physics Attention Transformer"
  - "GeoTransolver: Learning Physics on Irregular Domains"
  - "adams2025geotransolver"
note_type: "source"
schema_version: "research-wiki-pdf-v1"
source_id: "adams2025geotransolver"
citation_key: "adams2025geotransolver"
source_kind: "raw_pdf"
source_status: "compiled"
year: 2025
lead_author: "Corey Adams"
authors:
  - "Corey Adams"
  - "Rishikesh Ranad"
  - "Ram Cherukuri"
  - "Sanjay Choudhry"
sources:
  - "raw/Adams et al. - 2025 - GeoTransolver Learning Physics on Irregular Domains Using Multi-scale Geometry Aware Physics Attent.pdf"
concepts:
  - "[[Benchmarks and Evaluation]]"
  - "[[Computational Fluid Dynamics]]"
  - "[[Geometry-Aware Learning]]"
  - "[[Graph Neural Networks]]"
  - "[[Large Language Models]]"
  - "[[Multi-Physics]]"
  - "[[Neural Operators]]"
  - "[[Operator Learning]]"
  - "[[Partial Differential Equations]]"
  - "[[Physics-Informed Neural Networks]]"
  - "[[Scientific Datasets]]"
  - "[[Surrogate Models]]"
  - "[[Transformers]]"
domains:
  - "computational fluid dynamics"
  - "materials and chemistry"
themes:
  - "benchmarking and data curation"
  - "geometry and irregular domains"
  - "inverse design and optimization"
  - "physics-guided learning"
section_index:
  - "GeoTransolver: Learning Physics on Irregular Domains using Multi-scale Geometry Aware Physics Attention Transformer"
  - "1 Introduction"
  - "2 Background and Related Work"
  - "2.1 Neural operators"
  - "2.2 Geometry and mesh-aware encoders"
  - "2.3 Multi-scale locality and global coupling"
  - "2.4 Physics-aware conditioning and constraints"
  - "2.5 AI modeling for CAE"
  - "3 GeoTransolver"
  - "3.1 Geometry Aware Latent Embeddings (GALE)"
tags:
  - "research/source"
  - "source/raw-pdf"
  - "transcription/vision"
  - "year/2025"
related:
  - "[[Benchmarks and Evaluation]]"
  - "[[Computational Fluid Dynamics]]"
  - "[[Geometry-Aware Learning]]"
  - "[[Graph Neural Networks]]"
  - "[[Large Language Models]]"
  - "[[Multi-Physics]]"
  - "[[Neural Operators]]"
  - "[[Operator Learning]]"
  - "[[Partial Differential Equations]]"
  - "[[Physics-Informed Neural Networks]]"
  - "[[Scientific Datasets]]"
  - "[[Surrogate Models]]"
  - "[[Transformers]]"
cache_path: "_meta/converted_sources/Adams et al. - 2025 - GeoTransolver Learning Physics on Irregular Domains Using Multi-scale Geometry Aware Physics Attent.md"
page_image_dir: "_meta/source_page_images/adams-et-al-2025-geotransolver-learning-physics-on-irregular-domains-usi-355c590b"
page_count: 20
last_compiled: 2026-04-05
---

# GeoTransolver: Learning Physics on Irregular Domains using Multi-scale Geometry Aware Physics Attention Transformer

> This source page is maintained by the wiki compiler so the vault can summarize, link, and query `raw/Adams et al. - 2025 - GeoTransolver Learning Physics on Irregular Domains Using Multi-scale Geometry Aware Physics Attent.pdf` without modifying the raw source.

## Citation & Files

- Source ID: `adams2025geotransolver`
- Citation key: `adams2025geotransolver`
- Source kind: `raw_pdf`
- Status: `compiled`
- Raw source: `raw/Adams et al. - 2025 - GeoTransolver Learning Physics on Irregular Domains Using Multi-scale Geometry Aware Physics Attent.pdf`
- Working text cache: `_meta/converted_sources/Adams et al. - 2025 - GeoTransolver Learning Physics on Irregular Domains Using Multi-scale Geometry Aware Physics Attent.md`
- Page image directory: `_meta/source_page_images/adams-et-al-2025-geotransolver-learning-physics-on-irregular-domains-usi-355c590b`
- Page count: `20`
- Year: `2025`
- Lead author: Corey Adams
- Authors: Corey Adams; Rishikesh Ranad; Ram Cherukuri; Sanjay Choudhry

## TL;DR

We present GeoTransolver, a Multiscale Geometry-Aware Physics Attention Transformer for CAE that replaces standard attention with GALE, coupling physics-aware self-attention on learned state slices with cross-attention...

## Abstract

We present GeoTransolver, a Multiscale Geometry-Aware Physics Attention Transformer for CAE that replaces standard attention with GALE, coupling physics-aware self-attention on learned state slices with cross-attention to a shared geometry/global/boundary-condition context computed from multi-scale ball queries (inspired by DoMINO) and reused in every block. Implemented and released in NVIDIA PhysicsNeMo, GeoTransolver persistently projects geometry, global and boundary condition parameters into physical state spaces to anchor latent computations to domain structure and operating regimes. We benchmark GeoTransolver on DrivAerML, Luminary SHIFT-SUV, and Luminary SHIFT-Wing, comparing against Domino, Transolver (as released in PhysicsNeMo), and literature-reported AB-UPT, and evaluate drag/lift $R^2$ and Relative $L_1$ errors for field variables. GeoTransolver delivers better accuracy, improved robustness to geometry/regime shifts, and favorable data efficiency; we include ablations on DrivAerML and qualitative results such as contour plots and design trends for the best GeoTransolver models. By unifying multiscale geometry-aware context with physics-based attention in a scalable transformer, GeoTransolver advances operator learning for high-fidelity surrogate modeling across complex, irregular domains and non-linear physical regimes. *Keywords* Transformers · Multiscale Geometry Aware Models · CAE Surrogate Modeling ---

## Key Concepts

- [[Benchmarks and Evaluation]]
- [[Computational Fluid Dynamics]]
- [[Geometry-Aware Learning]]
- [[Graph Neural Networks]]
- [[Large Language Models]]
- [[Multi-Physics]]
- [[Neural Operators]]
- [[Operator Learning]]
- [[Partial Differential Equations]]
- [[Physics-Informed Neural Networks]]
- [[Scientific Datasets]]
- [[Surrogate Models]]
- [[Transformers]]

## Research Signals

- Domains: computational fluid dynamics, materials and chemistry
- Themes: benchmarking and data curation, geometry and irregular domains, inverse design and optimization, physics-guided learning
- Keywords: geotransolver, geometry, attention, transformer, multiscale, irregular

## Reading Map

- GeoTransolver: Learning Physics on Irregular Domains using Multi-scale Geometry Aware Physics Attention Transformer
- 1 Introduction
- 2 Background and Related Work
- 2.1 Neural operators
- 2.2 Geometry and mesh-aware encoders
- 2.3 Multi-scale locality and global coupling
- 2.4 Physics-aware conditioning and constraints
- 2.5 AI modeling for CAE
- 3 GeoTransolver
- 3.1 Geometry Aware Latent Embeddings (GALE)

## Provenance

- Last compiled: 2026-04-05
- Schema version: `research-wiki-pdf-v1`

