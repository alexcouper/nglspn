from dataclasses import dataclass, field

from services.competitions.django_impl import DjangoCompetitionQuery
from services.competitions.query_interface import CompetitionQueryInterface
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
from services.project_images.django_impl import (
    DjangoProjectImageHandler,
    DjangoProjectImageQuery,
)
from services.project_images.handler_interface import ProjectImageHandlerInterface
from services.project_images.query_interface import ProjectImageQueryInterface
from services.registration.django_impl import DjangoRegistrationHandler
from services.registration.handler_interface import RegistrationHandlerInterface
from services.tags.django_impl import DjangoTagHandler, DjangoTagQuery
from services.tags.handler_interface import TagHandlerInterface
from services.tags.query_interface import TagQueryInterface
from services.users.django_impl import DjangoUserHandler, DjangoUserQuery
from services.users.handler_interface import UserHandlerInterface
from services.users.query_interface import UserQueryInterface


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
    project_images: ProjectImageHandlerInterface = field(
        default_factory=DjangoProjectImageHandler
    )
    registration: RegistrationHandlerInterface = field(
        default_factory=DjangoRegistrationHandler
    )
    tags: TagHandlerInterface = field(default_factory=DjangoTagHandler)
    users: UserHandlerInterface = field(default_factory=DjangoUserHandler)


@dataclass(frozen=True)
class QueryServices:
    competitions: CompetitionQueryInterface = field(
        default_factory=DjangoCompetitionQuery
    )
    discussions: DiscussionQueryInterface = field(default_factory=DjangoDiscussionQuery)
    email: EmailQueryInterface = field(default_factory=DjangoEmailQuery)
    project: ProjectQueryInterface = field(default_factory=DjangoProjectQuery)
    project_images: ProjectImageQueryInterface = field(
        default_factory=DjangoProjectImageQuery
    )
    tags: TagQueryInterface = field(default_factory=DjangoTagQuery)
    users: UserQueryInterface = field(default_factory=DjangoUserQuery)


HANDLERS = HandlerServices()
REPO = QueryServices()
