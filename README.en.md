# Context Continuity

**Keep decisions, context, and task progress intact when work moves between AI agents, sessions, and tools.**

**English · [简体中文](README.md)**

Context Continuity is an open-source Agent Skill for maintaining *continuity of work*. It helps an agent locate the current source of truth, understand decisions and their rationale, carry relevant context into a handoff, and write verified outcomes back to the maintained project files.

It is designed for existing workspaces. It does not require replacing your folder structure, introducing a centralized memory database, or adopting a new orchestration system.

## Why it exists

When a project changes hands between agents or conversations, the next agent may act on an old summary, miss an accepted decision, or overwrite recent work. A short instruction like "continue the task" rarely carries enough context to prevent this.

Context Continuity addresses the handoff *process*, not just the size of a summary:

- **Source of truth:** identify which files contain the latest authoritative project facts, decisions, and constraints.
- **Task handoff:** transfer the goal, current status, relevant evidence, accepted decisions, unresolved questions, and editing scope.
- **Safe continuation:** inspect the current files before modifying them, preserve human edits, and avoid reviving outdated plans.
- **Learning from failure:** determine whether a recurring mistake comes from missing context, poor retrieval, conflicting rules, or execution; repair the right layer instead of adding more generic instructions.

## Quick start

Install the Skill with a compatible installer:

```bash
npx skills add JasperLin2333/context-continuity --skill context-continuity
```

Alternatively, [download the Skill package](https://github.com/JasperLin2333/context-continuity/releases/latest/download/context-continuity.zip) and install the full `context-continuity` directory using your agent host's Skill conventions. Keep `SKILL.md` and its `references/` directory together.

Then ask an agent that can access your workspace:

> Use context-continuity to inspect this project, find the current source of truth and accepted decisions, identify gaps in cross-session handoffs, and recommend the smallest useful fixes. Don't modify files until I authorize it.

For an existing project, you can also say:

> Check the current project files and the latest accepted decisions, then continue the unfinished task without overwriting more recent work.

The Skill runs through your existing AI assistant. It does not require a separate model API key.

## Where it fits

Use it to make multi-session and multi-agent collaboration more reliable in software repositories, product planning, research, and other maintained workspaces.

Keep project-specific facts in the project. Promote repeatable practices to shared instructions only when they demonstrably help. Prefer the smallest mechanism that reliably survives handoffs.

## Documentation and related projects

- [Skill instructions](SKILL.md)
- [Contributor guide](CONTRIBUTING.md)
- [Yuanxing: AI prototyping workbench](https://github.com/JasperLin2333/yuanxing)

**Limitations:** This Skill does not automatically synchronize private memories or files between tools. Every agent still needs access to the relevant current project sources, and file edits remain subject to the host's capabilities and your permissions.

## License

[MIT License](LICENSE)
