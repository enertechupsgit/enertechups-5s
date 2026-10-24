# Testing users

The configured workspace owner (BOOTSTRAP_ADMIN_EMAIL, initially marketing@enertechups.com) can open **People & teams → Isolated testing accounts → Create six test accounts**. The owner must have completed password setup and be signed in. Other roles, including a test Admin, cannot provision this batch.

The batch creates Management (director/read-only oversight), HR (people management and read-only operations), three zone leaders (one synthetic zone and task each), and Admin (administration within the test plant). A separate organization and test plant prevent these users from accessing operational plant records, including through the director's organization-wide read scope.

Each login uses an automatically generated email-format identifier under the reserved testing.enertech.example domain and a distinct random password stored only as a salted scrypt hash. These are login identifiers, not working email mailboxes. Passwords appear once in the creation response, are never committed to Git, and can be downloaded as CSV from that creation screen. Reloading does not reveal passwords again; repeated provisioning returns a conflict instead of resetting accounts.

Accounts expire after seven days. Both new password logins and existing sessions are rejected after expiry. Test records are retained. General enrollment/password recovery/SSO and test-batch reset/revocation interfaces remain follow-up work. Do not use test identities as permanent business accounts.
