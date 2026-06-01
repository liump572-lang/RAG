-- ============================================================
-- 修复已运行数据库中因 Latin-1 连接导致的中文乱码
-- 使用方法：docker exec -i kqa-mysql mysql -u root -p < fix_garbled.sql
-- ============================================================

USE knowledge_qa_system;
SET NAMES utf8mb4;

-- 1. 修复双编码存储的乱码数据（Latin-1 双重编码 → UTF-8）
--    原理：乱码字段 = UTF-8 字节被当作 Latin-1 写入 → 反转回 UTF-8
UPDATE system_configs
SET description = CONVERT(BINARY CONVERT(description USING latin1) USING utf8mb4)
WHERE HEX(description) REGEXP '^(C3|C4|C5|E[0-9A-F])';

-- 2. 删除旧的、与后端不一致的 config key（已被正确 key 替代）
DELETE FROM system_configs
WHERE config_key IN ('llm.api_key', 'llm.api_base', 'llm.model', 'embedding.model');

-- 3. 确保正确的 config key 存在（如果不存在则插入）
INSERT IGNORE INTO system_configs (config_key, config_value, description) VALUES
    ('deepseek_api_key', '', '大模型API Key'),
    ('deepseek_api_base', 'https://api.deepseek.com/v1', '大模型API地址'),
    ('llm_model', 'deepseek-v4-pro', '对话模型名称'),
    ('embedding_model', 'deepseek-embedding', 'Embedding模型名称');

-- 4. 验证修复结果
SELECT config_key, description, HEX(description)
FROM system_configs
WHERE config_key IN ('deepseek_api_key', 'deepseek_api_base', 'llm_model', 'embedding_model');
