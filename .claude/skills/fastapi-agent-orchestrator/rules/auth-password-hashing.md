---
title: Argon2id via pwdlib — Never Roll Your Own
impact: CRITICAL
impactDescription: Password hashing is a solved problem; rolling your own (or picking a weak algo) is the #1 way to fail security review
tags: auth, password-hashing, argon2
---

## Argon2id via pwdlib — Never Roll Your Own

Use `pwdlib[argon2]`. Default parameters are fine for this assignment.

### Setup

```toml
# pyproject.toml
dependencies = [
  "pwdlib[argon2]",
  # ...
]
```

```python
# app/core/security.py
from pwdlib import PasswordHash

password_hash = PasswordHash.recommended()   # argon2id with safe defaults


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return password_hash.verify(password, hashed)
```

### Bad — SHA-anything, MD5, plain bcrypt with low cost

```python
# ❌ Fast hash = brute-forceable
import hashlib
hashed = hashlib.sha256(password.encode()).hexdigest()
```

```python
# ❌ Custom salting scheme
hashed = hashlib.sha256((password + "myappsalt").encode()).hexdigest()
```

### Bad — comparing hashes with `==`

```python
# ❌ Timing-vulnerable; pwdlib's verify is constant-time
if user.hashed_password == hash_password(password):
    ...
```

### Bad — verifying then re-hashing on every login

```python
# ❌ Re-hashing every login wastes CPU
if verify_password(payload.password, user.hashed_password):
    user.hashed_password = hash_password(payload.password)   # pointless
```

### Good — rehash on demand only

If you ever change Argon2 parameters, pwdlib gives you `needs_update`:

```python
if verify_password(payload.password, user.hashed_password):
    if password_hash.needs_update(user.hashed_password):
        user.hashed_password = hash_password(payload.password)
        await self.users.save(user)
```

### Alternative

If `pwdlib` isn't available, fall back to `passlib[bcrypt]` with cost ≥ 12. Don't invent a third option.

```python
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
```

### Rules

- Hash on registration + password change. Never log or store the raw password.
- Verify on login + sensitive action (e.g., delete account).
- One hashing module: `app/core/security.py`. Do not re-import a hasher anywhere else.
- Never email a password back to a user. Reset flows generate a one-time token.

See: [[auth-jwt-and-refresh]], [[auth-current-user-dep]]
