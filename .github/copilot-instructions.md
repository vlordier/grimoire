# Copilot Instructions for Grimoire

## Project Overview

**Grimoire** is a system for building a continuously improving reasoning engine that accumulates structured thinking patterns. It enables AI to remember how it solved similar problems before, reuse good solution patterns ("recipes"), improve those recipes over time, and share the best ones across users safely in a federated manner.

The core architecture is **problem → lookup recipe → execute with verification → learn → improve**.

## Architecture

### Speckit Workflow System

This repository implements a multi-agent workflow system called **Speckit** that guides feature development through structured phases:

1. **Specification** (`speckit.specify`): Captures user requirements into prioritized user stories
2. **Clarification** (`speckit.clarify`): Identifies gaps and asks up to 5 targeted questions
3. **Planning** (`speckit.plan`): Generates implementation plans with research, data models, and contracts
4. **Tasking** (`speckit.tasks`): Converts plans into actionable, dependency-ordered tasks
5. **Checklist** (`speckit.checklist`): Creates domain-specific implementation checklists
6. **Implementation** (`speckit.implement`): Executes all tasks defined in tasks.md
7. **Analysis** (`speckit.analyze`): Performs cross-artifact consistency and quality checks
8. **Issues** (`speckit.taskstoissues`): Converts tasks into GitHub issues
9. **Constitution** (`speckit.constitution`): Creates/updates project principles and rules

### Directory Structure

```text
.github/
├── agents/              # Agent behavior definitions (9 speckit agents)
├── prompts/             # Prompt templates for each agent
└── copilot-instructions.md  # This file

.specify/
├── scripts/bash/        # Entry point scripts for agents
├── templates/           # Templates for spec, plan, tasks, checklist, etc.
└── memory/             # Stores constitution.md (project principles)

specs/
└── [###-feature-name]/  # Feature spec directories (numbered like 001-feature)
    ├── spec.md         # User scenarios and requirements
    ├── plan.md         # Technical design and implementation plan
    ├── research.md     # Phase 0: Research and clarifications
    ├── data-model.md   # Phase 1: Data structures and schemas
    ├── quickstart.md   # Phase 1: Quick reference guide
    ├── contracts/      # Phase 1: API/interface contracts
    └── tasks.md        # Phase 2: Concrete implementation tasks

docs/                   # Project documentation (see README.md for map)
```

### Agent-Driven Development

Each agent is triggered via CLI commands (or as subagents in the task tool) and follows a defined workflow:

- **Agent definitions** (`.github/agents/*.agent.md`) specify workflow, handoffs, and phase outputs
- **Prompt templates** (`.github/prompts/*.prompt.md`) provide context and instructions for agents
- **Setup scripts** (`.specify/scripts/bash/*.sh`) prepare environment and parse context

Key scripts:

- `setup-plan.sh`: Initializes feature directory and copies templates
- `create-new-feature.sh`: Sets up a new feature branch with spec template
- `update-agent-context.sh`: Updates agent context files after design phases
- `common.sh`: Shared utilities (get repo root, current branch, feature paths)

## Key Conventions

### Feature Branch Naming

All feature branches must follow the pattern: `###-feature-name` (e.g., `001-build-recipe-engine`, `042-federated-learning`)

The numeric prefix determines the spec directory (e.g., branch `042-*` uses `specs/042-*/`).

### Spec/Plan/Task Workflow

1. **Create a feature**: Branch creates `/specs/###-feature-name/spec.md` with user stories
2. **Run speckit.plan**: Generates research.md, data-model.md, quickstart.md, contracts/
3. **Run speckit.tasks**: Generates tasks.md with ordered, actionable tasks
4. **Implement**: Follow tasks.md; update it as needed
5. **Analyze**: Run speckit.analyze before merging to check consistency

### Environment Variables

- `SPECIFY_FEATURE`: Override current feature (useful for non-git repos)
- Agents also use `$ARGUMENTS` for user input

### JSON Output from Scripts

Scripts support `--json` flag for structured output (used by agents to parse paths and metadata). Example: `setup-plan.sh --json` returns:

```json
{
  "FEATURE_SPEC": "/path/to/spec.md",
  "IMPL_PLAN": "/path/to/plan.md",
  "SPECS_DIR": "/path/to/specs/###-feature",
  "BRANCH": "###-feature-name",
  "HAS_GIT": "true"
}
```

### Constitution File

`.specify/memory/constitution.md` defines project principles and gates that all features must satisfy. The speckit.constitution agent creates/updates this file based on interactive input or provided principles.

## Common Tasks

### Starting a New Feature

```bash
.specify/scripts/bash/create-new-feature.sh "My feature description"
```

This creates a feature branch `###-feature-name` and initializes spec.md from template.

### Running the Planning Workflow

```bash
# Specify → Clarify → Plan
# (User provides initial description)
# Agent collects 5 clarification questions
# Agent generates plan with research, data model, contracts
```

### Converting Plan to Tasks

Once plan.md is ready, the speckit.tasks agent converts it to tasks.md with dependencies and acceptance criteria.

### Implementing from Tasks

Read `specs/###-feature-name/tasks.md`, follow tasks in dependency order, update status as you go.

### Checking Consistency Before Merge

Run speckit.analyze to check:

- spec.md → plan.md alignment
- plan.md → tasks.md alignment
- Constitution gates satisfaction

## Linting and Testing Standards

**This project is strongly linted and well-tested.** All code contributions must meet these standards:

### Code Quality

- All source code must pass linting checks
- Configuration files (agent definitions, prompts, templates) must be valid (YAML for agent.md front matter, valid Markdown syntax)
- Bash scripts in `.specify/scripts/bash/` must pass shellcheck
- No hardcoded values or magic strings without justification

### Testing Requirements

- All new functionality must include tests
- Test coverage should reflect the importance and risk level of the code
- Integration tests validate agent workflows and script output formats
- Markdown and template files should be validated for structure and required sections

### Pre-Merge Checklist

Before creating a pull request:

1. Run all linters and fix violations
2. Run full test suite and verify all tests pass
3. Run `speckit.analyze` on any modified specs/plans to check consistency
4. Update documentation to match code changes

## Important Notes for AI Assistants

- **Do not modify agent definitions or prompts** unless explicitly requested—these define how all agents in this system work
- **Preserve template structure**: When updating `.specify/templates/`, maintain placeholder sections for future agent runs
- **Respect the workflow phases**: Don't skip research (Phase 0) or rush into implementation—the system depends on documented decisions
- **Update constitution.md carefully**: Changes to principles affect all features, so run speckit.analyze after updates
- **Use JSON mode for scripts**: When parsing script output programmatically, always use `--json` flag
- **Feature directories are immutable**: Don't delete specs/###-feature directories; they're the source of truth for feature history

## MCP Servers

Configure these MCP servers for optimal Copilot assistance:

- **GitHub MCP**: Essential for managing feature branches, creating/updating issues, and reviewing pull requests
- **Bash MCP**: Enables direct execution of `.specify/scripts/bash/` commands (setup-plan.sh, create-new-feature.sh, etc.)

## File Format Notes

- All markdown files use standard GitHub-flavored markdown
- Task dependencies in tasks.md use format: `Depends on: - Task 1 (ID) - Task 2 (ID)`
- Agent handoffs in agent.md files use YAML front matter for metadata
- Prompts in prompt.md files contain template variables like `$ARGUMENTS` and `$FEATURE_SPEC`
