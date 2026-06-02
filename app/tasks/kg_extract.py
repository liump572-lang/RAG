import json
import re
import unicodedata
from datetime import datetime

from app.common.graph_store import (
    create_node as neo4j_create_node,
    create_relation as neo4j_create_relation,
    run_query,
)
from app.common.llm_client import chat
from app.database import SessionLocal
from app.config import settings
from app.models import (
    Document, DocumentChunk, KgExtractionRun, KgRebuild, KgSyncFailure,
    KnowledgePoint, KnowledgePointSource, KnowledgeRelation, Subject,
)
from app.tasks.celery_app import celery_app

BATCH_SIZE = 10
MAX_CHARS_PER_CHUNK = 1200
GLOBAL_REL_MAX_ENTITIES = 25
VALID_RELATION_TYPES = {
    "PREREQUISITE", "NEXT", "RELATED", "CONTAINS", "CONTRAST", "EXAMINED_IN",
}


@celery_app.task(name="kg_task.extract_knowledge", bind=True, max_retries=2, default_retry_delay=60)
def extract_knowledge_task(self, document_id: int, run_id: int = None):
    db = SessionLocal()
    run = None
    try:
        if not run_id:
            from app.common.schema_migrations import KG_REBUILD_VERSION
            run = KgExtractionRun(document_id=document_id, version=KG_REBUILD_VERSION, status="queued")
            db.add(run)
            db.commit()
            db.refresh(run)
            run_id = run.id
        if run_id:
            run = db.query(KgExtractionRun).filter(KgExtractionRun.id == run_id).first()
            if run:
                run.status = "running"
                run.model = settings.llm_model
                run.started_at = datetime.now()
                db.commit()
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc or doc.parse_status != "success":
            if run:
                run.status = "failed"
                run.error_msg = "document not parsed successfully"
                run.finished_at = datetime.now()
                db.commit()
                _update_rebuild_status(db, run.rebuild_id)
            return {"status": "skipped", "reason": "document not parsed successfully"}

        subject = db.query(Subject).filter(Subject.id == doc.subject_id).first()
        subject_name = subject.name if subject else "未知"

        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        if not chunks:
            if run:
                run.status = "failed"
                run.error_msg = "no chunks"
                run.finished_at = datetime.now()
                db.commit()
                _update_rebuild_status(db, run.rebuild_id)
            return {"status": "skipped", "reason": "no chunks"}

        total_chunks = len(chunks)
        if run:
            run.batch_count = (total_chunks + BATCH_SIZE - 1) // BATCH_SIZE
            db.commit()

        # ── Phase 1: Batch extract entities from chunks ──
        all_kps = []
        all_rels = []

        for batch_start in range(0, total_chunks, BATCH_SIZE):
            batch = chunks[batch_start:batch_start + BATCH_SIZE]
            batch_text = _build_batch_text(doc.title, batch, batch_start, total_chunks)
            try:
                response = _call_extract_entities(batch_text, subject_name)
                data = _parse_json_response(response)
                if data:
                    for kp in data.get("knowledge_points", []):
                        kp["_batch"] = f"{batch_start + 1}-{batch_start + len(batch)}"
                        kp["_chunk_id"] = batch[0].id if batch else None
                    all_kps.extend(data.get("knowledge_points", []))
                    all_rels.extend(data.get("relations", []))
            except Exception:
                # A malformed or transient batch must not discard the rest of a large document.
                pass
            if run:
                run.processed_batches = min(run.batch_count, run.processed_batches + 1)
                db.commit()

        if not all_kps:
            result = {"status": "completed", "knowledge_points_created": 0, "relations_created": 0, "reason": "no entities extracted"}
            _finish_run(db, run, result)
            return result

        # ── Phase 2: Merge & deduplicate entities across batches ──
        merged_kps, merged_rels = _merge_entities(all_kps, all_rels, doc.title, subject_name)

        # ── Phase 2.5: Global relationship inference ──
        # Find relationships between entities extracted from different batches
        if len(merged_kps) >= 2:
            global_rels = _infer_global_relationships(merged_kps, doc.title, subject_name)
            merged_rels.extend(global_rels)
            # Deduplicate again
            merged_rels = _dedup_relations(merged_rels)

        # ── Phase 3: Store in DB and Neo4j ──
        name_to_id = _store_knowledge_points(db, merged_kps, doc.subject_id, doc.id)

        rel_count = _store_relations(db, merged_rels, name_to_id)

        # ── Phase 4: Cross-document linking ──
        cross_links = _link_to_existing_graph(db, merged_kps, name_to_id, doc.subject_id)
        rel_count += cross_links

        result = {
            "status": "success",
            "knowledge_points_created": len(name_to_id),
            "relations_created": rel_count,
            "cross_document_links": cross_links,
            "batches_processed": (total_chunks + BATCH_SIZE - 1) // BATCH_SIZE,
        }
        _finish_run(db, run, result)
        return result

    except Exception as e:
        db.rollback()
        if run_id:
            run = db.query(KgExtractionRun).filter(KgExtractionRun.id == run_id).first()
            if run:
                run.status = "failed"
                run.error_msg = str(e)[:1000]
                run.finished_at = datetime.now()
                db.commit()
                _update_rebuild_status(db, run.rebuild_id)
        return {"status": "failed", "reason": str(e)}
    finally:
        db.close()


def _build_batch_text(doc_title: str, batch: list, batch_start: int, total: int) -> str:
    parts = []
    for c in batch:
        chunk_idx = c.chunk_index
        content = c.content[:MAX_CHARS_PER_CHUNK]
        parts.append(f"[段落{chunk_idx + 1}/{total}]\n{content}")

    return (
        f"文档标题：{doc_title}\n"
        f"处理批次：段落 {batch_start + 1} - {batch_start + len(batch)} / {total}\n\n"
        + "\n\n---\n\n".join(parts)
    )


def _call_extract_entities(batch_text: str, subject_name: str) -> str:
    prompt = f"""你是一个知识抽取专家。请从以下文档片段中提取核心知识点和它们之间的关系。

所属科目：{subject_name}

文档内容：
{batch_text}

请提取出该片段中涵盖的核心知识点和它们之间的关系。
要求：
1. 知识点名称应简洁、准确（2-20字），提取具体的概念、术语、算法、定理等
2. 每个知识点给出简要描述（30-150字）
3. 难度等级1-5（1最简单，5最难），根据概念的抽象程度和复杂度判断
4. 关系类型只能是以下之一：PREREQUISITE（前置条件）、NEXT（后继）、RELATED（关联）、CONTAINS（包含）、CONTRAST（对比）、EXAMINED_IN（考点）
5. 仔细发现所有知识点之间的关联，包括：
   - 概念A是学习概念B的前置知识（PREREQUISITE）
   - 概念B是概念A的后续延伸（NEXT）
   - 概念A包含子概念B（CONTAINS）
   - 概念A和概念B互相对比/对立（CONTRAST）
   - 概念A和概念B在相关领域有关联（RELATED）
   - 概念A是考试中常考的知识点（EXAMINED_IN）
6. 只提取文档中明确出现的知识点，不要凭空编造
7. 尽量识别标准术语的全称和缩写（如"卷积神经网络（CNN）"）
8. 为每个知识点返回 aliases（别名数组）、evidence（原文依据）和 confidence（0-1）

请严格按照以下JSON格式返回，不要包含markdown代码块标记：
{{
  "knowledge_points": [
    {{"name": "知识点名称", "aliases": ["缩写或别名"], "description": "知识点描述", "difficulty": 3, "evidence": "原文依据", "confidence": 0.85}}
  ],
  "relations": [
    {{"source": "源知识点名称", "target": "目标知识点名称", "type": "RELATED", "description": "关系描述"}}
  ]
}}"""

    return chat(
        messages=[
            {"role": "system", "content": "你是一个知识抽取专家，只返回纯JSON，不要包含markdown代码块标记。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=4096,
    )


def _merge_entities(all_kps: list, all_rels: list, doc_title: str, subject_name: str) -> tuple:
    """Merge and deduplicate entities across batches."""
    if not all_kps:
        return [], []

    seen_names = {}
    canonical_names = {}
    unique_kps = []
    for kp in all_kps:
        name = kp.get("name", "").strip()
        if not name or len(name) > 100:
            continue
        normalized = _normalize_entity_name(name)
        aliases = [alias.strip() for alias in kp.get("aliases", []) if isinstance(alias, str) and alias.strip()]
        matched = seen_names.get(normalized)
        if not matched:
            matched = next((seen_names.get(_normalize_entity_name(alias)) for alias in aliases if seen_names.get(_normalize_entity_name(alias))), None)
        if not matched:
            kp["name"] = name
            seen_names[normalized] = kp
            for alias in aliases:
                seen_names[_normalize_entity_name(alias)] = kp
            canonical_names[name] = name
            unique_kps.append(kp)
        else:
            existing = matched
            canonical_names[name] = existing["name"]
            if len(kp.get("description", "")) > len(existing.get("description", "")):
                existing["description"] = kp["description"]
            if kp.get("difficulty") and not existing.get("difficulty"):
                existing["difficulty"] = kp["difficulty"]
            existing["aliases"] = sorted(set(existing.get("aliases", []) + kp.get("aliases", []) + [name]))
            for alias in existing["aliases"]:
                seen_names[_normalize_entity_name(alias)] = existing

    for rel in all_rels:
        rel["source"] = canonical_names.get(rel.get("source", "").strip(), rel.get("source", "").strip())
        rel["target"] = canonical_names.get(rel.get("target", "").strip(), rel.get("target", "").strip())

    if len(unique_kps) > 40:
        unique_kps, all_rels = _llm_merge_entities(unique_kps, all_rels, doc_title, subject_name)

    unique_rels = _dedup_relations(all_rels)
    return unique_kps, unique_rels


def _normalize_entity_name(name: str) -> str:
    text = unicodedata.normalize("NFKC", name or "").strip().lower()
    text = re.sub(r"[\s·_\-]+", "", text)
    return re.sub(r"[()（）\[\]【】]", "", text)


def _dedup_relations(rels: list) -> list:
    """Deduplicate relations by (source, target, type)."""
    seen = set()
    unique = []
    for rel in rels:
        source = rel.get("source", "").strip()
        target = rel.get("target", "").strip()
        rel_type = rel.get("type", "RELATED").strip().upper()
        if not source or not target or source == target or rel_type not in VALID_RELATION_TYPES:
            continue
        rel["source"] = source
        rel["target"] = target
        rel["type"] = rel_type
        key = (source, target, rel_type)
        if key not in seen:
            seen.add(key)
            unique.append(rel)
    return unique


def _infer_global_relationships(kps: list, doc_title: str, subject_name: str) -> list:
    """
    Use LLM to infer relationships between ALL extracted entities.
    This catches cross-batch connections that were missed in Phase 1.
    """
    if len(kps) < 2:
        return []

    # Sample the complete document evenly so basic concepts are not dropped.
    if len(kps) > GLOBAL_REL_MAX_ENTITIES:
        step = len(kps) / GLOBAL_REL_MAX_ENTITIES
        selected_kps = [kps[int(index * step)] for index in range(GLOBAL_REL_MAX_ENTITIES)]
    else:
        selected_kps = kps

    kp_text = "\n".join(
        f"{i+1}. {kp['name']}：{kp.get('description', '')}"
        for i, kp in enumerate(selected_kps)
    )

    prompt = f"""你是一个知识体系构建专家。以下是同一篇文档中提取出的所有知识点，它们来自文档的不同章节，请找出它们之间可能存在的关联关系。

文档标题：{doc_title}
所属科目：{subject_name}

知识点列表：
{kp_text}

请分析以上知识点之间的逻辑关系。注意：知识点来自文档的不同部分，有些关联可能是隐含的、跨章节的。
要求：
1. 仔细分析每对知识点之间的可能关系
2. 关系类型：PREREQUISITE（前置）、NEXT（后继）、RELATED（关联）、CONTAINS（包含）、CONTRAST（对比）、EXAMINED_IN（考点）
3. 只保留有明确语义依据的关系；没有可靠联系时不要为了数量强行添加
4. 只返回确实存在的关系，不要编造不存在的关联
5. 关系描述应简洁说明两个知识点之间的具体联系（10-40字）

请严格按照以下JSON格式返回：
{{
  "relations": [
    {{"source": "知识点A名称", "target": "知识点B名称", "type": "PREREQUISITE", "description": "A是学习B的基础"}}
  ]
}}"""

    response = chat(
        messages=[
            {"role": "system", "content": "你是一个知识体系构建专家，只返回纯JSON，不要包含markdown代码块标记。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    data = _parse_json_response(response)
    if data:
        return data.get("relations", [])
    return []


def _llm_merge_entities(kps: list, rels: list, doc_title: str, subject_name: str) -> tuple:
    """Use LLM to merge and consolidate entities when there are many."""
    kp_text = "\n".join(
        f"- {kp['name']}：{kp.get('description', '')}（难度{kp.get('difficulty', 3)}）"
        for kp in kps
    )
    rel_text = "\n".join(
        f"- {r['source']} → {r['target']}（{r.get('type', 'RELATED')}）"
        for r in rels
    )

    prompt = f"""你是一个知识体系整理专家。请对以下从文档中提取的知识点和关系进行合并去重。

文档标题：{doc_title}
所属科目：{subject_name}

当前知识点（共{len(kps)}个）：
{kp_text}

当前关系（共{len(rels)}个）：
{rel_text}

要求：
1. 合并名称不同但指向同一概念的知识点（如"CNN"和"卷积神经网络"应该合并）
2. 保留更规范、更标准的名称作为合并后的名称
3. 合并后知识点不超过30个
4. 更新关系中的知识点名称以匹配合并后的名称
5. 删除重复或无意义的关系

请按照以下JSON格式返回合并后的结果：
{{
  "knowledge_points": [
    {{"name": "规范名称", "description": "合并后的描述", "difficulty": 3}}
  ],
  "relations": [
    {{"source": "源知识点", "target": "目标知识点", "type": "RELATED", "description": "关系描述"}}
  ]
}}"""

    response = chat(
        messages=[
            {"role": "system", "content": "你是一个知识体系整理专家，只返回纯JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=4096,
    )

    data = _parse_json_response(response)
    if data:
        return data.get("knowledge_points", kps), data.get("relations", rels)
    return kps, rels


def _store_knowledge_points(db, kps: list, subject_id: int, document_id: int = None) -> dict:
    """Store knowledge points in MySQL and Neo4j. Returns name→id mapping."""
    name_to_id = {}
    existing_by_normalized_name = {
        _normalize_entity_name(point.name): point
        for point in db.query(KnowledgePoint).filter(KnowledgePoint.subject_id == subject_id).all()
    }

    for kp in kps:
        name = kp.get("name", "").strip()
        if not name:
            continue

        normalized_name = _normalize_entity_name(name)
        existing = existing_by_normalized_name.get(normalized_name)

        if existing:
            name_to_id[name] = existing.id
            if kp.get("description") and not existing.description:
                existing.description = kp.get("description")
                db.commit()
            try:
                neo4j_create_node(existing.id, existing.name, existing.subject_id)
            except Exception as exc:
                _record_sync_failure(db, "upsert", "node", existing.id, {"name": existing.name}, exc)
            _store_source(db, existing.id, document_id, kp, existing.name)
            continue

        point = KnowledgePoint(
            name=name,
            subject_id=subject_id,
            description=kp.get("description", ""),
            difficulty=kp.get("difficulty", 3),
            origin="auto",
            confidence=_safe_confidence(kp.get("confidence")),
            review_status="pending",
        )
        db.add(point)
        db.commit()
        db.refresh(point)

        try:
            neo4j_create_node(point.id, point.name, point.subject_id)
        except Exception as exc:
            _record_sync_failure(db, "upsert", "node", point.id, {"name": point.name}, exc)

        name_to_id[name] = point.id
        existing_by_normalized_name[normalized_name] = point
        _store_source(db, point.id, document_id, kp, point.name)

    return name_to_id


def _store_relations(db, rels: list, name_to_id: dict) -> int:
    """Store relations in MySQL and Neo4j."""
    count = 0
    for rel in rels:
        src_name = rel.get("source", "").strip()
        tgt_name = rel.get("target", "").strip()
        src_id = name_to_id.get(src_name)
        tgt_id = name_to_id.get(tgt_name)
        if not src_id or not tgt_id or src_id == tgt_id:
            continue

        rel_type = rel.get("type", "RELATED").strip().upper()
        if rel_type not in VALID_RELATION_TYPES:
            continue
        rel_desc = rel.get("description", "")

        existing_rel = (
            db.query(KnowledgeRelation)
            .filter(
                KnowledgeRelation.source_node_id == src_id,
                KnowledgeRelation.target_node_id == tgt_id,
                KnowledgeRelation.relation_type == rel_type,
            )
            .first()
        )
        if existing_rel:
            try:
                neo4j_create_relation(src_id, tgt_id, rel_type, rel_desc)
            except Exception as exc:
                _record_sync_failure(db, "upsert", "relation", existing_rel.id, rel, exc)
            continue

        relation = KnowledgeRelation(
            source_node_id=src_id,
            target_node_id=tgt_id,
            relation_type=rel_type,
            description=rel_desc,
            origin="auto",
            confidence=_safe_confidence(rel.get("confidence")),
            review_status="pending",
        )
        db.add(relation)
        db.commit()
        try:
            neo4j_create_relation(src_id, tgt_id, rel_type, rel_desc)
        except Exception as exc:
            _record_sync_failure(db, "upsert", "relation", relation.id, rel, exc)
        count += 1

    return count


def _link_to_existing_graph(db, new_kps: list, name_to_id: dict, subject_id: int) -> int:
    """
    Link newly extracted entities to existing knowledge graph nodes
    in the same subject using LLM-based relationship discovery.
    """
    if len(new_kps) < 1:
        return 0

    from app.models import KnowledgePoint

    # Get existing entities in the same subject (excluding the ones just created)
    new_ids = set(name_to_id.values())
    existing_kps = (
        db.query(KnowledgePoint)
        .filter(
            KnowledgePoint.subject_id == subject_id,
            ~KnowledgePoint.id.in_(new_ids),
        )
        .limit(120)
        .all()
    )

    if not existing_kps:
        return 0

    for point in existing_kps:
        try:
            neo4j_create_node(point.id, point.name, point.subject_id)
        except Exception as exc:
            _record_sync_failure(db, "upsert", "node", point.id, {"name": point.name}, exc)

    # Select a sample of new entities to link (top by difficulty)
    sorted_new = sorted(new_kps, key=lambda k: k.get("difficulty", 3), reverse=True)
    sample_new = sorted_new[:20]

    new_text = "\n".join(
        f"- {kp['name']}：{kp.get('description', '')}"
        for kp in sample_new
    )
    existing_text = "\n".join(
        f"- {kp.name}：{kp.description or ''}"
        for kp in existing_kps[:80]
    )

    prompt = f"""你是一个知识图谱构建专家。请找出新提取的知识点和已有知识点之间的关联关系。

新知识点：
{new_text}

已有知识点：
{existing_text}

要求：
1. 只找出确实存在语义关联的知识点对
2. 关系类型：PREREQUISITE（前置）、NEXT（后继）、RELATED（关联）、CONTAINS（包含）、CONTRAST（对比）、EXAMINED_IN（考点）
3. 关系描述应简洁说明具体联系（10-30字）
4. 知识点名称必须和上面列出的完全一致（一字不差）

请按JSON格式返回：
{{
  "relations": [
    {{"source": "已有知识点名称（必须是已有列表中的）", "target": "新知识点名称（必须是新列表中的）", "type": "RELATED", "description": "关系描述"}}
  ]
}}"""

    response = chat(
        messages=[
            {"role": "system", "content": "你是一个知识图谱构建专家，只返回纯JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    data = _parse_json_response(response)
    if not data:
        return 0

    relations = data.get("relations", [])
    # Build lookup: existing entity name → id
    existing_name_to_id = {kp.name: kp.id for kp in existing_kps}

    count = 0
    for rel in relations:
        src_name = rel.get("source", "").strip()
        tgt_name = rel.get("target", "").strip()
        src_id = existing_name_to_id.get(src_name)
        tgt_id = name_to_id.get(tgt_name)

        if not src_id or not tgt_id or src_id == tgt_id:
            # Try reversed: source might be new, target might be existing
            src_id = name_to_id.get(src_name)
            tgt_id = existing_name_to_id.get(tgt_name)

        if not src_id or not tgt_id or src_id == tgt_id:
            continue

        rel_type = rel.get("type", "RELATED").strip().upper()
        if rel_type not in VALID_RELATION_TYPES:
            continue
        rel_desc = rel.get("description", "")

        existing_rel = (
            db.query(KnowledgeRelation)
            .filter(
                KnowledgeRelation.source_node_id == src_id,
                KnowledgeRelation.target_node_id == tgt_id,
                KnowledgeRelation.relation_type == rel_type,
            )
            .first()
        )
        if existing_rel:
            try:
                neo4j_create_relation(src_id, tgt_id, rel_type, rel_desc)
            except Exception as exc:
                _record_sync_failure(db, "upsert", "relation", existing_rel.id, rel, exc)
            continue

        relation = KnowledgeRelation(
            source_node_id=src_id,
            target_node_id=tgt_id,
            relation_type=rel_type,
            description=rel_desc,
            origin="auto",
            confidence=_safe_confidence(rel.get("confidence")),
            review_status="pending",
        )
        db.add(relation)
        db.commit()
        try:
            neo4j_create_relation(src_id, tgt_id, rel_type, rel_desc)
        except Exception as exc:
            _record_sync_failure(db, "upsert", "relation", relation.id, rel, exc)
        count += 1

    return count


def _parse_json_response(text: str) -> dict:
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group()
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return None
        if "knowledge_points" in data and not isinstance(data["knowledge_points"], list):
            return None
        if "relations" in data and not isinstance(data["relations"], list):
            return None
        return data
    except json.JSONDecodeError:
        return None


def _safe_confidence(value, default: float = 0.8) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def _store_source(db, point_id: int, document_id: int, kp: dict, canonical_name: str):
    if not document_id:
        return
    source = KnowledgePointSource(
        knowledge_point_id=point_id,
        document_id=document_id,
        chunk_id=kp.get("_chunk_id"),
        raw_name=kp.get("name", canonical_name)[:100],
        canonical_name=canonical_name[:100],
        evidence_text=(kp.get("evidence") or kp.get("description") or "")[:1000],
        extraction_batch=kp.get("_batch"),
        confidence=_safe_confidence(kp.get("confidence")),
    )
    db.add(source)
    db.commit()


def _record_sync_failure(db, operation: str, entity_type: str, entity_id: int, payload: dict, error: Exception):
    db.add(KgSyncFailure(
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        payload=payload,
        error_msg=str(error)[:1000],
    ))
    db.commit()


def _finish_run(db, run: KgExtractionRun, result: dict):
    if not run:
        return
    run.status = "success"
    run.entity_count = result.get("knowledge_points_created", 0)
    run.relation_count = result.get("relations_created", 0)
    run.finished_at = datetime.now()
    db.commit()
    _update_rebuild_status(db, run.rebuild_id)
    from app.tasks.kg_rebuild import retry_neo4j_sync_task
    retry_neo4j_sync_task.delay()


def _update_rebuild_status(db, rebuild_id: int):
    if not rebuild_id:
        return
    rebuild = db.query(KgRebuild).filter(KgRebuild.id == rebuild_id).first()
    if not rebuild:
        return
    runs = db.query(KgExtractionRun).filter(KgExtractionRun.rebuild_id == rebuild_id).all()
    rebuild.completed_documents = sum(run.status == "success" for run in runs)
    rebuild.failed_documents = sum(run.status == "failed" for run in runs)
    if rebuild.completed_documents + rebuild.failed_documents >= rebuild.total_documents:
        rebuild.status = "partial_failed" if rebuild.failed_documents else "success"
        rebuild.finished_at = datetime.now()
    db.commit()
