class ProjectNotFoundError(Exception):
    pass


class InvalidProjectStateError(Exception):
    pass


class InvalidCompetitionError(Exception):
    pass


class InvalidTagsError(Exception):
    pass


class PublishPreconditionsError(Exception):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"Project not ready to publish; missing: {', '.join(missing)}")
