from dataclasses import dataclass, field

from svc.project.django_impl import DjangoProjectHandler, DjangoProjectQuery
from svc.project.handler_interface import ProjectHandlerInterface
from svc.project.query_interface import ProjectQueryInterface


@dataclass(frozen=True)
class HandlerServices:
    project: ProjectHandlerInterface = field(default_factory=DjangoProjectHandler)


@dataclass(frozen=True)
class QueryServices:
    project: ProjectQueryInterface = field(default_factory=DjangoProjectQuery)


HANDLERS = HandlerServices()
REPO = QueryServices()
