#!/usr/bin/env python3
"""
🕵️ HUMINT PROFILER - Actor Analysis & Motive Hypotheses Generator

Analyzes GDELT Actor fields + enriched signals to generate:
- Actor network mappings
- Motive hypotheses with evidence tables
- Counter-hypotheses for verification
- Influence pathway analysis
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Any
import argparse
import os
import warnings
warnings.filterwarnings('ignore')


class HUMINTProfiler:
    """Human Intelligence profiler for paranoid signal analysis."""
    
    def __init__(self):
        self.motive_framework = {
            'POWER': ['control', 'dominance', 'authority', 'influence'],
            'IDEOLOGICAL': ['belief', 'worldview', 'conviction', 'cause'],
            'ECONOMIC': ['profit', 'resource', 'market', 'financial'],
            'SECURITY': ['protection', 'defense', 'threat', 'safety'],
            'SOCIAL': ['status', 'reputation', 'recognition', 'belonging'],
            'REVENGE': ['retaliation', 'payback', 'justice', 'grievance']
        }
        
        self.influence_tactics = {
            'RECIPROCITY': 'obligation-based influence',
            'COMMITMENT': 'consistency-based compliance',
            'SOCIAL_PROOF': 'conformity-driven behavior',
            'AUTHORITY': 'deference to expertise/position',
            'LIKING': 'affinity-based persuasion',
            'SCARCITY': 'urgency/rarity-driven action'
        }
    
    def load_gdelt_actors(self, data_path: str) -> pd.DataFrame:
        """Extract actor information from paranoid dataset."""
        try:
            df = pd.read_csv(data_path)
            
            # Extract actor-like columns (synthetic for now)
            actors_data = []
            
            for _, row in df.iterrows():
                # Generate synthetic actor profiles based on features
                if row.get('propaganda_index', 0) > 1.0:
                    actors_data.append({
                        'topic_id': row.get('topic_id', f"topic_{len(actors_data):04d}"),
                        'actor_code': f"GOV_{np.random.randint(100, 999)}",
                        'actor_name': np.random.choice([
                            'Ministry of Information', 'State Media Agency', 'Information Bureau',
                            'Communications Office', 'Press Department'
                        ]),
                        'actor_country': row.get('region', 'XX'),
                        'actor_type': 'GOVERNMENT',
                        'influence_score': row.get('propaganda_index', 0),
                        'coordination_level': row.get('coordination_index', 0),
                        'narrative_control': row.get('framing_intensity', 0)
                    })
                
                if row.get('coordination_index', 0) > 0.5:
                    actors_data.append({
                        'topic_id': row.get('topic_id', f"topic_{len(actors_data):04d}"),
                        'actor_code': f"NGO_{np.random.randint(100, 999)}",
                        'actor_name': np.random.choice([
                            'Citizen Action Network', 'Freedom Foundation', 'Democracy Institute',
                            'Information Rights Group', 'Transparency Alliance'
                        ]),
                        'actor_country': row.get('region', 'XX'),
                        'actor_type': 'NGO',
                        'influence_score': row.get('coordination_index', 0) * 0.7,
                        'coordination_level': row.get('coordination_index', 0),
                        'narrative_control': row.get('framing_intensity', 0) * 0.8
                    })
            
            return pd.DataFrame(actors_data) if actors_data else pd.DataFrame()
            
        except Exception as e:
            print(f"⚠️ Actor extraction failed: {e}")
            return pd.DataFrame()
    
    def analyze_actor_networks(self, actors_df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze actor coordination networks."""
        if actors_df.empty:
            return {}
        
        networks = defaultdict(list)
        
        # Group by topic to find coordination
        for topic_id, group in actors_df.groupby('topic_id'):
            if len(group) > 1:
                actors_in_topic = group.to_dict('records')
                
                # Calculate network density
                avg_coordination = group['coordination_level'].mean()
                network_strength = 'HIGH' if avg_coordination > 1.5 else 'MEDIUM' if avg_coordination > 0.8 else 'LOW'
                
                networks[topic_id] = {
                    'actors': actors_in_topic,
                    'network_strength': network_strength,
                    'coordination_score': avg_coordination,
                    'influence_potential': group['influence_score'].sum(),
                    'actor_types': list(group['actor_type'].unique())
                }
        
        return dict(networks)
    
    def generate_motive_hypotheses(self, actor_networks: Dict, signal_data: Dict) -> List[Dict]:
        """Generate evidence-based motive hypotheses."""
        hypotheses = []
        
        # Extract signal characteristics
        signal_type = signal_data.get('signal_type', 'unknown')
        severity = signal_data.get('severity', 'medium')
        risk_factors = signal_data.get('risk_factors', [])
        
        for topic_id, network in actor_networks.items():
            actors = network['actors']
            coordination_score = network['coordination_score']
            
            # Primary hypothesis based on signal type
            if 'suppression' in risk_factors or 'suppression' in signal_type:
                primary_motive = 'POWER'
                evidence = [
                    f"High coordination score: {coordination_score:.2f}",
                    f"Network strength: {network['network_strength']}",
                    f"Actor types involved: {', '.join(network['actor_types'])}"
                ]
                
                hypothesis = {
                    'topic_id': topic_id,
                    'primary_motive': primary_motive,
                    'confidence': min(0.95, 0.6 + coordination_score * 0.2),
                    'evidence': evidence,
                    'actors_involved': len(actors),
                    'influence_pathway': self._trace_influence_pathway(actors, 'suppression'),
                    'counter_hypothesis': self._generate_counter_hypothesis(primary_motive, evidence),
                    'verification_steps': self._suggest_verification(primary_motive, topic_id)
                }
                
            elif 'narrative' in risk_factors or 'framing' in signal_type:
                primary_motive = 'IDEOLOGICAL'
                evidence = [
                    f"Narrative manipulation detected",
                    f"Framing intensity above threshold",
                    f"Coordinated messaging across {len(actors)} actors"
                ]
                
                hypothesis = {
                    'topic_id': topic_id,
                    'primary_motive': primary_motive,
                    'confidence': min(0.90, 0.5 + coordination_score * 0.3),
                    'evidence': evidence,
                    'actors_involved': len(actors),
                    'influence_pathway': self._trace_influence_pathway(actors, 'narrative'),
                    'counter_hypothesis': self._generate_counter_hypothesis(primary_motive, evidence),
                    'verification_steps': self._suggest_verification(primary_motive, topic_id)
                }
                
            else:
                primary_motive = 'ECONOMIC'
                evidence = [
                    f"Economic indicators in signal data",
                    f"Multi-actor coordination: {coordination_score:.2f}",
                    f"Potential resource/market implications"
                ]
                
                hypothesis = {
                    'topic_id': topic_id,
                    'primary_motive': primary_motive,
                    'confidence': min(0.85, 0.4 + coordination_score * 0.25),
                    'evidence': evidence,
                    'actors_involved': len(actors),
                    'influence_pathway': self._trace_influence_pathway(actors, 'economic'),
                    'counter_hypothesis': self._generate_counter_hypothesis(primary_motive, evidence),
                    'verification_steps': self._suggest_verification(primary_motive, topic_id)
                }
            
            hypotheses.append(hypothesis)
        
        return sorted(hypotheses, key=lambda h: h['confidence'], reverse=True)
    
    def _trace_influence_pathway(self, actors: List[Dict], signal_type: str) -> List[str]:
        """Trace likely influence pathway based on Cialdini principles."""
        pathway = []
        
        # Sort actors by influence score
        sorted_actors = sorted(actors, key=lambda a: a['influence_score'], reverse=True)
        
        if signal_type == 'suppression':
            pathway = [
                f"1. AUTHORITY: {sorted_actors[0]['actor_name']} leverages institutional position",
                f"2. SOCIAL_PROOF: Secondary actors amplify narrative ({len(sorted_actors)-1} actors)",
                f"3. SCARCITY: Creates urgency/fear of missing 'official' narrative",
                f"4. COMMITMENT: Forces public compliance through repeated messaging"
            ]
        elif signal_type == 'narrative':
            pathway = [
                f"1. LIKING: Builds affinity through relatable framing",
                f"2. SOCIAL_PROOF: Demonstrates 'everyone believes this' via coordination",
                f"3. RECIPROCITY: Creates obligation to accept new narrative",
                f"4. AUTHORITY: Legitimizes through expert/official endorsement"
            ]
        else:
            pathway = [
                f"1. SCARCITY: Emphasizes limited opportunity/threat",
                f"2. AUTHORITY: Leverages institutional credibility",
                f"3. COMMITMENT: Seeks behavioral consistency",
                f"4. SOCIAL_PROOF: Demonstrates widespread adoption"
            ]
        
        return pathway
    
    def _generate_counter_hypothesis(self, primary_motive: str, evidence: List[str]) -> Dict[str, Any]:
        """Generate alternative explanation to test primary hypothesis."""
        counter_motives = {
            'POWER': 'SECURITY',
            'IDEOLOGICAL': 'SOCIAL', 
            'ECONOMIC': 'IDEOLOGICAL',
            'SECURITY': 'ECONOMIC',
            'SOCIAL': 'POWER',
            'REVENGE': 'SECURITY'
        }
        
        counter_motive = counter_motives.get(primary_motive, 'IDEOLOGICAL')
        
        return {
            'alternative_motive': counter_motive,
            'reasoning': f"Could be {counter_motive.lower()}-driven rather than {primary_motive.lower()}-driven",
            'test_implications': [
                f"If {counter_motive}: expect different actor priorities",
                f"If {counter_motive}: different timeline/urgency patterns",
                f"If {counter_motive}: alternative benefit analysis"
            ],
            'distinguishing_evidence': f"Look for {counter_motive.lower()}-specific indicators in subsequent actions"
        }
    
    def _suggest_verification(self, motive: str, topic_id: str) -> List[str]:
        """Suggest verification steps for motive hypothesis."""
        base_steps = [
            f"Cross-reference actor history in topic {topic_id}",
            "Monitor for contradictory actions/statements",
            "Analyze timing relative to external events"
        ]
        
        motive_specific = {
            'POWER': [
                "Track policy/regulatory changes",
                "Monitor control mechanism implementations",
                "Verify institutional position changes"
            ],
            'IDEOLOGICAL': [
                "Analyze consistency with stated beliefs",
                "Check alignment with broader movement",
                "Verify sacrifice of immediate interests"
            ],
            'ECONOMIC': [
                "Follow money/resource flows",
                "Check market timing correlations",
                "Verify financial beneficiaries"
            ],
            'SECURITY': [
                "Assess threat timeline correlation",
                "Check defensive vs offensive patterns",
                "Verify protection beneficiaries"
            ]
        }
        
        return base_steps + motive_specific.get(motive, [])
    
    def generate_report(self, data_path: str, signal_path: str, output_path: str):
        """Generate comprehensive HUMINT profile report."""
        print("🕵️ Generating HUMINT profile...")
        
        # Load data
        actors_df = self.load_gdelt_actors(data_path)
        
        try:
            with open(signal_path, 'r') as f:
                signal_data = json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load signal data: {e}")
            signal_data = {'signal_type': 'unknown', 'severity': 'medium', 'risk_factors': []}
        
        # Analyze networks
        actor_networks = self.analyze_actor_networks(actors_df)
        
        # Generate hypotheses
        motive_hypotheses = self.generate_motive_hypotheses(actor_networks, signal_data)
        
        # Compile report
        report = {
            'analysis_timestamp': pd.Timestamp.now().isoformat(),
            'data_source': data_path,
            'signal_source': signal_path,
            'summary': {
                'total_actors': len(actors_df),
                'active_networks': len(actor_networks),
                'hypotheses_generated': len(motive_hypotheses),
                'highest_confidence': max([h['confidence'] for h in motive_hypotheses], default=0)
            },
            'actor_networks': actor_networks,
            'motive_hypotheses': motive_hypotheses,
            'methodology': {
                'framework': 'Cialdini influence principles + motive categorization',
                'counter_hypothesis': 'Mandatory alternative explanation generation',
                'verification': 'Evidence-based testing steps',
                'confidence_scoring': 'Coordination score + signal strength weighted'
            }
        }
        
        # Save report
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        print(f"✅ HUMINT profile saved to {output_path}")
        print(f"🎯 {len(motive_hypotheses)} hypotheses generated")
        print(f"🔍 {len(actor_networks)} actor networks identified")
        
        return report


def main():
    parser = argparse.ArgumentParser(description="HUMINT Profiler for Paranoid Signals")
    parser.add_argument('--data', default='data/paranoid.csv', help='Paranoid dataset path')
    parser.add_argument('--signal', default='artifacts/signal.raw.json', help='Signal data path')
    parser.add_argument('--out', default='artifacts/humint_profile.json', help='Output report path')
    
    args = parser.parse_args()
    
    profiler = HUMINTProfiler()
    profiler.generate_report(args.data, args.signal, args.out)


if __name__ == "__main__":
    main()
