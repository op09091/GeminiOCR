# GeminiOCR

GeminiOCR is a user-friendly desktop application for extracting text from images and PDFs using Google's powerful Gemini AI model. It features a simple Tkinter GUI, batch processing capabilities, and customizable settings.

## Requirements

*   Python 3.7 or higher
*   `google-generativeai` Python package
*   `PyMuPDF` (fitz) Python package
*   Tkinter (typically included with Python installations)

## Installation

1.  **Install Dependencies:**

    ```bash
    pip install google-generativeai PyMuPDF
    ```

2.  **Obtain the Code:**

    *   **Option 1 (Git):**
        ```bash
        git clone <your_repository_url>  # Replace with your repository URL
        cd <repository_name>
        ```
    *   **Option 2 (Download):** Download the `GeminiOCR.py` script (or whatever you named it) and the `config.json` file (see below) and place them in the same directory.

3.  **Configuration (config.json):**

    Create a file named `config.json` in the same directory as your script.  Use the following template, *replacing `YOUR_API_KEY_HERE` with your actual Gemini API key*:

    ```json
    {
        "api_key": "YOUR_API_KEY_HERE",
        "model_name": "gemini-1.5-pro",
        "image_extensions": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"],
        "pdf_extension": ".pdf",
        "default_prompt": "Extract the text and return it in Markdown format.",
        "gui": {
            "width": 700,
            "height": 550,
            "padding": 10,
            "bg_color": "#f0f0f0",
            "button_color": "#4a7abc",
            "button_text_color": "white",
            "success_color": "#4CAF50",
            "error_color": "#F44336"
        }
    }
    ```

    *   **Get an API Key:** Obtain a Gemini API key from [Google AI Studio](https://ai.google.dev/).  You may need to create a Google Cloud project and enable the Gemini API.
    *   **Customize:**  Feel free to adjust the other settings in `config.json`, such as the `default_prompt` or GUI appearance.

## License

This project is licensed under the Apache License 2.0.
