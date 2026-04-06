---
title: "Multiscale Graph Neural Network Autoencoders for Interpretable Scientific Machine Learning"
aliases:
  - "Multiscale Graph Neural Network Autoencoders for Interpretable Scientific Machine Learning"
  - "barwey2023multiscale"
note_type: "source"
schema_version: "research-wiki-pdf-v1"
source_id: "barwey2023multiscale"
citation_key: "barwey2023multiscale"
source_kind: "raw_pdf"
source_status: "compiled"
year: 2023
lead_author: "Shivam Barwey"
authors:
  - "Shivam Barwey"
  - "Varun Shankar"
  - "Venkatasubramanian Viswanathan"
  - "Romit Maulik"
sources:
  - "raw/Barwey et al. - 2023 - Multiscale Graph Neural Network Autoencoders for Interpretable Scientific Machine Learning.pdf"
concepts:
  - "[[Computational Fluid Dynamics]]"
  - "[[Graph Neural Networks]]"
  - "[[Large Language Models]]"
  - "[[Multi-Physics]]"
  - "[[Partial Differential Equations]]"
  - "[[Scientific Datasets]]"
  - "[[Scientific Machine Learning]]"
  - "[[Simulation Acceleration]]"
domains:
  - "computational fluid dynamics"
themes:
  - "benchmarking and data curation"
  - "geometry and irregular domains"
  - "inverse design and optimization"
section_index:
  - "Contents"
  - "1 Introduction 2"
  - "2 Configuration and Dataset 4"
  - "3 Methodology 9"
  - "4 Results 17"
  - "4.3 Analysis of reduction factor . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22"
  - "5 Conclusion 24"
  - "6 Acknowledgements 26"
  - "1 Introduction"
  - "3 Methodology"
tags:
  - "research/source"
  - "source/raw-pdf"
  - "transcription/vision"
  - "year/2023"
related:
  - "[[Computational Fluid Dynamics]]"
  - "[[Graph Neural Networks]]"
  - "[[Large Language Models]]"
  - "[[Multi-Physics]]"
  - "[[Partial Differential Equations]]"
  - "[[Scientific Datasets]]"
  - "[[Scientific Machine Learning]]"
  - "[[Simulation Acceleration]]"
cache_path: "_meta/converted_sources/Barwey et al. - 2023 - Multiscale Graph Neural Network Autoencoders for Interpretable Scientific Machine Learning.md"
page_image_dir: "_meta/source_page_images/barwey-et-al-2023-multiscale-graph-neural-network-autoencoders-for-inter-d8f047a3"
page_count: 30
last_compiled: 2026-04-05
---

# Multiscale Graph Neural Network Autoencoders for Interpretable Scientific Machine Learning

> This source page is maintained by the wiki compiler so the vault can summarize, link, and query `raw/Barwey et al. - 2023 - Multiscale Graph Neural Network Autoencoders for Interpretable Scientific Machine Learning.pdf` without modifying the raw source.

## Citation & Files

- Source ID: `barwey2023multiscale`
- Citation key: `barwey2023multiscale`
- Source kind: `raw_pdf`
- Status: `compiled`
- Raw source: `raw/Barwey et al. - 2023 - Multiscale Graph Neural Network Autoencoders for Interpretable Scientific Machine Learning.pdf`
- Working text cache: `_meta/converted_sources/Barwey et al. - 2023 - Multiscale Graph Neural Network Autoencoders for Interpretable Scientific Machine Learning.md`
- Page image directory: `_meta/source_page_images/barwey-et-al-2023-multiscale-graph-neural-network-autoencoders-for-inter-d8f047a3`
- Page count: `30`
- Year: `2023`
- Lead author: Shivam Barwey
- Authors: Shivam Barwey; Varun Shankar; Venkatasubramanian Viswanathan; Romit Maulik

## TL;DR

The goal of this work is to address two limitations in autoencoder-based models: latent space interpretability and compatibility with unstructured meshes. This is accomplished here with the development of a novel graph...

## Abstract

The goal of this work is to address two limitations in autoencoder-based models: latent space interpretability and compatibility with unstructured meshes. This is accomplished here with the development of a novel graph neural network (GNN) autoencoding architecture with demonstrations on complex fluid flow applications. To address the first goal of interpretability, the GNN autoencoder achieves reduction in the number nodes in the encoding stage through an adaptive graph reduction procedure. This reduction procedure essentially amounts to flowfield-conditioned node sampling and sensor identification, and produces interpretable latent graph representations tailored to the flowfield reconstruction task in the form of so-called masked fields. These masked fields allow the user to (a) visualize where in physical space a given latent graph is active, and (b) interpret the time-evolution of the latent graph connectivity in accordance with the time-evolution of unsteady flow features (e.g. recirculation zones, shear layers) in the domain. To address the goal of unstructured mesh compatibility, the autoencoding architecture utilizes a series of multi-scale message passing (MMP) layers, each of which models information exchange among node neighborhoods at various lengthscales. The MMP layer, which augments standard single-scale message passing with learnable coarsening operations, allows the decoder to more efficiently reconstruct the flowfield from the identified regions in the masked fields. Analysis of latent graphs produced by the autoencoder for various model settings are condu

## Key Concepts

- [[Computational Fluid Dynamics]]
- [[Graph Neural Networks]]
- [[Large Language Models]]
- [[Multi-Physics]]
- [[Partial Differential Equations]]
- [[Scientific Datasets]]
- [[Scientific Machine Learning]]
- [[Simulation Acceleration]]

## Research Signals

- Domains: computational fluid dynamics
- Themes: benchmarking and data curation, geometry and irregular domains, inverse design and optimization
- Keywords: graph, latent, goal, this, address, reduction

## Reading Map

- Contents
- 1 Introduction 2
- 2 Configuration and Dataset 4
- 3 Methodology 9
- 4 Results 17
- 4.3 Analysis of reduction factor . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 22
- 5 Conclusion 24
- 6 Acknowledgements 26
- 1 Introduction
- 3 Methodology

## Provenance

- Last compiled: 2026-04-05
- Schema version: `research-wiki-pdf-v1`

