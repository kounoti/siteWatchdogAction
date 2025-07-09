#!/usr/bin/env python3
"""
Site monitoring main module
"""
import os
import sys
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from .fetcher import SiteFetcher
from .detector import ChangeDetector
from .mailer import GmailSender

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SiteMonitor:
    def __init__(self, urls_file: str = "urls.txt", state_dir: str = "monitor/state"):
        self.urls_file = urls_file
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(exist_ok=True)
        
        self.fetcher = SiteFetcher()
        self.detector = ChangeDetector(self.state_dir)
        self.mailer = GmailSender()
    
    def load_urls(self) -> List[str]:
        """Load URLs from file"""
        try:
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            logger.info(f"Loaded {len(urls)} URLs from {self.urls_file}")
            return urls
        except FileNotFoundError:
            logger.error(f"URLs file not found: {self.urls_file}")
            return []
    
    def process_url(self, url: str) -> Optional[Tuple[str, Dict]]:
        """Process a single URL and return change information"""
        try:
            logger.info(f"Processing URL: {url}")
            
            # Fetch current content
            content = self.fetcher.fetch(url)
            if not content:
                logger.warning(f"Failed to fetch content from {url}")
                return None
            
            # Detect changes
            changes = self.detector.detect_changes(url, content)
            
            if changes:
                logger.info(f"Changes detected for {url}")
                return url, changes
            else:
                logger.info(f"No changes detected for {url}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return None
    
    def run(self) -> None:
        """Main monitoring loop"""
        urls = self.load_urls()
        if not urls:
            logger.error("No URLs to monitor")
            return
        
        changes_detected = []
        
        for url in urls:
            result = self.process_url(url)
            if result:
                changes_detected.append(result)
        
        if changes_detected:
            logger.info(f"Total changes detected: {len(changes_detected)}")
            
            # Send notification email
            try:
                self.mailer.send_notification(changes_detected)
                logger.info("Notification email sent successfully")
            except Exception as e:
                logger.error(f"Failed to send notification: {e}")
        else:
            logger.info("No changes detected across all monitored sites")


def main():
    """Main entry point"""
    try:
        monitor = SiteMonitor()
        monitor.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()