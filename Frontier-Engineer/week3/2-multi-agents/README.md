# Week 4 — Agentic AI & Multi-Agent Systems: Notebook Series

Six self-contained Jupyter notebooks covering every subtopic in Week 4 of the Frontier Engineering
programme (Sections 3.1–3.6). Each notebook runs **fully offline** — no API keys or extra packages
required — using small, dependency-free simulations that mirror the exact control-flow of real
LangChain / AutoGen / CrewAI / MCP systems. Real API/library usage is shown in commented code blocks
so you can swap in live credentials later.

## Contents

| # | Notebook | Programme Section | Covers |
|---|---|---|---|
| 1 | `01_fundamentals_of_agentic_ai.ipynb` | 3.1 | Traditional vs. agentic AI, the Brain + Hands analogy, a from-scratch ReAct loop |
| 2 | `02_building_basic_agents_langchain_autogen.ipynb` | 3.2 | LangChain prompt templates & tools, tool selection/fallback, AutoGen `AssistantAgent`/`UserProxyAgent`, streaming, multimodal agents |
| 3 | `03_intro_multi_agent_systems.ipynb` | 3.3 | The single-agent bottleneck, the "Project Team" analogy, context hand-offs, LangChain vs. AutoGen vs. CrewAI |
| 4 | `04_orchestrating_multi_agent_workflows.ipynb` | 3.4 | Fixed-sequence (`RoundRobinGroupChat`) vs. dynamic (`SelectorGroupChat`) orchestration, CrewAI Flow concepts, saving/reloading agent state |
| 5 | `05_practical_multi_agent_implementations.ipynb` | 3.5 | CrewAI customer-service & chef/nutritionist MAS examples, the "Teenager Framework" for observability, human-in-the-loop (confidence-based vs. hard category-based escalation) |
| 6 | `06_mcp_preview.ipynb` | 3.6 | MCP concepts ("USB-C for AI"), the three primitives (Tools/Resources/Prompts), architecture, a simulated discovery→execution flow — preview only, full build-out is Week 5 |

## How to use

1. Unzip and open the notebooks in Jupyter, VS Code, or JupyterLab, in numeric order.
2. Every notebook runs top-to-bottom with **Run All** — no setup required.
3. Each notebook ends with a **Key Takeaways** summary and **Check your understanding** questions —
   use these for self-check or as facilitator discussion prompts.
4. To go from simulation to a real implementation, look for the fenced code blocks marked
   `# Real ... usage` / `# Real ... sketch` — these show the actual library/API calls
   (`pip install langchain langchain-anthropic pyautogen crewai`, plus an Anthropic or OpenAI API key).

## Suggested pacing (matches the programme's Week 4 day plan)

- **Day 1 (Agentic fundamentals):** Notebook 1
- **Day 2 (LangChain & AutoGen agents):** Notebook 2
- **Day 3 (MAS design + CrewAI):** Notebooks 3 & 4
- **Day 4 (MCP preview):** Notebooks 5 & 6
- **Day 4–5 (Capstone: SupportPilot or CareRoute):** Apply the classify → retrieve → draft → validate →
  escalate pattern from Notebooks 3 and 5 directly to your chosen capstone domain.
