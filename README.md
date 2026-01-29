# Zeus Decision Graph Visualization

Interactive 3D visualization of decisions, learnings, and relationships in Zeus Memory.

## Overview

This project visualizes the Zeus Memory decision graph, showing how decisions, research, learnings (successes and failures), and system events interconnect within the ALDC knowledge base.

**Live Demo**: See `output/html/zeus_decision_graph.html`

## Features

- **192 nodes** from Zeus Memory (decisions, CCE memories, system events)
- **146 relationship edges** showing how knowledge connects
- **8 node types** with color-coded filtering:
  - Decisions (formal decision records)
  - CCE Decisions (decision logs)
  - Research (reference documents)
  - Failed Approaches (learnings from failures)
  - Successes (successful implementations)
  - System Events (operational logs)
  - CCE General (general memories)
  - Architecture (architectural decisions)

## Interaction

- **Click** a node to see details in sidebar
- **Double-click** to zoom in (switches to 2D)
- **Drag** nodes to reposition
- **Filter** by node type using checkboxes
- **Toggle** between 2D and 3D views

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
├── PROJECT_CHARTER.md      # Project goals and scope
├── README.md               # This file
├── src/
│   ├── extract_zeus_data.py   # Zeus data extraction
│   └── generate_3d.py         # 3D visualization generator
├── data/examples/
│   └── zeus_decisions.json    # Extracted graph data
└── output/html/
    └── zeus_decision_graph.html  # Interactive visualization
```

## Related

- **Skill**: `visualization/network-ecosystem.md`
- **Reference Implementation**: [FBC Partner Ecosystem](https://github.com/ALDC-io/fbc-partner-ecosystem-visualization)
- **Architecture Patterns**: Zeus Memory ID `7e2d0454-25f4-4189-a99a-644d2c4a9c00`

## License

Internal ALDC use only.
