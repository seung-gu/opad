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

from utils.mongodb import get_mongodb_client, get_database_stats, get_vocabulary_stats
from api.job_queue import get_job_stats

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
async def get_database_stats_endpoint():
    """Get MongoDB database and Redis statistics.
    
    Returns information about collection size, index size, document counts, job statistics, etc.
    Useful for debugging disk space issues and job processing.
    """
    _check_mongodb_connection()
    
    stats = get_database_stats()
    if not stats:
        raise HTTPException(status_code=503, detail="Failed to retrieve database statistics")
    
    # Get job statistics from Redis
    job_stats = get_job_stats()
    if job_stats:
        stats.update({f'job_{k}': v for k, v in job_stats.items()})
    
    # Get vocabulary statistics
    vocab_stats = get_vocabulary_stats()
    if vocab_stats:
        stats.update({f'vocab_{k}': v for k, v in vocab_stats.items()})
    
    return _render_stats_html(stats)


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

            <!-- Articles Collection Section -->
            <div class="bg-white rounded-lg shadow-lg overflow-hidden">
                <div class="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-6">
                    <h2 class="text-2xl font-semibold mb-2">Articles (MongoDB)</h2>
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
                        <h3 class="text-xl font-semibold text-gray-900 mb-4">Status Breakdown</h3>
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div class="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
                                <div class="text-sm text-yellow-600 font-medium mb-1">Running</div>
                                <div class="text-2xl font-bold text-yellow-900">{_format_number(stats.get('running_documents', 0))}</div>
                            </div>
                            <div class="bg-emerald-50 rounded-lg p-4 border border-emerald-200">
                                <div class="text-sm text-emerald-600 font-medium mb-1">Completed</div>
                                <div class="text-2xl font-bold text-emerald-900">{_format_number(stats.get('completed_documents', 0))}</div>
                            </div>
                            <div class="bg-orange-50 rounded-lg p-4 border border-orange-200">
                                <div class="text-sm text-orange-600 font-medium mb-1">Failed</div>
                                <div class="text-2xl font-bold text-orange-900">{_format_number(stats.get('failed_documents', 0))}</div>
                            </div>
                        </div>
                    </div>

                    <div class="mb-8">
                        <h3 class="text-xl font-semibold text-gray-900 mb-4">Collection Storage Information</h3>
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
                                    {_format_bytes(stats.get('total_size_bytes', 0))}
                                    <span class="text-gray-400 ml-1">(Storage + Index)</span>
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
                </div>
            </div>

            <!-- Job Queue Section -->
            <div class="bg-white rounded-lg shadow-lg overflow-hidden mt-8">
                <div class="bg-gradient-to-r from-purple-600 to-purple-700 text-white p-6">
                    <h2 class="text-2xl font-semibold mb-2">Jobs (Redis)</h2>
                    <p class="text-purple-100">Real-time job processing statistics</p>
                </div>

                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
                        <div class="bg-blue-50 rounded-lg p-4 border border-blue-200">
                            <div class="text-sm text-blue-600 font-medium mb-1">Queued</div>
                            <div class="text-3xl font-bold text-blue-900">{_format_number(stats.get('job_queued', 0))}</div>
                        </div>
                        <div class="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
                            <div class="text-sm text-yellow-600 font-medium mb-1">Running</div>
                            <div class="text-3xl font-bold text-yellow-900">{_format_number(stats.get('job_running', 0))}</div>
                        </div>
                        <div class="bg-emerald-50 rounded-lg p-4 border border-emerald-200">
                            <div class="text-sm text-emerald-600 font-medium mb-1">Completed</div>
                            <div class="text-3xl font-bold text-emerald-900">{_format_number(stats.get('job_completed', 0))}</div>
                        </div>
                        <div class="bg-orange-50 rounded-lg p-4 border border-orange-200">
                            <div class="text-sm text-orange-600 font-medium mb-1">Failed</div>
                            <div class="text-3xl font-bold text-orange-900">{_format_number(stats.get('job_failed', 0))}</div>
                        </div>
                    </div>

                    <div class="mb-8">
                        <h3 class="text-xl font-semibold text-gray-900 mb-4">Job Statistics</h3>
                        <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                            <div class="text-sm text-gray-600 font-medium mb-1">Total Jobs</div>
                            <div class="text-2xl font-bold text-gray-900">
                                {_format_number(stats.get('job_total', 0))}
                            </div>
                            <div class="text-xs text-gray-500 mt-1">
                                24h TTL, auto-expires
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Vocabulary Collection Section -->
            <div class="bg-white rounded-lg shadow-lg overflow-hidden mt-8">
                <div class="bg-gradient-to-r from-emerald-600 to-emerald-700 text-white p-6">
                    <h2 class="text-2xl font-semibold mb-2">Vocabularies (MongoDB)</h2>
                    <p class="text-emerald-100">Collection Overview</p>
                </div>

                <div class="p-6">
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                        <div class="bg-emerald-50 rounded-lg p-4 border border-emerald-200">
                            <div class="text-sm text-emerald-600 font-medium mb-1">Total Words</div>
                            <div class="text-3xl font-bold text-emerald-900">{_format_number(stats.get('vocab_total_documents', 0))}</div>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                            <div class="text-sm text-gray-600 font-medium mb-1">Data Size</div>
                            <div class="text-2xl font-bold text-gray-900">
                                {stats.get('vocab_data_size_mb', 0):.2f} MB
                            </div>
                        </div>
                        <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                            <div class="text-sm text-gray-600 font-medium mb-1">Total Size</div>
                            <div class="text-2xl font-bold text-gray-900">
                                {stats.get('vocab_total_size_mb', 0):.2f} MB
                            </div>
                        </div>
                    </div>

                    <div class="mb-8">
                        <h3 class="text-xl font-semibold text-gray-900 mb-4">By Language</h3>
                        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
"""
    
    # Add language breakdown if available
    vocab_by_language = stats.get('vocab_by_language', {})
    if vocab_by_language:
        for lang, count in sorted(vocab_by_language.items(), key=lambda x: x[1], reverse=True):
            html += f"""
                            <div class="bg-gray-50 rounded-lg p-4 border border-gray-200">
                                <div class="text-sm text-gray-600 font-medium mb-1">{lang}</div>
                                <div class="text-2xl font-bold text-gray-900">{_format_number(count)}</div>
                            </div>"""
    else:
        html += "                            <div class='text-gray-500 col-span-3 text-center py-4'>No vocabulary data available</div>"
    
    html += """
                        </div>
                    </div>
                </div>
            </div>

            <div class="mt-6 text-center space-x-4">
                <button onclick="window.location.reload()" class="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                    Refresh Statistics
                </button>
                <a href="/dictionary/stats" class="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors inline-block">
                    View Vocabulary List
                </a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html)
