"""
Effects Database System - Comprehensive Effects Library
Includes Scanner Types, Lightshows, Soap Bubble Machine, and more
All effects with expanded attributes and self-learning capabilities
"""
import json
import math
import random
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import numpy as np


class EffectType(Enum):
    """Effect type enumeration"""
    SCANNER = "scanner"
    LIGHTSHOW = "lightshow"
    PARTICLE = "particle"
    EMISSION = "emission"
    REFRACTION = "refraction"
    INTERFERENCE = "interference"
    DIFFRACTION = "diffraction"
    FLUID = "fluid"
    MECHANICAL = "mechanical"
    OPTICAL = "optical"
    QUANTUM = "quantum"


class ScannerType(Enum):
    """Scanner type enumeration"""
    LINEAR = "linear"
    RADIAL = "radial"
    SPIRAL = "spiral"
    MATRIX = "matrix"
    LASER = "laser"
    LED = "led"
    HOLOGRAPHIC = "holographic"
    QUANTUM = "quantum"
    NEURAL = "neural"
    TEMPORAL = "temporal"


class LightShowType(Enum):
    """Lightshow type enumeration"""
    CHASE = "chase"
    STROBE = "strobe"
    PULSE = "pulse"
    WAVE = "wave"
    RAINBOW = "rainbow"
    SPECTRUM = "spectrum"
    GLOBAL = "global"
    SEQUENTIAL = "sequential"
    RANDOM = "random"
    SYNCED = "synced"
    SPIRAL = "spiral"
    RADIAL = "radial"
    MATRIX = "matrix"
    LASER = "laser"
    LED = "led"
    HOLOGRAPHIC = "holographic"
    QUANTUM = "quantum"
    NEURAL = "neural"
    TEMPORAL = "temporal"


class SelfLearningReasoner:
    """
    Self-Learning Reasoning System using Science and Math
    Solves equations and improves through experience
    """
    
    def __init__(self):
        self.learning_data = {}
        self.equation_cache = {}
        self.reasoning_history = []
        self.performance_metrics = {}
        
    def learn_from_equation(self, equation_type: str, problem: Dict, solution: Any):
        """Learn from solved equations"""
        if equation_type not in self.learning_data:
            self.learning_data[equation_type] = {
                'solved_count': 0,
                'average_time': 0,
                'patterns': [],
                'success_rate': 1.0
            }
        
        self.learning_data[equation_type]['solved_count'] += 1
        self.reasoning_history.append({
            'type': equation_type,
            'problem': problem,
            'solution': solution,
            'timestamp': datetime.now().isoformat()
        })
    
    def solve_physics_equation(self, equation_type: str, variables: Dict[str, float]) -> Dict[str, float]:
        """
        Solve physics equations using scientific formulas
        
        Supported equations:
        - kinematic (velocity, acceleration, position)
        - optical (refraction, diffraction, interference)
        - fluid_dynamics (pressure, flow, viscosity)
        - wave (frequency, wavelength, amplitude)
        """
        if equation_type == 'kinematic':
            # v = v0 + at
            # s = v0*t + 0.5*a*t^2
            # v^2 = v0^2 + 2*a*s
            result = {}
            if 'v0' in variables and 'a' in variables and 't' in variables:
                result['v'] = variables['v0'] + variables['a'] * variables['t']
                result['s'] = variables['v0'] * variables['t'] + 0.5 * variables['a'] * (variables['t'] ** 2)
            elif 'v0' in variables and 'a' in variables and 's' in variables:
                result['v'] = math.sqrt(variables['v0'] ** 2 + 2 * variables['a'] * variables['s'])
            return result
        
        elif equation_type == 'optical_refraction':
            # Snell's law: n1*sin(θ1) = n2*sin(θ2)
            n1 = variables.get('n1', 1.0)
            n2 = variables.get('n2', 1.33)
            theta1 = variables.get('theta1', 45)
            
            if theta1 and n1 and n2:
                sin_theta2 = (n1 / n2) * math.sin(math.radians(theta1))
                if -1 <= sin_theta2 <= 1:
                    theta2 = math.degrees(math.asin(sin_theta2))
                    result = {
                        'theta2': theta2,
                        'refractive_ratio': n2 / n1,
                        'critical_angle': math.degrees(math.asin(n1 / n2)) if n2 > n1 else None
                    }
                    self.learn_from_equation('optical_refraction', variables, result)
                    return result
        
        elif equation_type == 'wave':
            # v = f * λ
            # E = h * f
            # T = 1/f
            result = {}
            if 'f' in variables and 'lambda' in variables:
                result['v'] = variables['f'] * variables['lambda']
            if 'f' in variables:
                result['T'] = 1 / variables['f']
                h = 6.626e-34  # Planck constant
                result['E'] = h * variables['f']
            return result
        
        elif equation_type == 'fluid_dynamics':
            # Bernoulli's principle: P + 0.5*ρ*v^2 + ρ*g*h = constant
            # Poiseuille's law: Q = (π*r^4*ΔP) / (8*η*L)
            result = {}
            if 'rho' in variables and 'v' in variables:
                result['dynamic_pressure'] = 0.5 * variables['rho'] * (variables['v'] ** 2)
            if 'r' in variables and 'delta_p' in variables and 'eta' in variables and 'L' in variables:
                r = variables['r']
                result['flow_rate'] = (math.pi * (r ** 4) * variables['delta_p']) / (8 * variables['eta'] * variables['L'])
            return result
        
        return {}
    
    def solve_math_equation(self, equation_type: str, variables: Dict[str, float]) -> Dict[str, float]:
        """
        Solve mathematical equations
        
        Supported equations:
        - linear
        - quadratic
        - exponential
        - trigonometric
        - logarithmic
        - differential (basic)
        """
        if equation_type == 'linear':
            # y = mx + b
            if 'm' in variables and 'x' in variables and 'b' in variables:
                return {'y': variables['m'] * variables['x'] + variables['b']}
        
        elif equation_type == 'quadratic':
            # ax^2 + bx + c = 0
            a = variables.get('a', 1)
            b = variables.get('b', 0)
            c = variables.get('c', 0)
            
            discriminant = b ** 2 - 4 * a * c
            if discriminant >= 0:
                x1 = (-b + math.sqrt(discriminant)) / (2 * a)
                x2 = (-b - math.sqrt(discriminant)) / (2 * a)
                return {'x1': x1, 'x2': x2, 'discriminant': discriminant}
            else:
                real_part = -b / (2 * a)
                imag_part = math.sqrt(-discriminant) / (2 * a)
                return {
                    'x1': complex(real_part, imag_part),
                    'x2': complex(real_part, -imag_part),
                    'discriminant': discriminant
                }
        
        elif equation_type == 'exponential':
            # y = a * e^(bx)
            if 'a' in variables and 'b' in variables and 'x' in variables:
                return {'y': variables['a'] * math.exp(variables['b'] * variables['x'])}
        
        elif equation_type == 'trigonometric':
            # sin, cos, tan calculations
            angle = variables.get('angle', 0)
            angle_rad = math.radians(angle)
            return {
                'sin': math.sin(angle_rad),
                'cos': math.cos(angle_rad),
                'tan': math.tan(angle_rad) if math.cos(angle_rad) != 0 else None
            }
        
        elif equation_type == 'logarithmic':
            # y = log_b(x)
            base = variables.get('base', 10)
            x = variables.get('x', 1)
            if base > 0 and x > 0:
                return {'y': math.log(x, base) if base != math.e else math.log(x)}
        
        return {}
    
    def optimize_effect_parameters(self, effect_id: str, target_performance: Dict[str, float]) -> Dict[str, float]:
        """Optimize effect parameters using learned patterns"""
        # Use gradient descent or similar optimization
        # This is a simplified version
        
        if effect_id in self.learning_data:
            learned_patterns = self.learning_data[effect_id].get('patterns', [])
            if learned_patterns:
                # Find similar patterns and optimize
                best_params = learned_patterns[0].get('optimal_params', {})
                return best_params
        
        return {}
    
    def reason_about_effect(self, effect_config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply scientific reasoning to effect configuration"""
        reasoning_result = {
            'recommendations': [],
            'warnings': [],
            'optimizations': {},
            'scientific_basis': {}
        }
        
        # Analyze effect parameters scientifically
        if 'frequency' in effect_config:
            freq = effect_config['frequency']
            # Check if frequency is within human perception range (0-20kHz)
            if freq > 20000:
                reasoning_result['warnings'].append(f"Frequency {freq}Hz exceeds human hearing range")
            elif freq < 0:
                reasoning_result['warnings'].append("Negative frequency is not physically meaningful")
            
            # Calculate period and wavelength
            if freq > 0:
                period = 1 / freq
                # Assuming speed of light for optical effects
                wavelength = 3e8 / freq if freq < 1e15 else None
                reasoning_result['scientific_basis']['period'] = period
                reasoning_result['scientific_basis']['wavelength'] = wavelength
        
        # Analyze color values
        if 'color' in effect_config:
            color = effect_config['color']
            if isinstance(color, (list, tuple)) and len(color) >= 3:
                r, g, b = color[0], color[1], color[2]
                # Calculate luminance (brightness perception)
                luminance = 0.299 * r + 0.587 * g + 0.114 * b
                reasoning_result['scientific_basis']['luminance'] = luminance
                
                if luminance > 200:
                    reasoning_result['warnings'].append("High luminance may cause eye strain")
        
        return reasoning_result


# Initialize self-learning reasoner
reasoner = SelfLearningReasoner()


class EffectDatabase:
    """Comprehensive Effects Database with Scanner Types, Lightshows, and More"""
    
    def __init__(self):
        self.effects = {}
        self.scanner_types = {}
        self.lightshow_types = {}
        self.initialize_scanner_types()
        self.initialize_lightshow_types()
        self.initialize_soap_bubble_machine()
        self.initialize_other_effects()
    
    def initialize_scanner_types(self):
        """Initialize all scanner types with lightshow capabilities"""
        
        # Linear Scanner
        self.scanner_types['linear'] = {
            'id': 'linear_scanner',
            'name': 'Linear Scanner',
            'type': EffectType.SCANNER.value,
            'scanner_type': ScannerType.LINEAR.value,
            'description': 'Linear scanning pattern with adjustable speed and direction',
            'attributes': {
                'speed': {'value': 50, 'min': 1, 'max': 200, 'unit': 'px/s'},
                'direction': {'value': 'horizontal', 'options': ['horizontal', 'vertical', 'diagonal']},
                'beam_width': {'value': 5, 'min': 1, 'max': 50, 'unit': 'px'},
                'color': {'value': [0, 255, 0], 'type': 'rgb'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'fade': {'value': 0.5, 'min': 0.0, 'max': 1.0},
                'frequency': {'value': 10, 'min': 0.1, 'max': 100, 'unit': 'Hz'},
                'wavelength': {'value': None, 'calculated': True},  # Calculated from frequency
                'period': {'value': None, 'calculated': True},  # Calculated from frequency
            },
            'lightshow': {
                'enabled': True,
                'type': LightShowType.CHASE.value,
                'patterns': ['chase', 'fade', 'strobe'],
                'sync': True,
                'music_reactive': True,
                'beat_detection': True
            },
            'physics': {
                'velocity': {'value': None, 'calculated': True},
                'acceleration': {'value': 0, 'min': -100, 'max': 100},
                'kinetic_energy': {'value': None, 'calculated': True}
            },
            'optical': {
                'refraction_index': {'value': 1.0, 'min': 1.0, 'max': 2.5},
                'diffraction': {'value': False, 'enabled': True},
                'interference': {'value': False, 'enabled': True}
            },
            'quantum': {
                'entanglement': False,
                'superposition': False,
                'tunneling': False
            },
            'self_learning': {
                'learning_enabled': True,
                'optimization_active': True,
                'performance_tracking': True
            }
        }
        
        # Radial Scanner
        self.scanner_types['radial'] = {
            'id': 'radial_scanner',
            'name': 'Radial Scanner',
            'type': EffectType.SCANNER.value,
            'scanner_type': ScannerType.RADIAL.value,
            'description': 'Radial scanning pattern emanating from center point',
            'attributes': {
                'angular_speed': {'value': 30, 'min': 1, 'max': 360, 'unit': 'deg/s'},
                'start_angle': {'value': 0, 'min': 0, 'max': 360, 'unit': 'deg'},
                'end_angle': {'value': 360, 'min': 0, 'max': 360, 'unit': 'deg'},
                'radius': {'value': 500, 'min': 10, 'max': 5000, 'unit': 'px'},
                'beam_width': {'value': 8, 'min': 1, 'max': 50, 'unit': 'px'},
                'color': {'value': [255, 100, 0], 'type': 'rgb'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'frequency': {'value': 5, 'min': 0.1, 'max': 100, 'unit': 'Hz'},
            },
            'lightshow': {
                'enabled': True,
                'type': LightShowType.RADIAL.value,
                'patterns': ['spiral', 'sweep', 'pulse'],
                'sync': True,
                'music_reactive': True
            },
            'physics': {
                'angular_velocity': {'value': None, 'calculated': True},
                'centripetal_force': {'value': None, 'calculated': True},
                'tangential_velocity': {'value': None, 'calculated': True}
            },
            'optical': {
                'refraction_index': {'value': 1.0},
                'diffraction': {'value': True, 'enabled': True},
                'interference': {'value': True, 'enabled': True}
            },
            'self_learning': {
                'learning_enabled': True,
                'optimization_active': True
            }
        }
        
        # Spiral Scanner
        self.scanner_types['spiral'] = {
            'id': 'spiral_scanner',
            'name': 'Spiral Scanner',
            'type': EffectType.SCANNER.value,
            'scanner_type': ScannerType.SPIRAL.value,
            'description': 'Spiral scanning pattern with expanding/contracting radius',
            'attributes': {
                'angular_speed': {'value': 45, 'min': 1, 'max': 360, 'unit': 'deg/s'},
                'radial_speed': {'value': 10, 'min': 1, 'max': 100, 'unit': 'px/s'},
                'spiral_tightness': {'value': 0.1, 'min': 0.01, 'max': 1.0},
                'radius_min': {'value': 50, 'min': 10, 'max': 1000, 'unit': 'px'},
                'radius_max': {'value': 800, 'min': 100, 'max': 5000, 'unit': 'px'},
                'beam_width': {'value': 6, 'min': 1, 'max': 50, 'unit': 'px'},
                'color': {'value': [100, 200, 255], 'type': 'rgb'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'frequency': {'value': 3, 'min': 0.1, 'max': 100, 'unit': 'Hz'},
            },
            'lightshow': {
                'enabled': True,
                'type': LightShowType.SPIRAL.value,
                'patterns': ['spiral_expand', 'spiral_contract', 'spiral_pulse'],
                'sync': True,
                'music_reactive': True
            },
            'physics': {
                'angular_velocity': {'value': None, 'calculated': True},
                'radial_velocity': {'value': None, 'calculated': True},
                'total_velocity': {'value': None, 'calculated': True}
            },
            'self_learning': {
                'learning_enabled': True
            }
        }
        
        # Matrix Scanner (Grid-based)
        self.scanner_types['matrix'] = {
            'id': 'matrix_scanner',
            'name': 'Matrix Scanner',
            'type': EffectType.SCANNER.value,
            'scanner_type': ScannerType.MATRIX.value,
            'description': 'Grid-based matrix scanning pattern',
            'attributes': {
                'grid_width': {'value': 20, 'min': 5, 'max': 100},
                'grid_height': {'value': 20, 'min': 5, 'max': 100},
                'scan_direction': {'value': 'row', 'options': ['row', 'column', 'diagonal', 'random']},
                'scan_speed': {'value': 5, 'min': 1, 'max': 50, 'unit': 'cells/s'},
                'cell_size': {'value': 25, 'min': 5, 'max': 100, 'unit': 'px'},
                'color': {'value': [0, 255, 0], 'type': 'rgb'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'frequency': {'value': 2, 'min': 0.1, 'max': 100, 'unit': 'Hz'},
            },
            'lightshow': {
                'enabled': True,
                'type': LightShowType.MATRIX.value,
                'patterns': ['matrix_rain', 'matrix_wave', 'matrix_pulse'],
                'sync': True
            },
            'self_learning': {
                'learning_enabled': True
            }
        }
        
        # Laser Scanner
        self.scanner_types['laser'] = {
            'id': 'laser_scanner',
            'name': 'Laser Scanner',
            'type': EffectType.SCANNER.value,
            'scanner_type': ScannerType.LASER.value,
            'description': 'High-intensity laser scanning with diffraction patterns',
            'attributes': {
                'power': {'value': 100, 'min': 1, 'max': 1000, 'unit': 'mW'},
                'wavelength': {'value': 532, 'min': 400, 'max': 700, 'unit': 'nm'},
                'beam_divergence': {'value': 0.5, 'min': 0.1, 'max': 5.0, 'unit': 'mrad'},
                'scan_speed': {'value': 100, 'min': 1, 'max': 1000, 'unit': 'deg/s'},
                'color': {'value': [0, 255, 100], 'type': 'rgb'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'frequency': {'value': 20, 'min': 0.1, 'max': 1000, 'unit': 'Hz'},
            },
            'lightshow': {
                'enabled': True,
                'type': LightShowType.LASER.value,
                'patterns': ['laser_sweep', 'laser_grid', 'laser_spiral'],
                'sync': True,
                'music_reactive': True,
                'beat_detection': True
            },
            'optical': {
                'wavelength_nm': {'value': 532, 'min': 400, 'max': 700},
                'frequency_hz': {'value': None, 'calculated': True},  # c / wavelength
                'photon_energy': {'value': None, 'calculated': True},  # h * f
                'refraction_index': {'value': 1.0},
                'diffraction': {'value': True, 'enabled': True},
                'interference': {'value': True, 'enabled': True},
                'coherence_length': {'value': None, 'calculated': True}
            },
            'physics': {
                'speed_of_light': 299792458,  # m/s
                'plancks_constant': 6.626e-34,  # J*s
                'photon_energy_j': {'value': None, 'calculated': True}
            },
            'safety': {
                'power_class': {'value': None, 'calculated': True},
                'eye_safe': {'value': False, 'check': True},
                'max_exposure_time': {'value': None, 'calculated': True}
            },
            'self_learning': {
                'learning_enabled': True,
                'optimization_active': True,
                'safety_monitoring': True
            }
        }
        
        # LED Scanner
        self.scanner_types['led'] = {
            'id': 'led_scanner',
            'name': 'LED Scanner',
            'type': EffectType.SCANNER.value,
            'scanner_type': ScannerType.LED.value,
            'description': 'LED array scanning with color mixing',
            'attributes': {
                'led_count': {'value': 144, 'min': 1, 'max': 1000},
                'led_spacing': {'value': 10, 'min': 1, 'max': 50, 'unit': 'mm'},
                'color_depth': {'value': 8, 'min': 1, 'max': 16, 'unit': 'bits'},
                'refresh_rate': {'value': 60, 'min': 1, 'max': 1000, 'unit': 'Hz'},
                'color': {'value': [255, 255, 255], 'type': 'rgb'},
                'brightness': {'value': 255, 'min': 0, 'max': 255},
                'frequency': {'value': 60, 'min': 0.1, 'max': 1000, 'unit': 'Hz'},
            },
            'lightshow': {
                'enabled': True,
                'type': LightShowType.LED.value,
                'patterns': ['chase', 'fade', 'rainbow', 'spectrum'],
                'sync': True,
                'music_reactive': True,
                'color_mixing': True
            },
            'physics': {
                'power_consumption': {'value': None, 'calculated': True},
                'heat_generation': {'value': None, 'calculated': True},
                'efficiency': {'value': 0.8, 'min': 0.0, 'max': 1.0}
            },
            'self_learning': {
                'learning_enabled': True,
                'power_optimization': True
            }
        }
        
        # Holographic Scanner
        self.scanner_types['holographic'] = {
            'id': 'holographic_scanner',
            'name': 'Holographic Scanner',
            'type': EffectType.SCANNER.value,
            'scanner_type': ScannerType.HOLOGRAPHIC.value,
            'description': '3D holographic scanning with depth perception',
            'attributes': {
                'depth_layers': {'value': 10, 'min': 1, 'max': 100},
                'depth_range': {'value': 500, 'min': 10, 'max': 5000, 'unit': 'px'},
                'holographic_resolution': {'value': 1080, 'min': 480, 'max': 4320},
                'scan_speed': {'value': 30, 'min': 1, 'max': 200, 'unit': 'deg/s'},
                'color': {'value': [100, 200, 255], 'type': 'rgb'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'frequency': {'value': 30, 'min': 0.1, 'max': 1000, 'unit': 'Hz'},
            },
            'lightshow': {
                'enabled': True,
                'type': LightShowType.HOLOGRAPHIC.value,
                'patterns': ['hologram_scan', 'depth_wave', '3d_pulse'],
                'sync': True,
                'music_reactive': True,
                'spatial_audio': True
            },
            'optical': {
                'refraction_index': {'value': 1.33},
                'diffraction': {'value': True, 'enabled': True},
                'interference': {'value': True, 'enabled': True},
                'coherence': {'value': 0.9, 'min': 0.0, 'max': 1.0}
            },
            'self_learning': {
                'learning_enabled': True,
                'depth_optimization': True
            }
        }
        
        # Quantum Scanner
        self.scanner_types['quantum'] = {
            'id': 'quantum_scanner',
            'name': 'Quantum Scanner',
            'type': EffectType.SCANNER.value,
            'scanner_type': ScannerType.QUANTUM.value,
            'description': 'Quantum-based scanning with superposition and entanglement',
            'attributes': {
                'quantum_states': {'value': 8, 'min': 2, 'max': 1024},
                'superposition_depth': {'value': 3, 'min': 1, 'max': 10},
                'entanglement_pairs': {'value': 4, 'min': 1, 'max': 100},
                'scan_speed': {'value': 50, 'min': 1, 'max': 200, 'unit': 'qubits/s'},
                'color': {'value': [200, 0, 255], 'type': 'rgb'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'frequency': {'value': 100, 'min': 0.1, 'max': 10000, 'unit': 'Hz'},
            },
            'lightshow': {
                'enabled': True,
                'type': LightShowType.QUANTUM.value,
                'patterns': ['quantum_entangle', 'superposition_wave', 'collapse_pulse'],
                'sync': True,
                'music_reactive': True
            },
            'quantum': {
                'entanglement': True,
                'superposition': True,
                'tunneling': True,
                'decoherence_time': {'value': 1.0, 'unit': 's'},
                'quantum_efficiency': {'value': 0.95, 'min': 0.0, 'max': 1.0}
            },
            'self_learning': {
                'learning_enabled': True,
                'quantum_optimization': True
            }
        }
        
        # Neural Scanner
        self.scanner_types['neural'] = {
            'id': 'neural_scanner',
            'name': 'Neural Scanner',
            'type': EffectType.SCANNER.value,
            'scanner_type': ScannerType.NEURAL.value,
            'description': 'Neural network-driven scanning with AI pattern recognition',
            'attributes': {
                'neural_layers': {'value': 5, 'min': 1, 'max': 20},
                'neurons_per_layer': {'value': 128, 'min': 8, 'max': 1024},
                'learning_rate': {'value': 0.01, 'min': 0.0001, 'max': 1.0},
                'scan_speed': {'value': 60, 'min': 1, 'max': 1000, 'unit': 'patterns/s'},
                'color': {'value': [255, 150, 0], 'type': 'rgb'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'frequency': {'value': 60, 'min': 0.1, 'max': 1000, 'unit': 'Hz'},
            },
            'lightshow': {
                'enabled': True,
                'type': LightShowType.NEURAL.value,
                'patterns': ['neural_pattern', 'learning_wave', 'recognition_pulse'],
                'sync': True,
                'music_reactive': True,
                'ai_generated': True
            },
            'neural': {
                'activation_function': 'relu',
                'loss_function': 'mse',
                'optimizer': 'adam',
                'training_active': True,
                'inference_mode': True
            },
            'self_learning': {
                'learning_enabled': True,
                'neural_optimization': True,
                'pattern_recognition': True
            }
        }
        
        # Temporal Scanner
        self.scanner_types['temporal'] = {
            'id': 'temporal_scanner',
            'name': 'Temporal Scanner',
            'type': EffectType.SCANNER.value,
            'scanner_type': ScannerType.TEMPORAL.value,
            'description': 'Time-based scanning with temporal dilation effects',
            'attributes': {
                'time_scale': {'value': 1.0, 'min': 0.1, 'max': 10.0},
                'temporal_resolution': {'value': 1000, 'min': 10, 'max': 100000, 'unit': 'samples/s'},
                'scan_speed': {'value': 1, 'min': 0.1, 'max': 100, 'unit': 'time/s'},
                'color': {'value': [255, 200, 100], 'type': 'rgb'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'frequency': {'value': 1, 'min': 0.001, 'max': 100, 'unit': 'Hz'},
            },
            'lightshow': {
                'enabled': True,
                'type': LightShowType.TEMPORAL.value,
                'patterns': ['time_wave', 'temporal_pulse', 'time_dilation'],
                'sync': True,
                'music_reactive': True
            },
            'temporal': {
                'time_dilation': True,
                'time_travel': False,
                'parallel_timelines': True,
                'causality_preservation': True
            },
            'physics': {
                'relativistic_effects': True,
                'lorentz_factor': {'value': None, 'calculated': True}
            },
            'self_learning': {
                'learning_enabled': True,
                'temporal_optimization': True
            }
        }
    
    def initialize_lightshow_types(self):
        """Initialize all lightshow types with expanded attributes"""
        
        # Chase Lightshow
        self.lightshow_types['chase'] = {
            'id': 'chase_lightshow',
            'name': 'Chase Lightshow',
            'type': EffectType.LIGHTSHOW.value,
            'lightshow_type': LightShowType.CHASE.value,
            'description': 'Chasing light pattern across multiple elements',
            'attributes': {
                'element_count': {'value': 10, 'min': 2, 'max': 1000},
                'chase_speed': {'value': 50, 'min': 1, 'max': 500, 'unit': 'elements/s'},
                'direction': {'value': 'forward', 'options': ['forward', 'backward', 'ping_pong', 'random']},
                'fade_amount': {'value': 0.5, 'min': 0.0, 'max': 1.0},
                'color': {'value': [255, 255, 255], 'type': 'rgb'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'frequency': {'value': 10, 'min': 0.1, 'max': 100, 'unit': 'Hz'},
            },
            'physics': {
                'velocity': {'value': None, 'calculated': True},
                'momentum': {'value': None, 'calculated': True}
            },
            'self_learning': {
                'learning_enabled': True,
                'pattern_optimization': True
            }
        }
        
        # Strobe Lightshow
        self.lightshow_types['strobe'] = {
            'id': 'strobe_lightshow',
            'name': 'Strobe Lightshow',
            'type': EffectType.LIGHTSHOW.value,
            'lightshow_type': LightShowType.STROBE.value,
            'description': 'Rapid flashing strobe effect',
            'attributes': {
                'flash_duration': {'value': 0.1, 'min': 0.01, 'max': 1.0, 'unit': 's'},
                'flash_interval': {'value': 0.2, 'min': 0.01, 'max': 10.0, 'unit': 's'},
                'intensity_peak': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'intensity_base': {'value': 0.0, 'min': 0.0, 'max': 1.0},
                'color': {'value': [255, 255, 255], 'type': 'rgb'},
                'frequency': {'value': 5, 'min': 0.1, 'max': 100, 'unit': 'Hz'},
            },
            'safety': {
                'epilepsy_warning': True,
                'max_flash_rate': {'value': 10, 'unit': 'Hz'},
                'safe_mode': {'value': False, 'enabled': True}
            },
            'physics': {
                'power_per_flash': {'value': None, 'calculated': True},
                'total_energy': {'value': None, 'calculated': True}
            },
            'self_learning': {
                'learning_enabled': True,
                'safety_monitoring': True
            }
        }
        
        # Pulse Lightshow
        self.lightshow_types['pulse'] = {
            'id': 'pulse_lightshow',
            'name': 'Pulse Lightshow',
            'type': EffectType.LIGHTSHOW.value,
            'lightshow_type': LightShowType.PULSE.value,
            'description': 'Smooth pulsing light effect',
            'attributes': {
                'pulse_rate': {'value': 2, 'min': 0.1, 'max': 20, 'unit': 'Hz'},
                'pulse_shape': {'value': 'sine', 'options': ['sine', 'square', 'triangle', 'sawtooth', 'custom']},
                'intensity_min': {'value': 0.2, 'min': 0.0, 'max': 1.0},
                'intensity_max': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'color': {'value': [255, 100, 100], 'type': 'rgb'},
                'frequency': {'value': 2, 'min': 0.1, 'max': 20, 'unit': 'Hz'},
            },
            'physics': {
                'waveform': {'value': 'sine', 'type': 'function'},
                'amplitude': {'value': None, 'calculated': True},
                'period': {'value': None, 'calculated': True}
            },
            'self_learning': {
                'learning_enabled': True
            }
        }
        
        # Wave Lightshow
        self.lightshow_types['wave'] = {
            'id': 'wave_lightshow',
            'name': 'Wave Lightshow',
            'type': EffectType.LIGHTSHOW.value,
            'lightshow_type': LightShowType.WAVE.value,
            'description': 'Wave-like light pattern',
            'attributes': {
                'wave_frequency': {'value': 1, 'min': 0.1, 'max': 20, 'unit': 'Hz'},
                'wavelength': {'value': 200, 'min': 10, 'max': 5000, 'unit': 'px'},
                'amplitude': {'value': 100, 'min': 1, 'max': 1000, 'unit': 'px'},
                'wave_speed': {'value': 50, 'min': 1, 'max': 500, 'unit': 'px/s'},
                'wave_type': {'value': 'sine', 'options': ['sine', 'cosine', 'square', 'triangle']},
                'color': {'value': [100, 200, 255], 'type': 'rgb'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
            },
            'physics': {
                'wave_velocity': {'value': None, 'calculated': True},  # v = f * λ
                'angular_frequency': {'value': None, 'calculated': True},  # ω = 2πf
                'wave_number': {'value': None, 'calculated': True},  # k = 2π/λ
                'wave_energy': {'value': None, 'calculated': True}  # E ∝ A²
            },
            'self_learning': {
                'learning_enabled': True,
                'wave_optimization': True
            }
        }
        
        # Rainbow Lightshow
        self.lightshow_types['rainbow'] = {
            'id': 'rainbow_lightshow',
            'name': 'Rainbow Lightshow',
            'type': EffectType.LIGHTSHOW.value,
            'lightshow_type': LightShowType.RAINBOW.value,
            'description': 'Full spectrum rainbow color cycle',
            'attributes': {
                'color_cycle_speed': {'value': 1, 'min': 0.1, 'max': 10, 'unit': 'cycles/s'},
                'saturation': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'brightness': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'hue_start': {'value': 0, 'min': 0, 'max': 360, 'unit': 'deg'},
                'hue_range': {'value': 360, 'min': 0, 'max': 360, 'unit': 'deg'},
                'frequency': {'value': 1, 'min': 0.1, 'max': 10, 'unit': 'Hz'},
            },
            'optical': {
                'wavelength_range': {'value': [380, 750], 'unit': 'nm'},
                'spectral_resolution': {'value': 1, 'unit': 'nm'},
                'color_temperature': {'value': None, 'calculated': True}
            },
            'physics': {
                'spectral_power_distribution': {'value': None, 'calculated': True}
            },
            'self_learning': {
                'learning_enabled': True,
                'color_optimization': True
            }
        }
        
        # Spectrum Lightshow
        self.lightshow_types['spectrum'] = {
            'id': 'spectrum_lightshow',
            'name': 'Spectrum Lightshow',
            'type': EffectType.LIGHTSHOW.value,
            'lightshow_type': LightShowType.SPECTRUM.value,
            'description': 'Spectrum analyzer-style lightshow',
            'attributes': {
                'band_count': {'value': 32, 'min': 8, 'max': 256},
                'band_width': {'value': 10, 'min': 1, 'max': 100, 'unit': 'px'},
                'band_spacing': {'value': 2, 'min': 0, 'max': 50, 'unit': 'px'},
                'sensitivity': {'value': 1.0, 'min': 0.1, 'max': 10.0},
                'decay_rate': {'value': 0.9, 'min': 0.1, 'max': 1.0},
                'color_mode': {'value': 'gradient', 'options': ['gradient', 'frequency', 'intensity', 'custom']},
                'frequency': {'value': 60, 'min': 1, 'max': 1000, 'unit': 'Hz'},
            },
            'audio': {
                'music_reactive': True,
                'beat_detection': True,
                'frequency_analysis': True,
                'fft_size': {'value': 2048, 'min': 256, 'max': 8192}
            },
            'physics': {
                'frequency_response': {'value': None, 'calculated': True},
                'power_spectrum': {'value': None, 'calculated': True}
            },
            'self_learning': {
                'learning_enabled': True,
                'audio_optimization': True
            }
        }
    
    def initialize_soap_bubble_machine(self):
        """Initialize Soap Bubble Machine effect with comprehensive attributes"""
        
        self.effects['soap_bubble_machine'] = {
            'id': 'soap_bubble_machine',
            'name': 'Soap Bubble Machine',
            'type': EffectType.FLUID.value,
            'description': 'Realistic soap bubble generation and physics simulation',
            'attributes': {
                'bubble_count': {'value': 50, 'min': 1, 'max': 1000},
                'bubble_size_min': {'value': 10, 'min': 1, 'max': 100, 'unit': 'px'},
                'bubble_size_max': {'value': 100, 'min': 10, 'max': 500, 'unit': 'px'},
                'bubble_size_distribution': {'value': 'normal', 'options': ['uniform', 'normal', 'exponential', 'custom']},
                'generation_rate': {'value': 5, 'min': 0.1, 'max': 100, 'unit': 'bubbles/s'},
                'lifetime_min': {'value': 2, 'min': 0.1, 'max': 60, 'unit': 's'},
                'lifetime_max': {'value': 10, 'min': 0.1, 'max': 60, 'unit': 's'},
                'rise_speed': {'value': 30, 'min': 1, 'max': 500, 'unit': 'px/s'},
                'rise_acceleration': {'value': -50, 'min': -200, 'max': 0, 'unit': 'px/s²'},
                'wind_effect': {'value': 0, 'min': -100, 'max': 100, 'unit': 'px/s'},
                'turbulence': {'value': 5, 'min': 0, 'max': 50, 'unit': 'px/s'},
                'color': {'value': [150, 200, 255], 'type': 'rgb'},
                'opacity': {'value': 0.6, 'min': 0.0, 'max': 1.0},
                'reflectivity': {'value': 0.8, 'min': 0.0, 'max': 1.0},
                'refraction_index': {'value': 1.33, 'min': 1.0, 'max': 2.5},
                'frequency': {'value': 5, 'min': 0.1, 'max': 100, 'unit': 'Hz'},
            },
            'physics': {
                'fluid_dynamics': {
                    'density_air': {'value': 1.225, 'unit': 'kg/m³'},
                    'density_bubble': {'value': 0.001, 'min': 0.0001, 'max': 0.1, 'unit': 'kg/m³'},
                    'viscosity_air': {'value': 1.81e-5, 'unit': 'Pa·s'},
                    'surface_tension': {'value': 0.072, 'min': 0.01, 'max': 1.0, 'unit': 'N/m'},
                    'gravity': {'value': 9.81, 'unit': 'm/s²'},
                    'buoyancy_force': {'value': None, 'calculated': True},
                    'drag_force': {'value': None, 'calculated': True},
                    'terminal_velocity': {'value': None, 'calculated': True},
                    'reynolds_number': {'value': None, 'calculated': True},
                    'stokes_law_applicable': {'value': None, 'calculated': True}
                },
                'optics': {
                    'thin_film_interference': True,
                    'interference_thickness': {'value': None, 'calculated': True},
                    'refractive_index_soap': {'value': 1.33},
                    'refractive_index_air': {'value': 1.0},
                    'wavelength_dominant': {'value': 550, 'unit': 'nm'},
                    'iridescent_colors': {'value': True, 'enabled': True},
                    'color_shift_rate': {'value': 0.1, 'min': 0.0, 'max': 1.0, 'unit': 'cycles/s'},
                    'thickness_variation': {'value': 0.1, 'min': 0.0, 'max': 1.0},
                    'light_polarization': {'value': False, 'enabled': True},
                    'diffraction_pattern': {'value': True, 'enabled': True}
                },
                'mechanics': {
                    'elasticity': {'value': 0.5, 'min': 0.0, 'max': 1.0},
                    'surface_area': {'value': None, 'calculated': True},  # 4πr²
                    'volume': {'value': None, 'calculated': True},  # (4/3)πr³
                    'mass': {'value': None, 'calculated': True},
                    'momentum': {'value': None, 'calculated': True},
                    'kinetic_energy': {'value': None, 'calculated': True},
                    'potential_energy': {'value': None, 'calculated': True},
                    'total_energy': {'value': None, 'calculated': True},
                    'angular_momentum': {'value': None, 'calculated': True}
                },
                'thermodynamics': {
                    'temperature': {'value': 20, 'min': 0, 'max': 100, 'unit': '°C'},
                    'evaporation_rate': {'value': 0.01, 'min': 0.0, 'max': 1.0, 'unit': 's⁻¹'},
                    'latent_heat': {'value': 2260000, 'unit': 'J/kg'},
                    'heat_transfer': {'value': None, 'calculated': True},
                    'lifetime_thermal': {'value': None, 'calculated': True}
                },
                'wave_properties': {
                    'capillary_waves': True,
                    'wave_frequency': {'value': None, 'calculated': True},
                    'wave_amplitude': {'value': None, 'calculated': True},
                    'wave_speed': {'value': None, 'calculated': True}
                }
            },
            'visual': {
                'reflection': True,
                'refraction': True,
                'caustics': True,
                'iridescence': True,
                'shadows': True,
                'highlights': True,
                'specular_highlight': {'value': True, 'intensity': 0.9},
                'environment_mapping': {'value': True, 'enabled': True},
                'blur_radius': {'value': 2, 'min': 0, 'max': 20, 'unit': 'px'},
                'particle_trail': {'value': False, 'enabled': True},
                'color_shift': {'value': True, 'rate': 0.1}
            },
            'interaction': {
                'collision_detection': True,
                'collision_response': {'value': 'elastic', 'options': ['elastic', 'inelastic', 'sticky']},
                'merge_on_collision': {'value': False, 'enabled': True},
                'burst_on_collision': {'value': True, 'enabled': True},
                'gravity_wells': {'value': False, 'enabled': True},
                'magnetic_fields': {'value': False, 'enabled': True},
                'user_interaction': {'value': True, 'enabled': True}
            },
            'sound': {
                'pop_sound': {'value': True, 'enabled': True},
                'rise_sound': {'value': False, 'enabled': True},
                'ambient_sound': {'value': False, 'enabled': True},
                'frequency_response': {'value': None, 'calculated': True}
            },
            'self_learning': {
                'learning_enabled': True,
                'physics_optimization': True,
                'rendering_optimization': True,
                'performance_tracking': True,
                'adaptive_quality': True,
                'bubble_pop_prediction': True,
                'lifetime_prediction': True,
                'trajectory_optimization': True
            },
            'advanced': {
                'multi_layer_bubbles': {'value': True, 'enabled': True},
                'nested_bubbles': {'value': False, 'enabled': True},
                'bubble_chains': {'value': False, 'enabled': True},
                'foam_generation': {'value': False, 'enabled': True},
                'liquid_simulation': {'value': False, 'enabled': True},
                'particle_system_integration': {'value': True, 'enabled': True}
            }
        }
    
    def initialize_other_effects(self):
        """Initialize other effects with expanded attributes"""
        
        # Particle Effect
        self.effects['particle'] = {
            'id': 'particle',
            'name': 'Particle Effect',
            'type': EffectType.PARTICLE.value,
            'description': 'Generic particle system',
            'attributes': {
                'particle_count': {'value': 100, 'min': 1, 'max': 10000},
                'size': {'value': 5, 'min': 1, 'max': 100, 'unit': 'px'},
                'lifetime': {'value': 5, 'min': 0.1, 'max': 60, 'unit': 's'},
                'velocity': {'value': 50, 'min': 1, 'max': 1000, 'unit': 'px/s'},
                'color': {'value': [255, 255, 255], 'type': 'rgb'},
                'frequency': {'value': 60, 'min': 0.1, 'max': 1000, 'unit': 'Hz'},
            },
            'physics': {
                'gravity': {'value': 100, 'min': 0, 'max': 1000, 'unit': 'px/s²'},
                'friction': {'value': 0.98, 'min': 0.0, 'max': 1.0}
            },
            'self_learning': {
                'learning_enabled': True
            }
        }
        
        # Emission Effect
        self.effects['emission'] = {
            'id': 'emission',
            'name': 'Emission Effect',
            'type': EffectType.EMISSION.value,
            'description': 'Light emission effect',
            'attributes': {
                'emission_rate': {'value': 10, 'min': 0.1, 'max': 1000, 'unit': 'photons/s'},
                'wavelength': {'value': 550, 'min': 380, 'max': 750, 'unit': 'nm'},
                'intensity': {'value': 1.0, 'min': 0.0, 'max': 1.0},
                'color': {'value': [255, 255, 255], 'type': 'rgb'},
                'frequency': {'value': 5.45e14, 'min': 4e14, 'max': 8e14, 'unit': 'Hz'},
            },
            'physics': {
                'photon_energy': {'value': None, 'calculated': True},  # E = h * f
                'power': {'value': None, 'calculated': True}
            },
            'self_learning': {
                'learning_enabled': True
            }
        }
    
    def get_effect(self, effect_id: str) -> Optional[Dict[str, Any]]:
        """Get effect by ID"""
        if effect_id in self.effects:
            return self.effects[effect_id]
        if effect_id in self.scanner_types:
            return self.scanner_types[effect_id]
        if effect_id in self.lightshow_types:
            return self.lightshow_types[effect_id]
        return None
    
    def get_all_scanner_types(self) -> Dict[str, Dict]:
        """Get all scanner types"""
        return self.scanner_types
    
    def get_all_lightshow_types(self) -> Dict[str, Dict]:
        """Get all lightshow types"""
        return self.lightshow_types
    
    def calculate_physics_properties(self, effect_id: str, effect_config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate physics properties using scientific equations"""
        effect = self.get_effect(effect_id)
        if not effect:
            return {}
        
        calculated = {}
        
        # Calculate frequency-dependent properties
        if 'frequency' in effect_config:
            freq = effect_config['frequency']
            
            # Calculate period
            if freq > 0:
                calculated['period'] = 1 / freq
                
                # For optical effects, calculate wavelength
                if effect_config.get('type') in ['laser', 'led', 'emission']:
                    c = 299792458  # Speed of light in m/s
                    # Convert to appropriate units based on frequency range
                    if freq < 1e15:  # Optical range
                        wavelength_nm = (c / freq) * 1e9
                        calculated['wavelength_nm'] = wavelength_nm
                        
                        # Calculate photon energy
                        h = 6.626e-34  # Planck constant
                        photon_energy_j = h * freq
                        calculated['photon_energy_j'] = photon_energy_j
                        calculated['photon_energy_ev'] = photon_energy_j / 1.602e-19  # Convert to eV
        
        # Calculate wave properties
        if 'wavelength' in effect_config and 'wave_frequency' in effect_config:
            wavelength = effect_config['wavelength']
            wave_freq = effect_config['wave_frequency']
            calculated['wave_velocity'] = wavelength * wave_freq
            calculated['angular_frequency'] = 2 * math.pi * wave_freq
            calculated['wave_number'] = 2 * math.pi / wavelength
            # Wave energy is proportional to amplitude squared
            if 'amplitude' in effect_config:
                calculated['wave_energy'] = effect_config['amplitude'] ** 2
        
        # Calculate bubble physics
        if effect_id == 'soap_bubble_machine' and 'bubble_size' in effect_config:
            bubble_radius = effect_config['bubble_size'] / 2
            
            # Surface area
            calculated['surface_area'] = 4 * math.pi * (bubble_radius ** 2)
            
            # Volume
            calculated['volume'] = (4 / 3) * math.pi * (bubble_radius ** 3)
            
            # Mass (assuming density)
            density = effect_config.get('density', 0.001)
            calculated['mass'] = density * calculated['volume']
            
            # Terminal velocity (Stokes' law approximation)
            g = 9.81
            viscosity = effect_config.get('viscosity', 1.81e-5)
            density_air = effect_config.get('density_air', 1.225)
            rho_diff = density_air - density
            if viscosity > 0 and rho_diff > 0:
                # Convert to SI units (assuming px to m conversion of 1px = 0.001m)
                r_m = bubble_radius * 0.001
                calculated['terminal_velocity'] = (2 * g * (r_m ** 2) * rho_diff) / (9 * viscosity)
                
                # Reynolds number
                if calculated['terminal_velocity']:
                    calculated['reynolds_number'] = (2 * density_air * calculated['terminal_velocity'] * r_m) / viscosity
                    calculated['stokes_law_applicable'] = calculated['reynolds_number'] < 1
        
        return calculated
    
    def apply_self_learning(self, effect_id: str, effect_config: Dict[str, Any], performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply self-learning optimization to effect"""
        effect = self.get_effect(effect_id)
        if not effect or not effect.get('self_learning', {}).get('learning_enabled'):
            return effect_config
        
        # Get reasoning from self-learning reasoner
        reasoning = reasoner.reason_about_effect(effect_config)
        
        # Optimize parameters based on learned patterns
        optimized_params = reasoner.optimize_effect_parameters(effect_id, performance_data)
        
        # Merge optimizations
        optimized_config = {**effect_config}
        optimized_config.update(optimized_params)
        
        # Apply recommendations
        for recommendation in reasoning.get('recommendations', []):
            # Parse and apply recommendation
            pass
        
        return optimized_config


# Initialize global effects database
effects_db = EffectDatabase()


def get_effects_database() -> EffectDatabase:
    """Get the global effects database instance"""
    return effects_db

