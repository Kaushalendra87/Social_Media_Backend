from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class AuthAndFollowApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='user@example.com',
            username='user',
            password='StrongPass123',
        )
        self.target = User.objects.create_user(
            email='target@example.com',
            username='target',
            password='StrongPass123',
            is_private=True,
        )

    def test_login_and_me_flow(self):
        login_response = self.client.post(
            '/api/users/login/',
            {'email': 'user@example.com', 'password': 'StrongPass123'},
            content_type='application/json',
        )
        self.assertEqual(login_response.status_code, 200, login_response.content)
        data = login_response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertIn('user', data)

        me_response = self.client.get(
            '/api/users/me/',
            HTTP_AUTHORIZATION=f"Bearer {data['access']}",
        )
        self.assertEqual(me_response.status_code, 200, me_response.content)
        self.assertEqual(me_response.json()['email'], 'user@example.com')

    def test_private_follow_request_and_relationship_status(self):
        login_response = self.client.post(
            '/api/users/login/',
            {'email': 'user@example.com', 'password': 'StrongPass123'},
            content_type='application/json',
        )
        token = login_response.json()['access']

        request_response = self.client.post(
            f'/api/users/{self.target.id}/follow-request/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(request_response.status_code, 201, request_response.content)
        self.assertEqual(request_response.json()['status'], 'pending')

        relationship_response = self.client.get(
            f'/api/users/{self.target.id}/relationship/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(relationship_response.status_code, 200, relationship_response.content)
        self.assertEqual(relationship_response.json()['status'], 'pending')

    def test_search_and_follow_request_routes_are_not_shadowed(self):
        response = self.client.get('/api/users/search/?q=user')
        self.assertNotEqual(response.status_code, 404)

        login_response = self.client.post(
            '/api/users/login/',
            {'email': 'user@example.com', 'password': 'StrongPass123'},
            content_type='application/json',
        )
        token = login_response.json()['access']
        follow_requests_response = self.client.get(
            '/api/users/follow-requests/',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertNotEqual(follow_requests_response.status_code, 404)
