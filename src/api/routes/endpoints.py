"""API endpoints listing endpoint."""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/endpoints")
async def list_endpoints(request: Request):
    """List all implemented API endpoints.
    
    Returns HTML page showing all registered endpoints grouped by category.
    """
    app = request.app
    
    endpoints = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = [m for m in route.methods if m != 'HEAD']
            if methods:
                for method in methods:
                    endpoints.append({
                        'method': method,
                        'path': route.path,
                        'summary': getattr(route, 'summary', '') or getattr(route, 'description', '')
                    })
    
    # Group by category
    articles = [ep for ep in endpoints if ep['path'].startswith('/articles')]
    jobs = [ep for ep in endpoints if ep['path'].startswith('/jobs')]
    health = [ep for ep in endpoints if ep['path'].startswith('/health')]
    other = [ep for ep in endpoints if not any(ep['path'].startswith(p) for p in ['/articles', '/jobs', '/health', '/docs', '/openapi', '/redoc'])]
    
    def format_endpoint(ep):
        summary_html = f'<div class="summary">{ep["summary"]}</div>' if ep["summary"] else ""
        return f'<div class="endpoint"><span class="method {ep["method"]}">{ep["method"]}</span><span class="path">{ep["path"]}</span>{summary_html}</div>'
    
    articles_html = ''.join([format_endpoint(ep) for ep in sorted(articles, key=lambda x: (x["path"], x["method"]))])
    jobs_html = ''.join([format_endpoint(ep) for ep in sorted(jobs, key=lambda x: (x["path"], x["method"]))])
    health_html = ''.join([format_endpoint(ep) for ep in sorted(health, key=lambda x: (x["path"], x["method"]))])
    other_html = ''.join([format_endpoint(ep) for ep in sorted(other, key=lambda x: (x["path"], x["method"]))])
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>OPAD API - Endpoints</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4a90e2; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .endpoint {{ margin: 10px 0; padding: 12px; background: #f9f9f9; border-left: 4px solid #4a90e2; border-radius: 4px; }}
        .method {{ display: inline-block; padding: 4px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; margin-right: 10px; }}
        .GET {{ background: #61affe; color: white; }}
        .POST {{ background: #49cc90; color: white; }}
        .PUT {{ background: #fca130; color: white; }}
        .DELETE {{ background: #f93e3e; color: white; }}
        .PATCH {{ background: #50e3c2; color: white; }}
        .path {{ font-family: monospace; color: #333; font-size: 14px; }}
        .summary {{ color: #666; font-size: 13px; margin-top: 4px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>OPAD API - Implemented Endpoints</h1>
        
        <h2>Articles Endpoints</h2>
        {articles_html}
        
        <h2>Jobs Endpoints</h2>
        {jobs_html}
        
        <h2>Health Endpoints</h2>
        {health_html}
        
        <h2>Other Endpoints</h2>
        {other_html}
        
        <p style="margin-top: 40px; color: #999; font-size: 12px;">
            Auto-generated from FastAPI app routes. Visit <a href="/docs">/docs</a> for interactive API documentation.
        </p>
    </div>
</body>
</html>"""
    
    return HTMLResponse(content=html)
