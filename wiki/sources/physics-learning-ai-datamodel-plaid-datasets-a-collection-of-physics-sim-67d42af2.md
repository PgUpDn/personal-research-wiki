---
title: "Physics-Learning AI Datamodel (PLAID) datasets: a collection of physics simulations for machine learning"
aliases:
  - "Physics-Learning AI Datamodel (PLAID) datasets: a collection of physics simulations for machine learning"
  - "Physics-Learning AI Datamodel (PLAID) datasets"
  - "casenav2025physics"
note_type: "source"
schema_version: "research-wiki-pdf-v1"
source_id: "casenav2025physics"
citation_key: "casenav2025physics"
source_kind: "raw_pdf"
source_status: "compiled"
year: 2025
lead_author: "Fabien Casenav"
authors:
  - "Fabien Casenav"
  - "Xavier Roynar"
  - "Brian Staber"
  - "William Piat"
  - "Michele Alessandro Bucci"
  - "Nissrine Akkari"
  - "Abbas Kabalan"
  - "Xuan Minh Vuong Nguyen"
  - "Luca Saverio"
  - "Raphaël Carpintero Perez"
  - "Anthony Kalaydjian"
  - "Samy Fouché $^{"
  - "Thierry Gonon"
  - "Ghassan Najjar"
  - "Emmanuel Menier"
  - "Matthieu Nastorg"
  - "Giovanni Catalani"
  - "Christian Rey"
  - "Augur Inria Airbus ISAE-SUPAERO"
sources:
  - "raw/Casenave et al. - 2025 - Physics-Learning AI Datamodel (PLAID) datasets a collection of physics simulations for machine lear.pdf"
concepts:
  - "[[Benchmarks and Evaluation]]"
  - "[[Computational Fluid Dynamics]]"
  - "[[Foundation Models]]"
  - "[[Graph Neural Networks]]"
  - "[[Inverse Design]]"
  - "[[Large Language Models]]"
  - "[[MeshGraphNets]]"
  - "[[Partial Differential Equations]]"
  - "[[Scientific Datasets]]"
  - "[[Scientific Machine Learning]]"
  - "[[Surrogate Models]]"
  - "[[Uncertainty Quantification]]"
domains:
  - "computational fluid dynamics"
  - "materials and chemistry"
themes:
  - "benchmarking and data curation"
  - "geometry and irregular domains"
  - "inverse design and optimization"
  - "scaling and transfer"
section_index:
  - "Physics-Learning AI Datamodel (PLAID) datasets: a collection of physics simulations for machine learning"
  - "1 Introduction"
  - "2 Related Work"
  - "3 PLAID standard"
  - "4 PLAID datasets"
  - "4.1 Structural mechanics"
  - "4.1.1 Tensile2d [69] (Zenodo, Hugging Face)"
  - "4.1.2 2D_MultiScHypEl [71] (Zenodo, Hugging Face)"
  - "4.1.3 2D_ElPlDynamics [74] (Zenodo, Hugging Face)"
  - "5.1 Methods"
tags:
  - "research/source"
  - "source/raw-pdf"
  - "transcription/vision"
  - "year/2025"
related:
  - "[[Benchmarks and Evaluation]]"
  - "[[Computational Fluid Dynamics]]"
  - "[[Foundation Models]]"
  - "[[Graph Neural Networks]]"
  - "[[Inverse Design]]"
  - "[[Large Language Models]]"
  - "[[MeshGraphNets]]"
  - "[[Partial Differential Equations]]"
  - "[[Scientific Datasets]]"
  - "[[Scientific Machine Learning]]"
  - "[[Surrogate Models]]"
  - "[[Uncertainty Quantification]]"
cache_path: "_meta/converted_sources/Casenave et al. - 2025 - Physics-Learning AI Datamodel (PLAID) datasets a collection of physics simulations for machine lear.md"
page_image_dir: "_meta/source_page_images/casenave-et-al-2025-physics-learning-ai-datamodel-plaid-datasets-a-colle-67101eb5"
page_count: 33
last_compiled: 2026-04-05
---

# Physics-Learning AI Datamodel (PLAID) datasets: a collection of physics simulations for machine learning

> This source page is maintained by the wiki compiler so the vault can summarize, link, and query `raw/Casenave et al. - 2025 - Physics-Learning AI Datamodel (PLAID) datasets a collection of physics simulations for machine lear.pdf` without modifying the raw source.

## Citation & Files

- Source ID: `casenav2025physics`
- Citation key: `casenav2025physics`
- Source kind: `raw_pdf`
- Status: `compiled`
- Raw source: `raw/Casenave et al. - 2025 - Physics-Learning AI Datamodel (PLAID) datasets a collection of physics simulations for machine lear.pdf`
- Working text cache: `_meta/converted_sources/Casenave et al. - 2025 - Physics-Learning AI Datamodel (PLAID) datasets a collection of physics simulations for machine lear.md`
- Page image directory: `_meta/source_page_images/casenave-et-al-2025-physics-learning-ai-datamodel-plaid-datasets-a-colle-67101eb5`
- Page count: `33`
- Year: `2025`
- Lead author: Fabien Casenav
- Authors: Fabien Casenav; Xavier Roynar; Brian Staber; William Piat; Michele Alessandro Bucci; Nissrine Akkari; Abbas Kabalan; Xuan Minh Vuong Nguyen; Luca Saverio; Raphaël Carpintero Perez; Anthony Kalaydjian; Samy Fouché $^{; Thierry Gonon; Ghassan Najjar; Emmanuel Menier; Matthieu Nastorg; Giovanni Catalani; Christian Rey; Augur Inria Airbus ISAE-SUPAERO

## TL;DR

Machine learning-based surrogate models have emerged as a powerful tool to accelerate simulation-driven scientific workflows. However, their widespread adoption is hindered by the lack of large-scale, diverse, and...

## Abstract

Machine learning-based surrogate models have emerged as a powerful tool to accelerate simulation-driven scientific workflows. However, their widespread adoption is hindered by the lack of large-scale, diverse, and standardized datasets tailored to physics-based simulations. While existing initiatives provide valuable contributions, many are limited in scope—focusing on specific physics domains, relying on fragmented tooling, or adhering to overly simplistic datamodels that restrict generalization. To address these limitations, we introduce PLAID (Physics-Learning AI Datamodel), a flexible and extensible framework for representing and sharing datasets of physics simulations. PLAID defines a unified standard for describing simulation data and is accompanied by a library for creating, reading, and manipulating complex datasets across a wide range of physical use cases (gitlab.com/drti/plaid). We release six carefully crafted datasets under the PLAID standard, covering structural mechanics and computational fluid dynamics, and provide baseline benchmarks using representative learning methods. Benchmarking tools are made available on Hugging Face, enabling direct participation by the community and contribution to ongoing evaluation efforts (huggingface.co/PLAIDcompetitions).

## Key Concepts

- [[Benchmarks and Evaluation]]
- [[Computational Fluid Dynamics]]
- [[Foundation Models]]
- [[Graph Neural Networks]]
- [[Inverse Design]]
- [[Large Language Models]]
- [[MeshGraphNets]]
- [[Partial Differential Equations]]
- [[Scientific Datasets]]
- [[Scientific Machine Learning]]
- [[Surrogate Models]]
- [[Uncertainty Quantification]]

## Research Signals

- Domains: computational fluid dynamics, materials and chemistry
- Themes: benchmarking and data curation, geometry and irregular domains, inverse design and optimization, scaling and transfer
- Keywords: plaid, datasets, physics-learning, datamodel, provide, standard

## Reading Map

- Physics-Learning AI Datamodel (PLAID) datasets: a collection of physics simulations for machine learning
- 1 Introduction
- 2 Related Work
- 3 PLAID standard
- 4 PLAID datasets
- 4.1 Structural mechanics
- 4.1.1 Tensile2d [69] (Zenodo, Hugging Face)
- 4.1.2 2D_MultiScHypEl [71] (Zenodo, Hugging Face)
- 4.1.3 2D_ElPlDynamics [74] (Zenodo, Hugging Face)
- 5.1 Methods

## Provenance

- Last compiled: 2026-04-05
- Schema version: `research-wiki-pdf-v1`

