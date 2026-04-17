class TagNotFoundError(Exception):
    pass


class DuplicateTagNameError(Exception):
    pass


class DuplicateTagSlugError(Exception):
    pass


class TagCategoryNotFoundError(Exception):
    pass


class TagAlreadyApprovedError(Exception):
    pass


class TagRejectedError(Exception):
    pass


class TagAlreadyRejectedError(Exception):
    pass
