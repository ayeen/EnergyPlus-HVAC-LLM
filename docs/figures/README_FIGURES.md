# Research Paper Figures

This directory contains all figures for the research paper:
**"Automated HVAC System Design using Multi-Agent Large Language Models with RAG and Fine-Tuning"**

## Figure List

| Figure # | Filename | Description | Section |
|----------|----------|-------------|---------|
| Fig. 1 | `fig1_system_architecture.svg` | Multi-Agent System Architecture | Methodology |
| Fig. 2 | `fig2_agent1_workflow.svg` | Agent 1: VRF Generator Workflow | Methodology |
| Fig. 3 | `fig3_validation_pipeline.svg` | Agent 2: 4-Stage Validation Pipeline | Methodology |
| Fig. 4 | `fig4_agent3_correction.svg` | Agent 3: Iterative Correction Loop | Methodology |
| Fig. 5 | `fig5_rag_architecture.svg` | RAG Knowledge Base Architecture | Methodology |
| Fig. 6 | `fig6_finetuning_approach.svg` | LoRA Fine-Tuning Approach | Methodology |
| Fig. 7 | `fig7_success_rate_comparison.svg` | Success Rate Comparison Bar Chart | Results |
| Fig. 8 | `fig8_scalability_analysis.svg` | Scalability Analysis Line Chart | Results |
| Fig. 9 | `fig9_rag_contribution.svg` | RAG Contribution Analysis | Results |
| Fig. 10 | `fig10_multiagent_synergy.svg` | Multi-Agent Synergy Diagram | Results |

## How to Use

1. Open the HTML file (`all_figures.html`) in a browser
2. Right-click on each figure → "Save Image As" (PNG)
3. Or use browser print to PDF for vector quality
4. For SVG: Copy the SVG code directly into your LaTeX/Word document

## Recommended Export Settings

- **Resolution:** 300 DPI minimum for print
- **Format:** SVG (vector) or PNG (raster)
- **Color Mode:** CMYK for print journals, RGB for online

## Figure Captions (for paper)

### Figure 1
**Caption:** Multi-agent system architecture for automated HVAC generation. The pipeline consists of three specialized agents: Agent 1 (VRF Generator), Agent 2 (Validation Orchestrator), and Agent 3 (Iterative Debugger), working collaboratively to transform natural language requests into simulation-ready EnergyPlus configurations.

### Figure 2
**Caption:** Agent 1 workflow showing the iterative generation strategy. The fine-tuned Mistral-7B model generates HVACTemplate objects in sequence: System:VRF (42 fields), Zone:VRF (per zone), and Thermostats, with RAG-enhanced prompts providing domain-specific knowledge.

### Figure 3
**Caption:** Four-stage validation pipeline in Agent 2. Each stage performs specific validation: IDD compliance checking, Eppy-based syntax validation, HVACTemplate expansion via ExpandObjects, and full EnergyPlus simulation with error parsing.

### Figure 4
**Caption:** Agent 3 iterative correction workflow. Upon receiving simulation errors, Agent 3 queries the RAG knowledge base for similar error patterns, generates targeted JSON fix specifications, and applies corrections. The maximum 3-iteration limit ensures bounded execution time.

### Figure 5
**Caption:** RAG knowledge base architecture using ChromaDB vector database. The knowledge base contains 718+ documents organized into specialized collections: field specifications, error patterns, design rules, field dependencies, and fix procedures.

### Figure 6
**Caption:** LoRA (Low-Rank Adaptation) fine-tuning approach. Only ~0.1% of model parameters are updated through low-rank adapter matrices, enabling efficient training on domain-specific data while preserving the base model's general capabilities.

### Figure 7
**Caption:** Success rate comparison between fine-tuned Mistral-7B and pre-trained models. Fine-tuned achieves 80% first-try and 100% final success, compared to 20% and 0% for pre-trained models with and without in-context examples, respectively.

### Figure 8
**Caption:** Scalability analysis showing output quality vs. zone count. Fine-tuned models maintain consistent 100% quality across all scales (1-20 zones), while pre-trained models degrade progressively, failing completely at 20 zones (breaking point).

### Figure 9
**Caption:** RAG contribution analysis through ablation study. RAG provides +15% improvement for fine-tuned models but cannot rescue pre-trained models, demonstrating that RAG enhances but cannot replace domain-specific fine-tuning.

### Figure 10
**Caption:** Multi-agent synergy effect. The combination of Agent 1 (80% first-try success) and Agent 3 (100% correction success) achieves 100% final success rate, demonstrating the robustness of the generate-validate-correct paradigm.
