"""
Real Mining Test Script
Tests the new core architecture with real BRAIN API
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.agents.core import (
    Hypothesis,
    AlphaExperiment,
    ExperimentStatus,
    HypothesisFeedback,
    AttributionType,
    ExperimentTrace,
    AlphaMiningScenario,
    create_scenario,
    create_trace,
)


async def test_brain_connection():
    """Test BRAIN API connection via MCP or direct adapter."""
    print("\n" + "="*60)
    print("Testing BRAIN API Connection")
    print("="*60)
    
    try:
        from backend.adapters.brain_adapter import BrainAdapter
        
        async with BrainAdapter() as brain:
            # Test getting datasets
            print("\n[1] Getting available datasets...")
            datasets = await brain.get_datasets()
            print(f"   Found {len(datasets)} datasets")
            if datasets:
                for ds in datasets[:5]:
                    ds_id = ds.get('id', ds.get('datasetId')) if isinstance(ds, dict) else ds
                    ds_name = ds.get('name', 'N/A') if isinstance(ds, dict) else 'N/A'
                    print(f"   - {ds_id}: {ds_name}")
            
            # Test getting operators
            print("\n[2] Getting available operators...")
            operators = await brain.get_operators()
            print(f"   Found {len(operators)} operators")
            if operators:
                for op in operators[:5]:
                    op_name = op.get('name') if isinstance(op, dict) else op
                    print(f"   - {op_name}")
            
            # Test getting user alphas
            print("\n[3] Getting user alphas...")
            alphas_resp = await brain.get_user_alphas(limit=5)
            alphas = alphas_resp.get('results', []) if isinstance(alphas_resp, dict) else alphas_resp
            print(f"   Found {len(alphas)} recent alphas")
            if alphas:
                for alpha in alphas[:3]:
                    alpha_id = alpha.get('id', 'N/A')
                    is_stats = alpha.get('is', {})
                    sharpe = is_stats.get('sharpe', 'N/A') if isinstance(is_stats, dict) else 'N/A'
                    print(f"   - {alpha_id}: Sharpe={sharpe}")
            
            return True
        
    except Exception as e:
        print(f"\n   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_alpha_simulation():
    """Test creating and simulating a simple alpha."""
    print("\n" + "="*60)
    print("Testing Alpha Simulation")
    print("="*60)
    
    try:
        from backend.adapters.brain_adapter import BrainAdapter
        
        async with BrainAdapter() as brain:
            # Create a simple test alpha
            test_expression = "rank(close)"
            print(f"\n[1] Simulating expression: {test_expression}")
            
            result = await brain.simulate_alpha(
                expression=test_expression,
                region="USA",
                universe="TOP3000"
            )
            
            if result and result.get('success'):
                print(f"   Simulation completed!")
                print(f"   Alpha ID: {result.get('alpha_id', 'N/A')}")
                
                metrics = result.get('metrics', {})
                print(f"   Sharpe: {metrics.get('sharpe', 'N/A')}")
                print(f"   Fitness: {metrics.get('fitness', 'N/A')}")
                print(f"   Turnover: {metrics.get('turnover', 'N/A')}")
                
                checks = result.get('checks', [])
                if checks:
                    print(f"   Checks ({len(checks)}):")
                    for check in checks[:5]:
                        name = check.get('name', 'unknown')
                        passed = check.get('result', 'N/A')
                        status = 'PASS' if passed == 'PASS' or passed == True else 'FAIL'
                        print(f"      - {name}: {status}")
                
                return result
            else:
                error = result.get('error', 'Unknown error') if result else 'No result'
                print(f"   Simulation failed: {error}")
                return None
            
    except Exception as e:
        print(f"\n   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_new_core_architecture():
    """Test the new core architecture with real data."""
    print("\n" + "="*60)
    print("Testing New Core Architecture")
    print("="*60)
    
    try:
        from backend.adapters.brain_adapter import BrainAdapter
        
        async with BrainAdapter() as brain:
            # Create scenario
            print("\n[1] Creating AlphaMiningScenario...")
            
            # Get real fields
            fields_raw = await brain.get_datafields("fundamental6")
            operators_raw = await brain.get_operators(detailed=True)
            
            # Convert to expected format
            fields = []
            for f in (fields_raw[:20] if fields_raw else []):
                if isinstance(f, dict):
                    fields.append({"id": f.get("id"), "description": f.get("description", "")})
                else:
                    fields.append({"id": str(f), "description": ""})
            
            operators = []
            for op in (operators_raw[:20] if operators_raw else []):
                if isinstance(op, dict):
                    operators.append({"name": op.get("name"), "description": op.get("description", "")})
                else:
                    operators.append({"name": str(op), "description": ""})
            
            scenario = create_scenario(
                region="USA",
                universe="TOP3000",
                dataset_id="fundamental6",
                fields=fields,
                operators=operators
            )
            
            print(f"   Scenario created for {scenario.region}/{scenario.universe}")
            print(f"   Dataset: {scenario.dataset_context.dataset_id}")
            print(f"   Fields available: {len(scenario.dataset_context.fields)}")
            print(f"   Operators available: {len(scenario.operator_context.operators)}")
            
            # Create trace
            print("\n[2] Creating ExperimentTrace...")
            trace = create_trace(
                dataset_id="fundamental6",
                region="USA",
                universe="TOP3000"
            )
            print(f"   Trace initialized, knowledge base ready")
            
            # Create hypothesis
            print("\n[3] Creating Hypothesis...")
            hypothesis = Hypothesis(
                statement="Simple price momentum using close price rank should provide predictive signal",
                rationale="Cross-sectional rank normalizes prices and captures relative momentum",
                expected_signal="momentum",
                key_fields=["close"],
                suggested_operators=["rank"],
                confidence="medium"
            )
            print(f"   Hypothesis: {hypothesis.statement[:60]}...")
            
            # Create experiment
            print("\n[4] Creating AlphaExperiment...")
            experiment = AlphaExperiment(
                id=f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                hypothesis=hypothesis,
                expression="rank(close)",
                explanation="Simple cross-sectional price rank for momentum capture",
                fields_used=["close"],
                dataset_id="fundamental6",
                region="USA",
                universe="TOP3000",
                status=ExperimentStatus.PENDING
            )
            print(f"   Experiment ID: {experiment.id}")
            print(f"   Expression: {experiment.expression}")
            
            # Run simulation
            print("\n[5] Running real simulation...")
            experiment.status = ExperimentStatus.RUNNING
            
            result = await brain.simulate_alpha(
                expression=experiment.expression,
                region=experiment.region,
                universe=experiment.universe
            )
            
            # Initialize metrics with defaults
            sharpe = 0
            fitness = 0
            turnover = 1
            
            if result and result.get('success'):
                # Update experiment with results
                experiment.status = ExperimentStatus.COMPLETED
                experiment.alpha_id = result.get('alpha_id')
                experiment.metrics = result.get('metrics', {})
                
                # Get metrics
                sharpe = experiment.metrics.get('sharpe', 0) or 0
                fitness = experiment.metrics.get('fitness', 0) or 0
                turnover = experiment.metrics.get('turnover', 1) or 1
                
                # Determine quality status
                if sharpe >= 1.58 and fitness >= 1.0 and turnover <= 0.3:
                    experiment.quality_status = "PASS"
                elif sharpe >= 1.0:
                    experiment.quality_status = "OPTIMIZE"
                else:
                    experiment.quality_status = "FAIL"
                
                print(f"   Status: {experiment.status.value}")
                print(f"   Alpha ID: {experiment.alpha_id}")
                print(f"   Quality: {experiment.quality_status}")
                print(f"   Metrics:")
                print(f"      Sharpe: {sharpe}")
                print(f"      Fitness: {fitness}")
                print(f"      Turnover: {turnover}")
            else:
                experiment.status = ExperimentStatus.FAILED
                experiment.error_message = result.get('error', 'Simulation returned no result') if result else "No result"
                experiment.quality_status = "FAIL"
                print(f"   Simulation failed: {experiment.error_message}")
            
            # Generate feedback
            print("\n[6] Generating HypothesisFeedback...")
            
            if experiment.quality_status == "PASS":
                feedback = HypothesisFeedback(
                    observations=f"Alpha achieved Sharpe={sharpe:.2f}, Fitness={fitness:.2f}, Turnover={turnover:.2f}",
                    hypothesis_evaluation="Hypothesis supported - price momentum captured successfully",
                    hypothesis_supported=True,
                    attribution=AttributionType.HYPOTHESIS,
                    decision=True,
                    reason="Meets all quality thresholds",
                    knowledge_extracted=[
                        f"If using rank(close), then achieves Sharpe around {sharpe:.1f}",
                        "If turnover is low, then signal quality is high"
                    ],
                    knowledge_confidence=0.8
                )
            elif experiment.quality_status == "OPTIMIZE":
                feedback = HypothesisFeedback(
                    observations=f"Alpha achieved Sharpe={sharpe:.2f}, Fitness={fitness:.2f}, Turnover={turnover:.2f}",
                    hypothesis_evaluation="Hypothesis partially supported - needs optimization",
                    hypothesis_supported=True,
                    attribution=AttributionType.HYPOTHESIS,
                    decision=False,
                    reason="Needs improvement in fitness or turnover",
                    new_hypothesis="Try adding temporal smoothing to reduce noise",
                    new_hypothesis_rationale="ts_mean or decay_linear could improve signal quality",
                    knowledge_extracted=[
                        f"If using simple rank(close), then may need smoothing for better fitness"
                    ],
                    knowledge_confidence=0.6
                )
            else:
                feedback = HypothesisFeedback(
                    observations=f"Alpha failed - Sharpe={sharpe:.2f}" if sharpe else f"Alpha failed: {experiment.error_message}",
                    hypothesis_evaluation="Hypothesis needs reconsideration" if sharpe else "Cannot evaluate - simulation failed",
                    hypothesis_supported=False,
                    attribution=AttributionType.HYPOTHESIS if sharpe else AttributionType.IMPLEMENTATION,
                    decision=False,
                    reason="Does not meet minimum Sharpe threshold" if sharpe else "Simulation error",
                    should_modify_hypothesis=True,
                    knowledge_extracted=[
                        "If using simple rank without smoothing, then may underperform"
                    ] if sharpe else [],
                    knowledge_confidence=0.5
                )
            
            print(f"   Decision: {feedback.decision}")
            print(f"   Attribution: {feedback.attribution.value}")
            print(f"   Observations: {feedback.observations[:60]}...")
            
            # Add to trace
            print("\n[7] Adding to ExperimentTrace...")
            idx = trace.add_experiment(experiment, feedback)
            print(f"   Added at index: {idx}")
            print(f"   Trace length: {len(trace)}")
            
            # Get stats
            stats = trace.get_stats()
            print(f"   Stats: {stats}")
            
            # Query knowledge
            print("\n[8] Querying Knowledge Base...")
            knowledge = trace.query_knowledge()
            print(f"   Success patterns: {len(knowledge.success_patterns)}")
            print(f"   Failure patterns: {len(knowledge.failure_patterns)}")
            
            if knowledge.success_patterns:
                print("   Learned patterns:")
                for pattern in knowledge.success_patterns[:3]:
                    print(f"      - If {pattern.condition}, then {pattern.conclusion}")
            
            print("\n" + "="*60)
            print("Core Architecture Test COMPLETE")
            print("="*60)
            
            return True
        
    except Exception as e:
        print(f"\n   ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main test runner."""
    print("\n" + "="*60)
    print("AIAC 2.0 - Real Mining Test")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Run tests
    results = {}
    
    # Test 1: BRAIN connection
    results['brain_connection'] = await test_brain_connection()
    
    # Test 2: Alpha simulation
    results['alpha_simulation'] = await test_alpha_simulation()
    
    # Test 3: Core architecture
    results['core_architecture'] = await test_new_core_architecture()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"   {test_name}: {status}")
    
    all_passed = all(results.values())
    print(f"\n   Overall: {'ALL TESTS PASSED' if all_passed else 'SOME TESTS FAILED'}")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
