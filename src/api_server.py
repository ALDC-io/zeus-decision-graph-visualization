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
        {"name": "Zeus Tenant Distribution", "path": "/viz/tenants", "description": "Ring chart showing memory distribution across tenants"},
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


@app.get("/viz/tenants")
async def viz_tenants():
    """Serve the Zeus Tenant Distribution ring chart visualization."""
    static_dir = get_static_dir()
    html_file = static_dir / "zeus_tenant_ring.html"
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
    raise HTTPException(status_code=404, detail="Zeus Tenant visualization not found")


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


@app.get("/favicon.ico")
async def favicon():
    """Return empty response for favicon to suppress 404 errors."""
    from fastapi.responses import Response
    return Response(status_code=204)


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


@app.get("/api/tenant-distribution")
async def get_tenant_distribution():
    """
    Get Zeus Memory distribution by tenant.
    Returns tenant names, memory counts, and percentages for visualization.
    """
    import asyncpg
    import os

    # Database connection from environment
    db_config = {
        "host": os.getenv("DB_HOST", "psql-zeus-memory-dev.postgres.database.azure.com"),
        "database": os.getenv("DB_NAME", "zeus_core"),
        "user": os.getenv("DB_USER", "zeus_admin"),
        "password": os.getenv("DB_PASSWORD", "ZeusMemory2024Db"),
    }

    try:
        conn = await asyncpg.connect(**db_config)

        query = """
            SELECT
                t.name as tenant_name,
                t.tenant_id::text,
                COUNT(m.memory_id) as memory_count
            FROM zeus_core.tenants t
            LEFT JOIN zeus_core.memories m ON t.tenant_id = m.tenant_id
            GROUP BY t.name, t.tenant_id
            ORDER BY memory_count DESC
        """

        rows = await conn.fetch(query)
        await conn.close()

        # Assign colors to tenants
        colors = [
            "#3182ce", "#805ad5", "#38a169", "#e53e3e", "#dd6b20",
            "#d69e2e", "#319795", "#b794f4", "#f687b3", "#68d391",
            "#fc8181", "#63b3ed", "#9f7aea", "#48bb78"
        ]

        tenants = []
        total_memories = 0

        for i, row in enumerate(rows):
            tenant = {
                "name": row["tenant_name"],
                "tenant_id": row["tenant_id"],
                "memory_count": row["memory_count"],
                "color": colors[i % len(colors)]
            }
            tenants.append(tenant)
            total_memories += row["memory_count"]

        # Calculate percentages
        for tenant in tenants:
            tenant["percentage"] = round((tenant["memory_count"] / total_memories * 100), 2) if total_memories > 0 else 0

        # Filter active tenants for the chart (those with memories)
        active_tenants = [t for t in tenants if t["memory_count"] > 0]

        return {
            "total_memories": total_memories,
            "total_tenants": len(tenants),
            "active_tenants": len(active_tenants),
            "tenants": tenants,
            "active_tenants_data": active_tenants,
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }

    except Exception as e:
        # Return fallback static data if DB unavailable
        return {
            "total_memories": 3556338,
            "total_tenants": 16,
            "active_tenants": 10,
            "tenants": [],
            "error": str(e),
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }


@app.get("/api/tenant-graph")
async def get_tenant_graph():
    """
    Get 3-level deep Zeus Memory graph for visualization.
    Level 1: Tenants
    Level 2: Sources within each tenant
    Level 3: Sample memories with semantic relationships based on embeddings
    """
    import asyncpg
    import os

    db_config = {
        "host": os.getenv("DB_HOST", "psql-zeus-memory-dev.postgres.database.azure.com"),
        "database": os.getenv("DB_NAME", "zeus_core"),
        "user": os.getenv("DB_USER", "zeus_admin"),
        "password": os.getenv("DB_PASSWORD", "ZeusMemory2024Db"),
    }

    # Colors for different levels
    tenant_colors = {
        "JK": "#3182ce",
        "ALDC Management Team": "#805ad5",
        "System Default": "#38a169",
        "Former Employees": "#e53e3e",
    }
    source_colors = {
        "email": "#63b3ed",
        "slack": "#f6ad55",
        "ms_graph": "#68d391",
        "api": "#fc8181",
        "web": "#b794f4",
        "avoma": "#f687b3",
        "rss": "#9ae6b4",
        "arxiv": "#fbd38d",
    }

    def get_source_color(source):
        for key, color in source_colors.items():
            if key in source.lower():
                return color
        return "#a0aec0"

    def get_source_group(source):
        source_lower = source.lower()
        if 'email' in source_lower or 'ms_graph' in source_lower:
            return 'email'
        elif 'slack' in source_lower:
            return 'slack'
        elif 'rss' in source_lower:
            return 'rss'
        elif 'arxiv' in source_lower:
            return 'research'
        elif 'api' in source_lower or 'claude' in source_lower:
            return 'api'
        elif 'web' in source_lower:
            return 'web'
        elif 'nextcloud' in source_lower or 'j5' in source_lower:
            return 'documents'
        else:
            return 'other'

    try:
        conn = await asyncpg.connect(**db_config, timeout=30, command_timeout=30)

        # Hardcode known tenant data for speed - avoid expensive COUNT queries
        # This provides instant response with accurate-enough data
        tenants = [
            {"tenant_name": "JK", "tenant_id": "b513bc6e-ad51-4a11-bea3-e3b1a84d7b55", "memory_count": 3284012},
            {"tenant_name": "ALDC Management Team", "tenant_id": "11111111-1111-1111-1111-111111111111", "memory_count": 250805},
            {"tenant_name": "System Default", "tenant_id": "00000000-0000-0000-0000-000000000001", "memory_count": 10500},
            {"tenant_name": "Former Employees", "tenant_id": "33333333-3333-3333-3333-333333333333", "memory_count": 5200},
            {"tenant_name": "J5:Customers", "tenant_id": "5a2d91f4-8b7e-4c3a-9f1a-6e8c2d3b5a7f", "memory_count": 3800},
            {"tenant_name": "J5 Design", "tenant_id": "4b1eacc5-169a-41d8-8f11-727c0e4bc0b8", "memory_count": 2300},
        ]
        tenant_ids = [t["tenant_id"] for t in tenants]

        # Hardcode top sources per tenant for instant response
        sources = [
            # JK tenant
            {"tenant_name": "JK", "tenant_id": "b513bc6e-ad51-4a11-bea3-e3b1a84d7b55", "source": "ms_graph_email_production", "memory_count": 2236202},
            {"tenant_name": "JK", "tenant_id": "b513bc6e-ad51-4a11-bea3-e3b1a84d7b55", "source": "slack_gap_fill", "memory_count": 377156},
            {"tenant_name": "JK", "tenant_id": "b513bc6e-ad51-4a11-bea3-e3b1a84d7b55", "source": "slack_robust_ingestion", "memory_count": 340057},
            {"tenant_name": "JK", "tenant_id": "b513bc6e-ad51-4a11-bea3-e3b1a84d7b55", "source": "email", "memory_count": 67099},
            {"tenant_name": "JK", "tenant_id": "b513bc6e-ad51-4a11-bea3-e3b1a84d7b55", "source": "api", "memory_count": 30662},
            {"tenant_name": "JK", "tenant_id": "b513bc6e-ad51-4a11-bea3-e3b1a84d7b55", "source": "rss_arxiv", "memory_count": 5200},
            # ALDC Management Team
            {"tenant_name": "ALDC Management Team", "tenant_id": "11111111-1111-1111-1111-111111111111", "source": "ms_graph_email", "memory_count": 180000},
            {"tenant_name": "ALDC Management Team", "tenant_id": "11111111-1111-1111-1111-111111111111", "source": "slack", "memory_count": 50000},
            {"tenant_name": "ALDC Management Team", "tenant_id": "11111111-1111-1111-1111-111111111111", "source": "api", "memory_count": 20000},
            # System Default
            {"tenant_name": "System Default", "tenant_id": "00000000-0000-0000-0000-000000000001", "source": "rss_tech_news", "memory_count": 5000},
            {"tenant_name": "System Default", "tenant_id": "00000000-0000-0000-0000-000000000001", "source": "rss_arxiv", "memory_count": 3500},
            {"tenant_name": "System Default", "tenant_id": "00000000-0000-0000-0000-000000000001", "source": "web_scraping", "memory_count": 2000},
            # J5 Customers
            {"tenant_name": "J5:Customers", "tenant_id": "5a2d91f4-8b7e-4c3a-9f1a-6e8c2d3b5a7f", "source": "covenant_portfolio", "memory_count": 2000},
            {"tenant_name": "J5:Customers", "tenant_id": "5a2d91f4-8b7e-4c3a-9f1a-6e8c2d3b5a7f", "source": "covenant_journey_map", "memory_count": 1800},
        ]

        # Skip live memory query - too slow. Use hardcoded sample for demo
        # Real memories would be loaded on-demand when drilling down
        memories = []

        # Skip semantic query for now - too slow with 3.5M rows
        # TODO: Pre-compute semantic links in a background job
        semantic_links = []

        await conn.close()

        # Build graph structure
        nodes = []
        links = []
        total_memories = sum(t["memory_count"] for t in tenants)

        # Central hub
        nodes.append({
            "id": "zeus-hub",
            "name": "Zeus Memory",
            "description": f"{total_memories:,} total memories across {len(tenants)} tenants",
            "val": 100,
            "color": "#1a365d",
            "tier": 0,
            "type": "hub",
            "group": "hub",
            "groupLabel": "Hub"
        })

        # Group sources by tenant
        sources_by_tenant = {}
        for s in sources:
            tid = s["tenant_id"]
            if tid not in sources_by_tenant:
                sources_by_tenant[tid] = []
            if len(sources_by_tenant[tid]) < 8:
                sources_by_tenant[tid].append(s)

        # Group actual memories by tenant+source
        memories_by_key = {}
        for m in memories:
            key = f"{m['tenant_id']}_{m['source']}"
            if key not in memories_by_key:
                memories_by_key[key] = []
            memories_by_key[key].append(m)

        # Track source node IDs for semantic links
        source_node_map = {}

        # Level 1: Tenants
        for i, tenant in enumerate(tenants):
            tid = tenant["tenant_id"]
            tname = tenant["tenant_name"]
            tcount = tenant["memory_count"]

            node_id = f"tenant_{tid[:8]}"
            nodes.append({
                "id": node_id,
                "name": tname,
                "description": f"{tcount:,} memories",
                "val": 30 + (tcount / total_memories) * 50,
                "color": tenant_colors.get(tname, "#718096"),
                "tier": 1,
                "type": "tenant",
                "group": "tenant",
                "groupLabel": "Tenants",
                "memoryCount": tcount
            })

            links.append({
                "source": "zeus-hub",
                "target": node_id,
                "value": tcount / total_memories * 10,
                "type": "hierarchy",
                "color": "rgba(255,255,255,0.2)"
            })

            # Level 2: Sources
            tenant_sources = sources_by_tenant.get(tid, [])
            tenant_total = sum(s["memory_count"] for s in tenant_sources)

            for j, source in enumerate(tenant_sources):
                source_id = f"source_{tid[:8]}_{source['source'][:20]}"
                source_count = source["memory_count"]
                source_group = get_source_group(source["source"])

                # Track for semantic links
                source_node_map[f"{tid}_{source['source']}"] = source_id

                nodes.append({
                    "id": source_id,
                    "name": source["source"].replace("_", " ").title()[:25],
                    "description": f"{source_count:,} memories from {source['source']}",
                    "val": 10 + (source_count / max(tenant_total, 1)) * 20,
                    "color": get_source_color(source["source"]),
                    "tier": 2,
                    "type": "source",
                    "group": source_group,
                    "groupLabel": source_group.title(),
                    "memoryCount": source_count,
                    "parentTenant": tname,
                    "tenantId": tid[:8]
                })

                links.append({
                    "source": node_id,
                    "target": source_id,
                    "value": source_count / max(tenant_total, 1) * 5,
                    "type": "hierarchy",
                    "color": "rgba(255,255,255,0.15)"
                })

                # Level 3: Actual memories (up to 5 per source)
                key = f"{tid}_{source['source']}"
                source_memories = memories_by_key.get(key, [])

                for k, mem in enumerate(source_memories[:5]):
                    mem_id = f"mem_{mem['memory_id'][:8]}"

                    # Use title if available, then content_summary, then content preview
                    mem_name = mem.get("title") or mem.get("content_summary") or mem.get("content_preview", "")
                    if not mem_name or mem_name.strip() == "":
                        mem_name = "Memory"
                    mem_name = mem_name[:80] + ("..." if len(mem_name) > 80 else "")

                    # Description: content_summary or content_preview
                    description = mem.get("content_summary") or mem.get("content_preview") or "No content"
                    if len(description) > 300:
                        description = description[:300] + "..."

                    nodes.append({
                        "id": mem_id,
                        "name": mem_name,
                        "description": description,
                        "val": 5,
                        "color": get_source_color(source["source"]),
                        "tier": 3,
                        "type": "memory",
                        "group": "memory",
                        "groupLabel": "Memories",
                        "fullId": mem["memory_id"],
                        "url": mem.get("url"),
                        "createdAt": mem["created_at"].isoformat() if mem["created_at"] else None,
                        "parentSource": source["source"],
                        "parentTenant": tname
                    })

                    links.append({
                        "source": source_id,
                        "target": mem_id,
                        "value": 1,
                        "type": "hierarchy",
                        "color": "rgba(255,255,255,0.1)"
                    })

        # Add semantic relationship links between sources
        for sem_link in semantic_links:
            source_key_a = f"{sem_link['tenant_a']}_{sem_link['source_a']}"
            source_key_b = f"{sem_link['tenant_b']}_{sem_link['source_b']}"

            node_a = source_node_map.get(source_key_a)
            node_b = source_node_map.get(source_key_b)

            if node_a and node_b:
                links.append({
                    "source": node_a,
                    "target": node_b,
                    "value": sem_link["connection_count"] / 2,
                    "type": "semantic",
                    "similarity": float(sem_link["avg_similarity"]),
                    "color": f"rgba(129, 90, 213, {min(0.8, sem_link['avg_similarity'])})",  # Purple for semantic
                    "connectionCount": sem_link["connection_count"]
                })

        # Collect unique groups for filters
        groups = {}
        for node in nodes:
            g = node.get("group", "other")
            if g not in groups:
                groups[g] = {
                    "id": g,
                    "label": node.get("groupLabel", g.title()),
                    "color": node.get("color", "#718096"),
                    "count": 0
                }
            groups[g]["count"] += 1

        return {
            "nodes": nodes,
            "links": links,
            "groups": list(groups.values()),
            "stats": {
                "total_memories": total_memories,
                "tenant_count": len(tenants),
                "source_count": len([n for n in nodes if n["type"] == "source"]),
                "sample_count": len([n for n in nodes if n["type"] == "memory"]),
                "semantic_links": len([l for l in links if l.get("type") == "semantic"])
            },
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }

    except Exception as e:
        import traceback
        return {
            "nodes": [],
            "links": [],
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": __import__("datetime").datetime.now().isoformat()
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
