# Project Charter: Athena - Knowledge Graph Visualization

**Created**: 2026-01-28
**SR&ED Project**: NO (internal tooling, reuses existing skill)
**Project Duration**: 2026-01-28 to 2026-01-29
**Service Name**: Athena
**Domain**: athena.aldc.io

## Executive Summary

**Athena** is the ALDC Knowledge Graph Visualization system, providing interactive 3D exploration of Zeus Memory's decisions, learnings, and relationships. Named after the Greek goddess of wisdom, Athena complements Zeus (memory storage) and Atlas (workspace dashboard).

**Business Problem**: Zeus Memory contains 3M+ memories with complex relationships. Currently, there's no visual way to explore these relationships at scale.

**Solution**: Interactive 3D graph visualization with:
- Semantic zoom (L2 clusters → L1 clusters → individual memories)
- Progressive loading API for 50K+ nodes
- Click-through navigation of decision chains
- Deployed as `athena.aldc.io` on Azure Container Apps

## Objectives

1. **Deploy Athena service** - `athena.aldc.io` on Azure Container Apps
2. **Visualize Zeus decision landscape** - Understand how decisions interconnect
3. **Enable decision exploration** - Click-through navigation of decision chains
4. **Scale to 50K+ memories** - Progressive loading with semantic zoom

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
2. **Cluster & Layout** - Leiden clustering + ForceAtlas2 positioning
3. **Progressive API** - FastAPI server for semantic zoom
4. **Generate HTML** - 3D visualization with 3d-force-graph
5. **Deploy to Azure** - Container Apps at `athena.aldc.io`

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    athena.aldc.io                           │
├─────────────────────────────────────────────────────────────┤
│  Azure Container Apps (cae-zeus-memory-dev)                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  athena container (Python 3.11 + FastAPI)           │   │
│  │  - /api/overview      → L2 clusters (385)           │   │
│  │  - /api/l2/{id}       → L1 clusters within L2       │   │
│  │  - /api/l1/{id}       → Memories within L1          │   │
│  │  - /api/memory/{id}   → Single memory details       │   │
│  │  - /                  → 3D visualization HTML       │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Data (baked into container)                                │
│  - clustering_results.json (50K memories, 3264 L1, 385 L2) │
│  - layout_results.json (pre-computed x,y positions)        │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Infrastructure

| Component | Value |
|-----------|-------|
| **Resource Group** | `rg-zeus-memory-dev` |
| **Container Environment** | `cae-zeus-memory-dev` |
| **Container Registry** | `acrzeusmemorydev.azurecr.io` |
| **Container Name** | `athena` |
| **Image** | `acrzeusmemorydev.azurecr.io/athena:v1.0.0` |
| **Port** | 8080 |
| **CPU/Memory** | 1.0 cores / 2.0 GB |
| **Replicas** | 1-3 (auto-scaling) |
| **Domain** | `athena.aldc.io` (Cloudflare proxy) |

## Success Criteria

- [x] Visualize 210 decisions with relationships (v1.0.0)
- [x] Click-through navigation works
- [x] Filters by node/edge type work
- [x] Progressive loading API complete (Phase 3)
- [x] Tagged v1.0.0 for rollback
- [ ] Deployed to `athena.aldc.io`
- [ ] Health endpoint responds
- [ ] Custom domain with HTTPS working

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
- [x] Create project structure
- [x] Query Zeus for decision data
- [x] Generate JSON and visualization
- [x] Push to GitHub
- [x] Phase 1-3 complete (clustering, layout, API)
- [x] Tag v1.0.0

**Day 2 (2026-01-29):**
- [ ] Create Dockerfile
- [ ] Build and push to ACR
- [ ] Deploy to Azure Container Apps
- [ ] Configure athena.aldc.io domain
- [ ] Verify health endpoint

## Team

- **Lead**: CCE (Claude Code Enhanced)
- **Oversight**: JK

## Related

- **Skill**: `visualization/network-ecosystem.md`
- **Skill**: `azure/container-apps-deployment.md`
- **Skill**: `cloudflare/tunnel-setup.md`
- **Reference Implementation**: https://github.com/ALDC-io/fbc-partner-ecosystem-visualization
- **Architecture Patterns**: ZMID `7e2d0454-25f4-4189-a99a-644d2c4a9c00`
- **CCE Learning - VR Mode Fix**: ZMID `c2d082b3-c54a-4ce1-b2b2-036ee50ce9c0`
- **CCE Learning - API Success**: ZMID `422126dd-2714-4008-b993-545e4ee8cdfb`
