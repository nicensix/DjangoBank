from django.shortcuts import render
from django.views.generic import TemplateView


class HomeView(TemplateView):
    """
    Home page view displaying the main landing page.
    """
    template_name = 'core/home.html'
