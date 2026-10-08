import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.ai_parser import AIConstraintParser


class TestAIConstraintParserStaticMappings:
    def test_supported_constraint_types_coverage(self):
        types = AIConstraintParser.SUPPORTED_TYPES
        assert "faculty_unavailability" in types
        assert "faculty_availability" in types
        assert "consecutive_periods" in types
        assert "subject_max_per_day" in types
        assert "preferred_time_slot" in types
        assert "avoid_time_slot" in types
        assert "class_gap" in types
        assert "specific_time_slot" in types

    def test_weekday_aliases_mapping(self):
        aliases = AIConstraintParser.WEEKDAY_ALIASES
        assert aliases["mon"] == "Monday"
        assert aliases["fri"] == "Friday"
        assert "Monday" in aliases["weekdays"]
        assert "Saturday" in aliases["weekend"]

    def test_number_words_mapping(self):
        nums = AIConstraintParser.NUMBER_WORDS
        assert nums["one"] == 1
        assert nums["two"] == 2
        assert nums["twice"] == 2
        assert nums["three"] == 3


class TestAIConstraintParserRuleBased:
    def setup_method(self):
        self.context = {
            "faculty_names": ["Dr. Shiva", "Prof. Alan Turing", "Dr. Jane Smith"],
            "subject_names": ["Operating Systems", "Compiler Design", "Machine Learning Lab"],
            "class_names": ["CSE-A", "CSE-B"],
            "periods_per_day": 7,
        }
        self.parser = AIConstraintParser(context=self.context)

    def test_single_day_detection(self):
        assert self.parser._single_day("monday") == "Monday"
        assert self.parser._single_day("Tue") == "Tuesday"
        assert self.parser._single_day("wed") == "Wednesday"
        assert self.parser._single_day("thur") == "Thursday"
        assert self.parser._single_day("friday") == "Friday"
        assert self.parser._single_day("invalid-day") is None

    def test_parse_days_range_and_lists(self):
        days_range = self.parser._parse_day_names("Monday to Wednesday")
        assert days_range == ["Monday", "Tuesday", "Wednesday"]

        weekend_days = self.parser._parse_day_names("only on the weekend")
        assert weekend_days == ["Saturday", "Sunday"]

        listed_days = self.parser._parse_day_names("Monday, Thursday")
        assert listed_days == ["Monday", "Thursday"]

    def test_parse_period_numbers(self):
        assert 1 in self.parser._parse_period_numbers("first period")
        assert 7 in self.parser._parse_period_numbers("last period")
        assert self.parser._parse_period_numbers("periods 2, 3 and 4") == [2, 3, 4]

    def test_match_name_exact_and_fuzzy(self):
        # Exact match
        matched, typo = self.parser._fuzzy_match("Dr. Shiva is not free", self.context["faculty_names"])
        assert matched == "Dr. Shiva"
        assert typo is None

        # Typo match
        matched_typo, typo = self.parser._fuzzy_match("Prof Alan Turring is absent", self.context["faculty_names"])
        assert matched_typo == "Prof. Alan Turing"

    def test_parse_constraints_returns_structured_dict(self):
        # Test rule-based parsing runs without exception and returns valid dictionary format
        result = self.parser.parse_constraints_with_diagnostics(
            "Dr. Shiva is unavailable on Friday. Avoid period 1 for Operating Systems."
        )
        assert "constraints" in result
        assert "corrections" in result
        assert "warnings" in result
        assert "unrecognized" in result
        assert isinstance(result["constraints"], list)
