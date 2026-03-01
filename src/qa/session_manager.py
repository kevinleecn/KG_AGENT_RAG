"""
会话管理
"""
import uuid
import time
import json
from typing import Dict, List, Optional
from flask import session
import logging

logger = logging.getLogger(__name__)

class SessionManager:
    """管理对话会话"""

    def __init__(self, storage_backend: str = 'memory'):
        """
        初始化会话管理器

        Args:
            storage_backend: 存储后端 ('memory', 'file', 'database')
        """
        self.storage_backend = storage_backend
        self.sessions = {}  # 内存存储
        self.file_storage_path = None

        if storage_backend == 'file':
            import os
            self.file_storage_path = 'data/sessions'
            os.makedirs(self.file_storage_path, exist_ok=True)

    def create_session(self, user_id: str = None, session_data: Dict = None) -> str:
        """创建新会话"""
        session_id = str(uuid.uuid4())

        session_obj = {
            'id': session_id,
            'user_id': user_id,
            'created_at': time.time(),
            'updated_at': time.time(),
            'messages': [],
            'context': session_data or {},
            'metadata': {
                'document_id': None,
                'language': 'en',
                'topic': 'general'
            }
        }

        if self.storage_backend == 'memory':
            self.sessions[session_id] = session_obj
        elif self.storage_backend == 'file':
            self._save_session_to_file(session_id, session_obj)

        logger.info(f"Created new session: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        """获取会话"""
        if not session_id:
            return None

        if self.storage_backend == 'memory':
            return self.sessions.get(session_id)
        elif self.storage_backend == 'file':
            return self._load_session_from_file(session_id)

        return None

    def add_message(self, session_id: str, role: str, content: str, metadata: Dict = None):
        """添加消息到会话"""
        session_obj = self.get_session(session_id)
        if not session_obj:
            logger.warning(f"Session not found: {session_id}")
            return False

        message = {
            'role': role,
            'content': content,
            'timestamp': time.time(),
            'metadata': metadata or {}
        }

        session_obj['messages'].append(message)
        session_obj['updated_at'] = time.time()

        # 限制历史消息数量
        if len(session_obj['messages']) > 50:
            session_obj['messages'] = session_obj['messages'][-50:]

        # 保存更新
        if self.storage_backend == 'memory':
            self.sessions[session_id] = session_obj
        elif self.storage_backend == 'file':
            self._save_session_to_file(session_id, session_obj)

        return True

    def get_session_history(self, session_id: str, limit: int = 10) -> List[Dict]:
        """获取会话历史"""
        session_obj = self.get_session(session_id)
        if not session_obj:
            return []

        messages = session_obj['messages']
        if limit > 0 and len(messages) > limit:
            return messages[-limit:]

        return messages

    def update_session_context(self, session_id: str, context_updates: Dict):
        """更新会话上下文"""
        session_obj = self.get_session(session_id)
        if not session_obj:
            return False

        session_obj['context'].update(context_updates)
        session_obj['updated_at'] = time.time()

        if self.storage_backend == 'memory':
            self.sessions[session_id] = session_obj
        elif self.storage_backend == 'file':
            self._save_session_to_file(session_id, session_obj)

        return True

    def clear_session(self, session_id: str):
        """清除会话历史"""
        session_obj = self.get_session(session_id)
        if not session_obj:
            return False

        session_obj['messages'] = []
        session_obj['updated_at'] = time.time()

        if self.storage_backend == 'memory':
            self.sessions[session_id] = session_obj
        elif self.storage_backend == 'file':
            self._save_session_to_file(session_id, session_obj)

        logger.info(f"Cleared session: {session_id}")
        return True

    def delete_session(self, session_id: str):
        """删除会话"""
        if self.storage_backend == 'memory':
            if session_id in self.sessions:
                del self.sessions[session_id]
                return True
        elif self.storage_backend == 'file':
            import os
            filepath = self._get_session_filepath(session_id)
            if os.path.exists(filepath):
                os.remove(filepath)
                return True

        return False

    def get_active_sessions(self, max_age_seconds: int = 86400) -> List[Dict]:
        """获取活跃会话"""
        current_time = time.time()
        active_sessions = []

        if self.storage_backend == 'memory':
            for session_id, session_obj in self.sessions.items():
                if current_time - session_obj['updated_at'] <= max_age_seconds:
                    active_sessions.append({
                        'id': session_id,
                        'user_id': session_obj['user_id'],
                        'message_count': len(session_obj['messages']),
                        'last_activity': session_obj['updated_at'],
                        'created_at': session_obj['created_at']
                    })
        elif self.storage_backend == 'file':
            import os
            if not os.path.exists(self.file_storage_path):
                return []

            for filename in os.listdir(self.file_storage_path):
                if filename.endswith('.json'):
                    session_id = filename[:-5]
                    session_obj = self._load_session_from_file(session_id)
                    if session_obj and current_time - session_obj['updated_at'] <= max_age_seconds:
                        active_sessions.append({
                            'id': session_id,
                            'user_id': session_obj['user_id'],
                            'message_count': len(session_obj['messages']),
                            'last_activity': session_obj['updated_at'],
                            'created_at': session_obj['created_at']
                        })

        return active_sessions

    def _get_session_filepath(self, session_id: str) -> str:
        """获取会话文件路径"""
        import os
        if not self.file_storage_path:
            self.file_storage_path = 'data/sessions'
            os.makedirs(self.file_storage_path, exist_ok=True)

        return os.path.join(self.file_storage_path, f"{session_id}.json")

    def _save_session_to_file(self, session_id: str, session_obj: Dict):
        """保存会话到文件"""
        try:
            import os
            filepath = self._get_session_filepath(session_id)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_obj, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving session to file: {e}")

    def _load_session_from_file(self, session_id: str) -> Optional[Dict]:
        """从文件加载会话"""
        try:
            import os
            filepath = self._get_session_filepath(session_id)
            if not os.path.exists(filepath):
                return None

            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading session from file: {e}")
            return None

# Flask集成辅助函数
def get_or_create_session(session_manager: SessionManager, session_key: str = 'chat_session_id') -> str:
    """获取或创建Flask会话"""
    from flask import session as flask_session

    # 检查Flask会话中是否有session_id
    session_id = flask_session.get(session_key)

    if not session_id:
        # 创建新会话
        session_id = session_manager.create_session()
        flask_session[session_key] = session_id
        flask_session.permanent = True  # 使会话持久化

    return session_id