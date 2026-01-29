#!/usr/bin/env python3
"""
Athena - Knowledge Graph Visualization API

Serves cluster and memory data for semantic zoom visualization.
Endpoints support loading data progressively based on zoom level:
- L2 clusters (zoomed out - overview)
- L1 clusters within L2 (zoomed in - detail)
- Individual memories within L1 (fully zoomed - node level)

Deployment:
    - Local: python src/api_server.py
    - Container: gunicorn api_server:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8080
"""

import json
import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


app = FastAPI(
    title="Athena - Knowledge Graph API",
    description="Progressive loading API for Zeus Memory semantic zoom visualization",
    version="1.0.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global data storage (loaded once on startup)
clustering_data = None
layout_data = None


def get_data_dir() -> Path:
    """Get data directory - works in both local dev and container."""
    # Container: /app/data
    # Local: ./data (relative to project root)
    container_path = Path("/app/data")
    if container_path.exists():
        return container_path

    # Local development
    local_path = Path(__file__).parent.parent / "data"
    if local_path.exists():
        return local_path

    # Fallback to current directory
    return Path("./data")


def get_static_dir() -> Path:
    """Get static files directory - works in both local dev and container."""
    container_path = Path("/app/static")
    if container_path.exists():
        return container_path

    local_path = Path(__file__).parent.parent / "output" / "html"
    if local_path.exists():
        return local_path

    return Path("./static")


def load_data():
    """Load clustering and layout data on startup."""
    global clustering_data, layout_data

    data_dir = get_data_dir()
    print(f"Loading data from: {data_dir}")

    clustering_path = data_dir / "clustering_results.json"
    layout_path = data_dir / "layout_results.json"

    if clustering_path.exists():
        with open(clustering_path, 'r') as f:
            clustering_data = json.load(f)
        print(f"Loaded clustering data: {len(clustering_data.get('memories', []))} memories")
    else:
        print(f"Warning: {clustering_path} not found")

    if layout_path.exists():
        with open(layout_path, 'r') as f:
            layout_data = json.load(f)
        print(f"Loaded layout data: {len(layout_data.get('positions', {}).get('memories', {}))} memory positions")
    else:
        print(f"Warning: {layout_path} not found")


@app.on_event("startup")
async def startup():
    load_data()


# Response models
class ClusterInfo(BaseModel):
    id: str
    x: float
    y: float
    size: int
    label: Optional[str] = None


class MemoryInfo(BaseModel):
    id: str
    x: float
    y: float
    content_preview: str
    category: str
    cluster_l1: int
    cluster_l2: int


class L2OverviewResponse(BaseModel):
    total_clusters: int
    total_memories: int
    clusters: list[ClusterInfo]


class L1DetailResponse(BaseModel):
    l2_cluster_id: str
    total_l1_clusters: int
    clusters: list[ClusterInfo]


class MemoriesResponse(BaseModel):
    l1_cluster_id: str
    total_memories: int
    memories: list[MemoryInfo]


# Endpoints

@app.get("/")
async def root():
    """Serve the landing page with links to all visualizations."""
    static_dir = get_static_dir()

    # Build list of available visualizations
    visualizations = [
        {"name": "Zeus Decision Graph", "path": "/viz/zeus", "description": "Knowledge graph of Zeus Memory decisions and learnings"},
        {"name": "Food Banks Canada Ecosystem", "path": "/viz/fbc", "description": "Partner ecosystem for Food Banks Canada supply chain initiative"},
        {"name": "Fusion92 Schema", "path": "/viz/f92", "description": "Data schema for Fusion92 Activation Model"},
        {"name": "ALDC Internal Schema", "path": "/viz/aldc", "description": "Data schema for ALDC Operations Model"},
        {"name": "GEP Schema", "path": "/viz/gep", "description": "Data schema for Global Export Platform"},
    ]

    # Generate landing page HTML
    viz_cards = ""
    for viz in visualizations:
        viz_cards += f'''
        <a href="{viz['path']}" class="viz-card">
            <h2>{viz['name']}</h2>
            <p>{viz['description']}</p>
        </a>
        '''

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Athena - Knowledge Graph Visualizations</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3a 100%);
            min-height: 100vh;
            color: #fff;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 40px 20px;
        }}
        header {{
            text-align: center;
            margin-bottom: 50px;
        }}
        h1 {{
            font-size: 48px;
            font-weight: 700;
            background: linear-gradient(90deg, #3182ce, #805ad5);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }}
        .subtitle {{
            font-size: 18px;
            color: #a0aec0;
        }}
        .viz-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 24px;
        }}
        .viz-card {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 24px;
            text-decoration: none;
            color: inherit;
            transition: all 0.3s ease;
        }}
        .viz-card:hover {{
            background: rgba(255, 255, 255, 0.1);
            border-color: #3182ce;
            transform: translateY(-4px);
        }}
        .viz-card h2 {{
            font-size: 20px;
            font-weight: 600;
            margin-bottom: 8px;
            color: #fff;
        }}
        .viz-card p {{
            font-size: 14px;
            color: #a0aec0;
            line-height: 1.5;
        }}
        footer {{
            text-align: center;
            margin-top: 60px;
            padding-top: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #718096;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Athena</h1>
            <p class="subtitle">Interactive Knowledge Graph Visualizations</p>
        </header>
        <div class="viz-grid">
            {viz_cards}
        </div>
        <footer>
            <p>Powered by Zeus Memory | ALDC</p>
        </footer>
    </div>
</body>
</html>'''

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)


@app.get("/viz/zeus")
async def viz_zeus():
    """Serve the Zeus Decision Graph visualization."""
    static_dir = get_static_dir()
    html_file = static_dir / "zeus_decision_graph.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Zeus visualization not found")


@app.get("/viz/fbc")
async def viz_fbc():
    """Serve the Food Banks Canada ecosystem visualization."""
    static_dir = get_static_dir()
    html_file = static_dir / "fbc_ecosystem.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="FBC visualization not found")


@app.get("/viz/f92")
async def viz_f92():
    """Serve the Fusion92 schema visualization."""
    static_dir = get_static_dir()
    html_file = static_dir / "f92_schema.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="F92 visualization not found")


@app.get("/viz/aldc")
async def viz_aldc():
    """Serve the ALDC schema visualization."""
    static_dir = get_static_dir()
    html_file = static_dir / "aldc_schema.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="ALDC visualization not found")


@app.get("/viz/gep")
async def viz_gep():
    """Serve the GEP schema visualization."""
    static_dir = get_static_dir()
    html_file = static_dir / "gep_schema.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="GEP visualization not found")


@app.get("/api")
async def api_info():
    """API info endpoint."""
    return {
        "service": "athena-knowledge-graph",
        "version": "1.0.0",
        "endpoints": {
            "/api/overview": "L2 cluster overview (zoomed out)",
            "/api/l2/{cluster_id}": "L1 clusters within an L2 cluster",
            "/api/l1/{cluster_id}": "Memories within an L1 cluster",
            "/api/memory/{memory_id}": "Single memory details",
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "data_loaded": clustering_data is not None and layout_data is not None,
        "memories_count": len(clustering_data.get('memories', [])) if clustering_data else 0,
    }


@app.get("/api/overview")
async def get_overview():
    """
    Get L2 cluster overview for zoomed-out view.
    Returns all L2 clusters with their positions, sizes, and colors.
    """
    if not clustering_data or not layout_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    l2_clusters = clustering_data.get('clusters', {}).get('l2', {})
    l2_positions = layout_data.get('positions', {}).get('l2_clusters', {})

    # Color palette for L2 clusters based on dominant category
    category_colors = {
        "decision": "#1a365d",
        "cce_decision_log": "#2f855a",
        "cce_research": "#3182ce",
        "cce_failed_approach": "#e53e3e",
        "cce_success_log": "#38a169",
        "cce_system": "#805ad5",
        "cce": "#d69e2e",
        "architecture": "#dd6b20",
        "default": "#718096",
    }

    clusters = []
    for cluster_id, info in l2_clusters.items():
        pos = l2_positions.get(cluster_id, {"x": 0, "y": 0})
        # Determine color based on dominant category
        dominant_cat = info.get("dominant_category", "default")
        color = category_colors.get(dominant_cat, category_colors["default"])
        clusters.append({
            "id": cluster_id,
            "x": pos.get("x", 0),
            "y": pos.get("y", 0),
            "size": info.get("total_size", info.get("size", 1)),
            "label": info.get("label", f"Cluster {cluster_id}"),
            "color": color,
        })

    return {
        "total_clusters": len(clusters),
        "total_memories": len(clustering_data.get('memories', [])),
        "clusters": clusters
    }


@app.get("/api/l2/{cluster_id}")
async def get_l2_detail(cluster_id: str):
    """
    Get L1 clusters within a specific L2 cluster.
    Used when zooming into an L2 cluster.
    """
    if not clustering_data or not layout_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    l2_clusters = clustering_data.get('clusters', {}).get('l2', {})
    l1_clusters = clustering_data.get('clusters', {}).get('l1', {})
    l1_positions = layout_data.get('positions', {}).get('l1_clusters', {})

    if cluster_id not in l2_clusters:
        raise HTTPException(status_code=404, detail=f"L2 cluster {cluster_id} not found")

    l2_info = l2_clusters[cluster_id]
    l1_ids = l2_info.get('l1_clusters', [])

    # Color palette for L1 clusters
    category_colors = {
        "decision": "#1a365d",
        "cce_decision_log": "#2f855a",
        "cce_research": "#3182ce",
        "cce_failed_approach": "#e53e3e",
        "cce_success_log": "#38a169",
        "cce_system": "#805ad5",
        "cce": "#d69e2e",
        "architecture": "#dd6b20",
        "default": "#4299e1",
    }

    clusters = []
    for l1_id in l1_ids:
        l1_id_str = str(l1_id)
        l1_info = l1_clusters.get(l1_id_str, {})
        pos = l1_positions.get(l1_id_str, {"x": 0, "y": 0})
        dominant_cat = l1_info.get("dominant_category", "default")
        color = category_colors.get(dominant_cat, category_colors["default"])
        clusters.append({
            "id": l1_id_str,
            "x": pos.get("x", 0),
            "y": pos.get("y", 0),
            "size": l1_info.get("size", 1),
            "label": l1_info.get("label", f"L1-{l1_id}"),
            "color": color,
        })

    return {
        "cluster_id": cluster_id,
        "cluster_label": l2_info.get("label", f"L2-{cluster_id}"),
        "l1_clusters": clusters
    }


@app.get("/api/l1/{cluster_id}")
async def get_l1_memories(
    cluster_id: str,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0)
):
    """
    Get memories within a specific L1 cluster.
    Used when zooming into an L1 cluster to see individual nodes.
    Supports pagination for large clusters.
    """
    if not clustering_data or not layout_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    cluster_id_int = int(cluster_id)
    memory_positions = layout_data.get('positions', {}).get('memories', {})
    l1_clusters = clustering_data.get('clusters', {}).get('l1', {})

    # Get L1 cluster info
    l1_info = l1_clusters.get(cluster_id, {})

    # Filter memories by L1 cluster
    cluster_memories = [
        m for m in clustering_data.get('memories', [])
        if m.get('cluster_l1') == cluster_id_int
    ]

    if not cluster_memories:
        raise HTTPException(status_code=404, detail=f"L1 cluster {cluster_id} not found or empty")

    # Apply pagination
    total = len(cluster_memories)
    paginated = cluster_memories[offset:offset + limit]
    has_more = offset + limit < total

    memories = []
    for mem in paginated:
        mem_id = mem['id']
        pos = memory_positions.get(mem_id, {"x": 0, "y": 0})
        memories.append({
            "id": mem_id,
            "x": pos.get("x", 0),
            "y": pos.get("y", 0),
            "content_preview": mem.get('content_preview', '')[:200],
            "category": mem.get('category', 'general'),
            "cluster_l1": mem.get('cluster_l1'),
            "cluster_l2": mem.get('cluster_l2'),
        })

    return {
        "cluster_id": cluster_id,
        "cluster_label": l1_info.get("label", f"L1-{cluster_id}"),
        "total_memories": total,
        "memories": memories,
        "has_more": has_more,
    }


@app.get("/api/memory/{memory_id}")
async def get_memory(memory_id: str):
    """
    Get full details for a specific memory.
    Used when clicking on a node.
    """
    if not clustering_data or not layout_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    memory_positions = layout_data.get('positions', {}).get('memories', {})

    # Find the memory
    memory = None
    for m in clustering_data.get('memories', []):
        if m['id'] == memory_id:
            memory = m
            break

    if not memory:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")

    pos = memory_positions.get(memory_id, {"x": 0, "y": 0})

    return {
        "id": memory_id,
        "content": memory.get('content_preview', ''),
        "category": memory.get('category', 'general'),
        "source": memory.get('source', 'zeus'),
        "created_at": memory.get('created_at', ''),
        "cluster_l1": str(memory.get('cluster_l1', '')),
        "cluster_l2": str(memory.get('cluster_l2', '')),
        "metadata": {
            "x": pos.get("x", 0),
            "y": pos.get("y", 0),
        }
    }


@app.get("/api/stats")
async def get_stats():
    """Get statistics about the loaded data."""
    if not clustering_data or not layout_data:
        return {
            "total_memories": 0,
            "total_l1_clusters": 0,
            "total_l2_clusters": 0,
            "data_loaded": False,
        }

    return {
        "total_memories": len(clustering_data.get('memories', [])),
        "total_l1_clusters": len(clustering_data.get('clusters', {}).get('l1', {})),
        "total_l2_clusters": len(clustering_data.get('clusters', {}).get('l2', {})),
        "data_loaded": True,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
