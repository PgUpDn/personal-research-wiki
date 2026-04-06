#!/usr/bin/env python3

from __future__ import annotations

import argparse
import base64
import hashlib
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
VENV_SITE_PACKAGES = PROJECT_ROOT / ".venv/lib/python3.9/site-packages"
if VENV_SITE_PACKAGES.exists():
    sys.path.insert(0, str(VENV_SITE_PACKAGES))

import fitz
import anthropic


DEFAULT_ROOT = PROJECT_ROOT
CONFIG_PATH = Path("_meta/config.json")
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
    "through",
    "towards",
    "using",
    "with",
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
        "aliases": ["accelerating scientific simulations", "accelerating", "fast approximate solver", "simulation acceleration"],
        "related": ["surrogate-models", "neural-operators", "scientific-machine-learning"],
    },
    {
        "slug": "graph-neural-networks",
        "title": "Graph Neural Networks",
        "group": "Model Families",
        "description": "message-passing models used to represent meshes, particles, and relational scientific systems with irregular connectivity",
        "aliases": ["graph neural network", "graph neural networks", "gnn", "gnns", "message passing"],
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
        "aliases": ["large language model", "large language models", "llm", "llms", "chatgpt", "deepseek", "claude"],
        "related": ["ai-agents", "multi-agent-systems", "foundation-models"],
    },
    {
        "slug": "ai-agents",
        "title": "AI Agents",
        "group": "Agents and Reasoning",
        "description": "autonomous or semi-autonomous systems that use tools, memory, or planning loops to execute scientific tasks end to end",
        "aliases": ["ai agent", "ai agents", "agentic", "autonomous", "autonomous visualization agent", "research assistants"],
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
        "aliases": ["geometry aware", "geometry-aware", "irregular domains", "general geometries", "shape representations", "surfaces"],
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
        "aliases": ["materials design", "materials", "alloy", "material fracture", "polycrystalline", "microstructure"],
        "related": ["autonomous-experimentation", "generative-models", "foundation-models"],
    },
    {
        "slug": "semiconductor-design",
        "title": "Semiconductor Design",
        "group": "Application Domains",
        "description": "chip, TCAD, packaging, and placement workflows where domain-adapted models and surrogates are used to guide design decisions",
        "aliases": ["semiconductor", "chip", "tcad", "placement", "integrated circuits", "electronic packaging"],
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
        "aliases": ["digital twin", "digital twins"],
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
        "slug": "cad-and-geometry-models",
        "title": "CAD and Geometry Models",
        "group": "Data and Evaluation",
        "description": "geometry-centric representations and datasets that connect visual or CAD interfaces to downstream simulation-ready assets",
        "aliases": ["cad", "geometry model", "large geometry model", "3d assets", "simulation-ready 3d assets"],
        "related": ["geometry-aware-learning", "inverse-design", "generative-models"],
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
    "geometry and irregular domains": ["geometry", "mesh", "surface", "irregular", "shape"],
    "inverse design and optimization": ["inverse design", "optimization", "design", "generative"],
    "scaling and transfer": ["scaling", "transfer", "pretraining", "foundation", "domain-adapted"],
    "physics-guided learning": ["physics informed", "physics-guided", "differentiable", "residual", "equilibrium"],
}

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")


def load_config(root: Path) -> dict[str, Any]:
    config_file = root / CONFIG_PATH
    if config_file.exists():
        return json.loads(config_file.read_text(encoding="utf-8"))
    return {
        "project_root": ".",
        "raw_dir": "raw",
        "wiki_dir": "wiki",
        "concepts_dir": "wiki/concepts",
        "source_notes_dir": "wiki/sources",
        "derived_wiki_dir": "wiki/derived",
        "output_dir": "output",
        "html_dir": "output/html",
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
        "venv_site_packages": ".venv/lib/python3.9/site-packages",
        "node_bin": "node",
        "pdf2md_entrypoint": "_meta/node_tools/pdf2md/node_modules/pdf2md/bin/index.js",
        "pdf2md_workspace_dir": "_meta/pdf2md_work",
        "raw_images_dir": "raw/images",
        "claude_api_env": "ANTHROPIC_API_KEY",
        "claude_api_key_file": "",
        "claude_api_base": "https://api.anthropic.com/v1/messages",
        "claude_model": "claude-sonnet-4-6",
        "qa_model": "claude-sonnet-4-6",
        "claude_max_tokens": 3500,
        "claude_page_batch_size": 8,
        "qa_max_tokens": 3000,
        "qa_context_char_limit": 180000,
        "qa_top_concepts": 14,
    }


def ensure_project_dirs(root: Path) -> None:
    config = load_config(root)
    for key in (
        "wiki_dir",
        "concepts_dir",
        "source_notes_dir",
        "derived_wiki_dir",
        "output_dir",
        "html_dir",
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


def dedupe_preserve_order(values: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def converted_pdf_markdown_path(root: Path, pdf_path: Path) -> Path:
    config = load_config(root)
    raw_dir = root / config["raw_dir"]
    return (root / config["converted_sources_dir"] / pdf_path.relative_to(raw_dir)).with_suffix(".md")


def source_note_page_path(root: Path, source_rel: str, title: str) -> Path:
    config = load_config(root)
    stem = slugify(title)[:72] or slugify(Path(source_rel).stem)[:72] or "source"
    return root / config["source_notes_dir"] / f"{stem}-{short_hash(source_rel)}.md"


def raw_markdown_files(root: Path) -> list[Path]:
    raw_dir = root / load_config(root)["raw_dir"]
    return sorted(path for path in raw_dir.rglob("*.md") if path.is_file())


def raw_pdf_files(root: Path) -> list[Path]:
    raw_dir = root / load_config(root)["raw_dir"]
    return sorted(path for path in raw_dir.rglob("*.pdf") if path.is_file())


def source_input_records(root: Path) -> list[dict[str, Any]]:
    records = []
    for path in raw_markdown_files(root):
        records.append(
            {
                "source": path.relative_to(root).as_posix(),
                "logical_path": path,
                "content_path": path,
                "source_kind": "raw_markdown",
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

    return sorted(records, key=lambda item: item["source"].lower())


def paper_title_from_name(name: str) -> str:
    stem = Path(name).stem
    parts = [part.strip() for part in stem.split(" - ") if part.strip()]
    if len(parts) >= 3 and re.fullmatch(r"\d{4}", parts[1]):
        return " - ".join(parts[2:]).strip()
    if len(parts) >= 2:
        return " - ".join(parts[1:]).strip()
    return stem.strip()


def clean_markdown_candidate(text: str) -> str:
    return text.strip().lstrip("#").strip().strip("*").strip()


def title_token_set(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", normalize_text(text).lower()) if len(token) >= 3}


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
    if any(hint in lowered for hint in AFFILIATION_HINTS | ORGANIZATION_HINTS | ADDRESS_HINTS):
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
    if not re.search(r"[a-z]", candidate):
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
    line = raw_line.strip().strip("*").strip()
    if not line or is_affiliation_or_metadata_line(line):
        return []
    separated = re.sub(r"([A-Za-z])(?:\^\{[^}]*\}|[$]?\^\d+|[¹²³⁴⁵⁶⁷⁸⁹⁰†‡✉*]+)", r"\1, ", line)
    separated = separated.replace(" · ", ", ").replace("•", ",").replace(";", ",")
    separated = separated.replace(" and ", ", ")
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


def normalize_author_token(token: str) -> str:
    cleaned = re.sub(r"\$[^$]*\$", "", token)
    cleaned = re.sub(r"\^\{[^}]*\}", "", cleaned)
    cleaned = re.sub(r"\^\d+", "", cleaned)
    cleaned = re.sub(r"[*†‡§¶#0-9]+", " ", cleaned)
    cleaned = re.sub(r"\([^)]*\)", " ", cleaned)
    cleaned = cleaned.translate(SUPERSCRIPT_TRANSLATION)
    cleaned = normalize_text(cleaned.replace("et al.", "").replace("et al", ""))
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


def extract_authors(markdown_text: str, title: str, source_path: Path) -> list[str]:
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
    if title_index is not None:
        for raw in lines[title_index + 1:title_index + 25]:
            stripped = clean_markdown_candidate(raw)
            lowered = normalize_text(stripped).lower().strip(":")
            if not stripped:
                continue
            if lowered in {"abstract", "article info"} or lowered.startswith(("abstract", "keywords", "introduction")):
                break
            if stripped.startswith("#"):
                break
            if is_affiliation_or_metadata_line(stripped):
                continue
            authors.extend(split_author_line(stripped))
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


def detect_title(markdown_text: str, source_path: Path) -> str:
    frontmatter_match = re.search(r"^title:\s*(.+)$", markdown_text, re.MULTILINE)
    frontmatter_title = frontmatter_match.group(1).strip().strip('"') if frontmatter_match else ""
    title_hint = paper_title_from_name(source_path.name)
    if frontmatter_title:
        return frontmatter_title
    body = extracted_markdown_body(markdown_text)
    for raw in body.splitlines()[:40]:
        heading_match = re.match(r"^\s*#{1,2}\s+(.+?)\s*$", raw)
        if not heading_match:
            continue
        heading = clean_markdown_candidate(heading_match.group(1))
        if heading and len(heading) >= 4:
            return heading
    body_lines = [line.strip() for line in body.splitlines()]
    candidate_lines = []
    for raw in body_lines[:80]:
        cleaned = clean_markdown_candidate(raw)
        lowered = normalize_text(cleaned).lower()
        if not cleaned or re.fullmatch(r"Pages? \d+(?:-\d+)?", cleaned, re.IGNORECASE):
            continue
        if any(hint in lowered for hint in {"manuscript", "inserted by the editor", "journal homepage", "check for updates"}):
            continue
        if len(cleaned) < 12 or len(cleaned) > 220:
            continue
        if re.search(r"[.!?]$", cleaned):
            continue
        if is_affiliation_or_metadata_line(cleaned):
            continue
        candidate_lines.append(cleaned)
    candidate_lines = combined_title_candidates(candidate_lines)
    if title_hint:
        ranked = [
            (title_similarity(candidate, title_hint), index, candidate)
            for index, candidate in enumerate(candidate_lines)
        ]
        ranked = [item for item in ranked if item[0] >= 0.55]
        if ranked:
            ranked.sort(key=lambda item: (-item[0], item[1], -len(item[2])))
            return ranked[0][2]
        if source_path.suffix.lower() == ".pdf":
            return title_hint
    for candidate in candidate_lines:
        if len(candidate.split()) >= 4 and not looks_like_person_name(candidate):
            return candidate
    return title_hint or frontmatter_title


def extract_abstract(markdown_text: str) -> str:
    body = extracted_markdown_body(markdown_text)
    compact = body.replace("\r\n", "\n")
    abstract_match = re.search(
        r"(?is)\babstract\b[:\s]*\n?(.*?)(?:\n\s*#|\n\s*##|\n\s*\d+\s+introduction\b|\n\s*introduction\b)",
        compact,
    )
    if abstract_match:
        snippet = normalize_text(abstract_match.group(1))
        if snippet:
            return snippet[:1600]
    frontmatter_match = re.search(r"^title:\s*(.+)$", markdown_text, re.MULTILINE)
    title = frontmatter_match.group(1).strip().strip('"') if frontmatter_match else ""
    title_norm = normalize_text(title).lower()
    seen_title = False
    without_headings = []
    lines = compact.splitlines()
    skip_next = False
    for index, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
        stripped = line.strip()
        if not stripped:
            if without_headings:
                break
            continue
        cleaned = normalize_text(clean_markdown_candidate(stripped)).lower()
        combined = cleaned
        if index + 1 < len(lines):
            next_cleaned = normalize_text(clean_markdown_candidate(lines[index + 1].strip())).lower()
            combined = f"{cleaned} {next_cleaned}".strip()
        if cleaned == title_norm or (title and title_similarity(clean_markdown_candidate(stripped), title) >= 0.75):
            seen_title = True
            continue
        if title and index + 1 < len(lines) and title_similarity(combined, title) >= 0.75:
            seen_title = True
            skip_next = True
            continue
        if not seen_title and title:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("> Converted from") or stripped.startswith("> Working markdown cache"):
            continue
        if split_author_line(stripped):
            continue
        if is_affiliation_or_metadata_line(stripped) or looks_like_person_name(stripped):
            continue
        lowered = normalize_text(stripped).lower().strip(":")
        if lowered in GENERIC_HEADER_LINES or lowered.startswith("keywords"):
            continue
        if stripped.count("|") >= 2:
            break
        without_headings.append(stripped)
        if len(" ".join(without_headings)) > 1800:
            break
    return normalize_text(" ".join(without_headings))[:1600]


def extracted_markdown_body(markdown_text: str) -> str:
    body = strip_frontmatter(markdown_text)
    if "\n## Extracted Markdown\n" in body:
        return body.split("\n## Extracted Markdown\n", 1)[1].strip()
    return body.strip()


def clean_identifier(value: str) -> str:
    return value.rstrip(".,);]}>\"'")


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


def matched_concepts(text: str) -> list[str]:
    normalized = normalize_for_match(text)
    found = []
    for concept in CONCEPTS:
        if any(matches_alias(normalized, alias) for alias in concept["aliases"]):
            found.append(concept["slug"])
    return sorted(set(found))


def classify_labels(text: str, patterns: dict[str, list[str]]) -> list[str]:
    normalized = normalize_for_match(text)
    labels = []
    for label, aliases in patterns.items():
        if any(matches_alias(normalized, alias) for alias in aliases):
            labels.append(label)
    return labels


def load_claude_api_key(root: Path) -> str:
    config = load_config(root)
    env_name = config["claude_api_env"]
    env_value = os.environ.get(env_name, "").strip()
    if env_value:
        return env_value

    key_file_value = str(config.get("claude_api_key_file", "")).strip()
    key_file = Path(key_file_value).expanduser() if key_file_value else None
    if key_file and key_file.is_file():
        raw = key_file.read_text(encoding="utf-8", errors="ignore").strip()
        if "=" in raw and not raw.startswith("sk-ant-"):
            raw = raw.split("=", 1)[1].strip().strip("'\"")
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
    document = fitz.open(pdf_path)
    try:
        matrix = fitz.Matrix(2.0, 2.0)
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
    with fitz.open(pdf_path) as document:
        last_page = min(page_end, document.page_count)
        for page_number in range(page_start, last_page + 1):
            text = document.load_page(page_number - 1).get_text("text").strip()
            if not text:
                continue
            cleaned = re.sub(r"\n{3,}", "\n\n", text)
            snippets.append(f"### Page {page_number}\n\n{cleaned}")
    return "\n\n".join(snippets).strip()


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
                text = "\n\n".join(text_blocks)
                break
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
    render_pipeline: str,
) -> str:
    title = detect_title(extracted_text, pdf_path)
    body = extracted_text or "Claude Vision did not return readable text for this PDF."
    transcription_mode = cache_transcription_mode(extracted_text)
    year = source_filename_parts(pdf_path).get("year")
    authors = extract_authors(extracted_text, title, pdf_path)
    doi = extract_doi(extracted_text)
    arxiv_id = extract_arxiv_id(extracted_text)
    venue = extract_venue(extracted_text, doi=doi, arxiv_id=arxiv_id)
    source_id = derive_citation_key(title, pdf_path, authors, year)
    page_count = len(relative_image_paths)
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
    lines.extend(
        [
        f"page_count: {page_count}",
        f"page_image_dir: {json.dumps(image_dir, ensure_ascii=False)}",
        f"converted_at: {today_string()}",
        f"conversion_pipeline: {json.dumps(f'{render_pipeline}+claude-vision', ensure_ascii=False)}",
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
        f"- Pipeline: `{render_pipeline}+claude-vision`",
        f"- Page count: `{page_count}`",
        f"- Page image directory: `{image_dir or '_meta/source_page_images/'}`",
        "",
    ]
    )
    if venue or doi or arxiv_id:
        lines.extend(["## Bibliographic Signals", ""])
        if venue:
            lines.append(f"- Venue: {venue}")
        if doi:
            lines.append(f"- DOI: `{doi}`")
        if arxiv_id:
            lines.append(f"- arXiv: `{arxiv_id}`")
        lines.append("")
    if relative_image_paths:
        lines.extend(["## Preview", "", f"![{Path(relative_image_paths[0]).name}]({relative_image_paths[0]})", ""])
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
    relative_image_paths = existing_relative_page_images(root, pdf_path, md_path)
    conversion_pipeline = (frontmatter_scalar(existing, "conversion_pipeline") or "pdf2md+claude-vision").split("+", 1)[0]
    markdown = markdown_from_pdf(pdf_path, pdf_path.relative_to(root).as_posix(), extracted, relative_image_paths, conversion_pipeline)
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
            try:
                image_paths, work_dir, render_pipeline = render_pdf_pages(root, pdf_path)
                extracted = claude_markdown_from_images(root, pdf_path, image_paths)
                relative_image_paths = copy_page_images(root, pdf_path, image_paths, md_path)
                markdown = markdown_from_pdf(pdf_path, rel_pdf, extracted, relative_image_paths, render_pipeline)
                changed = write_text_if_changed(md_path, markdown)
                converted.append({"source_pdf": rel_pdf, "cache_markdown": md_path.relative_to(root).as_posix(), "written": changed})
                shutil.rmtree(work_dir, ignore_errors=True)
            except Exception as exc:
                failures.append({"source_pdf": rel_pdf, "error": str(exc)})
                continue

    return {"converted": converted, "archived": [], "failures": failures}


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
    title = detect_title(text, logical_path)
    abstract = extract_abstract(text)
    doi = extract_doi(text)
    arxiv_id = extract_arxiv_id(text)
    venue = extract_venue(text, doi=doi, arxiv_id=arxiv_id)
    transcription_mode = cache_transcription_mode(text) if source_kind == "raw_pdf" else "raw_markdown"
    combined = f"{title}\n\n{abstract}"
    if transcription_mode == "vision":
        combined = f"{combined}\n\n{text[:10000]}"
    concepts = matched_concepts(combined)
    if not concepts:
        concepts = ["scientific-machine-learning"]
    source_rel = logical_path.relative_to(root).as_posix()
    content_rel = content_path.relative_to(root).as_posix()
    summary = trim_summary(abstract or strip_frontmatter(text)[:500])
    filename_bits = source_filename_parts(logical_path)
    authors = extract_authors(text, title, logical_path)
    year = filename_bits.get("year")
    citation_key = derive_citation_key(title, logical_path, authors, year)
    short_title = canonical_alias(title)
    page_count = page_count_for_pdf(root, logical_path) if source_kind == "raw_pdf" else None
    image_dir = page_image_directory_rel(root, logical_path) if source_kind == "raw_pdf" else None
    section_index = extract_section_headings(text, logical_path)
    aliases = dedupe_preserve_order([alias for alias in [short_title, citation_key] if alias and alias != title])
    tags = ["research/source", f"source/{source_kind.replace('_', '-')}"]
    if source_kind == "raw_pdf":
        tags.append(f"transcription/{transcription_mode.replace('_', '-')}")
    return {
        "source": source_rel,
        "source_files": [source_rel],
        "content_path": content_rel,
        "source_kind": source_kind,
        "source_status": "compiled",
        "transcription_mode": transcription_mode,
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
        "page_count": page_count,
        "page_image_dir": image_dir,
        "section_index": section_index,
        "tags": tags,
        "hash": file_hash(logical_path),
        "mtime_ns": logical_path.stat().st_mtime_ns,
        "abstract": abstract,
        "summary": summary,
        "concepts": concepts,
        "keywords": top_terms(f"{title} {abstract}"),
        "domains": classify_labels(combined, DOMAIN_PATTERNS),
        "themes": classify_labels(combined, THEME_PATTERNS),
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
    return f"[[{title}]]"


def render_yaml_list(key: str, values: list[str]) -> list[str]:
    if not values:
        return [f"{key}: []"]
    lines = [f"{key}:"]
    for value in values:
        lines.append(f"  - {json.dumps(value, ensure_ascii=False)}")
    return lines


def concept_article_content(concept_slug: str, docs: list[dict[str, Any]], compile_date: str, available_slugs: set[str]) -> str:
    concept = CONCEPTS_BY_SLUG[concept_slug]
    docs_sorted = sorted(docs, key=lambda item: item["title"].lower())
    source_paths = [doc["source"] for doc in docs_sorted]
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

    intro_bits = [f"[[{concept['title']}]] appears across `raw/` as {concept['description']}."]
    if top_domains:
        intro_bits.append(f"The strongest source cluster is in {', '.join(top_domains)}.")
    if related_links:
        intro_bits.append(f"It is most often discussed alongside {', '.join(related_links[:3])}.")

    takeaways = [
        f"The matched sources frame {concept['title']} through {', '.join(top_themes) if top_themes else 'recurring modeling and evaluation concerns'}.",
        f"Representative application areas include {', '.join(top_domains) if top_domains else 'multiple scientific domains'}.",
        f"Recurring vocabulary around this concept includes {', '.join(top_keywords[:5]) if top_keywords else 'simulation, modeling, and design'}.",
    ]

    representative = [f"- [[{doc['title']}]] from `{doc['source']}`" for doc in docs_sorted[:8]]
    related_section = [f"- {link}" for link in related_links] if related_links else ["- No related concept links yet."]

    lines = [
        "---",
        f"title: {json.dumps(concept['title'], ensure_ascii=False)}",
        *render_yaml_list("aliases", concept_aliases),
        "note_type: \"concept\"",
        f"schema_version: {json.dumps(SCHEMA_VERSION)}",
        f"concept_group: {json.dumps(concept['group'], ensure_ascii=False)}",
        f"source_count: {len(docs_sorted)}",
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
            f"- Source ID: `{profile['source_id']}`",
            f"- Citation key: `{profile['citation_key']}`",
            f"- Source kind: `{profile['source_kind']}`",
            f"- Status: `{profile['source_status']}`",
            f"- Raw source: `{profile['source']}`",
        ]
    )
    if profile.get("content_path") and profile["content_path"] != profile["source"]:
        lines.append(f"- Working text cache: `{profile['content_path']}`")
    if profile.get("page_image_dir"):
        lines.append(f"- Page image directory: `{profile['page_image_dir']}`")
    if profile.get("page_count"):
        lines.append(f"- Page count: `{profile['page_count']}`")
    if profile.get("year"):
        lines.append(f"- Year: `{profile['year']}`")
    if profile.get("venue"):
        lines.append(f"- Venue: {profile['venue']}")
    if profile.get("doi"):
        lines.append(f"- DOI: `{profile['doi']}`")
    if profile.get("arxiv_id"):
        lines.append(f"- arXiv: `{profile['arxiv_id']}`")
    if profile.get("lead_author"):
        lines.append(f"- Lead author: {profile['lead_author']}")
    if profile.get("authors"):
        lines.append(f"- Authors: {'; '.join(profile['authors'])}")
    lines.extend(["", "## TL;DR", "", profile.get("summary") or "No summary yet.", ""])
    lines.extend(["## Abstract", "", profile.get("abstract") or "No concise abstract was extracted from this source yet.", ""])
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
    derived_dir = root / config["derived_wiki_dir"]
    derived_notes = []
    for path in sorted(derived_dir.glob("*.md")):
        if not path.is_file():
            continue
        derived_notes.append(
            {
                "path": path.relative_to(root).as_posix(),
                "title": detect_title(read_text(path), path),
                "summary": note_blurb(read_text(path)),
            }
        )

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
        "- Filed-back notes: [derived/README](derived/README.md)",
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
        "| [derived/README](derived/README.md) | How query outputs get filed back into the wiki |",
        "",
        "## Source Pages",
        "",
        "| Source | Summary | Concepts |",
        "| --- | --- | --- |",
    ]

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
    lines.extend(["", "## Working Convention", "", "- Read the index first, then drill into source pages, concept pages, and derived notes as needed.", "- See [[Page Formats]] when adjusting generated note layouts or metadata conventions.", ""])

    return "\n".join(lines).rstrip() + "\n"


def render_derived_home(compile_date: str) -> str:
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
        "- `sources`",
        "- `source_pages`",
        "- `related`",
        "- `tags`",
        "- `last_compiled`",
        "",
        "Sections:",
        "- `## Definition`",
        "- `## What The Sources Emphasize`",
        "- `## Coverage`",
        "- `## Related Concepts`",
        "- `## Representative sources`",
        "- `## Provenance`",
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
        f"- Raw sources represented in the wiki: {len(state.get('source_docs', {}))}",
        f"- Source pages: {len(state.get('source_docs', {}))}",
        f"- Concept articles: {len(state.get('concepts', {}))}",
        "",
        "## Main Pipeline",
        "",
        "1. `raw/` stores source material as-is. It is the immutable source-of-truth layer.",
        "2. PDF transcription caches and rendered page images live under `_meta/`, not in `raw/`, so the compiler can process sources without mutating them.",
        "3. The compiler incrementally refreshes `wiki/sources/*.md`, `wiki/concepts/*.md`, `wiki/INDEX.md`, and `wiki/LOG.md`.",
        "4. The Q&A layer reads the maintained wiki, renders answers into markdown, Marp slides, or other output files, and can file valuable outputs back into `wiki/derived/`.",
        "",
        "## Three Layers",
        "",
        "- `raw/`: immutable source documents, web clips, datasets, and local assets.",
        "- `wiki/`: LLM-maintained markdown pages including source pages, concept pages, indexes, logs, and filed-back notes.",
        "- `AGENTS.md`: the in-repo schema that tells the LLM how to ingest, query, and maintain this workspace.",
        "- `wiki/PAGE_FORMATS.md`: the canonical frontmatter and section layouts for generated cache, source, and concept notes.",
        "- `wiki/PAPER_TEMPLATE.md`: the rationale and recommended structure for PDF-derived literature notes.",
        "",
        "## Support Layer",
        "",
        f"- Open `{root}` directly in Obsidian to browse `raw/`, `wiki/`, `_meta/`, and `output/` from one vault.",
        "- `LINT_AND_HEAL.md` tracks broken links, orphan pages, sparse concepts, low-coverage sources, and suggested cleanup passes.",
        "- `_meta/scripts/wiki_cli.py` is the unified CLI for compile, watch, search, ask, lint, and filing outputs back into the wiki.",
        "",
        "## Directory Map",
        "",
        "| Path | Purpose |",
        "| --- | --- |",
        f"| `{config['raw_dir']}/` | immutable source documents and user-managed local assets |",
        f"| `{config['wiki_dir']}/sources/` | one wiki page per source document, maintained by the compiler |",
        f"| `{config['wiki_dir']}/concepts/` | synthesized concept pages built across many sources |",
        f"| `{config['wiki_dir']}/derived/` | valuable outputs filed back into the knowledge base |",
        f"| `{config['output_dir']}/` | generated answers, slide decks, charts, and reports |",
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


def lint_wiki(root: Path, compile_date: str | None = None, state: dict[str, Any] | None = None) -> dict[str, Any]:
    ensure_project_dirs(root)
    config = load_config(root)
    compile_date = compile_date or today_string()
    state = state or load_state(root)

    wiki_dir = root / config["wiki_dir"]
    concepts_dir = root / config["concepts_dir"]
    sources_dir = root / config["source_notes_dir"]
    derived_dir = root / config["derived_wiki_dir"]
    report_path = root / config["lint_report_path"]

    core_docs = [path for path in [wiki_dir / "INDEX.md", wiki_dir / "SYSTEM_OVERVIEW.md", wiki_dir / "PAGE_FORMATS.md", wiki_dir / "LOG.md"] if path.exists()]
    wiki_docs = sorted(path for path in core_docs + list(concepts_dir.glob("*.md")) + list(sources_dir.glob("*.md")) + list(derived_dir.glob("*.md")) if path.is_file())
    available_titles = {CONCEPTS_BY_SLUG[path.stem]["title"] for path in concepts_dir.glob("*.md") if path.stem in CONCEPTS_BY_SLUG}
    for path in wiki_dir.glob("*.md"):
        available_titles.add(detect_title(read_text(path), path))
        available_titles.update(frontmatter_list(read_text(path), "aliases"))
    for path in sources_dir.glob("*.md"):
        available_titles.add(detect_title(read_text(path), path))
        available_titles.update(frontmatter_list(read_text(path), "aliases"))
    for path in derived_dir.glob("*.md"):
        available_titles.add(detect_title(read_text(path), path))
        available_titles.update(frontmatter_list(read_text(path), "aliases"))
    available_titles.update({"INDEX", "SYSTEM_OVERVIEW", "PAGE_FORMATS", "LINT_AND_HEAL", "README", "LOG"})

    broken_links = []
    inbound_links: Counter[str] = Counter()
    for path in wiki_docs:
        for link in extract_wiki_links(read_text(path)):
            if link in available_titles:
                inbound_links[link] += 1
            if link not in available_titles:
                broken_links.append({"source": path.relative_to(root).as_posix(), "target": link})

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

    low_coverage_profiles = [
        profile
        for profile in state.get("source_docs", {}).values()
        if profile.get("concepts") == ["scientific-machine-learning"]
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
        digest = file_hash(item["logical_path"])
        mtime_ns = item["logical_path"].stat().st_mtime_ns
        cached = source_docs.get(rel_path)
        if not force and cached and cached.get("hash") == digest and cached.get("mtime_ns") == mtime_ns:
            continue
        source_docs[rel_path] = build_source_profile(root, item["logical_path"], item["content_path"], item["source_kind"])
        changed_sources.append(rel_path)

    concept_docs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for profile in source_docs.values():
        for slug in profile.get("concepts", []):
            if slug in CONCEPTS_BY_SLUG:
                concept_docs[slug].append(profile)

    config = load_config(root)
    sources_dir = root / config["source_notes_dir"]
    concepts_dir = root / config["concepts_dir"]
    sources_dir.mkdir(parents=True, exist_ok=True)
    concepts_dir.mkdir(parents=True, exist_ok=True)

    written_source_pages = []
    for profile in sorted(source_docs.values(), key=lambda item: item["title"].lower()):
        page_path = root / profile["page"]
        content = source_page_content(profile, current_date)
        if write_text_if_changed(page_path, content):
            written_source_pages.append(page_path.relative_to(root).as_posix())

    existing_source_pages = {path.name for path in sources_dir.glob("*.md")}
    valid_source_pages = {Path(profile["page"]).name for profile in source_docs.values()}
    removed_source_pages = []
    for stale_name in sorted(existing_source_pages - valid_source_pages):
        stale_path = sources_dir / stale_name
        stale_path.unlink()
        removed_source_pages.append(stale_path.relative_to(root).as_posix())

    written_articles = []
    available_slugs = set(concept_docs)
    for concept_slug, docs in sorted(concept_docs.items()):
        article_path = concepts_dir / f"{concept_slug}.md"
        content = concept_article_content(concept_slug, docs, current_date, available_slugs)
        if write_text_if_changed(article_path, content):
            written_articles.append(article_path.relative_to(root).as_posix())

    existing_articles = {path.name for path in concepts_dir.glob("*.md")}
    valid_articles = {f"{slug}.md" for slug in concept_docs}
    removed_articles = []
    for stale_name in sorted(existing_articles - valid_articles):
        stale_path = concepts_dir / stale_name
        stale_path.unlink()
        removed_articles.append(stale_path.relative_to(root).as_posix())

    index_content = render_index(root, source_docs, concept_docs, current_date)
    index_written = write_text_if_changed(root / config["wiki_dir"] / "INDEX.md", index_content)

    new_state = {
        "compiled_at": timestamp_string(),
        "compile_date": current_date,
        "changed_sources": changed_sources,
        "removed_sources": removed_sources,
        "source_docs": source_docs,
        "concepts": {
            slug: {
                "title": CONCEPTS_BY_SLUG[slug]["title"],
                "article": f"wiki/concepts/{slug}.md",
                "source_count": len(docs),
            }
            for slug, docs in sorted(concept_docs.items())
        },
    }
    save_state(root, new_state)
    system_overview_written = write_text_if_changed(root / config["system_overview_path"], render_system_overview(root, current_date, new_state))
    page_formats_written = write_text_if_changed(root / config.get("page_formats_path", "wiki/PAGE_FORMATS.md"), render_page_formats(current_date))
    derived_home_written = write_text_if_changed(root / config["derived_wiki_dir"] / "README.md", render_derived_home(current_date))
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
        "index_written": index_written,
        "log_written": log_written,
        "system_overview_written": system_overview_written,
        "page_formats_written": page_formats_written,
        "derived_home_written": derived_home_written,
        "lint": lint_result,
        "source_count": len(current_sources),
        "concept_count": len(concept_docs),
    }


def snapshot_raw_tree(root: Path) -> dict[str, int]:
    raw_dir = root / load_config(root)["raw_dir"]
    snapshot = {}
    if not raw_dir.exists():
        return snapshot
    for path in sorted(raw_dir.rglob("*")):
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
    result = convert_pdfs(parse_root_arg(args.root), force=args.force)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not result["failures"] else 1


def compile_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    root = parse_root_arg(args.root)
    convert_result = convert_pdfs(root, force=args.force)
    result = compile_wiki(root, force=args.force)
    append_log_entry(
        root,
        "compile",
        "Incremental wiki refresh",
        [
            f"Converted PDF caches: {len(convert_result['converted'])}",
            f"Failed PDF conversions: {len(convert_result['failures'])}",
            f"Changed sources: {len(result['changed_sources'])}",
            f"Source pages written: {len(result['written_source_pages'])}",
            f"Concept pages written: {len(result['written_articles'])}",
        ],
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


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
            convert_result = convert_pdfs(root, force=args.force)
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
