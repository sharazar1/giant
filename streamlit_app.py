import streamlit as st
import datetime

# --- 1. Define Nested Workflows ---
# Structure: Category -> Note Type -> Details
workflows = {
    "Checks": {
        "Order Check": {
            "template": "We have ordered the {check_name} and are awaiting a response",
            # Define that 'check_name' requires special handling
            "input_config": {
                "check_name": {
                    "widget": "selectbox_conditional", # Custom identifier
                    "options": ["Social Media Check", "Country Specific Check"],
                    "conditional_input": {
                        "trigger_option": "Country Specific Check",
                        "prompt": "Enter Country Name:",
                        "format_string": "{} (Credit/Criminal/Directorship)" # How to format with country name
                    }
                }
                # Add other inputs here if this note needed more, e.g.:
                # "case_id": {"widget": "text_input", "label": "Case ID:"}
            }
        },
        # --- Add other note types for "Checks" ---
        # "Check Results Received": { ... }
    },
    "Referencing": {
        "Email Sent": {
            "template": "We have sent an email to {email_address} provided by the candidate",
            "input_config": {
                "email_address": {"widget": "text_input", "label": "Email Address:"}
            }
         }
         # --- Add other note types for "Referencing" ---
    },
    "Client Contact": {
         # --- Add note types for "Client Contact" ---
         # "Initial Call Log": { ... }
    },
    "Candidate Contact": {
         # --- Add note types for "Candidate Contact" ---
         # "Interview Scheduled": { ... }
    }
}

# --- Helper Function ---
def get_current_date():
    # Use current date based on context provided (May 3, 2025)
    # For real-world use, datetime.date.today() is better
    try:
        # Attempt to parse the specific date, fallback to today if error
        return datetime.datetime.strptime("2025-05-03", "%Y-%m-%d").date().strftime("%Y-%m-%d")
    except ValueError:
        return datetime.date.today().strftime("%Y-%m-%d")


# --- 2. Sidebar Structure ---
st.sidebar.title("Note Categories")

# Select Category using Radio buttons for a tab-like feel
categories = list(workflows.keys())
selected_category = st.sidebar.radio(
    "Select Category:",
    options=categories,
    key="category_selector"
)

# Select Specific Note Type within Category
selected_note_type = None
note_types_in_category = []
if selected_category and workflows[selected_category]: # Check if category has notes defined
    note_types_in_category = list(workflows[selected_category].keys())
    if note_types_in_category:
        selected_note_type = st.sidebar.selectbox(
            f"Select '{selected_category}' Note Type:",
            options=note_types_in_category,
            key=f"note_type_selector_{selected_category}" # Unique key per category
        )
    else:
         st.sidebar.info(f"No note types defined for '{selected_category}' yet.")
elif selected_category:
     st.sidebar.warning(f"No note types defined for '{selected_category}' yet.")


# --- 3. Main Area for Inputs and Output ---
st.title("Case Note Generator")

if selected_category and selected_note_type:
    st.header(f"{selected_category}: {selected_note_type}")
    st.markdown("---")

    # Get the details for the selected note type
    workflow_details = workflows[selected_category][selected_note_type]
    template = workflow_details["template"]
    input_config = workflow_details.get("input_config", {}) # Get input configuration

    user_inputs = {} # To store values formatted for the template
    widget_values = {} # To store raw values from widgets for logic

    st.subheader("Enter Details:")

    # --- Generate Input Widgets Based on Configuration ---
    for placeholder_name, config in input_config.items():
        widget_type = config.get("widget", "text_input") # Default to text input
        widget_key = f"{selected_category}_{selected_note_type}_{placeholder_name}"

        if widget_type == "text_input":
            label = config.get("label", placeholder_name.replace("_", " ").title() + ":")
            widget_values[placeholder_name] = st.text_input(label, key=widget_key)
            # Assume direct mapping for standard text inputs
            user_inputs[placeholder_name] = widget_values[placeholder_name]

        elif widget_type == "selectbox_conditional":
            options = config.get("options", [])
            label = config.get("label", placeholder_name.replace("_", " ").title() + ":")
            conditional_config = config.get("conditional_input", {})
            trigger_option = conditional_config.get("trigger_option")
            conditional_prompt = conditional_config.get("prompt", "Enter details:")
            format_string = conditional_config.get("format_string", "{}")

            # Main selectbox
            selection = st.selectbox(label, options=options, key=widget_key + "_select")
            widget_values[placeholder_name + "_selection"] = selection # Store the selection

            conditional_value = ""
            # Conditional text input
            if selection == trigger_option:
                conditional_value = st.text_input(conditional_prompt, key=widget_key + "_conditional")
                widget_values[placeholder_name + "_conditional"] = conditional_value # Store the conditional input

            # Construct the final value for the template placeholder
            if selection == trigger_option:
                # Use the format string if conditional value is provided
                if conditional_value:
                    user_inputs[placeholder_name] = format_string.format(conditional_value)
                else:
                    # Handle case where conditional input is needed but empty
                    user_inputs[placeholder_name] = f"[Requires {conditional_prompt}]" # Or some indicator
            else:
                # Use the selection directly if no conditional input needed/triggered
                user_inputs[placeholder_name] = selection
        # Add elif for other widget types like st.date_input, st.number_input etc.

    # --- Generate and Display the Note ---
    st.markdown("---")
    st.subheader("Generated Note:")

    # Add automatic fields if needed (like current_date)
    # Check if placeholder exists in the template string
    if "{current_date}" in template:
        user_inputs["current_date"] = get_current_date()

    # Check if all required inputs (especially conditional ones) are ready
    ready_to_format = True
    # Example check: If conditional input was triggered but is empty, maybe wait?
    for placeholder_name, config in input_config.items():
         if config.get("widget") == "selectbox_conditional":
             selection = widget_values.get(placeholder_name + "_selection")
             trigger = config.get("conditional_input", {}).get("trigger_option")
             if selection == trigger:
                 conditional_val = widget_values.get(placeholder_name + "_conditional")
                 if not conditional_val: # If the conditional input is empty
                      st.warning(f"Please provide: {config.get('conditional_input', {}).get('prompt', 'conditional details')}")
                      ready_to_format = False
                      # Clear the potentially incomplete input for the template
                      if placeholder_name in user_inputs:
                          del user_inputs[placeholder_name]


    if ready_to_format:
        try:
            # Fill placeholders using the prepared user_inputs dictionary
            generated_note = template.format(**user_inputs)

            st.text_area(
                "Copy the text below:",
                value=generated_note,
                height=150 # Adjust height
            )
        except KeyError as e:
            # This error is less likely now if user_inputs is built carefully
            st.error(f"Error: Template placeholder mismatch. Missing key: {e}. Check template and input configuration.")
            st.error(f"Data available for template: {user_inputs}") # Debugging help
        except Exception as e:
            st.error(f"An error occurred during note generation: {e}")

elif selected_category and not note_types_in_category:
     # Message already shown in sidebar if category exists but has no notes
     pass # Keep main area clean
else:
    st.info("Select a category and note type from the sidebar to begin.")


# --- Footer ---
st.sidebar.markdown("---")
st.sidebar.info(f"Note Generator App")
# Displaying the date being used for {current_date}
st.sidebar.markdown(f"<small>Using Date: {get_current_date()}</small>", unsafe_allow_html=True)