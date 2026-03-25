#!/usr/bin/env python3
"""
WanderAI — AI Travel Planner
Run: python run.py
Then: cd client && pnpm install && pnpm dev   (opens http://localhost:5173)
Or build: cd client && pnpm build            (serves from http://localhost:8000)
"""
import uvicorn

if __name__ == "__main__":
    print("\n🧭  WanderAI — AI Travel Planner")
    print("    API  → http://localhost:8000/docs")
    print("\n    Prerequisites:")
    print("    $ ollama serve")
    print("    $ ollama pull llama3")
    print("\n    Frontend (separate terminal):")
    print("    $ cd client && pnpm install && pnpm dev\n")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
