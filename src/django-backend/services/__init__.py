from dataclasses import dataclass, field

from services.articles.django_impl import (
    DjangoArticleHandler,
    DjangoArticleQuery,
)
from services.articles.handler_interface import ArticleHandlerInterface
from services.articles.query_interface import ArticleQueryInterface
from services.discussions.django_impl import (
    DjangoDiscussionHandler,
    DjangoDiscussionQuery,
)
from services.discussions.handler_interface import DiscussionHandlerInterface
from services.discussions.query_interface import DiscussionQueryInterface
from services.email.django_impl import DjangoEmailHandler, DjangoEmailQuery
from services.email.handler_interface import EmailHandlerInterface
from services.email.query_interface import EmailQueryInterface
from services.follows.django_impl import DjangoFollowHandler, DjangoFollowQuery
from services.follows.handler_interface import FollowHandlerInterface
from services.follows.query_interface import FollowQueryInterface
from services.images.django_impl import DjangoImageHandler
from services.images.handler_interface import ImageHandlerInterface
from services.notifications.django_impl import (
    DjangoNotificationHandler,
    DjangoNotificationQuery,
)
from services.notifications.handler_interface import NotificationHandlerInterface
from services.notifications.query_interface import NotificationQueryInterface
from services.project.django_impl import DjangoProjectHandler, DjangoProjectQuery
from services.project.handler_interface import ProjectHandlerInterface
from services.project.query_interface import ProjectQueryInterface
from services.registration.django_impl import DjangoRegistrationHandler
from services.registration.handler_interface import RegistrationHandlerInterface
from services.review.django_impl import DjangoReviewHandler, DjangoReviewQuery
from services.review.handler_interface import ReviewHandlerInterface
from services.review.query_interface import ReviewQueryInterface
from services.users.django_impl import DjangoUserHandler, DjangoUserQuery
from services.users.handler_interface import UserHandlerInterface
from services.users.query_interface import UserQueryInterface


@dataclass(frozen=True)
class HandlerServices:
    articles: ArticleHandlerInterface = field(default_factory=DjangoArticleHandler)
    discussions: DiscussionHandlerInterface = field(
        default_factory=DjangoDiscussionHandler
    )
    email: EmailHandlerInterface = field(default_factory=DjangoEmailHandler)
    follows: FollowHandlerInterface = field(default_factory=DjangoFollowHandler)
    images: ImageHandlerInterface = field(default_factory=DjangoImageHandler)
    notifications: NotificationHandlerInterface = field(
        default_factory=DjangoNotificationHandler
    )
    project: ProjectHandlerInterface = field(default_factory=DjangoProjectHandler)
    registration: RegistrationHandlerInterface = field(
        default_factory=DjangoRegistrationHandler
    )
    reviews: ReviewHandlerInterface = field(default_factory=DjangoReviewHandler)
    users: UserHandlerInterface = field(default_factory=DjangoUserHandler)


@dataclass(frozen=True)
class QueryServices:
    articles: ArticleQueryInterface = field(default_factory=DjangoArticleQuery)
    discussions: DiscussionQueryInterface = field(default_factory=DjangoDiscussionQuery)
    email: EmailQueryInterface = field(default_factory=DjangoEmailQuery)
    follows: FollowQueryInterface = field(default_factory=DjangoFollowQuery)
    notifications: NotificationQueryInterface = field(
        default_factory=DjangoNotificationQuery
    )
    project: ProjectQueryInterface = field(default_factory=DjangoProjectQuery)
    reviews: ReviewQueryInterface = field(default_factory=DjangoReviewQuery)
    users: UserQueryInterface = field(default_factory=DjangoUserQuery)


HANDLERS = HandlerServices()
REPO = QueryServices()
