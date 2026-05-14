from uuid import UUID

from apps.follows.models import Follow
from apps.projects.models import Project
from services.follows.query_interface import FollowQueryInterface, FollowState


class DjangoFollowQuery(FollowQueryInterface):
    def is_followed(self, user_id: UUID | None, project: Project) -> bool:
        if user_id is None:
            return False
        return Follow.objects.filter(user_id=user_id, project=project).exists()

    def get_state(self, user_id: UUID | None, project: Project) -> FollowState:
        if user_id is None:
            return FollowState(is_followed=False)
        follow = Follow.objects.filter(user_id=user_id, project=project).first()
        if follow is None:
            return FollowState(is_followed=False)
        return FollowState(is_followed=True, created_at=follow.created_at)
