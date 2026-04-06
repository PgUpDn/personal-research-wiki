---
title: "A physics-informed transformer neural operator for learning generalized solutions of initial boundary value problems"
aliases:
  - "A physics-informed transformer neural operator for learning generalized solutions of initial boundary value problems"
  - "A physics-informed transformer neural operator for"
  - "boya2024a"
note_type: "source"
schema_version: "research-wiki-pdf-v1"
source_id: "boya2024a"
citation_key: "boya2024a"
source_kind: "raw_pdf"
source_status: "compiled"
year: 2024
lead_author: "Sumanth Kumar Boya"
authors:
  - "Sumanth Kumar Boya"
  - "Deepak Subramani"
sources:
  - "raw/Boya and Subramani - 2024 - A physics-informed transformer neural operator for learning generalized solutions of initial boundar.pdf"
concepts:
  - "[[AI Agents]]"
  - "[[Computational Fluid Dynamics]]"
  - "[[Large Language Models]]"
  - "[[Neural Operators]]"
  - "[[Operator Learning]]"
  - "[[Partial Differential Equations]]"
  - "[[Physics-Informed Neural Networks]]"
  - "[[Scientific Machine Learning]]"
  - "[[Surrogate Models]]"
  - "[[Transformers]]"
  - "[[World Models]]"
domains:
  - "computational fluid dynamics"
  - "agents and automation"
themes:
  - "geometry and irregular domains"
  - "inverse design and optimization"
  - "physics-guided learning"
section_index:
  - "A physics-informed transformer neural operator for learning generalized solutions of initial boundary value problems"
  - "1 Introduction"
  - "1.1 Related work:"
  - "1.2 Key contributions"
  - "2 Development of Physics-Informed Transformer Neural Operator"
  - "2.1 Neural Operator Definition and Loss Function"
  - "2.2 Cross Attention Neural Operator Theory"
  - "2.3 Practical Implementation"
  - "3 Applications of PINTO"
  - "3.1 Advection Equation"
tags:
  - "research/source"
  - "source/raw-pdf"
  - "transcription/vision"
  - "year/2024"
related:
  - "[[AI Agents]]"
  - "[[Computational Fluid Dynamics]]"
  - "[[Large Language Models]]"
  - "[[Neural Operators]]"
  - "[[Operator Learning]]"
  - "[[Partial Differential Equations]]"
  - "[[Physics-Informed Neural Networks]]"
  - "[[Scientific Machine Learning]]"
  - "[[Surrogate Models]]"
  - "[[Transformers]]"
  - "[[World Models]]"
cache_path: "_meta/converted_sources/Boya and Subramani - 2024 - A physics-informed transformer neural operator for learning generalized solutions of initial boundar.md"
page_image_dir: "_meta/source_page_images/boya-and-subramani-2024-a-physics-informed-transformer-neural-operator-f-ec4e2eb6"
page_count: 29
last_compiled: 2026-04-05
---

# A physics-informed transformer neural operator for learning generalized solutions of initial boundary value problems

> This source page is maintained by the wiki compiler so the vault can summarize, link, and query `raw/Boya and Subramani - 2024 - A physics-informed transformer neural operator for learning generalized solutions of initial boundar.pdf` without modifying the raw source.

## Citation & Files

- Source ID: `boya2024a`
- Citation key: `boya2024a`
- Source kind: `raw_pdf`
- Status: `compiled`
- Raw source: `raw/Boya and Subramani - 2024 - A physics-informed transformer neural operator for learning generalized solutions of initial boundar.pdf`
- Working text cache: `_meta/converted_sources/Boya and Subramani - 2024 - A physics-informed transformer neural operator for learning generalized solutions of initial boundar.md`
- Page image directory: `_meta/source_page_images/boya-and-subramani-2024-a-physics-informed-transformer-neural-operator-f-ec4e2eb6`
- Page count: `29`
- Year: `2024`
- Lead author: Sumanth Kumar Boya
- Authors: Sumanth Kumar Boya; Deepak Subramani

## TL;DR

** Initial boundary value problems arise commonly in applications with engineering and natural systems governed by nonlinear partial differential equations (PDEs). Operator learning is an emerging field for solving...

## Abstract

** Initial boundary value problems arise commonly in applications with engineering and natural systems governed by nonlinear partial differential equations (PDEs). Operator learning is an emerging field for solving these equations by using a neural network to learn a map between infinite dimensional input and output function spaces. These neural operators are trained using a combination of data (observations or simulations) and PDE-residuals (physics-loss). A major drawback of existing neural approaches is the requirement to retrain with new initial/boundary conditions, and the necessity for a large amount of simulation data for training. We develop a physics-informed transformer neural operator (named PINTO) that efficiently generalizes to unseen initial and boundary conditions, trained in a simulation-free setting using only physics loss. The main innovation lies in our new iterative kernel integral operator units, implemented using cross-attention, to transform the PDE solution's domain points into an initial/boundary condition-aware representation vector, enabling efficient learning of the solution function for new scenarios. The PINTO architecture is applied to simulate the solutions of important equations used in engineering applications: advection, Burgers, and steady and unsteady Navier-Stokes equations (three flow scenarios). For these five test cases, we show that the relative errors during testing under challenging conditions of unseen initial/boundary conditions are only one-fifth to one-third of other leading physics informed operator learning methods. Moreover

## Key Concepts

- [[AI Agents]]
- [[Computational Fluid Dynamics]]
- [[Large Language Models]]
- [[Neural Operators]]
- [[Operator Learning]]
- [[Partial Differential Equations]]
- [[Physics-Informed Neural Networks]]
- [[Scientific Machine Learning]]
- [[Surrogate Models]]
- [[Transformers]]
- [[World Models]]

## Research Signals

- Domains: computational fluid dynamics, agents and automation
- Themes: geometry and irregular domains, inverse design and optimization, physics-guided learning
- Keywords: initial, boundary, operator, equations, conditions, these

## Reading Map

- A physics-informed transformer neural operator for learning generalized solutions of initial boundary value problems
- 1 Introduction
- 1.1 Related work:
- 1.2 Key contributions
- 2 Development of Physics-Informed Transformer Neural Operator
- 2.1 Neural Operator Definition and Loss Function
- 2.2 Cross Attention Neural Operator Theory
- 2.3 Practical Implementation
- 3 Applications of PINTO
- 3.1 Advection Equation

## Provenance

- Last compiled: 2026-04-05
- Schema version: `research-wiki-pdf-v1`

