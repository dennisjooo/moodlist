#!/usr/bin/env python3
"""
Key generation script for MoodList backend.
Generates secure JWT and session secret keys.
"""

import secrets
from pathlib import Path


def generate_keys():
    """Generate secure keys for JWT and session management."""
    jwt_key = secrets.token_urlsafe(64)
    session_key = secrets.token_urlsafe(64)

    print("🔐 Generated secure keys for MoodList backend:")
    print("=" * 50)
    print(f"JWT_SECRET_KEY={jwt_key}")
    print(f"SESSION_SECRET_KEY={session_key}")
    print("=" * 50)
    print("\n✅ Copy these keys to your .env file:")
    print(f"   JWT_SECRET_KEY={jwt_key}")
    print(f"   SESSION_SECRET_KEY={session_key}")
    print(
        "\n⚠️  IMPORTANT: Keep these keys secure and don't commit them to version control!"
    )

    return jwt_key, session_key


def update_env_file(jwt_key: str, session_key: str):
    """Update the .env file with new keys."""
    env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        print(f"❌ .env file not found at {env_path}")
        return False

    try:
        content = env_path.read_text()

        # Update JWT key
        if "JWT_SECRET_KEY=" in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("JWT_SECRET_KEY="):
                    lines[i] = f"JWT_SECRET_KEY={jwt_key}"
                    break
            content = "\n".join(lines)

        # Update session key
        if "SESSION_SECRET_KEY=" in content:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("SESSION_SECRET_KEY="):
                    lines[i] = f"SESSION_SECRET_KEY={session_key}"
                    break
            content = "\n".join(lines)

        env_path.write_text(content)
        print(f"✅ Updated .env file at {env_path}")
        return True

    except Exception as e:
        print(f"❌ Failed to update .env file: {e}")
        return False


if __name__ == "__main__":
    print("🎵 MoodList Backend Key Generator")
    print("Generating secure keys...")

    jwt_key, session_key = generate_keys()

    # Ask if user wants to update .env file
    response = input("\n🔄 Update .env file with these keys? (y/n): ").lower().strip()

    if response in ["y", "yes"]:
        if update_env_file(jwt_key, session_key):
            print("✅ .env file updated successfully!")
        else:
            print("❌ Failed to update .env file")
            print("Please manually update your .env file with the keys above")
    else:
        print("ℹ️  Keys not updated. Please manually add them to your .env file")
