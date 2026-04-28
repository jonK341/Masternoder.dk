/**
 * Three.js Visualizations - 3D graphics for game
 */
class ThreeJSVisualizations {
    constructor() {
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.initialized = false;
    }

    init(containerId) {
        if (this.initialized) {
            return;
        }

        try {
            if (typeof THREE === 'undefined') {
                console.warn('[ThreeJS] Three.js not loaded');
                return;
            }

            const container = document.getElementById(containerId);
            if (!container) {
                console.warn(`[ThreeJS] Container ${containerId} not found`);
                return;
            }

            // Scene
            this.scene = new THREE.Scene();
            this.scene.background = new THREE.Color(0x0a0a0a);

            // Camera
            this.camera = new THREE.PerspectiveCamera(
                75,
                container.clientWidth / container.clientHeight,
                0.1,
                1000
            );
            this.camera.position.z = 5;

            // Renderer
            this.renderer = new THREE.WebGLRenderer({ antialias: true });
            this.renderer.setSize(container.clientWidth, container.clientHeight);
            this.renderer.setPixelRatio(window.devicePixelRatio);
            container.appendChild(this.renderer.domElement);

            // Lighting
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
            this.scene.add(ambientLight);

            const pointLight = new THREE.PointLight(0x00ff88, 1);
            pointLight.position.set(5, 5, 5);
            this.scene.add(pointLight);

            this.initialized = true;
            this.animate();
        } catch (error) {
            console.error('[ThreeJS] Initialization error:', error);
        }
    }

    createPointsVisualization(pointsData) {
        if (!this.initialized || !this.scene) {
            return;
        }

        // Clear existing points
        const pointsToRemove = [];
        this.scene.children.forEach(child => {
            if (child.userData.isPoint) {
                pointsToRemove.push(child);
            }
        });
        pointsToRemove.forEach(obj => this.scene.remove(obj));

        // Create point spheres
        const pointTypes = Object.keys(pointsData).filter(key => 
            typeof pointsData[key] === 'number' && pointsData[key] > 0
        );

        pointTypes.forEach((type, index) => {
            const value = pointsData[type];
            const geometry = new THREE.SphereGeometry(0.1 + (value / 10000), 16, 16);
            const material = new THREE.MeshPhongMaterial({
                color: this.getColorForPointType(type),
                emissive: this.getColorForPointType(type),
                emissiveIntensity: 0.5
            });

            const sphere = new THREE.Mesh(geometry, material);
            const angle = (index / pointTypes.length) * Math.PI * 2;
            sphere.position.x = Math.cos(angle) * 2;
            sphere.position.y = Math.sin(angle) * 2;
            sphere.userData.isPoint = true;
            sphere.userData.pointType = type;
            sphere.userData.value = value;

            this.scene.add(sphere);
        });
    }

    getColorForPointType(type) {
        const colors = {
            'xp_total': 0x00ff88,
            'quest_points': 0x00d4ff,
            'battle_points': 0xff4444,
            'activity_points': 0x44ff44,
            'generation_points': 0x00ffff,
            'reward_points': 0xffaa00,
            'trophy_points': 0xffd700,
        };
        return colors[type] || 0x888888;
    }

    animate() {
        if (!this.initialized) {
            return;
        }

        requestAnimationFrame(() => this.animate());

        if (this.scene && this.camera && this.renderer) {
            // Rotate points
            this.scene.children.forEach(child => {
                if (child.userData.isPoint) {
                    child.rotation.x += 0.01;
                    child.rotation.y += 0.01;
                }
            });

            this.renderer.render(this.scene, this.camera);
        }
    }

    resize(width, height) {
        if (this.camera && this.renderer) {
            this.camera.aspect = width / height;
            this.camera.updateProjectionMatrix();
            this.renderer.setSize(width, height);
        }
    }
}

// Global instance
const threeJSViz = new ThreeJSVisualizations();

