# Requirements

*   Python 3.7 or higher
*   pip install -q -U google-generativeai
*   pip install PyMuPDF

# Configuration (config.json):

*   Obtain a Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).  You may need to enable the Gemini API.
*   Create a file named `config.json` in the same directory as your script.  Use the following template, *replacing `YOUR_API_KEY_HERE` with your actual Gemini API key*:

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

# License

This project is licensed under the Apache License 2.0.
