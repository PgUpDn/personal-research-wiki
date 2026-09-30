#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENV_SITE_PACKAGES = sorted((PROJECT_ROOT / ".venv/lib").glob("python*/site-packages"), reverse=True)
if VENV_SITE_PACKAGES:
    sys.path.insert(0, str(VENV_SITE_PACKAGES[0]))

import pymupdf
import anthropic


DEFAULT_ROOT = PROJECT_ROOT
CONFIG_PATH = Path("_meta/config.json")
CLIPPING_MERMAID_SOURCES_PATH = Path("_meta/clipping_mermaid_sources.json")
SCHEMA_VERSION = "research-wiki-pdf-v1"

STOPWORDS = {
    "about",
    "across",
    "after",
    "agent",
    "agents",
    "approach",
    "based",
    "between",
    "beyond",
    "case",
    "characterizing",
    "collection",
    "comprehensive",
    "computational",
    "data",
    "deep",
    "design",
    "discovery",
    "driven",
    "enabled",
    "enhancing",
    "evaluation",
    "framework",
    "from",
    "general",
    "high",
    "human",
    "improved",
    "large",
    "learning",
    "machine",
    "method",
    "model",
    "models",
    "neural",
    "novel",
    "open",
    "paper",
    "partial",
    "physics",
    "prediction",
    "problems",
    "research",
    "review",
    "robust",
    "scale",
    "science",
    "scientific",
    "simulation",
    "simulations",
    "solver",
    "solvers",
    "study",
    "systems",
    "the",
    "through",
    "towards",
    "using",
    "with",
    "also",
    "been",
    "could",
    "have",
    "into",
    "more",
    "most",
    "only",
    "other",
    "over",
    "should",
    "some",
    "such",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "what",
    "when",
    "where",
    "which",
    "while",
    "will",
    "would",
}

AFFILIATION_HINTS = {
    "university",
    "corporation",
    "department",
    "institute",
    "laboratory",
    "school",
    "college",
    "center",
    "centre",
    "lab",
    "group",
    "corresponding author",
}

ORGANIZATION_HINTS = {
    "amazon",
    "aws",
    "deepmind",
    "google",
    "google research",
    "nvidia",
    "research",
    "services",
    "gmbh",
    "inc",
    "ltd",
    "llc",
    "laboratories",
}

ADDRESS_HINTS = {
    "street",
    "st.",
    "road",
    "rd.",
    "avenue",
    "ave.",
    "viaduct",
    "lane",
    "boulevard",
    "blvd",
    "po box",
    "box",
    "suite",
    "building",
    "tel.",
    "e-mail",
    "email",
}

PERSON_CONNECTORS = {
    "a",
    "al",
    "bin",
    "da",
    "de",
    "del",
    "den",
    "der",
    "di",
    "dos",
    "du",
    "la",
    "le",
    "van",
    "von",
}

VENUE_KEYWORDS = {
    "advances",
    "archive",
    "conference",
    "environment",
    "journal",
    "letters",
    "materials",
    "nature",
    "physics",
    "preprint",
    "proceedings",
    "review",
    "science",
    "scientific",
    "society",
    "transactions",
}

CACHE_SCAFFOLD_HEADINGS = {
    "Conversion Snapshot",
    "Preview",
    "Extracted Markdown",
    "Source Page Images",
}

SUPERSCRIPT_TRANSLATION = str.maketrans("", "", "¹²³⁴⁵⁶⁷⁸⁹⁰†‡✉*\\")

GENERIC_HEADER_LINES = {
    "abstract",
    "article info",
    "contents lists available at sciencedirect",
    "conversion snapshot",
    "copyright",
    "extracted markdown",
    "journal homepage",
    "keywords",
    "perspective",
    "preview",
    "received",
    "research article",
}

WEAK_METADATA_HINTS = {"group", "lab", "inc"}

CONCEPTS = [
    {
        "slug": "scientific-machine-learning",
        "title": "Scientific Machine Learning",
        "group": "Core Methods",
        "description": "the umbrella area where machine learning is used to model, accelerate, or guide scientific simulation, design, and discovery workflows",
        "aliases": ["scientific machine learning", "sciml", "physical scientific discovery"],
        "related": ["simulation-acceleration", "surrogate-models", "foundation-models"],
    },
    {
        "slug": "partial-differential-equations",
        "title": "Partial Differential Equations",
        "group": "Core Methods",
        "description": "the governing equations that many of the sources try to solve, emulate, or invert with learned methods",
        "aliases": ["partial differential equations", "partial differential equation", "pdes", "pde"],
        "related": ["neural-operators", "physics-informed-neural-networks", "operator-learning"],
    },
    {
        "slug": "operator-learning",
        "title": "Operator Learning",
        "group": "Core Methods",
        "description": "learning mappings between fields or boundary conditions so that entire families of PDE solutions can be predicted efficiently",
        "aliases": ["operator learning", "operator-learning", "learned operator", "neural operator"],
        "related": ["neural-operators", "partial-differential-equations", "simulation-acceleration"],
    },
    {
        "slug": "neural-operators",
        "title": "Neural Operators",
        "group": "Core Methods",
        "description": "architectures that approximate solution operators for PDEs and related physical systems instead of predicting a single state at a time",
        "aliases": ["neural operator", "neural operators", "fourier neural operator", "laplace neural operator", "gnot", "transolver", "rigno"],
        "related": ["operator-learning", "partial-differential-equations", "transformers"],
    },
    {
        "slug": "physics-informed-neural-networks",
        "title": "Physics-Informed Neural Networks",
        "group": "Core Methods",
        "description": "networks constrained by physical laws, residual losses, or differentiable simulators so learning stays consistent with governing equations",
        "aliases": ["physics-informed neural network", "physics-informed neural networks", "pinn", "pinns", "physics informed"],
        "related": ["partial-differential-equations", "neural-operators", "surrogate-models"],
    },
    {
        "slug": "surrogate-models",
        "title": "Surrogate Models",
        "group": "Core Methods",
        "description": "approximate models that replace expensive simulation loops in prediction, optimization, and design tasks",
        "aliases": ["surrogate model", "surrogate models", "surrogate modeling", "surrogate"],
        "related": ["simulation-acceleration", "inverse-design", "uncertainty-quantification"],
    },
    {
        "slug": "simulation-acceleration",
        "title": "Simulation Acceleration",
        "group": "Core Methods",
        "description": "speeding up expensive numerical workflows by replacing or augmenting parts of the solver stack with learned approximations",
        "aliases": ["accelerating scientific simulations", "accelerating", "fast approximate solver", "simulation acceleration", "ai physics", "accelerated computing", "gpu accelerated solver", "gpu accelerated solvers"],
        "related": ["surrogate-models", "neural-operators", "scientific-machine-learning"],
    },
    {
        "slug": "graph-neural-networks",
        "title": "Graph Neural Networks",
        "group": "Model Families",
        "description": "message-passing models used to represent meshes, particles, and relational scientific systems with irregular connectivity",
        "aliases": ["graph neural network", "graph neural networks", "gnn", "gnns", "message passing", "geometric deep learning"],
        "related": ["meshgraphnets", "geometry-aware-learning", "scientific-machine-learning"],
    },
    {
        "slug": "meshgraphnets",
        "title": "MeshGraphNets",
        "group": "Model Families",
        "description": "graph-based simulators that operate on meshes to learn dynamics and steady-state behavior in physical systems",
        "aliases": ["meshgraphnets", "mesh graph nets", "mesh-based simulation", "mesh-based gnn"],
        "related": ["graph-neural-networks", "partial-differential-equations", "computational-fluid-dynamics"],
    },
    {
        "slug": "transformers",
        "title": "Transformers",
        "group": "Model Families",
        "description": "attention-based architectures adapted for operator learning, world modeling, sequence reasoning, and scientific representation learning",
        "aliases": ["transformer", "transformers", "attention", "operator transformer"],
        "related": ["neural-operators", "foundation-models", "world-models"],
    },
    {
        "slug": "diffusion-models",
        "title": "Diffusion Models",
        "group": "Model Families",
        "description": "generative models used for structure synthesis, inverse design, probabilistic emulation, and uncertainty-aware generation",
        "aliases": ["diffusion model", "diffusion models", "diffusion", "latent diffusion", "flow matching"],
        "related": ["generative-models", "inverse-design", "uncertainty-quantification"],
    },
    {
        "slug": "generative-models",
        "title": "Generative Models",
        "group": "Model Families",
        "description": "models that synthesize candidate structures, trajectories, or simulations rather than only predicting a scalar target",
        "aliases": ["generative model", "generative models", "generative", "gan", "dcgan"],
        "related": ["diffusion-models", "inverse-design", "materials-design"],
    },
    {
        "slug": "foundation-models",
        "title": "Foundation Models",
        "group": "Model Families",
        "description": "large pretrained models proposed as reusable backbones for scientific reasoning, simulation, and design tasks across domains",
        "aliases": ["foundation model", "foundation models", "large physics models", "domain-adapted llms", "pretrained"],
        "related": ["large-language-models", "pretraining-and-transfer-learning", "scientific-machine-learning"],
    },
    {
        "slug": "pretraining-and-transfer-learning",
        "title": "Pretraining and Transfer Learning",
        "group": "Model Families",
        "description": "reusing representations, scaling laws, and domain adaptation techniques so models generalize across scientific tasks and datasets",
        "aliases": ["pretraining", "pre-training", "transfer learning", "domain-adaptive pretraining", "domain adapted"],
        "related": ["foundation-models", "benchmarks-and-evaluation", "scientific-datasets"],
    },
    {
        "slug": "large-language-models",
        "title": "Large Language Models",
        "group": "Agents and Reasoning",
        "description": "language-centric models used as interfaces, planners, code generators, and scientific assistants in simulation-heavy workflows",
        "aliases": ["large language model", "large language models", "language model", "language models", "llm", "llms", "chatgpt", "deepseek", "claude"],
        "related": ["ai-agents", "multi-agent-systems", "foundation-models"],
    },
    {
        "slug": "ai-agents",
        "title": "AI Agents",
        "group": "Agents and Reasoning",
        "description": "autonomous or semi-autonomous systems that use tools, memory, or planning loops to execute scientific tasks end to end",
        "aliases": ["ai agent", "ai agents", "agentic", "agentic ai", "language agent", "language agents", "autonomous", "autonomous visualization agent", "research assistants", "co-scientist", "ai co-scientist"],
        "related": ["large-language-models", "multi-agent-systems", "control-and-automation"],
    },
    {
        "slug": "multi-agent-systems",
        "title": "Multi-Agent Systems",
        "group": "Agents and Reasoning",
        "description": "coordinated collections of agents used to divide planning, coding, verification, or design responsibilities across complex tasks",
        "aliases": ["multi-agent", "multi agent", "multi-agent systems", "multi modal multi-agent", "mixture-of-agents"],
        "related": ["ai-agents", "large-language-models", "scientific-discovery"],
    },
    {
        "slug": "collective-intelligence",
        "title": "Collective Intelligence",
        "group": "Agents and Reasoning",
        "description": "how groups of agents, people, or animals coordinate, communicate, and solve problems through emergent cooperation rather than individual reasoning alone",
        "aliases": [
            "collective intelligence",
            "collective cognition",
            "group cognition",
            "multi-agent collaboration",
            "collaborative scaling law",
            "small-world collaboration",
            "embodied multi-agent cooperation",
            "cooperative transport",
            "consensus decisions",
            "collaborative interactions",
        ],
        "related": ["multi-agent-systems", "ai-agents", "benchmarks-and-evaluation"],
    },
    {
        "slug": "world-models",
        "title": "World Models",
        "group": "Agents and Reasoning",
        "description": "learned internal models of dynamics or environment structure used for reasoning, prediction, and planning",
        "aliases": ["world model", "world models", "dynamical systems", "planning"],
        "related": ["transformers", "ai-agents", "scientific-discovery"],
    },
    {
        "slug": "scientific-discovery",
        "title": "Scientific Discovery",
        "group": "Agents and Reasoning",
        "description": "using learned models, symbolic search, and autonomous systems to uncover equations, structures, or new scientific hypotheses",
        "aliases": ["scientific discovery", "discovery", "discovering governing equations", "equation discovery"],
        "related": ["symbolic-regression", "ai-agents", "foundation-models"],
    },
    {
        "slug": "symbolic-regression",
        "title": "Symbolic Regression",
        "group": "Agents and Reasoning",
        "description": "recovering interpretable equations or laws from data with sparse search, program synthesis, or language-model-guided exploration",
        "aliases": ["symbolic regression", "sparse identification", "sindy", "equation discovery"],
        "related": ["scientific-discovery", "world-models", "large-language-models"],
    },
    {
        "slug": "active-learning",
        "title": "Active Learning",
        "group": "Optimization and Search",
        "description": "adaptive data collection where models choose the next experiments or simulations that are most informative",
        "aliases": ["active learning", "hierarchical active learning", "active inference"],
        "related": ["autonomous-experimentation", "surrogate-models", "scientific-datasets"],
    },
    {
        "slug": "reinforcement-learning",
        "title": "Reinforcement Learning",
        "group": "Optimization and Search",
        "description": "sequential decision-making methods used for design search, mesh generation, planning, and control under feedback",
        "aliases": ["reinforcement learning", "soft actor critic", "trial-and-error learning"],
        "related": ["ai-agents", "world-models", "control-and-automation"],
    },
    {
        "slug": "inverse-design",
        "title": "Inverse Design",
        "group": "Optimization and Search",
        "description": "working backward from desired physical behavior to candidate structures, parameters, or geometries",
        "aliases": ["inverse design", "inverse-design", "design optimization", "optimization"],
        "related": ["generative-models", "surrogate-models", "metasurfaces"],
    },
    {
        "slug": "uncertainty-quantification",
        "title": "Uncertainty Quantification",
        "group": "Optimization and Search",
        "description": "estimating confidence, variability, or probabilistic structure in learned predictions so models remain useful in high-stakes workflows",
        "aliases": ["uncertainty quantification", "probabilistic", "mixture density", "confidence"],
        "related": ["surrogate-models", "diffusion-models", "benchmarks-and-evaluation"],
    },
    {
        "slug": "geometry-aware-learning",
        "title": "Geometry-Aware Learning",
        "group": "Optimization and Search",
        "description": "methods that explicitly encode mesh structure, shapes, manifolds, or irregular domains so learned solvers generalize beyond regular grids",
        "aliases": ["geometry aware", "geometry-aware", "geometric priors", "equivariant deep learning", "irregular domains", "general geometries", "shape representations", "surfaces"],
        "related": ["graph-neural-networks", "meshgraphnets", "neural-operators"],
    },
    {
        "slug": "computational-fluid-dynamics",
        "title": "Computational Fluid Dynamics",
        "group": "Application Domains",
        "description": "fluid simulation and aerodynamic modeling, often used as a benchmark domain for surrogate learning and agentic automation",
        "aliases": ["computational fluid dynamics", "cfd", "fluid dynamics", "aerodynamic", "drivaer", "openfoam"],
        "related": ["neural-operators", "surrogate-models", "ai-agents"],
    },
    {
        "slug": "electromagnetics",
        "title": "Electromagnetics",
        "group": "Application Domains",
        "description": "electromagnetic field modeling, wave propagation, and solver acceleration for optics, Maxwell systems, and device design",
        "aliases": ["electromagnetic", "electromagnetics", "wave propagation", "photoacoustic", "fdtd"],
        "related": ["maxwell-equations", "metasurfaces", "nanophotonics"],
    },
    {
        "slug": "maxwell-equations",
        "title": "Maxwell Equations",
        "group": "Application Domains",
        "description": "the governing equations behind many optics and electromagnetics papers in the collection, especially inverse problems and fast solvers",
        "aliases": ["maxwell", "maxwell equations", "maxwell's equations"],
        "related": ["electromagnetics", "metasurfaces", "neural-operators"],
    },
    {
        "slug": "metasurfaces",
        "title": "Metasurfaces",
        "group": "Application Domains",
        "description": "engineered surfaces whose optical or electromagnetic response is designed with inverse methods, differentiable solvers, or generative models",
        "aliases": ["metasurface", "metasurfaces", "meta-optics", "meta optics", "meta-atom", "huygens"],
        "related": ["nanophotonics", "inverse-design", "electromagnetics"],
    },
    {
        "slug": "nanophotonics",
        "title": "Nanophotonics",
        "group": "Application Domains",
        "description": "small-scale photonic structure design where differentiable simulation and learned surrogates are used to optimize optical behavior",
        "aliases": ["nanophotonic", "nanophotonics", "photonic", "photonics", "optoelectronics"],
        "related": ["metasurfaces", "inverse-design", "electromagnetics"],
    },
    {
        "slug": "materials-design",
        "title": "Materials Design",
        "group": "Application Domains",
        "description": "using learned representations, active learning, and generative methods to search material compositions and microstructures",
        "aliases": ["materials design", "materials", "material science", "alloy", "material fracture", "polycrystalline", "microstructure", "inconel", "elastoplastic", "dislocation", "diffraction", "metals", "metamaterial", "metamaterials"],
        "related": ["autonomous-experimentation", "generative-models", "foundation-models"],
    },
    {
        "slug": "semiconductor-design",
        "title": "Semiconductor Design",
        "group": "Application Domains",
        "description": "chip, TCAD, packaging, and placement workflows where domain-adapted models and surrogates are used to guide design decisions",
        "aliases": ["semiconductor", "chip", "tcad", "placement", "integrated circuits", "electronic packaging", "wafer", "physical vapor deposition"],
        "related": ["foundation-models", "surrogate-models", "control-and-automation"],
    },
    {
        "slug": "control-and-automation",
        "title": "Control and Automation",
        "group": "Application Domains",
        "description": "closed-loop decision making in industrial, robotic, or process environments, often supported by agents, world models, and learned simulators",
        "aliases": ["control", "industrial automation", "closed-loop", "plc", "automation"],
        "related": ["ai-agents", "reinforcement-learning", "digital-twins"],
    },
    {
        "slug": "digital-twins",
        "title": "Digital Twins",
        "group": "Application Domains",
        "description": "virtual counterparts of real systems that combine simulation, sensing, and adaptation for monitoring or control",
        "aliases": ["digital twin", "digital twins", "virtual sensing", "virtual sensor", "soft sensor"],
        "related": ["control-and-automation", "scientific-machine-learning", "active-learning"],
    },
    {
        "slug": "multi-physics",
        "title": "Multi-Physics",
        "group": "Application Domains",
        "description": "coupled physical systems where learned models must account for interacting mechanisms across multiple scales or modalities",
        "aliases": ["multiphysics", "multi-physics", "coupled physics", "coupled multiphysics", "multi-scale"],
        "related": ["partial-differential-equations", "neural-operators", "scientific-machine-learning"],
    },
    {
        "slug": "autonomous-experimentation",
        "title": "Autonomous Experimentation",
        "group": "Data and Evaluation",
        "description": "systems that plan, run, and refine experiments or synthesis loops with minimal human intervention",
        "aliases": ["autonomous experimentation", "autonomous materials synthesis", "virtual lab"],
        "related": ["active-learning", "materials-design", "ai-agents"],
    },
    {
        "slug": "scientific-datasets",
        "title": "Scientific Datasets",
        "group": "Data and Evaluation",
        "description": "shared corpora of simulations, measurements, or tasks that support training and comparison across scientific ML methods",
        "aliases": ["dataset", "datasets", "benchmark dataset", "collection of diverse physics simulations", "plaid", "the well", "wavebench"],
        "related": ["benchmarks-and-evaluation", "pretraining-and-transfer-learning", "scientific-machine-learning"],
    },
    {
        "slug": "benchmarks-and-evaluation",
        "title": "Benchmarks and Evaluation",
        "group": "Data and Evaluation",
        "description": "datasets, suites, and empirical studies that compare scientific models on generalization, fidelity, and task coverage",
        "aliases": ["benchmark", "benchmarks", "evaluation", "benchmarking", "comprehensive evaluation", "comparative study"],
        "related": ["scientific-datasets", "pretraining-and-transfer-learning", "uncertainty-quantification"],
    },
    {
        "slug": "interpretability",
        "title": "Interpretability",
        "group": "Data and Evaluation",
        "description": "methods and tests for explaining what a learned scientific model represents and relies on, from interpretable architectures and symbolic read-outs to probing, decodability and counterfactual checks of mechanistic use",
        "aliases": ["interpretability", "interpretable", "mechanistic interpretability", "mechanistic fidelity", "decodability", "linear probe", "probing classifier", "counterfactual fidelity", "kolmogorov-arnold", "explainable ai", "explainability"],
        "related": ["symbolic-regression", "benchmarks-and-evaluation", "scientific-machine-learning"],
    },
    {
        "slug": "cad-and-geometry-models",
        "title": "CAD and Geometry Models",
        "group": "Data and Evaluation",
        "description": "geometry-centric representations and datasets that connect visual or CAD interfaces to downstream simulation-ready assets",
        "aliases": ["cad", "geometry model", "large geometry model", "3d assets", "simulation-ready 3d assets"],
        "related": ["geometry-aware-learning", "inverse-design", "generative-models"],
    },
    {
        "slug": "engineering-drawing-understanding",
        "title": "Engineering Drawing Understanding",
        "group": "Data and Evaluation",
        "description": "extracting geometry, dimensions, annotations, and cross-view relationships from engineering drawings while retaining traceable evidence and unresolved ambiguity",
        "aliases": ["engineering drawing understanding", "2d drawing understanding", "2d drawings", "engineering drawings", "drawing-to-model", "2d to 3d"],
        "related": ["cad-and-geometry-models", "geometry-aware-learning", "control-and-automation", "visual-pair-review-harness", "provenance-legend"],
    },
    {
        "slug": "classification-society-fe-contract",
        "title": "Classification Society FE Contract",
        "group": "Application Domains",
        "description": "the geometry, loading, corrosion, meshing, provenance, and review requirements that connect marine structural models to classification-ready finite-element analysis",
        "aliases": ["classification society fe contract", "classification society", "iacs csr", "cargo hold fe analysis", "sesam genie", "ocx approval", "class society", "class FE", "classification society FE", "FE contract", "net scantling", "mesh size s x s", "1+1+1 model", "eccentric beam"],
        "related": ["cad-and-geometry-models", "simulation-acceleration", "digital-twins"],
    },
    {
        "slug": "harness-engineering",
        "title": "Harness Engineering",
        "group": "Agents and Reasoning",
        "description": "designing repositories, tests, tools, context, and feedback loops so coding agents can execute substantial engineering work reliably",
        "aliases": ["harness engineering", "agent harness", "agent-first engineering", "coding agent", "full software engineer", "pin history", "seed baseline", "operator pin history"],
        "related": ["ai-agents", "large-language-models", "control-and-automation", "visual-pair-review-harness", "provenance-legend"],
    },
    {
        "slug": "visual-pair-review-harness",
        "title": "Visual-Pair Review Harness",
        "group": "Agents and Reasoning",
        "description": "a recall gate for extraction pipelines: rendering the same window of a source drawing and of the derived model at the same isotropic scale, verifying the renderer numerically before any comparison, collapsing identical stations by pixel identity, reading in band crops, having one comparator per pair and two independent adversarial verifiers per finding, synthesizing confirmed findings into mechanisms, and versioning the evidence set so every finding records the render version it was made against",
        "aliases": ["visual-pair review harness", "drawing-vs-model visual pair review", "visual pair review", "visual pair probe", "section pair probe", "drawing-vs-model pair review", "recall gate", "pair probe", "pair review", "framing check", "station renders", "known-omission list"],
        "related": ["harness-engineering", "engineering-drawing-understanding", "ai-agents", "multi-agent-systems", "cad-and-geometry-models", "provenance-legend"],
    },
    {
        "slug": "provenance-legend",
        "title": "Provenance Legend",
        "group": "Agents and Reasoning",
        "description": "a per-object evidence grading for models extracted from drawings: a value axis (where the number came from) and a geometry axis (whether extent, position and cuts rest on drawn entities, a disclosed approximation or an open ledger item), fill level = the worse axis (drawn here / drawn rule or measured transfer or disclosed approximation / assumed or open) refined into eight dominant-reason classes, an edge channel recording whether a human pair-reviewed the object at its current geometry, computed from an exact-token vocabulary that raises on unknown tokens plus a station- and document-scoped open-items index and a visual review ledger, and gated by input-sensitive checks proven fallible by mutation",
        "aliases": ["provenance legend", "evidence-level colouring", "evidence-level coloring", "three-level legend", "value axis geometry axis", "worse-axis rule", "provenance level", "open-items index", "visual review ledger", "exact-token vocabulary"],
        "related": ["visual-pair-review-harness", "harness-engineering", "engineering-drawing-understanding", "multi-agent-systems", "cad-and-geometry-models"],
    },
    {
        "slug": "render-registered-reconstruction",
        "title": "Render-Registered Reconstruction",
        "group": "Data and Evaluation",
        "description": "rebuilding a structure part by part from official whole-body renders: one pinhole camera per view family from vanishing points and known 3D curves, a joint bundle adjustment on shared tie points picked by independent raters and official datum holes with metric constraints (skin-free evidence shapes the cameras, the skin only translates them), each part carved on a named support surface with one parameter measured from the render, trimmed by the other views' visual hull with the camera-uncertainty margin, and scored by a render fidelity audit (per-page IoU, depth-order agreement, uncovered-steel blobs) that stays a proxy while an independent render-pair reviewer is the truth gate",
        "aliases": ["render-registered reconstruction", "reconstruction from official renders", "bundle adjustment with datum constraints", "tie points", "highlight carving", "support-surface carving", "visual hull trim", "page iou", "depth-order agreement", "camera resection", "resection of single renders", "held-out gate", "member ribbon", "near and far page iou"],
        "related": ["cad-and-geometry-models", "visual-pair-review-harness", "provenance-legend", "harness-engineering", "engineering-drawing-understanding", "multi-agent-systems"],
    },
]

CONCEPTS_BY_SLUG = {concept["slug"]: concept for concept in CONCEPTS}

DOMAIN_PATTERNS = {
    "computational fluid dynamics": ["cfd", "fluid", "aerodynamic", "drivaer", "openfoam", "vehicle"],
    "electromagnetics and optics": ["electromagnetic", "maxwell", "photonic", "meta-optics", "metasurface", "fdtd", "wave"],
    "materials and chemistry": ["material", "alloy", "polycrystalline", "fracture", "microstructure", "inorganic"],
    "semiconductor systems": ["chip", "semiconductor", "tcad", "placement", "integrated circuit", "packaging"],
    "agents and automation": ["agent", "agentic", "autonomous", "planning", "assistant"],
}

THEME_PATTERNS = {
    "benchmarking and data curation": ["benchmark", "dataset", "evaluation", "comparative", "corpus"],
    "coordination and cooperation": [
        "collective intelligence",
        "collective cognition",
        "multi-agent collaboration",
        "cooperative transport",
        "consensus decisions",
        "collaborative interactions",
        "embodied multi-agent cooperation",
    ],
    "geometry and irregular domains": ["geometry", "mesh", "surface", "irregular", "shape"],
    "inverse design and optimization": ["inverse design", "optimization", "design", "generative"],
    "scaling and transfer": ["scaling", "transfer", "pretraining", "foundation", "domain-adapted"],
    "physics-guided learning": ["physics informed", "physics-guided", "differentiable", "residual", "equilibrium"],
}

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
FENCED_MARKDOWN_BLOCK_RE = re.compile(
    r"(?ms)^(?P<fence>`{3,}|~{3,})[^\n]*\n(?P<body>.*?)\n(?P=fence)[ \t]*$"
)
MERMAID_RENDER_ARTIFACT_MARKERS = (
    "#mermaid-",
    "@keyframes edge-animation-frame",
    ".edge-animation-slow",
    ".edge-animation-fast",
    ".mindmap-node-label",
    ".flowchart-link",
    "--mermaid-font-family",
    ".marker.cross",
    ".edgepattern",
)
MERMAID_ESCAPED_FENCE_RE = re.compile(r"```mermaid\\n(.*?)\\n```", re.IGNORECASE | re.DOTALL)
MERMAID_LITERAL_FENCE_RE = re.compile(r"```mermaid[ \t]*\r?\n(.*?)\r?\n```", re.IGNORECASE | re.DOTALL)
MERMAID_DIAGRAM_PREFIXES = (
    "architecture",
    "block",
    "classdiagram",
    "erdiagram",
    "flowchart",
    "gantt",
    "gitgraph",
    "graph",
    "journey",
    "kanban",
    "mindmap",
    "packet",
    "pie",
    "quadrantchart",
    "radar",
    "requirementdiagram",
    "sankey",
    "sequencediagram",
    "statediagram",
    "timeline",
    "treemap",
    "xychart",
    "zenuml",
)
CLIPPING_SANITIZATION_PIPELINE = "clipper-mermaid-reconstruction-v2"


def load_config(root: Path) -> dict[str, Any]:
    config_file = root / CONFIG_PATH
    if config_file.exists():
        return json.loads(config_file.read_text(encoding="utf-8"))
    return {
        "project_root": ".",
        "raw_dir": "raw",
        "source_dirs": ["raw", "Clippings"],
        "wiki_dir": "wiki",
        "concepts_dir": "wiki/concepts",
        "curated_dir": "wiki/curated",
        "source_notes_dir": "wiki/sources",
        "derived_wiki_dir": "wiki/derived",
        "projects_dir": "wiki/projects",
        "output_dir": "output",
        "html_dir": "output/html",
        "okf_dir": "output/okf",
        "okf_archive": "output/research-wiki-okf.zip",
        "okf_active_project_stale_days": 90,
        "answers_dir": "output/answers",
        "slides_dir": "output/slides",
        "charts_dir": "output/charts",
        "reports_dir": "output/reports",
        "archive_dir": "_meta/original_pdfs",
        "converted_sources_dir": "_meta/converted_sources",
        "generated_images_dir": "_meta/source_page_images",
        "state_file": "_meta/compile_state.json",
        "lint_report_path": "wiki/LINT_AND_HEAL.md",
        "system_overview_path": "wiki/SYSTEM_OVERVIEW.md",
        "page_formats_path": "wiki/PAGE_FORMATS.md",
        "paper_template_path": "wiki/PAPER_TEMPLATE.md",
        "log_path": "wiki/LOG.md",
        "schema_path": "AGENTS.md",
        "watch_interval_seconds": 15,
        "venv_python": ".venv/bin/python",
        "pdf_conversion_backend": "markitdown",
        "markitdown_cli": ".venv/bin/markitdown",
        "tex_conversion_backend": "pandoc",
        "pandoc_bin": "pandoc",
        "node_bin": "node",
        "pdf2md_entrypoint": "_meta/node_tools/pdf2md/node_modules/pdf2md/bin/index.js",
        "pdf2md_workspace_dir": "_meta/pdf2md_work",
        "raw_images_dir": "raw/images",
        "sanitized_clippings_dir": "_meta/converted_sources/_sanitized_clippings",
        "zotero_data_dir": "~/Zotero",
        "zotero_import_dir": "raw/zotero",
        "zotero_report_dir": "_meta/zotero_imports",
        "zotero_linked_attachment_base_dir": "",
        "claude_api_env": "ANTHROPIC_API_KEY",
        "claude_api_key_file": "",
        "claude_api_base": "https://api.anthropic.com/v1/messages",
        "claude_model": "claude-sonnet-4-6",
        "claude_max_tokens": 3500,
        "claude_page_batch_size": 8,
        "qa_provider": "codex-subscription",
        "codex_cli": "codex",
        "qa_timeout_seconds": 300,
        "qa_context_char_limit": 180000,
        "qa_top_concepts": 14,
    }


def ensure_project_dirs(root: Path) -> None:
    config = load_config(root)
    for source_dir in configured_source_dirs(root):
        source_dir.mkdir(parents=True, exist_ok=True)
    for key in (
        "wiki_dir",
        "concepts_dir",
        "source_notes_dir",
        "derived_wiki_dir",
        "projects_dir",
        "output_dir",
        "html_dir",
        "okf_dir",
        "answers_dir",
        "slides_dir",
        "charts_dir",
        "reports_dir",
        "archive_dir",
        "converted_sources_dir",
        "generated_images_dir",
        "raw_images_dir",
        "pdf2md_workspace_dir",
    ):
        (root / config[key]).mkdir(parents=True, exist_ok=True)
    (root / "_meta").mkdir(parents=True, exist_ok=True)


def today_string() -> str:
    return datetime.now().date().isoformat()


def timestamp_string() -> str:
    return datetime.now().isoformat(timespec="seconds")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_page_title(title: str) -> str:
    cleaned = normalize_text(title)
    cleaned = cleaned.replace("|", " ").replace("\uFF5C", " ")
    return normalize_text(cleaned).strip(" -") or "Untitled source"


def normalize_for_match(text: str) -> str:
    lowered = text.lower().replace("'", "")
    collapsed = re.sub(r"[^a-z0-9]+", " ", lowered)
    squashed = re.sub(r"\s+", " ", collapsed).strip()
    return f" {squashed} "


def slugify(text: str) -> str:
    lowered = text.lower().replace("&", " and ")
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def short_hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def trim_summary(text: str, limit: int = 220) -> str:
    normalized = normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    shortened = normalized[:limit].rsplit(" ", 1)[0].strip()
    return (shortened or normalized[:limit]).rstrip(" .,;:") + "..."


def trim_abstract_for_card(text: str, sentence_limit: int = 3, char_limit: int = 700) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return ""
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", normalized) if part.strip()]
    selected = []
    for sentence in sentences:
        candidate = " ".join(selected + [sentence]).strip()
        if selected and len(candidate) > char_limit:
            break
        selected.append(sentence)
        if len(selected) >= sentence_limit:
            break
    compact = " ".join(selected).strip() or normalized
    if len(compact) <= char_limit:
        return compact
    shortened = compact[:char_limit].rsplit(" ", 1)[0].strip()
    return (shortened or compact[:char_limit]).rstrip(" .,;:") + "..."


def compact_author_metadata(profile: dict[str, Any]) -> tuple[str | None, list[str]]:
    authors = list(profile.get("authors", []))
    if not authors:
        return None, []
    if len(authors) <= 4:
        return "; ".join(authors), []
    lead_author = profile.get("lead_author") or authors[0]
    return f"{lead_author} et al.", authors


def compact_citation_lines(profile: dict[str, Any]) -> list[str]:
    citation_bits = []
    lead_author = profile.get("lead_author")
    year = profile.get("year")
    venue = profile.get("venue")
    citation_key = profile.get("citation_key")
    source_kind = profile.get("source_kind")
    source_status = profile.get("source_status")

    if lead_author:
        author_text = lead_author if len(profile.get("authors", [])) <= 1 else f"{lead_author} et al."
        citation_bits.append(author_text)
    if year:
        citation_bits.append(f"({year})")
    if venue:
        citation_bits.append(venue)
    if citation_key:
        citation_bits.append(f"`{citation_key}`")

    identifier_bits = []
    if profile.get("doi"):
        identifier_bits.append(f"DOI `{profile['doi']}`")
    if profile.get("arxiv_id"):
        identifier_bits.append(f"arXiv `{profile['arxiv_id']}`")
    if source_kind or source_status:
        record_bits = [bit for bit in [source_kind, source_status] if bit]
        if record_bits:
            identifier_bits.append(" / ".join(record_bits))

    github_links = profile.get("github_links", [])
    code_bits = [f"[{github_link_label(url)}]({url})" for url in github_links]

    asset_bits = []
    if profile.get("content_path") and profile["content_path"] != profile["source"]:
        asset_bits.append(f"cache `{profile['content_path']}`")
    if profile.get("page_image_dir"):
        page_label = f"{profile['page_count']} pages" if profile.get("page_count") else "page images"
        asset_bits.append(f"{page_label} `{profile['page_image_dir']}`")

    lines = []
    if citation_bits:
        lines.append(f"- Citation: {' · '.join(citation_bits)}")
    author_summary, _ = compact_author_metadata(profile)
    if author_summary:
        lines.append(f"- Authors: {author_summary}")
    if identifier_bits:
        lines.append(f"- Identifiers: {' · '.join(identifier_bits)}")
    if code_bits:
        lines.append(f"- Code: {' · '.join(code_bits)}")
    source_files = profile.get("source_files", [profile["source"]])
    source_label = "Sources" if len(source_files) > 1 else "Source"
    lines.append(f"- {source_label}: " + " · ".join(f"`{path}`" for path in source_files))
    if asset_bits:
        lines.append(f"- Assets: {' · '.join(asset_bits)}")
    return lines


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def source_title_identity(profile: dict[str, Any]) -> str:
    title = normalize_for_match(str(profile.get("title", ""))).strip()
    title = re.sub(r"\s+[0-9a-f]{8}$", "", title)
    meaningful_tokens = [token for token in title.split() if len(token) >= 3]
    if len(meaningful_tokens) < 3 or title.startswith("source "):
        return f"source:{profile.get('source', '')}"
    return title


def source_profile_quality(profile: dict[str, Any]) -> tuple[int, int, int, str]:
    source_kind_score = {"raw_tex": 3, "raw_pdf": 2, "raw_markdown": 1}.get(
        str(profile.get("source_kind", "")),
        0,
    )
    stem = Path(str(profile.get("source", ""))).stem
    readable_words = len(re.findall(r"[A-Za-z]{3,}", stem))
    opaque_penalty = 1 if re.fullmatch(r"[A-Za-z0-9_-]{32,}", stem) else 0
    metadata_score = sum(
        bool(profile.get(field)) for field in ("doi", "arxiv_id", "year", "venue")
    )
    return (
        source_kind_score,
        metadata_score,
        readable_words - (opaque_penalty * 20),
        str(profile.get("source", "")),
    )


def canonical_source_profiles(
    source_docs: dict[str, dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for profile in source_docs.values():
        grouped[source_title_identity(profile)].append(profile)

    canonical_docs: dict[str, dict[str, Any]] = {}
    duplicate_sources: dict[str, str] = {}
    for profiles in grouped.values():
        best = max(profiles, key=source_profile_quality)
        canonical = dict(best)
        canonical_source = str(best["source"])
        source_files = sorted(
            {
                source
                for profile in profiles
                for source in profile.get("source_files", [profile["source"]])
            },
            key=str.casefold,
        )
        canonical["source_files"] = source_files
        canonical["aliases"] = dedupe_preserve_order(
            [
                alias
                for profile in profiles
                for alias in [profile.get("title", ""), *profile.get("aliases", [])]
            ]
        )
        for field in ("concepts", "domains", "themes", "section_index", "github_links"):
            canonical[field] = dedupe_preserve_order(
                [value for profile in profiles for value in profile.get(field, [])]
            )
        canonical_docs[canonical_source] = canonical
        for profile in profiles:
            source = str(profile["source"])
            if source != canonical_source:
                duplicate_sources[source] = canonical_source
    return canonical_docs, duplicate_sources


def converted_pdf_markdown_path(root: Path, pdf_path: Path) -> Path:
    config = load_config(root)
    raw_dir = root / config["raw_dir"]
    source_dir = source_dir_for_path(root, pdf_path)
    if source_dir == raw_dir:
        relative = pdf_path.relative_to(raw_dir)
    else:
        relative = pdf_path.relative_to(root)
    return (root / config["converted_sources_dir"] / relative).with_suffix(".md")


def converted_tex_markdown_path(root: Path, tex_path: Path) -> Path:
    config = load_config(root)
    raw_dir = root / config["raw_dir"]
    source_dir = source_dir_for_path(root, tex_path)
    if source_dir == raw_dir:
        relative = tex_path.relative_to(raw_dir)
    else:
        relative = tex_path.relative_to(root)
    return (root / config["converted_sources_dir"] / relative).with_suffix(".md")


def converted_raw_markdown_path(root: Path, markdown_path: Path) -> Path:
    config = load_config(root)
    clippings_dir = root / "Clippings"
    relative = markdown_path.relative_to(clippings_dir)
    source_rel = markdown_path.relative_to(root).as_posix()
    source_namespace = hashlib.sha256(source_rel.encode("utf-8")).hexdigest()[:12]
    return root / config["sanitized_clippings_dir"] / source_namespace / relative


def is_mermaid_render_artifact(block: str) -> bool:
    lowered = block.lower()
    if len(block) < 1000 or not re.search(r"#mermaid-\d+", lowered):
        return False
    marker_count = sum(marker in lowered for marker in MERMAID_RENDER_ARTIFACT_MARKERS)
    css_signal_count = sum(
        signal in lowered
        for signal in ("stroke-width:", "fill:", "font-family:", "animation:", "text-anchor:")
    )
    return marker_count >= 3 and css_signal_count >= 3


def mermaid_source_is_valid(source: str) -> bool:
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        lowered = stripped.lower()
        return any(lowered.startswith(prefix) for prefix in MERMAID_DIAGRAM_PREFIXES)
    return False


def decode_escaped_mermaid_source(source: str) -> str | None:
    try:
        decoded = json.loads(f'"{source}"')
    except json.JSONDecodeError:
        return None
    normalized = html.unescape(decoded).replace("\r\n", "\n").strip()
    return normalized if mermaid_source_is_valid(normalized) else None


def extract_mermaid_sources_from_html(page_html: str) -> list[str]:
    sources: list[str] = []
    for match in MERMAID_ESCAPED_FENCE_RE.finditer(page_html):
        source = decode_escaped_mermaid_source(match.group(1))
        if source and source not in sources:
            sources.append(source)
    for match in MERMAID_LITERAL_FENCE_RE.finditer(page_html):
        source = html.unescape(match.group(1)).replace("\r\n", "\n").strip()
        if mermaid_source_is_valid(source) and source not in sources:
            sources.append(source)
    return sources


def local_mermaid_source_entry(root: Path, source_url: str) -> tuple[list[str], bool]:
    source_file = root / CLIPPING_MERMAID_SOURCES_PATH
    if not source_file.exists() or not source_url:
        return [], False
    try:
        configured = json.loads(source_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return [], False
    if not isinstance(configured, dict) or source_url not in configured:
        return [], False
    sources = configured[source_url]
    if not isinstance(sources, list):
        return [], True
    valid_sources = [
        source.strip()
        for source in sources
        if isinstance(source, str) and mermaid_source_is_valid(source)
    ]
    return valid_sources, True


def local_mermaid_sources(root: Path, source_url: str) -> list[str]:
    return local_mermaid_source_entry(root, source_url)[0]


def mermaid_sources_digest(sources: list[str]) -> str:
    serialized = json.dumps(sources, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def rendered_mermaid_artifact_count(text: str) -> int:
    return sum(
        1
        for match in FENCED_MARKDOWN_BLOCK_RE.finditer(text)
        if is_mermaid_render_artifact(match.group("body"))
    )


def sanitize_clipping_markdown(text: str, mermaid_sources: list[str]) -> tuple[str, int]:
    reconstructed = 0

    def replace_artifact(match: re.Match[str]) -> str:
        nonlocal reconstructed
        if not is_mermaid_render_artifact(match.group("body")):
            return match.group(0)
        if reconstructed >= len(mermaid_sources):
            return match.group(0)
        source = mermaid_sources[reconstructed].strip()
        reconstructed += 1
        return f"```mermaid\n{source}\n```"

    return FENCED_MARKDOWN_BLOCK_RE.sub(replace_artifact, text), reconstructed


def sanitized_markdown_cache_content(
    text: str,
    source_rel: str,
    source_digest: str,
    reconstructed_blocks: int,
    recovery_source: str,
    sources_digest: str,
) -> str:
    metadata = [
        f"sanitized_from: {json.dumps(source_rel, ensure_ascii=False)}",
        f"sanitization_pipeline: {json.dumps(CLIPPING_SANITIZATION_PIPELINE)}",
        f"source_digest: {json.dumps(source_digest)}",
        f"sanitized_artifact_blocks: {reconstructed_blocks}",
        f"reconstructed_mermaid_blocks: {reconstructed_blocks}",
        f"mermaid_recovery_source: {json.dumps(recovery_source, ensure_ascii=False)}",
        f"mermaid_sources_digest: {json.dumps(sources_digest)}",
    ]
    if text.startswith("---\n") and "\n---\n" in text[4:]:
        frontmatter, body = text.split("\n---\n", 1)
        return "\n".join([frontmatter, *metadata, "---", body])
    return "\n".join(["---", *metadata, "---", text])


def prepared_raw_markdown_content_path(
    root: Path,
    path: Path,
) -> tuple[Path, int]:
    try:
        path.resolve().relative_to((root / "Clippings").resolve())
    except ValueError:
        return path, 0
    original = read_text(path)
    artifact_count = rendered_mermaid_artifact_count(original)
    if not artifact_count:
        return path, 0

    cache_path = converted_raw_markdown_path(root, path)
    source_rel = path.relative_to(root).as_posix()
    source_digest = file_hash(path)
    source_url = frontmatter_scalar(original, "source") or ""
    local_sources = local_mermaid_sources(root, source_url)
    mermaid_sources = local_sources if len(local_sources) == artifact_count else []
    sources_digest = mermaid_sources_digest(mermaid_sources) if mermaid_sources else ""
    if cache_path.exists():
        cached = read_text(cache_path)
        cached_count = int(frontmatter_scalar(cached, "reconstructed_mermaid_blocks") or 0)
        cached_path_is_valid = bool(mermaid_sources) and (
            frontmatter_scalar(cached, "sanitization_pipeline") == CLIPPING_SANITIZATION_PIPELINE
            and frontmatter_scalar(cached, "source_digest") == source_digest
            and cached_count == artifact_count
            and rendered_mermaid_artifact_count(cached) == 0
            and frontmatter_scalar(cached, "mermaid_sources_digest") == sources_digest
        )
        if cached_path_is_valid:
            return cache_path, cached_count

    if not mermaid_sources:
        return path, 0
    sanitized, reconstructed_blocks = sanitize_clipping_markdown(original, mermaid_sources)
    if reconstructed_blocks != artifact_count:
        return path, 0

    cache_content = sanitized_markdown_cache_content(
        sanitized,
        source_rel,
        source_digest,
        reconstructed_blocks,
        "local-map",
        sources_digest,
    )
    write_text_if_changed(cache_path, cache_content)
    return cache_path, reconstructed_blocks


def configured_source_dirs(root: Path) -> list[Path]:
    config = load_config(root)
    configured = config.get("source_dirs")
    if not isinstance(configured, list) or not configured:
        configured = [config["raw_dir"]]
    source_dirs = []
    seen = set()
    for value in configured:
        if not isinstance(value, str) or not value.strip():
            continue
        path = root / value
        key = path.as_posix()
        if key in seen:
            continue
        seen.add(key)
        source_dirs.append(path)
    return source_dirs


def source_dir_for_path(root: Path, path: Path) -> Path:
    for source_dir in configured_source_dirs(root):
        try:
            path.relative_to(source_dir)
            return source_dir
        except ValueError:
            continue
    raise ValueError(f"{path} is not inside any configured source directory")


def source_note_page_path(root: Path, source_rel: str, title: str) -> Path:
    config = load_config(root)
    stem = slugify(title)[:72] or slugify(Path(source_rel).stem)[:72] or "source"
    return root / config["source_notes_dir"] / f"{stem}-{short_hash(source_rel)}.md"


def raw_markdown_files(root: Path) -> list[Path]:
    paths = []
    for source_dir in configured_source_dirs(root):
        if not source_dir.exists():
            continue
        paths.extend(path for path in source_dir.rglob("*.md") if path.is_file())
    return sorted(paths)


def raw_pdf_files(root: Path) -> list[Path]:
    tex_asset_pdfs = {
        dependency.resolve()
        for tex_path in raw_tex_files(root)
        for dependency in tex_dependency_files(tex_path)
        if dependency.suffix.lower() == ".pdf"
    }
    paths = []
    for source_dir in configured_source_dirs(root):
        if not source_dir.exists():
            continue
        paths.extend(
            path
            for path in source_dir.rglob("*.pdf")
            if path.is_file()
            and not path.with_suffix(".tex").is_file()
            and path.resolve() not in tex_asset_pdfs
        )
    return sorted(paths)


def raw_tex_files(root: Path) -> list[Path]:
    paths = []
    for source_dir in configured_source_dirs(root):
        if not source_dir.exists():
            continue
        paths.extend(path for path in source_dir.rglob("*.tex") if path.is_file())
    included_paths = set()
    for path in paths:
        text = read_text(path)
        for match in re.finditer(r"\\(?:input|include|subfile)\s*\{([^{}]+)\}", text):
            target = (path.parent / match.group(1).strip()).resolve()
            if not target.suffix:
                target = target.with_suffix(".tex")
            if target.is_file():
                included_paths.add(target)
    return sorted(path for path in paths if path.resolve() not in included_paths)


def source_input_records(root: Path) -> list[dict[str, Any]]:
    records = []
    for path in raw_markdown_files(root):
        if path.name.lower() == "readme.md":
            continue
        content_path, reconstructed_mermaid_blocks = prepared_raw_markdown_content_path(
            root,
            path,
        )
        records.append(
            {
                "source": path.relative_to(root).as_posix(),
                "logical_path": path,
                "content_path": content_path,
                "source_kind": "raw_markdown",
                "sanitized_artifact_blocks": reconstructed_mermaid_blocks,
                "reconstructed_mermaid_blocks": reconstructed_mermaid_blocks,
            }
        )

    for pdf_path in raw_pdf_files(root):
        cache_path = converted_pdf_markdown_path(root, pdf_path)
        if cache_path.exists():
            records.append(
                {
                    "source": pdf_path.relative_to(root).as_posix(),
                    "logical_path": pdf_path,
                    "content_path": cache_path,
                    "source_kind": "raw_pdf",
                }
            )

    for tex_path in raw_tex_files(root):
        cache_path = converted_tex_markdown_path(root, tex_path)
        if cache_path.exists():
            records.append(
                {
                    "source": tex_path.relative_to(root).as_posix(),
                    "logical_path": tex_path,
                    "content_path": cache_path,
                    "source_kind": "raw_tex",
                }
            )

    return sorted(records, key=lambda item: item["source"].lower())


def paper_title_from_name(name: str) -> str:
    stem = Path(name).stem
    parts = [part.strip() for part in stem.split(" - ") if part.strip()]
    if len(parts) >= 3 and re.fullmatch(r"\d{4}", parts[1]):
        title = " - ".join(parts[2:]).strip()
    elif len(parts) >= 2:
        title = " - ".join(parts[1:]).strip()
    else:
        title = stem.strip()
    return re.sub(r"-[0-9a-f]{8}$", "", title, flags=re.IGNORECASE).strip()


def clean_markdown_candidate(text: str) -> str:
    cleaned = text.strip().lstrip("#").strip().strip("*").strip().rstrip("\\").strip()
    cleaned = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", cleaned)
    return cleaned.strip()


def title_token_set(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", normalize_text(text).lower())
        if len(token) >= 3 and token not in STOPWORDS
    }


def title_similarity(candidate: str, hint: str) -> float:
    candidate_tokens = title_token_set(candidate)
    hint_tokens = title_token_set(hint)
    if not candidate_tokens or not hint_tokens:
        return 0.0
    overlap = len(candidate_tokens & hint_tokens)
    return overlap / max(1, len(hint_tokens))


def combined_title_candidates(lines: list[str]) -> list[str]:
    combined = []
    for index, line in enumerate(lines):
        combined.append(line)
        if index + 1 >= len(lines):
            continue
        next_line = lines[index + 1]
        lowered = normalize_text(line).lower()
        next_lowered = normalize_text(next_line).lower()
        if any(
            hint in lowered or hint in next_lowered
            for hint in {"manuscript", "inserted by the editor", "journal homepage", "check for updates"}
        ):
            continue
        if looks_like_person_name(next_line) or is_affiliation_or_metadata_line(next_line):
            continue
        if len(f"{line} {next_line}") > 220:
            continue
        combined.append(f"{line} {next_line}")
    return dedupe_preserve_order(combined)


def bibliographic_region(markdown_text: str, max_lines: int = 120) -> str:
    body = extracted_markdown_body(markdown_text)
    lines = []
    for raw in body.splitlines():
        stripped = raw.strip()
        lowered = normalize_text(stripped).lower().strip(":")
        if lowered in {"introduction", "references"} or re.match(r"^(?:##\s*)?1(?:\.0+)?\s+introduction\b", lowered):
            break
        if stripped.startswith("## 1 ") or stripped.startswith("## 1.") or stripped.startswith("1 Introduction"):
            break
        lines.append(raw)
        if len(lines) >= max_lines:
            break
    return "\n".join(lines).strip()


def contains_metadata_hint(text: str, hint: str) -> bool:
    if not hint:
        return False
    if hint in WEAK_METADATA_HINTS:
        return False
    if " " in hint:
        return hint in text
    return bool(re.search(rf"\b{re.escape(hint)}\b", text))


def is_affiliation_or_metadata_line(text: str) -> bool:
    lowered = normalize_text(text).lower().strip(":")
    if not lowered:
        return False
    if lowered in GENERIC_HEADER_LINES or lowered.startswith("keywords"):
        return True
    if lowered.startswith(("received", "accepted", "edited by", "corresponding author", "available online", "preprint")):
        return True
    if "@" in text:
        return True
    if any(contains_metadata_hint(lowered, hint) for hint in AFFILIATION_HINTS | ORGANIZATION_HINTS | ADDRESS_HINTS):
        return True
    if re.search(r"\b\d{3,}\b", text) and len(text.split()) >= 3:
        return True
    if re.search(r"\b(?:usa|uk|germany|france|netherlands|india|china|japan)\b", lowered):
        return True
    return False


def looks_like_person_name(text: str) -> bool:
    candidate = normalize_author_token(text)
    lowered = candidate.lower()
    words = [word for word in candidate.split() if word]
    if len(words) < 2 or len(words) > 5:
        return False
    if not re.search(r"[A-Za-z]", candidate):
        return False
    if any(word.lower() in GENERIC_HEADER_LINES for word in words):
        return False
    if any(word.lower() in ORGANIZATION_HINTS for word in words):
        return False
    if any(word.lower() in {"keywords", "article", "info", "received", "accepted", "introduction"} for word in words):
        return False
    if is_affiliation_or_metadata_line(candidate):
        return False
    capitals = 0
    for word in words:
        lowered_word = word.lower().strip(".")
        if lowered_word in PERSON_CONNECTORS:
            capitals += 1
            continue
        if re.fullmatch(r"[A-Z]\.?", word) or word[:1].isupper():
            capitals += 1
    if capitals < max(2, len(words) - 1):
        return False
    return len(re.findall(r"[A-Za-z]", candidate)) >= 4


def split_author_line(raw_line: str) -> list[str]:
    line = raw_line.strip()
    if not line:
        return []
    bold_names = []
    for value in re.findall(r"\*\*([^*]+)\*\*", line):
        for part in value.split(","):
            candidate = normalize_author_token(part)
            if looks_like_person_name(candidate):
                bold_names.append(candidate)
    if bold_names:
        return dedupe_preserve_order(bold_names)
    footnote_names = []
    for value in re.findall(r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){1,4})(?=\$?\^\{?\d)", line):
        candidate = normalize_author_token(value)
        if looks_like_person_name(candidate):
            footnote_names.append(candidate)
    if footnote_names:
        return dedupe_preserve_order(footnote_names)
    cite_match = re.search(
        r":\s*([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){1,4})\s+\*?et al\b",
        line,
        re.IGNORECASE,
    )
    if normalize_text(line).lower().startswith("to cite this article") and cite_match:
        candidate = normalize_author_token(cite_match.group(1))
        return [candidate] if looks_like_person_name(candidate) else []
    if is_affiliation_or_metadata_line(line):
        return []
    separated = line.replace("\\*", " ")
    separated = separated.replace("**", " ")
    separated = separated.replace("*", " ")
    separated = re.sub(r"\$[^$]*\$", ", ", separated)
    separated = separated.replace(r"\quad", ", ")
    separated = re.sub(r"\^\{[^}]*\}", ", ", separated)
    separated = re.sub(r"\^[A-Za-z0-9\\,*†‡]+", ", ", separated)
    separated = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰†‡✉]+", ", ", separated)
    separated = separated.replace(" · ", ", ").replace("•", ",").replace(";", ",")
    separated = re.sub(r"\band\b", ",", separated, flags=re.IGNORECASE)
    separated = re.sub(r"\s{2,}", ", ", separated)
    parts = [normalize_author_token(part) for part in separated.split(",")]
    return dedupe_preserve_order([part for part in parts if looks_like_person_name(part)])


def is_reasonable_venue_candidate(candidate: str) -> bool:
    cleaned = clean_markdown_candidate(candidate)
    lowered = normalize_text(cleaned).lower()
    if not cleaned or len(cleaned.split()) > 10:
        return False
    if looks_like_person_name(cleaned) or is_affiliation_or_metadata_line(cleaned):
        return False
    if re.search(r"[.!?]", cleaned):
        return False
    if not any(keyword in lowered for keyword in VENUE_KEYWORDS):
        return False
    titled_words = sum(1 for word in cleaned.split() if word[:1].isupper())
    if titled_words < 2:
        return False
    return len(re.findall(r"[A-Za-z]", cleaned)) >= 6


def cache_transcription_mode(markdown_text: str) -> str:
    declared_mode = re.search(r"^transcription_mode:\s*[\"']?([^\"'\n]+)", markdown_text, re.MULTILINE)
    if declared_mode:
        return declared_mode.group(1).strip()
    body = extracted_markdown_body(markdown_text)
    has_fallback = bool(re.search(r"^### Page \d+\s*$", body, re.MULTILINE))
    if has_fallback and "## Pages " in body:
        return "mixed"
    if has_fallback:
        return "local_fallback"
    return "vision"


def frontmatter_scalar(markdown_text: str, key: str) -> str | None:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", markdown_text, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def frontmatter_list(markdown_text: str, key: str) -> list[str]:
    block_match = re.search(rf"^{re.escape(key)}:\s*\n((?:  - .*\n?)*)", markdown_text, re.MULTILINE)
    if not block_match:
        return []
    values = []
    for raw_line in block_match.group(1).splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("- "):
            continue
        values.append(stripped[2:].strip().strip("\"'"))
    return [value for value in values if value]


def source_filename_parts(source_path: Path) -> dict[str, str | None]:
    parts = [part.strip() for part in source_path.stem.split(" - ", 2)]
    if len(parts) == 3 and re.fullmatch(r"\d{4}", parts[1]):
        return {
            "lead_author_text": parts[0],
            "year": parts[1],
            "title_hint": parts[2],
        }
    year_match = re.search(r"\b((?:19|20)\d{2})\b", source_path.stem)
    return {
        "lead_author_text": parts[0] if parts else None,
        "year": year_match.group(1) if year_match else None,
        "title_hint": paper_title_from_name(source_path.name),
    }


def canonical_alias(title: str) -> str | None:
    for delimiter in (":", " - ", " -- "):
        if delimiter in title:
            candidate = title.split(delimiter, 1)[0].strip()
            if 1 < len(candidate.split()) <= 8 and len(candidate) < len(title):
                return candidate
    words = title.split()
    if len(words) > 10:
        return " ".join(words[:6]).strip()
    return None


def source_page_aliases(title: str, citation_key: str | None = None) -> list[str]:
    aliases: list[str] = []
    is_supplementary = bool(re.search(r"\bsupplement(?:ary)?\b", title, re.IGNORECASE))
    if " | " in title:
        pipe_alias = title.split(" | ", 1)[0].strip()
        if pipe_alias and pipe_alias != title:
            aliases.append(pipe_alias)
    short_title = canonical_alias(title)
    if short_title and short_title != title and not is_supplementary:
        aliases.append(short_title)
    if citation_key and citation_key != title:
        aliases.append(citation_key)
    return dedupe_preserve_order(aliases)


def normalize_author_token(token: str) -> str:
    cleaned = re.sub(r"\$[^$]*\$", "", token)
    cleaned = re.sub(r"\^\{[^}]*\}", "", cleaned)
    cleaned = re.sub(r"\^\d+", "", cleaned)
    cleaned = re.sub(r"[*†‡§¶#0-9]+", " ", cleaned)
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = cleaned.translate(SUPERSCRIPT_TRANSLATION)
    cleaned = normalize_text(cleaned.replace("et al.", "").replace("et al", ""))
    cleaned = re.sub(r"^(?:and|&)\s+", "", cleaned, flags=re.IGNORECASE)
    words = cleaned.split()
    if words:
        last = words[-1]
        if re.fullmatch(r"[A-Za-z]{4,}[a-f]", last):
            words[-1] = last[:-1]
            cleaned = " ".join(words)
    return cleaned.strip(",; ")


def split_author_candidates(raw_text: str) -> list[str]:
    text = raw_text.replace(" and ", ", ")
    parts = [normalize_author_token(part) for part in text.split(",")]
    authors = []
    for part in parts:
        lowered = part.lower()
        if not part:
            continue
        if lowered in {"article info", "keywords"} or lowered.startswith("keywords"):
            continue
        if "@" in part or any(hint in lowered for hint in AFFILIATION_HINTS):
            continue
        if len(part.split()) > 5:
            continue
        if len(re.findall(r"[A-Za-z]", part)) < 3:
            continue
        authors.append(part)
    return dedupe_preserve_order(authors)


def author_names_from_mixed_line(raw_line: str) -> list[str]:
    line = raw_line.strip().strip("*").strip()
    if not line:
        return []
    if "@" not in raw_line and "**" not in raw_line:
        return []
    lowered = normalize_text(line).lower()
    if lowered.startswith(("abstract", "keywords", "introduction", "funding", "grant/award")):
        return []

    cleaned = re.sub(r"https?://\S+", " ", line)
    cleaned = re.sub(r"\S+@\S+", " ", cleaned)
    cleaned = re.sub(r"\b(?:co-first authors?|corresponding authors?|equal contribution[s]?).*$", " ", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("&", ", ")
    cleaned = cleaned.translate(SUPERSCRIPT_TRANSLATION)
    cleaned = re.sub(r"\$[^$]*\$", " ", cleaned)
    cleaned = re.sub(r"\^\{[^}]*\}", " ", cleaned)
    cleaned = re.sub(r"\^\d+", " ", cleaned)
    cleaned = normalize_text(cleaned)

    names = []
    for chunk in re.split(r"[;,]", cleaned):
        tokens = [token for token in chunk.split() if token]
        prefix = []
        for index, token in enumerate(tokens):
            lowered_token = token.lower().strip(".:")
            if lowered_token in {"co-first", "corresponding", "author", "authors"}:
                break
            if lowered_token in AFFILIATION_HINTS or lowered_token in ORGANIZATION_HINTS or lowered_token in ADDRESS_HINTS:
                break
            if "@" in token:
                break
            if prefix and not (
                lowered_token in PERSON_CONNECTORS
                or re.fullmatch(r"[A-Z]\.?", token)
                or token[:1].isupper()
            ):
                break
            prefix.append(token)
            candidate = normalize_author_token(" ".join(prefix))
            tail = [tokens[offset].lower().strip(".:") for offset in range(index + 1, min(len(tokens), index + 5))]
            if looks_like_person_name(candidate):
                if any(item in AFFILIATION_HINTS or item in ORGANIZATION_HINTS or item in ADDRESS_HINTS for item in tail):
                    break
                if len(prefix) >= 3 and tail and tail[0] not in PERSON_CONNECTORS and not re.fullmatch(r"[A-Z]\.?", tokens[index + 1]):
                    break
            if len(prefix) >= 5:
                break
        candidate = normalize_author_token(" ".join(prefix))
        if looks_like_person_name(candidate):
            names.append(candidate)
    return dedupe_preserve_order(names)


def extract_authors(markdown_text: str, title: str, source_path: Path) -> list[str]:
    declared_authors = frontmatter_list(markdown_text, "authors")
    if declared_authors:
        return declared_authors

    region = bibliographic_region(markdown_text, max_lines=40)
    lines = [line.strip() for line in region.splitlines()]
    title_norm = normalize_text(title).lower()
    title_index = None
    for index, line in enumerate(lines):
        cleaned = clean_markdown_candidate(line)
        if not cleaned:
            continue
        combined = cleaned
        if index + 1 < len(lines):
            combined = f"{cleaned} {clean_markdown_candidate(lines[index + 1])}".strip()
        if normalize_text(cleaned).lower() == title_norm or title_similarity(cleaned, title) >= 0.75:
            title_index = index
            break
        if index + 1 < len(lines) and title_similarity(combined, title) >= 0.75:
            title_index = index + 1
            break

    authors = []
    filename_lead = normalize_author_token(source_filename_parts(source_path).get("lead_author_text") or "").split(" ")[0].casefold()
    if title_index is not None:
        for raw in lines[title_index + 1:title_index + 25]:
            raw_line = raw.strip()
            stripped = clean_markdown_candidate(raw_line)
            lowered = normalize_text(stripped).lower().strip(":")
            if not stripped:
                continue
            if lowered in {"abstract", "article info"} or lowered.startswith(("abstract", "keywords", "introduction")):
                break
            if stripped.startswith("#"):
                break
            tokens = stripped.split()
            if (
                filename_lead
                and 4 <= len(tokens) <= 12
                and len(tokens) % 2 == 0
                and all(re.fullmatch(r"[A-Z][A-Za-z'-]+", token) for token in tokens)
                and tokens[1].casefold() == filename_lead
            ):
                authors.extend(" ".join(tokens[index:index + 2]) for index in range(0, len(tokens), 2))
                break
            parsed = split_author_line(raw_line)
            authors.extend(parsed)
            if not authors:
                authors.extend(author_names_from_mixed_line(raw_line))
            elif not parsed:
                authors.extend(author_names_from_mixed_line(raw_line))
    authors = dedupe_preserve_order(authors)
    if authors:
        return authors

    lead_author_text = source_filename_parts(source_path).get("lead_author_text") or ""
    fallback = normalize_author_token(lead_author_text)
    return [fallback] if fallback else []


def derive_citation_key(title: str, source_path: Path, authors: list[str], year: str | None) -> str:
    if authors:
        lead = slugify(authors[0].split()[-1])
    else:
        lead_author_text = source_filename_parts(source_path).get("lead_author_text") or "source"
        normalized = normalize_author_token(lead_author_text)
        lead = slugify(normalized.split()[-1] if normalized else "source")
    title_tokens = slugify(canonical_alias(title) or title).split("-")
    lead = lead or "source"
    year_token = year or "undated"
    key_tail = title_tokens[0] if title_tokens else "note"
    if "supplement" in title.lower():
        key_tail = f"{key_tail}-supplement"
    return f"{lead}{year_token}{key_tail}"


def page_image_directory_path(root: Path, pdf_path: Path) -> Path:
    config = load_config(root)
    return root / config["generated_images_dir"] / safe_project_name(pdf_path)


def page_image_directory_rel(root: Path, pdf_path: Path) -> str | None:
    directory = page_image_directory_path(root, pdf_path)
    if directory.exists():
        return directory.relative_to(root).as_posix()
    return None


def page_count_for_pdf(root: Path, pdf_path: Path) -> int | None:
    directory = page_image_directory_path(root, pdf_path)
    if not directory.exists():
        return None
    count = len(sorted(path for path in directory.glob("*.png") if path.is_file()))
    return count or None


def ensure_page_images(root: Path, pdf_path: Path, md_path: Path, expected_count: int | None = None) -> list[str]:
    relative_paths = existing_relative_page_images(root, pdf_path, md_path)
    if relative_paths and (expected_count is None or len(relative_paths) == expected_count):
        return relative_paths

    image_paths, work_dir, _ = render_pdf_pages(root, pdf_path)
    try:
        relative_paths = copy_page_images(root, pdf_path, image_paths, md_path)
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
    return relative_paths


def extract_section_headings(markdown_text: str, source_path: Path | None = None, limit: int = 10) -> list[str]:
    body = extracted_markdown_body(markdown_text)
    filename_title = paper_title_from_name(source_path.name) if source_path else ""
    headings = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
        elif re.match(r"^\d+(?:\.\d+)*\s+\S", stripped):
            heading = stripped
        else:
            continue
        if not heading or heading in CACHE_SCAFFOLD_HEADINGS:
            continue
        if re.fullmatch(r"Pages? \d+(?:-\d+)?", heading, re.IGNORECASE):
            continue
        if is_affiliation_or_metadata_line(heading):
            continue
        if len(re.findall(r"[A-Za-z]", heading)) < 3:
            continue
        if filename_title and heading == filename_title:
            continue
        headings.append(heading)
    return dedupe_preserve_order(headings)[:limit]


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        parts = text.split("\n---\n", 1)
        if len(parts) == 2:
            return parts[1]
    return text


def patent_title_candidate(markdown_text: str) -> str:
    lines = [clean_markdown_candidate(line) for line in extracted_markdown_body(markdown_text).splitlines()]
    for index, line in enumerate(lines):
        normalized = normalize_text(line)
        if not re.match(r"^WO\s+\d{4}/\d+.*\bPCT/", normalized, re.IGNORECASE):
            continue
        title_lines = []
        for candidate in lines[index + 1 : index + 10]:
            normalized_candidate = normalize_text(candidate).strip()
            if not normalized_candidate or re.fullmatch(
                r"Pages? \d+(?:-\d+)?", normalized_candidate, re.IGNORECASE
            ):
                continue
            if normalized_candidate.upper() in {"BACKGROUND", "ABSTRACT", "FIELD"}:
                break
            letters = [character for character in normalized_candidate if character.isalpha()]
            if len(letters) < 5:
                continue
            uppercase_ratio = sum(character.isupper() for character in letters) / len(letters)
            if uppercase_ratio < 0.85:
                break
            title_lines.append(normalized_candidate)
        if not title_lines:
            continue
        title = re.sub(r"(?<=[A-Za-z])-\s+(?=[A-Za-z])", "", " ".join(title_lines))
        title = re.sub(r"\s+", " ", title).strip(" .")
        if 20 <= len(title) <= 300:
            if title.isupper():
                title = title[:1] + title[1:].lower()
            return title
    return ""


def detect_title(markdown_text: str, source_path: Path) -> str:
    frontmatter_match = re.search(r"^title:\s*(.+)$", markdown_text, re.MULTILINE)
    frontmatter_title = frontmatter_match.group(1).strip().strip('"') if frontmatter_match else ""
    title_hint = paper_title_from_name(source_path.name)
    is_pdf_source = source_path.suffix.lower() == ".pdf"
    if is_pdf_source:
        frontmatter_title = re.sub(
            r"-[0-9a-f]{8}$",
            "",
            frontmatter_title,
            flags=re.IGNORECASE,
        ).strip()
    frontmatter_valid = (
        bool(frontmatter_title)
        and frontmatter_title.count("|") < 2
        and not re.fullmatch(r"Pages? \d+(?:-\d+)?", frontmatter_title, re.IGNORECASE)
    )
    if frontmatter_valid and not (is_pdf_source and title_hint):
        return frontmatter_title
    patent_title = patent_title_candidate(markdown_text)
    if patent_title:
        return patent_title
    body = extracted_markdown_body(markdown_text)
    heading_candidates = [frontmatter_title] if frontmatter_valid else []
    for raw in body.splitlines()[:40]:
        heading_match = re.match(r"^\s*#{1,2}\s+(.+?)\s*$", raw)
        if not heading_match:
            continue
        heading = clean_markdown_candidate(heading_match.group(1))
        if re.fullmatch(r"Pages? \d+(?:-\d+)?", heading, re.IGNORECASE):
            continue
        if heading and len(heading) >= 4:
            heading_candidates.append(heading)
    body_lines = [line.strip() for line in body.splitlines()]
    candidate_lines = []
    for raw in body_lines[:80]:
        cleaned = clean_markdown_candidate(raw)
        lowered = normalize_text(cleaned).lower()
        if not cleaned or re.fullmatch(r"Pages? \d+(?:-\d+)?", cleaned, re.IGNORECASE):
            continue
        if any(hint in lowered for hint in {"manuscript", "inserted by the editor", "journal homepage", "check for updates"}):
            continue
        if cleaned.count("|") >= 2:
            continue
        if len(cleaned) < 12 or len(cleaned) > 220:
            continue
        if re.search(r"[.!?]$", cleaned):
            continue
        if is_affiliation_or_metadata_line(cleaned):
            continue
        candidate_lines.append(cleaned)
    candidate_lines = dedupe_preserve_order(heading_candidates + combined_title_candidates(candidate_lines))
    if title_hint:
        ranked = [
            (title_similarity(candidate, title_hint), index, candidate)
            for index, candidate in enumerate(candidate_lines)
        ]
        ranked = [item for item in ranked if item[0] >= 0.55]
        if ranked:
            ranked.sort(key=lambda item: (-item[0], item[1], -len(item[2])))
            candidate = ranked[0][2]
            candidate_tokens = title_token_set(candidate)
            hint_tokens = title_token_set(title_hint)
            if (
                is_pdf_source
                and (
                    (candidate_tokens < hint_tokens and len(candidate) < len(title_hint) * 0.85)
                    or len(candidate) > len(title_hint) * 1.6
                )
            ):
                return title_hint
            return candidate
        if frontmatter_valid and title_similarity(frontmatter_title, title_hint) >= 0.35:
            return frontmatter_title
        if is_pdf_source:
            return title_hint
    for candidate in heading_candidates:
        if candidate and len(candidate) >= 4:
            return candidate
    for candidate in candidate_lines:
        if len(candidate.split()) >= 4 and not looks_like_person_name(candidate):
            return candidate
    return frontmatter_title or title_hint


def concept_body_signal(markdown_text: str, source_kind: str, limit: int = 1800) -> str:
    body = strip_frontmatter(markdown_text) if source_kind == "raw_markdown" else extracted_markdown_body(markdown_text)
    snippets = []
    for raw in body.splitlines():
        stripped = clean_markdown_candidate(raw)
        lowered = normalize_text(stripped).lower().strip(":")
        if not stripped:
            if snippets and len(" ".join(snippets)) >= limit:
                break
            continue
        if stripped.startswith(">") or stripped.startswith("![]("):
            continue
        if re.fullmatch(r"Pages? \d+(?:-\d+)?", stripped, re.IGNORECASE):
            continue
        if lowered in GENERIC_HEADER_LINES or lowered.startswith(("abstract", "keywords")):
            continue
        snippets.append(stripped)
        if len(" ".join(snippets)) >= limit:
            break
    return normalize_text(" ".join(snippets))[:limit]


def first_meaningful_paragraph(markdown_text: str, title: str = "", limit: int = 1600) -> str:
    source_kind = "raw_pdf" if "\n## Extracted Markdown\n" in strip_frontmatter(markdown_text) else "raw_markdown"
    body = extracted_markdown_body(markdown_text) if source_kind == "raw_pdf" else strip_frontmatter(markdown_text)
    title_norm = normalize_text(title).lower()
    seen_title = not bool(title)
    snippets = []

    for raw in body.splitlines()[:240]:
        stripped = raw.strip()
        cleaned = clean_markdown_candidate(stripped).strip("*").strip()
        lowered = normalize_text(cleaned).lower().strip(":")

        if not stripped:
            if snippets:
                break
            continue

        if stripped.startswith("#"):
            heading = clean_markdown_candidate(stripped.lstrip("#").strip())
            if title and (normalize_text(heading).lower() == title_norm or title_similarity(heading, title) >= 0.75):
                seen_title = True
            elif snippets:
                break
            continue

        if stripped.startswith(">") or stripped.startswith("![]("):
            if snippets:
                break
            continue

        if not seen_title and title:
            if normalize_text(cleaned).lower() == title_norm or title_similarity(cleaned, title) >= 0.75:
                seen_title = True
            continue

        if not cleaned or re.fullmatch(r"Pages? \d+(?:-\d+)?", cleaned, re.IGNORECASE):
            continue
        if lowered in GENERIC_HEADER_LINES or lowered.startswith(("abstract", "keywords")):
            if snippets:
                break
            continue
        if split_author_line(stripped) or author_names_from_mixed_line(stripped):
            continue
        if is_affiliation_or_metadata_line(cleaned) or looks_like_person_name(cleaned):
            continue
        if cleaned.count("|") >= 2:
            if snippets:
                break
            continue
        if len(cleaned.split()) < 8 and not snippets:
            continue

        snippets.append(cleaned)
        if len(" ".join(snippets)) >= limit:
            break

    return normalize_text(" ".join(snippets))[:limit]


ABSTRACT_SEARCH_WINDOW = 8000
AUTHOR_LINE_PATTERN = re.compile(r"[a-z]\d,\s?[A-Z]|(?:^|,)\s?\d[A-Z][a-z]|@")


def unlabeled_title_page_abstract(body: str) -> str:
    """Abstract printed without an 'Abstract' label, just before '1. Introduction'.

    Walks back from the first numbered Introduction heading on the title page and
    keeps the contiguous block of long prose lines, stopping at author or
    affiliation lines (superscript markers such as ``Nam1,`` or ``1Google``).
    """
    window = body[:ABSTRACT_SEARCH_WINDOW]
    intro = re.search(r"(?im)^\s*(?:#{1,3}\s*)?1\.?\s+Introduction\b", window)
    if not intro:
        return ""
    lines = [line.strip() for line in window[: intro.start()].splitlines()]
    block: list[str] = []
    for line in reversed(lines):
        if not line:
            if block:
                break
            continue
        if len(line) < 50 or AUTHOR_LINE_PATTERN.search(line) or line.startswith(("#", "<", "|")):
            break
        block.append(line)
    text = normalize_text(" ".join(reversed(block)))
    return text if len(text.split()) >= 40 else ""


def extract_abstract(markdown_text: str) -> str:
    cache_body = strip_frontmatter(markdown_text)
    cache_abstract = re.search(
        r"(?is)(?:^|\n)## Abstract\s*\n+(.*?)(?=\n## [^#]|\Z)",
        cache_body,
    )
    if cache_abstract:
        snippet = normalize_text(cache_abstract.group(1))
        if snippet:
            return snippet[:1600]

    body = extracted_markdown_body(markdown_text)
    compact = body.replace("\r\n", "\n")
    executive_summary = re.search(
        r"(?is)(?:^|\n)# Executive Summary[^\n]*\n+(.*?)(?=\n#|\n##)",
        compact,
    )
    if executive_summary:
        paragraphs = [normalize_text(part) for part in re.split(r"\n\s*\n", executive_summary.group(1))]
        paragraph = next((part for part in paragraphs if len(part.split()) >= 12 and not part.startswith("<")), "")
        if paragraph:
            return paragraph[:1600]

    abstract_match = re.search(
        r"(?is)\babstract\b[:\s]*\n?(.*?)(?:\n\s*#|\n\s*##|\n\s*\d+\s+introduction\b|\n\s*introduction\b)",
        compact,
    )
    unlabeled = unlabeled_title_page_abstract(compact)
    if unlabeled and (not abstract_match or abstract_match.start() > ABSTRACT_SEARCH_WINDOW):
        return unlabeled[:1600]
    if abstract_match:
        snippet = normalize_text(abstract_match.group(1))
        if snippet:
            return snippet[:1600]
    frontmatter_match = re.search(r"^title:\s*(.+)$", markdown_text, re.MULTILINE)
    title = frontmatter_match.group(1).strip().strip('"') if frontmatter_match else ""
    if "\n## Extracted Markdown\n" in cache_body:
        introduction = re.search(
            r"(?is)(?:^|\n)#{1,3}\s+Introduction[^\n]*\n+(.*?)(?=\n#{1,3}\s|\Z)",
            body,
        )
        if introduction:
            paragraphs = [normalize_text(part) for part in re.split(r"\n\s*\n", introduction.group(1))]
            paragraph = next((part for part in paragraphs if len(part.split()) >= 12 and not part.startswith("<")), "")
            if paragraph:
                return paragraph[:1600]
        fallback = first_meaningful_paragraph(markdown_text, limit=1600)
        if fallback:
            return fallback
    fallback = first_meaningful_paragraph(markdown_text, title=title, limit=1600)
    return fallback or first_meaningful_paragraph(markdown_text, limit=1600)


def extracted_markdown_body(markdown_text: str) -> str:
    body = strip_frontmatter(markdown_text)
    if "\n## Extracted Markdown\n" in body:
        return body.split("\n## Extracted Markdown\n", 1)[1].strip()
    return body.strip()


def clean_identifier(value: str) -> str:
    return value.rstrip(".,);]}>\"'")


def extract_github_links(markdown_text: str) -> list[str]:
    pattern = re.compile(
        r"(?<![\w@])(?:https?://)?(?:www\.)?(?:github\.com|gist\.github\.com)/[^\s<>)\]\"']+",
        re.IGNORECASE,
    )
    links = []
    for match in pattern.finditer(markdown_text):
        url = clean_identifier(match.group(0))
        if not url.lower().startswith(("http://", "https://")):
            url = f"https://{url}"
        url = re.sub(r"^https?://www\.", "https://", url, flags=re.IGNORECASE)
        links.append(url)
    return dedupe_preserve_order(links)


def github_link_label(url: str) -> str:
    match = re.match(r"https?://(?:gist\.)?github\.com/([^/?#]+)(?:/([^/?#]+))?", url, re.IGNORECASE)
    if not match:
        return url
    owner = unquote(match.group(1))
    repo = unquote(match.group(2) or "")
    if "gist.github.com" in url.lower():
        return f"gist:{owner}/{repo}" if repo else f"gist:{owner}"
    return f"{owner}/{repo}" if repo else owner


def extract_doi(markdown_text: str) -> str | None:
    region = bibliographic_region(markdown_text, max_lines=80)
    match = re.search(r"\b(10\.\d{4,9}/[-._;()/:A-Z0-9]+)\b", region, re.IGNORECASE)
    if match:
        return clean_identifier(match.group(1))
    return None


def extract_arxiv_id(markdown_text: str) -> str | None:
    body = bibliographic_region(markdown_text, max_lines=80)
    patterns = [
        r"arxiv[:\s]+(\d{4}\.\d{4,5}(?:v\d+)?)",
        r"10\.48550/arxiv\.(\d{4}\.\d{4,5}(?:v\d+)?)",
        r"arxiv\.org/(?:abs|pdf)/(\d{4}\.\d{4,5}(?:v\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            return clean_identifier(match.group(1))
    return None


def normalize_venue_case(text: str) -> str:
    collapsed = normalize_text(text).strip(" -|:,;")
    if collapsed.islower() or collapsed.isupper():
        return collapsed.title()
    return collapsed


def candidate_venue_lines(markdown_text: str) -> list[str]:
    body = bibliographic_region(markdown_text, max_lines=40)
    candidates = []
    for raw in body.splitlines():
        stripped = raw.strip().strip("*").strip()
        if not stripped:
            continue
        lowered = normalize_text(stripped).lower().strip(":")
        if lowered in GENERIC_HEADER_LINES:
            continue
        if lowered.startswith(("pages ", "journal homepage", "https://", "received ", "available online", "copyright", "e-mail")):
            continue
        candidates.append(stripped)
        if len(candidates) >= 40:
            break
    return candidates


def extract_venue(markdown_text: str, doi: str | None = None, arxiv_id: str | None = None) -> str | None:
    title_line = normalize_text(detect_title(markdown_text, Path("source.md"))).lower()
    for line in candidate_venue_lines(markdown_text):
        candidate = clean_markdown_candidate(line)
        lowered = normalize_text(candidate).lower()
        if not candidate or lowered == title_line:
            continue
        if lowered in GENERIC_HEADER_LINES or lowered.startswith("keywords"):
            continue
        if looks_like_person_name(candidate) or is_affiliation_or_metadata_line(candidate):
            continue
        if lowered.startswith("nature reviews "):
            return normalize_venue_case(candidate)
        if "science advances" in lowered:
            return "Science Advances"
        if re.match(r"^[A-Za-z][A-Za-z&,\- ]+\s+\d+\s+\(\d{4}\)", candidate):
            return normalize_venue_case(re.sub(r"\s+\d+\s+\(\d{4}\).*$", "", candidate).strip())
        if is_reasonable_venue_candidate(candidate) and lowered not in {"materials science"}:
            return normalize_venue_case(candidate)
    if arxiv_id:
        return "arXiv"
    if doi and doi.lower().startswith("10.48550/arxiv"):
        return "arXiv"
    return None


def top_terms(text: str, limit: int = 6) -> list[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]{3,}", text.lower())
    counts = Counter(token for token in tokens if token not in STOPWORDS)
    return [word for word, _ in counts.most_common(limit)]


def matches_alias(normalized_text: str, alias: str) -> bool:
    alias_text = normalize_for_match(alias)
    return alias_text in normalized_text


def matched_concepts(text: str, limit: int = 6) -> list[str]:
    normalized = normalize_for_match(text)
    scored = []
    for concept in CONCEPTS:
        score = 0
        for alias in concept["aliases"]:
            alias_text = normalize_for_match(alias)
            if not alias_text or alias_text not in normalized:
                continue
            word_count = len(alias_text.split())
            score += 1 + min(word_count, 3)
        if score > 0:
            scored.append((score, concept["title"].lower(), concept["slug"]))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [slug for _, _, slug in scored[:limit]]


def classify_labels(text: str, patterns: dict[str, list[str]]) -> list[str]:
    normalized = normalize_for_match(text)
    labels = []
    for label, aliases in patterns.items():
        if any(matches_alias(normalized, alias) for alias in aliases):
            labels.append(label)
    return labels


def normalize_api_key_value(raw: str, env_name: str) -> str:
    first_line = next((line.strip() for line in raw.splitlines() if line.strip()), "")
    value = re.sub(
        rf"^(?:export\s+)?{re.escape(env_name)}\s*(?:=|:|：)\s*",
        "",
        first_line,
        count=1,
    )
    return value.strip().strip("'\"")


def load_claude_api_key(root: Path) -> str:
    config = load_config(root)
    env_name = config["claude_api_env"]
    env_value = normalize_api_key_value(os.environ.get(env_name, ""), env_name)
    if env_value:
        return env_value

    key_file_value = str(config.get("claude_api_key_file", "")).strip()
    key_file = Path(key_file_value).expanduser() if key_file_value else None
    if key_file and key_file.is_file():
        raw = normalize_api_key_value(key_file.read_text(encoding="utf-8", errors="ignore"), env_name)
        if raw:
            return raw

    if key_file:
        raise RuntimeError(f"Missing {env_name}; also checked {key_file}")
    raise RuntimeError(f"Missing {env_name}")


def resolve_node_bin(node_bin: str) -> str | None:
    if Path(node_bin).exists():
        return node_bin
    return shutil.which(node_bin)


def safe_project_name(pdf_path: Path) -> str:
    digest = file_hash(pdf_path)[:8]
    slug = slugify(pdf_path.stem)[:72]
    return f"{slug or 'paper'}-{digest}"


def pdftocairo_path() -> str | None:
    return shutil.which("pdftocairo") or ("/opt/homebrew/bin/pdftocairo" if Path("/opt/homebrew/bin/pdftocairo").exists() else None)


def resolve_markitdown_cli(root: Path) -> str | None:
    config = load_config(root)
    configured = Path(str(config.get("markitdown_cli", ".venv/bin/markitdown"))).expanduser()
    candidates = [
        configured if configured.is_absolute() else root / configured,
        root / "_meta/markitdown_env/bin/markitdown",
    ]
    for candidate in candidates:
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    return shutil.which("markitdown")


def resolve_pandoc_bin(root: Path) -> str | None:
    config = load_config(root)
    configured = str(config.get("pandoc_bin", "pandoc")).strip() or "pandoc"
    candidate = Path(configured).expanduser()
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return shutil.which(configured)


def latex_command_arguments(text: str, command: str) -> list[str]:
    pattern = re.compile(rf"\\{re.escape(command)}\*?(?:\[[^\]]*\])?\s*\{{")
    arguments = []
    for match in pattern.finditer(text):
        start = match.end()
        depth = 1
        index = start
        while index < len(text) and depth:
            if text[index] == "\\":
                index += 2
                continue
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
            index += 1
        if depth == 0:
            arguments.append(text[start:index - 1].strip())
    return arguments


def latex_abstract_source(tex_text: str) -> str:
    command_abstracts = latex_command_arguments(tex_text, "abstract")
    if command_abstracts:
        return command_abstracts[0]
    environment = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex_text, re.DOTALL)
    return environment.group(1).strip() if environment else ""


def clean_latex_person_name(value: str) -> str:
    cleaned = re.sub(r"\\color\{[^{}]*\}", " ", value)
    for _ in range(4):
        updated = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?\{([^{}]*)\}", r" \1 ", cleaned)
        if updated == cleaned:
            break
        cleaned = updated
    cleaned = re.sub(r"\\[A-Za-z@]+\*?(?:\[[^\]]*\])?", " ", cleaned)
    cleaned = cleaned.replace("~", " ").replace("\\&", "&")
    return normalize_text(cleaned).strip(" ,;*\\")


def extract_latex_authors(tex_text: str) -> list[str]:
    authors = []
    for argument in latex_command_arguments(tex_text, "author"):
        fnm = re.search(r"\\fnm\{([^{}]+)\}", argument)
        surname = re.search(r"\\sur\{([^{}]+)\}", argument)
        if fnm and surname:
            authors.append(normalize_text(f"{fnm.group(1)} {surname.group(1)}"))
            continue
        first_line = re.split(r"\\\\|\\thanks\b|\\affil\b", argument, maxsplit=1)[0]
        candidate = clean_latex_person_name(first_line)
        if candidate and "@" not in candidate and len(candidate.split()) <= 6:
            authors.append(candidate)

    for argument in latex_command_arguments(tex_text, "icmlauthor"):
        candidate = clean_latex_person_name(argument)
        if candidate and "@" not in candidate and len(candidate.split()) <= 6:
            authors.append(candidate)

    prepared_by = re.search(r"Prepared\s+by[^\n&]*&(.+?)\\\\", tex_text, re.IGNORECASE)
    if prepared_by:
        authors.insert(0, clean_latex_person_name(prepared_by.group(1)))
    return dedupe_preserve_order(authors)


def extract_latex_year(tex_text: str) -> str | None:
    for command in ("IACpaperyear", "paperyear"):
        for argument in latex_command_arguments(tex_text, command):
            match = re.search(r"\b(?:19|20)\d{2}\b", argument)
            if match:
                return match.group(0)
    return None


TEX_DEPENDENCY_SUFFIXES = {
    ".tex",
    ".bib",
    ".bst",
    ".cls",
    ".sty",
    ".csl",
    ".png",
    ".jpg",
    ".jpeg",
    ".pdf",
    ".eps",
    ".svg",
}


def tex_dependency_files(tex_path: Path) -> list[Path]:
    package_root = tex_path.parent.resolve()
    dependencies: set[Path] = set()
    pending = [tex_path.resolve()]
    seen_tex: set[Path] = set()

    def add_candidate(raw_value: str, suffixes: tuple[str, ...]) -> Path | None:
        value = raw_value.strip().strip('"\'')
        if not value or "#" in value:
            return None
        candidate = (package_root / value).resolve()
        try:
            candidate.relative_to(package_root)
        except ValueError:
            return None
        variants = [candidate] if candidate.suffix else [candidate.with_suffix(suffix) for suffix in suffixes]
        return next((path for path in variants if path.is_file()), None)

    while pending:
        current = pending.pop()
        if current in seen_tex or not current.is_file():
            continue
        seen_tex.add(current)
        dependencies.add(current)
        text = read_text(current)

        reference_specs = (
            (r"\\(?:input|include|subfile)\s*\{([^{}]+)\}", (".tex",)),
            (r"\\includegraphics(?:\[[^\]]*\])?\s*\{([^{}]+)\}", (".pdf", ".png", ".jpg", ".jpeg", ".eps", ".svg")),
            (r"\\(?:bibliography|addbibresource)(?:\[[^\]]*\])?\s*\{([^{}]+)\}", (".bib",)),
            (r"\\documentclass(?:\[[^\]]*\])?\s*\{([^{}]+)\}", (".cls",)),
            (r"\\usepackage(?:\[[^\]]*\])?\s*\{([^{}]+)\}", (".sty",)),
        )
        for pattern, suffixes in reference_specs:
            for match in re.finditer(pattern, text):
                for raw_value in match.group(1).split(","):
                    candidate = add_candidate(raw_value, suffixes)
                    if candidate is None or candidate.suffix.lower() not in TEX_DEPENDENCY_SUFFIXES:
                        continue
                    dependencies.add(candidate)
                    if candidate.suffix.lower() == ".tex":
                        pending.append(candidate)

    for suffix in (".bib", ".bst", ".csl"):
        adjacent = tex_path.with_suffix(suffix).resolve()
        if adjacent.is_file():
            dependencies.add(adjacent)
    return sorted(dependencies)


def tex_package_digest(tex_path: Path) -> str:
    digest = hashlib.sha256()
    package_root = tex_path.parent.resolve()
    for path in tex_dependency_files(tex_path):
        digest.update(path.relative_to(package_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_hash(path).encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest()


def pandoc_latex_fragment(pandoc_bin: str, fragment: str, cwd: Path) -> str:
    if not fragment.strip():
        return ""
    result = subprocess.run(
        [pandoc_bin, "--from=latex", "--to=markdown+tex_math_dollars", "--wrap=none"],
        cwd=cwd,
        input=fragment,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        return normalize_text(fragment)
    return result.stdout.strip()


def run_pandoc_for_tex(root: Path, tex_path: Path) -> tuple[str, str]:
    pandoc_bin = resolve_pandoc_bin(root)
    if not pandoc_bin:
        raise RuntimeError("Pandoc is unavailable; install it with `brew install pandoc`")

    command = [
        pandoc_bin,
        tex_path.name,
        "--from=latex",
        "--to=markdown+tex_math_dollars+pipe_tables+fenced_code_blocks+yaml_metadata_block",
        "--standalone",
        "--wrap=none",
        f"--resource-path={tex_path.parent}",
    ]
    bibliographies = sorted(tex_path.parent.glob("*.bib"))
    for bibliography in bibliographies:
        command.append(f"--bibliography={bibliography.name}")
    if bibliographies:
        command.append("--citeproc")

    result = subprocess.run(
        command,
        cwd=tex_path.parent,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "Pandoc failed").strip())
    extracted = result.stdout.strip()
    if not extracted:
        raise RuntimeError("Pandoc returned empty Markdown")
    return extracted, pandoc_bin


def run_markitdown(root: Path, pdf_path: Path) -> tuple[str, Path]:
    cli = resolve_markitdown_cli(root)
    if not cli:
        raise RuntimeError("MarkItDown CLI is unavailable; install _meta/requirements.txt into .venv")

    config = load_config(root)
    work_dir = root / config["pdf2md_workspace_dir"] / safe_project_name(pdf_path)
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    output_path = work_dir / "markitdown.md"

    result = subprocess.run(
        [cli, str(pdf_path), "-o", str(output_path)],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "MarkItDown failed").strip())
    if not output_path.is_file():
        raise RuntimeError("MarkItDown did not create a Markdown output file")

    extracted = output_path.read_text(encoding="utf-8", errors="replace").strip()
    if not extracted:
        raise RuntimeError("MarkItDown returned empty Markdown")
    return extracted, work_dir


def recover_markitdown_spacing(pdf_path: Path, extracted: str) -> tuple[str, str, str]:
    sample = extracted[:30000]
    fused_words = len(re.findall(r"(?<![A-Za-z])[A-Za-z]{24,}(?![A-Za-z])", sample))
    if fused_words < 30:
        return extracted, "markitdown", "markitdown"
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return extracted, "markitdown", "markitdown"
    try:
        result = subprocess.run(
            [pdftotext, "-raw", str(pdf_path), "-"],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except (OSError, subprocess.TimeoutExpired):
        return extracted, "markitdown", "markitdown"
    recovered = result.stdout.strip()
    if result.returncode != 0 or not recovered:
        return extracted, "markitdown", "markitdown"
    recovered_sample = recovered[:30000]
    recovered_fused = len(re.findall(r"(?<![A-Za-z])[A-Za-z]{24,}(?![A-Za-z])", recovered_sample))
    if recovered_fused * 5 >= fused_words or len(recovered_sample.split()) <= len(sample.split()) * 1.1:
        return extracted, "markitdown", "markitdown"
    return recovered, "markitdown+pdftotext-spacing-recovery", "pdftotext-spacing-recovery"


def pdf_page_count(pdf_path: Path) -> int:
    with pymupdf.open(pdf_path) as document:
        return document.page_count


def can_use_pdf2md(root: Path) -> bool:
    config = load_config(root)
    return resolve_node_bin(config["node_bin"]) is not None and (root / config["pdf2md_entrypoint"]).exists() and pdftocairo_path() is not None


def run_pdf2md(root: Path, pdf_path: Path) -> tuple[list[Path], Path]:
    config = load_config(root)
    workspace_root = root / config["pdf2md_workspace_dir"]
    project_name = safe_project_name(pdf_path)
    work_dir = workspace_root / project_name
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    input_copy = work_dir / f"{project_name}.pdf"
    shutil.copy2(pdf_path, input_copy)

    node_bin = resolve_node_bin(config["node_bin"])
    if not node_bin:
        raise RuntimeError("Node.js is not available on PATH")

    command = [
        node_bin,
        str(root / config["pdf2md_entrypoint"]),
        input_copy.name,
        project_name,
    ]
    result = subprocess.run(command, cwd=work_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "pdf2md failed").strip())

    image_dir = work_dir / project_name / "images"
    image_paths = sorted(path for path in image_dir.glob("*.png") if path.is_file())
    if not image_paths:
        raise RuntimeError("pdf2md did not render any page images")
    return image_paths, work_dir


def render_pdf_with_pymupdf(root: Path, pdf_path: Path) -> tuple[list[Path], Path]:
    config = load_config(root)
    workspace_root = root / config["pdf2md_workspace_dir"]
    project_name = safe_project_name(pdf_path)
    work_dir = workspace_root / project_name
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    image_dir = work_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)

    image_paths = []
    document = pymupdf.open(pdf_path)
    try:
        matrix = pymupdf.Matrix(2.0, 2.0)
        for index, page in enumerate(document, start=1):
            image_path = image_dir / f"{project_name}-{index:03d}.png"
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            pixmap.save(str(image_path))
            image_paths.append(image_path)
    finally:
        document.close()

    if not image_paths:
        raise RuntimeError("PyMuPDF did not render any page images")
    return image_paths, work_dir


def render_pdf_pages(root: Path, pdf_path: Path) -> tuple[list[Path], Path, str]:
    if can_use_pdf2md(root):
        image_paths, work_dir = run_pdf2md(root, pdf_path)
        return image_paths, work_dir, "pdf2md"
    image_paths, work_dir = render_pdf_with_pymupdf(root, pdf_path)
    return image_paths, work_dir, "pymupdf"


def image_message_block(image_path: Path) -> dict[str, Any]:
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": base64.b64encode(image_path.read_bytes()).decode("ascii"),
        },
    }


def fallback_markdown_from_pdf_pages(pdf_path: Path, page_start: int, page_end: int) -> str:
    snippets = []
    with pymupdf.open(pdf_path) as document:
        last_page = min(page_end, document.page_count)
        for page_number in range(page_start, last_page + 1):
            text = document.load_page(page_number - 1).get_text("text").strip()
            if not text:
                continue
            cleaned = re.sub(r"\n{3,}", "\n\n", text)
            snippets.append(f"### Page {page_number}\n\n{cleaned}")
    if not snippets:
        if page_start == page_end:
            return f"### Page {page_start}\n\n[No extractable text could be recovered from this page.]"
        return (
            f"### Pages {page_start}-{page_end}\n\n"
            "[No extractable text could be recovered from these pages.]"
        )
    return "\n\n".join(snippets).strip()


def tesseract_markdown_from_images(image_paths: list[Path]) -> str:
    tesseract_bin = shutil.which("tesseract")
    if not tesseract_bin:
        raise RuntimeError(
            "MarkItDown returned empty Markdown and Tesseract OCR is unavailable"
        )

    chunks = []
    for page_number, image_path in enumerate(image_paths, start=1):
        result = subprocess.run(
            [tesseract_bin, str(image_path), "stdout", "-l", "eng"],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "Tesseract failed").strip()
            raise RuntimeError(f"Tesseract failed on page {page_number}: {detail}")
        page_text = re.sub(r"\n{3,}", "\n\n", result.stdout).strip()
        if page_text:
            chunks.append(f"### Page {page_number}\n\n{page_text}")

    if not chunks:
        raise RuntimeError("Tesseract OCR returned empty Markdown")
    return "\n\n".join(chunks)


def claude_markdown_from_images(root: Path, pdf_path: Path, image_paths: list[Path]) -> str:
    config = load_config(root)
    api_key = load_claude_api_key(root)
    model = config["claude_model"]
    max_tokens = int(config["claude_max_tokens"])
    configured_batch_size = max(1, int(config["claude_page_batch_size"]))
    if len(image_paths) >= 48:
        batch_size = min(configured_batch_size, 4)
    elif len(image_paths) >= 24:
        batch_size = min(configured_batch_size, 6)
    else:
        batch_size = configured_batch_size
    paper_title = paper_title_from_name(pdf_path.name)

    chunks = []
    timeout_seconds = 180.0
    total_batches = max(1, (len(image_paths) + batch_size - 1) // batch_size)
    client = anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds, max_retries=2)
    for start in range(0, len(image_paths), batch_size):
        batch = image_paths[start:start + batch_size]
        page_start = start + 1
        page_end = start + len(batch)
        batch_number = (start // batch_size) + 1
        print(
            f"[vision] {pdf_path.name} batch {batch_number}/{total_batches} pages {page_start}-{page_end}",
            flush=True,
        )
        prompt = (
            f"You are converting page images from the research PDF titled '{paper_title}' into clean Markdown. "
            f"These images correspond to pages {page_start}-{page_end}. "
            "Transcribe the visible content faithfully. Preserve headings, bullet lists, tables, figure captions, and references when legible. "
            "Render equations in plain text or LaTeX when possible. Do not add commentary. Do not use code fences. "
            "Return only the Markdown transcription for these pages."
        )
        content = [{"type": "text", "text": prompt}]
        content.extend(image_message_block(path) for path in batch)
        text = ""
        for attempt in range(1, 4):
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    messages=[{"role": "user", "content": content}],
                    timeout=timeout_seconds,
                )
                text_blocks = [
                    block.text.strip()
                    for block in response.content
                    if getattr(block, "type", None) == "text" and getattr(block, "text", "").strip()
                ]
                if text_blocks:
                    text = "\n\n".join(text_blocks)
                    break
                fallback_text = fallback_markdown_from_pdf_pages(pdf_path, page_start, page_end)
                if fallback_text:
                    text = fallback_text
                    print(
                        f"[vision] local fallback for {pdf_path.name} pages {page_start}-{page_end} "
                        f"(stop_reason={getattr(response, 'stop_reason', None) or 'empty-response'})",
                        flush=True,
                    )
                    break
                if attempt == 3:
                    raise RuntimeError(
                        f"Claude returned no Markdown for pages {page_start}-{page_end} "
                        f"(stop_reason={getattr(response, 'stop_reason', None) or 'empty-response'})"
                    )
                print(
                    f"[vision] empty response retry {attempt}/3 for {pdf_path.name} pages {page_start}-{page_end} "
                    f"(stop_reason={getattr(response, 'stop_reason', None) or 'empty-response'})",
                    flush=True,
                )
            except (anthropic.APITimeoutError, anthropic.APIConnectionError, anthropic.APIStatusError, anthropic.APIError) as exc:
                error_text = str(exc).lower()
                if "content filtering policy" in error_text or attempt == 3:
                    fallback_text = fallback_markdown_from_pdf_pages(pdf_path, page_start, page_end)
                    if fallback_text:
                        text = fallback_text
                        print(
                            f"[vision] local fallback for {pdf_path.name} pages {page_start}-{page_end}",
                            flush=True,
                        )
                        break
                if attempt == 3:
                    raise RuntimeError(
                        f"Claude SDK request failed for pages {page_start}-{page_end} after {attempt} attempts: {exc}"
                    ) from exc
                print(
                    f"[vision] retry {attempt}/3 for {pdf_path.name} pages {page_start}-{page_end}: {exc}",
                    flush=True,
                )
                time.sleep(min(12, attempt * 3))
        if not text:
            raise RuntimeError(f"Claude returned no Markdown for pages {page_start}-{page_end}")
        chunks.append(f"## Pages {page_start}-{page_end}\n\n{text}")

    return "\n\n".join(chunks).strip()


def copy_page_images(root: Path, pdf_path: Path, image_paths: list[Path], md_path: Path) -> list[str]:
    config = load_config(root)
    destination_dir = root / config["generated_images_dir"] / safe_project_name(pdf_path)
    if destination_dir.exists():
        shutil.rmtree(destination_dir)
    destination_dir.mkdir(parents=True, exist_ok=True)

    relative_paths = []
    for image_path in image_paths:
        destination_path = destination_dir / image_path.name
        shutil.copy2(image_path, destination_path)
        relative_paths.append(os.path.relpath(destination_path, start=md_path.parent))
    return relative_paths


def markdown_from_pdf(
    pdf_path: Path,
    rel_pdf: str,
    extracted_text: str,
    relative_image_paths: list[str],
    conversion_pipeline: str,
    page_count: int | None = None,
    transcription_mode: str | None = None,
) -> str:
    title = detect_title(extracted_text, pdf_path)
    body = extracted_text or "The configured PDF converter did not return readable text for this PDF."
    transcription_mode = transcription_mode or cache_transcription_mode(extracted_text)
    year = source_filename_parts(pdf_path).get("year")
    authors = extract_authors(extracted_text, title, pdf_path)
    doi = extract_doi(extracted_text)
    arxiv_id = extract_arxiv_id(extracted_text)
    venue = extract_venue(extracted_text, doi=doi, arxiv_id=arxiv_id)
    github_links = extract_github_links(extracted_text)
    source_id = derive_citation_key(title, pdf_path, authors, year)
    page_count = page_count if page_count is not None else len(relative_image_paths)
    image_dir = os.path.dirname(relative_image_paths[0]) if relative_image_paths else ""
    lines = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        "note_type: \"source_cache\"",
        f"schema_version: {json.dumps(SCHEMA_VERSION)}",
        f"source_id: {json.dumps(source_id, ensure_ascii=False)}",
        f"source_pdf: {json.dumps(rel_pdf, ensure_ascii=False)}",
        "source_kind: \"raw_pdf\"",
        *render_yaml_list("authors", authors),
    ]
    if year:
        lines.append(f"year: {year}")
    if venue:
        lines.append(f"venue: {json.dumps(venue, ensure_ascii=False)}")
    if doi:
        lines.append(f"doi: {json.dumps(doi, ensure_ascii=False)}")
    if arxiv_id:
        lines.append(f"arxiv_id: {json.dumps(arxiv_id, ensure_ascii=False)}")
    lines.extend(render_yaml_list("github_links", github_links))
    lines.extend(
        [
        f"page_count: {page_count}",
        f"page_image_dir: {json.dumps(image_dir, ensure_ascii=False)}",
        f"converted_at: {today_string()}",
        f"conversion_pipeline: {json.dumps(conversion_pipeline, ensure_ascii=False)}",
        "cache_role: \"pdf-source-cache\"",
        f"transcription_mode: {json.dumps(transcription_mode)}",
        *render_yaml_list("tags", ["research/cache", "cache/pdf-transcript", f"transcription/{transcription_mode.replace('_', '-')}"]),
        "---",
        "",
        f"# {title}",
        "",
        f"> Working markdown cache generated from `{rel_pdf}` on {today_string()}. The raw PDF remains the source of truth.",
        "",
        "## Conversion Snapshot",
        "",
        f"- Source ID: `{source_id}`",
        f"- Pipeline: `{conversion_pipeline}`",
        f"- Page count: `{page_count}`",
        f"- Page image directory: `{image_dir or '_meta/source_page_images/'}`",
        "",
    ]
    )
    if venue or doi or arxiv_id or github_links:
        lines.extend(["## Bibliographic Signals", ""])
        if venue:
            lines.append(f"- Venue: {venue}")
        if doi:
            lines.append(f"- DOI: `{doi}`")
        if arxiv_id:
            lines.append(f"- arXiv: `{arxiv_id}`")
        if github_links:
            lines.append("- GitHub: " + " · ".join(f"[{github_link_label(url)}]({url})" for url in github_links))
        lines.append("")
    lines.extend(["## Preview", ""])
    if relative_image_paths:
        lines.extend([f"![{Path(relative_image_paths[0]).name}]({relative_image_paths[0]})", ""])
    else:
        lines.extend(["No page preview was generated by the text-only conversion pipeline.", ""])
    lines.extend([
        "## Extracted Markdown",
        "",
        body.strip(),
        "",
    ])
    return "\n".join(lines)


def existing_relative_page_images(root: Path, pdf_path: Path, md_path: Path) -> list[str]:
    image_dir = page_image_directory_path(root, pdf_path)
    if not image_dir.exists():
        return []
    return [os.path.relpath(path, start=md_path.parent) for path in sorted(image_dir.glob("*.png")) if path.is_file()]


def refresh_pdf_cache_note(root: Path, pdf_path: Path) -> dict[str, Any]:
    md_path = converted_pdf_markdown_path(root, pdf_path)
    if not md_path.exists():
        raise FileNotFoundError(md_path)
    existing = read_text(md_path)
    extracted = extracted_markdown_body(existing)
    page_count_raw = frontmatter_scalar(existing, "page_count") or ""
    expected_count = int(page_count_raw) if page_count_raw.isdigit() else None
    conversion_pipeline = frontmatter_scalar(existing, "conversion_pipeline") or "pdf2md+claude-vision"
    transcription_mode = frontmatter_scalar(existing, "transcription_mode")
    if conversion_pipeline.startswith("markitdown"):
        relative_image_paths = []
        expected_count = expected_count or pdf_page_count(pdf_path)
    else:
        relative_image_paths = ensure_page_images(root, pdf_path, md_path, expected_count=expected_count)
    markdown = markdown_from_pdf(
        pdf_path,
        pdf_path.relative_to(root).as_posix(),
        extracted,
        relative_image_paths,
        conversion_pipeline,
        page_count=expected_count,
        transcription_mode=transcription_mode,
    )
    changed = write_text_if_changed(md_path, markdown)
    return {
        "source_pdf": pdf_path.relative_to(root).as_posix(),
        "cache_markdown": md_path.relative_to(root).as_posix(),
        "written": changed,
    }


def convert_pdfs(root: Path, force: bool = False) -> dict[str, Any]:
    ensure_project_dirs(root)
    converted = []
    failures = []

    pdf_files = raw_pdf_files(root)
    for pdf_path in pdf_files:
        rel_pdf = pdf_path.relative_to(root).as_posix()
        md_path = converted_pdf_markdown_path(root, pdf_path)
        needs_regen = force or (not md_path.exists()) or (pdf_path.stat().st_mtime_ns > md_path.stat().st_mtime_ns)
        if needs_regen:
            work_dir = None
            try:
                config = load_config(root)
                backend = str(config.get("pdf_conversion_backend", "markitdown")).strip().lower()
                if backend == "markitdown":
                    try:
                        extracted, work_dir = run_markitdown(root, pdf_path)
                        extracted, pipeline, transcription_mode = recover_markitdown_spacing(pdf_path, extracted)
                        markdown = markdown_from_pdf(
                            pdf_path,
                            rel_pdf,
                            extracted,
                            [],
                            pipeline,
                            page_count=pdf_page_count(pdf_path),
                            transcription_mode=transcription_mode,
                        )
                    except RuntimeError as error:
                        if str(error) != "MarkItDown returned empty Markdown":
                            raise
                        image_paths, work_dir, render_pipeline = render_pdf_pages(root, pdf_path)
                        extracted = tesseract_markdown_from_images(image_paths)
                        relative_image_paths = copy_page_images(root, pdf_path, image_paths, md_path)
                        markdown = markdown_from_pdf(
                            pdf_path,
                            rel_pdf,
                            extracted,
                            relative_image_paths,
                            f"markitdown+{render_pipeline}+tesseract-ocr",
                            page_count=pdf_page_count(pdf_path),
                            transcription_mode="markitdown-ocr-fallback",
                        )
                elif backend == "claude-vision":
                    image_paths, work_dir, render_pipeline = render_pdf_pages(root, pdf_path)
                    extracted = claude_markdown_from_images(root, pdf_path, image_paths)
                    relative_image_paths = copy_page_images(root, pdf_path, image_paths, md_path)
                    markdown = markdown_from_pdf(
                        pdf_path,
                        rel_pdf,
                        extracted,
                        relative_image_paths,
                        f"{render_pipeline}+claude-vision",
                    )
                else:
                    raise RuntimeError(f"Unsupported PDF conversion backend: {backend}")
                changed = write_text_if_changed(md_path, markdown)
                converted.append({"source_pdf": rel_pdf, "cache_markdown": md_path.relative_to(root).as_posix(), "written": changed})
            except Exception as exc:
                failures.append({"source_pdf": rel_pdf, "error": str(exc)})
                continue
            finally:
                if work_dir is not None:
                    shutil.rmtree(work_dir, ignore_errors=True)

    return {"converted": converted, "archived": [], "failures": failures}


def markdown_from_tex(
    tex_path: Path,
    rel_tex: str,
    pandoc_markdown: str,
    pandoc_bin: str,
    source_digest: str,
) -> str:
    tex_text = read_text(tex_path)
    title = frontmatter_scalar(pandoc_markdown, "title") or ""
    latex_titles = latex_command_arguments(tex_text, "title")
    if latex_titles:
        latex_title = normalize_text(pandoc_latex_fragment(pandoc_bin, latex_titles[0], tex_path.parent))
        latex_title = normalize_text(re.sub(r"\\+", " ", latex_title))
        if latex_title and (not title or len(latex_title) > len(title)):
            title = latex_title
    if not title:
        pdf_title = re.search(r"pdftitle\s*=\s*\{([^{}]+)\}", tex_text, re.IGNORECASE)
        title = pdf_title.group(1).strip() if pdf_title else paper_title_from_name(tex_path.name)
    if "supplement" in tex_path.stem.lower() and "supplement" not in title.lower():
        title = f"{title} - Supplementary Information"
    generic_supplement = re.match(r"^Supplementary Information\s*:\s*(.+)$", title, re.IGNORECASE)
    if generic_supplement:
        title = f"{generic_supplement.group(1).strip()} - Supplementary Information"
    title = normalize_page_title(title)

    abstract_source = latex_abstract_source(tex_text)
    abstract = pandoc_latex_fragment(pandoc_bin, abstract_source, tex_path.parent)
    authors = extract_latex_authors(tex_text)
    year = source_filename_parts(tex_path).get("year") or extract_latex_year(tex_text)
    source_id = derive_citation_key(title, tex_path, authors, year)
    package_root = tex_path.parent.resolve()
    dependencies = [path.relative_to(package_root).as_posix() for path in tex_dependency_files(tex_path)]
    body = strip_frontmatter(pandoc_markdown).strip()

    lines = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        "note_type: \"source_cache\"",
        f"schema_version: {json.dumps(SCHEMA_VERSION)}",
        f"source_id: {json.dumps(source_id, ensure_ascii=False)}",
        f"source_tex: {json.dumps(rel_tex, ensure_ascii=False)}",
        "source_kind: \"raw_tex\"",
        *render_yaml_list("authors", authors),
    ]
    if year:
        lines.append(f"year: {year}")
    lines.extend(
        [
            f"converted_at: {today_string()}",
            "conversion_pipeline: \"pandoc-latex-to-markdown\"",
            "cache_role: \"latex-source-cache\"",
            "transcription_mode: \"source-native\"",
            f"source_digest: {json.dumps(source_digest)}",
            *render_yaml_list("dependencies", dependencies),
            *render_yaml_list("tags", ["research/cache", "cache/latex-transcript", "transcription/source-native"]),
            "---",
            "",
            f"# {title}",
            "",
            f"> Working Markdown cache generated from `{rel_tex}` on {today_string()}. The immutable LaTeX package remains the source of truth.",
            "",
            "## Conversion Snapshot",
            "",
            f"- Source ID: `{source_id}`",
            "- Pipeline: `pandoc-latex-to-markdown`",
            f"- Tracked package files: {len(dependencies)}",
            "",
        ]
    )
    if abstract:
        lines.extend(["## Abstract", "", abstract, ""])
    lines.extend(["## Extracted Markdown", "", body, ""])
    return "\n".join(lines)


def convert_tex_sources(root: Path, force: bool = False) -> dict[str, Any]:
    ensure_project_dirs(root)
    converted = []
    failures = []
    config = load_config(root)
    backend = str(config.get("tex_conversion_backend", "pandoc")).strip().lower()

    for tex_path in raw_tex_files(root):
        rel_tex = tex_path.relative_to(root).as_posix()
        md_path = converted_tex_markdown_path(root, tex_path)
        source_digest = tex_package_digest(tex_path)
        existing_digest = frontmatter_scalar(read_text(md_path), "source_digest") if md_path.exists() else None
        needs_regen = force or not md_path.exists() or existing_digest != source_digest
        if not needs_regen:
            continue
        try:
            if backend != "pandoc":
                raise RuntimeError(f"Unsupported TeX conversion backend: {backend}")
            extracted, pandoc_bin = run_pandoc_for_tex(root, tex_path)
            markdown = markdown_from_tex(tex_path, rel_tex, extracted, pandoc_bin, source_digest)
            changed = write_text_if_changed(md_path, markdown)
            converted.append(
                {
                    "source_tex": rel_tex,
                    "cache_markdown": md_path.relative_to(root).as_posix(),
                    "written": changed,
                }
            )
        except Exception as exc:
            failures.append({"source_tex": rel_tex, "error": str(exc)})

    return {"converted": converted, "archived": [], "failures": failures}


def convert_sources(root: Path, force: bool = False) -> dict[str, Any]:
    pdf_result = convert_pdfs(root, force=force)
    tex_result = convert_tex_sources(root, force=force)
    return {
        "converted": [*pdf_result["converted"], *tex_result["converted"]],
        "archived": [*pdf_result["archived"], *tex_result["archived"]],
        "failures": [*pdf_result["failures"], *tex_result["failures"]],
        "pdf_converted": len(pdf_result["converted"]),
        "tex_converted": len(tex_result["converted"]),
    }


def state_path(root: Path) -> Path:
    config = load_config(root)
    return root / config["state_file"]


def load_state(root: Path) -> dict[str, Any]:
    path = state_path(root)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"compiled_at": None, "source_docs": {}, "concepts": {}}


def save_state(root: Path, state: dict[str, Any]) -> None:
    path = state_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def build_source_profile(root: Path, logical_path: Path, content_path: Path, source_kind: str) -> dict[str, Any]:
    text = read_text(content_path)
    tracked_path = content_path if content_path.exists() else logical_path
    title = normalize_page_title(detect_title(text, logical_path))
    abstract = extract_abstract(text)
    doi = extract_doi(text)
    arxiv_id = extract_arxiv_id(text)
    venue = extract_venue(text, doi=doi, arxiv_id=arxiv_id)
    github_links = extract_github_links(text)
    transcription_mode = cache_transcription_mode(text) if source_kind in {"raw_pdf", "raw_tex"} else "raw_markdown"
    sanitized_artifact_blocks = int(frontmatter_scalar(text, "sanitized_artifact_blocks") or 0)
    reconstructed_mermaid_blocks = int(frontmatter_scalar(text, "reconstructed_mermaid_blocks") or 0)
    section_index = extract_section_headings(text, logical_path)
    body_signal = concept_body_signal(text, source_kind) if source_kind == "raw_markdown" or not abstract else ""
    concept_text = "\n\n".join(
        bit for bit in [title, abstract, "\n".join(section_index[:10]), body_signal]
        if bit
    )
    concepts = matched_concepts(concept_text)
    if not concepts:
        concepts = ["scientific-machine-learning"]
    source_rel = logical_path.relative_to(root).as_posix()
    content_rel = content_path.relative_to(root).as_posix()
    summary = trim_summary(abstract or first_meaningful_paragraph(text, title=title, limit=500) or "No summary yet.")
    filename_bits = source_filename_parts(logical_path)
    authors = extract_authors(text, title, logical_path)
    year = filename_bits.get("year") or frontmatter_scalar(text, "year")
    citation_key = derive_citation_key(title, logical_path, authors, year)
    page_count = page_count_for_pdf(root, logical_path) if source_kind == "raw_pdf" else None
    image_dir = page_image_directory_rel(root, logical_path) if source_kind == "raw_pdf" else None
    aliases = source_page_aliases(title, citation_key)
    tags = ["research/source", f"source/{source_kind.replace('_', '-')}"]
    if source_kind in {"raw_pdf", "raw_tex"}:
        tags.append(f"transcription/{transcription_mode.replace('_', '-')}")
    if reconstructed_mermaid_blocks:
        tags.append("transcription/mermaid-reconstructed")
    return {
        "source": source_rel,
        "source_files": [source_rel],
        "content_path": content_rel,
        "source_kind": source_kind,
        "source_status": "compiled",
        "transcription_mode": transcription_mode,
        "sanitized_artifact_blocks": sanitized_artifact_blocks,
        "reconstructed_mermaid_blocks": reconstructed_mermaid_blocks,
        "title": title,
        "aliases": aliases,
        "schema_version": SCHEMA_VERSION,
        "source_id": citation_key,
        "citation_key": citation_key,
        "year": int(year) if year else None,
        "lead_author": authors[0] if authors else normalize_author_token((filename_bits.get("lead_author_text") or "").split(",")[0]),
        "authors": authors,
        "doi": doi,
        "arxiv_id": arxiv_id,
        "venue": venue,
        "github_links": github_links,
        "page_count": page_count,
        "page_image_dir": image_dir,
        "section_index": section_index,
        "tags": tags,
        "hash": file_hash(tracked_path),
        "mtime_ns": tracked_path.stat().st_mtime_ns,
        "abstract": abstract,
        "summary": summary,
        "concepts": concepts,
        "keywords": top_terms(" ".join(bit for bit in [title, abstract, body_signal] if bit)),
        "domains": classify_labels(concept_text, DOMAIN_PATTERNS),
        "themes": classify_labels(concept_text, THEME_PATTERNS),
        "page": source_note_page_path(root, source_rel, title).relative_to(root).as_posix(),
    }


def best_related_slugs(current_slug: str, docs: list[dict[str, Any]], available_slugs: set[str] | None = None) -> list[str]:
    concept = CONCEPTS_BY_SLUG[current_slug]
    allowed_slugs = available_slugs or set(CONCEPTS_BY_SLUG)
    counts: Counter[str] = Counter()
    for doc in docs:
        for slug in doc.get("concepts", []):
            if slug != current_slug and slug in allowed_slugs:
                counts[slug] += 1
    ordered = []
    for slug in concept["related"]:
        if slug in CONCEPTS_BY_SLUG and slug in allowed_slugs and slug != current_slug and slug not in ordered:
            ordered.append(slug)
    for slug, _ in counts.most_common():
        if slug in allowed_slugs and slug != current_slug and slug not in ordered:
            ordered.append(slug)
        if len(ordered) >= 6:
            break
    return ordered[:6]


def wiki_link(title: str) -> str:
    return f"[[{normalize_page_title(title)}]]"


def render_yaml_list(key: str, values: list[str]) -> list[str]:
    if not values:
        return [f"{key}: []"]
    lines = [f"{key}:"]
    for value in values:
        lines.append(f"  - {json.dumps(value, ensure_ascii=False)}")
    return lines


CURATED_NOTE_TYPE = "curated"
CURATED_SECTION_HEADING = "## Curated notes"


def curated_dir_path(root: Path) -> Path:
    """Folder holding hand-maintained concept fragments (`wiki/curated/<slug>.md`)."""
    config = load_config(root)
    return root / config.get("curated_dir", "wiki/curated")


def curated_note_path(root: Path, concept_slug: str) -> Path:
    return curated_dir_path(root) / f"{concept_slug}.md"


def is_curated_fragment(markdown_text: str) -> bool:
    """True for `note_type: curated` fragments, which are inlined into concept pages and are never standalone wiki documents."""
    declared = (frontmatter_scalar(markdown_text, "note_type") or "").strip().lower()
    return declared == CURATED_NOTE_TYPE


def curated_note_body(markdown_text: str) -> str:
    """Body of a curated fragment: frontmatter stripped, one leading H1 dropped, wikilinks and everything else kept verbatim."""
    lines = strip_frontmatter(markdown_text).splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r"^#\s+\S", lines[0]):
        lines.pop(0)
    return "\n".join(lines).strip("\n")


def load_curated_note(root: Path, concept_slug: str) -> dict[str, str] | None:
    path = curated_note_path(root, concept_slug)
    if not path.is_file():
        return None
    body = curated_note_body(read_text(path))
    if not body:
        return None
    return {"path": path.relative_to(root).as_posix(), "body": body}


def concept_is_pinned(root: Path, concept_slug: str) -> bool:
    """A pinned concept is generated even with zero matching sources and is never deleted as stale."""
    concept = CONCEPTS_BY_SLUG.get(concept_slug)
    if not concept:
        return False
    if concept.get("keep_without_sources"):
        return True
    return curated_note_path(root, concept_slug).is_file()


def concept_article_content(
    concept_slug: str,
    docs: list[dict[str, Any]],
    compile_date: str,
    available_slugs: set[str],
    curated_note: dict[str, str] | None = None,
) -> str:
    concept = CONCEPTS_BY_SLUG[concept_slug]
    docs_sorted = sorted(docs, key=lambda item: item["title"].lower())
    source_paths = dedupe_preserve_order(
        [
            source
            for doc in docs_sorted
            for source in doc.get("source_files", [doc["source"]])
        ]
    )
    related_slugs = best_related_slugs(concept_slug, docs_sorted, available_slugs)
    related_links = [wiki_link(CONCEPTS_BY_SLUG[slug]["title"]) for slug in related_slugs]
    source_pages = [wiki_link(doc["title"]) for doc in docs_sorted]

    domain_counts = Counter(domain for doc in docs_sorted for domain in doc.get("domains", []))
    theme_counts = Counter(theme for doc in docs_sorted for theme in doc.get("themes", []))
    keyword_counts = Counter(keyword for doc in docs_sorted for keyword in doc.get("keywords", []))

    top_domains = [label for label, _ in domain_counts.most_common(3)]
    top_themes = [label for label, _ in theme_counts.most_common(3)]
    top_keywords = [label for label, _ in keyword_counts.most_common(5) if label not in {"using", "based"}]
    concept_aliases = dedupe_preserve_order([concept["title"], *concept["aliases"]])

    if docs_sorted:
        intro_bits = [f"[[{concept['title']}]] appears across `raw/` as {concept['description']}."]
    else:
        intro_bits = [
            f"[[{concept['title']}]] is catalogued as {concept['description']}.",
            "No source in `raw/` or `Clippings/` currently matches its aliases; the page is kept because it carries curated notes or is pinned in the concept catalog.",
        ]
    if top_domains:
        intro_bits.append(f"The strongest source cluster is in {', '.join(top_domains)}.")
    if related_links:
        intro_bits.append(f"It is most often discussed alongside {', '.join(related_links[:3])}.")

    if docs_sorted:
        takeaways = [
            f"The matched sources frame {concept['title']} through {', '.join(top_themes) if top_themes else 'recurring modeling and evaluation concerns'}.",
            f"Representative application areas include {', '.join(top_domains) if top_domains else 'multiple scientific domains'}.",
            f"Recurring vocabulary around this concept includes {', '.join(top_keywords[:5]) if top_keywords else 'simulation, modeling, and design'}.",
        ]
    else:
        takeaways = [
            "No source currently matches this concept's aliases, so the compiler has nothing to synthesize yet.",
            "Add a raw note or clipping that carries one of the aliases early in its body to populate this section.",
        ]

    if docs_sorted:
        representative = [f"- [[{doc['title']}]] from `{doc['source']}`" for doc in docs_sorted[:8]]
    else:
        representative = ["- Representative sources: none matched yet."]

    curated_section: list[str] = []
    if curated_note:
        curated_section = [
            CURATED_SECTION_HEADING,
            "",
            f"*Hand-maintained in {curated_note['path']}; the other sections are compiler output.*",
            "",
            curated_note["body"],
            "",
        ]
    related_section = [f"- {link}" for link in related_links] if related_links else ["- No related concept links yet."]

    lines = [
        "---",
        f"title: {json.dumps(concept['title'], ensure_ascii=False)}",
        *render_yaml_list("aliases", concept_aliases),
        "note_type: \"concept\"",
        f"schema_version: {json.dumps(SCHEMA_VERSION)}",
        f"concept_group: {json.dumps(concept['group'], ensure_ascii=False)}",
        f"source_count: {len(docs_sorted)}",
        *([f"curated_note: {json.dumps(curated_note['path'], ensure_ascii=False)}"] if curated_note else []),
        *render_yaml_list("sources", source_paths),
        *render_yaml_list("source_pages", source_pages),
        *render_yaml_list("related", related_links),
        *render_yaml_list("tags", ["research/concept", f"group/{slugify(concept['group'])}"]),
    ]
    lines.append(f"last_compiled: {compile_date}")
    lines.extend(
        [
            "---",
            "",
            f"# {concept['title']}",
            "",
            "> This concept page is synthesized across the current source pages and is maintained by the wiki compiler.",
            "",
            "## Definition",
            "",
            " ".join(intro_bits),
            "",
            *curated_section,
            "## What The Sources Emphasize",
            "",
            *[f"- {item}" for item in takeaways],
            "",
            "## Coverage",
            "",
            f"- Source pages: {len(docs_sorted)}",
            f"- Concept group: {concept['group']}",
            f"- Top domains: {', '.join(top_domains) if top_domains else 'Not established yet.'}",
            f"- Top themes: {', '.join(top_themes) if top_themes else 'Not established yet.'}",
            "",
            "## Related Concepts",
            "",
            *related_section,
            "",
            "## Representative sources",
            "",
            *representative,
            "",
            "## Provenance",
            "",
            f"- Last compiled: {compile_date}",
            f"- Schema version: `{SCHEMA_VERSION}`",
            "",
        ]
    )
    return "\n".join(lines)


def source_page_content(profile: dict[str, Any], compile_date: str) -> str:
    related_links = [wiki_link(CONCEPTS_BY_SLUG[slug]["title"]) for slug in profile.get("concepts", []) if slug in CONCEPTS_BY_SLUG]
    aliases = dedupe_preserve_order([profile["title"], *profile.get("aliases", [])])
    tags = list(profile.get("tags", []))
    display_abstract = trim_abstract_for_card(profile.get("abstract", ""))
    citation_lines = compact_citation_lines(profile)
    _, full_author_list = compact_author_metadata(profile)
    if profile.get("year"):
        tags.append(f"year/{profile['year']}")
    tags = dedupe_preserve_order(tags)
    lines = [
        "---",
        f"title: {json.dumps(profile['title'], ensure_ascii=False)}",
        *render_yaml_list("aliases", aliases),
        "note_type: \"source\"",
        f"schema_version: {json.dumps(profile.get('schema_version', SCHEMA_VERSION))}",
        f"source_id: {json.dumps(profile['source_id'], ensure_ascii=False)}",
        f"citation_key: {json.dumps(profile['citation_key'], ensure_ascii=False)}",
        f"source_kind: {json.dumps(profile['source_kind'], ensure_ascii=False)}",
        f"source_status: {json.dumps(profile['source_status'], ensure_ascii=False)}",
    ]
    if profile.get("year"):
        lines.append(f"year: {profile['year']}")
    if profile.get("lead_author"):
        lines.append(f"lead_author: {json.dumps(profile['lead_author'], ensure_ascii=False)}")
    if profile.get("venue"):
        lines.append(f"venue: {json.dumps(profile['venue'], ensure_ascii=False)}")
    if profile.get("doi"):
        lines.append(f"doi: {json.dumps(profile['doi'], ensure_ascii=False)}")
    if profile.get("arxiv_id"):
        lines.append(f"arxiv_id: {json.dumps(profile['arxiv_id'], ensure_ascii=False)}")
    lines.extend(
        [
        *render_yaml_list("authors", profile.get("authors", [])),
        *render_yaml_list("github_links", profile.get("github_links", [])),
        *render_yaml_list("sources", profile.get("source_files", [profile["source"]])),
        *render_yaml_list("concepts", related_links),
        *render_yaml_list("domains", profile.get("domains", [])),
        *render_yaml_list("themes", profile.get("themes", [])),
        *render_yaml_list("section_index", profile.get("section_index", [])),
        *render_yaml_list("tags", tags),
        *render_yaml_list("related", related_links),
        ]
    )
    if profile.get("content_path") and profile["content_path"] != profile["source"]:
        lines.append(f"cache_path: {json.dumps(profile['content_path'], ensure_ascii=False)}")
    if profile.get("page_image_dir"):
        lines.append(f"page_image_dir: {json.dumps(profile['page_image_dir'], ensure_ascii=False)}")
    if profile.get("page_count"):
        lines.append(f"page_count: {profile['page_count']}")
    if profile.get("sanitized_artifact_blocks"):
        lines.append(f"sanitized_artifact_blocks: {profile['sanitized_artifact_blocks']}")
    if profile.get("reconstructed_mermaid_blocks"):
        lines.append(f"reconstructed_mermaid_blocks: {profile['reconstructed_mermaid_blocks']}")
    lines.extend(
        [
            f"last_compiled: {compile_date}",
            "---",
            "",
            f"# {profile['title']}",
            "",
            f"> This source page is maintained by the wiki compiler so the vault can summarize, link, and query `{profile['source']}` without modifying the raw source.",
            "",
            "## Citation & Files",
            "",
            *citation_lines,
        ]
    )
    if full_author_list:
        lines.extend(
            [
                "",
                "<details>",
                "<summary>Full author list</summary>",
                "",
                *[f"- {author}" for author in full_author_list],
                "</details>",
            ]
        )
    if profile.get("reconstructed_mermaid_blocks") and profile.get("content_path"):
        clean_href = os.path.relpath(
            profile["content_path"],
            start=Path(profile["page"]).parent.as_posix(),
        )
        lines.extend(
            [
                "",
                "## Reconstructed Reading Copy",
                "",
                f"- [Open the clean full-text Markdown](<{clean_href}>)",
                f"- Reconstructed {profile['reconstructed_mermaid_blocks']} Mermaid diagram(s) from the article's original Markdown; the immutable clipping remains unchanged.",
            ]
        )
    lines.extend(["", "## TL;DR", "", profile.get("summary") or "No summary yet.", ""])
    lines.extend(["## Abstract", "", display_abstract or "No concise abstract was extracted from this source yet.", ""])
    if related_links:
        lines.extend(["## Key Concepts", ""])
        lines.extend(f"- {link}" for link in related_links)
        lines.append("")
    if profile.get("domains") or profile.get("themes") or profile.get("keywords"):
        lines.extend(["## Research Signals", ""])
        if profile.get("domains"):
            lines.append(f"- Domains: {', '.join(profile['domains'])}")
        if profile.get("themes"):
            lines.append(f"- Themes: {', '.join(profile['themes'])}")
        if profile.get("keywords"):
            lines.append(f"- Keywords: {', '.join(profile['keywords'][:6])}")
        lines.append("")
    if profile.get("section_index"):
        lines.extend(["## Reading Map", ""])
        lines.extend(f"- {heading}" for heading in profile["section_index"])
        lines.append("")
    lines.extend(
        [
            "## Provenance",
            "",
            f"- Last compiled: {compile_date}",
            f"- Schema version: `{profile.get('schema_version', SCHEMA_VERSION)}`",
            "",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def note_blurb(text: str, fallback: str = "No summary yet.") -> str:
    body = strip_frontmatter(text)
    snippets = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(">"):
            continue
        snippets.append(stripped)
        if len(" ".join(snippets)) > 260:
            break
    return trim_summary(" ".join(snippets) or fallback, limit=160)


def collect_derived_notes(root: Path) -> list[dict[str, str]]:
    config = load_config(root)
    derived_dir = root / config["derived_wiki_dir"]
    notes = []
    for path in sorted(derived_dir.glob("*.md")):
        if not path.is_file() or path.name == "README.md":
            continue
        text = read_text(path)
        notes.append(
            {
                "path": path.relative_to(root).as_posix(),
                "title": detect_title(text, path),
                "summary": note_blurb(text),
            }
        )
    return notes


def collect_project_notes(root: Path) -> list[dict[str, str]]:
    config = load_config(root)
    projects_dir = root / config.get("projects_dir", "wiki/projects")
    notes = []
    for path in sorted(projects_dir.glob("*.md")):
        if not path.is_file() or path.name == "README.md":
            continue
        text = read_text(path)
        parent_project_id = frontmatter_scalar(text, "parent_project_id") or ""
        notes.append(
            {
                "path": path.relative_to(root).as_posix(),
                "title": detect_title(text, path),
                "summary": note_blurb(text),
                "project_id": frontmatter_scalar(text, "project_id") or path.stem,
                "project_name": frontmatter_scalar(text, "project_name") or detect_title(text, path),
                "project_level": frontmatter_scalar(text, "project_level") or ("subproject" if parent_project_id else "programme"),
                "parent_project_id": parent_project_id,
                "status": frontmatter_scalar(text, "project_status") or "active",
                "snapshot_date": frontmatter_scalar(text, "snapshot_date") or "",
            }
        )
    return notes


def render_log_index(root: Path) -> str:
    config = load_config(root)
    path = root / config["log_path"]
    if path.exists():
        return read_text(path)
    return "# Wiki Log\n\nAppend-only log of ingests, queries, and lint passes.\n"


def append_log_entry(root: Path, category: str, title: str, details: list[str]) -> None:
    config = load_config(root)
    path = root / config["log_path"]
    if not path.exists():
        path.write_text("# Wiki Log\n\nAppend-only log of ingests, queries, and lint passes.\n\n", encoding="utf-8")

    lines = [f"## [{timestamp_string()}] {category} | {title}", ""]
    lines.extend(f"- {detail}" for detail in details)
    lines.extend(["", ""])
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def render_index(root: Path, source_docs: dict[str, dict[str, Any]], concept_docs: dict[str, list[dict[str, Any]]], compile_date: str) -> str:
    available_slugs = set(concept_docs)
    grouped: dict[str, list[str]] = defaultdict(list)
    for slug in concept_docs:
        grouped[CONCEPTS_BY_SLUG[slug]["group"]].append(slug)

    config = load_config(root)
    derived_notes = collect_derived_notes(root)
    project_notes = collect_project_notes(root)

    lines = [
        "# Research Wiki Index",
        "",
        f"- Last compiled: {compile_date}",
        f"- Raw sources represented in the wiki: {len(source_docs)}",
        f"- Concepts: {len(concept_docs)}",
        "- System overview: [SYSTEM_OVERVIEW](SYSTEM_OVERVIEW.md)",
        "- Page formats: [PAGE_FORMATS](PAGE_FORMATS.md)",
        "- Paper template: [PAPER_TEMPLATE](PAPER_TEMPLATE.md)",
        "- Schema: [AGENTS](../AGENTS.md)",
        "- Log: [LOG](LOG.md)",
        "- Health checks: [LINT_AND_HEAL](LINT_AND_HEAL.md)",
        "- Projects: [projects/README](projects/README.md)",
        "- Filed-back notes: [derived/README](derived/README.md)",
        f"- Open Knowledge Format export: [output/okf](../{config.get('okf_dir', 'output/okf')}/index.md)",
        "",
        "## System Pages",
        "",
        "| Page | Purpose |",
        "| --- | --- |",
        "| [SYSTEM_OVERVIEW](SYSTEM_OVERVIEW.md) | High-level pipeline and directory map |",
        "| [PAGE_FORMATS](PAGE_FORMATS.md) | Canonical frontmatter and section layouts for cache, source, and concept pages |",
        "| [PAPER_TEMPLATE](PAPER_TEMPLATE.md) | Recommended literature-note template for PDF-derived source pages |",
        "| [LOG](LOG.md) | Append-only chronology of ingests, queries, and lint passes |",
        "| [LINT_AND_HEAL](LINT_AND_HEAL.md) | Health checks, contradictions, orphans, and cleanup suggestions |",
        "| [projects/README](projects/README.md) | Active research programmes and project dossiers |",
        "| [derived/README](derived/README.md) | How query outputs get filed back into the wiki |",
        f"| [output/okf](../{config.get('okf_dir', 'output/okf')}/index.md) | Portable OKF v0.2 bundle with standard links, provenance, trust, freshness, manifest, and conformance report |",
        "",
        "## Projects",
        "",
    ]

    if project_notes:
        projects_by_id = {item["project_id"]: item for item in project_notes}
        ordered_projects = sorted(
            project_notes,
            key=lambda item: (
                item["parent_project_id"] or item["project_id"],
                bool(item["parent_project_id"]),
                item["title"].lower(),
            ),
        )
        lines.extend(["| Project | Parent | Status | Snapshot | Summary |", "| --- | --- | --- | --- | --- |"])
        for item in ordered_projects:
            project_path = Path(item["path"]).relative_to(config["wiki_dir"]).as_posix()
            parent = projects_by_id.get(item["parent_project_id"])
            parent_cell = ""
            if parent:
                parent_path = Path(parent["path"]).relative_to(config["wiki_dir"]).as_posix()
                parent_cell = f"[{parent['project_name']}]({parent_path})"
            elif item["parent_project_id"]:
                parent_cell = item["parent_project_id"].upper()
            lines.append(
                f"| [{item['title']}]({project_path}) | {parent_cell} | {item['status']} | {item['snapshot_date']} | {item['summary']} |"
            )
    else:
        lines.append("- No project dossiers yet.")

    lines.extend(["", "## Source Pages", "", "| Source | Summary | Concepts |", "| --- | --- | --- |"])

    for profile in sorted(source_docs.values(), key=lambda item: item["title"].lower()):
        concept_links = [wiki_link(CONCEPTS_BY_SLUG[slug]["title"]) for slug in profile.get("concepts", []) if slug in CONCEPTS_BY_SLUG][:3]
        lines.append(
            f"| [{profile['title']}]({Path(profile['page']).relative_to(config['wiki_dir']).as_posix()}) | {profile.get('summary', '')} | {', '.join(concept_links)} |"
        )
    lines.extend(["", "## Concept Pages", ""])

    for group in sorted(grouped):
        lines.extend([f"### {group}", "", "| Concept | Sources | Related |", "| --- | ---: | --- |"])
        for slug in sorted(grouped[group], key=lambda item: CONCEPTS_BY_SLUG[item]["title"].lower()):
            concept = CONCEPTS_BY_SLUG[slug]
            docs = concept_docs[slug]
            related_titles = [wiki_link(CONCEPTS_BY_SLUG[related]["title"]) for related in best_related_slugs(slug, docs, available_slugs)[:3]]
            concept_path = f"concepts/{slug}.md"
            lines.append(
                f"| [{concept['title']}]({concept_path}) | {len(docs)} | {', '.join(related_titles) if related_titles else ''} |"
            )
        lines.extend(["", ""])

    lines.extend(["## Derived Notes", ""])
    if derived_notes:
        lines.extend(["| Note | Summary |", "| --- | --- |"])
        for item in derived_notes:
            lines.append(f"| [{item['title']}]({Path(item['path']).relative_to(config['wiki_dir']).as_posix()}) | {item['summary']} |")
    else:
        lines.append("- No filed-back notes yet.")
    lines.extend(["", "## Working Convention", "", "- Read the index first, then drill into projects, source pages, concept pages, and derived notes as needed.", "- See [[Page Formats]] when adjusting generated note layouts or metadata conventions.", ""])

    return "\n".join(lines).rstrip() + "\n"


def render_derived_home(root: Path, compile_date: str) -> str:
    derived_notes = collect_derived_notes(root)
    lines = [
        "---",
        "title: \"Derived Notes\"",
        "aliases:",
        "  - \"Derived Notes\"",
        "note_type: \"system\"",
        f"last_compiled: {compile_date}",
        "---",
        "",
        "# Derived Notes",
        "",
        f"- Last refreshed: {compile_date}",
        "",
        "This directory stores markdown answers, slide decks, and other generated artifacts that are worth filing back into the wiki.",
        "",
        "Use it when a query result should become part of the long-term knowledge base instead of staying only in `output/`.",
        "",
    ]
    lines.extend(["## Filed-back Notes", ""])
    if derived_notes:
        for item in derived_notes:
            lines.append(f"- {wiki_link(item['title'])} - {item['summary']}")
    else:
        lines.append("- No filed-back notes yet.")
    lines.append("")
    return "\n".join(lines)


def render_projects_home(root: Path, compile_date: str) -> str:
    project_notes = collect_project_notes(root)
    projects_by_id = {item["project_id"]: item for item in project_notes}
    lines = [
        "---",
        "title: \"Projects\"",
        "aliases:",
        "  - \"Project Catalog\"",
        "note_type: \"system\"",
        f"last_compiled: {compile_date}",
        "---",
        "",
        "# Projects",
        "",
        f"- Last refreshed: {compile_date}",
        "",
        "## Active Programmes",
        "",
    ]
    active_programmes = [
        item for item in project_notes
        if item["status"].lower() == "active" and not item["parent_project_id"]
    ]
    if active_programmes:
        for item in active_programmes:
            lines.append(f"- {wiki_link(item['title'])} - {item['summary']}")
    else:
        lines.append("- No active programmes yet.")

    active_subprojects = [
        item for item in project_notes
        if item["status"].lower() == "active" and item["parent_project_id"]
    ]
    if active_subprojects:
        lines.extend(["", "## Active Subprojects", ""])
        for item in active_subprojects:
            parent = projects_by_id.get(item["parent_project_id"])
            parent_label = wiki_link(parent["title"]) if parent else f"`{item['parent_project_id']}`"
            lines.append(f"- {wiki_link(item['title'])} - Part of {parent_label}. {item['summary']}")

    completed_statuses = {"complete", "completed", "done"}
    completed_subprojects = [
        item for item in project_notes
        if item["status"].lower() in completed_statuses and item["parent_project_id"]
    ]
    if completed_subprojects:
        lines.extend(["", "## Completed Subprojects", ""])
        for item in completed_subprojects:
            parent = projects_by_id.get(item["parent_project_id"])
            parent_label = wiki_link(parent["title"]) if parent else f"`{item['parent_project_id']}`"
            lines.append(f"- {wiki_link(item['title'])} - Part of {parent_label}. {item['summary']}")

    other = [
        item for item in project_notes
        if item["status"].lower() != "active" and item["status"].lower() not in completed_statuses
    ]
    if other:
        lines.extend(["", "## Other Projects", ""])
        for item in other:
            lines.append(f"- {wiki_link(item['title'])} - {item['summary']}")
    lines.append("")
    return "\n".join(lines)


def render_page_formats(compile_date: str) -> str:
    lines = [
        "---",
        "title: \"Page Formats\"",
        "aliases:",
        "  - \"Page Formats\"",
        "note_type: \"system\"",
        f"last_compiled: {compile_date}",
        "---",
        "",
        "# Page Formats",
        "",
        f"- Last refreshed: {compile_date}",
        f"- Schema version: `{SCHEMA_VERSION}`",
        "",
        "## Design Goals",
        "",
        "- Keep `raw/` immutable and move machine-generated transcript artifacts into `_meta/`.",
        "- Put Dataview-friendly metadata in frontmatter and graph-friendly wikilinks in body sections.",
        "- Keep generated source pages compact enough for browsing and Q&A, while preserving long transcripts in cache notes.",
        "- Prefer flat scalar and list properties over deeply nested YAML so Obsidian Properties and Dataview stay easy to query.",
        "",
        "## Open Knowledge Format Export",
        "",
        "The native `wiki/` schema remains optimized for Obsidian. A deterministic compatibility export under `output/okf/` targets Open Knowledge Format v0.2 without changing source or wiki documents.",
        "",
        "The export provides:",
        "- required OKF `type` metadata and standard Markdown links",
        "- structured `sources` provenance with stable identifiers and source timestamps when available",
        "- explicit `generated`, `status`, and active-project `stale_after` signals",
        "- optional explicit verification via flat native fields `okf_verified_by` and `okf_verified_at`",
        "- progressive `index.md` files and a newest-first `log.md`",
        "- `manifest.json`, `conformance.json`, and a portable ZIP archive",
        "",
        "Trust tiers are derived only from explicit verification events; compiler output is not mislabeled as human-reviewed content.",
        "",
        "## PDF Cache Notes",
        "",
        "Location: `_meta/converted_sources/*.md`",
        "",
        "Frontmatter:",
        "- `title`",
        "- `note_type: source_cache`",
        "- `schema_version`",
        "- `source_id`",
        "- `source_pdf`",
        "- `source_kind`",
        "- `authors`",
        "- `year`",
        "- `venue`",
        "- `doi`",
        "- `arxiv_id`",
        "- `github_links`",
        "- `page_count`",
        "- `page_image_dir`",
        "- `converted_at`",
        "- `conversion_pipeline`",
        "- `cache_role`",
        "- `tags`",
        "",
        "Sections:",
        "- `## Conversion Snapshot`",
        "- `## Preview`",
        "- `## Extracted Markdown`",
        "",
        "## LaTeX Cache Notes",
        "",
        "Location: `_meta/converted_sources/*.md`",
        "",
        "Frontmatter:",
        "- `title`",
        "- `note_type: source_cache`",
        "- `schema_version`",
        "- `source_id`",
        "- `source_tex`",
        "- `source_kind: raw_tex`",
        "- `authors`",
        "- `year`",
        "- `converted_at`",
        "- `conversion_pipeline: pandoc-latex-to-markdown`",
        "- `cache_role: latex-source-cache`",
        "- `source_digest`",
        "- `dependencies`",
        "- `tags`",
        "",
        "Sections:",
        "- `## Conversion Snapshot`",
        "- `## Abstract` when present",
        "- `## Extracted Markdown`",
        "",
        "## Reconstructed Clipping Cache Notes",
        "",
        "Location: `_meta/converted_sources/_sanitized_clippings/<source-hash>/*.md`",
        "",
        "Preserve the clipping's original frontmatter and add:",
        "- `sanitized_from`",
        "- `sanitization_pipeline`",
        "- `source_digest`",
        "- `sanitized_artifact_blocks`",
        "- `reconstructed_mermaid_blocks`",
        "- `mermaid_recovery_source`",
        "- `mermaid_sources_digest`",
        "",
        "Replace only high-confidence rendered Mermaid artifact fences and retain ordinary code fences and surrounding article text. Generate a cache only when the recovered definition count exactly matches the artifact count; otherwise compile the immutable clipping unchanged.",
        "",
        "## Source Pages",
        "",
        "Location: `wiki/sources/*.md`",
        "",
        "Frontmatter:",
        "- `title`",
        "- `aliases`",
        "- `note_type: source`",
        "- `schema_version`",
        "- `source_id`",
        "- `citation_key`",
        "- `source_kind`",
        "- `source_status`",
        "- `year`",
        "- `lead_author`",
        "- `venue`",
        "- `doi`",
        "- `arxiv_id`",
        "- `authors`",
        "- `github_links`",
        "- `sources`",
        "- `cache_path`",
        "- `page_image_dir`",
        "- `page_count`",
        "- `concepts`",
        "- `domains`",
        "- `themes`",
        "- `section_index`",
        "- `tags`",
        "- `related`",
        "- `last_compiled`",
        "",
        "Sections:",
        "- `## Citation & Files`",
        "- `## TL;DR`",
        "- `## Abstract`",
        "- `## Key Concepts`",
        "- `## Research Signals`",
        "- `## Reading Map`",
        "- `## Provenance`",
        "",
        "## Concept Pages",
        "",
        "Location: `wiki/concepts/*.md`",
        "",
        "Frontmatter:",
        "- `title`",
        "- `aliases`",
        "- `note_type: concept`",
        "- `schema_version`",
        "- `concept_group`",
        "- `source_count`",
        "- `curated_note` only when `wiki/curated/<slug>.md` exists",
        "- `sources`",
        "- `source_pages`",
        "- `related`",
        "- `tags`",
        "- `last_compiled`",
        "",
        "Sections:",
        "- `## Definition`",
        "- `## Curated notes` only when `wiki/curated/<slug>.md` exists (see Curated Concept Notes)",
        "- `## What The Sources Emphasize`",
        "- `## Coverage`",
        "- `## Related Concepts`",
        "- `## Representative sources`",
        "- `## Provenance`",
        "",
        "## Curated Concept Notes",
        "",
        "Location: `wiki/curated/<slug>.md`, at most one optional file per concept catalog slug (the slug is the file stem).",
        "",
        "Frontmatter:",
        "- `title`",
        "- `note_type: curated`",
        "- `concept: <slug>`",
        "- `sources` (raw paths the notes are distilled from)",
        "- `tags`",
        "- `last_edited`",
        "",
        "What compile does:",
        "- When `wiki/curated/<slug>.md` exists, `compile` strips its frontmatter and a leading H1 and inlines the body verbatim into `wiki/concepts/<slug>.md` as `## Curated notes`, placed right after `## Definition` and preceded by the italic line `Hand-maintained in wiki/curated/<slug>.md; the other sections are compiler output.` Wikilinks inside the curated text are preserved exactly as written.",
        "- A concept with a curated file, or with `keep_without_sources: true` in its catalog entry, is generated even when no source matches its aliases (`source_count: 0`, `Representative sources: none matched yet`) and is never deleted as stale.",
        "- Curated files are fragments, not pages. The lint orphan scan, `INDEX.md`, the OKF and HTML exports, and the CLI search corpus enumerate only the top-level `wiki/*.md`, `wiki/concepts/`, `wiki/sources/`, `wiki/projects/`, and `wiki/derived/`, so `wiki/curated/` never appears as a standalone document; the lint additionally skips any document declaring `note_type: curated`.",
        "- Curated text is the ONLY place hand-written concept prose survives: every other section of `wiki/concepts/*.md` is rewritten on each compile, so edit `wiki/curated/<slug>.md`, never the generated concept page.",
        "",
        "Writing guidance:",
        "- Use `###` headings inside the curated body (the generated page owns `#` and `##`).",
        "- Cite the raw source of record with a wikilink to its source page or a backticked `raw/` path; do not restate facts the source does not contain.",
        "",
        "## Project Pages",
        "",
        "Location: `wiki/projects/*.md`",
        "",
        "Frontmatter:",
        "- `title`",
        "- `aliases`",
        "- `note_type: project`",
        "- `project_id`",
        "- `project_name`",
        "- `project_level: programme | subproject`",
        "- `parent_project_id` for subprojects",
        "- `project_status`",
        "- `snapshot_date`",
        "- `sources`",
        "- `related`",
        "- `tags`",
        "",
        "Sections:",
        "- `## Programme Thesis` or `## Project Thesis`",
        "- `## Evidence Ledger`",
        "- `## Milestone Gates`",
        "- `## Negative Evidence and Open Gaps`",
        "- `## Next Execution Focus`",
        "- `## Source Package`",
        "",
        "## Querying Notes",
        "",
        "- Query frontmatter fields such as `note_type`, `year`, `lead_author`, `concept_group`, and `source_count` from Dataview.",
        "- Keep the same concepts both in frontmatter and body lists so Dataview remains structured while Graph/backlinks stay reliable.",
        "- Treat cache notes as machine-oriented transcript storage; treat source pages as the default human and agent landing pages.",
        "",
    ]
    return "\n".join(lines)


def render_system_overview(root: Path, compile_date: str, state: dict[str, Any]) -> str:
    config = load_config(root)
    source_docs = state.get("source_docs", {})
    active_source_keys = state.get("active_source_keys") or list(source_docs)
    lines = [
        "---",
        "title: \"System Overview\"",
        "aliases:",
        "  - \"System Overview\"",
        "note_type: \"system\"",
        f"last_compiled: {compile_date}",
        "---",
        "",
        "# System Overview",
        "",
        f"- Last refreshed: {compile_date}",
        f"- Immutable source files tracked: {len(source_docs)}",
        f"- Unique source pages: {len(active_source_keys)}",
        f"- Duplicate source variants merged into canonical pages: {len(state.get('duplicate_sources', {}))}",
        f"- Concept articles: {len(state.get('concepts', {}))}",
        "",
        "## Main Pipeline",
        "",
        "1. `raw/` stores source material as-is. It is the immutable source-of-truth layer.",
        "2. PDF transcription caches and rendered page images live under `_meta/`, not in `raw/`, so the compiler can process sources without mutating them.",
        "3. The compiler incrementally refreshes source pages, concept pages, the project catalog, `wiki/INDEX.md`, and `wiki/LOG.md`.",
        "4. The Q&A layer reads the maintained wiki, renders answers into markdown, Marp slides, or other output files, and can file valuable outputs back into `wiki/derived/`.",
        "5. The interchange layer exports the maintained wiki as an OKF v0.2 bundle with standard links, structured provenance, lifecycle signals, progressive indexes, and deterministic conformance checks.",
        "",
        "## Three Layers",
        "",
        "- `raw/`: immutable source documents, web clips, datasets, and local assets.",
        "- `wiki/`: LLM-maintained markdown pages including projects, source pages, concept pages, indexes, logs, and filed-back notes.",
        "- `AGENTS.md`: the in-repo schema that tells the LLM how to ingest, query, and maintain this workspace.",
        "- `wiki/PAGE_FORMATS.md`: the canonical frontmatter and section layouts for generated cache, source, and concept notes.",
        "- `wiki/PAPER_TEMPLATE.md`: the rationale and recommended structure for PDF-derived literature notes.",
        f"- `{config.get('okf_dir', 'output/okf')}/`: the portable Open Knowledge Format v0.2 compatibility bundle.",
        "",
        "## Support Layer",
        "",
        f"- Open `{root}` directly in Obsidian to browse `raw/`, `wiki/`, `_meta/`, and `output/` from one vault.",
        "- `LINT_AND_HEAL.md` tracks broken links, orphan pages, sparse concepts, low-coverage sources, and suggested cleanup passes.",
        "- `_meta/scripts/wiki_cli.py` is the unified CLI for compile, watch, search, ask, lint, OKF export, and filing outputs back into the wiki.",
        "",
        "## Directory Map",
        "",
        "| Path | Purpose |",
        "| --- | --- |",
        f"| `{config['raw_dir']}/` | immutable source documents and user-managed local assets |",
        f"| `{config['wiki_dir']}/sources/` | one wiki page per source document, maintained by the compiler |",
        f"| `{config['wiki_dir']}/concepts/` | synthesized concept pages built across many sources |",
        f"| `{config.get('curated_dir', 'wiki/curated')}/` | hand-maintained curated notes, inlined into the matching concept page at compile time (fragments, not standalone pages) |",
        f"| `{config.get('projects_dir', 'wiki/projects')}/` | active research programmes and project dossiers |",
        f"| `{config['wiki_dir']}/derived/` | valuable outputs filed back into the knowledge base |",
        f"| `{config['output_dir']}/` | generated answers, slide decks, charts, and reports |",
        f"| `{config.get('okf_dir', 'output/okf')}/` | OKF v0.2 exchange bundle, machine-readable graph manifest, and conformance report |",
        "| `_meta/` | compiler state, cached PDF transcriptions, rendered page images, scripts, and tooling |",
        "",
        "## Working Rhythm",
        "",
        "- Ingest with tools like Obsidian Web Clipper and save related source images locally in `raw/`.",
        "- Let the watcher or compile command keep source pages, concept pages, the index, and the log up to date.",
        "- Ask questions through the CLI and render results back into markdown so Obsidian remains the frontend.",
        "- Run lint passes regularly so the wiki keeps improving instead of drifting.",
        "",
    ]
    return "\n".join(lines)


def extract_wiki_links(text: str) -> list[str]:
    links = []
    for raw_target in WIKILINK_RE.findall(text):
        target = raw_target.split("|", 1)[0].strip()
        if target:
            links.append(target)
    return links


def extract_internal_markdown_links(text: str, source_path: Path, root: Path) -> list[str]:
    links = []
    for raw_target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        target = raw_target.strip()
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        target = unquote(target.split("#", 1)[0].strip())
        if not target.endswith(".md"):
            continue
        resolved = (source_path.parent / target).resolve()
        try:
            relative = resolved.relative_to(root).as_posix()
        except ValueError:
            continue
        if resolved.is_file():
            links.append(relative)
    return dedupe_preserve_order(links)


def lint_wiki(root: Path, compile_date: str | None = None, state: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_project_dirs(root)
    config = load_config(root)
    compile_date = compile_date or today_string()
    state = state or load_state(root)

    wiki_dir = root / config["wiki_dir"]
    concepts_dir = root / config["concepts_dir"]
    sources_dir = root / config["source_notes_dir"]
    derived_dir = root / config["derived_wiki_dir"]
    projects_dir = root / config.get("projects_dir", "wiki/projects")
    report_path = root / config["lint_report_path"]

    core_docs = [
        path
        for path in [
            wiki_dir / "INDEX.md",
            wiki_dir / "SYSTEM_OVERVIEW.md",
            wiki_dir / "PAGE_FORMATS.md",
            wiki_dir / "LOG.md",
            report_path,
        ]
        if path.exists()
    ]
    wiki_docs = sorted(
        path
        for path in core_docs
        + list(concepts_dir.glob("*.md"))
        + list(sources_dir.glob("*.md"))
        + list(projects_dir.glob("*.md"))
        + list(derived_dir.glob("*.md"))
        if path.is_file()
    )
    # Curated fragments (wiki/curated/*.md, note_type "curated") are inlined into concept
    # pages by the compiler and are never standalone documents for link/orphan checks.
    wiki_docs = [path for path in wiki_docs if not is_curated_fragment(read_text(path))]
    title_owner: dict[str, str] = {}
    path_owner: dict[str, str] = {}
    for path in wiki_docs:
        text = read_text(path)
        title = detect_title(text, path)
        path_owner[path.relative_to(root).as_posix()] = title
        for name in dedupe_preserve_order([title, *frontmatter_list(text, "aliases")]):
            title_owner[name] = title
    for static_name in {"INDEX", "SYSTEM_OVERVIEW", "PAGE_FORMATS", "LINT_AND_HEAL", "README", "LOG"}:
        title_owner[static_name] = static_name
    available_titles = set(title_owner)

    broken_links = []
    inbound_links: Counter[str] = Counter()
    for path in wiki_docs:
        text = read_text(path)
        for link in extract_wiki_links(text):
            if link in available_titles:
                inbound_links[title_owner.get(link, link)] += 1
            if link not in available_titles:
                broken_links.append({"source": path.relative_to(root).as_posix(), "target": link})
        for target_path in extract_internal_markdown_links(text, path, root):
            title = path_owner.get(target_path)
            if title:
                inbound_links[title] += 1

    orphan_pages = []
    for path in wiki_docs:
        title = detect_title(read_text(path), path)
        if path.name in {"INDEX.md", "SYSTEM_OVERVIEW.md", "LOG.md", "LINT_AND_HEAL.md", "README.md"}:
            continue
        if inbound_links.get(title, 0) == 0:
            orphan_pages.append({"title": title, "path": path.relative_to(root).as_posix()})

    concept_state = state.get("concepts", {})
    sparse_concepts = [
        {"title": info["title"], "source_count": info["source_count"]}
        for _, info in sorted(concept_state.items(), key=lambda item: (item[1]["source_count"], item[1]["title"].lower()))
        if info["source_count"] <= 1
    ]

    source_state = state.get("source_docs", {})
    active_source_keys = state.get("active_source_keys") or list(source_state)
    active_profiles = [source_state[key] for key in active_source_keys if key in source_state]
    low_coverage_profiles = [
        profile
        for profile in active_profiles
        if profile.get("concepts") == ["scientific-machine-learning"]
        and not profile.get("domains")
        and not profile.get("themes")
        and not (profile.get("source_kind") == "raw_markdown" and len(profile.get("section_index", [])) <= 3)
    ]
    candidate_terms = [term for term, _ in Counter(term for profile in low_coverage_profiles for term in profile.get("keywords", [])).most_common(8)]

    lines = [
        "---",
        "title: \"Lint + Heal\"",
        "aliases:",
        "  - \"Lint + Heal\"",
        "note_type: \"system\"",
        f"last_compiled: {compile_date}",
        "---",
        "",
        "# Lint + Heal",
        "",
        f"- Last checked: {compile_date}",
        f"- Wiki documents scanned: {len(wiki_docs)}",
        f"- Broken wiki-links: {len(broken_links)}",
        f"- Orphan pages: {len(orphan_pages)}",
        f"- Sparse concepts (<=1 source): {len(sparse_concepts)}",
        f"- Sources needing richer concept coverage: {len(low_coverage_profiles)}",
        "",
        "## Broken wiki-links",
        "",
    ]

    if broken_links:
        lines.extend(f"- `{item['source']}` links to missing wiki target `{item['target']}`." for item in broken_links[:25])
    else:
        lines.append("- No broken wiki-links detected in the current wiki pages.")

    lines.extend(["", "## Orphan Pages", ""])
    if orphan_pages:
        lines.extend(f"- `{item['path']}` has no inbound wiki-links yet." for item in orphan_pages[:25])
    else:
        lines.append("- No orphan pages detected among source pages, concept pages, or derived notes.")

    lines.extend(["", "## Sparse concepts", ""])
    if sparse_concepts:
        lines.extend(f"- `[[{item['title']}]]` is currently backed by {item['source_count']} source file(s)." for item in sparse_concepts[:20])
    else:
        lines.append("- Every concept currently has more than one supporting source.")

    lines.extend(["", "## Sources Needing Better Coverage", ""])
    if low_coverage_profiles:
        lines.extend(
            f"- `{profile['title']}` currently only maps to [[Scientific Machine Learning]]; consider adding a more specific concept tag."
            for profile in sorted(low_coverage_profiles, key=lambda item: item["title"].lower())[:20]
        )
    else:
        lines.append("- All tracked sources currently map to at least one specific concept beyond the fallback bucket.")

    lines.extend(["", "## New Article Candidates", ""])
    if candidate_terms:
        lines.append(f"- Repeated terms from low-coverage sources suggest new concept candidates such as: {', '.join(f'`{term}`' for term in candidate_terms)}.")
    else:
        lines.append("- No obvious new concept candidates emerged from the current low-coverage set.")

    lines.extend([
        "",
        "## Suggested Next Passes",
        "",
        "- Run `wiki_cli.py search <term>` on candidate terms before adding new concepts so the taxonomy stays tight.",
        "- File especially valuable Q&A outputs into `wiki/derived/` so later queries can build on them.",
        "- Re-run the compiler after new raw notes or PDF conversions land so the lint report stays actionable.",
        "",
    ])

    write_text_if_changed(report_path, "\n".join(lines))
    return {
        "report": report_path.relative_to(root).as_posix(),
        "broken_links": len(broken_links),
        "orphan_pages": len(orphan_pages),
        "sparse_concepts": len(sparse_concepts),
        "low_coverage_sources": len(low_coverage_profiles),
        "candidate_terms": candidate_terms,
    }


def compile_wiki(root: Path, force: bool = False) -> dict[str, Any]:
    ensure_project_dirs(root)
    current_date = today_string()
    previous_state = load_state(root)
    source_docs = dict(previous_state.get("source_docs", {}))

    current_sources = source_input_records(root)
    current_rel_paths = {item["source"] for item in current_sources}

    removed_sources = sorted(set(source_docs) - current_rel_paths)
    for rel_path in removed_sources:
        source_docs.pop(rel_path, None)

    changed_sources = []
    for item in current_sources:
        rel_path = item["source"]
        tracked_path = item["content_path"] if item["content_path"].exists() else item["logical_path"]
        digest = file_hash(tracked_path)
        mtime_ns = tracked_path.stat().st_mtime_ns
        cached = source_docs.get(rel_path)
        if not force and cached and cached.get("hash") == digest and cached.get("mtime_ns") == mtime_ns:
            continue
        source_docs[rel_path] = build_source_profile(root, item["logical_path"], item["content_path"], item["source_kind"])
        changed_sources.append(rel_path)

    canonical_docs, duplicate_sources = canonical_source_profiles(source_docs)
    concept_docs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for profile in canonical_docs.values():
        for slug in profile.get("concepts", []):
            if slug in CONCEPTS_BY_SLUG:
                concept_docs[slug].append(profile)

    # Concepts with a curated fragment (wiki/curated/<slug>.md) or `keep_without_sources`
    # in their catalog entry are generated even when no source matches their aliases.
    pinned_concepts = sorted(
        slug for slug in CONCEPTS_BY_SLUG if slug not in concept_docs and concept_is_pinned(root, slug)
    )
    for slug in pinned_concepts:
        concept_docs[slug] = []

    config = load_config(root)
    sources_dir = root / config["source_notes_dir"]
    concepts_dir = root / config["concepts_dir"]
    projects_dir = root / config.get("projects_dir", "wiki/projects")
    sources_dir.mkdir(parents=True, exist_ok=True)
    concepts_dir.mkdir(parents=True, exist_ok=True)
    projects_dir.mkdir(parents=True, exist_ok=True)

    written_source_pages = []
    for profile in sorted(canonical_docs.values(), key=lambda item: item["title"].lower()):
        page_path = root / profile["page"]
        content = source_page_content(profile, current_date)
        if write_text_if_changed(page_path, content):
            written_source_pages.append(page_path.relative_to(root).as_posix())

    existing_source_pages = {path.name for path in sources_dir.glob("*.md")}
    valid_source_pages = {Path(profile["page"]).name for profile in canonical_docs.values()}
    removed_source_pages = []
    for stale_name in sorted(existing_source_pages - valid_source_pages):
        stale_path = sources_dir / stale_name
        stale_path.unlink()
        removed_source_pages.append(stale_path.relative_to(root).as_posix())

    written_articles = []
    available_slugs = set(concept_docs)
    curated_notes = {slug: load_curated_note(root, slug) for slug in concept_docs}
    for concept_slug, docs in sorted(concept_docs.items()):
        article_path = concepts_dir / f"{concept_slug}.md"
        content = concept_article_content(
            concept_slug,
            docs,
            current_date,
            available_slugs,
            curated_note=curated_notes.get(concept_slug),
        )
        if write_text_if_changed(article_path, content):
            written_articles.append(article_path.relative_to(root).as_posix())

    existing_articles = {path.name for path in concepts_dir.glob("*.md")}
    valid_articles = {f"{slug}.md" for slug in concept_docs}
    removed_articles = []
    for stale_name in sorted(existing_articles - valid_articles):
        stale_path = concepts_dir / stale_name
        stale_path.unlink()
        removed_articles.append(stale_path.relative_to(root).as_posix())

    index_content = render_index(root, canonical_docs, concept_docs, current_date)
    index_written = write_text_if_changed(root / config["wiki_dir"] / "INDEX.md", index_content)

    new_state = {
        "compiled_at": timestamp_string(),
        "compile_date": current_date,
        "changed_sources": changed_sources,
        "removed_sources": removed_sources,
        "source_docs": source_docs,
        "active_source_keys": sorted(canonical_docs),
        "duplicate_sources": duplicate_sources,
        "concepts": {
            slug: {
                "title": CONCEPTS_BY_SLUG[slug]["title"],
                "article": f"wiki/concepts/{slug}.md",
                "source_count": len(docs),
                **({"curated_note": curated_notes[slug]["path"]} if curated_notes.get(slug) else {}),
            }
            for slug, docs in sorted(concept_docs.items())
        },
    }
    save_state(root, new_state)
    system_overview_written = write_text_if_changed(root / config["system_overview_path"], render_system_overview(root, current_date, new_state))
    page_formats_written = write_text_if_changed(root / config.get("page_formats_path", "wiki/PAGE_FORMATS.md"), render_page_formats(current_date))
    projects_home_written = write_text_if_changed(projects_dir / "README.md", render_projects_home(root, current_date))
    derived_home_written = write_text_if_changed(root / config["derived_wiki_dir"] / "README.md", render_derived_home(root, current_date))
    log_written = write_text_if_changed(root / config["log_path"], render_log_index(root))
    lint_result = lint_wiki(root, compile_date=current_date, state=new_state)

    return {
        "compile_date": current_date,
        "changed_sources": changed_sources,
        "removed_sources": removed_sources,
        "written_source_pages": written_source_pages,
        "removed_source_pages": removed_source_pages,
        "written_articles": written_articles,
        "removed_articles": removed_articles,
        "pinned_concepts": pinned_concepts,
        "curated_concepts": sorted(slug for slug, note in curated_notes.items() if note),
        "index_written": index_written,
        "log_written": log_written,
        "system_overview_written": system_overview_written,
        "page_formats_written": page_formats_written,
        "projects_home_written": projects_home_written,
        "derived_home_written": derived_home_written,
        "lint": lint_result,
        "source_count": len(current_sources),
        "unique_source_count": len(canonical_docs),
        "duplicate_source_count": len(duplicate_sources),
        "concept_count": len(concept_docs),
    }


def snapshot_raw_tree(root: Path) -> dict[str, int]:
    snapshot = {}
    for source_dir in configured_source_dirs(root):
        if not source_dir.exists():
            continue
        for path in sorted(source_dir.rglob("*")):
            if path.is_file():
                snapshot[path.relative_to(root).as_posix()] = path.stat().st_mtime_ns
    return snapshot


def parse_root_arg(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    return DEFAULT_ROOT


def convert_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    result = convert_sources(parse_root_arg(args.root), force=args.force)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not result["failures"] else 1


def compile_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    root = parse_root_arg(args.root)
    convert_result = convert_sources(root, force=args.force)
    result = compile_wiki(root, force=args.force)
    append_log_entry(
        root,
        "compile",
        "Incremental wiki refresh",
        [
            f"Converted PDF caches: {convert_result['pdf_converted']}",
            f"Converted LaTeX caches: {convert_result['tex_converted']}",
            f"Failed source conversions: {len(convert_result['failures'])}",
            f"Changed sources: {len(result['changed_sources'])}",
            f"Source pages written: {len(result['written_source_pages'])}",
            f"Concept pages written: {len(result['written_articles'])}",
        ],
    )
    payload = {**result, "conversion": convert_result}
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not convert_result["failures"] else 1


def lint_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    args = parser.parse_args(argv)
    root = parse_root_arg(args.root)
    result = lint_wiki(root)
    append_log_entry(
        root,
        "lint",
        "Wiki health check",
        [
            f"Broken links: {result['broken_links']}",
            f"Orphan pages: {result['orphan_pages']}",
            f"Sparse concepts: {result['sparse_concepts']}",
        ],
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def export_html_summary(root: Path) -> dict[str, Any]:
    try:
        from export_html import export_html
    except ModuleNotFoundError:
        import importlib
        import sys

        scripts_dir = (root / "_meta/scripts").resolve().as_posix()
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        export_html = importlib.import_module("export_html").export_html

    result = export_html(root)
    return {
        "entrypoint": result["entrypoint"],
        "search_page": result["search_page"],
        "pages_written": result["pages_written"],
    }


def watch_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    parser.add_argument("--interval", type=int, default=None)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    root = parse_root_arg(args.root)
    config = load_config(root)
    interval = args.interval or int(config.get("watch_interval_seconds", 15))

    last_snapshot = None
    while True:
        snapshot = snapshot_raw_tree(root)
        if args.force or last_snapshot is None or snapshot != last_snapshot:
            convert_result = convert_sources(root, force=args.force)
            compile_result = compile_wiki(root, force=args.force)
            html_export = None
            html_export_error = None
            try:
                html_export = export_html_summary(root)
            except Exception as exc:
                html_export_error = str(exc)
            payload = {
                "timestamp": timestamp_string(),
                "converted": len(convert_result["converted"]),
                "archived": len(convert_result["archived"]),
                "failures": convert_result["failures"],
                "compile": compile_result,
            }
            if html_export is not None:
                payload["html_export"] = html_export
            if html_export_error is not None:
                payload["html_export_error"] = html_export_error
            print(json.dumps(payload, ensure_ascii=False), flush=True)
            last_snapshot = snapshot_raw_tree(root)
            args.force = False
        if args.once:
            return 0
        time.sleep(interval)


if __name__ == "__main__":
    command = Path(sys.argv[0]).stem
    if command == "convert_pdfs":
        raise SystemExit(convert_main())
    if command == "compile_wiki":
        raise SystemExit(compile_main())
    if command == "lint_heal":
        raise SystemExit(lint_main())
    if command == "watch_raw":
        raise SystemExit(watch_main())
    print("Use convert_pdfs.py, compile_wiki.py, lint_heal.py, or watch_raw.py.", file=sys.stderr)
    raise SystemExit(2)
