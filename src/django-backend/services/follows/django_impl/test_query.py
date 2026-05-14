import pytest

from apps.follows.models import Follow
from services.follows.django_impl.query import DjangoFollowQuery
from services.follows.query_interface import FollowState
from tests.factories import ProjectFactory, UserFactory


@pytest.mark.django_db
class TestDjangoFollowQuery:
    def setup_method(self):
        self.query = DjangoFollowQuery()

    def test_anonymous_is_not_followed(self):
        project = ProjectFactory()
        assert self.query.is_followed(None, project) is False
        assert self.query.get_state(None, project) == FollowState(is_followed=False)

    def test_unfollowed_user(self):
        user = UserFactory()
        project = ProjectFactory()
        assert self.query.is_followed(user.id, project) is False

    def test_followed_user(self):
        user = UserFactory()
        project = ProjectFactory()
        follow = Follow.objects.create(user=user, project=project)
        state = self.query.get_state(user.id, project)
        assert state.is_followed is True
        assert state.created_at == follow.created_at
