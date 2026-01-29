#!/usr/bin/env python3
"""
Zeus Decision Graph - Progressive Loading API

Serves cluster and memory data for semantic zoom visualization.
Endpoints support loading data progressively based on zoom level:
- L2 clusters (zoomed out - overview)
- L1 clusters within L2 (zoomed in - detail)
- Individual memories within L1 (fully zoomed - node level)

Usage:
    source venv/bin/activate
    pip install fastapi uvicorn
    python src/api_server.py
    # or: uvicorn src.api_server:app --reload --port 8080
"""

import json
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel


app = FastAPI(
    title="Zeus Decision Graph API",
    description="Progressive loading API for semantic zoom visualization",
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


def load_data():
    """Load clustering and layout data on startup."""
    global clustering_data, layout_data

    data_dir = Path(__file__).parent.parent / "data"

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
    """API info endpoint."""
    return {
        "service": "zeus-decision-graph-api",
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


@app.get("/api/overview", response_model=L2OverviewResponse)
async def get_overview():
    """
    Get L2 cluster overview for zoomed-out view.
    Returns all L2 clusters with their positions and sizes.
    """
    if not clustering_data or not layout_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    l2_clusters = clustering_data.get('clusters', {}).get('l2', {})
    l2_positions = layout_data.get('positions', {}).get('l2_clusters', {})

    clusters = []
    for cluster_id, info in l2_clusters.items():
        pos = l2_positions.get(cluster_id, {"x": 0, "y": 0})
        clusters.append(ClusterInfo(
            id=cluster_id,
            x=pos.get("x", 0),
            y=pos.get("y", 0),
            size=info.get("total_size", info.get("size", 1)),
            label=info.get("label", f"Cluster {cluster_id}")
        ))

    return L2OverviewResponse(
        total_clusters=len(clusters),
        total_memories=len(clustering_data.get('memories', [])),
        clusters=clusters
    )


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

    clusters = []
    for l1_id in l1_ids:
        l1_id_str = str(l1_id)
        l1_info = l1_clusters.get(l1_id_str, {})
        pos = l1_positions.get(l1_id_str, {"x": 0, "y": 0})
        clusters.append({
            "id": l1_id_str,
            "x": pos.get("x", 0),
            "y": pos.get("y", 0),
            "size": l1_info.get("size", 1),
            "label": l1_info.get("label", f"L1-{l1_id}")
        })

    return {
        "l2_cluster_id": cluster_id,
        "total_l1_clusters": len(clusters),
        "clusters": clusters
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
        "l1_cluster_id": cluster_id,
        "total_memories": total,
        "offset": offset,
        "limit": limit,
        "memories": memories
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
        "x": pos.get("x", 0),
        "y": pos.get("y", 0),
        "content_preview": memory.get('content_preview', ''),
        "category": memory.get('category', 'general'),
        "cluster_l1": memory.get('cluster_l1'),
        "cluster_l2": memory.get('cluster_l2'),
    }


@app.get("/api/stats")
async def get_stats():
    """Get statistics about the loaded data."""
    if not clustering_data or not layout_data:
        raise HTTPException(status_code=503, detail="Data not loaded")

    return {
        "metadata": clustering_data.get('metadata', {}),
        "layout_metadata": layout_data.get('metadata', {}),
        "clusters": {
            "l1_count": len(clustering_data.get('clusters', {}).get('l1', {})),
            "l2_count": len(clustering_data.get('clusters', {}).get('l2', {})),
        },
        "positions": {
            "l1_positions": len(layout_data.get('positions', {}).get('l1_clusters', {})),
            "l2_positions": len(layout_data.get('positions', {}).get('l2_clusters', {})),
            "memory_positions": len(layout_data.get('positions', {}).get('memories', {})),
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8085)
