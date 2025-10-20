from typing import Dict, Optional
import yaml
from backend.data_objects import AIModel, LegalQuery, Country, COUNTRY_LANGUAGES, Topic


def get_country_language(country: Country) -> tuple[str, str]:
    """Get the language name and code for a country"""
    return COUNTRY_LANGUAGES.get(country, ("English", "en"))


def create_country_name_mapping() -> Dict[str, Country]:
    """
    Create a mapping from various country name formats to Country enum values.
    Handles filename variations, Excel inconsistencies, etc.
    """
    mapping = {}
    
    # Direct mappings for your exact enum values
    for country in Country:
        mapping[country.value] = country
    
    # Add variations/aliases found in your Excel filenames
    aliases = {
        # Handle filename inconsistencies
        "Egypt, Arab Rep.": Country.EGYPT,  # Your enum value
        "Egypt": Country.EGYPT,  # Possible variation
        
        "United Kingdom": Country.UNITED_KINGDOM,
        "UK": Country.UNITED_KINGDOM,
        
        "United States": Country.UNITED_STATES,
        "USA": Country.UNITED_STATES,
        "US": Country.UNITED_STATES,
        
        "Antigua and Barbuda": Country.ANTIGUA_AND_BARBUDA,
        
        # Add more as you discover them
        "Saudi Arabia": Country.SAUDI_ARABIA,
        "KSA": Country.SAUDI_ARABIA,

        "El Salvador": Country.EL_SALVADOR,
        "Salvador": Country.EL_SALVADOR,
        
        "Bolivia": Country.BOLIVIA,
        "Bolivia (Plurinational State of)": Country.BOLIVIA,
        
        "Guyana": Country.GUYANA,
        
        "Ecuador": Country.ECUADOR,
        "Ecuadorean": Country.ECUADOR,
        
        "Nigeria": Country.NIGERIA,
        "Nigerian": Country.NIGERIA,
        
        "Egypt": Country.EGYPT,
        "Egyptian": Country.EGYPT,
        
        "France": Country.FRANCE,
        "French": Country.FRANCE,
        
        "Spain": Country.SPAIN,
        "Spanish": Country.SPAIN,
        
        "Germany": Country.GERMANY,
        "German": Country.GERMANY,
        
        "Canada": Country.CANADA,
        "Canadian": Country.CANADA,
    }
    
    mapping.update(aliases)
    return mapping


def create_topic_name_mapping() -> Dict[str, Topic]:
    """Create a mapping from various topic name formats to Topic enum values"""
    mapping = {}
    for topic in Topic:
        mapping[topic.value] = topic
    return mapping


def load_survey() -> Dict[str, LegalQuery]:
    """Load survey questions from YAML file"""
    try:
        with open('legal_surveys.yaml', 'r') as file:
            data = yaml.safe_load(file)
            surveys = {}
            for survey_id, survey_data in data['surveys'].items():
                surveys[survey_id] = LegalQuery(**survey_data)
            return surveys
    except FileNotFoundError:
        raise FileNotFoundError("legal_surveys.yaml file not found.")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing legal_surveys.yaml: {e}")
