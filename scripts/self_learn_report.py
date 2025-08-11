#!/usr/bin/env python3
"""
Generate HTML report for self-learning system
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.hybrid.bandit import BanditRouter
from src.hybrid.prompter import PromptTuner
from src.hybrid.evaluator import QualityEvaluator
from src.hybrid.calibrator import CostController


def generate_html_report(output_path: str = "artifacts/selflearn/report.html"):
    """Generate comprehensive HTML report"""
    
    # Collect data from all components
    bandit_router = BanditRouter()
    prompt_tuner = PromptTuner()
    evaluator = QualityEvaluator()
    cost_controller = CostController()
    
    # Get statistics
    bandit_stats = bandit_router.bandit.get_statistics()
    prompt_stats = prompt_tuner.get_statistics()
    budget_status = cost_controller.get_status()
    
    # Load latest cycle results if available
    latest_cycle_path = Path("artifacts/selflearn/latest_cycle.json")
    latest_cycle = {}
    if latest_cycle_path.exists():
        with open(latest_cycle_path, 'r') as f:
            latest_cycle = json.load(f)
    
    # Generate HTML
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PARANOID Self-Learning Report</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #0A2342; color: white; padding: 30px; border-radius: 8px; margin-bottom: 20px; }}
        .card {{ background: white; padding: 20px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric {{ display: inline-block; margin: 10px 20px 10px 0; }}
        .metric-value {{ font-size: 2em; font-weight: bold; color: #FF7A00; }}
        .metric-label {{ font-size: 0.9em; color: #666; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .status-good {{ color: #28a745; }}
        .status-warning {{ color: #ffc107; }}
        .status-danger {{ color: #dc3545; }}
        .progress {{ background: #e9ecef; border-radius: 4px; height: 8px; }}
        .progress-bar {{ background: #FF7A00; height: 100%; border-radius: 4px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
        th, td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f8f9fa; }}
        .timestamp {{ font-size: 0.8em; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧠 PARANOID Self-Learning Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Intelligent routing • Quality gates • Budget optimization</p>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>📊 System Overview</h2>
                <div class="metric">
                    <div class="metric-value">{bandit_stats.get('total_events', 0)}</div>
                    <div class="metric-label">Total Events</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{bandit_stats.get('context_count', 0)}</div>
                    <div class="metric-label">Learned Contexts</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{prompt_stats.get('total_variants', 0)}</div>
                    <div class="metric-label">Prompt Variants</div>
                </div>
            </div>
            
            <div class="card">
                <h2>💰 Budget Status</h2>
                <div class="metric">
                    <div class="metric-value">€{budget_status['current_spending']['total']:.2f}</div>
                    <div class="metric-label">This Month</div>
                </div>
                <div class="progress">
                    <div class="progress-bar" style="width: {min(100, budget_status['budget']['utilization']*100):.1f}%"></div>
                </div>
                <p>Budget utilization: {budget_status['budget']['utilization']*100:.1f}%</p>
                
                <h4>Model Breakdown:</h4>
                <p>DeepSeek: €{budget_status['current_spending']['deepseek']:.3f}</p>
                <p>GPT-5: €{budget_status['current_spending']['gpt5']:.3f}</p>
            </div>
        </div>
        
        <div class="card">
            <h2>🎯 Model Performance</h2>
            <table>
                <tr><th>Model</th><th>Events</th><th>Avg Reward</th><th>Status</th></tr>
    """
    
    # Model performance table
    for model, stats in bandit_stats.get('model_performance', {}).items():
        if stats['count'] > 0:
            status_class = "status-good" if stats['avg_reward'] > 0.7 else "status-warning" if stats['avg_reward'] > 0.5 else "status-danger"
            html_content += f"""
                <tr>
                    <td>{model.upper()}</td>
                    <td>{stats['count']}</td>
                    <td>{stats['avg_reward']:.3f}</td>
                    <td class="{status_class}">{'Excellent' if stats['avg_reward'] > 0.7 else 'Good' if stats['avg_reward'] > 0.5 else 'Needs Work'}</td>
                </tr>
            """
    
    html_content += """
            </table>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>🔧 Prompt Variants</h2>
    """
    
    # Prompt performance
    for model, model_stats in prompt_stats.get('model_stats', {}).items():
        html_content += f"<h4>{model.upper()}</h4>"
        if model_stats.get('best_variant'):
            best = model_stats['best_variant']
            html_content += f"""
                <p><strong>Best:</strong> {best['variant_id']}<br>
                Success rate: {best['success_rate']:.3f} | Avg score: {best['avg_score']:.3f} | Trials: {best['trials']}</p>
            """
        else:
            html_content += "<p>No variants tested yet</p>"
    
    html_content += """
            </div>
            
            <div class="card">
                <h2>⚡ Latest Cycle</h2>
    """
    
    # Latest cycle information
    if latest_cycle:
        cycle_status = latest_cycle.get('status', 'unknown')
        status_class = "status-good" if cycle_status == "success" else "status-danger"
        
        html_content += f"""
            <p class="{status_class}"><strong>Status:</strong> {cycle_status.upper()}</p>
            <p><strong>Events processed:</strong> {latest_cycle.get('events_processed', 0)}</p>
            <p><strong>Duration:</strong> {latest_cycle.get('duration_seconds', 0):.1f}s</p>
        """
        
        if 'evaluation' in latest_cycle:
            eval_data = latest_cycle['evaluation']
            quality_passed = eval_data.get('quality_gates_passed', False)
            quality_class = "status-good" if quality_passed else "status-danger"
            html_content += f'<p class="{quality_class}"><strong>Quality gates:</strong> {"PASSED" if quality_passed else "FAILED"}</p>'
        
        if latest_cycle.get('rollback_check', {}).get('rollback_executed'):
            html_content += '<p class="status-danger"><strong>⚠️ ROLLBACK EXECUTED</strong></p>'
        
        # Show timestamp
        cycle_time = latest_cycle.get('cycle_timestamp', 'Unknown')
        html_content += f'<p class="timestamp">Last run: {cycle_time}</p>'
    else:
        html_content += "<p>No cycle data available yet</p>"
    
    html_content += """
            </div>
        </div>
        
        <div class="card">
            <h2>📈 Quality Metrics</h2>
    """
    
    # Quality metrics from latest cycle
    if latest_cycle.get('evaluation', {}).get('overall_metrics'):
        metrics = latest_cycle['evaluation']['overall_metrics']
        html_content += f"""
            <div class="grid">
                <div>
                    <h4>Core Metrics</h4>
                    <p>Card pass rate: {metrics.get('card_pass_rate', 0):.3f}</p>
                    <p>Coverage (why matters): {metrics.get('coverage_why_matters', 0):.3f}</p>
                    <p>Hallucination rate: {metrics.get('hallu_rate', 0):.3f}</p>
                    <p>Reference miss rate: {metrics.get('ref_miss_rate', 0):.3f}</p>
                </div>
                <div>
                    <h4>User Engagement</h4>
                    <p>Editor accept rate: {metrics.get('editor_accept_rate', 0):.3f}</p>
                    <p>User engagement: {metrics.get('user_engagement', 0):.3f}</p>
                    <p>Sample size: {metrics.get('sample_size', 0)}</p>
                    <p>Avg cost: €{metrics.get('avg_cost_eur', 0):.4f}</p>
                </div>
            </div>
        """
    else:
        html_content += "<p>No quality metrics available yet</p>"
    
    html_content += """
        </div>
        
        <div class="card">
            <h2>🔧 System Configuration</h2>
            <h4>Routing Adjustments</h4>
    """
    
    # Current routing adjustments
    routing_config = budget_status.get('routing_adjustments', {})
    html_content += f"""
        <p>GPT-5 usage multiplier: {routing_config.get('gpt5_usage_multiplier', 1.0):.2f}</p>
        <p>Frozen mode: {routing_config.get('frozen_mode', False)}</p>
        <p>Emergency mode: {routing_config.get('emergency_mode', False)}</p>
    """
    
    if routing_config.get('last_adjustment'):
        html_content += f'<p class="timestamp">Last adjustment: {routing_config["last_adjustment"]}</p>'
    
    html_content += """
        </div>
        
        <div class="card">
            <h2>🚀 Next Steps</h2>
            <h4>Recommendations:</h4>
            <ul>
    """
    
    # Generate recommendations
    if budget_status['budget']['utilization'] > 0.8:
        html_content += "<li>🟡 Budget utilization high - consider reducing GPT-5 usage</li>"
    
    if latest_cycle.get('evaluation', {}).get('quality_gates_passed') == False:
        html_content += "<li>🔴 Quality gates failed - review prompt variants</li>"
    
    if bandit_stats.get('total_events', 0) < 100:
        html_content += "<li>🟡 Low sample size - continue collecting data</li>"
    
    if budget_status.get('routing_adjustments', {}).get('frozen_mode'):
        html_content += "<li>🟡 System in frozen mode - consider unfreezing after quality improves</li>"
    
    # Default recommendations if none triggered
    total_recs = html_content.count('<li>')
    if total_recs == 0:
        html_content += "<li>✅ System operating normally</li>"
        html_content += "<li>📊 Continue monitoring quality metrics</li>"
        html_content += "<li>🔄 Run daily cycles regularly</li>"
    
    html_content += """
            </ul>
            
            <h4>Commands:</h4>
            <pre>
# Run daily learning cycle
make selflearn-daily

# Generate updated report
make selflearn-report

# Test system with mock data
python3 scripts/self_learn_test.py
            </pre>
        </div>
        
        <div class="card timestamp">
            <p>🤖 Generated by PARANOID Self-Learning System v1.0</p>
            <p>For support: check artifacts/selflearn/ for detailed logs</p>
        </div>
    </div>
</body>
</html>
    """
    
    # Write report
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description="Generate self-learning system report")
    parser.add_argument("--out", default="artifacts/selflearn/report.html", help="Output HTML file")
    
    args = parser.parse_args()
    
    print("📊 Generating self-learning report...")
    
    try:
        report_file = generate_html_report(args.out)
        print(f"✅ Report generated: {report_file}")
        print(f"🌐 Open in browser: file://{report_file.absolute()}")
        
        # Also generate JSON summary
        json_file = report_file.with_suffix('.json')
        
        # Collect summary data
        bandit_router = BanditRouter()
        cost_controller = CostController()
        
        summary = {
            "generated_at": datetime.now().isoformat(),
            "bandit_stats": bandit_router.bandit.get_statistics(),
            "budget_status": cost_controller.get_status(),
            "report_url": f"file://{report_file.absolute()}"
        }
        
        with open(json_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"📄 JSON summary: {json_file}")
        
    except Exception as e:
        print(f"❌ Error generating report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
