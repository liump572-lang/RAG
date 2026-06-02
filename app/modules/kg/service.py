import os
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.common.graph_store import (
    create_node as neo4j_create_node,
    create_relation as neo4j_create_relation,
    delete_node as neo4j_delete_node,
    delete_relation as neo4j_delete_relation,
    get_search_subgraph as neo4j_get_search_subgraph,
    get_subgraph as neo4j_get_subgraph,
    search_nodes as neo4j_search_nodes,
    update_node as neo4j_update_node,
)
from app.common.llm_client import chat
from app.config import settings
from app.models import Document, KnowledgePoint, KnowledgeRelation, Subject


class KgService:

    @staticmethod
    def create_point(db: Session, name: str, subject_id: int, description: str = None, difficulty: int = 3) -> KnowledgePoint:
        point = KnowledgePoint(name=name, subject_id=subject_id, description=description, difficulty=difficulty)
        db.add(point)
        db.commit()
        db.refresh(point)

        try:
            neo4j_create_node(point.id, point.name, point.subject_id)
        except Exception:
            pass

        return point

    @staticmethod
    def update_point(db: Session, point_id: int, name: str = None, description: str = None, difficulty: int = None) -> Optional[KnowledgePoint]:
        point = db.query(KnowledgePoint).filter(KnowledgePoint.id == point_id).first()
        if not point:
            return None
        if name is not None:
            point.name = name
        if description is not None:
            point.description = description
        if difficulty is not None:
            point.difficulty = difficulty
        db.commit()
        db.refresh(point)

        try:
            neo4j_update_node(point.id, point.name, point.description)
        except Exception:
            pass

        return point

    @staticmethod
    def delete_point(db: Session, point_id: int) -> bool:
        point = db.query(KnowledgePoint).filter(KnowledgePoint.id == point_id).first()
        if not point:
            return False
        db.query(KnowledgeRelation).filter(
            (KnowledgeRelation.source_node_id == point_id) | (KnowledgeRelation.target_node_id == point_id)
        ).delete()
        db.delete(point)
        db.commit()

        try:
            neo4j_delete_node(point_id)
        except Exception:
            pass

        return True

    @staticmethod
    def list_points(db: Session, subject_id: int = None, keyword: str = None, page: int = 1, size: int = 20):
        query = db.query(KnowledgePoint)
        if subject_id:
            query = query.filter(KnowledgePoint.subject_id == subject_id)
        if keyword:
            query = query.filter(KnowledgePoint.name.like(f"%{keyword}%"))
        total = query.count()
        items = query.order_by(KnowledgePoint.id).offset((page - 1) * size).limit(size).all()
        return items, total

    @staticmethod
    def get_point(db: Session, point_id: int) -> Optional[KnowledgePoint]:
        return db.query(KnowledgePoint).filter(KnowledgePoint.id == point_id).first()

    @staticmethod
    def create_relation(db: Session, source_id: int, target_id: int, relation_type: str, description: str = None) -> Optional[KnowledgeRelation]:
        source = db.query(KnowledgePoint).filter(KnowledgePoint.id == source_id).first()
        target = db.query(KnowledgePoint).filter(KnowledgePoint.id == target_id).first()
        if not source or not target or source.id == target.id or source.subject_id != target.subject_id:
            return None

        existing = db.query(KnowledgeRelation).filter(
            KnowledgeRelation.source_node_id == source_id,
            KnowledgeRelation.target_node_id == target_id,
            KnowledgeRelation.relation_type == relation_type,
        ).first()
        if existing:
            try:
                neo4j_create_node(source.id, source.name, source.subject_id)
                neo4j_create_node(target.id, target.name, target.subject_id)
                neo4j_create_relation(source_id, target_id, relation_type, description or existing.description)
            except Exception:
                pass
            return existing

        rel = KnowledgeRelation(
            source_node_id=source_id,
            target_node_id=target_id,
            relation_type=relation_type,
            description=description,
        )
        db.add(rel)
        db.commit()
        db.refresh(rel)

        try:
            neo4j_create_node(source.id, source.name, source.subject_id)
            neo4j_create_node(target.id, target.name, target.subject_id)
            neo4j_create_relation(source_id, target_id, relation_type, description)
        except Exception:
            pass

        return rel

    @staticmethod
    def delete_relation(db: Session, relation_id: int) -> bool:
        rel = db.query(KnowledgeRelation).filter(KnowledgeRelation.id == relation_id).first()
        if not rel:
            return False
        db.delete(rel)
        db.commit()

        try:
            neo4j_delete_relation(rel.source_node_id, rel.target_node_id, rel.relation_type)
        except Exception:
            pass

        return True

    @staticmethod
    def list_relations(db: Session, subject_id: int = None) -> list:
        query = db.query(KnowledgeRelation)
        if subject_id:
            query = query.join(
                KnowledgePoint,
                KnowledgeRelation.source_node_id == KnowledgePoint.id,
            ).filter(KnowledgePoint.subject_id == subject_id)
        return query.all()

    @staticmethod
    def get_subgraph(subject_id: int = None, depth: int = 2) -> dict:
        try:
            return neo4j_get_subgraph(subject_id, depth)
        except Exception as e:
            return {"nodes": [], "edges": [], "error": str(e)}

    @staticmethod
    def search_subgraph(keyword: str, subject_id: int = None) -> dict:
        try:
            return neo4j_get_search_subgraph(keyword, subject_id, depth=1)
        except Exception as e:
            return {"nodes": [], "edges": [], "error": str(e)}

    @staticmethod
    def search(keyword: str, subject_id: int = None) -> list:
        try:
            return neo4j_search_nodes(keyword, subject_id)
        except Exception:
            return []

    @staticmethod
    def generate_document(db: Session, subject_id: int, doc_type: str) -> Document:
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            raise ValueError("科目不存在")

        kg_data = neo4j_get_subgraph(subject_id)
        nodes = kg_data.get("nodes", [])
        edges = kg_data.get("edges", [])

        from app.common.vector_store import search_chunks
        chunk_results = search_chunks(subject.name, top_k=30, where={"subject_id": subject_id})

        nodes_text = "\n".join(
            f"- {n.get('label', '')} (ID: {n.get('id', '')})"
            for n in nodes[:50]
        ) if nodes else "暂无知识点"

        edges_text = "\n".join(
            f"- {e.get('from', '')} --[{e.get('label', '')}]--> {e.get('to', '')}"
            for e in edges[:80]
        ) if edges else "暂无关系"

        chunks_text = "\n\n".join(
            c.get("content", "") for c in chunk_results[:15]
        ) if chunk_results else "暂无相关文档内容"

        doc_type_labels = {
            "study_guide": ("学习指南", "supplement"),
            "exam_paper": ("考试试卷", "exam"),
            "summary": ("知识总结", "note"),
            "outline": ("教学大纲", "textbook"),
        }
        label, db_doc_type = doc_type_labels.get(doc_type, ("学习指南", "supplement"))

        system_prompt = """你是一个专业的教育文档生成助手。
根据提供的知识图谱（知识点和关系）以及相关文档内容，生成一份结构清晰、内容详实的Markdown文档。
文档应当包含：
1. 标题和概述
2. 知识结构（按关系组织，体现知识点之间的关联）
3. 每个知识点的详细说明
4. 总结或思考题

要求：
- 使用中文
- 使用Markdown格式（标题、列表、表格、代码块等）
- 内容专业、准确
- 不少于1000字"""

        user_prompt = f"""请为科目「{subject.name}」生成一份{label}。

## 知识图谱数据

### 知识点（共{len(nodes)}个）
{nodes_text}

### 知识点关系（共{len(edges)}条）
{edges_text}

## 相关文档内容
{chunks_text}

请基于以上知识图谱和文档内容，生成一份结构完整的{label}。"""

        content = chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=8192,
        )

        title = f"{subject.name}{label}"
        file_type = "md"
        subject_dir = os.path.join(settings.upload_dir, str(subject_id))
        os.makedirs(subject_dir, exist_ok=True)

        timestamp = int(time.time())
        filename = f"kg_gen_{doc_type}_{timestamp}.md"
        file_path = os.path.join(subject_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        doc = Document(
            subject_id=subject_id,
            title=title,
            file_path=file_path,
            file_size=os.path.getsize(file_path),
            file_type=file_type,
            doc_type=db_doc_type,
            parse_status="pending",
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        from app.tasks.document_parse import parse_document_task
        parse_document_task.delay(doc.id)

        return doc
