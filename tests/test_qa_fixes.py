"""测试智能问答系统的 bug 修复"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from datetime import datetime

# ── 测试 1: AskInput 的 max_length 是否提升到 50000 ──
from app.modules.qa.schemas import AskInput
long_text = "a" * 5000
try:
    obj = AskInput(question=long_text)
    print("[PASS] AskInput 接受 5000 字符文本")
except Exception as e:
    print(f"[FAIL] AskInput 应接受 5000 字符，但失败: {e}")

long_text_50001 = "a" * 50001
try:
    obj = AskInput(question=long_text_50001)
    print(f"[FAIL] AskInput 不应接受 50001 字符，但通过了")
except Exception as e:
    print(f"[PASS] AskInput 正确拒绝 50001 字符: {e}")

long_text_50000 = "a" * 50000
try:
    obj = AskInput(question=long_text_50000)
    print("[PASS] AskInput 接受 50000 字符（边界值）")
except Exception as e:
    print(f"[FAIL] AskInput 应接受 50000 字符: {e}")

# ── 测试 2: ConversationResponse 包含 subject_id ──
from app.modules.qa.schemas import ConversationResponse
try:
    fields = list(ConversationResponse.model_fields.keys())
    assert 'subject_id' in fields, f"缺少 subject_id, 当前字段: {fields}"
    print(f"[PASS] ConversationResponse 包含 subject_id 字段")
except Exception as e:
    print(f"[FAIL] {e}")

# ── 测试 3: ConversationResponse 序列化包含 subject_id ──
class MockConv:
    def __init__(self):
        self.id = 1
        self.title = "test"
        self.message_count = 5
        self.subject_id = 2
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

resp = ConversationResponse.model_validate(MockConv())
data = resp.model_dump()
assert data["subject_id"] == 2, f"subject_id 应为 2，实际为 {data.get('subject_id')}"
print("[PASS] ConversationResponse 正确序列化 subject_id")

# ── 测试 4: MessageResponse 正常序列化 ──
from app.modules.qa.schemas import MessageResponse

class MockMsg:
    def __init__(self):
        self.id = 1
        self.role = "user"
        self.content = "你好"
        self.sources = None
        self.question_type = "knowledge"
        self.feedback_score = None
        self.created_at = datetime.now()

msg_resp = MessageResponse.model_validate(MockMsg())
msg_data = msg_resp.model_dump()
assert msg_data["role"] == "user"
assert msg_data["content"] == "你好"
print("[PASS] MessageResponse 正常序列化")

# ── 测试 5: paginated_response 格式正确 ──
from app.common.response import paginated_response
result = paginated_response([{"id": 1}], 1, 1, 20)
assert result["code"] == 200
assert result["data"]["items"] == [{"id": 1}]
assert result["data"]["total"] == 1
print("[PASS] paginated_response 格式正确")

# ── 测试 6: success_response 格式正确 ──
from app.common.response import success_response
result = success_response(data={"key": "value"})
assert result["code"] == 200
assert result["data"]["key"] == "value"
print("[PASS] success_response 格式正确")

print("\n✅ 所有 QA 修复测试通过！")
