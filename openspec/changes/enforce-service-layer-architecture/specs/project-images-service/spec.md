## ADDED Requirements

### Requirement: Project images query interface

The system SHALL provide a `ProjectImageQueryInterface` abstract base class in `services/project_images/query_interface.py` with the following methods:

- `get_project_for_owner(project_id, owner_id)` — return a Project owned by the given user; raise `ProjectImageNotFoundError` with appropriate context if not found
- `get_image_for_project(image_id, project_id, upload_status=None)` — return a ProjectImage matching the given image and project, optionally filtered by upload_status; raise `ProjectImageNotFoundError` if not found
- `count_uploaded_non_icon_images(project)` — return the count of uploaded non-icon images for a project
- `has_main_image(project)` — return whether the project has any image with `is_main=True`

#### Scenario: Get project for owner
- **WHEN** `get_project_for_owner` is called with a valid project_id and matching owner_id
- **THEN** the system SHALL return the Project instance

#### Scenario: Get project for wrong owner
- **WHEN** `get_project_for_owner` is called with a project_id that does not belong to the owner
- **THEN** the system SHALL raise `ProjectImageNotFoundError`

#### Scenario: Get image for project
- **WHEN** `get_image_for_project` is called with a valid image_id and project_id
- **THEN** the system SHALL return the ProjectImage instance

#### Scenario: Get image for project with upload status filter
- **WHEN** `get_image_for_project` is called with `upload_status="pending"`
- **THEN** the system SHALL return the ProjectImage only if its upload_status matches

#### Scenario: Image not found
- **WHEN** `get_image_for_project` is called with a non-existent image_id
- **THEN** the system SHALL raise `ProjectImageNotFoundError`

### Requirement: Project images handler interface

The system SHALL provide a `ProjectImageHandlerInterface` abstract base class in `services/project_images/handler_interface.py` with the following methods:

- `create_image(project_id, owner_id, storage_key, original_filename, content_type, file_size, is_icon)` — create a ProjectImage with PENDING upload status, validating image count limits; raise `ProjectNotFoundError` if project not found; raise `ImageLimitExceededError` if non-icon image count limit reached
- `complete_upload(project_id, owner_id, image_id, width, height)` — mark image as UPLOADED, set uploaded_at, width, height; set is_main=True if this is the first non-icon uploaded image; raise `ProjectImageNotFoundError` if image not found; raise `UploadNotFoundError` if image storage key not found in S3
- `update_roles(project_id, owner_id, image_id, is_main, is_hero, is_usage)` — update role fields on an image; if setting a role to True, clear that role from all other images on the project; raise `ProjectImageNotFoundError` if image not found
- `delete_image(project_id, owner_id, image_id)` — delete an image and its S3 variants; if the deleted image was main, promote the first remaining uploaded image to main; raise `ProjectImageNotFoundError` if image not found

#### Scenario: Create image for project
- **WHEN** `create_image` is called with valid data
- **THEN** the system SHALL create a ProjectImage with PENDING status and return it with its generated ID and display_order

#### Scenario: Create image exceeding limit
- **WHEN** `create_image` is called for a project that already has the maximum number of uploaded non-icon images
- **THEN** the system SHALL raise `ImageLimitExceededError`

#### Scenario: Complete upload marks first non-icon as main
- **WHEN** `complete_upload` is called for a non-icon image and the project has no main image
- **THEN** the system SHALL set `is_main=True` on the uploaded image

#### Scenario: Complete upload does not override existing main
- **WHEN** `complete_upload` is called for a non-icon image and the project already has a main image
- **THEN** the system SHALL NOT change `is_main` on the uploaded image

#### Scenario: Update roles sets exclusive role
- **WHEN** `update_roles` sets `is_main=True` on an image
- **THEN** the system SHALL set `is_main=False` on all other images belonging to the same project

#### Scenario: Delete image promotes next to main
- **WHEN** `delete_image` deletes an image that was `is_main=True` and other uploaded images exist
- **THEN** the system SHALL set `is_main=True` on the first remaining uploaded image

#### Scenario: Delete image removes S3 objects
- **WHEN** `delete_image` is called
- **THEN** the system SHALL delete the image's variants and original from S3, then delete the database record

### Requirement: Django implementation of project images services

The system SHALL provide `DjangoProjectImageQuery` and `DjangoProjectImageHandler` in `services/project_images/django_impl/` implementing `ProjectImageQueryInterface` and `ProjectImageHandlerInterface` respectively. They SHALL be registered in `QueryServices` as `REPO.project_images` and `HandlerServices` as `HANDLERS.project_images`.

#### Scenario: DjangoProjectImageQuery uses Django ORM
- **WHEN** any `ProjectImageQueryInterface` method is called via `REPO.project_images`
- **THEN** the system SHALL use Django ORM queries to fulfill the request

#### Scenario: DjangoProjectImageHandler uses Django ORM
- **WHEN** any `ProjectImageHandlerInterface` method is called via `HANDLERS.project_images`
- **THEN** the system SHALL use Django ORM to create, update, or delete project images

### Requirement: My projects router image endpoints use service layer

The image-related endpoints in `api/routers/my_projects.py` SHALL NOT import from `apps.projects.models` for image operations. All database queries and mutations for images SHALL be delegated to `REPO.project_images` and `HANDLERS.project_images`.

#### Scenario: Upload URL endpoint uses service layer
- **WHEN** the get upload URL endpoint is called
- **THEN** it SHALL call `REPO.project_images.get_project_for_owner()` and `REPO.project_images.count_uploaded_non_icon_images()` for validation, and `HANDLERS.project_images.create_image()` for creation, instead of `get_object_or_404` and `ProjectImage.objects.create()`

#### Scenario: Complete upload endpoint uses service layer
- **WHEN** the complete upload endpoint is called
- **THEN** it SHALL call `HANDLERS.project_images.complete_upload()` instead of directly modifying and saving the image model

#### Scenario: Update image roles endpoint uses service layer
- **WHEN** the update image roles endpoint is called
- **THEN** it SHALL call `HANDLERS.project_images.update_roles()` instead of directly modifying, filtering, updating, and saving the image model

#### Scenario: Delete image endpoint uses service layer
- **WHEN** the delete image endpoint is called
- **THEN** it SHALL call `HANDLERS.project_images.delete_image()` instead of `get_object_or_404`, `.variants.all()`, `.delete()`, and `.save()`