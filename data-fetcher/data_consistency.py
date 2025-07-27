"""
Data Consistency Validation System
Ensures data integrity across the baseball simulation database
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

import asyncpg

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Individual validation issue"""
    check_name: str
    severity: ValidationSeverity
    description: str
    affected_records: int
    details: Dict[str, Any]
    timestamp: datetime


@dataclass
class ValidationReport:
    """Complete validation report"""
    report_id: str
    timestamp: datetime
    season: Optional[int]
    total_checks: int
    issues_found: List[ValidationIssue]
    summary: Dict[str, int]


class DataConsistencyValidator:
    """Comprehensive data consistency validation"""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
        self.validation_rules = self._initialize_validation_rules()
    
    def _initialize_validation_rules(self) -> Dict[str, Dict]:
        """Initialize validation rules and thresholds"""
        return {
            'team_consistency': {
                'description': 'Team data consistency across tables',
                'severity': ValidationSeverity.CRITICAL,
                'threshold': 0  # No inconsistencies allowed
            },
            'player_stats_totals': {
                'description': 'Player stats aggregate correctly',
                'severity': ValidationSeverity.ERROR,
                'threshold': 0.01  # 1% tolerance
            },
            'game_score_consistency': {
                'description': 'Game scores match individual stats',
                'severity': ValidationSeverity.ERROR,
                'threshold': 0
            },
            'pitch_count_validation': {
                'description': 'Pitch counts align with game data',
                'severity': ValidationSeverity.WARNING,
                'threshold': 5  # 5 pitch tolerance
            },
            'statistical_boundaries': {
                'description': 'Statistics within realistic bounds',
                'severity': ValidationSeverity.WARNING,
                'threshold': 0
            },
            'temporal_consistency': {
                'description': 'Dates and sequences are logical',
                'severity': ValidationSeverity.ERROR,
                'threshold': 0
            },
            'referential_integrity': {
                'description': 'Foreign key relationships intact',
                'severity': ValidationSeverity.CRITICAL,
                'threshold': 0
            }
        }
    
    async def run_full_validation(self, season: Optional[int] = None) -> ValidationReport:
        """Run comprehensive data consistency validation"""
        logger.info(f"Starting data consistency validation for season {season}")
        
        report_id = f"validation_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        issues = []
        
        # Run all validation checks
        validation_methods = [
            self._validate_team_consistency,
            self._validate_player_stats_totals,
            self._validate_game_score_consistency,
            self._validate_pitch_counts,
            self._validate_statistical_boundaries,
            self._validate_temporal_consistency,
            self._validate_referential_integrity
        ]
        
        for method in validation_methods:
            try:
                method_issues = await method(season)
                issues.extend(method_issues)
            except Exception as e:
                logger.error(f"Error in validation method {method.__name__}: {e}")
                issues.append(ValidationIssue(
                    check_name=method.__name__,
                    severity=ValidationSeverity.CRITICAL,
                    description=f"Validation check failed: {str(e)}",
                    affected_records=0,
                    details={'error': str(e)},
                    timestamp=datetime.utcnow()
                ))
        
        # Generate summary
        summary = self._generate_summary(issues)
        
        report = ValidationReport(
            report_id=report_id,
            timestamp=datetime.utcnow(),
            season=season,
            total_checks=len(validation_methods),
            issues_found=issues,
            summary=summary
        )
        
        # Store report in database
        await self._store_validation_report(report)
        
        logger.info(f"Validation completed. Found {len(issues)} issues across {len(validation_methods)} checks")
        return report
    
    async def _validate_team_consistency(self, season: Optional[int]) -> List[ValidationIssue]:
        """Validate team data consistency across tables"""
        issues = []
        
        # Check teams referenced in games exist
        orphaned_games = await self.db_pool.fetch("""
            SELECT g.id, g.game_id, g.home_team_id, g.away_team_id
            FROM games g
            LEFT JOIN teams ht ON g.home_team_id = ht.id
            LEFT JOIN teams at ON g.away_team_id = at.id
            WHERE ht.id IS NULL OR at.id IS NULL
            AND ($1 IS NULL OR g.season = $1)
            LIMIT 100
        """, season)
        
        if orphaned_games:
            issues.append(ValidationIssue(
                check_name="team_consistency",
                severity=ValidationSeverity.CRITICAL,
                description=f"Games reference non-existent teams",
                affected_records=len(orphaned_games),
                details={'orphaned_games': [dict(g) for g in orphaned_games]},
                timestamp=datetime.utcnow()
            ))
        
        # Check players reference valid teams
        orphaned_players = await self.db_pool.fetch("""
            SELECT p.id, p.player_id, p.first_name, p.last_name, p.team_id
            FROM players p
            LEFT JOIN teams t ON p.team_id = t.id
            WHERE t.id IS NULL AND p.status = 'active'
            LIMIT 100
        """)
        
        if orphaned_players:
            issues.append(ValidationIssue(
                check_name="team_consistency",
                severity=ValidationSeverity.ERROR,
                description=f"Active players reference non-existent teams",
                affected_records=len(orphaned_players),
                details={'orphaned_players': [dict(p) for p in orphaned_players]},
                timestamp=datetime.utcnow()
            ))
        
        return issues
    
    async def _validate_player_stats_totals(self, season: Optional[int]) -> List[ValidationIssue]:
        """Validate player statistics aggregate correctly"""
        issues = []
        
        if season is None:
            return issues
        
        # Check batting stats consistency
        batting_inconsistencies = await self.db_pool.fetch("""
            WITH stat_check AS (
                SELECT 
                    player_id,
                    (aggregated_stats->>'H')::int as hits,
                    (aggregated_stats->>'2B')::int as doubles,
                    (aggregated_stats->>'3B')::int as triples,
                    (aggregated_stats->>'HR')::int as home_runs,
                    (aggregated_stats->>'AB')::int as at_bats,
                    (aggregated_stats->>'BB')::int as walks,
                    (aggregated_stats->>'HBP')::int as hit_by_pitch,
                    (aggregated_stats->>'SF')::int as sac_flies,
                    (aggregated_stats->>'PA')::int as plate_appearances
                FROM player_season_aggregates
                WHERE season = $1 AND stats_type = 'batting'
                AND aggregated_stats ? 'H'
            )
            SELECT *
            FROM stat_check
            WHERE 
                hits < (doubles + triples + home_runs)  -- Hits can't be less than extra base hits
                OR plate_appearances < (at_bats + walks + hit_by_pitch + sac_flies)  -- PA logic
                OR hits > at_bats  -- Hits can't exceed at-bats
            LIMIT 50
        """, season)
        
        if batting_inconsistencies:
            issues.append(ValidationIssue(
                check_name="player_stats_totals",
                severity=ValidationSeverity.ERROR,
                description="Batting statistics contain logical inconsistencies",
                affected_records=len(batting_inconsistencies),
                details={'inconsistent_batting': [dict(b) for b in batting_inconsistencies]},
                timestamp=datetime.utcnow()
            ))
        
        # Check pitching stats consistency
        pitching_inconsistencies = await self.db_pool.fetch("""
            WITH stat_check AS (
                SELECT 
                    player_id,
                    (aggregated_stats->>'IP')::float as innings_pitched,
                    (aggregated_stats->>'H')::int as hits_allowed,
                    (aggregated_stats->>'ER')::int as earned_runs,
                    (aggregated_stats->>'BB')::int as walks_allowed,
                    (aggregated_stats->>'SO')::int as strikeouts,
                    (aggregated_stats->>'W')::int as wins,
                    (aggregated_stats->>'L')::int as losses,
                    (aggregated_stats->>'GS')::int as games_started,
                    (aggregated_stats->>'G')::int as games_pitched
                FROM player_season_aggregates
                WHERE season = $1 AND stats_type = 'pitching'
                AND aggregated_stats ? 'IP'
            )
            SELECT *
            FROM stat_check
            WHERE 
                games_started > games_pitched  -- Can't start more games than pitched
                OR innings_pitched < 0  -- Negative innings impossible
                OR earned_runs < 0  -- Negative ER impossible
            LIMIT 50
        """, season)
        
        if pitching_inconsistencies:
            issues.append(ValidationIssue(
                check_name="player_stats_totals",
                severity=ValidationSeverity.ERROR,
                description="Pitching statistics contain logical inconsistencies",
                affected_records=len(pitching_inconsistencies),
                details={'inconsistent_pitching': [dict(p) for p in pitching_inconsistencies]},
                timestamp=datetime.utcnow()
            ))
        
        return issues
    
    async def _validate_game_score_consistency(self, season: Optional[int]) -> List[ValidationIssue]:
        """Validate game scores match player statistics"""
        issues = []
        
        # This would require aggregating individual player stats to game totals
        # Simplified check for now - verify final scores exist
        games_missing_scores = await self.db_pool.fetch("""
            SELECT id, game_id, game_date, status
            FROM games
            WHERE (final_score_home IS NULL OR final_score_away IS NULL)
            AND status = 'completed'
            AND ($1 IS NULL OR season = $1)
            LIMIT 100
        """, season)
        
        if games_missing_scores:
            issues.append(ValidationIssue(
                check_name="game_score_consistency",
                severity=ValidationSeverity.WARNING,
                description="Completed games missing final scores",
                affected_records=len(games_missing_scores),
                details={'games_missing_scores': [dict(g) for g in games_missing_scores]},
                timestamp=datetime.utcnow()
            ))
        
        return issues
    
    async def _validate_pitch_counts(self, season: Optional[int]) -> List[ValidationIssue]:
        """Validate pitch counts align with game data"""
        issues = []
        
        # Check for unrealistic pitch counts
        extreme_pitch_counts = await self.db_pool.fetch("""
            WITH game_pitch_counts AS (
                SELECT 
                    game_id,
                    COUNT(*) as total_pitches,
                    COUNT(DISTINCT pitcher_id) as pitcher_count
                FROM pitches
                WHERE ($1 IS NULL OR EXTRACT(YEAR FROM game_date) = $1)
                GROUP BY game_id
            )
            SELECT *
            FROM game_pitch_counts
            WHERE total_pitches < 100 OR total_pitches > 400  -- Realistic bounds
            LIMIT 50
        """, season)
        
        if extreme_pitch_counts:
            issues.append(ValidationIssue(
                check_name="pitch_count_validation",
                severity=ValidationSeverity.WARNING,
                description="Games with unusual pitch counts detected",
                affected_records=len(extreme_pitch_counts),
                details={'extreme_pitch_counts': [dict(p) for p in extreme_pitch_counts]},
                timestamp=datetime.utcnow()
            ))
        
        return issues
    
    async def _validate_statistical_boundaries(self, season: Optional[int]) -> List[ValidationIssue]:
        """Validate statistics are within realistic bounds"""
        issues = []
        
        # Check for impossible batting averages
        impossible_averages = await self.db_pool.fetch("""
            SELECT 
                player_id,
                (aggregated_stats->>'AVG')::float as avg,
                (aggregated_stats->>'OBP')::float as obp,
                (aggregated_stats->>'SLG')::float as slg
            FROM player_season_aggregates
            WHERE season = $1 AND stats_type = 'batting'
            AND (
                (aggregated_stats->>'AVG')::float > 1.0 OR
                (aggregated_stats->>'OBP')::float > 1.0 OR
                (aggregated_stats->>'SLG')::float > 4.0 OR
                (aggregated_stats->>'AVG')::float < 0.0
            )
            LIMIT 50
        """, season)
        
        if impossible_averages:
            issues.append(ValidationIssue(
                check_name="statistical_boundaries",
                severity=ValidationSeverity.ERROR,
                description="Players with impossible batting statistics",
                affected_records=len(impossible_averages),
                details={'impossible_averages': [dict(a) for a in impossible_averages]},
                timestamp=datetime.utcnow()
            ))
        
        return issues
    
    async def _validate_temporal_consistency(self, season: Optional[int]) -> List[ValidationIssue]:
        """Validate dates and temporal sequences"""
        issues = []
        
        # Check for future game dates
        future_games = await self.db_pool.fetch("""
            SELECT id, game_id, game_date
            FROM games
            WHERE game_date > CURRENT_DATE + INTERVAL '1 year'
            AND ($1 IS NULL OR season = $1)
            LIMIT 50
        """, season)
        
        if future_games:
            issues.append(ValidationIssue(
                check_name="temporal_consistency",
                severity=ValidationSeverity.WARNING,
                description="Games scheduled far in the future",
                affected_records=len(future_games),
                details={'future_games': [dict(g) for g in future_games]},
                timestamp=datetime.utcnow()
            ))
        
        # Check for players with impossible birth dates
        age_issues = await self.db_pool.fetch("""
            SELECT id, player_id, first_name, last_name, birth_date
            FROM players
            WHERE birth_date > CURRENT_DATE - INTERVAL '15 years'  -- Too young
            OR birth_date < CURRENT_DATE - INTERVAL '65 years'     -- Too old for active
            AND status = 'active'
            LIMIT 50
        """)
        
        if age_issues:
            issues.append(ValidationIssue(
                check_name="temporal_consistency",
                severity=ValidationSeverity.WARNING,
                description="Players with unusual ages detected",
                affected_records=len(age_issues),
                details={'age_issues': [dict(a) for a in age_issues]},
                timestamp=datetime.utcnow()
            ))
        
        return issues
    
    async def _validate_referential_integrity(self, season: Optional[int]) -> List[ValidationIssue]:
        """Validate foreign key relationships"""
        issues = []
        
        # Check player_season_aggregates references
        orphaned_stats = await self.db_pool.fetch("""
            SELECT psa.id, psa.player_id, psa.season, psa.stats_type
            FROM player_season_aggregates psa
            LEFT JOIN players p ON psa.player_id = p.id
            WHERE p.id IS NULL
            AND ($1 IS NULL OR psa.season = $1)
            LIMIT 100
        """, season)
        
        if orphaned_stats:
            issues.append(ValidationIssue(
                check_name="referential_integrity",
                severity=ValidationSeverity.CRITICAL,
                description="Season statistics reference non-existent players",
                affected_records=len(orphaned_stats),
                details={'orphaned_stats': [dict(s) for s in orphaned_stats]},
                timestamp=datetime.utcnow()
            ))
        
        return issues
    
    def _generate_summary(self, issues: List[ValidationIssue]) -> Dict[str, int]:
        """Generate summary statistics for validation report"""
        summary = {
            'total_issues': len(issues),
            'critical': 0,
            'error': 0,
            'warning': 0,
            'info': 0
        }
        
        for issue in issues:
            summary[issue.severity.value] += 1
        
        return summary
    
    async def _store_validation_report(self, report: ValidationReport):
        """Store validation report in database"""
        try:
            # Create validation reports table if not exists
            await self.db_pool.execute("""
                CREATE TABLE IF NOT EXISTS data_validation_reports (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    report_id VARCHAR(100) UNIQUE NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    season INTEGER,
                    total_checks INTEGER,
                    issues_found JSONB,
                    summary JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """)
            
            # Store the report
            await self.db_pool.execute("""
                INSERT INTO data_validation_reports 
                (report_id, timestamp, season, total_checks, issues_found, summary)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, 
                report.report_id,
                report.timestamp,
                report.season,
                report.total_checks,
                json.dumps([issue.__dict__ for issue in report.issues_found], default=str),
                json.dumps(report.summary)
            )
            
            logger.info(f"Stored validation report {report.report_id}")
            
        except Exception as e:
            logger.error(f"Failed to store validation report: {e}")
    
    async def get_validation_history(self, limit: int = 10) -> List[Dict]:
        """Get recent validation reports"""
        try:
            reports = await self.db_pool.fetch("""
                SELECT report_id, timestamp, season, total_checks, summary
                FROM data_validation_reports
                ORDER BY timestamp DESC
                LIMIT $1
            """, limit)
            
            return [dict(report) for report in reports]
            
        except Exception as e:
            logger.error(f"Failed to get validation history: {e}")
            return []
    
    async def auto_fix_issues(self, report: ValidationReport) -> Dict[str, int]:
        """Attempt to automatically fix common data issues"""
        fix_count = {'fixed': 0, 'failed': 0}
        
        for issue in report.issues_found:
            try:
                if issue.check_name == "team_consistency" and issue.severity == ValidationSeverity.ERROR:
                    # Could implement auto-fixing orphaned players by setting team to NULL
                    pass
                elif issue.check_name == "statistical_boundaries":
                    # Could implement statistical clamping to realistic bounds
                    pass
                
                # Add more auto-fix logic as needed
                
            except Exception as e:
                logger.error(f"Failed to auto-fix issue {issue.check_name}: {e}")
                fix_count['failed'] += 1
        
        return fix_count


async def run_daily_consistency_check(db_pool: asyncpg.Pool, season: Optional[int] = None):
    """Run daily data consistency validation"""
    validator = DataConsistencyValidator(db_pool)
    
    try:
        report = await validator.run_full_validation(season)
        
        # Log summary
        logger.info(f"Daily consistency check completed:")
        logger.info(f"  Total issues: {report.summary['total_issues']}")
        logger.info(f"  Critical: {report.summary['critical']}")
        logger.info(f"  Errors: {report.summary['error']}")
        logger.info(f"  Warnings: {report.summary['warning']}")
        
        # Alert on critical issues
        if report.summary['critical'] > 0:
            logger.critical(f"CRITICAL DATA ISSUES DETECTED: {report.summary['critical']} issues found")
        
        return report
        
    except Exception as e:
        logger.error(f"Daily consistency check failed: {e}")
        raise