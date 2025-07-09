"""
Change detection module for monitoring website changes
"""
import os
import json
import hashlib
import logging
from typing import Dict, Optional, List, Set
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re

logger = logging.getLogger(__name__)


class ChangeDetector:
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(exist_ok=True)
    
    def detect_changes(self, url: str, html_content: str) -> Optional[Dict]:
        """
        Detect changes in website content
        
        Args:
            url: URL being monitored
            html_content: Current HTML content
            
        Returns:
            Dictionary with change information, or None if no changes
        """
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract various content types
            current_state = self._extract_content_state(soup, url)
            
            # Load previous state
            previous_state = self._load_state(url)
            
            # Compare states
            changes = self._compare_states(previous_state, current_state)
            
            # Save current state
            self._save_state(url, current_state)
            
            if changes:
                return {
                    'url': url,
                    'changes': changes,
                    'timestamp': current_state['timestamp']
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting changes for {url}: {e}")
            return None
    
    def _extract_content_state(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract current state of website content"""
        import time
        
        # Extract PDF links
        pdf_links = self._extract_pdf_links(soup, url)
        
        # Extract text content (removing scripts, styles, etc.)
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()
        
        text_content = soup.get_text()
        text_content = re.sub(r'\s+', ' ', text_content).strip()
        
        # Extract links
        links = self._extract_links(soup, url)
        
        # Extract images
        images = self._extract_images(soup, url)
        
        # Extract specific elements that might indicate updates
        update_indicators = self._extract_update_indicators(soup)
        
        # Calculate content hash
        content_hash = hashlib.md5(text_content.encode('utf-8')).hexdigest()
        
        return {
            'timestamp': time.time(),
            'content_hash': content_hash,
            'text_length': len(text_content),
            'pdf_links': pdf_links,
            'links': links,
            'images': images,
            'update_indicators': update_indicators
        }
    
    def _extract_pdf_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract PDF links from page"""
        pdf_links = []
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            
            # Check if it's a PDF link
            if href.lower().endswith('.pdf') or 'pdf' in href.lower():
                pdf_links.append({
                    'url': absolute_url,
                    'text': link.get_text(strip=True),
                    'title': link.get('title', ''),
                    'hash': hashlib.md5(absolute_url.encode()).hexdigest()[:8]
                })
        
        return pdf_links
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract all links from page"""
        links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            absolute_url = urljoin(base_url, href)
            
            # Filter out unwanted links
            if not any(skip in absolute_url.lower() for skip in ['javascript:', 'mailto:', 'tel:']):
                links.append(absolute_url)
        
        return list(set(links))  # Remove duplicates
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract image URLs from page"""
        images = []
        
        for img in soup.find_all('img', src=True):
            src = img['src']
            absolute_url = urljoin(base_url, src)
            images.append(absolute_url)
        
        return list(set(images))  # Remove duplicates
    
    def _extract_update_indicators(self, soup: BeautifulSoup) -> Dict:
        """Extract elements that commonly indicate updates"""
        indicators = {}
        
        # Look for date/time elements
        date_elements = soup.find_all(['time', 'span', 'div'], 
                                     class_=re.compile(r'date|time|updated|modified', re.I))
        if date_elements:
            indicators['date_elements'] = [elem.get_text(strip=True) for elem in date_elements[:5]]
        
        # Look for "new" or "updated" badges
        new_elements = soup.find_all(text=re.compile(r'new|updated|追加|更新|変更', re.I))
        if new_elements:
            indicators['new_indicators'] = [elem.strip() for elem in new_elements[:10]]
        
        # Look for version numbers
        version_elements = soup.find_all(text=re.compile(r'version|v\d+|バージョン', re.I))
        if version_elements:
            indicators['version_indicators'] = [elem.strip() for elem in version_elements[:5]]
        
        return indicators
    
    def _compare_states(self, previous: Optional[Dict], current: Dict) -> Optional[Dict]:
        """Compare previous and current states to detect changes"""
        if not previous:
            return {
                'type': 'initial',
                'description': 'Initial monitoring setup'
            }
        
        changes = {}
        
        # Check content changes
        if previous['content_hash'] != current['content_hash']:
            changes['content_changed'] = True
            changes['text_length_change'] = current['text_length'] - previous['text_length']
        
        # Check PDF changes
        pdf_changes = self._compare_pdf_links(previous['pdf_links'], current['pdf_links'])
        if pdf_changes:
            changes['pdf_changes'] = pdf_changes
        
        # Check link changes
        link_changes = self._compare_lists(previous['links'], current['links'])
        if link_changes:
            changes['link_changes'] = link_changes
        
        # Check image changes
        image_changes = self._compare_lists(previous['images'], current['images'])
        if image_changes:
            changes['image_changes'] = image_changes
        
        # Check update indicators
        if previous['update_indicators'] != current['update_indicators']:
            changes['update_indicators_changed'] = True
        
        return changes if changes else None
    
    def _compare_pdf_links(self, previous: List[Dict], current: List[Dict]) -> Optional[Dict]:
        """Compare PDF links between states"""
        prev_hashes = {pdf['hash'] for pdf in previous}
        curr_hashes = {pdf['hash'] for pdf in current}
        
        added = curr_hashes - prev_hashes
        removed = prev_hashes - curr_hashes
        
        if added or removed:
            result = {}
            
            if added:
                result['added'] = [pdf for pdf in current if pdf['hash'] in added]
            
            if removed:
                result['removed'] = [pdf for pdf in previous if pdf['hash'] in removed]
            
            return result
        
        return None
    
    def _compare_lists(self, previous: List[str], current: List[str]) -> Optional[Dict]:
        """Compare two lists and return differences"""
        prev_set = set(previous)
        curr_set = set(current)
        
        added = curr_set - prev_set
        removed = prev_set - curr_set
        
        if added or removed:
            result = {}
            
            if added:
                result['added'] = list(added)
            
            if removed:
                result['removed'] = list(removed)
            
            return result
        
        return None
    
    def _get_state_file_path(self, url: str) -> Path:
        """Get state file path for URL"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return self.state_dir / f"state_{url_hash}.json"
    
    def _load_state(self, url: str) -> Optional[Dict]:
        """Load previous state from file"""
        state_file = self._get_state_file_path(url)
        
        try:
            if state_file.exists():
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading state for {url}: {e}")
        
        return None
    
    def _save_state(self, url: str, state: Dict) -> None:
        """Save current state to file"""
        state_file = self._get_state_file_path(url)
        
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving state for {url}: {e}")
    
    def cleanup_old_states(self, max_age_days: int = 30) -> None:
        """Remove old state files"""
        import time
        
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        for state_file in self.state_dir.glob("state_*.json"):
            try:
                if current_time - state_file.stat().st_mtime > max_age_seconds:
                    state_file.unlink()
                    logger.info(f"Removed old state file: {state_file}")
            except Exception as e:
                logger.error(f"Error removing old state file {state_file}: {e}")