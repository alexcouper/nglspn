# Project Categories

## Purpose

Defines the `ProjectCategory` model, the optional category assignment on projects, admin management, and the API endpoints for listing and assigning categories.

## Requirements

### Requirement: ProjectCategory model

The system SHALL have a `ProjectCategory` model with fields: id (UUID), name (CharField), slug (CharField, unique), display_order (PositiveIntegerField, default 0), and created_at (DateTimeField). Categories SHALL be ordered by `display_order` then `name`.

#### Scenario: Category exists with required fields
- **WHEN** an admin creates a category with name "Dev Tools" and slug "dev-tools"
- **THEN** a `ProjectCategory` row is created with the given name, slug, auto-generated id, display_order 0, and created_at timestamp

#### Scenario: Slug uniqueness enforced
- **WHEN** an admin attempts to create a category with a slug that already exists
- **THEN** the system rejects the creation with a uniqueness error

### Requirement: Project has exactly one optional category

The `Project` model SHALL have a nullable ForeignKey to `ProjectCategory` (on_delete SET_NULL). A project MAY have zero or one category. The field SHALL default to null.

#### Scenario: Project with a category assigned
- **WHEN** a project's category is set to "Dev Tools"
- **THEN** the project's `category` field references that `ProjectCategory` row

#### Scenario: Project with no category
- **WHEN** a project has not been assigned a category
- **THEN** the project's `category` field is null

#### Scenario: Category deleted with assigned projects
- **WHEN** a category is deleted and projects reference it
- **THEN** those projects' `category` field is set to null

### Requirement: Category admin management

The `ProjectCategory` model SHALL be registered in Django admin with list display showing name, slug, display_order, and a count of assigned projects. Admin users SHALL be able to create, edit, and delete categories.

#### Scenario: Admin views category list
- **WHEN** an admin visits the ProjectCategory admin list
- **THEN** they see all categories with name, slug, display_order, and project count

#### Scenario: Admin creates a category
- **WHEN** an admin creates a new category via the admin interface
- **THEN** the category is saved and available for project assignment

### Requirement: Categories API endpoint

The system SHALL expose a `GET /api/projects/categories` endpoint returning all categories ordered by display_order. Each category in the response SHALL include id, name, slug, and project_count (count of approved projects in that category).

#### Scenario: List all categories
- **WHEN** a user requests `GET /api/projects/categories`
- **THEN** the system returns all categories ordered by display_order, each with id, name, slug, and project_count

#### Scenario: Category with no projects
- **WHEN** a category has no approved projects assigned
- **THEN** it is still returned in the list with project_count of 0

### Requirement: Category assignment by project owner

Project owners SHALL be able to assign a category to their project via the project edit API. The category field SHALL accept a category id or null.

#### Scenario: Owner assigns a category
- **WHEN** a project owner updates their project with a valid category id
- **THEN** the project's category is set to the referenced category

#### Scenario: Owner clears category
- **WHEN** a project owner updates their project with category set to null
- **THEN** the project's category is cleared
