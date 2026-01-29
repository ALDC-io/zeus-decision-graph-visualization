# Research Report: Improving Knowledge Graph Connectivity

## Problem Statement

The Zeus Decision Graph visualization currently has many disconnected nodes. Edges are created through:
1. Explicit `related_memory` metadata (rare)
2. Hardcoded hub connections (decisions → hub)
3. Artificial groupings (failed approaches ↔ successes)

This results in sparse connectivity that doesn't reflect the actual semantic relationships between memories.

---

## Approaches to Improve Connectivity

### 1. Semantic Similarity Edges (Vector-Based)

**Concept:** Use embeddings to find semantically similar nodes and create edges between them.

**How it works:**
- Each memory already has embeddings in Zeus (`embedding_voyage`, `embedding_bge`)
- Calculate cosine similarity between node embeddings
- Create edges where similarity exceeds a threshold (e.g., > 0.85)
- Edge weight = similarity score

**Implementation for Zeus:**
```sql
-- Find similar memories using pgvector
SELECT
  m1.memory_id as source,
  m2.memory_id as target,
  1 - (m1.embedding_voyage <=> m2.embedding_voyage) as similarity
FROM zeus_core.memories m1
JOIN zeus_core.memories m2 ON m1.memory_id < m2.memory_id
WHERE m1.tenant_id = 'tenant-id'
  AND m2.tenant_id = 'tenant-id'
  AND 1 - (m1.embedding_voyage <=> m2.embedding_voyage) > 0.85
LIMIT 500;
```

**Pros:**
- Uses existing infrastructure (pgvector)
- Discovers non-obvious relationships
- Quantifiable edge weights

**Cons:**
- Computationally expensive for large graphs
- May create too many edges (needs threshold tuning)
- Similarity ≠ meaningful relationship

**Research Support:**
- Amazon Neptune uses vector similarity for entity linking ([AWS Blog](https://aws.amazon.com/blogs/database/find-and-link-similar-entities-in-a-knowledge-graph-using-amazon-neptune-part-2-vector-similarity-search/))
- KGGen clusters similar nodes/edges to improve connectivity ([arXiv](https://arxiv.org/html/2502.09956v1))

---

### 2. Temporal Clustering

**Concept:** Connect nodes created around the same time, assuming temporal proximity implies contextual relationship.

**How it works:**
- Group memories by time windows (same day, same session, same hour)
- Create edges between nodes in same temporal cluster
- Edge type = "temporal_context" or "same_session"

**Implementation for Zeus:**
```sql
-- Find memories created within same session (1 hour window)
SELECT
  m1.memory_id as source,
  m2.memory_id as target,
  'temporal_context' as edge_type
FROM zeus_core.memories m1
JOIN zeus_core.memories m2
  ON m1.memory_id < m2.memory_id
  AND m1.created_at::date = m2.created_at::date
  AND ABS(EXTRACT(EPOCH FROM (m1.created_at - m2.created_at))) < 3600
WHERE m1.tenant_id = 'tenant-id'
  AND m2.tenant_id = 'tenant-id';
```

**Pros:**
- Simple to implement
- Captures session/workflow context
- Low computational cost

**Cons:**
- Temporal proximity doesn't guarantee semantic relationship
- May miss relationships across time

**Research Support:**
- Temporal Knowledge Graphs use dual-timestamp models for temporal reasoning ([Zep Architecture](https://www.emergentmind.com/topics/zep-a-temporal-knowledge-graph-architecture))
- Event-centric TKGs capture chronological sequences ([MDPI Survey](https://www.mdpi.com/2227-7390/11/23/4852))

---

### 3. LLM-Based Relationship Extraction

**Concept:** Use an LLM to analyze node content and extract explicit relationships.

**How it works:**
- Send pairs or batches of memory content to LLM
- Ask: "What is the relationship between these items?"
- LLM returns relationship type and confidence
- Create typed edges (references, contradicts, extends, implements, etc.)

**Implementation approach:**
```python
prompt = """
Given these two memories from a knowledge base, identify if there's a meaningful relationship:

Memory A: {content_a}
Memory B: {content_b}

If related, respond with:
- relationship_type: (references|extends|contradicts|implements|informs|supersedes)
- confidence: (0.0-1.0)
- reasoning: (brief explanation)

If not meaningfully related, respond: NO_RELATIONSHIP
"""
```

**Pros:**
- Extracts meaningful, typed relationships
- Can identify nuanced connections (contradictions, supersessions)
- Human-interpretable edge labels

**Cons:**
- Expensive (API costs for large graphs)
- Slow (can't process all pairs)
- Requires smart sampling strategy

**Research Support:**
- LLM-empowered KG construction is active research area ([arXiv Survey](https://arxiv.org/pdf/2510.20345))
- LKD-KGC uses LLM-based deduplication and schema integration ([ACM Survey](https://dl.acm.org/doi/10.1145/3618295))

---

### 4. Metadata-Based Relationships

**Concept:** Extract relationships from existing metadata fields.

**What to look for in Zeus metadata:**
- `related_memory` - explicit reference
- `category` - same category = related
- `source` - same source type = related workflow
- `agent_id` - same agent = same decision context
- `project` / `task` - same project = related work
- `tags` - shared tags = topical relationship

**Implementation:**
```sql
-- Connect by shared category
SELECT DISTINCT
  m1.memory_id as source,
  m2.memory_id as target,
  'same_category' as edge_type
FROM zeus_core.memories m1
JOIN zeus_core.memories m2
  ON m1.memory_id < m2.memory_id
  AND m1.metadata->>'category' = m2.metadata->>'category'
WHERE m1.tenant_id = 'tenant-id'
  AND m2.tenant_id = 'tenant-id'
  AND m1.metadata->>'category' IS NOT NULL;
```

**Pros:**
- Uses existing data
- Fast and deterministic
- No additional API costs

**Cons:**
- Limited by metadata quality/completeness
- May miss relationships not captured in metadata

---

### 5. Hybrid Approach (Recommended)

Combine multiple methods with different edge types and weights:

| Method | Edge Type | Weight | Use Case |
|--------|-----------|--------|----------|
| Vector similarity > 0.90 | `highly_similar` | similarity score | Core relationships |
| Vector similarity 0.80-0.90 | `related` | similarity score | Secondary relationships |
| Same category | `same_category` | 0.5 | Topical grouping |
| Same day + same source | `temporal_context` | 0.4 | Session context |
| Explicit metadata reference | `references` | 1.0 | Explicit links |
| LLM extraction (sampled) | varies | confidence | High-value edges |

**Filtering strategy:**
- Limit edges per node (max 10-15) to prevent visual clutter
- Prioritize by weight
- Keep explicit references always

---

## Implementation Recommendations for Zeus

### Phase 1: Quick Wins (Now)
1. Add category-based edges
2. Add temporal clustering (same-day, same-source)
3. Query existing `related_memory` metadata more thoroughly

### Phase 2: Vector Similarity (Short-term)
1. Use pgvector to find top-5 similar memories per node
2. Create edges for similarity > 0.85
3. Add edge weight to visualization (thicker = more similar)

### Phase 3: LLM Enrichment (Future)
1. Sample disconnected or weakly-connected nodes
2. Use LLM to identify relationship types
3. Store extracted relationships in metadata for future use

---

## Visualization Considerations

When displaying more edges:
- **Edge bundling** - group parallel edges
- **Edge filtering** - UI controls to show/hide edge types
- **Edge opacity** - fade weaker connections
- **Progressive disclosure** - show more edges on zoom/focus

---

## Sources

- [KGGen: Extracting Knowledge Graphs from Plain Text](https://arxiv.org/html/2502.09956v1)
- [AWS: Vector Similarity for Entity Linking](https://aws.amazon.com/blogs/database/find-and-link-similar-entities-in-a-knowledge-graph-using-amazon-neptune-part-2-vector-similarity-search/)
- [Event-Centric Temporal Knowledge Graph Construction Survey](https://www.mdpi.com/2227-7390/11/23/4852)
- [Zep: Temporal Knowledge Graph Architecture](https://www.emergentmind.com/topics/zep-a-temporal-knowledge-graph-architecture)
- [LLM-empowered Knowledge Graph Construction Survey](https://arxiv.org/pdf/2510.20345)
- [Automatic Knowledge Graph Construction Survey](https://dl.acm.org/doi/10.1145/3618295)
- [RP-ISS: Semantic and Structural Feature Integration](https://www.nature.com/articles/s41598-024-63279-2)
- [Neo4j: Future of Structured and Semantic Search](https://neo4j.com/blog/developer/knowledge-graph-structured-semantic-search/)

---

**Report Date:** 2026-01-28
**Project:** Zeus Decision Graph Visualization
**Status:** Research complete, ready for implementation decisions
