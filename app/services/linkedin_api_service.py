"""
LinkedIn API service as an alternative data source.
Uses LinkedIn's official Marketing Developer Platform API when available.
"""
from typing import Optional, Dict, Any, List
import httpx
from config import settings


class LinkedInAPIService:
    """Service for accessing LinkedIn data via official API."""
    
    def __init__(self):
        self.base_url = "https://api.linkedin.com/rest"
        self.access_token: Optional[str] = None
        self.api_version = "202411"  # Latest version
        self.is_available = False
    
    async def initialize(self):
        """Initialize API service with access token if available."""
        # Check if we have API credentials
        if hasattr(settings, 'linkedin_api_token') and settings.linkedin_api_token:
            self.access_token = settings.linkedin_api_token
            self.is_available = True
            print("[OK] LinkedIn API service initialized")
        else:
            print("[INFO] LinkedIn API token not configured. API service will not be available.")
            print("[INFO] To use LinkedIn API, add LINKEDIN_API_TOKEN to .env file")
            self.is_available = False
    
    async def get_organization_by_vanity_name(self, vanity_name: str) -> Optional[Dict[str, Any]]:
        """
        Get organization data by vanity name using Organization Lookup API.
        
        Args:
            vanity_name: LinkedIn page vanity name (e.g., 'google')
            
        Returns:
            Organization data dictionary or None
        """
        if not self.is_available or not self.access_token:
            return None
        
        try:
            url = f"{self.base_url}/organizations"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "LinkedIn-Version": self.api_version,
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json"
            }
            params = {
                "q": "vanityName",
                "vanityName": vanity_name
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'elements' in data and len(data['elements']) > 0:
                        org = data['elements'][0]
                        return self._parse_organization_data(org)
                elif response.status_code == 403:
                    print(f"[WARNING] LinkedIn API access denied. Check API permissions.")
                elif response.status_code == 404:
                    print(f"[INFO] Organization '{vanity_name}' not found via API")
                else:
                    print(f"[WARNING] LinkedIn API returned status {response.status_code}")
        
        except Exception as e:
            print(f"[DEBUG] LinkedIn API error: {e}")
        
        return None
    
    async def get_organization_followers(self, organization_urn: str) -> Optional[int]:
        """
        Get organization follower count using Network Size API.
        
        Args:
            organization_urn: Organization URN (e.g., 'urn:li:organization:123456')
            
        Returns:
            Follower count or None
        """
        if not self.is_available or not self.access_token:
            return None
        
        try:
            url = f"{self.base_url}/networkSizes/{organization_urn}"
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "LinkedIn-Version": self.api_version,
                "X-Restli-Protocol-Version": "2.0.0",
                "Content-Type": "application/json"
            }
            params = {
                "edgeType": "COMPANY_FOLLOWED_BY_MEMBER"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get('firstDegreeSize')
        
        except Exception as e:
            print(f"[DEBUG] LinkedIn API followers error: {e}")
        
        return None
    
    def _parse_organization_data(self, org_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse LinkedIn API organization response to our format."""
        parsed = {
            "name": None,
            "description": None,
            "website": None,
            "industry": None,
            "location": None,
            "founded": None,
            "specialities": [],
            "linkedin_id": None,
        }
        
        # Extract name
        if 'name' in org_data:
            name_obj = org_data['name']
            if isinstance(name_obj, dict) and 'localized' in name_obj:
                parsed['name'] = list(name_obj['localized'].values())[0] if name_obj['localized'] else None
            elif isinstance(name_obj, str):
                parsed['name'] = name_obj
        elif 'localizedName' in org_data:
            parsed['name'] = org_data['localizedName']
        
        # Extract description
        if 'description' in org_data:
            desc_obj = org_data['description']
            if isinstance(desc_obj, dict) and 'localized' in desc_obj:
                parsed['description'] = list(desc_obj['localized'].values())[0] if desc_obj['localized'] else None
            elif isinstance(desc_obj, str):
                parsed['description'] = desc_obj
        
        # Extract website
        if 'website' in org_data:
            website_obj = org_data['website']
            if isinstance(website_obj, dict) and 'localized' in website_obj:
                parsed['website'] = list(website_obj['localized'].values())[0] if website_obj['localized'] else None
            elif isinstance(website_obj, str):
                parsed['website'] = website_obj
        elif 'localizedWebsite' in org_data:
            parsed['website'] = org_data['localizedWebsite']
        
        # Extract industry (comes as URN, would need lookup)
        if 'industries' in org_data and org_data['industries']:
            # Industry is a URN like "urn:li:industry:4"
            # For now, just store the URN
            parsed['industry'] = str(org_data['industries'][0])
        
        # Extract location
        if 'locations' in org_data and org_data['locations']:
            location = org_data['locations'][0]
            if 'address' in location:
                addr = location['address']
                location_parts = []
                if 'city' in addr:
                    location_parts.append(addr['city'])
                if 'geographicArea' in addr:
                    location_parts.append(addr['geographicArea'])
                if 'country' in addr:
                    location_parts.append(addr['country'])
                if location_parts:
                    parsed['location'] = ', '.join(location_parts)
        
        # Extract founded date
        if 'foundedOn' in org_data:
            founded = org_data['foundedOn']
            if isinstance(founded, dict) and 'year' in founded:
                parsed['founded'] = str(founded['year'])
            elif isinstance(founded, str):
                parsed['founded'] = founded
        
        # Extract specialities
        if 'specialties' in org_data:
            parsed['specialities'] = org_data['specialties']
        elif 'localizedSpecialties' in org_data:
            parsed['specialities'] = org_data['localizedSpecialties']
        
        # Extract LinkedIn ID
        if 'id' in org_data:
            parsed['linkedin_id'] = str(org_data['id'])
        
        return parsed
    
    async def enrich_page_data(self, page_id: str, existing_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich existing page data with API data if available.
        
        Args:
            page_id: LinkedIn page ID
            existing_data: Existing scraped data
            
        Returns:
            Enriched data dictionary
        """
        if not self.is_available:
            return existing_data
        
        # Try to get organization data from API
        api_data = await self.get_organization_by_vanity_name(page_id)
        
        if api_data:
            # Merge API data with existing data (API data takes precedence for non-null values)
            for key, value in api_data.items():
                if value and not existing_data.get(key):
                    existing_data[key] = value
            
            # Try to get follower count
            if api_data.get('linkedin_id'):
                org_urn = f"urn:li:organization:{api_data['linkedin_id']}"
                followers = await self.get_organization_followers(org_urn)
                if followers and not existing_data.get('total_followers'):
                    existing_data['total_followers'] = followers
            
            print(f"[INFO] Enriched {page_id} data with LinkedIn API")
        
        return existing_data


# Global instance
linkedin_api_service = LinkedInAPIService()
