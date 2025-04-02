import zoneinfo

from asgiref.sync import iscoroutinefunction, markcoroutinefunction
from django.conf import settings
from django.utils import timezone

# https://docs.djangoproject.com/en/dev/topics/i18n/timezones/#selecting-the-current-time-zone


class TimezoneMiddleware:
    sync_capable = True
    async_capable = True

    def __init__(self, get_response):
        if get_response is None:
            raise ValueError("get_response must be provided.")
        self.get_response = get_response
        self.is_async = iscoroutinefunction(get_response)
        if self.is_async:
            markcoroutinefunction(self)
        super().__init__()

    def __call__(self, request):
        if self.is_async:
            return self.__acall__(request)

        self._process_request(request)
        return self.get_response(request)

    async def __acall__(self, request):
        self._process_request(request)
        return await self.get_response(request)

    def _process_request(self, request):
        """Shared synchronous logic to process the request."""
        tzname = request.session.get("django_timezone")
        if not tzname:
            if hasattr(settings, "USER_DEFAULT_TIME_ZONE"):
                tzname = settings.USER_DEFAULT_TIME_ZONE

        if tzname:
            try:
                timezone.activate(zoneinfo.ZoneInfo(tzname))
            except zoneinfo.ZoneInfoNotFoundError:
                timezone.deactivate()
        else:
            # If no timezone is found in session or default setting, deactivate
            # to use the default (settings.TIME_ZONE)
            timezone.deactivate()