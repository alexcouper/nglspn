from dataclasses import dataclass, field

from svc.email.django_impl import DjangoEmailHandler, DjangoEmailQuery
from svc.email.handler_interface import EmailHandlerInterface
from svc.email.query_interface import EmailQueryInterface
from svc.project.django_impl import DjangoProjectHandler, DjangoProjectQuery
from svc.project.handler_interface import ProjectHandlerInterface
from svc.project.query_interface import ProjectQueryInterface
from svc.users.django_impl import DjangoUserHandler, DjangoUserQuery
from svc.users.handler_interface import UserHandlerInterface
from svc.users.query_interface import UserQueryInterface


@dataclass(frozen=True)
class HandlerServices:
    email: EmailHandlerInterface = field(default_factory=DjangoEmailHandler)
    project: ProjectHandlerInterface = field(default_factory=DjangoProjectHandler)
    users: UserHandlerInterface = field(default_factory=DjangoUserHandler)


@dataclass(frozen=True)
class QueryServices:
    email: EmailQueryInterface = field(default_factory=DjangoEmailQuery)
    project: ProjectQueryInterface = field(default_factory=DjangoProjectQuery)
    users: UserQueryInterface = field(default_factory=DjangoUserQuery)


HANDLERS = HandlerServices()
REPO = QueryServices()
