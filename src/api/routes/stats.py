"""Database statistics API routes."""

import logging
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

# Add src to path
# stats.py is at /app/src/api/routes/stats.py
# src is at /app/src, so we go up 3 levels
_src_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_src_path))

from utils.mongodb import get_mongodb_client, get_database_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["stats"])


def _check_mongodb_connection() -> None:
    """Check MongoDB connection and raise if unavailable."""
    if not get_mongodb_client():
        raise HTTPException(status_code=503, detail="Database service unavailable")


def _format_bytes(bytes_val: int) -> str:
    """Format bytes to human-readable string."""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.2f} KB"
    return f"{bytes_val / (1024 * 1024):.2f} MB"


def _format_number(num: int) -> str:
    """Format number with thousand separators."""
    return f"{num:,}"


def _render_stats_html(stats: dict) -> HTMLResponse:
    """Render database statistics as HTML page."""
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Database Statistics - OPAD</title>
        <script src="https://cdn.tailwindcss.com"></script>
    </head>
    <body class="bg-gray-50 p-8">
        <div class="max-w-4xl mx-auto">
            <div class="mb-6">
                <h1 class="text-3xl font-bold text-gray-900 mb-2">Database Statistics</h1>
                <p class="text-gray-600">MongoDB collection statistics and storage information</p>
            </div>

            <div class="bg-white rounded-lg shadow-lg overflow-hidden">
                <div class="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6">
                    <h2 class="text-2xl font-semibold mb-2">{stats.get('collection', 'articles')}</h2>
                    <p class="text-blue-100">Collection Overview</p>
                </div>

                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                        <div class="bg-blue-50 rounded-lg p-4 border border-blue-200">
                            <div class="text-sm text-blue-600 font-medium mb-1">Total Documents</div>
                            <div class="text-3xl font-bold text-blue-900">{_format_number(stats.get('total_documents', 0))}</div>
                        </div>
                        <div class="bg-green-50 rounded-lg p-4 border border-green-200">
                            <div class="text-sm text-green-600 font-medium mb-1">Active Documents</div>
                            <div class="text-3xl font-bold text-green-900">{_format_number(stats.get('active_documents', 0))}</div>
                        </div>
                        <div class="bg-red-50 rounded-lg p-4 border border-red-200">
                            <div class="text-sm text-red-600 font-medium mb-1">Deleted Documents</div>
                            <div class="text-3xl font-bold text-red-900">{_format_number(stats.get('deleted_documents', 0))}</div>
                        </div>
                    </div>

                    <div class="mb-8">
                        <h3 class="text-xl font-semibold text-gray-900 mb-4">Storage Information</h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                                <div class="text-sm text-gray-600 font-medium mb-1">Data Size</div>
                                <div class="text-2xl font-bold text-gray-900">
                                    {stats.get('data_size_mb', 0):.2f} MB
                                </div>
                                <div class="text-xs text-gray-500 mt-1">
                                    {_format_bytes(stats.get('data_size_bytes', 0))}
                                </div>
                            </div>
                            <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                                <div class="text-sm text-gray-600 font-medium mb-1">Index Size</div>
                                <div class="text-2xl font-bold text-gray-900">
                                    {stats.get('index_size_mb', 0):.2f} MB
                                </div>
                                <div class="text-xs text-gray-500 mt-1">
                                    {_format_bytes(stats.get('index_size_bytes', 0))}
                                </div>
                            </div>
                            <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                                <div class="text-sm text-gray-600 font-medium mb-1">Storage Size</div>
                                <div class="text-2xl font-bold text-gray-900">
                                    {stats.get('storage_size_mb', 0):.2f} MB
                                </div>
                                <div class="text-xs text-gray-500 mt-1">
                                    {_format_bytes(stats.get('storage_size_bytes', 0))}
                                </div>
                            </div>
                            <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                                <div class="text-sm text-gray-600 font-medium mb-1">Total Size</div>
                                <div class="text-2xl font-bold text-gray-900">
                                    {stats.get('total_size_mb', 0):.2f} MB
                                </div>
                                <div class="text-xs text-gray-500 mt-1">
                                    {_format_bytes((stats.get('data_size_bytes', 0) or 0) + (stats.get('index_size_bytes', 0) or 0))}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="mb-8">
                        <h3 class="text-xl font-semibold text-gray-900 mb-4">Document Statistics</h3>
                        <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                            <div class="text-sm text-gray-600 font-medium mb-1">Average Document Size</div>
                            <div class="text-2xl font-bold text-gray-900">
                                {_format_bytes(stats.get('avg_document_size_bytes', 0))}
                            </div>
                        </div>
                    </div>

                    <div class="mb-8">
                        <h3 class="text-xl font-semibold text-gray-900 mb-4">Indexes ({stats.get('indexes', 0)})</h3>
                        <div class="space-y-3">
    """
    
    for idx in stats.get('index_details', []):
        idx_name = idx.get('name', 'unknown')
        idx_keys = idx.get('keys', {})
        keys_str = ', '.join([f"{k} ({'asc' if v > 0 else 'desc'})" for k, v in idx_keys.items()])
        html += f"""
                            <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                                <div class="text-sm font-medium text-gray-900">{idx_name}</div>
                                <div class="text-xs text-gray-500 mt-1">{keys_str}</div>
                            </div>
        """
    
    html += """
                        </div>
                    </div>
                </div>
            </div>

            <div class="mt-6 text-center">
                <button onclick="window.location.reload()" class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    Refresh Statistics
                </button>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)


@router.get("")
async def get_database_stats_endpoint():
    """Get MongoDB database statistics.
    
    Returns information about collection size, index size, document counts, etc.
    Useful for debugging disk space issues.
    
    Returns HTML page for browser requests.
    """
    _check_mongodb_connection()
    
    stats = get_database_stats()
    if not stats:
        raise HTTPException(status_code=503, detail="Failed to retrieve database statistics")
    
    return _render_stats_html(stats)
