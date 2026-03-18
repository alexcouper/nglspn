## 1. Fix discussion notification bug

- [x] 1.1 Add `is_active=True` filter to recipient collection in `create_notifications_for_discussion()` in `services/notifications/django_impl/handler.py`
- [x] 1.2 Add `is_active=True` filter to user queryset in `send_batch_notifications()` in `services/notifications/django_impl/handler.py`

## 2. Auth exclusion tests

- [x] 2.1 Create `test_inactive_user_auth.py` with test for inactive user login returning 401
- [x] 2.2 Add test for inactive user token refresh returning 401
- [x] 2.3 Add test for JWT access token validation rejecting inactive user

## 3. Broadcast email exclusion tests

- [x] 3.1 Create `test_inactive_user_emails.py` with test for platform update broadcast excluding inactive users
- [x] 3.2 Add test for competition results broadcast excluding inactive users
- [x] 3.3 Add test for individual recipient broadcast excluding inactive users

## 4. Discussion notification exclusion tests

- [x] 4.1 Add test for discussion reply not notifying inactive project owner
- [x] 4.2 Add test for discussion reply not notifying inactive thread participant
- [x] 4.3 Add test for batch notification digest skipping inactive users

## 5. Verify

- [x] 5.1 Run full test suite and confirm all tests pass
- [x] 5.2 Run linter and fix any issues
