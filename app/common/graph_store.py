from typing import Optional

from neo4j import GraphDatabase

from app.config import settings


_driver = None


def get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    return _driver


def run_query(query: str, params: dict = None):
    with get_driver().session() as session:
        result = session.run(query, params or {})
        return [r.data() for r in result]


def create_node(node_id: int, name: str, subject_id: int, labels: list = None) -> dict:
    results = run_query(
        """
        MERGE (n:KnowledgePoint {id: $id})
        SET n.name = $name, n.subject_id = $subject_id
        RETURN n.id as id, n.name as name, n.subject_id as subject_id
        """,
        {"id": node_id, "name": name, "subject_id": subject_id},
    )
    return results[0] if results else {}


def update_node(node_id: int, name: str = None, description: str = None) -> bool:
    sets = []
    params = {"id": node_id}
    if name is not None:
        sets.append("n.name = $name")
        params["name"] = name
    if description is not None:
        sets.append("n.description = $description")
        params["description"] = description
    if not sets:
        return False
    set_clause = ", ".join(sets)
    run_query(f"MATCH (n:KnowledgePoint {{id: $id}}) SET {set_clause} RETURN n", params)
    return True


def delete_node(node_id: int) -> bool:
    run_query(
        "MATCH (n:KnowledgePoint {id: $id}) DETACH DELETE n",
        {"id": node_id},
    )
    return True


def create_relation(
    source_id: int, target_id: int, rel_type: str,
    description: str = None,
) -> dict:
    results = run_query(
        """
        MATCH (a:KnowledgePoint {id: $source_id})
        MATCH (b:KnowledgePoint {id: $target_id})
        MERGE (a)-[r:RELATED {type: $rel_type}]->(b)
        SET r.type = $rel_type
        SET r.description = $description
        RETURN id(r) as rel_id, a.id as source_id, b.id as target_id, r.type as type
        """,
        {"source_id": source_id, "target_id": target_id, "rel_type": rel_type, "description": description or ""},
    )
    return results[0] if results else {}


def delete_relation(source_id: int, target_id: int, rel_type: str) -> bool:
    run_query(
        """
        MATCH (a:KnowledgePoint {id: $source_id})-[r:RELATED {type: $rel_type}]->(b:KnowledgePoint {id: $target_id})
        DELETE r
        """,
        {"source_id": source_id, "target_id": target_id, "rel_type": rel_type},
    )
    return True


def get_subgraph(subject_id: int = None, depth: int = 2) -> dict:
    if subject_id:
        query = """
            MATCH (n:KnowledgePoint)
            WHERE n.subject_id = $subject_id
            OPTIONAL MATCH (n)-[r:RELATED]-(m:KnowledgePoint)
            RETURN collect(DISTINCT {id: n.id, name: n.name, subject_id: n.subject_id, difficulty: n.difficulty}) as nodes,
                   collect(DISTINCT {source_id: r.type}) as rels
        """
        params = {"subject_id": subject_id}
    else:
        query = """
            MATCH (n:KnowledgePoint)
            OPTIONAL MATCH (n)-[r:RELATED]-(m:KnowledgePoint)
            RETURN collect(DISTINCT {id: n.id, name: n.name, subject_id: n.subject_id}) as nodes,
                   collect(DISTINCT {}) as rels
        """
        params = {}

    results = run_query(query, params)
    if not results:
        return {"nodes": [], "edges": []}

    data = results[0]
    nodes = {}
    edges = []
    seen = set()

    for n in data.get("nodes", []):
        if n.get("id") and n["id"] not in nodes:
            nodes[n["id"]] = {
                "id": n["id"],
                "label": n.get("name", ""),
                "subject_id": n.get("subject_id"),
                "group": str(n.get("subject_id", 0)),
            }

    edge_query = """
        MATCH (a:KnowledgePoint)-[r:RELATED]->(b:KnowledgePoint)
    """
    if subject_id:
        edge_query += " WHERE a.subject_id = $subject_id OR b.subject_id = $subject_id"
    edge_query += " RETURN a.id as source, b.id as target, r.type as type, r.description as description"
    edge_query += " LIMIT 200"

    edge_results = run_query(edge_query, {"subject_id": subject_id} if subject_id else {})
    for e in edge_results:
        if e.get("source") and e.get("target"):
            edge_key = f"{e['source']}-{e['target']}-{e.get('type', '')}"
            if edge_key not in seen:
                seen.add(edge_key)
                edges.append({
                    "from": e["source"],
                    "to": e["target"],
                    "label": e.get("type", ""),
                    "title": e.get("description", ""),
                })
            if e["source"] not in nodes:
                nodes[e["source"]] = {"id": e["source"], "label": str(e["source"]), "group": "0"}
            if e["target"] not in nodes:
                nodes[e["target"]] = {"id": e["target"], "label": str(e["target"]), "group": "0"}

    return {"nodes": list(nodes.values()), "edges": edges}


def search_nodes(keyword: str, subject_id: int = None) -> list:
    conditions = ["n.name CONTAINS $keyword"]
    params = {"keyword": keyword}
    if subject_id:
        conditions.append("n.subject_id = $subject_id")
        params["subject_id"] = subject_id

    where_clause = " AND ".join(conditions)
    query = f"""
        MATCH (n:KnowledgePoint)
        WHERE {where_clause}
        RETURN n.id as id, n.name as name, n.subject_id as subject_id
        LIMIT 20
    """
    return run_query(query, params)


def get_search_subgraph(keyword: str, subject_id: int = None, depth: int = 1) -> dict:
    ids_param = {"keyword": f"%{keyword}%"}
    id_conditions = ["n.name CONTAINS $keyword"]
    if subject_id:
        id_conditions.append("n.subject_id = $subject_id")
        ids_param["subject_id"] = subject_id
    id_where = " AND ".join(id_conditions)

    matched = run_query(f"""
        MATCH (n:KnowledgePoint)
        WHERE {id_where}
        RETURN n.id as id, n.name as name, n.subject_id as subject_id
        LIMIT 20
    """, ids_param)

    if not matched:
        return {"nodes": [], "edges": []}

    matched_ids = [n["id"] for n in matched]

    neighbors = run_query("""
        MATCH (n:KnowledgePoint)-[r:RELATED]-(m:KnowledgePoint)
        WHERE n.id IN $ids
        RETURN DISTINCT m.id as id, m.name as name, m.subject_id as subject_id
        LIMIT 50
    """, {"ids": matched_ids})

    all_edges = run_query("""
        MATCH (a:KnowledgePoint)-[r:RELATED]->(b:KnowledgePoint)
        WHERE a.id IN $ids OR b.id IN $ids
        RETURN DISTINCT a.id as source, b.id as target, r.type as type
        LIMIT 100
    """, {"ids": matched_ids})

    nodes_map = {}
    for n in matched + neighbors:
        nid = n.get("id")
        if nid is not None and nid not in nodes_map:
            nodes_map[nid] = {
                "id": nid,
                "label": n.get("name", ""),
                "subject_id": n.get("subject_id"),
                "group": str(n.get("subject_id", 0)),
            }

    edges = []
    seen = set()
    for e in all_edges:
        src, tgt = e.get("source"), e.get("target")
        if src is None or tgt is None:
            continue
        key = f"{src}-{tgt}-{e.get('type', '')}"
        if key not in seen:
            seen.add(key)
            edges.append({
                "from": src,
                "to": tgt,
                "label": e.get("type", ""),
                "title": e.get("type", ""),
            })
            if src not in nodes_map:
                nodes_map[src] = {"id": src, "label": str(src), "group": "0"}
            if tgt not in nodes_map:
                nodes_map[tgt] = {"id": tgt, "label": str(tgt), "group": "0"}

    return {"nodes": list(nodes_map.values()), "edges": edges}


def close():
    global _driver
    if _driver:
        _driver.close()
        _driver = None
