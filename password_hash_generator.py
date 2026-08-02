"""Script to generate a bcrypt password hash for the shared seed password.

This mirrors the pattern used in generate_data.py, but lets you quickly
check what a password hashes to, and confirm the hash verifies correctly,
without touching the database. Not required to run the seed script (which
hashes the password itself) - this is just a handy standalone check.

Usage:
    python password_hash_generator.py
"""
from flask import Flask
from flask_bcrypt import Bcrypt

app = Flask(__name__)
flask_bcrypt = Bcrypt(app)

PASSWORD = 'Sunnypreschool123'

password_hash = flask_bcrypt.generate_password_hash(PASSWORD).decode('utf-8')
matches = flask_bcrypt.check_password_hash(password_hash, PASSWORD)

print(f'Password : {PASSWORD}')
print(f'Hash     : {password_hash}')
print(f'Verifies : {matches}')
