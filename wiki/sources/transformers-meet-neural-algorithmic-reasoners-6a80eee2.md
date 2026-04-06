---
title: "Transformers meet Neural Algorithmic Reasoners"
aliases:
  - "Transformers meet Neural Algorithmic Reasoners"
  - "bounsi2024transformers"
note_type: "source"
schema_version: "research-wiki-pdf-v1"
source_id: "bounsi2024transformers"
citation_key: "bounsi2024transformers"
source_kind: "raw_pdf"
source_status: "compiled"
year: 2024
lead_author: "Wilfried Bounsi"
authors:
  - "Wilfried Bounsi"
  - "Borja Ibarz"
  - "Andrew Dudzik"
  - "Jessica B. Hamrick"
  - "Larisa Markeev"
  - "Alex Vitvitskyi"
sources:
  - "raw/Bounsi et al. - 2024 - Transformers meet Neural Algorithmic Reasoners.pdf"
concepts:
  - "[[Benchmarks and Evaluation]]"
  - "[[Foundation Models]]"
  - "[[Graph Neural Networks]]"
  - "[[Large Language Models]]"
  - "[[Pretraining and Transfer Learning]]"
  - "[[Reinforcement Learning]]"
  - "[[Scientific Datasets]]"
  - "[[Transformers]]"
domains: []
themes:
  - "benchmarking and data curation"
  - "scaling and transfer"
section_index:
  - "1. Introduction"
  - "2. Related work"
  - "3. TransNAR: Augmenting Transformers with a pre-trained GNN-based NAR"
  - "6. Effect of Randomized Positional Encoding"
  - "7. Parse Scores"
tags:
  - "research/source"
  - "source/raw-pdf"
  - "transcription/vision"
  - "year/2024"
related:
  - "[[Benchmarks and Evaluation]]"
  - "[[Foundation Models]]"
  - "[[Graph Neural Networks]]"
  - "[[Large Language Models]]"
  - "[[Pretraining and Transfer Learning]]"
  - "[[Reinforcement Learning]]"
  - "[[Scientific Datasets]]"
  - "[[Transformers]]"
cache_path: "_meta/converted_sources/Bounsi et al. - 2024 - Transformers meet Neural Algorithmic Reasoners.md"
page_image_dir: "_meta/source_page_images/bounsi-et-al-2024-transformers-meet-neural-algorithmic-reasoners-a6025874"
page_count: 11
last_compiled: 2026-04-05
---

# Transformers meet Neural Algorithmic Reasoners

> This source page is maintained by the wiki compiler so the vault can summarize, link, and query `raw/Bounsi et al. - 2024 - Transformers meet Neural Algorithmic Reasoners.pdf` without modifying the raw source.

## Citation & Files

- Source ID: `bounsi2024transformers`
- Citation key: `bounsi2024transformers`
- Source kind: `raw_pdf`
- Status: `compiled`
- Raw source: `raw/Bounsi et al. - 2024 - Transformers meet Neural Algorithmic Reasoners.pdf`
- Working text cache: `_meta/converted_sources/Bounsi et al. - 2024 - Transformers meet Neural Algorithmic Reasoners.md`
- Page image directory: `_meta/source_page_images/bounsi-et-al-2024-transformers-meet-neural-algorithmic-reasoners-a6025874`
- Page count: `11`
- Year: `2024`
- Lead author: Wilfried Bounsi
- Authors: Wilfried Bounsi; Borja Ibarz; Andrew Dudzik; Jessica B. Hamrick; Larisa Markeev; Alex Vitvitskyi

## TL;DR

*Transformers have revolutionized machine learning with their simple yet effective architecture. Pre-training Transformers on massive text datasets from the Internet has led to unmatched generalization for natural...

## Abstract

*Transformers have revolutionized machine learning with their simple yet effective architecture. Pre-training Transformers on massive text datasets from the Internet has led to unmatched generalization for natural language understanding (NLU) tasks. However, such language models remain fragile when tasked with algorithmic forms of reasoning, where computations must be precise and robust. To address this limitation, we propose a novel approach that combines the Transformer's language understanding with the robustness of graph neural network (GNN)-based neural algorithmic reasoners (NARs). Such NARs proved effective as generic solvers for algorithmic tasks, when specified in graph form. To make their embeddings accessible to a Transformer, we propose a hybrid architecture with a two-phase training procedure, allowing the tokens in the language model to cross-attend to the node embeddings from the NAR. We evaluate our resulting TransNAR model on CLRS-Text, the text-based version of the CLRS-30 benchmark, and demonstrate significant gains over Transformer-only models for algorithmic reasoning, both in and out of distribution.* Figure 1. Our TransNAR architecture, with its direct synergy of Transformers and Neural Algorithmic Reasoners, yields clear improvements in out-of-distribution reasoning across wide categories of algorithmic tasks in CLRS-Text [20], a textual version of the CLRS-30 benchmark [35]. Here, the x-axis indicates one of the eight algorithmic families of CLRS-30, and the y-axis spans the average execution accuracy across a dataset of out-of-distribution examples

## Key Concepts

- [[Benchmarks and Evaluation]]
- [[Foundation Models]]
- [[Graph Neural Networks]]
- [[Large Language Models]]
- [[Pretraining and Transfer Learning]]
- [[Reinforcement Learning]]
- [[Scientific Datasets]]
- [[Transformers]]

## Research Signals

- Themes: benchmarking and data curation, scaling and transfer
- Keywords: algorithmic, transformers, language, reasoners, architecture, tasks

## Reading Map

- 1. Introduction
- 2. Related work
- 3. TransNAR: Augmenting Transformers with a pre-trained GNN-based NAR
- 6. Effect of Randomized Positional Encoding
- 7. Parse Scores

## Provenance

- Last compiled: 2026-04-05
- Schema version: `research-wiki-pdf-v1`

