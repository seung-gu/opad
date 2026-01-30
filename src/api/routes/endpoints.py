"""API endpoints listing endpoint."""

import logging
from collections import defaultdict
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["meta"])

# Tags to exclude from the listing (internal/docs)
EXCLUDED_TAGS = {"meta"}
EXCLUDED_PATHS = {"/docs", "/openapi.json", "/redoc"}


def group_endpoints_by_tag(endpoints: list[dict]) -> dict[str, list[dict]]:
    """
    Group endpoints by their tag.

    Args:
        endpoints: List of endpoint dicts with keys: method, path, summary, tags
                   Example: {"method": "GET", "path": "/usage/me", "summary": "...", "tags": ["usage"]}

    Returns:
        Dictionary mapping tag name to list of endpoints
        Example: {"usage": [{"method": "GET", "path": "/usage/me", ...}], "articles": [...]}

    Hints:
        - Use defaultdict(list) to avoid KeyError
        - Each endpoint may have multiple tags - pick the first one, or use "other" if empty
        - Filter out tags in EXCLUDED_TAGS
        - Sort endpoints within each group by (path, method)
    """
    mapping = defaultdict(list)

    for ep in endpoints:
        tag = ep["tags"][0] if ep["tags"] else "other"
        if tag not in EXCLUDED_TAGS:
            mapping[tag].append(ep)

    # Sort endpoints within each group by (path, method)
    for tag in mapping:
        mapping[tag].sort(key=lambda ep: (ep["path"], ep["method"]))

    return mapping

def get_sorted_tags(grouped: dict[str, list[dict]]) -> list[str]:
    """Return tags sorted alphabetically, with 'other' at the end."""
    tags = sorted(tag for tag in grouped if tag != "other")
    if "other" in grouped:
        tags.append("other")
    return tags


def format_endpoint(ep: dict) -> str:
    """Format a single endpoint as HTML."""
    # Extract first line of summary for clean display
    summary = ep["summary"].split("\n")[0].strip() if ep["summary"] else ""
    summary_html = f'<div class="summary">{summary}</div>' if summary else ""
    return f'<div class="endpoint"><span class="method {ep["method"]}">{ep["method"]}</span><span class="path">{ep["path"]}</span>{summary_html}</div>'


def format_tag_title(tag: str) -> str:
    """Convert tag name to display title."""
    return f"{tag.title()} Endpoints"


@router.get("/endpoints")
async def list_endpoints(request: Request):
    """List all implemented API endpoints.

    Returns HTML page showing all registered endpoints grouped by tag.
    """
    app = request.app

    # Collect all endpoints with their tags
    endpoints = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            # Skip excluded paths
            if route.path in EXCLUDED_PATHS:
                continue

            methods = [m for m in route.methods if m != 'HEAD']
            tags = getattr(route, 'tags', []) or []

            if methods:
                for method in methods:
                    endpoints.append({
                        'method': method,
                        'path': route.path,
                        'summary': getattr(route, 'summary', '') or getattr(route, 'description', ''),
                        'tags': tags
                    })

    # Group by tag dynamically
    grouped = group_endpoints_by_tag(endpoints)

    # Generate HTML sections dynamically
    sections_html = ""
    for tag in get_sorted_tags(grouped):
        eps = grouped[tag]
        eps_html = ''.join([format_endpoint(ep) for ep in eps])
        sections_html += f"""
        <h2>{format_tag_title(tag)}</h2>
        {eps_html}
"""

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
        {sections_html}
        <p style="margin-top: 40px; color: #999; font-size: 12px;">
            Auto-generated from FastAPI app routes. Visit <a href="/docs">/docs</a> for interactive API documentation.
        </p>
    </div>
</body>
</html>"""

    return HTMLResponse(content=html)
