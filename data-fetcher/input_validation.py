"""
Enhanced Input Validation and Sanitization
Comprehensive validation for all API inputs and data processing
"""

import re
import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union, Type, get_type_hints
from dataclasses import dataclass
from enum import Enum
import uuid
from functools import wraps
import html

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation error severity levels"""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationRule:
    """Individual validation rule"""
    field_name: str
    rule_type: str
    constraint: Any
    message: str
    severity: ValidationSeverity = ValidationSeverity.ERROR


@dataclass
class ValidationResult:
    """Result of validation check"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    sanitized_value: Any = None


class InputValidationError(Exception):
    """Raised when input validation fails"""
    def __init__(self, message: str, errors: List[str], field_name: str = ""):
        super().__init__(message)
        self.errors = errors
        self.field_name = field_name


class SecuritySanitizer:
    """Security-focused input sanitization"""
    
    # Common injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(union\s+select)",
        r"(drop\s+table)",
        r"(delete\s+from)",
        r"(insert\s+into)",
        r"(update\s+set)",
        r"(--)",
        r"(/\*.*\*/)",
        r"(;\s*drop)",
        r"(exec\s*\()",
        r"(script\s*>)"
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>"
    ]
    
    @classmethod
    def sanitize_string(cls, value: str, max_length: int = 1000, 
                       allow_html: bool = False) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            raise ValueError("Value must be a string")
        
        # Length check
        if len(value) > max_length:
            raise ValueError(f"String too long: {len(value)} > {max_length}")
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # SQL injection check
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potential SQL injection detected: {pattern}")
        
        # XSS check
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potential XSS detected: {pattern}")
        
        # HTML escape if not allowing HTML
        if not allow_html:
            value = html.escape(value)
        
        # Unicode normalization
        value = value.encode('utf-8', errors='ignore').decode('utf-8')
        
        return value.strip()
    
    @classmethod
    def sanitize_numeric(cls, value: Union[int, float, str], 
                        min_val: Optional[float] = None,
                        max_val: Optional[float] = None,
                        allow_negative: bool = True) -> Union[int, float]:
        """Sanitize numeric input"""
        try:
            if isinstance(value, str):
                # Remove non-numeric characters except decimal point and minus
                cleaned = re.sub(r'[^0-9.-]', '', value)
                if '.' in cleaned:
                    numeric_value = float(cleaned)
                else:
                    numeric_value = int(cleaned)
            else:
                numeric_value = value
        except (ValueError, TypeError):
            raise ValueError(f"Invalid numeric value: {value}")
        
        # Check for negative values
        if not allow_negative and numeric_value < 0:
            raise ValueError(f"Negative values not allowed: {numeric_value}")
        
        # Range checks
        if min_val is not None and numeric_value < min_val:
            raise ValueError(f"Value below minimum: {numeric_value} < {min_val}")
        
        if max_val is not None and numeric_value > max_val:
            raise ValueError(f"Value above maximum: {numeric_value} > {max_val}")
        
        return numeric_value


class BaseballValidator:
    """Baseball-specific validation rules"""
    
    # Valid baseball positions
    VALID_POSITIONS = {
        'P', 'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH', 'PH', 'PR'
    }
    
    # Valid leagues and divisions
    VALID_LEAGUES = {'AL', 'NL'}
    VALID_DIVISIONS = {'East', 'Central', 'West'}
    
    # Team abbreviation patterns
    TEAM_ABBREV_PATTERN = re.compile(r'^[A-Z]{2,4}$')
    
    # Statistical bounds
    STAT_BOUNDS = {
        'batting_average': (0.0, 1.0),
        'on_base_percentage': (0.0, 1.0),
        'slugging_percentage': (0.0, 4.0),  # Theoretical max is 4.0
        'era': (0.0, 50.0),  # ERA can be very high in small samples
        'whip': (0.0, 10.0),
        'fielding_percentage': (0.0, 1.0),
        'velocity': (40.0, 110.0),  # MPH
        'spin_rate': (0, 4000),  # RPM
        'exit_velocity': (0.0, 125.0),  # MPH
        'launch_angle': (-90.0, 90.0),  # Degrees
    }
    
    @classmethod
    def validate_season(cls, season: int) -> bool:
        """Validate baseball season year"""
        return 1876 <= season <= datetime.now().year + 1
    
    @classmethod
    def validate_position(cls, position: str) -> bool:
        """Validate baseball position"""
        return position.upper() in cls.VALID_POSITIONS
    
    @classmethod
    def validate_league(cls, league: str) -> bool:
        """Validate baseball league"""
        return league.upper() in cls.VALID_LEAGUES
    
    @classmethod
    def validate_division(cls, division: str) -> bool:
        """Validate baseball division"""
        return division in cls.VALID_DIVISIONS
    
    @classmethod
    def validate_team_abbreviation(cls, abbrev: str) -> bool:
        """Validate team abbreviation format"""
        return bool(cls.TEAM_ABBREV_PATTERN.match(abbrev.upper()))
    
    @classmethod
    def validate_player_id(cls, player_id: str) -> bool:
        """Validate player ID format"""
        try:
            # Check if it's a valid UUID
            uuid.UUID(player_id)
            return True
        except ValueError:
            # Check if it's a valid MLB ID (numeric)
            return player_id.isdigit() and len(player_id) <= 10
    
    @classmethod
    def validate_game_date(cls, game_date: Union[str, date, datetime]) -> bool:
        """Validate game date is reasonable"""
        if isinstance(game_date, str):
            try:
                parsed_date = datetime.fromisoformat(game_date).date()
            except ValueError:
                return False
        elif isinstance(game_date, datetime):
            parsed_date = game_date.date()
        elif isinstance(game_date, date):
            parsed_date = game_date
        else:
            return False
        
        # Baseball started in 1876, allow up to 1 year in future
        earliest = date(1876, 1, 1)
        latest = date.today().replace(year=date.today().year + 1)
        
        return earliest <= parsed_date <= latest
    
    @classmethod
    def validate_statistic(cls, stat_name: str, value: float) -> bool:
        """Validate a statistical value is within reasonable bounds"""
        if stat_name in cls.STAT_BOUNDS:
            min_val, max_val = cls.STAT_BOUNDS[stat_name]
            return min_val <= value <= max_val
        
        # Default validation for unknown stats
        return -1000 <= value <= 1000


class InputValidator:
    """Main input validation class"""
    
    def __init__(self):
        self.sanitizer = SecuritySanitizer()
        self.baseball_validator = BaseballValidator()
        self.validation_rules: Dict[str, List[ValidationRule]] = {}
    
    def add_validation_rule(self, rule: ValidationRule):
        """Add custom validation rule"""
        if rule.field_name not in self.validation_rules:
            self.validation_rules[rule.field_name] = []
        self.validation_rules[rule.field_name].append(rule)
    
    def validate_field(self, field_name: str, value: Any, 
                      field_type: Type = str, required: bool = True) -> ValidationResult:
        """Validate individual field"""
        errors = []
        warnings = []
        sanitized_value = value
        
        # Required field check
        if required and (value is None or value == ""):
            errors.append(f"Field '{field_name}' is required")
            return ValidationResult(False, errors, warnings)
        
        # Skip validation for None/empty optional fields
        if not required and (value is None or value == ""):
            return ValidationResult(True, errors, warnings, None)
        
        try:
            # Type-specific validation and sanitization
            if field_type == str:
                sanitized_value = self._validate_string(field_name, value)
            elif field_type == int:
                sanitized_value = self._validate_integer(field_name, value)
            elif field_type == float:
                sanitized_value = self._validate_float(field_name, value)
            elif field_type == bool:
                sanitized_value = self._validate_boolean(field_name, value)
            elif field_type == uuid.UUID:
                sanitized_value = self._validate_uuid(field_name, value)
            elif field_type == datetime:
                sanitized_value = self._validate_datetime(field_name, value)
            elif field_type == date:
                sanitized_value = self._validate_date(field_name, value)
            
            # Apply custom validation rules
            for rule in self.validation_rules.get(field_name, []):
                try:
                    if not self._apply_validation_rule(rule, sanitized_value):
                        if rule.severity == ValidationSeverity.ERROR:
                            errors.append(rule.message)
                        else:
                            warnings.append(rule.message)
                except Exception as e:
                    errors.append(f"Validation rule error: {str(e)}")
            
            # Baseball-specific validation
            self._apply_baseball_validation(field_name, sanitized_value, errors, warnings)
            
        except Exception as e:
            errors.append(f"Validation error for {field_name}: {str(e)}")
        
        is_valid = len(errors) == 0
        return ValidationResult(is_valid, errors, warnings, sanitized_value if is_valid else None)
    
    def _validate_string(self, field_name: str, value: Any) -> str:
        """Validate and sanitize string"""
        if not isinstance(value, str):
            value = str(value)
        
        # Determine max length based on field name
        max_length = self._get_max_length(field_name)
        
        return self.sanitizer.sanitize_string(value, max_length=max_length)
    
    def _validate_integer(self, field_name: str, value: Any) -> int:
        """Validate and sanitize integer"""
        min_val, max_val = self._get_numeric_bounds(field_name)
        return int(self.sanitizer.sanitize_numeric(value, min_val, max_val))
    
    def _validate_float(self, field_name: str, value: Any) -> float:
        """Validate and sanitize float"""
        min_val, max_val = self._get_numeric_bounds(field_name)
        return float(self.sanitizer.sanitize_numeric(value, min_val, max_val))
    
    def _validate_boolean(self, field_name: str, value: Any) -> bool:
        """Validate and sanitize boolean"""
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            lower_val = value.lower()
            if lower_val in ('true', '1', 'yes', 'on'):
                return True
            elif lower_val in ('false', '0', 'no', 'off'):
                return False
            else:
                raise ValueError(f"Invalid boolean value: {value}")
        elif isinstance(value, (int, float)):
            return bool(value)
        else:
            raise ValueError(f"Cannot convert {type(value)} to boolean")
    
    def _validate_uuid(self, field_name: str, value: Any) -> uuid.UUID:
        """Validate and sanitize UUID"""
        if isinstance(value, uuid.UUID):
            return value
        elif isinstance(value, str):
            try:
                return uuid.UUID(value)
            except ValueError:
                raise ValueError(f"Invalid UUID format: {value}")
        else:
            raise ValueError(f"Cannot convert {type(value)} to UUID")
    
    def _validate_datetime(self, field_name: str, value: Any) -> datetime:
        """Validate and sanitize datetime"""
        if isinstance(value, datetime):
            return value
        elif isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                raise ValueError(f"Invalid datetime format: {value}")
        else:
            raise ValueError(f"Cannot convert {type(value)} to datetime")
    
    def _validate_date(self, field_name: str, value: Any) -> date:
        """Validate and sanitize date"""
        if isinstance(value, date):
            return value
        elif isinstance(value, datetime):
            return value.date()
        elif isinstance(value, str):
            try:
                return datetime.fromisoformat(value).date()
            except ValueError:
                raise ValueError(f"Invalid date format: {value}")
        else:
            raise ValueError(f"Cannot convert {type(value)} to date")
    
    def _get_max_length(self, field_name: str) -> int:
        """Get maximum length for string fields"""
        length_map = {
            'player_id': 50,
            'team_id': 10,
            'game_id': 50,
            'first_name': 100,
            'last_name': 100,
            'name': 200,
            'abbreviation': 5,
            'position': 10,
            'league': 10,
            'division': 20,
            'description': 1000,
            'title': 500,
            'message': 2000
        }
        return length_map.get(field_name, 200)
    
    def _get_numeric_bounds(self, field_name: str) -> tuple:
        """Get numeric bounds for fields"""
        bounds_map = {
            'season': (1876, datetime.now().year + 1),
            'games_played': (0, 200),
            'at_bats': (0, 1000),
            'hits': (0, 500),
            'home_runs': (0, 100),
            'runs': (0, 300),
            'rbi': (0, 300),
            'walks': (0, 300),
            'strikeouts': (0, 400),
            'innings_pitched': (0, 400),
            'wins': (0, 30),
            'losses': (0, 30),
            'era': (0, 50),
            'whip': (0, 10),
            'velocity': (40, 110),
            'spin_rate': (0, 4000),
            'age': (15, 65),
            'limit': (1, 1000),
            'offset': (0, 100000)
        }
        return bounds_map.get(field_name, (None, None))
    
    def _apply_validation_rule(self, rule: ValidationRule, value: Any) -> bool:
        """Apply custom validation rule"""
        if rule.rule_type == "range":
            min_val, max_val = rule.constraint
            return min_val <= value <= max_val
        elif rule.rule_type == "regex":
            return bool(re.match(rule.constraint, str(value)))
        elif rule.rule_type == "in_list":
            return value in rule.constraint
        elif rule.rule_type == "custom":
            return rule.constraint(value)
        else:
            return True
    
    def _apply_baseball_validation(self, field_name: str, value: Any, 
                                 errors: List[str], warnings: List[str]):
        """Apply baseball-specific validation"""
        if field_name == "season" and isinstance(value, int):
            if not self.baseball_validator.validate_season(value):
                errors.append(f"Invalid season year: {value}")
        
        elif field_name == "position" and isinstance(value, str):
            if not self.baseball_validator.validate_position(value):
                errors.append(f"Invalid baseball position: {value}")
        
        elif field_name == "league" and isinstance(value, str):
            if not self.baseball_validator.validate_league(value):
                errors.append(f"Invalid league: {value}")
        
        elif field_name == "division" and isinstance(value, str):
            if not self.baseball_validator.validate_division(value):
                errors.append(f"Invalid division: {value}")
        
        elif field_name == "abbreviation" and isinstance(value, str):
            if not self.baseball_validator.validate_team_abbreviation(value):
                warnings.append(f"Unusual team abbreviation format: {value}")
        
        elif field_name in ("player_id", "game_id") and isinstance(value, str):
            if not self.baseball_validator.validate_player_id(value):
                errors.append(f"Invalid ID format: {value}")
        
        elif "date" in field_name.lower() and hasattr(value, 'date'):
            if not self.baseball_validator.validate_game_date(value):
                errors.append(f"Invalid date: {value}")


def validate_api_input(input_schema: Dict[str, Dict[str, Any]]):
    """Decorator for API endpoint input validation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            validator = InputValidator()
            validation_errors = []
            sanitized_params = {}
            
            # Extract function parameters
            func_signature = get_type_hints(func)
            
            for param_name, param_config in input_schema.items():
                param_type = param_config.get('type', str)
                required = param_config.get('required', True)
                
                # Get parameter value from kwargs
                param_value = kwargs.get(param_name)
                
                # Validate parameter
                result = validator.validate_field(
                    param_name, param_value, param_type, required
                )
                
                if not result.is_valid:
                    validation_errors.extend([f"{param_name}: {error}" for error in result.errors])
                else:
                    sanitized_params[param_name] = result.sanitized_value
            
            # Raise validation error if any issues found
            if validation_errors:
                raise InputValidationError(
                    "Input validation failed",
                    validation_errors
                )
            
            # Update kwargs with sanitized values
            kwargs.update(sanitized_params)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Common validation schemas
PLAYER_STATS_SCHEMA = {
    'player_id': {'type': str, 'required': True},
    'season': {'type': int, 'required': True},
    'stats_type': {'type': str, 'required': False}
}

LEADERBOARD_SCHEMA = {
    'season': {'type': int, 'required': True},
    'stat_name': {'type': str, 'required': False},
    'limit': {'type': int, 'required': False},
    'position': {'type': str, 'required': False}
}

TEAM_ROSTER_SCHEMA = {
    'team_id': {'type': str, 'required': True}
}

FETCH_REQUEST_SCHEMA = {
    'start_date': {'type': datetime, 'required': False},
    'end_date': {'type': datetime, 'required': False},
    'fetch_type': {'type': str, 'required': False},
    'season': {'type': int, 'required': False}
}