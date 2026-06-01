import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.common.llm_client import chat_stream
from app.common.utils import sanitize_markdown
from app.config import settings
from app.database import SessionLocal
from app.models import Conversation, Message, SystemConfig
from app.modules.qa.intent import detect_intent, is_meta_question
from app.modules.qa.prompt import build_prompt
from app.modules.qa.retriever import fusion_rank, search_exam, search_graph, search_knowledge, search_notes

logger = logging.getLogger(__name__)


class QaService:

    @staticmethod
    def get_or_create_conversation(
        db: Session,
        user_id: int,
        conversation_id: Optional[int] = None,
        subject_id: Optional[int] = None,
    ) -> Conversation:
        if conversation_id:
            conv = db.query(Conversation).filter(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id,
            ).first()
            if conv:
                return conv

        conv = Conversation(
            user_id=user_id,
            subject_id=subject_id,
            title="新对话",
            message_count=0,
        )
        db.add(conv)
        db.commit()
        db.refresh(conv)
        return conv

    @staticmethod
    def save_message(db: Session, conversation_id: int, role: str, content: str, **kwargs) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=kwargs.get("sources"),
            question_type=kwargs.get("question_type"),
            intent_confidence=kwargs.get("intent_confidence"),
            token_count=kwargs.get("token_count", 0),
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if conv:
            conv.message_count = db.query(Message).filter(
                Message.conversation_id == conversation_id
            ).count()
            if role == "user" and conv.title == "新对话":
                conv.title = content[:50]
            db.commit()

        return msg

    @staticmethod
    def ask_stream(db: Session, user_id: int, question: str, conversation_id: Optional[int] = None, subject_id: Optional[int] = None):
        conv = QaService.get_or_create_conversation(db, user_id, conversation_id, subject_id)

        QaService.save_message(db, conv.id, "user", question, question_type="knowledge")

        intent = detect_intent(question)

        # For meta-questions about the AI/system itself, skip RAG and answer directly
        if is_meta_question(question):
            contexts = []
        else:
            knowledge_results = search_knowledge(db, question, subject_id=subject_id)
            exam_results = search_exam(db, question, subject_id=subject_id) if intent in ("exam", "knowledge") else []
            note_results = search_notes(db, question, subject_id=subject_id, current_user_id=user_id) if intent in ("note",) else []
            graph_results = search_graph(question, subject_id=subject_id)

            contexts = fusion_rank(knowledge_results, exam_results, note_results, graph_results, intent, subject_id)

        messages = build_prompt(intent, question, contexts)

        # Read LLM config from DB, fallback to env
        def _cfg(key: str, fallback: str = "") -> str:
            row = db.query(SystemConfig).filter(SystemConfig.config_key == key).first()
            return row.config_value if row else fallback

        model_name = _cfg("llm_model", settings.llm_model)
        api_key = _cfg("deepseek_api_key", settings.deepseek_api_key)
        api_base = _cfg("deepseek_api_base", settings.deepseek_api_base)

        def generate():
            collected_content = ""
            collected_reasoning = ""
            stream_error = None

            try:
                stream = chat_stream(messages, model=model_name, api_key=api_key, api_base=api_base)
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        collected_content += delta.content
                        yield {"data": json.dumps({"type": "token", "content": delta.content}, ensure_ascii=False)}
                    elif hasattr(delta, 'reasoning_content') and delta.reasoning_content:
                        collected_reasoning += delta.reasoning_content

            except Exception as e:
                stream_error = str(e)
                yield {"data": json.dumps({"type": "error", "content": stream_error}, ensure_ascii=False)}

            # Always save assistant message — use a fresh DB session because the
            # dependency-injected session may have been closed during long streaming.
            save_db = SessionLocal()
            try:
                if not collected_content and collected_reasoning:
                    collected_content = collected_reasoning

                cleaned = sanitize_markdown(collected_content) if collected_content else ""
                if stream_error:
                    cleaned += "\n\n> [回答中断：" + stream_error + "]"
                final_content = cleaned.strip() or "(模型未返回有效回答)"

                safe_sources = []
                for s in (contexts[:5] if contexts else []):
                    safe_sources.append({
                        "type": s.get("type", ""),
                        "content": s.get("content", "")[:200],
                        "source": s.get("source", s.get("node_name", "")),
                        "score": s.get("score", 0),
                    })

                assistant_msg = QaService.save_message(
                    save_db, conv.id, "assistant", final_content,
                    sources=safe_sources,
                    question_type=intent,
                )

                yield {"data": json.dumps({"type": "done", "conversation_id": conv.id, "message_id": assistant_msg.id, "subject_id": conv.subject_id}, ensure_ascii=False)}

            except Exception as save_err:
                logger.error("Failed to save assistant message for conv %s: %s", conv.id, save_err)
                yield {"data": json.dumps({"type": "error", "content": "保存消息失败: " + str(save_err)}, ensure_ascii=False)}
            finally:
                save_db.close()

            yield {"data": "[DONE]"}

        return generate, conv.id

    @staticmethod
    def list_conversations(db: Session, user_id: int, page: int = 1, size: int = 20):
        query = db.query(Conversation).filter(Conversation.user_id == user_id)
        total = query.count()
        items = query.order_by(Conversation.updated_at.desc()).offset((page - 1) * size).limit(size).all()
        return items, total

    @staticmethod
    def get_messages(db: Session, conversation_id: int, user_id: int):
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        ).first()
        if not conv:
            return None, []
        msgs = db.query(Message).filter(
            Message.conversation_id == conversation_id
        ).order_by(Message.created_at).all()
        return conv, msgs

    @staticmethod
    def delete_conversation(db: Session, conversation_id: int, user_id: int) -> bool:
        conv = db.query(Conversation).filter(
            Conversation.id == conversation_id,
            Conversation.user_id == user_id,
        ).first()
        if not conv:
            return False
        db.query(Message).filter(Message.conversation_id == conversation_id).delete()
        db.delete(conv)
        db.commit()
        return True

    @staticmethod
    def submit_feedback(db: Session, message_id: int, user_id: int, score: int):
        msg = db.query(Message).filter(
            Message.id == message_id,
            Message.role == "assistant",
        ).join(Conversation, Message.conversation_id == Conversation.id).filter(
            Conversation.user_id == user_id,
        ).first()
        if not msg:
            return None
        msg.feedback_score = score
        db.commit()
        db.refresh(msg)
        return msg
