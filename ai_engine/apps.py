from django.apps import AppConfig


class AiEngineConfig(AppConfig):
    name = 'ai_engine'
    verbose_name = 'AI Engine'

    def ready(self):
        # Import signals module so @receiver decorators are registered
        # when Django finishes loading all apps.
        import ai_engine.signals  # noqa: F401
