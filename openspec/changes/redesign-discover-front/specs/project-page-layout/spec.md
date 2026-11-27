## REMOVED Requirements

### Requirement: is_featured boolean on Project
**Reason**: The Featured section is replaced by article-driven Recent and spotlight sections; nothing reads the flag.
**Migration**: The column is dropped in the second PR. Admins use `Article.is_spotlight` instead.
