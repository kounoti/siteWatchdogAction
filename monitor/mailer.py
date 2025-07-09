"""
Gmail sender module for notification emails
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Tuple, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class GmailSender:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        
        # Get credentials from environment
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS')
        self.mail_to = os.getenv('MAIL_TO', '').split(',')
        
        # Validate configuration
        if not self.smtp_user or not self.smtp_pass:
            raise ValueError("SMTP_USER and SMTP_PASS environment variables must be set")
        
        if not self.mail_to or not self.mail_to[0]:
            raise ValueError("MAIL_TO environment variable must be set")
        
        # Clean up email addresses
        self.mail_to = [email.strip() for email in self.mail_to if email.strip()]
    
    def send_notification(self, changes: List[Tuple[str, Dict]]) -> None:
        """
        Send notification email about detected changes
        
        Args:
            changes: List of (url, changes_dict) tuples
        """
        try:
            # Create email message
            msg = self._create_email_message(changes)
            
            # Send email
            self._send_email(msg)
            
            logger.info(f"Notification email sent successfully to {len(self.mail_to)} recipients")
            
        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")
            raise
    
    def _create_email_message(self, changes: List[Tuple[str, Dict]]) -> MIMEMultipart:
        """Create HTML email message"""
        msg = MIMEMultipart('alternative')
        
        # Email headers
        msg['Subject'] = f"🔍 サイト更新検知通知 ({len(changes)}件)"
        msg['From'] = self.smtp_user
        msg['To'] = ', '.join(self.mail_to)
        
        # Create HTML content
        html_content = self._generate_html_content(changes)
        
        # Create plain text version
        text_content = self._generate_text_content(changes)
        
        # Attach both versions
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        
        msg.attach(part1)
        msg.attach(part2)
        
        return msg
    
    def _generate_html_content(self, changes: List[Tuple[str, Dict]]) -> str:
        """Generate HTML email content"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f0f8ff; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .site-block {{ border: 1px solid #ddd; margin: 15px 0; padding: 15px; border-radius: 5px; }}
                .site-url {{ font-weight: bold; color: #0066cc; margin-bottom: 10px; }}
                .change-item {{ margin: 8px 0; padding: 8px; background-color: #f9f9f9; border-radius: 3px; }}
                .added {{ color: #008000; }}
                .removed {{ color: #cc0000; }}
                .modified {{ color: #ff6600; }}
                .pdf-link {{ background-color: #fff0f0; padding: 5px; margin: 3px 0; border-radius: 3px; }}
                .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🔍 サイト更新検知通知</h2>
                <p><strong>検知時刻:</strong> {timestamp}</p>
                <p><strong>更新サイト数:</strong> {len(changes)}件</p>
            </div>
        """
        
        for url, change_data in changes:
            html += self._generate_site_change_html(url, change_data)
        
        html += """
            <div class="footer">
                <p>このメールは GitHub Actions によって自動送信されました。</p>
                <p>🤖 Generated with Claude Code</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _generate_site_change_html(self, url: str, change_data: Dict) -> str:
        """Generate HTML for a single site's changes"""
        changes = change_data.get('changes', {})
        
        html = f"""
        <div class="site-block">
            <div class="site-url">📄 <a href="{url}">{url}</a></div>
        """
        
        # Content changes
        if changes.get('content_changed'):
            text_change = changes.get('text_length_change', 0)
            direction = "増加" if text_change > 0 else "減少"
            html += f'<div class="change-item modified">📝 コンテンツが変更されました (文字数: {abs(text_change)}{direction})</div>'
        
        # PDF changes
        if 'pdf_changes' in changes:
            pdf_changes = changes['pdf_changes']
            
            if 'added' in pdf_changes:
                html += '<div class="change-item added">📄 <strong>新しいPDFファイル:</strong></div>'
                for pdf in pdf_changes['added']:
                    html += f'<div class="pdf-link added">+ <a href="{pdf["url"]}">{pdf["text"] or "PDF"}</a></div>'
            
            if 'removed' in pdf_changes:
                html += '<div class="change-item removed">📄 <strong>削除されたPDFファイル:</strong></div>'
                for pdf in pdf_changes['removed']:
                    html += f'<div class="pdf-link removed">- {pdf["text"] or "PDF"}</div>'
        
        # Link changes
        if 'link_changes' in changes:
            link_changes = changes['link_changes']
            
            if 'added' in link_changes:
                html += f'<div class="change-item added">🔗 新しいリンク: {len(link_changes["added"])}個</div>'
            
            if 'removed' in link_changes:
                html += f'<div class="change-item removed">🔗 削除されたリンク: {len(link_changes["removed"])}個</div>'
        
        # Image changes
        if 'image_changes' in changes:
            image_changes = changes['image_changes']
            
            if 'added' in image_changes:
                html += f'<div class="change-item added">🖼️ 新しい画像: {len(image_changes["added"])}個</div>'
            
            if 'removed' in image_changes:
                html += f'<div class="change-item removed">🖼️ 削除された画像: {len(image_changes["removed"])}個</div>'
        
        # Update indicators
        if changes.get('update_indicators_changed'):
            html += '<div class="change-item modified">🔄 更新インジケーターが変更されました</div>'
        
        # Initial setup
        if changes.get('type') == 'initial':
            html += '<div class="change-item">🆕 初回監視設定が完了しました</div>'
        
        html += '</div>'
        
        return html
    
    def _generate_text_content(self, changes: List[Tuple[str, Dict]]) -> str:
        """Generate plain text email content"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        text = f"""
サイト更新検知通知

検知時刻: {timestamp}
更新サイト数: {len(changes)}件

"""
        
        for url, change_data in changes:
            text += f"URL: {url}\\n"
            
            changes_dict = change_data.get('changes', {})
            
            if changes_dict.get('content_changed'):
                text += "- コンテンツが変更されました\\n"
            
            if 'pdf_changes' in changes_dict:
                pdf_changes = changes_dict['pdf_changes']
                
                if 'added' in pdf_changes:
                    text += f"- 新しいPDFファイル: {len(pdf_changes['added'])}個\\n"
                
                if 'removed' in pdf_changes:
                    text += f"- 削除されたPDFファイル: {len(pdf_changes['removed'])}個\\n"
            
            if 'link_changes' in changes_dict:
                link_changes = changes_dict['link_changes']
                
                if 'added' in link_changes:
                    text += f"- 新しいリンク: {len(link_changes['added'])}個\\n"
                
                if 'removed' in link_changes:
                    text += f"- 削除されたリンク: {len(link_changes['removed'])}個\\n"
            
            if changes_dict.get('type') == 'initial':
                text += "- 初回監視設定が完了しました\\n"
            
            text += "\\n"
        
        text += """
---
このメールは GitHub Actions によって自動送信されました。
🤖 Generated with Claude Code
"""
        
        return text
    
    def _send_email(self, msg: MIMEMultipart) -> None:
        """Send email via SMTP"""
        try:
            # Create SMTP session
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()  # Enable TLS
            server.login(self.smtp_user, self.smtp_pass)
            
            # Send email
            text = msg.as_string()
            server.sendmail(self.smtp_user, self.mail_to, text)
            server.quit()
            
        except Exception as e:
            logger.error(f"SMTP error: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.quit()
            logger.info("SMTP connection test successful")
            return True
        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False