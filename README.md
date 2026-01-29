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
- **VR support** - WebXR compatible for VR headsets
- **Security filtering** - Confidential content and secrets redacted

## Interaction

- **Click** a node to see details in sidebar
- **Double-click** to zoom in (switches to 2D)
- **Drag** nodes to reposition
- **Filter** by node/edge type using toolbar chips
- **Toggle** between 2D and 3D views
- **VR Mode** - "Enter VR" button for WebXR headsets

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

### Phase 3: Progressive Loading API
- Tile-based endpoints: `/api/graph/tiles/{zoom}/{x}/{y}`
- Viewport queries with spatial indexing
- Redis cache for hot clusters

### Phase 4: Semantic Zoom Frontend
- Switch to Sigma.js (WebGL, handles 50K+ nodes)
- Implement semantic zoom - clusters expand on click/zoom
- Keep current dark space aesthetic
- LOD switching based on zoom level

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
│   ├── extract_zeus_data.py        # Zeus data extraction + edge generation
│   └── generate_3d.py              # 3D visualization generator
├── data/examples/
│   └── zeus_decisions.json         # Extracted graph data
└── output/html/
    └── zeus_decision_graph.html    # Interactive visualization
```

## Related

- **Skill**: `visualization/network-ecosystem.md`
- **Reference Implementation**: [FBC Partner Ecosystem](https://github.com/ALDC-io/fbc-partner-ecosystem-visualization)

## License

Internal ALDC use only.
