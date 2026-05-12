# VoxCraft Pro

VoxCraft Pro is a professional-grade AI voice-over production suite built with Streamlit. It offers a comprehensive set of features for creating high-quality voice-overs with ease.

## Key Features

*   SSML & Precision: Support for pronunciation dictionaries and character-based voice assignments.
*   *   Audio Production: Integrated Background Music Mixer with 6 cinematic styles and Audio Normalization.
    *   *   Video Workflow: Timeline Sync feature to match speech rate with video duration.
        *   *   Voice Studio: Side-by-side comparison of 3 different voices.
            *   *   Global Reach: Over 60 neural voices across 15+ languages.
                *   *   High Performance: Parallel audio generation and instant stitching.
                 
                    *   ## Getting Started
                 
                    *   ### Prerequisites
                  clone https://github.com/mortalman-driod/voxcraft-pro.git
                    cd voxcraft-pro
                    ```
         
                2.  Install dependencies:
                3.      ```bash
                4.      pip install -r requirements.txt
                5.      ```
             
                6.  3.  Run the app:
                    4.      ```bash
                    5.      streamlit run voiceover_agent.py
                    6.      ```
                  
                    7.  ## Tech Stack
                  
                    8.  *   Frontend: Streamlit
                        *   *   Audio Engine: FFmpeg, pydub
                            *   *   Neural TTS: Edge TTS / Azure (via various libraries)
                                *   *   Parallelism: asyncio
                                 
                                    *   ## License
                                 
                                    *   MIT License
                                    *   
                    *   *   Python 3.8+
                        *   *   FFmpeg (required for audio processing)
                         
                            *   ### Installation
                         
                            *   1.  Clone the repository:
                                2.      ```bash
                                3.      git
