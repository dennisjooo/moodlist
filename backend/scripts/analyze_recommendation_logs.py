#!/usr/bin/env python3
"""
Log analysis script for recommendation pipeline logs.

Analyzes structured JSON logs to provide insights into:
- Track acceptance/rejection rates
- Rejection reasons breakdown
- Source effectiveness (confidence by source)
- Quality metrics over time
- Artist discovery success rates
- Genre filtering effectiveness

Usage:
    python analyze_recommendation_logs.py logs/agentic_system_*.log
    python analyze_recommendation_logs.py --session-id <session_id> logs/*.log
    python analyze_recommendation_logs.py --event track_evaluation logs/*.log
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any


class RecommendationLogAnalyzer:
    """Analyzer for recommendation pipeline logs."""

    def __init__(self):
        """Initialize the analyzer."""
        self.logs = []
        self.stats = {
            "total_logs": 0,
            "events": defaultdict(int),
            "sessions": set(),
            "workflows": set(),
        }

    def load_logs(self, log_files: List[Path], session_id: str = None, event_type: str = None):
        """Load and filter logs from files.

        Args:
            log_files: List of log file paths
            session_id: Optional session ID filter
            event_type: Optional event type filter
        """
        for log_file in log_files:
            try:
                with open(log_file) as f:
                    for line in f:
                        try:
                            log = json.loads(line.strip())
                            
                            # Apply filters
                            if session_id and log.get("session_id") != session_id:
                                continue
                            if event_type and log.get("event") != event_type:
                                continue
                            
                            self.logs.append(log)
                            self.stats["total_logs"] += 1
                            self.stats["events"][log.get("event", "unknown")] += 1
                            
                            if log.get("session_id"):
                                self.stats["sessions"].add(log.get("session_id"))
                            if log.get("workflow_id"):
                                self.stats["workflows"].add(log.get("workflow_id"))
                                
                        except json.JSONDecodeError:
                            continue
            except FileNotFoundError:
                print(f"Warning: File not found: {log_file}", file=sys.stderr)

    def analyze_track_evaluations(self) -> Dict[str, Any]:
        """Analyze track evaluation logs.

        Returns:
            Dictionary with track evaluation statistics
        """
        track_logs = [log for log in self.logs if log.get("event") == "track_evaluation"]
        
        if not track_logs:
            return {"error": "No track evaluation logs found"}

        decisions = defaultdict(int)
        rejection_reasons = defaultdict(int)
        sources = defaultdict(lambda: {"count": 0, "total_confidence": 0, "confidences": []})
        
        for log in track_logs:
            decision = log.get("decision", "UNKNOWN")
            decisions[decision] += 1
            
            if decision == "REJECTED" and log.get("rejection_reason"):
                rejection_reasons[log.get("rejection_reason")] += 1
            
            source = log.get("source", "unknown")
            if log.get("confidence") is not None:
                sources[source]["count"] += 1
                sources[source]["total_confidence"] += log.get("confidence", 0)
                sources[source]["confidences"].append(log.get("confidence", 0))

        # Calculate source statistics
        source_stats = {}
        for source, data in sources.items():
            if data["count"] > 0:
                source_stats[source] = {
                    "count": data["count"],
                    "avg_confidence": round(data["total_confidence"] / data["count"], 3),
                    "min_confidence": round(min(data["confidences"]), 3) if data["confidences"] else 0,
                    "max_confidence": round(max(data["confidences"]), 3) if data["confidences"] else 0,
                }

        total_tracks = len(track_logs)
        return {
            "total_evaluated": total_tracks,
            "decisions": dict(decisions),
            "acceptance_rate": round(decisions.get("ACCEPTED", 0) / total_tracks, 3) if total_tracks > 0 else 0,
            "rejection_rate": round(decisions.get("REJECTED", 0) / total_tracks, 3) if total_tracks > 0 else 0,
            "rejection_reasons": dict(sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True)),
            "source_statistics": source_stats,
        }

    def analyze_quality_evaluations(self) -> Dict[str, Any]:
        """Analyze quality evaluation logs.

        Returns:
            Dictionary with quality evaluation statistics
        """
        quality_logs = [log for log in self.logs if log.get("event") == "quality_evaluation"]
        
        if not quality_logs:
            return {"error": "No quality evaluation logs found"}

        scores = {
            "overall": [],
            "cohesion": [],
            "confidence": [],
            "diversity": [],
        }
        
        meets_threshold_count = 0
        all_issues = defaultdict(int)
        
        for log in quality_logs:
            scores["overall"].append(log.get("overall_score", 0))
            scores["cohesion"].append(log.get("cohesion_score", 0))
            scores["confidence"].append(log.get("confidence_score", 0))
            scores["diversity"].append(log.get("diversity_score", 0))
            
            if log.get("meets_threshold"):
                meets_threshold_count += 1
            
            for issue in log.get("issues", []):
                all_issues[issue] += 1

        def avg(lst):
            return round(sum(lst) / len(lst), 3) if lst else 0

        return {
            "total_evaluations": len(quality_logs),
            "meets_threshold_count": meets_threshold_count,
            "threshold_pass_rate": round(meets_threshold_count / len(quality_logs), 3),
            "average_scores": {
                "overall": avg(scores["overall"]),
                "cohesion": avg(scores["cohesion"]),
                "confidence": avg(scores["confidence"]),
                "diversity": avg(scores["diversity"]),
            },
            "common_issues": dict(sorted(all_issues.items(), key=lambda x: x[1], reverse=True)[:10]),
        }

    def analyze_source_mix(self) -> Dict[str, Any]:
        """Analyze recommendation source mix logs.

        Returns:
            Dictionary with source mix statistics
        """
        source_logs = [log for log in self.logs if log.get("event") == "source_mix"]
        
        if not source_logs:
            return {"error": "No source mix logs found"}

        source_totals = defaultdict(lambda: {"count": 0, "percentage": []})
        
        for log in source_logs:
            sources = log.get("sources", {})
            for source_name, source_data in sources.items():
                source_totals[source_name]["count"] += source_data.get("count", 0)
                source_totals[source_name]["percentage"].append(source_data.get("percentage", 0))

        source_stats = {}
        for source, data in source_totals.items():
            if data["percentage"]:
                source_stats[source] = {
                    "total_count": data["count"],
                    "avg_percentage": round(sum(data["percentage"]) / len(data["percentage"]), 1),
                    "min_percentage": round(min(data["percentage"]), 1),
                    "max_percentage": round(max(data["percentage"]), 1),
                }

        return source_stats

    def analyze_diversity_penalties(self) -> Dict[str, Any]:
        """Analyze diversity penalty logs.

        Returns:
            Dictionary with diversity penalty statistics
        """
        diversity_logs = [log for log in self.logs if log.get("event") == "diversity_penalty"]
        
        if not diversity_logs:
            return {"error": "No diversity penalty logs found"}

        protected_count = 0
        penalized_count = 0
        total_penalty = 0
        penalties = []
        
        for log in diversity_logs:
            if log.get("is_protected"):
                protected_count += 1
            else:
                penalized_count += 1
                penalty = log.get("penalty", 0)
                total_penalty += penalty
                penalties.append(penalty)

        return {
            "total_tracks": len(diversity_logs),
            "protected_count": protected_count,
            "penalized_count": penalized_count,
            "protection_rate": round(protected_count / len(diversity_logs), 3) if diversity_logs else 0,
            "average_penalty": round(total_penalty / penalized_count, 3) if penalized_count > 0 else 0,
            "max_penalty": round(max(penalties), 3) if penalties else 0,
        }

    def analyze_genre_filters(self) -> Dict[str, Any]:
        """Analyze genre filter logs.

        Returns:
            Dictionary with genre filter statistics
        """
        genre_logs = [log for log in self.logs if log.get("event") == "genre_filter"]
        
        if not genre_logs:
            return {"error": "No genre filter logs found"}

        passed_count = 0
        failed_count = 0
        failure_reasons = defaultdict(int)
        
        for log in genre_logs:
            if log.get("passed"):
                passed_count += 1
            else:
                failed_count += 1
                reason = log.get("rejection_reason", "unknown")
                failure_reasons[reason] += 1

        return {
            "total_filtered": len(genre_logs),
            "passed": passed_count,
            "failed": failed_count,
            "pass_rate": round(passed_count / len(genre_logs), 3) if genre_logs else 0,
            "failure_reasons": dict(sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)),
        }

    def print_summary(self):
        """Print a comprehensive summary of all analyses."""
        print("=" * 80)
        print("RECOMMENDATION PIPELINE LOG ANALYSIS")
        print("=" * 80)
        print(f"\nTotal Logs: {self.stats['total_logs']}")
        print(f"Sessions: {len(self.stats['sessions'])}")
        print(f"Workflows: {len(self.stats['workflows'])}")
        
        print("\nEvent Distribution:")
        for event, count in sorted(self.stats["events"].items(), key=lambda x: x[1], reverse=True):
            print(f"  {event}: {count}")

        print("\n" + "=" * 80)
        print("TRACK EVALUATION ANALYSIS")
        print("=" * 80)
        track_stats = self.analyze_track_evaluations()
        if "error" not in track_stats:
            print(f"\nTotal Evaluated: {track_stats['total_evaluated']}")
            print(f"Acceptance Rate: {track_stats['acceptance_rate'] * 100:.1f}%")
            print(f"Rejection Rate: {track_stats['rejection_rate'] * 100:.1f}%")
            
            print("\nDecisions:")
            for decision, count in track_stats["decisions"].items():
                print(f"  {decision}: {count}")
            
            if track_stats["rejection_reasons"]:
                print("\nTop Rejection Reasons:")
                for reason, count in list(track_stats["rejection_reasons"].items())[:10]:
                    print(f"  {reason}: {count}")
            
            if track_stats["source_statistics"]:
                print("\nSource Statistics:")
                for source, stats in track_stats["source_statistics"].items():
                    print(f"  {source}:")
                    print(f"    Count: {stats['count']}")
                    print(f"    Avg Confidence: {stats['avg_confidence']}")
                    print(f"    Range: {stats['min_confidence']} - {stats['max_confidence']}")

        print("\n" + "=" * 80)
        print("QUALITY EVALUATION ANALYSIS")
        print("=" * 80)
        quality_stats = self.analyze_quality_evaluations()
        if "error" not in quality_stats:
            print(f"\nTotal Evaluations: {quality_stats['total_evaluations']}")
            print(f"Threshold Pass Rate: {quality_stats['threshold_pass_rate'] * 100:.1f}%")
            
            print("\nAverage Scores:")
            for score_type, value in quality_stats["average_scores"].items():
                print(f"  {score_type}: {value}")
            
            if quality_stats["common_issues"]:
                print("\nCommon Issues:")
                for issue, count in list(quality_stats["common_issues"].items())[:10]:
                    print(f"  {issue}: {count}")

        print("\n" + "=" * 80)
        print("SOURCE MIX ANALYSIS")
        print("=" * 80)
        source_mix_stats = self.analyze_source_mix()
        if "error" not in source_mix_stats:
            for source, stats in source_mix_stats.items():
                print(f"\n{source}:")
                print(f"  Total Count: {stats['total_count']}")
                print(f"  Avg Percentage: {stats['avg_percentage']}%")
                print(f"  Range: {stats['min_percentage']}% - {stats['max_percentage']}%")

        print("\n" + "=" * 80)
        print("DIVERSITY PENALTY ANALYSIS")
        print("=" * 80)
        diversity_stats = self.analyze_diversity_penalties()
        if "error" not in diversity_stats:
            print(f"\nTotal Tracks: {diversity_stats['total_tracks']}")
            print(f"Protected: {diversity_stats['protected_count']}")
            print(f"Penalized: {diversity_stats['penalized_count']}")
            print(f"Protection Rate: {diversity_stats['protection_rate'] * 100:.1f}%")
            print(f"Average Penalty: {diversity_stats['average_penalty']}")
            print(f"Max Penalty: {diversity_stats['max_penalty']}")

        print("\n" + "=" * 80)
        print("GENRE FILTER ANALYSIS")
        print("=" * 80)
        genre_stats = self.analyze_genre_filters()
        if "error" not in genre_stats:
            print(f"\nTotal Filtered: {genre_stats['total_filtered']}")
            print(f"Passed: {genre_stats['passed']}")
            print(f"Failed: {genre_stats['failed']}")
            print(f"Pass Rate: {genre_stats['pass_rate'] * 100:.1f}%")
            
            if genre_stats["failure_reasons"]:
                print("\nFailure Reasons:")
                for reason, count in genre_stats["failure_reasons"].items():
                    print(f"  {reason}: {count}")

        print("\n" + "=" * 80)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze recommendation pipeline logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all logs in directory
  python analyze_recommendation_logs.py logs/agentic_system_*.log
  
  # Analyze logs for specific session
  python analyze_recommendation_logs.py --session-id abc123 logs/*.log
  
  # Analyze only track evaluation events
  python analyze_recommendation_logs.py --event track_evaluation logs/*.log
  
  # Export to JSON
  python analyze_recommendation_logs.py --json logs/*.log > analysis.json
        """
    )
    
    parser.add_argument(
        "log_files",
        nargs="+",
        type=Path,
        help="Log files to analyze"
    )
    
    parser.add_argument(
        "--session-id",
        help="Filter by session ID"
    )
    
    parser.add_argument(
        "--event",
        help="Filter by event type"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of human-readable format"
    )
    
    args = parser.parse_args()

    # Initialize analyzer
    analyzer = RecommendationLogAnalyzer()
    
    # Load logs
    analyzer.load_logs(args.log_files, session_id=args.session_id, event_type=args.event)
    
    if analyzer.stats["total_logs"] == 0:
        print("No logs found matching criteria", file=sys.stderr)
        sys.exit(1)

    # Generate output
    if args.json:
        # Export as JSON
        output = {
            "summary": {
                "total_logs": analyzer.stats["total_logs"],
                "sessions": len(analyzer.stats["sessions"]),
                "workflows": len(analyzer.stats["workflows"]),
                "events": dict(analyzer.stats["events"]),
            },
            "track_evaluations": analyzer.analyze_track_evaluations(),
            "quality_evaluations": analyzer.analyze_quality_evaluations(),
            "source_mix": analyzer.analyze_source_mix(),
            "diversity_penalties": analyzer.analyze_diversity_penalties(),
            "genre_filters": analyzer.analyze_genre_filters(),
        }
        print(json.dumps(output, indent=2))
    else:
        # Print human-readable summary
        analyzer.print_summary()


if __name__ == "__main__":
    main()
