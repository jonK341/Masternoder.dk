"""
Basic API Endpoint Tests
Tests for key API endpoints
"""
import unittest
from src.app import create_app
from src.db.models import db


class APITestCase(unittest.TestCase):
    """Test case for API endpoints"""
    
    def setUp(self):
        """Set up test client"""
        self.app = create_app('testing')
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
    
    def tearDown(self):
        """Clean up after tests"""
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = self.client.get('/api/health')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data.get('status'), 'healthy')
    
    def test_database_health(self):
        """Test database health check"""
        response = self.client.get('/api/health/database')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('database', data)
    
    def test_system_health(self):
        """Test system health check"""
        response = self.client.get('/api/health/system')
        self.assertIn(response.status_code, [200, 503])  # May be degraded
        data = response.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('components', data)
    
    def test_themes_list(self):
        """Test themes list endpoint"""
        response = self.client.get('/api/themes/list')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('themes', data)
        self.assertIsInstance(data.get('themes'), list)
    
    def test_points_comprehensive(self):
        """Test comprehensive points endpoint"""
        response = self.client.get('/api/points/comprehensive?user_id=test_user')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('user_id', data)
    
    def test_stats_summary(self):
        """Test stats summary endpoint"""
        response = self.client.get('/api/stats/summary?user_id=test_user')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))
    
    def test_monitoring_summary(self):
        """Test monitoring summary endpoint"""
        response = self.client.get('/api/monitoring/summary')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get('success'))
        self.assertIn('summary', data)
    
    def test_json_error_handler(self):
        """Test JSON error handler returns JSON"""
        response = self.client.get('/api/nonexistent/endpoint')
        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertIsNotNone(data)
        self.assertFalse(data.get('success'))


if __name__ == '__main__':
    unittest.main()
