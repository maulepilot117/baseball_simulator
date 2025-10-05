"""
Unit tests for stats calculator module
"""
import pytest
from stats_calculator import (
    calculate_batting_stats,
    calculate_pitching_stats,
    calculate_fielding_stats,
)


class TestBattingStatsCalculator:
    """Test batting statistics calculations"""

    def test_batting_average_calculation(self):
        """Test BA calculation"""
        stats = {
            'hits': 150,
            'at_bats': 500
        }
        result = calculate_batting_stats(stats)
        assert result['ba'] == pytest.approx(0.300, 0.001)

    def test_on_base_percentage(self):
        """Test OBP calculation"""
        stats = {
            'hits': 150,
            'walks': 50,
            'hbp': 5,
            'at_bats': 500,
            'sac_flies': 3
        }
        result = calculate_batting_stats(stats)
        # OBP = (H + BB + HBP) / (AB + BB + HBP + SF)
        expected_obp = (150 + 50 + 5) / (500 + 50 + 5 + 3)
        assert result['obp'] == pytest.approx(expected_obp, 0.001)

    def test_slugging_percentage(self):
        """Test SLG calculation"""
        stats = {
            'singles': 100,
            'doubles': 30,
            'triples': 5,
            'home_runs': 15,
            'at_bats': 500
        }
        result = calculate_batting_stats(stats)
        # SLG = (1B + 2*2B + 3*3B + 4*HR) / AB
        total_bases = 100 + (30*2) + (5*3) + (15*4)
        expected_slg = total_bases / 500
        assert result['slg'] == pytest.approx(expected_slg, 0.001)

    def test_ops_calculation(self):
        """Test OPS (OBP + SLG)"""
        stats = {
            'hits': 150,
            'walks': 50,
            'hbp': 5,
            'at_bats': 500,
            'sac_flies': 3,
            'singles': 100,
            'doubles': 30,
            'triples': 5,
            'home_runs': 15,
        }
        result = calculate_batting_stats(stats)
        assert 'ops' in result
        assert result['ops'] == pytest.approx(result['obp'] + result['slg'], 0.001)

    def test_iso_calculation(self):
        """Test ISO (Isolated Power)"""
        stats = {
            'slugging': 0.500,
            'batting_avg': 0.300
        }
        result = calculate_batting_stats(stats)
        # ISO = SLG - BA
        assert result['iso'] == pytest.approx(0.200, 0.001)

    def test_zero_at_bats(self):
        """Test handling of zero at-bats"""
        stats = {
            'hits': 0,
            'at_bats': 0
        }
        result = calculate_batting_stats(stats)
        assert result['ba'] == 0.000


class TestPitchingStatsCalculator:
    """Test pitching statistics calculations"""

    def test_era_calculation(self):
        """Test ERA calculation"""
        stats = {
            'earned_runs': 50,
            'innings_pitched': 200.0
        }
        result = calculate_pitching_stats(stats)
        # ERA = (ER * 9) / IP
        expected_era = (50 * 9) / 200.0
        assert result['era'] == pytest.approx(expected_era, 0.01)

    def test_whip_calculation(self):
        """Test WHIP calculation"""
        stats = {
            'walks': 40,
            'hits': 180,
            'innings_pitched': 200.0
        }
        result = calculate_pitching_stats(stats)
        # WHIP = (BB + H) / IP
        expected_whip = (40 + 180) / 200.0
        assert result['whip'] == pytest.approx(expected_whip, 0.01)

    def test_k_per_nine(self):
        """Test K/9 calculation"""
        stats = {
            'strikeouts': 200,
            'innings_pitched': 200.0
        }
        result = calculate_pitching_stats(stats)
        # K/9 = (K * 9) / IP
        expected_k9 = (200 * 9) / 200.0
        assert result['k_per_nine'] == pytest.approx(expected_k9, 0.01)

    def test_fip_calculation(self):
        """Test FIP (Fielding Independent Pitching) calculation"""
        stats = {
            'home_runs_allowed': 20,
            'walks': 40,
            'hit_by_pitch': 5,
            'strikeouts': 180,
            'innings_pitched': 200.0
        }
        result = calculate_pitching_stats(stats)
        # FIP = ((13*HR + 3*BB + 3*HBP - 2*K) / IP) + constant
        # Using FIP constant of 3.10
        assert 'fip' in result
        assert isinstance(result['fip'], float)

    def test_zero_innings_pitched(self):
        """Test handling of zero innings pitched"""
        stats = {
            'earned_runs': 0,
            'innings_pitched': 0.0
        }
        result = calculate_pitching_stats(stats)
        assert result['era'] == 0.000


class TestFieldingStatsCalculator:
    """Test fielding statistics calculations"""

    def test_fielding_percentage(self):
        """Test FPCT calculation"""
        stats = {
            'putouts': 300,
            'assists': 100,
            'errors': 10
        }
        result = calculate_fielding_stats(stats)
        # FPCT = (PO + A) / (PO + A + E)
        expected_fpct = (300 + 100) / (300 + 100 + 10)
        assert result['fpct'] == pytest.approx(expected_fpct, 0.001)

    def test_range_factor(self):
        """Test RF calculation"""
        stats = {
            'putouts': 300,
            'assists': 100,
            'innings_played': 1296.0,  # 144 games * 9 innings
            'games_played': 144
        }
        result = calculate_fielding_stats(stats)
        # RF = ((PO + A) * 9) / innings
        expected_rf = ((300 + 100) * 9) / 1296.0
        assert result['range_factor'] == pytest.approx(expected_rf, 0.01)

    def test_perfect_fielding(self):
        """Test perfect fielding (no errors)"""
        stats = {
            'putouts': 300,
            'assists': 100,
            'errors': 0
        }
        result = calculate_fielding_stats(stats)
        assert result['fpct'] == 1.000

    def test_zero_chances(self):
        """Test handling of zero fielding chances"""
        stats = {
            'putouts': 0,
            'assists': 0,
            'errors': 0
        }
        result = calculate_fielding_stats(stats)
        assert result['fpct'] == 1.000  # Perfect by default


# Integration test
class TestStatsIntegration:
    """Integration tests for complete stat calculations"""

    def test_complete_player_stats(self):
        """Test calculating complete player statistics"""
        player_stats = {
            # Batting
            'hits': 150,
            'at_bats': 500,
            'walks': 50,
            'strikeouts': 100,
            'home_runs': 25,
            # Fielding
            'putouts': 200,
            'assists': 15,
            'errors': 5,
        }

        batting = calculate_batting_stats(player_stats)
        fielding = calculate_fielding_stats(player_stats)

        assert 'ba' in batting
        assert 'obp' in batting
        assert 'slg' in batting
        assert 'ops' in batting
        assert 'fpct' in fielding
        assert all(isinstance(v, (int, float)) for v in batting.values())
        assert all(isinstance(v, (int, float)) for v in fielding.values())
