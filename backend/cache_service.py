"""
DuckDB-based persistent caching service for legal analysis responses
Provides fast, file-based caching that persists across sessions
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import duckdb
from pathlib import Path

from legal_agent import LegalAnalysisResponse, Country


class DuckDBCache:
    """DuckDB-based persistent cache for legal analysis responses"""
    
    def __init__(self, db_path: str = "legal_cache.duckdb"):
        """
        Initialize DuckDB cache
        
        Args:
            db_path: Path to the DuckDB database file
        """
        self.db_path = db_path
        self.conn = None
        
        # TTL settings based on confidence level (in days)
        self.ttl_mapping = {
            "High": 180,    # 6 months for high confidence
            "Medium": 90,   # 3 months for medium confidence
            "Low": 30,      # 1 month for low confidence
        }
        
        self._initialize_database()
    
    def _get_connection(self):
        """Get database connection, create if needed"""
        if self.conn is None:
            self.conn = duckdb.connect(self.db_path)
        return self.conn
    
    def _initialize_database(self):
        """Create the cache table if it doesn't exist"""
        conn = self._get_connection()
        
        # Create the main cache table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS legal_cache (
                cache_key VARCHAR PRIMARY KEY,
                survey_id VARCHAR NOT NULL,
                country VARCHAR NOT NULL,
                model VARCHAR NOT NULL,
                question_text TEXT NOT NULL,
                criteria TEXT NOT NULL,
                response_data JSON NOT NULL,
                confidence_level VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        
        # Create indexes for faster lookups
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_survey_country_model 
            ON legal_cache(survey_id, country, model)
        """)
        
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at 
            ON legal_cache(expires_at)
        """)
        
        # Clean up expired entries on startup
        self._cleanup_expired_entries()
        
        print(f"✅ DuckDB cache initialized: {self.db_path}")
    
    def _generate_cache_key(self, survey_id: str, question: str, criteria: str, country: str, model: str) -> str:
        """Generate a unique cache key"""
        content = f"{survey_id}:{question.strip()}:{criteria.strip()}:{country}:{model}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _calculate_expiry(self, confidence_level: str) -> datetime:
        """Calculate expiry datetime based on confidence level"""
        days = self.ttl_mapping.get(confidence_level, 30)  
        return datetime.now() + timedelta(days=days)
    
    def _cleanup_expired_entries(self):
        """Remove expired entries from cache"""
        conn = self._get_connection()
        
        result = conn.execute("""
            DELETE FROM legal_cache 
            WHERE expires_at < ?
        """, [datetime.now()]).fetchone()
        
        if result and result[0] > 0:
            print(f"🧹 Cleaned up {result[0]} expired cache entries")
    
    def get_cached_response(
        self, 
        survey_id: str, 
        question: str, 
        criteria: str, 
        country: str, 
        model: str
    ) -> Optional[LegalAnalysisResponse]:
        """
        Retrieve cached response if it exists and hasn't expired
        
        Returns:
            LegalAnalysisResponse if found, None otherwise
        """
        cache_key = self._generate_cache_key(survey_id, question, criteria, country, model)
        conn = self._get_connection()
        
        try:
            result = conn.execute("""
                SELECT response_data, expires_at 
                FROM legal_cache 
                WHERE cache_key = ? AND expires_at > ?
            """, [cache_key, datetime.now()]).fetchone()
            
            if not result:
                print(f"❌ Cache MISS: {survey_id} - {country} - {model}")
                return None
            
            response_data, expires_at = result
            
            # Parse JSON response data
            response_dict = json.loads(response_data) if isinstance(response_data, str) else response_data
            
            # Convert back to LegalAnalysisResponse
            legal_response = LegalAnalysisResponse(
                survey_id=response_dict['survey_id'],
                country=Country(response_dict['country']),
                question=response_dict['question'],
                answer=response_dict['answer'],
                legal_basis=response_dict['legal_basis'],
                additional_notes=response_dict.get('additional_notes'),
                confidence_level=response_dict['confidence_level'],
                is_cached=True  # 👈 ADD THIS LINE!
            )
            
            print(f"🎯 Cache HIT: {survey_id} - {country} - {model} (expires: {expires_at.strftime('%Y-%m-%d')})")
            return legal_response
            
        except Exception as e:
            print(f"❌ Error retrieving from cache: {e}")
            return None
    
    def store_response(
        self,
        survey_id: str,
        question: str,
        criteria: str,
        country: str,
        model: str,
        response: LegalAnalysisResponse
    ):
        """Store a legal analysis response in the cache"""
        cache_key = self._generate_cache_key(survey_id, question, criteria, country, model)
        expires_at = self._calculate_expiry(response.confidence_level)
        conn = self._get_connection()
        
        # Convert LegalAnalysisResponse to dict for JSON storage
        response_data = {
            'survey_id': response.survey_id,
            'country': response.country.value,
            'question': response.question,
            'answer': response.answer,
            'legal_basis': response.legal_basis,
            'additional_notes': response.additional_notes,
            'confidence_level': response.confidence_level
        }
        
        try:
            # Use INSERT OR REPLACE to handle duplicates
            conn.execute("""
                INSERT OR REPLACE INTO legal_cache (
                    cache_key, survey_id, country, model, question_text, 
                    criteria, response_data, confidence_level, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                cache_key,
                survey_id,
                country,
                model,
                question,
                criteria,
                json.dumps(response_data),
                response.confidence_level,
                datetime.now(),
                expires_at
            ])
            
            ttl_days = self.ttl_mapping.get(response.confidence_level, 30)
            print(f"💾 Cached response: {survey_id} - {country} - {model} (TTL: {ttl_days} days)")
            
        except Exception as e:
            print(f"❌ Error storing response in cache: {e}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        conn = self._get_connection()
        
        try:
            # Total cached responses
            total_count = conn.execute("SELECT COUNT(*) FROM legal_cache").fetchone()[0]
            
            # Active (non-expired) responses
            active_count = conn.execute("""
                SELECT COUNT(*) FROM legal_cache WHERE expires_at > ?
            """, [datetime.now()]).fetchone()[0]
            
            # Confidence level distribution
            confidence_stats = conn.execute("""
                SELECT confidence_level, COUNT(*) 
                FROM legal_cache 
                WHERE expires_at > ?
                GROUP BY confidence_level
            """, [datetime.now()]).fetchall()
            
            confidence_dist = {level: count for level, count in confidence_stats}
            
            # Model usage distribution
            model_stats = conn.execute("""
                SELECT model, COUNT(*) 
                FROM legal_cache 
                WHERE expires_at > ?
                GROUP BY model
            """, [datetime.now()]).fetchall()
            
            model_dist = {model: count for model, count in model_stats}
            
            # Country distribution
            country_stats = conn.execute("""
                SELECT country, COUNT(*) 
                FROM legal_cache 
                WHERE expires_at > ?
                GROUP BY country
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """, [datetime.now()]).fetchall()
            
            country_dist = {country: count for country, count in country_stats}
            
            # Database file size
            db_size = Path(self.db_path).stat().st_size / 1024 / 1024  # MB
            
            return {
                'database_file': self.db_path,
                'database_size_mb': round(db_size, 2),
                'total_responses': total_count,
                'active_responses': active_count,
                'expired_responses': total_count - active_count,
                'confidence_distribution': confidence_dist,
                'model_distribution': model_dist,
                'top_countries': country_dist
            }
            
        except Exception as e:
            print(f"❌ Error getting cache stats: {e}")
            return {'error': str(e)}
    
    def invalidate_survey(self, survey_id: str) -> int:
        """
        Invalidate all cached responses for a specific survey
        
        Returns:
            Number of entries invalidated
        """
        conn = self._get_connection()
        
        try:
            result = conn.execute("""
                DELETE FROM legal_cache WHERE survey_id = ?
            """, [survey_id]).fetchone()
            
            count = result[0] if result else 0
            print(f"🗑️  Invalidated {count} cached responses for survey: {survey_id}")
            return count
            
        except Exception as e:
            print(f"❌ Error invalidating survey cache: {e}")
            return 0
    
    def invalidate_country_model(self, country: str, model: str) -> int:
        """
        Invalidate all cached responses for a specific country-model combination
        
        Returns:
            Number of entries invalidated
        """
        conn = self._get_connection()
        
        try:
            result = conn.execute("""
                DELETE FROM legal_cache WHERE country = ? AND model = ?
            """, [country, model]).fetchone()
            
            count = result[0] if result else 0
            print(f"🗑️  Invalidated {count} cached responses for {country} - {model}")
            return count
            
        except Exception as e:
            print(f"❌ Error invalidating country-model cache: {e}")
            return 0
    
    def get_cached_surveys_for_country(self, country: str, model: str) -> List[str]:
        """Get list of survey IDs that have cached responses for a country-model combination"""
        conn = self._get_connection()
        
        try:
            results = conn.execute("""
                SELECT DISTINCT survey_id 
                FROM legal_cache 
                WHERE country = ? AND model = ? AND expires_at > ?
                ORDER BY survey_id
            """, [country, model, datetime.now()]).fetchall()
            
            return [row[0] for row in results]
            
        except Exception as e:
            print(f"❌ Error getting cached surveys: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None


# Global cache instance
cache = DuckDBCache() 