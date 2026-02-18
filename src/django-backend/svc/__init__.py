from dataclasses import dataclass, field

from svc.email.django_impl import DjangoEmailHandler, DjangoEmailQuery
from svc.email.handler_interface import EmailHandlerInterface
from svc.email.query_interface import EmailQueryInterface
from svc.project.django_impl import DjangoProjectHandler, DjangoProjectQuery
from svc.project.handler_interface import ProjectHandlerInterface
from svc.project.query_interface import ProjectQueryInterface


@dataclass(frozen=True)
class HandlerServices:
    email: EmailHandlerInterface = field(default_factory=DjangoEmailHandler)
    project: ProjectHandlerInterface = field(default_factory=DjangoProjectHandler)


@dataclass(frozen=True)
class QueryServices:
    email: EmailQueryInterface = field(default_factory=DjangoEmailQuery)
    project: ProjectQueryInterface = field(default_factory=DjangoProjectQuery)


HANDLERS = HandlerServices()
REPO = QueryServices()
