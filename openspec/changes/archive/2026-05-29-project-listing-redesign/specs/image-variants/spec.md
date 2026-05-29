## ADDED Requirements

### Requirement: Purpose field on ProjectImage

The `ProjectImage` model SHALL have a `purpose` CharField with choices (`general`, `icon`, `hero_banner`, `in_use`, `winner_composite`) and default `general`. Variant generation SHALL remain unchanged — the purpose field is orthogonal to size variants and does not affect the variant generation pipeline.

#### Scenario: Variant generation unaffected by purpose
- **WHEN** an image with purpose `icon` is uploaded and completed
- **THEN** the same variant generation pipeline runs (thumb, medium, large WebP variants) as for any other image

#### Scenario: API response includes purpose alongside variants
- **WHEN** the API returns a project image with purpose `hero_banner` and variants generated
- **THEN** the response includes the purpose field and the variants array as before
