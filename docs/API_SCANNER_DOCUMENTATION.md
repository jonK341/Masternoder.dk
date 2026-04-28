# API Scanner Documentation

**Date:** 2025-01-20  
**Status:** ✅ Complete  
**Integration:** Debugger Tool

---

## 🎯 Overview

The API Scanner is an intelligent tool that automatically scans your codebase for blueprints, routes, and API endpoints. It can detect missing API methods and auto-generate them, making it a powerful tool for maintaining and expanding your API structure.

---

## ✨ Features

### 1. **Comprehensive Scanning**
- Scans all blueprints in `backend/routes/` and `vidgenerator/src/routes/`
- Extracts all route definitions with methods and paths
- Identifies service files and classes
- Analyzes API structure

### 2. **Missing Method Detection**
- Detects missing CRUD operations
- Identifies standard API patterns
- Suggests function names based on REST conventions

### 3. **Auto-Generation**
- Generates complete API method code
- Includes error handling
- Supports GET, POST, PUT, DELETE methods
- Can generate for specific blueprints or all

### 4. **Registration Code Generation**
- Auto-generates blueprint registration code
- Includes error handling
- Ready to paste into registration file

---

## 📁 Files

### Service
- **`backend/services/api_scanner.py`** - Core scanner service

### Routes
- **`backend/routes/api_scanner_routes.py`** - API endpoints for scanner

### Integration
- **`vidgenerator/debugger/index.html`** - Debugger UI with Scanner tab
- **`backend/register_blueprints.py`** - Auto-registered scanner blueprint

---

## 🔌 API Endpoints

### Scan Endpoints

#### `GET /api/debugger/scanner/scan`
Scan entire codebase and get comprehensive report.

**Response:**
```json
{
  "success": true,
  "report": {
    "summary": {
      "total_blueprints": 7,
      "total_routes": 45,
      "total_services": 1,
      "missing_methods": 12,
      "suggestions": 12
    },
    "blueprints": [...],
    "routes": [...],
    "services": [...],
    "missing_methods": [...],
    "suggestions": [...]
  }
}
```

#### `GET /api/debugger/scanner/blueprints`
Get all blueprints.

#### `GET /api/debugger/scanner/routes`
Get all routes.

#### `GET /api/debugger/scanner/missing`
Get missing API methods.

#### `GET /api/debugger/scanner/suggestions`
Get code suggestions for missing methods.

#### `GET /api/debugger/scanner/services`
Get all services.

#### `GET /api/debugger/scanner/registration-code`
Get auto-generated blueprint registration code.

### Generation Endpoint

#### `POST /api/debugger/scanner/generate`
Auto-generate missing API methods.

**Request:**
```json
{
  "blueprint": "hunters_game",  // Optional: specific blueprint
  "dry_run": true  // Preview only, don't modify files
}
```

**Response:**
```json
{
  "success": true,
  "dry_run": false,
  "results": {
    "generated": [
      {
        "blueprint": "hunters_game",
        "path": "/api/hunters_game",
        "method": "POST",
        "file": "backend/routes/hunters_game.py"
      }
    ],
    "files_modified": ["backend/routes/hunters_game.py"],
    "errors": []
  }
}
```

---

## 🖥️ Debugger UI

### Access
Navigate to: `/vidgenerator/debugger` and click the **"🔍 API Scanner"** tab.

### Features in UI

1. **📊 Scan All** - Complete codebase scan
2. **🔵 Get Blueprints** - List all blueprints
3. **🛣️ Get Routes** - List all routes
4. **⚠️ Find Missing Methods** - Detect missing API methods
5. **💡 Get Suggestions** - View code suggestions
6. **✨ Generate Missing Methods** - Auto-generate methods
   - Optional: Specify blueprint name
   - Dry run mode (preview only)
7. **📝 Get Registration Code** - Get blueprint registration code
8. **⚙️ Get Services** - List all services

---

## 💻 Usage Examples

### Python Usage

```python
from backend.services.api_scanner import api_scanner

# Scan everything
report = api_scanner.get_report()
print(f"Found {report['summary']['total_blueprints']} blueprints")

# Find missing methods
missing = api_scanner.find_missing_methods()
print(f"Missing {len(missing)} methods")

# Generate missing methods (dry run)
results = api_scanner.auto_generate_missing_methods(dry_run=True)

# Actually generate
results = api_scanner.auto_generate_missing_methods('hunters_game')
```

### API Usage

```bash
# Scan all
curl http://localhost:5000/vidgenerator/api/debugger/scanner/scan

# Get missing methods
curl http://localhost:5000/vidgenerator/api/debugger/scanner/missing

# Generate methods (dry run)
curl -X POST http://localhost:5000/vidgenerator/api/debugger/scanner/generate \
  -H "Content-Type: application/json" \
  -d '{"dry_run": true}'

# Actually generate
curl -X POST http://localhost:5000/vidgenerator/api/debugger/scanner/generate \
  -H "Content-Type: application/json" \
  -d '{"blueprint": "hunters_game", "dry_run": false}'
```

---

## 🔧 Integration with Master Fix Script

The `fix_all_loose_ends_master.py` script now uses the API Scanner for more comprehensive blueprint detection:

```python
# Automatically uses scanner if available
blueprints = find_all_blueprints()  # Uses scanner internally
```

---

## 📝 Generated Code Format

The scanner generates code following this pattern:

```python
@blueprint_name.route('/api/resource', methods=['GET'])
@blueprint_name.route('/vidgenerator/api/resource', methods=['GET'])
def get_resource():
    """GET endpoint for /api/resource"""
    try:
        from flask import request, jsonify
        # TODO: Implement logic
        return jsonify({
            'success': True,
            'data': [],
            'message': 'Resource retrieved successfully'
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
```

---

## 🎯 Use Cases

1. **Initial Setup** - Scan codebase to understand API structure
2. **Missing Methods** - Find and generate missing CRUD operations
3. **Blueprint Registration** - Auto-generate registration code
4. **Code Review** - Identify incomplete API implementations
5. **Documentation** - Generate API structure reports

---

## ⚠️ Notes

- **Dry Run Mode**: Always test with `dry_run: true` first
- **Backup**: Generated code modifies files - backup first
- **Review**: Always review generated code before committing
- **Customization**: Generated code includes TODO comments for customization

---

## 🚀 Future Enhancements

- [ ] Support for PATCH method
- [ ] Custom route pattern detection
- [ ] Integration with OpenAPI/Swagger
- [ ] Automatic test generation
- [ ] Database model detection and CRUD generation

---

**Last Updated:** 2025-01-20
