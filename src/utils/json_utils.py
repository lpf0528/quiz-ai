import json
import logging

import json_repair

logger = logging.getLogger(__name__)


def repair_json_output(content: str) -> str:
    """
    用于修复和规范化可能包含 JSON 的字符串。代码中使用了 json_repair 库来尝试修复不完整或有误的 JSON 格式。
    """
    content = content.strip()

    try:
        # Try to repair and parse JSON
        repaired_content = json_repair.loads(content)
        if not isinstance(repaired_content, dict) and not isinstance(
                repaired_content, list
        ):
            logger.warning("Repaired content is not a valid JSON object or array.")
            return content
        content = json.dumps(repaired_content, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"JSON repair failed: {e}")

    return content
