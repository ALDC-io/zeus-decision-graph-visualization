#!/usr/bin/env python3
"""
Extract Zeus Memory decisions and CCE memories for visualization.
Generates JSON in network-ecosystem format.

Edge Generation Methods:
1. Metadata-based (category, source, agent_id, explicit references)
2. Temporal clustering (same session/day)
3. Vector similarity (pgvector embeddings)
4. Hub connections (structural)
5. Contributor connections (who created each learning)

Features:
- Contributor tracking (JK, Lori, Marshall, Mike, System)
- Last 24 hours filter option
- Human-centric view (center on contributor)
"""

import json
import re
import argparse
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

# Database connection
conn_params = {
    'host': 'psql-zeus-memory-dev.postgres.database.azure.com',
    'port': 5432,
    'dbname': 'zeus_core',
    'user': 'zeus_admin',
    'password': 'ZeusMemory2024Db',
    'sslmode': 'require'
}

TENANT_ID = 'b513bc6e-ad51-4a11-bea3-e3b1a84d7b55'

# Team member mapping (name variations -> canonical ID)
TEAM_MEMBERS = {
    # JK variations
    'john moran': 'jk',
    'jk': 'jk',
    'john': 'jk',
    'jkadmin': 'jk',
    # Lori variations
    'lori beck': 'lori',
    'lori': 'lori',
    'lb': 'lori',
    # Marshall variations (Marshall Johnston)
    'marshall johnston': 'marshall',
    'marshall': 'marshall',
    'mj': 'marshall',
    # Mike variations
    'mike stuart': 'mike',
    'mike': 'mike',
    'steven deutekom': 'mike',  # alias
    # System
    'system': 'system',
    'cce': 'system',
    'cce-system': 'system',
}

# Contributor node definitions with Slack headshot images
CONTRIBUTORS = {
    "jk": {
        "label": "JK",
        "color": "#3182ce",
        "description": "John Moran - CEO & Technical Lead",
        "management": True,
        "image": "https://avatars.slack-edge.com/2021-03-01/1792355334455_edeaf5f115f48e271cf1_192.jpg"
    },
    "lori": {
        "label": "Lori",
        "color": "#d53f8c",
        "description": "Lori Beck - COO & Operations",
        "management": True,
        "image": "https://avatars.slack-edge.com/2026-02-04/10442097229670_74526c6689d7559860d8_192.jpg"
    },
    "marshall": {
        "label": "Marshall",
        "color": "#38a169",
        "description": "Marshall Johnston - CTO & Development",
        "management": True,
        "image": "https://avatars.slack-edge.com/2024-12-04/8125572494050_11d2f7ce5515e06c2e5a_192.jpg"
    },
    "mike": {
        "label": "Mike",
        "color": "#dd6b20",
        "description": "Mike Stuart - VP Engineering",
        "management": True,
        "image": "https://avatars.slack-edge.com/2026-01-19/10313768312455_181e1011878ed971ea12_192.jpg"
    },
    "system": {
        "label": "System",
        "color": "#805ad5",
        "description": "Automated CCE Learnings",
        "management": False,
        "image": None  # No image for system
    },
}

# ALDC Management Team (forms a ring in visualization)
ALDC_MANAGEMENT_TEAM = ["jk", "lori", "marshall", "mike"]

# Project to Area mapping (Client vs R&D)
PROJECT_AREAS = {
    # Client Projects
    "canadian-tire": "client",
    "osfi": "client",
    "ctfs": "client",
    "seattle-orcas": "client",
    "fan-engagement": "client",
    # R&D / Internal Projects
    "athena": "rnd",
    "atlas": "rnd",
    "zeus": "rnd",
    "eclipse": "rnd",
    "cce": "rnd",
    "liquid": "rnd",
    "innovation": "rnd",
    "aldc": "rnd",
    "daa": "rnd",
    "sred": "rnd",
    "profitability": "rnd",
}

def classify_project_area(project_name):
    """Classify a project as 'client' or 'rnd' based on name patterns."""
    if not project_name:
        return "rnd"  # Default to R&D
    project_lower = project_name.lower()
    for pattern, area in PROJECT_AREAS.items():
        if pattern in project_lower:
            return area
    return "rnd"  # Default to R&D if no match

# Ingestion source definitions - maps source patterns to canonical sources
INGESTION_SOURCES = {
    "slack": {
        "patterns": ["slack"],
        "label": "Slack",
        "color": "#4A154B",  # Slack purple
        "icon": "💬",
        "description": "Messages and threads from Slack workspace"
    },
    "email": {
        "patterns": ["email", "ms_graph_email", "microsoft_graph_email"],
        "label": "Email",
        "color": "#0078D4",  # Outlook blue
        "icon": "📧",
        "description": "Emails from Microsoft 365 / Outlook"
    },
    "web_docs": {
        "patterns": ["web_scraping_docs"],
        "label": "Documentation",
        "color": "#10B981",  # Green
        "icon": "📚",
        "description": "Technical documentation (Anthropic, LangChain, etc.)"
    },
    "web_rss": {
        "patterns": ["web_scraping_rss", "rss_"],
        "label": "RSS Feeds",
        "color": "#F59E0B",  # Orange
        "icon": "📰",
        "description": "News and blog feeds (TechCrunch, Medium, arXiv)"
    },
    "web_direct": {
        "patterns": ["web_scraping_web_direct", "web_scraping_daemon"],
        "label": "Web Scraping",
        "color": "#6366F1",  # Indigo
        "icon": "🌐",
        "description": "Direct web page scraping"
    },
    "hubspot": {
        "patterns": ["hubspot"],
        "label": "HubSpot",
        "color": "#FF7A59",  # HubSpot orange
        "icon": "🎯",
        "description": "CRM data from HubSpot"
    },
    "api": {
        "patterns": ["api"],
        "label": "API",
        "color": "#8B5CF6",  # Purple
        "icon": "🔌",
        "description": "Direct API ingestion"
    },
    "cce": {
        "patterns": ["cce"],
        "label": "CCE Learnings",
        "color": "#EC4899",  # Pink
        "icon": "🧠",
        "description": "Claude Code Enhanced session learnings"
    },
}

def classify_ingestion_source(source_name):
    """Classify a source string into a canonical ingestion source."""
    if not source_name:
        return "other"
    source_lower = source_name.lower()
    for source_id, source_info in INGESTION_SOURCES.items():
        for pattern in source_info["patterns"]:
            if pattern in source_lower:
                return source_id
    return "other"


# Group definitions with colors
GROUPS = {
    "decision": {"color": "#1a365d", "label": "Decisions"},
    "cce_decision_log": {"color": "#2f855a", "label": "CCE Decisions"},
    "cce_research": {"color": "#3182ce", "label": "Research"},
    "cce_failed_approach": {"color": "#e53e3e", "label": "Failed Approaches"},
    "cce_success_log": {"color": "#38a169", "label": "Successes"},
    "cce_system": {"color": "#805ad5", "label": "System Events"},
    "cce": {"color": "#d69e2e", "label": "CCE General"},
    "architecture": {"color": "#dd6b20", "label": "Architecture"},
    "contributor": {"color": "#718096", "label": "Contributors"},
    "management": {"color": "#e53e3e", "label": "ALDC Management Team"},
    # Area groups
    "area_client": {"color": "#2b6cb0", "label": "Client Work"},
    "area_rnd": {"color": "#9f7aea", "label": "R&D"},
    # Project groups (dynamically colored)
    "project": {"color": "#4a5568", "label": "Projects"},
    # Ingestion source groups
    "ingestion_source": {"color": "#0EA5E9", "label": "Ingestion Sources"},
    "web_domain": {"color": "#14B8A6", "label": "Web Domains"},
}

# Edge type styles - expanded for new relationship types
EDGE_TYPES = {
    # Explicit relationships
    "references": {"color": "#3182ce", "width": 3, "label": "References"},
    "informs": {"color": "#2f855a", "width": 2, "label": "Informs"},

    # Semantic similarity
    "highly_similar": {"color": "#9f7aea", "width": 3, "label": "Highly Similar"},
    "similar": {"color": "#b794f4", "width": 2, "label": "Similar"},

    # Metadata-based
    "same_category": {"color": "#ed8936", "width": 1, "label": "Same Category"},
    "same_agent": {"color": "#4fd1c5", "width": 1, "label": "Same Agent"},

    # Temporal
    "temporal_context": {"color": "#fc8181", "width": 1, "label": "Temporal Context"},

    # Contributor
    "created_by": {"color": "#00b5d8", "width": 2, "label": "Created By"},

    # Team relationships
    "team_member": {"color": "#e53e3e", "width": 4, "label": "ALDC Management Team"},

    # Hierarchy relationships (Area -> Project -> Learning)
    "contains": {"color": "#4a5568", "width": 3, "label": "Contains"},
    "belongs_to": {"color": "#718096", "width": 2, "label": "Belongs To"},
    "works_on": {"color": "#63b3ed", "width": 2, "label": "Works On"},

    # Generic
    "related": {"color": "#a0aec0", "width": 1, "label": "Related"},

    # Ingestion relationships
    "ingested_from": {"color": "#0EA5E9", "width": 2, "label": "Ingested From"},
    "feeds_into": {"color": "#14B8A6", "width": 2, "label": "Feeds Into"},
}


def resolve_contributor(metadata, source, content=""):
    """Resolve the contributor from metadata, source, or content."""
    # Check metadata fields
    if isinstance(metadata, dict):
        # Check assignee
        assignee = metadata.get('assignee', '').lower()
        if assignee in TEAM_MEMBERS:
            return TEAM_MEMBERS[assignee]

        # Check user_name (Slack)
        user_name = metadata.get('user_name', '').lower()
        if user_name in TEAM_MEMBERS:
            return TEAM_MEMBERS[user_name]

        # Check created_by
        created_by = metadata.get('created_by', '').lower()
        if created_by in TEAM_MEMBERS:
            return TEAM_MEMBERS[created_by]

    # Check source for CCE patterns (assume JK for now - could enhance)
    if source and source.startswith('cce'):
        return 'system'  # CCE learnings are system-generated

    # Check content for name mentions
    content_lower = content.lower() if content else ""
    for name, contrib_id in TEAM_MEMBERS.items():
        if name in content_lower and contrib_id != 'system':
            return contrib_id

    return 'system'  # Default to system

# Patterns that might contain secrets
SECRET_PATTERNS = [
    r'ntn_[a-zA-Z0-9]{40,}',  # Notion tokens
    r'sk-[a-zA-Z0-9]{32,}',   # OpenAI keys
    r'xoxb-[a-zA-Z0-9\-]+',   # Slack bot tokens
    r'xoxp-[a-zA-Z0-9\-]+',   # Slack user tokens
    r'ghp_[a-zA-Z0-9]{36}',   # GitHub tokens
    r'gho_[a-zA-Z0-9]{36}',   # GitHub OAuth tokens
    r'zm_[a-zA-Z0-9_]{30,}',  # Zeus Memory API keys
    r'AKIA[A-Z0-9]{16}',      # AWS access keys
    r'password["\']?\s*[:=]\s*["\'][^"\']+["\']',  # Password patterns
    r'api[_-]?key["\']?\s*[:=]\s*["\'][^"\']+["\']',  # API key patterns
]

# Safe categories (non-confidential)
SAFE_CATEGORIES = [
    'technical', 'cce_setup', 'general', 'workspace-management',
    'implementation_plan', 'implementation_validation', 'prd-review',
    'collective_intelligence', 'hybrid_collective_intelligence',
    'local_p100_deployment', 'snowflake_search'
]
# EXCLUDED (confidential): financial_analysis, cash_flow, tax_credit,
# debt_service, holdco_structure, business, business_context, operational_plan


def sanitize_secrets(text):
    """Remove potential secrets from text."""
    if not text:
        return text
    for pattern in SECRET_PATTERNS:
        text = re.sub(pattern, '[REDACTED]', text, flags=re.IGNORECASE)
    return text


def clean_text(text, max_len=None):
    """Clean text for display. If max_len is None, returns full text."""
    if not text:
        return "Untitled"
    text = sanitize_secrets(text)
    cleaned = ' '.join(text.split())
    if max_len and len(cleaned) > max_len:
        cleaned = cleaned[:max_len-3] + "..."
    return cleaned


def extract_nodes(cur, hours_filter=0):
    """Extract all nodes (decisions + memories).

    Args:
        cur: Database cursor
        hours_filter: Only include data from last N hours (0 = no filter)
    """
    nodes = []
    node_ids = set()
    node_metadata = {}  # Store metadata for edge generation

    # Build time filter clause
    time_clause = ""
    if hours_filter > 0:
        time_clause = f"AND created_at > NOW() - INTERVAL '{hours_filter} hours'"
        print(f"Filtering to last {hours_filter} hours")

    # 1. Get decisions
    cur.execute(f"""
        SELECT decision_id, action, reasoning, confidence, agent_id, created_at
        FROM zeus_core.decisions
        WHERE tenant_id = %s
        {time_clause}
        ORDER BY created_at DESC
        LIMIT 200
    """, (TENANT_ID,))

    decisions = cur.fetchall()
    print(f"Found {len(decisions)} decisions")

    for row in decisions:
        decision_id, action, reasoning, confidence, agent_id, created_at = row
        node_id = str(decision_id)
        node_ids.add(node_id)

        # Build full content with action, reasoning, and confidence
        full_content = clean_text(action)
        if reasoning:
            full_content += f"\n\nReasoning: {clean_text(reasoning)}"
        if confidence:
            full_content += f"\n\nConfidence: {confidence}"

        # Resolve contributor
        contributor = resolve_contributor({}, "decision", action)

        nodes.append({
            "id": node_id,
            "label": clean_text(action, 50),
            "title": full_content,  # Full content for modal display
            "tier": 1,
            "group": "decision",
            "size": 25 + (int(confidence * 10) if confidence else 0),
            "created_at": created_at.isoformat() if created_at else None,
            "contributor": contributor,
        })

        node_metadata[node_id] = {
            "type": "decision",
            "agent_id": str(agent_id) if agent_id else None,
            "created_at": created_at,
            "category": None,
            "source": "decision",
            "contributor": contributor,
        }

    # 2. Get CCE memories
    cur.execute(f"""
        SELECT memory_id, content, source, metadata, created_at
        FROM zeus_core.memories
        WHERE tenant_id = %s
          AND source IN ('cce_decision_log', 'cce_research', 'cce_failed_approach',
                        'cce_success_log', 'cce_system', 'cce', 'cce-learning',
                        'cce-prototype', 'cce_learn', 'cce-session', 'slack')
          AND (
            metadata->>'category' IS NULL
            OR metadata->>'category' IN %s
          )
        {time_clause}
        ORDER BY created_at DESC
        LIMIT 300
    """, (TENANT_ID, tuple(SAFE_CATEGORIES)))

    memories = cur.fetchall()
    print(f"Found {len(memories)} CCE memories")

    tier_map = {
        'cce_decision_log': 1,
        'cce_research': 2,
        'cce_failed_approach': 3,
        'cce_success_log': 2,
        'cce_system': 4,
        'cce': 3,
        'cce-learning': 2,
        'cce-prototype': 2,
        'cce_learn': 2,
        'cce-session': 3,
        'slack': 4,
    }

    size_map = {
        'cce_decision_log': 25,
        'cce_research': 20,
        'cce_failed_approach': 15,
        'cce_success_log': 20,
        'cce_system': 10,
        'cce': 15,
        'cce-learning': 18,
        'cce-prototype': 22,
        'cce_learn': 18,
        'cce-session': 12,
        'slack': 10,
    }

    for row in memories:
        memory_id, content, source, metadata, created_at = row
        node_id = str(memory_id)

        if node_id in node_ids:
            continue

        node_ids.add(node_id)

        meta = metadata if isinstance(metadata, dict) else {}

        # Resolve contributor from metadata or content
        contributor = resolve_contributor(meta, source, content)

        # Extract project name from metadata
        project = meta.get('project', '')
        area = classify_project_area(project)

        nodes.append({
            "id": node_id,
            "label": clean_text(content, 50),
            "title": clean_text(content),  # Full content for modal display
            "tier": tier_map.get(source, 3),
            "group": source if source in GROUPS else "cce",
            "size": size_map.get(source, 15),
            "created_at": created_at.isoformat() if created_at else None,
            "contributor": contributor,
            "project": project,
            "area": area,
        })

        node_metadata[node_id] = {
            "type": "memory",
            "agent_id": meta.get('agent_id'),
            "created_at": created_at,
            "category": meta.get('category'),
            "source": source,
            "related_memory": meta.get('related_memory'),
            "contributor": contributor,
            "project": project,
            "area": area,
        }

    # 3. Create hub node
    hub_id = "zeus-memory-hub"
    nodes.insert(0, {
        "id": hub_id,
        "label": "Zeus Memory",
        "title": "Zeus Memory Hub - Central knowledge store for ALDC",
        "tier": 0,
        "group": "architecture",
        "size": 50,
        "logo": "https://raw.githubusercontent.com/ALDC-io/zeus-decision-graph-visualization/main/output/static/aldc_icon_purple.png",
    })
    node_ids.add(hub_id)
    node_metadata[hub_id] = {
        "type": "hub",
        "agent_id": None,
        "created_at": datetime.now(),
        "category": "hub",
        "source": "architecture",
    }

    return nodes, node_ids, node_metadata


def generate_metadata_edges(nodes, node_ids, node_metadata):
    """Generate edges based on metadata relationships."""
    edges = []
    edge_set = set()  # Track unique edges

    def add_edge(source, target, edge_type):
        """Add edge if not already exists."""
        key = tuple(sorted([source, target])) + (edge_type,)
        if key not in edge_set and source != target:
            edge_set.add(key)
            edges.append({
                "source": source,
                "target": target,
                "type": edge_type
            })

    # 1. Explicit references from metadata
    for node_id, meta in node_metadata.items():
        related = meta.get('related_memory')
        if related and related in node_ids:
            add_edge(node_id, related, "references")

    # 2. Same category connections
    category_groups = defaultdict(list)
    for node_id, meta in node_metadata.items():
        cat = meta.get('category')
        if cat:
            category_groups[cat].append(node_id)

    for category, members in category_groups.items():
        if len(members) > 1 and len(members) <= 20:  # Avoid huge clusters
            for i, m1 in enumerate(members):
                for m2 in members[i+1:min(i+4, len(members))]:  # Max 3 edges per node
                    add_edge(m1, m2, "same_category")

    # 3. Same agent connections
    agent_groups = defaultdict(list)
    for node_id, meta in node_metadata.items():
        agent = meta.get('agent_id')
        if agent:
            agent_groups[agent].append(node_id)

    for agent, members in agent_groups.items():
        if len(members) > 1 and len(members) <= 30:
            for i, m1 in enumerate(members):
                for m2 in members[i+1:min(i+3, len(members))]:
                    add_edge(m1, m2, "same_agent")

    # 4. Same source type - connect within groups (limited)
    source_groups = defaultdict(list)
    for node_id, meta in node_metadata.items():
        src = meta.get('source')
        if src:
            source_groups[src].append(node_id)

    # Connect failed approaches to successes (learning loop)
    failed = source_groups.get('cce_failed_approach', [])
    success = source_groups.get('cce_success_log', [])
    for f in failed[:15]:
        for s in success[:15]:
            add_edge(f, s, "related")

    # Connect research to decisions
    research = source_groups.get('cce_research', [])
    decisions = source_groups.get('decision', [])
    for r in research[:20]:
        for d in decisions[:10]:
            add_edge(r, d, "informs")

    print(f"Generated {len(edges)} metadata-based edges")
    return edges, edge_set


def generate_temporal_edges(node_ids, node_metadata, edge_set):
    """Generate edges based on temporal proximity."""
    edges = []

    def add_edge(source, target, edge_type):
        key = tuple(sorted([source, target])) + (edge_type,)
        if key not in edge_set and source != target:
            edge_set.add(key)
            edges.append({
                "source": source,
                "target": target,
                "type": edge_type
            })

    # Group by day
    day_groups = defaultdict(list)
    for node_id, meta in node_metadata.items():
        created = meta.get('created_at')
        if created and meta.get('type') != 'hub':
            day_key = created.date() if hasattr(created, 'date') else None
            if day_key:
                day_groups[day_key].append((node_id, created, meta.get('source')))

    # Connect nodes from same day with same source type
    for day, members in day_groups.items():
        # Group by source within the day
        source_day = defaultdict(list)
        for node_id, created, source in members:
            source_day[source].append((node_id, created))

        for source, items in source_day.items():
            if len(items) > 1:
                # Sort by time
                items.sort(key=lambda x: x[1])
                # Connect sequential items (max 2 connections per node)
                for i in range(len(items) - 1):
                    if i < 10:  # Limit edges
                        add_edge(items[i][0], items[i+1][0], "temporal_context")

    print(f"Generated {len(edges)} temporal edges")
    return edges


def generate_similarity_edges(cur, node_ids, node_metadata, edge_set, similarity_threshold=0.85, max_edges=200):
    """Generate edges based on vector similarity using pgvector."""
    edges = []

    def add_edge(source, target, edge_type, similarity):
        key = tuple(sorted([source, target])) + (edge_type,)
        if key not in edge_set and source != target:
            edge_set.add(key)
            edges.append({
                "source": source,
                "target": target,
                "type": edge_type,
                "weight": round(similarity, 3)
            })

    # Get memory IDs that are in our node set
    memory_ids = [nid for nid, meta in node_metadata.items()
                  if meta.get('type') == 'memory']

    if not memory_ids:
        print("No memory nodes for similarity calculation")
        return edges

    # Query for similar pairs using pgvector
    # Using embedding_voyage for similarity (or embedding_bge as fallback)
    try:
        # Convert string UUIDs to proper format for PostgreSQL
        uuid_list = [uuid for uuid in memory_ids if uuid != 'zeus-memory-hub']
        cur.execute("""
            WITH node_embeddings AS (
                SELECT memory_id, embedding_voyage
                FROM zeus_core.memories
                WHERE memory_id::text = ANY(%s)
                  AND embedding_voyage IS NOT NULL
            )
            SELECT
                m1.memory_id::text as source,
                m2.memory_id::text as target,
                1 - (m1.embedding_voyage <=> m2.embedding_voyage) as similarity
            FROM node_embeddings m1
            JOIN node_embeddings m2 ON m1.memory_id < m2.memory_id
            WHERE 1 - (m1.embedding_voyage <=> m2.embedding_voyage) > %s
            ORDER BY similarity DESC
            LIMIT %s
        """, (uuid_list, similarity_threshold, max_edges))

        similar_pairs = cur.fetchall()
        print(f"Found {len(similar_pairs)} similar memory pairs")

        for source, target, similarity in similar_pairs:
            if source in node_ids and target in node_ids:
                edge_type = "highly_similar" if similarity > 0.92 else "similar"
                add_edge(source, target, edge_type, similarity)

    except Exception as e:
        print(f"Warning: Similarity query failed: {e}")
        print("Continuing without similarity edges...")

    print(f"Generated {len(edges)} similarity edges")
    return edges


def generate_hub_edges(nodes, edge_set):
    """Generate hub connections for structure."""
    edges = []
    hub_id = "zeus-memory-hub"

    def add_edge(source, target, edge_type):
        key = tuple(sorted([source, target])) + (edge_type,)
        if key not in edge_set and source != target:
            edge_set.add(key)
            edges.append({
                "source": source,
                "target": target,
                "type": edge_type
            })

    # Connect decisions and decision logs to hub
    for node in nodes:
        if node['group'] in ('decision', 'cce_decision_log') and node['id'] != hub_id:
            add_edge(hub_id, node['id'], "informs")

    print(f"Generated {len(edges)} hub edges")
    return edges


def generate_contributor_nodes_and_edges(nodes, node_ids, node_metadata, edge_set):
    """Add contributor nodes and connect learnings to their creators.

    Also creates ALDC Management Team ring connecting JK, Lori, Marshall, and Mike.
    """
    contributor_nodes = []
    contributor_edges = []
    contributor_counts = defaultdict(int)

    def add_edge(source, target, edge_type):
        key = tuple(sorted([source, target])) + (edge_type,)
        if key not in edge_set and source != target:
            edge_set.add(key)
            contributor_edges.append({
                "source": source,
                "target": target,
                "type": edge_type
            })

    # Add contributor nodes
    for contrib_id, contrib_info in CONTRIBUTORS.items():
        node_id = f"contributor_{contrib_id}"
        is_management = contrib_info.get("management", False)
        node_data = {
            "id": node_id,
            "label": contrib_info["label"],
            "title": contrib_info["description"],
            "tier": 0,  # Top tier like hub
            "group": "management" if is_management else "contributor",
            "size": 50 if is_management else 40,
            "contributor_id": contrib_id,
            "is_management": is_management,
        }
        # Add headshot image as logo for visualization
        if contrib_info.get("image"):
            node_data["logo"] = contrib_info["image"]
        contributor_nodes.append(node_data)
        node_ids.add(node_id)

    # Create ALDC Management Team ring (connect each member to the next)
    # This creates: JK <-> Lori <-> Marshall <-> Mike <-> JK
    for i, member_id in enumerate(ALDC_MANAGEMENT_TEAM):
        next_member_id = ALDC_MANAGEMENT_TEAM[(i + 1) % len(ALDC_MANAGEMENT_TEAM)]
        source_node = f"contributor_{member_id}"
        target_node = f"contributor_{next_member_id}"
        add_edge(source_node, target_node, "team_member")

    # Connect Zeus Memory hub to each management team member
    # This makes Zeus Memory part of the management team cluster
    hub_id = "zeus-memory-hub"
    for member_id in ALDC_MANAGEMENT_TEAM:
        member_node = f"contributor_{member_id}"
        add_edge(hub_id, member_node, "team_member")

    print(f"Created ALDC Management Team ring: {' <-> '.join([c.upper() for c in ALDC_MANAGEMENT_TEAM])} <-> {ALDC_MANAGEMENT_TEAM[0].upper()} + Zeus Memory")

    # Connect learnings to contributors
    for node_id, meta in node_metadata.items():
        if meta.get('type') == 'hub':
            continue
        contrib_id = meta.get('contributor', 'system')
        contributor_counts[contrib_id] += 1
        contrib_node_id = f"contributor_{contrib_id}"
        if contrib_node_id in node_ids:
            add_edge(contrib_node_id, node_id, "created_by")

    # Update contributor node sizes based on activity
    for node in contributor_nodes:
        contrib_id = node.get('contributor_id')
        count = contributor_counts.get(contrib_id, 0)
        base_size = 50 if node.get('is_management') else 30
        node['size'] = base_size + min(count, 50)  # Scale size by activity
        if node.get('is_management'):
            node['title'] += f"\n\nALDC Management Team\nLearnings: {count}"
        else:
            node['title'] += f"\n\nLearnings: {count}"

    print(f"Generated {len(contributor_nodes)} contributor nodes")
    print(f"Generated {len(contributor_edges)} contributor edges")
    print(f"  Contributor activity: {dict(contributor_counts)}")

    return contributor_nodes, contributor_edges


def generate_hierarchy_nodes_and_edges(nodes, node_ids, node_metadata, edge_set):
    """Create Area and Project hierarchy nodes.

    Hierarchy: Area (Client/R&D) -> Project -> Learning (success/failure/decision)
    This creates a visual structure showing work organized by:
    - Area (Client Work vs R&D)
    - Project/Initiative
    - Type (Success/Failure/Decision)
    """
    hierarchy_nodes = []
    hierarchy_edges = []
    project_counts = defaultdict(lambda: {'success': 0, 'failure': 0, 'decision': 0, 'other': 0})
    area_projects = defaultdict(set)

    def add_edge(source, target, edge_type):
        key = tuple(sorted([source, target])) + (edge_type,)
        if key not in edge_set and source != target:
            edge_set.add(key)
            hierarchy_edges.append({
                "source": source,
                "target": target,
                "type": edge_type
            })

    # Create Area nodes (Client and R&D)
    area_nodes = {
        "area_client": {
            "id": "area_client",
            "label": "Client Work",
            "title": "Client Projects and Engagements",
            "tier": 0,
            "group": "area_client",
            "size": 60,
        },
        "area_rnd": {
            "id": "area_rnd",
            "label": "R&D",
            "title": "Research & Development / Internal Projects",
            "tier": 0,
            "group": "area_rnd",
            "size": 60,
        }
    }

    for area_id, area_node in area_nodes.items():
        hierarchy_nodes.append(area_node)
        node_ids.add(area_id)

    # Scan nodes for projects and categorize learnings
    for node_id, meta in node_metadata.items():
        if meta.get('type') == 'hub':
            continue

        project = meta.get('project', '')
        area = meta.get('area', 'rnd')
        source = meta.get('source', '')

        if project:
            area_projects[area].add(project)

            # Categorize by type (success/failure/decision)
            if source == 'cce_success_log':
                project_counts[project]['success'] += 1
            elif source == 'cce_failed_approach':
                project_counts[project]['failure'] += 1
            elif source == 'cce_decision_log':
                project_counts[project]['decision'] += 1
            else:
                project_counts[project]['other'] += 1

    # Create Project nodes
    project_colors = ['#3182ce', '#38a169', '#d53f8c', '#dd6b20', '#805ad5', '#319795', '#d69e2e', '#e53e3e']
    color_idx = 0

    for area, projects in area_projects.items():
        for project_name in projects:
            project_id = f"project_{project_name.replace(' ', '_').replace('-', '_').lower()}"
            if project_id in node_ids:
                continue

            counts = project_counts[project_name]
            total = sum(counts.values())

            # Determine project health color
            if counts['failure'] > counts['success']:
                project_color = "#e53e3e"  # Red - more failures
            elif counts['success'] > 0:
                project_color = "#38a169"  # Green - has successes
            else:
                project_color = project_colors[color_idx % len(project_colors)]
                color_idx += 1

            hierarchy_nodes.append({
                "id": project_id,
                "label": project_name[:30],
                "title": f"{project_name}\n\nSuccesses: {counts['success']}\nFailures: {counts['failure']}\nDecisions: {counts['decision']}\nOther: {counts['other']}",
                "tier": 1,
                "group": "project",
                "size": 30 + min(total * 2, 30),
                "project_name": project_name,
                "area": area,
                "successes": counts['success'],
                "failures": counts['failure'],
            })
            node_ids.add(project_id)

            # Connect project to area
            area_node_id = f"area_{area}"
            add_edge(area_node_id, project_id, "contains")

            # Connect learnings to project
            for node_id, meta in node_metadata.items():
                if meta.get('project') == project_name:
                    add_edge(project_id, node_id, "belongs_to")

    # Summary
    print(f"Generated {len(hierarchy_nodes)} hierarchy nodes (2 areas + {len(hierarchy_nodes) - 2} projects)")
    print(f"Generated {len(hierarchy_edges)} hierarchy edges")
    print(f"  Client projects: {len(area_projects['client'])}")
    print(f"  R&D projects: {len(area_projects['rnd'])}")

    return hierarchy_nodes, hierarchy_edges


def generate_ingestion_source_nodes_and_edges(cur, node_ids, node_metadata, edge_set):
    """Generate ingestion source nodes and web domain nodes.

    Creates a visual representation of where data is being ingested from:
    - Main source nodes (Slack, Email, Web, HubSpot, etc.)
    - Web domain breakdown (grouped by domain for web sources)
    - Edges connecting sources to the hub
    """
    ingestion_nodes = []
    ingestion_edges = []
    source_counts = defaultdict(int)
    web_domain_counts = defaultdict(int)

    def add_edge(source, target, edge_type):
        key = tuple(sorted([source, target])) + (edge_type,)
        if key not in edge_set and source != target:
            edge_set.add(key)
            ingestion_edges.append({
                "source": source,
                "target": target,
                "type": edge_type
            })

    # Query source distribution from database
    cur.execute("""
        SELECT source, COUNT(*) as count
        FROM zeus_core.memories
        WHERE tenant_id = %s
        GROUP BY source
        ORDER BY count DESC
    """, (TENANT_ID,))

    source_rows = cur.fetchall()

    # Aggregate by canonical source
    for source_name, count in source_rows:
        canonical = classify_ingestion_source(source_name)
        source_counts[canonical] += count

        # Track web domains separately
        if source_name and 'web_scraping' in source_name.lower():
            # Extract domain hint from source name
            parts = source_name.replace('web_scraping_', '').replace('web-scraping_', '').split('_')
            if len(parts) >= 2:
                domain_hint = parts[0] + '_' + parts[1]  # e.g., "docs_anthropic" or "rss_techcrunch"
            else:
                domain_hint = parts[0] if parts else 'unknown'
            web_domain_counts[domain_hint] += count

    # Create main ingestion source nodes
    hub_id = "zeus-memory-hub"
    total_memories = sum(source_counts.values())

    for source_id, source_info in INGESTION_SOURCES.items():
        count = source_counts.get(source_id, 0)
        if count == 0:
            continue

        percentage = round(count / total_memories * 100, 1) if total_memories > 0 else 0
        node_id = f"source_{source_id}"

        ingestion_nodes.append({
            "id": node_id,
            "label": f"{source_info['icon']} {source_info['label']}",
            "title": f"{source_info['label']}\n\n{source_info['description']}\n\nMemories: {count:,}\nPercentage: {percentage}%",
            "tier": 1,
            "group": "ingestion_source",
            "size": 30 + min(int(count / 10000), 40),  # Scale size by count
            "source_type": source_id,
            "memory_count": count,
            "percentage": percentage,
            "color": source_info['color'],
        })
        node_ids.add(node_id)

        # Connect to hub
        add_edge(hub_id, node_id, "feeds_into")

    # Create web domain nodes (top 15 by count)
    web_source_node = "source_web_docs"
    rss_source_node = "source_web_rss"
    direct_source_node = "source_web_direct"

    sorted_domains = sorted(web_domain_counts.items(), key=lambda x: -x[1])[:15]

    for domain_hint, count in sorted_domains:
        if count < 100:  # Skip tiny sources
            continue

        domain_id = f"domain_{domain_hint.replace(' ', '_').replace('-', '_')}"
        domain_label = domain_hint.replace('_', ' ').title()

        # Determine parent source
        if 'docs' in domain_hint:
            parent_source = web_source_node
        elif 'rss' in domain_hint:
            parent_source = rss_source_node
        else:
            parent_source = direct_source_node

        ingestion_nodes.append({
            "id": domain_id,
            "label": domain_label[:25],
            "title": f"Web Source: {domain_label}\n\nMemories: {count:,}",
            "tier": 2,
            "group": "web_domain",
            "size": 15 + min(int(count / 500), 25),
            "domain": domain_hint,
            "memory_count": count,
        })
        node_ids.add(domain_id)

        # Connect to parent web source if it exists
        if parent_source in node_ids:
            add_edge(parent_source, domain_id, "contains")

    print(f"Generated {len(ingestion_nodes)} ingestion source nodes")
    print(f"  Sources: {dict(source_counts)}")
    print(f"Generated {len(ingestion_edges)} ingestion edges")

    return ingestion_nodes, ingestion_edges


def get_embedding_backlog_count(cur):
    """Get the count of pending embeddings from the embedding queue."""
    try:
        cur.execute("""
            SELECT COUNT(*) FROM zeus_core.embedding_queue
            WHERE status = 'pending'
        """)
        return cur.fetchone()[0]
    except Exception as e:
        print(f"Warning: Could not get embedding backlog: {e}")
        return 0


def extract_data(hours_filter=0, include_contributors=False, include_hierarchy=False, include_ingestion=False):
    """Extract all data and generate edges using multiple methods.

    Args:
        hours_filter: Only include data from last N hours (0 = no filter)
        include_contributors: Add contributor nodes and edges
        include_hierarchy: Add Area/Project hierarchy nodes and edges
        include_ingestion: Add ingestion source nodes and edges

    Returns:
        nodes, edges, metadata dict with embedding_backlog count
    """
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()

    # Extract nodes (pass hours filter)
    nodes, node_ids, node_metadata = extract_nodes(cur, hours_filter=hours_filter)

    # Generate edges using all methods
    all_edges = []
    edge_set = set()

    # 1. Metadata-based edges
    metadata_edges, edge_set = generate_metadata_edges(nodes, node_ids, node_metadata)
    all_edges.extend(metadata_edges)

    # 2. Temporal edges
    temporal_edges = generate_temporal_edges(node_ids, node_metadata, edge_set)
    all_edges.extend(temporal_edges)

    # 3. Similarity edges (vector-based)
    similarity_edges = generate_similarity_edges(cur, node_ids, node_metadata, edge_set)
    all_edges.extend(similarity_edges)

    # 4. Hub edges (structural)
    hub_edges = generate_hub_edges(nodes, edge_set)
    all_edges.extend(hub_edges)

    # 5. Contributor nodes and edges (optional)
    if include_contributors:
        contrib_nodes, contrib_edges = generate_contributor_nodes_and_edges(
            nodes, node_ids, node_metadata, edge_set
        )
        nodes.extend(contrib_nodes)
        all_edges.extend(contrib_edges)

    # 6. Hierarchy nodes and edges (Area -> Project -> Learning)
    if include_hierarchy:
        hierarchy_nodes, hierarchy_edges = generate_hierarchy_nodes_and_edges(
            nodes, node_ids, node_metadata, edge_set
        )
        nodes.extend(hierarchy_nodes)
        all_edges.extend(hierarchy_edges)

    # 7. Ingestion source nodes and edges
    if include_ingestion:
        ingestion_nodes, ingestion_edges = generate_ingestion_source_nodes_and_edges(
            cur, node_ids, node_metadata, edge_set
        )
        nodes.extend(ingestion_nodes)
        all_edges.extend(ingestion_edges)

    # 8. Get embedding backlog count
    embedding_backlog = get_embedding_backlog_count(cur)
    print(f"Embedding backlog: {embedding_backlog} pending")

    cur.close()
    conn.close()

    # Summary
    print(f"\n--- Edge Summary ---")
    edge_types = defaultdict(int)
    for e in all_edges:
        edge_types[e['type']] += 1
    for etype, count in sorted(edge_types.items(), key=lambda x: -x[1]):
        print(f"  {etype}: {count}")

    # Return additional metadata
    extra_metadata = {
        "embedding_backlog": embedding_backlog,
    }

    return nodes, all_edges, extra_metadata


def main():
    parser = argparse.ArgumentParser(description='Extract Zeus Memory data for visualization')
    parser.add_argument('--hours', type=int, default=0,
                       help='Filter to last N hours (0 = no filter, default)')
    parser.add_argument('--no-contributors', action='store_true',
                       help='Disable contributor nodes and edges (enabled by default)')
    parser.add_argument('--hierarchy', action='store_true',
                       help='Add Area/Project hierarchy nodes (Client vs R&D)')
    parser.add_argument('--no-ingestion', action='store_true',
                       help='Disable ingestion source nodes (enabled by default)')
    parser.add_argument('--output', type=str, default='data/examples/zeus_decisions.json',
                       help='Output file path')
    args = parser.parse_args()

    # Extract data with optional time filter
    # Contributors and ingestion enabled by default
    nodes, edges, extra_metadata = extract_data(
        hours_filter=args.hours,
        include_contributors=not args.no_contributors,
        include_hierarchy=args.hierarchy,
        include_ingestion=not args.no_ingestion
    )

    # Build visualization data
    data = {
        "metadata": {
            "title": "Zeus Memory Knowledge Graph",
            "description": "Knowledge graph of decisions, learnings, and relationships in Zeus Memory",
            "source": "zeus_core database",
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "edge_methods": ["metadata", "temporal", "similarity", "hub", "contributor", "hierarchy", "ingestion"],
            "hours_filter": args.hours if args.hours > 0 else "all",
            "contributors_enabled": not args.no_contributors,
            "hierarchy_enabled": args.hierarchy,
            "ingestion_enabled": not args.no_ingestion,
            "embedding_backlog": extra_metadata.get("embedding_backlog", 0),
        },
        "groups": GROUPS,
        "edge_types": EDGE_TYPES,
        "contributors": CONTRIBUTORS,
        "ingestion_sources": INGESTION_SOURCES,
        "nodes": nodes,
        "edges": edges
    }

    # Write output
    with open(args.output, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    print(f"\nGenerated {args.output}")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)}")
    print(f"  Groups: {list(GROUPS.keys())}")
    if args.hours > 0:
        print(f"  Time filter: Last {args.hours} hours")
    if not args.no_contributors:
        print(f"  Contributors: {list(CONTRIBUTORS.keys())}")


if __name__ == "__main__":
    main()
