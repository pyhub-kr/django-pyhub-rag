import zoneinfo

from django.conf import settings
from django.utils import timezone

# https://docs.djangoproject.com/en/dev/topics/i18n/timezones/#selecting-the-current-time-zone


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = request.session.get("django_timezone")
        if not tzname:
            if hasattr(settings, "USER_DEFAULT_TIME_ZONE"):
                tzname = settings.USER_DEFAULT_TIME_ZONE

        if tzname:
            timezone.activate(zoneinfo.ZoneInfo(tzname))
        else:
            timezone.deactivate()

        return self.get_response(request)
