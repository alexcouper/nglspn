# morphvox.net

**URL:** https://morphvox.net

## Database Description

MorphVox — real-time voice conversion, TTS, and song voice-swap (RVC as a usable web platform). Features: Real-time voice conversion, Text-to-speech, Song Remix + Voice Swap, Model ownership + access control. Also has Wizart (guided creator flow) in development. GitHub: https://github.com/alli959/rvc_real_time

## Product Overview

MorphVox is a full-stack AI voice conversion platform built on top of RVC (Retrieval-based Voice Conversion) technology. The platform turns what is typically a complex, command-line-driven AI voice workflow into an accessible web application. The tech stack combines a Next.js frontend, a Laravel API backend, and a Python-based RVC voice engine, with MinIO for object storage and Docker Compose for orchestration.

Key capabilities include:

- **Real-time voice conversion** -- transform audio input to sound like a different voice using trained RVC models.
- **Text-to-speech** -- generate speech using Bark (neural TTS) and Edge TTS with support for 50+ voices and emotion control.
- **Song remix and voice swap** -- separate vocals from instrumentals using UVR5 vocal separation, then swap the vocal track with a different RVC voice model.
- **Voice model training** -- users can train custom RVC voice models from their own audio samples directly through the web interface.
- **Model ownership and access control** -- users manage their own voice models with authentication via Google and GitHub OAuth.
- **Admin dashboard** -- a dedicated admin panel at admin.morphvox.net for platform management.

The project is open source and appears aimed at creators, musicians, and hobbyists who want to experiment with AI voice technology without dealing with the underlying Python/ML tooling directly.

## Possible Categories

- **AI & Machine Learning** -- The core product is built entirely on AI voice models (RVC, Bark TTS, UVR5) and includes model training capabilities.
- **Audio & Music Technology** -- Focused on voice conversion, text-to-speech, vocal separation, and song remixing.
- **Creative Tools** -- A platform for creators to generate, transform, and remix voice and audio content, with a guided creator flow (Wizart) in development.
- **Consumer Products** -- Packaged as an end-user web application rather than a developer library or API-only service.
