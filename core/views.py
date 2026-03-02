from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.views import View
from django.contrib.auth import login
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.db import connection

from .models import Project, Task
from .forms import ProjectForm, TaskForm, RegisterForm


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

def health_check(request):
    """Returns application and database health status."""
    health = {'status': 'healthy', 'checks': {}}
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        health['checks']['database'] = 'ok'
    except Exception as exc:
        health['status'] = 'unhealthy'
        health['checks']['database'] = str(exc)
    status_code = 200 if health['status'] == 'healthy' else 503
    return JsonResponse(health, status=status_code)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class RegisterView(View):
    template_name = 'registration/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('home')
        return render(request, self.template_name, {'form': RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f'Welcome, {user.username}! Your account was created.')
            return redirect('home')
        return render(request, self.template_name, {'form': form})


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['recent_projects'] = Project.objects.filter(owner=user).prefetch_related('tasks')[:5]
        context['recent_tasks'] = (
            Task.objects.filter(project__owner=user)
            .select_related('project')
            .prefetch_related('tags')[:8]
        )
        context['total_projects'] = Project.objects.filter(owner=user).count()
        context['total_tasks'] = Task.objects.filter(project__owner=user).count()
        context['completed_tasks'] = Task.objects.filter(project__owner=user, status='done').count()
        context['in_progress_tasks'] = Task.objects.filter(project__owner=user, status='in_progress').count()
        return context


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class ProjectListView(LoginRequiredMixin, ListView):
    model = Project
    template_name = 'core/project_list.html'
    context_object_name = 'projects'

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user).prefetch_related('tasks')


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = 'core/project_detail.html'

    def get_queryset(self):
        return Project.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tasks'] = (
            self.object.tasks.all()
            .select_related('assigned_to')
            .prefetch_related('tags')
        )
        context['todo_tasks'] = context['tasks'].filter(status='todo')
        context['in_progress_tasks'] = context['tasks'].filter(status='in_progress')
        context['done_tasks'] = context['tasks'].filter(status='done')
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, 'Project created successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('project-detail', kwargs={'pk': self.object.pk})


class ProjectUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Project
    form_class = ProjectForm
    template_name = 'core/project_form.html'

    def test_func(self):
        return self.get_object().owner == self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Project updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('project-detail', kwargs={'pk': self.object.pk})


class ProjectDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Project
    template_name = 'core/project_confirm_delete.html'
    success_url = reverse_lazy('project-list')

    def test_func(self):
        return self.get_object().owner == self.request.user

    def form_valid(self, form):
        messages.success(self.request, 'Project deleted.')
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class TaskDetailView(LoginRequiredMixin, DetailView):
    model = Task
    template_name = 'core/task_detail.html'

    def get_queryset(self):
        return Task.objects.filter(project__owner=self.request.user).select_related('project', 'assigned_to')


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = 'core/task_form.html'

    def _get_project(self):
        return get_object_or_404(Project, pk=self.kwargs['project_pk'], owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self._get_project()
        return context

    def form_valid(self, form):
        form.instance.project = self._get_project()
        messages.success(self.request, 'Task created successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('project-detail', kwargs={'pk': self.kwargs['project_pk']})


class TaskUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Task
    form_class = TaskForm
    template_name = 'core/task_form.html'

    def test_func(self):
        return self.get_object().project.owner == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = self.get_object().project
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Task updated successfully!')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('task-detail', kwargs={'pk': self.object.pk})


class TaskDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Task
    template_name = 'core/task_confirm_delete.html'

    def test_func(self):
        return self.get_object().project.owner == self.request.user

    def get_success_url(self):
        return reverse_lazy('project-detail', kwargs={'pk': self.object.project.pk})

    def form_valid(self, form):
        messages.success(self.request, 'Task deleted.')
        return super().form_valid(form)
