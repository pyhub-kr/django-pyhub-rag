from datetime import datetime

from ninja import Schema


class NaverMapRouterLocation(Schema):
    location: list[float]


class NaverMapRouterSummary(Schema):
    start: NaverMapRouterLocation
    goal: NaverMapRouterLocation
    distance: int
    duration: int
    departureTime: datetime
    bbox: list[list[float]]
    tollFare: int
    taxiFare: int
    fuelPrice: int


class NaverMapRouterSection(Schema):
    pointIndex: int
    pointCount: int
    distance: int
    name: str
    congestion: int
    speed: int


class NaverMapRouterGuide(Schema):
    pointIndex: int
    type: int
    instructions: str
    distance: int
    duration: int


class NaverMapRouterTrafast(Schema):
    summary: NaverMapRouterSummary
    path: list[list[float]]
    section: list[NaverMapRouterSection]
    guide: list[NaverMapRouterGuide]


class NaverMapRouterRoute(Schema):
    trafast: list[NaverMapRouterTrafast]


class NaverMapRouterResponse(Schema):
    code: int
    message: str
    currentDateTime: datetime
    route: NaverMapRouterRoute
