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
        
        # Generate AI response via routed_chat (parity + MN2/coin rewards), with direct LLM fallback
        llm = get_llm_service()
        ai_response = None
        reward = None
        history = load_chat_history(user_id, limit=10)
        context_messages = [{
            'role': 'system',
            'content': 'You are a helpful AI assistant in the MasterNoder chat room. Be friendly, concise, and helpful. Keep responses under 100 words unless asked for more detail.'
        }]
        for msg in history[-5:]:
            role = 'assistant' if msg.get('is_ai') else 'user'
            context_messages.append({
                'role': role,
                'content': msg.get('message', '')
            })
        context_messages.append({'role': 'user', 'content': message})

        try:
            from backend.services.agent_ai_router import routed_chat

            result, routing = routed_chat(
                context_messages,
                'chat_general',
                user_id,
                temperature=0.7,
                max_tokens=200,
            )
            if result.success and result.content:
                ai_response = result.content.strip()
                save_message('ai_assistant', ai_response, 'AI Assistant', is_ai=True)
                reward = routing.get('crypto_reward')
        except Exception:
            pass

        if not ai_response and llm.is_available():
            result = llm.chat(
                messages=context_messages,
                temperature=0.7,
                max_tokens=200,
                task_type="speed",
            )
            if result.success and result.content:
                ai_response = result.content.strip()
                save_message('ai_assistant', ai_response, 'AI Assistant', is_ai=True)

        out = {
            'success': True,
            'message_saved': True,
            'ai_response': ai_response,
            'timestamp': datetime.now().isoformat()
        }
        if reward:
            out['reward'] = reward
        return jsonify(out), 200
        
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
    Uses direct LLM streaming for UX; grants routed_chat MN2/coins on completion
    (routed_chat is non-streaming — reward is awarded after the full response).
    Each event: data: {"type":"token","text":"..."}\n\n
    Final event: data: {"type":"done","full":"...","reward":{...}}\n\n
    Error event: data: {"type":"error","error":"..."}\n\n
    """
    try:
        data = request.get_json(silent=True) or {}
        user_id = _resolve_uid()
        message = data.get('message', '').strip()

        if not message:
            def _err():
                yield 'data: ' + json.dumps({'type': 'error', 'error': 'Message required'}) + '\n\n'
            return Response(stream_with_context(_err()), content_type='text/event-stream')

        save_message(user_id, message, data.get('username', user_id), is_ai=False)

        history = load_chat_history(user_id, limit=10)
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
            reward = None
            try:
                yield 'data: ' + json.dumps({'type': 'start'}) + '\n\n'
                for token in llm_stream(context_messages, task_type='speed', max_tokens=200, temperature=0.7):
                    full_text += token
                    yield 'data: ' + json.dumps({'type': 'token', 'text': token}) + '\n\n'
                if full_text:
                    save_message('ai_assistant', full_text, 'AI Assistant', is_ai=True)
                    if user_id and user_id not in ('', 'default_user', 'anonymous'):
                        try:
                            from backend.services.agent_crypto_rewards_service import award_agent_action
                            import uuid as _uuid
                            reward = award_agent_action(
                                user_id,
                                'routed_chat',
                                reference=f'stream-chat:{_uuid.uuid4().hex[:12]}',
                                metadata={'source': 'chat_stream', 'task_kind': 'chat_general'},
                                success=True,
                            )
                        except Exception:
                            pass
                done_payload = {'type': 'done', 'full': full_text}
                if reward and reward.get('success'):
                    done_payload['reward'] = reward
                yield 'data: ' + json.dumps(done_payload) + '\n\n'
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


TIP_MIN_MN2 = 0.001
TIP_MAX_MN2 = 5.0
TIP_PRESETS = [0.01, 0.05, 0.1, 0.25]


@chat_bp.route('/api/chat/tip/config', methods=['GET'])
def chat_tip_config():
    """Public MN2 tip presets and limits for the chat UI."""
    return jsonify({
        'success': True,
        'currency': 'MN2',
        'min_mn2': TIP_MIN_MN2,
        'max_mn2': TIP_MAX_MN2,
        'presets': TIP_PRESETS,
    }), 200


@chat_bp.route('/api/chat/tip', methods=['POST'])
def send_tip():
    """Send an MN2 tip to another user (peer transfer on mn2_balance)."""
    try:
        data = request.get_json(silent=True) or {}
        from_user = _resolve_uid()
        to_user = (data.get('to_user_id') or data.get('recipient_id') or '').strip()
        message = (data.get('message') or '').strip()[:200]

        if not to_user:
            return jsonify({'success': False, 'error': 'to_user_id is required'}), 400
        if to_user == from_user:
            return jsonify({'success': False, 'error': 'Cannot tip yourself'}), 400

        try:
            amount = float(data.get('amount'))
        except (TypeError, ValueError):
            return jsonify({'success': False, 'error': 'amount is required'}), 400
        if amount < TIP_MIN_MN2 or amount > TIP_MAX_MN2:
            return jsonify({
                'success': False,
                'error': f'Tip must be between {TIP_MIN_MN2} and {TIP_MAX_MN2} MN2',
            }), 400

        from backend.services.unified_points_database import unified_points_db
        from backend.services.mn2_ledger import append_entry

        points_result = unified_points_db.get_all_points(from_user)
        if not points_result.get('success', True):
            return jsonify({'success': False, 'error': 'Failed to load sender balance'}), 500
        sender_points = points_result.get('points', {}) or {}
        sender_balance = float(sender_points.get('mn2_balance', 0) or 0)
        if sender_balance == 0 and isinstance(sender_points.get('systems'), dict):
            sender_balance = float(sender_points['systems'].get('mn2_balance', 0) or 0)
        if sender_balance < amount:
            return jsonify({
                'success': False,
                'error': f'Insufficient MN2 balance. Need {amount:.8f}, have {sender_balance:.8f}',
                'mn2_balance': sender_balance,
            }), 400

        meta = {
            'from_user_id': from_user,
            'to_user_id': to_user,
            'message': message or None,
            'source': 'chat_tip',
        }
        debit = unified_points_db.add_points(
            from_user, 'mn2_balance', -amount, source='chat_tip_sent', metadata=meta,
        )
        if not debit.get('success', True):
            return jsonify({'success': False, 'error': 'Failed to debit sender balance'}), 500

        credit = unified_points_db.add_points(
            to_user, 'mn2_balance', amount, source='chat_tip_received', metadata=meta,
        )
        if not credit.get('success', True):
            unified_points_db.add_points(
                from_user, 'mn2_balance', amount, source='chat_tip_refund', metadata=meta,
            )
            return jsonify({'success': False, 'error': 'Failed to credit recipient; tip refunded'}), 500

        try:
            append_entry(
                user_id=from_user,
                entry_type='chat_tip_sent',
                amount=amount,
                metadata=meta,
            )
            append_entry(
                user_id=to_user,
                entry_type='chat_tip_received',
                amount=amount,
                metadata=meta,
            )
        except Exception:
            pass

        tip_note = f'Tipped {amount:.4f} MN2 to {to_user}'
        if message:
            tip_note += f': {message}'
        save_message(from_user, tip_note, username=from_user, is_ai=False)

        recipient_balance = unified_points_db.get_all_points(to_user).get('points', {}) or {}
        new_sender_balance = unified_points_db.get_all_points(from_user).get('points', {}) or {}

        return jsonify({
            'success': True,
            'from_user_id': from_user,
            'to_user_id': to_user,
            'amount': amount,
            'currency': 'MN2',
            'message': message or None,
            'sender_balance': float(new_sender_balance.get('mn2_balance', 0) or 0),
            'recipient_balance': float(recipient_balance.get('mn2_balance', 0) or 0),
        }), 200
    except Exception as e:
        print(f"Error in send_tip: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
