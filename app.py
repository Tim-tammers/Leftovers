import streamlit as st
import requests
import os
from io import BytesIO
from PIL import Image
from openai import OpenAI
import base64 
from dotenv import load_dotenv

# API Keys (store securely, e.g., as environment variables)


if "OPENAI_API_KEY" in st.secrets:
    OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
    GROK_API_KEY = st.secrets["GROK_API_KEY"]
else:
    from dotenv import load_dotenv
    load_dotenv()
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GROK_API_KEY = os.getenv("GROK_API_KEY")

GROK_API_URL = "https://api.x.ai/v1/chat/completions"  # Check xAI docs for exact endpoint
OPENAI_IMAGE_URL = "https://api.openai.com/v1/images/generations"

client = OpenAI(api_key=OPENAI_API_KEY)
# Function to generate recipe using Grok API
def generate_recipe(ingredients: list):
    """Generate recipe using Grok API given list of ingredients."""
    prompt = "Create a simple, delicious recipe using these ingredients. You can add a few items or leave out a few items if they do not pair together well:\n"
    for ing in ingredients:
        prompt += f"- {ing['quantity']} {ing['unit']} {ing['item']}\n"
    prompt += "\nInclude: title, ingredient list with quantities, step-by-step instructions, and estimated time."

    headers = {
        "Authorization": f"Bearer {GROK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "grok-4",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500
    }

    try:
        response = requests.post(GROK_API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        resp_json = response.json()
        return resp_json.get("choices", [{}])[0].get("message", {}).get("content", "No content received.")
    except Exception as e:
        return f"❌ Error generating recipe: {e}"


def generate_image(dish_title: str):
    """Generate image using OpenAI DALL-E (gpt-image-1)."""
    prompt = f"A high-quality, appetizing photo of {dish_title} on a plate, realistic style."
    try:
        result = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )
        image_data = result.data[0]
        if getattr(image_data, "url", None):
            resp = requests.get(image_data.url, timeout=30)
            return Image.open(BytesIO(resp.content))
        elif getattr(image_data, "b64_json", None):
            image_bytes = base64.b64decode(image_data.b64_json)
            return Image.open(BytesIO(image_bytes))
    except Exception as e:
        st.error(f"❌ Error generating image: {e}")
        return None

# --- STREAMLIT APP ---

st.title("🧑‍🍳 Leftovers!")

# --- Ingredients Input Table ---
if "ingredients" not in st.session_state:
    st.session_state["ingredients"] = [{"item": "", "quantity": "", "unit": ""}]

st.subheader("Ingredients")

# Function to remove an ingredient
def remove_ingredient(index):
    st.session_state.ingredients.pop(index)

# Display each ingredient row
for i, ing in enumerate(st.session_state.ingredients):
    cols = st.columns([4, 2, 1])  # Quantity, Unit, Item, Remove button

    ing["item"] = cols[0].text_input("Item", value=ing["item"], key=f"item_{i}")
    ing["quantity"] = cols[1].text_input("Quantity", value=ing["quantity"], key=f"qty_{i}")
    # ing["unit"] = cols[2].text_input("Unit", value=ing["unit"], key=f"unit_{i}")
    
    # Remove button with callback
    cols[2].button(
        "❌",
        key=f"remove_{i}",
        on_click=remove_ingredient,
        args=(i,)
    )

# Add new ingredient row
if st.button("➕ Add Ingredient"):
    st.session_state.ingredients.append({"item": "", "quantity": "", "unit": ""})

has_ingredient = any(ing["item"].strip() for ing in st.session_state["ingredients"])

# --- Generate Recipe + Image ---
if st.button("Generate Recipe & Image", disabled=not has_ingredient):
    if all(ing["item"] for ing in st.session_state["ingredients"]):
        with st.spinner("Generating recipe..."):
            recipe = generate_recipe(st.session_state["ingredients"])
            dish_title = recipe.split("\n")[0].strip() if recipe else "Dish"
            st.session_state["dish_title"] = dish_title

        # Generate image automatically
        with st.spinner("Generating image..."):
            image = generate_image(dish_title)
            if image:
                st.image(image, caption=dish_title)

        st.subheader("Generated Recipe")
        st.text(recipe)
    else:
        st.warning("⚠️ Please fill in all ingredient items.")