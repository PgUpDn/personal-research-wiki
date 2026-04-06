---
title: "LNO: Laplace Neural Operator for Solving Differential Equations"
aliases:
  - "LNO: Laplace Neural Operator for Solving Differential Equations"
  - "cao-a2023lno"
note_type: "source"
schema_version: "research-wiki-pdf-v1"
source_id: "cao-a2023lno"
citation_key: "cao-a2023lno"
source_kind: "raw_pdf"
source_status: "compiled"
year: 2023
lead_author: "Qianying Cao$^{a"
authors:
  - "Qianying Cao$^{a"
  - "Somdatta Goswami"
  - "George Em Karniadakis$^{b"
sources:
  - "raw/Cao et al. - 2023 - LNO Laplace Neural Operator for Solving Differential Equations.pdf"
concepts:
  - "[[Diffusion Models]]"
  - "[[Large Language Models]]"
  - "[[Neural Operators]]"
  - "[[Operator Learning]]"
  - "[[Partial Differential Equations]]"
  - "[[Scientific Datasets]]"
  - "[[Scientific Machine Learning]]"
domains: []
themes:
  - "benchmarking and data curation"
section_index:
  - "LNO: Laplace Neural Operator for Solving Differential Equations"
  - "1. Introduction"
  - "2. Neural Operators"
  - "2.1. Laplace neural operator"
  - "3.2. Driven gravity pendulum"
  - "3.3. Forced Lorenz system"
  - "3.4. Euler-Bernoulli beam"
  - "3.5. Diffusion equation"
  - "*Acknowledgement*"
  - "Appendix A. Network Architectures"
tags:
  - "research/source"
  - "source/raw-pdf"
  - "transcription/vision"
  - "year/2023"
related:
  - "[[Diffusion Models]]"
  - "[[Large Language Models]]"
  - "[[Neural Operators]]"
  - "[[Operator Learning]]"
  - "[[Partial Differential Equations]]"
  - "[[Scientific Datasets]]"
  - "[[Scientific Machine Learning]]"
cache_path: "_meta/converted_sources/Cao et al. - 2023 - LNO Laplace Neural Operator for Solving Differential Equations.md"
page_image_dir: "_meta/source_page_images/cao-et-al-2023-lno-laplace-neural-operator-for-solving-differential-equa-73271882"
page_count: 19
last_compiled: 2026-04-05
---

# LNO: Laplace Neural Operator for Solving Differential Equations

> This source page is maintained by the wiki compiler so the vault can summarize, link, and query `raw/Cao et al. - 2023 - LNO Laplace Neural Operator for Solving Differential Equations.pdf` without modifying the raw source.

## Citation & Files

- Source ID: `cao-a2023lno`
- Citation key: `cao-a2023lno`
- Source kind: `raw_pdf`
- Status: `compiled`
- Raw source: `raw/Cao et al. - 2023 - LNO Laplace Neural Operator for Solving Differential Equations.pdf`
- Working text cache: `_meta/converted_sources/Cao et al. - 2023 - LNO Laplace Neural Operator for Solving Differential Equations.md`
- Page image directory: `_meta/source_page_images/cao-et-al-2023-lno-laplace-neural-operator-for-solving-differential-equa-73271882`
- Page count: `19`
- Year: `2023`
- Lead author: Qianying Cao$^{a
- Authors: Qianying Cao$^{a; Somdatta Goswami; George Em Karniadakis$^{b

## TL;DR

We introduce the Laplace neural operator (LNO), which leverages the Laplace transform to decompose the input space. Unlike the Fourier Neural Operator (FNO), LNO can handle non-periodic signals, account for transient...

## Abstract

We introduce the Laplace neural operator (LNO), which leverages the Laplace transform to decompose the input space. Unlike the Fourier Neural Operator (FNO), LNO can handle non-periodic signals, account for transient responses, and exhibit exponential convergence. LNO incorporates the pole-residue relationship between the input and the output space, enabling greater interpretability and improved generalization ability. Herein, we demonstrate the superior approximation accuracy of a single Laplace layer in LNO over four Fourier modules in FNO in approximating the solutions of three ODEs (Duffing oscillator, driven gravity pendulum, and Lorenz system) and three PDEs (Euler-Bernoulli beam, diffusion equation, and reaction-diffusion system). Notably, LNO outperforms FNO in capturing transient responses in undamped scenarios. For the linear Euler-Bernoulli beam and diffusion equation, LNO's exact representation of the pole-residue formulation yields significantly better results than FNO. For the nonlinear reaction-diffusion system, LNO's errors are smaller than those of FNO, demonstrating the effectiveness of using system poles and residues as network parameters for operator learning. Overall, our results suggest that LNO represents a promising new approach for learning neural operators that map functions between infinite-dimensional spaces. *Keywords:* Operator Learning, neural operators, Laplace transformation, transient response, pole, residue ---

## Key Concepts

- [[Diffusion Models]]
- [[Large Language Models]]
- [[Neural Operators]]
- [[Operator Learning]]
- [[Partial Differential Equations]]
- [[Scientific Datasets]]
- [[Scientific Machine Learning]]

## Research Signals

- Themes: benchmarking and data curation
- Keywords: laplace, operator, system, transient, input, space

## Reading Map

- LNO: Laplace Neural Operator for Solving Differential Equations
- 1. Introduction
- 2. Neural Operators
- 2.1. Laplace neural operator
- 3.2. Driven gravity pendulum
- 3.3. Forced Lorenz system
- 3.4. Euler-Bernoulli beam
- 3.5. Diffusion equation
- *Acknowledgement*
- Appendix A. Network Architectures

## Provenance

- Last compiled: 2026-04-05
- Schema version: `research-wiki-pdf-v1`

