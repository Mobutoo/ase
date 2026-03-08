"""Global template context variables."""
import ase_project


def global_settings(request):
    return {
        'SITE_NAME': 'Asé',
        'SITE_DESCRIPTION': 'Human-centric flow engine',
        'SITE_VERSION': ase_project.__version__,
    }
