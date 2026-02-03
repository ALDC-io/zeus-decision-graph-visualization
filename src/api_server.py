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
        {"name": "Ecosystem Navigator", "path": "/viz/navigator", "description": "Multi-scale semantic zoom with project/initiative overlays - drill from ecosystem to data elements", "featured": True},
        {"name": "ALDC Data Ecosystem", "path": "/viz/ecosystem", "description": "Complete data lineage from sources through transformations to AI/ML consumption"},
        {"name": "Zeus Decision Graph", "path": "/viz/zeus", "description": "Knowledge graph of Zeus Memory decisions and learnings"},
        {"name": "Food Banks Canada Ecosystem", "path": "/viz/fbc", "description": "Partner ecosystem for Food Banks Canada supply chain initiative"},
        {"name": "Athena Data Flow", "path": "/viz/dataflow", "description": "End-to-end F92 DAX AI workflow: Account Management to Reporting with Eclipse as Data Foundation"},
        {"name": "Fusion92 Flightcheck", "path": "/viz/flightcheck", "description": "DAX AI data flow for media planning, activation, and flight management"},
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


@app.get("/viz/ecosystem")
async def viz_ecosystem():
    """Serve the ALDC Data Ecosystem visualization - complete data lineage."""
    static_dir = get_static_dir()
    html_file = static_dir / "aldc_ecosystem.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="ALDC Ecosystem visualization not found")


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
        return FileResponse(
            html_file,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    raise HTTPException(status_code=404, detail="FBC visualization not found")


@app.get("/viz/fbc_radial")
async def viz_fbc_radial():
    """Serve the Food Banks Canada radial/concentric visualization."""
    static_dir = get_static_dir()
    html_file = static_dir / "fbc_radial.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="FBC radial visualization not found")


@app.get("/viz/f92")
async def viz_f92():
    """Serve the Fusion92 schema visualization."""
    static_dir = get_static_dir()
    html_file = static_dir / "f92_schema.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="F92 visualization not found")


@app.get("/viz/flightcheck")
async def viz_flightcheck():
    """Serve the Fusion92 Flightcheck DAX AI visualization."""
    static_dir = get_static_dir()
    html_file = static_dir / "f92_flightcheck.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Flightcheck visualization not found")


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


@app.get("/viz/dataflow")
async def viz_dataflow():
    """Serve the Athena Data Flow visualization - F92 DAX AI end-to-end workflow."""
    static_dir = get_static_dir()
    html_file = static_dir / "athena_data_flow.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Athena Data Flow visualization not found")


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


@app.get("/api/search")
async def search_memories(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(default=20, le=100)
):
    """
    Search memories by content and return matching results with cluster info.
    Useful for finding where a topic fits in the hierarchy.
    """
    if not clustering_data or not layout_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    query_lower = q.lower()
    l1_clusters = clustering_data.get('clusters', {}).get('l1', {})
    l2_clusters = clustering_data.get('clusters', {}).get('l2', {})
    memory_positions = layout_data.get('positions', {}).get('memories', {})

    results = []
    for mem in clustering_data.get('memories', []):
        content = mem.get('content_preview', '').lower()
        if query_lower in content:
            l1_id = str(mem.get('cluster_l1', ''))
            l2_id = str(mem.get('cluster_l2', ''))
            l1_info = l1_clusters.get(l1_id, {})
            l2_info = l2_clusters.get(l2_id, {})
            pos = memory_positions.get(mem['id'], {"x": 0, "y": 0})

            results.append({
                "id": mem['id'],
                "content_preview": mem.get('content_preview', '')[:200],
                "category": mem.get('category', 'general'),
                "cluster_l1": l1_id,
                "cluster_l1_label": l1_info.get('label', f'L1-{l1_id}'),
                "cluster_l2": l2_id,
                "cluster_l2_label": l2_info.get('label', f'L2-{l2_id}'),
                "x": pos.get("x", 0),
                "y": pos.get("y", 0),
            })

            if len(results) >= limit:
                break

    return {
        "query": q,
        "total_results": len(results),
        "results": results,
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


# =============================================================================
# Extended Feature Endpoints (v2.0)
# =============================================================================

@app.get("/api/visualization-options")
async def get_visualization_options():
    """
    Get available visualization options and their configurations.
    Used by Atlas frontend to populate settings panels.
    """
    return {
        "layouts": [
            {"id": "force", "name": "Force-Directed", "description": "Physics-based node positioning"},
            {"id": "layered", "name": "Layered 3D", "description": "Z-axis represents hierarchy/tier"},
            {"id": "spherical", "name": "Spherical", "description": "Nodes on sphere surface by category"},
            {"id": "cylinder", "name": "Cylinder", "description": "Time on Y-axis, categories on circumference"},
        ],
        "geometries": [
            {"id": "sphere", "name": "Sphere", "symbol": "●"},
            {"id": "cube", "name": "Cube", "symbol": "■"},
            {"id": "octahedron", "name": "Octahedron", "symbol": "◆"},
            {"id": "ring", "name": "Ring", "symbol": "○"},
        ],
        "effects": [
            {"id": "glow", "name": "Glow", "description": "Add glow effect to nodes"},
            {"id": "particles", "name": "Particles", "description": "Animated particles along edges"},
            {"id": "labels", "name": "Labels", "description": "Show node labels on hover", "default": True},
            {"id": "pulse", "name": "Pulse Recent", "description": "Pulse animation for recent nodes"},
        ],
        "colorModes": [
            {"id": "category", "name": "By Category", "description": "Color by node type/category"},
            {"id": "heatmap_connections", "name": "Heat Map (Connections)", "description": "Color by connection count"},
            {"id": "heatmap_recency", "name": "Heat Map (Recency)", "description": "Color by creation date"},
        ],
        "sizeModes": [
            {"id": "default", "name": "Default", "description": "Use data-defined sizes"},
            {"id": "centrality", "name": "By Centrality", "description": "Size based on node degree"},
        ],
    }


@app.get("/api/centrality")
async def compute_centrality():
    """
    Compute centrality metrics for all nodes in the graph.
    Returns degree centrality for each node.
    """
    if not clustering_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    # Build adjacency from clustering data
    # This is a simplified centrality - for full graph we'd need edge data
    memories = clustering_data.get('memories', [])
    l1_clusters = clustering_data.get('clusters', {}).get('l1', {})

    centrality = {}
    for mem in memories:
        mem_id = mem['id']
        # Use cluster membership as proxy for connectivity
        l1_id = str(mem.get('cluster_l1', 0))
        cluster_size = l1_clusters.get(l1_id, {}).get('size', 1)
        # Nodes in larger clusters have higher "centrality"
        centrality[mem_id] = min(cluster_size / 10, 1.0)

    return {
        "metric": "degree_centrality",
        "total_nodes": len(centrality),
        "values": centrality,
    }


@app.get("/api/temporal-distribution")
async def get_temporal_distribution():
    """
    Get temporal distribution of nodes for time slider feature.
    Returns date range and counts per time bucket.
    """
    if not clustering_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    from datetime import datetime

    memories = clustering_data.get('memories', [])
    dated_memories = [m for m in memories if m.get('created_at')]

    if not dated_memories:
        return {
            "has_temporal_data": False,
            "total_with_dates": 0,
        }

    # Parse dates and find range
    dates = []
    for mem in dated_memories:
        try:
            dt = datetime.fromisoformat(mem['created_at'].replace('Z', '+00:00'))
            dates.append(dt)
        except (ValueError, TypeError):
            pass

    if not dates:
        return {"has_temporal_data": False, "total_with_dates": 0}

    min_date = min(dates)
    max_date = max(dates)

    # Create monthly buckets
    buckets = {}
    for dt in dates:
        bucket = dt.strftime("%Y-%m")
        buckets[bucket] = buckets.get(bucket, 0) + 1

    return {
        "has_temporal_data": True,
        "total_with_dates": len(dates),
        "date_range": {
            "min": min_date.isoformat(),
            "max": max_date.isoformat(),
        },
        "distribution": [
            {"period": k, "count": v}
            for k, v in sorted(buckets.items())
        ],
    }


@app.get("/api/clusters/{level}")
async def get_clusters_for_collapse(level: str = "l1"):
    """
    Get all clusters at a specific level for expand/collapse feature.
    Returns cluster info with member counts.
    """
    if not clustering_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    if level not in ["l1", "l2"]:
        raise HTTPException(status_code=400, detail="Level must be 'l1' or 'l2'")

    clusters = clustering_data.get('clusters', {}).get(level, {})

    result = []
    for cluster_id, info in clusters.items():
        result.append({
            "id": cluster_id,
            "label": info.get("label", f"{level.upper()}-{cluster_id}"),
            "size": info.get("size", info.get("total_size", 0)),
            "dominant_category": info.get("dominant_category", "unknown"),
        })

    return {
        "level": level,
        "total_clusters": len(result),
        "clusters": sorted(result, key=lambda x: x["size"], reverse=True),
    }


@app.get("/api/path/{start_id}/{end_id}")
async def find_path(start_id: str, end_id: str):
    """
    Find shortest path between two nodes.
    Uses cluster membership for path approximation.
    """
    if not clustering_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    memories = clustering_data.get('memories', [])
    mem_by_id = {m['id']: m for m in memories}

    if start_id not in mem_by_id:
        raise HTTPException(status_code=404, detail=f"Start node {start_id} not found")
    if end_id not in mem_by_id:
        raise HTTPException(status_code=404, detail=f"End node {end_id} not found")

    start_mem = mem_by_id[start_id]
    end_mem = mem_by_id[end_id]

    # Check if same cluster
    if start_mem.get('cluster_l1') == end_mem.get('cluster_l1'):
        return {
            "path_exists": True,
            "path_length": 1,
            "path": [start_id, end_id],
            "path_type": "same_l1_cluster",
        }
    elif start_mem.get('cluster_l2') == end_mem.get('cluster_l2'):
        # Find bridge through L2 cluster
        return {
            "path_exists": True,
            "path_length": 2,
            "path": [start_id, f"l2-{start_mem.get('cluster_l2')}", end_id],
            "path_type": "same_l2_cluster",
        }
    else:
        return {
            "path_exists": True,
            "path_length": 3,
            "path": [
                start_id,
                f"l2-{start_mem.get('cluster_l2')}",
                f"l2-{end_mem.get('cluster_l2')}",
                end_id
            ],
            "path_type": "cross_cluster",
        }


@app.get("/api/neighbors/{memory_id}")
async def get_neighbors(memory_id: str, max_neighbors: int = Query(default=20, le=100)):
    """
    Get neighbors of a memory node based on cluster membership.
    Useful for highlighting connected nodes on selection.
    """
    if not clustering_data or not layout_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    memories = clustering_data.get('memories', [])
    memory_positions = layout_data.get('positions', {}).get('memories', {})

    # Find the target memory
    target = None
    for m in memories:
        if m['id'] == memory_id:
            target = m
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Memory {memory_id} not found")

    target_l1 = target.get('cluster_l1')
    target_l2 = target.get('cluster_l2')

    # Find neighbors (same L1 cluster first, then same L2)
    neighbors = []
    for m in memories:
        if m['id'] == memory_id:
            continue

        if m.get('cluster_l1') == target_l1:
            pos = memory_positions.get(m['id'], {"x": 0, "y": 0})
            neighbors.append({
                "id": m['id'],
                "x": pos.get("x", 0),
                "y": pos.get("y", 0),
                "content_preview": m.get('content_preview', '')[:100],
                "category": m.get('category', 'general'),
                "relationship": "same_l1_cluster",
                "weight": 1.0,
            })

        if len(neighbors) >= max_neighbors:
            break

    # If not enough, add L2 neighbors
    if len(neighbors) < max_neighbors:
        for m in memories:
            if m['id'] == memory_id or m.get('cluster_l1') == target_l1:
                continue

            if m.get('cluster_l2') == target_l2:
                pos = memory_positions.get(m['id'], {"x": 0, "y": 0})
                neighbors.append({
                    "id": m['id'],
                    "x": pos.get("x", 0),
                    "y": pos.get("y", 0),
                    "content_preview": m.get('content_preview', '')[:100],
                    "category": m.get('category', 'general'),
                    "relationship": "same_l2_cluster",
                    "weight": 0.5,
                })

            if len(neighbors) >= max_neighbors:
                break

    return {
        "memory_id": memory_id,
        "total_neighbors": len(neighbors),
        "neighbors": neighbors,
    }


# =============================================================================
# Multi-Scale Navigator & Overlay Endpoints (v3.0)
# =============================================================================

@app.get("/viz/navigator")
async def viz_navigator():
    """Serve the Multi-Scale Ecosystem Navigator with semantic zoom and overlays."""
    static_dir = get_static_dir()
    html_file = static_dir / "ecosystem_navigator.html"
    if html_file.exists():
        return FileResponse(html_file, media_type="text/html")
    raise HTTPException(status_code=404, detail="Navigator visualization not found")


@app.get("/api/navigator/graph")
async def get_navigator_graph(level: str = "ecosystem", node_id: Optional[str] = None):
    """
    Get graph data for the multi-scale navigator.
    Supports zooming into specific nodes to load sub-graphs.

    Levels:
    - ecosystem: Full ALDC ecosystem overview
    - client: Client-specific schema (requires node_id)
    - schema: Table-level view
    - element: Column/measure level
    """
    data_dir = get_data_dir()

    if level == "ecosystem" or node_id is None:
        # Load main ecosystem navigator data
        graph_file = data_dir / "examples" / "aldc_ecosystem_navigator.json"
    else:
        # Load sub-graph based on zoom target
        graph_mapping = {
            "fusion92_client": "f92_schema_graph.json",
            "gep_client": "gep_schema_graph.json",
            "aldc_eng": "aldc_schema_graph.json",
        }

        if node_id in graph_mapping:
            graph_file = data_dir / "examples" / graph_mapping[node_id]
        else:
            graph_file = data_dir / "examples" / "aldc_ecosystem_navigator.json"

    if not graph_file.exists():
        raise HTTPException(status_code=404, detail=f"Graph data not found: {graph_file}")

    with open(graph_file, 'r') as f:
        graph_data = json.load(f)

    return {
        "level": level,
        "node_id": node_id,
        "graph": graph_data,
        "navigation": graph_data.get("navigation", {}),
        "available_overlays": list(graph_data.get("overlays", {}).keys()),
    }


@app.get("/api/overlays/projects")
async def get_project_overlays():
    """
    Get project overlay data to show on the ecosystem graph.
    Returns projects with their affected nodes for visualization.
    """
    data_dir = get_data_dir()

    # Load navigator data which contains sample overlays
    graph_file = data_dir / "examples" / "aldc_ecosystem_navigator.json"

    if graph_file.exists():
        with open(graph_file, 'r') as f:
            data = json.load(f)

        projects = data.get("sample_overlays", {}).get("projects", [])
    else:
        # Fallback sample data
        projects = [
            {
                "id": "prj-fu92-28",
                "name": "Smartsheet Replacement",
                "status": "in_progress",
                "jira_key": "FU92-28",
                "affected_nodes": ["smartsheet", "eclipse_connectors", "snowflake_warehouse", "fusion92_client"],
                "hours_spent": 218.39,
                "due_date": "2026-02-15"
            }
        ]

    return {
        "overlay_type": "projects",
        "total": len(projects),
        "items": projects,
        "style": {
            "node_halo": "#ffd700",
            "edge_style": "dashed",
            "badge_color": "#ffd700",
            "badge_icon": "clipboard"
        }
    }


@app.get("/api/overlays/initiatives")
async def get_initiative_overlays():
    """
    Get initiative overlay data for strategic view.
    Shows business initiatives mapped to technical components.
    """
    data_dir = get_data_dir()

    graph_file = data_dir / "examples" / "aldc_ecosystem_navigator.json"

    if graph_file.exists():
        with open(graph_file, 'r') as f:
            data = json.load(f)

        initiatives = data.get("sample_overlays", {}).get("initiatives", [])
    else:
        initiatives = []

    return {
        "overlay_type": "initiatives",
        "total": len(initiatives),
        "items": initiatives,
        "style": {
            "node_halo": "#00ff88",
            "edge_style": "dotted",
            "badge_color": "#00ff88",
            "badge_icon": "flag"
        }
    }


@app.get("/api/overlays/dashboards")
async def get_dashboard_overlays():
    """
    Get dashboard overlay showing data dependencies.
    Shows which data sources feed into which dashboards.
    """
    data_dir = get_data_dir()

    graph_file = data_dir / "examples" / "aldc_ecosystem_navigator.json"

    if graph_file.exists():
        with open(graph_file, 'r') as f:
            data = json.load(f)

        dashboards = data.get("sample_overlays", {}).get("dashboards", [])
    else:
        dashboards = []

    return {
        "overlay_type": "dashboards",
        "total": len(dashboards),
        "items": dashboards,
        "style": {
            "node_halo": "#ff6b6b",
            "badge_color": "#ff6b6b",
            "badge_icon": "chart"
        }
    }


@app.get("/api/overlays/timelines")
async def get_timeline_overlays():
    """
    Get timeline overlay for temporal view.
    Shows when data flows through the system.
    """
    return {
        "overlay_type": "timelines",
        "total": 0,
        "items": [],
        "style": {
            "node_pulse": True,
            "edge_particles": True,
            "gradient": ["#3182ce", "#e53e3e"]
        },
        "message": "Timeline data is derived from temporal distribution endpoint"
    }


@app.get("/api/zoom-targets/{node_id}")
async def get_zoom_target(node_id: str):
    """
    Get zoom target information for a specific node.
    Returns details about what sub-graph to load when zooming into this node.
    """
    data_dir = get_data_dir()

    # Load navigator data
    graph_file = data_dir / "examples" / "aldc_ecosystem_navigator.json"

    if not graph_file.exists():
        raise HTTPException(status_code=404, detail="Navigator data not found")

    with open(graph_file, 'r') as f:
        data = json.load(f)

    # Check navigation zoom_targets
    zoom_targets = data.get("navigation", {}).get("zoom_targets", {})

    if node_id in zoom_targets:
        target = zoom_targets[node_id]
        return {
            "node_id": node_id,
            "can_zoom": True,
            "target_graph": target.get("target_graph"),
            "target_endpoint": target.get("target_endpoint"),
            "level": target.get("level"),
            "description": target.get("description"),
        }

    # Check nodes for expandable flag
    for node in data.get("nodes", []):
        if node.get("id") == node_id and node.get("expandable"):
            return {
                "node_id": node_id,
                "can_zoom": True,
                "target_graph": node.get("zoom_target"),
                "target_endpoint": node.get("zoom_endpoint"),
                "children_preview": node.get("children_preview", {}),
            }

    return {
        "node_id": node_id,
        "can_zoom": False,
        "message": "This node does not have a drill-down view"
    }


@app.get("/api/breadcrumb")
async def get_breadcrumb(path: str = "ecosystem"):
    """
    Get breadcrumb navigation for current position in the multi-scale view.
    Path format: ecosystem > client:fusion92 > schema:Campaign > element:Spend
    """
    parts = path.split(">")

    breadcrumb = []
    for i, part in enumerate(parts):
        part = part.strip()
        if ":" in part:
            level, node_id = part.split(":", 1)
        else:
            level = part
            node_id = None

        breadcrumb.append({
            "level": level,
            "node_id": node_id,
            "path": " > ".join(parts[:i+1]),
            "is_current": i == len(parts) - 1,
        })

    return {
        "breadcrumb": breadcrumb,
        "current_level": breadcrumb[-1]["level"] if breadcrumb else "ecosystem",
        "can_zoom_out": len(breadcrumb) > 1,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
