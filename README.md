# Zeus Decision Graph Visualization

Interactive 3D visualization of decisions, learnings, and relationships in Zeus Memory.

## Overview

This project visualizes the Zeus Memory decision graph, showing how decisions, research, learnings (successes and failures), and system events interconnect within the ALDC knowledge base.

**Live Demo**: See `output/html/zeus_decision_graph.html`

## Current Features

- **210 nodes** from Zeus Memory (decisions, CCE memories)
- **310 relationship edges** with intelligent edge generation:
  - Metadata-based (same category, same agent, explicit references)
  - Temporal clustering (same-day, same-source sequences)
  - Vector similarity (pgvector embeddings > 0.85 similarity)
  - Hub connections (decisions linked to central hub)
- **8 node types** with color-coded filtering
- **6 edge types** with independent filtering
- **Collapsible toolbar** - compact UI with expandable filter sections
- **3D navigation** - Orbit controls for rotation, zoom, and pan
- **Security filtering** - Confidential content and secrets redacted

## Interaction

- **Click** a node to see details in sidebar
- **Double-click** to zoom in (switches to 2D)
- **Drag** nodes to reposition
- **Filter** by node/edge type using toolbar chips
- **Toggle** between 2D and 3D views
- **Camera reset** - Return to default view

## Roadmap: Scaling to 3M+ Memories

The current visualization shows ~200 nodes. To scale to Zeus Memory's 3M+ memories, we're implementing a **navigable hierarchy**:

### Phase 1: Cluster the Data
- Run Leiden algorithm on k-NN graph from pgvector embeddings
- Store `cluster_l1_id`, `cluster_l2_id` on each memory
- Build 3-4 level hierarchy

### Phase 2: Pre-compute Layout
- Run ForceAtlas2 offline for each hierarchy level
- Store (pos_x, pos_y) positions in PostgreSQL
- Generate cluster labels via LLM summarization

### Phase 3: Progressive Loading API ✅
- FastAPI server at `src/api_server.py`
- Endpoints: `/api/overview`, `/api/l2/{id}`, `/api/l1/{id}`, `/api/memory/{id}`
- Loads pre-computed positions from Phase 2

### Phase 4: Semantic Zoom Frontend ✅
- Sigma.js component integrated into Atlas (`SigmaGraph.tsx`)
- API client for progressive loading (`athenaApi.ts`)
- Semantic zoom navigation: L2 domains → L1 topics → individual memories
- Breadcrumb navigation and details sidebar
- Available in Atlas Knowledge Graph view as "Zeus Semantic Zoom"

### Hierarchy Levels
| Zoom Level | What You See | ~Node Count |
|------------|--------------|-------------|
| Global | Domain themes | 10-20 |
| Region | Topic clusters | 100-500 |
| Neighborhood | Sub-clusters + key memories | 1K-5K |
| Detail | Individual memories | 200-500 |

**Performance Targets**: Max 10K nodes rendered, <2s initial load, <500ms zoom transitions

## Data Source

Data is extracted from Zeus Memory PostgreSQL database:
- `zeus_core.decisions` - Formal decision records
- `zeus_core.memories` - CCE-generated memories

## Usage

### Generate Fresh Data
```bash
python3 src/extract_zeus_data.py
```

### Generate Visualization
```bash
python3 src/generate_3d.py --input data/examples/zeus_decisions.json --output output/html/zeus_decision_graph.html
```

### View Locally
```bash
python3 -m http.server 8889 -d output/html
# Open http://localhost:8889/zeus_decision_graph.html
```

## Project Structure

```
├── PROJECT_CHARTER.md              # Project goals and scope
├── README.md                       # This file
├── RESEARCH_GRAPH_CONNECTIVITY.md  # Edge generation research
├── src/
│   ├── api_server.py               # FastAPI progressive loading API
│   ├── cluster_memories.py         # Phase 1: Leiden clustering
│   ├── compute_layout.py           # Phase 2: ForceAtlas2 layout
│   ├── extract_zeus_data.py        # Zeus data extraction + edge generation
│   └── generate_3d.py              # 3D visualization generator
├── data/
│   ├── clustering_results.json     # 50K memories with L1/L2 clusters
│   ├── layout_results.json         # Pre-computed x,y positions
│   └── examples/
│       └── zeus_decisions.json     # Sample graph data (210 nodes)
└── output/html/
    └── zeus_decision_graph.html    # Interactive visualization
```

## Deployment

### Athena API (Knowledge Graph Backend)
- **URL**: https://athena.aldc.io
- **Container**: Azure Container Apps (`athena` in `cae-zeus-memory-dev`)
- **CI/CD**: GitHub Actions auto-deploys on push to main
- **Data**: 50K memories clustered into 385 L2 domains and 3,264 L1 topics

### Atlas Frontend (Semantic Zoom UI)
- **URL**: https://atlas.aldc.io
- **Container**: Azure Container Apps (`atlas` in `cae-zeus-memory-dev`)
- **CI/CD**: GitHub Actions auto-deploys on push to main
- **Integration**: Sigma.js component fetches from Athena API

### API Endpoints
| Endpoint | Description |
|----------|-------------|
| `/api/overview` | L2 cluster overview (385 domains) |
| `/api/l2/{id}` | L1 clusters within L2 domain |
| `/api/l1/{id}?limit=N` | Memories within L1 topic (paginated) |
| `/api/memory/{id}` | Full memory details |
| `/api/stats` | Data statistics |

## Related

- **Skill**: `visualization/network-ecosystem.md`
- **Reference Implementation**: [FBC Partner Ecosystem](https://github.com/ALDC-io/fbc-partner-ecosystem-visualization)
- **Atlas Repository**: [ALDC-io/atlas](https://github.com/ALDC-io/atlas)

## License

Internal ALDC use only.
