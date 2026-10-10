"""Gallery routes"""
from flask import render_template, request, jsonify
from src.db.models import db, Documentary
# Cache temporarily disabled
# from src.services.cache.query_cache import query_cache


def register_gallery_routes(app):
    """Register gallery routes"""
    
    @app.route('/gallery', methods=['GET'], endpoint='gallery')
    @app.route('/vidgenerator/gallery', methods=['GET'], endpoint='gallery_vidgenerator')
    @app.route('/vidgenerator/gallery/', methods=['GET'], endpoint='gallery_vidgenerator_slash')
    def gallery_index():
        """Gallery page to browse all documentaries"""
        try:
            # Get query parameters for filtering/sorting
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 12, type=int)
            status_filter = request.args.get('status', 'all')
            search_query = request.args.get('search', '').strip()
            sort_by = request.args.get('sort', 'newest')
            
            # Try cache first (only for non-search queries)
            # Note: Cache disabled temporarily to avoid errors
            # if not search_query:
            #     try:
            #         cached = query_cache.get('gallery', page=page, per_page=per_page, 
            #                                 status_filter=status_filter, sort_by=sort_by)
            #         if cached is not None:
            #             return render_template('gallery/index.html', **cached)
            #     except Exception as cache_error:
            #         print(f"Cache error (ignoring): {cache_error}")
            
            # Build query - Show ANY documentary with a valid video path
            # This is more permissive to catch all videos that have been created
            query = Documentary.query.filter(
                Documentary.video_path.isnot(None),
                Documentary.video_path != ''
            )
            
            # Apply status filter if specified
            if status_filter and status_filter != 'all':
                query = query.filter(Documentary.status == status_filter)
            
            # Enhanced search filter
            if search_query:
                try:
                    from datetime import datetime
                    search_date = datetime.strptime(search_query, '%Y-%m-%d').date()
                    # Try completed_at first, then created_at
                    query = query.filter(
                        db.or_(
                            db.func.date(Documentary.completed_at) == search_date,
                            db.func.date(Documentary.created_at) == search_date
                        )
                    )
                except (ValueError, TypeError):
                    # Text search in multiple fields
                    query = query.filter(
                        db.or_(
                            Documentary.title.ilike(f'%{search_query}%'),
                            Documentary.prompt.ilike(f'%{search_query}%'),
                            Documentary.description.ilike(f'%{search_query}%')
                        )
                    )
            
            # Enhanced sorting options - prefer completed_at for newest, fallback to created_at
            if sort_by == 'oldest':
                query = query.order_by(
                    db.func.coalesce(Documentary.completed_at, Documentary.created_at).asc()
                )
            elif sort_by == 'title':
                query = query.order_by(Documentary.title.asc())
            elif sort_by == 'duration':
                query = query.order_by(Documentary.duration.desc().nullslast())
            else:  # newest (default) - use completed_at if available, otherwise created_at
                query = query.order_by(
                    db.func.coalesce(Documentary.completed_at, Documentary.created_at).desc()
                )
            
            # Pagination
            pagination = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            documentaries = pagination.items
            
            # Debug: Log what we're returning
            print(f"[Gallery] Returning {len(documentaries)} documentaries")
            for doc in documentaries[:3]:  # Log first 3
                print(f"[Gallery] - {doc.id}: {doc.title}, status={doc.status}, video_path={doc.video_path[:50] if doc.video_path else 'None'}...")
            
            template_data = {
                'documentaries': documentaries,
                'pagination': pagination,
                'current_page': page,
                'status_filter': status_filter,
                'search_query': search_query,
                'sort_by': sort_by
            }
            
            # Cache result (only if no search query)
            # Note: Cache disabled temporarily to avoid errors
            # if not search_query:
            #     try:
            #         query_cache.set('gallery', template_data, ttl=180, 
            #                       page=page, per_page=per_page, 
            #                       status_filter=status_filter, sort_by=sort_by)
            #     except Exception as cache_error:
            #         print(f"Cache error (ignoring): {cache_error}")
            
            return render_template('gallery/index.html', **template_data)
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            print(f"Gallery error: {e}")
            print(f"Traceback: {error_trace}")
            return f"Error loading gallery: {str(e)}<br><pre>{error_trace}</pre>", 500
    
    # API endpoint for gallery data (JSON)
    @app.route('/api/gallery', methods=['GET'], endpoint='gallery_api')
    @app.route('/vidgenerator/api/gallery', methods=['GET'], endpoint='gallery_api_vidgenerator')
    def gallery_api():
        """API endpoint to get gallery data as JSON"""
        try:
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 12, type=int)
            status_filter = request.args.get('status', 'all')
            search_query = request.args.get('search', '').strip()
            sort_by = request.args.get('sort', 'newest')
            
            # Build query - Show ANY documentary with a valid video path
            # This is more permissive to catch all videos that have been created
            query = Documentary.query.filter(
                Documentary.video_path.isnot(None),
                Documentary.video_path != ''
            )
            
            # Apply status filter if specified
            if status_filter and status_filter != 'all':
                query = query.filter(Documentary.status == status_filter)
            
            # Enhanced search filter
            if search_query:
                try:
                    from datetime import datetime
                    search_date = datetime.strptime(search_query, '%Y-%m-%d').date()
                    # Try completed_at first, then created_at
                    query = query.filter(
                        db.or_(
                            db.func.date(Documentary.completed_at) == search_date,
                            db.func.date(Documentary.created_at) == search_date
                        )
                    )
                except (ValueError, TypeError):
                    query = query.filter(
                        db.or_(
                            Documentary.title.ilike(f'%{search_query}%'),
                            Documentary.prompt.ilike(f'%{search_query}%'),
                            Documentary.description.ilike(f'%{search_query}%')
                        )
                    )
            
            # Sorting - prefer completed_at for newest, fallback to created_at
            if sort_by == 'oldest':
                query = query.order_by(
                    db.func.coalesce(Documentary.completed_at, Documentary.created_at).asc()
                )
            elif sort_by == 'title':
                query = query.order_by(Documentary.title.asc())
            elif sort_by == 'duration':
                query = query.order_by(Documentary.duration.desc().nullslast())
            else:
                query = query.order_by(
                    db.func.coalesce(Documentary.completed_at, Documentary.created_at).desc()
                )
            
            # Debug: Log query details
            print(f"[Gallery API] Query filters: status_filter={status_filter}, search={search_query}, sort={sort_by}")
            print(f"[Gallery API] Total matching documents: {query.count()}")
            
            # Pagination
            pagination = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            # Format documentaries for JSON response
            documentaries = []
            for doc in pagination.items:
                documentaries.append({
                    'id': doc.id,
                    'title': doc.title,
                    'prompt': doc.prompt,
                    'description': doc.description or '',
                    'status': doc.status,
                    'video_path': doc.video_path or '',
                    'thumbnail_path': doc.thumbnail_path or '',
                    'duration': doc.duration or 0,
                    'created_at': doc.created_at.isoformat() if doc.created_at else None,
                    'completed_at': doc.completed_at.isoformat() if doc.completed_at else None
                })
            
            return jsonify({
                'success': True,
                'documentaries': documentaries,
                'pagination': {
                    'page': pagination.page,
                    'pages': pagination.pages,
                    'per_page': pagination.per_page,
                    'total': pagination.total,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    # Clip editing API endpoints
    @app.route('/api/clip/<clip_id>', methods=['GET'], endpoint='get_clip')
    @app.route('/vidgenerator/api/clip/<clip_id>', methods=['GET'], endpoint='get_clip_vidgenerator')
    def get_clip(clip_id):
        """Get clip data for editing"""
        try:
            from src.db.models import MovieClip
            clip = MovieClip.query.get(clip_id)
            if not clip:
                return jsonify({'success': False, 'error': 'Clip not found'}), 404
            
            return jsonify({
                'success': True,
                'clip': clip.to_dict()
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/clip/<clip_id>', methods=['PUT'], endpoint='update_clip')
    @app.route('/vidgenerator/api/clip/<clip_id>', methods=['PUT'], endpoint='update_clip_vidgenerator')
    def update_clip(clip_id):
        """Update clip data"""
        try:
            from src.db.models import MovieClip
            clip = MovieClip.query.get(clip_id)
            if not clip:
                return jsonify({'success': False, 'error': 'Clip not found'}), 404
            
            data = request.get_json() or {}
            
            # Update allowed fields
            if 'title' in data:
                clip.title = data['title']
            if 'quality_score' in data:
                clip.quality_score = float(data['quality_score'])
            if 'order_index' in data:
                clip.order_index = int(data['order_index'])
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'clip': clip.to_dict()
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/clip/<clip_id>/separate', methods=['POST'], endpoint='separate_clip')
    @app.route('/vidgenerator/api/clip/<clip_id>/separate', methods=['POST'], endpoint='separate_clip_vidgenerator')
    def separate_clip(clip_id):
        """Separate audio and video for a clip"""
        try:
            from src.db.models import MovieClip
            from src.services.documentary_pipeline.clip_quality_ensurer import ClipQualityEnsurer
            
            clip = MovieClip.query.get(clip_id)
            if not clip:
                return jsonify({'success': False, 'error': 'Clip not found'}), 404
            
            # Use clip quality ensurer to separate
            ensurer = ClipQualityEnsurer()
            result = ensurer.separate_video_audio(clip.clip_path or clip.video_path)
            
            if result.get('success'):
                # Update clip with separated paths
                clip.video_path = result.get('video_path')
                clip.audio_path = result.get('audio_path')
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'clip': clip.to_dict(),
                    'video_path': result.get('video_path'),
                    'audio_path': result.get('audio_path')
                })
            else:
                return jsonify({'success': False, 'error': result.get('error', 'Separation failed')}), 500
                
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/clip/<clip_id>/ai-edit', methods=['POST'], endpoint='ai_edit_clip')
    @app.route('/vidgenerator/api/clip/<clip_id>/ai-edit', methods=['POST'], endpoint='ai_edit_clip_vidgenerator')
    def ai_edit_clip(clip_id):
        """Apply AI editing to a clip"""
        try:
            from src.db.models import MovieClip
            from src.services.ai_editor.clip_editor import ClipEditor
            
            clip = MovieClip.query.get(clip_id)
            if not clip:
                return jsonify({'success': False, 'error': 'Clip not found'}), 404
            
            data = request.get_json() or {}
            strategy = data.get('strategy', 'quality')
            
            # Use AI clip editor
            editor = ClipEditor()
            clip_path = clip.video_path or clip.clip_path
            
            if not clip_path:
                return jsonify({'success': False, 'error': 'No clip path available'}), 400
            
            result = editor.edit_clip(clip_path, strategy=strategy)
            
            if result.get('success'):
                # Update clip with new path and quality
                if result.get('output_path'):
                    clip.video_path = result.get('output_path')
                if result.get('quality_score'):
                    clip.quality_score = result.get('quality_score')
                db.session.commit()
                
                return jsonify({
                    'success': True,
                    'clip': clip.to_dict(),
                    'quality_improvement': result.get('quality_improvement', 0)
                })
            else:
                return jsonify({'success': False, 'error': result.get('error', 'AI edit failed')}), 500
                
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
