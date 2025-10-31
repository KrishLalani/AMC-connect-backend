import google.generativeai as genai
import json
import base64
from PIL import Image
import io
import os
from dotenv import load_dotenv
from pathlib import Path
import requests
from typing import Dict, Any, Union
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class MunicipalIssueDetector:
    """
    A system that analyzes images to detect municipal issues and categorize them
    by department, priority, and description using Google Gemini API.
    """
    
    def __init__(self, api_key: str):
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Define municipal departments and their typical issues
        self.departments = {
            'FIRE': [
                'fire', 'smoke', 'burning', 'flames', 'emergency', 'rescue',
                'explosion', 'blaze', 'scorch', 'alarm', 'firefighter'
            ],
            'WATER': [
                'water', 'flooding', 'leak', 'pipe', 'drainage', 'sewer', 'overflow',
                'wet road', 'sewage', 'contaminated water', 'broken pipe', 'manhole'
            ],
            'ELECTRIC': [
                'electric', 'power', 'cable', 'wire', 'pole', 'outage', 'transformer',
                'short circuit', 'live wire', 'street light', 'spark'
            ],
            'ROADS': [
                'road', 'pothole', 'pavement', 'street', 'traffic', 'sign', 'marking',
                'speed breaker', 'signal', 'barrier', 'crack', 'manhole cover'
            ],
            'WASTE': [
                'garbage', 'trash', 'waste', 'dumpster', 'litter', 'recycling',
                'overflowing bin', 'illegal dumping', 'dead animal', 'open garbage'
            ],
            'PARKS': [
                'park', 'tree', 'garden', 'playground', 'bench', 'maintenance',
                'broken swing', 'fallen tree', 'damaged slide', 'open well'
            ],
            'BUILDING': [
                'building', 'construction', 'structure', 'violation', 'permit',
                'broken wall', 'collapsed', 'unsafe building', 'crack', 'illegal work'
            ],
            'HEALTH': [
                'health', 'sanitation', 'pest', 'contamination', 'safety',
                'mosquito', 'dirty toilet', 'open defecation', 'septic tank', 'infection'
            ],
            'TRANSPORT': [
                'bus stop', 'shelter damage', 'vehicle damage', 'rail track', 'sign board',
                'auto stand', 'transport board', 'public bus'
            ],
            'TRAFFIC': [
                'congestion', 'signal not working', 'road block', 'illegal parking',
                'no entry', 'wrong side', 'accident'
            ],
            'EDUCATION': [
                'school', 'playground', 'broken desk', 'unsafe building', 'dirty classroom',
                'toilet school', 'open wiring'
            ],
            'CIVIC INFRASTRUCTURE': [
                'open manhole', 'unfinished construction', 'broken tap', 'non-functional toilet',
                'public facility broken', 'leaking roof'
            ],
            'COMMUNICATION': [
                'telecom pole', 'fiber wire', 'damaged antenna', 'communication wire',
                'internet cable', 'broken signal tower'
            ],
            'DISASTER RELIEF': [
                'earthquake', 'collapsed building', 'flood', 'waterlogging', 'relief camp',
                'emergency shelter', 'rescue operation'
            ]
        }

        
        # Priority levels
        self.priority_levels = {
            'CRITICAL': 'Immediate attention required - public safety risk',
            'HIGH': 'Urgent - should be addressed within 24 hours',
            'MEDIUM': 'Important - should be addressed within 1 week',
            'LOW': 'Minor issue - can be scheduled for routine maintenance'
        }
    
    def encode_image(self, image_path: str) -> str:
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Error encoding image: {e}")
            raise
    
    def load_image_from_url(self, image_url: str) -> Image.Image:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(image_url, headers=headers, timeout=10)
            response.raise_for_status()
            
            image = Image.open(io.BytesIO(response.content))
            return image
            
        except Exception as e:
            logger.error(f"Error loading image from URL: {e}")
            raise
    
    def analyze_image(self, image_source: Union[str, Image.Image]):
        try:
            # Handle different input types
            if isinstance(image_source, str):
                if image_source.startswith(('http://', 'https://')):
                    # It's a URL
                    image = self.load_image_from_url(image_source)
                    logger.info(f"Loaded image from URL: {image_source}")
                else:
                    # It's a local file path
                    image = Image.open(image_source)
                    logger.info(f"Loaded image from path: {image_source}")
            elif isinstance(image_source, Image.Image):
                # It's already a PIL Image
                image = image_source
                logger.info("Using provided PIL Image")
            else:
                raise ValueError("image_source must be a file path, URL, or PIL Image")
            
            # Ensure image is in RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Create detailed prompt for Gemini
            prompt = f"""
            Analyze this image for municipal issues and infrastructure problems that citizens would report to local government.
            
            FIRST, determine if there are any actual municipal/civic issues visible in the image:
            - Municipal issues include: fires, water leaks, road damage, electrical hazards, waste problems, park maintenance issues, building violations, health hazards
            - NOT municipal issues: personal items (phones, cars, food), people, animals, indoor scenes, shopping, entertainment, normal everyday objects
            
            If NO municipal issues are present, respond with exactly: "NON_CIVIC_ISSUE"
            
            If municipal issues ARE present, provide a JSON response with this structure:
            {{
                "department": "ONE OF: FIRE, WATER, ELECTRIC, ROADS, WASTE, PARKS, BUILDING, HEALTH",
                "priority": "ONE OF: CRITICAL, HIGH, MEDIUM, LOW",
                "description": "Detailed description of the issue visible in the image",
                "location_details": "Any visible location markers, street signs, or identifying features",
                "recommended_action": "Suggested action to resolve the issue",
                "safety_concern": "Yes/No - whether this poses immediate safety risk",
                "confidence_score": "0.0-1.0 - confidence in the analysis"
            }}
            
            CLASSIFICATION GUIDELINES:
            
            DEPARTMENTS:
            - FIRE: Fires, smoke, burning buildings, fire alarms, illegal burning
            - WATER: Leaks, flooding, pipe bursts, drainage blockages, water contamination
            - ELECTRIC: Exposed wires, transformer failure, pole damage, power outages
            - ROADS: Potholes, damaged pavements, traffic sign damage, signal failure
            - WASTE: Overflowing bins, uncollected trash, illegal dumps, dead animals
            - PARKS: Broken play equipment, overgrown trees, poor lighting, closed parks
            - BUILDING: Illegal construction, structural damage, safety violations
            - HEALTH: Mosquito breeding, open defecation, pests, dirty public areas
            - TRANSPORT: Broken bus stops, signage damage, illegal parking, vehicle safety
            - TRAFFIC: Blocked roads, reckless driving zones, traffic jam patterns
            - EDUCATION: Unsafe school infrastructure, unhygienic school environments
            - CIVIC INFRASTRUCTURE: Open manholes, unfinished public works, broken streetlights
            - COMMUNICATION: Damaged telecom poles, exposed fiber wires
            - DISASTER RELIEF: Collapsed buildings, flood zones, crowding after disaster
            
            PRIORITY LEVELS:
            - CRITICAL: Immediate danger to public safety (fires, major flooding, electrical hazards)
            - HIGH: Urgent issues that could become dangerous (water leaks, road damage)
            - MEDIUM: Issues that need attention but not immediately dangerous (minor repairs)
            - LOW: Routine maintenance items (cosmetic issues, minor inconveniences)
            
            Be strict about what constitutes a municipal issue. Personal items, indoor scenes, and normal everyday objects are NOT municipal issues.
            """
            
            # Generate response using Gemini
            response = self.model.generate_content([prompt, image])
            
            # Parse the response
            try:
                # Clean the response text to extract JSON
                response_text = response.text.strip()
                
                # Check if it's a non-civic issue
                if response_text == "NON_CIVIC_ISSUE" or "NON_CIVIC_ISSUE" in response_text:
                    logger.info(f"No municipal issue detected in image")
                    return "No Municipal Issue Detected - This appears to be a non-civic matter. Please upload images of infrastructure problems, public safety concerns, or municipal service issues."
                
                # Remove any markdown formatting if present
                if response_text.startswith('```json'):
                    response_text = response_text[7:]
                if response_text.endswith('```'):
                    response_text = response_text[:-3]
                
                # Parse JSON
                result = json.loads(response_text)
                
                # Validate and enhance the result
                result = self._validate_and_enhance_result(result)
                
                logger.info(f"Successfully analyzed image")
                return result
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                # Check if the raw response indicates no civic issue
                if any(keyword in response.text.lower() for keyword in ['no municipal', 'no civic', 'not a municipal', 'personal item', 'non-civic']):
                    return "No Municipal Issue Detected - This appears to be a non-civic matter. Please upload images of infrastructure problems, public safety concerns, or municipal service issues."
                # Return a fallback response
                return self._create_fallback_response(response.text)
                
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return f"Error: Unable to analyze image - {str(e)}"
    
    def _validate_and_enhance_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        # Ensure required fields exist
        required_fields = ['department', 'priority', 'description']
        for field in required_fields:
            if field not in result:
                result[field] = 'UNKNOWN'
        
        # Validate department
        valid_departments = list(self.departments.keys())
        if result['department'] not in valid_departments:
            result['department'] = 'BUILDING'  # Default fallback
        
        # Validate priority
        valid_priorities = list(self.priority_levels.keys())
        if result['priority'] not in valid_priorities:
            result['priority'] = 'MEDIUM'  # Default fallback
        
        # Add timestamp
        from datetime import datetime
        result['timestamp'] = datetime.now().isoformat()
        
        # Add status
        result['status'] = 'PENDING'
        
        return result
    
    def _create_fallback_response(self, raw_response: str) -> Dict[str, Any]:
        return {
            'department': 'BUILDING',
            'priority': 'MEDIUM',
            'description': raw_response[:200] + '...' if len(raw_response) > 200 else raw_response,
            'location_details': 'Not specified',
            'recommended_action': 'Manual review required',
            'safety_concern': 'Unknown',
            'confidence_score': 0.5,
            'timestamp': datetime.now().isoformat(),
            'status': 'PENDING',
            'note': 'Fallback response - manual review recommended'
        }

# Utility function to call from Flask or any API layer
def detect_municipal_issue(image_url: str) -> Union[Dict[str, Any], str]:

    try:
        API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
        if not API_KEY:
            return "Error: Google Gemini API key not found."

        detector = MunicipalIssueDetector(API_KEY)
        result = detector.analyze_image(image_url)
        return result

    except Exception as e:
        return {
            "error": str(e),
            "message": "Failed to analyze the image. Please check the URL or server logs."
        }
