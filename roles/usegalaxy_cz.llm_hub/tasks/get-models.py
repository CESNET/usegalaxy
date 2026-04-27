import requests
from typing import List, Dict, Optional, Any

def transform_model_data(table_data: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Transforms the parsed markdown table data into a simplified list of dictionaries
    containing only model_name, description, and a multimodal boolean.

    Label: Gemini 2026
    """
    transformed_data = []

    for row in table_data:
        # Extract the relevant fields, defaulting to empty strings if a key is missing
        model_name = row.get('Model Name', '')
        description = row.get('Description', '')
        capabilities = row.get('Capability', '').lower()

        # Check if 'multimodal' is present in the capabilities string
        is_multimodal = 'multimodal' in capabilities

        transformed_data.append({
            'model_name': model_name,
            'description': description,
            'multimodal': is_multimodal
        })

    return transformed_data

def get_markdown_table(url: str, section_header: str = "#### Guaranteed Models") -> List[Dict[str, str]]:
    """
    Downloads a markdown file from a URL, finds a specific section, 
    and parses the first markdown table it encounters into a list of dictionaries.
    """
    try:
        # 1. Download the markdown file
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for bad status codes
        markdown_content = response.text
    except requests.RequestException as e:
        print(f"Error downloading the file: {e}")
        return []

    lines = markdown_content.splitlines()
    
    in_target_section = False
    in_table = False
    headers: List[str] = []
    parsed_data: List[Dict[str, str]] = []

    # 2. Parse the file line by line
    for line in lines:
        stripped_line = line.strip()

        # Check if we've reached the target section
        if stripped_line == section_header:
            in_target_section = True
            continue

        # If we are in another section (denoted by #), stop looking
        if in_target_section and stripped_line.startswith("#") and not in_table:
            print(f"Section '{section_header}' found, but no table was present.")
            break

        # 3. Look for the table within the section
        if in_target_section:
            # Standard markdown tables start and end with a pipe character '|'
            if stripped_line.startswith("|") and stripped_line.endswith("|"):
                in_table = True
                
                # Extract cell values, ignoring the first and last empty strings from the split
                raw_cells = stripped_line.split("|")[1:-1]
                cells = [cell.strip() for cell in raw_cells]

                # If headers aren't set yet, this is the header row
                if not headers:
                    headers = cells
                    continue
                
                # Check if this is the separator row (e.g., |---|---|)
                if all(all(char in '-:' for char in cell.strip()) for cell in cells):
                    continue
                
                # Otherwise, it's a data row
                row_dict = dict(zip(headers, cells))
                parsed_data.append(row_dict)
                
            elif in_table and not stripped_line.startswith("|"):
                # We reached the end of the table
                break

    if not in_target_section:
         print(f"Warning: Section '{section_header}' was not found in the document.")

    return parsed_data

# ==========================================
# Example Usage
# ==========================================
if __name__ == "__main__":
    TARGET_URL = "https://raw.githubusercontent.com/CERIT-SC/kube-docs/refs/heads/fumadocs/content/docs/ai-as-a-service/chat-ai.mdx"
    
    guaranteed = transform_model_data(get_markdown_table(TARGET_URL, "#### Guaranteed Models"))
    experimental = transform_model_data(get_markdown_table(TARGET_URL, "#### Experimental Models"))
    
    print("#<value>	<model_id>	<display_name>	<domain>	<provider>	<free_tag>")

    for m in guaranteed:
        name,desc,mm = m['model_name'],m['description'],m['multimodal']
        print(f'{name}\t{name}\t{desc}\t{"multimodal" if mm else "text"}\tCERIT-SC\tguaranteed')

    for m in experimental:
        name,desc,mm = m['model_name'],m['description'],m['multimodal']
        print(f'{name}\t{name}\t{desc}\t{"multimodal" if mm else "text"}\tCERIT-SC\texperimental')


