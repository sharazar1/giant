import streamlit as st
import yaml # Need to install PyYAML: pip install pyyaml
import datetime
from collections import OrderedDict # To preserve order in sidebar

# --- Configuration ---
YAML_FILE = "templates.yaml"

# --- Helper Function to Format Check Types (from previous step) ---
def format_check_types(selected_types):
    """Joins a list of selected check types into a readable string."""
    if not selected_types:
        return "[No check type selected]"
    elif len(selected_types) == 1:
        return selected_types[0]
    elif len(selected_types) == 2:
        sorted_types = sorted(selected_types)
        return f"{sorted_types[0]} & {sorted_types[1]}"
    elif len(selected_types) == 3:
        return "Credit, Criminal & Directorship"
    else:
         return " & ".join(sorted(selected_types))

# --- Registry for Special Formatting Functions named in YAML ---
# Maps the string name in YAML to the actual Python function
format_functions_registry = {
    "format_check_types": format_check_types
    # Add other formatting functions here if needed for other templates
}

# --- YAML Loading Function ---
@st.cache_data # Cache the loaded data to avoid reloading on every interaction
def load_yaml_data(filepath):
    """Loads YAML data from the specified file."""
    try:
        with open(filepath, 'r') as file:
            # Use OrderedDict to preserve the order from the YAML file if needed
            # For standard dict, use yaml.safe_load(file)
            # data = yaml.load(file, Loader=yaml.FullLoader) # Less safe
            data = yaml.safe_load(file)
            if data is None:
                st.error(f"Error: YAML file '{filepath}' is empty or invalid.")
                return None
            return data
    except FileNotFoundError:
        st.error(f"Error: YAML file '{filepath}' not found.")
        return None
    except yaml.YAMLError as e:
        st.error(f"Error parsing YAML file '{filepath}': {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred while loading YAML: {e}")
        return None


# --- Function to Flatten Hierarchy for Selectbox ---
def get_sidebar_options(data):
    """
    Flattens the nested dictionary structure from YAML into options for the sidebar.
    Returns an OrderedDict mapping display strings to key paths.
    """
    options = OrderedDict()

    def recurse(sub_data, path_list, display_prefix):
        for key, value in sub_data.items():
            if isinstance(value, dict):
                current_display_name = value.get("display_name", key.replace("_", " ").title())
                current_path_list = path_list + [key]
                new_display_prefix = f"{display_prefix}{current_display_name}"

                # If it has 'sub_items', recurse into those
                if "sub_items" in value and isinstance(value["sub_items"], dict):
                     recurse(value["sub_items"], current_path_list, new_display_prefix + " > ")
                # If it has a 'template', it's a selectable note type
                elif "template" in value:
                    options[new_display_prefix] = current_path_list

    recurse(data, [], "")
    return options

# --- Function to Get Nested Item from Data using Path ---
def get_nested_item(data, path_list):
    """Accesses a nested dictionary item using a list of keys."""
    temp_data = data
    try:
        for key in path_list:
            temp_data = temp_data[key]
        return temp_data
    except KeyError:
        st.error(f"Error: Could not find path {path_list} in the loaded data.")
        return None
    except TypeError:
         st.error(f"Error: Problem accessing path {path_list}. Is the structure correct?")
         return None


# --- Load Data ---
template_data = load_yaml_data(YAML_FILE)
sidebar_options = OrderedDict() # Initialize empty
if template_data:
    sidebar_options = get_sidebar_options(template_data)


# --- Sidebar ---
st.sidebar.title("Note Templates")

selected_display_option = None
if sidebar_options:
    selected_display_option = st.sidebar.selectbox(
        "Select Note Template:",
        options=list(sidebar_options.keys()), # Use the display strings as options
        key="template_selector"
    )
else:
    st.sidebar.error("No templates loaded. Check YAML file.")

# --- Main Area ---
st.title("Case Note Generator")

selected_note_data = None
if selected_display_option and template_data and sidebar_options:
    # Get the key path (e.g., ['Checks', 'checks_ordered']) from the selected display string
    selected_key_path = sidebar_options[selected_display_option]
    # Retrieve the specific template's data from the loaded YAML data
    selected_note_data = get_nested_item(template_data, selected_key_path)

if selected_note_data:
    st.header(selected_display_option) # Show the selected path as header
    st.markdown("---")

    template = selected_note_data.get("template", "[Template not found in YAML]")
    input_config = selected_note_data.get("input_config", {})

    user_inputs = {} # To store final values formatted for the template
    widget_values = {} # To store raw values from widgets

    st.subheader("Enter Details:")

    # --- Generate Input Widgets Dynamically ---
    if not input_config:
         st.info("This template requires no additional details.")

    for placeholder_name, config in input_config.items():
        widget_type = config.get("widget", "text_input")
        label = config.get("label", placeholder_name.replace("_", " ").title() + ":")
        placeholder = config.get("placeholder", "")
        options = config.get("options", [])
        format_function_name = config.get("format_function") # Get formatter name string

        # Unique key for widget state management
        widget_key = f"{'_'.join(selected_key_path)}_{placeholder_name}"

        # Store raw widget value
        raw_value = None

        # Create the appropriate widget
        if widget_type == "text_input":
            raw_value = st.text_input(label, key=widget_key, placeholder=placeholder)
        elif widget_type == "text_area":
            raw_value = st.text_area(label, key=widget_key, placeholder=placeholder)
        elif widget_type == "multiselect":
             raw_value = st.multiselect(label, options=options, key=widget_key)
        # Add elif for other widget types (e.g., selectbox, number_input, date_input) here
        # elif widget_type == "selectbox":
        #    raw_value = st.selectbox(label, options=options, key=widget_key)
        # elif widget_type == "number_input":
        #    raw_value = st.number_input(label, key=widget_key, ...) # Add step, format etc.
        # elif widget_type == "date_input":
        #    raw_value = st.date_input(label, key=widget_key)

        else:
            st.warning(f"Unsupported widget type '{widget_type}' defined in YAML for '{placeholder_name}'. Using text input.")
            raw_value = st.text_input(label, key=widget_key, placeholder=placeholder)

        widget_values[placeholder_name] = raw_value # Store raw value

        # --- Apply Formatting Function if Specified ---
        final_value = raw_value # Default to raw value
        if format_function_name:
            if format_function_name in format_functions_registry:
                formatting_function = format_functions_registry[format_function_name]
                try:
                    final_value = formatting_function(raw_value)
                except Exception as format_e:
                     st.error(f"Error applying format function '{format_function_name}' to '{placeholder_name}': {format_e}")
                     final_value = "[Formatting Error]" # Indicate error in output
            else:
                st.error(f"Formatting function '{format_function_name}' specified in YAML but not found in Python registry.")
                final_value = "[Unknown Format Function]"

        # Add the final processed value to user_inputs for template .format()
        user_inputs[placeholder_name] = final_value


    # --- Generate and Display the Note ---
    st.markdown("---")
    st.subheader("Generated Note:")

    # Add automatic fields if needed (e.g., current_date)
    if "{current_date}" in template:
         # Using today's date. Adjust if needed.
        user_inputs["current_date"] = datetime.date.today().strftime("%Y-%m-%d")

    # Basic validation (optional - enhance as needed)
    inputs_complete = True # Assume complete unless an issue found
    # Add checks here if specific fields are mandatory but empty

    if inputs_complete:
        try:
            # Fill placeholders
            generated_note = template.format(**user_inputs)

            st.text_area(
                "Copy the text below:",
                value=generated_note,
                height=200 # Adjust height
            )
        except KeyError as e:
             st.error(f"Error: Placeholder {{{e}}} in the template was not provided a value. Check YAML input_config and Python logic.")
             st.caption(f"Data provided to template: `{user_inputs}`") # Help debugging
        except Exception as e:
            st.error(f"An error occurred during note generation: {e}")
    # else:
        # Optionally show a placeholder or warning if inputs not complete

else:
    st.info("Select a note template from the sidebar to begin.")


# --- Footer ---
st.sidebar.markdown("---")
st.sidebar.info("Note Generator v2.0")