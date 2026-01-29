# Project Charter: Zeus Decision Graph Visualization

**Created**: 2026-01-28
**SR&ED Project**: NO (internal tooling, reuses existing skill)
**Project Duration**: 2026-01-28 to 2026-01-29

## Executive Summary

This project applies the **network-ecosystem visualization skill** (created in the FBC partner ecosystem project) to visualize the Zeus Memory decision graph. It demonstrates the reusability of the skill and provides valuable insight into how decisions, memories, and agents relate within Zeus Memory.

**Business Problem**: Zeus Memory contains thousands of decisions, learnings, and memories with relationships between them (via `related_memory` metadata, decision chains, etc.). Currently, there's no visual way to explore these relationships.

**Solution**: Use the `visualization/network-ecosystem.md` skill to generate an interactive 3D graph showing:
- Decisions as primary nodes
- Related memories as connected nodes
- Agent relationships
- Source type clustering

## Objectives

1. **Demonstrate skill reusability** - Second implementation of network-ecosystem skill
2. **Visualize Zeus decision landscape** - Understand how decisions interconnect
3. **Enable decision exploration** - Click-through navigation of decision chains
4. **Validate polyrepo strategy** - Second standalone project repo

## Data Sources

### Primary: Zeus Memory Decisions
```sql
SELECT decision_id, action, reasoning, confidence, agent_id, created_at
FROM zeus_core.decisions
WHERE tenant_id = 'b513bc6e-ad51-4a11-bea3-e3b1a84d7b55'
```

### Secondary: Related Memories
```sql
SELECT memory_id, content, source, metadata
FROM zeus_core.memories
WHERE metadata->>'type' = 'decision'
   OR metadata->>'related_memory' IS NOT NULL
```

## Node Types (Groups)

| Group | Color | Description |
|-------|-------|-------------|
| `decision_architecture` | #1a365d | Architecture decisions |
| `decision_implementation` | #2f855a | Implementation decisions |
| `decision_operational` | #3182ce | Operational decisions |
| `memory_learning` | #805ad5 | Learning/insight memories |
| `memory_research` | #d69e2e | Research documents |
| `agent` | #e53e3e | CCE agents |

## Edge Types

| Type | Description |
|------|-------------|
| `references` | Memory references another memory |
| `informs` | Memory informs a decision |
| `supersedes` | Decision supersedes previous decision |
| `agent_made` | Agent made this decision |

## Technical Approach

1. **Query Zeus** - Extract decisions and memories with relationships
2. **Transform to JSON** - Convert to network-ecosystem data format
3. **Generate HTML** - Use `generate_3d.py` from FBC project
4. **Deploy** - Standalone HTML, push to GitHub

## Success Criteria

- [ ] Visualize 50+ decisions with relationships
- [ ] Click-through navigation works
- [ ] Filters by decision type work
- [ ] Reuses skill without modification
- [ ] Published to GitHub as polyrepo

## First Principles Alignment

### 1. NO HALLUCINATIONS
- All nodes from real Zeus Memory data
- No synthetic relationships

### 2. VIRTUOUS CYCLE
- Validates and improves network-ecosystem skill
- Learnings feed back to skill documentation

### 3. FEDERATION
- Clean data extraction from Zeus API
- Standard JSON format for visualization

### 4. DATA-DRIVEN
- Visualization reflects actual Zeus Memory state
- Relationships from metadata, not assumptions

### 5. LEVERAGE COGNITION
- Reuses proven visualization skill
- No reinvention of wheel

### 6. BIDIRECTIONAL COMMUNICATION
- Clear data flow: Zeus → JSON → HTML

### 7. RACING IMPROVES BREED
- Second implementation validates skill generality

### 8. NO THEATRICAL ENGINEERING
- Minimal code - just data extraction + existing generator
- Focus on value, not complexity

## Timeline

**Day 1 (2026-01-28):**
- Create project structure
- Query Zeus for decision data
- Generate JSON and visualization
- Push to GitHub

## Team

- **Lead**: CCE (Claude Code Enhanced)
- **Oversight**: JK

## Related

- **Skill**: `visualization/network-ecosystem.md`
- **Reference Implementation**: https://github.com/ALDC-io/fbc-partner-ecosystem-visualization
- **Architecture Patterns**: ZMID `7e2d0454-25f4-4189-a99a-644d2c4a9c00`
- **Polyrepo Decision**: ZMID `1847c602-74bb-4ff9-b31c-37eaeaa9c8b6`
