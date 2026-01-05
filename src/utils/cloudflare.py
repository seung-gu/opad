"""Cloudflare R2 storage utilities."""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


try:
    import boto3  # type: ignore[import-untyped]
    from botocore.config import Config  # type: ignore[import-untyped]
except ImportError:
    boto3 = None  # type: ignore[assignment]
    Config = None  # type: ignore[assignment]

load_dotenv()

# R2 credentials
R2_BUCKET_NAME = os.getenv('R2_BUCKET_NAME', '')
R2_ACCOUNT_ID = os.getenv('R2_ACCOUNT_ID', '')
R2_ACCESS_KEY_ID = os.getenv('R2_ACCESS_KEY_ID', '')
R2_SECRET_ACCESS_KEY = os.getenv('R2_SECRET_ACCESS_KEY', '')

# Public URL for CSV files (no auth needed)
R2_PUBLIC_URL = os.getenv('R2_PUBLIC_URL', '')

# Default paths for OPAD (change these as needed)
R2_DIRECTORY = 'public'
ARTICLE_FILENAME = 'adapted_reading_material.md'
DEFAULT_ARTICLE_PATH = f'{R2_DIRECTORY}/{ARTICLE_FILENAME}'


def _get_s3_client():
    """Get S3 client for R2."""
    if not boto3 or not Config:
        logger.warning(f"boto3 or Config not available: boto3={boto3}, Config={Config}")
        return None
    
    try:
        return boto3.client(
            's3',
            endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )
    except Exception as e:
        logger.error(f"Error creating S3 client: {e}")
        return None


def upload_to_cloud(file_path: Path | str, cloud_path: str | None = None) -> bool:
    """Upload file or string content to Cloudflare R2.
    
    Args:
        file_path: Local file path (Path) or string content (str)
        cloud_path: Cloud storage path (if None, uses DEFAULT_ARTICLE_PATH for str, or file_path.name for Path)
        
    Returns:
        True if successful, False otherwise (never raises exceptions)
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return False
    
    cloud_path = cloud_path or (file_path.name if isinstance(file_path, Path) else DEFAULT_ARTICLE_PATH)
    
    try:
        if isinstance(file_path, str):
            s3_client.put_object(
                Bucket=R2_BUCKET_NAME,
                Key=cloud_path,
                Body=file_path.encode('utf-8'),
                ContentType='text/markdown'
            )
        else:
            if not file_path.exists():
                return False
            s3_client.upload_file(str(file_path), R2_BUCKET_NAME, cloud_path)
        return True
    except Exception:
        return False


def download_from_cloud(cloud_path: str | None = None, local_path: Path | None = None) -> str | bool | None:
    """Download file from Cloudflare R2.
    
    Args:
        cloud_path: Cloud storage path (if None, uses DEFAULT_ARTICLE_PATH)
        local_path: Local file path to save to. If None, returns content as string.
        
    Returns:
        File content as string if local_path is None, True if saved successfully, None on error
    """
    s3_client = _get_s3_client()
    if not s3_client:
        logger.warning("S3 client not available for download")
        return None
    
    cloud_path = cloud_path or DEFAULT_ARTICLE_PATH
    logger.info(f"Downloading from R2: bucket={R2_BUCKET_NAME}, key={cloud_path}")
    
    try:
        if local_path is None:
            response = s3_client.get_object(Bucket=R2_BUCKET_NAME, Key=cloud_path)
            content = response['Body'].read().decode('utf-8')
            logger.info(f"Successfully downloaded {len(content)} bytes from R2")
            return content
        else:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            s3_client.download_file(R2_BUCKET_NAME, cloud_path, str(local_path))
            logger.info(f"Successfully downloaded to {local_path}")
            return True
    except Exception as e:
        logger.error(f"Error downloading from R2 (bucket={R2_BUCKET_NAME}, key={cloud_path}): {e}")
        return None


def file_exists_in_cloud(cloud_path: str) -> bool:
    """Check if file exists in Cloudflare R2.
    
    Args:
        cloud_path: Cloud storage path
        
    Returns:
        True if file exists, False otherwise (never raises exceptions)
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return False
    
    try:
        s3_client.head_object(Bucket=R2_BUCKET_NAME, Key=cloud_path)
        return True
    except Exception:
        return False


def upload_file_to_public_cloud(file_path: Path, cloud_path: str) -> bool:
    """Upload file to public bucket (requires auth).
    
    Args:
        file_path: Local file path
        cloud_path: Cloud storage path
        
    Returns:
        True if successful, False otherwise
    """
    if not boto3 or not Config:
        return False
    
    if not file_path.exists():
        return False
    
    try:
        s3_client = boto3.client(
            's3',
            endpoint_url=f'https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com',
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            config=Config(signature_version='s3v4')
        )
        
        # Determine content type based on file extension
        content_type = 'application/octet-stream'
        if file_path.suffix.lower() == '.png':
            content_type = 'image/png'
        elif file_path.suffix.lower() == '.jpg' or file_path.suffix.lower() == '.jpeg':
            content_type = 'image/jpeg'
        elif file_path.suffix.lower() == '.csv':
            content_type = 'text/csv'
        elif file_path.suffix.lower() == '.md':
            content_type = 'text/markdown'
        
        s3_client.upload_file(
            str(file_path),
            R2_BUCKET_NAME,
            cloud_path,
            ExtraArgs={'ContentType': content_type}
        )
        return True
    except Exception as e:
        logger.error(f"Error uploading file to public cloud: {e}")
        return False


def list_cloud_files(prefix: str = '') -> list[str]:
    """List files in Cloudflare R2 bucket with given prefix.
    
    Args:
        prefix: Prefix to filter files (e.g., 'estimates/' for PNG files, 'reports/' for PDFs)
        
    Returns:
        List of file paths (keys) in cloud storage
    """
    s3_client = _get_s3_client()
    if not s3_client:
        return []
    
    try:
        files = []
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=R2_BUCKET_NAME, Prefix=prefix):
            if 'Contents' in page:
                for obj in page['Contents']:
                    files.append(obj['Key'])
        return files
    except Exception as e:
        logger.error(f"Error listing cloud files (bucket={R2_BUCKET_NAME}, prefix={prefix}): {e}")
        return []

