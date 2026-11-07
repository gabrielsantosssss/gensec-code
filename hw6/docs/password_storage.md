# Password Storage

Passwords must never be stored in plaintext or with reversible encryption.
Instead, store a salted hash produced by a slow, memory-hard, adaptive
hashing algorithm designed specifically for passwords.

Recommended algorithms, in order of preference: Argon2id, scrypt, bcrypt,
and PBKDF2 (only when FIPS compliance is required).

Each password must use a unique, randomly generated salt stored alongside
the hash. Never reuse a salt across users or accounts.

Work factors (iteration counts, memory cost) should be tuned so hashing
takes a noticeable but acceptable amount of time on your hardware, and
increased over time as hardware gets faster.

Never roll your own hashing scheme. Use a well-reviewed library
(e.g. argon2-cffi, bcrypt) rather than implementing the algorithm yourself.
