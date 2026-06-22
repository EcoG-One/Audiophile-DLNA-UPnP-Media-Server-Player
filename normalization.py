import re
import unicodedata

class ArtistNormalizer:
    # Extensible list of articles across multiple languages
    ARTICLES = {'the', 'a', 'an', 'le', 'la', 'les', 'der', 'die', 'das', 'el', 'los', 'las'}
    
    @classmethod
    def normalize(cls, raw_name: str):
        """
        Takes a raw artist name and returns a tuple: (Canonical Display Name, Normalized Key)
        Example: "beatles, The" -> ("Beatles", "beatles")
        """
        if not raw_name or not raw_name.strip():
            return "Unknown Artist", "unknown_artist"
            
        # 1. Unicode Normalization (converts weird accented characters to standard forms)
        name = unicodedata.normalize('NFKD', raw_name).strip()
        
        # 2. Build dynamic regex patterns for articles
        articles_pattern = '|'.join(cls.ARTICLES)
        
        # Remove trailing articles (e.g., "Beatles, The" -> "Beatles")
        trailing_regex = re.compile(rf',\s*({articles_pattern})$', re.IGNORECASE)
        name = trailing_regex.sub('', name)
        
        # Remove leading articles (e.g., "The Beatles" -> "Beatles")
        leading_regex = re.compile(rf'^({articles_pattern})\s+', re.IGNORECASE)
        name = leading_regex.sub('', name)
        
        # 3. Clean up whitespace
        name = re.sub(r'\s+', ' ', name).strip()
        
        # 4. Generate the canonical matching key
        normalized_key = name.lower()
        
        # 5. Generate the Canonical Display Name
        # If the original name was entirely lowercase, we Title Case it.
        # Otherwise, we preserve the original intentional capitalization (e.g., "AC/DC", "deadmau5").
        if name.islower():
            display_name = name.title()
        else:
            display_name = name
            
        return display_name, normalized_key