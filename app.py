


import google.generativeai as genai
import json
import re
import requests
import gradio as gr
import pdfplumber


genai.configure(api_key="AIzaSyDzve_BL2dJ64pd8bE1IUQz-JfIPYWDJcs") 
model = genai.GenerativeModel("gemini-1.5-pro-latest")


context = """
You are a financial assistant specialized in providing product recommendations with a focus on budget management.
You assist users in selecting the best products based on their budgets and needs.
Your task is to recommend products with the best value for the price within the specified budget.
The price should be displayed in INR.
"""


def extract_valid_json(response_text):
    try:
        json_match = re.search(r"{.*}", response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        else:
            print("Error: No valid JSON found in the response.")
            return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing the JSON response: {e}")
        return {}

# Function to extract event details using Gemini
def extract_event_details(text):
    prompt = f"""
    Extract the following event details from the given text:
    - Event name
    - Location
    - Date
    - Time

    Text: "{text}"

    Return the event details as a valid JSON object in this format:
    {{
        "event_name": "<event_name>",
        "location": "<location>",
        "date": "<date>",
        "time": "<time>"
    }}
    Ensure the response is strictly in JSON format without extra commentary.
    """
    response = model.generate_content(prompt)
    raw_response = response.text.strip()
    return extract_valid_json(raw_response)

# Function to extract finance-related suggestions
def extract_finance_suggestions(text, budget):
    print(f"Extract Finance Suggestions - Text: {text}, Budget: {budget}")
    prompt = f"{context}\nPlease retrieve the best products related to '{text}' and provide suggestions for the best products within a budget of {budget}. Include the name of the product and its relevant link. Sample output: [suggestions: Laptop: [name: Zenbook, price: 20k INR], Camera: [name: Nikon D3200, price: 10k INR], etc.] Only give this part and no prefix needed. Display price in INR and remove any extra notes."
    response = model.generate_content(prompt)
    raw_response = response.text.strip()
    return raw_response

# Function to send event details to API
def send_event_to_endpoint(event_details):
    api_endpoint = "https://your-api-endpoint.com/submit_event"
    try:
        response = requests.post(api_endpoint, json=event_details)
        if response.status_code == 200:
            return "Event details successfully sent to the endpoint!"
        else:
            return f"Failed to send event details. Status code: {response.status_code}"
    except requests.RequestException as e:
        return f"Error sending event details: {e}"


# Gradio Interface Functions
def chatbot_response(history, user_input, category, event_details=None, first_prompt=None, user_input_suggestion=None):
    # Initialize pdf_file and budget
    pdf_file = None
    budget = None

    # Check if user_input_suggestion contains the files and budget
    if isinstance(user_input_suggestion, dict):
        pdf_file = user_input_suggestion.get('files', [None])[0]  # Default to None if no files found
        budget = user_input_suggestion.get('text', '')  # Default to empty string if no budget provided

    # Ensure user_input is extracted correctly
    if isinstance(user_input, dict):
        user_input = user_input.get('text', '')  # Fetch the text from the input dictionary

    # Append user input to history
    history.append((user_input, None))

    # Handle Event Logic
    if category == "Event":
        # Combine the existing prompt with the new input
        combined_prompt = (first_prompt or "") + " " + user_input  # Initialize combined_prompt if first_prompt is None
        event_details = extract_event_details(combined_prompt)

        # Check for missing details
        missing_details = [key for key in ["event_name", "location", "date", "time"] if not event_details.get(key)]
        if missing_details:
            history.append((None, f"Missing details: {', '.join(missing_details)}. Please provide them."))
            return history, history, combined_prompt  # Keep updated combined_prompt for the next round

        # Finalize event and reset states
        result = send_event_to_endpoint(event_details)
        history.append((None, f"Event successfully created! {result}"))
        return history, history, None  # Reset first_prompt after event creation

    # Handle other logic (Finance, General Chat, etc.)
    elif category == "Finance":
        # Pass the user input (finance-related query) along with the context for finance
        response = model.generate_content(f"{context}\n{user_input}")
        history.append((None, response.text))  # Append response to history
        return history, history  # Return only two values


    # Handle Suggestion logic (PDF and budget)
    elif category == "Suggesstion":
        if pdf_file and budget:
            items = extract_items_from_pdf(pdf_file)
            suggestions = extract_finance_suggestions(", ".join(items), budget)
            history.append(("Uploaded", suggestions))
        else:
            history.append((None, "Upload a PDF and provide a budget for suggestions."))
        return history, history, None  # Always return two outputs

    # General Chat logic
    else:
        response = model.generate_content(f"Answer the question: {user_input}")
        history.append((None, response.text))
        return history, history, None  # Always return two outputs

def clear_inputs():
       return ""
 
    
    
def clear_inputs1():
    return "",None,""


# Function to extract items from a PDF
def extract_items_from_pdf(pdf_path):
    items = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            items.extend(page.extract_text().split('\n'))
    return items

# CSS to be applied
css = """
.upload-button {
    display: none !important;
}

/* Specific styles to enable file input in the Suggesstion tab */
#suggesstion-tab .upload-button {
    display: flex !important;
}
"""

# Updated Gradio UI
# Gradio App
def create_interface():
    with gr.Blocks(css=css, theme=gr.themes.Ocean()) as demo:
        category = gr.State(value=None)
        first_prompt = gr.State(value=None)
        event_details = gr.State(value={})

        with gr.Column(elem_classes="container1"):
            gr.Markdown("# Welcome to Event Bot")

            with gr.Tabs():
                with gr.Tab("General"):
                    with gr.Column():
                        chatbot_general = gr.Chatbot(value=[(None, "Hello! How can I assist you today?")], bubble_full_width=False)
                        chat_input = gr.MultimodalTextbox(interactive=True, placeholder="Message Eventify", show_label=False)

                        # Submit logic for General Tab
                        chat_input.submit(chatbot_response, inputs=[chatbot_general, chat_input, gr.State(value="General"), gr.State(value=False)], outputs=[chatbot_general, chatbot_general])
                        chat_input.submit(clear_inputs, outputs=[chat_input])

                with gr.Tab("Event"):
                    with gr.Column():
                        chatbot_event = gr.Chatbot(value=[(None, "You selected Event. Please provide event details.")])
                        chat_input_event = gr.MultimodalTextbox(interactive=True, placeholder="Enter an event you want to schedule", show_label=False)

                        # Submit logic for Event Tab
                        chat_input_event.submit(chatbot_response, inputs=[chatbot_event, chat_input_event, gr.State(value="Event"), gr.State(value=False), first_prompt], outputs=[chatbot_event, chatbot_event, first_prompt])
                        chat_input_event.submit(clear_inputs, outputs=[chat_input_event])

                with gr.Tab("Finance"):
                    with gr.Column():
                        chatbot_finance = gr.Chatbot(value=[(None, "You selected Finance. Please ask a finance-related query.")])
                        chat_input_finance = gr.MultimodalTextbox(interactive=True, placeholder="Ask me anything related to finance...", show_label=False)

                        # Submit logic for Finance Tab
                        chat_input_finance.submit(chatbot_response, inputs=[chatbot_finance, chat_input_finance, gr.State(value="Finance")], outputs=[chatbot_finance, chatbot_finance])
                        chat_input_finance.submit(clear_inputs, outputs=[chat_input_finance])

                with gr.Tab("Suggesstion", elem_id="suggesstion-tab"):
                    with gr.Column():
                        chatbot_suggestion = gr.Chatbot(value=[(None, "You selected Suggestion. Please enter a list in PDF and budget.")])
                        chat_input_suggestion = gr.MultimodalTextbox(interactive=True, elem_id="custom-column", file_count="single", placeholder="Enter budget...", show_label=False)

                        # Submit logic for Suggestion Tab
                        chat_input_suggestion.submit(chatbot_response, inputs=[chatbot_suggestion, gr.State(value=None), gr.State(value="Suggesstion"), gr.State(value=None), gr.State(value=None), chat_input_suggestion], outputs=[chatbot_suggestion, chatbot_suggestion])
                        chat_input_suggestion.submit(clear_inputs, outputs=[chat_input_suggestion])

    return demo

if __name__ == "__main__":
    create_interface().launch()
