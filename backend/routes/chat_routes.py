"""
Chat Routes - AI-powered chat with LLM integration
Provides endpoints for sending messages and getting AI responses.
All endpoints resolve user_id via session > body/query > identification.
Chat history is stored per-user, not globally.
"""
from flask import Blueprint, jsonify, request, Response, stream_with_context
from datetime import datetime
import os
import json
from typing import Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHAT_DATA_DIR = os.path.join(BASE_DIR, 'data', 'chat')
os.makedirs(CHAT_DATA_DIR, exist_ok=True)

chat_bp = Blueprint('chat', __name__)


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return request.args.get('user_id', 'default_user')


def get_llm_service():
    """Lazy import LLM service"""
    from backend.services.llm_service import llm_service
    return llm_service


def get_chat_history_file(user_id: str = 'global') -> str:
    """Get chat history file path for user"""
    return os.path.join(CHAT_DATA_DIR, f'chat_history_{user_id}.json')


def load_chat_history(user_id: str = 'global', limit: int = 50) -> List[Dict]:
    """Load chat history from DB when available, else from file"""
    try:
        from backend.services.chat_db_service import chat_tables_exist, load_chat_history as load_from_db
        if chat_tables_exist():
            from_db = load_from_db(user_id, limit)
            if from_db is not None:
                return from_db
    except Exception:
        pass
    file_path = get_chat_history_file(user_id)
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            messages = data.get('messages', [])
            return messages[-limit:] if len(messages) > limit else messages
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []


def save_message(user_id: str, message: str, username: str = None, is_ai: bool = False):
    """Save message to DB when available, then fallback to per-user file"""
    try:
        from backend.services.chat_db_service import chat_tables_exist, save_message as save_to_db
        if chat_tables_exist() and save_to_db(user_id, user_id, username or user_id, message, is_ai):
            return
    except Exception:
        pass
    file_path = get_chat_history_file(user_id)
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception:
            data = {'messages': []}
    else:
        data = {'messages': []}
    msg_data = {
        'user_id': 'AI Assistant' if is_ai else user_id,
        'username': 'AI Assistant' if is_ai else (username or user_id),
        'message': message,
        'timestamp': datetime.now().isoformat(),
        'is_ai': is_ai
    }
    data['messages'].append(msg_data)
    if len(data['messages']) > 500:
        data['messages'] = data['messages'][-500:]
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving message: {e}")


@chat_bp.route('/api/chat/send', methods=['POST'])
def send_message():
    """Send a chat message and get AI response"""
    try:
        data = request.get_json() or {}
        user_id = _resolve_uid()
        message = data.get('message', '').strip()
        username = data.get('username', user_id)
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message is required'
            }), 400
        
        # Save user message
        save_message(user_id, message, username, is_ai=False)
        
        # Generate AI response
        llm = get_llm_service()
        ai_response = None
        
        if llm.is_available():
            # Build context from recent messages
            history = load_chat_history(user_id, limit=10)
            context_messages = []
            
            # Add system prompt
            context_messages.append({
                'role': 'system',
                'content': 'You are a helpful AI assistant in the MasterNoder chat room. Be friendly, concise, and helpful. Keep responses under 100 words unless asked for more detail.'
            })
            
            # Add recent history (last 5 messages for context)
            for msg in history[-5:]:
                role = 'assistant' if msg.get('is_ai') else 'user'
                context_messages.append({
                    'role': role,
                    'content': msg.get('message', '')
                })
            
            # Add current message
            context_messages.append({
                'role': 'user',
                'content': message
            })
            
            # Get AI response — route to fast providers (Groq/Cerebras) for low latency
            result = llm.chat(
                messages=context_messages,
                temperature=0.7,
                max_tokens=200,
                task_type="speed",
            )
            
            if result.success and result.content:
                ai_response = result.content.strip()
                # Save AI response
                save_message('ai_assistant', ai_response, 'AI Assistant', is_ai=True)
        
        return jsonify({
            'success': True,
            'message_saved': True,
            'ai_response': ai_response,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        print(f"Error in send_message: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/api/chat/stream', methods=['POST'])
def chat_stream():
    """
    Streaming SSE chat endpoint. Returns text/event-stream.
    Each event: data: {"type":"token","text":"..."}\n\n
    Final event: data: {"type":"done","full":"..."}\n\n
    Error event: data: {"type":"error","error":"..."}\n\n
    """
    try:
        data = request.get_json(silent=True) or {}
        user_id = data.get('user_id', 'default_user')
        message = data.get('message', '').strip()

        if not message:
            def _err():
                yield 'data: ' + json.dumps({'type': 'error', 'error': 'Message required'}) + '\n\n'
            return Response(stream_with_context(_err()), content_type='text/event-stream')

        save_message(user_id, message, data.get('username', user_id), is_ai=False)

        history = load_chat_history('global', limit=10)
        context_messages = [{
            'role': 'system',
            'content': 'You are a helpful AI assistant in the MasterNoder chat room. Be friendly, concise, and helpful. Keep responses under 100 words unless asked for more detail.'
        }]
        for msg in history[-5:]:
            context_messages.append({
                'role': 'assistant' if msg.get('is_ai') else 'user',
                'content': msg.get('message', '')
            })
        context_messages.append({'role': 'user', 'content': message})

        def generate():
            from backend.services.llm_service import stream_chat as llm_stream
            full_text = ''
            try:
                yield 'data: ' + json.dumps({'type': 'start'}) + '\n\n'
                for token in llm_stream(context_messages, task_type='speed', max_tokens=200, temperature=0.7):
                    full_text += token
                    yield 'data: ' + json.dumps({'type': 'token', 'text': token}) + '\n\n'
                if full_text:
                    save_message('ai_assistant', full_text, 'AI Assistant', is_ai=True)
                yield 'data: ' + json.dumps({'type': 'done', 'full': full_text}) + '\n\n'
            except Exception as e:
                yield 'data: ' + json.dumps({'type': 'error', 'error': str(e)}) + '\n\n'

        resp = Response(stream_with_context(generate()), content_type='text/event-stream')
        resp.headers['X-Accel-Buffering'] = 'no'
        resp.headers['Cache-Control'] = 'no-cache'
        resp.headers['Connection'] = 'keep-alive'
        return resp

    except Exception as e:
        def _err2():
            yield 'data: ' + json.dumps({'type': 'error', 'error': str(e)}) + '\n\n'
        return Response(stream_with_context(_err2()), content_type='text/event-stream')


@chat_bp.route('/api/chat/history', methods=['GET'])
def get_history():
    """Get chat history (from DB when migration run, else file)"""
    try:
        user_id = _resolve_uid()
        limit = int(request.args.get('limit', 50))
        messages = load_chat_history(user_id, limit)
        return jsonify({
            'success': True,
            'messages': messages,
            'count': len(messages)
        }), 200
    except Exception as e:
        print(f"Error in get_history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/api/chat/messages', methods=['GET'])
def get_new_messages():
    """Get new messages since a timestamp (for polling)"""
    try:
        since = request.args.get('since')
        user_id = _resolve_uid()
        try:
            from backend.services.chat_db_service import chat_tables_exist, get_messages_since
            if since and chat_tables_exist():
                from_db = get_messages_since(user_id, since, limit=100)
                if from_db is not None:
                    return jsonify({
                        'success': True,
                        'messages': from_db,
                        'count': len(from_db)
                    }), 200
        except Exception:
            pass
        messages = load_chat_history(user_id, limit=100)
        if since:
            try:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                messages = [
                    msg for msg in messages
                    if datetime.fromisoformat(msg.get('timestamp', '').replace('Z', '+00:00')) > since_dt
                ]
            except Exception:
                pass
        return jsonify({
            'success': True,
            'messages': messages,
            'count': len(messages)
        }), 200
    except Exception as e:
        print(f"Error in get_new_messages: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'messages': []
        }), 200


@chat_bp.route('/api/chat/clear', methods=['POST'])
def clear_history():
    """Clear chat history (DB when available, then file)"""
    try:
        data = request.get_json() or {}
        user_id = _resolve_uid()
        try:
            from backend.services.chat_db_service import chat_tables_exist, clear_history as clear_db
            if chat_tables_exist() and clear_db(user_id):
                pass  # cleared in DB
        except Exception:
            pass
        file_path = get_chat_history_file(user_id)
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({
            'success': True,
            'message': 'Chat history cleared'
        }), 200
    except Exception as e:
        print(f"Error in clear_history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
