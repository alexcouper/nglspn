from dataclasses import dataclass, field

from services.discussions.django_impl import (
    DjangoDiscussionHandler,
    DjangoDiscussionQuery,
)
from services.discussions.handler_interface import DiscussionHandlerInterface
from services.discussions.query_interface import DiscussionQueryInterface
from services.email.django_impl import DjangoEmailHandler, DjangoEmailQuery
from services.email.handler_interface import EmailHandlerInterface
from services.email.query_interface import EmailQueryInterface
from services.image.django_impl import DjangoImageHandler
from services.image.handler_interface import ImageHandlerInterface
from services.notifications.django_impl import DjangoNotificationHandler
from services.notifications.handler_interface import NotificationHandlerInterface
from services.project.django_impl import DjangoProjectHandler, DjangoProjectQuery
from services.project.handler_interface import ProjectHandlerInterface
from services.project.query_interface import ProjectQueryInterface
from services.users.django_impl import DjangoUserHandler, DjangoUserQuery
from services.users.handler_interface import UserHandlerInterface
from services.users.query_interface import UserQueryInterface
from services.web_ui.django_impl import DjangoWebUIHandler
from services.web_ui.handler_interface import WebUIHandlerInterface


@dataclass(frozen=True)
class HandlerServices:
    discussions: DiscussionHandlerInterface = field(
        default_factory=DjangoDiscussionHandler
    )
    email: EmailHandlerInterface = field(default_factory=DjangoEmailHandler)
    image: ImageHandlerInterface = field(default_factory=DjangoImageHandler)
    notifications: NotificationHandlerInterface = field(
        default_factory=DjangoNotificationHandler
    )
    project: ProjectHandlerInterface = field(default_factory=DjangoProjectHandler)
    users: UserHandlerInterface = field(default_factory=DjangoUserHandler)
    web_ui: WebUIHandlerInterface = field(default_factory=DjangoWebUIHandler)


@dataclass(frozen=True)
class QueryServices:
    discussions: DiscussionQueryInterface = field(default_factory=DjangoDiscussionQuery)
    email: EmailQueryInterface = field(default_factory=DjangoEmailQuery)
    project: ProjectQueryInterface = field(default_factory=DjangoProjectQuery)
    users: UserQueryInterface = field(default_factory=DjangoUserQuery)


HANDLERS = HandlerServices()
REPO = QueryServices()
