## 1. Competitions Service

- [x] 1.1 Create `services/competitions/` directory with `__init__.py`, `exceptions.py` (add `CompetitionNotFoundError`)
- [x] 1.2 Create `services/competitions/query_interface.py` with `CompetitionQueryInterface` ABC defining: `list_all()`, `list_with_projects()`, `get_by_id_or_slug()`, `list_highlights()`, `count_pending_projects()`
- [x] 1.3 Create `services/competitions/django_impl/__init__.py` and `query.py` with `DjangoCompetitionQuery` implementing all `CompetitionQueryInterface` methods using Django ORM
- [x] 1.4 Register `competitions` in `services/__init__.py` `QueryServices` as `REPO.competitions`
- [x] 1.5 Refactor `api/routers/competitions.py` to use `REPO.competitions` instead of direct ORM queries, removing all `apps.projects.models` imports
- [x] 1.6 Refactor `api/schemas/competition.py` to remove direct ORM queries from `from_competition()` methods — accept pre-computed data; remove import of `to_list_item` from `services.project.django_impl`
- [x] 1.7 Write tests for `DjangoCompetitionQuery`

## 2. Tags Service

- [x] 2.1 Create `services/tags/` directory with `__init__.py`, `exceptions.py` (add `TagNotFoundError`, `DuplicateTagNameError`, `DuplicateTagSlugError`, `TagCategoryNotFoundError`, `TagAlreadyApprovedError`, `TagRejectedError`, `TagAlreadyRejectedError`)
- [x] 2.2 Create `services/tags/query_interface.py` with `TagQueryInterface` ABC defining: `list_non_rejected()`, `list_categories()`, `list_grouped()`, `list_pending()`, `get_by_id()`
- [x] 2.3 Create `services/tags/handler_interface.py` with `TagHandlerInterface` ABC defining: `suggest()`, `approve()`, `reject()`
- [x] 2.4 Create `services/tags/django_impl/__init__.py`, `query.py` with `DjangoTagQuery`, and `handler.py` with `DjangoTagHandler`
- [x] 2.5 Register `tags` in `services/__init__.py` as `REPO.tags` and `HANDLERS.tags`
- [x] 2.6 Refactor `api/routers/tags.py` to use `REPO.tags` and `HANDLERS.tags` instead of direct ORM queries, removing all `apps.tags.models` and `apps.projects.models` imports
- [x] 2.7 Write tests for `DjangoTagQuery` and `DjangoTagHandler`

## 3. Project Images Service

- [x] 3.1 Create `services/project_images/` directory with `__init__.py`, `exceptions.py` (add `ProjectImageNotFoundError`, `ImageLimitExceededError`, `UploadNotFoundError`)
- [x] 3.2 Create `services/project_images/query_interface.py` with `ProjectImageQueryInterface` ABC defining: `get_project_for_owner()`, `get_image_for_project()`, `count_uploaded_non_icon_images()`, `has_main_image()`
- [x] 3.3 Create `services/project_images/handler_interface.py` with `ProjectImageHandlerInterface` ABC defining: `create_image()`, `complete_upload()`, `update_roles()`, `delete_image()`
- [x] 3.4 Create `services/project_images/django_impl/__init__.py`, `query.py` with `DjangoProjectImageQuery`, and `handler.py` with `DjangoProjectImageHandler`
- [x] 3.5 Register `project_images` in `services/__init__.py` as `REPO.project_images` and `HANDLERS.project_images`
- [x] 3.6 Refactor image endpoints in `api/routers/my_projects.py` to use `REPO.project_images` and `HANDLERS.project_images`, removing direct `ProjectImage.objects.create()`, `.save()`, `.delete()`, and `get_object_or_404` calls
- [x] 3.7 Write tests for `DjangoProjectImageQuery` and `DjangoProjectImageHandler`

## 4. Review Service

- [ ] 4.1 Create `services/review/` directory with `__init__.py`, `exceptions.py` (add `ReviewNotFoundError`, `ReviewAlreadyCompletedError`, `InvalidProjectIdsError`)
- [ ] 4.2 Create `services/review/query_interface.py` with `ReviewQueryInterface` ABC defining: `list_reviewer_assignments()`, `get_reviewer_assignment()`, `get_competition_with_projects()`, `get_reviewer_rankings()`, `get_competition_project_ids()`, `get_review_project()`
- [ ] 4.3 Create `services/review/handler_interface.py` with `ReviewHandlerInterface` ABC defining: `update_rankings()`, `update_review_status()`
- [ ] 4.4 Create `services/review/django_impl/__init__.py`, `query.py` with `DjangoReviewQuery`, and `handler.py` with `DjangoReviewHandler`
- [ ] 4.5 Register `review` in `services/__init__.py` as `REPO.review` and `HANDLERS.review`
- [ ] 4.6 Refactor `api/routers/my_review.py` to use `REPO.review` and `HANDLERS.review`, removing all `apps.projects.models` imports
- [ ] 4.7 Write tests for `DjangoReviewQuery` and `DjangoReviewHandler`

## 5. Fix Existing Violations

- [ ] 5.1 Refactor `api/tasks/email.py` to use `REPO.users.get_active_by_id()`, `REPO.project.get_by_id()`, and `REPO.email.get_broadcast_by_id()` instead of direct `Model.objects.get()` calls; add `get_broadcast_by_id()` to `EmailQueryInterface` and `DjangoEmailQuery` if needed
- [ ] 5.2 Add `update_profile()` method to `UserHandlerInterface` and `DjangoUserHandler` that accepts field updates; refactor `api/routers/auth.py:update_current_user()` to delegate to `HANDLERS.users.update_profile()`
- [ ] 5.3 Refactor `api/schemas/project.py` resolve methods to receive pre-fetched data from the router instead of traversing ORM relations; remove `.all()`, `.exclude()`, `.filter()` calls from resolve methods
- [ ] 5.4 Refactor `api/schemas/my_review.py` resolve methods to receive pre-fetched data instead of querying ORM relations directly
- [ ] 5.5 Remove `ProjectStatus` direct import from `api/routers/projects.py` and use the value from service layer response or schema enum instead

## 6. Documentation

- [ ] 6.1 Create `src/django-backend/ARCHITECTURE.md` documenting the service-layer rule, the interface pattern (ABC → django_impl → HANDLERS/REPO), list of all service domains, and examples of correct vs incorrect usage
- [ ] 6.2 Update `CLAUDE.md` to reference `ARCHITECTURE.md` for the service-layer convention