"""
Single shared Supabase client for the whole backend.

Uses the SECRET (service_role) key — never the publishable/anon key —
because the backend is the only thing that should be able to read/write
the database and storage bucket. The secret key is never sent to the
frontend; the frontend only ever talks to *our* FastAPI, never to
Supabase directly.
"""

import os
import sys

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
    sys.exit(
        "Missing SUPABASE_URL or SUPABASE_SECRET_KEY.\n"
        "Copy .env.example to .env and fill in your Supabase project "
        "credentials (Project Settings -> API)."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)

EVIDENCE_BUCKET = "evidence"
