#!/usr/bin/env python3
"""
Analytics Jobs
Scheduled jobs to populate metrics and aggregation tables
"""
import os
import sys
import json
from datetime import datetime, timedelta, date
from typing import Dict, List, Any
from sqlalchemy import text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


class AnalyticsJobs:
    """Analytics jobs for metrics and aggregation"""
    
    def __init__(self):
        self.app = create_app()
        self.app.app_context().push()
        self.jobs_completed = []
    
    def run_all_jobs(self):
        """Run all analytics jobs"""
        print("=" * 80)
        print("ANALYTICS JOBS")
        print("=" * 80)
        print()
        
        # 1. Daily metrics for technologies
        print("1. Generating daily technology metrics...")
        self.generate_technology_metrics()
        print()
        
        # 2. Point aggregates
        print("2. Generating point aggregates...")
        self.generate_point_aggregates()
        print()
        
        # 3. Point analytics
        print("3. Generating point analytics...")
        self.generate_point_analytics()
        print()
        
        # Record analytics sync for dashboard
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('analytics', count=len(self.jobs_completed))
        except Exception:
            pass
        # Summary
        print("=" * 80)
        print("JOBS SUMMARY")
        print("=" * 80)
        print()
        print(f"Completed {len(self.jobs_completed)} jobs:")
        for job in self.jobs_completed:
            print(f"   [OK] {job}")
        print()
    
    def generate_technology_metrics(self):
        """Generate daily metrics for all technologies"""
        try:
            today = date.today()
            
            # Get all technologies
            technologies = db.session.execute(
                text("SELECT tech_id FROM agent_technologies WHERE enabled = 1")
            ).fetchall()
            
            generated = 0
            for (tech_id,) in technologies:
                try:
                    # Check if metrics already exist for today
                    existing = db.session.execute(
                        text("SELECT id FROM agent_technology_metrics WHERE tech_id = :tech_id AND metric_date = :date"),
                        {"tech_id": tech_id, "date": today}
                    ).fetchone()
                    
                    if existing:
                        continue
                    
                    # Get metrics from events
                    events = db.session.execute(
                        text("""
                            SELECT 
                                COUNT(*) as total_operations,
                                SUM(CASE WHEN event_status = 'success' THEN 1 ELSE 0 END) as successful_operations,
                                SUM(CASE WHEN event_status = 'failed' THEN 1 ELSE 0 END) as failed_operations,
                                AVG(execution_time) as avg_response_time,
                                SUM(points_earned) as total_throughput
                            FROM agent_technology_events
                            WHERE tech_id = :tech_id AND DATE(created_at) = :date
                        """),
                        {"tech_id": tech_id, "date": today}
                    ).fetchone()
                    
                    total_ops = events[0] or 0
                    successful = events[1] or 0
                    failed = events[2] or 0
                    avg_time = float(events[3] or 0)
                    throughput = float(events[4] or 0)
                    error_rate = (failed / total_ops * 100) if total_ops > 0 else 0
                    
                    # Get technology scores
                    tech = db.session.execute(
                        text("SELECT performance_score, security_score, reliability_score FROM agent_technologies WHERE tech_id = :tech_id"),
                        {"tech_id": tech_id}
                    ).fetchone()
                    
                    db.session.execute(
                        text("""
                            INSERT INTO agent_technology_metrics
                            (tech_id, metric_date, performance_score, security_score, reliability_score,
                             total_operations, successful_operations, failed_operations, average_response_time,
                             total_throughput, error_rate, created_at)
                            VALUES (:tech_id, :metric_date, :performance_score, :security_score, :reliability_score,
                                    :total_operations, :successful_operations, :failed_operations, :average_response_time,
                                    :total_throughput, :error_rate, CURRENT_TIMESTAMP)
                        """),
                        {
                            "tech_id": tech_id,
                            "metric_date": today,
                            "performance_score": float(tech[0] or 0) if tech else 0,
                            "security_score": float(tech[1] or 0) if tech else 0,
                            "reliability_score": float(tech[2] or 0) if tech else 0,
                            "total_operations": total_ops,
                            "successful_operations": successful,
                            "failed_operations": failed,
                            "average_response_time": avg_time,
                            "total_throughput": throughput,
                            "error_rate": round(error_rate, 2),
                        }
                    )
                    generated += 1
                except Exception as e:
                    print(f"   [WARN] Failed to generate metrics for {tech_id}: {str(e)}")
            
            db.session.commit()
            self.jobs_completed.append(f"Generated {generated} technology metrics")
            print(f"   [OK] Generated {generated} technology metrics")
        except Exception as e:
            db.session.rollback()
            print(f"   [ERROR] Failed: {str(e)}")
    
    def generate_point_aggregates(self):
        """Generate point aggregates for users"""
        try:
            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            month_start = date(today.year, today.month, 1)
            
            # Get all users with point activity
            users = db.session.execute(
                text("SELECT DISTINCT user_id FROM point_transactions WHERE DATE(created_at) >= :month_start"),
                {"month_start": month_start}
            ).fetchall()
            
            generated = 0
            for (user_id,) in users:
                try:
                    # Daily aggregate
                    self._generate_user_aggregate(user_id, 'daily', today, today)
                    
                    # Weekly aggregate
                    week_end = week_start + timedelta(days=6)
                    self._generate_user_aggregate(user_id, 'weekly', week_start, week_end)
                    
                    # Monthly aggregate
                    if today.day == 1:  # Only on first day of month
                        last_month_end = month_start - timedelta(days=1)
                        last_month_start = date(last_month_end.year, last_month_end.month, 1)
                        self._generate_user_aggregate(user_id, 'monthly', last_month_start, last_month_end)
                    
                    generated += 1
                except Exception as e:
                    print(f"   [WARN] Failed to generate aggregates for {user_id}: {str(e)}")
            
            db.session.commit()
            self.jobs_completed.append(f"Generated aggregates for {generated} users")
            print(f"   [OK] Generated aggregates for {generated} users")
        except Exception as e:
            db.session.rollback()
            print(f"   [ERROR] Failed: {str(e)}")
    
    def _generate_user_aggregate(self, user_id: str, aggregate_type: str, period_start: date, period_end: date):
        """Generate aggregate for a user"""
        # Check if already exists
        existing = db.session.execute(
            text("""
                SELECT id FROM point_aggregates
                WHERE user_id = :user_id AND aggregate_type = :type AND period_start = :start
            """),
            {"user_id": user_id, "type": aggregate_type, "start": period_start}
        ).fetchone()
        
        if existing:
            return
        
        # Get transaction data
        transactions = db.session.execute(
            text("""
                SELECT 
                    COUNT(DISTINCT system_name) as systems_count,
                    SUM(amount) as total_points,
                    GROUP_CONCAT(DISTINCT system_name) as active_systems
                FROM point_transactions
                WHERE user_id = :user_id AND DATE(created_at) BETWEEN :start AND :end
            """),
            {"user_id": user_id, "start": period_start, "end": period_end}
        ).fetchone()
        
        systems_count = transactions[0] or 0
        total_points = float(transactions[1] or 0)
        active_systems = transactions[2] or ''
        
        # Calculate growth rate (compare with previous period)
        previous_end = period_start - timedelta(days=1)
        previous_start = previous_end - (period_end - period_start)
        
        previous_total = db.session.execute(
            text("""
                SELECT SUM(amount) FROM point_transactions
                WHERE user_id = :user_id AND DATE(created_at) BETWEEN :start AND :end
            """),
            {"user_id": user_id, "start": previous_start, "end": previous_end}
        ).scalar() or 0
        
        growth_rate = 0
        if previous_total > 0:
            growth_rate = ((total_points - previous_total) / previous_total * 100)
        
        db.session.execute(
            text("""
                INSERT INTO point_aggregates
                (user_id, aggregate_type, period_start, period_end, total_points, systems_count,
                 active_systems, growth_rate, aggregate_data, created_at)
                VALUES (:user_id, :aggregate_type, :period_start, :period_end, :total_points, :systems_count,
                        :active_systems, :growth_rate, :aggregate_data, CURRENT_TIMESTAMP)
            """),
            {
                "user_id": user_id,
                "aggregate_type": aggregate_type,
                "period_start": period_start,
                "period_end": period_end,
                "total_points": total_points,
                "systems_count": systems_count,
                "active_systems": active_systems,
                "growth_rate": round(growth_rate, 2),
                "aggregate_data": json.dumps({
                    "period": f"{period_start} to {period_end}",
                    "generated_at": datetime.now().isoformat()
                }),
            }
        )
    
    def generate_point_analytics(self):
        """Generate point analytics for users"""
        try:
            today = date.today()
            
            # Get users with recent activity
            users = db.session.execute(
                text("""
                    SELECT DISTINCT user_id FROM point_transactions
                    WHERE DATE(created_at) >= DATE('now', '-30 days')
                """)
            ).fetchall()
            
            generated = 0
            for (user_id,) in users:
                try:
                    # Check if analytics already exist for today
                    existing = db.session.execute(
                        text("SELECT id FROM point_analytics WHERE user_id = :user_id AND analysis_date = :date"),
                        {"user_id": user_id, "date": today}
                    ).fetchone()
                    
                    if existing:
                        continue
                    
                    # Get point data
                    total_points = db.session.execute(
                        text("""
                            SELECT SUM(point_value) FROM system_point_snapshots s
                            JOIN (
                                SELECT system_name, MAX(id) AS max_id
                                FROM system_point_snapshots
                                WHERE user_id = :user_id
                                GROUP BY system_name
                            ) t ON s.id = t.max_id
                            WHERE s.user_id = :user_id
                        """),
                        {"user_id": user_id}
                    ).scalar() or 0
                    
                    # Get active systems
                    active_systems = db.session.execute(
                        text("""
                            SELECT COUNT(DISTINCT system_name) FROM point_transactions
                            WHERE user_id = :user_id AND DATE(created_at) >= DATE('now', '-7 days')
                        """),
                        {"user_id": user_id}
                    ).scalar() or 0
                    
                    # Get top systems
                    top_systems = db.session.execute(
                        text("""
                            SELECT system_name, SUM(amount) as total
                            FROM point_transactions
                            WHERE user_id = :user_id AND DATE(created_at) >= DATE('now', '-30 days')
                            GROUP BY system_name
                            ORDER BY total DESC
                            LIMIT 10
                        """),
                        {"user_id": user_id}
                    ).fetchall()
                    
                    top_systems_list = [{"system": row[0], "points": float(row[1])} for row in top_systems]
                    
                    # Calculate growth trend
                    week_ago = today - timedelta(days=7)
                    week_points = db.session.execute(
                        text("""
                            SELECT SUM(amount) FROM point_transactions
                            WHERE user_id = :user_id AND DATE(created_at) BETWEEN :start AND :end
                        """),
                        {"user_id": user_id, "start": week_ago, "end": today}
                    ).scalar() or 0
                    
                    previous_week_points = db.session.execute(
                        text("""
                            SELECT SUM(amount) FROM point_transactions
                            WHERE user_id = :user_id AND DATE(created_at) BETWEEN :start AND :end
                        """),
                        {"user_id": user_id, "start": week_ago - timedelta(days=7), "end": week_ago}
                    ).scalar() or 0
                    
                    growth_rate = 0
                    growth_trend = 'stable'
                    if previous_week_points > 0:
                        growth_rate = ((week_points - previous_week_points) / previous_week_points * 100)
                        if growth_rate > 5:
                            growth_trend = 'increasing'
                        elif growth_rate < -5:
                            growth_trend = 'decreasing'
                    
                    # Generate insights and recommendations
                    insights = []
                    recommendations = []
                    
                    if active_systems < 5:
                        insights.append("Low system activity")
                        recommendations.append("Try exploring more point systems")
                    
                    if growth_rate < 0:
                        insights.append("Point growth declining")
                        recommendations.append("Increase engagement with active systems")
                    
                    db.session.execute(
                        text("""
                            INSERT INTO point_analytics
                            (user_id, analysis_date, total_points, systems_active, top_systems, growth_trend,
                             growth_rate, insights, recommendations, analytics_data, created_at)
                            VALUES (:user_id, :analysis_date, :total_points, :systems_active, :top_systems, :growth_trend,
                                    :growth_rate, :insights, :recommendations, :analytics_data, CURRENT_TIMESTAMP)
                        """),
                        {
                            "user_id": user_id,
                            "analysis_date": today,
                            "total_points": float(total_points),
                            "systems_active": active_systems,
                            "top_systems": json.dumps(top_systems_list),
                            "growth_trend": growth_trend,
                            "growth_rate": round(growth_rate, 2),
                            "insights": json.dumps(insights),
                            "recommendations": json.dumps(recommendations),
                            "analytics_data": json.dumps({
                                "generated_at": datetime.now().isoformat(),
                                "analysis_period": "30 days"
                            }),
                        }
                    )
                    generated += 1
                except Exception as e:
                    print(f"   [WARN] Failed to generate analytics for {user_id}: {str(e)}")
            
            db.session.commit()
            self.jobs_completed.append(f"Generated analytics for {generated} users")
            print(f"   [OK] Generated analytics for {generated} users")
        except Exception as e:
            db.session.rollback()
            print(f"   [ERROR] Failed: {str(e)}")


def main():
    """Main entry point"""
    jobs = AnalyticsJobs()
    jobs.run_all_jobs()


if __name__ == '__main__':
    main()
