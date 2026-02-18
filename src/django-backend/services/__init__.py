from dataclasses import dataclass, field

from services.email.django_impl import DjangoEmailHandler, DjangoEmailQuery
from services.email.handler_interface import EmailHandlerInterface
from services.email.query_interface import EmailQueryInterface
from services.project.django_impl import DjangoProjectHandler, DjangoProjectQuery
from services.project.handler_interface import ProjectHandlerInterface
from services.project.query_interface import ProjectQueryInterface
from services.users.django_impl import DjangoUserHandler, DjangoUserQuery
from services.users.handler_interface import UserHandlerInterface
from services.users.query_interface import UserQueryInterface


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
