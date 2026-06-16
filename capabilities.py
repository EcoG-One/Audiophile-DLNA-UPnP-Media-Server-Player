import re

class BrowserCapabilities:
    @staticmethod
    def needs_alac_transcoding(user_agent: str, codec: str) -> bool:
        """Determines if the client requires ALAC to be transcoded to FLAC."""
        if codec.lower() != 'alac':
            return False
            
        if not user_agent:
            return True # Play it safe for unknown clients
            
        # Safari detection: UA contains 'Safari' but NOT Chrome, Chromium, or Edge
        is_safari = (
            'Safari' in user_agent and 
            'Chrome' not in user_agent and 
            'Chromium' not in user_agent and 
            'Edg' not in user_agent
        )
        
        # If it's Safari, no transcode needed. Otherwise, transcode ALAC to FLAC.
        return not is_safari