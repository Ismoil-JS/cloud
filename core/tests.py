from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Project, Task, Tag


class TagModelTest(TestCase):
    def setUp(self):
        self.tag = Tag.objects.create(name='Backend', color='primary')

    def test_tag_str(self):
        self.assertEqual(str(self.tag), 'Backend')

    def test_tag_slug_auto_generated(self):
        self.assertEqual(self.tag.slug, 'backend')


class ProjectModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='testpass123')
        self.project = Project.objects.create(
            title='Test Project',
            description='A test project',
            owner=self.user,
        )

    def test_project_str(self):
        self.assertEqual(str(self.project), 'Test Project')

    def test_project_owner(self):
        self.assertEqual(self.project.owner, self.user)

    def test_project_task_count(self):
        self.assertEqual(self.project.task_count(), 0)


class TaskModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', password='testpass123')
        self.project = Project.objects.create(title='My Project', owner=self.user)
        self.tag = Tag.objects.create(name='Bug', color='danger')
        self.task = Task.objects.create(
            title='Fix login bug',
            description='The login page crashes on bad input.',
            project=self.project,
            status='todo',
            priority='high',
        )
        self.task.tags.add(self.tag)

    def test_task_str(self):
        self.assertEqual(str(self.task), 'Fix login bug')

    def test_task_many_to_many_tags(self):
        self.assertIn(self.tag, self.task.tags.all())

    def test_task_many_to_one_project(self):
        self.assertEqual(self.task.project, self.project)


class HealthCheckViewTest(TestCase):
    def test_health_check_returns_200(self):
        response = self.client.get(reverse('health-check'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')


class AuthViewTest(TestCase):
    def test_register_page_loads(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user_and_redirects(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'StrongPass123!',
            'password2': 'StrongPass123!',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='newuser').exists())

    def test_home_redirects_if_not_authenticated(self):
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response['Location'])


class ProjectViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='tester', password='testpass123')
        self.client.login(username='tester', password='testpass123')
        self.project = Project.objects.create(title='Dashboard Project', owner=self.user)

    def test_project_list_view(self):
        response = self.client.get(reverse('project-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Project')

    def test_project_detail_view(self):
        response = self.client.get(reverse('project-detail', kwargs={'pk': self.project.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard Project')

    def test_project_create_view(self):
        response = self.client.post(reverse('project-create'), {
            'title': 'New Project',
            'description': 'Created in test',
            'is_active': True,
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Project.objects.filter(title='New Project').exists())

    def test_project_update_view(self):
        response = self.client.post(
            reverse('project-update', kwargs={'pk': self.project.pk}),
            {'title': 'Updated Title', 'description': '', 'is_active': True},
        )
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.assertEqual(self.project.title, 'Updated Title')

    def test_project_delete_view(self):
        response = self.client.post(reverse('project-delete', kwargs={'pk': self.project.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())


class TaskViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='tester', password='testpass123')
        self.client.login(username='tester', password='testpass123')
        self.project = Project.objects.create(title='Task Project', owner=self.user)
        self.task = Task.objects.create(
            title='Initial Task',
            project=self.project,
            status='todo',
            priority='medium',
        )

    def test_task_create_view(self):
        response = self.client.post(
            reverse('task-create', kwargs={'project_pk': self.project.pk}),
            {
                'title': 'New Task',
                'description': '',
                'status': 'todo',
                'priority': 'low',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Task.objects.filter(title='New Task').exists())

    def test_task_detail_view(self):
        response = self.client.get(reverse('task-detail', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Initial Task')

    def test_task_delete_view(self):
        response = self.client.post(reverse('task-delete', kwargs={'pk': self.task.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Task.objects.filter(pk=self.task.pk).exists())
