"""
HTTP fetcher module with retry functionality
"""
import requests
import time
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class SiteFetcher:
    def __init__(self, timeout: int = 30, max_retries: int = 3, retry_delay: int = 1):
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # Set up session with reasonable defaults
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def fetch(self, url: str) -> Optional[str]:
        """
        Fetch content from URL with retry logic
        
        Args:
            url: URL to fetch
            
        Returns:
            HTML content as string, or None if failed
        """
        if not self._is_valid_url(url):
            logger.error(f"Invalid URL format: {url}")
            return None
        
        for attempt in range(self.max_retries + 1):
            try:
                logger.debug(f"Fetching {url} (attempt {attempt + 1}/{self.max_retries + 1})")
                
                response = self.session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                # Check if request was successful
                response.raise_for_status()
                
                # Check content type
                content_type = response.headers.get('content-type', '').lower()
                if 'text/html' not in content_type and 'application/xhtml' not in content_type:
                    logger.warning(f"Non-HTML content type for {url}: {content_type}")
                
                logger.info(f"Successfully fetched {url} ({len(response.text)} chars)")
                return response.text
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed for {url} (attempt {attempt + 1}): {e}")
                
                if attempt < self.max_retries:
                    sleep_time = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.info(f"Retrying {url} in {sleep_time} seconds...")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Max retries exceeded for {url}")
                    return None
            
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                return None
        
        return None
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format"""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and parsed.scheme in ['http', 'https']
        except Exception:
            return False
    
    def get_response_info(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get response metadata without downloading full content
        
        Args:
            url: URL to check
            
        Returns:
            Dictionary with response metadata
        """
        try:
            response = self.session.head(url, timeout=self.timeout)
            return {
                'status_code': response.status_code,
                'content_type': response.headers.get('content-type'),
                'content_length': response.headers.get('content-length'),
                'last_modified': response.headers.get('last-modified'),
                'etag': response.headers.get('etag')
            }
        except Exception as e:
            logger.error(f"Failed to get response info for {url}: {e}")
            return None